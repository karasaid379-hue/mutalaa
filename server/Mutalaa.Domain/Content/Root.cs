namespace Mutalaa.Domain.Content;

/// <summary>icerik.root satiri (Editoryal veritabani 5). Kimlik kalicidir; veritabani uretmez.</summary>
public sealed class Root
{
    public int Id { get; set; }

    public required string Letters { get; set; }

    public string? LettersBw { get; set; }

    public int Occurrences { get; set; }

    public int AyahCount { get; set; }

    public float? IdfQ { get; set; }

    public string? KokAnlami { get; set; }

    public required string SourceId { get; set; }

    public required string DataVersion { get; set; }
}
