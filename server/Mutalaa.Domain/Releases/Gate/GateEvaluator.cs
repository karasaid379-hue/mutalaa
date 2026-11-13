using Mutalaa.Domain.Anchors;
using Mutalaa.Domain.Content;
using Mutalaa.Domain.Links;

namespace Mutalaa.Domain.Releases.Gate;

/// <summary>
/// Kalite kapisi (Yayin sureci 4; Backend API 10.3). Saf ve belirlenimcidir: girdi ayni ise sonuc ve rapor baytlari aynidir.
/// Suzme kurallari (P-07, P-08, P-09, P-10, P-12) icerigi pakete almaz ve rapora "girmedi" yazar, durdurmaz.
/// Butunluk kurallari (P-01, P-11, P-13, P-14) ihlal uretir ve yayini reddeder (GateReport.Rejected).
/// Degerlendirme sirasi: kaynak (P-12, sonra P-01) -> birim (kaynak, kullanim disi, P-08, P-10) -> paket -> P-13 -> baglanti (P-07)
/// -> sozluk (P-09) -> capa sureklilik. Baglanti (P-07) ayrica uc birimlerin bu derlemenin kapsamina girmesini ister (K-47 madde 1: "uc-birim-girmedi");
/// capa sureklilik onceki yayinin her capasinin bu derlemede bulunmasini ya da acik geri cekilme kaydi (kullanim_disi + successors) tasimasini ister
/// (K-47 madde 2: "capa-kayboldu"). P-11 ve P-14 dosya/kanal verisi gerektirdiginden ayri islevlerdir (GateEvaluator.Integrity).
/// K-51 (A18.6): otomatik turlerin (kok, lemma, benzer_ayet) aday satiri public'e yalniz xref_gate'te o tur icin altin ya da silver sinifiyla gecen kapi varsa girer
/// ("kapi-olculmedi", "kapi-gecmedi"; sentetik sinif kapi acmaz; dev ve internal kapiya bakmaz); ucun birimi var ve evidence ozeti birimin content_hash on ekiyle
/// tutmuyorsa satir hicbir derlemeye girmez ("uc-ozeti-tutmadi"). P-09: Turkce lemma yalniz onayli girer; otomatik onayli lemma kanit nesnesi ister ("kanitsiz-otomatik-onay")
/// ve public'te kok kapisina baglidir; tr_root_index ve tr_form bagli lemmanin kararini izler, tr_root_index ayrica birim kapsami ve unit_hash ozeti ister
/// ("birim-girmedi", "ozet-tutmadi"). Rapora her kapi turu icin "kapi" satiri yazilir ("silver-ile-olculdu" ya da "kapi-olculmedi").
/// </summary>
public static partial class GateEvaluator
{
    private readonly record struct SourceVerdict(GateDecision Decision, GateRule? Rule, string Reason);

    private readonly record struct UnitExclusion(GateRule? Rule, string Reason);

    /// <summary>Tur kapisi olan baglanti turleri (kok, lemma, benzer_ayet); rapor ve kapi cozumu bu sirayla yapilir.</summary>
    private static readonly XrefType[] GateTypes = [XrefType.Kok, XrefType.Lemma, XrefType.BenzerAyet];

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
        Dictionary<string, UnitExclusion> excludedUnits = new(StringComparer.Ordinal);
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
            else
            {
                excludedUnits.TryAdd(unit.Anchor, new UnitExclusion(rule, reason));
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

        // Tur kapilari (xref_gate; K-51 madde 5 ve 11): her kapi turunun durumu bir kez cozulur.
        Dictionary<XrefType, XrefTypeGate> typeGates = [];
        foreach (XrefType gateType in GateTypes)
        {
            typeGates[gateType] = XrefGateRules.Resolve(input.Gates, gateType);
        }

        Dictionary<string, GateUnit> unitsByAnchor = new(StringComparer.Ordinal);
        foreach (GateUnit unit in input.Units)
        {
            unitsByAnchor.TryAdd(unit.Anchor, unit);
        }

        // Baglantilar (P-07).
        Dictionary<Guid, XrefVerdict> verdicts = [];
        HashSet<XrefType> seenGateTypes = [];
        foreach (GateXref xref in input.Xrefs)
        {
            XrefTypeGate typeGate = typeGates.GetValueOrDefault(xref.Type);
            if (XrefGateRules.HasGate(xref.Type))
            {
                seenGateTypes.Add(xref.Type);
            }

            XrefVerdict verdict = EvaluateXref(
                f,
                xref,
                IsVisible(sources, xref.SrcSourceSlug),
                IsVisible(sources, xref.DstSourceSlug),
                typeGate);
            if (verdict.Included)
            {
                verdict = CheckXrefEndUnits(xref, verdict, includedUnits, excludedUnits);
            }

            if (verdict.Included)
            {
                verdict = CheckXrefEndHashes(xref, verdict, unitsByAnchor);
            }

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
                string reason = verdict.Detail.Length == 0 ? verdict.Reason : verdict.Reason + ":" + verdict.Detail;
                Count(groups, GateSubjectKind.Baglanti, typeLabel, GateDecision.Girmedi, verdict.Rule, reason);
            }
        }

        // Sozluk ve duzeltmeler (P-09).
        HashSet<string> includedLexicals = new(StringComparer.Ordinal);

        // Turkce lemmalar once (K-51 madde 9): tr_root_index ve tr_form satirlari bagli lemmanin kararini izler.
        Dictionary<int, (bool Included, string Reason)> lemmaVerdicts = [];
        XrefTypeGate rootGate = typeGates.GetValueOrDefault(XrefType.Kok);
        bool anyAutoLemma = false;
        foreach (GateLexical lexical in input.Lexicals)
        {
            if (lexical.Kind != LexicalKind.TrLemma)
            {
                continue;
            }

            string label = lexical.Kind.ToLabel();
            (bool ok, string reason) = DecideTrLemma(f, lexical, rootGate);
            anyAutoLemma |= string.Equals(lexical.OnayYolu, GateReasons.OnayYoluOtomatik, StringComparison.Ordinal);
            if (lexical.LemmaId is { } lemmaId)
            {
                lemmaVerdicts[lemmaId] = (ok, reason);
            }

            if (ok)
            {
                includedLexicals.Add(label + ":" + lexical.Id);
                Count(groups, GateSubjectKind.Sozluk, label, GateDecision.Girdi, null, reason);
            }
            else
            {
                Count(groups, GateSubjectKind.Sozluk, label, GateDecision.Girmedi, GateRule.P09, reason);
            }
        }

        foreach (GateLexical lexical in input.Lexicals)
        {
            if (lexical.Kind == LexicalKind.TrLemma)
            {
                continue;
            }

            string label = lexical.Kind.ToLabel();
            (bool ok, string reason) = DecideLexical(f, lexical, lemmaVerdicts, includedUnits, unitsByAnchor);
            if (ok)
            {
                includedLexicals.Add(label + ":" + lexical.Id);
                Count(groups, GateSubjectKind.Sozluk, label, GateDecision.Girdi, null, reason);
                if (lexical.Kind == LexicalKind.QuranWordFix && lexical.ApplyDefect is { Length: > 0 } defect)
                {
                    violations.Add(new GateViolation(null, label + ":" + lexical.Id, GateReasons.DuzeltmeUygulanamaz + ":" + defect));
                }
            }
            else
            {
                Count(groups, GateSubjectKind.Sozluk, label, GateDecision.Girmedi, GateRule.P09, reason);
            }
        }

        // Tur kapisi satirlari: kapi turu icin baglanti (ya da, kok icin, otomatik Turkce lemma) varsa ya da olcum satiri varsa yazilir.
        foreach (XrefType gateType in GateTypes)
        {
            XrefTypeGate gate = typeGates[gateType];
            bool relevant = seenGateTypes.Contains(gateType)
                || gate.Status != XrefGateStatus.NotMeasured
                || (gateType == XrefType.Kok && anyAutoLemma);
            if (!relevant)
            {
                continue;
            }

            string typeLabel = gateType.ToLabel();
            if (gate.Opens)
            {
                rows.Add(new GateReportRow(GateSubjectKind.Kapi, typeLabel, GateDecision.Girdi, null, gate.SetClass + GateReasons.OlculduSoneki));
            }
            else
            {
                string reason = XrefGateRules.ReasonWhenClosed(gate)!;
                if (gate.SetClass is not null)
                {
                    reason += ":" + gate.SetClass;
                }

                rows.Add(new GateReportRow(GateSubjectKind.Kapi, typeLabel, GateDecision.Girmedi, GateRule.P07, reason));
            }
        }

        violations.AddRange(CheckAnchorContinuity(input, includedUnits, excludedUnits));

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
    /// gate: otomatik turun (kok, lemma, benzer_ayet) xref_gate durumu (K-51 madde 5 ve 11); varsayilan "olculmemis". public'te onaysiz (aday) otomatik
    /// satir yalniz gate.Opens iken girer; dev ve internal kapiya bakmaz.
    /// </summary>
    public static XrefVerdict EvaluateXref(BuildFlavor flavor, GateXref xref, bool srcVisible, bool dstVisible, XrefTypeGate gate = default)
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

            // K-51 madde 5 ve 11: kapidan kalan ya da olculmemis turun aday satiri public'e girmez; onayli satir her derlemeye girer.
            if (!approved && isPublic && XrefGateRules.HasGate(xref.Type) && XrefGateRules.ReasonWhenClosed(gate) is { } closed)
            {
                return Out(closed);
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

    /// <summary>
    /// P-09 (K-50 madde 8, K-46 madde 7, K-51 madde 1 ve 9). quran_word_fix her derlemede yalniz onayli ile girer. lemma_gloss: onayli her derlemeye ("uygun"), aday yalniz
    /// dev ve internal'a ("aday"; public'te "aday-public" ile girmez), red hicbirine girmez ("red"). tr_root_index ve tr_form bagli Turkce lemma
    /// pakete giriyorsa girer (lemma karari DecideTrLemma'dadir; lemma kapi ya da kanit yuzunden girmediyse satir ayni gerekceyle girmez). tr_root_index satiri
    /// ayrica birimi derlemenin kapsaminda ve unit_hash degeri birimin guncel content_hash ilk 16 haneyle tutan olmalidir ("birim-girmedi", "ozet-tutmadi").
    /// Sonuc gerekcesi rapor satirinin gerekcesidir.
    /// </summary>
    private static (bool Included, string Reason) DecideLexical(
        BuildFlavor flavor,
        GateLexical lexical,
        Dictionary<int, (bool Included, string Reason)> lemmaVerdicts,
        HashSet<string> includedUnits,
        Dictionary<string, GateUnit> unitsByAnchor)
    {
        switch (lexical.Kind)
        {
            case LexicalKind.QuranWordFix:
                return lexical.Status == XrefStatus.Onayli ? (true, GateReasons.Uygun) : (false, GateReasons.OnaysizSatir);
            case LexicalKind.LemmaGloss:
                return lexical.Status switch
                {
                    XrefStatus.Onayli => (true, GateReasons.Uygun),
                    XrefStatus.Aday when FlavorPolicy.AllowsCandidateGlosses(flavor) => (true, GateReasons.Aday),
                    XrefStatus.Aday => (false, GateReasons.AdayPublic),
                    XrefStatus.Red => (false, GateReasons.Red),
                    _ => (false, GateReasons.OnaysizSatir),
                };
            case LexicalKind.TrRootIndex:
            case LexicalKind.TrForm:
                (bool linkedOk, string linkedReason) = DecideLinkedLemma(lexical, lemmaVerdicts);
                if (!linkedOk)
                {
                    return (false, linkedReason);
                }

                if (lexical.Kind == LexicalKind.TrRootIndex && lexical.UnitAnchor is { } unitAnchor)
                {
                    if (!includedUnits.Contains(unitAnchor))
                    {
                        return (false, GateReasons.BirimGirmedi);
                    }

                    if (unitsByAnchor.TryGetValue(unitAnchor, out GateUnit? unit) && !HashMatches(lexical.UnitHash, unit.HashPrefix))
                    {
                        return (false, GateReasons.OzetTutmadi);
                    }
                }

                return (true, linkedReason);
            default:
                return (false, GateReasons.OnaysizSatir);
        }
    }

    // Bagli lemma karari: lemma satiri girdideyse onun karari (kapi ve kanit gerekceleri satira tasinir; baska neden "lemma-onaysiz"),
    // degilse yalniz LinkedLemmaApproved (geriye uyumlu).
    private static (bool Included, string Reason) DecideLinkedLemma(GateLexical lexical, Dictionary<int, (bool Included, string Reason)> lemmaVerdicts)
    {
        if (lexical.LemmaId is { } lemmaId && lemmaVerdicts.TryGetValue(lemmaId, out (bool Included, string Reason) verdict))
        {
            if (verdict.Included)
            {
                return (true, verdict.Reason);
            }

            bool propagated = string.Equals(verdict.Reason, GateReasons.KapiOlculmedi, StringComparison.Ordinal)
                || string.Equals(verdict.Reason, GateReasons.KapiGecmedi, StringComparison.Ordinal)
                || string.Equals(verdict.Reason, GateReasons.KanitsizOtomatikOnay, StringComparison.Ordinal);
            return (false, propagated ? verdict.Reason : GateReasons.LemmaOnaysiz);
        }

        return lexical.LinkedLemmaApproved ? (true, GateReasons.Uygun) : (false, GateReasons.LemmaOnaysiz);
    }

    /// <summary>
    /// P-09, Turkce lemma (K-51 madde 9 ve 11): yalniz status = onayli girer. onay_yolu = editor her derlemeye girer ("uygun"). onay_yolu = otomatik kanit
    /// nesnesi ister (yoksa "kanitsiz-otomatik-onay", her derlemede) ve public'e yalniz kok kapisi (xref_gate, tur = kok) altin ya da silver sinifiyla gectiyse
    /// girer ("kapi-olculmedi", "kapi-gecmedi"); dev ve internal kapiya bakmaz ("otomatik-onay"). Onay yolu bilinmiyorsa "onaysiz-satir".
    /// </summary>
    private static (bool Included, string Reason) DecideTrLemma(BuildFlavor flavor, GateLexical lexical, XrefTypeGate rootGate)
    {
        switch (lexical.Status)
        {
            case XrefStatus.Onayli:
                break;
            case XrefStatus.Red:
                return (false, GateReasons.Red);
            default:
                return (false, GateReasons.OnaysizSatir);
        }

        if (string.Equals(lexical.OnayYolu, GateReasons.OnayYoluEditor, StringComparison.Ordinal))
        {
            return (true, GateReasons.Uygun);
        }

        if (!string.Equals(lexical.OnayYolu, GateReasons.OnayYoluOtomatik, StringComparison.Ordinal))
        {
            return (false, GateReasons.OnaysizSatir);
        }

        if (!lexical.HasKanit)
        {
            return (false, GateReasons.KanitsizOtomatikOnay);
        }

        if (flavor == BuildFlavor.Public && XrefGateRules.ReasonWhenClosed(rootGate) is { } closed)
        {
            return (false, closed);
        }

        return (true, GateReasons.OtomatikOnay);
    }

    // Iki ozet de varsa ilk 16 hanesi (buyuk-kucuk harf gozetilmeksizin) esit olmali; biri yoksa denetlenemez ve tutar sayilir.
    private static bool HashMatches(string? recorded, string? current)
    {
        if (string.IsNullOrEmpty(recorded) || string.IsNullOrEmpty(current))
        {
            return true;
        }

        const int Length = 16;
        string a = recorded.Length > Length ? recorded[..Length] : recorded;
        string b = current.Length > Length ? current[..Length] : current;
        return string.Equals(a, b, StringComparison.OrdinalIgnoreCase);
    }

    // K-51 madde 1: ucun birimi girdide varsa ve satirin evidence ozeti birimin guncel content_hash ilk 16 haneyle tutmuyorsa satir pakete girmez
    // (P-07, "uc-ozeti-tutmadi"; tum derleme turlerinde). Birim satiri olmayan uc (konu:, ayri dizin) ve ozet alani olmayan satir etkilenmez.
    private static XrefVerdict CheckXrefEndHashes(GateXref xref, XrefVerdict verdict, Dictionary<string, GateUnit> unitsByAnchor)
    {
        bool srcBad = EndHashMismatch(xref.SrcAnchor, xref.SrcHash, unitsByAnchor);
        bool dstBad = !xref.DstIsSeparateIndex && EndHashMismatch(xref.DstAnchor, xref.DstHash, unitsByAnchor);
        return srcBad || dstBad
            ? verdict with { Included = false, Rule = GateRule.P07, Reason = GateReasons.UcOzetiTutmadi, Detail = string.Empty }
            : verdict;
    }

    private static bool EndHashMismatch(string anchor, string? recorded, Dictionary<string, GateUnit> unitsByAnchor)
    {
        if (string.IsNullOrEmpty(recorded))
        {
            return false;
        }

        if (!unitsByAnchor.TryGetValue(anchor, out GateUnit? unit))
        {
            // Kelime ve aralik soneklerini atip birim duzeyine in (K-35 madde 5, unitOf).
            if (!AnchorRef.TryParse(anchor, out AnchorRef? parsed) || !unitsByAnchor.TryGetValue(parsed.UnitOf().ToString(), out unit))
            {
                return false;
            }
        }

        return !HashMatches(recorded, unit.HashPrefix);
    }

    /// <summary>
    /// K-47 madde 1: baglanti yalniz iki ucunun birimi de derlemenin kapsamina girmisse pakete yazilir. Ucun birim satiri girdide varsa ve kapsam disindaysa
    /// (P-08, P-10, kullanim disi ya da kaynak kurali) baglanti "girmedi" olur (P-07, "uc-birim-girmedi"); neden Detail alaninda "kaynak=..." ve "hedef=..." olarak
    /// yazilir. Girdide birim satiri olmayan uclar (konu:, ayri dizin) etkilenmez; ayri kayitli dizindeki hedef de aranmaz (eser gorunurlugu kuraliyla ayni).
    /// </summary>
    private static XrefVerdict CheckXrefEndUnits(
        GateXref xref,
        XrefVerdict verdict,
        HashSet<string> includedUnits,
        Dictionary<string, UnitExclusion> excludedUnits)
    {
        UnitExclusion? src = FindEndExclusion(xref.SrcAnchor, includedUnits, excludedUnits);
        UnitExclusion? dst = xref.DstIsSeparateIndex ? null : FindEndExclusion(xref.DstAnchor, includedUnits, excludedUnits);
        if (src is null && dst is null)
        {
            return verdict;
        }

        List<string> parts = [];
        if (src is { } s)
        {
            parts.Add("kaynak=" + Describe(s));
        }

        if (dst is { } d)
        {
            parts.Add("hedef=" + Describe(d));
        }

        return verdict with
        {
            Included = false,
            Rule = GateRule.P07,
            Reason = GateReasons.UcBirimGirmedi,
            Detail = string.Join(',', parts),
        };

        static string Describe(UnitExclusion e) => e.Rule is { } rule ? rule.ToCode() + ":" + e.Reason : e.Reason;
    }

    private static UnitExclusion? FindEndExclusion(string anchor, HashSet<string> includedUnits, Dictionary<string, UnitExclusion> excludedUnits)
    {
        // Once uc capasinin kendisi aranir (birim satiri olan capa kendi birimidir; coklu baglanti kumelerinde ayristirma yapilmaz).
        if (includedUnits.Contains(anchor))
        {
            return null;
        }

        if (excludedUnits.TryGetValue(anchor, out UnitExclusion found))
        {
            return found;
        }

        // Iskada: kelime araligi (":3-7") ve kesin aralik ("@bas-bit") soneki atilir, baglanti ucu birim duzeyindedir (K-35 madde 5, unitOf).
        if (!AnchorRef.TryParse(anchor, out AnchorRef? parsed))
        {
            return null;
        }

        string unit = parsed.UnitOf().ToString();
        if (string.Equals(unit, anchor, StringComparison.Ordinal) || includedUnits.Contains(unit))
        {
            return null;
        }

        return excludedUnits.TryGetValue(unit, out found) ? found : null;
    }

    /// <summary>
    /// K-47 madde 2: onceki yayinin her capasi (a) bu derlemenin kapsamina girmis bir birim, ya da (b) acik geri cekilme kaydi tasiyan birim
    /// (status kullanim_disi ve successors dolu) olmalidir; aksi halde yayin reddedilir (kural kodu yok, gerekce "capa-kayboldu:{alt-neden}").
    /// Alt neden: "satir-yok" (girdide birim yok), "yonlendirmesiz" (kullanim_disi, successors bos), ya da kapsam disi birimin suzme gerekcesi
    /// (taslaga donmus: "onaysiz-birim", "yapay-zeka-taslagi-onaysiz"; suzulmus kaynak: "test-oneki" vb.). Onaysiz birimler dev ve internal'da kapsamdadir.
    /// </summary>
    private static List<GateViolation> CheckAnchorContinuity(
        GateInput input,
        HashSet<string> includedUnits,
        Dictionary<string, UnitExclusion> excludedUnits)
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
            if (includedUnits.Contains(anchor))
            {
                continue;
            }

            string? cause = null;
            if (!byAnchor.TryGetValue(anchor, out GateUnit? unit))
            {
                cause = GateReasons.CapaSatirYok;
            }
            else if (unit.Status != UnitStatus.Etkin)
            {
                if (!unit.HasSuccessors)
                {
                    cause = GateReasons.CapaYonlendirmesiz;
                }
            }
            else
            {
                cause = excludedUnits.TryGetValue(anchor, out UnitExclusion exclusion) ? exclusion.Reason : GateReasons.CapaKapsamDisi;
            }

            if (cause is not null)
            {
                violations.Add(new GateViolation(null, anchor, GateReasons.CapaKayboldu + ":" + cause));
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
