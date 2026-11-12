"""RNK ayristirmasindan capali `StagedUnit` uretimi (A20.1b, K-51 madde 2, 3 ve 6).

`risale_rnk.ayristir` kitap dosyasini ham birimlere boler; bu modul onlara `rn:` capasi verir:

* **Bolum agaci** RNK `json` icindekilerindendir (`contents`). Baslik satirlari (`<&€∑`) json
  dugumleriyle `title`/`textInBook` normalize eslesmesi ve `pageNo` ile eslesir; eslesen baslik
  o bolumun `p1` birimidir ve bolumun adi dugum adindan turetilir (`slug_turet`, kardes
  cakismasinda `-2`). Eslesmeyen baslik satiri duzeysiz baslik olarak o anki bolumde kalir
  (uyari). Ilk eslesmeden onceki birimler kitap kokundedir (`rn:{kitap}:p{n}`).
* **Paragraf** numarasi `p{n}` bolum basina 1'den artar (okuma sirasi). Dipnot `hasiye-{n}`
  bolumudur (`rn:{kitap}:{bolum}:hasiye-{n}:p{k}`; `n` bolumdeki sira, `k` dipnot ici paragraf);
  ana paragrafta `t: "hasiye"` isareti `a` ile dipnotun ilk paragraf capasini gosterir.
* **Bolunme** (`risale-kitaplar.json` `rnk.bolunme`, ornek `tr_k/sunuhat`): bir RNK dosyasi
  birden cok kitap slug'ina bolunur; birim, ilk satirinin sayfasina gore parcaya gider. Sayfa
  isaretleri hicbir birimi bolmez; sayfa listesi RNK dosyasi (uid) duzeyinde kalir.

Bolum adlari json basligindan turetilir (siralamali `soz-10` kalibi degil); kalip adlandirma ve
slug dogrulamasi A20.2b ve I-24'e aittir. Metin degismez; `attrs.marks` isaretleri tasir.
"""

import bisect
from collections import Counter
from dataclasses import dataclass, field
from typing import Final

from mutalaa_pipeline.anchor.risale import (
    Kitap,
    RisaleHatasi,
    hasiye_yolu,
    kardes_slug,
    rn_capa,
    slug_denetle,
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


def _bolum_slug(dugum: Dugum, kardesler: set[str]) -> str:
    ad = dugum.baslik or dugum.metin_kitapta
    try:
        ham = slug_turet(ad, kes=False)[:MAKS_BOLUM_SLUG].rstrip("-")
    except RisaleHatasi:
        ham = "bolum"
    try:
        slug_denetle(ham)
    except RisaleHatasi:
        try:
            ham = slug_denetle((BOLUM_ONEKI + ham)[:MAKS_BOLUM_SLUG].rstrip("-"))
        except RisaleHatasi:
            ham = "bolum"
    sonuc = kardes_slug(ham, kardesler)
    kardesler.add(sonuc)
    return sonuc


def bolum_yollari(dugumler: tuple[Dugum, ...]) -> list[tuple[str, ...]]:
    """Her dugumun bolum yolu (kok `()`); kardes cakismasi `-2` ekiyle cozulur."""
    yollar: list[tuple[str, ...]] = []
    kardesler: dict[int, set[str]] = {}
    for d in dugumler:
        if d.ust is None:
            yollar.append(())
            continue
        ad = _bolum_slug(d, kardesler.setdefault(d.ust, set()))
        yollar.append((*yollar[d.ust], ad))
    return yollar


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
        secilen = parca_listesi[0]
        for p in parca_listesi:
            if sayfa is not None and sayfa >= p.baslangic:
                secilen = p
        if sayfa is not None and son_sayfa is not None and sayfa > son_sayfa:
            uyari["bolunme_son_sayfa_asildi"] += 1
        return secilen

    yollar = bolum_yollari(bilgi.dugumler)
    dugumler = bilgi.dugumler

    # --- 1. gecis: bolum, parca, numara ------------------------------------------------
    n = len(a.birimler)
    parca_ad: list[str] = [""] * n
    bolum: list[tuple[str, ...]] = [()] * n
    numara: list[int] = [0] * n  # paragraf: p{n}; hasiye: dipnot icindeki paragraf p{k}
    hasiye_no: dict[int, int] = {}  # birim sirasi -> bolumdeki hasiye sirasi (1 tabanli)
    dugum_of: dict[int, int] = {}
    sayac_p: Counter[tuple[str, tuple[str, ...]]] = Counter()
    sayac_h: Counter[tuple[str, tuple[str, ...]]] = Counter()
    suanki: tuple[str, ...] = ()
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
            else:
                parca_ad[b.sira] = parca_of(sayfa).slug
                bolum[b.sira] = suanki
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
                eslesen_dugum += 1
                dugum_of[b.sira] = j
                if not uyumlu:
                    sayfa_uyumsuz += 1
            else:
                uyari["baslik_eslesmedi"] += 1
        parca_ad[b.sira] = parca_of(sayfa).slug
        bolum[b.sira] = suanki
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
