using Mutalaa.Api.Tests.Support;
using Mutalaa.Infrastructure.Packs;

namespace Mutalaa.Publisher.Tests;

/// <summary>PackDefinitions: paketler.json okuyucusu (A13.3). Docker gerektirmez.</summary>
public class PackDefinitionsTests
{
    [Theory]
    [InlineData("core", "core")]
    [InlineData("test-kucuk", "metin")]
    [InlineData("tefsir-test-ornek", "metin")]
    [InlineData("tefsir-elmalili", "metin")]
    [InlineData("hadis-tecrid", "metin")]
    [InlineData("risale-sozler", "risale-kitap")]
    [InlineData("risale-dizin", "risale-dizin")]
    [InlineData("kelime-kok", "kelime-kok")]
    [InlineData("mushaf-a-cuz-30", "mushaf-a-cuz")]
    [InlineData("ses-zaman-alafasy", "ses-zaman")]
    public void Resolve_returns_exactly_one_type(string packId, string expected)
    {
        PackDefinitions definitions = PackTestData.Definitions();

        Assert.Equal(expected, definitions.Resolve(packId).Name);
    }

    [Theory]
    [InlineData("")]
    [InlineData("Core")]
    [InlineData("core\n")]
    [InlineData("test-")]
    [InlineData("test_kucuk")]
    [InlineData("mushaf-a-cuz-31")]
    [InlineData("bilinmeyen")]
    [InlineData("../core")]
    public void Resolve_rejects_ids_matching_no_type(string packId)
    {
        PackDefinitions definitions = PackTestData.Definitions();

        Assert.Throws<PackDefinitionException>(() => definitions.Resolve(packId));
        Assert.False(definitions.TryResolve(packId, out _));
    }

    [Fact]
    public void Resolve_rejects_an_id_matching_two_types()
    {
        const string json = """
            {"version":1,"turler":{
              "a":{"desen":"^x-[a-z]+$","ddl":[],"sonra":[]},
              "b":{"desen":"^x-y$","ddl":[],"sonra":[]}}}
            """;
        PackDefinitions definitions = PackDefinitions.Parse(json, RepoFiles.PathOf(PackTestData.SchemaDirRelative));

        PackDefinitionException ex = Assert.Throws<PackDefinitionException>(() => definitions.Resolve("x-y"));

        Assert.Contains("birden fazla", ex.Message, StringComparison.Ordinal);
        Assert.Equal("a", definitions.Resolve("x-z").Name);
    }

    [Fact]
    public void Types_follow_the_json_order_and_carry_ddl_and_after_lists()
    {
        PackDefinitions definitions = PackTestData.Definitions();

        Assert.Equal(1, definitions.Version);
        Assert.Equal(
            ["core", "metin", "risale-kitap", "risale-dizin", "kelime-kok", "mushaf-a-cuz", "mushaf-b", "ses-katalog", "ses-zaman"],
            definitions.Types.Select(t => t.Name));
        PackType metin = definitions.Resolve("test-kucuk");
        Assert.Equal("^(tefsir|hadis|test)-[a-z0-9-]+$", metin.Pattern);
        Assert.Contains("10-metin.sql", metin.Ddl);
        Assert.Equal(["29-arama-sonrasi.sql"], metin.After);
    }

    [Fact]
    public void Load_resolves_a_relative_schema_dir_against_the_working_directory()
    {
        string absolute = RepoFiles.PathOf(PackTestData.SchemaDirRelative);
        string relative = Path.GetRelativePath(Directory.GetCurrentDirectory(), absolute);

        PackDefinitions definitions = PackDefinitions.Load(relative);

        Assert.True(Path.IsPathRooted(definitions.SchemaDir));
        Assert.Equal(Path.GetFullPath(absolute), definitions.SchemaDir);
        Assert.Contains("CREATE TABLE unit", definitions.ReadSql("10-metin.sql"), StringComparison.Ordinal);
    }

    [Fact]
    public void Load_throws_for_a_missing_directory_and_ReadSql_rejects_paths()
    {
        using PackTestData.TempDir temp = new();

        Assert.Throws<PackDefinitionException>(() => PackDefinitions.Load(temp.Path));
        PackDefinitions definitions = PackTestData.Definitions();
        Assert.Throws<PackDefinitionException>(() => definitions.ReadSql("../paketler.json"));
        Assert.Throws<PackDefinitionException>(() => definitions.ReadSql("yok.sql"));
    }

    [Fact]
    public void ExpectedTables_are_derived_by_running_the_ddl()
    {
        PackDefinitions definitions = PackTestData.Definitions();

        IReadOnlyList<string> core = definitions.ExpectedTables(definitions.Resolve("core"));
        IReadOnlyList<string> metin = definitions.ExpectedTables(definitions.Resolve("test-kucuk"));

        string[] expectedCore = ["attribution", "page_map", "pack_meta", "pack_source", "quran_marker", "quran_word", "sure", "unit", "unit_fts", "unit_search", "unit_tri", "xref_idx"];
        Assert.Equal(expectedCore.Order(StringComparer.Ordinal), core);
        Assert.Contains("tr_root_index", metin);
        Assert.DoesNotContain("quran_word", metin);
    }

    [Fact]
    public void Every_catalog_pack_resolves_to_exactly_one_type()
    {
        PackDefinitions definitions = PackTestData.Definitions();

        foreach (PackDefinition pack in PackCatalog.Default.All)
        {
            Assert.True(definitions.TryResolve(pack.PackId, out PackType? type), pack.PackId);
            Assert.NotNull(type);
        }
    }
}
