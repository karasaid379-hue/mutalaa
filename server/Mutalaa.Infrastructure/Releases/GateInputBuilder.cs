using Mutalaa.Domain.Content;
using Mutalaa.Domain.Links;
using Mutalaa.Domain.Releases.Gate;
using Mutalaa.Infrastructure.Packs;

namespace Mutalaa.Infrastructure.Releases;

/// <summary>
/// Editoryal anlik goruntu + paket katalogundan Domain kapi girdisini kurar (Yayin sureci 2). Girdi derleme turunden bagimsizdir: derleme turu
/// kurallari <see cref="GateEvaluator.Evaluate"/> cagrisindadir (P-01, P-07...P-14 orada). Burada yalniz girdi eslemesi yapilir.
/// <list type="bullet">
/// <item>Kaynak kaydi = source tablosunda satir VE <c>{sourcesDir}/{slug}.toml</c> dosyasi (dosya yoksa kayitsiz sayilir; icerigi okunmaz).
/// Kapiya giren kaynaklar: butun source satirlari + icerigi olan paketlerin zorunlu kaynaklari (satiri yoksa kayitsiz, P-01).</item>
/// <item>Paket: icerigi (birim ya da yapi satiri) yoksa HasContent = false ("icerik-yok"; kaynaklari kapiya sokulmaz). Zorunlu olmayan kaynak yalniz
/// satiri varsa pakete bagli sayilir.</item>
/// <item>Birim: IsAiDraft = onaysiz birimin yz_modeli dolu review satiri var; HasSuccessors = successors dolu.</item>
/// <item>Baglanti: uclarin kaynagi uc capanin birim satirindan; bulunamayan uc kaynaksiz ("") sayilir (gorunmez). DstIsSeparateIndex: hedef birimin
/// kaynaginin turu <c>baglanti_verisi</c> (risale-atif-dizini). LexiconApproved: evidence.lexicon_status yok ya da <c>onayli</c>.</item>
/// <item>PreviousAnchors ve CarriedPackIds cagiran tarafindan verilir (onceki yayinin paket dosyalarindan ve manifestinden gelir).</item>
/// </list>
/// </summary>
public static class GateInputBuilder
{
    private const string ApprovedLabel = "onayli";
    private const string SeparateIndexKind = "baglanti_verisi";

    /// <param name="fileExists">Kaynak kaydi dosyasi denetimi; null ise <see cref="File.Exists(string?)"/>. Testler enjekte eder.</param>
    public static GateInput Build(
        EditorialSnapshot snapshot,
        PackCatalog catalog,
        string sourcesDir,
        IReadOnlyCollection<string>? carriedPackIds = null,
        IReadOnlyCollection<string>? previousAnchors = null,
        Func<string, bool>? fileExists = null)
    {
        ArgumentNullException.ThrowIfNull(snapshot);
        ArgumentNullException.ThrowIfNull(catalog);
        ArgumentException.ThrowIfNullOrWhiteSpace(sourcesDir);

        Func<string, bool> exists = fileExists ?? File.Exists;

        Dictionary<string, SourceRow> sourceRows = new(StringComparer.Ordinal);
        foreach (SourceRow row in snapshot.Sources)
        {
            sourceRows[row.Slug] = row;
        }

        // Kaynak basina birim sayisi (paketin icerigi var mi) ve kaynak slug'i -> tur.
        Dictionary<string, int> unitCounts = new(StringComparer.Ordinal);
        Dictionary<string, UnitRow> unitByAnchor = new(StringComparer.Ordinal);
        List<GateUnit> units = [];
        foreach (UnitRow unit in snapshot.Units)
        {
            unitCounts[unit.SourceId] = unitCounts.GetValueOrDefault(unit.SourceId) + 1;
            unitByAnchor.TryAdd(unit.Anchor, unit);
            units.Add(ToGateUnit(unit));
        }

        // Paketler.
        List<GatePack> packs = [];
        HashSet<string> requiredSlugs = new(StringComparer.Ordinal);
        foreach (PackDefinition pack in catalog.All)
        {
            bool hasContent = HasContent(pack, snapshot, unitCounts);
            List<string> slugs = [];
            if (hasContent)
            {
                foreach (PackSourceBinding binding in pack.Sources)
                {
                    if (binding.Required || sourceRows.ContainsKey(binding.Slug) || unitCounts.ContainsKey(binding.Slug))
                    {
                        slugs.Add(binding.Slug);
                        if (binding.Required)
                        {
                            requiredSlugs.Add(binding.Slug);
                        }
                    }
                }
            }

            packs.Add(new GatePack(pack.PackId, pack.DependsOn, slugs, hasContent, HasStructure(pack, snapshot)));
        }

        // Kaynaklar: butun satirlar + icerigi olan paketlerin zorunlu kaynaklari (satirsiz olanlar kayitsiz).
        List<GateSource> sources = [];
        foreach (SourceRow row in snapshot.Sources)
        {
            sources.Add(new GateSource(row.Slug, row.AtifMetni, IsRegistered(sourcesDir, row.Slug, exists)));
        }

        foreach (string slug in requiredSlugs.Order(StringComparer.Ordinal))
        {
            if (!sourceRows.ContainsKey(slug))
            {
                sources.Add(new GateSource(slug, null, false));
            }
        }

        List<GateXref> xrefs = [];
        foreach (XrefRow xref in snapshot.Xrefs)
        {
            xrefs.Add(ToGateXref(xref, unitByAnchor, sourceRows, snapshot.OpenReviewXrefIds));
        }

        List<GateLexical> lexicals = [];
        foreach (LexicalRow row in snapshot.Lexicals)
        {
            lexicals.Add(new GateLexical(row.Kind, row.Id, ParseStatus(row.Status), row.LinkedLemmaApproved));
        }

        return new GateInput
        {
            Sources = sources,
            Units = units,
            Xrefs = xrefs,
            Packs = packs,
            Lexicals = lexicals,
            CarriedPackIds = carriedPackIds ?? [],
            PreviousAnchors = previousAnchors ?? [],
        };
    }

    /// <summary>Kaynak kaydi: pipeline/sources/{slug}.toml dosyasi var. Slug dosya adi olarak gecerli degilse kayitsizdir (yol kacisi yok).</summary>
    public static bool IsRegistered(string sourcesDir, string slug, Func<string, bool> fileExists)
    {
        ArgumentNullException.ThrowIfNull(fileExists);
        if (string.IsNullOrEmpty(slug) || !string.Equals(Path.GetFileName(slug), slug, StringComparison.Ordinal))
        {
            return false;
        }

        return fileExists(Path.Combine(sourcesDir, slug + ".toml"));
    }

    private static bool HasStructure(PackDefinition pack, EditorialSnapshot snapshot) =>
        pack.CarriesQuranStructure && (snapshot.QuranWords.Count > 0 || snapshot.QuranMarkers.Count > 0 || snapshot.PageMaps.Count > 0);

    private static bool HasContent(PackDefinition pack, EditorialSnapshot snapshot, Dictionary<string, int> unitCounts)
    {
        if (pack.ContentSources.Any(b => unitCounts.GetValueOrDefault(b.Slug) > 0))
        {
            return true;
        }

        // Kur'an yapisi (kelime, isaret, sayfa) birimsiz de paket icerigidir.
        return HasStructure(pack, snapshot);
    }

    private static GateUnit ToGateUnit(UnitRow unit)
    {
        TextStatus textStatus = ParseTextStatus(unit.MetinDurumu, unit.Anchor);
        if (!UnitStatusLabels.TryParseLabel(unit.Status, out UnitStatus status))
        {
            throw new InvalidDataException($"Bilinmeyen birim durumu ({unit.Anchor}): {unit.Status}");
        }

        return new GateUnit(unit.Anchor, unit.SourceId, textStatus, unit.IsAiDraft, status, !string.IsNullOrEmpty(unit.Successors));
    }

    private static GateXref ToGateXref(
        XrefRow xref,
        Dictionary<string, UnitRow> unitByAnchor,
        Dictionary<string, SourceRow> sourceRows,
        IReadOnlySet<Guid> openReviews)
    {
        if (!XrefTypeLabels.TryParseLabel(xref.Type, out XrefType type))
        {
            throw new InvalidDataException($"Bilinmeyen baglanti turu ({xref.Id}): {xref.Type}");
        }

        if (!XrefStatusLabels.TryParseLabel(xref.Status, out XrefStatus status))
        {
            throw new InvalidDataException($"Bilinmeyen baglanti durumu ({xref.Id}): {xref.Status}");
        }

        string srcSource = unitByAnchor.TryGetValue(xref.SrcAnchor, out UnitRow? src) ? src.SourceId : string.Empty;
        string dstSource = unitByAnchor.TryGetValue(xref.DstAnchor, out UnitRow? dst) ? dst.SourceId : string.Empty;
        bool separateIndex = sourceRows.TryGetValue(dstSource, out SourceRow? dstRow)
            && string.Equals(dstRow.Tur, SeparateIndexKind, StringComparison.Ordinal);

        // float -> double "R" bicimiyle (0,7 -> 0,699999988 olmasin).
        double confidence = PackRows.FromSingle(xref.Confidence);
        bool lexiconApproved = xref.LexiconStatus is null || string.Equals(xref.LexiconStatus, ApprovedLabel, StringComparison.Ordinal);

        return new GateXref(
            xref.Id,
            xref.SrcAnchor,
            xref.DstAnchor,
            type,
            status,
            confidence,
            openReviews.Contains(xref.Id),
            lexiconApproved,
            srcSource,
            dstSource,
            separateIndex);
    }

    private static TextStatus ParseTextStatus(string label, string anchor) =>
        TextStatusLabels.TryParseLabel(label, out TextStatus value)
            ? value
            : throw new InvalidDataException($"Bilinmeyen metin durumu ({anchor}): {label}");

    private static XrefStatus? ParseStatus(string? label)
    {
        if (label is null)
        {
            return null;
        }

        return XrefStatusLabels.TryParseLabel(label, out XrefStatus value)
            ? value
            : throw new InvalidDataException($"Bilinmeyen durum: {label}");
    }
}
