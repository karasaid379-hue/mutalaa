using Mutalaa.Domain.Anchors;

namespace Mutalaa.Domain.Content;

/// <summary>
/// icerik.hadith_number_map satiri (Editoryal veritabani 11; hadis_numara_esleme).
/// System ozelligi sinif icinde System ad alanini gizler; sinifa kod eklenirse global::System kullanilir.
/// </summary>
public sealed class HadithNumberMap
{
    public required string Collection { get; set; }

    /// <summary>Numaralama sistemi: 'kaynak-baski', 'sunnah-com', 'tecrid'.</summary>
    public required string System { get; set; }

    public required string Number { get; set; }

    public required AnchorRef Anchor { get; set; }
}
