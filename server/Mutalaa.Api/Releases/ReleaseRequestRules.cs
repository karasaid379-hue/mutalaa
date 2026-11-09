using System.Buffers;
using System.Globalization;
using System.Text;
using Mutalaa.Domain.Releases;
using Mutalaa.Infrastructure.Packs;

namespace Mutalaa.Api.Releases;

/// <summary>Dogrulanmis yayin talebi gövdesi. Errors bos degilse diger alanlar kullanilmaz.</summary>
/// <param name="Flavor">Derleme turu (yalniz Errors bos ise anlamli).</param>
/// <param name="Packs">Bos ya da verilmediyse null (butun paketler); aksi hâlde katalogda olan, tekrarsiz kimlikler (verilen sirayla).</param>
/// <param name="Notes">Bos ya da yalniz bosluktan olusuyorsa null.</param>
/// <param name="Errors">Alan adi (JSON, snake_case) -> iletiler.</param>
public sealed record ReleaseRequestResult(
    BuildFlavor Flavor,
    string[]? Packs,
    string? Notes,
    IReadOnlyDictionary<string, string[]> Errors)
{
    public bool IsValid => Errors.Count == 0;
}

/// <summary>
/// Yayin talebi gövdelerinin ortak kurallari (K-48 madde 7): derleme turu etiketi tam eslesir (Ordinal; buyuk-kucuk harf duyarli, kultursuz),
/// <c>paketler</c> katalogla dogrulanir ve tekrarsizdir, <c>notlar</c> en cok 2000 Unicode kod noktasidir ve PostgreSQL'e yazilabilir olmalidir
/// (NUL ve eslesmemis vekil karakter reddedilir). Saf islevlerdir; veritabani ve ag kullanmazlar.
/// </summary>
public static class ReleaseRequestRules
{
    public const int MaxNotesCodePoints = 2000;

    private const int MaxEchoLength = 64;

    /// <summary>derleme, paketler ve notlar alanlarini dogrular (preview <c>notlar</c> vermez: null).</summary>
    public static ReleaseRequestResult Validate(string? derleme, string[]? paketler, string? notlar, PackCatalog catalog)
    {
        ArgumentNullException.ThrowIfNull(catalog);

        Dictionary<string, string[]> errors = new(StringComparer.Ordinal);

        BuildFlavor flavor = default;
        if (string.IsNullOrEmpty(derleme))
        {
            errors["derleme"] = ["derleme alanı zorunludur."];
        }
        else if (!BuildFlavorLabels.TryParseLabel(derleme, out flavor))
        {
            errors["derleme"] = [$"Geçersiz derleme türü: '{Echo(derleme)}'. İzin verilenler: dev, internal, public."];
        }

        string[]? packs = ValidatePacks(paketler, catalog, errors);
        string? notes = ValidateNotes(notlar, errors);

        return new ReleaseRequestResult(flavor, packs, notes, errors);
    }

    /// <summary>Yalniz <c>notlar</c> alani olan gövdeler (promote ve rollback) icin: hata varsa alan -> iletiler, yoksa null.</summary>
    public static IDictionary<string, string[]>? ValidateNotesOnly(string? notlar, out string? notes)
    {
        Dictionary<string, string[]> errors = new(StringComparer.Ordinal);
        notes = ValidateNotes(notlar, errors);
        return errors.Count == 0 ? null : errors;
    }

    private static string[]? ValidatePacks(string[]? paketler, PackCatalog catalog, Dictionary<string, string[]> errors)
    {
        if (paketler is null || paketler.Length == 0)
        {
            return null;
        }

        List<string> messages = [];
        HashSet<string> seen = new(StringComparer.Ordinal);
        foreach (string? id in paketler)
        {
            if (string.IsNullOrWhiteSpace(id))
            {
                messages.Add("Paket kimliği boş olamaz.");
            }
            else if (!catalog.TryGet(id, out _))
            {
                messages.Add($"Bilinmeyen paket: '{Echo(id)}'.");
            }
            else if (!seen.Add(id))
            {
                messages.Add($"Yinelenen paket: '{id}'.");
            }
        }

        if (messages.Count > 0)
        {
            errors["paketler"] = [.. messages];
            return null;
        }

        return [.. paketler];
    }

    private static string? ValidateNotes(string? notlar, Dictionary<string, string[]> errors)
    {
        if (string.IsNullOrWhiteSpace(notlar))
        {
            return null;
        }

        int count = 0;
        ReadOnlySpan<char> rest = notlar;
        while (!rest.IsEmpty)
        {
            OperationStatus status = Rune.DecodeFromUtf16(rest, out Rune rune, out int consumed);
            if (status != OperationStatus.Done || rune.Value == 0)
            {
                errors["notlar"] = ["notlar alanı geçersiz karakter içeriyor (NUL ya da eşleşmemiş vekil karakter)."];
                return null;
            }

            count++;
            rest = rest[consumed..];
        }

        if (count > MaxNotesCodePoints)
        {
            errors["notlar"] = [string.Create(CultureInfo.InvariantCulture, $"notlar en çok {MaxNotesCodePoints} karakter olabilir.")];
            return null;
        }

        return notlar;
    }

    /// <summary>Hata iletisine girecek kullanici girdisini kisaltir (vekil cifti bolmez).</summary>
    private static string Echo(string value)
    {
        if (value.Length <= MaxEchoLength)
        {
            return value;
        }

        int length = char.IsHighSurrogate(value[MaxEchoLength - 1]) ? MaxEchoLength - 1 : MaxEchoLength;
        return value[..length] + "…";
    }
}
