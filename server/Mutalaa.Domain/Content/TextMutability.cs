namespace Mutalaa.Domain.Content;

/// <summary>
/// Metin degistirilebilirligi (K-26, Sunucu kurali): ayet birimlerinin ve kuran_metni kaynaginin metni degismez
/// (Tanzil bayt bayt saklanir); duzeltme ucu 422 <c>degistirilemez-metin</c> doner.
/// </summary>
public static class TextMutability
{
    /// <summary>Birim turu ayet ya da kaynak turu kuran_metni ise metin degistirilemez.</summary>
    public static bool IsImmutable(UnitKind kind, SourceKind sourceKind) =>
        kind == UnitKind.Ayet || sourceKind == SourceKind.KuranMetni;
}
