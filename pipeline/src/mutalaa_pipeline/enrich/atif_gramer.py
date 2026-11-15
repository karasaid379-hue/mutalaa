"""Acik atif grameri: "(Bakara Suresi, 255)", "Ad: 7", "(2:255)" gibi bicimler (A20.7a).

Iktibas tespiti §2'nin kucuk gramerini uygular; arac secimine bagli degildir. Sure adlari bu
modulde yazili DEGILDIR: cagiran bir `SureAdTablosu` verir (editoryal veritabanindaki `surah_alias`
tablosunun ya da `data/staged/sure-adlari-vikipedi` ciktisinin satirlarindan; sure adi hafizadan
yazilmaz). Adsiz sayisal bicimler (`(2:255)`, `[2/255]`) tablo olmadan da calisir.

Ofsetler metinde Unicode kod noktasi, aralik yari acik `[bas, son)` (K-26). Cikti capasi
`anchor.capa` ile uretilir ve dogrulanir (`q:{sure}:{ayet}`; gecersiz sure ya da ayet atilir).

Bicimler (basit "ad" = tablodaki herhangi bir yazim; kelimeler genis anahtarla eslenir, yani
sapka, nokta ve buyuk-kucuk harf farki onemsizdir):

    ad [Suresi|Suresinin|...] AYRAC AYETLER      "Ad, 255"   "Ad: 7"   "Ad Suresi, 255-257"
    ad [Suresi] SURE_NO AYRAC AYETLER            "Ad 2/255"  (SURE_NO adin suresiyle ayni olmali)
    "Sure-i" ad AYRAC AYETLER                    "Sure-i Ad, 255"
    ad Suresinin 255. ayeti                      sirali bicim
    ( SURE_NO AYRAC AYETLER )  ya da [ ... ]     "(2:255)"  yalniz parantez icinde
    Arapca ad AYRAC AYETLER                      Arapca adlar tabloda Arapca yazimla verilir

Riskli adlar (ortak kelime ya da ozel isim) yalniz parantez, "Sure" kelimesi ya da "ayet" kelimesi
ile kabul edilir. Bosluk ayracli ("Ad 255") bicim de parantez ya da anahtar kelime ister.
Aralik ve liste ayet basina bir sonuc verir (`Atif.ayetler`) ve `grup` ile baglanir.

Baslangic guvenleri Iktibas tespiti §2 "Dogrulama ve guven" madde 3'tendir: parantezli ya da
anahtar kelimeli guvenli ad 0,95; ciplak "Ad: SAYI" 0,85; guclu ipuclu riskli ad 0,85.
Adsiz parantezli sayisal bicim icin belge deger vermez: 0,85 (baslangic degeri; ayarlanir).
"""

import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Final

from mutalaa_pipeline.anchor import AnchorRef, Q, format, try_parse
from mutalaa_pipeline.normalize.arabic import ar_anahtari
from mutalaa_pipeline.normalize.turkish import fold_wide, lower_turkish
from mutalaa_pipeline.normalize.unicode import arapca_mi

GUVEN_ANAHTAR_KELIMELI: Final = 0.95
GUVEN_CIPLAK: Final = 0.85
GUVEN_RISKLI_IPUCLU: Final = 0.85
GUVEN_ADSIZ_PARANTEZ: Final = 0.85

# Adin ardindan gelebilecek "sure" kelimeleri (genis anahtar).
_SURE_KELIMELERI: Final = frozenset({"suresi", "suresinin", "suresinde", "suresine", "sure"})
_ARAPCA_SURE_KELIMELERI: Final = frozenset(
    {
        ar_anahtari(
            "\N{ARABIC LETTER SEEN}\N{ARABIC LETTER WAW}"
            "\N{ARABIC LETTER REH}\N{ARABIC LETTER TEH MARBUTA}"
        )
    }
)
_RAKAMLAR: Final = "0-9\u0660-\u0669"  # ASCII ve Arapca-Hint rakamlar
_SAYI: Final = rf"[{_RAKAMLAR}]{{1,3}}"
_ARALIK: Final = rf"{_SAYI}(?:[ \t]*[-\N{{EN DASH}}][ \t]*{_SAYI})?"
_LISTE: Final = rf"{_ARALIK}(?:[ \t]*,[ \t]*{_ARALIK})*"

# Adin ardindan: "SURE_NO AYRAC AYETLER" (sure numarali).
_SURE_NO_AYRAC: Final = re.compile(
    rf"[ \t]*(?P<sure>{_SAYI})[ \t]*(?P<ayrac>[:/])[ \t]*(?P<ayetler>{_LISTE})"
)
# Adin ardindan: "AYRAC AYETLER" ya da yalniz bosluk.
_AYRAC_AYETLER: Final = re.compile(rf"[ \t]*(?P<ayrac>[:,/]|)[ \t]*(?P<ayetler>{_LISTE})")
# Sirali bicim: "255. ayeti".
_SIRALI_KELIME: Final = re.compile(rf"[ \t]*(?P<ayetler>{_SAYI})\.[ \t]*[AÂaâ]yet\w*")
# Adsiz parantezli sayisal bicim.
_ADSIZ: Final = re.compile(
    rf"[(\[][ \t]*(?P<sure>{_SAYI})[ \t]*[:/][ \t]*(?P<ayetler>{_LISTE})[ \t]*[)\]]"
)
_SAYI_PARCASI: Final = re.compile(rf"({_SAYI})(?:[ \t]*[-\N{{EN DASH}}][ \t]*({_SAYI}))?")
_ACILIS: Final = "(["
_KAPANIS: Final = ")]"
_ARAPCA_HINT: Final = str.maketrans(dict(zip(range(0x0660, 0x066A), "0123456789", strict=True)))

MAKS_ARALIK: Final = 286  # tek sure icinde en uzun ayet sayisi (bir araligin ust siniri)


def sozcuk_anahtari(sozcuk: str) -> str:
    """Bir sozcugun adlandirma anahtari: Arapca ise `ar_anahtari`, degilse Turkce genis anahtar."""
    if any(arapca_mi(k) for k in sozcuk):
        return ar_anahtari(sozcuk)
    return fold_wide(lower_turkish(sozcuk))


def _sozcuk_karakteri(karakter: str) -> bool:
    return karakter.isalpha() or unicodedata.category(karakter).startswith("M")


def _sozcukler(metin: str) -> list[tuple[str, int, int]]:
    """Harf (ve birlesen isaret) dizileri: `(anahtar, bas, son)`; bos anahtarlar atilir."""
    sonuc: list[tuple[str, int, int]] = []
    bas = -1
    for i, karakter in enumerate((*metin, "\0")):
        if _sozcuk_karakteri(karakter) and karakter != "\0":
            if bas < 0:
                bas = i
        elif bas >= 0:
            anahtar = sozcuk_anahtari(metin[bas:i])
            if anahtar:
                sonuc.append((anahtar, bas, i))
            bas = -1
    return sonuc


@dataclass(frozen=True, slots=True)
class SureAdi:
    """Bir sure adi yazimi: `no`, gorunen `ad`, `riskli` bayragi."""

    no: int
    ad: str
    riskli: bool = False


class SureAdTablosu:
    """Sure adi yazimlari, kelime dizisi anahtariyla (en uzun yazim once eslenir)."""

    def __init__(self, adlar: Iterable[SureAdi]) -> None:
        self._tablo: dict[tuple[str, ...], list[SureAdi]] = {}
        for sure_adi in adlar:
            anahtar = tuple(a for a, _, _ in _sozcukler(sure_adi.ad))
            if not anahtar:
                raise ValueError("sure adi bos anahtar uretti")
            self._tablo.setdefault(anahtar, []).append(sure_adi)
        self.en_uzun: Final = max((len(a) for a in self._tablo), default=0)

    @classmethod
    def kur(
        cls, ciftler: Iterable[tuple[int, str]], riskli_adlar: Iterable[str] = ()
    ) -> "SureAdTablosu":
        """`(sure_no, ad)` ciftlerinden; `riskli_adlar` listesindeki adlar riskli sayilir."""
        riskli = {tuple(a for a, _, _ in _sozcukler(r)) for r in riskli_adlar}
        adlar = [
            SureAdi(no, ad, tuple(a for a, _, _ in _sozcukler(ad)) in riskli) for no, ad in ciftler
        ]
        return cls(adlar)

    def bul(self, anahtar: tuple[str, ...]) -> list[SureAdi]:
        return self._tablo.get(anahtar, [])

    def __len__(self) -> int:
        return sum(len(v) for v in self._tablo.values())


@dataclass(frozen=True, slots=True)
class Atif:
    """Metindeki bir acik atif: ifade araligi `[bas, son)`, sure, ayetler, guven."""

    bas: int
    son: int
    sure: int
    ayetler: tuple[int, ...]
    guven: float
    sinyal: str  # bicim adi (evidence.sinyal)
    parantez: bool
    grup: bool  # aralik ya da liste (birden cok ayet ayni ifadeden)

    def capalar(self) -> tuple[str, ...]:
        """Ayet basina `q:{sure}:{ayet}` capalari (`anchor.capa` ile uretilir ve dogrulanir)."""
        return tuple(format(AnchorRef(Q(self.sure, a))) for a in self.ayetler)


@dataclass
class AtifSonucu:
    """`ayristir` sonucu: atiflar ve atilan adaylarin neden bazli sayilari."""

    atiflar: list[Atif] = field(default_factory=list)
    atilan: dict[str, int] = field(default_factory=dict)

    def _at(self, neden: str) -> None:
        self.atilan[neden] = self.atilan.get(neden, 0) + 1


def _sayi(parca: str) -> int:
    return int(parca.translate(_ARAPCA_HINT))


def _ayetleri_coz(liste: str) -> list[int] | None:
    """`255-257, 259` -> `[255, 256, 257, 259]`; ters ya da cok uzun aralik `None`."""
    ayetler: list[int] = []
    for parca in liste.split(","):
        eslesme = _SAYI_PARCASI.fullmatch(parca.strip())
        if eslesme is None:
            return None
        ilk = _sayi(eslesme.group(1))
        son = _sayi(eslesme.group(2)) if eslesme.group(2) is not None else ilk
        if ilk > son or son - ilk >= MAKS_ARALIK:
            return None
        ayetler.extend(range(ilk, son + 1))
    return ayetler


def _gecerli_ayetler(sure: int, ayetler: list[int]) -> tuple[int, ...] | None:
    """Capa gramerine gore gecerli olanlar; biri gecersizse hepsi atilir (`None`)."""
    for ayet in ayetler:
        if try_parse(f"q:{sure}:{ayet}") is None:
            return None
    # Sirayi koruyarak tekrarlari at.
    return tuple(dict.fromkeys(ayetler))


def _parantez_icinde(metin: str, bas: int, son: int) -> tuple[int, int]:
    """Ifadeyi saran `(`/`[` ve `)`/`]` varsa araligi onlari kapsayacak sekilde genisletir."""
    onceki = bas - 1
    while onceki >= 0 and metin[onceki] in " \t":
        onceki -= 1
    sonraki = son
    while sonraki < len(metin) and metin[sonraki] in " \t":
        sonraki += 1
    acilis = onceki >= 0 and metin[onceki] in _ACILIS
    kapanis = sonraki < len(metin) and metin[sonraki] in _KAPANIS
    if acilis and kapanis:
        return onceki, sonraki + 1
    return bas, son


def ayristir(metin: str, tablo: SureAdTablosu | None = None) -> AtifSonucu:
    """`metin` icindeki acik atiflari bulur; bas ofsetine gore sirali, cakismasiz."""
    sonuc = AtifSonucu()
    _adsiz_bul(metin, sonuc)
    if tablo is not None and len(tablo) > 0:
        _adli_bul(metin, tablo, sonuc)
    sonuc.atiflar.sort(key=lambda a: (a.bas, a.son))
    # Cakisma: once baslayan ve daha uzun olan kalir.
    temiz: list[Atif] = []
    for atif in sonuc.atiflar:
        if temiz and atif.bas < temiz[-1].son:
            sonuc._at("cakisan")
            continue
        temiz.append(atif)
    sonuc.atiflar = temiz
    return sonuc


def _adsiz_bul(metin: str, sonuc: AtifSonucu) -> None:
    for eslesme in _ADSIZ.finditer(metin):
        sure = _sayi(eslesme.group("sure"))
        ayetler = _ayetleri_coz(eslesme.group("ayetler"))
        gecerli = None if ayetler is None else _gecerli_ayetler(sure, ayetler)
        if gecerli is None:
            sonuc._at("aralik_disi")
            continue
        sonuc.atiflar.append(
            Atif(
                eslesme.start(),
                eslesme.end(),
                sure,
                gecerli,
                GUVEN_ADSIZ_PARANTEZ,
                "adsiz_parantez",
                True,
                len(gecerli) > 1,
            )
        )


def _adli_bul(metin: str, tablo: SureAdTablosu, sonuc: AtifSonucu) -> None:
    sozcukler = _sozcukler(metin)
    anahtarlar = [a for a, _, _ in sozcukler]
    i = 0
    while i < len(sozcukler):
        bulunan = _ad_eslestir(anahtarlar, i, tablo)
        if bulunan is None:
            i += 1
            continue
        uzunluk, adaylar = bulunan
        ad_bas = sozcukler[i][1]
        son_sozcuk = i + uzunluk - 1
        # "Sure-i Ad": adin onunda `sure` (+ `i`) varsa ifade oradan baslar.
        on_ek = False
        if i >= 1 and anahtarlar[i - 1] == "sure":
            on_ek, ad_bas = True, sozcukler[i - 1][1]
        elif i >= 2 and anahtarlar[i - 2] == "sure" and anahtarlar[i - 1] == "i":
            on_ek, ad_bas = True, sozcukler[i - 2][1]
        # Adin arkasindaki "Suresi" benzeri kelime.
        anahtar_kelime = on_ek
        j = son_sozcuk + 1
        if j < len(sozcukler) and (
            anahtarlar[j] in _SURE_KELIMELERI or anahtarlar[j] in _ARAPCA_SURE_KELIMELERI
        ):
            anahtar_kelime = True
            son_sozcuk = j
        ad_son = sozcukler[son_sozcuk][2]
        atif = _sayilari_oku(metin, ad_bas, ad_son, adaylar, anahtar_kelime, sonuc)
        if atif is None:
            i += 1
            continue
        sonuc.atiflar.append(atif)
        while i < len(sozcukler) and sozcukler[i][1] < atif.son:
            i += 1


def _ad_eslestir(
    anahtarlar: list[str], i: int, tablo: SureAdTablosu
) -> tuple[int, list[SureAdi]] | None:
    for uzunluk in range(min(tablo.en_uzun, len(anahtarlar) - i), 0, -1):
        adaylar = tablo.bul(tuple(anahtarlar[i : i + uzunluk]))
        if adaylar:
            return uzunluk, adaylar
    return None


def _sayilari_oku(
    metin: str,
    ad_bas: int,
    ad_son: int,
    adaylar: list[SureAdi],
    anahtar_kelime: bool,
    sonuc: AtifSonucu,
) -> Atif | None:
    sureler = {a.no for a in adaylar}
    riskli = any(a.riskli for a in adaylar)

    def _kur(
        bas: int, son: int, sure: int, ayetler: list[int], ayrac: str, sinyal: str
    ) -> Atif | None:
        gecerli = _gecerli_ayetler(sure, ayetler)
        if gecerli is None:
            sonuc._at("aralik_disi")
            return None
        p_bas, p_son = _parantez_icinde(metin, bas, son)
        parantez = (p_bas, p_son) != (bas, son)
        if ayrac == "" and not (parantez or anahtar_kelime):
            sonuc._at("bosluk_ipucsuz")
            return None
        if riskli and not (parantez or anahtar_kelime or sinyal == "sirali"):
            sonuc._at("riskli_ipucsuz")
            return None
        if parantez or anahtar_kelime:
            guven = GUVEN_ANAHTAR_KELIMELI
        elif riskli:
            guven = GUVEN_RISKLI_IPUCLU
        else:
            guven = GUVEN_CIPLAK
        return Atif(p_bas, p_son, sure, gecerli, guven, sinyal, parantez, len(gecerli) > 1)

    # 1) Sure numarali: "Ad 2/255" (numara adin suresiyle ayni olmali).
    sure_no = _SURE_NO_AYRAC.match(metin, ad_son)
    if sure_no is not None:
        sure = _sayi(sure_no.group("sure"))
        ayetler = _ayetleri_coz(sure_no.group("ayetler"))
        if ayetler is not None and sure in sureler:
            return _kur(
                ad_bas, sure_no.end(), sure, ayetler, sure_no.group("ayrac"), "ad_sure_ayet"
            )
        if ayetler is not None:
            sonuc._at("sure_no_tutarsiz")
            return None
    # 2) Sirali: "Ad Suresinin 255. ayeti".
    sirali = _SIRALI_KELIME.match(metin, ad_son)
    if sirali is not None and len(sureler) == 1:
        ayetler = _ayetleri_coz(sirali.group("ayetler"))
        if ayetler is not None:
            return _kur(ad_bas, sirali.end(), next(iter(sureler)), ayetler, ":", "sirali")
    # 3) Ayrac ve ayetler: "Ad, 255", "Ad: 7", "Ad Suresi 255".
    ayrac = _AYRAC_AYETLER.match(metin, ad_son)
    if ayrac is not None and len(sureler) == 1:
        ayetler = _ayetleri_coz(ayrac.group("ayetler"))
        if ayetler is not None:
            sinyal = "ad_ayrac_ayet" if ayrac.group("ayrac") else "ad_bosluk_ayet"
            return _kur(
                ad_bas, ayrac.end(), next(iter(sureler)), ayetler, ayrac.group("ayrac"), sinyal
            )
    if ayrac is not None or sure_no is not None:
        sonuc._at("belirsiz_ad")
    return None


def evidence_sinyalleri(atif: Atif) -> dict[str, bool | str]:
    """`xref.evidence` icin metin icermeyen alanlar (`sinyal`, `parantez`)."""
    return {"sinyal": atif.sinyal, "parantez": atif.parantez}


__all__ = [
    "GUVEN_ADSIZ_PARANTEZ",
    "GUVEN_ANAHTAR_KELIMELI",
    "GUVEN_CIPLAK",
    "GUVEN_RISKLI_IPUCLU",
    "Atif",
    "AtifSonucu",
    "SureAdTablosu",
    "SureAdi",
    "ayristir",
    "evidence_sinyalleri",
    "sozcuk_anahtari",
]
