using Mutalaa.Domain.Anchors;

namespace Mutalaa.Domain.Content;

/// <summary>
/// icerik.unit satiri (Editoryal veritabani 4): ayet, meal, tefsir, Risale, hadis ve kitap paragraflari.
/// tsv_tr ve tsv_ar uretilen sutunlardir, burada yer almaz. Baslangic degerleri veritabani varsayilaniyla aynidir.
/// </summary>
public sealed class Unit
{
    /// <summary>Kimlik sutunu (GENERATED ALWAYS AS IDENTITY).</summary>
    public long Id { get; set; }

    /// <summary>Birim capasi; '@' araligi tasimaz.</summary>
    public required AnchorRef Anchor { get; set; }

    /// <summary>Veritabaninda varsayilan yok; CLR varsayilanina sessizce dusmesin diye zorunlu.</summary>
    public required UnitKind Kind { get; set; }

    /// <summary>govde, baslik, hasiye, dipnot, siir.</summary>
    public string Role { get; set; } = "govde";

    public required string SourceId { get; set; }

    /// <summary>Icindekiler yolu (capa degil): 'rn:sozler:soz-10:hakikat-3'.</summary>
    public string? ParentPath { get; set; }

    public long Ord { get; set; }

    /// <summary>
    /// Kuresel ayet sirasi araligi [ilk, son+1), sira 1..6236 (AnchorSpan anlami 2: kod noktasi degil); ayete bagli degilse null.
    /// </summary>
    public AnchorSpan? AyahRange { get; set; }

    /// <summary>Kanonik metin (K-26).</summary>
    public required string Metin { get; set; }

    /// <summary>jsonb.</summary>
    public string Marks { get; set; } = "[]";

    /// <summary>Cumle sinirlari: birim metninde kod noktasi araliklari [baslangic, bitis) (AnchorSpan anlami 1).</summary>
    public AnchorSpan[]? Sentences { get; set; }

    /// <summary>jsonb.</summary>
    public string Attrs { get; set; } = "{}";

    public required string ContentHash { get; set; }

    public int Rev { get; set; } = 1;

    public TextStatus MetinDurumu { get; set; } = TextStatus.Taslak;

    public UnitStatus Status { get; set; } = UnitStatus.Etkin;

    /// <summary>jsonb; kullanim disi birimde dolu.</summary>
    public string? Successors { get; set; }

    public string? TrNarrow { get; set; }

    public string? TrWide { get; set; }

    public string? TrStem { get; set; }

    public string? ArNorm { get; set; }

    public required string DataVersion { get; set; }

    /// <summary>jsonb.</summary>
    public string Provenance { get; set; } = "{}";

    /// <summary>Yukleyen hat calistirmasi (pipeline_run.run_id).</summary>
    public Guid? RunId { get; set; }

    /// <summary>UTC; veritabani now() yazar.</summary>
    public DateTime CreatedAt { get; set; }

    /// <summary>UTC; veritabani now() yazar.</summary>
    public DateTime UpdatedAt { get; set; }
}
