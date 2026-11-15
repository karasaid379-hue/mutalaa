using System.Globalization;
using Mutalaa.Domain.Content;
using Mutalaa.Domain.Releases;
using Mutalaa.Domain.Text;

namespace Mutalaa.Domain.Reviews;

/// <summary>Kitap onayinin onkosul kodlari (422 <c>on-kosul-eksik</c> yanitinin <c>eksikler</c> listesi; K-52 madde 11).</summary>
public static class RisaleApprovalPrerequisites
{
    /// <summary>Tur 1: kitabin birimlerinden en az biri, G-BUT dahil dort kapidan gecmis bir hat yuklemesinden gelmiyor.</summary>
    public const string GbutKanitiYok = "gbut-kaniti-yok";

    /// <summary>Slug <c>risale-kitaplar.json</c> icinde <c>dogrulandi: true</c> degil (i-24).</summary>
    public const string SlugDogrulanmadi = "slug-dogrulanmadi";

    /// <summary>Tur 2: orneklem okumasi yapildi bayragi istekte yok ya da false.</summary>
    public const string OrnekOkumaYok = "ornek-okuma-yok";
}

/// <summary>Kitabin bir etkin birimi: capa, icerik ozeti, metin durumu ve kaynakla bayt esitligi kaniti.</summary>
/// <param name="Anchor">Birim capasi (<c>rn:{slug}:...</c>).</param>
/// <param name="ContentHash">64 kucuk harf onaltilik.</param>
/// <param name="MetinDurumu">Birimin editoryal durumu.</param>
/// <param name="HasGbutEvidence">
/// Birimin <c>run_id</c> degeri, <c>durum = basarili</c> ve <c>manifest.qa_rapor</c> dolu bir hat calismasina isaret ediyor.
/// Hat yuklemesi yalniz dort kapi (G-KAY, G-BUT, G-CAP, G-NOR) gectiginde yazilir; bu yuzden kanit yuklemenin kendisidir.
/// </param>
public readonly record struct RisaleBookUnit(string Anchor, string ContentHash, TextStatus MetinDurumu, bool HasGbutEvidence);

/// <summary>Kitap durumunun saf ozeti: sayilar, ozet, istek disi onkosullar.</summary>
/// <param name="Digest">Kitap ozeti: <see cref="RisaleBookApproval.ComputeDigest"/>.</param>
/// <param name="Total">Etkin birim sayisi.</param>
/// <param name="Draft"><c>taslak</c> birim sayisi.</param>
/// <param name="Approved"><c>onayli</c> birim sayisi.</param>
/// <param name="WithoutEvidence">G-BUT kaniti olmayan birim sayisi.</param>
/// <param name="SlugVerified">Slug dogrulandi mi (i-24).</param>
public readonly record struct RisaleBookAssessment(string Digest, int Total, int Draft, int Approved, int WithoutEvidence, bool SlugVerified)
{
    /// <summary>Kitapta birim varsa ve hepsinin kaniti varsa.</summary>
    public bool GbutEvidence => Total > 0 && WithoutEvidence == 0;
}

/// <summary>Kitap onayi karari: onayla, bayat surum, onkosul eksik ya da onaylanacak birim yok.</summary>
public enum RisaleApprovalOutcome
{
    /// <summary>Taslak birimler <c>onayli</c> yapilir.</summary>
    Approve = 0,

    /// <summary>If-Match ozeti guncel kitap ozetiyle ayni degil (412).</summary>
    Stale = 1,

    /// <summary>Onkosul eksik (422 <c>on-kosul-eksik</c>).</summary>
    PrerequisitesMissing = 2,

    /// <summary>Kitapta onaylanacak <c>taslak</c> birim yok (422 <c>onaylanacak-birim-yok</c>).</summary>
    NothingToApprove = 3,
}

/// <summary>Karar ve eksik onkosul kodlari (sabit sirada: G-BUT, slug, orneklem).</summary>
public readonly record struct RisaleApprovalVerdict(RisaleApprovalOutcome Outcome, IReadOnlyList<string> Missing);

/// <summary>
/// Kitap bazinda toplu onay kurali (K-52 madde 11), saf islevler: veritabani, saat ve HTTP yok.
/// <para>
/// Kitap ozeti: kitabin etkin birimlerinin <c>anchor</c> ve <c>content_hash</c> cifti <see cref="ContentDigest"/> ile ozetlenir
/// (capa BAYT sirasi, her satir <c>anchor TAB content_hash LF</c>, SHA-256, 64 kucuk harf onaltilik; K-46 kaynak ozetiyle ayni algoritma).
/// Metin durumu ozete girmez: onay metni ve ozeti degistirmez, bu yuzden ayni <c>If-Match</c> ile ikinci cagri 412 degil
/// <c>onaylanacak-birim-yok</c> alir. ETag bicimi <c>"{64 hex}"</c> (yalniz guclu ve tek etiket).
/// </para>
/// </summary>
public static class RisaleBookApproval
{
    /// <summary>Gerekce uzunluk ust siniri (kod noktasi); inceleme kararlariyla ayni.</summary>
    public const int MaxGerekceLength = ReviewDecisions.MaxGerekceLength;

    /// <summary>Birim <c>risale</c> kaynaklarinin capa oneki: <c>rn:{slug}:</c>.</summary>
    public static string AnchorPrefix(string slug)
    {
        ArgumentException.ThrowIfNullOrEmpty(slug);
        return string.Create(CultureInfo.InvariantCulture, $"rn:{slug}:");
    }

    /// <summary>Hedef anahtar: <c>risale:{kitap}</c> (review.hedef_anahtar, hedef_tablo = source).</summary>
    public static string TargetKey(string slug)
    {
        ArgumentException.ThrowIfNullOrEmpty(slug);
        return "risale:" + slug;
    }

    /// <summary>Kitap ozeti; girdi sirasindan bagimsizdir. Bos kitap: girdisiz SHA-256.</summary>
    public static string ComputeDigest(IEnumerable<RisaleBookUnit> units)
    {
        ArgumentNullException.ThrowIfNull(units);
        return ContentDigest.Compute(units.Select(u => new ContentDigestEntry(u.Anchor, u.ContentHash)));
    }

    /// <summary>Kitap durumunun ozeti (sayilar, ozet, kanit).</summary>
    public static RisaleBookAssessment Assess(bool slugVerified, IReadOnlyCollection<RisaleBookUnit> units)
    {
        ArgumentNullException.ThrowIfNull(units);
        int draft = 0;
        int approved = 0;
        int withoutEvidence = 0;
        foreach (RisaleBookUnit unit in units)
        {
            if (unit.MetinDurumu == TextStatus.Taslak)
            {
                draft++;
            }
            else if (unit.MetinDurumu == TextStatus.Onayli)
            {
                approved++;
            }

            if (!unit.HasGbutEvidence)
            {
                withoutEvidence++;
            }
        }

        return new RisaleBookAssessment(ComputeDigest(units), units.Count, draft, approved, withoutEvidence, slugVerified);
    }

    /// <summary>
    /// Karar sirasi: surum (412) -> onkosullar (422) -> onaylanacak birim (422). Onkosul eksikleri birlikte ve sabit sirada doner.
    /// </summary>
    /// <param name="assessment">Guncel kitap durumu.</param>
    /// <param name="ifMatchDigest">Istemcinin If-Match ozeti.</param>
    /// <param name="sampleReadingDone">Orneklem okumasi bayragi (tur 2).</param>
    public static RisaleApprovalVerdict Decide(RisaleBookAssessment assessment, string ifMatchDigest, bool sampleReadingDone)
    {
        ArgumentNullException.ThrowIfNull(ifMatchDigest);

        if (!string.Equals(assessment.Digest, ifMatchDigest, StringComparison.Ordinal))
        {
            return new RisaleApprovalVerdict(RisaleApprovalOutcome.Stale, []);
        }

        List<string> missing = Missing(assessment, sampleReadingDone);
        if (missing.Count > 0)
        {
            return new RisaleApprovalVerdict(RisaleApprovalOutcome.PrerequisitesMissing, missing);
        }

        return assessment.Draft == 0
            ? new RisaleApprovalVerdict(RisaleApprovalOutcome.NothingToApprove, [])
            : new RisaleApprovalVerdict(RisaleApprovalOutcome.Approve, []);
    }

    /// <summary>Eksik onkosul kodlari (G-BUT kaniti, slug, orneklem okumasi sirasiyla).</summary>
    public static List<string> Missing(RisaleBookAssessment assessment, bool sampleReadingDone)
    {
        List<string> missing = [];
        if (assessment.WithoutEvidence > 0)
        {
            missing.Add(RisaleApprovalPrerequisites.GbutKanitiYok);
        }

        if (!assessment.SlugVerified)
        {
            missing.Add(RisaleApprovalPrerequisites.SlugDogrulanmadi);
        }

        if (!sampleReadingDone)
        {
            missing.Add(RisaleApprovalPrerequisites.OrnekOkumaYok);
        }

        return missing;
    }

    /// <summary>ETag degeri: <c>"{ozet}"</c>.</summary>
    public static string FormatEtag(string digest)
    {
        ArgumentNullException.ThrowIfNull(digest);
        return "\"" + digest + "\"";
    }

    /// <summary>
    /// Yalniz <c>"{64 kucuk harf onaltilik}"</c> biciminde, tek ve guclu etiket kabul eder (<c>*</c>, <c>W/</c>, liste ve buyuk harf yok).
    /// </summary>
    public static bool TryParseEtag(string? value, out string digest)
    {
        digest = string.Empty;
        if (value is null || value.Length != 66 || value[0] != '"' || value[^1] != '"')
        {
            return false;
        }

        foreach (char c in value.AsSpan(1, 64))
        {
            if (c is not ((>= '0' and <= '9') or (>= 'a' and <= 'f')))
            {
                return false;
            }
        }

        digest = value[1..^1];
        return true;
    }

    /// <summary>Gerekce: zorunlu, bos degil, en cok 2.000 kod noktasi (inceleme kararlariyla ayni kural). Gecerliyse null, degilse ileti.</summary>
    public static string? CheckGerekce(string? gerekce)
    {
        if (string.IsNullOrWhiteSpace(gerekce))
        {
            return "gerekce zorunludur.";
        }

        return CodePointOffsets.CodePointCount(gerekce) > MaxGerekceLength ? "gerekce en çok 2.000 karakter olabilir." : null;
    }
}
