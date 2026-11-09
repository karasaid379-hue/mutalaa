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
/// </summary>
public static class PackAssembler
{
    private const string ApprovedLabel = "onayli";

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
        };
    }

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
