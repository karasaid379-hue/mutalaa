using System.Buffers.Text;
using System.Globalization;
using System.Text;
using System.Text.RegularExpressions;

namespace Mutalaa.Api.Releases;

/// <summary>
/// Yayin listesi imleci: <c>(id azalan)</c> anahtar kumesi sayfalamasinin opak (base64url, dolgusuz) belirteci. Icerik <c>r:{id}</c> olur; istemci
/// yorumlamaz. Kanonik olmayan her bicim (dolgu, bosluk, baska on ek, bastaki sifir, tasma) gecersizdir.
/// </summary>
public static partial class ReleaseCursor
{
    private const string Prefix = "r:";

    [GeneratedRegex("^r:[1-9][0-9]{0,9}$", RegexOptions.CultureInvariant)]
    private static partial Regex Pattern();

    /// <summary>Verilen kimlikten KUCUK kayitlarin sirasi baslar: imlec son gonderilen ogenin kimligidir.</summary>
    public static string Encode(int lastId) =>
        Base64Url.EncodeToString(Encoding.ASCII.GetBytes(string.Create(CultureInfo.InvariantCulture, $"{Prefix}{lastId}")));

    public static bool TryDecode(string? cursor, out int lastId)
    {
        lastId = 0;
        if (string.IsNullOrEmpty(cursor) || cursor.Length > 32)
        {
            return false;
        }

        byte[] bytes;
        try
        {
            bytes = Base64Url.DecodeFromChars(cursor);
        }
        catch (FormatException)
        {
            return false;
        }

        string text = Encoding.ASCII.GetString(bytes);
        if (!Pattern().IsMatch(text) || !int.TryParse(text.AsSpan(Prefix.Length), NumberStyles.None, CultureInfo.InvariantCulture, out int id) || id <= 0)
        {
            return false;
        }

        if (!string.Equals(Encode(id), cursor, StringComparison.Ordinal))
        {
            return false;
        }

        lastId = id;
        return true;
    }
}
