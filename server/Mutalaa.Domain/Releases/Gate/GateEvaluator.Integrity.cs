namespace Mutalaa.Domain.Releases.Gate;

/// <summary>
/// Butunluk kurallari (P-11, P-13, P-14) saf kisimlari. Dosya okuma, ham hash hesabi ve depo erisimi Infrastructure'dadir;
/// buraya hazir hesaplanmis kayitlar gelir. Her islev ihlal listesi dondurur (bos = gecti); sira Ordinal ve belirlenimcidir.
/// </summary>
public static partial class GateEvaluator
{
    /// <summary>
    /// P-11: ham dosyadan yeniden hesaplanan content_hash (rawHashes: capa -> hash) ile birimlerin content_hash degerleri
    /// (unitHashes: capa -> hash) ayni kumede ve ayni degerde olmali.
    /// </summary>
    public static IReadOnlyList<GateViolation> VerifyP11ContentHashes(
        IReadOnlyDictionary<string, string> rawHashes,
        IReadOnlyDictionary<string, string> unitHashes)
    {
        ArgumentNullException.ThrowIfNull(rawHashes);
        ArgumentNullException.ThrowIfNull(unitHashes);

        List<GateViolation> violations = [];
        foreach (string anchor in rawHashes.Keys.Order(StringComparer.Ordinal))
        {
            if (!unitHashes.TryGetValue(anchor, out string? unitHash))
            {
                violations.Add(new GateViolation(GateRule.P11, anchor, "birim-yok"));
            }
            else if (!string.Equals(unitHash, rawHashes[anchor], StringComparison.Ordinal))
            {
                violations.Add(new GateViolation(GateRule.P11, anchor, "hash-uyusmuyor"));
            }
        }

        foreach (string anchor in unitHashes.Keys.Order(StringComparer.Ordinal))
        {
            if (!rawHashes.ContainsKey(anchor))
            {
                violations.Add(new GateViolation(GateRule.P11, anchor, "ham-dosyada-yok"));
            }
        }

        return violations;
    }

    /// <summary>P-11: pakete yazilan attribution (atif_metni, atif_url) kaynak satiriyla aynen (Ordinal; null yalniz null ile) ayni olmali.</summary>
    public static IReadOnlyList<GateViolation> VerifyP11Attribution(
        string sourceSlug,
        string? sourceAtifMetni,
        string? sourceAtifUrl,
        string? packAtifMetni,
        string? packAtifUrl)
    {
        ArgumentNullException.ThrowIfNull(sourceSlug);

        List<GateViolation> violations = [];
        if (!string.Equals(sourceAtifMetni, packAtifMetni, StringComparison.Ordinal))
        {
            violations.Add(new GateViolation(GateRule.P11, sourceSlug, "atif-metni-uyusmuyor"));
        }

        if (!string.Equals(sourceAtifUrl, packAtifUrl, StringComparison.Ordinal))
        {
            violations.Add(new GateViolation(GateRule.P11, sourceSlug, "atif-url-uyusmuyor"));
        }

        return violations;
    }

    /// <summary>
    /// P-11: kaynagin kendi bildirimi (source.notice_text) ham dosyadaki bildirim blogu ile bayt bayt ayni olmali
    /// (gecerli Unicode metinde Ordinal dizgi esitligi bayt esitligidir).
    /// </summary>
    public static IReadOnlyList<GateViolation> VerifyP11Notice(string sourceSlug, string? sourceNotice, string? rawNotice)
    {
        ArgumentNullException.ThrowIfNull(sourceSlug);

        return string.Equals(sourceNotice, rawNotice, StringComparison.Ordinal)
            ? []
            : [new GateViolation(GateRule.P11, sourceSlug, "bildirim-uyusmuyor")];
    }

    /// <summary>
    /// P-13: giren paketlerde depends_on kendine bagimlilik, manifestte olmayan bagimlilik ve dongu icermemeli.
    /// manifestPackIds = giren paketler + onceki surumden tasinanlar. Bagimliligi bilinmeyen (tasinan) paketlerin kenarlari dongu aramasina girmez.
    /// </summary>
    public static IReadOnlyList<GateViolation> EvaluateP13(IReadOnlyCollection<GatePack> enteredPacks, IReadOnlyCollection<string> manifestPackIds)
    {
        ArgumentNullException.ThrowIfNull(enteredPacks);
        ArgumentNullException.ThrowIfNull(manifestPackIds);

        HashSet<string> manifest = new(manifestPackIds, StringComparer.Ordinal);
        Dictionary<string, string[]> edges = new(StringComparer.Ordinal);
        List<GateViolation> violations = [];

        foreach (GatePack pack in enteredPacks.OrderBy(p => p.PackId, StringComparer.Ordinal))
        {
            string[] deps = [.. pack.DependsOn.Distinct(StringComparer.Ordinal).Order(StringComparer.Ordinal)];
            if (!edges.TryAdd(pack.PackId, deps))
            {
                throw new ArgumentException($"Yinelenen paket kimligi: {pack.PackId}", nameof(enteredPacks));
            }

            foreach (string dep in deps)
            {
                if (string.Equals(dep, pack.PackId, StringComparison.Ordinal))
                {
                    violations.Add(new GateViolation(GateRule.P13, pack.PackId, "kendine-bagimlilik"));
                }
                else if (!manifest.Contains(dep))
                {
                    violations.Add(new GateViolation(GateRule.P13, pack.PackId, "bagimlilik-manifestte-yok:" + dep));
                }
            }
        }

        // Dongu: 0 = ziyaret edilmedi, 1 = yigitta, 2 = bitti.
        Dictionary<string, int> state = new(StringComparer.Ordinal);
        List<string> path = [];

        void Visit(string id)
        {
            state[id] = 1;
            path.Add(id);
            foreach (string dep in edges[id])
            {
                if (string.Equals(dep, id, StringComparison.Ordinal) || !edges.ContainsKey(dep))
                {
                    continue;
                }

                int depState = state.GetValueOrDefault(dep);
                if (depState == 1)
                {
                    int start = path.IndexOf(dep);
                    string cycle = string.Join(">", path.Skip(start).Append(dep));
                    violations.Add(new GateViolation(GateRule.P13, id, "dongu:" + cycle));
                }
                else if (depState == 0)
                {
                    Visit(dep);
                }
            }

            path.RemoveAt(path.Count - 1);
            state[id] = 2;
        }

        foreach (string id in edges.Keys.Order(StringComparer.Ordinal))
        {
            if (state.GetValueOrDefault(id) == 0)
            {
                Visit(id);
            }
        }

        return violations;
    }

    /// <summary>
    /// P-14: terfide public'e giren her kaynagin icerik ozeti, ic kanalda test edilen yayinin ozetiyle ayni olmali.
    /// Sozlukler kaynak slug'i -> kaynak ozeti (ContentDigest). Yalniz ic kanalda olup public'e girmeyen kaynak ihlal degildir.
    /// </summary>
    public static IReadOnlyList<GateViolation> EvaluateP14(
        IReadOnlyDictionary<string, string> internalSourceDigests,
        IReadOnlyDictionary<string, string> publicSourceDigests)
    {
        ArgumentNullException.ThrowIfNull(internalSourceDigests);
        ArgumentNullException.ThrowIfNull(publicSourceDigests);

        List<GateViolation> violations = [];
        foreach (string slug in publicSourceDigests.Keys.Order(StringComparer.Ordinal))
        {
            if (!internalSourceDigests.TryGetValue(slug, out string? internalDigest))
            {
                violations.Add(new GateViolation(GateRule.P14, slug, "ic-kanalda-yok"));
            }
            else if (!string.Equals(internalDigest, publicSourceDigests[slug], StringComparison.Ordinal))
            {
                violations.Add(new GateViolation(GateRule.P14, slug, "ozet-uyusmuyor"));
            }
        }

        return violations;
    }
}
