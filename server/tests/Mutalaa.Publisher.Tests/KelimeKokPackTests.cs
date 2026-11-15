using System.Globalization;
using Microsoft.Data.Sqlite;
using Mutalaa.Domain.Releases;
using Mutalaa.Domain.Releases.Gate;
using Mutalaa.Infrastructure.Packs;
using Mutalaa.Infrastructure.Releases;
using Mutalaa.Publisher.Tests.Support;

namespace Mutalaa.Publisher.Tests;

/// <summary>
/// kelime-kok paketi (A17.7, K-50 madde 8 ve 9): kapi, birlestirici, kaynak ozeti, yazici ve kunye. Sentetik veri: kok ve lemma metni uydurma harf dizisi
/// (kod noktalariyla), anlamlar "Deneme anlam N"; gercek Kur'an kelimesi, kok, lemma ya da anlam yoktur. Docker gerektirmez.
/// </summary>
public class KelimeKokPackTests
{
    private const string Qac = PackCatalog.QacMorphologySlug;
    private const string Wbw = PackCatalog.GlossSourceSlug;
    private const string TestLexicon = "test-sozluk";

    private static readonly Guid FixPos = new("0190b000-0000-7000-8000-000000000001");
    private static readonly Guid FixRoot = new("0190b000-0000-7000-8000-000000000002");
    private static readonly Guid FixLemma = new("0190b000-0000-7000-8000-000000000003");
    private static readonly Guid FixFeatures = new("0190b000-0000-7000-8000-000000000004");
    private static readonly Guid FixCandidate = new("0190b000-0000-7000-8000-000000000005");
    private static readonly Guid FixRed = new("0190b000-0000-7000-8000-000000000006");

    /// <summary>
    /// Sozluk fiksturu. Kokler 1 ve 2 (qac), 9 (test-sozluk); lemmalar 1 ve 4 onayli (qac), 2 aday durumlu (qac; pakete girmez), 3 onayli ama test-sozluk kaynakli.
    /// Anlamlar: lemma 1 onayli, 4 aday, 2 aday (lemma onaysiz: pakete girmez), 3 aday (test kaynakli lemma: pakete girmez), 5 red. Kelimeler q:1:1:1, q:1:2:1 ve
    /// q:1:3:1 (taslak ayet) QAC sutunu tasir; q:1:1:2 tasimaz.
    /// </summary>
    private static EditorialSnapshot Snapshot(IReadOnlyList<QuranWordFixRow>? fixes = null, IReadOnlyList<LexicalRow>? lexicals = null, bool testSource = true)
    {
        EditorialSnapshot basis = PackTestData.Snapshot();
        List<SourceRow> sources =
        [
            .. basis.Sources,
            PackTestData.Source(Qac, "morfoloji", atifMetni: "Sentetik QAC atfi", baslik: "QAC deneme", surum: "0.4", atifUrl: "https://example.invalid/qac", notice: "Sentetik bildirim"),
            PackTestData.Source(Wbw, "kelime_anlami", atifMetni: "Sentetik anlam atfi", baslik: "Anlam deneme"),
        ];
        if (testSource)
        {
            sources.Add(PackTestData.Source(TestLexicon, "sozluk"));
        }

        QuranWordRow[] words =
        [
            Morph("q:1:1:1", 1, 1, 1, 1, 0, 6, rootId: 1, lemmaId: 1, pos: "V", features: "{\"b\": 2, \"a\": 1}"),
            new("q:1:1:2", 1, 1, 2, 1, PackTestData.SyntheticArabic, PackTestData.SyntheticArabic, 7, 13, "tanzil-uthmani"),
            Morph("q:1:2:1", 1, 2, 1, 2, 0, 6, rootId: 2, lemmaId: 4, pos: "N", features: null),
            Morph("q:1:3:1", 1, 3, 1, 3, 0, 6, rootId: 1, lemmaId: 1, pos: "V", features: null),
        ];

        return new EditorialSnapshot
        {
            Sources = sources,
            Units = basis.Units,
            QuranWords = words,
            QuranMarkers = basis.QuranMarkers,
            PageMaps = basis.PageMaps,
            Xrefs = [],
            Lexicals = lexicals ?? DefaultLexicals(fixes ?? []),
            Roots =
            [
                new RootRow(1, "بتث", 3, 2, 0.7f, null, Qac),
                new RootRow(2, "جحخ", 1, 1, null, "Deneme kok anlami", Qac),
                new RootRow(9, "دذر", 1, 1, null, null, TestLexicon),
            ],
            Lemmas =
            [
                new LemmaRow(1, "بتث", "بتث", 1, 3, null, false, "onayli", Qac),
                new LemmaRow(2, "جحخ", "جحخ", 2, 1, null, false, "aday", Qac),
                new LemmaRow(3, "دذر", "دذر", 9, 1, null, true, "onayli", TestLexicon),
                new LemmaRow(4, "جحخ", "جحخ", 2, 1, 1, true, "onayli", Qac),
            ],
            LemmaGlosses =
            [
                new LemmaGlossRow(1, "Deneme anlam 1", "[]", null, false, "onayli", "editor", "2"),
                new LemmaGlossRow(2, "Deneme anlam 2", "[]", null, false, "aday", "kaynak:quranwbw-tr", "1"),
                new LemmaGlossRow(3, "Deneme anlam 3", "[]", null, false, "aday", "kaynak:quranwbw-tr", "1"),
                new LemmaGlossRow(4, "Deneme anlam 4", "[\"deneme\"]", "deneme", true, "aday", "kaynak:quranwbw-tr", "1"),
                new LemmaGlossRow(5, "Deneme anlam 5", "[]", null, false, "red", "kaynak:quranwbw-tr", "1"),
            ],
            WordFixes = fixes ?? [],
        };
    }

    private static QuranWordRow Morph(string anchor, int surah, int ayah, int word, int index, int start, int end, int rootId, int lemmaId, string pos, string? features) =>
        new(anchor, surah, ayah, word, index, PackTestData.SyntheticArabic, PackTestData.SyntheticArabic, start, end, "tanzil-uthmani", rootId, lemmaId, pos, features, Qac);

    private static List<LexicalRow> DefaultLexicals(IReadOnlyList<QuranWordFixRow> fixes)
    {
        List<LexicalRow> rows =
        [
            new(LexicalKind.LemmaGloss, "1", "onayli", false),
            new(LexicalKind.LemmaGloss, "2", "aday", false),
            new(LexicalKind.LemmaGloss, "3", "aday", false),
            new(LexicalKind.LemmaGloss, "4", "aday", false),
            new(LexicalKind.LemmaGloss, "5", "red", false),
        ];
        rows.AddRange(fixes.Select(f => new LexicalRow(LexicalKind.QuranWordFix, f.Id.ToString("D", CultureInfo.InvariantCulture), f.Status, false)));
        return rows;
    }

    private static QuranWordFixRow Fix(Guid id, string anchor, string field, string value, string status = "onayli") => new(id, anchor, field, value, status);

    private static PackContent Assemble(BuildFlavor flavor, EditorialSnapshot snapshot, PackCatalog? catalog = null, string packId = "kelime-kok")
    {
        PackCatalog cat = catalog ?? PackCatalog.Default;
        GateResult gate = PackTestData.Evaluate(flavor, snapshot, cat);
        return PackAssembler.Assemble(cat.Get(packId), flavor, snapshot, gate, cat);
    }

    /// <summary>Ayni katalog, kelime-kok'a test-sozluk Dictionary baglantisi eklenmis (P-12 testi: test- onekli sozluk kaynagi).</summary>
    private static PackCatalog CatalogWithTestDictionary() => new(
    [
        .. PackCatalog.Default.All.Where(p => p.PackId != "kelime-kok"),
        PackCatalog.Default.Get("kelime-kok") with
        {
            Sources = [.. PackCatalog.Default.Get("kelime-kok").Sources, new PackSourceBinding(TestLexicon, PackSourceRole.Dictionary, Required: false)],
        },
    ]);

    // ---------------------------------------------------------------- birlestirici: sozluk tablolari

    [Fact]
    public void Dev_takes_approved_lemmas_roots_candidate_glosses_and_the_qac_base_without_fixes()
    {
        PackContent pack = Assemble(BuildFlavor.Dev, Snapshot());

        Assert.Equal("kelime-kok", pack.PackId);
        Assert.Equal([1L, 2L], pack.Roots.Select(r => r.Id).Order());
        PackRootRow root1 = pack.Roots.Single(r => r.Id == 1);
        Assert.Equal(("بتث", 3L, 2L, 0.7, (string?)null), (root1.Letters, root1.Occurrences, root1.AyahCount, root1.IdfQ, root1.KokAnlami));
        Assert.Equal("Deneme kok anlami", pack.Roots.Single(r => r.Id == 2).KokAnlami);

        // Yalniz lang = 'ar' ve onayli lemma, yalniz sozluk kaynagindan: 2 (aday durumlu) ve 3 (test-sozluk) yok.
        Assert.Equal([1L, 4L], pack.Lemmas.Select(l => l.Id).Order());
        Assert.All(pack.Lemmas, l => Assert.Equal("ar", l.Lang));
        PackLemmaRow lemma4 = pack.Lemmas.Single(l => l.Id == 4);
        Assert.Equal((2L, 1L, 1L, 1L), (lemma4.RootId, lemma4.Occurrences, lemma4.ArLemmaId, lemma4.EtymologicalOnly));

        Assert.Equal(["q:1:1:1", "q:1:2:1", "q:1:3:1"], pack.WordMorph.Select(w => w.Anchor).Order(StringComparer.Ordinal));
        PackWordMorphRow first = pack.WordMorph.Single(w => w.Anchor == "q:1:1:1");
        Assert.Equal((1L, 1L, "V", "{\"a\":1,\"b\":2}"), (first.RootId, first.LemmaId, first.Pos, first.Features));
        Assert.Null(pack.WordMorph.Single(w => w.Anchor == "q:1:2:1").Features);

        Assert.Equal(0, pack.WordFixCount);
        Assert.Empty(pack.Units);
        Assert.Empty(pack.TrForms);
        Assert.Empty(pack.TrRootIndex);
    }

    [Fact]
    public void Glosses_follow_the_flavor_and_an_unapproved_gloss_row_carries_status_aday_with_its_origin()
    {
        PackContent dev = Assemble(BuildFlavor.Dev, Snapshot());
        PackContent inner = Assemble(BuildFlavor.Internal, Snapshot());
        PackContent publicPack = Assemble(BuildFlavor.Public, Snapshot());

        // red (5), onaysiz lemmanin (2) ve test kaynakli lemmanin (3) anlami hicbir derlemede yok.
        Assert.Equal(
            [(1L, "onayli", "editor"), (4L, "aday", "kaynak:quranwbw-tr")],
            dev.LemmaGlosses.OrderBy(g => g.LemmaId).Select(g => (g.LemmaId, g.Status, g.Origin)));
        Assert.Equal(dev.LemmaGlosses.OrderBy(g => g.LemmaId), inner.LemmaGlosses.OrderBy(g => g.LemmaId));
        PackLemmaGlossRow candidate = dev.LemmaGlosses.Single(g => g.LemmaId == 4);
        Assert.Equal(("Deneme anlam 4", "[\"deneme\"]", "deneme", 1L), (candidate.AnlamKisa, candidate.KuranAnlamlari, candidate.TurkceEsKelime, candidate.YalnizcaEtimolojik));

        // public: yalniz onayli; aday anlam yok.
        Assert.Equal([1L], publicPack.LemmaGlosses.Select(g => g.LemmaId));
        Assert.DoesNotContain(publicPack.LemmaGlosses, g => g.Status == "aday");
    }

    [Fact]
    public void Public_drops_the_word_whose_ayah_unit_is_unapproved_but_dev_keeps_it()
    {
        PackContent dev = Assemble(BuildFlavor.Dev, Snapshot());
        PackContent publicPack = Assemble(BuildFlavor.Public, Snapshot());

        Assert.Contains(dev.WordMorph, w => w.Anchor == "q:1:3:1");
        Assert.DoesNotContain(publicPack.WordMorph, w => w.Anchor == "q:1:3:1");
        Assert.Equal(["q:1:1:1", "q:1:2:1"], publicPack.WordMorph.Select(w => w.Anchor).Order(StringComparer.Ordinal));
    }

    // ---------------------------------------------------------------- onayli duzeltmeler

    [Fact]
    public void Approved_fixes_are_applied_per_field_with_type_conversion_and_counted_in_the_hallmark()
    {
        QuranWordFixRow[] fixes =
        [
            Fix(FixPos, "q:1:1:1", "pos", "N"),
            Fix(FixRoot, "q:1:2:1", "root_id", "1"),
            Fix(FixLemma, "q:1:3:1", "lemma_id", "4"),
            Fix(FixFeatures, "q:1:1:1", "features", "{\"z\": 1,   \"y\": [2]}"),
        ];

        foreach (BuildFlavor flavor in Enum.GetValues<BuildFlavor>())
        {
            EditorialSnapshot snapshot = Snapshot(fixes);
            PackContent pack = Assemble(flavor, snapshot);

            PackWordMorphRow w1 = pack.WordMorph.Single(w => w.Anchor == "q:1:1:1");
            Assert.Equal((1L, 1L, "N", "{\"y\":[2],\"z\":1}"), (w1.RootId, w1.LemmaId, w1.Pos, w1.Features));
            Assert.Equal(1L, pack.WordMorph.Single(w => w.Anchor == "q:1:2:1").RootId);
            Assert.Equal(flavor == BuildFlavor.Public ? 3 : 4, pack.WordFixCount);
            Assert.False(PackTestData.Evaluate(flavor, snapshot).Rejected);
        }

        // lemma_id duzeltmesi yalniz ayeti girmis kelimeye uygulanir: public'te q:1:3:1 yok (taslak ayet), dev'de var.
        PackContent dev = Assemble(BuildFlavor.Dev, Snapshot(fixes));
        PackContent publicPack = Assemble(BuildFlavor.Public, Snapshot(fixes));
        Assert.Equal(4L, dev.WordMorph.Single(w => w.Anchor == "q:1:3:1").LemmaId);
    }

    [Fact]
    public void Candidate_and_rejected_fixes_are_never_applied_in_any_flavor()
    {
        QuranWordFixRow[] fixes = [Fix(FixCandidate, "q:1:1:1", "pos", "N", "aday"), Fix(FixRed, "q:1:2:1", "pos", "X", "red")];

        foreach (BuildFlavor flavor in Enum.GetValues<BuildFlavor>())
        {
            PackContent pack = Assemble(flavor, Snapshot(fixes));

            Assert.Equal("V", pack.WordMorph.Single(w => w.Anchor == "q:1:1:1").Pos);
            Assert.Equal("N", pack.WordMorph.Single(w => w.Anchor == "q:1:2:1").Pos);
            Assert.Equal(0, pack.WordFixCount);
        }
    }

    [Theory]
    [InlineData("root_id", "99", "hedef-kimlik-yok")]
    [InlineData("root_id", "9", "hedef-kimlik-yok")] // 9 yalniz test-sozluk kokudur: pakette yok
    [InlineData("lemma_id", "2", "hedef-kimlik-yok")] // lemma 2 onaysiz
    [InlineData("lemma_id", "3", "hedef-kimlik-yok")] // lemma 3 test kaynakli
    [InlineData("root_id", "abc", "deger-gecersiz")]
    [InlineData("root_id", "0", "deger-gecersiz")]
    [InlineData("root_id", "-1", "deger-gecersiz")]
    [InlineData("root_id", "1.0", "deger-gecersiz")]
    [InlineData("root_id", " 1", "deger-gecersiz")]
    [InlineData("root_id", "٣", "deger-gecersiz")] // Arap-Hint rakami
    [InlineData("root_id", "99999999999", "deger-gecersiz")]
    [InlineData("pos", "  ", "deger-gecersiz")]
    [InlineData("features", "{bozuk", "deger-gecersiz")]
    [InlineData("features", "null", "deger-gecersiz")]
    [InlineData("features", "{\"a\":1,\"a\":2}", "deger-gecersiz")] // yinelenen anahtar: RFC 8785 kanonikleme atar
    [InlineData("features", "{\"a\":-0}", "deger-gecersiz")]
    [InlineData("features", "{\"a\":1e999}", "deger-gecersiz")]
    public void An_approved_fix_that_cannot_be_applied_rejects_the_release_and_is_skipped_by_the_assembler(string field, string value, string defect)
    {
        QuranWordFixRow[] fixes = [Fix(FixPos, "q:1:1:1", field, value)];

        foreach (BuildFlavor flavor in Enum.GetValues<BuildFlavor>())
        {
            EditorialSnapshot snapshot = Snapshot(fixes);
            GateResult gate = PackTestData.Evaluate(flavor, snapshot);

            Assert.True(gate.Rejected);
            GateViolation violation = Assert.Single(gate.Report.Violations);
            Assert.Null(violation.Rule);
            Assert.Equal("quran_word_fix:" + FixPos.ToString("D", CultureInfo.InvariantCulture), violation.Subject);
            Assert.Equal("duzeltme-uygulanamaz:" + defect, violation.Reason);

            // Kapi yayini durdurur; birlestirici kusurlu duzeltmeyi atlar (taban degismez, sayac 0).
            PackContent pack = PackAssembler.Assemble(PackCatalog.Default.Get("kelime-kok"), flavor, snapshot, gate, PackCatalog.Default);
            Assert.Equal(0, pack.WordFixCount);
            Assert.Equal("V", pack.WordMorph.Single(w => w.Anchor == "q:1:1:1").Pos);
        }
    }

    [Fact]
    public void Non_canonicalizable_json_never_crashes_the_gate_input_the_assembler_or_the_source_digest()
    {
        string[] bad = ["{\"a\":1,\"a\":2}", "{\"a\":-0}", "{\"a\":1e999}"];
        foreach (string json in bad)
        {
            Assert.Null(WordMorphFixes.CanonicalJson(json));
            Assert.Equal(json, WordMorphFixes.CanonicalJsonOrRaw(json));

            // Taban features ve anlam alani temsil edilemeyen JSON tasisa da (bellek ici anlik goruntu) kapi, birlestirici ve ozet cokmez.
            EditorialSnapshot snapshot = Snapshot([Fix(FixFeatures, "q:1:1:1", "features", json)]);
            EditorialSnapshot withBad = With(
                snapshot,
                words: [.. snapshot.QuranWords.Select(w => w.Anchor == "q:1:2:1" ? w with { Features = json } : w)],
                glosses: [.. snapshot.LemmaGlosses.Select(g => g.LemmaId == 1 ? g with { KuranAnlamlari = json } : g)]);

            GateResult gate = PackTestData.Evaluate(BuildFlavor.Dev, withBad);
            Assert.Equal("duzeltme-uygulanamaz:deger-gecersiz", Assert.Single(gate.Report.Violations).Reason);
            PackContent pack = PackAssembler.Assemble(PackCatalog.Default.Get("kelime-kok"), BuildFlavor.Dev, withBad, gate, PackCatalog.Default);
            Assert.Equal(json, pack.WordMorph.Single(w => w.Anchor == "q:1:2:1").Features);
            Assert.Equal(json, pack.LemmaGlosses.Single(g => g.LemmaId == 1).KuranAnlamlari);
            Assert.Equal(SourceDigests.Compute(withBad, [Qac, Wbw]), SourceDigests.Compute(withBad, [Qac, Wbw]));
        }
    }

    [Fact]
    public void The_same_jsonb_value_in_two_textual_forms_gives_the_same_pack_row_and_source_digest()
    {
        EditorialSnapshot spaced = Snapshot();
        EditorialSnapshot compact = With(
            spaced,
            words: [.. spaced.QuranWords.Select(w => w.Anchor == "q:1:1:1" ? w with { Features = "{\"a\":1,\"b\":2}" } : w)],
            glosses: [.. spaced.LemmaGlosses.Select(g => g.LemmaId == 4 ? g with { KuranAnlamlari = "[\"deneme\",\"b\"]" } : g)]);
        EditorialSnapshot spacedGloss = With(
            spaced,
            glosses: [.. spaced.LemmaGlosses.Select(g => g.LemmaId == 4 ? g with { KuranAnlamlari = "[\"deneme\", \"b\"]" } : g)]);

        PackContent a = Assemble(BuildFlavor.Dev, spacedGloss);
        PackContent b = Assemble(BuildFlavor.Dev, compact);

        Assert.Equal("[\"deneme\",\"b\"]", a.LemmaGlosses.Single(g => g.LemmaId == 4).KuranAnlamlari);
        Assert.Equal(a.LemmaGlosses, b.LemmaGlosses);
        Assert.Equal(a.WordMorph, b.WordMorph);
        Assert.Equal(PackDigest.Compute(a), PackDigest.Compute(b));
        Assert.Equal(SourceDigests.Compute(spacedGloss, [Qac, Wbw]), SourceDigests.Compute(compact, [Qac, Wbw]));
    }

    // ---------------------------------------------------------------- kaynak ozeti: quran_word_fix (P-14)

    [Fact]
    public void Quran_word_fixes_of_every_status_enter_the_qac_source_digest_and_a_status_change_alters_it()
    {
        EditorialSnapshot none = Snapshot();
        EditorialSnapshot candidate = Snapshot([Fix(FixCandidate, "q:1:1:1", "pos", "N", "aday")]);
        EditorialSnapshot approved = Snapshot([Fix(FixCandidate, "q:1:1:1", "pos", "N", "onayli")]);
        EditorialSnapshot rejected = Snapshot([Fix(FixCandidate, "q:1:1:1", "pos", "N", "red")]);

        string Qd(EditorialSnapshot s) => SourceDigests.Compute(s, [Qac, Wbw])[Qac];

        string[] digests = [Qd(none), Qd(candidate), Qd(approved), Qd(rejected)];
        Assert.Equal(4, digests.Distinct(StringComparer.Ordinal).Count());
        Assert.Equal(Qd(approved), Qd(Snapshot([Fix(FixCandidate, "q:1:1:1", "pos", "N", "onayli")])));
        Assert.Equal(SourceDigests.Compute(none, [Qac, Wbw])[Wbw], SourceDigests.Compute(approved, [Qac, Wbw])[Wbw]);

        // Girdi sirasi onemsiz; deger degisirse ozet degisir.
        QuranWordFixRow a = Fix(FixPos, "q:1:1:1", "pos", "N");
        QuranWordFixRow b = Fix(FixRoot, "q:1:2:1", "root_id", "1");
        Assert.Equal(Qd(Snapshot([a, b])), Qd(Snapshot([b, a])));
        Assert.NotEqual(Qd(Snapshot([a, b])), Qd(Snapshot([a, b with { NewValue = "2" }])));
    }

    [Fact]
    public void A_candidate_to_approved_fix_transition_makes_the_p14_comparison_fail()
    {
        EditorialSnapshot atInternal = Snapshot([Fix(FixCandidate, "q:1:1:1", "pos", "N", "aday")]);
        EditorialSnapshot atPromote = Snapshot([Fix(FixCandidate, "q:1:1:1", "pos", "N", "onayli")]);

        IReadOnlyDictionary<string, string> internalDigests = SourceDigests.Compute(atInternal, [Qac, Wbw]);
        IReadOnlyDictionary<string, string> promoteDigests = SourceDigests.Compute(atPromote, [Qac, Wbw]);

        IReadOnlyList<GateViolation> violations = GateEvaluator.EvaluateP14(internalDigests, promoteDigests);

        GateViolation violation = Assert.Single(violations);
        Assert.Equal((GateRule.P14, Qac, "ozet-uyusmuyor"), (violation.Rule, violation.Subject, violation.Reason));
        Assert.Empty(GateEvaluator.EvaluateP14(internalDigests, SourceDigests.Compute(atInternal, [Qac, Wbw])));
    }

    [Fact]
    public void An_approved_fix_on_a_word_without_a_qac_row_is_rejected_as_kelime_yok()
    {
        QuranWordFixRow[] fixes = [Fix(FixPos, "q:1:1:2", "pos", "N")];

        GateResult gate = PackTestData.Evaluate(BuildFlavor.Public, Snapshot(fixes));

        Assert.True(gate.Rejected);
        Assert.Equal("duzeltme-uygulanamaz:kelime-yok", Assert.Single(gate.Report.Violations).Reason);
    }

    [Fact]
    public void A_candidate_fix_with_a_missing_target_does_not_reject_the_release()
    {
        QuranWordFixRow[] fixes = [Fix(FixCandidate, "q:1:1:1", "root_id", "99", "aday"), Fix(FixRed, "q:1:2:1", "lemma_id", "99", "red")];

        foreach (BuildFlavor flavor in Enum.GetValues<BuildFlavor>())
        {
            Assert.False(PackTestData.Evaluate(flavor, Snapshot(fixes)).Rejected);
        }
    }

    // ---------------------------------------------------------------- P-12: test- onekli sozluk kaynagi

    [Fact]
    public void P12_a_test_prefixed_dictionary_source_leaks_into_dev_only_and_never_into_the_public_pack()
    {
        PackCatalog catalog = CatalogWithTestDictionary();

        PackContent dev = Assemble(BuildFlavor.Dev, Snapshot(), catalog);
        PackContent inner = Assemble(BuildFlavor.Internal, Snapshot(), catalog);
        PackContent publicPack = Assemble(BuildFlavor.Public, Snapshot(), catalog);

        // dev: test-sozluk kaynagi girer (kok 9, lemma 3 ve onun anlami); internal ve public: girmez (yalniz uctan uca fikstur kaynaklari internal'a girer).
        Assert.Contains(dev.Roots, r => r.Id == 9);
        Assert.Contains(dev.Lemmas, l => l.Id == 3);
        Assert.Contains(dev.LemmaGlosses, g => g.LemmaId == 3);
        Assert.Contains(dev.PackSources, s => s.SourceId == TestLexicon);
        foreach (PackContent pack in new[] { inner, publicPack })
        {
            Assert.DoesNotContain(pack.Roots, r => r.Id == 9);
            Assert.DoesNotContain(pack.Lemmas, l => l.Id == 3);
            Assert.DoesNotContain(pack.LemmaGlosses, g => g.LemmaId == 3);
            Assert.DoesNotContain(pack.PackSources, s => s.SourceId == TestLexicon);
            Assert.DoesNotContain(pack.Attributions, a => a.SourceId == TestLexicon);
        }

        GateResult gate = PackTestData.Evaluate(BuildFlavor.Public, Snapshot(), catalog);
        Assert.Contains(gate.Report.Rows, r => r.Kind == GateSubjectKind.Kaynak && r.Id == TestLexicon && r.Rule == GateRule.P12);
        Assert.False(gate.Rejected);
    }

    [Fact]
    public void A_dictionary_row_of_a_source_the_pack_does_not_list_never_enters_even_without_the_test_prefix()
    {
        EditorialSnapshot snapshot = Snapshot();
        EditorialSnapshot withStranger = new()
        {
            Sources = snapshot.Sources,
            Units = snapshot.Units,
            QuranWords = snapshot.QuranWords,
            QuranMarkers = snapshot.QuranMarkers,
            PageMaps = snapshot.PageMaps,
            Lexicals = snapshot.Lexicals,
            Roots = [.. snapshot.Roots, new RootRow(50, "دذر", 1, 1, null, null, "baska-kaynak")],
            Lemmas = [.. snapshot.Lemmas, new LemmaRow(50, "دذر", "دذر", null, 1, null, false, "onayli", "baska-kaynak")],
            LemmaGlosses = snapshot.LemmaGlosses,
            WordFixes = snapshot.WordFixes,
        };

        PackContent pack = Assemble(BuildFlavor.Dev, withStranger);

        Assert.DoesNotContain(pack.Roots, r => r.Id == 50);
        Assert.DoesNotContain(pack.Lemmas, l => l.Id == 50);
    }

    // ---------------------------------------------------------------- kaynak kaydi ve atif (P-01, P-11)

    [Fact]
    public void Pack_sources_and_attribution_rows_equal_the_source_records_byte_for_byte_and_do_not_depend_on_fixes()
    {
        EditorialSnapshot plain = Snapshot();
        EditorialSnapshot fixedUp = Snapshot([Fix(FixPos, "q:1:1:1", "pos", "N")]);

        PackContent a = Assemble(BuildFlavor.Dev, plain);
        PackContent b = Assemble(BuildFlavor.Dev, fixedUp);

        Assert.Equal([Qac, Wbw], a.PackSources.Select(s => s.SourceId).Order(StringComparer.Ordinal));
        PackAttributionRow qac = a.Attributions.Single(x => x.SourceId == Qac);
        SourceRow source = plain.Sources.Single(s => s.Slug == Qac);
        Assert.Equal((source.Baslik, source.Surum, source.AtifUrl, source.AtifMetni, source.NoticeText), (qac.Title, qac.Version, qac.SourceUrl, qac.RequiredCredit, qac.NoticeText));
        Assert.Equal(a.Attributions, b.Attributions);
        Assert.Equal(a.PackSources, b.PackSources);
    }

    [Fact]
    public void The_gloss_source_is_listed_only_when_the_pack_carries_gloss_rows()
    {
        EditorialSnapshot snapshot = Snapshot();
        EditorialSnapshot noGlosses = new()
        {
            Sources = snapshot.Sources,
            Units = snapshot.Units,
            QuranWords = snapshot.QuranWords,
            QuranMarkers = snapshot.QuranMarkers,
            PageMaps = snapshot.PageMaps,
            Lexicals = snapshot.Lexicals.Where(l => l.Kind != LexicalKind.LemmaGloss).ToList(),
            Roots = snapshot.Roots,
            Lemmas = snapshot.Lemmas,
            LemmaGlosses = [],
        };

        PackContent pack = Assemble(BuildFlavor.Dev, noGlosses);

        Assert.Equal([Qac], pack.PackSources.Select(s => s.SourceId));
        Assert.Empty(pack.LemmaGlosses);
    }

    // ---------------------------------------------------------------- kapi girdisi: HasContent

    [Fact]
    public void The_pack_is_a_candidate_only_when_dictionary_data_exists()
    {
        EditorialSnapshot empty = new() { Sources = Snapshot().Sources };
        EditorialSnapshot onlyRoots = new() { Sources = Snapshot().Sources, Roots = [new RootRow(1, "بتث", 1, 1, null, null, Qac)] };
        EditorialSnapshot onlyGlosses = new() { Sources = Snapshot().Sources, LemmaGlosses = [new LemmaGlossRow(1, "Deneme anlam 1", "[]", null, false, "aday", "editor", "1")] };
        EditorialSnapshot onlyMorph = new()
        {
            Sources = Snapshot().Sources,
            QuranWords = [Morph("q:1:1:1", 1, 1, 1, 1, 0, 6, 1, 1, "V", null)],
        };
        EditorialSnapshot tanzilOnly = new()
        {
            Sources = Snapshot().Sources,
            QuranWords = [new QuranWordRow("q:1:1:1", 1, 1, 1, 1, PackTestData.SyntheticArabic, PackTestData.SyntheticArabic, 0, 6, "tanzil-uthmani")],
        };

        Assert.False(HasContent(empty));
        Assert.False(HasContent(tanzilOnly));
        Assert.True(HasContent(onlyRoots));
        Assert.True(HasContent(onlyGlosses));
        Assert.True(HasContent(onlyMorph));

        static bool HasContent(EditorialSnapshot snapshot) =>
            GateInputBuilder.Build(snapshot, PackCatalog.Default, "pipeline/sources", fileExists: _ => true).Packs.Single(p => p.PackId == "kelime-kok").HasContent;
    }

    [Fact]
    public void An_empty_lexicon_pack_is_reported_as_icerik_yok_and_never_a_violation()
    {
        EditorialSnapshot snapshot = new() { Sources = Snapshot().Sources };

        GateResult gate = PackTestData.Evaluate(BuildFlavor.Public, snapshot);

        GateReportRow row = Assert.Single(gate.Report.Rows, r => r.Kind == GateSubjectKind.Paket && r.Id == "kelime-kok");
        Assert.Equal((GateDecision.Girmedi, (GateRule?)null, GateReasons.IcerikYok), (row.Decision, row.Rule, row.Reason));
        Assert.False(gate.Rejected);
    }

    // ---------------------------------------------------------------- kaynak ozeti (K-46 madde 1)

    [Fact]
    public void Lexicon_source_digests_cover_the_dictionary_rows_independent_of_the_flavor_and_the_input_order()
    {
        EditorialSnapshot snapshot = Snapshot();
        EditorialSnapshot reordered = new()
        {
            Sources = snapshot.Sources,
            Units = snapshot.Units,
            QuranWords = [.. snapshot.QuranWords.Reverse()],
            QuranMarkers = snapshot.QuranMarkers,
            PageMaps = snapshot.PageMaps,
            Lexicals = snapshot.Lexicals,
            Roots = [.. snapshot.Roots.Reverse()],
            Lemmas = [.. snapshot.Lemmas.Reverse()],
            LemmaGlosses = [.. snapshot.LemmaGlosses.Reverse()],
        };

        IReadOnlyDictionary<string, string> a = SourceDigests.Compute(snapshot, [Qac, Wbw]);
        IReadOnlyDictionary<string, string> b = SourceDigests.Compute(reordered, [Qac, Wbw]);

        Assert.Equal(a, b);
        Assert.Matches("^[0-9a-f]{64}$", a[Qac]);
        Assert.NotEqual(a[Qac], a[Wbw]);
        Assert.NotEqual(SourceDigests.Compute(new EditorialSnapshot { Sources = snapshot.Sources }, [Qac])[Qac], a[Qac]);
    }

    [Fact]
    public void A_change_in_a_root_a_lemma_a_qac_word_column_or_a_gloss_changes_the_matching_source_digest_only()
    {
        EditorialSnapshot snapshot = Snapshot();
        IReadOnlyDictionary<string, string> baseline = SourceDigests.Compute(snapshot, [Qac, Wbw]);

        EditorialSnapshot rootChanged = With(snapshot, roots: [.. snapshot.Roots.Select(r => r.Id == 1 ? r with { Occurrences = 99 } : r)]);
        EditorialSnapshot lemmaChanged = With(snapshot, lemmas: [.. snapshot.Lemmas.Select(l => l.Id == 1 ? l with { Status = "aday" } : l)]);
        EditorialSnapshot wordChanged = With(snapshot, words: [.. snapshot.QuranWords.Select(w => w.Anchor == "q:1:1:1" ? w with { Pos = "N" } : w)]);
        EditorialSnapshot glossChanged = With(snapshot, glosses: [.. snapshot.LemmaGlosses.Select(g => g.LemmaId == 4 ? g with { Status = "onayli" } : g)]);

        foreach (EditorialSnapshot changed in new[] { rootChanged, lemmaChanged, wordChanged })
        {
            IReadOnlyDictionary<string, string> digest = SourceDigests.Compute(changed, [Qac, Wbw]);
            Assert.NotEqual(baseline[Qac], digest[Qac]);
            Assert.Equal(baseline[Wbw], digest[Wbw]);
        }

        IReadOnlyDictionary<string, string> glossDigest = SourceDigests.Compute(glossChanged, [Qac, Wbw]);
        Assert.Equal(baseline[Qac], glossDigest[Qac]);
        Assert.NotEqual(baseline[Wbw], glossDigest[Wbw]);
    }

    [Fact]
    public void The_word_morphology_of_another_morph_source_is_not_part_of_the_qac_digest()
    {
        EditorialSnapshot snapshot = Snapshot();
        EditorialSnapshot other = With(snapshot, words: [.. snapshot.QuranWords.Select(w => w.Anchor == "q:1:1:1" ? w with { MorphSource = "baska-kaynak", Pos = "N" } : w)]);

        IReadOnlyDictionary<string, string> baseline = SourceDigests.Compute(snapshot, [Qac]);
        IReadOnlyDictionary<string, string> changed = SourceDigests.Compute(other, [Qac]);

        // q:1:1:1 artik qac-morfoloji satiri degil: ozet degisir (satir cikti), ama baska kaynagin sutunlari ozete girmez.
        Assert.NotEqual(baseline[Qac], changed[Qac]);
        EditorialSnapshot otherPosChanged = With(other, words: [.. other.QuranWords.Select(w => w.Anchor == "q:1:1:1" ? w with { Pos = "X" } : w)]);
        Assert.Equal(changed[Qac], SourceDigests.Compute(otherPosChanged, [Qac])[Qac]);
    }

    private static EditorialSnapshot With(
        EditorialSnapshot s,
        IReadOnlyList<RootRow>? roots = null,
        IReadOnlyList<LemmaRow>? lemmas = null,
        IReadOnlyList<QuranWordRow>? words = null,
        IReadOnlyList<LemmaGlossRow>? glosses = null) => new()
        {
            Sources = s.Sources,
            Units = s.Units,
            QuranWords = words ?? s.QuranWords,
            QuranMarkers = s.QuranMarkers,
            PageMaps = s.PageMaps,
            Lexicals = s.Lexicals,
            Roots = roots ?? s.Roots,
            Lemmas = lemmas ?? s.Lemmas,
            LemmaGlosses = glosses ?? s.LemmaGlosses,
            WordFixes = s.WordFixes,
        };

    // ---------------------------------------------------------------- satirlar, ozet ve yazici

    [Fact]
    public void Row_order_puts_the_kelime_kok_tables_after_tr_root_index_in_the_documented_sequence()
    {
        PackContent pack = Assemble(BuildFlavor.Dev, Snapshot());

        string[] tables = [.. PackRows.Enumerate(pack).Select(r => r.Table).Distinct(StringComparer.Ordinal)];

        Assert.Equal(["pack_source", "attribution", "word_morph", "root", "lemma", "lemma_gloss"], tables);
        Assert.Equal(
            ["pack_source", "attribution", "unit", "unit_search", "xref_idx", "quran_word", "quran_marker", "page_map", "sure", "tr_root_index", "word_morph", "root", "lemma", "lemma_gloss", "tr_form"],
            PackTables.Order);
        Assert.Equal(["lemma_id", "anlam_kisa", "kuran_anlamlari", "turkce_es_kelime", "yalnizca_etimolojik", "status", "origin"], PackTables.Columns("lemma_gloss"));
    }

    [Fact]
    public void The_pack_digest_is_stable_across_input_order_and_changes_with_a_fix_a_gloss_status_or_the_flavor()
    {
        EditorialSnapshot snapshot = Snapshot();
        EditorialSnapshot reordered = With(
            snapshot,
            roots: [.. snapshot.Roots.Reverse()],
            lemmas: [.. snapshot.Lemmas.Reverse()],
            words: [.. snapshot.QuranWords.Reverse()],
            glosses: [.. snapshot.LemmaGlosses.Reverse()]);

        string baseline = PackDigest.Compute(Assemble(BuildFlavor.Dev, snapshot));

        Assert.Equal(baseline, PackDigest.Compute(Assemble(BuildFlavor.Dev, reordered)));
        Assert.NotEqual(baseline, PackDigest.Compute(Assemble(BuildFlavor.Dev, Snapshot([Fix(FixPos, "q:1:1:1", "pos", "N")]))));
        Assert.NotEqual(baseline, PackDigest.Compute(Assemble(BuildFlavor.Public, snapshot)));
        Assert.NotEqual(baseline, PackDigest.Compute(Assemble(BuildFlavor.Internal, snapshot)));
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task The_writer_writes_a_kelime_kok_pack_with_the_fix_count_meta_and_a_green_self_check(bool turkish)
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        using PackTestData.TempDir dir = new();
        EditorialSnapshot snapshot = Snapshot([Fix(FixPos, "q:1:1:1", "pos", "N"), Fix(FixRoot, "q:1:2:1", "root_id", "1"), Fix(FixCandidate, "q:1:3:1", "pos", "X", "aday")]);

        await StorageTestKit.RunAsync(turkish, async () =>
        {
            PackContent content = Assemble(BuildFlavor.Dev, snapshot);
            SqlitePackWriter writer = new(PackTestData.Definitions(), new FixedClock(new DateTimeOffset(2026, 11, 12, 9, 0, 0, TimeSpan.Zero)));

            PackFile file = await writer.WriteAsync(content, new PackWriteRequest(dir.Path, "2026.11.0", "2026.11.12-abcdef0", snapshot.Sources), ct);

            Assert.True(file.SelfCheck.Passed, file.SelfCheck.FailedNames);
            SqliteConnectionStringBuilder builder = new() { DataSource = file.Path, Pooling = false, Mode = SqliteOpenMode.ReadOnly };
            using SqliteConnection connection = new(builder.ConnectionString);
            connection.Open();
            Dictionary<string, string> meta = ReadMeta(connection);
            Assert.Equal("2", meta[PackMetaKeys.WordFixCount]);
            Assert.Equal("word_fix_count", PackMetaKeys.WordFixCount);
            Assert.Equal("0", meta["unit_count"]);
            Assert.Equal(file.ContentDigest, meta["content_digest"]);
            Assert.Equal("N", Scalar(connection, "SELECT pos FROM word_morph WHERE anchor = 'q:1:1:1'"));
            Assert.Equal("1", Scalar(connection, "SELECT root_id FROM word_morph WHERE anchor = 'q:1:2:1'"));
            Assert.Equal("V", Scalar(connection, "SELECT pos FROM word_morph WHERE anchor = 'q:1:3:1'"));
            Assert.Equal("1", Scalar(connection, "SELECT count(*) FROM lemma_gloss WHERE status = 'aday'"));
            Assert.Equal("0", Scalar(connection, "SELECT count(*) FROM tr_form"));
            Assert.Equal("0", Scalar(connection, "SELECT count(*) FROM tr_root_index"));

            // attribution satiri kaynakla bayt bayt ayni (PackSelfCheck gidis-donus denetimi yesil).
            Assert.Equal("Sentetik QAC atfi", Scalar(connection, "SELECT required_credit FROM attribution WHERE source_id = 'qac-morfoloji'"));
            Assert.Equal("Sentetik bildirim", Scalar(connection, "SELECT notice_text FROM attribution WHERE source_id = 'qac-morfoloji'"));
        });
    }

    [Fact]
    public async Task Other_packs_do_not_carry_the_fix_count_meta_key()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        using PackTestData.TempDir dir = new();
        SqlitePackWriter writer = new(PackTestData.Definitions(), new FixedClock(new DateTimeOffset(2026, 11, 12, 9, 0, 0, TimeSpan.Zero)));

        PackFile file = await writer.WriteAsync(PackTestData.SmallContent(), PackTestData.Request(dir.Path), ct);

        SqliteConnectionStringBuilder builder = new() { DataSource = file.Path, Pooling = false, Mode = SqliteOpenMode.ReadOnly };
        using SqliteConnection connection = new(builder.ConnectionString);
        connection.Open();
        Assert.DoesNotContain(PackMetaKeys.WordFixCount, ReadMeta(connection).Keys);
    }

    [Fact]
    public void The_hallmark_count_does_not_change_the_pack_digest_but_the_rows_that_it_is_derived_from_do()
    {
        // Sayac ozete girmez (K-46 madde 1: ozet pakete yazilan satirlardan turer); bir duzeltme word_morph satirini degistirdigi icin ozet yine degisir.
        PackContent a = Assemble(BuildFlavor.Dev, Snapshot());
        PackContent b = new()
        {
            PackId = a.PackId,
            Flavor = a.Flavor,
            PackSources = a.PackSources,
            Attributions = a.Attributions,
            WordMorph = a.WordMorph,
            Roots = a.Roots,
            Lemmas = a.Lemmas,
            LemmaGlosses = a.LemmaGlosses,
            GateSummary = a.GateSummary,
            WordFixCount = 7,
        };

        Assert.Equal(PackDigest.Compute(a), PackDigest.Compute(b));
    }

    private static Dictionary<string, string> ReadMeta(SqliteConnection connection)
    {
        using SqliteCommand command = connection.CreateCommand();
        command.CommandText = "SELECT key, value FROM pack_meta";
        using SqliteDataReader reader = command.ExecuteReader();
        Dictionary<string, string> meta = new(StringComparer.Ordinal);
        while (reader.Read())
        {
            meta[reader.GetString(0)] = reader.GetString(1);
        }

        return meta;
    }

    private static string Scalar(SqliteConnection connection, string sql)
    {
        using SqliteCommand command = connection.CreateCommand();
        command.CommandText = sql;
        return Convert.ToString(command.ExecuteScalar(), CultureInfo.InvariantCulture)!;
    }
}
