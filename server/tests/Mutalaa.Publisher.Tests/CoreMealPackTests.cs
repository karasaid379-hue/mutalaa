using Mutalaa.Api.Tests.Support;
using Mutalaa.Domain.Releases;
using Mutalaa.Domain.Releases.Gate;
using Mutalaa.Infrastructure.Packs;
using Mutalaa.Infrastructure.Releases;

namespace Mutalaa.Publisher.Tests;

/// <summary>
/// K-49: core paketi iki Elmalili mealini (elmalili-meal, elmalili-sade-meal) istege bagli icerik kaynagi olarak tasir. Kapi girdisi,
/// PackAssembler (dev ve internal'da onaysiz meal, public'te P-10 suzmesi), K-47 capa surekliligi (capa-kayboldu) ve sentetik meal fikstürüyle
/// kapi -> paket -> SQLite dosyasi -> geri okuma. Metinler acikca sentetiktir ("Deneme meal paragrafi N"); gercek meal metni yoktur.
/// Test kaynak kaydi (test- onekli) eklenmez: kaynaklar kapida kayitli sayilir (PackTestData.AllRegistered). Docker gerektirmez.
/// </summary>
public class CoreMealPackTests
{
    private const string OriginalSlug = "elmalili-meal";
    private const string PlainSlug = "elmalili-sade-meal";
    private const string OriginalCredit = "Deneme atif metni (orijinal meal), sentetik.";
    private const string PlainCredit = "Deneme atif metni (sadelestirilmis meal), sentetik.";
    private const string OriginalVersion = "2026-11-11 deneme-surum-1";
    private const string PlainVersion = "deneme-surum-2";

    private static readonly string[] MealAnchors =
    [
        "meal:elmalili-sade:1:1",
        "meal:elmalili-sade:1:2",
        "meal:elmalili:1:1",
        "meal:elmalili:1:2",
        "meal:elmalili:1:3",
    ];

    /// <summary>Temel sentetik goruntu + iki meal kaynagi. Orijinal: 1:1 onayli, 1:2 taslak, 1:3 birlesik izleyen (bos metin). Sade: ikisi de taslak.</summary>
    private static EditorialSnapshot WithMeals(bool includeOriginal = true, bool includePlain = true)
    {
        EditorialSnapshot snapshot = PackTestData.Snapshot();
        List<SourceRow> sources = [.. snapshot.Sources];
        List<UnitRow> units = [.. snapshot.Units];
        if (includeOriginal)
        {
            sources.Add(PackTestData.Source(OriginalSlug, "meal", OriginalCredit, baslik: "Deneme orijinal meal", surum: OriginalVersion));
            units.Add(PackTestData.Unit("meal:elmalili:1:1", OriginalSlug, "meal", "Deneme meal paragrafi 1", durum: "onayli", ord: 1, ayahLo: 1, ayahHi: 3));
            units.Add(PackTestData.Unit("meal:elmalili:1:2", OriginalSlug, "meal", "Deneme meal paragrafi 2", durum: "taslak", ord: 2, ayahLo: 3, ayahHi: 4));
            units.Add(PackTestData.Unit("meal:elmalili:1:3", OriginalSlug, "meal", string.Empty, durum: "taslak", ord: 3, ayahLo: 4, ayahHi: 5) with
            {
                Attrs = "{\"birlesik_ile\":\"meal:elmalili:1:2\"}",
            });
        }

        if (includePlain)
        {
            sources.Add(PackTestData.Source(PlainSlug, "meal", PlainCredit, baslik: "Deneme sade meal", surum: PlainVersion));
            units.Add(PackTestData.Unit("meal:elmalili-sade:1:1", PlainSlug, "meal", "Deneme meal paragrafi 3", durum: "taslak", ord: 1, ayahLo: 1, ayahHi: 2));
            units.Add(PackTestData.Unit("meal:elmalili-sade:1:2", PlainSlug, "meal", "Deneme meal paragrafi 4", durum: "taslak", ord: 2, ayahLo: 2, ayahHi: 3));
        }

        return new EditorialSnapshot
        {
            Sources = sources,
            Units = units,
            QuranWords = snapshot.QuranWords,
            QuranMarkers = snapshot.QuranMarkers,
            PageMaps = snapshot.PageMaps,
            Xrefs = snapshot.Xrefs,
            OpenReviewXrefIds = snapshot.OpenReviewXrefIds,
            Lexicals = snapshot.Lexicals,
            PreviousRelease = snapshot.PreviousRelease,
        };
    }

    private static GateInput Input(EditorialSnapshot snapshot, IReadOnlyCollection<string>? previous = null, Func<string, bool>? fileExists = null) =>
        GateInputBuilder.Build(snapshot, PackCatalog.Default, "pipeline/sources", previousAnchors: previous, fileExists: fileExists ?? PackTestData.AllRegistered());

    private static PackContent AssembleCore(BuildFlavor flavor, EditorialSnapshot snapshot)
    {
        GateResult gate = GateEvaluator.Evaluate(flavor, Input(snapshot));
        Assert.False(gate.Rejected, gate.Report.ToJson());
        return PackAssembler.Assemble(PackCatalog.Default.Get("core"), flavor, snapshot, gate, PackCatalog.Default);
    }

    // ---- Katalog ----

    [Fact]
    public void Core_catalog_lists_both_meal_sources_as_optional_content_and_the_new_title()
    {
        PackDefinition core = PackCatalog.Default.Get("core");

        Assert.Equal("Kur'an ve Elmalılı mealleri", core.Title);
        Assert.Equal(
            [OriginalSlug, PlainSlug],
            core.Sources.Where(s => !s.Required).Select(s => s.Slug).Order(StringComparer.Ordinal));
        Assert.All(core.Sources.Where(s => !s.Required), s => Assert.Equal(PackSourceRole.Content, s.Role));
        Assert.Equal(
            ["elmalili-meal", "elmalili-sade-meal", "tanzil-uthmani"],
            core.ContentSources.Select(s => s.Slug).Order(StringComparer.Ordinal));
    }

    // ---- Kapi girdisi ----

    [Fact]
    public void The_gate_input_carries_the_meal_sources_only_when_they_have_a_row_or_units()
    {
        GatePack withMeals = Input(WithMeals()).Packs.Single(p => p.PackId == "core");
        GatePack withoutMeals = Input(PackTestData.Snapshot()).Packs.Single(p => p.PackId == "core");
        GatePack onlyOriginal = Input(WithMeals(includePlain: false)).Packs.Single(p => p.PackId == "core");

        Assert.Equal(
            ["elmalili-meal", "elmalili-sade-meal", "tanzil-simple-clean", "tanzil-ust-veri", "tanzil-uthmani"],
            withMeals.SourceSlugs.Order(StringComparer.Ordinal));
        Assert.Equal(["tanzil-simple-clean", "tanzil-ust-veri", "tanzil-uthmani"], withoutMeals.SourceSlugs.Order(StringComparer.Ordinal));
        Assert.Equal(["elmalili-meal", "tanzil-simple-clean", "tanzil-ust-veri", "tanzil-uthmani"], onlyOriginal.SourceSlugs.Order(StringComparer.Ordinal));
        Assert.True(withMeals.HasContent);
        Assert.True(withoutMeals.HasContent);
    }

    [Fact]
    public void A_core_without_any_meal_row_is_not_rejected_and_the_meal_sources_are_not_gate_sources()
    {
        EditorialSnapshot snapshot = PackTestData.Snapshot();
        GateInput input = Input(snapshot);

        GateResult result = GateEvaluator.Evaluate(BuildFlavor.Dev, input);

        Assert.False(result.Rejected, result.Report.ToJson());
        Assert.Contains("core", result.IncludedPacks);
        Assert.DoesNotContain(input.Sources, s => s.Slug is OriginalSlug or PlainSlug);
    }

    [Fact]
    public void A_meal_source_without_its_toml_is_unregistered_and_rejects_the_core_with_p01()
    {
        GateResult result = GateEvaluator.Evaluate(
            BuildFlavor.Dev,
            Input(WithMeals(), fileExists: path => !path.EndsWith(OriginalSlug + ".toml", StringComparison.Ordinal)));

        Assert.True(result.Rejected);
        GateViolation violation = Assert.Single(result.Report.Violations, v => v.Rule == GateRule.P01 && v.Subject == OriginalSlug);
        Assert.Equal(GateReasons.KaynakKaydiYok, violation.Reason);
    }

    [Fact]
    public void A_blank_meal_atif_text_is_reported_as_atif_metni_bos()
    {
        EditorialSnapshot snapshot = WithMeals();
        SourceRow blank = snapshot.Sources.Single(s => s.Slug == PlainSlug) with { AtifMetni = " " };
        EditorialSnapshot changed = new()
        {
            Sources = [.. snapshot.Sources.Where(s => s.Slug != PlainSlug), blank],
            Units = snapshot.Units,
            QuranWords = snapshot.QuranWords,
            QuranMarkers = snapshot.QuranMarkers,
            PageMaps = snapshot.PageMaps,
            Xrefs = snapshot.Xrefs,
        };

        GateResult result = GateEvaluator.Evaluate(BuildFlavor.Dev, Input(changed));

        Assert.True(result.Rejected);
        Assert.Contains(result.Report.Violations, v => v.Subject == PlainSlug && v.Reason == GateReasons.AtifMetniBos);
    }

    // ---- PackAssembler ----

    [Theory]
    [InlineData(BuildFlavor.Dev)]
    [InlineData(BuildFlavor.Internal)]
    public void Dev_and_internal_carry_every_meal_unit_with_approved_zero_for_the_unapproved_ones(BuildFlavor flavor)
    {
        PackContent core = AssembleCore(flavor, WithMeals());

        string[] mealRows = [.. core.Units.Where(u => string.Equals(u.Kind, "meal", StringComparison.Ordinal)).Select(u => u.Anchor).Order(StringComparer.Ordinal)];
        Assert.Equal(MealAnchors, mealRows);
        Assert.Equal(1, core.Units.Single(u => u.Anchor == "meal:elmalili:1:1").Approved);
        Assert.Equal(0, core.Units.Single(u => u.Anchor == "meal:elmalili:1:2").Approved);
        Assert.Equal(0, core.Units.Single(u => u.Anchor == "meal:elmalili-sade:1:1").Approved);
        Assert.Equal(core.Units.Count, core.UnitSearch.Count);

        // Birlesik izleyen birim bos metin ve attrs.birlesik_ile ile olduğu gibi tasinir.
        PackUnitRow follower = core.Units.Single(u => u.Anchor == "meal:elmalili:1:3");
        Assert.Equal(string.Empty, follower.Text);
        Assert.Equal("{\"birlesik_ile\":\"meal:elmalili:1:2\"}", follower.Attrs);
        Assert.Equal("meal:elmalili:1:3", follower.Label);

        // Tanzil birimleri ve kelimeleri etkilenmez.
        Assert.Equal(["q:1:1", "q:1:2", "q:1:3"], core.Units.Where(u => u.Kind == "ayet").Select(u => u.Anchor).Order(StringComparer.Ordinal));
        Assert.Equal(3, core.QuranWords.Count);
    }

    [Fact]
    public void The_attribution_rows_of_the_meal_sources_carry_atif_metni_and_surum_verbatim()
    {
        PackContent core = AssembleCore(BuildFlavor.Dev, WithMeals());

        PackAttributionRow original = core.Attributions.Single(a => a.SourceId == OriginalSlug);
        PackAttributionRow plain = core.Attributions.Single(a => a.SourceId == PlainSlug);
        Assert.Equal((OriginalCredit, OriginalVersion, "Deneme orijinal meal"), (original.RequiredCredit, original.Version, original.Title));
        Assert.Equal((PlainCredit, PlainVersion, "Deneme sade meal"), (plain.RequiredCredit, plain.Version, plain.Title));
        Assert.Equal(
            [OriginalSlug, PlainSlug, "tanzil-simple-clean", "tanzil-ust-veri", "tanzil-uthmani"],
            core.PackSources.Select(s => s.SourceId).Order(StringComparer.Ordinal));
    }

    [Fact]
    public void Public_drops_the_unapproved_meal_units_by_p10_and_lists_only_the_sources_that_still_give_rows()
    {
        // K-49 madde 5: bu test A34'e kadar gecerli olan davranisi kilitler; kismi meal (1/3 birim onayli) bugun public'e girer.
        // A34'te G-INC kurali yazilinca tersine doner: G-INC gecmemis meal kaynagi public'te hic girmemeli (bu beklenti guncellenecek).
        PackContent core = AssembleCore(BuildFlavor.Public, WithMeals());

        Assert.Equal(["meal:elmalili:1:1"], core.Units.Where(u => u.Kind == "meal").Select(u => u.Anchor));
        Assert.All(core.Units, u => Assert.Equal(1, u.Approved));
        Assert.Contains(core.PackSources, s => s.SourceId == OriginalSlug);
        Assert.DoesNotContain(core.PackSources, s => s.SourceId == PlainSlug);
        Assert.DoesNotContain(core.Attributions, a => a.SourceId == PlainSlug);
        Assert.Equal(core.Units.Count, core.UnitSearch.Count);
    }

    [Fact]
    public void Public_with_only_unapproved_meals_carries_no_meal_unit_and_no_meal_source()
    {
        EditorialSnapshot snapshot = WithMeals(includeOriginal: false);

        PackContent core = AssembleCore(BuildFlavor.Public, snapshot);

        Assert.DoesNotContain(core.Units, u => u.Kind == "meal");
        Assert.DoesNotContain(core.PackSources, s => s.SourceId is OriginalSlug or PlainSlug);
        Assert.Equal(["q:1:1", "q:1:2"], core.Units.Select(u => u.Anchor).Order(StringComparer.Ordinal));
    }

    [Fact]
    public void Core_without_meal_rows_is_assembled_exactly_as_before()
    {
        PackContent core = AssembleCore(BuildFlavor.Dev, PackTestData.Snapshot());

        Assert.DoesNotContain(core.Units, u => u.Kind == "meal");
        Assert.Equal(["tanzil-simple-clean", "tanzil-ust-veri", "tanzil-uthmani"], core.PackSources.Select(s => s.SourceId).Order(StringComparer.Ordinal));
    }

    // ---- K-47: capa sureklilik (capa-kayboldu) ----

    [Fact]
    public void A_meal_anchor_of_the_previous_dev_manifest_that_is_missing_from_the_snapshot_rejects_the_release()
    {
        // Onceki dev yayininda meal capalari vardi; yeni goruntude meal kaynagi hic yok (hat verisi silindi ya da yuklenmedi).
        EditorialSnapshot snapshot = PackTestData.Snapshot();

        GateResult result = GateEvaluator.Evaluate(BuildFlavor.Dev, Input(snapshot, previous: ["meal:elmalili:1:1", "meal:elmalili:1:2", "q:1:1"]));

        Assert.True(result.Rejected);
        GateViolation[] lost = [.. result.Report.Violations.Where(v => v.Reason.StartsWith(GateReasons.CapaKayboldu, StringComparison.Ordinal))];
        Assert.Equal(["meal:elmalili:1:1", "meal:elmalili:1:2"], lost.Select(v => v.Subject).Order(StringComparer.Ordinal));
        Assert.All(lost, v => Assert.Equal(GateReasons.CapaKayboldu + ":" + GateReasons.CapaSatirYok, v.Reason));
        Assert.All(lost, v => Assert.Null(v.Rule));
    }

    [Fact]
    public void Previous_meal_anchors_that_are_all_present_do_not_reject_the_dev_release()
    {
        GateResult result = GateEvaluator.Evaluate(BuildFlavor.Dev, Input(WithMeals(), previous: MealAnchors));

        Assert.False(result.Rejected, result.Report.ToJson());
        Assert.All(MealAnchors, a => Assert.Contains(a, result.IncludedUnits));
    }

    [Fact]
    public void An_unapproved_meal_anchor_that_the_previous_release_carried_is_lost_in_public_with_the_filter_reason()
    {
        GateResult result = GateEvaluator.Evaluate(BuildFlavor.Public, Input(WithMeals(), previous: ["meal:elmalili:1:1", "meal:elmalili:1:2"]));

        Assert.True(result.Rejected);
        GateViolation lost = Assert.Single(result.Report.Violations, v => v.Reason.StartsWith(GateReasons.CapaKayboldu, StringComparison.Ordinal));
        Assert.Equal("meal:elmalili:1:2", lost.Subject);
        Assert.Equal(GateReasons.CapaKayboldu + ":" + GateReasons.OnaysizBirim, lost.Reason);
    }

    // ---- Sentetik meal fikstürüyle uctan uca: kapi -> paket -> SQLite -> geri okuma ----

    [Fact]
    public async Task A_synthetic_meal_fixture_goes_from_the_gate_through_the_pack_file_and_reads_back_in_dev_and_public()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        EditorialSnapshot snapshot = WithMeals();
        SqlitePackWriter writer = new(PackTestData.Definitions());
        using PackTestData.TempDir temp = new();

        PackContent dev = AssembleCore(BuildFlavor.Dev, snapshot);
        PackFile devFile = await writer.WriteAsync(dev, PackTestData.Request(temp.Path, "2026.11.0", [.. snapshot.Sources.Where(s => dev.PackSources.Any(p => p.SourceId == s.Slug))]), ct);
        PackContent pub = AssembleCore(BuildFlavor.Public, snapshot);
        PackFile publicFile = await writer.WriteAsync(pub, PackTestData.Request(temp.Path, "2026.11.0", [.. snapshot.Sources.Where(s => pub.PackSources.Any(p => p.SourceId == s.Slug))]), ct);

        Assert.True(devFile.SelfCheck.Passed, devFile.SelfCheck.ToJson());
        Assert.True(publicFile.SelfCheck.Passed, publicFile.SelfCheck.ToJson());
        Assert.Equal(PackDigest.Compute(dev), devFile.ContentDigest);

        // dev: bes meal birimi (biri bos metinli izleyen) ve iki meal kaynagi dosyada.
        string[] devAnchors = [.. PackInspector.ReadUnitAnchors(devFile.Path).Where(a => a.StartsWith("meal:", StringComparison.Ordinal)).Order(StringComparer.Ordinal)];
        Assert.Equal(MealAnchors, devAnchors);
        Assert.Contains(OriginalSlug, PackInspector.ReadPackSources(devFile.Path));
        Assert.Contains(PlainSlug, PackInspector.ReadPackSources(devFile.Path));
        PackAttributionInfo original = PackInspector.ReadAttributions(devFile.Path).Single(a => a.SourceId == OriginalSlug);
        Assert.Equal((OriginalCredit, OriginalVersion), (original.RequiredCredit, original.Version));

        // public: yalniz onayli meal birimi ve onun kaynagi; P-10 suzmesi dosyada da gorunur.
        Assert.Equal(
            ["meal:elmalili:1:1"],
            PackInspector.ReadUnitAnchors(publicFile.Path).Where(a => a.StartsWith("meal:", StringComparison.Ordinal)));
        Assert.DoesNotContain(PlainSlug, PackInspector.ReadPackSources(publicFile.Path));
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void Meal_pack_assembly_is_culture_independent(bool turkish)
    {
        EditorialSnapshot snapshot = WithMeals();
        string baseline = PackDigest.Compute(AssembleCore(BuildFlavor.Dev, snapshot));
        string measured = string.Empty;

        Mutalaa.Domain.Tests.Support.CultureScope.For(turkish, () => measured = PackDigest.Compute(AssembleCore(BuildFlavor.Dev, snapshot)));

        Assert.Equal(baseline, measured);
    }
}
