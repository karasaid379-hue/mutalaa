using System.Buffers.Text;
using System.Text;

namespace Mutalaa.Api.Paging;

/// <summary>
/// Opak sayfalama imleci: UTF-8 yukun base64url (dolgusuz) gosterimi. Istemci icerigini yorumlamaz.
/// Cozme kati ve kanoniktir: base64url olmayan, gecersiz UTF-8 iceren ya da yeniden kodlandiginda ayni cikmayan dizgi gecersizdir.
/// </summary>
internal static class Cursor
{
    /// <summary>Kabul edilen en uzun imlec (karakter); kaynak kimligi en cok 64 karakterdir, imlec bunun cok altinda kalir.</summary>
    public const int MaxLength = 512;

    private static readonly UTF8Encoding StrictUtf8 = new(encoderShouldEmitUTF8Identifier: false, throwOnInvalidBytes: true);

    public static string Encode(string payload)
    {
        ArgumentNullException.ThrowIfNull(payload);
        return Base64Url.EncodeToString(StrictUtf8.GetBytes(payload));
    }

    public static bool TryDecode(string? cursor, out string payload)
    {
        payload = string.Empty;
        if (string.IsNullOrEmpty(cursor) || cursor.Length > MaxLength || !Base64Url.IsValid(cursor))
        {
            return false;
        }

        try
        {
            payload = StrictUtf8.GetString(Base64Url.DecodeFromChars(cursor));
        }
        catch (Exception e) when (e is FormatException or ArgumentException)
        {
            return false;
        }

        return string.Equals(Encode(payload), cursor, StringComparison.Ordinal);
    }
}
