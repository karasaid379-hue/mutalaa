using System.Globalization;
using Mutalaa.Domain.Content;
using Mutalaa.Domain.Links;
using Mutalaa.Domain.Releases;
using Mutalaa.Domain.Reviews;
using Mutalaa.Domain.Tests.Support;

namespace Mutalaa.Domain.Tests;

/// <summary>
/// C# enum'lari packages/content-schema/enums.json ile ayni sirada ve ayni etiketle olmali.
/// Sira anlamlidir (ozellikle metin_durumu: taslak &lt; incelemede &lt; onayli; alfabetik sira degildir).
/// </summary>
public class EnumLabelTests
{
    private delegate bool TryParse<T>(string? label, out T value);

    /// <summary>JSON tur anahtari -> denetim. Yeni tur JSON'a eklenip buraya eklenmezse All_json_enum_keys_are_covered kirilir.</summary>
    private static readonly Dictionary<string, Action<string[]>> Checks = new(StringComparer.Ordinal)
    {
        ["xref_type"] = labels => Check<XrefType>(labels, XrefTypeLabels.ToLabel, XrefTypeLabels.TryParseLabel),
        ["xref_status"] = labels => Check<XrefStatus>(labels, XrefStatusLabels.ToLabel, XrefStatusLabels.TryParseLabel),
        ["xref_origin"] = labels => Check<XrefOrigin>(labels, XrefOriginLabels.ToLabel, XrefOriginLabels.TryParseLabel),
        ["source_kind"] = labels => Check<SourceKind>(labels, SourceKindLabels.ToLabel, SourceKindLabels.TryParseLabel),
        ["derleme_turu"] = labels => Check<BuildFlavor>(labels, BuildFlavorLabels.ToLabel, BuildFlavorLabels.TryParseLabel),
        ["unit_kind"] = labels => Check<UnitKind>(labels, UnitKindLabels.ToLabel, UnitKindLabels.TryParseLabel),
        ["unit_status"] = labels => Check<UnitStatus>(labels, UnitStatusLabels.ToLabel, UnitStatusLabels.TryParseLabel),
        ["metin_durumu"] = labels => Check<TextStatus>(labels, TextStatusLabels.ToLabel, TextStatusLabels.TryParseLabel),
        ["inceleme_durumu"] = labels => Check<ReviewStatus>(labels, ReviewStatusLabels.ToLabel, ReviewStatusLabels.TryParseLabel),
        ["surum_durumu"] = labels => Check<ReleaseStatus>(labels, ReleaseStatusLabels.ToLabel, ReleaseStatusLabels.TryParseLabel),
    };

    public static TheoryData<string> Keys => new(Checks.Keys.Order(StringComparer.Ordinal));

    [Fact]
    public void All_json_enum_keys_are_covered()
    {
        string[] jsonKeys = [.. EnumsJson.Load().Keys.Order(StringComparer.Ordinal)];
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
    public void Metin_durumu_order_follows_the_editorial_flow_not_the_alphabet()
    {
        Assert.True(TextStatus.Taslak < TextStatus.Incelemede);
        Assert.True(TextStatus.Incelemede < TextStatus.Onayli);
        Assert.True(string.CompareOrdinal(TextStatus.Taslak.ToLabel(), TextStatus.Onayli.ToLabel()) > 0);
    }

    [Fact]
    public void Undefined_numeric_value_throws_out_of_range()
    {
        Assert.Throws<ArgumentOutOfRangeException>(() => ((TextStatus)99).ToLabel());
        Assert.Throws<ArgumentOutOfRangeException>(() => ((BuildFlavor)(-1)).ToLabel());
        Assert.Throws<ArgumentOutOfRangeException>(() => ((SourceKind)17).ToLabel());
        Assert.Throws<ArgumentOutOfRangeException>(() => ((XrefType)8).ToLabel());
        Assert.Throws<ArgumentOutOfRangeException>(() => ((XrefStatus)3).ToLabel());
        Assert.Throws<ArgumentOutOfRangeException>(() => ((XrefOrigin)3).ToLabel());
        Assert.Throws<ArgumentOutOfRangeException>(() => ((UnitKind)7).ToLabel());
        Assert.Throws<ArgumentOutOfRangeException>(() => ((UnitStatus)2).ToLabel());
        Assert.Throws<ArgumentOutOfRangeException>(() => ((TextStatus)3).ToLabel());
        Assert.Throws<ArgumentOutOfRangeException>(() => ((ReviewStatus)4).ToLabel());
        Assert.Throws<ArgumentOutOfRangeException>(() => ((ReleaseStatus)5).ToLabel());
    }

    [Fact]
    public void Null_label_is_rejected()
    {
        Assert.False(TextStatusLabels.TryParseLabel(null, out TextStatus value));
        Assert.Equal(default, value);
    }

    private static void Run(string key)
    {
        Dictionary<string, string[]> json = EnumsJson.Load();
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

        Assert.False(tryParse("IKTIBAS", out _));
        Assert.False(tryParse("KULLANIM_DISI", out _));
        Assert.False(tryParse("Taslak", out _));
        Assert.False(tryParse(string.Empty, out _));
        Assert.False(tryParse("yok", out _));
    }
}
