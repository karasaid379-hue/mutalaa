using System.Globalization;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Text;
using System.Text.Json.Nodes;
using Mutalaa.Domain.Tests.Support;
using Mutalaa.Domain.Text;

namespace Mutalaa.Domain.Tests;

/// <summary>
/// Arama normallestirmesi (K-36): normalize/tr.jsonl ve normalize/ar.jsonl ortak vektorleri.
/// Her Theory Invariant ve tr-TR kulturunde ayri kosar.
/// </summary>
public class NormalizeVectorTests
{
    private const string TrFile = "normalize/tr.jsonl";
    private const string ArFile = "normalize/ar.jsonl";

    public static TheoryData<string> TrIds => VectorFile.Ids(TrFile);

    public static TheoryData<string> ArIds => VectorFile.Ids(ArFile);

    // ---- tr ----

    [Theory]
    [MemberData(nameof(TrIds))]
    public void Turkish_Invariant(string id) => CultureScope.Invariant(() => CheckTurkish(id));

    [Theory]
    [MemberData(nameof(TrIds))]
    public void Turkish_trTR(string id) => CultureScope.Turkish(() => CheckTurkish(id));

    private static void CheckTurkish(string id)
    {
        VectorCase v = VectorFile.Get(TrFile, id);
        string input = v.Input!.GetValue<string>();
        string copy = new(input.AsSpan());
        JsonObject expected = v.Expected!.AsObject();
        string dar = expected["dar"]!.GetValue<string>();
        string genis = expected["genis"]!.GetValue<string>();

        Assert.Equal(dar, SearchNormalizer.TurkishNarrow(input));
        Assert.Equal(genis, SearchNormalizer.TurkishWide(input));

        SearchKeys keys = SearchNormalizer.Keys(input);
        Assert.Equal(dar, keys.TrNarrow);
        Assert.Equal(genis, keys.TrWide);
        Assert.Equal(SearchNormalizer.Arabic(input), keys.ArNorm);

        // Sozcuk sayisi ve sirasi: dar ve genis ayni sayida sozcuk tasir.
        Assert.Equal(dar.Length == 0 ? 0 : dar.Split(' ').Length, genis.Length == 0 ? 0 : genis.Split(' ').Length);
        Assert.Equal(copy, input);
    }

    // ---- ar ----

    [Theory]
    [MemberData(nameof(ArIds))]
    public void Arabic_Invariant(string id) => CultureScope.Invariant(() => CheckArabic(id));

    [Theory]
    [MemberData(nameof(ArIds))]
    public void Arabic_trTR(string id) => CultureScope.Turkish(() => CheckArabic(id));

    private static void CheckArabic(string id)
    {
        VectorCase v = VectorFile.Get(ArFile, id);
        string input = v.Input!.GetValue<string>();
        string expected = v.Expected!.GetValue<string>();

        Assert.Equal(expected, SearchNormalizer.Arabic(input));
        Assert.Equal(expected, SearchNormalizer.Keys(input).ArNorm);
    }

    // ---- ic kesme listesi ----

    [Fact]
    public void IcKesme_entries_match_shared_file()
    {
        string path = Path.Combine(AppContext.BaseDirectory, "data", "ic-kesme.txt");
        string text = new UTF8Encoding(encoderShouldEmitUTF8Identifier: false, throwOnInvalidBytes: true)
            .GetString(File.ReadAllBytes(path));

        Assert.EndsWith("\n", text, StringComparison.Ordinal);
        string[] lines = text[..^1].Split('\n');

        Assert.Equal(lines, SearchNormalizer_IcKesmeEntries());
    }

    private static string[] SearchNormalizer_IcKesmeEntries() => [.. IcKesme.Entries];

    [Theory]
    [InlineData("ab'cd'ef", "abcdef")]
    [InlineData("ab'cx'y", "abcx")]
    [InlineData("ab'dx", "ab")]
    [InlineData("zz'ab'cd'e", "zz")]
    public void Longest_ic_kesme_entry_wins_in_any_order(string input, string expected)
    {
        string[] forward = ["ab'c", "ab'cd'e"];
        string[] backward = ["ab'cd'e", "ab'c"];

        Assert.Equal(expected, SearchNormalizer.TurkishKeys(input, forward).Narrow);
        Assert.Equal(expected, SearchNormalizer.TurkishKeys(input, backward).Narrow);
    }

    [Fact]
    public void Empty_ic_kesme_list_cuts_at_first_apostrophe()
    {
        Assert.Equal("kur", SearchNormalizer.TurkishKeys("Kur'an", []).Narrow);
        Assert.Equal("kuran", SearchNormalizer.TurkishKeys("Kur'an", ["kur'an"]).Narrow);
    }

    // ---- eslesmemis vekil ----

    public static TheoryData<string, string> SurrogateCases => new()
    {
        { "a\ud800b", "a b" },
        { "a\udc00b", "a b" },
        { "\udc00\ud800", string.Empty },
        { "a\ud800", "a" },
        { "\udc00a", "a" },
        { "a\ud801\udc00b", "a\ud801\udc28b" },
        { "\ud800\ud801\udc00", "\ud801\udc28" },
        { "a\ud801\ud801\udc00b", "a \ud801\udc28b" },
    };

    [Theory]
    [MemberData(nameof(SurrogateCases))]
    public void Unpaired_surrogates_become_spaces_and_pairs_survive(string input, string expectedNarrow)
    {
        // Dar anahtar sozcuklere bolundugu icin beklenen dize, bosluklarin ayirdigi sozcuklerle karsilastirilir.
        string narrow = SearchNormalizer.TurkishNarrow(input);
        Assert.Equal(string.Join(' ', expectedNarrow.Split(' ', StringSplitOptions.RemoveEmptyEntries)), narrow);
        Assert.Equal(string.Empty, SearchNormalizer.Arabic(input));
    }

    [Fact]
    public void SplitScripts_replaces_each_unpaired_surrogate_with_exactly_one_space()
    {
        (string tr, string ar) = SearchNormalizer.SplitScripts("a\ud800b\udc00");

        Assert.Equal("a b ", tr);
        Assert.Equal("    ", ar);
    }

    // ---- ilk adim ve genel ozellikler ----

    [Fact]
    public void LowerTurkish_maps_dotted_and_dotless_I_before_simple_lowercase()
    {
        Assert.Equal("\u0131i\u0131i", SearchNormalizer.LowerTurkish("I\u0130\u0131i"));
        Assert.Equal("\u0131\u015fik", SearchNormalizer.LowerTurkish("I\u015e\u0130K"));
        Assert.Equal("\u03bf\u03b4\u03bf\u03c3", SearchNormalizer.LowerTurkish("\u039f\u0394\u039f\u03a3"));
    }

    [Fact]
    public void LowerTurkish_is_culture_independent()
    {
        string input = "I\u0130\u0131iABC";
        string invariant = string.Empty;
        string turkish = string.Empty;
        CultureScope.Invariant(() => invariant = SearchNormalizer.LowerTurkish(input));
        CultureScope.Turkish(() => turkish = SearchNormalizer.LowerTurkish(input));

        Assert.Equal(invariant, turkish);
        Assert.Equal("\u0131i\u0131iabc", invariant);
    }

    // ---- U+FFFE (string.Normalize atar; parcalayarak normallestirilir) ----

    // Beklenenler K-36'dan turetildi: U+FFFE Cn'dir (sozcuk karakteri degil, Cf degil), Arapca blokta degil.
    [Theory]
    [InlineData("a\uFFFEb", "a b", "a b", "")]
    [InlineData("\uFFFE", "", "", "")]
    [InlineData("\uFFFE\uFFFEa", "a", "a", "")]
    [InlineData("a\uFFFE\uFFFE", "a", "a", "")]
    [InlineData("a\uFFFE\uFFFEb", "a b", "a b", "")]
    [InlineData("ab\uFFFE", "ab", "ab", "")]
    [InlineData("a\u200E\uFFFE\u200Fb", "a b", "a b", "")]
    [InlineData("I\uFFFE\u0130", "\u0131 i", "i i", "")]
    // Birlesen isaret Cn'in ardinda e'ye birlesmez: ayri (harf icermeyen) sozcuk olur ve atilir.
    [InlineData("e\uFFFE\u0301", "e", "e", "")]
    // Cn'den once gelen isaret NFC'de onceki harfle birlesir.
    [InlineData("e\u0301\uFFFE\u0301", "\u00E9", "e", "")]
    [InlineData("\u0628\uFFFE\u0628", "", "", "\u0628 \u0628")]
    [InlineData("\u0628\uFFFE", "", "", "\u0628")]
    [InlineData("\uFFFE\u0628", "", "", "\u0628")]
    [InlineData("\u0628\uFFFE\u064E", "", "", "\u0628")]
    [InlineData("\u0628\uFFFE\uFFFE\u0628\uFFFEabc", "abc", "abc", "\u0628 \u0628")]
    public void Noncharacter_FFFE_does_not_throw_and_acts_as_separator(string input, string narrow, string wide, string arabic)
    {
        CultureScope.Invariant(() => CheckFffe(input, narrow, wide, arabic));
        CultureScope.Turkish(() => CheckFffe(input, narrow, wide, arabic));
    }

    private static void CheckFffe(string input, string narrow, string wide, string arabic)
    {
        SearchKeys keys = SearchNormalizer.Keys(input);

        Assert.Equal(narrow, keys.TrNarrow);
        Assert.Equal(wide, keys.TrWide);
        Assert.Equal(arabic, keys.ArNorm);
        Assert.Equal(narrow, SearchNormalizer.TurkishNarrow(input));
        Assert.Equal(wide, SearchNormalizer.TurkishWide(input));
        Assert.Equal(arabic, SearchNormalizer.Arabic(input));
    }

    // Diger degismez/atanmamis kod noktalari (K-36): Cn ve So ayirici; Cf (U+E0001) silinir. U+FDD0 Arapca blokta
    // oldugu icin Turkce parcada bosluk olur, Arapca parcada Cn ayirici kalir.
    [Theory]
    [InlineData("\uFFFF", "a b", "a b", "\u0628 \u0628")]
    [InlineData("\U0001FFFE", "a b", "a b", "\u0628 \u0628")]
    [InlineData("\U0010FFFF", "a b", "a b", "\u0628 \u0628")]
    [InlineData("\uFDD0", "a b", "a b", "\u0628 \u0628")]
    [InlineData("\uFFFD", "a b", "a b", "\u0628 \u0628")]
    [InlineData("\U000E0001", "ab", "ab", "\u0628\u0628")]
    public void Other_noncharacters_and_unassigned_code_points_do_not_throw(string cp, string narrow, string wide, string arabic)
    {
        CultureScope.Invariant(() => CheckFffe("a" + cp + "b", narrow, wide, string.Empty));
        CultureScope.Turkish(() => CheckFffe("a" + cp + "b", narrow, wide, string.Empty));
        CultureScope.Invariant(() => CheckFffe("\u0628" + cp + "\u0628", string.Empty, string.Empty, arabic));
        CultureScope.Turkish(() => CheckFffe("\u0628" + cp + "\u0628", string.Empty, string.Empty, arabic));
    }

    [Fact]
    public void SplitScripts_keeps_FFFE_in_turkish_part_and_normalizes_around_it()
    {
        (string tr, string ar) = SearchNormalizer.SplitScripts("e\u0301\uFFFE\u0301");

        Assert.Equal("\u00E9\uFFFE\u0301", tr);
        Assert.Equal("   ", ar);
    }

    [Fact]
    public void Null_input_is_rejected_and_empty_input_gives_empty_keys()
    {
        Assert.Throws<ArgumentNullException>(() => SearchNormalizer.Keys(null!));
        Assert.Throws<ArgumentNullException>(() => SearchNormalizer.LowerTurkish(null!));
        Assert.Throws<ArgumentNullException>(() => SearchNormalizer.SplitScripts(null!));
        Assert.Throws<ArgumentNullException>(() => SearchNormalizer.TurkishNarrow(null!));
        Assert.Throws<ArgumentNullException>(() => SearchNormalizer.TurkishWide(null!));
        Assert.Throws<ArgumentNullException>(() => SearchNormalizer.Arabic(null!));

        Assert.Equal(new SearchKeys(string.Empty, string.Empty, string.Empty), SearchNormalizer.Keys(string.Empty));
    }

    [Fact]
    public void Keys_returns_all_three_keys_for_mixed_text()
    {
        SearchKeys keys = SearchNormalizer.Keys("Kur'an \u0628\u064e\u0651\u062a I\u015e\u0130K");

        Assert.Equal("kuran \u0131\u015fik", keys.TrNarrow);
        Assert.Equal("kuran isik", keys.TrWide);
        Assert.Equal("\u0628\u062a", keys.ArNorm);
    }

    [Fact]
    public void Normalizer_version_is_1_0() => Assert.Equal("1.0", SearchNormalizer.NormalizerVersion);

    // ---- calisma ortami kaydi ----

    [Fact]
    public void Environment_is_recorded()
    {
        string? useNlsSwitch = AppContext.TryGetSwitch("System.Globalization.UseNls", out bool nls) ? nls.ToString() : "(ayarlanmamis)";
        string? invariantMode = AppContext.TryGetSwitch("System.Globalization.Invariant", out bool inv) ? inv.ToString() : "(ayarlanmamis)";
        string effective = EffectiveGlobalizationMode();
        string info =
            $"[normalize ortami] OS={RuntimeInformation.OSDescription}; Runtime={RuntimeInformation.FrameworkDescription}; "
            + $"UseNls anahtari={useNlsSwitch}; Invariant anahtari={invariantMode}; etkin kip={effective}; "
            + $"CurrentCulture={CultureInfo.CurrentCulture.Name}; Unicode(Rune) ornek kategori U+0131={Rune.GetUnicodeCategory(new Rune(0x131))}";

        TestContext.Current.SendDiagnosticMessage(info);
        Console.WriteLine(info);

        // Kip okunabilmeli: ICU, NLS ya da Invariant'tan biri. "bilinmiyor" ise yansima calismamistir ve test kirmizi olur.
        Assert.Contains(effective, new[] { "ICU", "NLS", "Invariant" });
    }

    private static string EffectiveGlobalizationMode()
    {
        // GlobalizationMode ic bir tiptir; yoksa ya da yansima basarisizsa kip "bilinmiyor" yazilir.
        Type? t = typeof(object).Assembly.GetType("System.Globalization.GlobalizationMode");
        if (t is null)
        {
            return "bilinmiyor";
        }

        const BindingFlags flags = BindingFlags.Static | BindingFlags.Public | BindingFlags.NonPublic;
        bool? invariant = t.GetProperty("Invariant", flags)?.GetValue(null) as bool?;
        bool? useNls = t.GetProperty("UseNls", flags)?.GetValue(null) as bool?;
        if (invariant == true)
        {
            return "Invariant";
        }

        return useNls switch
        {
            true => "NLS",
            false => "ICU",
            _ => "bilinmiyor",
        };
    }
}
