using System.Text.RegularExpressions;
using Microsoft.Extensions.Options;
using Mutalaa.Api.Problems;
using Mutalaa.Api.Settings;

namespace Mutalaa.Api.Endpoints;

/// <summary>
/// OCR sayfa gorseli (<c>data/raw/{baski}/{YYYY-MM-DD}/{sayfa}.{uzanti}</c>, degismez ham veri). Gorsel akitilir (belleğe tam yuklenmez).
/// Yol parcalari katı desenle dogrulanir; cozulen tam yol <c>RawDir</c> icinde kalmali ve sembolik bag izlenmez.
/// </summary>
public static partial class ScanEndpoints
{
    private static readonly string[] Extensions = ["tif", "tiff", "png", "jpg", "jpeg"];

    public static RouteGroupBuilder MapScanEndpoints(this RouteGroupBuilder editor)
    {
        ArgumentNullException.ThrowIfNull(editor);

        RouteGroupBuilder scans = editor.MapGroup("/scans").WithTags("scans");

        // Govde JSON degil (dosya); oturumsuz 401 yine ProblemDetails (cerez yonlendirmesi AuthSetup'ta kapali).
        scans.MapGet("/{baski}/{sayfa}", GetPageAsync)
            .WithName("getScanPage")
            .WithSummary("Bir baskının OCR sayfa görselini (en yeni tarihli ham klasörden) akıtır.")
            .Produces(StatusCodes.Status200OK, contentType: "image/png")
            .Produces(StatusCodes.Status200OK, contentType: "image/jpeg")
            .Produces(StatusCodes.Status200OK, contentType: "image/tiff")
            .ProducesProblem(StatusCodes.Status400BadRequest)
            .ProducesProblem(StatusCodes.Status404NotFound);

        return editor;
    }

    // "\z": '$' sondaki satir sonundan once de eslesir ("abc%0A"); yol parcasi yalniz bu desene uymali.
    [GeneratedRegex(@"^[a-z0-9-]{1,64}\z", RegexOptions.CultureInvariant)]
    private static partial Regex BaskiPattern();

    [GeneratedRegex(@"^c[0-9]{2}-s[0-9]{4}\z", RegexOptions.CultureInvariant)]
    private static partial Regex SayfaPattern();

    [GeneratedRegex(@"^[0-9]{4}-[0-9]{2}-[0-9]{2}\z", RegexOptions.CultureInvariant)]
    private static partial Regex DatePattern();

    private static IResult GetPageAsync(string baski, string sayfa, HttpContext httpContext, IOptions<ApiOptions> options)
    {
        Dictionary<string, string[]> errors = new(StringComparer.Ordinal);
        if (!BaskiPattern().IsMatch(baski))
        {
            errors["baski"] = ["baski küçük harf, rakam ve '-' içeren en çok 64 karakter olmalı."];
        }

        if (!SayfaPattern().IsMatch(sayfa))
        {
            errors["sayfa"] = ["sayfa 'cNN-sNNNN' biçiminde olmalı."];
        }

        if (errors.Count > 0)
        {
            return ApiProblem.Validation(errors);
        }

        string? file = Resolve(options.Value.RawDir, baski, sayfa);
        if (file is null)
        {
            return ApiProblem.Create(StatusCodes.Status404NotFound, ProblemCodes.Bulunamadi, "Sayfa görseli bulunamadı.");
        }

        httpContext.Response.Headers.CacheControl = "private, no-store";
        httpContext.Response.Headers.XContentTypeOptions = "nosniff";
        return TypedResults.PhysicalFile(file, ContentTypeOf(file));
    }

    /// <summary>En yeni tarih klasorunden baslayarak sayfa dosyasini arar; bulunamazsa ya da kok disina cikarsa null.</summary>
    internal static string? Resolve(string rawDir, string baski, string sayfa)
    {
        string root = Path.GetFullPath(rawDir);
        if (!Directory.Exists(root))
        {
            return null;
        }

        string prefix = root.EndsWith(Path.DirectorySeparatorChar) ? root : root + Path.DirectorySeparatorChar;
        string baskiDir = Path.GetFullPath(Path.Combine(root, baski));
        if (!IsInside(prefix, baskiDir) || IsLink(new DirectoryInfo(baskiDir)) || !Directory.Exists(baskiDir))
        {
            return null;
        }

        // YYYY-MM-DD adi sirali (Ordinal) azalan: en yeni tarih once.
        string[] dates =
        [
            .. Directory.EnumerateDirectories(baskiDir)
                .Select(path => Path.GetFileName(path))
                .Where(name => DatePattern().IsMatch(name))
                .OrderByDescending(name => name, StringComparer.Ordinal),
        ];

        foreach (string date in dates)
        {
            string dateDir = Path.GetFullPath(Path.Combine(baskiDir, date));
            if (!IsInside(prefix, dateDir) || IsLink(new DirectoryInfo(dateDir)))
            {
                continue;
            }

            foreach (string extension in Extensions)
            {
                string candidate = Path.GetFullPath(Path.Combine(dateDir, sayfa + "." + extension));
                if (IsInside(prefix, candidate) && File.Exists(candidate) && !IsLink(new FileInfo(candidate)))
                {
                    return candidate;
                }
            }
        }

        return null;
    }

    private static bool IsInside(string rootWithSeparator, string path) =>
        path.StartsWith(rootWithSeparator, StringComparison.Ordinal);

    // Sembolik bag ve baglanti noktasi (junction); OneDrive yer tutucusu gibi bulut dosyalari bag sayilmaz.
    private static bool IsLink(FileSystemInfo info) => info.LinkTarget is not null;

    private static string ContentTypeOf(string file) =>
        Path.GetExtension(file).ToUpperInvariant() switch
        {
            ".TIF" or ".TIFF" => "image/tiff",
            ".PNG" => "image/png",
            _ => "image/jpeg",
        };
}
