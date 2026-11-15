using Microsoft.Data.Sqlite;
using Mutalaa.Domain.Releases;
using Mutalaa.Domain.Releases.Gate;
using Mutalaa.Infrastructure.Packs;
using Mutalaa.Infrastructure.Releases;

namespace Mutalaa.Publisher.Tests;

// Lugat (A20.6, K-52 madde 9 ve 10): risale-dizin'in lugat tablosu. RisalePackTests ile ayni sinif (kismi): sentetik Risale anlik goruntusunu ve
// yardimcilarini paylasir. Girdi tamamen sentetiktir ("deneme-sozcuk", "Deneme tanimi"); gercek Risale ya da sozluk metni yoktur. Docker gerektirmez.
public partial class RisalePackTests
{
    private const string LugatSource = PackCatalog.RisaleLugatSlug;
    private const string LugatRnkSource = PackCatalog.RisaleLugatRnkSlug;
    private const string LugatSozlukSource = PackCatalog.RisaleLugatSozlukSlug;
    private const string LugatFixtureSource = PackCatalog.RisaleFixtureSourceSlug;

    private static LugatMaddeRow Madde(
        string source,
        string basliksoz,
        string status,
        string? tanim = null,
        string origin = "hat",
        string version = "1",
        string? norm = null,
        int anlamNo = 1) =>
        new(source, basliksoz, norm ?? basliksoz, anlamNo, null, null, tanim, 1, status, origin, version, LugatMaddeHash(basliksoz, tanim));

    private static string LugatMaddeHash(string basliksoz, string? tanim) =>
        Mutalaa.Domain.Text.ContentHash.Compute(basliksoz + "\n" + (tanim ?? string.Empty));

    /// <summary>Risale anlik goruntusu + lugat kaynaklari ve maddeleri (Lexicals da kurulur; kapi P-09'u bunlardan okur).</summary>
    private static EditorialSnapshot WithLugat(EditorialSnapshot basis, IReadOnlyList<LugatMaddeRow> rows)
    {
        // Fikstur kaynagi (test-risale-ornek) temel goruntude zaten vardir: birimleri, page_map ve lugat maddeleri tek kaynak adindadir.
        List<SourceRow> sources = [.. basis.Sources, Src(LugatSource, "sozluk"), Src(LugatRnkSource, "sozluk"), Src(LugatSozlukSource, "sozluk")];

        return new EditorialSnapshot
        {
            Sources = sources,
            Units = basis.Units,
            QuranWords = basis.QuranWords,
            QuranMarkers = basis.QuranMarkers,
            PageMaps = basis.PageMaps,
            Xrefs = basis.Xrefs,
            Lexicals = [.. basis.Lexicals, .. rows.Select(r => new LexicalRow(LexicalKind.LugatMadde, r.SourceId + ":" + r.AnlamNo.ToString(System.Globalization.CultureInfo.InvariantCulture) + ":" + r.Basliksoz, r.Status, false))],
            LugatMaddeler = rows,
        };
    }

    private static LugatMaddeRow[] ThreeStates() =>
    [
        Madde(LugatSource, "onayli-sozcuk", "onayli", "Deneme tanimi 1", origin: "editor", version: "2"),
        Madde(LugatSource, "aday-sozcuk", "aday"),
        Madde(LugatSource, "red-sozcuk", "red"),
    ];

    [Fact]
    public void Lugat_table_columns_and_the_row_order_follow_the_contract_and_come_last()
    {
        Assert.Equal(
            ["basliksoz", "basliksoz_norm", "osmanlica_yazim", "koken_dil", "tanim_tr", "anlam_no", "kaynak", "duzey", "status", "origin", "version", "content_hash"],
            PackTables.Columns("lugat"));
        Assert.Equal("lugat", PackTables.Order[^1]);
        Assert.DoesNotContain(PackTables.Columns("lugat"), c => c is "kaynaklar" or "siklik" or "kitaplar" or "anlam_basvuru" or "sozluk_isabet" or "source_id" or "anlam");

        // Satir kayitlari ve anlik goruntu satiri basvuru verisi tasimaz (K-52 madde 10).
        foreach (Type type in new[] { typeof(PackLugatRow), typeof(LugatMaddeRow) })
        {
            Assert.DoesNotContain(type.GetProperties(), p => p.Name is "Kaynaklar" or "Siklik" or "Kitaplar" or "AnlamBasvuru");
        }
    }

    [Theory]
    [InlineData(BuildFlavor.Dev, new[] { "aday-sozcuk", "onayli-sozcuk" })]
    [InlineData(BuildFlavor.Internal, new[] { "aday-sozcuk", "onayli-sozcuk" })]
    [InlineData(BuildFlavor.Public, new[] { "onayli-sozcuk" })]
    public void Lugat_visibility_onayli_everywhere_aday_only_in_dev_and_internal_red_nowhere(BuildFlavor flavor, string[] expected)
    {
        EditorialSnapshot snapshot = WithLugat(Snapshot(), ThreeStates());

        PackContent index = Assemble(flavor, snapshot, "risale-dizin", out GateResult gate);

        Assert.Equal(expected, index.Lugat.Select(r => r.Basliksoz).Order(StringComparer.Ordinal));
        Assert.DoesNotContain(index.Lugat, r => r.Basliksoz == "red-sozcuk");
        PackLugatRow approved = index.Lugat.Single(r => r.Basliksoz == "onayli-sozcuk");
        Assert.Equal(("onayli", "Deneme tanimi 1", "editor", "2"), (approved.Status, approved.TanimTr, approved.Origin, approved.Version));
        Assert.All(index.Lugat, r => Assert.Equal(r.Basliksoz.StartsWith("onayli", StringComparison.Ordinal) ? "onayli" : "aday", r.Status));

        // Kapi raporu: P-09 satirlari lugat_madde etiketiyle sayilir.
        Assert.Contains(gate.Report.Rows, r => r.Kind == GateSubjectKind.Sozluk && r.Id == "lugat_madde" && r.Decision == GateDecision.Girdi && r.Reason == GateReasons.Uygun);
        Assert.Contains(gate.Report.Rows, r => r.Kind == GateSubjectKind.Sozluk && r.Id == "lugat_madde" && r.Decision == GateDecision.Girmedi && r.Rule == GateRule.P09 && r.Reason == GateReasons.Red);
        if (flavor == BuildFlavor.Public)
        {
            Assert.Contains(gate.Report.Rows, r => r.Kind == GateSubjectKind.Sozluk && r.Id == "lugat_madde" && r.Reason == GateReasons.AdayPublic);
            Assert.DoesNotContain(gate.Report.Rows, r => r.Id == "lugat_madde" && r.Reason == GateReasons.Aday);
        }
        else
        {
            Assert.Contains(gate.Report.Rows, r => r.Kind == GateSubjectKind.Sozluk && r.Id == "lugat_madde" && r.Reason == GateReasons.Aday && r.Decision == GateDecision.Girdi);
        }
    }

    [Fact]
    public void A_candidate_without_a_definition_is_visible_in_dev_with_status_aday_and_no_definition()
    {
        EditorialSnapshot snapshot = WithLugat(Snapshot(), [Madde(LugatSource, "aday-sozcuk", "aday")]);

        PackContent index = Assemble(BuildFlavor.Dev, snapshot, "risale-dizin");

        PackLugatRow row = Assert.Single(index.Lugat);
        Assert.Equal(("aday", null, "hat", "1", 1L), (row.Status, row.TanimTr, row.Origin, row.Version, row.Duzey));
        Assert.Equal(LugatMaddeHash("aday-sozcuk", null), row.ContentHash);
    }

    [Fact]
    public async Task The_written_index_file_holds_the_lugat_rows_with_a_candidate_marker_and_nothing_of_the_reference_data()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        using PackTestData.TempDir temp = new();
        EditorialSnapshot snapshot = WithLugat(Snapshot(), ThreeStates());

        PackFile dev = await Write(Assemble(BuildFlavor.Dev, snapshot, "risale-dizin"), snapshot, temp.Path, ct);

        Assert.True(dev.SelfCheck.Passed, dev.SelfCheck.ToJson());
        Assert.Contains(dev.SelfCheck.Items, i => i.Name == "lugat" && i.Passed && i.Detail.Contains("2 madde, 1 aday", StringComparison.Ordinal));
        using SqliteConnection connection = Open(dev.Path);
        Assert.Equal(
            ["basliksoz", "basliksoz_norm", "osmanlica_yazim", "koken_dil", "tanim_tr", "anlam_no", "kaynak", "duzey", "status", "origin", "version", "content_hash"],
            Strings(connection, "SELECT name FROM pragma_table_info('lugat') ORDER BY cid"));
        Assert.Equal(["basliksoz", "kaynak", "anlam_no"], Strings(connection, "SELECT name FROM pragma_table_info('lugat') WHERE pk > 0 ORDER BY pk"));
        Assert.Equal(
            ["aday-sozcuk|aday|hat|1|", "onayli-sozcuk|onayli|editor|2|Deneme tanimi 1"],
            Strings(connection, "SELECT basliksoz || '|' || status || '|' || origin || '|' || version || '|' || coalesce(tanim_tr, '') FROM lugat ORDER BY basliksoz"));

        // basliksoz_norm uzerinde (tekil olmayan) dizin var.
        Assert.Equal(["lugat_norm|0"], Strings(connection, "SELECT name || '|' || \"unique\" FROM pragma_index_list('lugat') WHERE origin = 'c'"));
        Assert.Equal(["basliksoz_norm"], Strings(connection, "SELECT name FROM pragma_index_info('lugat_norm')"));

        // Lugat kaynagi satir verdigi icin kunye ve atif listelenir (P-01, P-11).
        Assert.Contains(LugatSource, Strings(connection, "SELECT source_id FROM pack_source"));
        Assert.Contains(LugatSource, Strings(connection, "SELECT source_id FROM attribution"));

        // unit_count lugat'tan etkilenmez.
        Assert.Equal(["4"], Strings(connection, "SELECT value FROM pack_meta WHERE key = 'unit_count'"));
    }

    [Fact]
    public async Task The_public_index_file_has_no_candidate_rows_and_the_self_check_catches_one_added_by_hand()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        using PackTestData.TempDir temp = new();
        EditorialSnapshot snapshot = WithLugat(Snapshot(), ThreeStates());

        PackFile publicIndex = await Write(Assemble(BuildFlavor.Public, snapshot, "risale-dizin"), snapshot, temp.Path, ct);

        Assert.True(publicIndex.SelfCheck.Passed, publicIndex.SelfCheck.ToJson());
        using SqliteConnection writable = Open(publicIndex.Path, readOnly: false);
        Assert.Equal(["onayli"], Strings(writable, "SELECT DISTINCT status FROM lugat"));
        Assert.Empty(Strings(writable, "SELECT basliksoz FROM lugat WHERE status = 'aday'"));

        using (SqliteCommand insert = writable.CreateCommand())
        {
            insert.CommandText = "INSERT INTO lugat(basliksoz, basliksoz_norm, anlam_no, kaynak, duzey, status, origin, version, content_hash) VALUES ('elle-aday', 'elle-aday', 1, 'deneme-kaynak', 1, 'aday', 'hat', '1', $h)";
            insert.Parameters.AddWithValue("$h", new string('a', 64));
            insert.ExecuteNonQuery();
        }

        PackDefinitions definitions = PackTestData.Definitions();
        PackSelfCheckExpectations expectations = new(
            "risale-dizin",
            "2026.11.0",
            definitions.ExpectedTables(definitions.Resolve("risale-dizin")),
            new Dictionary<string, string>(),
            []);
        PackSelfCheckReport report = PackSelfCheck.Run(writable, expectations);
        Assert.Contains(report.Items, i => i.Name == "lugat" && !i.Passed && i.Detail.Contains("public-aday:1", StringComparison.Ordinal));
    }

    [Fact]
    public void A_test_prefixed_lugat_source_never_enters_public_or_internal_but_is_visible_in_dev()
    {
        EditorialSnapshot snapshot = WithLugat(
            Snapshot(),
            [
                Madde(LugatSource, "gercek-onayli", "onayli", "Deneme tanimi"),
                Madde(LugatFixtureSource, "deneme-fikstur", "onayli", "Deneme fikstur tanimi"),
                Madde(LugatFixtureSource, "deneme-fikstur-aday", "aday"),
            ]);

        string[] Words(BuildFlavor flavor) => [.. Assemble(flavor, snapshot, "risale-dizin").Lugat.Select(r => r.Basliksoz).Order(StringComparer.Ordinal)];

        Assert.Equal(["deneme-fikstur", "deneme-fikstur-aday", "gercek-onayli"], Words(BuildFlavor.Dev));

        // Fikstur kaynagi hem birim hem lugat kaynagidir ama pack_source ve atif satiri tekildir (iki baglama yazilmaz).
        PackContent dev = Assemble(BuildFlavor.Dev, snapshot, "risale-dizin");
        Assert.Single(dev.PackSources, s => s.SourceId == LugatFixtureSource);
        Assert.Single(dev.Attributions, a => a.SourceId == LugatFixtureSource);

        // P-12: internal'a yalniz test-kucuk ve test-ses girer; public'e hicbir test- kaynagi girmez.
        Assert.Equal(["gercek-onayli"], Words(BuildFlavor.Internal));
        Assert.Equal(["gercek-onayli"], Words(BuildFlavor.Public));
        GateResult publicGate = PackTestData.Evaluate(BuildFlavor.Public, snapshot, Catalog);
        Assert.Contains(publicGate.Report.Rows, r => r.Kind == GateSubjectKind.Kaynak && r.Id == LugatFixtureSource && r.Rule == GateRule.P12);
    }

    [Fact]
    public void An_unregistered_lugat_source_is_rejected_by_p01_and_its_rows_do_not_enter()
    {
        EditorialSnapshot snapshot = WithLugat(Snapshot(), ThreeStates());
        GateResult gate = PackTestData.Evaluate(BuildFlavor.Dev, snapshot, Catalog, fileExists: path => !path.Contains(LugatSource, StringComparison.Ordinal));

        PackContent index = PackAssembler.Assemble(Catalog.Get("risale-dizin"), BuildFlavor.Dev, snapshot, gate, Catalog);

        Assert.Empty(index.Lugat);
        Assert.DoesNotContain(index.PackSources, s => s.SourceId == LugatSource);
        Assert.Contains(gate.Report.Rows, r => r.Kind == GateSubjectKind.Kaynak && r.Id == LugatSource && r.Rule == GateRule.P01);
    }

    [Fact]
    public void Lugat_alone_does_not_make_the_index_a_candidate_and_other_packs_carry_no_lugat()
    {
        EditorialSnapshot textless = WithLugat(PackTestData.Snapshot(), ThreeStates());

        GateResult gate = PackTestData.Evaluate(BuildFlavor.Dev, textless, Catalog);

        Assert.DoesNotContain("risale-dizin", gate.IncludedPacks);
        Assert.Contains(gate.Report.Rows, r => r.Kind == GateSubjectKind.Paket && r.Id == "risale-dizin" && r.Reason == GateReasons.IcerikYok);

        EditorialSnapshot snapshot = WithLugat(Snapshot(), ThreeStates());
        Assert.Empty(Assemble(BuildFlavor.Dev, snapshot, "risale-sozler").Lugat);
        Assert.Empty(Assemble(BuildFlavor.Dev, snapshot, "core").Lugat);
    }

    [Fact]
    public void An_approved_madde_without_a_definition_and_the_same_key_twice_are_inconsistent_input()
    {
        EditorialSnapshot blank = WithLugat(Snapshot(), [Madde(LugatSource, "onayli-bos", "onayli", "   ")]);
        PackAssemblyException emptyDefinition = Assert.Throws<PackAssemblyException>(() => Assemble(BuildFlavor.Dev, blank, "risale-dizin"));
        Assert.Contains("tanimi bos", emptyDefinition.Message, StringComparison.Ordinal);

        // Ayni (kaynak, basliksoz, anlam_no) iki kez gelirse hata kalir.
        EditorialSnapshot duplicate = WithLugat(
            Snapshot(),
            [Madde(LugatSource, "ayni-sozcuk", "aday"), Madde(LugatSource, "ayni-sozcuk", "aday")]);
        PackAssemblyException twice = Assert.Throws<PackAssemblyException>(() => Assemble(BuildFlavor.Dev, duplicate, "risale-dizin"));
        Assert.Contains("ayni anahtarla iki kez", twice.Message, StringComparison.Ordinal);
    }

    [Fact]
    public void The_same_headword_may_come_from_two_sources_and_as_several_meanings()
    {
        EditorialSnapshot snapshot = WithLugat(
            Snapshot(),
            [
                Madde(LugatRnkSource, "ayni-sozcuk", "onayli", "RNK birinci anlam", origin: "kaynak", anlamNo: 1),
                Madde(LugatRnkSource, "ayni-sozcuk", "onayli", "RNK ikinci anlam", origin: "kaynak", anlamNo: 2),
                Madde(LugatSozlukSource, "ayni-sozcuk", "onayli", "Sozluk anlami", origin: "kaynak", anlamNo: 1),
            ]);

        PackContent index = Assemble(BuildFlavor.Dev, snapshot, "risale-dizin");

        Assert.Equal(
            [("ayni-sozcuk", LugatRnkSource, 1L), ("ayni-sozcuk", LugatRnkSource, 2L), ("ayni-sozcuk", LugatSozlukSource, 1L)],
            index.Lugat.Select(r => (r.Basliksoz, r.Kaynak, r.AnlamNo)).Order());
        Assert.Contains(index.PackSources, s => s.SourceId == LugatRnkSource);
        Assert.Contains(index.PackSources, s => s.SourceId == LugatSozlukSource);
        Assert.Contains(index.Attributions, a => a.SourceId == LugatRnkSource);
        Assert.Contains(index.Attributions, a => a.SourceId == LugatSozlukSource);
    }

    [Theory]
    [InlineData(BuildFlavor.Dev, true)]
    [InlineData(BuildFlavor.Internal, true)]
    [InlineData(BuildFlavor.Public, false)]
    public void A_source_candidate_follows_the_candidate_rule_with_its_definition_and_origin_kept_byte_for_byte(BuildFlavor flavor, bool visible)
    {
        // Kaynak tanimi NFC'ye uymaz (birlesik vurgu); pakete aynen yazilir.
        string definition = "café kaynak tanimi";
        EditorialSnapshot snapshot = WithLugat(Snapshot(), [Madde(LugatRnkSource, "kaynakli-sozcuk", "aday", definition, origin: "kaynak")]);

        PackContent index = Assemble(flavor, snapshot, "risale-dizin");

        if (!visible)
        {
            Assert.Empty(index.Lugat);
            return;
        }

        PackLugatRow row = Assert.Single(index.Lugat);
        Assert.Equal(("aday", "kaynak", definition, LugatRnkSource), (row.Status, row.Origin, row.TanimTr, row.Kaynak));
    }

    [Theory]
    [InlineData(BuildFlavor.Dev)]
    [InlineData(BuildFlavor.Internal)]
    [InlineData(BuildFlavor.Public)]
    public void An_approved_source_row_enters_every_flavor_and_a_red_one_none(BuildFlavor flavor)
    {
        EditorialSnapshot snapshot = WithLugat(
            Snapshot(),
            [
                Madde(LugatRnkSource, "onayli-sozcuk", "onayli", "Onayli kaynak tanimi", origin: "kaynak", version: "2"),
                Madde(LugatRnkSource, "red-sozcuk", "red", "Reddedilen kaynak tanimi", origin: "kaynak"),
            ]);

        PackContent index = Assemble(flavor, snapshot, "risale-dizin");

        PackLugatRow row = Assert.Single(index.Lugat);
        Assert.Equal(("onayli-sozcuk", "onayli", "kaynak", "2"), (row.Basliksoz, row.Status, row.Origin, row.Version));
    }

    [Fact]
    public void A_definitionless_candidate_is_dropped_when_a_defined_row_shares_its_normalized_headword()
    {
        EditorialSnapshot snapshot = WithLugat(
            Snapshot(),
            [
                Madde(LugatSource, "Deneme-Sozcuk", "aday", norm: "deneme-sozcuk"), // tanimsiz Kelime-Frekans adayi
                Madde(LugatRnkSource, "deneme-sozcuk", "aday", "Kaynak tanimi", origin: "kaynak", norm: "deneme-sozcuk"),
                Madde(LugatSource, "yalniz-sozcuk", "aday", norm: "yalniz-sozcuk"), // cakisan tanimli madde yok: kalir
            ]);

        PackContent dev = Assemble(BuildFlavor.Dev, snapshot, "risale-dizin");

        Assert.Equal(["deneme-sozcuk", "yalniz-sozcuk"], dev.Lugat.Select(r => r.Basliksoz).Order(StringComparer.Ordinal));
        Assert.DoesNotContain(dev.Lugat, r => r.Basliksoz == "Deneme-Sozcuk");

        // Public'te aday yoktur: ne tanimli ne tanimsiz aday girer.
        Assert.Empty(Assemble(BuildFlavor.Public, snapshot, "risale-dizin").Lugat);
    }

    [Fact]
    public void A_definitionless_candidate_stays_when_the_defined_row_with_the_same_norm_is_not_in_the_pack()
    {
        // Tanimli madde reddedilmis: pakete girmez, bu yuzden tanimsiz adayi golgelemez.
        EditorialSnapshot snapshot = WithLugat(
            Snapshot(),
            [
                Madde(LugatSource, "tanimsiz-sozcuk", "aday", norm: "ortak-norm"),
                Madde(LugatRnkSource, "tanimli-sozcuk", "red", "Kaynak tanimi", origin: "kaynak", norm: "ortak-norm"),
            ]);

        PackContent dev = Assemble(BuildFlavor.Dev, snapshot, "risale-dizin");

        Assert.Equal(["tanimsiz-sozcuk"], dev.Lugat.Select(r => r.Basliksoz));
    }

    [Fact]
    public void A_dropped_definitionless_candidate_does_not_list_its_source_but_the_defined_rows_source_is_listed()
    {
        EditorialSnapshot snapshot = WithLugat(
            Snapshot(),
            [
                Madde(LugatSource, "deneme-sozcuk", "aday"),
                Madde(LugatRnkSource, "deneme-sozcuk", "aday", "Kaynak tanimi", origin: "kaynak"),
            ]);

        PackContent dev = Assemble(BuildFlavor.Dev, snapshot, "risale-dizin");

        Assert.DoesNotContain(dev.PackSources, s => s.SourceId == LugatSource);
        Assert.Contains(dev.PackSources, s => s.SourceId == LugatRnkSource);
    }

    [Fact]
    public void The_three_lugat_sources_are_bound_as_glossary_sources_of_the_index_pack()
    {
        PackDefinition index = Catalog.Get("risale-dizin");

        foreach (string slug in new[] { LugatSource, LugatRnkSource, LugatSozlukSource })
        {
            PackSourceBinding binding = Assert.Single(index.Sources, b => b.Slug == slug);
            Assert.Equal(PackSourceRole.Glossary, binding.Role);
            Assert.False(binding.Required);
        }
    }

    [Fact]
    public async Task The_self_check_catches_a_definitionless_row_that_shares_a_norm_with_a_defined_row()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        using PackTestData.TempDir temp = new();
        EditorialSnapshot snapshot = WithLugat(Snapshot(), [Madde(LugatRnkSource, "deneme-sozcuk", "aday", "Kaynak tanimi", origin: "kaynak")]);
        PackFile dev = await Write(Assemble(BuildFlavor.Dev, snapshot, "risale-dizin"), snapshot, temp.Path, ct);
        using SqliteConnection writable = Open(dev.Path, readOnly: false);
        using (SqliteCommand insert = writable.CreateCommand())
        {
            insert.CommandText = "INSERT INTO lugat(basliksoz, basliksoz_norm, anlam_no, kaynak, duzey, status, origin, version, content_hash) VALUES ('golge', 'deneme-sozcuk', 1, 'x', 1, 'aday', 'hat', '1', $h)";
            insert.Parameters.AddWithValue("$h", new string('a', 64));
            insert.ExecuteNonQuery();
        }

        PackDefinitions definitions = PackTestData.Definitions();
        PackSelfCheckReport report = PackSelfCheck.Run(
            writable,
            new PackSelfCheckExpectations("risale-dizin", "2026.11.0", definitions.ExpectedTables(definitions.Resolve("risale-dizin")), new Dictionary<string, string>(), []));

        Assert.Contains(report.Items, i => i.Name == "lugat" && !i.Passed && i.Detail.Contains("tanimsiz-ve-tanimli-ayni-norm:1", StringComparison.Ordinal));
    }

    [Fact]
    public async Task An_approved_row_without_a_definition_violates_the_pack_check_constraint_when_written()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        using PackTestData.TempDir temp = new();
        EditorialSnapshot snapshot = WithLugat(Snapshot(), [Madde(LugatSource, "aday-sozcuk", "aday")]);
        PackContent content = Assemble(BuildFlavor.Dev, snapshot, "risale-dizin");
        PackContent broken = new()
        {
            PackId = content.PackId,
            Flavor = content.Flavor,
            PackSources = content.PackSources,
            Attributions = content.Attributions,
            Units = content.Units,
            UnitRefs = content.UnitRefs,
            UnitSearch = content.UnitSearch,
            Xrefs = content.Xrefs,
            PageMaps = content.PageMaps,
            Lugat = [.. content.Lugat.Select(r => r with { Status = "onayli", TanimTr = null })],
        };

        await Assert.ThrowsAsync<PackWriteException>(() => Write(broken, snapshot, temp.Path, ct));
    }

    [Fact]
    public void The_pack_digest_is_stable_across_input_order_and_changes_with_the_status_the_definition_and_the_flavor()
    {
        LugatMaddeRow[] rows = ThreeStates();
        string baseline = PackDigest.Compute(Assemble(BuildFlavor.Dev, WithLugat(Snapshot(), rows), "risale-dizin"));

        Assert.Equal(baseline, PackDigest.Compute(Assemble(BuildFlavor.Dev, WithLugat(Snapshot(), [.. rows.Reverse()]), "risale-dizin")));

        LugatMaddeRow[] edited = [rows[0] with { TanimTr = "Baska tanim" }, rows[1], rows[2]];
        Assert.NotEqual(baseline, PackDigest.Compute(Assemble(BuildFlavor.Dev, WithLugat(Snapshot(), edited), "risale-dizin")));

        LugatMaddeRow[] approvedNow = [rows[0], rows[1] with { Status = "onayli", TanimTr = "Yeni tanim", Origin = "editor", Version = "2" }, rows[2]];
        Assert.NotEqual(baseline, PackDigest.Compute(Assemble(BuildFlavor.Dev, WithLugat(Snapshot(), approvedNow), "risale-dizin")));

        Assert.NotEqual(baseline, PackDigest.Compute(Assemble(BuildFlavor.Public, WithLugat(Snapshot(), rows), "risale-dizin")));

        // Lugat satiri olmayan dizinin ozeti degismez (tablo satirsiz).
        Assert.Equal(
            PackDigest.Compute(Assemble(BuildFlavor.Dev, Snapshot(), "risale-dizin")),
            PackDigest.Compute(Assemble(BuildFlavor.Dev, WithLugat(Snapshot(), []), "risale-dizin")));
    }

    [Fact]
    public void The_source_digest_of_the_lugat_source_covers_every_state_and_changes_on_approval()
    {
        LugatMaddeRow[] rows = ThreeStates();
        string Digest(LugatMaddeRow[] data) => SourceDigests.Compute(WithLugat(Snapshot(), data), [LugatSource])[LugatSource];

        string baseline = Digest(rows);

        Assert.Equal(baseline, Digest([.. rows.Reverse()]));
        Assert.NotEqual(baseline, Digest([rows[0], rows[1] with { Status = "onayli", TanimTr = "Yeni tanim", Origin = "editor", Version = "2" }, rows[2]]));
        Assert.NotEqual(baseline, Digest([rows[0], rows[1], rows[2] with { Status = "aday" }]));
        Assert.NotEqual(baseline, Digest([rows[0], rows[1]]));
    }
}
