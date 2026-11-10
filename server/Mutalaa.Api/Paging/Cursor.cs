using System.Buffers.Text;
using System.Text;
using Mutalaa.Api.Validation;

namespace Mutalaa.Api.Paging;

/// <summary>
/// Opak sayfalama imleci: UTF-8 yukun base64url (dolgusuz) gosterimi. Istemci icerigini yorumlamaz.
/// Cozme kati ve kanoniktir: base64url olmayan, gecersiz UTF-8 ya da NUL iceren ya da yeniden kodlandiginda ayni cikmayan dizgi gecersizdir.
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

        // NUL PostgreSQL parametresine giremez; imlec yuku sorguya girer.
        return WritableText.IsWritable(payload) && string.Equals(Encode(payload), cursor, StringComparison.Ordinal);
    }
}
