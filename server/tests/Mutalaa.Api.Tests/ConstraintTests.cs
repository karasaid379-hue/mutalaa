using Microsoft.EntityFrameworkCore;
using Mutalaa.Api.Tests.Support;
using Mutalaa.Domain.Anchors;
using Mutalaa.Domain.Content;
using Mutalaa.Domain.Links;
using Mutalaa.Domain.Reviews;
using Mutalaa.Infrastructure.Persistence;
using Npgsql;

namespace Mutalaa.Api.Tests;

/// <summary>
/// CHECK, UNIQUE ve uretilen sutun kisitlari (Docker'li). Her test kendi islemini acar ve sonunda geri alir;
/// hem SqlState (23514 check, 23505 unique) hem ConstraintName dogrulanir. Yazma yolu gercek EF INSERT'idir.
/// </summary>
public class ConstraintTests(EditorialDatabase<ConstraintTests> fixture) : IClassFixture<EditorialDatabase<ConstraintTests>>
{
    private const string Check = "23514";
    private const string Unique = "23505";

    private TestDatabase Db => fixture.Database;

    private static async Task<Source> AddSourceAsync(IcerikDbContext context, CancellationToken ct, Action<Source>? configure = null)
    {
        Source source = TestData.NewSource();
        configure?.Invoke(source);
        context.Add(source);
        await context.SaveChangesAsync(ct);
        return source;
    }

    // --- unit_content_hash_check ---

    [Theory]
    [InlineData("xyz")]
    [InlineData("ABCDEF0123456789ABCDEF0123456789ABCDEF0123456789ABCDEF0123456789")]
    [InlineData("0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcde")]
    [InlineData("0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdeg")]
    public async Task Unit_content_hash_check_rejects_a_malformed_digest(string digest)
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using RollbackSession session = await Db.OpenRollbackSessionAsync(ct);
        Source source = await AddSourceAsync(session.Context, ct);
        Unit unit = TestData.NewUnit(source.Slug, "rn:sozler:soz-10:p1");
        unit.ContentHash = digest;
        session.Context.Add(unit);

        await TestData.ExpectViolationAsync(Check, "unit_content_hash_check", () => session.Context.SaveChangesAsync(ct));
    }

    [Fact]
    public async Task Unit_content_hash_check_accepts_64_lowercase_hex_characters()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using RollbackSession session = await Db.OpenRollbackSessionAsync(ct);
        Source source = await AddSourceAsync(session.Context, ct);
        Unit unit = TestData.NewUnit(source.Slug, "rn:sozler:soz-10:p1");
        unit.ContentHash = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef";
        session.Context.Add(unit);

        await session.Context.SaveChangesAsync(ct);

        Assert.True(unit.Id > 0);
    }

    // --- source_check (Kurul onayi) ---

    private const string ValidBoardApproval = "{\"onay_no\":\"test-1\",\"onayli_surum\":\"1\"}";

    [Fact]
    public async Task Source_check_rejects_a_board_approval_without_a_date()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using RollbackSession session = await Db.OpenRollbackSessionAsync(ct);
        Source source = TestData.NewSource();
        source.KurulOnay = ValidBoardApproval;
        source.KurulOnayOzeti = TestData.Hash();
        session.Context.Add(source);

        await TestData.ExpectViolationAsync(Check, "source_check", () => session.Context.SaveChangesAsync(ct));
    }

    [Fact]
    public async Task Source_check_rejects_a_board_approval_without_a_digest()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using RollbackSession session = await Db.OpenRollbackSessionAsync(ct);
        Source source = TestData.NewSource();
        source.KurulOnay = ValidBoardApproval;
        source.KurulOnayTarihi = new DateOnly(2026, 10, 26);
        session.Context.Add(source);

        await TestData.ExpectViolationAsync(Check, "source_check", () => session.Context.SaveChangesAsync(ct));
    }

    [Fact]
    public async Task Source_check_rejects_a_board_approval_missing_a_required_key()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using RollbackSession session = await Db.OpenRollbackSessionAsync(ct);
        Source source = TestData.NewSource();
        source.KurulOnay = "{\"onay_no\":\"test-1\"}";
        source.KurulOnayTarihi = new DateOnly(2026, 10, 26);
        source.KurulOnayOzeti = TestData.Hash();
        session.Context.Add(source);

        await TestData.ExpectViolationAsync(Check, "source_check", () => session.Context.SaveChangesAsync(ct));
    }

    [Fact]
    public async Task Source_check_accepts_a_complete_board_approval_and_a_row_without_one()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using RollbackSession session = await Db.OpenRollbackSessionAsync(ct);
        Source approved = TestData.NewSource();
        approved.KurulOnay = ValidBoardApproval;
        approved.KurulOnayTarihi = new DateOnly(2026, 10, 26);
        approved.KurulOnayOzeti = TestData.Hash();
        Source plain = TestData.NewSource();
        session.Context.AddRange(approved, plain);

        await session.Context.SaveChangesAsync(ct);

        Assert.Equal(2L, await session.ScalarAsync<long>("SELECT count(*) FROM icerik.source WHERE slug = ANY(@slugs)", ct, ("slugs", new[] { approved.Slug, plain.Slug })));
    }

    // --- unit_check (kullanim disi birim halef ister) ---

    [Fact]
    public async Task Unit_check_rejects_a_retired_unit_without_successors()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using RollbackSession session = await Db.OpenRollbackSessionAsync(ct);
        Source source = await AddSourceAsync(session.Context, ct);
        Unit unit = TestData.NewUnit(source.Slug, "rn:sozler:soz-10:p1");
        unit.Status = UnitStatus.KullanimDisi;
        unit.Successors = null;
        session.Context.Add(unit);

        await TestData.ExpectViolationAsync(Check, "unit_check", () => session.Context.SaveChangesAsync(ct));
    }

    [Fact]
    public async Task Unit_check_accepts_a_retired_unit_with_successors_and_an_active_unit_without()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using RollbackSession session = await Db.OpenRollbackSessionAsync(ct);
        Source source = await AddSourceAsync(session.Context, ct);
        Unit retired = TestData.NewUnit(source.Slug, "rn:sozler:soz-10:p1");
        retired.Status = UnitStatus.KullanimDisi;
        retired.Successors = "[{\"anchor\":\"rn:sozler:soz-10:p2\",\"from\":0,\"to\":10,\"delta\":0}]";
        Unit active = TestData.NewUnit(source.Slug, "rn:sozler:soz-10:p2");
        session.Context.AddRange(retired, active);

        await session.Context.SaveChangesAsync(ct);

        Assert.Equal(2L, await session.ScalarAsync<long>("SELECT count(*) FROM icerik.unit WHERE source_id = @s", ct, ("s", source.Slug)));
    }

    // --- xref_natural_key ---

    [Fact]
    public async Task Xref_natural_key_rejects_a_duplicate_with_null_spans()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using RollbackSession session = await Db.OpenRollbackSessionAsync(ct);
        session.Context.Add(TestData.NewXref());
        await session.Context.SaveChangesAsync(ct);

        session.Context.Add(TestData.NewXref());

        await TestData.ExpectViolationAsync(Unique, "xref_natural_key", () => session.Context.SaveChangesAsync(ct));
    }

    [Fact]
    public async Task Xref_natural_key_accepts_a_different_type_and_different_spans()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using RollbackSession session = await Db.OpenRollbackSessionAsync(ct);
        session.Context.Add(TestData.NewXref());
        await session.Context.SaveChangesAsync(ct);

        Xref otherType = TestData.NewXref(type: XrefType.Iktibas);
        Xref withSpan = TestData.NewXref();
        withSpan.SrcSpan = new AnchorSpan(3, 8);
        session.Context.AddRange(otherType, withSpan);
        await session.Context.SaveChangesAsync(ct);

        Assert.Equal(3L, await session.ScalarAsync<long>("SELECT count(*) FROM icerik.xref", ct));
    }

    [Fact]
    public async Task Xref_natural_key_rejects_a_duplicate_with_equal_non_null_spans()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using RollbackSession session = await Db.OpenRollbackSessionAsync(ct);
        Xref first = TestData.NewXref();
        first.SrcSpan = new AnchorSpan(3, 8);
        first.DstSpan = new AnchorSpan(0, 5);
        session.Context.Add(first);
        await session.Context.SaveChangesAsync(ct);

        Xref second = TestData.NewXref();
        second.SrcSpan = new AnchorSpan(3, 8);
        second.DstSpan = new AnchorSpan(0, 5);
        session.Context.Add(second);

        await TestData.ExpectViolationAsync(Unique, "xref_natural_key", () => session.Context.SaveChangesAsync(ct));
    }

    [Fact]
    public async Task Xref_natural_key_treats_one_null_span_and_one_set_span_as_different()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using RollbackSession session = await Db.OpenRollbackSessionAsync(ct);
        Xref first = TestData.NewXref();
        first.DstSpan = new AnchorSpan(0, 5);
        session.Context.Add(first);
        await session.Context.SaveChangesAsync(ct);

        session.Context.Add(TestData.NewXref());
        await session.Context.SaveChangesAsync(ct);

        Assert.Equal(2L, await session.ScalarAsync<long>("SELECT count(*) FROM icerik.xref", ct));
    }

    // --- quran_word_check ---

    private static QuranWord NewWord(int start, int end) => new()
    {
        Anchor = AnchorRef.Parse("q:2:255:3"),
        Surah = 2,
        Ayah = 255,
        Word = 3,
        AyahIndex = 262,
        TextUthmani = "kelime-3",
        Norm = "kelime-3",
        CharStart = start,
        CharEnd = end,
        SourceId = string.Empty,
        DataVersion = "test",
    };

    [Theory]
    [InlineData(5, 5)]
    [InlineData(7, 3)]
    public async Task Quran_word_check_rejects_char_start_not_below_char_end(int start, int end)
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using RollbackSession session = await Db.OpenRollbackSessionAsync(ct);
        Source source = await AddSourceAsync(session.Context, ct);
        QuranWord word = NewWord(start, end);
        word.SourceId = source.Slug;
        session.Context.Add(word);

        await TestData.ExpectViolationAsync(Check, "quran_word_check", () => session.Context.SaveChangesAsync(ct));
    }

    [Fact]
    public async Task Quran_word_check_accepts_char_start_below_char_end()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using RollbackSession session = await Db.OpenRollbackSessionAsync(ct);
        Source source = await AddSourceAsync(session.Context, ct);
        QuranWord word = NewWord(3, 7);
        word.SourceId = source.Slug;
        session.Context.Add(word);

        await session.Context.SaveChangesAsync(ct);

        Assert.Equal(1L, await session.ScalarAsync<long>("SELECT count(*) FROM icerik.quran_word WHERE anchor = 'q:2:255:3'", ct));
    }

    // --- review_yz_kaydi_check (K-37) ---

    private static string YzRecord(string? promptSha = null, string? inputSha = null) =>
        $"{{\"prompt_id\":\"p1\",\"prompt_sha256\":\"{promptSha ?? TestData.Hash('a')}\",\"input_sha256\":\"{inputSha ?? TestData.Hash('b')}\"}}";

    public static TheoryData<string, string?, string?, bool> YzCases => new()
    {
        { "both_null", null, null, true },
        { "valid", "test-modeli", YzRecord(), true },
        { "model_without_record", "test-modeli", null, false },
        { "record_without_model", null, YzRecord(), false },
        { "json_array", "test-modeli", "[]", false },
        { "json_scalar", "test-modeli", "\"metin\"", false },
        { "prompt_sha_null", "test-modeli", "{\"prompt_id\":\"p1\",\"prompt_sha256\":null,\"input_sha256\":\"" + TestData.Hash('b') + "\"}", false },
        { "prompt_sha_missing", "test-modeli", "{\"prompt_id\":\"p1\",\"input_sha256\":\"" + TestData.Hash('b') + "\"}", false },
        { "prompt_sha_short", "test-modeli", YzRecord(promptSha: "abc"), false },
        { "prompt_sha_uppercase", "test-modeli", YzRecord(promptSha: TestData.Hash('A')), false },
        { "input_sha_wrong_format", "test-modeli", YzRecord(inputSha: new string('z', 64)), false },
        { "prompt_id_missing", "test-modeli", "{\"prompt_sha256\":\"" + TestData.Hash('a') + "\",\"input_sha256\":\"" + TestData.Hash('b') + "\"}", false },
    };

    [Theory]
    [MemberData(nameof(YzCases))]
    public async Task Review_yz_kaydi_check_follows_the_k37_rule(string caseName, string? model, string? record, bool accepted)
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using RollbackSession session = await Db.OpenRollbackSessionAsync(ct);
        Review review = new()
        {
            HedefTablo = "source",
            HedefAnahtar = "test-kaynak",
            Alan = "metin",
            Eylem = "onayla",
            Koken = XrefOrigin.Hat,
            Oneren = "test-editor",
            YzModeli = model,
            YzKaydi = record,
        };
        session.Context.Add(review);

        if (accepted)
        {
            await session.Context.SaveChangesAsync(ct);
            Assert.True(review.Id > 0, caseName);
        }
        else
        {
            await TestData.ExpectViolationAsync(Check, "review_yz_kaydi_check", () => session.Context.SaveChangesAsync(ct));
        }
    }

    // --- uretilen sutunlar ve uuidv7 ---

    [Theory]
    [InlineData("tsv_tr")]
    [InlineData("tsv_ar")]
    public async Task Search_vector_columns_are_stored_generated_columns(string column)
    {
        CancellationToken ct = TestContext.Current.CancellationToken;

        string generated = await Db.ScalarAsync<string>(
            "SELECT a.attgenerated::text FROM pg_attribute a JOIN pg_class c ON c.oid = a.attrelid JOIN pg_namespace n ON n.oid = c.relnamespace "
            + "WHERE n.nspname = 'icerik' AND c.relname = 'unit' AND a.attname = @column",
            ct,
            ("column", column));

        Assert.Equal("s", generated);
    }

    [Fact]
    public async Task Search_vectors_are_filled_by_the_database_from_the_search_keys()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using RollbackSession session = await Db.OpenRollbackSessionAsync(ct);
        Source source = await AddSourceAsync(session.Context, ct);
        Unit unit = TestData.NewUnit(source.Slug, "rn:sozler:soz-10:p1");
        unit.TrNarrow = "deneme paragrafi";
        unit.ArNorm = "abc def";
        session.Context.Add(unit);

        await session.Context.SaveChangesAsync(ct);

        Assert.Equal(2, await session.ScalarAsync<int>("SELECT length(tsv_tr) FROM icerik.unit WHERE id = @id", ct, ("id", unit.Id)));
        Assert.Equal(2, await session.ScalarAsync<int>("SELECT length(tsv_ar) FROM icerik.unit WHERE id = @id", ct, ("id", unit.Id)));
    }

    [Fact]
    public async Task Xref_id_is_generated_by_the_database_as_a_uuid_version_7()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using RollbackSession session = await Db.OpenRollbackSessionAsync(ct);
        Xref xref = TestData.NewXref();
        session.Context.Add(xref);

        await session.Context.SaveChangesAsync(ct);

        Assert.NotEqual(Guid.Empty, xref.Id);
        Assert.Equal(7, xref.Id.Version);
        Assert.Equal(7, await session.ScalarAsync<short>("SELECT uuid_extract_version(id) FROM icerik.xref WHERE id = @id", ct, ("id", xref.Id)));
    }

    [Fact]
    public async Task Quran_word_fix_id_is_generated_by_the_database_as_a_uuid_version_7()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using RollbackSession session = await Db.OpenRollbackSessionAsync(ct);
        QuranWordFix fix = new() { Anchor = AnchorRef.Parse("q:2:255:3"), Field = "pos", NewValue = "N", Reason = "deneme" };
        session.Context.Add(fix);

        await session.Context.SaveChangesAsync(ct);

        Assert.NotEqual(Guid.Empty, fix.Id);
        Assert.Equal(7, await session.ScalarAsync<short>("SELECT uuid_extract_version(id) FROM icerik.quran_word_fix WHERE id = @id", ct, ("id", fix.Id)));
    }

    [Fact]
    public async Task Two_xrefs_get_different_database_generated_ids()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using RollbackSession session = await Db.OpenRollbackSessionAsync(ct);
        Xref a = TestData.NewXref(type: XrefType.Atif);
        Xref b = TestData.NewXref(type: XrefType.Ima);
        session.Context.AddRange(a, b);

        await session.Context.SaveChangesAsync(ct);

        Assert.NotEqual(a.Id, b.Id);
    }

    // --- T-02: unit tekillik ve yabanci anahtar kisitlari ---

    private const string ForeignKey = "23503";

    [Fact]
    public async Task Unit_anchor_key_rejects_two_units_with_the_same_anchor()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using RollbackSession session = await Db.OpenRollbackSessionAsync(ct);
        Source source = await AddSourceAsync(session.Context, ct);
        session.Context.Add(TestData.NewUnit(source.Slug, "rn:sozler:soz-10:p1"));
        await session.Context.SaveChangesAsync(ct);

        session.Context.Add(TestData.NewUnit(source.Slug, "rn:sozler:soz-10:p1"));

        await TestData.ExpectViolationAsync(Unique, "unit_anchor_key", () => session.Context.SaveChangesAsync(ct));
    }

    [Fact]
    public async Task Unit_anchor_key_is_global_and_rejects_the_same_anchor_under_another_source()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using RollbackSession session = await Db.OpenRollbackSessionAsync(ct);
        Source first = await AddSourceAsync(session.Context, ct);
        Source second = await AddSourceAsync(session.Context, ct);
        session.Context.Add(TestData.NewUnit(first.Slug, "rn:sozler:soz-10:p1"));
        await session.Context.SaveChangesAsync(ct);

        session.Context.Add(TestData.NewUnit(second.Slug, "rn:sozler:soz-10:p1"));

        await TestData.ExpectViolationAsync(Unique, "unit_anchor_key", () => session.Context.SaveChangesAsync(ct));
    }

    [Fact]
    public async Task Unit_source_id_fkey_rejects_an_unknown_source()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using RollbackSession session = await Db.OpenRollbackSessionAsync(ct);
        session.Context.Add(TestData.NewUnit("test-olmayan-kaynak", "rn:sozler:soz-10:p1"));

        await TestData.ExpectViolationAsync(ForeignKey, "unit_source_id_fkey", () => session.Context.SaveChangesAsync(ct));
    }

    [Fact]
    public async Task Deleting_a_source_that_has_units_is_rejected_because_the_foreign_keys_are_no_action()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using RollbackSession session = await Db.OpenRollbackSessionAsync(ct);
        Source source = await AddSourceAsync(session.Context, ct);
        session.Context.Add(TestData.NewUnit(source.Slug, "rn:sozler:soz-10:p1"));
        await session.Context.SaveChangesAsync(ct);

        // Izlenen bagimli varken EF kaynagi silerken birimin source_id'sini NULL'a ceker (23502, NOT NULL); gercek NoAction davranisini
        // gormek icin izleme temizlenir ve silme dogrudan SQL'e gider (ExecuteDelete): veritabani yabanci anahtari reddeder.
        session.Context.ChangeTracker.Clear();
        string slug = source.Slug;

        PostgresException exception = await Assert.ThrowsAsync<PostgresException>(
            () => session.Context.Sources.Where(s => s.Slug == slug).ExecuteDeleteAsync(ct));

        Assert.Equal(ForeignKey, exception.SqlState);
        Assert.Equal("unit_source_id_fkey", exception.ConstraintName);
    }

    [Fact]
    public async Task Deleting_a_source_without_children_succeeds()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using RollbackSession session = await Db.OpenRollbackSessionAsync(ct);
        Source source = await AddSourceAsync(session.Context, ct);

        session.Context.Remove(source);
        await session.Context.SaveChangesAsync(ct);

        Assert.Equal(0L, await session.ScalarAsync<long>("SELECT count(*) FROM icerik.source WHERE slug = @s", ct, ("s", source.Slug)));
    }

    // --- T-03: page_map tekillik ve kalan CHECK kisitlari (ham SQL; parametreli kaynak kimligi) ---

    private const string InsertPageMap =
        "INSERT INTO icerik.page_map (source_id, volume, page, line, start_anchor, end_anchor, data_version) "
        + "VALUES (@s, {0}, 1, {1}, 'q:1:1', 'q:1:1', 'test')";

    private static string PageMapRow(string volume, string line) => InsertPageMap.Replace("{0}", volume, StringComparison.Ordinal).Replace("{1}", line, StringComparison.Ordinal);

    [Fact]
    public async Task Page_map_key_rejects_a_duplicate_row_whose_nullable_columns_are_both_null()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using RollbackSession session = await Db.OpenRollbackSessionAsync(ct);
        Source source = await AddSourceAsync(session.Context, ct);
        await session.ExecuteAsync(PageMapRow("NULL", "NULL"), ct, ("s", source.Slug));

        PostgresException exception = await Assert.ThrowsAsync<PostgresException>(
            () => session.ExecuteAsync(PageMapRow("NULL", "NULL"), ct, ("s", source.Slug)));

        Assert.Equal(Unique, exception.SqlState);
        Assert.Equal("page_map_source_id_volume_page_line_key", exception.ConstraintName);
    }

    [Fact]
    public async Task Page_map_key_rejects_an_exact_duplicate_with_set_volume_and_line()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using RollbackSession session = await Db.OpenRollbackSessionAsync(ct);
        Source source = await AddSourceAsync(session.Context, ct);
        await session.ExecuteAsync(PageMapRow("2", "7"), ct, ("s", source.Slug));

        PostgresException exception = await Assert.ThrowsAsync<PostgresException>(
            () => session.ExecuteAsync(PageMapRow("2", "7"), ct, ("s", source.Slug)));

        Assert.Equal(Unique, exception.SqlState);
        Assert.Equal("page_map_source_id_volume_page_line_key", exception.ConstraintName);
    }

    [Fact]
    public async Task Page_map_key_accepts_rows_that_differ_in_volume_or_line()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using RollbackSession session = await Db.OpenRollbackSessionAsync(ct);
        Source source = await AddSourceAsync(session.Context, ct);

        await session.ExecuteAsync(PageMapRow("NULL", "NULL"), ct, ("s", source.Slug));
        await session.ExecuteAsync(PageMapRow("1", "NULL"), ct, ("s", source.Slug));
        await session.ExecuteAsync(PageMapRow("2", "NULL"), ct, ("s", source.Slug));
        await session.ExecuteAsync(PageMapRow("NULL", "1"), ct, ("s", source.Slug));
        await session.ExecuteAsync(PageMapRow("NULL", "2"), ct, ("s", source.Slug));
        await session.ExecuteAsync(PageMapRow("1", "1"), ct, ("s", source.Slug));

        Assert.Equal(6L, await session.ScalarAsync<long>("SELECT count(*) FROM icerik.page_map WHERE source_id = @s", ct, ("s", source.Slug)));
    }

    /// <summary>Ham INSERT sablonu: &lt;v&gt; yer tutucusu ihlal eden (bad) ya da gecerli (good) degerle degisir.</summary>
    public static TheoryData<string, string, string, string> RemainingChecks => new()
    {
        { "unit_role_check", "INSERT INTO icerik.unit (anchor, kind, role, source_id, ord, metin, content_hash, data_version) VALUES ('rn:sozler:soz-10:p1', 'risale', '<v>', @s, 1, 'Deneme paragrafi 1', repeat('a', 64), 'test')", "gecersiz", "siir" },
        { "lemma_lang_check", "INSERT INTO icerik.lemma (id, lang, text, text_clean, source_id, data_version) VALUES (2, '<v>', 'b', 'b', @s, 'test')", "xx", "tr" },
        { "quran_word_fix_field_check", "INSERT INTO icerik.quran_word_fix (anchor, field, new_value, reason) VALUES ('q:2:255:3', '<v>', 'N', 'deneme')", "yok", "pos" },
        { "surah_alias_surah_no_check", "INSERT INTO icerik.surah_alias (surah_no, alias, alias_key, kind) VALUES (<v>, 'a', 'a', 'kanonik')", "0", "1" },
        { "surah_alias_surah_no_check", "INSERT INTO icerik.surah_alias (surah_no, alias, alias_key, kind) VALUES (<v>, 'a', 'a', 'kanonik')", "115", "114" },
        { "surah_alias_kind_check", "INSERT INTO icerik.surah_alias (surah_no, alias, alias_key, kind) VALUES (1, 'a', 'a', '<v>')", "yok", "diger_ad" },
        { "xref_score_check", "INSERT INTO icerik.xref (src_anchor, dst_anchor, type, score, confidence, origin, data_version, license) VALUES ('q:2:255', 'meal:elmalili:2:255', 'atif', <v>, 0.5, 'hat', 'test', 'serbest')", "1.5", "1" },
        { "xref_score_check", "INSERT INTO icerik.xref (src_anchor, dst_anchor, type, score, confidence, origin, data_version, license) VALUES ('q:2:255', 'meal:elmalili:2:255', 'atif', <v>, 0.5, 'hat', 'test', 'serbest')", "-0.1", "0" },
        { "xref_confidence_check", "INSERT INTO icerik.xref (src_anchor, dst_anchor, type, score, confidence, origin, data_version, license) VALUES ('q:2:255', 'meal:elmalili:2:255', 'atif', 0.5, <v>, 'hat', 'test', 'serbest')", "1.5", "1" },
        { "xref_confidence_check", "INSERT INTO icerik.xref (src_anchor, dst_anchor, type, score, confidence, origin, data_version, license) VALUES ('q:2:255', 'meal:elmalili:2:255', 'atif', 0.5, <v>, 'hat', 'test', 'serbest')", "-0.1", "0" },
        { "review_hedef_tablo_check", "INSERT INTO icerik.review (hedef_tablo, hedef_anahtar, alan, eylem, koken, oneren) VALUES ('<v>', 'x', 'metin', 'onayla', 'editor', 'test-editor')", "yok", "audio_timing" },
        { "page_map_line_type_check", "INSERT INTO icerik.page_map (source_id, page, line_type, start_anchor, end_anchor, data_version) VALUES (@s, 1, '<v>', 'q:1:1', 'q:1:1', 'test')", "yok", "besmele" },
        { "pipeline_run_durum_check", "INSERT INTO icerik.pipeline_run (run_id, komut, git_commit, parmak_izi, baslangic, durum) VALUES (uuidv7(), 'komut', 'abc', repeat('a', 64), now(), '<v>')", "yok", "basarili" },
        { "tr_root_index_check", "INSERT INTO icerik.tr_root_index (anchor, span_start, span_end, root_id, tr_lemma_id, data_version) VALUES ('rn:sozler:soz-10:p1', 5, <v>, 1, 1, 'test')", "5", "6" },
        { "tr_root_index_check", "INSERT INTO icerik.tr_root_index (anchor, span_start, span_end, root_id, tr_lemma_id, data_version) VALUES ('rn:sozler:soz-10:p1', 5, <v>, 1, 1, 'test')", "4", "6" },
        { "ayah_box_check", "INSERT INTO icerik.ayah_box (source_id, page, anchor, seq, x, y, w, h, data_version) VALUES (@s, 1, 'q:1:1', 1, 0, 0, <v>, 5, 'test')", "0", "1" },
        { "ayah_box_check", "INSERT INTO icerik.ayah_box (source_id, page, anchor, seq, x, y, w, h, data_version) VALUES (@s, 1, 'q:1:1', 1, 0, 0, 5, <v>, 'test')", "0", "1" },
        { "audio_timing_check", "INSERT INTO icerik.audio_timing (source_id, anchor, file, file_sha256, start_ms, end_ms, timing_source, data_version) VALUES (@s, 'q:1:1', '001.mp3', repeat('a', 64), 10, <v>, 'editor', 'test')", "10", "11" },
        { "audio_timing_check", "INSERT INTO icerik.audio_timing (source_id, anchor, file, file_sha256, start_ms, end_ms, timing_source, data_version) VALUES (@s, 'q:1:1', '001.mp3', repeat('a', 64), 10, <v>, 'editor', 'test')", "9", "11" },
    };

    [Theory]
    [MemberData(nameof(RemainingChecks))]
    public async Task Each_remaining_check_rejects_its_violation_and_accepts_the_valid_value(string constraint, string template, string bad, string good)
    {
        CancellationToken ct = TestContext.Current.CancellationToken;

        // Gecerli deger: ayni sablon kabul edilir (ihlalin gercekten yalniz bu degerden geldigini kanitlar).
        await using (RollbackSession accepted = await Db.OpenRollbackSessionAsync(ct))
        {
            string slug = await PrepareDependenciesAsync(accepted, ct);
            Assert.Equal(1, await accepted.ExecuteAsync(template.Replace("<v>", good, StringComparison.Ordinal), ct, ("s", slug)));
        }

        await using RollbackSession rejected = await Db.OpenRollbackSessionAsync(ct);
        string rejectedSlug = await PrepareDependenciesAsync(rejected, ct);
        PostgresException exception = await Assert.ThrowsAsync<PostgresException>(
            () => rejected.ExecuteAsync(template.Replace("<v>", bad, StringComparison.Ordinal), ct, ("s", rejectedSlug)));

        Assert.Equal(Check, exception.SqlState);
        Assert.Equal(constraint, exception.ConstraintName);
    }

    /// <summary>Kaynak, kok (1) ve lemma (1) satirlarini kurar: CHECK sinamalari yabanci anahtarlara takilmaz.</summary>
    private static async Task<string> PrepareDependenciesAsync(RollbackSession session, CancellationToken ct)
    {
        string slug = TestData.UniqueSlug();
        await session.ExecuteAsync(
            "INSERT INTO icerik.source (slug, tur, baslik, surum, license_name, atif_metni) VALUES (@s, 'meal', 'Deneme kaynagi', '1', 'Deneme', 'Deneme atfi')",
            ct,
            ("s", slug));
        await session.ExecuteAsync("INSERT INTO icerik.root (id, letters, source_id, data_version) VALUES (1, 'kok-1', @s, 'test')", ct, ("s", slug));
        await session.ExecuteAsync(
            "INSERT INTO icerik.lemma (id, lang, text, text_clean, source_id, data_version) VALUES (1, 'ar', 'lemma-1', 'lemma-1', @s, 'test')",
            ct,
            ("s", slug));
        return slug;
    }
}
