using Mutalaa.Domain.Tests.Support;

namespace Mutalaa.Domain.Tests;

/// <summary>
/// Editoryal veritabani 2'deki CREATE TYPE ... AS ENUM tanimlari packages/content-schema/enums.json ile ayni olmali:
/// ayni tur kumesi, her turde ayni etiketler ayni sirada (K-37 madde 2). Docker gerektirmez.
/// </summary>
public class EnumDocumentTests
{
    [Fact]
    public void Document_section_2_enum_types_match_enums_json()
    {
        string section = EditorialDoc.Section(EditorialDoc.Read(), 2);
        IReadOnlyList<KeyValuePair<string, string[]>> doc = EditorialDoc.ParseEnumTypes(EditorialDoc.SqlBlocks(section));
        Dictionary<string, string[]> json = EnumsJson.Load();

        Assert.NotEmpty(doc);
        List<string> problems = Compare(doc, json);
        if (problems.Count > 0)
        {
            Assert.Fail($"{EditorialDoc.RelativePath} 2 ile enums.json farkli:\n" + string.Join('\n', problems));
        }
    }

    [Fact]
    public void Parser_reads_multi_line_definitions_in_order_and_ignores_comments()
    {
        const string sql =
            "CREATE TYPE deneme_a AS ENUM ('bir','iki',\n" +
            "                              'uc_4');\n" +
            "-- yorum: CREATE TYPE deneme_c AS ENUM ('yok');\n" +
            "CREATE TYPE deneme_b   AS ENUM (\n  'x'\n);\n";

        IReadOnlyList<KeyValuePair<string, string[]>> types = EditorialDoc.ParseEnumTypes(sql);

        string[] names = ["deneme_a", "deneme_b"];
        string[] first = ["bir", "iki", "uc_4"];
        string[] second = ["x"];
        Assert.Equal(names, types.Select(t => t.Key));
        Assert.Equal(first, types[0].Value);
        Assert.Equal(second, types[1].Value);
    }

    [Theory]
    [InlineData("CREATE TYPE t AS ENUM ('a', b);")]
    [InlineData("CREATE TYPE t AS ENUM ('a','B');")]
    [InlineData("CREATE TYPE t AS ENUM ('a',);")]
    [InlineData("CREATE TYPE t AS ENUM ('a')")]
    public void Parser_rejects_unrecognised_definitions(string sql) =>
        Assert.Throws<InvalidDataException>(() => EditorialDoc.ParseEnumTypes(sql));

    [Fact]
    public void Parser_rejects_non_ascii_digits_in_labels()
    {
        // U+0661 ARABIC-INDIC DIGIT ONE: \d eslerdi, [0-9] eslemez.
        string sql = "CREATE TYPE t AS ENUM ('a" + char.ConvertFromUtf32(0x0661) + "');";

        Assert.Throws<InvalidDataException>(() => EditorialDoc.ParseEnumTypes(sql));
    }

    [Fact]
    public void Comparison_reports_duplicate_missing_extra_and_reordered_types()
    {
        KeyValuePair<string, string[]>[] doc =
        [
            new("a", ["x", "y"]),
            new("b", ["p"]),
            new("b", ["p"]),
            new("d", ["r"]),
        ];
        Dictionary<string, string[]> json = new(StringComparer.Ordinal)
        {
            ["a"] = ["y", "x"],
            ["c"] = ["q"],
            ["d"] = ["r"],
        };

        List<string> problems = Compare(doc, json);

        string[] expected =
        [
            "Belgede yinelenen tur: 'b'",
            "Belgede var, enums.json'da yok: 'b'",
            "enums.json'da var, belgede yok: 'c'",
            "'a' etiketleri farkli: belge [x, y] / enums.json [y, x]",
        ];
        Assert.Equal(expected, problems);
    }

    private static List<string> Compare(IReadOnlyList<KeyValuePair<string, string[]>> doc, Dictionary<string, string[]> json)
    {
        List<string> problems = [];
        Dictionary<string, string[]> docByName = new(StringComparer.Ordinal);
        foreach (KeyValuePair<string, string[]> type in doc)
        {
            if (!docByName.TryAdd(type.Key, type.Value))
            {
                problems.Add($"Belgede yinelenen tur: '{type.Key}'");
            }
        }

        foreach (string name in docByName.Keys.Except(json.Keys, StringComparer.Ordinal).Order(StringComparer.Ordinal))
        {
            problems.Add($"Belgede var, enums.json'da yok: '{name}'");
        }

        foreach (string name in json.Keys.Except(docByName.Keys, StringComparer.Ordinal).Order(StringComparer.Ordinal))
        {
            problems.Add($"enums.json'da var, belgede yok: '{name}'");
        }

        foreach (string name in docByName.Keys.Intersect(json.Keys, StringComparer.Ordinal).Order(StringComparer.Ordinal))
        {
            string[] fromDoc = docByName[name];
            string[] fromJson = json[name];
            if (!fromDoc.SequenceEqual(fromJson, StringComparer.Ordinal))
            {
                problems.Add($"'{name}' etiketleri farkli: belge [{string.Join(", ", fromDoc)}] / enums.json [{string.Join(", ", fromJson)}]");
            }
        }

        return problems;
    }
}
