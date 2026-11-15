using System.Text.Json;
using Mutalaa.Domain.Anchors;
using Mutalaa.Domain.Links;
using Mutalaa.Domain.Reviews;
using Mutalaa.Domain.Tests.Support;
using static Mutalaa.Domain.Tests.Support.ReviewFixtures;

namespace Mutalaa.Domain.Tests;

/// <summary>
/// "Uzmana gonder" (K-51 madde 2), "Ima olarak isaretle" ve "Kalip listesine ekle" (A18.4). Metinler sentetiktir; "Arapca" dizi yerine
/// Latin harfli deneme metni kullanilir, normalizasyon anahtari kendi surumunden alinir.
/// </summary>
public class ReviewHandoffAndLinkActionsTests
{
    private const string Hash = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef";
    private const string Hash16 = "0123456789abcdef";

    private static string CodeOf(Action action) => Assert.Throws<DomainException>(action).Code;

    // --- Uzmana gonder ---

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void A_handoff_moves_an_open_record_to_uzmanda_and_keeps_the_original_action(bool turkish) => CultureScope.For(turkish, () =>
    {
        Review review = StatusReview(ReviewTargets.QuranWordFix, ReviewFields.Pos, XrefOrigin.Editor, "editor-a");
        review.Duzenlenen = """{"new_value": "N"}""";

        ReviewOutcome outcome = ReviewHandoff.ToExpert(review, "editor-b", "Uzman gorusu gerekli", Now);
        outcome.ApplyTo(review);

        Assert.Equal(ReviewStatus.Uzmanda, review.Durum);
        Assert.Equal(ReviewActions.Oner, review.Eylem);
        Assert.Equal("editor-b", review.Inceleyen);
        Assert.Equal("Uzman gorusu gerekli", review.Gerekce);
        Assert.Equal(Now, review.IncelendiAt);
        Assert.Null(review.IkinciGerekce);
        Assert.Equal("""{"new_value": "N"}""", review.Duzenlenen);
        Assert.Null(outcome.TargetStatus);
    });

    [Theory]
    [InlineData(ReviewStatus.Uzmanda)]
    [InlineData(ReviewStatus.Onaylandi)]
    [InlineData(ReviewStatus.Reddedildi)]
    [InlineData(ReviewStatus.GeriAlindi)]
    public void Only_an_open_record_can_be_sent(ReviewStatus durum)
    {
        Review review = StatusReview(durum: durum);

        Assert.Equal(DomainErrorCodes.DurumGecisiGecersiz, CodeOf(() => ReviewHandoff.ToExpert(review, "editor-a", "Deneme", Now)));
    }

    [Fact]
    public void A_unit_text_review_cannot_be_sent_because_of_the_two_stage_flow()
    {
        Assert.Equal(DomainErrorCodes.IncelemeDesteklenmiyor, CodeOf(() => ReviewHandoff.ToExpert(UnitReview(), "editor-a", "Deneme", Now)));
    }

    [Fact]
    public void An_unsupported_target_is_refused_with_inceleme_desteklenmiyor()
    {
        Review review = StatusReview(ReviewTargets.Source, ReviewFields.Status);

        Assert.Equal(DomainErrorCodes.IncelemeDesteklenmiyor, CodeOf(() => ReviewHandoff.ToExpert(review, "editor-a", "Deneme", Now)));
    }

    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("   ")]
    public void A_handoff_needs_a_reason(string? gerekce)
    {
        Assert.Equal(DomainErrorCodes.Dogrulama, CodeOf(() => ReviewHandoff.ToExpert(StatusReview(), "editor-a", gerekce, Now)));
    }

    [Fact]
    public void A_handoff_needs_an_actor_and_a_reason_within_the_limit()
    {
        Assert.Equal(DomainErrorCodes.Dogrulama, CodeOf(() => ReviewHandoff.ToExpert(StatusReview(), null, "Deneme", Now)));
        Assert.Equal(
            DomainErrorCodes.Dogrulama,
            CodeOf(() => ReviewHandoff.ToExpert(StatusReview(), "editor-a", new string('a', ReviewDecisions.MaxGerekceLength + 1), Now)));
    }

    // --- Ima ---

    private static Xref Source(XrefType type = XrefType.Iktibas, XrefStatus status = XrefStatus.Aday, string evidence = """{"src_hash": "aaaaaaaaaaaaaaaa", "dst_hash": "bbbbbbbbbbbbbbbb", "source_id": "deneme", "run_id": "r1", "matched_words": 9}""") =>
        new()
        {
            Id = Guid.CreateVersion7(),
            SrcAnchor = AnchorRef.Parse("rn:sozler:soz-10:p4"),
            SrcSpan = new AnchorSpan(5, 30),
            DstAnchor = AnchorRef.Parse("q:2:255"),
            DstSpan = new AnchorSpan(3, 8),
            Type = type,
            Score = 0.6f,
            Confidence = 0.55f,
            Evidence = evidence,
            Origin = XrefOrigin.Hat,
            Status = status,
            DataVersion = "test-1",
        };

    private static Review LinkReview(Xref xref, ReviewStatus durum = ReviewStatus.Acik) =>
        new()
        {
            Id = 7,
            HedefTablo = ReviewTargets.Xref,
            HedefAnahtar = xref.Id.ToString("D"),
            XrefId = xref.Id,
            Alan = ReviewFields.Status,
            Eylem = ReviewActions.Oner,
            Koken = XrefOrigin.Hat,
            Oneren = "hat",
            Durum = durum,
        };

    [Fact]
    public void Ima_opens_an_approved_editor_row_from_the_same_source_to_the_same_target()
    {
        Xref source = Source();
        Guid id = Guid.CreateVersion7();

        (Xref ima, Review audit) = LinkQueueActions.MarkIma(source, LinkReview(source), id, "editor-a", "Deneme gerekcesi", Now);

        Assert.Equal(id, ima.Id);
        Assert.Equal(XrefType.Ima, ima.Type);
        Assert.Equal(XrefOrigin.Editor, ima.Origin);
        Assert.Equal(XrefStatus.Onayli, ima.Status);
        Assert.Equal(1f, ima.Confidence);
        Assert.Equal(1f, ima.Score);
        Assert.Equal(source.SrcAnchor, ima.SrcAnchor);
        Assert.Equal(source.SrcSpan, ima.SrcSpan);
        Assert.Equal(source.DstAnchor, ima.DstAnchor);
        Assert.Equal(source.DstSpan, ima.DstSpan);
        Assert.Equal("test-1", ima.DataVersion);

        using JsonDocument evidence = JsonDocument.Parse(ima.Evidence);
        Assert.True(evidence.RootElement.GetProperty("editor_ima").GetBoolean());
        Assert.Equal("aaaaaaaaaaaaaaaa", evidence.RootElement.GetProperty("src_hash").GetString());
        Assert.Equal("bbbbbbbbbbbbbbbb", evidence.RootElement.GetProperty("dst_hash").GetString());
        Assert.Equal("deneme", evidence.RootElement.GetProperty("source_id").GetString());
        Assert.False(evidence.RootElement.TryGetProperty("run_id", out _));
        Assert.False(evidence.RootElement.TryGetProperty("matched_words", out _));

        Assert.Equal(ReviewTargets.Xref, audit.HedefTablo);
        Assert.Equal(id.ToString("D"), audit.HedefAnahtar);
        Assert.Equal(id, audit.XrefId);
        Assert.Equal(ReviewActions.ImaIsaretle, audit.Eylem);
        Assert.Equal(ReviewStatus.Onaylandi, audit.Durum);
        Assert.Equal("editor-a", audit.Oneren);
        Assert.Equal("editor-a", audit.Inceleyen);
        Assert.Equal("Deneme gerekcesi", audit.Gerekce);
        Assert.Equal(XrefOrigin.Editor, audit.Koken);

        // Ozgun aday korunur.
        Assert.Equal(XrefType.Iktibas, source.Type);
        Assert.Equal(XrefStatus.Aday, source.Status);
    }

    [Fact]
    public void Ima_works_for_atif_too_and_a_row_that_is_already_ima_conflicts()
    {
        Xref atif = Source(XrefType.Atif);
        Assert.Equal(XrefType.Ima, LinkQueueActions.MarkIma(atif, LinkReview(atif), Guid.CreateVersion7(), "editor-a", "Deneme", Now).Ima.Type);

        Xref ima = Source(XrefType.Ima);
        Assert.Equal(DomainErrorCodes.DurumGecisiGecersiz, CodeOf(() => LinkQueueActions.MarkIma(ima, LinkReview(ima), Guid.CreateVersion7(), "editor-a", "Deneme", Now)));
    }

    [Theory]
    [InlineData(XrefType.Kok)]
    [InlineData(XrefType.Lemma)]
    [InlineData(XrefType.BenzerAyet)]
    public void Ima_is_refused_for_the_automatic_types(XrefType type)
    {
        Xref source = Source(type);

        Assert.Equal(DomainErrorCodes.IncelemeDesteklenmiyor, CodeOf(() => LinkQueueActions.MarkIma(source, LinkReview(source), Guid.CreateVersion7(), "editor-a", "Deneme", Now)));
    }

    [Theory]
    [InlineData(ReviewStatus.Onaylandi)]
    [InlineData(ReviewStatus.Reddedildi)]
    [InlineData(ReviewStatus.Uzmanda)]
    public void Ima_needs_an_open_review(ReviewStatus durum)
    {
        Xref source = Source();

        Assert.Equal(
            DomainErrorCodes.DurumGecisiGecersiz,
            CodeOf(() => LinkQueueActions.MarkIma(source, LinkReview(source, durum), Guid.CreateVersion7(), "editor-a", "Deneme", Now)));
    }

    [Fact]
    public void Ima_needs_a_candidate_row_a_link_review_a_reason_and_an_actor()
    {
        Xref approved = Source(status: XrefStatus.Onayli);
        Assert.Equal(DomainErrorCodes.DurumGecisiGecersiz, CodeOf(() => LinkQueueActions.MarkIma(approved, LinkReview(approved), Guid.CreateVersion7(), "editor-a", "Deneme", Now)));

        Xref source = Source();
        Review notLink = StatusReview(ReviewTargets.Lemma, ReviewFields.Status);
        Assert.Equal(DomainErrorCodes.IncelemeDesteklenmiyor, CodeOf(() => LinkQueueActions.MarkIma(source, notLink, Guid.CreateVersion7(), "editor-a", "Deneme", Now)));
        Assert.Equal(DomainErrorCodes.Dogrulama, CodeOf(() => LinkQueueActions.MarkIma(source, LinkReview(source), Guid.CreateVersion7(), "editor-a", " ", Now)));
        Assert.Equal(DomainErrorCodes.Dogrulama, CodeOf(() => LinkQueueActions.MarkIma(source, LinkReview(source), Guid.CreateVersion7(), null, "Deneme", Now)));
    }

    // --- Kalip ---

    // Anahtar Arapca arama anahtaridir (ar_norm); Latin harfli metin bos anahtar verir. Dizi sentetiktir (rastgele harfler, Kur'an metni degil).
    private const string Arab = "بتث جحخ";

    private static readonly string SrcText = "Deneme paragrafi baslangic " + Arab + " ve devami";

    private static string Key(string text) => Mutalaa.Domain.Text.SearchNormalizer.Keys(text).ArNorm.Trim();

    private static string EvidenceFor(string? phraseKey = null) =>
        phraseKey is null
            ? $$"""{"src_hash": "{{Hash16}}", "matched_words": 3}"""
            : $$"""{"src_hash": "{{Hash16}}", "phrase_key": "{{phraseKey}}"}""";

    [Fact]
    public void The_pattern_key_comes_from_the_evidence_when_the_pipeline_gave_one()
    {
        string key = LinkQueueActions.PatternKey(EvidenceFor(Arab), null, null, null);

        Assert.NotEmpty(key);
        Assert.Equal(Key(Arab), key);
    }

    [Fact]
    public void Without_a_phrase_key_the_pattern_key_is_the_normalized_matched_slice_of_the_source_text()
    {
        // "Deneme paragrafi baslangic " = 27 kod noktasi; eslesen dilim Arab (7 kod noktasi).
        string key = LinkQueueActions.PatternKey(EvidenceFor(), SrcText, Hash, new AnchorSpan(27, 34));

        Assert.NotEmpty(key);
        Assert.Equal(Key(Arab), key);
    }

    [Fact]
    public void A_mismatching_source_hash_a_missing_span_or_blank_key_is_refused_with_inceleme_desteklenmiyor()
    {
        string other = "ffffffffffffffff" + new string('0', 48);

        Assert.Equal(DomainErrorCodes.IncelemeDesteklenmiyor, CodeOf(() => LinkQueueActions.PatternKey(EvidenceFor(), SrcText, other, new AnchorSpan(27, 34))));
        Assert.Equal(DomainErrorCodes.IncelemeDesteklenmiyor, CodeOf(() => LinkQueueActions.PatternKey(EvidenceFor(), SrcText, Hash, null)));
        Assert.Equal(DomainErrorCodes.IncelemeDesteklenmiyor, CodeOf(() => LinkQueueActions.PatternKey(EvidenceFor(), null, null, new AnchorSpan(27, 34))));
        Assert.Equal(DomainErrorCodes.IncelemeDesteklenmiyor, CodeOf(() => LinkQueueActions.PatternKey("{}", SrcText, Hash, new AnchorSpan(27, 34))));
        Assert.Equal(DomainErrorCodes.IncelemeDesteklenmiyor, CodeOf(() => LinkQueueActions.PatternKey(EvidenceFor("   "), null, null, null)));
    }

    [Fact]
    public void Adding_to_the_pattern_list_rejects_the_candidate_and_writes_a_closed_audit_record()
    {
        Xref source = Source(evidence: EvidenceFor(Arab));
        Review review = LinkReview(source);

        (ReviewOutcome reject, Review audit, string key) = LinkQueueActions.AddToPatternList(review, source, null, null, "editor-a", "Kalip ifade", Now);

        Assert.Equal(ReviewStatus.Reddedildi, reject.Durum);
        Assert.Equal(XrefStatus.Red, reject.TargetStatus);
        Assert.Equal("Kalip ifade", reject.Gerekce);
        Assert.Equal(Key(Arab), key);

        Assert.Equal(ReviewTargets.Xref, audit.HedefTablo);
        Assert.Equal(source.Id.ToString("D"), audit.HedefAnahtar);
        Assert.Equal(source.Id, audit.XrefId);
        Assert.Equal(ReviewActions.KalipEkle, audit.Eylem);
        Assert.Equal(ReviewStatus.Onaylandi, audit.Durum);
        Assert.Equal(XrefOrigin.Editor, audit.Koken);
        Assert.Equal("editor-a", audit.Oneren);
        using JsonDocument proposal = JsonDocument.Parse(audit.Onerilen!);
        Assert.Equal(key, proposal.RootElement.GetProperty("anahtar").GetString());
        Assert.Equal("Kalip ifade", proposal.RootElement.GetProperty("gerekce").GetString());
    }

    [Theory]
    [InlineData(XrefType.Atif)]
    [InlineData(XrefType.Ima)]
    [InlineData(XrefType.Kok)]
    public void Only_an_iktibas_candidate_can_join_the_pattern_list(XrefType type)
    {
        Xref source = Source(type, evidence: EvidenceFor(Arab));

        Assert.Equal(
            DomainErrorCodes.IncelemeDesteklenmiyor,
            CodeOf(() => LinkQueueActions.AddToPatternList(LinkReview(source), source, null, null, "editor-a", "Deneme", Now)));
    }

    [Theory]
    [InlineData(ReviewStatus.Uzmanda)]
    [InlineData(ReviewStatus.Onaylandi)]
    public void The_pattern_list_needs_an_open_review_and_a_candidate_row(ReviewStatus durum)
    {
        Xref source = Source(evidence: EvidenceFor(Arab));

        Assert.Equal(
            DomainErrorCodes.DurumGecisiGecersiz,
            CodeOf(() => LinkQueueActions.AddToPatternList(LinkReview(source, durum), source, null, null, "editor-a", "Deneme", Now)));

        Xref approved = Source(status: XrefStatus.Onayli, evidence: EvidenceFor(Arab));
        Assert.Equal(
            DomainErrorCodes.DurumGecisiGecersiz,
            CodeOf(() => LinkQueueActions.AddToPatternList(LinkReview(approved), approved, null, null, "editor-a", "Deneme", Now)));
    }
}
