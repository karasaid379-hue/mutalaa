namespace Mutalaa.Domain.Anchors;

/// <summary>
/// Gecersiz capa dizgisinde <see cref="AnchorRef.Parse(string)"/> tarafindan firlatilir.
/// </summary>
public sealed class AnchorException : Exception
{
    public AnchorException(AnchorErrorCode code)
        : base("Gecersiz capa: " + NameOf(code))
    {
        Code = code;
    }

    public AnchorException()
        : this(AnchorErrorCode.Bicim)
    {
    }

    public AnchorException(string message)
        : base(message)
    {
        Code = AnchorErrorCode.Bicim;
    }

    public AnchorException(string message, Exception innerException)
        : base(message, innerException)
    {
        Code = AnchorErrorCode.Bicim;
    }

    public AnchorErrorCode Code { get; }

    /// <summary>Belgedeki hata kodu: BICIM, SURE_ARALIGI, AYET_ARALIGI, TERS_ARALIK, KANONIK_DEGIL, UZUNLUK.</summary>
    public string CodeName => NameOf(Code);

    public static string NameOf(AnchorErrorCode code) => code switch
    {
        AnchorErrorCode.Bicim => "BICIM",
        AnchorErrorCode.SureAraligi => "SURE_ARALIGI",
        AnchorErrorCode.AyetAraligi => "AYET_ARALIGI",
        AnchorErrorCode.TersAralik => "TERS_ARALIK",
        AnchorErrorCode.KanonikDegil => "KANONIK_DEGIL",
        AnchorErrorCode.Uzunluk => "UZUNLUK",
        _ => throw new ArgumentOutOfRangeException(nameof(code)),
    };
}
