using Mutalaa.Domain.Anchors;

namespace Mutalaa.Domain.Content;

/// <summary>icerik.hadith_location satiri (Editoryal veritabani 11; hadis_konum: kitap, bab, hadis).</summary>
public sealed class HadithLocation
{
    public required AnchorRef Anchor { get; set; }

    public int? BookNo { get; set; }

    public string? BookName { get; set; }

    public int? BabNo { get; set; }

    public string? BabName { get; set; }

    public int Ord { get; set; }
}
