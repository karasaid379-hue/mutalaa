using System.Text.Json;
using Mutalaa.Domain.Links;
using Mutalaa.Domain.Reviews;
using Mutalaa.Domain.Tests.Support;
using static Mutalaa.Domain.Tests.Support.ReviewFixtures;

namespace Mutalaa.Domain.Tests;

/// <summary>
/// Turkce lemma kok eslemesi incelemesi (K-51 madde 9): onay, ret, Duzenle ve onayla, otomatik onaya itiraz ve etimolojik isaret.
/// Veri sentetiktir (kimlikler ve "deneme" metinleri); ortak yardimcilar Turk kulturunde de calisir.
/// </summary>
public class ReviewRootMappingDecisionTests
{
    private const int RootA = 11;
    private const int RootB = 12;
    private const int ArLemma = 21;

    private static string Value(int root = RootA, int? ar = ArLemma, bool etymological = false)
    {
        Dictionary<string, object?> map = new() { ["root_id"] = root, ["ar_lemma_id"] = ar, ["etymological_only"] = etymological };
        return JsonSerializer.Serialize(map);
    }

    private static string Proposal(int root = RootA, int? ar = ArLemma, bool etymological = false)
    {
        Dictionary<string, object?> map = new()
        {
            ["root_id"] = root,
            ["ar_lemma_id"] = ar,
            ["etymological_only"] = etymological,
            ["neden"] = "deneme gerekcesi",
            ["kanit_ozeti"] = new Dictionary<string, object> { ["kaynak_sayisi"] = 2 },
        };
        return JsonSerializer.Serialize(map);
    }

    private static Review Mapping(string? onerilen = null, XrefOrigin koken = XrefOrigin.Hat, string oneren = "hat", ReviewStatus durum = ReviewStatus.Acik) =>
        new()
        {
            HedefTablo = ReviewTargets.Lemma,
            HedefAnahtar = "301",
            Alan = ReviewFields.KokEslemesi,
            Eylem = ReviewActions.Oner,
            Onerilen = onerilen ?? Proposal(),
            Koken = koken,
            Oneren = oneren,
            Durum = durum,
        };

    private static Review Objection(string oneren = "test-editor-2") =>
        Mapping(LemmaMappingPayload.ToObjectionPayload("deneme itiraz gerekcesi"), XrefOrigin.Editor, oneren);

    private static RootMappingFacts Facts(bool root = true, bool ar = true, string? lang = "ar", int? arRoot = RootA) => new(root, ar, lang, arRoot);

    private static LemmaReviewState Lemma(
        string lang = "tr",
        string? onayYolu = null,
        string? origin = "kaikki",
        bool etymological = false,
        int? root = null,
        int? ar = null,
        RootMappingFacts? facts = null) =>
        new(lang, root, ar, etymological, origin, onayYolu) { Facts = facts ?? Facts() };

    private static ReviewTargetState Candidate(LemmaReviewState? lemma = null, XrefStatus status = XrefStatus.Aday) =>
        ReviewTargetState.ForLemma(status, lemma ?? Lemma());

    private static ReviewTargetState AutoApproved() =>
        ReviewTargetState.ForLemma(XrefStatus.Onayli, Lemma(onayYolu: LemmaApprovalPaths.Otomatik, root: RootA, ar: ArLemma));

    [Fact]
    public void The_kok_eslemesi_field_of_a_lemma_is_a_supported_review_and_the_other_fields_still_are_not()
    {
        Assert.True(ReviewDecisions.IsSupported(ReviewTargets.Lemma, ReviewFields.KokEslemesi));
        Assert.True(ReviewDecisions.IsSupported(ReviewTargets.Lemma, ReviewFields.Status));
        Assert.False(ReviewDecisions.IsSupported(ReviewTargets.Lemma, "baska"));
        Assert.False(ReviewDecisions.IsSupported(ReviewTargets.Xref, ReviewFields.KokEslemesi));
        Assert.False(ReviewDecisions.IsSupported(ReviewTargets.LemmaGloss, ReviewFields.KokEslemesi));
        Assert.True(ReviewDecisions.IsRootMappingTarget(ReviewTargets.Lemma, ReviewFields.KokEslemesi));
        Assert.False(ReviewDecisions.IsRootMappingTarget(ReviewTargets.Lemma, ReviewFields.Status));
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void Approving_the_proposal_writes_the_mapping_with_the_editor_approval_path_and_keeps_the_hat_origin(bool turkish)
    {
        CultureScope.For(turkish, () =>
        {
            ReviewOutcome outcome = ReviewDecisions.Approve(Mapping(), Request(), Candidate());

            Assert.Equal(ReviewStatus.Onaylandi, outcome.Durum);
            Assert.Equal(ReviewActions.Onayla, outcome.Eylem);
            Assert.Equal(XrefStatus.Onayli, outcome.TargetStatus);
            Assert.Equal("test-editor-1", outcome.Inceleyen);
            Assert.Null(outcome.Duzenlenen);
            LemmaMappingUpdate update = Assert.NotNull(outcome.LemmaMapping);
            Assert.Equal(RootA, update.RootId);
            Assert.Equal(ArLemma, update.ArLemmaId);
            Assert.False(update.EtymologicalOnly);
            Assert.Equal("kaikki", update.Origin);
            Assert.Equal(LemmaApprovalPaths.Editor, update.OnayYolu);
        });
    }

    [Fact]
    public void An_edit_that_differs_from_the_proposal_records_duzenle_onayla_makes_the_origin_editor_and_stores_the_value()
    {
        ReviewOutcome outcome = ReviewDecisions.Approve(
            Mapping(),
            Request(duzenlenen: Value(RootB, null, etymological: true)),
            Candidate(Lemma(facts: Facts(arRoot: null))));

        Assert.Equal(ReviewActions.DuzenleOnayla, outcome.Eylem);
        LemmaMappingUpdate update = Assert.NotNull(outcome.LemmaMapping);
        Assert.Equal(RootB, update.RootId);
        Assert.Null(update.ArLemmaId);
        Assert.True(update.EtymologicalOnly);
        Assert.Equal(LemmaOrigins.Editor, update.Origin);
        Assert.Equal(LemmaApprovalPaths.Editor, update.OnayYolu);
        using JsonDocument stored = JsonDocument.Parse(outcome.Duzenlenen!);
        Assert.Equal(RootB, stored.RootElement.GetProperty("root_id").GetInt32());
        Assert.Equal(JsonValueKind.Null, stored.RootElement.GetProperty("ar_lemma_id").ValueKind);
        Assert.True(stored.RootElement.GetProperty("etymological_only").GetBoolean());
    }

    [Fact]
    public void An_edit_equal_to_the_proposal_still_records_duzenle_onayla_but_keeps_the_origin()
    {
        ReviewOutcome outcome = ReviewDecisions.Approve(Mapping(), Request(duzenlenen: Value()), Candidate());

        Assert.Equal(ReviewActions.DuzenleOnayla, outcome.Eylem);
        Assert.Equal("kaikki", Assert.NotNull(outcome.LemmaMapping).Origin);
    }

    [Fact]
    public void Without_a_proposal_value_the_edit_is_required_and_the_origin_becomes_editor()
    {
        Review review = Mapping();
        review.Onerilen = null;

        Assert.Equal(DomainErrorCodes.Dogrulama, CodeOf(() => ReviewDecisions.Approve(review, Request(), Candidate())));

        ReviewOutcome outcome = ReviewDecisions.Approve(review, Request(duzenlenen: Value()), Candidate());
        Assert.Equal(LemmaOrigins.Editor, Assert.NotNull(outcome.LemmaMapping).Origin);
    }

    [Fact]
    public void A_proposal_without_root_id_is_a_validation_error_unless_the_edit_replaces_it()
    {
        Review review = Mapping("{\"etymological_only\": false}");

        Assert.Equal(DomainErrorCodes.Dogrulama, CodeOf(() => ReviewDecisions.Approve(review, Request(), Candidate())));
        Assert.NotNull(ReviewDecisions.Approve(review, Request(duzenlenen: Value()), Candidate()).LemmaMapping);
    }

    [Theory]
    [InlineData("{\"root_id\": 11}")]
    [InlineData("{\"root_id\": 11, \"etymological_only\": \"false\"}")]
    [InlineData("{\"etymological_only\": false}")]
    [InlineData("{\"root_id\": 0, \"etymological_only\": false}")]
    [InlineData("{\"root_id\": \"11\", \"etymological_only\": false}")]
    [InlineData("{\"root_id\": 11.5, \"etymological_only\": false}")]
    [InlineData("{\"root_id\": 11, \"ar_lemma_id\": -3, \"etymological_only\": false}")]
    [InlineData("{\"root_id\": 11, \"ar_lemma_id\": \"x\", \"etymological_only\": false}")]
    [InlineData("[1]")]
    [InlineData("not json")]
    public void A_malformed_edited_value_is_a_validation_error(string edited)
    {
        Assert.Equal(DomainErrorCodes.Dogrulama, CodeOf(() => ReviewDecisions.Approve(Mapping(), Request(duzenlenen: edited), Candidate())));
    }

    [Fact]
    public void A_missing_root_is_a_validation_error()
    {
        LemmaReviewState lemma = Lemma(facts: Facts(root: false));

        Assert.Equal(DomainErrorCodes.Dogrulama, CodeOf(() => ReviewDecisions.Approve(Mapping(), Request(), Candidate(lemma))));
    }

    [Fact]
    public void The_arabic_lemma_must_exist_be_arabic_and_share_the_root()
    {
        Assert.Equal(
            DomainErrorCodes.Dogrulama,
            CodeOf(() => ReviewDecisions.Approve(Mapping(), Request(), Candidate(Lemma(facts: Facts(ar: false, lang: null, arRoot: null))))));
        Assert.Equal(
            DomainErrorCodes.Dogrulama,
            CodeOf(() => ReviewDecisions.Approve(Mapping(), Request(), Candidate(Lemma(facts: Facts(lang: "tr"))))));
        Assert.Equal(
            DomainErrorCodes.Dogrulama,
            CodeOf(() => ReviewDecisions.Approve(Mapping(), Request(), Candidate(Lemma(facts: Facts(arRoot: RootB))))));
        Assert.Equal(
            DomainErrorCodes.Dogrulama,
            CodeOf(() => ReviewDecisions.Approve(Mapping(), Request(), Candidate(Lemma(facts: Facts(arRoot: null))))));
    }

    [Fact]
    public void A_mapping_without_an_arabic_lemma_needs_only_the_root()
    {
        ReviewOutcome outcome = ReviewDecisions.Approve(
            Mapping(Proposal(ar: null)),
            Request(),
            Candidate(Lemma(facts: new RootMappingFacts(true, false, null, null))));

        Assert.Null(Assert.NotNull(outcome.LemmaMapping).ArLemmaId);
    }

    [Fact]
    public void Missing_facts_are_a_programming_error_not_a_user_error()
    {
        LemmaReviewState lemma = new("tr", null, null, false, "kaikki", null);

        Assert.Throws<InvalidOperationException>(() => ReviewDecisions.Approve(Mapping(), Request(), ReviewTargetState.ForLemma(XrefStatus.Aday, lemma)));
    }

    [Fact]
    public void An_arabic_lemma_has_no_mapping_review_for_approval_or_rejection()
    {
        ReviewTargetState arabic = Candidate(Lemma(lang: "ar", origin: "qac"), XrefStatus.Onayli);

        Assert.Equal(DomainErrorCodes.IncelemeDesteklenmiyor, CodeOf(() => ReviewDecisions.Approve(Mapping(), Request(), arabic)));
        Assert.Equal(DomainErrorCodes.IncelemeDesteklenmiyor, CodeOf(() => ReviewDecisions.Reject(Mapping(), Request(), arabic)));
    }

    [Theory]
    [InlineData(XrefStatus.Onayli)]
    [InlineData(XrefStatus.Red)]
    public void Only_a_candidate_target_can_be_approved_or_rejected(XrefStatus status)
    {
        ReviewTargetState target = Candidate(status: status);

        Assert.Equal(DomainErrorCodes.DurumGecisiGecersiz, CodeOf(() => ReviewDecisions.Approve(Mapping(), Request(), target)));
        Assert.Equal(DomainErrorCodes.DurumGecisiGecersiz, CodeOf(() => ReviewDecisions.Reject(Mapping(), Request(), target)));
    }

    [Fact]
    public void An_editor_cannot_approve_their_own_proposal_but_can_reject_it()
    {
        Review review = Mapping(koken: XrefOrigin.Editor, oneren: "test-editor-1");

        Assert.Equal(DomainErrorCodes.DurumGecisiGecersiz, CodeOf(() => ReviewDecisions.Approve(review, Request("test-editor-1"), Candidate())));
        Assert.Equal(ReviewStatus.Reddedildi, ReviewDecisions.Reject(review, Request("test-editor-1"), Candidate()).Durum);

        // Baska bir editor onaylayabilir; kullanici adi buyuk-kucuk harfe duyarsiz karsilastirilir.
        Assert.Equal(ReviewStatus.Onaylandi, ReviewDecisions.Approve(review, Request("test-editor-2"), Candidate()).Durum);
        Assert.Equal(DomainErrorCodes.DurumGecisiGecersiz, CodeOf(() => ReviewDecisions.Approve(review, Request("TEST-EDITOR-1"), Candidate())));
    }

    [Fact]
    public void A_decided_review_and_a_missing_gerekce_are_rejected_before_the_target_is_read()
    {
        Assert.Equal(DomainErrorCodes.DurumGecisiGecersiz, CodeOf(() => ReviewDecisions.Approve(Mapping(durum: ReviewStatus.Onaylandi), Request(), Candidate())));
        Assert.Equal(DomainErrorCodes.Dogrulama, CodeOf(() => ReviewDecisions.Approve(Mapping(), Request(gerekce: " "), Candidate())));
        Assert.Equal(DomainErrorCodes.Dogrulama, CodeOf(() => ReviewDecisions.Reject(Mapping(), Request(gerekce: null), Candidate())));
    }

    [Fact]
    public void Rejecting_a_candidate_marks_it_red_without_a_mapping_change_and_takes_no_value()
    {
        ReviewOutcome outcome = ReviewDecisions.Reject(Mapping(), Request(), Candidate());

        Assert.Equal(ReviewStatus.Reddedildi, outcome.Durum);
        Assert.Equal(ReviewActions.Reddet, outcome.Eylem);
        Assert.Equal(XrefStatus.Red, outcome.TargetStatus);
        Assert.Null(outcome.LemmaMapping);
        Assert.Equal(DomainErrorCodes.Dogrulama, CodeOf(() => ReviewDecisions.Reject(Mapping(), Request(duzenlenen: Value()), Candidate())));
    }

    // Itiraz (otomatik onaya)

    [Fact]
    public void Approving_an_objection_returns_the_lemma_to_candidate_and_clears_the_approval_path()
    {
        ReviewOutcome outcome = ReviewDecisions.Approve(Objection(), Request("test-editor-1"), AutoApproved());

        Assert.Equal(ReviewStatus.Onaylandi, outcome.Durum);
        Assert.Equal(ReviewActions.Onayla, outcome.Eylem);
        Assert.Equal(XrefStatus.Aday, outcome.TargetStatus);
        LemmaMappingUpdate update = Assert.NotNull(outcome.LemmaMapping);
        Assert.Null(update.OnayYolu);

        // Esleme degerleri ve koken oldugu gibi kalir; kanit hic dokunulmaz (Api yazmaz).
        Assert.Equal(RootA, update.RootId);
        Assert.Equal(ArLemma, update.ArLemmaId);
        Assert.Equal("kaikki", update.Origin);
    }

    [Fact]
    public void The_editor_who_opened_the_objection_cannot_approve_it_but_can_reject_it()
    {
        Review objection = Objection(oneren: "test-editor-1");

        Assert.Equal(DomainErrorCodes.DurumGecisiGecersiz, CodeOf(() => ReviewDecisions.Approve(objection, Request("test-editor-1"), AutoApproved())));
        ReviewOutcome withdrawn = ReviewDecisions.Reject(objection, Request("test-editor-1"), AutoApproved());
        Assert.Equal(ReviewStatus.Reddedildi, withdrawn.Durum);
    }

    [Fact]
    public void Rejecting_an_objection_leaves_the_lemma_unchanged_even_when_it_is_no_longer_auto_approved()
    {
        ReviewOutcome onAuto = ReviewDecisions.Reject(Objection(), Request("test-editor-1"), AutoApproved());
        ReviewOutcome onCandidate = ReviewDecisions.Reject(Objection(), Request("test-editor-1"), Candidate());

        Assert.Null(onAuto.TargetStatus);
        Assert.Null(onAuto.LemmaMapping);
        Assert.Null(onCandidate.TargetStatus);
        Assert.Null(onCandidate.LemmaMapping);
        Assert.Equal(ReviewActions.Reddet, onAuto.Eylem);
    }

    [Fact]
    public void An_objection_is_approved_only_while_the_lemma_is_auto_approved()
    {
        Assert.Equal(DomainErrorCodes.DurumGecisiGecersiz, CodeOf(() => ReviewDecisions.Approve(Objection(), Request("test-editor-1"), Candidate())));
        Assert.Equal(
            DomainErrorCodes.DurumGecisiGecersiz,
            CodeOf(() => ReviewDecisions.Approve(
                Objection(),
                Request("test-editor-1"),
                ReviewTargetState.ForLemma(XrefStatus.Onayli, Lemma(onayYolu: LemmaApprovalPaths.Editor, root: RootA)))));
        Assert.Equal(
            DomainErrorCodes.DurumGecisiGecersiz,
            CodeOf(() => ReviewDecisions.Approve(
                Objection(),
                Request("test-editor-1"),
                ReviewTargetState.ForLemma(XrefStatus.Red, Lemma(onayYolu: LemmaApprovalPaths.Otomatik, root: RootA)))));
    }

    [Fact]
    public void An_objection_approval_takes_no_edited_value()
    {
        Assert.Equal(DomainErrorCodes.IncelemeDesteklenmiyor, CodeOf(() => ReviewDecisions.Approve(Objection(), Request("test-editor-1", duzenlenen: Value()), AutoApproved())));
    }

    [Fact]
    public void An_objection_on_an_arabic_lemma_is_unsupported()
    {
        ReviewTargetState arabic = ReviewTargetState.ForLemma(XrefStatus.Onayli, Lemma(lang: "ar", onayYolu: null));

        Assert.Equal(DomainErrorCodes.IncelemeDesteklenmiyor, CodeOf(() => ReviewDecisions.Approve(Objection(), Request("test-editor-1"), arabic)));
    }

    [Fact]
    public void Opening_an_objection_builds_an_editor_origin_review_with_the_reason_and_the_current_mapping()
    {
        Review review = LemmaObjections.Open(301, XrefStatus.Onayli, Lemma(onayYolu: LemmaApprovalPaths.Otomatik, root: RootA, ar: ArLemma, etymological: true), "test-editor-1", "Deneme itiraz gerekcesi", hasOpenObjection: false);

        Assert.Equal(ReviewTargets.Lemma, review.HedefTablo);
        Assert.Equal("301", review.HedefAnahtar);
        Assert.Equal(ReviewFields.KokEslemesi, review.Alan);
        Assert.Equal(ReviewActions.Oner, review.Eylem);
        Assert.Equal(XrefOrigin.Editor, review.Koken);
        Assert.Equal("test-editor-1", review.Oneren);
        Assert.Equal(ReviewStatus.Acik, review.Durum);
        Assert.Equal("Deneme itiraz gerekcesi", review.Gerekce);
        Assert.True(LemmaMappingPayload.IsObjection(review.Onerilen));
        using JsonDocument proposed = JsonDocument.Parse(review.Onerilen!);
        Assert.Equal("Deneme itiraz gerekcesi", proposed.RootElement.GetProperty("gerekce").GetString());
        using JsonDocument previous = JsonDocument.Parse(review.Onceki!);
        Assert.Equal(RootA, previous.RootElement.GetProperty("root_id").GetInt32());
        Assert.True(previous.RootElement.GetProperty("etymological_only").GetBoolean());
        Assert.Equal("otomatik", previous.RootElement.GetProperty("onay_yolu").GetString());
    }

    [Fact]
    public void Opening_an_objection_has_a_fixed_check_order_and_exact_error_codes()
    {
        LemmaReviewState auto = Lemma(onayYolu: LemmaApprovalPaths.Otomatik, root: RootA);

        Assert.Equal(DomainErrorCodes.Dogrulama, CodeOf(() => LemmaObjections.Open(1, XrefStatus.Onayli, auto, null, "g", false)));
        Assert.Equal(DomainErrorCodes.Dogrulama, CodeOf(() => LemmaObjections.Open(1, XrefStatus.Onayli, auto, "e", " ", false)));
        Assert.Equal(DomainErrorCodes.Dogrulama, CodeOf(() => LemmaObjections.Open(1, XrefStatus.Onayli, auto, "e", new string('a', 2001), false)));
        Assert.Equal(DomainErrorCodes.IncelemeDesteklenmiyor, CodeOf(() => LemmaObjections.Open(1, XrefStatus.Onayli, Lemma(lang: "ar"), "e", "g", false)));
        Assert.Equal(DomainErrorCodes.DurumGecisiGecersiz, CodeOf(() => LemmaObjections.Open(1, XrefStatus.Aday, auto, "e", "g", false)));
        Assert.Equal(DomainErrorCodes.DurumGecisiGecersiz, CodeOf(() => LemmaObjections.Open(1, XrefStatus.Onayli, Lemma(onayYolu: LemmaApprovalPaths.Editor), "e", "g", false)));
        Assert.Equal(DomainErrorCodes.DurumGecisiGecersiz, CodeOf(() => LemmaObjections.Open(1, XrefStatus.Onayli, auto, "e", "g", true)));
    }

    // Etimolojik isaret

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void Marking_an_auto_approved_lemma_changes_the_value_and_moves_it_to_the_editor_path_keeping_the_evidence(bool turkish)
    {
        CultureScope.For(turkish, () =>
        {
            EtymologyMark mark = LemmaEtymology.Apply(
                301,
                XrefStatus.Onayli,
                Lemma(onayYolu: LemmaApprovalPaths.Otomatik, root: RootA, ar: ArLemma),
                true,
                "test-editor-1",
                "Deneme gerekcesi",
                Now);

            Assert.True(mark.Update.EtymologicalOnly);
            Assert.Equal(LemmaApprovalPaths.Editor, mark.Update.OnayYolu);
            Assert.Equal(LemmaOrigins.Editor, mark.Update.Origin);
            Assert.Equal(RootA, mark.Update.RootId);
            Assert.Equal(ArLemma, mark.Update.ArLemmaId);

            Review audit = mark.Review;
            Assert.Equal(ReviewActions.EtimolojikIsaretle, audit.Eylem);
            Assert.Equal(ReviewStatus.Onaylandi, audit.Durum);
            Assert.Equal(XrefOrigin.Editor, audit.Koken);
            Assert.Equal("test-editor-1", audit.Oneren);
            Assert.Equal("test-editor-1", audit.Inceleyen);
            Assert.Equal(Now, audit.IncelendiAt);
            Assert.Equal("Deneme gerekcesi", audit.Gerekce);
            Assert.Equal("301", audit.HedefAnahtar);
            Assert.Equal(ReviewFields.KokEslemesi, audit.Alan);
            using JsonDocument previous = JsonDocument.Parse(audit.Onceki!);
            Assert.False(previous.RootElement.GetProperty("etymological_only").GetBoolean());
            using JsonDocument proposed = JsonDocument.Parse(audit.Onerilen!);
            Assert.True(proposed.RootElement.GetProperty("etymological_only").GetBoolean());
        });
    }

    [Fact]
    public void Clearing_the_mark_works_the_same_way_on_an_editor_approved_lemma()
    {
        EtymologyMark mark = LemmaEtymology.Apply(
            301,
            XrefStatus.Onayli,
            Lemma(onayYolu: LemmaApprovalPaths.Editor, root: RootA, etymological: true),
            false,
            "test-editor-1",
            "Deneme gerekcesi",
            Now);

        Assert.False(mark.Update.EtymologicalOnly);
        Assert.Equal(LemmaApprovalPaths.Editor, mark.Update.OnayYolu);
    }

    [Fact]
    public void The_etymological_mark_has_exact_error_codes()
    {
        LemmaReviewState ok = Lemma(onayYolu: LemmaApprovalPaths.Otomatik, root: RootA);

        Assert.Equal(DomainErrorCodes.Dogrulama, CodeOf(() => LemmaEtymology.Apply(1, XrefStatus.Onayli, ok, true, null, "g", Now)));
        Assert.Equal(DomainErrorCodes.Dogrulama, CodeOf(() => LemmaEtymology.Apply(1, XrefStatus.Onayli, ok, true, "e", null, Now)));
        Assert.Equal(DomainErrorCodes.IncelemeDesteklenmiyor, CodeOf(() => LemmaEtymology.Apply(1, XrefStatus.Onayli, Lemma(lang: "ar", root: RootA), true, "e", "g", Now)));
        Assert.Equal(DomainErrorCodes.DurumGecisiGecersiz, CodeOf(() => LemmaEtymology.Apply(1, XrefStatus.Aday, ok, true, "e", "g", Now)));
        Assert.Equal(DomainErrorCodes.DurumGecisiGecersiz, CodeOf(() => LemmaEtymology.Apply(1, XrefStatus.Red, ok, true, "e", "g", Now)));
        Assert.Equal(DomainErrorCodes.DurumGecisiGecersiz, CodeOf(() => LemmaEtymology.Apply(1, XrefStatus.Onayli, Lemma(onayYolu: LemmaApprovalPaths.Editor), true, "e", "g", Now)));
        Assert.Equal(DomainErrorCodes.Dogrulama, CodeOf(() => LemmaEtymology.Apply(1, XrefStatus.Onayli, ok, false, "e", "g", Now)));
    }

    // (lemma, status) hedefi: Turkce lemma onay yolu

    [Fact]
    public void A_plain_status_approval_of_a_turkish_lemma_also_sets_the_editor_approval_path()
    {
        Review review = Mapping();
        review.Alan = ReviewFields.Status;
        ReviewTargetState target = ReviewTargetState.ForLemma(XrefStatus.Aday, Lemma(root: RootA, ar: ArLemma));

        ReviewOutcome outcome = ReviewDecisions.Approve(review, Request(), target);

        Assert.Equal(XrefStatus.Onayli, outcome.TargetStatus);
        LemmaMappingUpdate update = Assert.NotNull(outcome.LemmaMapping);
        Assert.Equal(LemmaApprovalPaths.Editor, update.OnayYolu);
        Assert.Equal(RootA, update.RootId);
        Assert.Equal("kaikki", update.Origin);
    }

    [Fact]
    public void An_arabic_lemma_and_a_state_less_target_keep_the_plain_status_behaviour()
    {
        Review review = Mapping();
        review.Alan = ReviewFields.Status;

        Assert.Null(ReviewDecisions.Approve(review, Request(), ReviewTargetState.ForLemma(XrefStatus.Aday, Lemma(lang: "ar", origin: "qac"))).LemmaMapping);
        Assert.Null(ReviewDecisions.Approve(review, Request(), ReviewTargetState.ForStatus(XrefStatus.Aday)).LemmaMapping);
    }

    // Yukler ve ozetler

    [Fact]
    public void The_payload_reader_distinguishes_a_missing_value_from_a_malformed_one()
    {
        Assert.Null(LemmaMappingPayload.Read(null, "onerilen"));
        Assert.Null(LemmaMappingPayload.Read("  ", "onerilen"));
        Assert.Null(LemmaMappingPayload.Read("null", "onerilen"));
        Assert.Equal(new RootMappingValue(5, null, true), LemmaMappingPayload.Read("{\"root_id\":5,\"etymological_only\":true}", "onerilen"));
        Assert.Equal(new RootMappingValue(5, 9, false), LemmaMappingPayload.Read("{\"root_id\":5,\"ar_lemma_id\":9,\"etymological_only\":false}", "onerilen"));

        Assert.False(LemmaMappingPayload.TryRead("{\"root_id\":0}", out _));
        Assert.False(LemmaMappingPayload.TryRead(null, out _));
        Assert.True(LemmaMappingPayload.TryRead("{\"root_id\":5,\"etymological_only\":false}", out RootMappingValue value));
        Assert.Equal(5, value.RootId);
    }

    [Fact]
    public void The_objection_flag_is_read_only_from_a_true_itiraz_property()
    {
        Assert.True(LemmaMappingPayload.IsObjection("{\"itiraz\": true, \"gerekce\": \"x\"}"));
        Assert.False(LemmaMappingPayload.IsObjection("{\"itiraz\": false}"));
        Assert.False(LemmaMappingPayload.IsObjection("{\"itiraz\": \"true\"}"));
        Assert.False(LemmaMappingPayload.IsObjection("{\"root_id\": 1}"));
        Assert.False(LemmaMappingPayload.IsObjection("[true]"));
        Assert.False(LemmaMappingPayload.IsObjection("bozuk"));
        Assert.False(LemmaMappingPayload.IsObjection(null));
    }

    [Fact]
    public void The_evidence_summary_counts_sources_and_reads_the_match_decision_and_reason()
    {
        const string kanit = "{\"politika\":\"p\",\"politika_surumu\":\"1\",\"yontem\":\"y\",\"kaynaklar\":[{\"source_id\":\"a\"},{\"source_id\":\"b\"}],"
            + "\"qac\":{\"root_id\":11,\"letters\":\"deneme\",\"eslesme\":\"kok_harfleri\"},\"karar\":\"onayli\",\"neden\":\"yapisal_kanit\"}";

        LemmaKanitSummary summary = LemmaKanitSummary.Summarize(kanit) ?? throw new InvalidOperationException("ozet yok");

        Assert.Equal(2, summary.KaynakSayisi);
        Assert.Equal("kok_harfleri", summary.QacEslesme);
        Assert.Equal("onayli", summary.Karar);
        Assert.Equal("yapisal_kanit", summary.Neden);
        Assert.Equal("1", summary.PolitikaSurumu);
    }

    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("bozuk")]
    [InlineData("[1]")]
    public void No_summary_is_made_from_a_missing_or_unreadable_evidence(string? kanit)
    {
        Assert.Null(LemmaKanitSummary.Summarize(kanit));
    }

    [Fact]
    public void A_sparse_evidence_gives_a_partial_summary_with_nulls()
    {
        LemmaKanitSummary summary = LemmaKanitSummary.Summarize("{\"kaynaklar\":\"yok\",\"qac\":5,\"karar\":3}") ?? throw new InvalidOperationException("ozet yok");

        Assert.Null(summary.KaynakSayisi);
        Assert.Null(summary.QacEslesme);
        Assert.Equal("3", summary.Karar);
        Assert.Null(summary.Neden);
    }
}
