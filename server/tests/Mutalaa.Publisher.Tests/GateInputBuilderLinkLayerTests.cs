using Mutalaa.Domain.Links;
using Mutalaa.Domain.Releases;
using Mutalaa.Domain.Releases.Gate;
using Mutalaa.Infrastructure.Packs;
using Mutalaa.Infrastructure.Releases;

namespace Mutalaa.Publisher.Tests;

/// <summary>A18.6: GateInputBuilder'in baglanti katmani eslemesi (birim ozeti, xref uc ozetleri, xref_gate, Turkce lemma ve tr_* satirlari). Docker gerektirmez.</summary>
public class GateInputBuilderLinkLayerTests
{
    private static EditorialSnapshot Snapshot(
        IReadOnlyList<XrefRow>? xrefs = null,
        IReadOnlyList<XrefGateRow>? gates = null,
        IReadOnlyList<TrLemmaRow>? lemmas = null,
        IReadOnlyList<TrRootIndexRow>? index = null,
        IReadOnlyList<TrFormRow>? forms = null)
    {
        EditorialSnapshot basis = PackTestData.Snapshot();
        return new EditorialSnapshot
        {
            Sources = basis.Sources,
            Units = basis.Units,
            QuranWords = basis.QuranWords,
            QuranMarkers = basis.QuranMarkers,
            PageMaps = basis.PageMaps,
            Xrefs = xrefs ?? basis.Xrefs,
            XrefGates = gates ?? [],
            TrLemmas = lemmas ?? [],
            TrRootIndex = index ?? [],
            TrForms = forms ?? [],
        };
    }

    private static GateInput Build(EditorialSnapshot snapshot) =>
        GateInputBuilder.Build(snapshot, PackCatalog.Default, "pipeline/sources", fileExists: PackTestData.AllRegistered());

    private static TrLemmaRow Lemma(int id, string status, string? path, bool kanit) =>
        new(id, "deneme", "deneme-" + id, null, 0, null, false, 1, status, path, kanit, "kaikki", "kaikki-tr", "dv-1");

    [Fact]
    public void Units_carry_the_first_sixteen_hex_digits_of_their_content_hash()
    {
        EditorialSnapshot snapshot = Snapshot();

        GateInput input = Build(snapshot);

        foreach (UnitRow row in snapshot.Units)
        {
            GateUnit unit = Assert.Single(input.Units, u => u.Anchor == row.Anchor);
            Assert.Equal(16, unit.HashPrefix!.Length);
            Assert.StartsWith(unit.HashPrefix, row.ContentHash, StringComparison.Ordinal);
        }
    }

    [Fact]
    public void Xref_end_hashes_pass_through_and_are_null_when_the_evidence_has_none()
    {
        Guid withHash = Guid.NewGuid();
        Guid without = Guid.NewGuid();
        EditorialSnapshot snapshot = Snapshot(
            xrefs:
            [
                PackTestData.Xref("q:1:1", "q:1:2", "kok", "aday", id: withHash, srcHash: "aaaaaaaaaaaaaaaa", dstHash: "bbbbbbbbbbbbbbbb"),
                PackTestData.Xref("q:1:1", "q:1:2", "kok", "aday", id: without),
            ]);

        GateInput input = Build(snapshot);

        GateXref a = Assert.Single(input.Xrefs, x => x.Id == withHash);
        Assert.Equal(("aaaaaaaaaaaaaaaa", "bbbbbbbbbbbbbbbb"), (a.SrcHash, a.DstHash));
        GateXref b = Assert.Single(input.Xrefs, x => x.Id == without);
        Assert.Equal(((string?)null, (string?)null), (b.SrcHash, b.DstHash));
    }

    [Fact]
    public void Xref_gate_rows_become_measurements_and_an_unknown_type_is_a_data_error()
    {
        GateInput input = Build(Snapshot(gates:
        [
            new XrefGateRow("kok", "silver", "gecti", "s1", ["a@1"], new string('a', 64), DateTime.UnixEpoch),
            new XrefGateRow("benzer_ayet", "altin", "kaldi", "s2", ["b@1"], new string('b', 64), DateTime.UnixEpoch),
        ]));

        Assert.Equal(
            [(XrefType.Kok, "silver", "gecti"), (XrefType.BenzerAyet, "altin", "kaldi")],
            input.Gates.Select(g => (g.Type, g.SetClass, g.Result)));
        Assert.Empty(Build(Snapshot()).Gates);
        Assert.Throws<InvalidDataException>(() => Build(Snapshot(gates: [new XrefGateRow("bilinmeyen", "silver", "gecti", "s", [], new string('a', 64), DateTime.UnixEpoch)])));
    }

    [Fact]
    public void Turkish_lemma_root_index_and_form_rows_become_lexicals_that_follow_the_linked_lemma()
    {
        EditorialSnapshot snapshot = Snapshot(
            lemmas: [Lemma(1, "onayli", "otomatik", true), Lemma(2, "aday", null, false)],
            index:
            [
                new TrRootIndexRow("meal:elmalili:1:1", 3, 8, 1, 1, false, "0123456789abcdef", "dv"),
                new TrRootIndexRow("meal:elmalili:1:1", 9, 12, 1, 2, false, "0123456789abcdef", "dv"),
            ],
            forms: [new TrFormRow("deneme", "deneme", 1, 2, "dv"), new TrFormRow("baska", "baska", 2, 1, "dv")]);

        GateInput input = Build(snapshot);

        GateLexical lemma = Assert.Single(input.Lexicals, l => l.Kind == LexicalKind.TrLemma && l.Id == "1");
        Assert.Equal((XrefStatus.Onayli, "otomatik", true, 1), (lemma.Status, lemma.OnayYolu, lemma.HasKanit, lemma.LemmaId));
        GateLexical candidate = Assert.Single(input.Lexicals, l => l.Kind == LexicalKind.TrLemma && l.Id == "2");
        Assert.Equal((XrefStatus.Aday, (string?)null, false), (candidate.Status, candidate.OnayYolu, candidate.HasKanit));

        GateLexical index1 = Assert.Single(input.Lexicals, l => l.Kind == LexicalKind.TrRootIndex && l.Id == "meal:elmalili:1:1|3");
        Assert.Equal((true, 1, "meal:elmalili:1:1", "0123456789abcdef"), (index1.LinkedLemmaApproved, index1.LemmaId, index1.UnitAnchor, index1.UnitHash));
        Assert.False(Assert.Single(input.Lexicals, l => l.Kind == LexicalKind.TrRootIndex && l.Id == "meal:elmalili:1:1|9").LinkedLemmaApproved);
        Assert.True(Assert.Single(input.Lexicals, l => l.Kind == LexicalKind.TrForm && l.Id == "deneme|1").LinkedLemmaApproved);
        Assert.False(Assert.Single(input.Lexicals, l => l.Kind == LexicalKind.TrForm && l.Id == "baska|2").LinkedLemmaApproved);
    }

    [Fact]
    public void Turkish_lemma_data_alone_makes_kelime_kok_a_pack_with_content()
    {
        EditorialSnapshot basis = Snapshot(lemmas: [Lemma(1, "onayli", "editor", false)]);
        EditorialSnapshot withQac = new()
        {
            Sources = [.. basis.Sources, PackTestData.Source(PackCatalog.QacMorphologySlug, "morfoloji")],
            Units = basis.Units,
            TrLemmas = basis.TrLemmas,
        };

        Assert.False(Build(Snapshot()).Packs.Single(p => p.PackId == "kelime-kok").HasContent);
        Assert.True(Build(withQac).Packs.Single(p => p.PackId == "kelime-kok").HasContent);
    }
}
