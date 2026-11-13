using Mutalaa.Api.Tests.Support;
using Mutalaa.Domain.Releases;
using Mutalaa.Domain.Releases.Gate;
using Mutalaa.Domain.Text;
using Mutalaa.Infrastructure.Packs;
using Mutalaa.Infrastructure.Releases;

namespace Mutalaa.Publisher.Tests;

/// <summary>
/// Paket testlerinin sentetik verisi. Metinler acikca sentetiktir ("Deneme paragrafi N", "Isik" sozcugu, uydurma harf dizisi); gercek Kur'an, meal, tefsir,
/// hadis ya da Risale metni yoktur. Tanzil bayt testleri yalniz depodaki fiksturu parcalariyla yapilir (TanzilRawVerifierTests).
/// </summary>
internal static class PackTestData
{
    public const string SchemaDirRelative = "packages/content-schema/sql";

    /// <summary>Uydurma Arapca harf dizisi (kod noktalariyla kurulur; Kur'an kelimesi degil).</summary>
    public static readonly string SyntheticArabic = new([(char)0x628, (char)0x62A, (char)0x62B, (char)0x62C, (char)0x62D, (char)0x62E]);

    public static PackDefinitions Definitions() => PackDefinitions.Load(RepoFiles.PathOf(SchemaDirRelative));

    public static SourceRow Source(
        string slug,
        string tur = "kitap",
        string atifMetni = "Sentetik test verisi (Mutalaa).",
        string? atifUrl = null,
        string? kaynakUrl = null,
        string? notice = null,
        string baslik = "Deneme kaynagi",
        string surum = "1") =>
        new(slug, tur, baslik, null, surum, null, kaynakUrl, null, null, null, atifMetni, atifUrl, notice, null);

    public static UnitRow Unit(
        string anchor,
        string sourceId,
        string kind = "kitap",
        string metin = "Deneme paragrafi 1",
        string durum = "onayli",
        long ord = 1,
        int? ayahLo = null,
        int? ayahHi = null,
        string? arNorm = null,
        string? trWide = null,
        string? trStem = null,
        bool aiDraft = false,
        string status = "etkin",
        string? successors = null) =>
        new(
            anchor,
            kind,
            "govde",
            sourceId,
            null,
            ord,
            ayahLo,
            ayahHi,
            metin,
            "[]",
            null,
            "{}",
            ContentHash.Compute(metin),
            durum,
            status,
            successors,
            trWide,
            trStem,
            arNorm,
            aiDraft);

    public static XrefRow Xref(
        string src,
        string dst,
        string type = "atif",
        string status = "onayli",
        float score = 0.5f,
        float confidence = 0.9f,
        Guid? id = null,
        string? srcHash = null,
        string? dstHash = null,
        string? evidenceSource = null) =>
        new(id ?? Guid.NewGuid(), src, null, null, dst, null, null, type, score, confidence, "{}", status, "test", null, srcHash, dstHash, evidenceSource);

    /// <summary>Gate icin kayit dosyasi var sayilan kaynak kumesi.</summary>
    public static Func<string, bool> AllRegistered() => _ => true;

    public static GateResult Evaluate(BuildFlavor flavor, EditorialSnapshot snapshot, PackCatalog? catalog = null, Func<string, bool>? fileExists = null)
    {
        GateInput input = GateInputBuilder.Build(snapshot, catalog ?? PackCatalog.Default, "pipeline/sources", fileExists: fileExists ?? AllRegistered());
        return GateEvaluator.Evaluate(flavor, input);
    }

    /// <summary>Tek paketlik (test-kucuk) bir icerik: 3 birim, biri "Isik" sozcugu tasir. Anahtarlar SearchNormalizer'dan gelir.</summary>
    public static PackContent SmallContent(BuildFlavor flavor = BuildFlavor.Dev, string packId = "test-kucuk")
    {
        string light = "Deneme paragrafi 3 Işık sözcüğü";
        SearchKeys keys = SearchNormalizer.Keys(light);
        return new PackContent
        {
            PackId = packId,
            Flavor = flavor,
            PackSources = [new PackSourceRow("test-kucuk")],
            Attributions = [new PackAttributionRow("test-kucuk", "Deneme kaynagi", "1", null, "Sentetik test verisi (Mutalaa).", null)],
            Units =
            [
                PackUnit("k:test-kucuk:bolum-1:p1", "Deneme paragrafi 1", 1, approved: 1),
                PackUnit("k:test-kucuk:bolum-1:p2", "Deneme paragrafi 2", 2, approved: 0),
                PackUnit("k:test-kucuk:bolum-1:p3", light, 3, approved: 1),
            ],
            UnitSearch =
            [
                new PackUnitSearchRow("k:test-kucuk:bolum-1:p1", "deneme paragrafi 1", "deneme paragraf 1", null),
                new PackUnitSearchRow("k:test-kucuk:bolum-1:p2", "deneme paragrafi 2", "deneme paragraf 2", null),
                new PackUnitSearchRow("k:test-kucuk:bolum-1:p3", keys.TrWide, keys.TrWide, null),
            ],
        };
    }

    public static PackUnitRow PackUnit(string anchor, string text, long ord, long approved = 1, long? ayahFirst = null, long? ayahLast = null, string kind = "kitap") =>
        new(anchor, kind, "govde", null, ord, ayahFirst, ayahLast, anchor, text, "[]", null, "{}", ContentHash.Compute(text), "etkin", approved, null);

    public static PackWriteRequest Request(string outDir, string version = "2026.11.0", params SourceRow[] sources) =>
        new(outDir, version, "2026.11.09-abcdef0", sources.Length == 0 ? [Source("test-kucuk")] : sources);

    public const string TanzilNotice = "\n\n# Deneme bildirimi satiri 1\n# Deneme bildirimi satiri 2\n";

    public static readonly Guid XrefCore = new("0190a000-0000-7000-8000-000000000001");
    public static readonly Guid XrefToTefsir = new("0190a000-0000-7000-8000-000000000002");
    public static readonly Guid XrefFromKucuk = new("0190a000-0000-7000-8000-000000000003");
    public static readonly Guid XrefRed = new("0190a000-0000-7000-8000-000000000004");

    /// <summary>
    /// Sentetik anlik goruntu: core kaynaklari (uc Tanzil kaynagi, metinler "Deneme paragrafi N"), iki ayet ve bir onaysiz ayet, kelimeler, isaret, sayfa,
    /// test-kucuk ve test-tefsir-ornek birimleri ve dort baglanti (core ici onayli, core->tefsir aday, kucuk->core aday, red).
    /// </summary>
    public static EditorialSnapshot Snapshot() => new()
    {
        Sources =
        [
            Source("tanzil-uthmani", "kuran_metni", atifMetni: "Atif 1", notice: TanzilNotice, baslik: "Uthmani deneme"),
            Source("tanzil-simple-clean", "kuran_metni", atifMetni: "Atif 2", atifUrl: "https://example.invalid/atif", kaynakUrl: "https://example.invalid/kaynak"),
            Source("tanzil-ust-veri", "mushaf_duzeni", atifMetni: "Atif 3", kaynakUrl: "https://example.invalid/ust-veri"),
            Source("test-kucuk"),
            Source("test-tefsir-ornek", "tefsir"),
        ],
        Units =
        [
            Unit("q:1:1", "tanzil-uthmani", "ayet", "Deneme paragrafi 1", ord: 1, ayahLo: 1, ayahHi: 2, arNorm: SyntheticArabic, trWide: "deneme paragrafi 1"),
            Unit("q:1:2", "tanzil-uthmani", "ayet", "Deneme paragrafi 2", ord: 2, ayahLo: 2, ayahHi: 3, arNorm: SyntheticArabic),
            Unit("q:1:3", "tanzil-uthmani", "ayet", "Deneme paragrafi 3", ord: 3, ayahLo: 3, ayahHi: 4, durum: "taslak"),
            Unit("k:test-kucuk:bolum-1:p1", "test-kucuk", "kitap", "Deneme paragrafi 4", ord: 1),
            Unit("tf:test-ornek:1-1-2:p1", "test-tefsir-ornek", "tefsir", "Deneme paragrafi 5", ord: 1, ayahLo: 1, ayahHi: 3),
        ],
        QuranWords =
        [
            new QuranWordRow("q:1:1:1", 1, 1, 1, 1, SyntheticArabic, SyntheticArabic, 0, 6, "tanzil-uthmani"),
            new QuranWordRow("q:1:2:1", 1, 2, 1, 2, SyntheticArabic, SyntheticArabic, 0, 6, "tanzil-uthmani"),
            new QuranWordRow("q:1:3:1", 1, 3, 1, 3, SyntheticArabic, SyntheticArabic, 0, 6, "tanzil-uthmani"),
        ],
        QuranMarkers = [new QuranMarkerRow("cuz", 1, "q:1:1", null, "tanzil-ust-veri"), new QuranMarkerRow("secde", 1, "q:1:2", "recommended", "tanzil-ust-veri")],
        PageMaps = [new PageMapRow("tanzil-ust-veri", null, 1, null, "q:1:1", null, "q:1:3", null)],
        Xrefs =
        [
            Xref("q:1:1", "q:1:2", "benzer_ayet", "onayli", score: 0.7f, confidence: 0.9f, id: XrefCore),
            Xref("q:1:1", "tf:test-ornek:1-1-2:p1", "atif", "aday", id: XrefToTefsir),
            Xref("k:test-kucuk:bolum-1:p1", "q:1:2", "ima", "aday", id: XrefFromKucuk),
            Xref("q:1:1", "q:1:2", "iktibas", "red", id: XrefRed),
        ],
    };

    /// <summary>Gecici klasor (sistem gecici klasoru; test cercevesi icin serbest). Atilinca silinir.</summary>
    public sealed class TempDir : IDisposable
    {
        public TempDir()
        {
            Path = System.IO.Path.Combine(System.IO.Path.GetTempPath(), "mutalaa-pack-" + Guid.NewGuid().ToString("N"));
            Directory.CreateDirectory(Path);
        }

        public string Path { get; }

        public void Dispose()
        {
            try
            {
                Directory.Delete(Path, recursive: true);
            }
            catch (IOException)
            {
                // Windows / OneDrive kilidi: temizlik en iyi cabadir.
            }
        }
    }
}
