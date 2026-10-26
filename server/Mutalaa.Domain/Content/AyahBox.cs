using Mutalaa.Domain.Anchors;

namespace Mutalaa.Domain.Content;

/// <summary>icerik.ayah_box satiri (Editoryal veritabani 9.1): Mod B gorselinde ayet kutusu (gorsel pikseli).</summary>
public sealed class AyahBox
{
    public required string SourceId { get; set; }

    public int Page { get; set; }

    /// <summary>Ayet capasi: 'q:{sure}:{ayet}'.</summary>
    public required AnchorRef Anchor { get; set; }

    public short Seq { get; set; }

    public int X { get; set; }

    public int Y { get; set; }

    public int W { get; set; }

    public int H { get; set; }

    public required string DataVersion { get; set; }
}
