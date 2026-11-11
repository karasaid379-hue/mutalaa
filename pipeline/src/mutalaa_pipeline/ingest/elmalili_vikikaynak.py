# ruff: noqa: RUF001, RUF002
"""Vikikaynak bagdastiricisi (A16.2): `elmalili-meal`, orijinal meal (K-49 madde 1, 7, 8).

`mutalaa ingest meal --source elmalili-meal`:

1. `data/gelen/elmalili-meal/<tarih>/` altindaki MediaWiki API yanitlari (`vikikaynak-NN.json`) ve
   `basliklar.tsv` bayt olarak okunur ve `elmalili_meal.lock.json` ile karsilastirilir (boyut,
   SHA-256). Tutmazsa cikis 2. Kilitten sonra 114 sayfanin her biri kilitle sayfa sayfa
   karsilastirilir: baslik, `revid`, MediaWiki `sha1` ve wikitext SHA-256 (sure numarasi kilitteki
   ACIK eslemedir; baslik burada ayristirilmaz). Dosyalar `data/raw`'a kopyalanir.
2. Her sayfanin wikitext'i `mwparserfromhell` ile ayristirilir ve ACIK kural tablosuyla okunur:
   her sablon ve etiket icin "at", "ilk parametreyi tut", "bosluk yap", "icerigi ac" ya da
   "ham tut" kurali vardir; tabloda olmayan sablon, etiket ya da dugum turu cikis 2 verir. Ayet
   isareti `{{kısım||N}}` METNIN ONUNDE gelir (metin sonraki isarete kadar).
3. Sinir kurallari (K-49 madde 8; hepsi `uyari` kodu tasir ve incelemede gorunur):
   * `N-M` araligi: baş birim metni tasir ve `attrs.kapsam = "q:{s}:{N}-{M}"`; izleyen birimler bos
     metin ve `attrs.birlesik_ile = "meal:elmalili:{s}:{N}"` tasir.
   * `,` (numarasiz isaret): metin onceki numarali ayetin birimine tek U+0020 ile eklenir.
   * Ayni numarali iki isaret (Nisa 68): parcalar sirasiyla tek U+0020 ile birlestirilir.
   * Numara sirasi bozuksa (sonraki isaret onceki + 1 degilse) birim `sira_disi` uyarisi tasir.
   * `besmele` isareti (yalniz bu acik isaretle; sure 1 ve 9'da yoktur): metin
     `attrs.besmele_meali = {metin, content_hash}` olur (ayet 1 biriminde).
   * Ilk isaretten onceki ve son ayetten sonraki sayfa icerigi metne alinmaz; yalniz sayfa
     basina uzunluk ve ozet olarak manifeste yazilir (`bolgeler`).
4. Satir sonu kurali: CRLF ve CR -> LF; bir parcanin icinde tek LF -> U+0020, iki ya da daha
   cok ardisik LF -> tek LF; kenarlardan yalniz U+0020, U+0009, U+000A kirpilir. `str.split()`,
   `str.strip()` (argumansiz) ve `\\s` kullanilmaz (U+00A0 korunur); sayilar `[0-9]` ile okunur.
5. Kanonik metin: birlestirilmis metne `kanonik_metin` ilk kayit olarak BIR KEZ uygulanir (NFC
   yalniz burada; K-35 madde 7). Konum `provenance.konum`: kilitli revizyonun wikitext dizgisinde
   yari acik kod noktasi araliklarinin listesi ve parca ayiricisi; `@` ofseti degildir.

Cikti dogrudan `meal:elmalili:{sure}:{ayet}` birimleridir (6.236 birim; ayet sayisi Tanzil'le
birebir). Hata iletileri yalniz sure no, sayi ve alan adi tasir; metin asla.
"""

import hashlib
import re
import unicodedata
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

import mwparserfromhell
from mwparserfromhell.nodes import (
    Comment,
    HTMLEntity,
    Tag,
    Template,
    Text,
)
from mwparserfromhell.wikicode import Wikicode

from mutalaa_pipeline import lineage
from mutalaa_pipeline.anchor import (
    AnchorRef,
    Meal,
    Qa,
    content_hash,
    kanonik_metin,
    silinecekleri_sil,
)
from mutalaa_pipeline.anchor import format as anchor_format
from mutalaa_pipeline.anchor.ayet_sayilari import AYET_SAYILARI
from mutalaa_pipeline.export.ortak import GirdiHatasi, kati_json
from mutalaa_pipeline.ingest import meal_ortak
from mutalaa_pipeline.ingest.base import RawFile, StagedUnit
from mutalaa_pipeline.ingest.meal_kaynaklari import BOLUM_VIKIKAYNAK, KAYNAK_ORIJINAL, capa_eseri
from mutalaa_pipeline.ingest.meal_kilit import (
    LISTE_DOSYASI,
    MealKilidi,
    SayfaKilidi,
    VikikaynakKilidi,
    kilit_ozeti,
    kilit_yukle,
)
from mutalaa_pipeline.normalize import lower_turkish
from mutalaa_pipeline.runctx import RunContext

CIKARICI_SURUMU: Final = "1"
KAYNAK: Final = KAYNAK_ORIJINAL
EN_DERIN_SABLON: Final = 4
AYIRICI: Final = " "  # birlestirilen parcalarin ayiricisi (U+0020)

# Ayet isareti degerleri.
ISARET_TEK: Final = re.compile(r"[1-9][0-9]{0,2}")
ISARET_ARALIK: Final = re.compile(r"([1-9][0-9]{0,2})-([1-9][0-9]{0,2})")
NUMARASIZ: Final = ","
BESMELE: Final = "besmele"
BESMELESIZ_SURELER: Final = frozenset({1, 9})  # sure 1'de besmele ayettir, sure 9'da yoktur

# Uyari kodlari (incelemede `onerilen.uyari`; K-49 madde 8 ve 9).
UYARI_NUMARASIZ: Final = "numarasiz_parca"
UYARI_YINELENEN: Final = "yinelenen_numara"
UYARI_SIRA_DISI: Final = "sira_disi"
UYARI_BIRLESIK: Final = "birlesik_meal"
UYARI_BESMELE: Final = "besmele_meali"
UYARI_ORTAK_METIN: Final = "ortak_metin"

# --- acik kural tablosu --------------------------------------------------------------------
# Anahtar: `_ad_anahtari` ile katlanmis sablon/etiket adi. Tabloda olmayan her sey cikis 2 verir.
KURAL_AT: Final = "at"  # dugum ve icerigi metne girmez
KURAL_ILK_PARAMETRE: Final = "ilk-parametre"  # tek parametreli sablon: 1. parametrenin icerigi
KURAL_BOSLUK: Final = "bosluk"  # tek U+0020
KURAL_ICERIGI_AC: Final = "icerigi-ac"  # etiket atilir, icerigi okunur
KURAL_HAM: Final = "ham"  # icerik ayristirilmadan aynen
KURAL_ISARET: Final = "isaret"  # ayet isareti

SABLON_KURALLARI: Final[Mapping[str, str]] = {
    "eser başlığı": KURAL_AT,  # sayfa ust bilgisi (alan listesi), metne alinmaz
    "ortalı ve hizalı": KURAL_ILK_PARAMETRE,  # bazi sayfalarda butun metni sarar
    "kısım": KURAL_ISARET,
}
ETIKET_KURALLARI: Final[Mapping[str, str]] = {
    "ref": KURAL_AT,
    "br": KURAL_BOSLUK,
    "nowiki": KURAL_HAM,
    "i": KURAL_ICERIGI_AC,  # '' ... ''
    "b": KURAL_ICERIGI_AC,  # ''' ... '''
}
# Son ayetten sonra tek basina duran, eslesmemis kapanis etiketleri (sayfa sonu bolgesi).
SAYFA_SONU_KAPANISLARI: Final = ("</div>",)
# Metin icinde kalmamasi gereken wikitext artiklari (bozuk ya da bilinmeyen kod: cikis 2).
ARTIK_KARAKTERLER: Final = frozenset("{}<>")
REVID: Final = re.compile(r"[0-9]{1,9}")
_BOS_SATIR: Final = re.compile(r"\n[ \t]*\n")
_LF_DIZISI: Final = re.compile(r"[ \t]*\n(?:[ \t]*\n)*[ \t]*")
_KIRPILACAK: Final = " \t\n"  # U+0020, U+0009, U+000A (U+00A0 korunur)


# --- yardimcilar ---------------------------------------------------------------------------


def kirp(metin: str) -> str:
    """Bastan ve sondan yalniz U+0020, U+0009, U+000A; argumansiz `strip()` U+00A0'i da keserdi."""
    return metin.strip(_KIRPILACAK)


def ad_anahtari(ad: str) -> str:
    """Sablon ya da etiket adinin kural anahtari: kenar bosluklari, `_` ve Turkce kucuk harf."""
    return lower_turkish(kirp(ad.replace("_", " ")))


def satir_sonlari(metin: str) -> str:
    """Satir sonu kurali: CRLF ve CR -> LF; tek LF -> U+0020; iki ya da daha cok LF -> tek LF."""
    duz = metin.replace("\r\n", "\n").replace("\r", "\n")
    return _LF_DIZISI.sub(lambda e: " " if e.group().count("\n") == 1 else "\n", duz)


def parca_metni(parcalar: Sequence[str]) -> str:
    """Bir isaretin metin parcalarindan temiz parca metni (kanonik hale getirilmeden once).

    Sira (K-35 madde 7): once silinecek karakterler (U+FEFF, U+00AD, U+200E/F, U+202A-E,
    U+2066-9, U+061C), sonra satir sonu kurali; NFC birlestirilmis metne `kanonik_metin` ile
    bir kez uygulanir. Boylece silinen bir karakter iki satir sonunu ayirip kurali sasirtmaz.
    """
    return satir_sonlari(kirp(silinecekleri_sil("".join(parcalar))))


def _bolge_ozeti(metin: str) -> dict[str, object] | None:
    """Metin bolgesinin uzunlugu (kod noktasi) ve SHA-256'si; yalniz bosluk ise None."""
    govde = kirp(metin)
    if govde == "":
        return None
    return {"uzunluk": len(govde), "sha256": lineage.sha256_bayt(govde.encode("utf-8"))}


# --- dugum yuruyusu --------------------------------------------------------------------------


@dataclass(frozen=True)
class _Olay:
    tur: str  # "metin" ya da "isaret"
    metin: str
    bas: int  # wikitext'te yari acik kod noktasi araligi [bas, son)
    son: int
    tam: bool  # True: metin wikitext[bas:son] dilimidir (ayni konumda kesilebilir)


def _sablon_parametre_tabani(sablon: Template, parametre: object, taban: int) -> int:
    """Sablonun bir parametre degerinin wikitext'teki baslangic konumu."""
    konum = taban + 2 + len(str(sablon.name))
    for oge in sablon.params:
        konum += 1  # '|'
        if oge is parametre:
            if oge.showkey:
                konum += len(str(oge.name)) + 1
            return konum
        konum += len(str(oge))
    raise GirdiHatasi("sablon parametresi bulunamadi")


def _isaret_degeri(sablon: Template) -> str:
    """`{{kısım||N}}`: ilk parametre bos, ikincisi isaret degeri; baska bicim cikis 2."""
    oge = list(sablon.params)
    if (
        len(oge) != 2
        or any(p.showkey for p in oge)
        or [str(p.name) for p in oge] != ["1", "2"]
        or kirp(str(oge[0].value)) != ""
    ):
        raise GirdiHatasi("kisim sablonu {{kisim||N}} biciminde degil")
    return kirp(str(oge[1].value))


def _yuru(
    kod: Wikicode,
    taban: int,
    wikitext: str,
    olaylar: list[_Olay],
    derinlik: int,
    kesin: bool = True,
) -> None:
    """Dugumleri sirayla kural tablosuyla okur; olaylar belge sirasindadir.

    `kesin`: `taban` konumu wikitext'te tam bilinir (sablon parametresi ve ust duzey metin).
    Etiket iclerinde (`''` isaretinin uzunlugu gibi) konum yaklasiktir: metin olaylari `tam`
    olmaz ve etiketin butun araligini gosterir.
    """
    if derinlik > EN_DERIN_SABLON:
        raise GirdiHatasi("wikitext cok derin ic ice")
    konum = taban
    for dugum in kod.nodes:
        ham = str(dugum)
        bas, son = konum, konum + len(ham)
        konum = son
        if isinstance(dugum, Text):
            if kesin and wikitext[bas:son] != ham:
                raise GirdiHatasi("metin konumu wikitext ile tutmuyor")
            olaylar.append(_Olay("metin", ham, bas, son, kesin))
        elif isinstance(dugum, Template):
            kural = SABLON_KURALLARI.get(ad_anahtari(str(dugum.name)))
            if kural is None:
                raise GirdiHatasi("bilinmeyen sablon (kural tablosunda yok)")
            if kural == KURAL_AT:
                continue
            if kural == KURAL_ISARET:
                if wikitext[bas:son] != ham:
                    raise GirdiHatasi("isaret konumu wikitext ile tutmuyor")
                olaylar.append(_Olay("isaret", _isaret_degeri(dugum), bas, son, True))
            elif kural == KURAL_ILK_PARAMETRE:
                oge = list(dugum.params)
                if len(oge) != 1 or oge[0].showkey or str(oge[0].name) != "1":
                    raise GirdiHatasi("sarmalayici sablon tek konumsal parametre tasimali")
                ic_taban = _sablon_parametre_tabani(dugum, oge[0], bas)
                if wikitext[ic_taban : ic_taban + len(str(oge[0].value))] != str(oge[0].value):
                    raise GirdiHatasi("sablon parametresi konumu wikitext ile tutmuyor")
                _yuru(oge[0].value, ic_taban, wikitext, olaylar, derinlik + 1, kesin)
            else:  # pragma: no cover - tablo ile tutarli
                raise GirdiHatasi("sablon kurali tanimsiz")
        elif isinstance(dugum, Tag):
            kural = ETIKET_KURALLARI.get(ad_anahtari(str(dugum.tag)))
            if kural is None:
                raise GirdiHatasi("bilinmeyen etiket (kural tablosunda yok)")
            if kural == KURAL_AT:
                continue
            if kural == KURAL_BOSLUK:
                olaylar.append(_Olay("metin", " ", bas, son, False))
            elif kural == KURAL_HAM:
                icerik = "" if dugum.contents is None else str(dugum.contents)
                olaylar.append(_Olay("metin", icerik, bas, son, False))
            elif kural == KURAL_ICERIGI_AC and dugum.contents is not None:
                ic: list[_Olay] = []
                _yuru(dugum.contents, bas, wikitext, ic, derinlik + 1, False)
                for o in ic:
                    if o.tur == "isaret":
                        raise GirdiHatasi("ayet isareti bir etiketin icinde")
                    olaylar.append(_Olay("metin", o.metin, bas, son, False))
        elif isinstance(dugum, HTMLEntity):
            olaylar.append(_Olay("metin", dugum.normalize(), bas, son, False))
        elif isinstance(dugum, Comment):
            continue  # yorum metne girmez
        else:
            raise GirdiHatasi(f"bilinmeyen dugum turu ({type(dugum).__name__})")


# --- sayfa cikarimi ------------------------------------------------------------------------


@dataclass(frozen=True)
class AyetTaslagi:
    """Bir sure sayfasindan cikan tek ayet birimi (capa daha sonra eklenir)."""

    sure: int
    ayet: int
    metin: str  # kanonik; birlesik izleyen birimde ""
    attrs: dict[str, object]
    uyari: tuple[str, ...]
    araliklar: tuple[tuple[int, int], ...]  # wikitext'te yari acik kod noktasi araliklari
    ayirici: str = AYIRICI


@dataclass(frozen=True)
class SayfaCikti:
    ayetler: tuple[AyetTaslagi, ...]  # ayet 1..N sirali
    isaret_sayisi: int
    on_bolge: dict[str, object] | None
    son_bolge: dict[str, object] | None


@dataclass(frozen=True)
class _Uye:
    """Bir isaretin cozulmus hali; `metin` bos olabilir (ardisik isaret grubu)."""

    parca: "_Parca"
    tur: str
    ilk: int
    son: int
    metin: str
    bitis: int


@dataclass
class _Parca:
    deger: str
    isaret_bas: int
    isaret_son: int
    olaylar: list[_Olay] = field(default_factory=list)


def _son_bolgeyi_ayir(olay: _Olay) -> tuple[_Olay, str]:
    """Son isaretten sonraki son metin parcasinda sayfa sonu bolgesini ayirir.

    Bolge, ilk bos satirda ya da bilinen bir eslesmemis kapanis etiketinde (`</div>`) baslar.
    Donus: (kesilmis olay, bolge metni). Konumu kesilemeyen (tam olmayan) olayda bolge yoktur.
    """
    if not olay.tam:
        return olay, ""
    adaylar = []
    bos = _BOS_SATIR.search(olay.metin)
    if bos is not None:
        adaylar.append(bos.start())
    for kapanis in SAYFA_SONU_KAPANISLARI:
        i = olay.metin.find(kapanis)
        if i >= 0:
            adaylar.append(i)
    if not adaylar:
        return olay, ""
    kesim = min(adaylar)
    return _Olay("metin", olay.metin[:kesim], olay.bas, olay.bas + kesim, True), olay.metin[kesim:]


def _isaret_coz(deger: str) -> tuple[str, int, int]:
    """Isaret degeri: (tur, ilk, son); tur tek, aralik, numarasiz ya da besmele."""
    if ISARET_TEK.fullmatch(deger):
        n = int(deger)
        return "tek", n, n
    aralik = ISARET_ARALIK.fullmatch(deger)
    if aralik is not None:
        ilk, son = int(aralik.group(1)), int(aralik.group(2))
        if ilk >= son:
            raise GirdiHatasi("ayet isareti araligi artan degil")
        return "aralik", ilk, son
    if deger == NUMARASIZ:
        return "numarasiz", 0, 0
    if deger == BESMELE:
        return "besmele", 0, 0
    raise GirdiHatasi("ayet isareti bicimi tanimsiz")


def _artik_denetle(metin: str) -> None:
    if any(k in ARTIK_KARAKTERLER for k in metin) or "[[" in metin or "]]" in metin:
        raise GirdiHatasi("ayet metninde wikitext artigi var (bozuk ya da bilinmeyen kod)")


def sayfa_cikar(wikitext: str, *, sure: int, ayet_sayisi: int, eser: str) -> SayfaCikti:
    """Bir sure sayfasinin wikitext'inden ayet birimleri; kural tablosu ve sinir kurallari.

    Sure ve ayet sayisi disaridan verilir (kilitteki acik eslesme ve Tanzil sayisi). Kapsam
    (1..ayet_sayisi her ayet tam bir kez) saglanmazsa `GirdiHatasi`.
    """
    kod = mwparserfromhell.parse(wikitext, context=0, skip_style_tags=False)
    if str(kod) != wikitext:
        raise GirdiHatasi("wikitext ayristirmasi metni geri uretmiyor")
    olaylar: list[_Olay] = []
    _yuru(kod, 0, wikitext, olaylar, 0)

    on: list[_Olay] = []
    parcalar: list[_Parca] = []
    for olay in olaylar:
        if olay.tur == "isaret":
            parcalar.append(_Parca(olay.metin, olay.bas, olay.son))
        elif parcalar:
            parcalar[-1].olaylar.append(olay)
        else:
            on.append(olay)
    if not parcalar:
        raise GirdiHatasi("sayfada ayet isareti yok")

    son_bolge = ""
    son = parcalar[-1]
    if son.olaylar and son.olaylar[-1].tur == "metin":
        kesik, son_bolge = _son_bolgeyi_ayir(son.olaylar[-1])
        son.olaylar[-1] = kesik
    bitisler = [p.isaret_bas for p in parcalar[1:]]
    bitisler.append(son.olaylar[-1].son if son.olaylar else son.isaret_son)

    sirali: dict[int, list[tuple[str, tuple[int, int]]]] = {}
    uyarilar: dict[int, list[str]] = {}
    izleyen: dict[int, int] = {}  # izleyen ayet -> bas ayet
    kapsamlar: dict[int, int] = {}  # bas ayet -> kapsamin son ayeti
    besmele: tuple[str, tuple[int, int]] | None = None
    onceki_son = 0
    onceki_bas: int | None = None

    def uyar(ayet: int, kod_: str) -> None:
        liste = uyarilar.setdefault(ayet, [])
        if kod_ not in liste:
            liste.append(kod_)

    bekleyen: list[_Uye] = []  # metni sonraki isarete kalan bos isaretler (ardisik isaret grubu)

    def grup_isle(uyeler: list[_Uye]) -> None:
        nonlocal onceki_son, onceki_bas
        metin = uyeler[-1].metin  # yalniz son uye metin tasir
        aralik = (uyeler[0].parca.isaret_son, uyeler[-1].bitis)
        numaralar = [n for u in uyeler if u.tur != "numarasiz" for n in range(u.ilk, u.son + 1)]
        numarasiz = any(u.tur == "numarasiz" for u in uyeler)
        if not numaralar:  # yalniz numarasiz isaret(ler): metin onceki numarali ayete eklenir
            if onceki_bas is None:
                raise GirdiHatasi("numarasiz parca onceki numarali ayet olmadan geldi")
            sirali[onceki_bas].append((metin, aralik))
            uyar(onceki_bas, UYARI_NUMARASIZ)
            return
        if numaralar != sorted(set(numaralar)):
            raise GirdiHatasi("ardisik isaretlerin ayet numaralari artan degil")
        if numaralar[-1] > ayet_sayisi:
            raise GirdiHatasi("ayet isareti sure ayet sayisinin disinda")
        ilk = numaralar[0]
        beklenen_ilk = onceki_son + 1
        while beklenen_ilk in sirali or beklenen_ilk in izleyen:  # onceki gruplarda yerlesenler
            beklenen_ilk += 1
        if ilk != beklenen_ilk and not (ilk == onceki_son and ilk in sirali):
            uyar(ilk, UYARI_SIRA_DISI)  # hemen onceki isaretin tekrari yalniz `yinelenen` sayilir
        if len(numaralar) == 1:
            if ilk in izleyen:
                raise GirdiHatasi("ayet numarasi birlesik bir grubun kapsaminda yinelendi")
            if ilk in sirali:
                uyar(ilk, UYARI_YINELENEN)
            sirali.setdefault(ilk, []).append((metin, aralik))
            onceki_son, onceki_bas = ilk, ilk
            if numarasiz:
                uyar(ilk, UYARI_NUMARASIZ)
            return
        if any(n in sirali or n in izleyen for n in numaralar):
            raise GirdiHatasi("birlesik grubun ayet numarasi yinelendi")
        if numaralar == list(range(ilk, numaralar[-1] + 1)):  # ardisik: birlesik meal
            sirali[ilk] = [(metin, aralik)]
            kapsamlar[ilk] = numaralar[-1]
            for n in numaralar[1:]:
                izleyen[n] = ilk
            for n in numaralar:
                uyar(n, UYARI_BIRLESIK)
            onceki_son, onceki_bas = numaralar[-1], ilk
        else:  # ardisik degil: ayni metin her ayete verilir (tekrarlanan ayet, ortak ceviri)
            for n in numaralar:
                sirali[n] = [(metin, aralik)]
                uyar(n, UYARI_ORTAK_METIN)
            onceki_son, onceki_bas = ilk, ilk
        if numarasiz:
            uyar(ilk, UYARI_NUMARASIZ)

    for parca, bitis in zip(parcalar, bitisler, strict=True):
        tur, ilk_n, son_n = _isaret_coz(parca.deger)
        metin = parca_metni([o.metin for o in parca.olaylar])
        if tur == "besmele":
            if (
                sure in BESMELESIZ_SURELER
                or besmele is not None
                or onceki_bas is not None
                or bekleyen
            ):
                raise GirdiHatasi("besmele isareti bu sayfada kullanilamaz")
            besmele = (metin, (parca.isaret_son, bitis))
            continue
        bekleyen.append(_Uye(parca, tur, ilk_n, son_n, metin, bitis))
        if metin == "" and parca is not parcalar[-1]:
            continue  # metin sonraki isarette: ardisik isaret grubu
        grup_isle(bekleyen)
        bekleyen = []

    var = set(sirali) | set(izleyen)
    beklenen = set(range(1, ayet_sayisi + 1))
    if var != beklenen:
        eksik, fazla = sorted(beklenen - var), sorted(var - beklenen)
        raise GirdiHatasi(
            f"ayet kumesi Tanzil sayisiyla esit degil: sure {sure}, eksik {len(eksik)}"
            f" (ilk {eksik[:3]}), fazla {len(fazla)}"
        )

    ayetler: list[AyetTaslagi] = []
    for n in range(1, ayet_sayisi + 1):
        attrs: dict[str, object] = {}
        uy = list(uyarilar.get(n, []))
        if n in izleyen:
            attrs["birlesik_ile"] = anchor_format(AnchorRef(Meal(eser, sure, izleyen[n])))
            ayetler.append(AyetTaslagi(sure, n, "", attrs, tuple(uy), ()))
            continue
        pcs = sirali[n]
        metin = kanonik_metin(AYIRICI.join(p for p, _ in pcs if p != ""))
        _artik_denetle(metin)
        if n in kapsamlar:
            attrs["kapsam"] = anchor_format(AnchorRef(Qa(sure, n, kapsamlar[n])))
        if n == 1 and besmele is not None:
            b_metin = kanonik_metin(besmele[0])
            _artik_denetle(b_metin)
            attrs["besmele_meali"] = {"metin": b_metin, "content_hash": content_hash(b_metin)}
            uy.append(UYARI_BESMELE)
        if metin == "":  # birlesik degismezi: bos metin yalniz izleyen birimde olur
            raise GirdiHatasi(f"sure {sure} ayet {n}: izleyen olmayan birimin metni bos")
        araliklar = tuple(a for _, a in pcs)
        ayetler.append(AyetTaslagi(sure, n, metin, attrs, tuple(uy), araliklar))
    return SayfaCikti(
        ayetler=tuple(ayetler),
        isaret_sayisi=len(parcalar),
        on_bolge=_bolge_ozeti("".join(o.metin for o in on if o.tur == "metin")),
        son_bolge=_bolge_ozeti(son_bolge),
    )


# --- ham dosyalar ----------------------------------------------------------------------------


@dataclass(frozen=True)
class OkunanSayfa:
    kilit: SayfaKilidi
    wikitext: str
    dosya: str  # sayfayi tasiyan API yanit dosyasi


def sha1_hesapla(veri: bytes) -> str:
    """MediaWiki'nin revizyon ozeti SHA-1'dir (guvenlik amacli degil, kilit karsilastirmasi)."""
    return hashlib.sha1(veri, usedforsecurity=False).hexdigest()


def yanitlardan_sayfalar(
    yanitlar: Mapping[str, bytes], kilit: VikikaynakKilidi
) -> dict[int, OkunanSayfa]:
    """API yanitlarini kati okur ve her sayfayi kilitle (baslik, revid, sha1, ozet) eslestirir.

    Donus: `sure -> OkunanSayfa`. 114 sayfanin hepsi tam bir kez bulunmali.
    """
    kilit_baslik = {s.baslik: s for s in kilit.sayfalar}
    bulunan: dict[int, OkunanSayfa] = {}
    for ad in sorted(yanitlar):
        try:
            belge = kati_json(yanitlar[ad].decode("utf-8"))
        except UnicodeDecodeError:
            raise GirdiHatasi(f"{ad}: UTF-8 degil") from None
        except GirdiHatasi as hata:
            raise GirdiHatasi(f"{ad}: {hata}") from None
        sayfalar = yol_al(belge, ad, "query", "pages")
        if not isinstance(sayfalar, list):
            raise GirdiHatasi(f"{ad}: query.pages liste degil")
        for sira, sayfa in enumerate(sayfalar, start=1):
            yer = f"{ad} sayfa {sira}"
            if not isinstance(sayfa, dict) or sayfa.get("missing") or sayfa.get("invalid"):
                raise GirdiHatasi(f"{yer}: sayfa yok ya da gecersiz")
            baslik = sayfa.get("title")
            sk = kilit_baslik.get(baslik) if isinstance(baslik, str) else None
            if sk is None:
                raise GirdiHatasi(f"{yer}: baslik kilitte yok")
            revizyonlar = sayfa.get("revisions")
            if not isinstance(revizyonlar, list) or len(revizyonlar) != 1:
                raise GirdiHatasi(f"{yer}: tek revizyon bekleniyor")
            rev = revizyonlar[0]
            ana = yol_al(rev, yer, "slots", "main")
            if not isinstance(ana, dict):
                raise GirdiHatasi(f"{yer}: slots.main nesne degil")
            icerik = ana.get("content")
            if (
                ana.get("contentmodel") != "wikitext"
                or not isinstance(rev, dict)
                or not isinstance(icerik, str)
            ):
                raise GirdiHatasi(f"{yer}: revizyon wikitext degil")
            ham = icerik.encode("utf-8", "strict")
            if (
                rev.get("revid") != sk.revid
                or rev.get("sha1") != sk.sha1
                or sha1_hesapla(ham) != sk.sha1
                or rev.get("size") != len(ham)
                or lineage.sha256_bayt(ham) != sk.wikitext_sha256
            ):
                raise GirdiHatasi(
                    f"{yer}: sure {sk.sure}: revizyon kilitle tutmuyor. {meal_ortak.UYARI}"
                )
            if sk.sure in bulunan:
                raise GirdiHatasi(f"{yer}: sure {sk.sure} birden fazla kez geldi")
            bulunan[sk.sure] = OkunanSayfa(sk, icerik, ad)
    if sorted(bulunan) != list(range(1, 115)):
        raise GirdiHatasi(f"yanitlarda {len(bulunan)} sayfa var; 114 bekleniyor")
    return bulunan


def yol_al(nesne: object, yer: str, *anahtarlar: str) -> object:
    for a in anahtarlar:
        if not isinstance(nesne, dict) or a not in nesne:
            raise GirdiHatasi(f"{yer}: '{a}' alani yok")
        nesne = nesne[a]
    return nesne


def liste_denetle(liste: bytes, kilit: VikikaynakKilidi) -> None:
    """`basliklar.tsv` satirlari ("baslik TAB revid") kilitteki sayfalarla ayni olmali."""
    try:
        metin = liste.decode("utf-8")
    except UnicodeDecodeError:
        raise GirdiHatasi(f"{LISTE_DOSYASI}: UTF-8 degil") from None
    if "\r" in metin or not metin.endswith("\n"):
        raise GirdiHatasi(f"{LISTE_DOSYASI}: LF satir sonlari ve sonda satir sonu bekleniyor")
    satirlar = metin[:-1].split("\n")
    beklenen = {(s.baslik, s.revid) for s in kilit.sayfalar}
    bulunan: set[tuple[str, int]] = set()
    for sira, satir in enumerate(satirlar, start=1):
        parca = satir.split("\t")
        if len(parca) != 2 or REVID.fullmatch(parca[1]) is None:
            raise GirdiHatasi(f"{LISTE_DOSYASI}: satir {sira} bicimi gecersiz")
        bulunan.add((parca[0], int(parca[1])))
    if bulunan != beklenen or len(satirlar) != len(beklenen):
        raise GirdiHatasi(f"{LISTE_DOSYASI}: kilitteki sayfa listesiyle ayni degil")


# --- bagdastirici ----------------------------------------------------------------------------


@dataclass
class _Durum:
    tarih: str = ""
    kilit_sha256: str = ""
    bolgeler: list[dict[str, object]] = field(default_factory=list)
    uyari_sayilari: dict[str, int] = field(default_factory=dict)
    birim: int = 0
    isaret: int = 0


class VikikaynakBagdastirici:
    """`SourceAdapter`: Vikikaynak'in 114 sure sayfasini `data/gelen`den alir (K-49)."""

    source_id = KAYNAK

    def __init__(self, *, gelen_tarih: str | None = None, kilit: MealKilidi | None = None) -> None:
        self._istenen_tarih = gelen_tarih
        self._kilit = (kilit if kilit is not None else kilit_yukle()).vikikaynak
        self._ham: dict[str, bytes] = {}
        self._durum = _Durum()

    def fetch(self, ctx: RunContext) -> list[RawFile]:
        tarih, icerik = meal_ortak.gelenleri_oku(
            ctx, KAYNAK, self._istenen_tarih, self._kilit.dosyalar
        )
        # Kilit denetimi gecti: icerik bu asamada da dogrulanir (raw'a hicbir sey yazilmadan).
        liste_denetle(icerik[LISTE_DOSYASI], self._kilit)
        sayfalar = yanitlardan_sayfalar(
            {d.ad: icerik[d.ad] for d in self._kilit.yanit_dosyalari}, self._kilit
        )
        if len(sayfalar) != 114:  # pragma: no cover - yanitlardan_sayfalar zaten denetler
            raise GirdiHatasi("114 sayfa bekleniyor")
        ozet = kilit_ozeti(self._kilit.sozluk())
        yollar, yeni = meal_ortak.ham_kopyala(
            ctx,
            KAYNAK,
            tarih,
            icerik,
            meal_ortak.fetch_kaydi(KAYNAK, tarih, self._kilit.url, ozet, self._kilit.dosyalar),
        )
        self._ham = icerik
        self._durum.tarih = tarih
        self._durum.kilit_sha256 = ozet
        ctx.sayi("ham_dosya", len(icerik))
        ctx.sayi("ham_yeni", 1 if yeni else 0)
        ctx.gunluk.yaz(
            "INFO",
            "vikikaynak_fetch",
            source_id=KAYNAK,
            sayilar={"dosya": len(icerik), "ham_yeni": 1 if yeni else 0},
        )
        return meal_ortak.raw_dosyalari(ctx, yollar, icerik)

    def parse(self, ctx: RunContext, files: list[RawFile]) -> Iterator[StagedUnit]:
        if not self._ham:
            raise GirdiHatasi("fetch cagrilmadan parse")
        sayfalar = yanitlardan_sayfalar(
            {d.ad: self._ham[d.ad] for d in self._kilit.yanit_dosyalari}, self._kilit
        )
        dosya_ozeti = {d.ad: lineage.sha256_bayt(self._ham[d.ad]) for d in self._kilit.dosyalar}
        eser = capa_eseri(KAYNAK)
        durum = self._durum
        for sure in range(1, 115):
            sayfa = sayfalar[sure]
            try:
                cikti = sayfa_cikar(
                    sayfa.wikitext,
                    sure=sure,
                    ayet_sayisi=AYET_SAYILARI[sure - 1],
                    eser=eser,
                )
            except GirdiHatasi as hata:
                raise GirdiHatasi(f"vikikaynak sure {sure}: {hata}") from None
            durum.isaret += cikti.isaret_sayisi
            if cikti.on_bolge is not None or cikti.son_bolge is not None:
                durum.bolgeler.append({"sure": sure, "on": cikti.on_bolge, "son": cikti.son_bolge})
            for ayet in cikti.ayetler:
                for kod_ in ayet.uyari:
                    durum.uyari_sayilari[kod_] = durum.uyari_sayilari.get(kod_, 0) + 1
                durum.birim += 1
                yield StagedUnit(
                    anchor=anchor_format(AnchorRef(Meal(eser, sure, ayet.ayet))),
                    text=ayet.metin,
                    attrs=ayet.attrs,
                    provenance=_provenance(sayfa, ayet, dosya_ozeti[sayfa.dosya]),
                )

    def manifest_ayrintilari(self) -> dict[str, object]:
        d = self._durum
        return {
            "kaynak": KAYNAK,
            "gelen_tarih": d.tarih,
            "kilit_bolumu": BOLUM_VIKIKAYNAK,
            "kilit_sha256": d.kilit_sha256,
            "cikarici_surumu": CIKARICI_SURUMU,
            "mwparserfromhell": mwparserfromhell.__version__,
            "unidata": unicodedata.unidata_version,
            "birim": d.birim,
            "isaret": d.isaret,
            "uyari_sayilari": dict(sorted(d.uyari_sayilari.items())),
            "bolgeler": d.bolgeler,
        }


def _provenance(sayfa: OkunanSayfa, ayet: AyetTaslagi, dosya_sha256: str) -> dict[str, object]:
    kayit: dict[str, object] = {
        "file": sayfa.dosya,
        "sha256": dosya_sha256,
        "sayfa": sayfa.kilit.baslik,
        "revid": sayfa.kilit.revid,
        "wikitext_sha256": sayfa.kilit.wikitext_sha256,
        "cikarici": {
            "surum": CIKARICI_SURUMU,
            "mwparserfromhell": mwparserfromhell.__version__,
            "unidata": unicodedata.unidata_version,
        },
    }
    if ayet.araliklar:
        kayit["konum"] = {
            "araliklar": [list(a) for a in ayet.araliklar],
            "ayirici": ayet.ayirici,
        }
    if ayet.uyari:
        kayit["uyari"] = list(ayet.uyari)
    return kayit


def bagdastirici_olustur(*, gelen_tarih: str | None = None) -> VikikaynakBagdastirici:
    return VikikaynakBagdastirici(gelen_tarih=gelen_tarih)


def ham_sayfalar(yollar: Mapping[str, Path], kilit: VikikaynakKilidi) -> dict[int, OkunanSayfa]:
    """Ham dosya yollarindan sayfalar (QA yeniden uretilebilirlik denetimi icin)."""
    yanitlar = {d.ad: yollar[d.ad].read_bytes() for d in kilit.yanit_dosyalari}
    return yanitlardan_sayfalar(yanitlar, kilit)


def yeniden_uret(
    ham: Mapping[str, bytes], kilit: MealKilidi | None = None
) -> dict[str, tuple[str, dict[str, object]]]:
    """Ham dosya baytlarindan `capa -> (metin, attrs)`; QA G-BUT yeniden uretilebilirlik denetimi.

    Ingest ile ayni kod yolunu (`sayfa_cikar`) kullanir; kilit ve ham dosyalar tutmazsa
    `GirdiHatasi`.
    """
    vk = (kilit if kilit is not None else kilit_yukle()).vikikaynak
    sayfalar = yanitlardan_sayfalar({d.ad: ham[d.ad] for d in vk.yanit_dosyalari}, vk)
    eser = capa_eseri(KAYNAK)
    sonuc: dict[str, tuple[str, dict[str, object]]] = {}
    for sure in range(1, 115):
        cikti = sayfa_cikar(
            sayfalar[sure].wikitext,
            sure=sure,
            ayet_sayisi=AYET_SAYILARI[sure - 1],
            eser=eser,
        )
        for ayet in cikti.ayetler:
            sonuc[anchor_format(AnchorRef(Meal(eser, sure, ayet.ayet)))] = (ayet.metin, ayet.attrs)
    return sonuc
