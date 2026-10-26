using Mutalaa.Domain.Anchors;

namespace Mutalaa.Domain.Content;

/// <summary>icerik.tr_root_index satiri (Editoryal veritabani 6): onayli koke baglanan Turkce token.</summary>
public sealed class TrRootIndex
{
    public required AnchorRef Anchor { get; set; }

    /// <summary>Kanonik metinde kod noktasi.</summary>
    public int SpanStart { get; set; }

    public int SpanEnd { get; set; }

    public int RootId { get; set; }

    public int TrLemmaId { get; set; }

    public bool EtymologicalOnly { get; set; }

    public required string DataVersion { get; set; }
}
