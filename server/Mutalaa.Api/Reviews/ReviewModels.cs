using System.Text.Json;
using System.Text.Json.Serialization;

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

    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public string? Field { get; init; }

    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public string? QacValue { get; init; }

    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public string? NewValue { get; init; }

    // lemma, lemma_gloss
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public int? LemmaId { get; init; }

    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public string? Lang { get; init; }

    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public string? Text { get; init; }

    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public string? AnlamKisa { get; init; }

    /// <summary>Durum sutunlu hedeflerde status (aday, onayli, red); birimde unit.status (etkin, kullanim_disi).</summary>
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public string? Status { get; init; }
}

public sealed record ReviewQueueCount(string HedefTablo, string Alan, int Acik);

public sealed record ReviewStatsResponse(IReadOnlyList<ReviewQueueCount> Kuyruklar, int ToplamAcik);

/// <summary>Editorun duzenledigi deger: yalniz birim metni onayinda.</summary>
public sealed record DecisionEdit(string? Metin);

/// <summary>Tekil karar govdesi. karar: onaylandi ya da reddedildi.</summary>
public sealed record DecisionBody(string? Karar, DecisionEdit? Duzenlenen, string? Gerekce);

public sealed record BulkDecisionItem(long Id, uint Xmin, string? Karar, DecisionEdit? Duzenlenen, string? Gerekce);

public sealed record BulkDecisionBody(IReadOnlyList<BulkDecisionItem>? Kararlar);

public sealed record ReviewDecisionResult(long Id, string Durum, string Eylem, bool IkinciOnayBekliyor, string? HedefDurumu, uint Xmin);

public sealed record BulkDecisionOutcome(long Id, string Durum, string Eylem, uint Xmin);

public sealed record BulkDecisionResult(IReadOnlyList<BulkDecisionOutcome> Sonuclar);
