using System.Collections.Concurrent;
using System.Text;
using System.Text.Json.Nodes;

namespace Mutalaa.Domain.Tests.Support;

/// <summary>Bir vektor satiri: id, input, expected ve isteye bagli note.</summary>
internal sealed record VectorCase(string Id, JsonNode? Input, JsonNode? Expected, string? Note);

/// <summary>
/// shared/test-vectors altindaki JSONL dosyalarini okur (cikti klasorunde vectors\).
/// Dosya yoksa ya da bos ise ACIK HATA verir; sifir test sessizce gecmez.
/// </summary>
internal static class VectorFile
{
    private static readonly ConcurrentDictionary<string, IReadOnlyList<VectorCase>> Cache = new(StringComparer.Ordinal);

    public static IReadOnlyList<VectorCase> Load(string relativePath)
    {
        return Cache.GetOrAdd(relativePath, ReadAll);
    }

    public static VectorCase Get(string relativePath, string id)
    {
        foreach (VectorCase c in Load(relativePath))
        {
            if (string.Equals(c.Id, id, StringComparison.Ordinal))
            {
                return c;
            }
        }

        throw new InvalidOperationException($"Vektor bulunamadi: {relativePath} / {id}");
    }

    /// <summary>MemberData icin kimlik listesi (nesne degil dizgi; testler id ile gorunur).</summary>
    public static TheoryData<string> Ids(string relativePath)
    {
        TheoryData<string> data = [];
        foreach (VectorCase c in Load(relativePath))
        {
            data.Add(c.Id);
        }

        return data;
    }

    private static IReadOnlyList<VectorCase> ReadAll(string relativePath)
    {
        string path = Path.Combine(AppContext.BaseDirectory, "vectors", relativePath);
        if (!File.Exists(path))
        {
            throw new FileNotFoundException($"Vektor dosyasi yok (csproj baglantisini denetleyin): {path}");
        }

        string text = new UTF8Encoding(encoderShouldEmitUTF8Identifier: false, throwOnInvalidBytes: true)
            .GetString(File.ReadAllBytes(path));
        if (text.Length == 0)
        {
            throw new InvalidDataException($"Vektor dosyasi bos: {relativePath}");
        }

        if (text[0] == (char)0xFEFF)
        {
            throw new InvalidDataException($"Vektor dosyasinda BOM var: {relativePath}");
        }

        // Yalniz LF ile bol; Unicode satir ayiricilari (U+2028 vb.) satir sonu sayilmaz.
        string[] lines = text.Split('\n');
        if (lines[^1].Length != 0)
        {
            throw new InvalidDataException($"Dosya satir sonuyla bitmiyor: {relativePath}");
        }

        List<VectorCase> cases = new(lines.Length - 1);
        HashSet<string> seen = new(StringComparer.Ordinal);
        for (int i = 0; i < lines.Length - 1; i++)
        {
            if (lines[i].Length == 0)
            {
                throw new InvalidDataException($"Bos satir: {relativePath}:{i + 1}");
            }

            JsonObject obj = JsonNode.Parse(lines[i])?.AsObject()
                ?? throw new InvalidDataException($"Gecersiz satir: {relativePath}:{i + 1}");
            string id = obj["id"]?.GetValue<string>()
                ?? throw new InvalidDataException($"id yok: {relativePath}:{i + 1}");
            if (!seen.Add(id))
            {
                throw new InvalidDataException($"Yinelenen id: {relativePath} / {id}");
            }

            if (!obj.TryGetPropertyValue("input", out JsonNode? input) || !obj.TryGetPropertyValue("expected", out JsonNode? expected))
            {
                throw new InvalidDataException($"input/expected yok: {relativePath} / {id}");
            }

            // Dugumler bir ust dugume bagli oldugu icin ayrilir.
            string? note = obj["note"]?.GetValue<string>();
            obj.Remove("input");
            obj.Remove("expected");
            cases.Add(new VectorCase(id, input, expected, note));
        }

        if (cases.Count == 0)
        {
            throw new InvalidDataException($"Vektor dosyasinda satir yok: {relativePath}");
        }

        return cases;
    }
}
