using Mutalaa.Api.Tests.Support;
using Npgsql;

namespace Mutalaa.Api.Tests;

/// <summary>
/// A17.G (AddLemmaWave): lemma(qac_ref) kismi tekil dizini, root(letters_bw) tekil dizini ve lemma_dalga anahtarlari (Docker'li).
/// Her test kendi islemini acar ve sonunda geri alir.
/// </summary>
public class LemmaWaveConstraintTests(EditorialDatabase<LemmaWaveConstraintTests> fixture) : IClassFixture<EditorialDatabase<LemmaWaveConstraintTests>>
{
    private const string Unique = "23505";
    private const string ForeignKey = "23503";

    private TestDatabase Db => fixture.Database;

    private static async Task<string> AddSourceAsync(RollbackSession session, CancellationToken ct)
    {
        string slug = TestData.UniqueSlug();
        await session.ExecuteAsync(
            "INSERT INTO icerik.source (slug, tur, baslik, surum, atif_metni) VALUES (@s, 'meal', 'Deneme kaynagi', '1', 'Deneme atfi')",
            ct,
            ("s", slug));
        return slug;
    }

    private static Task<int> AddLemmaAsync(RollbackSession session, CancellationToken ct, int id, string lang, string? qacRef, string slug) =>
        session.ExecuteAsync(
            "INSERT INTO icerik.lemma (id, lang, text, text_clean, qac_ref, source_id, data_version) VALUES (@id, @lang, 'lemma', 'lemma', @q, @s, 'test')",
            ct,
            ("id", id),
            ("lang", lang),
            ("q", (object?)qacRef ?? DBNull.Value),
            ("s", slug));

    private static Task<int> AddRootAsync(RollbackSession session, CancellationToken ct, int id, string letters, string? lettersBw, string slug) =>
        session.ExecuteAsync(
            "INSERT INTO icerik.root (id, letters, letters_bw, source_id, data_version) VALUES (@id, @l, @b, @s, 'test')",
            ct,
            ("id", id),
            ("l", letters),
            ("b", (object?)lettersBw ?? DBNull.Value),
            ("s", slug));

    [Fact]
    public async Task Lemma_qac_ref_is_unique_among_arabic_lemmas()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using RollbackSession session = await Db.OpenRollbackSessionAsync(ct);
        string slug = await AddSourceAsync(session, ct);
        await AddLemmaAsync(session, ct, 1, "ar", "deneme-ref", slug);

        PostgresException exception = await Assert.ThrowsAsync<PostgresException>(() => AddLemmaAsync(session, ct, 2, "ar", "deneme-ref", slug));

        Assert.Equal(Unique, exception.SqlState);
        Assert.Equal("lemma_qac_ref_key", exception.ConstraintName);
    }

    [Fact]
    public async Task Lemma_qac_ref_index_ignores_turkish_lemmas_and_null_references()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using RollbackSession session = await Db.OpenRollbackSessionAsync(ct);
        string slug = await AddSourceAsync(session, ct);

        Assert.Equal(1, await AddLemmaAsync(session, ct, 1, "ar", "deneme-ref", slug));
        Assert.Equal(1, await AddLemmaAsync(session, ct, 2, "tr", "deneme-ref", slug));
        Assert.Equal(1, await AddLemmaAsync(session, ct, 3, "ar", null, slug));
        Assert.Equal(1, await AddLemmaAsync(session, ct, 4, "ar", null, slug));
    }

    [Fact]
    public async Task Root_letters_bw_is_unique_but_null_values_do_not_collide()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using RollbackSession session = await Db.OpenRollbackSessionAsync(ct);
        string slug = await AddSourceAsync(session, ct);

        Assert.Equal(1, await AddRootAsync(session, ct, 1, "kok-1", null, slug));
        Assert.Equal(1, await AddRootAsync(session, ct, 2, "kok-2", null, slug));
        Assert.Equal(1, await AddRootAsync(session, ct, 3, "kok-3", "bw-deneme", slug));

        PostgresException exception = await Assert.ThrowsAsync<PostgresException>(() => AddRootAsync(session, ct, 4, "kok-4", "bw-deneme", slug));

        Assert.Equal(Unique, exception.SqlState);
        Assert.Equal("root_letters_bw_key", exception.ConstraintName);
    }

    [Fact]
    public async Task Lemma_dalga_is_one_row_per_lemma_and_needs_an_existing_lemma()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using RollbackSession session = await Db.OpenRollbackSessionAsync(ct);
        string slug = await AddSourceAsync(session, ct);
        await AddLemmaAsync(session, ct, 1, "ar", null, slug);
        const string insert = "INSERT INTO icerik.lemma_dalga (lemma_id, dalga, sira, data_version) VALUES (@id, 1, 1, 'test')";

        Assert.Equal(1, await session.ExecuteAsync(insert, ct, ("id", 1)));

        PostgresException duplicate = await Assert.ThrowsAsync<PostgresException>(() => session.ExecuteAsync(insert, ct, ("id", 1)));
        Assert.Equal(Unique, duplicate.SqlState);
        Assert.Equal("lemma_dalga_pkey", duplicate.ConstraintName);
    }

    [Fact]
    public async Task Lemma_dalga_foreign_key_rejects_an_unknown_lemma()
    {
        CancellationToken ct = TestContext.Current.CancellationToken;
        await using RollbackSession session = await Db.OpenRollbackSessionAsync(ct);

        PostgresException exception = await Assert.ThrowsAsync<PostgresException>(
            () => session.ExecuteAsync("INSERT INTO icerik.lemma_dalga (lemma_id, dalga, sira, data_version) VALUES (999, 1, 1, 'test')", ct));

        Assert.Equal(ForeignKey, exception.SqlState);
        Assert.Equal("lemma_dalga_lemma_id_fkey", exception.ConstraintName);
    }
}
