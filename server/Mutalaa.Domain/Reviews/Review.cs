using Mutalaa.Domain.Links;

namespace Mutalaa.Domain.Reviews;

/// <summary>icerik.review satiri (Editoryal veritabani 8; yz_kaydi K-37).</summary>
public sealed class Review
{
    /// <summary>Kimlik sutunu (GENERATED ALWAYS AS IDENTITY).</summary>
    public long Id { get; set; }

    public required string HedefTablo { get; set; }

    /// <summary>Capa, lemma kimligi, kaynak kimligi ... (capa turu degil).</summary>
    public required string HedefAnahtar { get; set; }

    public Guid? XrefId { get; set; }

    public required string Alan { get; set; }

    public required string Eylem { get; set; }

    /// <summary>jsonb.</summary>
    public string? Onceki { get; set; }

    /// <summary>jsonb.</summary>
    public string? Onerilen { get; set; }

    public ReviewStatus Durum { get; set; } = ReviewStatus.Acik;

    /// <summary>Veritabaninda varsayilan yok; CLR varsayilanina sessizce dusmesin diye zorunlu.</summary>
    public required XrefOrigin Koken { get; set; }

    public string? YzModeli { get; set; }

    /// <summary>jsonb (K-37): prompt_id, prompt_sha256, input_sha256; yz_modeli ile birlikte dolu ya da bos.</summary>
    public string? YzKaydi { get; set; }

    public float? Guven { get; set; }

    public required string Oneren { get; set; }

    public string? Inceleyen { get; set; }

    public string? IkinciInceleyen { get; set; }

    public int? SureMs { get; set; }

    public string? Gerekce { get; set; }

    /// <summary>UTC; veritabani now() yazar.</summary>
    public DateTime CreatedAt { get; set; }

    /// <summary>UTC.</summary>
    public DateTime? IncelendiAt { get; set; }
}
