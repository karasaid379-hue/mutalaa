using System.Globalization;
using System.Text.Json.Nodes;
using Mutalaa.Domain.Content;
using Mutalaa.Domain.Licensing;
using Mutalaa.Domain.Links;
using Mutalaa.Domain.Tests.Support;

namespace Mutalaa.Domain.Tests;

/// <summary>
/// C# enum'lari packages/content-schema/enums.json ile ayni sirada ve ayni etiketle olmali.
/// Sira anlamlidir (ozellikle license_status: serbest &lt; bekliyor &lt; ic_kullanim &lt; kapali).
/// </summary>
public class EnumLabelTests
{
    private delegate bool TryParse<T>(string? label, out T value);

    /// <summary>JSON tur anahtari -> denetim. Yeni tur JSON'a eklenip buraya eklenmezse All_json_enum_keys_are_covered kirilir.</summary>
    private static readonly Dictionary<string, Action<string[]>> Checks = new(StringComparer.Ordinal)
    {
        ["license_status"] = labels => Check<LicenseStatus>(labels, LicenseStatusLabels.ToLabel, LicenseStatusLabels.TryParseLabel),
        ["xref_type"] = labels => Check<XrefType>(labels, XrefTypeLabels.ToLabel, XrefTypeLabels.TryParseLabel),
        ["xref_status"] = labels => Check<XrefStatus>(labels, XrefStatusLabels.ToLabel, XrefStatusLabels.TryParseLabel),
        ["xref_origin"] = labels => Check<XrefOrigin>(labels, XrefOriginLabels.ToLabel, XrefOriginLabels.TryParseLabel),
        ["source_kind"] = labels => Check<SourceKind>(labels, SourceKindLabels.ToLabel, SourceKindLabels.TryParseLabel),
        ["derleme_turu"] = labels => Check<BuildFlavor>(labels, BuildFlavorLabels.ToLabel, BuildFlavorLabels.TryParseLabel),
    };

    public static TheoryData<string> Keys => new(Checks.Keys.Order(StringComparer.Ordinal));

    private static Dictionary<string, string[]> LoadEnums()
    {
        string path = Path.Combine(AppContext.BaseDirectory, "data", "enums.json");
        if (!File.Exists(path))
        {
            throw new FileNotFoundException("packages/content-schema/enums.json cikti klasorune kopyalanmamis: " + path);
        }

        JsonObject enums = JsonNode.Parse(File.ReadAllText(path))!.AsObject()["enums"]!.AsObject();
        Dictionary<string, string[]> result = new(StringComparer.Ordinal);
        foreach (KeyValuePair<string, JsonNode?> entry in enums)
        {
            result[entry.Key] = [.. entry.Value!.AsArray().Select(n => n!.GetValue<string>())];
        }

        return result;
    }

    [Fact]
    public void All_json_enum_keys_are_covered()
    {
        string[] jsonKeys = [.. LoadEnums().Keys.Order(StringComparer.Ordinal)];
        string[] testKeys = [.. Checks.Keys.Order(StringComparer.Ordinal)];

        Assert.Equal(jsonKeys, testKeys);
    }

    [Theory]
    [MemberData(nameof(Keys))]
    public void Enum_matches_json_under_invariant_culture(string key) =>
        CultureScope.Invariant(() => Run(key));

    [Theory]
    [MemberData(nameof(Keys))]
    public void Enum_matches_json_under_turkish_culture(string key) =>
        CultureScope.Turkish(() => Run(key));

    [Fact]
    public void License_status_order_is_most_restrictive_last()
    {
        Assert.True(LicenseStatus.Serbest < LicenseStatus.Bekliyor);
        Assert.True(LicenseStatus.Bekliyor < LicenseStatus.IcKullanim);
        Assert.True(LicenseStatus.IcKullanim < LicenseStatus.Kapali);
    }

    [Fact]
    public void Undefined_numeric_value_throws_out_of_range()
    {
        Assert.Throws<ArgumentOutOfRangeException>(() => ((LicenseStatus)99).ToLabel());
        Assert.Throws<ArgumentOutOfRangeException>(() => ((BuildFlavor)(-1)).ToLabel());
        Assert.Throws<ArgumentOutOfRangeException>(() => ((SourceKind)17).ToLabel());
        Assert.Throws<ArgumentOutOfRangeException>(() => ((XrefType)8).ToLabel());
        Assert.Throws<ArgumentOutOfRangeException>(() => ((XrefStatus)3).ToLabel());
        Assert.Throws<ArgumentOutOfRangeException>(() => ((XrefOrigin)3).ToLabel());
    }

    [Fact]
    public void Null_label_is_rejected()
    {
        Assert.False(LicenseStatusLabels.TryParseLabel(null, out LicenseStatus value));
        Assert.Equal(default, value);
    }

    private static void Run(string key)
    {
        Dictionary<string, string[]> json = LoadEnums();
        Assert.True(json.TryGetValue(key, out string[]? labels), $"enums.json icinde '{key}' yok.");
        Checks[key](labels!);
    }

    private static int Num<T>(T value)
        where T : struct, Enum => Convert.ToInt32(value, CultureInfo.InvariantCulture);

    private static void Check<T>(string[] labels, Func<T, string> toLabel, TryParse<T> tryParse)
        where T : struct, Enum
    {
        T[] members = [.. Enum.GetValues<T>().OrderBy(Num)];

        // (a) uye sayisi
        Assert.Equal(labels.Length, members.Length);

        for (int i = 0; i < labels.Length; i++)
        {
            // (c) sayisal deger = JSON sirasi
            Assert.Equal(i, Num(members[i]));

            // (b) i. uyenin etiketi = JSON'un i. etiketi
            Assert.Equal(labels[i], toLabel(members[i]));

            // (d) gidis-donus
            Assert.True(tryParse(labels[i], out T parsed), $"'{labels[i]}' ayristirilamadi.");
            Assert.Equal(members[i], parsed);
        }

        // (e) bilinmeyen, buyuk harfli, kirpilmamis ve bos etiketler reddedilir
        foreach (string label in labels)
        {
            Assert.False(tryParse(label.ToUpperInvariant(), out _), $"'{label}' buyuk harfle kabul edildi.");
            Assert.False(tryParse(char.ToUpperInvariant(label[0]) + label[1..], out _), $"'{label}' bas harf buyukle kabul edildi.");
            Assert.False(tryParse(" " + label, out _));
            Assert.False(tryParse(label + " ", out _));
        }

        Assert.False(tryParse("IC_KULLANIM", out _));
        Assert.False(tryParse("Serbest", out _));
        Assert.False(tryParse(string.Empty, out _));
        Assert.False(tryParse("yok", out _));
    }
}
