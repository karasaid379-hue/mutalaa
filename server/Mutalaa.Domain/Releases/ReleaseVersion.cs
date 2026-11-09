using System.Globalization;

namespace Mutalaa.Domain.Releases;

/// <summary>
/// Yayin surumu, CalVer YYYY.M.N (packages/content-schema/manifest.schema.json deseniyle ayni):
/// yil 4 hane, ay 1-12 ve basinda sifir yok, N 0 ya da basinda sifir olmayan sayi. Bes derleme turu tek sayac kullanir.
/// </summary>
public readonly record struct ReleaseVersion(int Year, int Month, int Number) : IComparable<ReleaseVersion>
{
    /// <summary>Surum dizgisini ayristirir; desene uymayan her girdi (null, bos, baslarinda sifir, ay 13, ASCII disi rakam, tasma) false verir.</summary>
    public static bool TryParse(string? text, out ReleaseVersion version)
    {
        version = default;
        if (text is null)
        {
            return false;
        }

        string[] parts = text.Split('.');
        if (parts.Length != 3)
        {
            return false;
        }

        string yearText = parts[0];
        string monthText = parts[1];
        string numberText = parts[2];

        if (yearText.Length != 4 || !AllAsciiDigits(yearText))
        {
            return false;
        }

        if (monthText.Length is < 1 or > 2 || !AllAsciiDigits(monthText) || monthText[0] == '0')
        {
            return false;
        }

        if (numberText.Length == 0 || !AllAsciiDigits(numberText) || (numberText.Length > 1 && numberText[0] == '0'))
        {
            return false;
        }

        int year = int.Parse(yearText, NumberStyles.None, CultureInfo.InvariantCulture);
        int month = int.Parse(monthText, NumberStyles.None, CultureInfo.InvariantCulture);
        if (month > 12)
        {
            return false;
        }

        if (!int.TryParse(numberText, NumberStyles.None, CultureInfo.InvariantCulture, out int number))
        {
            return false;
        }

        version = new ReleaseVersion(year, month, number);
        return true;
    }

    /// <summary>
    /// Ayin siradaki surumu: today'in yili ve ayi icin, basarisiz olmayan yayinlarin surumleri arasindaki en buyuk N'nin bir fazlasi;
    /// yoksa 0. Ayristirilamayan dizgiler yok sayilir (desene uymayan surum yeni numarayla cakisamaz).
    /// </summary>
    /// <exception cref="InvalidOperationException">N, int.MaxValue ise.</exception>
    public static ReleaseVersion Next(DateOnly today, IEnumerable<string> existingNonFailedVersions)
    {
        ArgumentNullException.ThrowIfNull(existingNonFailedVersions);

        int max = -1;
        foreach (string text in existingNonFailedVersions)
        {
            if (TryParse(text, out ReleaseVersion v) && v.Year == today.Year && v.Month == today.Month && v.Number > max)
            {
                max = v.Number;
            }
        }

        if (max == int.MaxValue)
        {
            throw new InvalidOperationException("Surum numarasi tasti.");
        }

        return new ReleaseVersion(today.Year, today.Month, max + 1);
    }

    public int CompareTo(ReleaseVersion other)
    {
        int c = Year.CompareTo(other.Year);
        if (c != 0)
        {
            return c;
        }

        c = Month.CompareTo(other.Month);
        return c != 0 ? c : Number.CompareTo(other.Number);
    }

    /// <summary>YYYY.M.N (yil 4 hane, ay ve N sifirsiz); kulturden bagimsiz.</summary>
    public override string ToString() =>
        string.Create(CultureInfo.InvariantCulture, $"{Year:D4}.{Month}.{Number}");

    private static bool AllAsciiDigits(string text)
    {
        foreach (char c in text)
        {
            if (c is < '0' or > '9')
            {
                return false;
            }
        }

        return true;
    }
}
