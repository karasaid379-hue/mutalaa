namespace Mutalaa.Domain.Content;

/// <summary>icerik.tr_form satiri (Editoryal veritabani 6): Turkce bicimden lemmaya.</summary>
public sealed class TrForm
{
    public required string KeyWide { get; set; }

    public required string KeyNarrow { get; set; }

    public int TrLemmaId { get; set; }

    public int Freq { get; set; }
}
