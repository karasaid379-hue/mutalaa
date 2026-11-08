using Mutalaa.Domain.Anchors;

namespace Mutalaa.Domain.Content;

/// <summary>icerik.quran_marker satiri (Editoryal veritabani 5, K-43): cuz, hizb, rub ve secde isaretleri.</summary>
public sealed class QuranMarker
{
    /// <summary>cuz, hizb, rub, secde.</summary>
    public required string Kind { get; set; }

    /// <summary>Tur icinde 1'den kesintisiz sira.</summary>
    public short No { get; set; }

    /// <summary>Baslangic ayeti: 'q:2:142'. Secde icin secde ayeti.</summary>
    public required AnchorRef Anchor { get; set; }

    /// <summary>recommended, obligatory (Tanzil etiketi); yalniz secde satirinda dolu.</summary>
    public string? SecdeTuru { get; set; }

    public required string SourceId { get; set; }

    public required string DataVersion { get; set; }
}
