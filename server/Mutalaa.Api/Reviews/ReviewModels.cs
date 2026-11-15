using System.Text.Json;
using System.Text.Json.Serialization;
using Mutalaa.Api.Lemmas;
using Mutalaa.Domain.Reviews;

namespace Mutalaa.Api.Reviews;

/// <summary>Kuyruk ve ayrinti ortak alanlari. jsonb sutunlari (yz_kaydi, onceki, onerilen, duzenlenen) JSON nesnesi olarak doner.</summary>
public record ReviewItemDto
{
    public required long Id { get; init; }

    public required string HedefTablo { get; init; }

    public required string HedefAnahtar { get; init; }

    public Guid? XrefId { get; init; }

    public required string Alan { get; init; }

    public required string Eylem { get; init; }

    /// <summary>acik, onaylandi, reddedildi, geri_alindi.</summary>
    public required string Durum { get; init; }

    /// <summary>hat, editor, kullanici_oyu.</summary>
    public required string Koken { get; init; }

    public string? YzModeli { get; init; }

    public JsonElement? YzKaydi { get; init; }

    /// <summary>Degisiklikten onceki deger; unit + metin icin {metin, content_hash}, deger yoksa null.</summary>
    public JsonElement? Onceki { get; init; }

    /// <summary>Onerilen deger; unit + metin icin {metin, content_hash}, surah_alias icin onerilen alanlar, deger yoksa null.</summary>
    public JsonElement? Onerilen { get; init; }

    /// <summary>Editorun duzenledigi deger; unit + metin icin {metin, content_hash}, deger yoksa null.</summary>
    public JsonElement? Duzenlenen { get; init; }

    public float? Guven { get; init; }

    public required string Oneren { get; init; }

    public string? Inceleyen { get; init; }

    public string? IkinciInceleyen { get; init; }

    public DateTime? IkinciIncelendiAt { get; init; }

    public required DateTime CreatedAt { get; init; }

    public DateTime? IncelendiAt { get; init; }

    /// <summary>Iyimser eszamanlilik surumu (ETag degeri); karar bu sayiyi geri ister.</summary>
    public required uint Xmin { get; init; }

    /// <summary>K-25: yz_modeli dolu ve hedef onayli degil.</summary>
    public required bool Dogrulanmamis { get; init; }

    /// <summary>Meal ya da tefsir metninde ilk onay verilmis, ikinci onay bekleniyor.</summary>
    public required bool IkinciOnayBekliyor { get; init; }

    /// <summary>
    /// Baglanti adayi sinifi (hedef_tablo xref; A18.4): tutarsiz, toplu, gri, diger. Kural <c>LinkCandidateClassifier</c>'dir;
    /// baglanti satiri okunamiyorsa ve baska hedeflerde yazilmaz.
    /// </summary>
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public string? Sinif { get; init; }

    /// <summary>Kelime anlami dalgasi (0..4): hedef lemma ya da lemma_gloss ise lemma_dalga.dalga; satir yoksa ve baska hedeflerde yazilmaz.</summary>
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public int? Dalga { get; init; }

    /// <summary>Hedef lemmanin onay yolu (editor, otomatik); yalniz Turkce lemma hedefinde ve yolu varsa yazilir (aday lemmada yok).</summary>
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public string? OnayYolu { get; init; }
}

public sealed record ReviewListResponse(IReadOnlyList<ReviewItemDto> Items, string? NextCursor);

public sealed record ReviewDetailDto : ReviewItemDto
{
    public string? Gerekce { get; init; }

    public string? IkinciGerekce { get; init; }

    public int? SureMs { get; init; }

    /// <summary>Hedef satirin anlik gorunumu; desteklenmeyen hedefte ya da satir yoksa null.</summary>
    public ReviewTargetSnapshot? Hedef { get; init; }

    /// <summary>Hedefin onayli olup olmadigi (hedef durumundan turetilir, saklanmaz).</summary>
    public required bool Dogrulanmis { get; init; }
}

/// <summary>Hedef tabloya gore dolan alanlar; bos alanlar yazilmaz.</summary>
public sealed record ReviewTargetSnapshot
{
    public required string Tablo { get; init; }

    // unit
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public string? Anchor { get; init; }

    /// <summary>unit: birim turu; surah_alias: ad turu.</summary>
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public string? Kind { get; init; }

    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public string? Source { get; init; }

    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public string? Metin { get; init; }

    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public string? ContentHash { get; init; }

    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public string? MetinDurumu { get; init; }

    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public int? Rev { get; init; }

    // surah_alias
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public int? SurahNo { get; init; }

    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public string? Alias { get; init; }

    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public bool? Risky { get; init; }

    // xref, quran_word_fix
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public Guid? Id { get; init; }

    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public string? SrcAnchor { get; init; }

    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public string? DstAnchor { get; init; }

    // xref (A18.4)

    /// <summary>xref: baglanti turu (atif, iktibas, ima, kok, lemma, benzer_ayet ...).</summary>
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public string? Type { get; init; }

    /// <summary>xref: kaynak uc araligi <c>[bas, son]</c> iki sayi (yari acik; metin biriminde kod noktasi, Kur'an ucunda kelime konumu); yok = birimin tamami.</summary>
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public int[]? SrcSpan { get; init; }

    /// <summary>xref: hedef uc araligi; <see cref="SrcSpan"/> ile ayni anlam.</summary>
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public int[]? DstSpan { get; init; }

    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public float? Score { get; init; }

    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public float? Confidence { get; init; }

    /// <summary>xref: kanit ozeti (beyaz listeli anahtarlar: matched_words, ayah_words, coverage, identity, phrase_freq, consistent_quote, position, subtype, group, alternatives, src_hash, dst_hash, source_id, editor_duzeltmesi).</summary>
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public JsonElement? EvidenceOzeti { get; init; }

    /// <summary>xref: kaynak birimin metninden kaynak araligina denk gelen dilim ve kod noktasi baglami (±40). Metin yoksa, aralik metin disindaysa ya da kanittaki src_hash birimin ozetiyle uyusmuyorsa uc alan da null.</summary>
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public VurguluDizi? VurguluDizi { get; init; }

    /// <summary>xref: aday sinifi (<see cref="ReviewItemDto.Sinif"/> ile ayni kural).</summary>
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public string? Sinif { get; init; }

    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public string? Field { get; init; }

    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public string? QacValue { get; init; }

    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public string? NewValue { get; init; }

    /// <summary>quran_word_fix: duzeltmenin gerekcesi.</summary>
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public string? Reason { get; init; }

    /// <summary>quran_word_fix: duzeltmeyi yazan editor.</summary>
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public string? Editor { get; init; }

    // lemma, lemma_gloss
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public int? LemmaId { get; init; }

    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public string? Lang { get; init; }

    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public string? Text { get; init; }

    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public string? AnlamKisa { get; init; }

    /// <summary>lemma: kok kimligi (kokusuz lemmada ve lemma_gloss'ta yok).</summary>
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public int? RootId { get; init; }

    /// <summary>lemma: kelime duzeyinde gecis sayisi.</summary>
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public int? Occurrences { get; init; }

    /// <summary>lemma: yalnizca etimolojik lemma (lemma.etymological_only).</summary>
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public bool? EtymologicalOnly { get; init; }

    /// <summary>lemma: lemma.origin ('qac' ...); lemma_gloss: lemma_gloss.origin ('kaynak:quranwbw-tr', 'editor', 'yz:{model}').</summary>
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public string? Origin { get; init; }

    /// <summary>lemma_gloss: en cok 3 maddelik Kur'an anlamlari (jsonb dizisi).</summary>
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public JsonElement? KuranAnlamlari { get; init; }

    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public string? TurkceEsKelime { get; init; }

    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public bool? YalnizcaEtimolojik { get; init; }

    /// <summary>lemma_gloss: icerik surumu ('1', her duzenlemede +1).</summary>
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public string? Version { get; init; }

    /// <summary>Durum sutunlu hedeflerde status (aday, onayli, red); birimde unit.status (etkin, kullanim_disi).</summary>
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public string? Status { get; init; }

    // lemma (yalniz lang = 'tr'; K-51 madde 9)

    /// <summary>Turkce lemma: onay yolu (editor, otomatik); aday ya da redde yok.</summary>
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public string? OnayYolu { get; init; }

    /// <summary>Turkce lemma: otomatik onay kaniti ozeti (kaynak sayisi, QAC eslesme turu, karar, neden); kanit yoksa yazilmaz.</summary>
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public LemmaKanitSummary? KanitOzeti { get; init; }

    /// <summary>Turkce lemma: eslenen kokun harfleri (root.letters).</summary>
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public string? RootLetters { get; init; }

    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public int? ArLemmaId { get; init; }

    /// <summary>Turkce lemma: Arapca karsiligin metni (ar_lemma.text).</summary>
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public string? ArLemmaText { get; init; }

    /// <summary>Turkce lemma: kulliyat sikligi (lemma.freq).</summary>
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public int? Freq { get; init; }

    /// <summary>Turkce lemma: tr_root_index uzerinden en cok 3 ornek (birim metninden +/-40 kod noktasi); tablo bossa bos liste.</summary>
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public IReadOnlyList<TrKwicItem>? Kwic { get; init; }
}

/// <summary>Vurgulu dizi: <c>dizi</c> vurgulanan dilim, <c>sol</c> ve <c>sag</c> yanlarindaki en cok 40 kod noktasi. Uc alan birlikte dolu ya da birlikte null.</summary>
public sealed record VurguluDizi(string? Sol, string? Dizi, string? Sag);

public sealed record ReviewQueueCount(string HedefTablo, string Alan, int Acik);

/// <summary>Acik baglanti adaylarinin sinif sayilari (A18.4); sinif etiketi <c>tutarsiz</c>, <c>toplu</c>, <c>gri</c>, <c>diger</c>.</summary>
public sealed record ReviewClassCount(string Sinif, int Acik);

/// <summary>
/// Kuyruk sayilari. <c>toplam_acik</c> yalniz <c>acik</c> kayitlari sayar; uzmana gonderilenler (<c>uzmanda</c>) ayri sayilir.
/// <c>baglanti_siniflari</c> acik xref adaylarinin dort sinifini da (sifir olsa da) sabit sirayla verir.
/// </summary>
public sealed record ReviewStatsResponse(
    IReadOnlyList<ReviewQueueCount> Kuyruklar,
    int ToplamAcik,
    IReadOnlyList<ReviewClassCount> BaglantiSiniflari,
    int ToplamUzmanda);

/// <summary>
/// Editorun duzenledigi deger: birim metni onayinda <c>metin</c>, lemma_gloss onayinda <c>anlam_kisa</c> (K-50 madde 6),
/// Turkce lemma kok eslemesi onayinda <c>root_id</c>, <c>ar_lemma_id</c> ve <c>etymological_only</c> (K-51 madde 9);
/// hedefe gore yalniz o hedefin alanlari verilir (baska alan 400), ote hedeflerde duzenlenen deger 422 <c>inceleme-desteklenmiyor</c> alir.
/// Kok eslemesinde <c>root_id</c> ve <c>etymological_only</c> zorunludur; <c>ar_lemma_id</c> yoksa ya da null ise Arapca karsilik yoktur.
/// Baglanti (xref) onayinda <c>dst_anchor</c>, <c>dst_span</c> (<c>[bas, son)</c> iki sayi) ve <c>type</c> (yalniz atif, iktibas, ima kendi aralarinda) verilir,
/// en az biri; <c>dst_anchor</c> verilirse hedef araligi o capayla birlikte yeniden belirlenir (<c>dst_span</c> yoksa birimin tamami),
/// yalniz <c>dst_span</c> verilirse mevcut hedefin araligi duzeltilir. <c>quran_word_fix</c> onayinda yalniz <c>new_value</c> verilir.
/// </summary>
public sealed record DecisionEdit(
    string? Metin = null,
    string? AnlamKisa = null,
    int? RootId = null,
    int? ArLemmaId = null,
    bool? EtymologicalOnly = null,
    string? DstAnchor = null,
    int[]? DstSpan = null,
    string? Type = null,
    string? NewValue = null);

/// <summary>Uzmana gonder, kalip ve ima gibi gerekce isteyen eylem govdesi.</summary>
public sealed record ReviewReasonBody(string? Gerekce);

/// <summary>Uzmana gonder sonucu: kaydin yeni durumu (<c>uzmanda</c>), korunan eylemi ve yeni <c>xmin</c>.</summary>
public sealed record ReviewHandoffResult(long Id, string Durum, string Eylem, uint Xmin);

/// <summary>"Ima olarak isaretle" sonucu: yeni <c>ima</c> satirinin kimligi, denetim kaydinin <c>review</c> kimligi, turu ve durumu.</summary>
public sealed record ImaMarkResult(Guid Id, long ReviewId, string Type, string Status);

/// <summary>"Kalip listesine ekle" sonucu: reddedilen adayin <c>review</c> sonucu, saklanan normalize anahtar ve kapali denetim kaydinin kimligi.</summary>
public sealed record PatternAddResult(long Id, string Durum, string Eylem, uint Xmin, string Anahtar, long DenetimReviewId);

/// <summary>Editorun kelime duzeltmesi adayi: <c>anchor</c> kelime capasi (<c>q:s:a:k</c>), <c>field</c> <c>root_id|lemma_id|pos|features</c>.</summary>
public sealed record WordFixRequest(string? Anchor, string? Field, string? NewValue, string? Reason);

/// <summary>Acilan kelime duzeltmesi: <c>id</c> duzeltme kimligi, <c>review_id</c> inceleme kaydi, <c>durum</c> her zaman <c>aday</c>.</summary>
public sealed record WordFixResponse(Guid Id, long ReviewId, string Durum);

/// <summary>Tekil karar govdesi. karar: onaylandi ya da reddedildi.</summary>
public sealed record DecisionBody(string? Karar, string? Gerekce, DecisionEdit? Duzenlenen = null);

public sealed record BulkDecisionItem(long Id, uint Xmin, string? Karar, string? Gerekce, DecisionEdit? Duzenlenen = null);

public sealed record BulkDecisionBody(IReadOnlyList<BulkDecisionItem>? Kararlar);

public sealed record ReviewDecisionResult(long Id, string Durum, string Eylem, bool IkinciOnayBekliyor, string? HedefDurumu, uint Xmin);

public sealed record BulkDecisionOutcome(long Id, string Durum, string Eylem, uint Xmin);

public sealed record BulkDecisionResult(IReadOnlyList<BulkDecisionOutcome> Sonuclar);
