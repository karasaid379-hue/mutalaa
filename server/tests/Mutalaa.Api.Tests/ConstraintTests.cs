using Microsoft.EntityFrameworkCore;
using Mutalaa.Api.Tests.Support;
using Mutalaa.Domain.Anchors;
using Mutalaa.Domain.Content;
using Mutalaa.Domain.Links;
using Mutalaa.Domain.Reviews;
using Mutalaa.Infrastructure.Persistence;

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
}
