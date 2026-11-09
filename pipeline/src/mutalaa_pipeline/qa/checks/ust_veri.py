"""Tanzil ust veri QA kapilari (A11.6): G-KAY, G-BUT, G-CAP ve olcumler (K-43).

Kapi islevleri bellekteki `UstVeriGirdisi` uzerinde calisir; ham dosya, staged satirlari ve
dogrulama girdileri `qa/run_ust_veri.py` tarafindan yuklenir. Bulgu listesi bos ise kapi `gecti`.
Bulgular ASCII ve kisadir; yalniz capa, sayi ve kisaltilmis ozet tasir, metin asla.

G-NOR bu kaynakta YOKTUR: ust veri `ar_norm` ya da baska bir arama metni uretmez (kelime `norm`
degerleri `tanzil-uthmani` kaynagindadir ve onun G-NOR kapisindan gecer); bu nedenle gerekli
kapilar G-KAY, G-BUT, G-CAP'tir (`qa/__init__.py` `YAPI_KAPILARI`).

* G-KAY: uc kaynak kaydi (`tanzil-ust-veri`, `medine-604-duzen`, `quran-meta`) gecerli ve
  `atif_metni` dolu; ham XML kilitteki `sha256` ve boyutla, `shared/data/ayet-sayilari.json`
  ozetiyle ve kok `version` kayit/kilit surumuyle tutarli; kayit adresi kilit adresiyle ayni.
* G-BUT (yapisal kurallar HER ZAMAN; sayilar kaynak dosyadan):
  ust veri uc yonlu ayet sayisi (sure `ayas` == birim sayisi == `ayet-sayilari.json`); ingest
  ciktisi ham XML'den yeniden uretilenle ayni; isaret satirlari: cuz/hizb/rub/secde numaralari
  kesintisiz, baslangiclar okuma sirasinda artar, ilk cuz kitabin ilk ayetidir, sayilar kaynak
  sayilariyla tutar (hizb = ceyrek/4), `secde_turu` yalniz secdede ve Tanzil etiketiyle;
  sayfa satirlari: sayfa numaralari kesintisiz, ilk sayfa kitabin ilk kelimesiyle baslar, son
  sayfa son kelimeyle biter, sayfalar kelime kelime kesintisiz (bosluk ve ortusme yok), her
  sayfa ayet sinirinda baslar ve biter, her ayet en az bir sayfada; satirlar kaynak ve
  kelime dosyasindan yeniden uretilenle ayni. Dogrulama girdileri (QPC1, quran-meta) VARSA
  zorunludur: sayfa baslangic/bitisi 604/604 ve baslangic listeleri 0 fark; yoksa olcum
  "atlandi" olarak raporlanir (CI'da `data/` yoktur).
* G-CAP: isaret capalari kanonik ayet capasi ve kelime dosyasinda var; sayfa capalari kanonik
  tekil kelime capasi ve sayfa tablosuna (`anchor/sayfa.py`) kurulabilir; (kind, no) ve sayfa
  numarasi tekil; sabit alanlar (`source_id`, `data_version`) dogru.
"""

from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from functools import cached_property
from itertools import pairwise
from pathlib import Path
from typing import Final

from mutalaa_pipeline import lineage
from mutalaa_pipeline.adimlar.anchor_tanzil import ayet_coz
from mutalaa_pipeline.adimlar.anchor_ust_veri import (
    AyetBilgisi,
    ayet_bilgisi,
    isaret_satirlari,
    sayfa_satirlari,
)
from mutalaa_pipeline.anchor import AnchorError, Q, parse
from mutalaa_pipeline.anchor import format as anchor_format
from mutalaa_pipeline.anchor.sayfa import SayfaHatasi, SayfaTablosu, sayfa_bul
from mutalaa_pipeline.export import ayet_sayilari
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.ingest.tanzil import UstVeriKilidi
from mutalaa_pipeline.ingest.tanzil_ust_veri import KAYNAK
from mutalaa_pipeline.lineage import kisa_ozet
from mutalaa_pipeline.qa.checks.tanzil import KapiSonucu
from mutalaa_pipeline.qa.dogrulama import Qpc1, QuranMeta
from mutalaa_pipeline.sources.kayit import Kaynak
from mutalaa_pipeline.staged import Satir

ORNEK_CAPA: Final = 5
ISARET_TURLERI: Final = ("cuz", "hizb", "rub", "secde")
# quran-meta HafsLists dizisi -> (yapi turu); hepsi mutlak (kuresel) ayet numarasidir.
META_ESLEME: Final = (
    ("JuzList", "cuz"),
    ("HizbQuarterList", "rub"),
    ("ManzilList", "menzil"),
    ("RukuList", "ruku"),
    ("PageList", "sayfa"),
)
Yapi = Mapping[str, Sequence[Mapping[str, object]]]


@dataclass
class UstVeriGirdisi:
    """Zincirden yuklenmis, kapilarin okudugu veri."""

    kayit: Kaynak
    diger_kayitlar: Mapping[str, Kaynak]  # medine-604-duzen, quran-meta
    kilit: UstVeriKilidi
    ham: bytes
    ham_sha256: str
    yapi: Yapi  # ham XML'den yeniden ayristirilmis
    ingest_yapi: Yapi  # ingest calismasinin staged dosyalari
    isaret_satirlari: Sequence[Satir]
    sayfa_satirlari: Sequence[Satir]
    kelime_satirlari: Sequence[Satir]  # tanzil-uthmani words.jsonl
    birim_satirlari: Sequence[Satir]  # tanzil-uthmani units.jsonl
    depo_kok: Path
    qpc1: Qpc1 | None = None
    quran_meta: QuranMeta | None = None

    @cached_property
    def ayetler(self) -> AyetBilgisi:
        return ayet_bilgisi([s.veri for s in self.kelime_satirlari])

    @cached_property
    def surum(self) -> str:
        return f"{self.kayit.surum}"

    @cached_property
    def baslangic_sirasi(self) -> dict[int, int]:
        """Ayetin kuresel sirasi -> ayetten onceki toplam kelime sayisi."""
        toplam = 0
        sonuc: dict[int, int] = {}
        for idx in sorted(self.ayetler.konum):
            sonuc[idx] = toplam
            toplam += self.ayetler.kelime_sayisi[self.ayetler.konum[idx]]
        return sonuc

    @cached_property
    def kelime_toplami(self) -> int:
        return sum(self.ayetler.kelime_sayisi.values())

    def kelime_sirasi(self, sure: int, ayet: int, kelime: int) -> int:
        """Kelimenin kitap icindeki 1 tabanli sirasi (kelime dosyasina gore)."""
        return self.baslangic_sirasi[self.ayetler.sira[(sure, ayet)]] + kelime


# --- yardimcilar -------------------------------------------------------------------------


def _g(deger: object, en_uzun: int = 60) -> str:
    return ascii(str(deger))[1:-1][:en_uzun]


def _capalar(capalar: Sequence[str]) -> str:
    gosterilen = ", ".join(_g(c) for c in capalar[:ORNEK_CAPA])
    fazla = len(capalar) - ORNEK_CAPA
    return gosterilen + (f" (+{fazla})" if fazla > 0 else "")


def _bos(metin: str) -> bool:
    return all(harf in " \t\n" for harf in metin)


def _ekle(bulgular: list[str], ad: str, liste: Sequence[str], neden: str) -> None:
    if liste:
        bulgular.append(f"{ad}: {len(liste)} birim: {neden}: {_capalar(liste)}")


def _kelime_konumu(capa: str) -> tuple[int, int, int] | None:
    """Kanonik `q:s:a:k` capasinin `(s, a, k)` degeri; degilse None."""
    try:
        ref = parse(capa)
        kanonik = anchor_format(ref) == capa
    except (AnchorError, ValueError):
        return None
    kok = ref.anchor
    if not kanonik or ref.span is not None or not isinstance(kok, Q):
        return None
    if kok.ilk is None or kok.son is not None:
        return None
    return kok.sure, kok.ayet, kok.ilk


def _konum(satir: Mapping[str, object]) -> tuple[int, int]:
    return int(str(satir["sura"])), int(str(satir["aya"]))


def _yeniden_uretim(g: UstVeriGirdisi) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    return (
        isaret_satirlari(g.yapi, g.ayetler, g.surum),
        sayfa_satirlari(g.yapi, g.ayetler, g.surum),
    )


# --- G-KAY -------------------------------------------------------------------------------


def g_kay(g: UstVeriGirdisi) -> KapiSonucu:
    """Kaynak kayitlari, ham dosya ve kilit tutarliligi."""
    bulgular: list[str] = []
    kayitlar = {KAYNAK: g.kayit, **g.diger_kayitlar}
    for ad, kayit in kayitlar.items():
        if _bos(kayit.atif_metni):
            bulgular.append(f"{ad}: atif_metni bos")
    kilit = g.kilit
    if g.ham_sha256 != kilit.sha256 or len(g.ham) != kilit.boyut:
        bulgular.append("ham XML kilitteki sha256 ve boyutla tutmuyor")
    try:
        belge = ayet_sayilari.json_oku(g.depo_kok)
    except GirdiHatasi as hata:
        bulgular.append(f"ayet-sayilari.json okunamadi: {_g(hata, 120)}")
    else:
        if belge.sha256 != kilit.sha256:
            bulgular.append(
                f"ayet-sayilari.json sha256 {kisa_ozet(belge.sha256)} kilitteki"
                f" {kisa_ozet(kilit.sha256)} degil"
            )
    try:
        xml_surumu = ayet_sayilari.ayristir(g.ham).surum
    except GirdiHatasi as hata:
        bulgular.append(f"ham XML ayristirilamadi: {_g(hata, 120)}")
    else:
        if xml_surumu != kilit.surum:
            bulgular.append("XML kok version degeri kilit surumuyle ayni degil")
    if g.kayit.surum != kilit.surum:
        bulgular.append(
            f"{KAYNAK}: kayit surumu {_g(g.kayit.surum)} kilit surumu {_g(kilit.surum)} degil"
        )
    if g.kayit.kaynak_url != kilit.url:
        bulgular.append(f"{KAYNAK}: kayit kaynak_url degeri kilitteki url ile ayni degil")
    sayilar = {"kaynak_kaydi": len(kayitlar), "ham_boyut": len(g.ham)}
    return KapiSonucu("G-KAY", tuple(bulgular), sayilar)


# --- G-BUT -------------------------------------------------------------------------------


def _ayet_sayilari(g: UstVeriGirdisi) -> tuple[list[str], dict[str, object]]:
    """Uc yonlu sure basina ayet sayisi: ust veri == birimler == ayet-sayilari.json."""
    ust = {int(str(s["no"])): int(str(s["ayas"])) for s in g.yapi["sure"]}
    birim = Counter(
        konum[0] for s in g.birim_satirlari if (konum := ayet_coz(s.metin("anchor"))) is not None
    )
    try:
        json_sayilar = ayet_sayilari.json_oku(g.depo_kok).sayilar
    except GirdiHatasi:
        json_sayilar = ()
    farkli = sorted(
        sure
        for sure in set(ust) | set(birim) | set(range(1, len(json_sayilar) + 1))
        if not (
            ust.get(sure) == birim.get(sure)
            and sure <= len(json_sayilar)
            and json_sayilar[sure - 1] == ust.get(sure)
        )
    )
    bulgular: list[str] = []
    if not json_sayilar:
        bulgular.append("ayet-sayilari.json okunamadi: uc yonlu sayim yapilamadi")
    _ekle(
        bulgular,
        "ayet sayisi",
        [f"sure {s}" for s in farkli],
        "ust veri, birimler ve ayet-sayilari.json ayni degil",
    )
    olcum: dict[str, object] = {
        "sure": len(ust),
        "ust_veri_ayet": sum(ust.values()),
        "birim_ayet": sum(birim.values()),
        "json_ayet": sum(json_sayilar),
        "uc_yonlu_ayni": bool(json_sayilar) and not farkli,
        "farkli_sure": farkli,
    }
    return bulgular, olcum


def _isaret_yapisi(g: UstVeriGirdisi) -> list[str]:
    bulgular: list[str] = []
    gruplar: dict[str, list[Satir]] = {tur: [] for tur in ISARET_TURLERI}
    bilinmeyen: list[str] = []
    for s in g.isaret_satirlari:
        tur = s.metin("kind")
        if tur in gruplar:
            gruplar[tur].append(s)
        else:
            bilinmeyen.append(f"{tur}/{s.sayi('no')}")
    _ekle(bulgular, "isaret turu", bilinmeyen, "cuz, hizb, rub ya da secde degil")
    beklenen = {
        "cuz": len(g.yapi["cuz"]),
        "rub": len(g.yapi["rub"]),
        "hizb": len(g.yapi["rub"]) // 4,
        "secde": len(g.yapi["secde"]),
    }
    ilk_ayet = g.ayetler.konum[min(g.ayetler.konum)]
    for tur, satirlar in gruplar.items():
        if len(satirlar) != beklenen[tur]:
            bulgular.append(f"{tur}: {len(satirlar)} satir; kaynak dosyada {beklenen[tur]}")
        numaralar = [s.sayi("no") for s in satirlar]
        if numaralar != list(range(1, len(numaralar) + 1)):
            bulgular.append(f"{tur}: numaralar 1'den kesintisiz degil")
        siralar = [
            g.ayetler.sira.get(konum, -1)
            for s in satirlar
            if (konum := ayet_coz(s.metin("anchor"))) is not None
        ]
        if any(b >= a for b, a in pairwise(siralar)) or -1 in siralar:
            bulgular.append(f"{tur}: baslangiclar okuma sirasinda artmiyor")
    if gruplar["cuz"] and ayet_coz(gruplar["cuz"][0].metin("anchor")) != ilk_ayet:
        bulgular.append("ilk cuz kitabin ilk ayetiyle baslamiyor")
    etiketler = {s["no"]: s.get("type") for s in g.yapi["secde"]}
    yanlis_etiket = [
        f"{s.metin('kind')}/{s.sayi('no')}"
        for s in g.isaret_satirlari
        if (s.metin("kind") == "secde") != (s.veri.get("secde_turu") is not None)
        or (s.metin("kind") == "secde" and s.veri.get("secde_turu") != etiketler.get(s.sayi("no")))
    ]
    _ekle(
        bulgular,
        "secde_turu",
        yanlis_etiket,
        "yalniz secdede ve Tanzil'in kendi etiketiyle dolu olmali",
    )
    return bulgular


def _sayfa_yapisi(g: UstVeriGirdisi) -> list[str]:
    bulgular: list[str] = []
    satirlar = list(g.sayfa_satirlari)
    sayfalar = [s.sayi("page") for s in satirlar]
    if len(satirlar) != len(g.yapi["sayfa"]):
        bulgular.append(f"sayfa: {len(satirlar)} satir; kaynak dosyada {len(g.yapi['sayfa'])}")
    if sayfalar != list(range(1, len(sayfalar) + 1)):
        bulgular.append("sayfa: numaralar 1'den kesintisiz degil")
    konumlar: list[tuple[int, int, int, int, int, int]] = []
    ayet_ortasi: list[str] = []
    for s in satirlar:
        bas, bit = _kelime_konumu(s.metin("start_anchor")), _kelime_konumu(s.metin("end_anchor"))
        if bas is None or bit is None:
            bulgular.append(f"sayfa {s.sayi('page')}: capa kanonik kelime capasi degil")
            return bulgular  # G-CAP ayrintiyi verir; sirasi anlamsiz
        try:
            ilk, son = g.kelime_sirasi(*bas), g.kelime_sirasi(*bit)
        except KeyError:
            bulgular.append(f"sayfa {s.sayi('page')}: capa kelime dosyasinda yok")
            return bulgular
        konumlar.append(
            (s.sayi("page"), ilk, son, bas[2], bit[2], g.ayetler.kelime_sayisi[bit[:2]])
        )
        if bas[2] != 1 or bit[2] != g.ayetler.kelime_sayisi[bit[:2]]:
            ayet_ortasi.append(f"q:{bas[0]}:{bas[1]}")
    _ekle(
        bulgular, "sayfa ayet sinirinda degil", ayet_ortasi, "sayfa ayet ortasinda basliyor/bitiyor"
    )
    kesinti: list[str] = []
    for onceki, sonraki in pairwise(konumlar):
        if sonraki[1] != onceki[2] + 1:
            kesinti.append(f"sayfa {sonraki[0]}")
    _ekle(
        bulgular,
        "sayfa kesintisi",
        kesinti,
        "baslangic onceki sayfanin bitisinden hemen sonra degil",
    )
    if konumlar and konumlar[0][1] != 1:
        bulgular.append("ilk sayfa kitabin ilk kelimesiyle baslamiyor")
    if konumlar and konumlar[-1][2] != g.kelime_toplami:
        bulgular.append("son sayfa kitabin son kelimesiyle bitmiyor")
    if any(k[2] < k[1] for k in konumlar):
        bulgular.append("sayfa: bitis baslangictan once")
    return bulgular


def _dogrulama_bulgulari(g: UstVeriGirdisi) -> tuple[list[str], dict[str, object]]:
    """QPC1 ve quran-meta karsilastirmalari (dosya varsa zorunlu, yoksa 'atlandi')."""
    bulgular: list[str] = []
    olcum: dict[str, object] = {}
    sayfalar = {s.sayi("page"): s for s in g.sayfa_satirlari}
    if g.qpc1 is None:
        olcum["qpc1"] = {"durum": "atlandi"}
    else:
        qpc1 = g.qpc1
        baslangic_ayni = bitis_ayni = ortada_baslayan = ortada_biten = 0
        for sayfa, satir in sayfalar.items():
            ilk, son = qpc1.ilk.get(sayfa), qpc1.son.get(sayfa)
            bas, bit = (
                _kelime_konumu(satir.metin("start_anchor")),
                _kelime_konumu(satir.metin("end_anchor")),
            )
            if ilk is None or son is None or bas is None or bit is None:
                continue
            ilk_k = tuple(int(x) for x in ilk.split(":"))
            son_k = tuple(int(x) for x in son.split(":"))
            baslangic_ayni += 1 if ilk_k[:2] == bas[:2] else 0
            bitis_ayni += 1 if son_k == bit else 0
            ortada_baslayan += 1 if ilk_k[2] != 1 else 0
            sayi = g.ayetler.kelime_sayisi.get((son_k[0], son_k[1]))
            ortada_biten += 1 if sayi is None or son_k[2] != sayi else 0
        farkli_sayfa = sorted(set(sayfalar) ^ set(qpc1.ilk))
        olcum["qpc1"] = {
            "durum": "yapildi",
            "tarih": qpc1.tarih,
            "sha256sums_sha256": qpc1.sha256sums_ozeti,
            "sayfa": len(sayfalar),
            "qpc1_sayfa": qpc1.sayfa_sayisi,
            "baslangic_ayni": baslangic_ayni,
            "bitis_ayni": bitis_ayni,
            "ayet_ortasinda_baslayan": ortada_baslayan,
            "ayet_ortasinda_biten": ortada_biten,
        }
        if farkli_sayfa:
            bulgular.append(
                f"QPC1 ve sayfa tablosunun sayfa kumesi farkli (sayi {len(farkli_sayfa)})"
            )
        for ad, deger in (
            ("sayfa baslangic ayeti Tanzil ve QPC1'de ayni degil", len(sayfalar) - baslangic_ayni),
            ("sayfa son kelimesi QPC1'in son kelimesiyle ayni degil", len(sayfalar) - bitis_ayni),
            ("QPC1'de ayet ortasinda baslayan sayfa", ortada_baslayan),
            ("QPC1'de ayet ortasinda biten sayfa", ortada_biten),
        ):
            if deger:
                bulgular.append(f"{ad}: {deger} sayfa")
    if g.quran_meta is None:
        olcum["quran_meta"] = {"durum": "atlandi"}
    else:
        meta = g.quran_meta
        farklar: dict[str, int] = {}
        toplam_ayet = len(g.ayetler.sira)
        for ad, tur in META_ESLEME:
            tanzil = [g.ayetler.sira.get(_konum(s), -1) for s in g.yapi[tur]]
            kaynak = list(meta.listeler[ad])
            farklar[ad] = sum(1 for a, b in zip(tanzil, kaynak, strict=False) if a != b) + abs(
                len(tanzil) - len(kaynak)
            )
        tanzil_secde = [g.ayetler.sira.get(_konum(s), -1) for s in g.yapi["secde"]]
        kaynak_secde = list(meta.listeler["SajdaList"])
        farklar["SajdaList"] = sum(
            1 for a, b in zip(tanzil_secde, kaynak_secde, strict=False) if a != b
        ) + abs(len(tanzil_secde) - len(kaynak_secde))
        olcum["quran_meta"] = {
            "durum": "yapildi",
            "tarih": meta.tarih,
            "tgz_sha256": meta.tgz_sha256,
            "farklar": farklar,
            "sentinel_ayet_artisi_ile_ayni": meta.sentinel == toplam_ayet + 1,
        }
        for ad, fark in farklar.items():
            if fark:
                bulgular.append(f"quran-meta {ad} Tanzil ile {fark} konumda farkli")
        if meta.sentinel != toplam_ayet + 1:
            bulgular.append("quran-meta sentinel degeri toplam ayet + 1 degil")
    return bulgular, olcum


def g_but(g: UstVeriGirdisi) -> KapiSonucu:
    """Sayilar, isaret ve sayfa yapisi, yeniden uretim ve (varsa) dogrulama girdileri."""
    bulgular, _ = _ayet_sayilari(g)
    if g.ingest_yapi != g.yapi:
        bulgular.append("ingest ciktisi ham XML'den yeniden uretilenle ayni degil")
    bulgular += _isaret_yapisi(g)
    bulgular += _sayfa_yapisi(g)
    try:
        isaret, sayfa = _yeniden_uretim(g)
    except (GirdiHatasi, KeyError) as hata:
        bulgular.append(f"satirlar yeniden uretilemedi: {_g(hata, 120)}")
    else:
        if [s.veri for s in g.isaret_satirlari] != isaret:
            bulgular.append("markers.jsonl kaynak dosyadan yeniden uretilenle ayni degil")
        if [s.veri for s in g.sayfa_satirlari] != sayfa:
            bulgular.append("pages.jsonl kaynak dosyadan ve kelime dosyasindan uretilenle farkli")
    dogrulama, _ = _dogrulama_bulgulari(g)
    bulgular += dogrulama
    sayilar = {
        "isaret": len(g.isaret_satirlari),
        "sayfa": len(g.sayfa_satirlari),
        "kelime": g.kelime_toplami,
        **{f"yapi_{tur}": len(satirlar) for tur, satirlar in g.yapi.items()},
    }
    return KapiSonucu("G-BUT", tuple(bulgular), sayilar)


# --- G-CAP -------------------------------------------------------------------------------


def g_cap(g: UstVeriGirdisi) -> KapiSonucu:
    """Capa gramer, teklik, kelime dosyasinda varlik, sayfa tablosu ve sabit alanlar."""
    bulgular: list[str] = []
    data_version = f"{KAYNAK}@{g.surum}"
    gecersiz: list[str] = []
    yok: list[str] = []
    tekrar: list[str] = []
    sabit: list[str] = []
    gorulen: set[tuple[str, int]] = set()
    for s in g.isaret_satirlari:
        anahtar = (s.metin("kind"), s.sayi("no"))
        etiket = f"{anahtar[0]}/{anahtar[1]}"
        if anahtar in gorulen:
            tekrar.append(etiket)
        gorulen.add(anahtar)
        konum = ayet_coz(s.metin("anchor"))
        if konum is None:
            gecersiz.append(etiket)
        elif konum not in g.ayetler.sira:
            yok.append(etiket)
        if s.metin("source_id") != KAYNAK or s.metin("data_version") != data_version:
            sabit.append(etiket)
    _ekle(bulgular, "gecersiz isaret capasi", gecersiz, "kanonik bir q:{sure}:{ayet} capasi degil")
    _ekle(bulgular, "isaret ayeti", yok, "kelime dosyasinda yok")
    _ekle(bulgular, "yinelenen isaret", tekrar, "(kind, no) birden fazla satirda")
    _ekle(bulgular, "isaret sabit alani", sabit, "source_id ya da data_version yanlis")

    sayfa_gecersiz: list[str] = []
    sayfa_yok: list[str] = []
    sayfa_tekrar: list[str] = []
    sayfa_sabit: list[str] = []
    sayfalar: set[int] = set()
    uclar: list[tuple[int, str, str]] = []
    for s in g.sayfa_satirlari:
        sayfa = s.sayi("page")
        etiket = f"sayfa {sayfa}"
        if sayfa in sayfalar:
            sayfa_tekrar.append(etiket)
        sayfalar.add(sayfa)
        for alan in ("start_anchor", "end_anchor"):
            uc = _kelime_konumu(s.metin(alan))
            if uc is None:
                sayfa_gecersiz.append(f"{etiket} {alan}")
            elif g.ayetler.kelime_sayisi.get(uc[:2], 0) < uc[2]:
                sayfa_yok.append(f"{etiket} {alan}")
        uclar.append((sayfa, s.metin("start_anchor"), s.metin("end_anchor")))
        if s.metin("source_id") != KAYNAK or s.metin("data_version") != data_version:
            sayfa_sabit.append(etiket)
    _ekle(bulgular, "gecersiz sayfa capasi", sayfa_gecersiz, "kanonik tekil kelime capasi degil")
    _ekle(bulgular, "sayfa capasi", sayfa_yok, "kelime dosyasinda yok")
    _ekle(bulgular, "yinelenen sayfa", sayfa_tekrar, "sayfa numarasi birden fazla satirda")
    _ekle(bulgular, "sayfa sabit alani", sayfa_sabit, "source_id ya da data_version yanlis")
    kapsanmayan = 0
    if not (sayfa_gecersiz or sayfa_tekrar):
        try:
            tablo = SayfaTablosu.kur(uclar)
        except SayfaHatasi as hata:
            bulgular.append(f"sayfa tablosu kurulamadi: {_g(hata, 120)}")
        else:
            for konum in g.ayetler.sira:
                try:
                    sayfa_bul(tablo, f"q:{konum[0]}:{konum[1]}")
                except SayfaHatasi:
                    kapsanmayan += 1
            if kapsanmayan:
                bulgular.append(f"hicbir sayfada olmayan ayet: {kapsanmayan}")
    sayilar = {
        "isaret_capa": len(gorulen),
        "sayfa_capa": len(sayfalar),
        "sayfada_olmayan": kapsanmayan,
    }
    return KapiSonucu("G-CAP", tuple(bulgular), sayilar)


KAPI_ISLEVLERI: Final[dict[str, Callable[[UstVeriGirdisi], KapiSonucu]]] = {
    "G-KAY": g_kay,
    "G-BUT": g_but,
    "G-CAP": g_cap,
}


# --- olcumler (kapi degil; rapora yazilir) -----------------------------------------------


def olcumler(g: UstVeriGirdisi) -> dict[str, object]:
    """Rapora yazilan olcumler: uc yonlu ayet sayisi, QPC1 ve quran-meta, dosya ozetleri."""
    _, ayet = _ayet_sayilari(g)
    _, dogrulama = _dogrulama_bulgulari(g)
    return {
        "yapi_sayilari": {tur: len(satirlar) for tur, satirlar in g.yapi.items()},
        "isaret_sayilari": dict(Counter(s.metin("kind") for s in g.isaret_satirlari)),
        "secde_etiketleri": dict(
            Counter(
                str(s.veri.get("secde_turu"))
                for s in g.isaret_satirlari
                if s.metin("kind") == "secde"
            )
        ),
        "ayet_sayisi": ayet,
        "kelime_toplami": g.kelime_toplami,
        **dogrulama,
        "dosya_ozetleri": {
            "quran_data_xml_sha256": g.ham_sha256,
            "quran_meta_tgz_sha256": g.quran_meta.tgz_sha256 if g.quran_meta else None,
            "qpc1_sha256sums_sha256": g.qpc1.sha256sums_ozeti if g.qpc1 else None,
            "ayet_sayilari_json_sha256": _json_ozeti(g.depo_kok),
        },
    }


def _json_ozeti(depo_kok: Path) -> str | None:
    yol = depo_kok / ayet_sayilari.JSON_YOLU
    return lineage.sha256_dosya(yol) if yol.is_file() else None
