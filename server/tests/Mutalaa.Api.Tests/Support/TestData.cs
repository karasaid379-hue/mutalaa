using System.Globalization;
using Microsoft.EntityFrameworkCore;
using Mutalaa.Domain.Anchors;
using Mutalaa.Domain.Content;
using Mutalaa.Domain.Licensing;
using Mutalaa.Domain.Links;
using Npgsql;

namespace Mutalaa.Api.Tests.Support;

/// <summary>Sentetik test verisi ve istisna zinciri yardimcilari (gercek Kur'an, meal ya da Risale metni yoktur).</summary>
internal static class TestData
{
    /// <summary>64 kucuk harfli onaltilik karakter (gecerli ozet bicimi).</summary>
    public static string Hash(char digit = 'a') => new(digit, 64);

    private static int _anchorCounter;

    /// <summary>Veritabaninda tekil capa (unit.anchor): ayni veritabanini paylasan testler birbirine carpmaz.</summary>
    public static string UnitAnchor() =>
        "rn:sozler:soz-10:p" + Interlocked.Increment(ref _anchorCounter).ToString(CultureInfo.InvariantCulture);

    public static string UniqueSlug() =>
        "test-" + Guid.NewGuid().ToString("N", CultureInfo.InvariantCulture)[..8];

    public static Source NewSource(string? slug = null) => new()
    {
        Slug = slug ?? UniqueSlug(),
        Tur = SourceKind.Meal,
        Baslik = "Deneme kaynagi",
        Surum = "1",
        LicenseName = "Deneme",
        AtifMetni = "Deneme atfi",
    };

    public static Unit NewUnit(string sourceId, string anchor) => new()
    {
        Anchor = AnchorRef.Parse(anchor),
        Kind = UnitKind.Risale,
        SourceId = sourceId,
        Metin = "Deneme paragrafi 1",
        ContentHash = Hash(),
        DataVersion = "test",
    };

    public static Xref NewXref(string src = "q:2:255", string dst = "meal:elmalili:2:255", XrefType type = XrefType.Atif) => new()
    {
        SrcAnchor = AnchorRef.Parse(src),
        DstAnchor = AnchorRef.Parse(dst),
        Type = type,
        Origin = XrefOrigin.Hat,
        DataVersion = "test",
        License = LicenseStatus.Serbest,
    };

    /// <summary>Istisna zincirinde (kendisi dahil) ilk T'yi bulur; yoksa null.</summary>
    public static T? FindInChain<T>(Exception exception)
        where T : Exception
    {
        for (Exception? current = exception; current is not null; current = current.InnerException)
        {
            if (current is T match)
            {
                return match;
            }
        }

        return null;
    }

    /// <summary>Eylem EF DbUpdateException ile PostgreSQL hatasi vermeli; SqlState ve kisit adi dogrulanir.</summary>
    public static async Task ExpectViolationAsync(string sqlState, string constraintName, Func<Task> action)
    {
        DbUpdateException exception = await Assert.ThrowsAsync<DbUpdateException>(action);
        PostgresException postgres = FindInChain<PostgresException>(exception)
            ?? throw new Xunit.Sdk.XunitException("DbUpdateException icinde PostgresException yok: " + exception.Message);
        Assert.Equal(sqlState, postgres.SqlState);
        Assert.Equal(constraintName, postgres.ConstraintName);
    }
}
