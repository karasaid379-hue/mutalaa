using Mutalaa.Domain.Links;

namespace Mutalaa.Domain.Content;

/// <summary>icerik.surah_alias satiri (Editoryal veritabani 6): sure adi alternatifleri.</summary>
public sealed class SurahAlias
{
    public short SurahNo { get; set; }

    /// <summary>Goruldugu gibi.</summary>
    public required string Alias { get; set; }

    /// <summary>Genis anahtar.</summary>
    public required string AliasKey { get; set; }

    /// <summary>kanonik, yazim, arapca, diger_ad.</summary>
    public required string Kind { get; set; }

    public bool Risky { get; set; }

    public XrefStatus Status { get; set; } = XrefStatus.Aday;
}
