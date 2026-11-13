using System.Reflection;
using System.Text.Json;
using System.Text.RegularExpressions;

namespace Mutalaa.Infrastructure.Packs;

/// <summary>
/// Risale kitabi (shared/data/risale-kitaplar.json satiri). Paket kimligi <c>risale-{slug}</c>, capa oneki <c>rn:{slug}</c> (K-51 madde 4).
/// Language: <c>tr</c>, <c>ota</c> (Osmanlica) ya da <c>ar</c>; Direction: <c>ltr</c> ya da <c>rtl</c> (Osmanlica ve Arapca kitaplarda rtl).
/// Volume: RNK dosyasinin kalici cilt numarasi (page_map.volume, smallint; ayni dosyadan bolunen kitaplar ayni cildi paylasir); null yalniz
/// katalogdaki sentetik fikstur kitabinda (sayfa eslemesi yok).
/// </summary>
public sealed record RisaleBook(string Slug, string Title, string Language, string Direction, int? Volume)
{
    public string PackId => RisaleBookTable.PackIdPrefix + Slug;

    public string AnchorPrefix => RisaleBookTable.AnchorPrefix + Slug;
}

/// <summary>
/// Risale kitap tablosu: <c>shared/data/risale-kitaplar.json</c> dosyasi Infrastructure'a gomulu kaynak olarak girer (csproj, LogicalName
/// <c>risale-kitaplar.json</c>) ve katalog buradan URETILIR; slug, dil, yon ve cilt baska yerde elle tekrarlanmaz. Dosya ile katalogun esitligi
/// RisalePackTests'tedir. Kurallar (Capa semasi 5, K-51 madde 4 ve 12): slug kucuk harf ASCII, rakam ve tire, en cok 64 karakter, benzersiz,
/// <c>dizin</c> olamaz (risale-dizin paketiyle cakisir) ve <c>test-</c> ile baslayamaz (fikstur kitaplari katalogda ayridir).
/// </summary>
public static class RisaleBookTable
{
    public const string ResourceName = "risale-kitaplar.json";

    public const string PackIdPrefix = "risale-";

    public const string AnchorPrefix = "rn:";

    /// <summary>Capa semasi 5: slug en cok 64 karakter.</summary>
    public const int MaxSlugLength = 64;

    /// <summary>Kitap slug'i olamayan ad: <c>risale-dizin</c> paketiyle cakisir.</summary>
    public const string ReservedSlug = "dizin";

    private static readonly Regex SlugShape = new(@"^[a-z0-9]+(-[a-z0-9]+)*\z", RegexOptions.CultureInvariant);

    private static readonly string[] Languages = ["tr", "ota", "ar"];

    private static readonly string[] Directions = ["ltr", "rtl"];

    /// <summary>Gomulu dosyadan okunan 87 kitap (dosya sirasi).</summary>
    public static IReadOnlyList<RisaleBook> Default { get; } = LoadEmbedded();

    /// <summary>Gomulu kaynagin baytlari (senkron testi dosyayla bayt bayt karsilastirir).</summary>
    public static byte[] ReadEmbeddedBytes()
    {
        Assembly assembly = typeof(RisaleBookTable).Assembly;
        using Stream stream = assembly.GetManifestResourceStream(ResourceName)
            ?? throw new InvalidDataException($"Gomulu kaynak yok: {ResourceName}");
        using MemoryStream copy = new();
        stream.CopyTo(copy);
        return copy.ToArray();
    }

    /// <summary>JSON baytlarindan okur ve dogrular; gecersiz girdide <see cref="InvalidDataException"/>.</summary>
    public static IReadOnlyList<RisaleBook> Parse(ReadOnlySpan<byte> json)
    {
        try
        {
            using JsonDocument document = JsonDocument.Parse(json.ToArray());
            JsonElement books = document.RootElement.GetProperty("kitaplar");
            List<RisaleBook> result = [];
            HashSet<string> seen = new(StringComparer.Ordinal);
            foreach (JsonElement element in books.EnumerateArray())
            {
                RisaleBook book = ParseBook(element);
                if (!seen.Add(book.Slug))
                {
                    throw new InvalidDataException($"Yinelenen Risale kitap slug'i: {book.Slug}");
                }

                result.Add(book);
            }

            return result.Count > 0 ? result : throw new InvalidDataException("Risale kitap listesi bos.");
        }
        catch (Exception ex) when (ex is JsonException or KeyNotFoundException or InvalidOperationException or FormatException)
        {
            throw new InvalidDataException($"{ResourceName} gecersiz: {ex.Message}", ex);
        }
    }

    private static RisaleBook ParseBook(JsonElement element)
    {
        string slug = element.GetProperty("slug").GetString() ?? string.Empty;
        if (!SlugShape.IsMatch(slug) || slug.Length > MaxSlugLength)
        {
            throw new InvalidDataException($"Gecersiz Risale kitap slug'i: {slug}");
        }

        if (string.Equals(slug, ReservedSlug, StringComparison.Ordinal)
            || slug.StartsWith("test-", StringComparison.Ordinal))
        {
            throw new InvalidDataException($"Ayrilmis Risale kitap slug'i: {slug}");
        }

        string title = element.GetProperty("baslik").GetString() ?? string.Empty;
        string language = element.GetProperty("dil").GetString() ?? string.Empty;
        string direction = element.GetProperty("yon").GetString() ?? string.Empty;
        if (title.Length == 0 || !Languages.Contains(language, StringComparer.Ordinal) || !Directions.Contains(direction, StringComparer.Ordinal))
        {
            throw new InvalidDataException($"Gecersiz Risale kitap satiri: {slug}");
        }

        int volume = element.GetProperty("rnk").GetProperty("cilt").GetInt32();
        return volume is >= 1 and <= short.MaxValue
            ? new RisaleBook(slug, title, language, direction, volume)
            : throw new InvalidDataException($"Cilt numarasi smallint araliginda degil: {slug}");
    }

    private static IReadOnlyList<RisaleBook> LoadEmbedded() => Parse(ReadEmbeddedBytes());
}
