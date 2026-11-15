"""RNK metin QA kapilari (A20.1b, A20.2b; K-52): G-KAY, G-BUT, G-CAP, G-NOR (`risale-rnk-metin`).

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
* G-CAP (anchor ciktisi; A20.2b): capa gramere uyar, kanoniktir ve tekildir; `rn:` capasi
  `anchor/risale.py` dogrulayicisindan gecer (slug, derinlik, kalip) ve kitabi tabloda vardir;
  oz yinelenen capa yok (ilk bolum adi kitap slug'iyla ayni degil); paket
  kimligi `risale-{kitap}` ve `risale-dizin` degil; `parent_path`, `kind`, `role`, `ord` (kitap
  icinde 1..N okuma sirasi), `data_version`, `metin_durumu` capayla ve kayitla tutarli;
  `content_hash` metnin SHA-256'si; `marks` ve `sentences` araliklari yari acik ve metne sigar,
  cumle sinirlari ayiriciyla yeniden uretilince ayni ve `ar` isaretinde bolunmez; onceki
  (kapilari gecmis) anchor calismasindaki her capa durur ve ayni `content_hash`i tasir (onceki
  calisma yoksa atlanir; kaynak kilidi degistiyse yalniz `content_hash` farki kabul edilir).
* G-NOR: normalizasyon vektorleri gecer; Turkce kitapta `tr_narrow`, `tr_wide`, `tr_stem` dolu ve
  `search_keys` ile yeniden uretilince ayni; Osmanlica ve Arapca birimlerde yalniz `ar_norm` vardir
  (`tr_*` bos), `ar_norm` metinden `normalize_ar` ile yeniden uretilince ayni ve Arapca harfli
  birimde bos degil (anchor ciktisi yoksa yalniz ingest birimlerinde uretilebilirlik denetlenir).
"""

import hashlib
import unicodedata
from collections import Counter, defaultdict
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path
from typing import Final

from mutalaa_pipeline import lineage
from mutalaa_pipeline.adimlar.risale import (
    ANCHOR_ALANLARI,
    KIND,
    METIN_DURUMU,
    ROLLER,
    cumle_araliklari,
    hasiye_bolumu_mu,
    ord_anahtari_degerleri,
    parent_yolu,
    rn_yolu,
)
from mutalaa_pipeline.anchor import SortKey, content_hash, parse, sort_key
from mutalaa_pipeline.anchor.cumle import CUMLE_SURUMU
from mutalaa_pipeline.anchor.risale import DIZIN, DIZIN_PAKETI, PAKET_ONEKI, Kitap, paket_kimligi
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
from mutalaa_pipeline.normalize import NORMALIZER_VERSION, normalize_ar, search_keys
from mutalaa_pipeline.qa.checks.tanzil import KapiSonucu, Onceki
from mutalaa_pipeline.qa.vektorler import vektorleri_calistir
from mutalaa_pipeline.sources.kayit import Kaynak
from mutalaa_pipeline.staged import satirlari_oku

RNK_KAPILARI: Final = ("G-KAY", "G-BUT", "G-CAP", "G-NOR")
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
    # anchor ciktisi (A20.2b): her cagrida yeni bir satir akisi; yoksa G-CAP ve G-NOR'un anchor
    # denetimleri kosulamaz (G-CAP kalir). Bellek icin liste degil akistir.
    anchor: Callable[[], Iterator[Satir]] | None = None
    onceki: Onceki | None = None  # G-CAP tabani (kapilari gecmis onceki anchor calismasi)
    onceki_kilit_ozeti: str | None = None  # o calismanin ingest'indeki kilit ozeti
    # Ayristirici surumu (ingest manifesti): kilit ayni kalsa da ayristirici duzeltilince
    # metin (ve content_hash) degisebilir; surum degisimi kayit altina alinir.
    ayristirici_surumu: str | None = None
    onceki_ayristirici_surumu: str | None = None


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


# --- G-CAP -------------------------------------------------------------------------------


def _oz_yineleme(yol: Sequence[str]) -> bool:
    """Ilk bolum kitap slug'iyla ayni mi (`rn:tuluat:tuluat:p1`); bu duzey daraltilmalidir."""
    return len(yol) > 1 and yol[1] == yol[0]


def _araliklar_gecerli(deger: object, uzunluk: int) -> bool:
    """`[[bas, son], ...]`: tam sayi, `0 <= bas < son <= uzunluk`, artan ve ayrik (yari acik)."""
    if not isinstance(deger, list):
        return False
    onceki_son = 0
    for oge in deger:
        if (
            not isinstance(oge, list)
            or len(oge) != 2
            or any(isinstance(v, bool) or not isinstance(v, int) for v in oge)
        ):
            return False
        bas, son = oge
        if not 0 <= bas < son <= uzunluk or bas < onceki_son:
            return False
        onceki_son = son
    return True


def _isaretler_gecerli(marks: Sequence[object], uzunluk: int) -> bool:
    """Her isaret `t` ve tam sayi `s` tasir; `e` varsa `0 <= s <= e <= uzunluk` (yari acik)."""
    for m in marks:
        if not isinstance(m, dict) or not isinstance(m.get("t"), str):
            return False
        bas = m.get("s")
        son = m.get("e", bas)
        if (
            isinstance(bas, bool)
            or isinstance(son, bool)
            or not isinstance(bas, int)
            or not isinstance(son, int)
            or not 0 <= bas <= son <= uzunluk
        ):
            return False
    return True


def _ar_icinde_boler(sentences: Sequence[object], marks: Sequence[object]) -> bool:
    """Ardisik iki cumle arasindaki sinir bir `ar` isaretli araligin icine dusuyor mu.

    Sinir, bir onceki cumlenin bitisi ile sonrakinin baslangicidir; aralik ikisini de kapsiyorsa
    cumle `ar` isaretinde bolunmustur. Son cumlenin sondaki bosluk kirpmasi bolme sayilmaz.
    """
    araliklar = [
        (_tam(m["s"]), _tam(m["e"]))
        for m in marks
        if isinstance(m, dict) and m.get("t") == "ar" and "e" in m
    ]
    sinirlar = [(_tam(_liste(a)[1]), _tam(_liste(b)[0])) for a, b in pairwise(sentences)]
    return any(bas < son and sonraki < bit for son, sonraki in sinirlar for bas, bit in araliklar)


def _hash_bicimi(ozet: str) -> bool:
    return len(ozet) == 64 and all(c in "0123456789abcdef" for c in ozet)


def g_cap(g: RnkGirdisi) -> KapiSonucu:
    if g.anchor is None:
        return KapiSonucu("G-CAP", ("anchor ciktisi yok (once normalize ve anchor)",), {"capa": 0})
    bulgular: list[str] = []
    tablo = {k.slug: k for k in g.tablo}
    gorulen: set[str] = set()
    adet = 0
    listeler: dict[str, list[str]] = defaultdict(list)
    anahtarlar: list[tuple[SortKey, str]] = []
    siralar: dict[str, list[tuple[object, int]]] = defaultdict(list)
    simdiki: dict[str, str] = {}
    kitap_kumesi: set[str] = set()
    derinlik: Counter[int] = Counter()
    data_version = f"{KAYNAK}@{g.kayit.surum}"
    for b in g.anchor():
        adet += 1
        capa = _metin(b["anchor"])
        if capa in gorulen:
            listeler["yinelenen capa"].append(capa)
        gorulen.add(capa)
        if set(b) != ANCHOR_ALANLARI:
            listeler["alan kumesi"].append(capa)
            continue
        parcalar = capa.split(":")
        if capa.startswith("rn:") and len(parcalar) > 1 and parcalar[1] == DIZIN:
            listeler["paket kimligi risale-dizin"].append(capa)
            continue
        try:
            yol = rn_yolu(capa)
        except GirdiHatasi:
            listeler["gecersiz capa"].append(capa)
            continue
        derinlik[len(yol)] += 1
        kitap = yol[0]
        kitap_kumesi.add(kitap)
        if _oz_yineleme(yol):
            listeler["oz yinelenen capa"].append(capa)
        kayit = tablo.get(kitap)
        if kayit is None:
            listeler["kitap tabloda yok"].append(capa)
        else:
            paket = paket_kimligi(kitap)
            if not paket.startswith(PAKET_ONEKI) or paket == DIZIN_PAKETI:
                listeler["paket kimligi"].append(capa)
            attrs = _nesne(b["attrs"])
            if attrs.get("dil") != kayit.dil or attrs.get("yon") != kayit.yon:
                listeler["dil ve yon kitap tablosuyla ayni degil"].append(capa)
        hasiye = hasiye_bolumu_mu(yol)
        rol = b.get("role")
        if rol not in ROLLER.values() or (rol == ROLLER["hasiye"]) != hasiye:
            listeler["role"].append(capa)
        if (
            b.get("kind") != KIND
            or b.get("metin_durumu") != METIN_DURUMU
            or b.get("source_id") != KAYNAK
            or b.get("data_version") != data_version
            or b.get("ayah_lo") is not None
            or b.get("ayah_hi") is not None
        ):
            listeler["sabit alan"].append(capa)
        if b.get("parent_path") != parent_yolu(yol):
            listeler["parent_path"].append(capa)
        ozet, metin = _metin(b["content_hash"]), _metin(b["text"])
        if not _hash_bicimi(ozet):
            listeler["content_hash biciminde"].append(capa)
        elif ozet != content_hash(metin):
            listeler["content_hash"].append(capa)
        marks = _liste(b["marks"])
        sentences = b["sentences"]
        if not _isaretler_gecerli(marks, len(metin)):
            listeler["marks araligi"].append(capa)
        if not _araliklar_gecerli(sentences, len(metin)):
            listeler["sentences araligi"].append(capa)
        elif rol == ROLLER["baslik"]:
            if sentences:
                listeler["baslik biriminde cumle"].append(capa)
        elif _isaretler_gecerli(marks, len(metin)):
            try:
                beklenen = cumle_araliklari(capa, metin, [_nesne(m) for m in marks])
            except GirdiHatasi:
                beklenen = []
            if beklenen != sentences:
                listeler["sentences ayiriciyla yeniden uretilemedi"].append(capa)
            if _ar_icinde_boler(_liste(sentences), marks):
                listeler["ar isaretinde cumle siniri"].append(capa)
        saglayici = _nesne(b["provenance"])
        if _nesne(saglayici.get("cumle", {})).get("surum") != CUMLE_SURUMU:
            listeler["provenance.cumle.surum"].append(capa)
        try:
            ord_anahtari = ord_anahtari_degerleri(capa, saglayici)
        except GirdiHatasi:
            listeler["provenance.konum"].append(capa)
        else:
            siralar[kitap].append((ord_anahtari, _tam(b["ord"])))
        anahtarlar.append((sort_key(parse(capa)), capa))
        simdiki[capa] = ozet
    siralama = [c for (a, _), (bb, c) in pairwise(anahtarlar) if not a < bb]
    ord_hatasi: list[str] = []
    for kitap, liste in siralar.items():
        liste.sort(key=lambda cift: cift[0])  # type: ignore[arg-type, return-value]
        if [o for _, o in liste] != list(range(1, len(liste) + 1)):
            ord_hatasi.append(kitap)
    eksik_kitap = sorted(set(tablo) - kitap_kumesi)
    for ad, neden in (
        ("alan kumesi", "anchor cikisinin alan kumesi degil"),
        ("yinelenen capa", "capa birden fazla satirda"),
        ("gecersiz capa", "gramere, rn: dogrulayicisina ya da kanonik bicime uymuyor"),
        ("kitap tabloda yok", "kitap slug'i risale-kitaplar.json'da yok"),
        ("oz yinelenen capa", "ilk bolum adi kitap slug'iyla ayni (duzey daraltilmali)"),
        ("paket kimligi risale-dizin", "dizin kitap slug'i olamaz"),
        ("paket kimligi", "risale-{kitap} paket kimligi uretilemiyor"),
        ("dil ve yon kitap tablosuyla ayni degil", "attrs.dil ya da attrs.yon tabloyla farkli"),
        ("role", "role baslik/dipnot/govde kuralina uymuyor"),
        ("sabit alan", "kind, metin_durumu, source_id, data_version ya da ayah_lo/hi"),
        ("parent_path", "capanin bolum yoluyla ayni degil"),
        ("content_hash biciminde", "64 haneli kucuk harfli onaltilik degil"),
        ("content_hash", "metnin SHA-256'siyla tutmuyor"),
        ("marks araligi", "yari acik aralik metne sigmiyor"),
        ("sentences araligi", "yari acik, artan, ayrik aralik metne sigmiyor"),
        ("baslik biriminde cumle", "baslik birimi cumle tasimaz"),
        ("sentences ayiriciyla yeniden uretilemedi", "cumle ayirici surumuyle farkli"),
        ("ar isaretinde cumle siniri", "ar isaretli aralik icinde bolunmus"),
        ("provenance.cumle.surum", "cumle ayirici surumu yok ya da farkli"),
        ("provenance.konum", "okuma sirasi icin satir konumu yok"),
    ):
        _bulgu(bulgular, ad, listeler.get(ad, []), neden)
    _bulgu(bulgular, "okuma sirasi", siralama, "satir onceki capadan sonra gelmiyor")
    _bulgu(bulgular, "ord", ord_hatasi, "kitapta ord 1..N okuma sirasi degil")
    _bulgu(bulgular, "capasiz kitap", eksik_kitap, "kitap tablosunda var, birimi yok")
    sayilar: dict[str, int] = {
        "capa": adet,
        "kitap": len(kitap_kumesi),
        "onceki_run": 0,
        "hash_degisen": 0,
        "kilit_degisti": 0,
        **{f"derinlik_{d}": n for d, n in sorted(derinlik.items())},
    }
    if g.onceki is not None:
        sayilar["onceki_run"] = 1
        kayip = sorted(c for c in g.onceki.ozetler if c not in simdiki)
        degisen = sorted(
            c for c, ozet in g.onceki.ozetler.items() if c in simdiki and simdiki[c] != ozet
        )
        kilit_degisti = (
            g.onceki_kilit_ozeti is None or g.onceki_kilit_ozeti != g.kilit_ozeti_manifest
        )
        ayristirici_degisti = (
            g.ayristirici_surumu is not None
            and g.onceki_ayristirici_surumu is not None
            and g.ayristirici_surumu != g.onceki_ayristirici_surumu
        )
        sayilar.update(
            onceki_capa=len(g.onceki.ozetler),
            hash_degisen=len(degisen),
            kilit_degisti=1 if kilit_degisti else 0,
            ayristirici_degisti=1 if ayristirici_degisti else 0,
        )
        _bulgu(bulgular, "onceki surumde olup kaybolan capa", kayip, "capa kullanim disi olamaz")
        if not (kilit_degisti or ayristirici_degisti):
            # content_hash yalniz kaynak kilidi ya da ayristirici surumu degisince degisebilir
            _bulgu(
                bulgular,
                "onceki surumle content_hash farkli",
                degisen,
                "kilit ve ayristirici surumu ayni iken metin degismis",
            )
    return KapiSonucu("G-CAP", tuple(bulgular), sayilar)


# --- G-NOR -------------------------------------------------------------------------------

TR_ALANLARI: Final = ("tr_narrow", "tr_wide", "tr_stem")


def _arapca_harf_var(metin: str) -> bool:
    return any("؀" <= c <= "ۿ" and unicodedata.category(c).startswith("L") for c in metin)


def _anchor_normu(g: RnkGirdisi, bulgular: list[str]) -> dict[str, int]:
    """Anchor ciktisinda arama sutunlari: doluluk ve yeniden uretim (`search_keys`)."""
    assert g.anchor is not None
    listeler: dict[str, list[str]] = defaultdict(list)
    sayac: Counter[str] = Counter()
    for b in g.anchor():
        capa = _metin(b["anchor"])
        dil = _nesne(b["attrs"]).get("dil")
        metin = _metin(b["text"])
        sayac[f"birim_{dil}"] += 1
        arama = _nesne(_nesne(b["provenance"]).get("arama", {}))
        if arama.get("normalizer_version") != NORMALIZER_VERSION:
            listeler["normalizer_version"].append(capa)
        if dil == "tr":
            k = search_keys(metin)
            for alan, deger in zip(TR_ALANLARI, (k.tr_narrow, k.tr_wide, k.tr_stem), strict=True):
                if b.get(alan) is None:
                    listeler["tr_* bos (null)"].append(capa)
                elif b[alan] != deger:
                    listeler["tr_*"].append(capa)
            ar_beklenen = k.ar_norm or None
            sayac["tr_denetlenen"] += 1
        else:
            if any(b.get(a) is not None for a in TR_ALANLARI):
                listeler["ota/ar tr_*"].append(capa)
            ar_beklenen = normalize_ar(metin) or None
            if _arapca_harf_var(metin) and ar_beklenen is None:
                listeler["ar_norm uretilemedi"].append(capa)
        if "ar_norm" not in b or b["ar_norm"] != ar_beklenen:
            listeler["ar_norm"].append(capa)
        sayac["ar_norm_denetlenen"] += 1
        if b.get("ar_norm") is not None:
            sayac["ar_norm_dolu"] += 1
    for ad, neden in (
        ("normalizer_version", "provenance.arama.normalizer_version guncel degil"),
        ("tr_* bos (null)", "Turkce kitapta tr_narrow, tr_wide ya da tr_stem null"),
        ("tr_*", "Turkce kitapta search_keys ile yeniden uretilen degerle ayni degil"),
        ("ota/ar tr_*", "Osmanlica/Arapca birimde tr_* dolu (yalniz ar_norm)"),
        ("ar_norm uretilemedi", "Arapca harfli birimde ar_norm uretilemedi"),
        ("ar_norm", "metinden normalize_ar ile uretilen degerle ayni degil"),
    ):
        _bulgu(bulgular, ad, listeler.get(ad, []), neden)
    return dict(sayac)


def g_nor(g: RnkGirdisi) -> KapiSonucu:
    bulgular: list[str] = []
    vektor = vektorleri_calistir(g.depo_kok)
    if vektor.kalan:
        bulgular.append(f"normalizasyon vektoru: {len(vektor.kalan)}/{vektor.toplam} kaldi")
    if vektor.hizasiz:
        bulgular.append(f"tr_wide/tr_stem sozcuk hizasi: {len(vektor.hizasiz)} vektor")
    sayilar: dict[str, int] = {"vektor": vektor.toplam, "vektor_kalan": len(vektor.kalan)}
    if g.anchor is not None:
        sayilar.update(_anchor_normu(g, bulgular))
        sayilar["ota_ar_birim"] = sayilar.get("birim_ota", 0) + sayilar.get("birim_ar", 0)
        return KapiSonucu("G-NOR", tuple(bulgular), sayilar)
    # Anchor ciktisi yoksa (yalniz ingest birimleri): Osmanlica/Arapca uretilebilirlik.
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
    sayilar.update(ar_norm_denetlenen=kontrol, ota_ar_birim=sayac["ota"] + sayac["ar"])
    return KapiSonucu("G-NOR", tuple(bulgular), sayilar)


KAPI_ISLEVLERI: Final[dict[str, Callable[[RnkGirdisi], KapiSonucu]]] = {
    "G-KAY": g_kay,
    "G-BUT": g_but,
    "G-CAP": g_cap,
    "G-NOR": g_nor,
}

__all__ = ["KAPI_ISLEVLERI", "RNK_KAPILARI", "RnkGirdisi", "girdi_yukle"]
