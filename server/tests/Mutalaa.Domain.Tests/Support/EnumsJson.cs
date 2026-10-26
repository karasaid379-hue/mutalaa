using System.Text;
using System.Text.Json.Nodes;

namespace Mutalaa.Domain.Tests.Support;

/// <summary>
/// packages/content-schema/enums.json (cikti klasorunde data\enums.json) okuyucusu.
/// Tur anahtari -> etiketler (JSON sirasiyla). Dosya yoksa acik hata verir.
/// </summary>
internal static class EnumsJson
{
    public static Dictionary<string, string[]> Load()
    {
        string path = Path.Combine(AppContext.BaseDirectory, "data", "enums.json");
        if (!File.Exists(path))
        {
            throw new FileNotFoundException("packages/content-schema/enums.json cikti klasorune kopyalanmamis: " + path);
        }

        string text = new UTF8Encoding(encoderShouldEmitUTF8Identifier: false, throwOnInvalidBytes: true)
            .GetString(File.ReadAllBytes(path));
        JsonObject enums = JsonNode.Parse(text)!.AsObject()["enums"]!.AsObject();
        Dictionary<string, string[]> result = new(StringComparer.Ordinal);
        foreach (KeyValuePair<string, JsonNode?> entry in enums)
        {
            result.Add(entry.Key, [.. entry.Value!.AsArray().Select(n => n!.GetValue<string>())]);
        }

        return result;
    }
}
