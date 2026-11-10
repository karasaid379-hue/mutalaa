using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using Mutalaa.Api.Problems;
using Mutalaa.Domain.Content;
using Mutalaa.Infrastructure.Persistence;

namespace Mutalaa.Api.Endpoints;

/// <summary>Kaynak kaydi (icerik.source) ve birim sayisi. Enum alanlari veritabani etiketidir; baski_bilgisi JSON nesnesidir.</summary>
public sealed record SourceDto(
    string Slug,
    string Tur,
    string Baslik,
    string? Yazar,
    string Surum,
    string? Provider,
    string? KaynakUrl,
    DateOnly? AlinmaTarihi,
    string? DosyaSha256,
    JsonElement? BaskiBilgisi,
    string AtifMetni,
    string? AtifUrl,
    string? NoticeText,
    string? Notlar,
    DateTime CreatedAt,
    DateTime UpdatedAt,
    long BirimSayisi);

/// <summary>Kaynak uclari: salt okunur. GET disindaki yontemler eslesmez; ASP.NET 405 ve Allow basligini kendisi verir.</summary>
public static class SourceEndpoints
{
    public static RouteGroupBuilder MapSourceEndpoints(this RouteGroupBuilder editor)
    {
        ArgumentNullException.ThrowIfNull(editor);

        RouteGroupBuilder sources = editor.MapGroup("/sources").WithTags("sources");

        sources.MapGet(string.Empty, ListAsync)
            .WithName("listSources")
            .WithSummary("Kaynak kayıtlarını slug sırasıyla listeler.")
            .Produces<IReadOnlyList<SourceDto>>();

        sources.MapGet("/{slug}", GetAsync)
            .WithName("getSource")
            .WithSummary("Tek kaynak kaydını (atıf, sürüm, dosya özeti) ve birim sayısını döndürür.")
            .Produces<SourceDto>()
            .ProducesProblem(StatusCodes.Status404NotFound);

        return editor;
    }

    private static async Task<IResult> ListAsync(IcerikDbContext db, CancellationToken cancellationToken)
    {
        List<SourceRow> rows = await Query(db).OrderBy(r => r.Slug).ToListAsync(cancellationToken);
        return EditorJson.Ok(rows.Select(ToDto).ToList());
    }

    private static async Task<IResult> GetAsync(string slug, IcerikDbContext db, CancellationToken cancellationToken)
    {
        SourceRow? row = await Query(db).FirstOrDefaultAsync(r => r.Slug == slug, cancellationToken);
        return row is null
            ? ApiProblem.Create(StatusCodes.Status404NotFound, ProblemCodes.Bulunamadi, "Kaynak bulunamadı.")
            : EditorJson.Ok(ToDto(row));
    }

    // Slug sutunu COLLATE "C" (bayt siralamasi): OrderBy dogrudan o siralamayi kullanir.
    private static IQueryable<SourceRow> Query(IcerikDbContext db) =>
        db.Sources.AsNoTracking().Select(s => new SourceRow
        {
            Slug = s.Slug,
            Tur = s.Tur,
            Baslik = s.Baslik,
            Yazar = s.Yazar,
            Surum = s.Surum,
            Provider = s.Provider,
            KaynakUrl = s.KaynakUrl,
            AlinmaTarihi = s.AlinmaTarihi,
            DosyaSha256 = s.DosyaSha256,
            BaskiBilgisi = s.BaskiBilgisi,
            AtifMetni = s.AtifMetni,
            AtifUrl = s.AtifUrl,
            NoticeText = s.NoticeText,
            Notlar = s.Notlar,
            CreatedAt = s.CreatedAt,
            UpdatedAt = s.UpdatedAt,
            BirimSayisi = db.Units.LongCount(u => u.SourceId == s.Slug),
        });

    private static SourceDto ToDto(SourceRow r) => new(
        r.Slug,
        r.Tur.ToLabel(),
        r.Baslik,
        r.Yazar,
        r.Surum,
        r.Provider,
        r.KaynakUrl,
        r.AlinmaTarihi,
        r.DosyaSha256,
        EditorJson.Raw(r.BaskiBilgisi),
        r.AtifMetni,
        r.AtifUrl,
        r.NoticeText,
        r.Notlar,
        r.CreatedAt,
        r.UpdatedAt,
        r.BirimSayisi);

    private sealed class SourceRow
    {
        public required string Slug { get; init; }

        public required SourceKind Tur { get; init; }

        public required string Baslik { get; init; }

        public string? Yazar { get; init; }

        public required string Surum { get; init; }

        public string? Provider { get; init; }

        public string? KaynakUrl { get; init; }

        public DateOnly? AlinmaTarihi { get; init; }

        public string? DosyaSha256 { get; init; }

        public string? BaskiBilgisi { get; init; }

        public required string AtifMetni { get; init; }

        public string? AtifUrl { get; init; }

        public string? NoticeText { get; init; }

        public string? Notlar { get; init; }

        public DateTime CreatedAt { get; init; }

        public DateTime UpdatedAt { get; init; }

        public long BirimSayisi { get; init; }
    }
}
