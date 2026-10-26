using Mutalaa.Domain.Anchors;

namespace Mutalaa.Domain.Content;

/// <summary>icerik.quran_word satiri (Editoryal veritabani 5). Metin Tanzil'den aynen gelir; kok, lemma ve pos QAC'den.</summary>
public sealed class QuranWord
{
    /// <summary>Kelime capasi (birincil anahtar): 'q:2:255:3'.</summary>
    public required AnchorRef Anchor { get; set; }

    public short Surah { get; set; }

    public short Ayah { get; set; }

    public short Word { get; set; }

    /// <summary>Kuresel ayet sirasi 1..6236.</summary>
    public short AyahIndex { get; set; }

    /// <summary>Kaynaktaki baytlarla; degistirilmez.</summary>
    public required string TextUthmani { get; set; }

    public required string Norm { get; set; }

    /// <summary>Ayet kanonik metninde kod noktasi.</summary>
    public int CharStart { get; set; }

    public int CharEnd { get; set; }

    public int? RootId { get; set; }

    public int? LemmaId { get; set; }

    public string? Pos { get; set; }

    /// <summary>jsonb.</summary>
    public string? Features { get; set; }

    public required string SourceId { get; set; }

    public string? MorphSource { get; set; }

    public required string DataVersion { get; set; }
}
