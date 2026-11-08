"""Tanzil QA kapilari (A10.5): G-KAY, G-BUT, G-CAP, G-NOR ve olcumler (Icerik hatti §9).

Kapi islevleri bellekteki `QaGirdisi` uzerinde calisir: ham dosyalar ve staged satirlari
`qa/run.py` tarafindan zincirden yuklenir. Bu modul yalniz `depo_kok` altindaki sabit veri
dosyalarini (`shared/data/ayet-sayilari.json` ve kopyalari, `shared/test-vectors/normalize/`)
okur. Bir kapi bulgu listesi dondurur: bos liste `gecti`, dolu liste `kaldi`. Bulgular ASCII ve
kisadir; yalniz capa, sayi, kisaltilmis ozet ve alan adi tasir, metin icerigi asla (§7).

Kapilar:

* G-KAY: iki Tanzil kaynak kaydi gecerli (`require_sources`), `atif_metni` dolu, TOML
  `notice_text` ham dosyadaki ve staged `notice.txt` dosyasindaki bildirim blogunun baytlarina
  esit, `sha256(notice_text)` kilitteki `bildirim_sha256`, kayit surumu ve adresi kilit ve dosya
  basligiyla tutarli.
* G-BUT: 114 sure ve 6.236 ayet (JSON ve kopyalari, anchor satirlari, iki ham dosya), bos birim
  ve kontrol karakteri yok, her birimin metni ham dosyanin ayni bayt dilimi, `steps` bos, ham
  dosyalar kilitle ayni. Kelime satirlari (A11.2, K-43): her kelimenin metni ayet metninin
  `[char_start, char_end)` dilimidir, araliklar ortusmez, numaralar her ayette 1'den kesintisizdir,
  her ayetin en az bir kelimesi vardir ve satirlar bolme kuralindan yeniden uretilenle ayni;
  toplam kelime sayisi `sayilar` ve `olcumler`de. NFC durumu yalniz olcumdur (kapi degil, K-26).
* G-CAP: capa gramere uyar ve kanoniktir, tekildir, okuma sirasindadir ve 6.236 ayetin hepsini
  kapsar; `ord`, `ayah_lo`, `ayah_hi` kuresel siradir; `content_hash` yeniden hesapla tutar;
  onceki anchor calismasindaki her capa durur ve ozeti degismemistir. Kelime capalari
  (`q:{sure}:{ayet}:{kelime}`) gramere uyar, kanoniktir, tekildir, okuma sirasindadir ve
  `surah`, `ayah`, `word`, `ayah_index` capayla ve ayet satiriyla tutarlidir.
* G-NOR: normalizasyon vektorleri Python'da gecer; her satirin `ar_norm` degeri ham
  dosyalardan yeniden uretilince (AR-4) tutar ve `provenance.ar_norm` dogrudur. Her kelimenin
  `norm` degeri `normalize_ar(text_uthmani)` ile ayni ve bos degildir.

Olcumler (`olcumler`, kapi degil; rapora yazilir): NFC durumu, AR-8 karakterleri, normalizasyondan
sonra kalan birlesen isaretler (Mn), besmele, AR-4 eki ve `ayet-sayilari.json` dizisinin iki ham
dosyayla ve uc kopyayla karsilastirmasi.
"""

import json
import re
import unicodedata
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from functools import cached_property
from itertools import accumulate, pairwise
from pathlib import Path
from typing import Final

from mutalaa_pipeline import lineage
from mutalaa_pipeline.adimlar.anchor_tanzil import KIND, METIN_DURUMU, ayet_coz
from mutalaa_pipeline.adimlar.anchor_tanzil import kelime_satirlari as kelimelere_bolunmus
from mutalaa_pipeline.adimlar.normalize_tanzil import EK_KAYNAK, KAYNAK, ar4_birlestir
from mutalaa_pipeline.anchor import (
    AnchorError,
    AnchorRef,
    Q,
    SortKey,
    content_hash,
    parse,
    sort_key,
)
from mutalaa_pipeline.anchor import format as anchor_format
from mutalaa_pipeline.anchor.ayet_sayilari import AYET_SAYILARI
from mutalaa_pipeline.anchor.quran import BIRLESTIRME
from mutalaa_pipeline.export import ayet_sayilari
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.ingest.tanzil import KilitGirdisi, dosya_adi
from mutalaa_pipeline.ingest.tanzil_bicim import Ayrisma, bildirim_basligi
from mutalaa_pipeline.lineage import OZET_DESENI, kisa_ozet
from mutalaa_pipeline.normalize import NORMALIZER_VERSION, normalize_ar
from mutalaa_pipeline.qa.vektorler import vektorleri_calistir
from mutalaa_pipeline.sources.kayit import Kaynak
from mutalaa_pipeline.staged import Satir

ORNEK_CAPA: Final = 5
KONTROL: Final = re.compile(r"[\x00-\x1f\x7f-\x9f]")  # Unicode Cc
TR_ALANLARI: Final = ("tr_narrow", "tr_wide", "tr_stem")
VARYANT_ADLARI: Final = {KAYNAK: "uthmani", EK_KAYNAK: "simple-clean"}
# AR-8 (Arama §1.3 madde 4): 1.0'da degismeyen, kaynakta gorulurse karar gerektiren karakterler.
AR8_ARALIKLARI: Final = (
    ("farsca_ye_u06cc", 0x06CC, 0x06CC),
    ("farsca_kef_u06a9", 0x06A9, 0x06A9),
    ("arapca_hint_rakam_u0660_u0669", 0x0660, 0x0669),
    ("dogu_arapca_hint_rakam_u06f0_u06f9", 0x06F0, 0x06F9),
)
BESMELE_BELIRTEC: Final = 4


# --- veri tipleri -----------------------------------------------------------------------


@dataclass(frozen=True)
class KapiSonucu:
    kapi: str
    bulgular: tuple[str, ...]  # bos: gecti
    sayilar: dict[str, int]

    @property
    def gecti(self) -> bool:
        return not self.bulgular


@dataclass(frozen=True)
class Varyant:
    """Bir Tanzil varyantinin zincirdeki verisi: kayit, kilit, ham dosya ve ingest ciktilari."""

    kaynak: str
    kayit: Kaynak
    kilit: KilitGirdisi
    ham: bytes
    ham_sha256: str
    ayrisma: Ayrisma
    bildirim_dosyasi: bytes | None  # staged ingest klasorundeki notice.txt
    ingest_surum: str | None  # ingest manifestinin ayrintilar.surum

    @cached_property
    def harf_sayimi(self) -> Counter[str]:
        return Counter("".join(ay.metin for ay in self.ayrisma.ayetler))


@dataclass(frozen=True)
class Onceki:
    """Onceki (saglam) anchor calismasi: `anchor -> content_hash`."""

    run_id: str
    ozetler: Mapping[str, str]


@dataclass
class QaGirdisi:
    """Zincirden yuklenmis, kapilarin okudugu veri."""

    anchor_satirlari: Sequence[Satir]
    uthmani: Varyant
    simple: Varyant
    depo_kok: Path
    onceki: Onceki | None = None
    sure_tablosu: Sequence[int] = AYET_SAYILARI
    kelime_satirlari: Sequence[Satir] = ()  # anchor calismasinin words.jsonl satirlari (A11.2)

    @cached_property
    def normalize_cifti(self) -> dict[str, tuple[str, str]]:
        """`capa -> (normalize_ar(simple_clean), normalize_ar(uthmani))` (ham dosyalardan)."""
        simple = {ay.capa: ay.metin for ay in self.simple.ayrisma.ayetler}
        return {
            ay.capa: (normalize_ar(simple[ay.capa]), normalize_ar(ay.metin))
            for ay in self.uthmani.ayrisma.ayetler
            if ay.capa in simple
        }

    @property
    def uthmani_surumu(self) -> str:
        """Anchor satirlarinin `data_version` ekinde beklenen surum (kaynak kaydindan)."""
        return f"{self.uthmani.kayit.surum}"

    @cached_property
    def baslangic(self) -> tuple[int, ...]:
        """`baslangic[s - 1]` = 1..s-1. surelerdeki ayet toplami (tablodan)."""
        return tuple(accumulate(self.sure_tablosu, initial=0))


# --- yardimcilar -------------------------------------------------------------------------


def _g(deger: object, en_uzun: int = 60) -> str:
    """Dosyadan gelen bir degeri iletide guvenli (ASCII) gosterir."""
    return ascii(str(deger))[1:-1][:en_uzun]


def _capalar(capalar: Sequence[str]) -> str:
    gosterilen = ", ".join(_g(c) for c in capalar[:ORNEK_CAPA])
    fazla = len(capalar) - ORNEK_CAPA
    return gosterilen + (f" (+{fazla})" if fazla > 0 else "")


def _bos(metin: str) -> bool:
    """Bos ya da yalniz U+0020, U+0009, U+000A (varsayilan strip kullanilmaz)."""
    return all(harf in " \t\n" for harf in metin)


def _esit(a: object, b: object) -> bool:
    """JSON degeri olarak esitlik (`True` ile `1` ayni sayilmaz)."""
    return json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def _baytlar(metin: str) -> bytes | None:
    try:
        return metin.encode("utf-8")
    except UnicodeEncodeError:  # eslesmeyen vekil: UTF-8'e yazilamaz
        return None


def _sayim_bulgulari(
    etiket: str, sayim: Mapping[int, int], satir: int, tablo: Sequence[int]
) -> list[str]:
    """Sure ve ayet sayimini tabloyla karsilastirir."""
    bulgular: list[str] = []
    if satir != sum(tablo):
        bulgular.append(f"{etiket}: ayet sayisi {satir}, beklenen {sum(tablo)}")
    sure_sayisi = sum(1 for adet in sayim.values() if adet > 0)
    if sure_sayisi != len(tablo):
        bulgular.append(f"{etiket}: sure sayisi {sure_sayisi}, beklenen {len(tablo)}")
    farklar = [
        f"sure {sure} ({sayim.get(sure, 0)}/{beklenen})"
        for sure, beklenen in enumerate(tablo, start=1)
        if sayim.get(sure, 0) != beklenen
    ]
    farklar += [
        f"sure {sure} ({adet}/-)" for sure, adet in sorted(sayim.items()) if sure > len(tablo)
    ]
    if farklar:
        fazla = len(farklar) - ORNEK_CAPA
        gosterilen = ", ".join(farklar[:ORNEK_CAPA])
        bulgular.append(
            f"{etiket}: sure basina ayet sayisi tabloyla ayni degil: {gosterilen}"
            + (f" (+{fazla})" if fazla > 0 else "")
        )
    return bulgular


def _tablo_bulgulari(depo_kok: Path) -> list[str]:
    """`ayet-sayilari.json` kodun tablosuyla ve uc kopyasi (TS, Python, C#) JSON'la ayni olmali."""
    try:
        belge = ayet_sayilari.json_oku(depo_kok)
        kopyalar = ayet_sayilari.denetle(depo_kok)
    except GirdiHatasi as hata:
        return [f"ayet-sayilari.json okunamadi: {_g(hata, 120)}"]
    bulgular: list[str] = []
    if belge.sayilar != tuple(AYET_SAYILARI):
        bulgular.append("ayet-sayilari.json dizisi kodun tablosuyla (AYET_SAYILARI) ayni degil")
    bulgular += [
        f"{yol} JSON'dan uretilen metinle ayni degil (export ayet-sayilari --check)"
        for yol in kopyalar
    ]
    return bulgular


# --- G-KAY -------------------------------------------------------------------------------


def g_kay(g: QaGirdisi) -> KapiSonucu:
    """Kaynak kaydi ve bildirim: `notice_text` dosyadaki bloga bayt bayt esit (K-39 madde 6)."""
    bulgular: list[str] = []
    sayilar: dict[str, int] = {"kaynak_kaydi": 0}
    for v in (g.uthmani, g.simple):
        ad, kayit, kilit = v.kaynak, v.kayit, v.kilit
        sayilar["kaynak_kaydi"] += 1
        if _bos(kayit.atif_metni):
            bulgular.append(f"{ad}: atif_metni bos")
        beklenen = v.ayrisma.bildirim
        sayilar[f"bildirim_bayt_{VARYANT_ADLARI[ad].replace('-', '_')}"] = len(beklenen)
        if kayit.notice_text is None:
            bulgular.append(f"{ad}: kayitta notice_text yok (dosyada bildirim blogu var)")
        else:
            yazilan = kayit.notice_text.encode("utf-8")
            if yazilan != beklenen:
                bulgular.append(
                    f"{ad}: notice_text dosyadaki bildirim blogundan farkli"
                    f" (bayt {len(yazilan)}/{len(beklenen)})"
                )
            ozet = lineage.sha256_bayt(yazilan)
            if ozet != kilit.bildirim_sha256:
                bulgular.append(
                    f"{ad}: sha256(notice_text) {kisa_ozet(ozet)} kilitteki bildirim_sha256"
                    f" {kisa_ozet(kilit.bildirim_sha256)} degil"
                )
        if v.bildirim_dosyasi is None:
            bulgular.append(f"{ad}: staged notice.txt yok")
        elif v.bildirim_dosyasi != beklenen:
            bulgular.append(f"{ad}: staged notice.txt dosyadaki bildirim blogundan farkli")
        try:
            _, baslik_surumu = bildirim_basligi(beklenen)
        except GirdiHatasi:
            bulgular.append(f"{ad}: bildirim basligi (tur ve surum) cozulemedi")
        else:
            if kayit.surum != baslik_surumu:
                bulgular.append(
                    f"{ad}: kayit surumu {_g(kayit.surum)} dosya basligindaki"
                    f" {_g(baslik_surumu)} ile ayni degil"
                )
            if kilit.surum != baslik_surumu:
                bulgular.append(f"{ad}: kilit surumu dosya basligindaki surumle ayni degil")
        if v.ingest_surum is not None and v.ingest_surum != kayit.surum:
            bulgular.append(f"{ad}: ingest manifestindeki surum kayit surumuyle ayni degil")
        if kayit.kaynak_url != kilit.url:
            bulgular.append(f"{ad}: kayit kaynak_url degeri kilitteki url ile ayni degil")
    return KapiSonucu("G-KAY", tuple(bulgular), sayilar)


# --- kelime satirlari (A11.2, K-43) ------------------------------------------------------


def _kelime_gruplari(g: QaGirdisi) -> dict[tuple[int, int], list[Satir]]:
    """Kelime satirlari `(sure, ayet)` ile gruplanir (dosya sirasi korunur)."""
    gruplar: dict[tuple[int, int], list[Satir]] = {}
    for satir in g.kelime_satirlari:
        gruplar.setdefault((satir.sayi("surah"), satir.sayi("ayah")), []).append(satir)
    return gruplar


def _ayet_haritasi(g: QaGirdisi, alan: str) -> dict[tuple[int, int], Satir]:
    """`(sure, ayet) -> anchor satiri`; gecersiz capalar atlanir (G-CAP bildirir)."""
    harita: dict[tuple[int, int], Satir] = {}
    for satir in g.anchor_satirlari:
        konum = ayet_coz(satir.metin("anchor"))
        if konum is not None and satir.var(alan):
            harita[konum] = satir
    return harita


def _kelime_but(g: QaGirdisi) -> tuple[list[str], dict[str, int]]:
    """Kelime satirlarinin G-BUT denetimleri: dilim, ortusme, numara, kapsam, yeniden uretim."""
    satirlar = g.kelime_satirlari
    if not satirlar:
        return ["kelime satirlari: words.jsonl bos ya da okunmadi"], {"kelime": 0}
    ayetler = _ayet_haritasi(g, "text")
    gruplar = _kelime_gruplari(g)
    dilim: list[str] = []
    ortusme: list[str] = []
    numara: list[str] = []
    ayetsiz: list[str] = []
    for konum, grup in gruplar.items():
        ayet = ayetler.get(konum)
        if ayet is None:
            ayetsiz += [s.metin("anchor") for s in grup]
            continue
        metin = ayet.metin("text")
        onceki_son = 0
        for sira, satir in enumerate(grup, start=1):
            capa = satir.metin("anchor")
            bas, son = satir.sayi("char_start"), satir.sayi("char_end")
            if satir.sayi("word") != sira:
                numara.append(capa)
            if not 0 <= bas < son <= len(metin) or metin[bas:son] != satir.metin("text_uthmani"):
                dilim.append(capa)
            if bas < onceki_son:
                ortusme.append(capa)
            onceki_son = max(onceki_son, son)
    kelimesiz = sorted(f"q:{sure}:{ayet}" for sure, ayet in ayetler if (sure, ayet) not in gruplar)
    bulgular: list[str] = []
    for ad, liste, neden in (
        ("kelime dilim", dilim, "metin ayet metninin [char_start, char_end) dilimi degil"),
        ("kelime ortusme", ortusme, "aralik onceki kelimenin araligiyla ortusuyor"),
        ("kelime numarasi", numara, "numara ayet icinde 1'den kesintisiz degil"),
        ("kelimesi olmayan ayet", kelimesiz, "ayetin hic kelime satiri yok"),
        ("kelime ayeti", ayetsiz, "kelimenin ayeti anchor satirlarinda yok"),
    ):
        if liste:
            bulgular.append(f"{ad}: {len(liste)} birim: {neden}: {_capalar(liste)}")
    try:
        beklenen = {
            str(r["anchor"]): r
            for r in kelimelere_bolunmus([s.veri for s in g.anchor_satirlari], g.uthmani_surumu)
        }
    except GirdiHatasi as hata:
        bulgular.append(f"kelime bolme kurali uygulanamadi: {_g(hata, 120)}")
    else:
        var = {s.metin("anchor"): s.veri for s in satirlar}
        farkli = sorted(c for c, v in var.items() if c in beklenen and not _esit(v, beklenen[c]))
        for ad, liste in (
            ("bolme kuralindan uretilenden farkli kelime satiri", farkli),
            ("kuralda olup words.jsonl'de olmayan kelime", sorted(set(beklenen) - set(var))),
            ("words.jsonl'de olup kuralda olmayan kelime", sorted(set(var) - set(beklenen))),
        ):
            if liste:
                bulgular.append(f"{ad}: {len(liste)} birim: {_capalar(liste)}")
    return bulgular, {"kelime": len(satirlar), "kelime_ayet": len(gruplar)}


def _kelime_cap(g: QaGirdisi) -> tuple[list[str], dict[str, int]]:
    """Kelime capalarinin G-CAP denetimleri: gramer, teklik, sira, alan tutarliligi."""
    ayet_sirasi = {konum: s.sayi("ord") for konum, s in _ayet_haritasi(g, "ord").items()}
    data_version = f"{KAYNAK}@{g.uthmani.kayit.surum}"
    gecersiz: list[str] = []
    tekrar: list[str] = []
    tutarsiz: list[str] = []
    sabit: list[str] = []
    gorulen: set[str] = set()
    anahtarlar: list[tuple[SortKey, str]] = []
    for satir in g.kelime_satirlari:
        capa = satir.metin("anchor")
        if capa in gorulen:
            tekrar.append(capa)
        gorulen.add(capa)
        try:
            ref = parse(capa)
            kanonik = anchor_format(ref) == capa
        except (AnchorError, ValueError):
            gecersiz.append(capa)
            continue
        cozulen = ref.anchor
        if (
            not kanonik
            or ref.span is not None
            or not isinstance(cozulen, Q)
            or cozulen.ilk is None
            or cozulen.son is not None
        ):
            gecersiz.append(capa)
            continue
        anahtarlar.append((sort_key(ref), capa))
        if (
            satir.sayi("surah") != cozulen.sure
            or satir.sayi("ayah") != cozulen.ayet
            or satir.sayi("word") != cozulen.ilk
            or ayet_sirasi.get((cozulen.sure, cozulen.ayet)) != satir.sayi("ayah_index")
        ):
            tutarsiz.append(capa)
        if satir.metin("source_id") != KAYNAK or satir.metin("data_version") != data_version:
            sabit.append(capa)
    siralama = [
        capa for (onceki, _), (simdiki, capa) in pairwise(anahtarlar) if not onceki < simdiki
    ]
    bulgular: list[str] = []
    for ad, liste, neden in (
        ("gecersiz kelime capasi", gecersiz, "kanonik bir q:{sure}:{ayet}:{kelime} capasi degil"),
        ("yinelenen kelime capasi", tekrar, "capa birden fazla satirda"),
        ("kelime okuma sirasi", siralama, "satir onceki capadan sonra gelmiyor"),
        ("kelime alanlari", tutarsiz, "surah, ayah, word ya da ayah_index capayla tutmuyor"),
        ("kelime sabit alani", sabit, "source_id ya da data_version yanlis"),
    ):
        if liste:
            bulgular.append(f"{ad}: {len(liste)} birim: {neden}: {_capalar(liste)}")
    return bulgular, {"kelime_capa": len(gorulen)}


def _kelime_nor(g: QaGirdisi) -> list[str]:
    """Her kelimenin `norm` degeri `normalize_ar(text_uthmani)` ile ayni ve bos degil."""
    farkli = [
        s.metin("anchor")
        for s in g.kelime_satirlari
        if s.metin("norm") != normalize_ar(s.metin("text_uthmani"))
    ]
    bos = [s.metin("anchor") for s in g.kelime_satirlari if s.metin("norm") == ""]
    bulgular: list[str] = []
    if farkli:
        bulgular.append(
            f"kelime norm: {len(farkli)} birim: normalize_ar(text_uthmani) ile ayni degil:"
            f" {_capalar(farkli)}"
        )
    if bos:
        bulgular.append(f"bos kelime norm: {len(bos)} birim: {_capalar(bos)}")
    return bulgular


# --- G-BUT -------------------------------------------------------------------------------


def g_but(g: QaGirdisi) -> KapiSonucu:
    """Sayilar, bos birim, kontrol karakteri ve ham dosyayla bayt esitligi (K-26)."""
    tablo = tuple(g.sure_tablosu)
    bulgular = _tablo_bulgulari(g.depo_kok)

    satirlar = g.anchor_satirlari
    konumlar = [ayet_coz(s.metin("anchor")) for s in satirlar]
    sayim = Counter(k[0] for k in konumlar if k is not None)
    bulgular += _sayim_bulgulari("anchor satirlari", sayim, len(satirlar), tablo)
    for v in (g.uthmani, g.simple):
        ham_sayim = Counter(ay.sure for ay in v.ayrisma.ayetler)
        bulgular += _sayim_bulgulari(
            f"{v.kaynak} ham dosya", ham_sayim, len(v.ayrisma.ayetler), tablo
        )

    harita = {ay.capa: ay for ay in g.uthmani.ayrisma.ayetler}
    ham = g.uthmani.ham
    dosya = dosya_adi("uthmani")
    bos: list[str] = []
    kontrol: list[str] = []
    farkli: list[str] = []
    yersiz: list[str] = []
    kokensiz: list[str] = []
    adimli: list[str] = []
    gorulen: set[str] = set()
    for satir in satirlar:
        capa, metin = satir.metin("anchor"), satir.metin("text")
        if _bos(metin):
            bos.append(capa)
        if KONTROL.search(metin):
            kontrol.append(capa)
        if satir.nesne("provenance").get("steps") != []:
            adimli.append(capa)
        ay = harita.get(capa)
        if ay is None:
            yersiz.append(capa)
            continue
        gorulen.add(capa)
        if _baytlar(metin) != ham[ay.bayt_bas : ay.bayt_son]:
            farkli.append(capa)
        kok = satir.nesne("provenance")
        if not all(
            _esit(kok.get(alan), beklenen)
            for alan, beklenen in (
                ("file", dosya),
                ("sha256", g.uthmani.ham_sha256),
                ("line", ay.satir),
                ("bayt", [ay.bayt_bas, ay.bayt_son]),
            )
        ):
            kokensiz.append(capa)
    eksik = [capa for capa in harita if capa not in gorulen]
    for ad, liste, neden in (
        ("bos birim", bos, "metin bos"),
        ("kontrol karakteri", kontrol, "metinde kontrol karakteri (Cc) var"),
        ("bayt esitligi", farkli, "metin ham dosyanin bayt dilimiyle ayni degil"),
        ("ham dosyada karsiligi", yersiz, "ham dosyada bu capa yok"),
        ("provenance", kokensiz, "provenance (file, sha256, line, bayt) ham dosyayla tutmuyor"),
        ("donusum adimi", adimli, "provenance.steps bos degil (kanonik metne donusum uygulanmis)"),
        ("eksik birim", eksik, "ham dosyadaki ayet anchor satirlarinda yok"),
    ):
        if liste:
            bulgular.append(f"{ad}: {len(liste)} birim: {neden}: {_capalar(liste)}")

    for v in (g.uthmani, g.simple):
        if v.ham_sha256 != v.kilit.sha256 or len(v.ham) != v.kilit.boyut:
            bulgular.append(f"{v.kaynak}: ham dosya kilitteki sha256 ve boyutla tutmuyor")
        if v.ayrisma.metin_sha256 != v.kilit.metin_sha256:
            bulgular.append(f"{v.kaynak}: ayet satirlari kilitteki metin_sha256 ile tutmuyor")
        if v.ayrisma.bildirim_sha256 != v.kilit.bildirim_sha256:
            bulgular.append(f"{v.kaynak}: bildirim blogu kilitteki bildirim_sha256 ile tutmuyor")
    kelime_bulgulari, kelime_sayilari = _kelime_but(g)
    bulgular += kelime_bulgulari
    sayilar = {
        "birim": len(satirlar),
        "sure": len(sayim),
        "ham_uthmani_ayet": len(g.uthmani.ayrisma.ayetler),
        "ham_simple_clean_ayet": len(g.simple.ayrisma.ayetler),
        "bos_birim": len(bos),
        "kontrol_karakteri": len(kontrol),
        "bayt_farki": len(farkli),
        **kelime_sayilari,
    }
    return KapiSonucu("G-BUT", tuple(bulgular), sayilar)


# --- G-CAP -------------------------------------------------------------------------------


def _beklenen_capalar(tablo: Sequence[int]) -> list[str]:
    return [
        anchor_format(AnchorRef(Q(sure, ayet)))
        for sure, adet in enumerate(tablo, start=1)
        for ayet in range(1, adet + 1)
    ]


def g_cap(g: QaGirdisi) -> KapiSonucu:
    """Capa gramer, teklik, sira, tam kume, ord/ayah, content_hash ve onceki capalar."""
    bulgular: list[str] = []
    satirlar = g.anchor_satirlari
    gecersiz: list[str] = []
    tekrar: list[str] = []
    gorulen: set[str] = set()
    anahtarlar: list[tuple[SortKey, str]] = []
    sira_hatasi: list[str] = []
    ozet_hatasi: list[str] = []
    ozet_yanlis: list[str] = []
    sabit_hatasi: list[str] = []
    data_version = f"{KAYNAK}@{g.uthmani.kayit.surum}"
    for satir in satirlar:
        capa = satir.metin("anchor")
        if capa in gorulen:
            tekrar.append(capa)
        gorulen.add(capa)
        konum = ayet_coz(capa)
        if konum is None:
            gecersiz.append(capa)
            continue
        anahtarlar.append((sort_key(parse(capa)), capa))
        sure, ayet = konum
        if sure > len(g.sure_tablosu):
            sira_hatasi.append(capa)
        else:
            beklenen = g.baslangic[sure - 1] + ayet
            if (
                satir.sayi("ord") != beklenen
                or satir.sayi("ayah_lo") != beklenen
                or satir.sayi("ayah_hi") != beklenen + 1
            ):
                sira_hatasi.append(capa)
        ozet, metin = satir.metin("content_hash"), satir.metin("text")
        if OZET_DESENI.fullmatch(ozet) is None:
            ozet_hatasi.append(capa)
        elif _baytlar(metin) is None or ozet != content_hash(metin):
            ozet_yanlis.append(capa)
        if (
            satir.metin("kind") != KIND
            or satir.metin("source_id") != KAYNAK
            or satir.metin("metin_durumu") != METIN_DURUMU
            or satir.metin("data_version") != data_version
        ):
            sabit_hatasi.append(capa)
    siralama: list[str] = []
    for (onceki, _), (simdiki, capa) in pairwise(anahtarlar):
        if not onceki < simdiki:
            siralama.append(capa)
    beklenen_kume = set(_beklenen_capalar(g.sure_tablosu))
    var = set(gorulen)
    eksik = sorted(beklenen_kume - var)
    fazla = sorted(var - beklenen_kume - set(gecersiz))
    for ad, liste, neden in (
        ("gecersiz capa", gecersiz, "kanonik bir q:{sure}:{ayet} capasi degil"),
        ("yinelenen capa", tekrar, "capa birden fazla satirda"),
        ("okuma sirasi", siralama, "satir onceki capadan sonra gelmiyor"),
        ("eksik capa", eksik, "beklenen capa satirlarda yok"),
        ("fazla capa", fazla, "tablodaki ayetlerden biri degil"),
        ("ord/ayah", sira_hatasi, "ord, ayah_lo ya da ayah_hi kuresel siradan farkli"),
        ("content_hash biciminde", ozet_hatasi, "64 haneli kucuk harfli onaltilik degil"),
        ("content_hash", ozet_yanlis, "metnin SHA-256'siyla tutmuyor"),
        ("sabit alan", sabit_hatasi, "kind, source_id, metin_durumu ya da data_version yanlis"),
    ):
        if liste:
            bulgular.append(f"{ad}: {len(liste)} birim: {neden}: {_capalar(liste)}")

    kelime_bulgulari, kelime_sayilari = _kelime_cap(g)
    bulgular += kelime_bulgulari
    sayilar = {
        "capa": len(var),
        "beklenen_capa": len(beklenen_kume),
        "onceki_run": 0,
        **kelime_sayilari,
    }
    if g.onceki is not None:
        sayilar["onceki_run"] = 1
        simdiki_ozetler = {s.metin("anchor"): s.metin("content_hash") for s in satirlar}
        kayip = sorted(c for c in g.onceki.ozetler if c not in simdiki_ozetler)
        degisen = sorted(
            c
            for c, ozet in g.onceki.ozetler.items()
            if c in simdiki_ozetler and simdiki_ozetler[c] != ozet
        )
        sayilar["onceki_capa"] = len(g.onceki.ozetler)
        if kayip:
            bulgular.append(
                f"onceki surumde olup kaybolan capa: {len(kayip)} birim: {_capalar(kayip)}"
            )
        if degisen:
            bulgular.append(
                f"onceki surumle content_hash farkli: {len(degisen)} birim: {_capalar(degisen)}"
            )
    return KapiSonucu("G-CAP", tuple(bulgular), sayilar)


# --- G-NOR -------------------------------------------------------------------------------


def g_nor(g: QaGirdisi) -> KapiSonucu:
    """Vektorler Python'da gecer; `ar_norm` (AR-4) ve `provenance.ar_norm` yeniden uretilir."""
    bulgular: list[str] = []
    vektor = vektorleri_calistir(g.depo_kok)
    if vektor.kalan:
        bulgular.append(
            f"normalizasyon vektoru: {len(vektor.kalan)}/{vektor.toplam} kaldi:"
            f" {_capalar(vektor.kalan)}"
        )
    cifter = g.normalize_cifti
    simple_satir = {ay.capa: ay for ay in g.simple.ayrisma.ayetler}
    farkli: list[str] = []
    bos: list[str] = []
    kokensiz: list[str] = []
    tr_dolu: list[str] = []
    for satir in g.anchor_satirlari:
        capa = satir.metin("anchor")
        cift = cifter.get(capa)
        s_ay = simple_satir.get(capa)
        if cift is None or s_ay is None:
            farkli.append(capa)
            continue
        ar_norm = satir.metin("ar_norm")
        if ar_norm != ar4_birlestir(cift[0], cift[1])[0]:
            farkli.append(capa)
        if ar_norm == "":
            bos.append(capa)
        beklenen_kok = {
            "kaynak": EK_KAYNAK,
            "sha256": g.simple.ham_sha256,
            "line": s_ay.satir,
            "normalizer_version": NORMALIZER_VERSION,
            "ar4": True,
        }
        if not _esit(satir.nesne("provenance").get("ar_norm"), beklenen_kok):
            kokensiz.append(capa)
        if any(satir.veri.get(alan) not in (None, "") for alan in TR_ALANLARI):
            tr_dolu.append(capa)
    for ad, liste, neden in (
        ("ar_norm", farkli, "ham dosyalardan AR-4 ile uretilen degerle ayni degil"),
        ("bos ar_norm", bos, "ar_norm bos"),
        (
            "provenance.ar_norm",
            kokensiz,
            "kaynak, sha256, line, normalizer_version ya da ar4 yanlis",
        ),
        ("tr alani", tr_dolu, "Kur'an biriminde tr_* alani bos olmali"),
    ):
        if liste:
            bulgular.append(f"{ad}: {len(liste)} birim: {neden}: {_capalar(liste)}")
    bulgular += _kelime_nor(g)
    sayilar = {
        "vektor": vektor.toplam,
        "vektor_kalan": len(vektor.kalan),
        "ar_norm_farki": len(farkli),
    }
    return KapiSonucu("G-NOR", tuple(bulgular), sayilar)


KAPI_ISLEVLERI: Final[dict[str, Callable[[QaGirdisi], KapiSonucu]]] = {
    "G-KAY": g_kay,
    "G-BUT": g_but,
    "G-CAP": g_cap,
    "G-NOR": g_nor,
}


# --- olcumler (kapi degil; rapora yazilir) -----------------------------------------------


def _ar8(v: Varyant) -> dict[str, int]:
    sayim = dict.fromkeys((ad for ad, _, _ in AR8_ARALIKLARI), 0)
    for harf, adet in v.harf_sayimi.items():
        kod = ord(harf)
        for ad, bas, son in AR8_ARALIKLARI:
            if bas <= kod <= son:
                sayim[ad] += adet
    return sayim


def _mn_kalan(normalize_metinler: Sequence[str]) -> dict[str, int]:
    """Normalizasyondan sonra kalan birlesen isaretler (Mn): `U+XXXX -> adet`."""
    sayim = Counter("".join(normalize_metinler))
    return {
        f"U+{ord(harf):04X}": adet
        for harf, adet in sorted(sayim.items())
        if unicodedata.category(harf) == "Mn"
    }


def _besmele(v: Varyant, tablo: Sequence[int]) -> dict[str, object]:
    """Besmele ayri satir mi, ilk ayetin parcasi mi; ilk dort belirtec 1:1 ile ayni mi."""
    ayetler = v.ayrisma.ayetler
    ilk_ayetler = {ay.sure: ay.metin for ay in ayetler if ay.ayet == 1}
    referans = ilk_ayetler.get(1)
    sonuc: dict[str, object] = {"ayri_besmele_satiri": len(ayetler) > sum(tablo)}
    if referans is None:
        return sonuc
    belirtecler = referans.split(" ")
    ilk_dort = belirtecler[:BESMELE_BELIRTEC]
    ilk_dort_norm = [normalize_ar(b) for b in ilk_dort]
    ayni: list[int] = []
    yazim_farki: list[int] = []
    farkli: list[int] = []
    for sure in sorted(ilk_ayetler):
        if sure == 1:
            continue
        aday = ilk_ayetler[sure].split(" ")[:BESMELE_BELIRTEC]
        if aday == ilk_dort:
            ayni.append(sure)
        elif [normalize_ar(b) for b in aday] == ilk_dort_norm:
            yazim_farki.append(sure)
        else:
            farkli.append(sure)
    sonuc.update(
        {
            "fatiha_ilk_ayet_belirtec": len(belirtecler),
            "karsilastirilan_sure": len(ayni) + len(yazim_farki) + len(farkli),
            "ilk_dort_belirtec_ayni_bayt": len(ayni),
            "yazim_farki_sureler": yazim_farki,
            "farkli_sureler": farkli,
        }
    )
    return sonuc


def _json_ile_ayni(v: Varyant, sayilar: Sequence[int]) -> bool:
    """Ham dosyanin sure sure ayet sayisi `sayilar` dizisiyle ayni mi (sure sayisi dahil)."""
    sayim = Counter(ay.sure for ay in v.ayrisma.ayetler)
    return len(v.ayrisma.ayetler) == sum(sayilar) and all(
        sayim.get(sure, 0) == adet for sure, adet in enumerate(sayilar, start=1)
    )


def _json_olcumu(g: QaGirdisi) -> dict[str, object]:
    """`shared/data/ayet-sayilari.json` dizisi: iki ham dosyanin sayimi, kodun tablosu, uc kopya.

    Kapi karari G-BUT'tadir; bu olcum raporda kanittir (A04'un dizisi Tanzil sayimiyla ayni mi).
    """
    try:
        belge = ayet_sayilari.json_oku(g.depo_kok)
        kopyalar = ayet_sayilari.denetle(g.depo_kok)
    except GirdiHatasi:
        return {"okundu": False}
    return {
        "okundu": True,
        "eleman": len(belge.sayilar),
        "toplam": sum(belge.sayilar),
        "uthmani_ile_ayni": _json_ile_ayni(g.uthmani, belge.sayilar),
        "simple_clean_ile_ayni": _json_ile_ayni(g.simple, belge.sayilar),
        "kodun_tablosuyla_ayni": belge.sayilar == tuple(AYET_SAYILARI),
        "kopyalar_ayni": not kopyalar,
    }


def _kelime_olcumu(g: QaGirdisi) -> dict[str, object]:
    """Kelime bolmesi (K-43): toplam kelime, kelimeli ayet ve birlestirme listesi (kapi degil)."""
    return {
        "toplam": len(g.kelime_satirlari),
        "ayet": len(_kelime_gruplari(g)),
        "birlestirme": sorted(f"{s}:{a}:{i}" for (s, a), i in BIRLESTIRME.items()),
    }


def olcumler(g: QaGirdisi) -> dict[str, object]:
    """Rapora yazilan olcumler: NFC (bilgi), AR-8, Mn, besmele, AR-4, ayet sayilari (kapi degil)."""
    cifter = g.normalize_cifti
    tablo = tuple(g.sure_tablosu)
    sonuc: dict[str, object] = {}
    sonuc["nfc"] = {
        v.kaynak: {
            "nfc_olmayan_ayet": sum(
                1 for ay in v.ayrisma.ayetler if not unicodedata.is_normalized("NFC", ay.metin)
            )
        }
        for v in (g.uthmani, g.simple)
    }
    ar8 = {v.kaynak: _ar8(v) for v in (g.uthmani, g.simple)}
    sonuc["ar8"] = ar8
    sonuc["ar8_gorulen"] = any(adet for sayim in ar8.values() for adet in sayim.values())
    mn = {
        g.simple.kaynak: _mn_kalan([c[0] for c in cifter.values()]),
        g.uthmani.kaynak: _mn_kalan([c[1] for c in cifter.values()]),
    }
    sonuc["mn_kalan"] = mn
    sonuc["mn_kalan_gorulen"] = any(bool(sayim) for sayim in mn.values())
    sonuc["besmele"] = {v.kaynak: _besmele(v, tablo) for v in (g.uthmani, g.simple)}
    ek_ayet = ek_sozcuk = 0
    for simple_norm, uthmani_norm in cifter.values():
        eklenen = ar4_birlestir(simple_norm, uthmani_norm)[1]
        ek_ayet += 1 if eklenen else 0
        ek_sozcuk += eklenen
    sonuc["ar4"] = {"ek_sozcuklu_ayet": ek_ayet, "ek_sozcuk": ek_sozcuk}
    sonuc["ayet_sayilari"] = {
        v.kaynak: {
            "sure": len({ay.sure for ay in v.ayrisma.ayetler}),
            "ayet": len(v.ayrisma.ayetler),
        }
        for v in (g.uthmani, g.simple)
    }
    sonuc["ayet_sayilari_json"] = _json_olcumu(g)
    sonuc["kelime"] = _kelime_olcumu(g)
    return sonuc
