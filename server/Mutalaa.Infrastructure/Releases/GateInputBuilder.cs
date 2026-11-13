using System.Globalization;
using System.Text.Json;
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
/// <item>Paket: icerigi (birim, yapi satiri ya da sozluk verisi: kok, lemma, anlam, QAC kelime morfolojisi) yoksa HasContent = false ("icerik-yok"; kaynaklari kapiya sokulmaz). Zorunlu olmayan kaynak yalniz
/// satiri varsa pakete bagli sayilir.</item>
/// <item>Birim: IsAiDraft = onaysiz birimin yz_modeli dolu review satiri var; HasSuccessors = successors en az bir ogeli dizi ('[]' ve JSON null bos sayilir).</item>
/// <item>Sozluk (P-09): quran_word_fix satirinda ApplyDefect, duzeltmenin uygulanamama nedenidir (WordMorphFixes; deger cevrilemiyor, kelimenin QAC satiri yok,
/// gosterdigi root_id ya da lemma_id yok); kapi onayli ve kusurlu duzeltmeyi yayin reddi sayar.</item>
/// <item>Baglanti: uclarin kaynagi uc capanin birim satirindan; bulunamayan uc kaynaksiz ("") sayilir (gorunmez). DstIsSeparateIndex: hedef birimin
/// kaynaginin turu <c>baglanti_verisi</c> (risale-atif-dizini). LexiconApproved: evidence.lexicon_status yok ya da <c>onayli</c>.</item>
/// <item>PreviousAnchors ve CarriedPackIds cagiran tarafindan verilir (onceki yayinin paket dosyalarindan ve manifestinden gelir).</item>
/// </list>
/// </summary>
public static class GateInputBuilder
{
    private const string ApprovedLabel = "onayli";
    private const string SeparateIndexKind = "baglanti_verisi";

    /// <summary>content_hash ozet on eki (K-51 madde 1: evidence.src_hash, dst_hash ve tr_root_index.unit_hash).</summary>
    private const int HashPrefixLength = 16;

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
        FixChecker fixes = new(snapshot, catalog);
        foreach (LexicalRow row in snapshot.Lexicals)
        {
            lexicals.Add(new GateLexical(
                row.Kind,
                row.Id,
                ParseStatus(row.Status),
                row.LinkedLemmaApproved,
                row.Kind == LexicalKind.QuranWordFix ? fixes.Defect(row.Id) : null));
        }

        AddTurkishLexicals(snapshot, lexicals);

        List<GateMeasurement> gates = [];
        foreach (XrefGateRow row in snapshot.XrefGates)
        {
            if (!XrefTypeLabels.TryParseLabel(row.Tur, out XrefType gateType))
            {
                throw new InvalidDataException($"Bilinmeyen xref_gate turu: {row.Tur}");
            }

            gates.Add(new GateMeasurement(gateType, row.SetSinifi, row.Sonuc));
        }

        return new GateInput
        {
            Sources = sources,
            Units = units,
            Xrefs = xrefs,
            Packs = packs,
            Lexicals = lexicals,
            Gates = gates,
            CarriedPackIds = carriedPackIds ?? [],
            PreviousAnchors = previousAnchors ?? [],
        };
    }

    // Turkce lemma, tr_root_index ve tr_form (K-51 madde 1 ve 9): kapi girdisine her satir bir GateLexical olur. tr_root_index ve tr_form satiri
    // bagli lemmanin kimligini tasir (kapi lemmanin kararini izler); tr_root_index ayrica birim capasi ve kaydedilen unit_hash degerini tasir.
    // Kimlikler: lemma "{id}", tr_root_index "{anchor}|{span_start}", tr_form "{key_narrow}|{tr_lemma_id}" (PackAssembler ayni anahtari kullanir).
    private static void AddTurkishLexicals(EditorialSnapshot snapshot, List<GateLexical> lexicals)
    {
        Dictionary<int, TrLemmaRow> lemmas = [];
        foreach (TrLemmaRow lemma in snapshot.TrLemmas)
        {
            lemmas[lemma.Id] = lemma;
            lexicals.Add(new GateLexical(
                LexicalKind.TrLemma,
                lemma.Id.ToString(CultureInfo.InvariantCulture),
                ParseStatus(lemma.Status),
                LinkedLemmaApproved: false,
                LemmaId: lemma.Id,
                OnayYolu: lemma.OnayYolu,
                HasKanit: lemma.HasKanit));
        }

        foreach (TrRootIndexRow row in snapshot.TrRootIndex)
        {
            lexicals.Add(new GateLexical(
                LexicalKind.TrRootIndex,
                row.Anchor + "|" + row.SpanStart.ToString(CultureInfo.InvariantCulture),
                null,
                IsApproved(lemmas, row.TrLemmaId),
                LemmaId: row.TrLemmaId,
                UnitAnchor: row.Anchor,
                UnitHash: row.UnitHash));
        }

        foreach (TrFormRow row in snapshot.TrForms)
        {
            lexicals.Add(new GateLexical(
                LexicalKind.TrForm,
                row.KeyNarrow + "|" + row.TrLemmaId.ToString(CultureInfo.InvariantCulture),
                null,
                IsApproved(lemmas, row.TrLemmaId),
                LemmaId: row.TrLemmaId));
        }
    }

    private static bool IsApproved(Dictionary<int, TrLemmaRow> lemmas, int lemmaId) =>
        lemmas.TryGetValue(lemmaId, out TrLemmaRow? lemma) && string.Equals(lemma.Status, ApprovedLabel, StringComparison.Ordinal);

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

        // Kur'an yapisi (kelime, isaret, sayfa) birimsiz de paket icerigidir; sozluk verisi de (kok, lemma, anlam, QAC kelime morfolojisi).
        return HasStructure(pack, snapshot) || HasLexicon(pack, snapshot);
    }

    private static bool HasLexicon(PackDefinition pack, EditorialSnapshot snapshot) =>
        pack.CarriesLexicon
        && (snapshot.Roots.Count > 0
            || snapshot.Lemmas.Count > 0
            || snapshot.TrLemmas.Count > 0
            || snapshot.LemmaGlosses.Count > 0
            || snapshot.QuranWords.Any(w => w.MorphSource is not null));

    // quran_word_fix uygulanabilirlik denetimi (WordMorphFixes.Check): kapi girdisi ile birlestirici ayni kurali kullanir.
    private sealed class FixChecker
    {
        private readonly Dictionary<string, QuranWordFixRow> _byId = new(StringComparer.Ordinal);
        private readonly HashSet<string> _morphWords = new(StringComparer.Ordinal);
        private readonly HashSet<int> _rootIds;
        private readonly HashSet<int> _lemmaIds;

        public FixChecker(EditorialSnapshot snapshot, PackCatalog catalog)
        {
            foreach (QuranWordFixRow fix in snapshot.WordFixes)
            {
                _byId[fix.Id.ToString("D", CultureInfo.InvariantCulture)] = fix;
            }

            if (_byId.Count > 0)
            {
                foreach (QuranWordRow word in snapshot.QuranWords)
                {
                    if (word.MorphSource is not null)
                    {
                        _morphWords.Add(word.Anchor);
                    }
                }
            }

            // Hedef kimlik, sozluk paketinin Dictionary kaynaklarindan gelen kok ya da onayli lemma olmalidir (birlestirici ayni kumeyi kullanir).
            HashSet<string> dictionary = new(
                catalog.All.Where(p => p.CarriesLexicon).SelectMany(p => p.Sources).Where(b => b.Role == PackSourceRole.Dictionary).Select(b => b.Slug),
                StringComparer.Ordinal);
            _rootIds = [.. snapshot.Roots.Where(r => dictionary.Contains(r.SourceId)).Select(r => r.Id)];
            _lemmaIds = [.. snapshot.Lemmas.Where(l => dictionary.Contains(l.SourceId) && string.Equals(l.Status, ApprovedLabel, StringComparison.Ordinal)).Select(l => l.Id)];
        }

        public string? Defect(string fixId) =>
            _byId.TryGetValue(fixId, out QuranWordFixRow? fix)
                ? WordMorphFixes.Check(fix.Field, fix.NewValue, _morphWords.Contains(fix.Anchor), _rootIds.Contains, _lemmaIds.Contains, out _)
                : null;
    }

    private static GateUnit ToGateUnit(UnitRow unit)
    {
        TextStatus textStatus = ParseTextStatus(unit.MetinDurumu, unit.Anchor);
        if (!UnitStatusLabels.TryParseLabel(unit.Status, out UnitStatus status))
        {
            throw new InvalidDataException($"Bilinmeyen birim durumu ({unit.Anchor}): {unit.Status}");
        }

        string? hashPrefix = unit.ContentHash.Length >= HashPrefixLength ? unit.ContentHash[..HashPrefixLength] : unit.ContentHash;
        return new GateUnit(unit.Anchor, unit.SourceId, textStatus, unit.IsAiDraft, status, HasSuccessors(unit), hashPrefix);
    }

    // K-47 madde 2: yonlendirme "dolu" successors'tir. jsonb sutunda '[]' (bos dizi) ve JSON 'null' bos sayilir; yalniz en az bir ogeli dizi doludur.
    private static bool HasSuccessors(UnitRow unit)
    {
        if (string.IsNullOrWhiteSpace(unit.Successors))
        {
            return false;
        }

        try
        {
            using JsonDocument document = JsonDocument.Parse(unit.Successors);
            return document.RootElement.ValueKind switch
            {
                JsonValueKind.Array => document.RootElement.GetArrayLength() > 0,
                JsonValueKind.Null => false,
                _ => throw new InvalidDataException($"Birim successors degeri bir dizi degil ({unit.Anchor})."),
            };
        }
        catch (JsonException ex)
        {
            throw new InvalidDataException($"Birim successors degeri gecerli JSON degil ({unit.Anchor}).", ex);
        }
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
            separateIndex,
            xref.SrcHash,
            xref.DstHash);
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
