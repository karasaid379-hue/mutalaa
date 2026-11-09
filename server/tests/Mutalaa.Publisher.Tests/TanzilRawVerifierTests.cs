using System.Globalization;
using System.Security.Cryptography;
using System.Text;
using Mutalaa.Api.Tests.Support;
using Mutalaa.Domain.Releases.Gate;
using Mutalaa.Domain.Tests.Support;
using Mutalaa.Domain.Text;
using Mutalaa.Infrastructure.Releases;

namespace Mutalaa.Publisher.Tests;

/// <summary>
/// TanzilRawVerifier (P-11): depodaki fikstur parcalariyla (pipeline/tests/fixtures/tanzil/*-parca.txt; ilk 40 ayet satiri + tam bildirim blogu, bayt bayt).
/// Parcalar csproj ile baytlari degismeden cikti klasorunun data\tanzil\ altina kopyalanir. Metin testte hicbir yerde elle yazilmaz: birim hash'leri
/// ve bildirim, dosyanin kendi baytlarindan test icinde bagimsiz bir bolmeyle turetilir. Docker gerektirmez.
/// </summary>
public class TanzilRawVerifierTests
{
    private const string Date = "2026-11-02";

    private static byte[] Fixture(string name)
    {
        string path = Path.Combine(AppContext.BaseDirectory, "data", "tanzil", name);
        Assert.True(File.Exists(path), "Fikstur cikti klasorune kopyalanmamis: " + path);
        return File.ReadAllBytes(path);
    }

    // Test icinde bagimsiz bolme: 0x0A ile satirlara bol; "s|a|" onekli satirlar ayet, geri kalan bildirim.
    private static (Dictionary<string, string> Hashes, string Notice, int Count) Split(byte[] data)
    {
        UTF8Encoding strict = new(false, true);
        Dictionary<string, string> hashes = new(StringComparer.Ordinal);
        int pos = 0;
        int count = 0;
        while (pos < data.Length)
        {
            int end = Array.IndexOf(data, (byte)'\n', pos);
            byte[] line = data[pos..end];
            int bar1 = Array.IndexOf(line, (byte)'|');
            int bar2 = bar1 < 0 ? -1 : Array.IndexOf(line, (byte)'|', bar1 + 1);
            bool verse = bar1 > 0 && bar2 > bar1 && line[..bar1].All(b => b is >= (byte)'0' and <= (byte)'9') && line[(bar1 + 1)..bar2].All(b => b is >= (byte)'0' and <= (byte)'9');
            if (!verse)
            {
                return (hashes, strict.GetString(data[pos..]), count);
            }

            string anchor = "q:" + strict.GetString(line[..bar1]) + ":" + strict.GetString(line[(bar1 + 1)..bar2]);
            hashes[anchor] = Convert.ToHexStringLower(SHA256.HashData(line[(bar2 + 1)..]));
            count++;
            pos = end + 1;
        }

        throw new InvalidDataException("bildirim blogu yok");
    }

    private sealed class RawLayout : IDisposable
    {
        private readonly PackTestData.TempDir _temp = new();

        public string RawDir => _temp.Path;

        public SourceRow Place(string slug, string fileName, byte[] data, string? notice, string date = Date)
        {
            string dir = Path.Combine(RawDir, slug, date);
            Directory.CreateDirectory(dir);
            File.WriteAllBytes(Path.Combine(dir, fileName), data);
            string sha = Convert.ToHexStringLower(SHA256.HashData(data));
            return PackTestData.Source(slug, "kuran_metni", notice: notice) with
            {
                AlinmaTarihi = DateOnly.ParseExact(date, "yyyy-MM-dd", CultureInfo.InvariantCulture),
                DosyaSha256 = sha,
            };
        }

        public void Dispose() => _temp.Dispose();
    }

    [Fact]
    public void The_fixture_split_matches_the_documented_shape()
    {
        (Dictionary<string, string> hashes, string notice, int count) = Split(Fixture("uthmani-parca.txt"));

        Assert.Equal(40, count);
        Assert.Equal(40, hashes.Count);
        Assert.Contains("q:1:1", hashes.Keys);
        Assert.Contains("q:2:33", hashes.Keys);
        Assert.StartsWith("\n\n#", notice, StringComparison.Ordinal);
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void The_uthmani_fixture_passes_with_matching_hashes_notice_and_line_count(bool turkish)
    {
        CultureScope.For(turkish, () =>
        {
            byte[] data = Fixture("uthmani-parca.txt");
            (Dictionary<string, string> hashes, string notice, int count) = Split(data);
            using RawLayout layout = new();
            SourceRow source = layout.Place("tanzil-uthmani", "quran-uthmani.txt", data, notice);

            IReadOnlyList<GateViolation> violations = new TanzilRawVerifier(layout.RawDir).Verify(source, hashes, count);

            Assert.Empty(violations);
        });
    }

    [Fact]
    public void Unit_hashes_computed_by_the_domain_function_equal_the_raw_hashes_of_the_parsed_file()
    {
        byte[] data = Fixture("uthmani-parca.txt");
        (Dictionary<string, string> hashes, _, _) = Split(data);

        TanzilRawFile file = TanzilRawFile.Parse(data);

        Assert.Equal(40, file.Verses.Count);
        foreach (TanzilVerse verse in file.Verses)
        {
            string anchor = string.Create(CultureInfo.InvariantCulture, $"q:{verse.Sure}:{verse.Ayet}");
            Assert.Equal(hashes[anchor], ContentHash.Compute(verse.Text));
        }
    }

    [Fact]
    public void The_simple_clean_fixture_passes_with_notice_and_line_count_only()
    {
        byte[] data = Fixture("simple-clean-parca.txt");
        (_, string notice, int count) = Split(data);
        using RawLayout layout = new();
        SourceRow source = layout.Place("tanzil-simple-clean", "quran-simple-clean.txt", data, notice);

        IReadOnlyList<GateViolation> violations = new TanzilRawVerifier(layout.RawDir).Verify(source, null, count);

        Assert.Empty(violations);
    }

    [Fact]
    public void A_flipped_text_byte_is_reported_as_a_hash_mismatch_for_that_anchor()
    {
        byte[] original = Fixture("uthmani-parca.txt");
        (Dictionary<string, string> hashes, string notice, int count) = Split(original);
        byte[] flipped = FlipFirstLetterByte(original);
        using RawLayout layout = new();
        // Dosya kendi ozetiyle kayitli (dosya_sha256 degisen dosyadan); birim hash'leri ASIL metinden.
        SourceRow source = layout.Place("tanzil-uthmani", "quran-uthmani.txt", flipped, notice);

        IReadOnlyList<GateViolation> violations = new TanzilRawVerifier(layout.RawDir).Verify(source, hashes, count);

        GateViolation violation = Assert.Single(violations);
        Assert.Equal(GateRule.P11, violation.Rule);
        Assert.Equal("hash-uyusmuyor", violation.Reason);
        Assert.Matches("^q:[0-9]+:[0-9]+$", violation.Subject);
        Assert.NotEqual(Convert.ToHexStringLower(SHA256.HashData(original)), source.DosyaSha256);
    }

    [Fact]
    public void A_changed_notice_byte_is_reported_as_bildirim_uyusmuyor()
    {
        byte[] data = Fixture("uthmani-parca.txt");
        (Dictionary<string, string> hashes, string notice, int count) = Split(data);
        using RawLayout layout = new();
        SourceRow source = layout.Place("tanzil-uthmani", "quran-uthmani.txt", data, notice + "x");

        IReadOnlyList<GateViolation> violations = new TanzilRawVerifier(layout.RawDir).Verify(source, hashes, count);

        GateViolation violation = Assert.Single(violations);
        Assert.Equal((GateRule.P11, "tanzil-uthmani", "bildirim-uyusmuyor"), (violation.Rule, violation.Subject, violation.Reason));
    }

    [Fact]
    public void A_null_notice_on_the_source_is_a_mismatch_too()
    {
        byte[] data = Fixture("uthmani-parca.txt");
        (Dictionary<string, string> hashes, _, int count) = Split(data);
        using RawLayout layout = new();
        SourceRow source = layout.Place("tanzil-uthmani", "quran-uthmani.txt", data, notice: null);

        IReadOnlyList<GateViolation> violations = new TanzilRawVerifier(layout.RawDir).Verify(source, hashes, count);

        Assert.Equal("bildirim-uyusmuyor", Assert.Single(violations).Reason);
    }

    [Fact]
    public void A_unit_count_different_from_the_line_count_is_reported()
    {
        byte[] data = Fixture("uthmani-parca.txt");
        (Dictionary<string, string> hashes, string notice, int count) = Split(data);
        using RawLayout layout = new();
        SourceRow source = layout.Place("tanzil-uthmani", "quran-uthmani.txt", data, notice);
        Dictionary<string, string> missingOne = new(hashes, StringComparer.Ordinal);
        missingOne.Remove("q:2:33");

        IReadOnlyList<GateViolation> violations = new TanzilRawVerifier(layout.RawDir).Verify(source, missingOne, count - 1);

        // Satir sayisi 40, birim sayisi 39: hem sayi hem birim eksigi bildirilir.
        Assert.Contains(violations, v => v.Reason == "satir-sayisi-uyusmuyor");
        Assert.Contains(violations, v => v.Reason == "ham-dosyada-yok" || v.Reason == "birim-yok");
        Assert.All(violations, v => Assert.Equal(GateRule.P11, v.Rule));
    }

    [Fact]
    public void The_file_is_found_by_sha256_even_when_its_name_is_not_the_expected_one()
    {
        byte[] data = Fixture("uthmani-parca.txt");
        (Dictionary<string, string> hashes, string notice, int count) = Split(data);
        using RawLayout layout = new();
        SourceRow source = layout.Place("tanzil-uthmani", "baska-ad.txt", data, notice);
        File.WriteAllText(Path.Combine(layout.RawDir, "tanzil-uthmani", Date, "fetch.json"), "{}");

        IReadOnlyList<GateViolation> violations = new TanzilRawVerifier(layout.RawDir).Verify(source, hashes, count);

        Assert.Empty(violations);
    }

    [Fact]
    public void A_file_whose_sha256_differs_from_the_record_is_not_accepted()
    {
        byte[] data = Fixture("uthmani-parca.txt");
        (Dictionary<string, string> hashes, string notice, int count) = Split(data);
        using RawLayout layout = new();
        SourceRow source = layout.Place("tanzil-uthmani", "quran-uthmani.txt", data, notice) with { DosyaSha256 = new string('0', 64) };

        GateViolation violation = Assert.Single(new TanzilRawVerifier(layout.RawDir).Verify(source, hashes, count));

        Assert.Equal((GateRule.P11, "ham-dosya-sha256-uyusmuyor"), (violation.Rule, violation.Reason));
    }

    [Fact]
    public void A_missing_directory_date_or_sha_is_reported()
    {
        byte[] data = Fixture("uthmani-parca.txt");
        (Dictionary<string, string> hashes, string notice, int count) = Split(data);
        using RawLayout layout = new();
        SourceRow source = layout.Place("tanzil-uthmani", "quran-uthmani.txt", data, notice);
        TanzilRawVerifier verifier = new(layout.RawDir);

        Assert.Equal("ham-dosya-yok", Assert.Single(verifier.Verify(source with { AlinmaTarihi = new DateOnly(2026, 1, 1) }, hashes, count)).Reason);
        Assert.Equal("ham-dosya-konumu-yok", Assert.Single(verifier.Verify(source with { AlinmaTarihi = null }, hashes, count)).Reason);
        Assert.Equal("ham-dosya-konumu-yok", Assert.Single(verifier.Verify(source with { DosyaSha256 = null }, hashes, count)).Reason);
        Assert.Equal("ham-dosya-konumu-yok", Assert.Single(verifier.Verify(source with { Slug = "../x" }, hashes, count)).Reason);
    }

    [Theory]
    [InlineData("bom")]
    [InlineData("cr")]
    [InlineData("sonda-lf-yok")]
    [InlineData("gecersiz-utf8")]
    [InlineData("bildirimsiz")]
    [InlineData("bos-metin")]
    [InlineData("bildirimde-ayet")]
    public void A_malformed_file_is_a_format_violation_without_the_line_content(string defect)
    {
        byte[] data = Malform(Fixture("uthmani-parca.txt"), defect);
        using RawLayout layout = new();
        SourceRow source = layout.Place("tanzil-uthmani", "quran-uthmani.txt", data, "x");

        GateViolation violation = Assert.Single(new TanzilRawVerifier(layout.RawDir).Verify(source, new Dictionary<string, string>(), 0));

        Assert.Equal(GateRule.P11, violation.Rule);
        Assert.StartsWith("ham-dosya-bicimi: ", violation.Reason, StringComparison.Ordinal);
        Assert.True(violation.Reason.All(c => c < 128), "Ileti satir icerigi (Arapca metin) tasimamali.");
    }

    [Fact]
    public void Parse_returns_the_notice_block_verbatim_and_the_verse_texts_without_any_transformation()
    {
        byte[] data = Fixture("uthmani-parca.txt");
        (_, string notice, _) = Split(data);

        TanzilRawFile file = TanzilRawFile.Parse(data);

        Assert.Equal(notice, file.Notice);
        Assert.Equal((1, 1), (file.Verses[0].Sure, file.Verses[0].Ayet));
        Assert.Equal((2, 33), (file.Verses[^1].Sure, file.Verses[^1].Ayet));
        // Metin bayt bayt: NFC uygulansaydi degisirdi; satir yeniden kurulunca dosya aynen elde edilir.
        StringBuilder rebuilt = new();
        foreach (TanzilVerse v in file.Verses)
        {
            rebuilt.Append(CultureInfo.InvariantCulture, $"{v.Sure}|{v.Ayet}|").Append(v.Text).Append('\n');
        }

        rebuilt.Append(file.Notice);
        Assert.Equal(data, new UTF8Encoding(false, true).GetBytes(rebuilt.ToString()));
    }

    [Fact]
    public void ExpectedFileName_maps_the_two_tanzil_downloads_only()
    {
        Assert.Equal("quran-uthmani.txt", TanzilRawVerifier.ExpectedFileName("tanzil-uthmani"));
        Assert.Equal("quran-simple-clean.txt", TanzilRawVerifier.ExpectedFileName("tanzil-simple-clean"));
        Assert.Null(TanzilRawVerifier.ExpectedFileName("tanzil-ust-veri"));
    }

    // Birimler ham dosyanin kendi metninden: metin satirdaki gibi, content_hash metinden.
    private static UnitRow[] UnitsOf(byte[] data) =>
    [
        .. TanzilRawFile.Parse(data).Verses.Select((v, i) =>
            PackTestData.Unit(string.Create(CultureInfo.InvariantCulture, $"q:{v.Sure}:{v.Ayet}"), "tanzil-uthmani", "ayet", ord: i)
            with { Metin = v.Text, ContentHash = ContentHash.Compute(v.Text) }),
    ];

    [Fact]
    public void VerifyAll_reports_a_unit_text_that_differs_from_the_raw_line_even_when_the_hash_is_left_unchanged()
    {
        byte[] uthmani = Fixture("uthmani-parca.txt");
        (_, string notice, _) = Split(uthmani);
        using RawLayout layout = new();
        SourceRow source = layout.Place("tanzil-uthmani", "quran-uthmani.txt", uthmani, notice);
        UnitRow[] units = UnitsOf(uthmani);
        units[5] = units[5] with { Metin = units[5].Metin + "x" };
        EditorialSnapshot snapshot = new() { Sources = [source], Units = units };

        IReadOnlyList<GateViolation> violations = new TanzilRawVerifier(layout.RawDir).VerifyAll(snapshot, ["tanzil-uthmani"]);

        Assert.All(violations, v => Assert.Equal(GateRule.P11, v.Rule));
        Assert.Contains(violations, v => v.Subject == units[5].Anchor && v.Reason == "metin-uyusmuyor");
        Assert.Contains(violations, v => v.Subject == units[5].Anchor && v.Reason == "hash-metinle-uyusmuyor");
        Assert.DoesNotContain(violations, v => v.Reason == "hash-uyusmuyor");
        Assert.Equal(2, violations.Count);
    }

    [Fact]
    public void VerifyAll_reports_a_unit_whose_text_and_hash_both_changed_consistently_as_a_hash_mismatch_with_the_raw_file()
    {
        byte[] uthmani = Fixture("uthmani-parca.txt");
        (_, string notice, _) = Split(uthmani);
        using RawLayout layout = new();
        SourceRow source = layout.Place("tanzil-uthmani", "quran-uthmani.txt", uthmani, notice);
        UnitRow[] units = UnitsOf(uthmani);
        string changed = units[2].Metin + "x";
        units[2] = units[2] with { Metin = changed, ContentHash = ContentHash.Compute(changed) };
        EditorialSnapshot snapshot = new() { Sources = [source], Units = units };

        IReadOnlyList<GateViolation> violations = new TanzilRawVerifier(layout.RawDir).VerifyAll(snapshot, ["tanzil-uthmani"]);

        Assert.Contains(violations, v => v.Subject == units[2].Anchor && v.Reason == "hash-uyusmuyor");
        Assert.Contains(violations, v => v.Subject == units[2].Anchor && v.Reason == "metin-uyusmuyor");
        Assert.DoesNotContain(violations, v => v.Reason == "hash-metinle-uyusmuyor");
    }

    [Fact]
    public void VerifyAll_checks_that_a_word_is_the_code_point_slice_of_its_ayah_text()
    {
        byte[] uthmani = Fixture("uthmani-parca.txt");
        (_, string notice, _) = Split(uthmani);
        using RawLayout layout = new();
        SourceRow source = layout.Place("tanzil-uthmani", "quran-uthmani.txt", uthmani, notice);
        UnitRow[] units = UnitsOf(uthmani);
        UnitRow ayah = units[1];
        int firstSpace = ayah.Metin.IndexOf(' ', StringComparison.Ordinal);
        string firstWord = ayah.Metin[..firstSpace];
        int length = CodePointOffsets.CodePointCount(firstWord);
        QuranWordRow good = new(ayah.Anchor + ":1", 1, 2, 1, 2, firstWord, firstWord, 0, length, "tanzil-uthmani");
        EditorialSnapshot ok = new() { Sources = [source], Units = units, QuranWords = [good] };
        TanzilRawVerifier verifier = new(layout.RawDir);

        Assert.Empty(verifier.VerifyAll(ok, ["tanzil-uthmani"]));

        GateViolation wrongText = Assert.Single(verifier.VerifyAll(
            new EditorialSnapshot { Sources = ok.Sources, Units = units, QuranWords = [good with { TextUthmani = firstWord + "x" }] }, ["tanzil-uthmani"]));
        Assert.Equal((GateRule.P11, good.Anchor, "kelime-metni-uyusmuyor"), (wrongText.Rule, wrongText.Subject, wrongText.Reason));

        GateViolation outOfRange = Assert.Single(verifier.VerifyAll(
            new EditorialSnapshot { Sources = ok.Sources, Units = units, QuranWords = [good with { CharEnd = CodePointOffsets.CodePointCount(ayah.Metin) + 1 }] }, ["tanzil-uthmani"]));
        Assert.Equal("kelime-metni-uyusmuyor", outOfRange.Reason);

        GateViolation noAyah = Assert.Single(verifier.VerifyAll(
            new EditorialSnapshot { Sources = ok.Sources, Units = units, QuranWords = [good with { Anchor = "q:114:6:1", Surah = 114, Ayah = 6 }] }, ["tanzil-uthmani"]));
        Assert.Equal(("q:114:6:1", "kelime-ayeti-yok"), (noAyah.Subject, noAyah.Reason));
    }

    [Fact]
    public void VerifyAll_checks_included_tanzil_sources_against_the_snapshot()
    {
        byte[] uthmani = Fixture("uthmani-parca.txt");
        byte[] simple = Fixture("simple-clean-parca.txt");
        (_, string uthmaniNotice, _) = Split(uthmani);
        (_, string simpleNotice, _) = Split(simple);
        using RawLayout layout = new();
        SourceRow uthmaniSource = layout.Place("tanzil-uthmani", "quran-uthmani.txt", uthmani, uthmaniNotice);
        SourceRow simpleSource = layout.Place("tanzil-simple-clean", "quran-simple-clean.txt", simple, simpleNotice);
        UnitRow[] units = UnitsOf(uthmani);
        EditorialSnapshot snapshot = new() { Sources = [uthmaniSource, simpleSource, PackTestData.Source("tanzil-ust-veri")], Units = units };
        TanzilRawVerifier verifier = new(layout.RawDir);

        Assert.Empty(verifier.VerifyAll(snapshot, ["tanzil-uthmani", "tanzil-simple-clean", "tanzil-ust-veri"]));

        // Bir birimin hash'i bozulursa yalniz o capa ihlal verir.
        UnitRow[] broken = [.. units];
        broken[3] = broken[3] with { ContentHash = new string('f', 64) };
        EditorialSnapshot brokenSnapshot = new() { Sources = snapshot.Sources, Units = broken };
        // Bozulan hash iki ihlal verir: ham dosyadakiyle farkli, ve birimin kendi metninden hesaplananla farkli.
        IReadOnlyList<GateViolation> brokenViolations = verifier.VerifyAll(brokenSnapshot, ["tanzil-uthmani", "tanzil-simple-clean"]);
        Assert.Equal(["hash-metinle-uyusmuyor", "hash-uyusmuyor"], brokenViolations.Select(v => v.Reason).Order(StringComparer.Ordinal).ToArray());
        Assert.All(brokenViolations, v => Assert.Equal(broken[3].Anchor, v.Subject));

        // Kapidan girmeyen kaynak denetlenmez.
        Assert.Empty(verifier.VerifyAll(brokenSnapshot, ["tanzil-simple-clean"]));
        Assert.Empty(verifier.VerifyAll(snapshot, []));
    }

    [Fact]
    public void VerifyAll_ignores_deprecated_units_when_comparing_counts_and_hashes()
    {
        byte[] uthmani = Fixture("uthmani-parca.txt");
        (_, string notice, _) = Split(uthmani);
        using RawLayout layout = new();
        SourceRow source = layout.Place("tanzil-uthmani", "quran-uthmani.txt", uthmani, notice);
        List<UnitRow> units = [.. UnitsOf(uthmani)];
        units.Add(PackTestData.Unit("q:9:9", "tanzil-uthmani", "ayet", status: "kullanim_disi", successors: "[]"));
        EditorialSnapshot snapshot = new() { Sources = [source], Units = units };

        Assert.Empty(new TanzilRawVerifier(layout.RawDir).VerifyAll(snapshot, ["tanzil-uthmani"]));
    }

    // Ilk Arapca harf bayt cifti (0xD8 0xA8) icin son baytini 0xA9 yapar: gecerli UTF-8 kalir, harf degisir.
    private static byte[] FlipFirstLetterByte(byte[] data)
    {
        byte[] copy = [.. data];
        for (int i = 0; i < copy.Length - 1; i++)
        {
            if (copy[i] == 0xD8 && copy[i + 1] == 0xA8)
            {
                copy[i + 1] = 0xA9;
                return copy;
            }
        }

        throw new InvalidDataException("Fiksturda cevrilecek bayt cifti yok.");
    }

    private static byte[] Malform(byte[] data, string defect)
    {
        int firstLf = Array.IndexOf(data, (byte)'\n');
        switch (defect)
        {
            case "bom":
                return [0xEF, 0xBB, 0xBF, .. data];
            case "cr":
                return [.. data[..firstLf], (byte)'\r', .. data[firstLf..]];
            case "sonda-lf-yok":
                return data[..^1];
            case "gecersiz-utf8":
                return [.. data[..firstLf], 0xFF, .. data[firstLf..]];
            case "bildirimsiz":
                // yalniz ilk ayet satiri
                return data[..(firstLf + 1)];
            case "bos-metin":
                return [.. "1|1|\n"u8, .. data[(firstLf + 1)..]];
            case "bildirimde-ayet":
                return [.. data, .. "1|1|x\n"u8];
            default:
                throw new ArgumentOutOfRangeException(nameof(defect));
        }
    }
}
