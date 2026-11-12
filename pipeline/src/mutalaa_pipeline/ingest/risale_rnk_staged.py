"""RNK ayristirmasindan capali `StagedUnit` uretimi (A20.1b, K-51 madde 2, 3 ve 6).

`risale_rnk.ayristir` kitap dosyasini ham birimlere boler; bu modul onlara `rn:` capasi verir:

* **Bolum agaci** RNK `json` icindekilerindendir (`contents`). Baslik satirlari (`<&€∑`) json
  dugumleriyle `title`/`textInBook` normalize eslesmesi ve `pageNo` ile eslesir; eslesen baslik
  o bolumun `p1` birimidir. Bolum adi sayili kalibi izler (A20.2b; `anchor.risale.baslik_bolum_adi`:
  "Yirmi Besinci Soz" -> `soz-25`, `mukaddime`, `zeyl`, `hatime`); kaliba uymayan baslik
  basliktan turetilir (`slug_turet`, en cok 40 karakter), kardes cakismasinda `-2` eki alir
  (kalip adlari kalip disi bir adin eki olarak uretilmez). Kitabin ilk duzey dugumu kitap
  slug'iyla ayni adi tasiyorsa (Sunuhat, Tuluat, Isarat) o duzey daraltilir. Eslesmeyen baslik
  satiri duzeysiz baslik olarak o anki bolumde kalir (uyari). Ilk eslesmeden onceki birimler
  kitap kokundedir (`rn:{kitap}:p{n}`).
* **Paragraf** numarasi `p{n}` bolum basina 1'den artar (okuma sirasi). Dipnot `hasiye-{n}`
  bolumudur (`rn:{kitap}:{bolum}:hasiye-{n}:p{k}`; `n` bolumdeki sira, `k` dipnot ici paragraf);
  ana paragrafta `t: "hasiye"` isareti `a` ile dipnotun ilk paragraf capasini gosterir.
* **Bolunme** (`risale-kitaplar.json` `rnk.bolunme`, ornek `tr_k/sunuhat`): bir RNK dosyasi
  birden cok kitap slug'ina bolunur; birim, ilk satirinin sayfasina gore parcaya gider. Sayfa
  isaretleri hicbir birimi bolmez; sayfa listesi RNK dosyasi (uid) duzeyinde kalir.

Slug dogrulamasi (`slug_denetle`, `bolum_denetle`) ve editor onayi I-24'e aittir. Metin degismez;
`attrs.marks` isaretleri tasir; `attrs.baslik_yolu` bolumun json baslik zinciridir (etiket icin).
"""

import bisect
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Final

from mutalaa_pipeline.anchor.risale import (
    Kitap,
    RisaleHatasi,
    baslik_bolum_adi,
    bolum_denetle,
    bolum_kalibi,
    hasiye_yolu,
    kardes_slug,
    rn_capa,
    slug_turet,
)
from mutalaa_pipeline.export.ortak import GirdiHatasi, kati_json
from mutalaa_pipeline.ingest.base import StagedUnit
from mutalaa_pipeline.ingest.risale_rnk import (
    AYRISTIRICI_SURUMU,
    Birim,
    KitapAyristirma,
    ayristir,
)
from mutalaa_pipeline.normalize import search_keys

MAKS_BOLUM_SLUG: Final = 40
ESLESME_PENCERESI: Final = 80
SAYFA_UYUMSUZ_PENCERE: Final = 5
BOLUM_ONEKI: Final = "bolum-"


# ---------------------------------------------------------------------------
# json icindekiler agaci


@dataclass(frozen=True)
class Dugum:
    sira: int  # on sira (kok = 0)
    baslik: str
    metin_kitapta: str
    sayfa: int
    derinlik: int
    ust: int | None
    anahtarlar: frozenset[str]


@dataclass(frozen=True)
class JsonBilgisi:
    uid: str
    raf: str
    ilk_sayfa: int
    son_sayfa: int
    dugumler: tuple[Dugum, ...]


def baslik_anahtari(metin: str) -> str:
    """Baslik karsilastirma anahtari: Turkce dar anahtar ve `ar_norm` birlikte."""
    k = search_keys(metin)
    return f"{k.tr_narrow}|{k.ar_norm}"


def _tam(deger: object, ad: str) -> int:
    if isinstance(deger, bool) or not isinstance(deger, int):
        raise GirdiHatasi(f"rnk json: {ad} tam sayi degil")
    return deger


def _metin(deger: object, ad: str) -> str:
    if not isinstance(deger, str):
        raise GirdiHatasi(f"rnk json: {ad} metin degil")
    return deger


def json_oku(veri: bytes) -> JsonBilgisi:
    """`json` baytlarindan meta ve on sirali dugum listesi (kok dahil)."""
    try:
        belge = kati_json(veri.decode("utf-8"))
    except UnicodeDecodeError:
        raise GirdiHatasi("rnk json: UTF-8 degil") from None
    if not isinstance(belge, dict):
        raise GirdiHatasi("rnk json: nesne degil")
    meta = belge.get("meta_data")
    kok = belge.get("contents")
    if not isinstance(meta, dict) or not isinstance(kok, dict):
        raise GirdiHatasi("rnk json: meta_data ve contents bekleniyor")
    dugumler: list[Dugum] = []

    def yuru(oge: object, derinlik: int, ust: int | None) -> None:
        if not isinstance(oge, dict):
            raise GirdiHatasi("rnk json: dugum nesne degil")
        baslik = _metin(oge.get("title", ""), "title")
        kitapta = _metin(oge.get("textInBook", ""), "textInBook")
        sira = len(dugumler)
        anahtarlar = frozenset(
            a for a in (baslik_anahtari(baslik), baslik_anahtari(kitapta)) if a != "|"
        )
        dugumler.append(
            Dugum(
                sira,
                baslik,
                kitapta,
                _tam(oge.get("pageNo"), "pageNo"),
                derinlik,
                ust,
                anahtarlar,
            )
        )
        cocuklar = oge.get("children", [])
        if not isinstance(cocuklar, list):
            raise GirdiHatasi("rnk json: children liste degil")
        for cocuk in cocuklar:
            yuru(cocuk, derinlik + 1, sira)

    yuru(kok, 0, None)
    return JsonBilgisi(
        uid=_metin(meta.get("uid"), "uid"),
        raf=_metin(meta.get("shelf_id"), "shelf_id"),
        ilk_sayfa=_tam(meta.get("first_page"), "first_page"),
        son_sayfa=_tam(meta.get("last_page"), "last_page"),
        dugumler=tuple(dugumler),
    )


@dataclass(frozen=True)
class BolumAgaci:
    """Her json dugumunun bolum yolu, baslik zinciri ve adlandirma sayilari.

    `yollar[j]`: dugumun slug yolu (kok `()`; daraltilan dugum ustunun yolunu tasir);
    `basliklar[j]`: kokten dugume gorunen baslik zinciri (kok ve daraltilan dugum yok);
    `istatistik`: `kalip_{tur}`, `baslik_turetilen`, `baslik_bos`, `kesildi_{40}`, `bolum_onekli`,
    `kardes_eki`, `daraltildi` sayaclari (metin tasimaz).
    """

    yollar: tuple[tuple[str, ...], ...]
    basliklar: tuple[tuple[str, ...], ...]
    istatistik: Counter[str]


def _baslik_slug(ad: str, istatistik: Counter[str]) -> str:
    """Kalip disi baslikta slug: `slug_turet`, en cok 40 karakter; gecersizse `bolum-` oneki."""
    try:
        tam = slug_turet(ad, kes=False)
    except RisaleHatasi:
        istatistik["baslik_bos"] += 1
        return "bolum"
    istatistik["baslik_turetilen"] += 1
    ham = tam[:MAKS_BOLUM_SLUG].rstrip("-")
    if len(tam) > MAKS_BOLUM_SLUG:
        istatistik[f"kesildi_{MAKS_BOLUM_SLUG}"] += 1
    if _kalip_disi_uygun(ham):
        return ham
    istatistik["bolum_onekli"] += 1
    onekli = (BOLUM_ONEKI + ham)[:MAKS_BOLUM_SLUG].rstrip("-")
    return onekli if _kalip_disi_uygun(onekli) else "bolum"


def _kalip_disi_uygun(ad: str) -> bool:
    """Gecerli bolum adi mi; kalip adlari (`soz-4`, `hasiye-3`, `parca-1`) ayrilmis kalir.

    `soz` gibi tur sozcugu de uygun degildir: kardes eki (`soz-2`) kalip adiyla karisirdi.
    """
    try:
        bolum_denetle(ad)
    except RisaleHatasi:
        return False
    return bolum_kalibi(ad) is None and bolum_kalibi(ad + "-2") is None


def _benzersiz(ham: str, kardesler: set[str]) -> tuple[str, bool]:
    """Kardes cakismasinda `-2`, `-3` ... eki (`kardes_slug`). `(ad, ek var mi)`."""
    ad = kardes_slug(ham, kardesler)
    return ad, ad != ham


def bolum_agaci(
    dugumler: tuple[Dugum, ...],
    *,
    parca_adi: Callable[[int], str] | None = None,
) -> BolumAgaci:
    """Bolum yollari, baslik zincirleri ve istatistik.

    Kardes adlari `(etkin ust, kitap parcasi)` anahtariyla tekil kalir (ayni bolum agacindaki uc
    kitap, ornegin Sunuhat/Tuluat/Isarat, birbirine `-2` eki yaptirmaz). `parca_adi(sayfa)` kitap
    slug'ini verir; verilirse ilk duzey dugum kitap slug'iyla ayni adi tasidiginda daraltilir.
    """
    istatistik: Counter[str] = Counter()
    yollar: list[tuple[str, ...]] = []
    basliklar: list[tuple[str, ...]] = []
    etkin: list[int] = []  # en yakin daraltilmamis atanin sirasi (kendisi dahil)
    kardesler: dict[tuple[int, str], set[str]] = {}
    for d in dugumler:
        if d.ust is None:
            yollar.append(())
            basliklar.append(())
            etkin.append(d.sira)
            continue
        gorunen = d.baslik or d.metin_kitapta
        parca = parca_adi(d.sayfa) if parca_adi is not None else ""
        kalip = baslik_bolum_adi(gorunen)
        if kalip is not None:
            ham = kalip
            kalip_turu = bolum_kalibi(kalip)
            assert kalip_turu is not None
            istatistik[f"kalip_{kalip_turu.tur}"] += 1
        else:
            ham = _baslik_slug(gorunen, istatistik)
        if d.ust == 0 and parca_adi is not None and kalip is None and ham == parca:
            istatistik["daraltildi"] += 1
            yollar.append(yollar[d.ust])
            basliklar.append(basliklar[d.ust])
            etkin.append(etkin[d.ust])
            continue
        mevcut = kardesler.setdefault((etkin[d.ust], parca), set())
        ad, ekli = _benzersiz(ham, mevcut)
        mevcut.add(ad)
        if ekli:
            istatistik["kardes_eki"] += 1
        yollar.append((*yollar[d.ust], ad))
        basliklar.append((*basliklar[d.ust], gorunen))
        etkin.append(d.sira)
    return BolumAgaci(tuple(yollar), tuple(basliklar), istatistik)


def bolum_yollari(
    dugumler: tuple[Dugum, ...], *, parca_adi: Callable[[int], str] | None = None
) -> list[tuple[str, ...]]:
    """Her dugumun bolum yolu (kok `()`); kardes cakismasi `-2` ekiyle cozulur."""
    return list(bolum_agaci(dugumler, parca_adi=parca_adi).yollar)


# ---------------------------------------------------------------------------
# Kitap donusumu


@dataclass
class KitapSonucu:
    birimler: list[StagedUnit]
    sayfalar: list[dict[str, object]]
    yapi: list[dict[str, object]]
    kitap: dict[str, object]
    uyarilar: Counter[str] = field(default_factory=Counter)
    rnk: KitapAyristirma | None = None


@dataclass(frozen=True)
class Parca:
    slug: str
    baslangic: int  # baslangic sayfasi (ilk parcada kullanilmaz)


def parcalar(kitaplar: list[Kitap]) -> tuple[list[Parca], int | None]:
    """Bir RNK dosyasina bagli kitap slug'lari: (parcalar, son sayfa); bolunme yoksa tek parca."""
    ilk = kitaplar[0]
    assert ilk.rnk is not None
    if ilk.rnk.bolunme is None:
        if len(kitaplar) != 1:
            raise GirdiHatasi("bolunmesiz RNK dosyasina birden cok kitap bagli")
        return [Parca(ilk.slug, 0)], None
    b = ilk.rnk.bolunme
    return [Parca(p.slug, p.baslangic_sayfasi) for p in b.parcalar], b.son_sayfa


def parca_sec(parca_listesi: list[Parca], sayfa: int | None) -> Parca:
    """Sayfaya gore kitap parcasi (bolunmede ilk satirin sayfasi; sayfa yoksa ilk parca)."""
    secilen = parca_listesi[0]
    for p in parca_listesi:
        if sayfa is not None and sayfa >= p.baslangic:
            secilen = p
    return secilen


def kitap_donustur(
    *,
    raf: str,
    uid: str,
    txt: bytes,
    json_veri: bytes,
    txt_sha256: str,
    kitaplar: list[Kitap],
) -> KitapSonucu:
    """Bir RNK dosyasini (txt + json) capali birimlere, sayfa ve yapi satirlarina cevirir."""
    dosya = f"{raf}/{uid}"
    a = ayristir(txt, raf)
    bilgi = json_oku(json_veri)
    if bilgi.uid != uid or bilgi.raf != raf:
        raise GirdiHatasi(f"{dosya}: json meta_data dosyayla uyusmuyor")
    parca_listesi, son_sayfa = parcalar(kitaplar)
    ilk_kitap = kitaplar[0]
    uyari: Counter[str] = Counter(a.uyarilar)

    sayfa_satirlari = [s.satir for s in a.sayfalar]
    sayfa_numaralari = [s.n for s in a.sayfalar]

    def sayfa_of(satir: int) -> int | None:
        i = bisect.bisect_right(sayfa_satirlari, satir) - 1
        return sayfa_numaralari[i] if i >= 0 else None

    def parca_of(sayfa: int | None) -> Parca:
        if len(parca_listesi) == 1:
            return parca_listesi[0]
        if sayfa is not None and son_sayfa is not None and sayfa > son_sayfa:
            uyari["bolunme_son_sayfa_asildi"] += 1
        return parca_sec(parca_listesi, sayfa)

    agac = bolum_agaci(bilgi.dugumler, parca_adi=lambda sayfa: parca_sec(parca_listesi, sayfa).slug)
    yollar = list(agac.yollar)
    dugumler = bilgi.dugumler

    # --- 1. gecis: bolum, parca, numara ------------------------------------------------
    n = len(a.birimler)
    parca_ad: list[str] = [""] * n
    bolum: list[tuple[str, ...]] = [()] * n
    bolum_dugumu: list[int] = [0] * n  # birimin bolumunun json dugumu (baslik zinciri icin)
    numara: list[int] = [0] * n  # paragraf: p{n}; hasiye: dipnot icindeki paragraf p{k}
    hasiye_no: dict[int, int] = {}  # birim sirasi -> bolumdeki hasiye sirasi (1 tabanli)
    dugum_of: dict[int, int] = {}
    sayac_p: Counter[tuple[str, tuple[str, ...]]] = Counter()
    sayac_h: Counter[tuple[str, tuple[str, ...]]] = Counter()
    suanki: tuple[str, ...] = ()
    suanki_dugum = 0
    ptr = 0
    eslesen_dugum = 0
    sayfa_uyumsuz = 0
    for b in a.birimler:
        sayfa = sayfa_of(b.ilk_satir)
        if b.tur == "hasiye":
            if b.ust is not None:
                ana = b.ust
                parca_ad[b.sira] = parca_ad[ana]
                bolum[b.sira] = bolum[ana]
                bolum_dugumu[b.sira] = bolum_dugumu[ana]
            else:
                parca_ad[b.sira] = parca_of(sayfa).slug
                bolum[b.sira] = suanki
                bolum_dugumu[b.sira] = suanki_dugum
            anahtar = (parca_ad[b.sira], bolum[b.sira])
            if b.ic_sira == 0:
                sayac_h[anahtar] += 1
                hasiye_no[b.sira] = sayac_h[anahtar]
            else:
                # ayni dipnotun onceki paragrafi ayni numarayi tasir
                hasiye_no[b.sira] = sayac_h[anahtar]
            numara[b.sira] = b.ic_sira + 1
            continue
        if b.tur == "baslik":
            secilen = _eslestir(dugumler, ptr, b.metin, sayfa)
            if secilen is not None:
                j, uyumlu = secilen
                ptr = j + 1
                suanki = yollar[j]
                suanki_dugum = j
                eslesen_dugum += 1
                dugum_of[b.sira] = j
                if not uyumlu:
                    sayfa_uyumsuz += 1
            else:
                uyari["baslik_eslesmedi"] += 1
        parca_ad[b.sira] = parca_of(sayfa).slug
        bolum[b.sira] = suanki
        bolum_dugumu[b.sira] = suanki_dugum
        anahtar = (parca_ad[b.sira], suanki)
        sayac_p[anahtar] += 1
        numara[b.sira] = sayac_p[anahtar]
    if sayfa_uyumsuz:
        uyari["baslik_sayfa_uyumsuz"] += sayfa_uyumsuz

    # --- 2. gecis: capalar ----------------------------------------------------------------
    capalar: list[str] = [""] * n
    for b in a.birimler:
        slug, yol = parca_ad[b.sira], bolum[b.sira]
        try:
            if b.tur == "hasiye":
                capalar[b.sira] = rn_capa(
                    hasiye_yolu((slug, *yol), hasiye_no[b.sira]), numara[b.sira]
                )
            else:
                capalar[b.sira] = rn_capa((slug, *yol), numara[b.sira])
        except (RisaleHatasi, ValueError) as hata:
            raise GirdiHatasi(f"{dosya}: birim {b.sira}: capa uretilemedi ({hata})") from None

    # --- 3. gecis: StagedUnit ---------------------------------------------------------------
    dil = ilk_kitap.dil
    yon = ilk_kitap.yon
    birimler: list[StagedUnit] = []
    for b in a.birimler:
        sayfa = sayfa_of(b.ilk_satir)
        attrs: dict[str, object] = {
            "kind": b.tur,
            "slug": parca_ad[b.sira],
            "bolum_yolu": list(bolum[b.sira]),
            "p": numara[b.sira],
            "baslik_yolu": list(agac.basliklar[bolum_dugumu[b.sira]]),
            "dil": dil,
            "yon": yon,
            "marks": _isaretler(b, capalar),
        }
        if sayfa is not None:
            attrs["sayfa"] = sayfa
        if b.tur == "baslik":
            attrs["baslik_isareti"] = b.ozellik.get("baslik_isareti")
            dugum_sirasi = dugum_of.get(b.sira)
            if dugum_sirasi is not None:
                attrs["baslik_duzeyi"] = dugumler[dugum_sirasi].derinlik
                attrs["json_dugum"] = {"sira": dugum_sirasi, "pageNo": dugumler[dugum_sirasi].sayfa}
            else:
                attrs["baslik_duzeysiz"] = True
        if b.tur == "hasiye":
            attrs["hasiye_no"] = hasiye_no[b.sira]
            attrs["etiket_bicimi"] = b.ozellik.get("etiket_bicimi")
        if b.ozellik.get("girintisiz"):
            attrs["girintisiz"] = True
        birimler.append(
            StagedUnit(
                anchor=capalar[b.sira],
                text=b.metin,
                attrs=attrs,
                provenance={
                    "kaynak": "rnk",
                    "file": f"{dosya}.txt",
                    "sha256": txt_sha256,
                    "raf": raf,
                    "uid": uid,
                    "konum": {
                        "satir": [b.ilk_satir, b.son_satir],
                        "segmentler": b.segmentler,
                    },
                    "cikarici": {"surum": AYRISTIRICI_SURUMU},
                },
            )
        )

    sayfalar: list[dict[str, object]] = []
    for s in a.sayfalar:
        kayit: dict[str, object] = {"dosya": dosya, "n": s.n, "satir": s.satir}
        if s.birim is not None:
            kayit["capa"] = capalar[s.birim]
            kayit["ofs"] = s.ofs
            kayit["tur"] = "bas" if s.ofs == 0 else "ortasi"
        else:
            kayit["capa"] = None
            kayit["ofs"] = 0
            kayit["tur"] = "icerik-yok"
        sayfalar.append(kayit)
    yapi: list[dict[str, object]] = [{"dosya": dosya, "no": no, "ham": ham} for no, ham in a.yapi]
    sayac_tur = Counter(b.tur for b in a.birimler)
    kitap: dict[str, object] = {
        "dosya": dosya,
        "raf": raf,
        "uid": uid,
        "slug": [p.slug for p in parca_listesi],
        "satir_sayisi": a.satir_sayisi,
        "bom": a.bom,
        "cr_satir": a.cr_satir,
        "cr_son": a.cr_son,
        "son_lf": a.son_lf,
        "sayfa_sayisi": len(a.sayfalar),
        "ilk_sayfa": sayfa_numaralari[0] if sayfa_numaralari else None,
        "son_sayfa": sayfa_numaralari[-1] if sayfa_numaralari else None,
        "json_ilk_sayfa": bilgi.ilk_sayfa,
        "json_son_sayfa": bilgi.son_sayfa,
        "birim": {t: sayac_tur.get(t, 0) for t in ("baslik", "paragraf", "hasiye")},
        "json_dugum": len(dugumler),
        "json_eslesen": eslesen_dugum,
        "bolum_adlari": dict(sorted(agac.istatistik.items())),
        "ayristirici": AYRISTIRICI_SURUMU,
        "uyarilar": dict(sorted(uyari.items())),
    }
    return KitapSonucu(birimler, sayfalar, yapi, kitap, uyari, a)


def _eslestir(
    dugumler: tuple[Dugum, ...], ptr: int, metin: str, sayfa: int | None
) -> tuple[int, bool] | None:
    """Baslik satirini ileri dogru ilk uygun json dugumune eslestirir: (dugum, sayfa uyumlu mu)."""
    anahtar = baslik_anahtari(metin)
    ilk_metin: int | None = None
    for j in range(ptr, min(len(dugumler), ptr + ESLESME_PENCERESI)):
        d = dugumler[j]
        if anahtar in d.anahtarlar:
            if d.sayfa == sayfa:
                return j, True
            if ilk_metin is None:
                ilk_metin = j
    if ilk_metin is not None and ilk_metin - ptr <= SAYFA_UYUMSUZ_PENCERE:
        return ilk_metin, False
    return None


def _isaretler(b: Birim, capalar: list[str]) -> list[dict[str, object]]:
    """`marks`: hasiye ek noktasi `h` (birim sirasi) yerine dipnotun ilk paragraf capasini alir."""
    sonuc: list[dict[str, object]] = []
    for m in b.isaretler:
        if m.get("t") == "hasiye":
            h = m["h"]
            assert isinstance(h, int)
            sonuc.append({"t": "hasiye", "s": m["s"], "a": capalar[h]})
        else:
            sonuc.append(m)
    return sonuc
