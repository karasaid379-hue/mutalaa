using System.ComponentModel.DataAnnotations;
using System.Text.Json;

namespace Mutalaa.Api.Endpoints;

/// <summary>POST /releases gövdesi. <c>paketler</c> bos ya da yoksa butun paketler.</summary>
public sealed record CreateReleaseRequest(
    [property: Required(ErrorMessage = "{0} alanı zorunludur.")] string Derleme,
    string[]? Paketler,
    string? Notlar);

/// <summary>POST /releases/preview gövdesi.</summary>
public sealed record PreviewReleaseRequest(
    [property: Required(ErrorMessage = "{0} alanı zorunludur.")] string Derleme,
    string[]? Paketler);

/// <summary>POST /releases/{id}/promote ve /rollback gövdesi (gövde hic verilmeyebilir).</summary>
public sealed record ReleaseNotesRequest(string? Notlar);

/// <summary>Kabul edilen talep (202).</summary>
public sealed record ReleaseAccepted(int Id, string Surum, string Derleme, string Durum, string Talep);

/// <summary>409 <c>yayin-suruyor</c> yanitinin <c>yayin</c> uzantisi: derleme turunde acik olan satir.</summary>
public sealed record ReleaseRef(int Id, string Surum, string Derleme, string Durum, string Talep);

/// <summary>Liste ogesi. <c>Xmin</c> iyimser eszamanlilik belirtecidir (ETag ile ayni deger).</summary>
public sealed record ReleaseSummary(
    int Id,
    string Surum,
    string Derleme,
    string Durum,
    string Talep,
    int? KaynakReleaseId,
    string[]? Paketler,
    string Olusturan,
    DateTime CreatedAt,
    DateTime? YayinlandiAt,
    uint Xmin);

public sealed record ReleaseListResponse(IReadOnlyList<ReleaseSummary> Items, string? NextCursor);

/// <summary>Ayrinti: ozet alanlari + not, veri surumu ve ham JSON nesneler (kapi raporu, ozetler, manifest).</summary>
public sealed record ReleaseDetail(
    int Id,
    string Surum,
    string Derleme,
    string Durum,
    string Talep,
    int? KaynakReleaseId,
    string[]? Paketler,
    string Olusturan,
    DateTime CreatedAt,
    DateTime? YayinlandiAt,
    string? Notlar,
    string DataVersion,
    JsonElement KapiRaporu,
    JsonElement Ozetler,
    JsonElement? Manifest,
    uint Xmin);

/// <summary>Onizleme yaniti (200): kapi raporu reddetmedi.</summary>
public sealed record ReleasePreviewResponse(string Derleme, JsonElement KapiRaporu, IReadOnlyList<string> Uyarilar);
