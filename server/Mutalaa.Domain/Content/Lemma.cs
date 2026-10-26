using Mutalaa.Domain.Links;

namespace Mutalaa.Domain.Content;

/// <summary>icerik.lemma satiri (Editoryal veritabani 5); Arapca ve Turkce lemmalar. Kimlik kalicidir; veritabani uretmez.</summary>
public sealed class Lemma
{
    public int Id { get; set; }

    /// <summary>ar ya da tr.</summary>
    public required string Lang { get; set; }

    public required string Text { get; set; }

    public required string TextClean { get; set; }

    public int? RootId { get; set; }

    public int Occurrences { get; set; }

    public string? QacRef { get; set; }

    /// <summary>Yalniz tr satirinda: Arapca karsiligi.</summary>
    public int? ArLemmaId { get; set; }

    public bool EtymologicalOnly { get; set; }

    public string? Origin { get; set; }

    public XrefStatus Status { get; set; } = XrefStatus.Aday;

    public int? Freq { get; set; }

    public required string SourceId { get; set; }

    public required string DataVersion { get; set; }
}
