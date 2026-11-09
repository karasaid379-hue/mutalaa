using System.Text.Json;
using Mutalaa.Domain.Content;
using Mutalaa.Domain.Links;
using Mutalaa.Domain.Reviews;
using Mutalaa.Domain.Text;

namespace Mutalaa.Domain.Tests.Support;

/// <summary>Inceleme testleri icin sentetik veri ureticileri (Kur'an, meal ya da hadis metni yok).</summary>
internal static class ReviewFixtures
{
    public static readonly DateTime Now = new(2026, 11, 9, 10, 0, 0, DateTimeKind.Utc);

    public const string CurrentText = "Deneme paragrafi 1";

    public const string ProposedText = "Deneme paragrafi 2";

    public const string EditedText = "Deneme paragrafi 3";

    /// <summary>Metni ve ozetini tasiyan jsonb degeri.</summary>
    public static string Payload(string metin, string? contentHash = null) =>
        JsonSerializer.Serialize(new Dictionary<string, string> { ["metin"] = metin, ["content_hash"] = contentHash ?? ContentHash.Compute(metin) });

    public static UnitReviewState Unit(
        UnitKind kind = UnitKind.Meal,
        TextStatus durum = TextStatus.Taslak,
        string metin = CurrentText,
        SourceKind sourceKind = SourceKind.Meal,
        int rev = 1) =>
        new(kind, sourceKind, durum, metin, ContentHash.Compute(metin), rev);

    /// <summary>Birim metni incelemesi: onceki mevcut metin, onerilen yeni metin.</summary>
    public static Review UnitReview(
        string? onceki = null,
        string? onerilen = null,
        XrefOrigin koken = XrefOrigin.Hat,
        string oneren = "hat",
        ReviewStatus durum = ReviewStatus.Acik,
        string? inceleyen = null,
        string? duzenlenen = null) =>
        new()
        {
            HedefTablo = ReviewTargets.Unit,
            HedefAnahtar = "meal:test:1:1",
            Alan = ReviewFields.Metin,
            Eylem = ReviewActions.Oner,
            Onceki = onceki ?? Payload(CurrentText),
            Onerilen = onerilen ?? Payload(ProposedText),
            Duzenlenen = duzenlenen,
            Durum = durum,
            Koken = koken,
            Oneren = oneren,
            Inceleyen = inceleyen,
        };

    public static Review StatusReview(
        string hedefTablo = ReviewTargets.Xref,
        string alan = ReviewFields.Status,
        XrefOrigin koken = XrefOrigin.Hat,
        string oneren = "hat",
        ReviewStatus durum = ReviewStatus.Acik) =>
        new()
        {
            HedefTablo = hedefTablo,
            HedefAnahtar = "x",
            Alan = alan,
            Eylem = ReviewActions.Oner,
            Durum = durum,
            Koken = koken,
            Oneren = oneren,
        };

    public static ReviewDecisionRequest Request(string actor = "test-editor-1", string? gerekce = "Deneme gerekcesi", string? duzenlenen = null) =>
        new() { Actor = actor, Gerekce = gerekce, Duzenlenen = duzenlenen, Now = Now };

    /// <summary>Eylemin firlattigi DomainException'in kodunu dondurur; firlatmazsa ya da baska istisna atarsa test kirilir.</summary>
    public static string CodeOf<T>(Func<T> action) => Assert.Throws<DomainException>(() => _ = action()).Code;
}
