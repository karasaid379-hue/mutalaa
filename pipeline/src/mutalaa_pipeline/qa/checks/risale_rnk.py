"""RNK metin QA kapilari (A20.1b, K-51 madde 2 ve 5): G-KAY, G-BUT, G-NOR (`risale-rnk-metin`).

Kapi islevleri bellekteki `RnkGirdisi` uzerinde calisir; yukleyici `girdi_yukle` staged klasorunu
ve ham dosyalari okur. Bulgular ASCII ve kisadir: yalniz dosya (`raf/uid`), capa, sayi ve alan
adi tasir, metin asla.

* G-KAY: kaynak kaydi gecerli (`slug`, `tur = risale`, `surum`, `kaynak_url`, `atif_metni` dolu);
  ingest manifestindeki kilit ozeti paketteki `risale_rnk.lock.json` ozetiyle ayni.
* G-BUT: ham dosya boyut, SHA-256 ve MD5 kilitle ayni; kilit sayilari (satir, `#n`, baslik
  satiri, her isaret karakteri, denetlenen karakterler, BOM, CR, NFC olmayan satir) ham dosyadan
  yeniden sayilinca ayni (kilit disi karakter ya da sayi farki kapiyi kaldirir); `#n` sirasi +1 ve
  ilk/son sayfa json meta ile ayni; `<&€∑` satir sayisi baslik birimi sayisiyla ayni; birim metni
  isaret karakteri, BOM ya da CR tasimaz ve bos degildir; her metin karakteri bir kaynak
  segmentine ya da birlestirme bosluguna (`t: "satir"`) aittir; birim metni + isaretler + yapi
  ile kaynak dosya BAYT BAYT yeniden kurulur; dipnot ek noktalari ve sayfa konumlari gecerli
  capaya isaret eder.
* G-NOR: normalizasyon vektorleri gecer; Osmanlica ve Arapca birimlerde yalniz `ar_norm` vardir
  (`tr_*` bos), `ar_norm` metinden `normalize_ar` ile yeniden uretilince ayni (ingest asamasinda
  alan yoksa yalniz uretilebilirlik denetlenir).
"""

import hashlib
import unicodedata
from collections import Counter, defaultdict
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path
from typing import Final

from mutalaa_pipeline import lineage
from mutalaa_pipeline.anchor.risale import Kitap
from mutalaa_pipeline.enums import SourceKind
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.ingest.risale_rnk import (
    ISARETLER,
    S12_KUMESI,
    yeniden_kur,
)
from mutalaa_pipeline.ingest.risale_rnk_kilit import (
    KAYNAK,
    RnkKilidi,
    kilit_ozeti,
    kitap_istatistigi,
)
from mutalaa_pipeline.normalize import normalize_ar
from mutalaa_pipeline.qa.checks.tanzil import KapiSonucu
from mutalaa_pipeline.qa.vektorler import vektorleri_calistir
from mutalaa_pipeline.sources.kayit import Kaynak
from mutalaa_pipeline.staged import satirlari_oku

RNK_KAPILARI: Final = ("G-KAY", "G-BUT", "G-NOR")
YER_TUTUCU: Final = "{surum}"
EN_COK_ORNEK: Final = 5
ISTATISTIK_ALANLARI: Final = (
    "satir_sayisi",
    "bom",
    "cr_satir",
    "cr_son",
    "son_lf",
    "nfc_olmayan_satir",
    "sayfa_sayisi",
    "ilk_sayfa",
    "son_sayfa",
    "baslik_satiri",
    "boyut_txt",
    "boyut_json",
    "sha256_txt",
    "sha256_json",
    "md5_txt",
    "md5_json",
)

Satir = dict[str, object]


@dataclass
class RnkGirdisi:
    kayit: Kaynak
    kilit: RnkKilidi
    kilit_ozeti_manifest: str | None  # ingest manifestindeki kilit ozeti
    ham: Mapping[str, bytes]  # "tr/sozler.txt" ve "tr/sozler.json" -> bayt
    birimler: Sequence[Satir]  # units.jsonl satirlari
    sayfalar: Sequence[Satir]
    yapi: Sequence[Satir]
    kitaplar: Sequence[Satir]  # kitaplar.jsonl
    tablo: tuple[Kitap, ...]
    depo_kok: Path


def girdi_yukle(klasor: Path) -> tuple[list[Satir], list[Satir], list[Satir], list[Satir]]:
    """`staged/{kaynak}/{run}` klasorundeki (birimler, sayfalar, yapi, kitaplar) satirlari."""
    sonuc: list[list[Satir]] = []
    for ad in ("units.jsonl", "sayfalar.jsonl", "yapi.jsonl", "kitaplar.jsonl"):
        try:
            veri = (klasor / ad).read_bytes()
        except OSError:
            raise GirdiHatasi(f"staged {ad} okunamadi") from None
        sonuc.append([s.veri for s in satirlari_oku(veri, ad)])
    return sonuc[0], sonuc[1], sonuc[2], sonuc[3]


def _bulgu(bulgular: list[str], ad: str, liste: Sequence[str], neden: str) -> None:
    if liste:
        ornek = ", ".join(liste[:EN_COK_ORNEK])
        bulgular.append(f"{ad}: {len(liste)} {neden} (ornek: {ornek})")


def _tam(deger: object) -> int:
    if isinstance(deger, bool) or not isinstance(deger, int):
        raise GirdiHatasi("staged satir: tam sayi bekleniyor")
    return deger


def _metin(deger: object) -> str:
    if not isinstance(deger, str):
        raise GirdiHatasi("staged satir: metin bekleniyor")
    return deger


def _nesne(deger: object) -> dict[str, object]:
    if not isinstance(deger, dict):
        raise GirdiHatasi("staged satir: nesne bekleniyor")
    return deger


def _liste(deger: object) -> list[object]:
    if not isinstance(deger, list):
        raise GirdiHatasi("staged satir: liste bekleniyor")
    return deger


# --- G-KAY -------------------------------------------------------------------------------


def g_kay(g: RnkGirdisi) -> KapiSonucu:
    bulgular: list[str] = []
    k = g.kayit
    if k.slug != KAYNAK:
        bulgular.append("kaynak kaydi: slug kaynak kimligiyle ayni degil")
    if k.tur is not SourceKind.RISALE:
        bulgular.append("kaynak kaydi: tur risale olmali")
    if k.surum is None or k.surum == "":
        bulgular.append("kaynak kaydi: surum yok")
    if k.kaynak_url is None:
        bulgular.append("kaynak kaydi: kaynak_url yok")
    if YER_TUTUCU in k.atif_metni or k.atif_metni.strip(" \t\n") == "":
        bulgular.append("kaynak kaydi: atif_metni bos ya da {surum} yer tutucusu tasiyor")
    if g.kilit_ozeti_manifest is None:
        bulgular.append("ingest manifestinde kilit ozeti yok (once ingest --force)")
    elif g.kilit_ozeti_manifest != kilit_ozeti(g.kilit):
        bulgular.append("ingest eski bir kilitle alinmis: kilit ozeti paketteki kilitle ayni degil")
    return KapiSonucu("G-KAY", tuple(bulgular), {"kayit": 1})


# --- G-BUT -------------------------------------------------------------------------------


def _ham_denetimi(g: RnkGirdisi, bulgular: list[str]) -> int:
    """Ham dosyalarin boyut, SHA-256, MD5 ve kilit sayilari; denetlenen dosya sayisi."""
    kilit_disi: list[str] = []
    for ad, kitap in g.kilit.kitaplar.items():
        txt = g.ham.get(f"{ad}.txt")
        js = g.ham.get(f"{ad}.json")
        if txt is None or js is None:
            bulgular.append(f"{ad}: ham dosya yok")
            continue
        if (
            lineage.sha256_bayt(txt) != kitap.metin("sha256_txt")
            or lineage.sha256_bayt(js) != kitap.metin("sha256_json")
            or hashlib.md5(txt, usedforsecurity=False).hexdigest() != kitap.metin("md5_txt")
            or hashlib.md5(js, usedforsecurity=False).hexdigest() != kitap.metin("md5_json")
        ):
            bulgular.append(f"{ad}: ham dosya ozeti kilitle tutmuyor")
            continue
        sayilan = kitap_istatistigi(txt, js)
        farkli = [a for a in ISTATISTIK_ALANLARI if sayilan[a] != kitap.veri[a]]
        for alan in ("isaretler", "karakterler"):
            beklenen = kitap.sayilar(alan)
            bulunan = sayilan[alan]
            assert isinstance(bulunan, dict)
            for anahtar in sorted(set(beklenen) | set(bulunan)):
                if beklenen.get(anahtar, 0) != bulunan.get(anahtar, 0):
                    farkli.append(f"{alan}[{anahtar}]")
        if sayilan["ozel_kullanim"] != kitap.veri["ozel_kullanim"]:
            farkli.append("ozel_kullanim")
        if farkli:
            bulgular.append(f"{ad}: kilit sayilari ham dosyayla tutmuyor: {', '.join(farkli[:8])}")
        for kod in kitap.sayilar("karakterler"):
            if int(kod[2:], 16) not in S12_KUMESI:
                kilit_disi.append(f"{ad}:{kod}")
    _bulgu(bulgular, "karakter kurali", kilit_disi, "kilitte S12 kumesi disinda karakter")
    return len(g.kilit.kitaplar)


def _sayfa_denetimi(g: RnkGirdisi, bulgular: list[str]) -> None:
    sayfalar: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for s in g.sayfalar:
        sayfalar[_metin(s["dosya"])].append((_tam(s["satir"]), _tam(s["n"])))
    kitap_satirlari = {_metin(k["dosya"]): k for k in g.kitaplar}
    bozuk: list[str] = []
    for ad, kitap in g.kilit.kitaplar.items():
        sirali = [n for _, n in sorted(sayfalar.get(ad, []))]
        k = kitap_satirlari.get(ad)
        if k is None:
            bulgular.append(f"{ad}: kitaplar.jsonl satiri yok")
            continue
        artis = all(b - a == 1 for a, b in pairwise(sirali))
        if not sirali or not artis:
            bozuk.append(f"{ad}:siralama")
        elif sirali[0] != k["json_ilk_sayfa"] or sirali[-1] != k["json_son_sayfa"]:
            bozuk.append(f"{ad}:json_meta")
        elif sirali[0] != kitap.sayi("ilk_sayfa") or sirali[-1] != kitap.sayi("son_sayfa"):
            bozuk.append(f"{ad}:kilit")
        if len(sirali) != kitap.sayi("sayfa_sayisi"):
            bozuk.append(f"{ad}:sayi")
        baslik = _nesne(k["birim"]).get("baslik")
        if baslik != kitap.sayi("baslik_satiri"):
            bozuk.append(f"{ad}:baslik_sayisi")
    _bulgu(bulgular, "sayfa ve baslik sayilari", bozuk, "dosyada tutarsizlik")


def _birim_denetimi(g: RnkGirdisi, bulgular: list[str]) -> dict[str, int]:
    """Birim metni, segment kapsami, dipnot ve sayfa baglantilari."""
    capalar: dict[str, int] = {}
    for b in g.birimler:
        capalar[_metin(b["anchor"])] = len(_metin(b["text"]))
    bos: list[str] = []
    isaretli: list[str] = []
    kapsamsiz: list[str] = []
    dipnot: list[str] = []
    for b in g.birimler:
        capa = _metin(b["anchor"])
        metin = _metin(b["text"])
        attrs = _nesne(b["attrs"])
        if metin == "":
            bos.append(capa)
        if any(c in ISARETLER for c in metin) or "﻿" in metin or "\r" in metin:
            isaretli.append(capa)
        konum = _nesne(_nesne(b["provenance"])["konum"])
        kapsanan = bytearray(len(metin))
        for segment in _liste(konum["segmentler"]):
            _, _, bas, bit = (_tam(v) for v in _liste(segment))
            for i in range(bas, bit):
                kapsanan[i] += 1
        for m in _liste(attrs["marks"]):
            isaret = _nesne(m)
            if isaret.get("t") == "satir":
                for i in range(_tam(isaret["s"]), _tam(isaret["e"])):
                    kapsanan[i] += 1
            elif isaret.get("t") == "hasiye":
                hedef = _metin(isaret["a"])
                if hedef not in capalar or not 0 <= _tam(isaret["s"]) <= len(metin):
                    dipnot.append(capa)
        if any(v != 1 for v in kapsanan):
            kapsamsiz.append(capa)
    sayfa_hatasi: list[str] = []
    for s in g.sayfalar:
        hedef_capa = s.get("capa")
        if hedef_capa is None:
            continue
        uzunluk = capalar.get(_metin(hedef_capa))
        if uzunluk is None or not 0 <= _tam(s["ofs"]) <= uzunluk:
            sayfa_hatasi.append(f"{_metin(s['dosya'])}#{_tam(s['n'])}")
    _bulgu(bulgular, "bos birim", bos, "birimin metni bos")
    _bulgu(
        bulgular, "isaret karakteri", isaretli, "birim metninde isaret karakteri ya da BOM/CR var"
    )
    _bulgu(bulgular, "segment kapsami", kapsamsiz, "birimde metin karakteri kaynakla eslesmiyor")
    _bulgu(bulgular, "dipnot ek noktasi", dipnot, "birimde dipnot baglantisi gecersiz")
    _bulgu(bulgular, "sayfa konumu", sayfa_hatasi, "sayfa kaydi gecersiz birime ya da ofsete bagli")
    return {"bos": len(bos), "isaretli": len(isaretli), "kapsamsiz": len(kapsamsiz)}


def _yeniden_kurma(g: RnkGirdisi, bulgular: list[str]) -> int:
    """Her kaynak dosya birim metni, isaretler ve yapi satirlarindan bayt bayt yeniden kurulur."""
    birim_grup: dict[str, list[dict[str, object]]] = defaultdict(list)
    for b in g.birimler:
        saglayici = _nesne(b["provenance"])
        dosya = _metin(saglayici["file"]).removesuffix(".txt")
        birim_grup[dosya].append(
            {
                "text": b["text"],
                "marks": _nesne(b["attrs"])["marks"],
                "segmentler": _nesne(saglayici["konum"])["segmentler"],
            }
        )
    sayfalar: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for s in g.sayfalar:
        sayfalar[_metin(s["dosya"])].append((_tam(s["n"]), _tam(s["satir"])))
    yapi: dict[str, list[tuple[int, str]]] = defaultdict(list)
    for y in g.yapi:
        yapi[_metin(y["dosya"])].append((_tam(y["no"]), _metin(y["ham"])))
    kitap_satirlari = {_metin(k["dosya"]): k for k in g.kitaplar}
    tutmayan: list[str] = []
    for ad in g.kilit.kitaplar:
        k = kitap_satirlari.get(ad)
        txt = g.ham.get(f"{ad}.txt")
        if k is None or txt is None:
            tutmayan.append(ad)
            continue
        kurulan = yeniden_kur(
            birimler=birim_grup.get(ad, []),
            sayfalar=sayfalar.get(ad, []),
            yapi=yapi.get(ad, []),
            satir_sayisi=_tam(k["satir_sayisi"]),
            bom=bool(k["bom"]),
            cr_satir=_tam(k["cr_satir"]),
            cr_son=bool(k["cr_son"]),
            son_lf=bool(k["son_lf"]),
        )
        if kurulan != txt:
            tutmayan.append(ad)
    _bulgu(bulgular, "yeniden kurma", tutmayan, "dosya kaynakla bayt bayt ayni kurulamadi")
    return len(g.kilit.kitaplar) - len(tutmayan)


def g_but(g: RnkGirdisi) -> KapiSonucu:
    bulgular: list[str] = []
    dosya = _ham_denetimi(g, bulgular)
    _sayfa_denetimi(g, bulgular)
    ayrinti = _birim_denetimi(g, bulgular)
    kurulan = _yeniden_kurma(g, bulgular)
    toplam = sum(
        _tam(_nesne(k["birim"])[t]) for k in g.kitaplar for t in ("baslik", "paragraf", "hasiye")
    )
    if toplam != len(g.birimler):
        bulgular.append(f"birim sayisi {len(g.birimler)}, kitaplar.jsonl toplami {toplam}")
    beklenen = {f"{r}/{u}" for (r, u) in {(k.rnk.raf, k.rnk.uid) for k in g.tablo if k.rnk}}
    if set(g.kilit.kitaplar) != beklenen:
        bulgular.append("kilit dosya kumesi kitap tablosuyla ayni degil")
    sayilar = {
        "dosya": dosya,
        "yeniden_kurulan": kurulan,
        "birim": len(g.birimler),
        "sayfa": len(g.sayfalar),
        **ayrinti,
    }
    return KapiSonucu("G-BUT", tuple(bulgular), sayilar)


# --- G-NOR -------------------------------------------------------------------------------

TR_ALANLARI: Final = ("tr_narrow", "tr_wide", "tr_stem")


def _arapca_harf_var(metin: str) -> bool:
    return any("؀" <= c <= "ۿ" and unicodedata.category(c).startswith("L") for c in metin)


def g_nor(g: RnkGirdisi) -> KapiSonucu:
    bulgular: list[str] = []
    vektor = vektorleri_calistir(g.depo_kok)
    if vektor.kalan:
        bulgular.append(f"normalizasyon vektoru: {len(vektor.kalan)}/{vektor.toplam} kaldi")
    if vektor.hizasiz:
        bulgular.append(f"tr_wide/tr_stem sozcuk hizasi: {len(vektor.hizasiz)} vektor")
    tr_dolu: list[str] = []
    farkli: list[str] = []
    bos_anahtar: list[str] = []
    kontrol = 0
    sayac: Counter[str] = Counter()
    for b in g.birimler:
        attrs = _nesne(b["attrs"])
        dil = attrs.get("dil")
        sayac[str(dil)] += 1
        if dil not in ("ota", "ar"):
            continue
        capa = _metin(b["anchor"])
        metin = _metin(b["text"])
        if any(b.get(a) is not None for a in TR_ALANLARI):
            tr_dolu.append(capa)
        uretilen = normalize_ar(metin)
        if _arapca_harf_var(metin) and uretilen == "":
            bos_anahtar.append(capa)
        if "ar_norm" in b and b["ar_norm"] is not None:
            kontrol += 1
            if b["ar_norm"] != uretilen:
                farkli.append(capa)
    _bulgu(
        bulgular, "tr_* anahtari", tr_dolu, "Osmanlica/Arapca birimde tr_* dolu (yalniz ar_norm)"
    )
    _bulgu(bulgular, "ar_norm", farkli, "metinden normalize_ar ile uretilen degerle ayni degil")
    _bulgu(bulgular, "ar_norm", bos_anahtar, "Arapca harfli birimde ar_norm uretilemedi")
    sayilar = {
        "vektor": vektor.toplam,
        "vektor_kalan": len(vektor.kalan),
        "ar_norm_denetlenen": kontrol,
        "ota_ar_birim": sayac["ota"] + sayac["ar"],
    }
    return KapiSonucu("G-NOR", tuple(bulgular), sayilar)


KAPI_ISLEVLERI: Final[dict[str, Callable[[RnkGirdisi], KapiSonucu]]] = {
    "G-KAY": g_kay,
    "G-BUT": g_but,
    "G-NOR": g_nor,
}

__all__ = ["KAPI_ISLEVLERI", "RNK_KAPILARI", "RnkGirdisi", "girdi_yukle"]
