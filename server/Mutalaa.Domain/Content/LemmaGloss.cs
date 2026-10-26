using Mutalaa.Domain.Links;

namespace Mutalaa.Domain.Content;

/// <summary>icerik.lemma_gloss satiri (Editoryal veritabani 5; K-19 Turkce anlamlari).</summary>
public sealed class LemmaGloss
{
    /// <summary>Birincil anahtar ve lemma.id yabanci anahtari.</summary>
    public int LemmaId { get; set; }

    public required string AnlamKisa { get; set; }

    /// <summary>jsonb.</summary>
    public string KuranAnlamlari { get; set; } = "[]";

    public string? TurkceEsKelime { get; set; }

    public bool YalnizcaEtimolojik { get; set; }

    public string? EditorNotu { get; set; }

    public XrefStatus Status { get; set; } = XrefStatus.Aday;

    public required string Origin { get; set; }

    public required string Version { get; set; }

    public required string ContentHash { get; set; }

    /// <summary>UTC; veritabani now() yazar.</summary>
    public DateTime UpdatedAt { get; set; }
}
