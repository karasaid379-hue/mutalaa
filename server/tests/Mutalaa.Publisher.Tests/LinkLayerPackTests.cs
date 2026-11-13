using System.Globalization;
using Microsoft.Data.Sqlite;
using Mutalaa.Domain.Links;
using Mutalaa.Domain.Releases;
using Mutalaa.Domain.Releases.Gate;
using Mutalaa.Domain.Text;
using Mutalaa.Infrastructure.Packs;
using Mutalaa.Infrastructure.Releases;
using Mutalaa.Publisher.Tests.Support;

namespace Mutalaa.Publisher.Tests;

/// <summary>
/// A18.6 (K-51): baglanti ve Turkce kok verisinin pakete girmesi. kelime-kok'te Turkce lemma (approval editor | auto), tr_root_index, tr_form ve xref_idx;
/// core'da benzer_ayet; pack_meta gate_summary; tur kapisi (xref_gate) ve ozet kosullari. Sentetik veri: Turkce kelimeler "deneme-N", kok harfleri uydurma
/// harf dizisi, meal metni "Deneme paragrafi N"; gercek Kur'an, meal ya da lugat verisi yoktur. Docker gerektirmez.
/// </summary>
public class LinkLayerPackTests
{
    private const string Qac = PackCatalog.QacMorphologySlug;
    private const string TrSource = PackCatalog.TrLemmaSourceSlug;
    private const string Qursim = PackCatalog.QursimSlug;
    private const string Meal = "elmalili-meal";
    private const string MealAnchor = "meal:elmalili:1:1";

    private static readonly string MealText = "Deneme paragrafi 7";
    private static readonly string MealHash = ContentHash.Compute(MealText)[..16];
    private const string StaleHash = "0123456789abcdef";

    private static readonly Guid KokId = new("0190c000-0000-7000-8000-000000000001");
    private static readonly Guid LemmaXrefId = new("0190c000-0000-7000-8000-000000000002");
    private static readonly Guid SimilarId = new("0190c000-0000-7000-8000-000000000003");
    private static readonly Guid KokApprovedId = new("0190c000-0000-7000-8000-000000000004");
    private static readonly Guid SimilarStaleId = new("0190c000-0000-7000-8000-000000000005");

    private static string Hash16(string text) => ContentHash.Compute(text)[..16];

    private static EditorialSnapshot Snapshot(
        IReadOnlyList<XrefGateRow>? gates = null,
        IReadOnlyList<TrLemmaRow>? lemmas = null,
        IReadOnlyList<TrRootIndexRow>? index = null,
        IReadOnlyList<TrFormRow>? forms = null,
        IReadOnlyList<XrefRow>? xrefs = null)
    {
        EditorialSnapshot basis = PackTestData.Snapshot();
        string ayah1 = Hash16("Deneme paragrafi 1");
        string ayah2 = Hash16("Deneme paragrafi 2");

        return new EditorialSnapshot
        {
            Sources =
            [
                .. basis.Sources,
                PackTestData.Source(Qac, "morfoloji", atifMetni: "Sentetik QAC atfi", baslik: "QAC deneme", surum: "0.4"),
                PackTestData.Source(TrSource, "sozluk", atifMetni: "Sentetik sozluk atfi", baslik: "Sozluk deneme"),
                PackTestData.Source(Qursim, "baglanti_verisi", atifMetni: "Sentetik cift listesi atfi", baslik: "Cift listesi deneme"),
                PackTestData.Source(Meal, "meal"),
            ],
            Units = [.. basis.Units, PackTestData.Unit(MealAnchor, Meal, "meal", MealText, durum: "onayli", ord: 1)],
            QuranWords = basis.QuranWords,
            QuranMarkers = basis.QuranMarkers,
            PageMaps = basis.PageMaps,
            Xrefs = xrefs ??
            [
                .. basis.Xrefs,
                PackTestData.Xref("q:1:1", "q:1:2", "kok", "aday", confidence: 0.9f, id: KokId, srcHash: ayah1, dstHash: ayah2, evidenceSource: Qac),
                PackTestData.Xref("q:1:1", "q:1:2", "lemma", "aday", confidence: 0.8f, id: LemmaXrefId, srcHash: ayah1, dstHash: ayah2),
                PackTestData.Xref("q:1:1", "q:1:2", "kok", "onayli", confidence: 0.8f, id: KokApprovedId),
                PackTestData.Xref("q:1:2", "q:1:1", "benzer_ayet", "aday", confidence: 0.9f, id: SimilarId, srcHash: ayah2, dstHash: ayah1, evidenceSource: Qursim),
                PackTestData.Xref("q:1:1", "q:1:2", "benzer_ayet", "aday", confidence: 0.9f, id: SimilarStaleId, srcHash: StaleHash, dstHash: ayah2),
            ],
            Roots = [new RootRow(1, "بتث", 3, 2, 0.7f, null, Qac)],
            Lemmas = [new LemmaRow(1, "بتث", "بتث", 1, 3, null, false, "onayli", Qac)],
            TrLemmas = lemmas ?? DefaultLemmas(),
            TrRootIndex = index ?? DefaultIndex(),
            TrForms = forms ?? DefaultForms(),
            XrefGates = gates ?? [],
        };
    }

    private static TrLemmaRow Lemma(int id, string status, string? path, bool kanit, int? freq = 5, string source = TrSource) =>
        new(id, "deneme-" + id.ToString(CultureInfo.InvariantCulture), "deneme-" + id.ToString(CultureInfo.InvariantCulture), 1, 0, null, false, freq, status, path, kanit, "kaikki", source, "dv-1");

    private static List<TrLemmaRow> DefaultLemmas() =>
    [
        Lemma(100, "onayli", "otomatik", true, freq: 9),
        Lemma(101, "onayli", "editor", false, freq: null),
        Lemma(102, "aday", null, false),
        Lemma(103, "onayli", "otomatik", false),
    ];

    private static List<TrRootIndexRow> DefaultIndex() =>
    [
        new(MealAnchor, 0, 4, 1, 100, false, MealHash, "dv-1"),
        new(MealAnchor, 5, 9, 1, 101, true, MealHash, "dv-1"),
        new(MealAnchor, 10, 14, 1, 102, false, MealHash, "dv-1"),
        new(MealAnchor, 15, 19, 1, 103, false, MealHash, "dv-1"),
        new(MealAnchor, 20, 24, 1, 101, false, StaleHash, "dv-1"),
    ];

    private static List<TrFormRow> DefaultForms() =>
    [
        new("deneme", "deneme", 100, 3, "dv-1"),
        new("deneme", "deneme", 101, 2, "dv-1"),
        new("baska", "baska", 102, 1, "dv-1"),
    ];

    private static XrefGateRow Gate(string tur, string setClass, string result) =>
        new(tur, setClass, result, "s1", ["kaynak@1"], new string('a', 64), new DateTime(2026, 11, 13, 0, 0, 0, DateTimeKind.Utc));

    private static PackContent Assemble(BuildFlavor flavor, EditorialSnapshot snapshot, string packId)
    {
        PackCatalog catalog = PackCatalog.Default;
        GateResult gate = PackTestData.Evaluate(flavor, snapshot, catalog);
        return PackAssembler.Assemble(catalog.Get(packId), flavor, snapshot, gate, catalog);
    }

    // ---- xref_idx dagilimi ----

    [Fact]
    public void Dev_writes_kok_and_lemma_links_to_kelime_kok_and_benzer_ayet_to_core()
    {
        EditorialSnapshot snapshot = Snapshot();

        PackContent kelimeKok = Assemble(BuildFlavor.Dev, snapshot, "kelime-kok");
        PackContent core = Assemble(BuildFlavor.Dev, snapshot, "core");

        Assert.Equal(
            new[] { KokId, LemmaXrefId, KokApprovedId }.Select(Id).Order(StringComparer.Ordinal),
            kelimeKok.Xrefs.Select(x => x.Id).Order(StringComparer.Ordinal));
        Assert.All(kelimeKok.Xrefs, x => Assert.Contains(x.Type, new[] { "kok", "lemma" }));

        // core: benzer_ayet (onayli ozet-siz, aday ozetli); ozeti tutmayan satir (StaleHash) girmez.
        Assert.Equal(
            new[] { PackTestData.XrefCore, SimilarId }.Select(Id).Order(StringComparer.Ordinal),
            core.Xrefs.Select(x => x.Id).Order(StringComparer.Ordinal));
        Assert.DoesNotContain(core.Xrefs, x => x.Id == Id(SimilarStaleId));
        Assert.DoesNotContain(core.Xrefs, x => x.Type is "kok" or "lemma");
    }

    [Fact]
    public void Public_without_gate_rows_keeps_automatic_candidates_out_and_the_approved_row_in()
    {
        EditorialSnapshot snapshot = Snapshot();

        PackContent kelimeKok = Assemble(BuildFlavor.Public, snapshot, "kelime-kok");
        PackContent core = Assemble(BuildFlavor.Public, snapshot, "core");

        Assert.Equal([Id(KokApprovedId)], kelimeKok.Xrefs.Select(x => x.Id));
        Assert.DoesNotContain(core.Xrefs, x => x.Id == Id(SimilarId));
        Assert.Contains(core.Xrefs, x => x.Id == Id(PackTestData.XrefCore));
    }

    [Fact]
    public void Public_with_a_silver_gate_lets_that_types_candidates_in_and_only_that_type()
    {
        EditorialSnapshot snapshot = Snapshot([Gate("kok", "silver", "gecti"), Gate("benzer_ayet", "silver", "kaldi"), Gate("lemma", "sentetik", "gecti")]);

        PackContent kelimeKok = Assemble(BuildFlavor.Public, snapshot, "kelime-kok");
        PackContent core = Assemble(BuildFlavor.Public, snapshot, "core");

        Assert.Equal(new[] { KokId, KokApprovedId }.Select(Id).Order(StringComparer.Ordinal), kelimeKok.Xrefs.Select(x => x.Id).Order(StringComparer.Ordinal));
        Assert.DoesNotContain(core.Xrefs, x => x.Id == Id(SimilarId));
    }

    [Fact]
    public void Public_with_gold_and_silver_gates_open_admits_the_candidates_and_the_end_hash_still_applies()
    {
        EditorialSnapshot snapshot = Snapshot([Gate("kok", "altin", "gecti"), Gate("lemma", "silver", "gecti"), Gate("benzer_ayet", "silver", "gecti")]);

        PackContent kelimeKok = Assemble(BuildFlavor.Public, snapshot, "kelime-kok");
        PackContent core = Assemble(BuildFlavor.Public, snapshot, "core");

        Assert.Equal(new[] { KokId, LemmaXrefId, KokApprovedId }.Select(Id).Order(StringComparer.Ordinal), kelimeKok.Xrefs.Select(x => x.Id).Order(StringComparer.Ordinal));
        Assert.Contains(core.Xrefs, x => x.Id == Id(SimilarId));
        Assert.DoesNotContain(core.Xrefs, x => x.Id == Id(SimilarStaleId));
    }

    [Fact]
    public void An_evidence_source_bound_as_attribution_is_listed_only_when_its_rows_are_in_the_pack()
    {
        EditorialSnapshot snapshot = Snapshot();

        PackContent devCore = Assemble(BuildFlavor.Dev, snapshot, "core");
        PackContent publicCore = Assemble(BuildFlavor.Public, snapshot, "core");

        Assert.Contains(devCore.PackSources, s => s.SourceId == Qursim);
        Assert.Contains(devCore.Attributions, a => a.SourceId == Qursim && a.RequiredCredit == "Sentetik cift listesi atfi");
        Assert.DoesNotContain(publicCore.PackSources, s => s.SourceId == Qursim);
    }

    // ---- Turkce lemma, tr_root_index, tr_form ----

    [Fact]
    public void Dev_writes_approved_turkish_lemmas_with_their_approval_path_and_freq_as_occurrences()
    {
        PackContent pack = Assemble(BuildFlavor.Dev, Snapshot(), "kelime-kok");

        PackLemmaRow[] turkish = [.. pack.Lemmas.Where(l => l.Lang == "tr").OrderBy(l => l.Id)];
        Assert.Equal([100L, 101L], turkish.Select(l => l.Id));
        Assert.Equal(["auto", "editor"], turkish.Select(l => l.Approval));
        // freq pakette occurrences olur (freq yoksa editoryal occurrences).
        Assert.Equal([9L, 0L], turkish.Select(l => l.Occurrences));
        Assert.Equal((1L, 0L), (turkish[0].RootId, turkish[0].EtymologicalOnly));
        Assert.Equal("deneme-100", turkish[0].Text);

        PackLemmaRow arabic = Assert.Single(pack.Lemmas, l => l.Lang == "ar");
        Assert.Equal("qac", arabic.Approval);
        Assert.Contains(pack.PackSources, s => s.SourceId == TrSource);
        Assert.Contains(pack.Attributions, a => a.SourceId == TrSource && a.RequiredCredit == "Sentetik sozluk atfi");
    }

    [Fact]
    public void Dev_writes_tr_root_index_and_tr_form_rows_of_included_lemmas_and_drops_stale_hash_rows()
    {
        PackContent pack = Assemble(BuildFlavor.Dev, Snapshot(), "kelime-kok");

        // 102 aday, 103 kanitsiz otomatik, 101'in StaleHash satiri (ozet tutmuyor): girmez.
        Assert.Equal([(MealAnchor, 0L, 100L), (MealAnchor, 5L, 101L)], pack.TrRootIndex.OrderBy(r => r.SpanStart).Select(r => (r.Anchor, r.SpanStart, r.TrLemmaId)));
        PackTrRootIndexRow editor = pack.TrRootIndex.Single(r => r.SpanStart == 5);
        Assert.Equal((9L, 1L, 1L), (editor.SpanEnd, editor.RootId, editor.EtymologicalOnly));
        Assert.Equal([100L, 101L], pack.TrForms.OrderBy(f => f.TrLemmaId).Select(f => f.TrLemmaId));
        Assert.All(pack.TrForms, f => Assert.Equal("deneme", f.KeyNarrow));
    }

    [Fact]
    public void Public_without_the_kok_gate_keeps_automatic_lemmas_and_their_rows_out_but_editor_lemmas_in()
    {
        PackContent pack = Assemble(BuildFlavor.Public, Snapshot(), "kelime-kok");

        Assert.Equal([101L], pack.Lemmas.Where(l => l.Lang == "tr").Select(l => l.Id));
        Assert.Equal([5L], pack.TrRootIndex.Select(r => r.SpanStart));
        Assert.Equal([101L], pack.TrForms.Select(f => f.TrLemmaId));
    }

    [Fact]
    public void Public_with_a_passed_kok_gate_admits_automatic_lemmas_but_a_failed_one_or_the_lemma_gate_alone_does_not()
    {
        PackContent opened = Assemble(BuildFlavor.Public, Snapshot([Gate("kok", "silver", "gecti")]), "kelime-kok");
        PackContent failed = Assemble(BuildFlavor.Public, Snapshot([Gate("kok", "silver", "kaldi")]), "kelime-kok");
        PackContent lemmaGate = Assemble(BuildFlavor.Public, Snapshot([Gate("lemma", "silver", "gecti")]), "kelime-kok");

        Assert.Equal([100L, 101L], opened.Lemmas.Where(l => l.Lang == "tr").Select(l => l.Id).Order());
        Assert.Equal([0L, 5L], opened.TrRootIndex.Select(r => r.SpanStart).Order());
        Assert.Equal([101L], failed.Lemmas.Where(l => l.Lang == "tr").Select(l => l.Id));
        Assert.Equal([101L], lemmaGate.Lemmas.Where(l => l.Lang == "tr").Select(l => l.Id));
    }

    [Fact]
    public void Without_turkish_rows_the_dictionary_source_is_not_listed_and_the_pack_keeps_its_arabic_rows()
    {
        PackContent pack = Assemble(BuildFlavor.Dev, Snapshot(lemmas: [], index: [], forms: []), "kelime-kok");

        Assert.DoesNotContain(pack.PackSources, s => s.SourceId == TrSource);
        Assert.DoesNotContain(pack.Attributions, a => a.SourceId == TrSource);
        Assert.Empty(pack.TrRootIndex);
        Assert.Empty(pack.TrForms);
        Assert.Equal(["ar"], pack.Lemmas.Select(l => l.Lang));
    }

    [Fact]
    public void A_turkish_lemma_whose_source_is_not_bound_to_the_pack_is_not_written()
    {
        EditorialSnapshot snapshot = Snapshot(lemmas: [Lemma(101, "onayli", "editor", false, source: "baska-kaynak")]);

        PackContent pack = Assemble(BuildFlavor.Dev, snapshot, "kelime-kok");

        Assert.DoesNotContain(pack.Lemmas, l => l.Lang == "tr");
        Assert.Empty(pack.TrRootIndex);
        Assert.Empty(pack.TrForms);
    }

    [Fact]
    public void A_meal_unit_outside_the_flavor_scope_takes_its_tr_root_index_rows_with_it()
    {
        EditorialSnapshot basis = Snapshot();
        EditorialSnapshot draft = new()
        {
            Sources = basis.Sources,
            Units = [.. basis.Units.Where(u => u.Anchor != MealAnchor), PackTestData.Unit(MealAnchor, Meal, "meal", MealText, durum: "taslak", ord: 1)],
            QuranWords = basis.QuranWords,
            QuranMarkers = basis.QuranMarkers,
            PageMaps = basis.PageMaps,
            Xrefs = basis.Xrefs,
            Roots = basis.Roots,
            Lemmas = basis.Lemmas,
            TrLemmas = basis.TrLemmas,
            TrRootIndex = basis.TrRootIndex,
            TrForms = basis.TrForms,
        };

        Assert.Equal(2, Assemble(BuildFlavor.Dev, draft, "kelime-kok").TrRootIndex.Count);
        Assert.Empty(Assemble(BuildFlavor.Public, draft, "kelime-kok").TrRootIndex);
    }

    // ---- gate_summary ----

    [Fact]
    public void Gate_summary_is_canonical_json_with_class_and_result_for_the_types_of_the_pack_only()
    {
        EditorialSnapshot snapshot = Snapshot(
        [
            Gate("kok", "silver", "gecti"),
            Gate("kok", "sentetik", "kaldi"),
            Gate("lemma", "altin", "kaldi"),
            Gate("lemma", "silver", "gecti"),
            Gate("benzer_ayet", "sentetik", "gecti"),
            Gate("atif", "silver", "gecti"),
        ]);

        Assert.Equal(
            "{\"kok\":{\"set_sinifi\":\"silver\",\"sonuc\":\"gecti\"},\"lemma\":{\"set_sinifi\":\"altin\",\"sonuc\":\"kaldi\"}}",
            Assemble(BuildFlavor.Public, snapshot, "kelime-kok").GateSummary);
        Assert.Equal("{}", Assemble(BuildFlavor.Public, snapshot, "core").GateSummary); // benzer_ayet yalniz sentetik: olculmemis
        Assert.Null(Assemble(BuildFlavor.Dev, snapshot, "test-kucuk").GateSummary);
        Assert.Equal(
            "{\"benzer_ayet\":{\"set_sinifi\":\"silver\",\"sonuc\":\"kaldi\"}}",
            Assemble(BuildFlavor.Dev, Snapshot([Gate("benzer_ayet", "silver", "kaldi")]), "core").GateSummary);
        Assert.Equal("{}", Assemble(BuildFlavor.Dev, Snapshot(), "kelime-kok").GateSummary);
    }

    [Fact]
    public void Gate_summary_enters_the_pack_digest_and_a_changed_gate_changes_the_digest()
    {
        string none = PackDigest.Compute(Assemble(BuildFlavor.Dev, Snapshot(), "kelime-kok"));
        string passed = PackDigest.Compute(Assemble(BuildFlavor.Dev, Snapshot([Gate("kok", "silver", "gecti")]), "kelime-kok"));
        string failed = PackDigest.Compute(Assemble(BuildFlavor.Dev, Snapshot([Gate("kok", "silver", "kaldi")]), "kelime-kok"));
        string again = PackDigest.Compute(Assemble(BuildFlavor.Dev, Snapshot([Gate("kok", "silver", "gecti")]), "kelime-kok"));

        Assert.NotEqual(none, passed);
        Assert.NotEqual(passed, failed);
        Assert.Equal(passed, again);
    }

    [Fact]
    public void Row_order_places_xref_idx_before_quran_word_and_the_kelime_kok_tables_after_tr_root_index()
    {
        PackContent pack = Assemble(BuildFlavor.Dev, Snapshot(), "kelime-kok");

        string[] tables = [.. PackRows.Enumerate(pack).Select(r => r.Table).Distinct(StringComparer.Ordinal)];

        Assert.Equal(["pack_source", "attribution", "xref_idx", "tr_root_index", "root", "lemma", "tr_form"], tables);
        Assert.Equal(["id", "lang", "text", "text_clean", "root_id", "occurrences", "ar_lemma_id", "etymological_only", "approval"], PackTables.Columns("lemma"));
    }

    // ---- yazici ----

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task The_writer_writes_kelime_kok_with_xref_idx_turkish_rows_approval_and_the_gate_summary_meta(bool turkish)
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        using PackTestData.TempDir dir = new();
        EditorialSnapshot snapshot = Snapshot([Gate("kok", "silver", "gecti")]);

        await StorageTestKit.RunAsync(turkish, async () =>
        {
            PackContent content = Assemble(BuildFlavor.Dev, snapshot, "kelime-kok");
            SqlitePackWriter writer = new(PackTestData.Definitions(), new FixedClock(new DateTimeOffset(2026, 11, 13, 9, 0, 0, TimeSpan.Zero)));

            PackFile file = await writer.WriteAsync(content, new PackWriteRequest(dir.Path, "2026.11.0", "2026.11.13-abcdef0", snapshot.Sources), ct);

            Assert.True(file.SelfCheck.Passed, file.SelfCheck.FailedNames);
            SqliteConnectionStringBuilder builder = new() { DataSource = file.Path, Pooling = false, Mode = SqliteOpenMode.ReadOnly };
            using SqliteConnection connection = new(builder.ConnectionString);
            connection.Open();

            Assert.Equal("{\"kok\":{\"set_sinifi\":\"silver\",\"sonuc\":\"gecti\"}}", Scalar(connection, "SELECT value FROM pack_meta WHERE key = 'gate_summary'"));
            Assert.Equal("gate_summary", PackMetaKeys.GateSummary);
            Assert.Equal("3", Scalar(connection, "SELECT count(*) FROM xref_idx"));
            Assert.Equal("auto", Scalar(connection, "SELECT approval FROM lemma WHERE id = 100"));
            Assert.Equal("editor", Scalar(connection, "SELECT approval FROM lemma WHERE id = 101"));
            Assert.Equal("qac", Scalar(connection, "SELECT approval FROM lemma WHERE id = 1"));
            Assert.Equal("2", Scalar(connection, "SELECT count(*) FROM tr_root_index"));
            Assert.Equal("2", Scalar(connection, "SELECT count(*) FROM tr_form"));
            // tr_root_index birincil anahtari (anchor, span_start): bosluksuz yazilabilir; ayni anchor'da iki satir.
            Assert.Equal("2", Scalar(connection, "SELECT count(*) FROM tr_root_index WHERE anchor = 'meal:elmalili:1:1'"));
            Assert.Equal("1", Scalar(connection, "SELECT count(*) FROM attribution WHERE source_id = 'kaikki-tr'"));
        });
    }

    [Fact]
    public async Task The_writer_writes_core_with_the_benzer_ayet_rows_and_the_gate_summary_meta()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        using PackTestData.TempDir dir = new();
        EditorialSnapshot snapshot = Snapshot([Gate("benzer_ayet", "silver", "gecti")]);
        PackContent content = Assemble(BuildFlavor.Public, snapshot, "core");
        SqlitePackWriter writer = new(PackTestData.Definitions(), new FixedClock(new DateTimeOffset(2026, 11, 13, 9, 0, 0, TimeSpan.Zero)));

        PackFile file = await writer.WriteAsync(content, new PackWriteRequest(dir.Path, "2026.11.0", "2026.11.13-abcdef0", snapshot.Sources), ct);

        Assert.True(file.SelfCheck.Passed, file.SelfCheck.FailedNames);
        SqliteConnectionStringBuilder builder = new() { DataSource = file.Path, Pooling = false, Mode = SqliteOpenMode.ReadOnly };
        using SqliteConnection connection = new(builder.ConnectionString);
        connection.Open();
        Assert.Equal("{\"benzer_ayet\":{\"set_sinifi\":\"silver\",\"sonuc\":\"gecti\"}}", Scalar(connection, "SELECT value FROM pack_meta WHERE key = 'gate_summary'"));
        Assert.Equal("2", Scalar(connection, "SELECT count(*) FROM xref_idx WHERE type = 'benzer_ayet'"));
        Assert.Equal("0", Scalar(connection, "SELECT count(*) FROM xref_idx WHERE type IN ('kok', 'lemma')"));
    }

    [Fact]
    public async Task Other_packs_carry_no_gate_summary_meta_key()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        using PackTestData.TempDir dir = new();
        SqlitePackWriter writer = new(PackTestData.Definitions(), new FixedClock(new DateTimeOffset(2026, 11, 13, 9, 0, 0, TimeSpan.Zero)));

        PackFile file = await writer.WriteAsync(PackTestData.SmallContent(), PackTestData.Request(dir.Path), ct);

        SqliteConnectionStringBuilder builder = new() { DataSource = file.Path, Pooling = false, Mode = SqliteOpenMode.ReadOnly };
        using SqliteConnection connection = new(builder.ConnectionString);
        connection.Open();
        Assert.Equal("0", Scalar(connection, "SELECT count(*) FROM pack_meta WHERE key = 'gate_summary'"));
    }

    private static string Id(Guid id) => id.ToString("D", CultureInfo.InvariantCulture);

    private static string Scalar(SqliteConnection connection, string sql)
    {
        using SqliteCommand command = connection.CreateCommand();
        command.CommandText = sql;
        return Convert.ToString(command.ExecuteScalar(), CultureInfo.InvariantCulture) ?? string.Empty;
    }
}
