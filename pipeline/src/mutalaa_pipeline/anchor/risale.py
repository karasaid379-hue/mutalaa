# ruff: noqa: RUF001
"""Risale (`rn:`) kitap ve bolum adlari: dogrulayici, kaliplar, slug turetme, kitap tablosu.

Davranis Capa semasi bolum 5 (slug kurallari), K-26, K-51 madde 4 ve madde 12 ile belirlidir.
Capa ayristirma, bicimleme ve siralama `anchor.capa` uygulamasindadir; bu dosya onlari
yeniden yazmaz, yalniz adlari dogrular ve `rn:` capasini `capa.format` ile uretir.

Kurallar:
  * slug: kucuk harf ASCII (`[a-z0-9]` ve tire), harfle baslar, en cok 64 karakter;
  * `p{n}` ve `s{n}` bicimindeki adlar ayrilmistir (paragraf ve cumle eki);
  * yol (kitap dahil) en cok 8 parca;
  * `dizin` kitap slug'i olamaz (`risale-dizin` paketi icin ayrilmistir);
  * kardes cakismasinda `-2` eki (ucuncu icin `-3`), 64 karakter sinirina uyarak.

Duzenli ifadelerde `[0-9]` kullanilir (`\\d` degil). Buyuk-kucuk harf donusumu `str.lower()` ile
degil acik tabloyla yapilir (Turkce I/i tuzagi); tablodaki Turkce harfler kaynakta acik yazilidir
(ruff RUF001 dotless i'yi belirsiz sayar: dosya basindaki noqa). Bu modul yalniz `anchor`
paketini ice aktarir (yaprak kitaplik).
"""

import json
import re
import unicodedata
from collections.abc import Collection, Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Final, Literal

from mutalaa_pipeline.anchor.capa import (
    MAX_DERINLIK,
    MAX_SAYI,
    MAX_SLUG,
    AnchorRef,
    Rn,
    format,
    parse,
)

HataKodu = Literal["BICIM", "UZUNLUK", "AYRILMIS", "KALIP", "DERINLIK"]
Dil = Literal["tr", "ota", "ar"]
Yon = Literal["ltr", "rtl"]
MetinKaynagi = Literal["rnk"]
DiyanetKarsiligi = Literal["diyanet", "derleme", "rnk"]

DIZIN: Final = "dizin"
PAKET_ONEKI: Final = "risale-"
DIZIN_PAKETI: Final = PAKET_ONEKI + DIZIN
OSMANLICA_EKI: Final = "-osmanlica"
ARAPCA_EKI: Final = "-arapca"

# Siralamali bolum adlari: `{tur}-{n}`, n kanonik pozitif tam sayi.
SIRA_TURLERI: Final = (
    "soz",
    "mektup",
    "lema",
    "sua",
    "makam",
    "hakikat",
    "nukte",
    "mesele",
    "isaret",
    "hasiye",
    "parca",
)
# Numarasiz sabit bolum adlari.
SABIT_BOLUMLER: Final = ("mukaddime", "zeyl", "hatime")

_SLUG: Final = re.compile("[a-z][a-z0-9]*(?:-[a-z0-9]+)*")
_AYRILMIS: Final = re.compile("[ps][0-9]+")
_SIRA_ONEKLI: Final = re.compile("(?P<tur>" + "|".join(SIRA_TURLERI) + ")-(?P<n>[0-9]+)")
_KANONIK_SAYI: Final = re.compile("[1-9][0-9]*")

DILLER: Final = ("tr", "ota", "ar")
YONLER: Final = ("ltr", "rtl")
# K-51 madde 2: butun kitaplarin metni RNK'dandir (13 Kasim 2026); Diyanet yalniz karsilastirmadir.
METIN_KAYNAKLARI: Final = ("rnk",)
# Eski siniflama: kitabin Diyanet'teki karsiligi (diyanet: ayni ad; derleme: bolum derlemesi;
# rnk: Diyanet'te yok). Karsilastirma ve rapor icin saklanir; metin kaynagini belirlemez.
DIYANET_KARSILIKLARI: Final = ("diyanet", "derleme", "rnk")
RNK_RAFLARI: Final = ("tr", "tr_k", "osm", "ar", "ar_k")
# Dil -> RNK rafi (K-51 madde 1) ve slug eki.
_DIL_RAFLARI: Final[dict[str, tuple[str, ...]]] = {
    "tr": ("tr", "tr_k"),
    "ota": ("osm",),
    "ar": ("ar", "ar_k"),
}


class RisaleHatasi(ValueError):
    """Ad ya da tablo hatasi; `kod` hata sinifini verir."""

    kod: HataKodu

    def __init__(self, kod: HataKodu, mesaj: str) -> None:
        super().__init__(f"{kod}: {mesaj}")
        self.kod = kod


# ---------------------------------------------------------------------------
# Slug ve bolum dogrulayicilari


def slug_denetle(ad: str) -> str:
    """Bir yol parcasinin (kitap ya da bolum) slug kurallarina uydugunu denetler; `ad` doner.

    Sira (capa ile ayni): desen (`BICIM`), 64 karakter (`UZUNLUK`), ayrilmis ad (`AYRILMIS`).
    """
    if _SLUG.fullmatch(ad) is None:
        raise RisaleHatasi("BICIM", "slug kucuk harf ASCII olmali ve harfle baslamali")
    if len(ad) > MAX_SLUG:
        raise RisaleHatasi("UZUNLUK", f"slug {MAX_SLUG} karakteri asiyor")
    if _AYRILMIS.fullmatch(ad) is not None:
        raise RisaleHatasi("AYRILMIS", "p{n} ve s{n} adlari paragraf ve cumle eki icin ayrilmis")
    return ad


def kitap_slug_denetle(slug: str) -> str:
    """Kitap slug'i: `slug_denetle` ve `dizin` yasagi (`risale-dizin` paketine ayrilmis)."""
    slug_denetle(slug)
    if slug == DIZIN:
        raise RisaleHatasi("AYRILMIS", "'dizin' kitap slug'i olamaz")
    return slug


def sira_adi(tur: str, n: int) -> str:
    """`soz-10` gibi siralamali bolum adi; `tur` bilinen turlerden, `n` 1..2147483647."""
    if tur not in SIRA_TURLERI:
        raise RisaleHatasi("KALIP", "bilinmeyen bolum turu")
    if isinstance(n, bool) or not 1 <= n <= MAX_SAYI:
        raise RisaleHatasi("KALIP", "bolum numarasi 1 ile 2147483647 arasinda olmali")
    return f"{tur}-{n}"


@dataclass(frozen=True, slots=True)
class BolumKalibi:
    """Taninan bolum adi: `tur` ve (siralamali turlerde) `n`; sabit adlarda `n` yoktur."""

    tur: str
    n: int | None = None


def bolum_kalibi(ad: str) -> BolumKalibi | None:
    """Bolum adi bir kalibi taniyorsa `BolumKalibi`, taniyamiyorsa `None`.

    Kaliplar: `soz-{n}`, `mektup-{n}`, `lema-{n}`, `sua-{n}`, `makam-{n}`, `hakikat-{n}`,
    `nukte-{n}`, `mesele-{n}`, `isaret-{n}`, `hasiye-{n}`, `parca-{n}`, `mukaddime`, `zeyl`,
    `hatime`. Numara baslangicta sifirsiz olmalidir (`soz-01` bir kalip degildir).
    """
    if ad in SABIT_BOLUMLER:
        return BolumKalibi(ad)
    eslesme = _SIRA_ONEKLI.fullmatch(ad)
    if eslesme is None:
        return None
    numara = eslesme.group("n")
    if _KANONIK_SAYI.fullmatch(numara) is None or int(numara) > MAX_SAYI:
        return None
    return BolumKalibi(eslesme.group("tur"), int(numara))


def bolum_denetle(ad: str) -> str:
    """Bolum adi: slug kurallari; siralama onekli ad kanonik degilse `KALIP` hatasi.

    Kalip disi adlar (`giris`, `birinci-bab` ...) gecerlidir; yalniz `soz-01` gibi bir
    kaliba benzeyip kanonik olmayan ad reddedilir (ayni birime iki ad verilmesin).
    """
    slug_denetle(ad)
    if _SIRA_ONEKLI.fullmatch(ad) is not None and bolum_kalibi(ad) is None:
        raise RisaleHatasi("KALIP", "bolum numarasi sifirla baslayamaz ve sinirin altinda olmali")
    return ad


# Basliktan sayili kalip (A20.2b): "{sira} {tur}" -> `{tur}-{n}`; tur sozcugu ASCII'ye katlanmis
# (`slug_turet`) haliyle aranir. `hasiye` ve `parca` basliktan uretilmez (hasiye bolumu dipnot
# sirasindan, lahika parcasi kaynaktaki numaradan ya da `parca-{n}`den gelir).
_TUR_SOZCUKLERI: Final[dict[str, str]] = {
    "soz": "soz",
    "mektup": "mektup",
    "mektub": "mektup",
    "lema": "lema",
    "sua": "sua",
    "makam": "makam",
    "hakikat": "hakikat",
    "nukte": "nukte",
    "mesele": "mesele",
    "isaret": "isaret",
}
# Turkce sira sayilari (ASCII'ye katlanmis): birler, onlar ve onluk siralari.
_SIRA_BIRLER: Final[dict[str, int]] = {
    "birinci": 1,
    "ikinci": 2,
    "ucuncu": 3,
    "dorduncu": 4,
    "besinci": 5,
    "altinci": 6,
    "yedinci": 7,
    "sekizinci": 8,
    "dokuzuncu": 9,
}
_SIRA_ONLUK: Final[dict[str, int]] = {
    "onuncu": 10,
    "yirminci": 20,
    "otuzuncu": 30,
    "kirkinci": 40,
    "ellinci": 50,
    "altmisinci": 60,
    "yetmisinci": 70,
    "sekseninci": 80,
    "doksaninci": 90,
}
_ONLAR: Final[dict[str, int]] = {
    "on": 10,
    "yirmi": 20,
    "otuz": 30,
    "kirk": 40,
    "elli": 50,
    "altmis": 60,
    "yetmis": 70,
    "seksen": 80,
    "doksan": 90,
}


def sira_sayisi(ad: str) -> int | None:
    """ASCII katlanmis Turkce sira sayisini (`besinci`, `yirmi-besinci`, `otuzuncu`) cevirir.

    Tireler ve bosluklar yok sayilir (`yirmibesinci` de tanir); 1..99. Taninmazsa `None`.
    """
    s = ad.replace("-", "")
    if s in _SIRA_ONLUK:
        return _SIRA_ONLUK[s]
    if s in _SIRA_BIRLER:
        return _SIRA_BIRLER[s]
    for onlar, deger in _ONLAR.items():
        if s.startswith(onlar) and s[len(onlar) :] in _SIRA_BIRLER:
            return deger + _SIRA_BIRLER[s[len(onlar) :]]
    return None


def baslik_bolum_adi(baslik: str) -> str | None:
    """Baslik sayili ya da sabit kaliba uyuyorsa bolum adi (`soz-10`, `mukaddime`), yoksa `None`.

    Taninan bicimler: `{sira sozcugu} {tur}` (ornegin "Yirmi Besinci Soz"), `{n}. {tur}` ve
    `{tur} {n}` (n kanonik pozitif tam sayi) ile tek basina `Mukaddime`, `Zeyl`, `Hatime`. Tur:
    soz, mektup, lema, sua, makam, hakikat, nukte, mesele, isaret. Harf buyuklugu, sapkali harf
    ve kesme isareti `slug_turet` ile katlanir. Basligin ardindan baska sozcuk gelen
    ("Birinci Soz'un Zeyli") ya da turu olmayan baslik kalibi tanimaz; slug basliktan turetilir.
    """
    try:
        ham = slug_turet(baslik, kes=False)
    except RisaleHatasi:
        return None
    if ham in SABIT_BOLUMLER:
        return ham
    parcalar = ham.split("-")
    if len(parcalar) < 2:
        return None
    tur_ilk, tur_son = _TUR_SOZCUKLERI.get(parcalar[0]), _TUR_SOZCUKLERI.get(parcalar[-1])
    if tur_son is not None:
        n = _sira_ya_da_sayi(parcalar[:-1])
        tur = tur_son
    elif tur_ilk is not None:
        n = _sira_ya_da_sayi(parcalar[1:])
        tur = tur_ilk
    else:
        return None
    if n is None or not 1 <= n <= MAX_SAYI:
        return None
    return sira_adi(tur, n)


def _sira_ya_da_sayi(parcalar: Sequence[str]) -> int | None:
    """Sira sozcugu dizisi ya da tek kanonik sayi belirteci; degilse `None`."""
    if not parcalar:
        return None
    if len(parcalar) == 1 and _KANONIK_SAYI.fullmatch(parcalar[0]) is not None:
        return int(parcalar[0])
    return sira_sayisi("".join(parcalar))


def yol_denetle(yol: Sequence[str]) -> tuple[str, ...]:
    """`yol[0]` kitap, gerisi bolum; derinlik (kitap dahil) en cok 8."""
    if not yol:
        raise RisaleHatasi("BICIM", "yol bos")
    if len(yol) > MAX_DERINLIK:
        raise RisaleHatasi("DERINLIK", f"bolum derinligi {MAX_DERINLIK} degerini asiyor")
    kitap_slug_denetle(yol[0])
    for bolum in yol[1:]:
        bolum_denetle(bolum)
    return tuple(yol)


# ---------------------------------------------------------------------------
# Capa uretimi (capa.format ile; ayristirma capa.parse'indir)


def rn_capa(yol: Sequence[str], p: int, s: int | None = None) -> str:
    """`rn:{kitap}(:{bolum})*:p{p}[:s{s}]` kanonik dizgisi; once adlar, sonra capa dogrulanir."""
    kesin = yol_denetle(yol)
    dizge = format(AnchorRef(Rn(kesin, p, s)))
    parse(dizge)  # sayi ve toplam uzunluk sinirlari capa ile ayni
    return dizge


def hasiye_yolu(bolum_yolu: Sequence[str], n: int) -> tuple[str, ...]:
    """Hasiye bolumunun yolu: `{bolum_yolu}:hasiye-{n}` (`n` bolumdeki atif sirasidir)."""
    yol = (*yol_denetle(bolum_yolu), sira_adi("hasiye", n))
    return yol_denetle(yol)


def parca_slug(n: int) -> str:
    """Lahika parcasi icin kaynakta numara yoksa `parca-{n}`."""
    return sira_adi("parca", n)


LAHIKA_SONEKI: Final = "-lahikasi"


def lahika_mi(kitap_slug: str) -> bool:
    """Kitap bir Lahika mi (Barla, Kastamonu, Emirdag 1 ve 2; Osmanlica karsiliklari dahil).

    Kitap slug'i `-lahikasi` ile biter ya da `-lahikasi-{n}` / `-osmanlica` / `-arapca` ekleri
    sonrasinda `-lahikasi` ile bitiyorsa (`shared/data/risale-kitaplar.json` slug'lari).
    """
    govde = kitap_slug.removesuffix(OSMANLICA_EKI).removesuffix(ARAPCA_EKI)
    return govde.endswith(LAHIKA_SONEKI) or re.fullmatch(r".*-lahikasi-[0-9]+", govde) is not None


def kardes_slug(slug: str, mevcut: Collection[str]) -> str:
    """Kardes cakismasinda `-2` (sonra `-3` ...) eki; sonuc 64 karakteri asmaz.

    `slug` `mevcut` icinde degilse oldugu gibi doner. Taban, ek sigsin diye gerekirse kisaltilir.
    """
    if slug not in mevcut:
        return slug
    sayac = 2
    while True:
        ek = f"-{sayac}"
        taban = slug[: MAX_SLUG - len(ek)].rstrip("-")
        aday = taban + ek
        if aday not in mevcut:
            return aday
        sayac += 1


def paket_kimligi(kitap: str) -> str:
    """`rn:{kitap}` -> paket kimligi `risale-{kitap}`."""
    return PAKET_ONEKI + kitap_slug_denetle(kitap)


def capa_paket_kimligi(capa: str) -> str:
    """`rn:` capasinin kitap paketi; baska turde capa icin `RisaleHatasi`."""
    cozulen = parse(capa).anchor
    if not isinstance(cozulen, Rn):
        raise RisaleHatasi("BICIM", "yalniz rn: capasi bir Risale paketine baglanir")
    return paket_kimligi(cozulen.yol[0])


# ---------------------------------------------------------------------------
# Slug turetme (Capa semasi bolum 5): acik harf esleme, `str.lower()` yok

# Turkce ve kardes harfler -> ASCII (kucuk ve buyuk). `I` ve `i` ayri iki harf degil, ikisi de `i`.
_HARF_ESLEME: Final[dict[str, str]] = {
    "ç": "c",  # c cedilla
    "Ç": "c",
    "ğ": "g",  # g breve
    "Ğ": "g",
    "ı": "i",  # dotless i
    "İ": "i",  # dotted capital I
    "ö": "o",  # o diaeresis
    "Ö": "o",
    "ş": "s",  # s cedilla
    "Ş": "s",
    "ü": "u",  # u diaeresis
    "Ü": "u",
    "â": "a",  # a circumflex
    "Â": "a",
    "î": "i",  # i circumflex
    "Î": "i",
    "û": "u",  # u circumflex
    "Û": "u",
}
_BUYUK_ASCII: Final[dict[str, str]] = {
    chr(kod): chr(kod + 32) for kod in range(ord("A"), ord("Z") + 1)
}
# Kesme isaretleri silinir (bosluk gibi tire olmazlar): ' ` U+2019 U+02BC U+02BB U+2018 U+00B4
_KESME: Final = frozenset("'`") | frozenset(map(chr, (0x2019, 0x02BC, 0x02BB, 0x2018, 0x00B4)))


def _harf(ch: str) -> str:
    """Tek karakterin slug karsiligi: harf ya da rakam, `""` (silinir) ya da `"-"` (ayirici)."""
    if ch in _KESME:
        return ""
    if ch in _HARF_ESLEME:
        return _HARF_ESLEME[ch]
    if ch in _BUYUK_ASCII:
        return _BUYUK_ASCII[ch]
    if ("a" <= ch <= "z") or ("0" <= ch <= "9"):
        return ch
    return "-"


def slug_turet(ad: str, *, kes: bool = True) -> str:
    """Gorunen addan slug turetir.

    Adimlar: her karakter once acik Turkce harf esleme tablosundan gecer (cedilla, yumusak g,
    noktasiz ve noktali i, umlaut, sapkali harfler); tabloda olmayan karakter NFD ile ayrilir ve
    birlesen isaretleri (ornegin ayrik `I` + U+0307) atilir; kesme isaretleri silinir; bosluk ve
    noktalama tire olur; ardisik tireler teke iner; bastaki ve sondaki tire atilir.

    `kes` dogruysa sonuc 64 karakteri asmaz (son tire sinirinda kesilir, olmazsa sert kesim);
    `kes=False` ham sonucu verir (uzunluk denetimi cagirana kalir). Bos sonucta
    `RisaleHatasi("BICIM")`. Sonuc harfle baslamayabilir; `kitap_slug_denetle` denetler.
    """
    parcalar: list[str] = []
    for ch in ad:
        if ch in _HARF_ESLEME or ch in _KESME:
            parcalar.append(_harf(ch))
            continue
        for parca in unicodedata.normalize("NFD", ch):
            if unicodedata.category(parca) != "Mn":  # ayrik birlesen isaretler atilir
                parcalar.append(_harf(parca))
    ham = re.sub("-+", "-", "".join(parcalar)).strip("-")
    if ham == "":
        raise RisaleHatasi("BICIM", "addan slug turetilemedi")
    if not kes or len(ham) <= MAX_SLUG:
        return ham
    kesik = ham[:MAX_SLUG]
    son_tire = kesik.rfind("-")
    if son_tire > 0 and ham[MAX_SLUG] != "-":
        kesik = kesik[:son_tire]
    return kesik.rstrip("-")


# ---------------------------------------------------------------------------
# Kitap tablosu: shared/data/risale-kitaplar.json

DEPO_KOKU: Final = Path(__file__).resolve().parents[4]
KITAPLAR_YOLU: Final = DEPO_KOKU / "shared" / "data" / "risale-kitaplar.json"
TABLO_SURUMU: Final = 1


@dataclass(frozen=True, slots=True)
class Diyanet:
    """Diyanet deposu kaynagi: `txt/` altindaki klasor ve dosya adlari (bayt bayt, NFC degil)."""

    klasor: str
    dosyalar: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class BolunmeParcasi:
    slug: str
    baslangic_sayfasi: int


@dataclass(frozen=True, slots=True)
class Bolunme:
    """Bir RNK kitabinin birden cok slug'a bolunmesi (K-51 madde 1)."""

    son_sayfa: int
    parcalar: tuple[BolunmeParcasi, ...]


@dataclass(frozen=True, slots=True)
class RnkBaglanti:
    raf: str
    uid: str
    ad: str
    bolunme: Bolunme | None = None


@dataclass(frozen=True, slots=True)
class Kitap:
    slug: str
    baslik: str
    dil: Dil
    yon: Yon
    metin_kaynagi: MetinKaynagi
    diyanet_karsiligi: DiyanetKarsiligi
    diyanet: Diyanet | None
    rnk: RnkBaglanti | None
    dogrulandi: bool

    @property
    def paket_kimligi(self) -> str:
        return paket_kimligi(self.slug)


def _hata(mesaj: str) -> RisaleHatasi:
    return RisaleHatasi("BICIM", mesaj)


def _kati_cift(ciftler: list[tuple[str, Any]]) -> dict[str, Any]:
    sonuc: dict[str, Any] = {}
    for anahtar, deger in ciftler:
        if anahtar in sonuc:
            raise _hata(f"yinelenen anahtar: {anahtar}")
        sonuc[anahtar] = deger
    return sonuc


def _nesne(
    deger: object, nerede: str, zorunlu: Iterable[str], istege_bagli: Iterable[str] = ()
) -> dict[str, Any]:
    if not isinstance(deger, dict):
        raise _hata(f"{nerede}: nesne bekleniyor")
    beklenen = {*zorunlu, *istege_bagli}
    fazla = sorted(set(deger) - beklenen)
    eksik = sorted(set(zorunlu) - set(deger))
    if fazla or eksik:
        raise _hata(f"{nerede}: bilinmeyen {fazla} ya da eksik {eksik} alan")
    return deger


def _metin(deger: object, nerede: str) -> str:
    if not isinstance(deger, str) or deger == "":
        raise _hata(f"{nerede}: bos olmayan metin bekleniyor")
    return deger


def _sayi(deger: object, nerede: str) -> int:
    if isinstance(deger, bool) or not isinstance(deger, int) or deger < 1:
        raise _hata(f"{nerede}: pozitif tam sayi bekleniyor")
    return deger


def dosya_adi_guvenli_mi(ad: str) -> bool:
    """Zip ve klasor adi guvenligi: bos, mutlak, `..` iceren, surucu harfli ya da bolulu olmaz."""
    if ad == "" or "\\" in ad or "\x00" in ad:
        return False
    yol = PurePosixPath(ad)
    return not (yol.is_absolute() or ".." in yol.parts or ":" in ad or "/" in ad)


def _diyanet(deger: object, nerede: str) -> Diyanet:
    nesne = _nesne(deger, nerede, ("klasor", "dosyalar"))
    klasor = _metin(nesne["klasor"], f"{nerede}.klasor")
    dosyalar = nesne["dosyalar"]
    if not isinstance(dosyalar, list) or not dosyalar:
        raise _hata(f"{nerede}.dosyalar: bos olmayan liste bekleniyor")
    adlar = tuple(_metin(d, f"{nerede}.dosyalar") for d in dosyalar)
    if not dosya_adi_guvenli_mi(klasor) or not all(dosya_adi_guvenli_mi(a) for a in adlar):
        raise _hata(f"{nerede}: guvensiz klasor ya da dosya adi")
    if len(set(adlar)) != len(adlar):
        raise _hata(f"{nerede}: yinelenen dosya adi")
    return Diyanet(klasor, adlar)


def _bolunme(deger: object, nerede: str) -> Bolunme:
    nesne = _nesne(deger, nerede, ("son_sayfa", "parcalar"))
    liste = nesne["parcalar"]
    if not isinstance(liste, list) or len(liste) < 2:
        raise _hata(f"{nerede}.parcalar: en az iki parca bekleniyor")
    parcalar: list[BolunmeParcasi] = []
    for sira, oge in enumerate(liste):
        ayrinti = _nesne(oge, f"{nerede}.parcalar[{sira}]", ("slug", "baslangic_sayfasi"))
        parcalar.append(
            BolunmeParcasi(
                kitap_slug_denetle(_metin(ayrinti["slug"], f"{nerede}.slug")),
                _sayi(ayrinti["baslangic_sayfasi"], f"{nerede}.baslangic_sayfasi"),
            )
        )
    son = _sayi(nesne["son_sayfa"], f"{nerede}.son_sayfa")
    baslar = [p.baslangic_sayfasi for p in parcalar]
    if baslar != sorted(set(baslar)) or son < baslar[-1]:
        raise _hata(f"{nerede}: sayfalar artan ve son_sayfa son parcadan kucuk olamaz")
    return Bolunme(son, tuple(parcalar))


def _rnk(deger: object, nerede: str) -> RnkBaglanti:
    nesne = _nesne(deger, nerede, ("raf", "uid", "ad"), ("bolunme",))
    raf = _metin(nesne["raf"], f"{nerede}.raf")
    if raf not in RNK_RAFLARI:
        raise _hata(f"{nerede}.raf: bilinmeyen raf")
    bolunme = None if "bolunme" not in nesne else _bolunme(nesne["bolunme"], f"{nerede}.bolunme")
    return RnkBaglanti(
        raf, _metin(nesne["uid"], f"{nerede}.uid"), _metin(nesne["ad"], f"{nerede}.ad"), bolunme
    )


def _kitap(deger: object, nerede: str) -> Kitap:
    nesne = _nesne(
        deger,
        nerede,
        (
            "slug",
            "baslik",
            "dil",
            "yon",
            "metin_kaynagi",
            "diyanet_karsiligi",
            "diyanet",
            "rnk",
            "dogrulandi",
        ),
    )
    slug = kitap_slug_denetle(_metin(nesne["slug"], f"{nerede}.slug"))
    dil, yon, kaynak = nesne["dil"], nesne["yon"], nesne["metin_kaynagi"]
    karsilik = nesne["diyanet_karsiligi"]
    if (
        dil not in DILLER
        or yon not in YONLER
        or kaynak not in METIN_KAYNAKLARI
        or karsilik not in DIYANET_KARSILIKLARI
    ):
        raise _hata(f"{nerede}: dil, yon, metin_kaynagi ya da diyanet_karsiligi gecersiz")
    if not isinstance(nesne["dogrulandi"], bool):
        raise _hata(f"{nerede}.dogrulandi: mantiksal deger bekleniyor")
    diyanet = None if nesne["diyanet"] is None else _diyanet(nesne["diyanet"], f"{nerede}.diyanet")
    rnk = None if nesne["rnk"] is None else _rnk(nesne["rnk"], f"{nerede}.rnk")
    kitap = Kitap(
        slug,
        _metin(nesne["baslik"], f"{nerede}.baslik"),
        dil,
        yon,
        kaynak,
        karsilik,
        diyanet,
        rnk,
        nesne["dogrulandi"],
    )
    _tutarlilik(kitap, nerede)
    return kitap


def _tutarlilik(kitap: Kitap, nerede: str) -> None:
    """Dil, yon, slug eki, metin kaynagi ve baglanti alanlari birbiriyle uyumlu olmali."""
    beklenen_yon = "ltr" if kitap.dil == "tr" else "rtl"
    ek_osmanlica, ek_arapca = kitap.slug.endswith(OSMANLICA_EKI), kitap.slug.endswith(ARAPCA_EKI)
    if kitap.yon != beklenen_yon:
        raise _hata(f"{nerede}: dil {kitap.dil} icin yon {beklenen_yon} olmali")
    if (kitap.dil == "ota") != ek_osmanlica or (kitap.dil == "ar") != ek_arapca:
        raise _hata(f"{nerede}: slug eki dille uyusmuyor (K-51 madde 4)")
    if kitap.dil != "tr" and (kitap.diyanet_karsiligi != "rnk" or kitap.diyanet is not None):
        raise _hata(f"{nerede}: Osmanlica ve Arapca kitabin Diyanet karsiligi yoktur")
    if (kitap.diyanet_karsiligi == "diyanet") != (kitap.diyanet is not None):
        raise _hata(
            f"{nerede}: diyanet alani yalniz diyanet_karsiligi=diyanet olan kitapta dolu olur"
        )
    if kitap.rnk is None:
        raise _hata(f"{nerede}: her kitap bir RNK kitabina baglidir (K-51 madde 1)")
    if kitap.rnk.raf not in _DIL_RAFLARI[kitap.dil]:
        raise _hata(f"{nerede}: RNK rafi dille uyusmuyor")
    bolunme = kitap.rnk.bolunme
    if bolunme is not None and kitap.slug not in {p.slug for p in bolunme.parcalar}:
        raise _hata(f"{nerede}: bolunme parcalari kitabin kendi slug'ini icermiyor")


def kitaplar(yol: Path | None = None) -> tuple[Kitap, ...]:
    """`shared/data/risale-kitaplar.json` tablosunu okur ve dogrular.

    `yol` verilmezse sabit depo yolu kullanilir; verilen yol depo kokunun icinde olmali (disari
    cikan yol `ValueError`). Tablo hatalarinda `RisaleHatasi`. Sira dosyadaki siradir; slug'lar
    tekildir; her slug `kitap_slug_denetle`'den gecer.
    """
    kaynak = KITAPLAR_YOLU if yol is None else yol.resolve()
    if not kaynak.is_relative_to(DEPO_KOKU):
        raise ValueError("kitap tablosu depo kokunun disinda olamaz")
    ham = json.loads(kaynak.read_bytes().decode("utf-8"), object_pairs_hook=_kati_cift)
    govde = _nesne(ham, "tablo", ("surum", "kitaplar"))
    if govde["surum"] != TABLO_SURUMU:
        raise _hata(f"tablo.surum {TABLO_SURUMU} olmali")
    liste = govde["kitaplar"]
    if not isinstance(liste, list) or not liste:
        raise _hata("tablo.kitaplar: bos olmayan liste bekleniyor")
    sonuc = tuple(_kitap(oge, f"kitaplar[{sira}]") for sira, oge in enumerate(liste))
    slug_listesi = [k.slug for k in sonuc]
    if len(set(slug_listesi)) != len(slug_listesi):
        raise _hata("yinelenen slug")
    return sonuc


def kitap_haritasi(yol: Path | None = None) -> Mapping[str, Kitap]:
    """Slug -> `Kitap` (dosya sirasi korunur)."""
    return {k.slug: k for k in kitaplar(yol)}
