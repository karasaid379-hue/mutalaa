namespace Mutalaa.Domain.Content;

/// <summary>icerik.lemma_dalga satiri (Editoryal veritabani 5; K-50 madde 7). Hat yazar, API okur.</summary>
public sealed class LemmaDalga
{
    /// <summary>Birincil anahtar ve lemma.id yabanci anahtari.</summary>
    public int LemmaId { get; set; }

    /// <summary>0..4 (CHECK).</summary>
    public short Dalga { get; set; }

    /// <summary>Dalga icindeki sira.</summary>
    public int Sira { get; set; }

    public required string DataVersion { get; set; }
}
