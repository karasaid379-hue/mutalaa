using System.Globalization;
using System.Text.RegularExpressions;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata;
using Mutalaa.Api.Tests.Support;
using Mutalaa.Domain.Anchors;
using Mutalaa.Domain.Tests.Support;
using Mutalaa.Infrastructure.Persistence;
using Npgsql.EntityFrameworkCore.PostgreSQL.Metadata;

namespace Mutalaa.Api.Tests;

/// <summary>
/// IcerikDbContext modeli (veritabani ve Docker gerektirmez): tablo sayilari, ad politikasi (K-37 madde 4), capa sutunlarinda
/// COLLATE "C", 11 PostgreSQL enum turu ve etiket sirasi, xmin, uretilen arama sutunlari.
/// Her sinama hem varsayilan modelde hem model onbellegi atlanarak, tr-TR kulturunde yeniden kurulan modelde kosar.
/// </summary>
public partial class ModelNamingTests
{
    private const string ContentSchema = "icerik";
    private const string IdentitySchema = "kimlik";

    private static readonly string[] IdentityTables =
        ["role_claims", "roles", "user_claims", "user_logins", "user_roles", "user_tokens", "users"];

    [GeneratedRegex("^[a-z0-9_]+$", RegexOptions.CultureInvariant)]
    private static partial Regex SnakeCase();

    /// <summary>Varsayilan ve tr-TR kulturunde yeniden kurulmus modelde ayni sinama.</summary>
    private static void OnAllModels(Action<IModel> verify)
    {
        ModelFactory.ForEachModel(verify);
        CultureScope.Turkish(() =>
        {
            verify(ModelFactory.CreateModel(uncachedModel: true));
        });
    }

    private static string Schema(IEntityType entityType, IModel model) =>
        entityType.GetSchema() ?? model.GetDefaultSchema() ?? string.Empty;

    private static IEnumerable<IEntityType> TableEntities(IModel model, string schema) =>
        model.GetEntityTypes().Where(e => e.GetTableName() is not null && string.Equals(Schema(e, model), schema, StringComparison.Ordinal));

    [Fact]
    public void Content_schema_has_19_tables_and_identity_schema_7()
    {
        OnAllModels(model =>
        {
            string[] content = [.. TableEntities(model, ContentSchema).Select(e => e.GetTableName()!).Order(StringComparer.Ordinal)];
            string[] identity = [.. TableEntities(model, IdentitySchema).Select(e => e.GetTableName()!).Order(StringComparer.Ordinal)];

            Assert.Equal(19, content.Length);
            Assert.Equal(content.Length, content.Distinct(StringComparer.Ordinal).Count());
            Assert.Equal(IdentityTables, identity);
            Assert.Equal(26, model.GetEntityTypes().Count());
        });
    }

    [Fact]
    public void Content_tables_match_the_ddl_table_list()
    {
        string[] fromDoc = [.. EditorialDoc.ParseTables(EditorialDoc.SqlBlocks(EditorialDoc.Read()))
            .Select(t => t.Name)
            .Where(n => n is not "xref_vote" and not "embedding")
            .Order(StringComparer.Ordinal)];

        OnAllModels(model =>
        {
            string[] fromModel = [.. TableEntities(model, ContentSchema).Select(e => e.GetTableName()!).Order(StringComparer.Ordinal)];
            Assert.Equal(fromDoc, fromModel);
        });
    }

    [Fact]
    public void All_names_are_lower_snake_case()
    {
        OnAllModels(model =>
        {
            List<string> bad = [];
            foreach (IEntityType entityType in model.GetEntityTypes())
            {
                string table = entityType.GetTableName()!;
                string schema = Schema(entityType, model);
                StoreObjectIdentifier store = StoreObjectIdentifier.Table(table, schema);
                List<string> names = [schema, table];
                names.AddRange(entityType.GetProperties().Select(p => p.GetColumnName(store)!));
                names.AddRange(entityType.GetKeys().Select(k => k.GetName()!));
                names.AddRange(entityType.GetForeignKeys().Select(f => f.GetConstraintName()!));
                names.AddRange(entityType.GetIndexes().Select(i => i.GetDatabaseName()!));
                names.AddRange(entityType.GetCheckConstraints().Select(c => c.Name!));
                bad.AddRange(names.Where(n => !SnakeCase().IsMatch(n)).Select(n => $"{schema}.{table}: {n}"));
            }

            bad.AddRange(model.GetPostgresEnums().Select(e => e.Name).Where(n => !SnakeCase().IsMatch(n)));
            Assert.Empty(bad);
        });
    }

    [Fact]
    public void Content_schema_uses_postgresql_default_constraint_names()
    {
        OnAllModels(model =>
        {
            List<string> problems = [];
            foreach (IEntityType entityType in TableEntities(model, ContentSchema))
            {
                string table = entityType.GetTableName()!;
                StoreObjectIdentifier store = StoreObjectIdentifier.Table(table, ContentSchema);

                string? pk = entityType.FindPrimaryKey()!.GetName();
                if (!string.Equals(pk, table + "_pkey", StringComparison.Ordinal))
                {
                    problems.Add($"{table}: PK adi '{pk}'");
                }

                foreach (IForeignKey fk in entityType.GetForeignKeys())
                {
                    string columns = string.Join('_', fk.Properties.Select(p => p.GetColumnName(store)));
                    string expected = $"{table}_{columns}_fkey";
                    if (!string.Equals(fk.GetConstraintName(), expected, StringComparison.Ordinal))
                    {
                        problems.Add($"{table}: FK adi '{fk.GetConstraintName()}', beklenen '{expected}'");
                    }
                }

                foreach (IIndex index in entityType.GetIndexes())
                {
                    string name = index.GetDatabaseName()!;
                    if (!name.StartsWith(table + "_", StringComparison.Ordinal))
                    {
                        problems.Add($"{table}: dizin adi '{name}' tablo adiyla baslamiyor");
                    }

                    if (index.IsUnique && !name.EndsWith("_key", StringComparison.Ordinal))
                    {
                        problems.Add($"{table}: tekil dizin '{name}' _key ile bitmiyor");
                    }
                }

                string[] forbidden = ["pk_", "fk_", "ix_"];
                IEnumerable<string> all = entityType.GetKeys().Select(k => k.GetName()!)
                    .Concat(entityType.GetForeignKeys().Select(f => f.GetConstraintName()!))
                    .Concat(entityType.GetIndexes().Select(i => i.GetDatabaseName()!));
                problems.AddRange(all
                    .Where(n => forbidden.Any(p => n.StartsWith(p, StringComparison.Ordinal)))
                    .Select(n => $"{table}: yasak onek: {n}"));

                foreach (ICheckConstraint check in entityType.GetCheckConstraints())
                {
                    if (!check.Name!.StartsWith(table + "_", StringComparison.Ordinal) || !check.Name!.EndsWith("_check", StringComparison.Ordinal))
                    {
                        problems.Add($"{table}: CHECK adi '{check.Name}'");
                    }
                }
            }

            Assert.Empty(problems);
        });
    }

    [Fact]
    public void Documented_check_constraints_exist_with_their_names()
    {
        string[] expected =
        [
            "unit_role_check", "unit_content_hash_check", "lemma_lang_check", "quran_word_fix_field_check",
            "surah_alias_surah_no_check", "surah_alias_kind_check", "xref_score_check", "xref_confidence_check",
            "review_hedef_tablo_check", "page_map_line_type_check", "pipeline_run_durum_check",
            "source_check", "unit_check", "quran_word_check", "tr_root_index_check", "ayah_box_check", "audio_timing_check",
            "review_yz_kaydi_check",
        ];

        OnAllModels(model =>
        {
            string[] actual = [.. TableEntities(model, ContentSchema)
                .SelectMany(e => e.GetCheckConstraints().Select(c => c.Name!))
                .Order(StringComparer.Ordinal)];
            Assert.Equal([.. expected.Order(StringComparer.Ordinal)], actual);
        });
    }

    [Fact]
    public void Documented_indexes_exist_and_no_foreign_key_indexes_were_added()
    {
        string[] expected =
        [
            "unit_anchor_key", "unit_source_ord", "unit_parent", "unit_ayah", "unit_tsv_tr", "unit_tsv_ar",
            "root_letters_key", "quran_word_surah_ayah_word_key", "quran_word_root", "quran_word_lemma", "quran_word_ayah",
            "quran_word_fix_anchor_field_key", "tr_root_index_root", "tr_form_wide",
            "xref_src", "xref_dst", "xref_queue", "review_queue", "review_xref",
            "page_map_start", "page_map_source_id_volume_page_line_key", "release_surum_derleme_key",
        ];

        OnAllModels(model =>
        {
            string[] actual = [.. TableEntities(model, ContentSchema)
                .SelectMany(e => e.GetIndexes().Select(i => i.GetDatabaseName()!))
                .Order(StringComparer.Ordinal)];
            Assert.Equal([.. expected.Order(StringComparer.Ordinal)], actual);

            // xref_natural_key EF ile ifade edilmez; goce ham SQL olarak eklenir. Modelde xref icin tekil dizin olmamali.
            IEntityType xref = TableEntities(model, ContentSchema).Single(e => e.GetTableName() == "xref");
            Assert.DoesNotContain(xref.GetIndexes(), i => i.IsUnique);
        });
    }

    [Fact]
    public void Partial_gist_gin_and_nulls_not_distinct_indexes_are_configured()
    {
        OnAllModels(model =>
        {
            IIndex Find(string name) => model.GetEntityTypes()
                .SelectMany(e => e.GetIndexes())
                .Single(i => string.Equals(i.GetDatabaseName(), name, StringComparison.Ordinal));

            Assert.Equal("gist", Find("unit_ayah").GetMethod());
            Assert.Equal("gin", Find("unit_tsv_tr").GetMethod());
            Assert.Equal("gin", Find("unit_tsv_ar").GetMethod());
            Assert.Equal("status = 'aday'", Find("xref_queue").GetFilter());
            Assert.Equal([false, true], Find("xref_queue").IsDescending);
            Assert.Equal("durum = 'acik'", Find("review_queue").GetFilter());
            Assert.Equal("xref_id IS NOT NULL", Find("review_xref").GetFilter());
            Assert.Equal(false, Find("page_map_source_id_volume_page_line_key").GetAreNullsDistinct());
        });
    }

    [Fact]
    public void Every_anchor_ref_column_uses_the_c_collation_and_matches_the_ddl()
    {
        // DDL'de COLLATE "C" yazan sutun adlari (embedding v1.x tablosunun 'anchor' sutunu haric).
        string sql = EditorialDoc.StripComments(EditorialDoc.SqlBlocks(EditorialDoc.Read()));
        List<string> fromDdl = [.. CollatedColumn().Matches(sql).Select(m => m.Groups["col"].Value)];
        Assert.True(fromDdl.Remove("anchor"), "embedding.anchor bulunamadi");

        OnAllModels(model =>
        {
            List<string> collated = [];
            foreach (IEntityType entityType in TableEntities(model, ContentSchema))
            {
                StoreObjectIdentifier store = StoreObjectIdentifier.Table(entityType.GetTableName()!, ContentSchema);
                foreach (IProperty property in entityType.GetProperties())
                {
                    bool collatedC = string.Equals(property.GetCollation(), "C", StringComparison.Ordinal);
                    if (property.ClrType == typeof(AnchorRef))
                    {
                        Assert.True(collatedC, $"{entityType.GetTableName()}.{property.Name} C collation tasimiyor");
                    }

                    if (collatedC)
                    {
                        collated.Add(property.GetColumnName(store)!);
                    }
                }
            }

            Assert.Equal([.. fromDdl.Order(StringComparer.Ordinal)], [.. collated.Order(StringComparer.Ordinal)]);
        });
    }

    [GeneratedRegex(@"(?<col>[a-z0-9_]+)[ ]+text COLLATE ""C""", RegexOptions.CultureInvariant)]
    private static partial Regex CollatedColumn();

    [Fact]
    public void Eleven_postgres_enums_exist_with_the_json_label_order()
    {
        Dictionary<string, string[]> json = EnumsJson.Load();

        OnAllModels(model =>
        {
            var enums = model.GetPostgresEnums().ToList();
            Assert.Equal(11, enums.Count);
            Assert.All(enums, e => Assert.Equal(ContentSchema, e.Schema));
            Assert.Equal(
                [.. json.Keys.Order(StringComparer.Ordinal)],
                [.. enums.Select(e => e.Name).Order(StringComparer.Ordinal)]);
            foreach (var pgEnum in enums)
            {
                Assert.Equal(json[pgEnum.Name], pgEnum.Labels.ToArray());
            }

            // Npgsql MapEnum etiketleri alfabetik dizer (efcore.pg #3667); sira bizim verdigimiz sayisal sira olmali.
            Assert.Equal(
                ["serbest", "bekliyor", "ic_kullanim", "kapali"],
                [.. enums.Single(e => e.Name == "license_status").Labels]);
        });
    }

    [Fact]
    public void Every_content_entity_has_an_xmin_row_version()
    {
        OnAllModels(model =>
        {
            foreach (IEntityType entityType in TableEntities(model, ContentSchema))
            {
                IProperty? xmin = entityType.FindProperty("xmin");
                Assert.True(xmin is not null, $"{entityType.GetTableName()}: xmin yok");
                Assert.True(xmin.IsShadowProperty(), $"{entityType.GetTableName()}: xmin gercek ozellik");
                Assert.True(xmin.IsConcurrencyToken);
                Assert.Equal(typeof(uint), xmin.ClrType);
                Assert.Equal("xid", xmin.GetColumnType());
                Assert.Equal("xmin", xmin.GetColumnName(StoreObjectIdentifier.Table(entityType.GetTableName()!, ContentSchema)));
                Assert.Equal(ValueGenerated.OnAddOrUpdate, xmin.ValueGenerated);
            }
        });
    }

    [Fact]
    public void Search_vectors_are_stored_computed_columns()
    {
        OnAllModels(model =>
        {
            IEntityType unit = TableEntities(model, ContentSchema).Single(e => e.GetTableName() == "unit");
            StoreObjectIdentifier store = StoreObjectIdentifier.Table("unit", ContentSchema);

            IProperty tr = unit.GetProperties().Single(p => p.GetColumnName(store) == "tsv_tr");
            IProperty ar = unit.GetProperties().Single(p => p.GetColumnName(store) == "tsv_ar");
            Assert.Equal("to_tsvector('turkish', coalesce(tr_narrow, ''))", tr.GetComputedColumnSql());
            Assert.Equal("to_tsvector('arabic', coalesce(ar_norm, ''))", ar.GetComputedColumnSql());
            Assert.True(tr.GetIsStored());
            Assert.True(ar.GetIsStored());
            Assert.Equal("tsvector", tr.GetColumnType());
        });
    }

    [Fact]
    public void Identity_columns_and_key_generation_follow_the_ddl()
    {
        OnAllModels(model =>
        {
            foreach ((string table, string property) in new[] { ("unit", "Id"), ("review", "Id"), ("page_map", "Id"), ("release", "Id") })
            {
                IProperty p = TableEntities(model, ContentSchema).Single(e => e.GetTableName() == table).FindProperty(property)!;
                Assert.Equal(NpgsqlValueGenerationStrategy.IdentityAlwaysColumn, p.GetValueGenerationStrategy(StoreObjectIdentifier.Table(table, ContentSchema)));
            }

            foreach ((string table, string property) in new[] { ("root", "Id"), ("lemma", "Id"), ("pipeline_run", "RunId") })
            {
                IProperty p = TableEntities(model, ContentSchema).Single(e => e.GetTableName() == table).FindProperty(property)!;
                Assert.Equal(ValueGenerated.Never, p.ValueGenerated);
            }

            foreach (string table in new[] { "xref", "quran_word_fix" })
            {
                IProperty p = TableEntities(model, ContentSchema).Single(e => e.GetTableName() == table).FindProperty("Id")!;
                Assert.Equal("uuidv7()", p.GetDefaultValueSql());
                Assert.Equal(ValueGenerated.OnAdd, p.ValueGenerated);
            }
        });
    }

    [Fact]
    public void Content_foreign_keys_do_not_cascade_and_identity_foreign_keys_do()
    {
        OnAllModels(model =>
        {
            foreach (IEntityType entityType in TableEntities(model, ContentSchema))
            {
                Assert.All(entityType.GetForeignKeys(), fk => Assert.Equal(DeleteBehavior.NoAction, fk.DeleteBehavior));
            }

            IEntityType userClaims = TableEntities(model, IdentitySchema).Single(e => e.GetTableName() == "user_claims");
            Assert.All(userClaims.GetForeignKeys(), fk => Assert.Equal(DeleteBehavior.Cascade, fk.DeleteBehavior));
        });
    }

    [Fact]
    public void Identity_foreign_key_indexes_are_added_by_hand()
    {
        OnAllModels(model =>
        {
            string[] expected =
            [
                "ix_role_claims_role_id", "ix_roles_normalized_name", "ix_user_claims_user_id", "ix_user_logins_user_id",
                "ix_user_roles_role_id", "ix_users_normalized_email", "ix_users_normalized_user_name",
            ];
            string[] actual = [.. TableEntities(model, IdentitySchema)
                .SelectMany(e => e.GetIndexes().Select(i => i.GetDatabaseName()!))
                .Order(StringComparer.Ordinal)];
            Assert.Equal(expected, actual);
        });
    }

    [Fact]
    public void Model_is_identical_in_turkish_culture_without_model_cache()
    {
        string[] baseline = Dump(ModelFactory.CreateModel(uncachedModel: false));

        string[] turkish = [];
        CultureScope.Turkish(() =>
        {
            turkish = Dump(ModelFactory.CreateModel(uncachedModel: true));
        });

        Assert.Equal(baseline, turkish);
        Assert.Contains("enum|icerik.license_status|serbest,bekliyor,ic_kullanim,kapali", baseline);
        Assert.True(baseline.Length > 200);
    }

    /// <summary>Modelin adlandirma ve tur yuzeyini sirali metin satirlari olarak dokumler.</summary>
    private static string[] Dump(IModel model)
    {
        List<string> lines = [];
        foreach (IEntityType entityType in model.GetEntityTypes())
        {
            string table = entityType.GetTableName()!;
            string schema = Schema(entityType, model);
            StoreObjectIdentifier store = StoreObjectIdentifier.Table(table, schema);
            string prefix = $"{schema}.{table}";
            lines.AddRange(entityType.GetProperties().Select(p =>
                string.Create(CultureInfo.InvariantCulture, $"{prefix}|col|{p.GetColumnName(store)}|{p.GetColumnType()}|{p.IsNullable}|{p.GetCollation()}|{p.GetDefaultValueSql()}")));
            lines.AddRange(entityType.GetKeys().Select(k => $"{prefix}|key|{k.GetName()}"));
            lines.AddRange(entityType.GetForeignKeys().Select(f => $"{prefix}|fk|{f.GetConstraintName()}"));
            lines.AddRange(entityType.GetIndexes().Select(i => $"{prefix}|ix|{i.GetDatabaseName()}|{i.GetFilter()}"));
            lines.AddRange(entityType.GetCheckConstraints().Select(c => $"{prefix}|ck|{c.Name}|{c.Sql}"));
        }

        lines.AddRange(model.GetPostgresEnums().Select(e => $"enum|{e.Schema}.{e.Name}|{string.Join(',', e.Labels)}"));
        return [.. lines.Order(StringComparer.Ordinal)];
    }
}
