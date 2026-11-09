namespace Mutalaa.Infrastructure.Manifests;

/// <summary>Base64 ve onaltilik yardimcilari. Cozme katidir: bosluk, satir sonu ya da kanonik olmayan dolgu kabul edilmez.</summary>
public static class Base64Strict
{
    public static string Encode(ReadOnlySpan<byte> bytes) => Convert.ToBase64String(bytes);

    /// <summary>Kucuk harfli onaltilik gosterim.</summary>
    public static string ToHex(ReadOnlySpan<byte> bytes) => Convert.ToHexStringLower(bytes);

    /// <summary>Standart base64 (dolgulu) cozer; kanonik olmayan ya da bosluklu metin icin false doner.</summary>
    public static bool TryDecode(string? value, out byte[] bytes)
    {
        bytes = [];
        if (string.IsNullOrEmpty(value))
        {
            return false;
        }

        byte[] buffer = new byte[(value.Length / 4 * 3) + 3];
        if (!Convert.TryFromBase64String(value, buffer, out int written))
        {
            return false;
        }

        byte[] decoded = buffer.AsSpan(0, written).ToArray();
        if (!string.Equals(Convert.ToBase64String(decoded), value, StringComparison.Ordinal))
        {
            return false;
        }

        bytes = decoded;
        return true;
    }
}
