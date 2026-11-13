using Mutalaa.Domain.Anchors;
using Mutalaa.Domain.Links;
using Mutalaa.Infrastructure.Packs;

namespace Mutalaa.Publisher.Tests;

/// <summary>PackCatalog: paket-kaynak eslemesi, capa -> paket ve baglanti yerlesimi (Icerik paketleri 4). Docker gerektirmez.</summary>
public class PackCatalogTests
{
    private static PackCatalog Catalog => PackCatalog.Default;

    [Fact]
    public void Core_maps_the_three_tanzil_sources_and_the_two_optional_meal_sources_with_distinct_roles()
    {
        PackDefinition core = Catalog.Get("core");

        Assert.True(core.Bundled);
        Assert.Empty(core.DependsOn);
        Assert.Equal(1, core.SchemaVersion);
        Assert.True(core.CarriesQuranStructure);
        Assert.Equal(
            [
                ("elmalili-meal", PackSourceRole.Content),
                ("elmalili-sade-meal", PackSourceRole.Content),
                ("qursim", PackSourceRole.Attribution),
                ("tanzil-simple-clean", PackSourceRole.Attribution),
                ("tanzil-ust-veri", PackSourceRole.Structure),
                ("tanzil-uthmani", PackSourceRole.Content),
            ],
            core.Sources.OrderBy(s => s.Slug, StringComparer.Ordinal).Select(s => (s.Slug, s.Role)));
        Assert.Equal("medine-604", core.Sources.Single(s => s.Role == PackSourceRole.Structure).PageMapLayout);
        Assert.Equal(["tanzil-uthmani", "elmalili-meal", "elmalili-sade-meal"], core.ContentSources.Select(s => s.Slug));

        // K-49: mealler istege bagli (Required: false); Tanzil kaynaklari zorunlu kalir.
        Assert.Equal(["elmalili-meal", "elmalili-sade-meal", "qursim"], core.Sources.Where(s => !s.Required).Select(s => s.Slug).Order(StringComparer.Ordinal));
        Assert.All(core.Sources.Where(s => s.Slug.StartsWith("tanzil-", StringComparison.Ordinal)), s => Assert.True(s.Required));
        Assert.Equal("Kur'an ve Elmalılı mealleri", core.Title);
    }

    [Fact]
    public void Fixture_packs_map_to_their_sources_and_dependencies()
    {
        PackDefinition kucuk = Catalog.Get("test-kucuk");
        PackDefinition tefsir = Catalog.Get("tefsir-test-ornek");

        Assert.Empty(kucuk.DependsOn);
        Assert.False(kucuk.Bundled);
        Assert.Equal(["test-kucuk"], kucuk.Sources.Select(s => s.Slug));
        Assert.Equal(["core"], tefsir.DependsOn);
        Assert.Equal(["test-tefsir-ornek"], tefsir.Sources.Select(s => s.Slug));
    }

    [Fact]
    public void Future_packs_are_listed_and_kelime_kok_is_in_the_catalog_but_audio_is_not()
    {
        Assert.Equal(["elmalili-tefsir"], Catalog.Get("tefsir-elmalili").Sources.Select(s => s.Slug));
        Assert.Equal(
            ["tecrid-ar", "tecrid-miras", "tecrid-naim"],
            Catalog.Get("hadis-tecrid").Sources.Select(s => s.Slug).Order(StringComparer.Ordinal));
        Assert.Equal(["hadis-fawaz-ar"], Catalog.Get("hadis-kutub-i-sitte").Sources.Select(s => s.Slug));
        Assert.True(Catalog.TryGet("kelime-kok", out PackDefinition? kelimeKok));
        Assert.Equal(["core"], kelimeKok.DependsOn);
        Assert.False(kelimeKok.Bundled);
        Assert.True(kelimeKok.CarriesLexicon);
        Assert.False(kelimeKok.CarriesQuranStructure);
        Assert.Equal(
            [("qac-morfoloji", PackSourceRole.Dictionary, true), ("quranwbw-tr", PackSourceRole.Attribution, false), ("kaikki-tr", PackSourceRole.Attribution, false)],
            kelimeKok.Sources.Select(s => (s.Slug, s.Role, s.Required)));
        Assert.Equal(["qac-morfoloji", "quranwbw-tr"], PackCatalog.LexiconSourceSlugs);
        Assert.DoesNotContain(Catalog.All, p => p.PackId.StartsWith("ses-", StringComparison.Ordinal));
        Assert.False(Catalog.TryGet(null, out _));
        Assert.Throws<KeyNotFoundException>(() => Catalog.Get("yok"));
    }

    [Fact]
    public void All_is_ordered_by_pack_id_ordinal_and_every_dependency_exists()
    {
        string[] ids = [.. Catalog.All.Select(p => p.PackId)];

        Assert.Equal(ids.Order(StringComparer.Ordinal), ids);
        foreach (PackDefinition pack in Catalog.All)
        {
            Assert.All(pack.DependsOn, dep => Assert.True(Catalog.TryGet(dep, out _), $"{pack.PackId} -> {dep}"));
        }
    }

    [Fact]
    public void Duplicate_pack_ids_are_rejected()
    {
        PackDefinition one = new("a", "A", false, [], []);

        Assert.Throws<ArgumentException>(() => new PackCatalog([one, one]));
    }

    [Theory]
    [InlineData("q:2:255", "core")]
    [InlineData("q:2:255:3-7", "core")]
    [InlineData("q:2:255-257", "core")]
    [InlineData("meal:elmalili:2:255", "core")]
    [InlineData("tf:elmalili:2-255-257:p3", "tefsir-elmalili")]
    [InlineData("tf:elmalili:mukaddime:p4", "tefsir-elmalili")]
    [InlineData("tf:test-ornek:2-1-3:p1", "tefsir-test-ornek")]
    [InlineData("k:test-kucuk:bolum-1:p1", "test-kucuk")]
    [InlineData("rn:sozler:soz-10:hakikat-3:p4", "risale-sozler")]
    [InlineData("h:tecrid:15", "hadis-tecrid")]
    [InlineData("ht:naim:tecrid:15", "hadis-tecrid")]
    [InlineData("h:buhari:52", "hadis-kutub-i-sitte")]
    public void PackIdForAnchor_maps_anchors_to_packs(string anchor, string expected)
    {
        Assert.Equal(expected, PackCatalog.PackIdForAnchor(anchor));
        Assert.Equal(expected, PackCatalog.PackIdForAnchor(AnchorRef.Parse(anchor)));
    }

    [Theory]
    [InlineData("konu:tevhid")]
    [InlineData("q:115:1")]
    [InlineData("")]
    [InlineData("Q:2:255")]
    public void PackIdForAnchor_returns_null_for_unpackable_anchors(string anchor)
    {
        Assert.Null(PackCatalog.PackIdForAnchor(anchor));
    }

    [Theory]
    [InlineData("q:2:255", "meal:elmalili:2:255", "core")]
    [InlineData("q:2:255:3-7", "q:3:1", "core")]
    [InlineData("q:2:255", "tf:test-ornek:2-255-255:p1", "tefsir-test-ornek")]
    [InlineData("tf:elmalili:2-255-255:p1", "q:2:255", "tefsir-elmalili")]
    [InlineData("k:test-kucuk:bolum-1:p1", "q:2:255", "test-kucuk")]
    [InlineData("q:2:255", "rn:sozler:soz-10:p1", "risale-dizin")]
    [InlineData("rn:sozler:soz-10:p1", "rn:sozler:soz-10:p2", "risale-dizin")]
    [InlineData("tf:test-ornek:2-1-3:p1", "tf:test-ornek:2-4-5:p2", "tefsir-test-ornek")]
    public void PackIdForXref_follows_the_placement_rules(string src, string dst, string expected)
    {
        Assert.Equal(expected, Catalog.PackIdForXref(src, dst));
        Assert.Equal(expected, Catalog.PackIdForXref(dst, src));
    }

    [Theory]
    [InlineData(XrefType.Kok, "q:2:255", "q:3:1", "kelime-kok")]
    [InlineData(XrefType.Lemma, "q:2:255", "q:2:256", "kelime-kok")]
    [InlineData(XrefType.BenzerAyet, "q:2:255", "q:3:1", "core")]
    [InlineData(XrefType.BenzerAyet, "q:3:1", "q:2:255", "core")]
    [InlineData(XrefType.Atif, "q:2:255", "q:3:1", "core")]
    [InlineData(XrefType.Iktibas, "q:2:255", "k:test-kucuk:bolum-1:p1", "test-kucuk")]
    [InlineData(XrefType.Atif, "q:2:255", "rn:sozler:soz-10:p1", "risale-dizin")]
    [InlineData(XrefType.BenzerAyet, "q:2:255", "tf:test-ornek:2-255-255:p1", "tefsir-test-ornek")]
    public void PackIdForXref_by_type_sends_kok_and_lemma_to_kelime_kok_and_benzer_ayet_to_core(XrefType type, string src, string dst, string expected)
    {
        Assert.Equal(expected, Catalog.PackIdForXref(type, src, dst));
    }

    [Fact]
    public void PackIdForXref_by_type_returns_null_when_an_end_is_not_packable()
    {
        Assert.Null(Catalog.PackIdForXref(XrefType.Kok, "q:2:255", "konu:tevhid"));
        Assert.Null(Catalog.PackIdForXref(XrefType.BenzerAyet, "???", "q:2:255"));
    }

    [Fact]
    public void PackIdForXref_between_two_independent_optional_packs_picks_the_later_pack_id()
    {
        // tefsir-elmalili ve tefsir-test-ornek ikisi de core'a bagli; birbirine bagli degil: alfabetik olarak sonra gelen.
        Assert.Equal(
            "tefsir-test-ornek",
            Catalog.PackIdForXref("tf:elmalili:2-255-255:p1", "tf:test-ornek:2-255-255:p1"));
    }

    [Fact]
    public void PackIdForXref_prefers_the_dependent_pack_even_when_it_sorts_first()
    {
        PackCatalog custom = new(
        [
            new PackDefinition("tefsir-aaa", "A", false, ["tefsir-zzz"], []),
            new PackDefinition("tefsir-zzz", "Z", false, [], []),
        ]);

        Assert.Equal("tefsir-aaa", custom.PackIdForXref("tf:aaa:2-1-1:p1", "tf:zzz:2-1-1:p1"));
        Assert.Equal("tefsir-aaa", custom.PackIdForXref("tf:zzz:2-1-1:p1", "tf:aaa:2-1-1:p1"));
    }

    [Fact]
    public void PackIdForXref_returns_null_when_an_end_is_not_packable()
    {
        Assert.Null(Catalog.PackIdForXref("q:2:255", "konu:tevhid"));
        Assert.Null(Catalog.PackIdForXref("???", "q:2:255"));
    }
}
