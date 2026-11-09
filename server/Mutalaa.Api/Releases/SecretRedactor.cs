using System.Text.RegularExpressions;
using Npgsql;

namespace Mutalaa.Api.Releases;

/// <summary>
/// Istemciye giden iletilerden bilinen sirlari siler (Yayinlayicinin <c>Redact</c> mantigi): baglanti dizesi ve parolasi/kullanici adi, ayarlarda adinda
/// sir geçen degerler ve <c>anahtar=deger</c> kaliplari. Kapi plani iletileri zaten yalniz capa, ozet ve slug tasir; bu ikinci savunma hattidir.
/// </summary>
public sealed partial class SecretRedactor(IConfiguration configuration)
{
    private const string Mask = "***";
    private const int MinSecretLength = 4;

    private static readonly string[] SecretKeyParts = ["password", "secret", "accesskey", "privatekey", "seed", "token", "apikey"];

    [GeneratedRegex(
        @"(?<key>password|pwd|secret[a-z_]*|access[_ ]?key|private[_ ]?key|token|api[_-]?key)\s*[=:]\s*(?<value>[^;\s,""']+)",
        RegexOptions.IgnoreCase | RegexOptions.CultureInvariant)]
    private static partial Regex KeyValuePattern();

    [GeneratedRegex(@"(?<scheme>[a-z][a-z0-9+.-]*://)[^/\s:@]+:[^/\s@]+@", RegexOptions.IgnoreCase | RegexOptions.CultureInvariant)]
    private static partial Regex UrlCredentialsPattern();

    public string Redact(string text)
    {
        ArgumentNullException.ThrowIfNull(text);

        string result = text;
        foreach (string secret in Secrets())
        {
            result = result.Replace(secret, Mask, StringComparison.Ordinal);
        }

        result = UrlCredentialsPattern().Replace(result, "${scheme}" + Mask + "@");
        return KeyValuePattern().Replace(result, "${key}=" + Mask);
    }

    private List<string> Secrets()
    {
        List<string> secrets = [];

        string? connection = configuration.GetConnectionString(Mutalaa.Infrastructure.DependencyInjection.ConnectionName);
        if (!string.IsNullOrWhiteSpace(connection))
        {
            secrets.Add(connection);
            try
            {
                NpgsqlConnectionStringBuilder builder = new(connection);
                Add(secrets, builder.Password);
                Add(secrets, builder.Username);
            }
            catch (ArgumentException)
            {
                // Bicimi bozuk dize: yalniz butunuyle silinir.
            }
        }

        foreach (KeyValuePair<string, string?> pair in configuration.AsEnumerable())
        {
            if (SecretKeyParts.Any(part => pair.Key.Contains(part, StringComparison.OrdinalIgnoreCase)))
            {
                Add(secrets, pair.Value);
            }
        }

        // Uzun sir once silinir: kisa olan uzunun icinde kalip onu bozmasin.
        secrets.Sort((a, b) => b.Length.CompareTo(a.Length));
        return secrets;
    }

    private static void Add(List<string> secrets, string? value)
    {
        if (!string.IsNullOrEmpty(value) && value.Length >= MinSecretLength)
        {
            secrets.Add(value);
        }
    }
}
