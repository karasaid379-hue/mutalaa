using System.Globalization;
using Mutalaa.Domain.Anchors;
using Mutalaa.Domain.Releases;
using Mutalaa.Domain.Releases.Gate;
using Mutalaa.Infrastructure.Releases;

namespace Mutalaa.Infrastructure.Packs;

/// <summary>
/// Bir paketin butun satirlarini kapi sonucuna gore toplar (A13.3). Pakete yalniz Domain'in sectigi birimler (GateResult.IncludedUnits),
/// kaynaklar (IncludedSources) ve baglantilar (XrefVerdict.Included) girer; metin aynen aktarilir (Tanzil bayt bayt). Kur'an ayeti etiketi
/// "{sure}:{ayet}"dir (sure adlari onaylanana kadar), digerlerinde capa metnidir. sure tablosu bos kalir: adlar onayli degildir, ad uydurulmaz.
/// Satir sirasi PackRows'a aittir (capa bayt sirasi); burada siralama yapilmaz.
/// kelime-kok (CarriesLexicon, K-50 madde 9): word_morph = quran_word'un QAC sutunlari (yalniz Dictionary rolundeki kaynaklarin morph_source'u) uzerine
/// kapidan gecen (IncludedLexicals) onayli quran_word_fix; root ve lemma yalniz Dictionary kaynaklarindan (kaynak kapidan girmis olmali: P-12) ve lemma
/// yalniz lang = 'ar' ve onayli; lemma_gloss kapidan gecenler (onayli, ve dev/internal'da aday: status satirda 'aday' kalir) ve yalniz pakete giren lemmalara
/// bagli. Uygulanamayan onayli duzeltme (WordMorphFixes) atlanir; kapi bunu zaten yayin reddi sayar. tr_form ve tr_root_index A18'e kadar bostur.
/// </summary>
public static class PackAssembler
{
    private const string ApprovedLabel = "onayli";
    private const string ArabicLang = "ar";

    /// <exception cref="PackAssemblyException">Paket kapidan girmediyse ya da girdi tutarsizsa.</exception>
    public static PackContent Assemble(
        PackDefinition pack,
        BuildFlavor flavor,
        EditorialSnapshot snapshot,
        GateResult gate,
        PackCatalog catalog)
    {
        ArgumentNullException.ThrowIfNull(pack);
        ArgumentNullException.ThrowIfNull(snapshot);
        ArgumentNullException.ThrowIfNull(gate);
        ArgumentNullException.ThrowIfNull(catalog);

        if (!gate.IncludedPacks.Contains(pack.PackId))
        {
            throw new PackAssemblyException($"Paket kapidan girmedi: {pack.PackId}");
        }

        Dictionary<string, SourceRow> sourceRows = new(StringComparer.Ordinal);
        foreach (SourceRow row in snapshot.Sources)
        {
            sourceRows[row.Slug] = row;
        }

        HashSet<string> contentSlugs = new(StringComparer.Ordinal);
        HashSet<string> dictionarySlugs = new(StringComparer.Ordinal);
        Dictionary<string, string> layouts = new(StringComparer.Ordinal);
        foreach (PackSourceBinding binding in pack.Sources)
        {
            if (!gate.IncludedSources.Contains(binding.Slug) || !sourceRows.ContainsKey(binding.Slug))
            {
                continue;
            }

            if (binding.Role == PackSourceRole.Content)
            {
                contentSlugs.Add(binding.Slug);
            }
            else if (binding.Role == PackSourceRole.Dictionary)
            {
                dictionarySlugs.Add(binding.Slug);
            }
            else if (binding.Role == PackSourceRole.Structure)
            {
                layouts[binding.Slug] = binding.PageMapLayout
                    ?? throw new PackAssemblyException($"Yapi kaynaginin page_map duzeni yok: {binding.Slug}");
            }
        }

        List<PackUnitRow> units = [];
        List<PackUnitSearchRow> search = [];
        HashSet<string> sourcesWithRows = new(StringComparer.Ordinal);
        foreach (UnitRow unit in snapshot.Units)
        {
            if (!contentSlugs.Contains(unit.SourceId) || !gate.IncludedUnits.Contains(unit.Anchor))
            {
                continue;
            }

            units.Add(ToPackUnit(unit));
            search.Add(new PackUnitSearchRow(unit.Anchor, unit.TrWide, unit.TrStem, unit.ArNorm));
            sourcesWithRows.Add(unit.SourceId);
        }

        List<PackQuranWordRow> words = [];
        List<PackQuranMarkerRow> markers = [];
        List<PackPageMapRow> pages = [];
        if (pack.CarriesQuranStructure)
        {
            foreach (QuranWordRow word in snapshot.QuranWords)
            {
                if (contentSlugs.Contains(word.SourceId) && gate.IncludedUnits.Contains(AyahAnchorOfWord(word.Anchor)))
                {
                    words.Add(new PackQuranWordRow(word.Anchor, word.AyahIndex, word.Word, word.TextUthmani, word.Norm, word.CharStart, word.CharEnd));
                    sourcesWithRows.Add(word.SourceId);
                }
            }

            foreach (QuranMarkerRow marker in snapshot.QuranMarkers)
            {
                if (layouts.ContainsKey(marker.SourceId))
                {
                    markers.Add(new PackQuranMarkerRow(marker.Kind, marker.No, marker.Anchor, marker.SecdeTuru));
                    sourcesWithRows.Add(marker.SourceId);
                }
            }

            foreach (PageMapRow page in snapshot.PageMaps)
            {
                if (layouts.TryGetValue(page.SourceId, out string? layout))
                {
                    pages.Add(new PackPageMapRow(layout, page.Volume, page.Page, page.Line, page.StartAnchor, page.StartOffset, page.EndAnchor, page.EndOffset));
                    sourcesWithRows.Add(page.SourceId);
                }
            }
        }

        Lexicon lexicon = pack.CarriesLexicon ? AssembleLexicon(snapshot, gate, dictionarySlugs) : Lexicon.Empty;
        sourcesWithRows.UnionWith(lexicon.SourcesWithRows);
        if (lexicon.GlossRows > 0)
        {
            // Hazir anlam kaynagi (atif rolu, Required: false): anlam satiri varsa kunye ve atif satiri listelenir (P-01, P-11).
            foreach (PackSourceBinding binding in pack.Sources.Where(b => b.Role == PackSourceRole.Attribution && !b.Required))
            {
                sourcesWithRows.Add(binding.Slug);
            }
        }

        List<PackXrefRow> xrefs = [];
        foreach (XrefRow xref in snapshot.Xrefs)
        {
            if (!gate.XrefVerdicts.TryGetValue(xref.Id, out XrefVerdict verdict) || !verdict.Included)
            {
                continue;
            }

            if (!string.Equals(catalog.PackIdForXref(xref.SrcAnchor, xref.DstAnchor), pack.PackId, StringComparison.Ordinal))
            {
                continue;
            }

            xrefs.Add(new PackXrefRow(
                xref.Id.ToString("D", CultureInfo.InvariantCulture),
                xref.SrcAnchor,
                xref.SrcLo,
                xref.SrcHi,
                xref.DstAnchor,
                xref.DstLo,
                xref.DstHi,
                xref.Type,
                PackRows.FromSingle(xref.Score),
                PackRows.FromSingle(xref.Confidence),
                verdict.Approved ? 1 : 0,
                verdict.Folded ? 1 : 0,
                xref.Evidence,
                xref.DataVersion));
        }

        List<PackSourceRow> packSources = [];
        List<PackAttributionRow> attributions = [];
        foreach (PackSourceBinding binding in pack.Sources)
        {
            if (!gate.IncludedSources.Contains(binding.Slug) || !sourceRows.TryGetValue(binding.Slug, out SourceRow? source))
            {
                continue;
            }

            // Zorunlu kaynak her zaman, istege bagli kaynak yalniz pakete satir verdiyse listelenir. Atif kaynaklari (simple-clean) zorunludur.
            if (!binding.Required && !sourcesWithRows.Contains(binding.Slug))
            {
                continue;
            }

            packSources.Add(new PackSourceRow(source.Slug));
            attributions.Add(new PackAttributionRow(
                source.Slug,
                source.Baslik,
                source.Surum,
                source.AtifUrl ?? source.KaynakUrl,
                source.AtifMetni,
                source.NoticeText));
        }

        return new PackContent
        {
            PackId = pack.PackId,
            Flavor = flavor,
            SchemaVersion = pack.SchemaVersion,
            PackSources = packSources,
            Attributions = attributions,
            Units = units,
            UnitSearch = search,
            Xrefs = xrefs,
            QuranWords = words,
            QuranMarkers = markers,
            PageMaps = pages,
            Sures = [],
            TrRootIndex = [],
            WordMorph = lexicon.WordMorph,
            Roots = lexicon.Roots,
            Lemmas = lexicon.Lemmas,
            LemmaGlosses = lexicon.LemmaGlosses,
            TrForms = [],
            WordFixCount = pack.CarriesLexicon ? lexicon.AppliedFixes : null,
        };
    }

    private sealed record Lexicon(
        IReadOnlyList<PackWordMorphRow> WordMorph,
        IReadOnlyList<PackRootRow> Roots,
        IReadOnlyList<PackLemmaRow> Lemmas,
        IReadOnlyList<PackLemmaGlossRow> LemmaGlosses,
        int AppliedFixes,
        ISet<string> SourcesWithRows)
    {
        public static Lexicon Empty { get; } = new([], [], [], [], 0, new HashSet<string>(StringComparer.Ordinal));

        public int GlossRows => LemmaGlosses.Count;
    }

    private static Lexicon AssembleLexicon(EditorialSnapshot snapshot, GateResult gate, HashSet<string> dictionarySlugs)
    {
        HashSet<string> withRows = new(StringComparer.Ordinal);

        List<PackRootRow> roots = [];
        HashSet<int> rootIds = [];
        foreach (RootRow root in snapshot.Roots)
        {
            if (dictionarySlugs.Contains(root.SourceId))
            {
                roots.Add(new PackRootRow(root.Id, root.Letters, root.Occurrences, root.AyahCount, root.IdfQ is { } idf ? PackRows.FromSingle(idf) : null, root.KokAnlami));
                rootIds.Add(root.Id);
                withRows.Add(root.SourceId);
            }
        }

        List<PackLemmaRow> lemmas = [];
        HashSet<int> lemmaIds = [];
        foreach (LemmaRow lemma in snapshot.Lemmas)
        {
            if (dictionarySlugs.Contains(lemma.SourceId) && string.Equals(lemma.Status, ApprovedLabel, StringComparison.Ordinal))
            {
                lemmas.Add(new PackLemmaRow(
                    lemma.Id,
                    ArabicLang,
                    lemma.Text,
                    lemma.TextClean,
                    lemma.RootId,
                    lemma.Occurrences,
                    lemma.ArLemmaId,
                    lemma.EtymologicalOnly ? 1 : 0));
                lemmaIds.Add(lemma.Id);
                withRows.Add(lemma.SourceId);
            }
        }

        // Ayeti bu derlemenin kapsamina girmeyen kelime (birim biliniyor ve girmedi) word_morph'a yazilmaz.
        HashSet<string> knownAyahs = new(snapshot.Units.Select(u => u.Anchor), StringComparer.Ordinal);
        Dictionary<string, MorphState> morph = new(StringComparer.Ordinal);
        foreach (QuranWordRow word in snapshot.QuranWords)
        {
            if (word.MorphSource is null || !dictionarySlugs.Contains(word.MorphSource))
            {
                continue;
            }

            string ayah = AyahAnchorOfWord(word.Anchor);
            if (knownAyahs.Contains(ayah) && !gate.IncludedUnits.Contains(ayah))
            {
                continue;
            }

            string? features = null;
            if (word.Features is not null)
            {
                features = WordMorphFixes.CanonicalJson(word.Features)
                    ?? throw new PackAssemblyException($"quran_word.features gecerli JSON degil: {word.Anchor}");
            }

            morph[word.Anchor] = new MorphState(word.RootId, word.LemmaId, word.Pos, features);
            withRows.Add(word.MorphSource);
        }

        int applied = 0;
        foreach (QuranWordFixRow fix in snapshot.WordFixes.OrderBy(f => f.Anchor, Utf8Order.Instance).ThenBy(f => f.Field, Utf8Order.Instance))
        {
            if (!gate.IncludedLexicals.Contains("quran_word_fix:" + fix.Id.ToString("D", CultureInfo.InvariantCulture)))
            {
                continue;
            }

            bool hasWord = morph.TryGetValue(fix.Anchor, out MorphState? state);
            string? defect = WordMorphFixes.Check(fix.Field, fix.NewValue, hasWord, rootIds.Contains, lemmaIds.Contains, out WordFixValue value);
            if (defect is not null || state is null)
            {
                continue;
            }

            morph[fix.Anchor] = fix.Field switch
            {
                WordMorphFixes.RootId => state with { RootId = value.Id },
                WordMorphFixes.LemmaId => state with { LemmaId = value.Id },
                WordMorphFixes.Pos => state with { Pos = value.Text },
                _ => state with { Features = value.Text },
            };
            applied++;
        }

        List<PackWordMorphRow> wordMorph = [.. morph.Select(p => new PackWordMorphRow(p.Key, p.Value.RootId, p.Value.LemmaId, p.Value.Pos, p.Value.Features))];

        List<PackLemmaGlossRow> glosses = [];
        foreach (LemmaGlossRow gloss in snapshot.LemmaGlosses)
        {
            if (gate.IncludedLexicals.Contains("lemma_gloss:" + gloss.LemmaId.ToString(CultureInfo.InvariantCulture)) && lemmaIds.Contains(gloss.LemmaId))
            {
                glosses.Add(new PackLemmaGlossRow(
                    gloss.LemmaId,
                    gloss.AnlamKisa,
                    gloss.KuranAnlamlari,
                    gloss.TurkceEsKelime,
                    gloss.YalnizcaEtimolojik ? 1 : 0,
                    gloss.Status,
                    gloss.Origin));
            }
        }

        return new Lexicon(wordMorph, roots, lemmas, glosses, applied, withRows);
    }

    private sealed record MorphState(int? RootId, int? LemmaId, string? Pos, string? Features);

    /// <summary>Kur'an ayeti icin "{sure}:{ayet}", digerleri icin capa metni.</summary>
    public static string LabelOf(string kind, string anchor)
    {
        if (string.Equals(kind, "ayet", StringComparison.Ordinal)
            && AnchorRef.TryParse(anchor, out AnchorRef? parsed)
            && parsed.Kind == AnchorKind.Q
            && parsed.Ilk == 0)
        {
            return string.Create(CultureInfo.InvariantCulture, $"{parsed.Sure}:{parsed.Ayet}");
        }

        return anchor;
    }

    private static PackUnitRow ToPackUnit(UnitRow unit) => new(
        unit.Anchor,
        unit.Kind,
        unit.Role,
        unit.ParentPath,
        unit.Ord,
        unit.AyahLo,
        unit.AyahLo is null || unit.AyahHi is null ? null : unit.AyahHi - 1,
        LabelOf(unit.Kind, unit.Anchor),
        unit.Metin,
        unit.Marks,
        unit.SentencesJson,
        unit.Attrs,
        unit.ContentHash,
        unit.Status,
        string.Equals(unit.MetinDurumu, ApprovedLabel, StringComparison.Ordinal) ? 1 : 0,
        unit.Successors);

    // quran_word capasi q:{sure}:{ayet}:{kelime}; ayet birimi son iki nokta ust uste isaretine kadardir.
    private static string AyahAnchorOfWord(string wordAnchor)
    {
        int cut = wordAnchor.LastIndexOf(':');
        return cut < 0 ? wordAnchor : wordAnchor[..cut];
    }
}
