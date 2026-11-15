using System.Globalization;
using System.Text;
using System.Text.Json;
using Mutalaa.Domain.Anchors;
using Mutalaa.Domain.Links;
using Mutalaa.Domain.Text;

namespace Mutalaa.Domain.Reviews;

/// <summary>"Uzmana gonder" (K-51 madde 2): acik kaydi <c>uzmanda</c> durumuna alir; karari yalniz <c>uzman</c> rolu verir.</summary>
public static class ReviewHandoff
{
    /// <summary>
    /// Sonucu hesaplar (saf). Kaydin ozgun eylemi, oneri, duzenlenen deger ve ikinci onay alanlari korunur; gonderen <c>inceleyen</c>, gerekce
    /// <c>gerekce</c> alanina yazilir (denetim icin <c>ikinci_gerekce</c> kullanilmaz). Yalniz <c>acik</c> kayit gonderilir (aksi 409
    /// <c>durum-gecisi-gecersiz</c>); desteklenmeyen hedef ve birim metni (meal ve tefsirde ikinci onay akisiyla cakisir) 422
    /// <c>inceleme-desteklenmiyor</c>; gerekce zorunlu (400).
    /// </summary>
    public static ReviewOutcome ToExpert(Review review, string? actor, string? gerekce, DateTime now)
    {
        ArgumentNullException.ThrowIfNull(review);

        if (!ReviewDecisions.IsSupported(review.HedefTablo, review.Alan))
        {
            throw new DomainException(
                DomainErrorCodes.IncelemeDesteklenmiyor,
                $"'{review.HedefTablo}' hedefinde '{review.Alan}' alani icin inceleme desteklenmiyor.");
        }

        string who = ReviewDecisions.RequireActor(actor);
        string reason = ReviewDecisions.RequireGerekce(gerekce);

        if (string.Equals(review.HedefTablo, ReviewTargets.Unit, StringComparison.Ordinal))
        {
            throw new DomainException(
                DomainErrorCodes.IncelemeDesteklenmiyor,
                "Birim metni incelemesi uzmana gonderilemez (meal ve tefsirde ikinci onay akisi vardir).");
        }

        if (review.Durum != ReviewStatus.Acik)
        {
            throw new DomainException(
                DomainErrorCodes.DurumGecisiGecersiz,
                $"Yalniz acik kayit uzmana gonderilir (durum: {review.Durum.ToLabel()}).");
        }

        return new ReviewOutcome
        {
            Durum = ReviewStatus.Uzmanda,
            Eylem = review.Eylem,
            Inceleyen = who,
            IncelendiAt = now,
            Gerekce = reason,
            Duzenlenen = review.Duzenlenen,
            IkinciInceleyen = review.IkinciInceleyen,
            IkinciIncelendiAt = review.IkinciIncelendiAt,
            IkinciGerekce = review.IkinciGerekce,
        };
    }
}

/// <summary>
/// Baglanti kuyrugunun ek eylemleri (A18.4): "Ima olarak isaretle" ve "Kalip listesine ekle". Saf islevler; kimlikleri cagiran verir,
/// veritabani yazimi cagiranindir.
/// </summary>
public static class LinkQueueActions
{
    /// <summary>Kalip anahtari ust siniri (kod birimi); eslesen dizi bundan uzunsa kalip degildir.</summary>
    public const int MaxPatternKeyLength = 1000;

    /// <summary>
    /// Ima: acik adayin kaynak ucundan ayni hedefe yeni bir <c>ima</c> satiri acar (<c>origin = editor</c>, <c>status = onayli</c>,
    /// <c>confidence = 1</c>); ozgun aday korunur. Ayni dogal anahtar zaten varsa cakisma veritabaninin tekil kisitiyla 409 olur.
    /// Kaynak tur <c>atif</c> ya da <c>iktibas</c> olmali (<c>ima</c> zaten ima: 409; baska tur 422). Kaynak kayit acik olmali (409).
    /// Denetim kaydi (<c>review</c>, kapali, <c>onaylandi</c>) yeni satirla birlikte doner.
    /// </summary>
    public static (Xref Ima, Review Audit) MarkIma(Xref source, Review sourceReview, Guid newId, string? actor, string? gerekce, DateTime now)
    {
        ArgumentNullException.ThrowIfNull(source);
        ArgumentNullException.ThrowIfNull(sourceReview);

        string who = ReviewDecisions.RequireActor(actor);
        string reason = ReviewDecisions.RequireGerekce(gerekce);
        RequireLinkReview(sourceReview, source);
        if (source.Type == XrefType.Ima)
        {
            throw new DomainException(DomainErrorCodes.DurumGecisiGecersiz, "Baglanti zaten bir ima.");
        }

        if (source.Type is not (XrefType.Atif or XrefType.Iktibas))
        {
            throw new DomainException(
                DomainErrorCodes.IncelemeDesteklenmiyor,
                $"'{source.Type.ToLabel()}' baglantisi ima olarak isaretlenemez; yalniz atif ve iktibas adaylari.");
        }

        Xref ima = new()
        {
            Id = newId,
            SrcAnchor = source.SrcAnchor,
            SrcSpan = source.SrcSpan,
            DstAnchor = source.DstAnchor,
            DstSpan = source.DstSpan,
            Type = XrefType.Ima,
            Score = 1f,
            Confidence = 1f,
            Evidence = ImaEvidence(source),
            Origin = XrefOrigin.Editor,
            Status = XrefStatus.Onayli,
            DataVersion = source.DataVersion,
        };

        Review audit = new()
        {
            HedefTablo = ReviewTargets.Xref,
            HedefAnahtar = newId.ToString("D", CultureInfo.InvariantCulture),
            XrefId = newId,
            Alan = ReviewFields.Status,
            Eylem = ReviewActions.ImaIsaretle,
            Onceki = Json(("kaynak_xref", source.Id.ToString("D", CultureInfo.InvariantCulture)), ("kaynak_review", sourceReview.Id.ToString(CultureInfo.InvariantCulture))),
            Onerilen = Json(("type", "ima")),
            Durum = ReviewStatus.Onaylandi,
            Koken = XrefOrigin.Editor,
            Oneren = who,
            Inceleyen = who,
            IncelendiAt = now,
            Gerekce = reason,
        };
        return (ima, audit);
    }

    /// <summary>
    /// Kalip listesine ekle: eslesen dizinin normalize anahtarini <c>kalip_ekle</c> kapali denetim kaydi olarak yazar
    /// (<c>onerilen = {anahtar, gerekce}</c>, durum <c>onaylandi</c>) ve adayi reddeder (<c>red</c>). Kalip listesi dosyasi hatta bu
    /// kayitlardan disa aktarilir. Yalniz <c>iktibas</c> adayi ve acik, aday satir (aksi 409/422).
    /// </summary>
    /// <param name="srcText">Kaynak birimin metni; anahtar kanitta yoksa eslesen diziden turetilir.</param>
    /// <param name="srcContentHash">Kaynak birimin guncel ozeti (kanit <c>src_hash</c> ile uyusmuyorsa dilim guvenilmez, anahtar uretilmez).</param>
    public static (ReviewOutcome Reject, Review Audit, string Key) AddToPatternList(
        Review review,
        Xref source,
        string? srcText,
        string? srcContentHash,
        string? actor,
        string? gerekce,
        DateTime now)
    {
        ArgumentNullException.ThrowIfNull(review);
        ArgumentNullException.ThrowIfNull(source);

        string who = ReviewDecisions.RequireActor(actor);
        string reason = ReviewDecisions.RequireGerekce(gerekce);
        RequireLinkReview(review, source);
        if (source.Type != XrefType.Iktibas)
        {
            throw new DomainException(
                DomainErrorCodes.IncelemeDesteklenmiyor,
                $"Kalip listesine yalniz iktibas adaylari eklenir (bu baglanti: '{source.Type.ToLabel()}').");
        }

        string key = PatternKey(source.Evidence, srcText, srcContentHash, source.SrcSpan);

        ReviewOutcome reject = ReviewDecisions.Reject(
            review,
            new ReviewDecisionRequest { Actor = who, Gerekce = reason, Now = now },
            ReviewTargetState.ForStatus(source.Status));

        Review audit = new()
        {
            HedefTablo = ReviewTargets.Xref,
            HedefAnahtar = source.Id.ToString("D", CultureInfo.InvariantCulture),
            XrefId = source.Id,
            Alan = "kalip_listesi",
            Eylem = ReviewActions.KalipEkle,
            Onerilen = Json(("anahtar", key), ("gerekce", reason)),
            Durum = ReviewStatus.Onaylandi,
            Koken = XrefOrigin.Editor,
            Oneren = who,
            Inceleyen = who,
            IncelendiAt = now,
            Gerekce = reason,
        };
        return (reject, audit, key);
    }

    /// <summary>
    /// Eslesen dizinin normalize anahtari: kanitta <c>phrase_key</c> (hattin verdigi) varsa o, yoksa kaynak metnin kaynak araligindaki
    /// diliminin Arapca arama anahtari (<c>ar_norm</c>). Anahtar bossa ya da cok uzunsa 422 <c>inceleme-desteklenmiyor</c>.
    /// </summary>
    public static string PatternKey(string? evidenceJson, string? srcText, string? srcContentHash, AnchorSpan? srcSpan)
    {
        string? raw = LinkEvidenceReader.ReadString(evidenceJson, "phrase_key");
        if (string.IsNullOrWhiteSpace(raw))
        {
            HighlightedSequence highlight = LinkHighlight.Compute(srcText, srcContentHash, LinkEvidenceReader.ReadString(evidenceJson, "src_hash"), srcSpan);
            raw = srcSpan is null ? null : highlight.Dizi;
        }

        string key = string.IsNullOrWhiteSpace(raw) ? string.Empty : SearchNormalizer.Keys(raw).ArNorm.Trim();
        if (key.Length == 0 || key.Length > MaxPatternKeyLength)
        {
            throw new DomainException(
                DomainErrorCodes.IncelemeDesteklenmiyor,
                "Kalip anahtari uretilemedi: eslesen dizi kanitta yok ya da kaynak metnin ozeti uyusmuyor.");
        }

        return key;
    }

    private static void RequireLinkReview(Review review, Xref source)
    {
        if (!string.Equals(review.HedefTablo, ReviewTargets.Xref, StringComparison.Ordinal)
            || !string.Equals(review.Alan, ReviewFields.Status, StringComparison.Ordinal))
        {
            throw new DomainException(DomainErrorCodes.IncelemeDesteklenmiyor, "Bu eylem yalniz baglanti adayi incelemesinde kullanilir.");
        }

        if (review.Durum != ReviewStatus.Acik)
        {
            throw new DomainException(DomainErrorCodes.DurumGecisiGecersiz, $"Yalniz acik kayit uzerinde calisir (durum: {review.Durum.ToLabel()}).");
        }

        if (source.Status != XrefStatus.Aday)
        {
            throw new DomainException(DomainErrorCodes.DurumGecisiGecersiz, $"Hedef aday degil (durum: {source.Status.ToLabel()}).");
        }
    }

    /// <summary>Ima kaniti: kaynak adayin uc ozetleri korunur (Yayinlayici uc ozetlerini ister), yeni kayit editor imasidir.</summary>
    private static string ImaEvidence(Xref source)
    {
        using MemoryStream stream = new();
        using (Utf8JsonWriter writer = new(stream))
        {
            writer.WriteStartObject();
            writer.WriteBoolean("editor_ima", true);
            WriteCopy(writer, source.Evidence, "src_hash");
            WriteCopy(writer, source.Evidence, "dst_hash");
            WriteCopy(writer, source.Evidence, "source_id");
            writer.WriteEndObject();
        }

        return Encoding.UTF8.GetString(stream.ToArray());
    }

    private static void WriteCopy(Utf8JsonWriter writer, string evidenceJson, string name)
    {
        string? value = LinkEvidenceReader.ReadString(evidenceJson, name);
        if (value is not null && value.Length <= LinkEvidenceSummary.MaxStringLength)
        {
            writer.WriteString(name, value);
        }
    }

    private static string Json(params (string Name, string Value)[] pairs)
    {
        using MemoryStream stream = new();
        using (Utf8JsonWriter writer = new(stream))
        {
            writer.WriteStartObject();
            foreach ((string name, string value) in pairs)
            {
                writer.WriteString(name, value);
            }

            writer.WriteEndObject();
        }

        return Encoding.UTF8.GetString(stream.ToArray());
    }
}
