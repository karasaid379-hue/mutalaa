using System.Text;
using Microsoft.EntityFrameworkCore;
using Mutalaa.Api.Tests.Support;
using Mutalaa.Domain.Content;

namespace Mutalaa.Api.Tests;

/// <summary>
/// K-26 metin butunlugu (Docker'li): <c>unit.metin</c> kod noktalari veritabaninda AYNEN saklanir; NFC, kirpma, satir sonu ya da
/// kulturle ilgili hicbir donusum yoktur. Her girdi EF ile yazilir, (a) EF ile ayri bir baglamdan geri okunur ve (b) ham SQL ile
/// <c>convert_to(metin, 'UTF8')</c> baytlari girdinin UTF-8 baytlariyla karsilastirilir; Invariant ve tr-TR kulturunde.
/// Amac: ileride <c>Properties&lt;string&gt;()</c> donusturucusu, NFC ya da kirpma eklenirse bu testlerin kirilmasi.
/// Girdiler sentetiktir: yalniz kod noktasi dizileri (Kur'an, meal ya da Risale metni degil).
/// </summary>
public class TextIntegrityTests(EditorialDatabase<TextIntegrityTests> fixture) : IClassFixture<EditorialDatabase<TextIntegrityTests>>
{
    private static readonly UTF8Encoding StrictUtf8 = new(encoderShouldEmitUTF8Identifier: false, throwOnInvalidBytes: true);

    /// <summary>NFC altinda degisen (bir donusturucu eklenirse fark edilecek) girdiler: testin anlamli kalmasi icin korunur.</summary>
    private static readonly string[] NfcUnstable = ["nfd_decomposed_e_acute", "arabic_shadda_then_fatha_nfc_unstable"];

    /// <summary>Ad -> girdi. Kod noktalari Cp(...) ile kurulur; xunit'e yalniz ad gider (gorunmez karakterler gosterim adini bozmasin).</summary>
    private static readonly Dictionary<string, string> Inputs = new(StringComparer.Ordinal)
    {
        // U+00E9 ile e + U+0301: ayni gorunur, NFC altinda tek kod noktasina birlesir.
        ["nfc_precomposed_e_acute"] = Cp(0x00E9),
        ["nfd_decomposed_e_acute"] = Cp(0x0065, 0x0301),
        ["crlf_and_edge_spaces"] = "a\r\n b ",
        ["nbsp_edges"] = Cp(0x00A0) + "Deneme" + Cp(0x00A0),
        ["supplementary_plane_book"] = Cp(0x1F4D6),
        ["supplementary_plane_between_bmp"] = "a" + Cp(0x1F4D6) + "b" + Cp(0x1D400) + "c",

        // beh + shadda (ccc 33) + fatha (ccc 30): NFC siralamayi degistirir; beh + fatha + shadda zaten kanonik siradadir.
        ["arabic_shadda_then_fatha_nfc_unstable"] = Cp(0x0628, 0x0651, 0x064E),
        ["arabic_fatha_then_shadda_nfc_stable"] = Cp(0x0628, 0x064E, 0x0651),
        ["leading_and_trailing_spaces"] = "  Deneme paragrafi 1  ",
        ["leading_and_trailing_tabs_and_newlines"] = "\t\nDeneme\n\t",
        ["turkish_capital_dotted_i"] = Cp(0x0130),
        ["turkish_dotless_i_and_ascii_i_mixed"] = Cp(0x0130, 0x0131) + "Ii i" + Cp(0x0307),
        ["zero_width_and_bidi_marks"] = "a" + Cp(0x200D) + "b" + Cp(0x200E, 0x200F, 0x2028) + "c" + Cp(0xFEFF) + "d",
        ["only_whitespace_inside"] = "a " + Cp(0x2003) + " b",
    };

    public static TheoryData<string> InputNames => new(Inputs.Keys);

    private TestDatabase Db => fixture.Database;

    /// <summary>Kod noktalarindan dize kurar (kaynak dosya ASCII kalir; gorunmez karakterler araca ya da editore bagli degildir).</summary>
    private static string Cp(params int[] codePoints) => string.Concat(codePoints.Select(char.ConvertFromUtf32));

    [Fact]
    public void The_nfc_unstable_inputs_really_change_under_nfc_and_the_others_cover_the_edge_cases()
    {
        foreach (string name in NfcUnstable)
        {
            Assert.False(Inputs[name].IsNormalized(NormalizationForm.FormC), name);
            Assert.NotEqual(Inputs[name], Inputs[name].Normalize(NormalizationForm.FormC));
        }

        Assert.True(Inputs["nfc_precomposed_e_acute"].IsNormalized(NormalizationForm.FormC));
        Assert.True(Inputs["arabic_fatha_then_shadda_nfc_stable"].IsNormalized(NormalizationForm.FormC));

        // NFC ile birlesen ikili ayni gorunur ama farkli kod noktasidir; veritabani ikisini ayri saklamali.
        Assert.Equal(Inputs["nfc_precomposed_e_acute"], Inputs["nfd_decomposed_e_acute"].Normalize(NormalizationForm.FormC));
        Assert.NotEqual(Inputs["nfc_precomposed_e_acute"], Inputs["nfd_decomposed_e_acute"]);
        Assert.Contains("\r\n", Inputs["crlf_and_edge_spaces"], StringComparison.Ordinal);
        Assert.NotEqual(Inputs["leading_and_trailing_spaces"].Trim(), Inputs["leading_and_trailing_spaces"]);
        Assert.NotEqual(Inputs["nbsp_edges"].Trim(), Inputs["nbsp_edges"]);
        Assert.Single(Inputs["supplementary_plane_book"].EnumerateRunes().ToArray());
        Assert.Equal(2, Inputs["supplementary_plane_book"].Length);
    }

    [Theory]
    [MemberData(nameof(InputNames))]
    public async Task Metin_is_stored_and_read_back_byte_for_byte_under_the_invariant_culture(string name)
    {
        CancellationToken ct = TestContext.Current.CancellationToken;

        await AssertStoredVerbatimAsync(name, ct);
    }

    [Theory]
    [MemberData(nameof(InputNames))]
    public async Task Metin_is_stored_and_read_back_byte_for_byte_under_tr_TR(string name)
    {
        CancellationToken ct = TestContext.Current.CancellationToken;

        await AsyncCultureScope.TurkishAsync(() => AssertStoredVerbatimAsync(name, ct));
    }

    [Fact]
    public async Task Nfc_equivalent_inputs_are_kept_as_two_distinct_values()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        long idPrecomposed = await WriteAsync(Inputs["nfc_precomposed_e_acute"], ct);
        long idDecomposed = await WriteAsync(Inputs["nfd_decomposed_e_acute"], ct);

        byte[] a = await Db.ScalarAsync<byte[]>("SELECT convert_to(metin, 'UTF8') FROM icerik.unit WHERE id = @id", ct, ("id", idPrecomposed));
        byte[] b = await Db.ScalarAsync<byte[]>("SELECT convert_to(metin, 'UTF8') FROM icerik.unit WHERE id = @id", ct, ("id", idDecomposed));

        Assert.Equal(new byte[] { 0xC3, 0xA9 }, a);
        Assert.Equal(new byte[] { 0x65, 0xCC, 0x81 }, b);
        Assert.Equal(2L, await Db.ScalarAsync<long>(
            "SELECT count(DISTINCT metin) FROM icerik.unit WHERE id = ANY(@ids)", ct, ("ids", new[] { idPrecomposed, idDecomposed })));
    }

    private async Task AssertStoredVerbatimAsync(string name, CancellationToken ct)
    {
        string input = Inputs[name];
        byte[] expectedBytes = StrictUtf8.GetBytes(input);
        int expectedCodePoints = input.EnumerateRunes().Count();

        long id = await WriteAsync(input, ct);

        // (a) EF ile ayri bir baglamdan (ayri baglanti, izleme onbellegi yok) geri okuma.
        await using (DbSession reader = Db.OpenSession())
        {
            Unit read = await reader.Context.Units.AsNoTracking().SingleAsync(u => u.Id == id, ct);
            Assert.Equal(input, read.Metin);
            Assert.Equal(expectedBytes, StrictUtf8.GetBytes(read.Metin));
        }

        // (b) Ham SQL: saklanan bayt dizisi, boyut ve kod noktasi sayisi.
        byte[] stored = await Db.ScalarAsync<byte[]>("SELECT convert_to(metin, 'UTF8') FROM icerik.unit WHERE id = @id", ct, ("id", id));
        Assert.Equal(expectedBytes, stored);
        Assert.Equal(expectedBytes.Length, await Db.ScalarAsync<int>("SELECT octet_length(metin) FROM icerik.unit WHERE id = @id", ct, ("id", id)));
        Assert.Equal(expectedCodePoints, await Db.ScalarAsync<int>("SELECT char_length(metin) FROM icerik.unit WHERE id = @id", ct, ("id", id)));
    }

    /// <summary>EF ile yeni kaynak + birim yazar (islem commit edilir); birimin kimligini dondurur.</summary>
    private async Task<long> WriteAsync(string metin, CancellationToken ct)
    {
        await using DbSession writer = Db.OpenSession();
        Source source = TestData.NewSource();
        writer.Context.Add(source);
        await writer.Context.SaveChangesAsync(ct);

        Unit unit = TestData.NewUnit(source.Slug, TestData.UnitAnchor());
        unit.Metin = metin;
        writer.Context.Add(unit);
        await writer.Context.SaveChangesAsync(ct);
        return unit.Id;
    }
}
