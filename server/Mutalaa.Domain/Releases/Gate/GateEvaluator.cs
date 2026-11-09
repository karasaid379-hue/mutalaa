using Mutalaa.Domain.Content;
using Mutalaa.Domain.Links;

namespace Mutalaa.Domain.Releases.Gate;

/// <summary>
/// Kalite kapisi (Yayin sureci 4; Backend API 10.3). Saf ve belirlenimcidir: girdi ayni ise sonuc ve rapor baytlari aynidir.
/// Suzme kurallari (P-07, P-08, P-09, P-10, P-12) icerigi pakete almaz ve rapora "girmedi" yazar, durdurmaz.
/// Butunluk kurallari (P-01, P-11, P-13, P-14) ihlal uretir ve yayini reddeder (GateReport.Rejected).
/// Degerlendirme sirasi: kaynak (P-12, sonra P-01) -> birim (kaynak, kullanim disi, P-08, P-10) -> paket -> P-13 -> baglanti (P-07)
/// -> sozluk (P-09) -> capa sureklilik. P-11 ve P-14 dosya/kanal verisi gerektirdiginden ayri islevlerdir (GateEvaluator.Integrity).
/// </summary>
public static partial class GateEvaluator
{
    private readonly record struct SourceVerdict(GateDecision Decision, GateRule? Rule, string Reason);

    private readonly record struct RowKey(GateSubjectKind Kind, string Id, GateDecision Decision, GateRule? Rule, string Reason);

    /// <summary>
    /// Girdiyi derleme turune gore degerlendirir. Tanimsiz derleme turu public sayilir (FlavorPolicy.Normalize).
    /// Yinelenen kaynak slug'i, paket kimligi ya da baglanti kimligi ArgumentException atar (girdi hatasi).
    /// </summary>
    public static GateResult Evaluate(BuildFlavor flavor, GateInput input)
    {
        ArgumentNullException.ThrowIfNull(input);
        BuildFlavor f = FlavorPolicy.Normalize(flavor);

        Dictionary<string, SourceVerdict> sources = new(StringComparer.Ordinal);
        foreach (GateSource source in input.Sources)
        {
            if (!sources.TryAdd(source.Slug, DecideSource(f, source)))
            {
                throw new ArgumentException($"Yinelenen kaynak slug'i: {source.Slug}", nameof(input));
            }
        }

        Dictionary<RowKey, int> groups = [];
        List<GateReportRow> rows = [];
        List<GateViolation> violations = [];

        // Birimler (kaynak kurali -> kullanim disi -> P-08 -> P-10).
        HashSet<string> includedUnits = new(StringComparer.Ordinal);
        Dictionary<string, int> unitsBySource = new(StringComparer.Ordinal);
        Dictionary<string, int> includedBySource = new(StringComparer.Ordinal);
        foreach (GateUnit unit in input.Units)
        {
            SourceVerdict sv = EnsureSource(f, sources, unit.SourceSlug);
            (GateDecision decision, GateRule? rule, string reason) = DecideUnit(f, unit, sv);
            Count(groups, GateSubjectKind.Birim, unit.SourceSlug, decision, rule, reason);
            unitsBySource[unit.SourceSlug] = unitsBySource.GetValueOrDefault(unit.SourceSlug) + 1;
            if (decision == GateDecision.Girdi)
            {
                includedUnits.Add(unit.Anchor);
                includedBySource[unit.SourceSlug] = includedBySource.GetValueOrDefault(unit.SourceSlug) + 1;
            }
        }

        // Paketler.
        HashSet<string> seenPacks = new(StringComparer.Ordinal);
        List<GatePack> enteredPacks = [];
        foreach (GatePack pack in input.Packs.OrderBy(p => p.PackId, StringComparer.Ordinal))
        {
            if (!seenPacks.Add(pack.PackId))
            {
                throw new ArgumentException($"Yinelenen paket kimligi: {pack.PackId}", nameof(input));
            }

            (GateDecision decision, GateRule? rule, string reason) = DecidePack(f, pack, sources, unitsBySource, includedBySource, violations);
            rows.Add(new GateReportRow(GateSubjectKind.Paket, pack.PackId, decision, rule, reason));
            if (decision == GateDecision.Girdi)
            {
                enteredPacks.Add(pack);
            }
        }

        // Kaynaklar (paket ve birimlerin gerektirdigi kayitsiz kaynaklar dahil).
        HashSet<string> includedSources = new(StringComparer.Ordinal);
        foreach (string slug in sources.Keys.Order(StringComparer.Ordinal))
        {
            SourceVerdict sv = sources[slug];
            rows.Add(new GateReportRow(GateSubjectKind.Kaynak, slug, sv.Decision, sv.Rule, sv.Reason));
            if (sv.Decision == GateDecision.Girdi)
            {
                includedSources.Add(slug);
            }
            else if (sv.Rule == GateRule.P01)
            {
                violations.Add(new GateViolation(GateRule.P01, slug, sv.Reason));
            }
        }

        // P-13: manifest = kapidan giren paketler + onceki surumden tasinanlar.
        HashSet<string> manifest = new(enteredPacks.Select(p => p.PackId), StringComparer.Ordinal);
        manifest.UnionWith(input.CarriedPackIds);
        violations.AddRange(EvaluateP13(enteredPacks, manifest));

        // Baglantilar (P-07).
        Dictionary<Guid, XrefVerdict> verdicts = [];
        foreach (GateXref xref in input.Xrefs)
        {
            XrefVerdict verdict = EvaluateXref(
                f,
                xref,
                IsVisible(sources, xref.SrcSourceSlug),
                IsVisible(sources, xref.DstSourceSlug));
            if (!verdicts.TryAdd(xref.Id, verdict))
            {
                throw new ArgumentException($"Yinelenen baglanti kimligi: {xref.Id}", nameof(input));
            }

            string typeLabel = Enum.IsDefined(xref.Type) ? xref.Type.ToLabel() : "bilinmeyen";
            if (verdict.Included)
            {
                Count(groups, GateSubjectKind.Baglanti, typeLabel, GateDecision.Girdi, null, verdict.Approved ? GateReasons.Uygun : GateReasons.Aday);
            }
            else
            {
                Count(groups, GateSubjectKind.Baglanti, typeLabel, GateDecision.Girmedi, verdict.Rule, verdict.Reason);
            }
        }

        // Sozluk ve duzeltmeler (P-09).
        HashSet<string> includedLexicals = new(StringComparer.Ordinal);
        foreach (GateLexical lexical in input.Lexicals)
        {
            string label = lexical.Kind.ToLabel();
            (bool ok, string reason) = DecideLexical(lexical);
            if (ok)
            {
                includedLexicals.Add(label + ":" + lexical.Id);
                Count(groups, GateSubjectKind.Sozluk, label, GateDecision.Girdi, null, GateReasons.Uygun);
            }
            else
            {
                Count(groups, GateSubjectKind.Sozluk, label, GateDecision.Girmedi, GateRule.P09, reason);
            }
        }

        violations.AddRange(CheckAnchorContinuity(input));

        foreach ((RowKey key, int count) in groups)
        {
            rows.Add(new GateReportRow(key.Kind, key.Id, key.Decision, key.Rule, key.Reason, count));
        }

        GateReport report = GateReport.Create(f, rows, violations);
        return new GateResult(
            report,
            new HashSet<string>(enteredPacks.Select(p => p.PackId), StringComparer.Ordinal),
            includedSources,
            includedUnits,
            includedLexicals,
            verdicts);
    }

    /// <summary>
    /// P-07: tek baglanti. srcVisible ve dstVisible uclarin eserinin bu derlemede gorunurlugudur (kaynak karari "girdi").
    /// Hedef ayri kayitli dizinse (DstIsSeparateIndex) dstVisible aranmaz.
    /// </summary>
    public static XrefVerdict EvaluateXref(BuildFlavor flavor, GateXref xref, bool srcVisible, bool dstVisible)
    {
        ArgumentNullException.ThrowIfNull(xref);
        BuildFlavor f = FlavorPolicy.Normalize(flavor);
        bool isPublic = f == BuildFlavor.Public;

        bool approved = xref.Status == XrefStatus.Onayli;
        bool folded = xref.Type == XrefType.Anlamsal ||
            (XrefTypeClass.IsAutomatic(xref.Type) && !approved && !(xref.Confidence >= XrefTypeClass.FoldBelow));

        XrefVerdict Out(string reason) => new(false, approved, folded, GateRule.P07, reason);

        switch (xref.Status)
        {
            case XrefStatus.Red:
                return Out(GateReasons.Red);
            case XrefStatus.Onayli:
            case XrefStatus.Aday:
                break;
            default:
                return Out(GateReasons.DurumBilinmiyor);
        }

        if (!srcVisible)
        {
            return Out(GateReasons.KaynakEserGorunmez);
        }

        if (!xref.DstIsSeparateIndex && !dstVisible)
        {
            return Out(GateReasons.HedefEserGorunmez);
        }

        if (xref.Type == XrefType.Anlamsal && isPublic)
        {
            return Out(GateReasons.AnlamsalPublic);
        }

        if (XrefTypeClass.RequiresHumanApproval(xref.Type))
        {
            if (!approved && isPublic)
            {
                return Out(GateReasons.AdayPublic);
            }
        }
        else if (XrefTypeClass.IsAutomatic(xref.Type))
        {
            // NaN karsilastirmasi false verir: guveni olmayan aday girmez.
            if (!approved && !(xref.Confidence >= XrefTypeClass.ConfidenceMin))
            {
                return Out(GateReasons.DusukGuven);
            }
        }
        else
        {
            return Out(GateReasons.TurBilinmiyor);
        }

        if (isPublic)
        {
            if (xref.HasOpenReview)
            {
                return Out(GateReasons.AcikInceleme);
            }

            if (XrefTypeClass.RequiresLexiconApproval(xref.Type) && !xref.LexiconApproved)
            {
                return Out(GateReasons.SozlukOnaysiz);
            }
        }

        return new XrefVerdict(true, approved, folded, null, approved ? GateReasons.Uygun : GateReasons.Aday);
    }

    private static SourceVerdict DecideSource(BuildFlavor flavor, GateSource source)
    {
        // P-12 once: pakete hic girmeyecek kaynagin kaydi eksik diye yayin reddedilmez.
        if (!FlavorPolicy.AllowsSource(flavor, source.Slug))
        {
            return new SourceVerdict(GateDecision.Girmedi, GateRule.P12, GateReasons.TestKaynagi);
        }

        if (!source.Registered)
        {
            return new SourceVerdict(GateDecision.Girmedi, GateRule.P01, GateReasons.KaynakKaydiYok);
        }

        if (string.IsNullOrWhiteSpace(source.AtifMetni))
        {
            return new SourceVerdict(GateDecision.Girmedi, GateRule.P01, GateReasons.AtifMetniBos);
        }

        return new SourceVerdict(GateDecision.Girdi, null, GateReasons.Uygun);
    }

    private static SourceVerdict EnsureSource(BuildFlavor flavor, Dictionary<string, SourceVerdict> sources, string slug)
    {
        if (!sources.TryGetValue(slug, out SourceVerdict verdict))
        {
            // Girdide kaydi olmayan kaynak: kayitsiz sayilir.
            verdict = DecideSource(flavor, new GateSource(slug, null, false));
            sources[slug] = verdict;
        }

        return verdict;
    }

    private static bool IsVisible(Dictionary<string, SourceVerdict> sources, string slug) =>
        sources.TryGetValue(slug, out SourceVerdict verdict) && verdict.Decision == GateDecision.Girdi;

    private static (GateDecision Decision, GateRule? Rule, string Reason) DecideUnit(BuildFlavor flavor, GateUnit unit, SourceVerdict source)
    {
        if (source.Decision == GateDecision.Girmedi)
        {
            return (GateDecision.Girmedi, source.Rule, source.Reason);
        }

        if (unit.Status != UnitStatus.Etkin)
        {
            return (GateDecision.Girmedi, null, GateReasons.KullanimDisi);
        }

        bool approved = unit.TextStatus == TextStatus.Onayli;
        if (!approved && !FlavorPolicy.AllowsUnapprovedUnits(flavor))
        {
            // P-08, P-10'dan once: yapay zeka taslagi kendi koduyla girmez.
            return unit.IsAiDraft
                ? (GateDecision.Girmedi, GateRule.P08, GateReasons.YapayZekaTaslagi)
                : (GateDecision.Girmedi, GateRule.P10, GateReasons.OnaysizBirim);
        }

        return (GateDecision.Girdi, null, approved ? GateReasons.Uygun : GateReasons.Dogrulanmamis);
    }

    private static (GateDecision Decision, GateRule? Rule, string Reason) DecidePack(
        BuildFlavor flavor,
        GatePack pack,
        Dictionary<string, SourceVerdict> sources,
        Dictionary<string, int> unitsBySource,
        Dictionary<string, int> includedBySource,
        List<GateViolation> violations)
    {
        if (!pack.HasContent)
        {
            return (GateDecision.Girmedi, null, GateReasons.IcerikYok);
        }

        string[] slugs = [.. pack.SourceSlugs.Distinct(StringComparer.Ordinal).Order(StringComparer.Ordinal)];
        if (slugs.Length == 0)
        {
            violations.Add(new GateViolation(GateRule.P01, pack.PackId, GateReasons.KaynakKaydiYok));
            return (GateDecision.Girmedi, GateRule.P01, GateReasons.KaynakKaydiYok);
        }

        bool anyEntered = false;
        bool anyUnits = false;
        bool anyIncluded = false;
        (GateRule? Rule, string Slug)? firstExcluded = null;
        foreach (string slug in slugs)
        {
            SourceVerdict sv = EnsureSource(flavor, sources, slug);
            if (sv.Decision == GateDecision.Girdi)
            {
                anyEntered = true;
                anyUnits |= unitsBySource.GetValueOrDefault(slug) > 0;
                anyIncluded |= includedBySource.GetValueOrDefault(slug) > 0;
            }
            else
            {
                firstExcluded ??= (sv.Rule, slug);
            }
        }

        // Suzme kaynak duzeyindedir: paket, en az bir kaynagi girdiyse (o kaynaklarin icerigiyle) girer. Ama kaynagi girip birimlerinin hepsi bu derlemede
        // suzulduyse (ornegin public'te butun birimler taslak: P-08/P-10) icerigi kalmamistir: "girmedi · icerik-yok", kural kodu yok, kapi reddetmez.
        // Yapi satiri tasiyan paket (core) suzmeden etkilenmez. Girilen kaynaklarin girdide hic birimi yoksa birim kaniti yoktur (sentetik girdi, yapi ya da
        // ses kaynagi); o zaman paketin HasContent bilgisi (GateInputBuilder: birim ya da yapi satiri) gecerli kalir.
        if (anyEntered)
        {
            return pack.HasStructure || anyIncluded || !anyUnits
                ? (GateDecision.Girdi, null, GateReasons.Uygun)
                : (GateDecision.Girmedi, null, GateReasons.IcerikYok);
        }

        return (GateDecision.Girmedi, firstExcluded!.Value.Rule, GateReasons.KaynakGirmedi + firstExcluded.Value.Slug);
    }

    private static (bool Included, string Reason) DecideLexical(GateLexical lexical)
    {
        switch (lexical.Kind)
        {
            case LexicalKind.QuranWordFix:
            case LexicalKind.LemmaGloss:
                return lexical.Status == XrefStatus.Onayli ? (true, GateReasons.Uygun) : (false, GateReasons.OnaysizSatir);
            case LexicalKind.TrRootIndex:
            case LexicalKind.TrForm:
                return lexical.LinkedLemmaApproved ? (true, GateReasons.Uygun) : (false, GateReasons.LemmaOnaysiz);
            default:
                return (false, GateReasons.OnaysizSatir);
        }
    }

    private static List<GateViolation> CheckAnchorContinuity(GateInput input)
    {
        List<GateViolation> violations = [];
        if (input.PreviousAnchors.Count == 0)
        {
            return violations;
        }

        Dictionary<string, GateUnit> byAnchor = new(StringComparer.Ordinal);
        foreach (GateUnit unit in input.Units)
        {
            byAnchor.TryAdd(unit.Anchor, unit);
        }

        foreach (string anchor in input.PreviousAnchors.Distinct(StringComparer.Ordinal).Order(StringComparer.Ordinal))
        {
            if (!byAnchor.TryGetValue(anchor, out GateUnit? unit))
            {
                violations.Add(new GateViolation(null, anchor, GateReasons.CapaKayip));
            }
            else if (unit.Status != UnitStatus.Etkin && !unit.HasSuccessors)
            {
                violations.Add(new GateViolation(null, anchor, GateReasons.CapaYonlendirmesiz));
            }
        }

        return violations;
    }

    private static void Count(Dictionary<RowKey, int> groups, GateSubjectKind kind, string id, GateDecision decision, GateRule? rule, string reason)
    {
        RowKey key = new(kind, id, decision, rule, reason);
        groups[key] = groups.GetValueOrDefault(key) + 1;
    }
}
