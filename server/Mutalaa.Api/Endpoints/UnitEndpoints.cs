using System.ComponentModel.DataAnnotations;
using System.Globalization;
using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using Mutalaa.Api.Paging;
using Mutalaa.Api.Problems;
using Mutalaa.Api.Validation;
using Mutalaa.Domain.Anchors;
using Mutalaa.Domain.Content;
using Mutalaa.Domain.Text;
using Mutalaa.Infrastructure.Persistence;

namespace Mutalaa.Api.Endpoints;

/// <summary>Birim liste ogesi. Metin tam doner (Risale paragraflari buyuk olabilir; bkz. A14 raporu).</summary>
public sealed record UnitListItem(
    string Anchor,
    string Kind,
    string Role,
    string Source,
    long Ord,
    string MetinDurumu,
    string Status,
    int Rev,
    string ContentHash,
    string? ParentPath,
    string Metin);

public sealed record UnitListResponse(IReadOnlyList<UnitListItem> Items, string? NextCursor);

/// <summary>Birim ayrintisi: liste alanlari + jsonb alanlari (ham JSON), cumle ve ayet araliklari, kaynak turu, duzeltilebilirlik.</summary>
public sealed record UnitDetail(
    string Anchor,
    string Kind,
    string Role,
    string Source,
    long Ord,
    string MetinDurumu,
    string Status,
    int Rev,
    string ContentHash,
    string? ParentPath,
    string Metin,
    JsonElement Marks,
    JsonElement Attrs,
    int[][]? Sentences,
    int[]? AyahRange,
    JsonElement? Successors,
    string DataVersion,
    JsonElement Provenance,
    DateTime CreatedAt,
    DateTime UpdatedAt,
    bool Duzeltilebilir,
    string KaynakTur);

public sealed record CorrectionRequest(
    [property: Required(ErrorMessage = "{0} alanı zorunludur.")] string Metin,
    [property: Required(ErrorMessage = "{0} alanı zorunludur.")] string Gerekce);

public sealed record CorrectionResponse(long Id, string Durum);

/// <summary>Birim uclari: liste (imleç sayfalama), ayrinti ve metin duzeltme onerisi.</summary>
public static partial class UnitEndpoints
{
    public const int DefaultLimit = 50;
    public const int MaxLimit = 200;

    /// <summary>q en cok bu kadar kod noktasi (Rune); UTF-16 uzunlugu degil.</summary>
    public const int MaxQueryLength = 1024;

    public static RouteGroupBuilder MapUnitEndpoints(this RouteGroupBuilder editor)
    {
        ArgumentNullException.ThrowIfNull(editor);

        RouteGroupBuilder units = editor.MapGroup("/units").WithTags("units");

        units.MapGet(string.Empty, ListAsync)
            .WithName("listUnits")
            .WithSummary("Birimleri (source_id, ord, id) sırasıyla ve imleçle sayfalayarak listeler.")
            .Produces<UnitListResponse>()
            .ProducesProblem(StatusCodes.Status400BadRequest)
            .ProducesProblem(StatusCodes.Status404NotFound);

        units.MapGet("/{anchor}", GetAsync)
            .WithName("getUnit")
            .WithSummary("Tek birimi çapasıyla döndürür (ETag = xmin).")
            .Produces<UnitDetail>()
            .ProducesProblem(StatusCodes.Status400BadRequest)
            .ProducesProblem(StatusCodes.Status404NotFound);

        MapCorrectionEndpoints(units);

        return editor;
    }

    private static async Task<IResult> ListAsync(
        string? source,
        string? prefix,
        string? q,
        string? cursor,
        int? limit,
        IcerikDbContext db,
        CancellationToken cancellationToken)
    {
        Dictionary<string, string[]> errors = new(StringComparer.Ordinal);

        // Sayi olmayan deger baglama asamasinda 400 dogrulama olur; aralik burada denetlenir.
        int take = limit ?? DefaultLimit;
        if (take is < 1 or > MaxLimit)
        {
            errors["limit"] = [$"limit 1 ile {MaxLimit.ToString(CultureInfo.InvariantCulture)} arasında bir tamsayı olmalı."];
        }

        // Metin sorgu parametreleri NUL ve eslesmemis vekil icermez (PostgreSQL parametresi olamaz).
        if (!string.IsNullOrEmpty(q))
        {
            if (!WritableText.TryCountCodePoints(q, out int queryLength))
            {
                errors["q"] = [WritableText.Message("q")];
            }
            else if (queryLength > MaxQueryLength)
            {
                errors["q"] = [$"q en çok {MaxQueryLength.ToString(CultureInfo.InvariantCulture)} karakter olabilir."];
            }
        }

        WritableText.Check(errors, "prefix", prefix);
        WritableText.Check(errors, "source", source);

        UnitCursor? after = null;
        if (!string.IsNullOrEmpty(cursor))
        {
            after = DecodeCursor(cursor);
            if (after is null)
            {
                errors["cursor"] = ["cursor geçersiz."];
            }
        }

        if (errors.Count > 0)
        {
            return ApiProblem.Validation(errors);
        }

        if (!string.IsNullOrEmpty(source) && !await db.Sources.AnyAsync(s => s.Slug == source, cancellationToken))
        {
            return ApiProblem.Create(StatusCodes.Status404NotFound, ProblemCodes.Bulunamadi, "Kaynak bulunamadı.");
        }

        string? sourceFilter = string.IsNullOrEmpty(source) ? null : source;
        string? prefixPattern = string.IsNullOrEmpty(prefix) ? null : EscapeLike(prefix) + "%";

        string? trPattern = null;
        string? arPattern = null;
        if (!string.IsNullOrEmpty(q))
        {
            SearchKeys keys = SearchNormalizer.Keys(q);
            string trKey = keys.TrWide.Trim();
            string arKey = keys.ArNorm.Trim();
            trPattern = trKey.Length == 0 ? null : "%" + EscapeLike(trKey) + "%";
            arPattern = arKey.Length == 0 ? null : "%" + EscapeLike(arKey) + "%";
            if (trPattern is null && arPattern is null)
            {
                // Normallestirme sonrasi aranacak bir sey kalmadi (yalniz noktalama ya da bosluk): hicbir birim eslesmez.
                return EditorJson.Ok(new UnitListResponse([], null));
            }
        }

        bool filterQuery = trPattern is not null || arPattern is not null;
        string? cursorSource = after?.SourceId;
        long? cursorOrd = after?.Ord;
        long? cursorId = after?.Id;

        // Degerler parametredir; metin sabittir. "::tip" donusumleri bos (NULL) parametrenin tipini belirler.
        // Capa ve normalize sutunlarinda LIKE '\' kacisiyla; '%', '_' ve '\' kullanici girdisinde kacislanmistir.
        IQueryable<Unit> filtered = db.Units.FromSql($"""
            SELECT * FROM icerik.unit
            WHERE ({sourceFilter}::text IS NULL OR source_id = {sourceFilter}::text)
              AND ({prefixPattern}::text IS NULL OR anchor LIKE {prefixPattern}::text ESCAPE '\')
              AND (NOT {filterQuery}::boolean
                   OR tr_wide LIKE {trPattern}::text ESCAPE '\'
                   OR ar_norm LIKE {arPattern}::text ESCAPE '\')
              AND ({cursorOrd}::bigint IS NULL
                   OR (source_id COLLATE "C", ord, id) > ({cursorSource}::text, {cursorOrd}::bigint, {cursorId}::bigint))
            """);

        // Projeksiyon: tsv_tr ve tsv_ar golge sutunlari secilmez.
        List<UnitListRow> rows = await filtered
            .AsNoTracking()
            .OrderBy(u => EF.Functions.Collate(u.SourceId, "C"))
            .ThenBy(u => u.Ord)
            .ThenBy(u => u.Id)
            .Take(take + 1)
            .Select(u => new UnitListRow
            {
                Id = u.Id,
                Anchor = u.Anchor,
                Kind = u.Kind,
                Role = u.Role,
                SourceId = u.SourceId,
                Ord = u.Ord,
                MetinDurumu = u.MetinDurumu,
                Status = u.Status,
                Rev = u.Rev,
                ContentHash = u.ContentHash,
                ParentPath = u.ParentPath,
                Metin = u.Metin,
            })
            .ToListAsync(cancellationToken);

        bool more = rows.Count > take;
        if (more)
        {
            rows.RemoveRange(take, rows.Count - take);
        }

        string? next = more ? EncodeCursor(rows[^1]) : null;
        return EditorJson.Ok(new UnitListResponse([.. rows.Select(ToItem)], next));
    }

    private static async Task<IResult> GetAsync(string anchor, HttpContext httpContext, IcerikDbContext db, CancellationToken cancellationToken)
    {
        (AnchorRef? parsed, IResult? problem) = UnitAnchors.Parse(anchor);
        if (problem is not null)
        {
            return problem;
        }

        AnchorRef key = parsed!;
        UnitDetailRow? row = await (
            from u in db.Units.AsNoTracking()
            join s in db.Sources.AsNoTracking() on u.SourceId equals s.Slug
            where u.Anchor == key
            select new UnitDetailRow
            {
                Anchor = u.Anchor,
                Kind = u.Kind,
                Role = u.Role,
                SourceId = u.SourceId,
                Ord = u.Ord,
                MetinDurumu = u.MetinDurumu,
                Status = u.Status,
                Rev = u.Rev,
                ContentHash = u.ContentHash,
                ParentPath = u.ParentPath,
                Metin = u.Metin,
                Marks = u.Marks,
                Attrs = u.Attrs,
                Sentences = u.Sentences,
                AyahRange = u.AyahRange,
                Successors = u.Successors,
                DataVersion = u.DataVersion,
                Provenance = u.Provenance,
                CreatedAt = u.CreatedAt,
                UpdatedAt = u.UpdatedAt,
                SourceKind = s.Tur,
                Xmin = EF.Property<uint>(u, RowVersion.Name),
            }).FirstOrDefaultAsync(cancellationToken);

        if (row is null)
        {
            return ApiProblem.Create(StatusCodes.Status404NotFound, ProblemCodes.Bulunamadi, "Birim bulunamadı.");
        }

        httpContext.Response.Headers.ETag = "\"" + row.Xmin.ToString(CultureInfo.InvariantCulture) + "\"";
        return EditorJson.Ok(new UnitDetail(
            row.Anchor.ToString(),
            row.Kind.ToLabel(),
            row.Role,
            row.SourceId,
            row.Ord,
            row.MetinDurumu.ToLabel(),
            row.Status.ToLabel(),
            row.Rev,
            row.ContentHash,
            row.ParentPath,
            row.Metin,
            EditorJson.Raw(row.Marks)!.Value,
            EditorJson.Raw(row.Attrs)!.Value,
            row.Sentences?.Select(s => new[] { s.Start, s.End }).ToArray(),
            row.AyahRange is { } range ? [range.Start, range.End] : null,
            EditorJson.Raw(row.Successors),
            row.DataVersion,
            EditorJson.Raw(row.Provenance)!.Value,
            row.CreatedAt,
            row.UpdatedAt,
            !TextMutability.IsImmutable(row.Kind, row.SourceKind),
            row.SourceKind.ToLabel()));
    }

    private static UnitListItem ToItem(UnitListRow r) => new(
        r.Anchor.ToString(),
        r.Kind.ToLabel(),
        r.Role,
        r.SourceId,
        r.Ord,
        r.MetinDurumu.ToLabel(),
        r.Status.ToLabel(),
        r.Rev,
        r.ContentHash,
        r.ParentPath,
        r.Metin);

    // Imlec: "{ord}:{id}:{source_id}" (kaynak kimligi sonda; ':' icerse bile ilk iki ':' ile ayrilir) base64url.
    private static string EncodeCursor(UnitListRow last) =>
        Cursor.Encode(
            last.Ord.ToString(CultureInfo.InvariantCulture) + ":" + last.Id.ToString(CultureInfo.InvariantCulture) + ":" + last.SourceId);

    private static UnitCursor? DecodeCursor(string cursor)
    {
        if (!Cursor.TryDecode(cursor, out string payload))
        {
            return null;
        }

        string[] parts = payload.Split(':', 3);
        if (parts.Length != 3 || parts[2].Length == 0 || !TryCanonicalLong(parts[0], out long ord) || !TryCanonicalLong(parts[1], out long id))
        {
            return null;
        }

        return new UnitCursor(parts[2], ord, id);
    }

    private static bool TryCanonicalLong(string text, out long value) =>
        long.TryParse(text, NumberStyles.None, CultureInfo.InvariantCulture, out value)
        && string.Equals(value.ToString(CultureInfo.InvariantCulture), text, StringComparison.Ordinal);

    /// <summary>LIKE ozel karakterlerini ('\', '%', '_') '\' ile kacislar; once '\' (yoksa eklenen kacislar yeniden kacislanir).</summary>
    internal static string EscapeLike(string text) =>
        text
            .Replace("\\", "\\\\", StringComparison.Ordinal)
            .Replace("%", "\\%", StringComparison.Ordinal)
            .Replace("_", "\\_", StringComparison.Ordinal);

    private sealed record UnitCursor(string SourceId, long Ord, long Id);

    private sealed class UnitListRow
    {
        public required long Id { get; init; }

        public required AnchorRef Anchor { get; init; }

        public required UnitKind Kind { get; init; }

        public required string Role { get; init; }

        public required string SourceId { get; init; }

        public required long Ord { get; init; }

        public required TextStatus MetinDurumu { get; init; }

        public required UnitStatus Status { get; init; }

        public required int Rev { get; init; }

        public required string ContentHash { get; init; }

        public string? ParentPath { get; init; }

        public required string Metin { get; init; }
    }

    private sealed class UnitDetailRow
    {
        public required AnchorRef Anchor { get; init; }

        public required UnitKind Kind { get; init; }

        public required string Role { get; init; }

        public required string SourceId { get; init; }

        public required long Ord { get; init; }

        public required TextStatus MetinDurumu { get; init; }

        public required UnitStatus Status { get; init; }

        public required int Rev { get; init; }

        public required string ContentHash { get; init; }

        public string? ParentPath { get; init; }

        public required string Metin { get; init; }

        public required string Marks { get; init; }

        public required string Attrs { get; init; }

        public AnchorSpan[]? Sentences { get; init; }

        public AnchorSpan? AyahRange { get; init; }

        public string? Successors { get; init; }

        public required string DataVersion { get; init; }

        public required string Provenance { get; init; }

        public DateTime CreatedAt { get; init; }

        public DateTime UpdatedAt { get; init; }

        public required SourceKind SourceKind { get; init; }

        public uint Xmin { get; init; }
    }
}
