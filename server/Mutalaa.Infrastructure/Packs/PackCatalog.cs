using System.Diagnostics.CodeAnalysis;
using Mutalaa.Domain.Anchors;

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
/// PageMapLayout: Structure kaynagin page_map satirlarina yazilan duzen adi. Content kaynakta da verilebilir: kaynak kendi sayfa eslemesini de tasir
/// (risale-dizin'de sentetik fikstur kaynagi test-risale-ornek; gercek baski eslemesinin duzeniyle karismasin diye ayri duzen adiyla).
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
/// CarriesLexicon: paket word_morph, root, lemma ve lemma_gloss tablolarini doldurur (yalniz kelime-kok; tr_form ve tr_root_index A18'e kadar bos).
/// Book: Risale kitap paketi (risale-{kitap}, A20.4): yalniz unit tasir (arama tablosu, xref_idx ve page_map yoktur); birimleri kaynagin (87 kitap tek
/// kaynaktan, risale-rnk-metin, gelir) capa oneki <see cref="AnchorPrefix"/> ile ayrilir; dil ve yon pack_meta'ya yazilir.
/// IndexesBooks: risale-dizin: unit yerine unit_ref ile icerigi olmayan unit_fts ve unit_tri satirlari, Risale uclu xref_idx ve page_map tasir.
/// </summary>
public sealed record PackDefinition(
    string PackId,
    string Title,
    bool Bundled,
    IReadOnlyList<string> DependsOn,
    IReadOnlyList<PackSourceBinding> Sources,
    bool CarriesQuranStructure = false,
    bool CarriesLexicon = false,
    RisaleBook? Book = null,
    bool IndexesBooks = false)
{
    public int SchemaVersion => PackFormat.SchemaVersion;

    /// <summary>Kitap paketinin capa oneki ("rn:sozler"); kitap paketi degilse null.</summary>
    public string? AnchorPrefix => Book?.AnchorPrefix;

    /// <summary>Birim ve kelime veren kaynaklar.</summary>
    public IEnumerable<PackSourceBinding> ContentSources => Sources.Where(s => s.Role == PackSourceRole.Content);
}

/// <summary>
/// A13'teki paket kimlikleri ve kaynak eslemesi (A13.3). Verisi olmayan paket (hadis, tefsir-elmalili) tabloda durur ama aday sayilmaz:
/// kapi girdisini kuran GateInputBuilder icerigi olmayan paketi HasContent = false verir (Domain: "girmedi · icerik-yok").
/// kelime-kok (A17.7; sozluk verisi yoksa aday sayilmaz) ve Risale paketleri (A20.4: risale-dizin, kitap tablosundan 87 risale-{kitap}, risale-test-ornek)
/// katalogdadir; ses paketleri bu asamada kataloga alinmaz.
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

    /// <summary>Risale uclu baglantilarin, arama indeksinin ve baski sayfa eslemesinin gittigi paket (Icerik paketleri 3.4 ve 4 madde 2).</summary>
    public const string RisaleIndexPackId = "risale-dizin";

    /// <summary>Risale metninin tek kaynagi: 87 kitabin birimleri buradan gelir (K-51 madde 2).</summary>
    public const string RisaleTextSlug = "risale-rnk-metin";

    /// <summary>Risale baski sayfa eslemesinin kaynagi (RNK Neşriyat en son baski; K-51 madde 6 ve 7): risale-dizin'de Structure rolunde.</summary>
    public const string RisalePageSlug = "risale-baski-rnk";

    /// <summary>Risale baglanti dizininin kaynagi (xref satirlari): risale-dizin'de atif rolunde, yalniz xref satiri varsa listelenir.</summary>
    public const string RisaleLinkSlug = "risale-atif-dizini";

    /// <summary>risale-dizin page_map satirlarinin duzen adi (RNK baskisi; core'da "medine-604").</summary>
    public const string RisalePageLayout = "rnk-baski";

    /// <summary>Sentetik Risale fiksturu: kitap slug'i (capa "rn:test-ornek:..."), paket risale-test-ornek ve kaynak test-risale-ornek (K-46 madde 9 ile ayni kalip).</summary>
    public const string RisaleFixtureBookSlug = "test-ornek";

    public const string RisaleFixtureSourceSlug = "test-risale-ornek";

    /// <summary>Fikstur kitabinin page_map duzen adi: fikstur cildi (1) Sozler cildiyle (1) cakisir, ayri duzen adi (layout, volume, page) anahtarini ayirir.</summary>
    public const string RisaleFixturePageLayout = "rnk-baski-test";

    private readonly Dictionary<string, PackDefinition> _byId;
    private readonly Dictionary<string, PackDefinition> _byAnchorPrefix;

    public PackCatalog(IEnumerable<PackDefinition> packs)
    {
        ArgumentNullException.ThrowIfNull(packs);

        _byId = new Dictionary<string, PackDefinition>(StringComparer.Ordinal);
        _byAnchorPrefix = new Dictionary<string, PackDefinition>(StringComparer.Ordinal);
        foreach (PackDefinition pack in packs)
        {
            if (!_byId.TryAdd(pack.PackId, pack))
            {
                throw new ArgumentException($"Yinelenen paket kimligi: {pack.PackId}", nameof(packs));
            }

            if (pack.AnchorPrefix is { } prefix && !_byAnchorPrefix.TryAdd(prefix, pack))
            {
                throw new ArgumentException($"Yinelenen capa oneki: {prefix}", nameof(packs));
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
        .. RisaleDefinitions(RisaleBookTable.Default),
    ]);

    /// <summary>
    /// Risale paketleri (A20.4, K-51): risale-dizin, kitap tablosundan (shared/data/risale-kitaplar.json, gomulu) uretilen her kitap icin risale-{kitap}
    /// ve sentetik fikstur risale-test-ornek. Katalog elle yazilmaz; kitap eklemek dosyaya satir eklemektir. Kitap ve dizin paketleri baska pakete bagli degildir
    /// (kitaplar istek aninda baglanir, dizin kitap olmadan da acilir; Icerik paketleri 2). Fikstur kaynagi test- onekli oldugu icin public'e girmez (P-12).
    /// </summary>
    public static IEnumerable<PackDefinition> RisaleDefinitions(IReadOnlyList<RisaleBook> books)
    {
        ArgumentNullException.ThrowIfNull(books);

        RisaleBook fixture = new(RisaleFixtureBookSlug, "Sentetik Risale örneği (test)", "tr", "ltr", null);
        yield return new PackDefinition(
            RisaleIndexPackId,
            "Risale-i Nur dizini",
            Bundled: false,
            DependsOn: [],
            Sources:
            [
                new PackSourceBinding(RisaleTextSlug, PackSourceRole.Content, Required: true),
                new PackSourceBinding(RisaleFixtureSourceSlug, PackSourceRole.Content, Required: false, PageMapLayout: RisaleFixturePageLayout),
                new PackSourceBinding(RisaleLinkSlug, PackSourceRole.Attribution, Required: false),
                new PackSourceBinding(RisalePageSlug, PackSourceRole.Structure, Required: false, PageMapLayout: RisalePageLayout),
            ],
            IndexesBooks: true);

        foreach (RisaleBook book in books)
        {
            yield return new PackDefinition(
                book.PackId,
                book.Title,
                Bundled: false,
                DependsOn: [],
                Sources: [new PackSourceBinding(RisaleTextSlug, PackSourceRole.Content, Required: true)],
                Book: book);
        }

        yield return new PackDefinition(
            fixture.PackId,
            fixture.Title,
            Bundled: false,
            DependsOn: [],
            Sources: [new PackSourceBinding(RisaleFixtureSourceSlug, PackSourceRole.Content, Required: true)],
            Book: fixture);
    }

    /// <summary>Capa oneki ("rn:sozler") ile kitap paketi; onek katalogda yoksa false (ornegin rn:dizin ya da bilinmeyen kitap).</summary>
    public bool TryGetByAnchorPrefix(string prefix, [NotNullWhen(true)] out PackDefinition? pack)
    {
        ArgumentNullException.ThrowIfNull(prefix);
        return _byAnchorPrefix.TryGetValue(prefix, out pack);
    }

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
    /// Ayristirilamayan capa ve konu: capasi icin null. rn:dizin kitap slug'i olamaz (risale-dizin paketiyle cakisirdi): null. Donen kimligin
    /// katalogda olmasi gerekmez (ornegin tabloda olmayan bir kitap).
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
            AnchorKind.Rn => anchor.Yol.IsDefaultOrEmpty || string.Equals(anchor.Yol[0], RisaleBookTable.ReservedSlug, StringComparison.Ordinal)
                ? null
                : RisaleBookTable.PackIdPrefix + anchor.Yol[0],
            AnchorKind.K => anchor.Yol.IsDefaultOrEmpty ? null : anchor.Yol[0],
            AnchorKind.H or AnchorKind.Ht => string.Equals(anchor.Koleksiyon, "tecrid", StringComparison.Ordinal)
                ? "hadis-tecrid"
                : "hadis-kutub-i-sitte",
            _ => null,
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
