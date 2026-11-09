namespace Mutalaa.Domain.Releases;

/// <summary>release.talep degerleri (BC-04): text + CHECK, PostgreSQL enum degil.</summary>
public static class ReleaseRequests
{
    public const string Yayin = "yayin";
    public const string Terfi = "terfi";
    public const string GeriAlma = "geri_alma";

    public static IReadOnlyList<string> All { get; } = [Yayin, Terfi, GeriAlma];

    /// <summary>Tam (Ordinal) eslesme.</summary>
    public static bool IsValid(string? value) =>
        string.Equals(value, Yayin, StringComparison.Ordinal) ||
        string.Equals(value, Terfi, StringComparison.Ordinal) ||
        string.Equals(value, GeriAlma, StringComparison.Ordinal);
}
