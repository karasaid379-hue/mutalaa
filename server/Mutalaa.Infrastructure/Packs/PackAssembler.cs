using System.Globalization;
using Mutalaa.Domain.Anchors;
using Mutalaa.Domain.Releases;
using Mutalaa.Domain.Releases.Gate;
using Mutalaa.Domain.Reviews;
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
/// Risale (A20.4, K-51): risale-{kitap} (PackDefinition.Book) yalniz kendi capa onekli birimlerini unit olarak alir (etiket RisaleLabels; arama satiri, baglanti
/// ve sayfa eslemesi yoktur) ve dil ile yonu pack_meta'ya tasir. risale-dizin (IndexesBooks) unit yerine, kapidan giren her kitap paketinin birimleri icin
/// unit_ref ve icerigi olmayan arama satirlari yazar (Osmanli ve Arapca kitaplarda yalniz ar_norm), bir ucu Risale olan baglantilari alir ve baski sayfa
/// satirlarini yalniz iki ucu da kapsamdaki birimler icin yazar (K-47 ile ayni sarkan uc kurali; volume kitabin cildiyle ayni olmalidir). risale-dizin ayrica lugat
/// tablosunu tasir (A20.6, K-51 madde 9 ve 10): Glossary kaynaklarinin kapidan giren (IncludedLexicals "lugat_madde:{source_id}:{anlam_no}:{basliksoz}") maddeleri (K-51 madde 14: ayni basliksoz farkli kaynaktan ve/veya farkli anlam_no ile gelebilir;
/// tanimsiz aday, ayni normalize basliksozde tanimli madde varsa pakete yazilmaz); onayli her
/// derlemeye, aday yalniz dev ve internal'a (status 'aday'), red hicbirine girmez; test- onekli kaynak public'e girmez (kaynak karari, P-12). kaynaklar (siklik, kitaplar,
/// sozluk isabeti) ve anlam basvurusu pakete yazilmaz.
/// </summary>
public static class PackAssembler
{
    private const string ApprovedLabel = "onayli";
    private const string ArabicLang = "ar";
    private const string RisaleTurkish = "tr";

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
        HashSet<string> glossarySlugs = new(StringComparer.Ordinal);
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
                if (binding.AlsoGlossary)
                {
                    glossarySlugs.Add(binding.Slug);
                }

                if (binding.PageMapLayout is { } contentLayout)
                {
                    // Icerik kaynagi kendi sayfa eslemesini de tasir (risale-dizin'de fikstur kaynagi).
                    layouts[binding.Slug] = contentLayout;
                }
            }
            else if (binding.Role == PackSourceRole.Dictionary)
            {
                dictionarySlugs.Add(binding.Slug);
            }
            else if (binding.Role == PackSourceRole.Glossary)
            {
                glossarySlugs.Add(binding.Slug);
            }
            else if (binding.Role == PackSourceRole.Structure)
            {
                layouts[binding.Slug] = binding.PageMapLayout
                    ?? throw new PackAssemblyException($"Yapi kaynaginin page_map duzeni yok: {binding.Slug}");
            }
        }

        RisaleBook? book = pack.Book;
        List<PackUnitRow> units = [];
        List<PackUnitSearchRow> search = [];
        List<PackUnitRefRow> unitRefs = [];
        HashSet<string> sourcesWithRows = new(StringComparer.Ordinal);
        foreach (UnitRow unit in snapshot.Units)
        {
            if (!contentSlugs.Contains(unit.SourceId) || !gate.IncludedUnits.Contains(unit.Anchor))
            {
                continue;
            }

            if (pack.IndexesBooks)
            {
                // Dizin: birim kitap paketine aittir ve o paket kapidan girmistir; kaynak o kitabin icerik kaynagi olmalidir (rn:test-ornek yalniz fikstur kaynagindan).
                if (!catalog.TryGetByAnchorPrefix(GatePack.PrefixOf(unit.Anchor), out PackDefinition? bookPack)
                    || bookPack.Book is not { } indexed
                    || !gate.IncludedPacks.Contains(bookPack.PackId)
                    || !bookPack.ContentSources.Any(b => string.Equals(b.Slug, unit.SourceId, StringComparison.Ordinal)))
                {
                    continue;
                }

                unitRefs.Add(new PackUnitRefRow(unit.Anchor, bookPack.PackId, unit.Ord, RisaleLabels.Build(indexed, unit)));
                search.Add(IndexSearchRow(indexed, unit));
                sourcesWithRows.Add(unit.SourceId);
                continue;
            }

            if (pack.AnchorPrefix is { } prefix && !string.Equals(GatePack.PrefixOf(unit.Anchor), prefix, StringComparison.Ordinal))
            {
                continue;
            }

            units.Add(ToPackUnit(unit, book));
            if (book is null)
            {
                // Kitap paketi arama tablosu tasimaz; arama risale-dizin'dedir (K-44 madde 3).
                search.Add(new PackUnitSearchRow(unit.Anchor, unit.TrWide, unit.TrStem, unit.ArNorm));
            }

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

        if (pack.IndexesBooks)
        {
            AddBookPages(pack, snapshot, gate, catalog, layouts, pages, sourcesWithRows);
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

        List<PackLugatRow> lugat = pack.IndexesBooks ? AssembleLugat(snapshot, gate, glossarySlugs, sourcesWithRows) : [];

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

        if (pack.IndexesBooks && xrefs.Count > 0)
        {
            // Risale baglantilari ayri dizin kaynaginin kaydiyla listelenir (P-01, P-11; Icerik paketleri 7).
            sourcesWithRows.Add(PackCatalog.RisaleLinkSlug);
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
            UnitRefs = unitRefs,
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
            Lugat = lugat,
            WordFixCount = pack.CarriesLexicon ? lexicon.AppliedFixes : null,
            Language = book?.Language,
            Direction = book?.Direction,
        };
    }

    /// <summary>
    /// risale-dizin lugat tablosu (K-51 madde 9, 10 ve 14). Satir yalniz kaynagi kapidan girmisse (P-01, P-12) ve madde P-09'dan gecmisse (IncludedLexicals) alinir; satir sirasi
    /// PackRows'a aittir. Anahtar (basliksoz, kaynak, anlam_no): ayni basliksoz farkli kaynaktan ve/veya farkli anlam_no ile gelebilir; ayni anahtar iki kez gelirse girdi tutarsizdir.
    /// Onayli maddenin tanimi dolu olmalidir (veritabani CHECK'i); bos ise girdi tutarsizdir. Tanimsiz (tanim_tr bos) aday, ayni normalize basliksozde (basliksoz_norm)
    /// tanimli bir madde de pakete giriyorsa yazilmaz (gurultuyu onler; tanimsiz basliksoz tek basina dev ve internal'da gorunur). Kaynak lugat satiri verdiyse kunye ve
    /// atif satiri listelenir (P-01, P-11); yazilmayan satirin kaynagi bu yuzden listelenmez.
    /// </summary>
    private static List<PackLugatRow> AssembleLugat(
        EditorialSnapshot snapshot,
        GateResult gate,
        HashSet<string> glossarySlugs,
        HashSet<string> sourcesWithRows)
    {
        List<LugatMaddeRow> admitted = [];
        HashSet<(string Basliksoz, string Kaynak, int AnlamNo)> keys = [];
        foreach (LugatMaddeRow madde in snapshot.LugatMaddeler)
        {
            if (!glossarySlugs.Contains(madde.SourceId)
                || !gate.IncludedLexicals.Contains("lugat_madde:" + ReviewTargets.LugatKey(madde.SourceId, madde.AnlamNo, madde.Basliksoz)))
            {
                continue;
            }

            if (string.Equals(madde.Status, ApprovedLabel, StringComparison.Ordinal) && string.IsNullOrWhiteSpace(madde.TanimTr))
            {
                throw new PackAssemblyException($"Onayli lugat maddesinin tanimi bos ({madde.SourceId}, anlam {madde.AnlamNo.ToString(CultureInfo.InvariantCulture)}): {madde.Basliksoz}");
            }

            if (!keys.Add((madde.Basliksoz, madde.SourceId, madde.AnlamNo)))
            {
                throw new PackAssemblyException($"Lugat maddesi ayni anahtarla iki kez gelir ({madde.SourceId}, anlam {madde.AnlamNo.ToString(CultureInfo.InvariantCulture)}): {madde.Basliksoz}");
            }

            admitted.Add(madde);
        }

        HashSet<string> defined = new(
            admitted.Where(m => !string.IsNullOrWhiteSpace(m.TanimTr)).Select(m => m.BasliksozNorm),
            StringComparer.Ordinal);

        List<PackLugatRow> rows = [];
        foreach (LugatMaddeRow madde in admitted)
        {
            if (string.IsNullOrWhiteSpace(madde.TanimTr) && defined.Contains(madde.BasliksozNorm))
            {
                continue;
            }

            rows.Add(new PackLugatRow(
                madde.Basliksoz,
                madde.BasliksozNorm,
                madde.OsmanlicaYazim,
                madde.KokenDil,
                madde.TanimTr,
                madde.AnlamNo,
                madde.SourceId,
                madde.Duzey,
                madde.Status,
                madde.Origin,
                madde.Version,
                madde.ContentHash));
            sourcesWithRows.Add(madde.SourceId);
        }

        return rows;
    }

    /// <summary>
    /// Dizin arama satiri: Turkce kitapta tr_wide, tr_stem ve ar_norm; Osmanlica ve Arapca kitapta yalniz ar_norm (tr_* NULL; K-51 madde 4). Birimde bulunmayan
    /// sutun NULL kalir; sutunlar yazilirken yeniden hesaplanmaz.
    /// </summary>
    private static PackUnitSearchRow IndexSearchRow(RisaleBook book, UnitRow unit) =>
        string.Equals(book.Language, RisaleTurkish, StringComparison.Ordinal)
            ? new PackUnitSearchRow(unit.Anchor, unit.TrWide, unit.TrStem, unit.ArNorm)
            : new PackUnitSearchRow(unit.Anchor, null, null, unit.ArNorm);

    // risale-dizin page_map: Structure kaynaginin satiri, iki ucu da bu derlemenin kapsamindaki birimler (aksi halde sarkan sayfa satiri olurdu).
    private static void AddBookPages(
        PackDefinition pack,
        EditorialSnapshot snapshot,
        GateResult gate,
        PackCatalog catalog,
        Dictionary<string, string> layouts,
        List<PackPageMapRow> pages,
        HashSet<string> sourcesWithRows)
    {
        foreach (PageMapRow page in snapshot.PageMaps)
        {
            if (!layouts.TryGetValue(page.SourceId, out string? layout)
                || !gate.IncludedUnits.Contains(page.StartAnchor)
                || !gate.IncludedUnits.Contains(page.EndAnchor))
            {
                continue;
            }

            if (catalog.TryGetByAnchorPrefix(GatePack.PrefixOf(page.StartAnchor), out PackDefinition? bookPack)
                && bookPack.Book?.Volume is { } volume
                && page.Volume != volume)
            {
                throw new PackAssemblyException(
                    $"page_map cildi kitabin cildiyle uyusmuyor ({pack.PackId}): {page.StartAnchor} sayfa {page.Page.ToString(CultureInfo.InvariantCulture)}");
            }

            pages.Add(new PackPageMapRow(layout, page.Volume, page.Page, page.Line, page.StartAnchor, page.StartOffset, page.EndAnchor, page.EndOffset));
            sourcesWithRows.Add(page.SourceId);
        }
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

            // Taban features jsonb'dir (gecerli JSON); kanonikleme basarisizsa (temsil edilemeyen sayi) ham metin kalir, birlestirici cokmez.
            string? features = word.Features is null ? null : WordMorphFixes.CanonicalJsonOrRaw(word.Features);

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
                    WordMorphFixes.CanonicalJsonOrRaw(gloss.KuranAnlamlari),
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

    private static PackUnitRow ToPackUnit(UnitRow unit, RisaleBook? book) => new(
        unit.Anchor,
        unit.Kind,
        unit.Role,
        unit.ParentPath,
        unit.Ord,
        unit.AyahLo,
        unit.AyahLo is null || unit.AyahHi is null ? null : unit.AyahHi - 1,
        book is null ? LabelOf(unit.Kind, unit.Anchor) : RisaleLabels.Build(book, unit),
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
