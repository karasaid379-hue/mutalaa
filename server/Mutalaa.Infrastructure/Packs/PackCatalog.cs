using System.Diagnostics.CodeAnalysis;
using Mutalaa.Domain.Anchors;
using Mutalaa.Domain.Links;

namespace Mutalaa.Infrastructure.Packs;

/// <summary>Bir kaynagin pakete nasil girdigi.</summary>
public enum PackSourceRole
{
    /// <summary>Birimleri (ve core'da quran_word satirlarini) pakete verir.</summary>
    Content = 0,

    /// <summary>Yalniz pack_source ve attribution satirlarinda yer alir (core'da tanzil-simple-clean: ar_norm kaynagi, K-44 madde 2).</summary>
    Attribution = 1,

    /// <summary>Yapi verisi: page_map ve quran_marker satirlarini verir (core'da tanzil-ust-veri).</summary>
    Structure = 2,

    /// <summary>Sozluk verisi: root, lemma ve quran_word'un QAC sutunlarini verir (kelime-kok'te qac-morfoloji; K-50 madde 3 ve 4).</summary>
    Dictionary = 3,
}

/// <summary>
/// Paket-kaynak baglantisi. Required: kaynak bu paketin kapi girdisinde her zaman bulunur (kaydi yoksa P-01); aksi hâlde yalniz editoryal
/// veritabaninda satiri ya da birimi varsa girer (ornegin hadis-tecrid'te Turkce ceviriler henuz alinmamis olabilir).
/// PageMapLayout: Structure kaynagin page_map satirlarina yazilan duzen adi.
/// K-47 notu: core'daki Elmalili mealleri (elmalili-meal, elmalili-sade-meal) Required: false'tur (kaynak kaydi ve birimleri yoksa paket
/// onlarsiz uretilir); ilk meal yayininden sonra meal capa kumesi donar: onceki yayindaki her meal capasi sonrakinde etkin ya da
/// yonlendirmeli olmali, kaybolursa yayin <c>capa-kayboldu</c> ile reddedilir.
/// A34'e kadar kismi meal public'e girebilir (K-49 madde 5): onayli birimleri olan meal kaynagi, butun ayetleri onaylanmadan da
/// public pakete girer; "G-INC gecmeden public'e cikmaz" kurali A34'te yazilir.
/// </summary>
public sealed record PackSourceBinding(string Slug, PackSourceRole Role, bool Required, string? PageMapLayout = null);

/// <summary>
/// Katalogdaki bir paket (manifest satirinin kaynagi: Icerik paketleri 5). SchemaVersion her zaman <see cref="PackFormat.SchemaVersion"/>'dur.
/// CarriesQuranStructure: paket quran_word, quran_marker ve page_map tablolarini doldurur (yalniz core).
/// CarriesLexicon: paket word_morph, root, lemma (QAC Arapca ve Turkce, K-51 madde 9), lemma_gloss, tr_root_index ve tr_form tablolarini doldurur (yalniz kelime-kok).
/// </summary>
public sealed record PackDefinition(
    string PackId,
    string Title,
    bool Bundled,
    IReadOnlyList<string> DependsOn,
    IReadOnlyList<PackSourceBinding> Sources,
    bool CarriesQuranStructure = false,
    bool CarriesLexicon = false)
{
    public int SchemaVersion => PackFormat.SchemaVersion;

    /// <summary>Birim ve kelime veren kaynaklar.</summary>
    public IEnumerable<PackSourceBinding> ContentSources => Sources.Where(s => s.Role == PackSourceRole.Content);
}

/// <summary>
/// A13'teki paket kimlikleri ve kaynak eslemesi (A13.3). Verisi olmayan paket (hadis, tefsir-elmalili) tabloda durur ama aday sayilmaz:
/// kapi girdisini kuran GateInputBuilder icerigi olmayan paketi HasContent = false verir (Domain: "girmedi · icerik-yok").
/// kelime-kok (A17.7; sozluk verisi yoksa aday sayilmaz) katalogdadir; ses paketleri bu asamada kataloga alinmaz.
/// </summary>
public sealed class PackCatalog
{
    public const string CorePackId = "core";

    /// <summary>QAC kok, lemma ve kelime morfolojisi paketi (K-50 madde 9).</summary>
    public const string KelimeKokPackId = "kelime-kok";

    /// <summary>QAC morfoloji kaynagi: root, lemma ve quran_word'un QAC sutunlari (kelime-kok'te Dictionary rolu).</summary>
    public const string QacMorphologySlug = "qac-morfoloji";

    /// <summary>Hazir kelime anlami kaynagi (QuranWBW): lemma_gloss adaylarinin kaynagi; kelime-kok'te atif rolu, Required: false.</summary>
    public const string GlossSourceSlug = "quranwbw-tr";

    /// <summary>
    /// Sozluk verisi kaynaklari (K-46 madde 1 ve K-50 madde 3): anlik goruntu okuyucusu root, lemma, lemma_gloss ve quran_word'un QAC
    /// sutunlarini yalniz bu kaynaklar icin okur; kaynak ozeti de bunlar icin sozluk satirlarini ozetler.
    /// </summary>
    public static IReadOnlyList<string> LexiconSourceSlugs { get; } = [QacMorphologySlug, GlossSourceSlug];

    /// <summary>Turkce lemma kaynagi (kaikki-tr): lemma (lang = 'tr') satirlarinin kaynagi; kelime-kok'te atif rolu, Required: false.</summary>
    public const string TrLemmaSourceSlug = "kaikki-tr";

    /// <summary>QurSim (benzer_ayet kaynaklarindan biri): core'da atif rolu, Required: false; benzer_ayet satiri varsa kunyesi listelenir.</summary>
    public const string QursimSlug = "qursim";

    /// <summary>Risale uclu baglantilarin gittigi paket (Icerik paketleri 4 madde 2); A20'ye kadar katalogda degildir.</summary>
    public const string RisaleIndexPackId = "risale-dizin";

    private readonly Dictionary<string, PackDefinition> _byId;

    public PackCatalog(IEnumerable<PackDefinition> packs)
    {
        ArgumentNullException.ThrowIfNull(packs);

        _byId = new Dictionary<string, PackDefinition>(StringComparer.Ordinal);
        foreach (PackDefinition pack in packs)
        {
            if (!_byId.TryAdd(pack.PackId, pack))
            {
                throw new ArgumentException($"Yinelenen paket kimligi: {pack.PackId}", nameof(packs));
            }
        }

        All = [.. _byId.Values.OrderBy(p => p.PackId, StringComparer.Ordinal)];
    }

    /// <summary>A13 kataloğu.</summary>
    public static PackCatalog Default { get; } = new(
    [
        new PackDefinition(
            CorePackId,
            "Kur'an ve Elmalılı mealleri",
            Bundled: true,
            DependsOn: [],
            Sources:
            [
                new PackSourceBinding("tanzil-uthmani", PackSourceRole.Content, Required: true),
                new PackSourceBinding("elmalili-meal", PackSourceRole.Content, Required: false),
                new PackSourceBinding("elmalili-sade-meal", PackSourceRole.Content, Required: false),
                new PackSourceBinding("tanzil-simple-clean", PackSourceRole.Attribution, Required: true),
                new PackSourceBinding("tanzil-ust-veri", PackSourceRole.Structure, Required: true, PageMapLayout: "medine-604"),
                new PackSourceBinding(QursimSlug, PackSourceRole.Attribution, Required: false),
            ],
            CarriesQuranStructure: true),
        new PackDefinition(
            KelimeKokPackId,
            "Kelime, kök ve lemma (QAC)",
            Bundled: false,
            DependsOn: [CorePackId],
            Sources:
            [
                new PackSourceBinding(QacMorphologySlug, PackSourceRole.Dictionary, Required: true),
                new PackSourceBinding(GlossSourceSlug, PackSourceRole.Attribution, Required: false),
                new PackSourceBinding(TrLemmaSourceSlug, PackSourceRole.Attribution, Required: false),
            ],
            CarriesLexicon: true),
        new PackDefinition(
            "test-kucuk",
            "Sentetik küçük kitap (test)",
            Bundled: false,
            DependsOn: [],
            Sources: [new PackSourceBinding("test-kucuk", PackSourceRole.Content, Required: true)]),
        new PackDefinition(
            "tefsir-test-ornek",
            "Sentetik tefsir örneği (test)",
            Bundled: false,
            DependsOn: [CorePackId],
            Sources: [new PackSourceBinding("test-tefsir-ornek", PackSourceRole.Content, Required: true)]),
        new PackDefinition(
            "tefsir-elmalili",
            "Elmalılı · Hak Dini Kur'an Dili",
            Bundled: false,
            DependsOn: [CorePackId],
            Sources: [new PackSourceBinding("elmalili-tefsir", PackSourceRole.Content, Required: true)]),
        new PackDefinition(
            "hadis-tecrid",
            "Tecrîd-i Sarîh (Arapça, Ahmed Naim ve Kâmil Miras)",
            Bundled: false,
            DependsOn: [CorePackId],
            Sources:
            [
                new PackSourceBinding("tecrid-ar", PackSourceRole.Content, Required: true),
                new PackSourceBinding("tecrid-naim", PackSourceRole.Content, Required: false),
                new PackSourceBinding("tecrid-miras", PackSourceRole.Content, Required: false),
            ]),
        new PackDefinition(
            "hadis-kutub-i-sitte",
            "Kütüb-i Sitte (Arapça)",
            Bundled: false,
            DependsOn: [CorePackId],
            Sources: [new PackSourceBinding("hadis-fawaz-ar", PackSourceRole.Content, Required: true)]),
    ]);

    /// <summary>Paket kimligine gore Ordinal sirali.</summary>
    public IReadOnlyList<PackDefinition> All { get; }

    public PackDefinition Get(string packId) =>
        TryGet(packId, out PackDefinition? pack) ? pack : throw new KeyNotFoundException($"Katalogda paket yok: {packId}");

    public bool TryGet(string? packId, [NotNullWhen(true)] out PackDefinition? pack)
    {
        pack = null;
        return packId is not null && _byId.TryGetValue(packId, out pack);
    }

    /// <summary>
    /// Capanin ait oldugu paket (Icerik paketleri 4, son paragraf): q, qa ve meal capalari core; tf:{eser} tefsir-{eser}; rn:{kitap} risale-{kitap};
    /// k:{kitap} {kitap} paketi; h ve ht capalari tecrid koleksiyonu icin hadis-tecrid, digerleri hadis-kutub-i-sitte.
    /// Ayristirilamayan capa ve konu: capasi icin null. Donen kimligin katalogda olmasi gerekmez (ornegin risale-sozler).
    /// </summary>
    public static string? PackIdForAnchor(string anchor)
    {
        if (!AnchorRef.TryParse(anchor, out AnchorRef? parsed))
        {
            return null;
        }

        return PackIdForAnchor(parsed);
    }

    public static string? PackIdForAnchor(AnchorRef anchor)
    {
        ArgumentNullException.ThrowIfNull(anchor);

        return anchor.Kind switch
        {
            AnchorKind.Q or AnchorKind.Qa or AnchorKind.Meal => CorePackId,
            AnchorKind.Tf or AnchorKind.Tfb => "tefsir-" + anchor.Eser,
            AnchorKind.Rn => anchor.Yol.IsDefaultOrEmpty ? null : "risale-" + anchor.Yol[0],
            AnchorKind.K => anchor.Yol.IsDefaultOrEmpty ? null : anchor.Yol[0],
            AnchorKind.H or AnchorKind.Ht => string.Equals(anchor.Koleksiyon, "tecrid", StringComparison.Ordinal)
                ? "hadis-tecrid"
                : "hadis-kutub-i-sitte",
            _ => null,
        };
    }

    /// <summary>
    /// Baglantinin yazilacagi paket, tur dahil (Icerik paketleri 4; K-51 madde 3): QAC'den tureyen kok ve lemma baglantilari iki ucu core olsa da
    /// kelime-kok'e (core QAC verisi tasimaz); benzer_ayet iki ucu da core'daysa core'a (yani q: capalari) gider. Digerleri
    /// <see cref="PackIdForXref(string, string)"/> kuralini izler (benzer_ayet'in iki ucu q: ise sonuc core'dur). Uclardan biri paketlenemiyorsa (ayristirilamayan capa, konu:) null.
    /// </summary>
    public string? PackIdForXref(XrefType type, string srcAnchor, string dstAnchor)
    {
        string? generic = PackIdForXref(srcAnchor, dstAnchor);
        if (generic is null)
        {
            return null;
        }

        return type switch
        {
            XrefType.Kok or XrefType.Lemma => KelimeKokPackId,
            _ => generic,
        };
    }

    /// <summary>
    /// Baglantinin yazilacagi paket (Icerik paketleri 4). Her iki uc core ise core; bir uc Risale ise risale-dizin; bir uc core digeri P ise P;
    /// iki ayri istege bagli pakette depends_on ile bagimli olan, bagimlilik yoksa pack_id Ordinal olarak sonra gelen. Uclardan biri
    /// paketlenemiyorsa (ayristirilamayan capa, konu:) null.
    /// </summary>
    public string? PackIdForXref(string srcAnchor, string dstAnchor)
    {
        string? src = PackIdForAnchor(srcAnchor);
        string? dst = PackIdForAnchor(dstAnchor);
        if (src is null || dst is null)
        {
            return null;
        }

        // Risale uclu baglanti (kitap paketine degil dizine yazilir); iki uc ayni kitap olsa da dizin.
        if (src.StartsWith("risale-", StringComparison.Ordinal) || dst.StartsWith("risale-", StringComparison.Ordinal))
        {
            return RisaleIndexPackId;
        }

        if (string.Equals(src, dst, StringComparison.Ordinal))
        {
            return src;
        }

        if (string.Equals(src, CorePackId, StringComparison.Ordinal))
        {
            return dst;
        }

        if (string.Equals(dst, CorePackId, StringComparison.Ordinal))
        {
            return src;
        }

        if (DependsOn(src, dst))
        {
            return src;
        }

        if (DependsOn(dst, src))
        {
            return dst;
        }

        return string.CompareOrdinal(src, dst) > 0 ? src : dst;
    }

    private bool DependsOn(string packId, string other) =>
        _byId.TryGetValue(packId, out PackDefinition? pack) && pack.DependsOn.Contains(other, StringComparer.Ordinal);
}
