using Mutalaa.Domain.Anchors;

namespace Mutalaa.Domain.Content;

/// <summary>icerik.page_map satiri (Editoryal veritabani 9.1): duzen ya da baski sayfasi/satiri.</summary>
public sealed class PageMap
{
    /// <summary>Kimlik sutunu (GENERATED ALWAYS AS IDENTITY).</summary>
    public long Id { get; set; }

    public required string SourceId { get; set; }

    public short? Volume { get; set; }

    public int Page { get; set; }

    /// <summary>Yalniz Mod A.</summary>
    public short? Line { get; set; }

    /// <summary>ayet, sure_adi, besmele.</summary>
    public string? LineType { get; set; }

    public bool Centered { get; set; }

    public required AnchorRef StartAnchor { get; set; }

    public int? StartOffset { get; set; }

    public required AnchorRef EndAnchor { get; set; }

    public int? EndOffset { get; set; }

    /// <summary>jsonb.</summary>
    public string? Glyphs { get; set; }

    public required string DataVersion { get; set; }
}
