"""Capa (kalici adres) ayristirma, bicimleme, siralama, kapsama ve rota islevleri.

Davranis `docs/03-veri/01-capa-semasi.md` (bolum 2, 3, 11) ve K-35 ile belirlidir; TypeScript
(`packages/anchors`) ve C# (`Mutalaa.Domain/Anchors`) uygulamalariyla ayni test vektorlerine
baglidir. Bu dosya vektor ureteciyle (`export/test_vectors.py`) baglanmaz.

Hata onceligi (K-35 madde 1): karakter kumesi, toplam uzunluk, desen, slug/derinlik/sayi
siniri, SURE_ARALIGI, AYET_ARALIGI, TERS_ARALIK, KANONIK_DEGIL.
"""

import re
from dataclasses import dataclass
from typing import ClassVar, Final, Literal

from mutalaa_pipeline.anchor.ayet_sayilari import AYET_SAYILARI

ErrorCode = Literal[
    "BICIM", "SURE_ARALIGI", "AYET_ARALIGI", "TERS_ARALIK", "KANONIK_DEGIL", "UZUNLUK"
]

MAX_UZUNLUK: Final = 256
MAX_SLUG: Final = 64
MAX_DERINLIK: Final = 8
MAX_SAYI: Final = 2_147_483_647
SEMALAR: Final = ("mutalaa", "mutalaa-internal", "mutalaa-dev")


class AnchorError(ValueError):
    """Capa hatasi; `code` alti koddan biridir."""

    code: ErrorCode

    def __init__(self, code: ErrorCode, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


# ---------------------------------------------------------------------------
# Turler


@dataclass(frozen=True, slots=True)
class Span:
    """Kod noktasi araligi `[start, end)`."""

    start: int
    end: int


@dataclass(frozen=True, slots=True)
class Q:
    """Kur'an ayeti; `ilk` tek basina kelime, `ilk` ve `son` kelime araligi."""

    t: ClassVar[str] = "q"
    sure: int
    ayet: int
    ilk: int | None = None
    son: int | None = None


@dataclass(frozen=True, slots=True)
class Qa:
    """Ayet araligi (`q:2:255-257`)."""

    t: ClassVar[str] = "qa"
    sure: int
    ilk: int
    son: int


@dataclass(frozen=True, slots=True)
class Konu:
    t: ClassVar[str] = "konu"
    slug: str


@dataclass(frozen=True, slots=True)
class Meal:
    t: ClassVar[str] = "meal"
    meal: str
    sure: int
    ayet: int


@dataclass(frozen=True, slots=True)
class Tf:
    """Ayete bagli tefsir paragrafi."""

    t: ClassVar[str] = "tf"
    eser: str
    sure: int
    ilk: int
    son: int
    p: int


@dataclass(frozen=True, slots=True)
class Tfb:
    """Ayetsiz tefsir bolumu paragrafi."""

    t: ClassVar[str] = "tfb"
    eser: str
    bolum: str
    p: int


@dataclass(frozen=True, slots=True)
class Rn:
    """Risale paragrafi (`s` yoksa) ya da cumlesi; `yol[0]` kitaptir."""

    t: ClassVar[str] = "rn"
    yol: tuple[str, ...]
    p: int
    s: int | None = None


@dataclass(frozen=True, slots=True)
class H:
    t: ClassVar[str] = "h"
    koleksiyon: str
    no: int


@dataclass(frozen=True, slots=True)
class Ht:
    t: ClassVar[str] = "ht"
    ceviri: str
    koleksiyon: str
    no: int


@dataclass(frozen=True, slots=True)
class K:
    t: ClassVar[str] = "k"
    yol: tuple[str, ...]
    p: int


type Anchor = Q | Qa | Konu | Meal | Tf | Tfb | Rn | H | Ht | K


@dataclass(frozen=True, slots=True)
class AnchorRef:
    anchor: Anchor
    span: Span | None = None

    def __str__(self) -> str:
        return format(self)


@dataclass(frozen=True, slots=True)
class UnitSpan:
    """Depolama bicimi: birim capa dizgisi ve istege bagli aralik."""

    unit: str
    span: tuple[int, int] | None = None


@dataclass(frozen=True, slots=True)
class Ayah:
    sure: int
    ayet: int


# ---------------------------------------------------------------------------
# Desenler (bolum 3). `[0-9]` kullanilir; `\d` kullanilmaz.

_SAYI = "[1-9][0-9]*"
_K3 = "[1-9][0-9]{0,2}"
_SLUG = "[a-z][a-z0-9]*(?:-[a-z0-9]+)*"
_SEG = "(?![ps][0-9]+(?::|@|\\Z))[a-z][a-z0-9]*(?:-[a-z0-9]+)*"
_ARA = "(?:@(?P<bas>0|[1-9][0-9]*)-(?P<bit>[1-9][0-9]*))?"

_KARAKTER = re.compile("[a-z0-9:@-]*")
_DESENLER: Final[dict[str, re.Pattern[str]]] = {
    "q": re.compile(
        f"q:(?P<sure>{_K3}):(?:(?P<ayet>{_K3})(?::(?P<ilk>{_K3})(?:-(?P<son>{_K3}))?)?"
        f"|(?P<ayet_ilk>{_K3})-(?P<ayet_son>{_K3}))"
    ),
    "konu": re.compile(f"konu:(?P<konu>{_SLUG})"),
    "meal": re.compile(f"meal:(?P<meal>{_SLUG}):(?P<sure>{_K3}):(?P<ayet>{_K3}){_ARA}"),
    "tf": re.compile(
        f"tf:(?P<eser>{_SLUG}):(?:(?P<sure>{_K3})-(?P<ilk>{_K3})-(?P<son>{_K3})"
        f"|(?P<bolum>{_SEG})):p(?P<p>{_SAYI}){_ARA}"
    ),
    "rn": re.compile(f"rn:(?P<yol>{_SEG}(?::{_SEG})*):p(?P<p>{_SAYI})(?::s(?P<s>{_SAYI})|{_ARA})"),
    "h": re.compile(f"h:(?P<koleksiyon>{_SLUG}):(?P<no>{_SAYI}){_ARA}"),
    "ht": re.compile(f"ht:(?P<ceviri>{_SLUG}):(?P<koleksiyon>{_SLUG}):(?P<no>{_SAYI}){_ARA}"),
    "k": re.compile(f"k:(?P<yol>{_SEG}(?::{_SEG})*):p(?P<p>{_SAYI}){_ARA}"),
}


def _tur(s: str) -> str | None:
    """Onekten turu belirler; tanimsizsa None."""
    onek = s.split(":", 1)[0]
    return onek if ":" in s and onek in _DESENLER else None


def _sayi(deger: str) -> int:
    sonuc = int(deger)
    if sonuc > MAX_SAYI:
        raise AnchorError("UZUNLUK", "sayi alani 2147483647 degerini asiyor")
    return sonuc


def _slug(deger: str) -> str:
    if len(deger) > MAX_SLUG:
        raise AnchorError("UZUNLUK", "slug 64 karakteri asiyor")
    return deger


def _yol(deger: str) -> tuple[str, ...]:
    parcalar = deger.split(":")
    if len(parcalar) > MAX_DERINLIK:
        raise AnchorError("UZUNLUK", "bolum derinligi 8'i asiyor")
    return tuple(_slug(parca) for parca in parcalar)


def _anlam(
    sure: int | None,
    ayetler: tuple[int, ...],
    araliklar: tuple[tuple[int, int, bool], ...],
    span: Span | None,
) -> None:
    """Anlam denetimleri: SURE, AYET, TERS, KANONIK sirasiyla (K-35 madde 1).

    `araliklar` ogeleri `(ilk, son, tek_yazilmaz)`; `tek_yazilmaz` dogruysa `ilk == son`
    kanonik degildir. `@` araliginda `baslangic >= bitis` ters aralik sayilir.
    """
    if sure is not None:
        if not 1 <= sure <= len(AYET_SAYILARI):
            raise AnchorError("SURE_ARALIGI", "sure 1-114 disinda")
        if any(ayet > AYET_SAYILARI[sure - 1] for ayet in ayetler):
            raise AnchorError("AYET_ARALIGI", "ayet sure icindeki ayet sayisini asiyor")
    if any(ilk > son for ilk, son, _ in araliklar) or (span is not None and span.start >= span.end):
        raise AnchorError("TERS_ARALIK", "aralik ters")
    if any(ilk == son and yasak for ilk, son, yasak in araliklar):
        raise AnchorError("KANONIK_DEGIL", "tek ogeli aralik kanonik degil")


def _aralik(grup: dict[str, str | None]) -> Span | None:
    bas, bit = grup.get("bas"), grup.get("bit")
    if bas is None or bit is None:
        return None
    return Span(_sayi(bas), _sayi(bit))


def _kur(tur: str, grup: dict[str, str | None]) -> AnchorRef:
    """Eslesen gruplardan sinir, anlam denetimlerini yapip capayi kurar."""

    def g(ad: str) -> str:
        deger = grup[ad]
        if deger is None:  # desen bunu garanti eder
            raise AnchorError("BICIM", "beklenen alan yok")
        return deger

    def opt(ad: str) -> int | None:
        deger = grup.get(ad)
        return None if deger is None else _sayi(deger)

    span = _aralik(grup)
    anchor: Anchor
    if tur == "q":
        if grup["ayet_ilk"] is not None:
            sure, ilk, son = _sayi(g("sure")), _sayi(g("ayet_ilk")), _sayi(g("ayet_son"))
            _anlam(sure, (ilk, son), ((ilk, son, True),), span)
            return AnchorRef(Qa(sure, ilk, son))
        sure, ayet = _sayi(g("sure")), _sayi(g("ayet"))
        kilk, kson = opt("ilk"), opt("son")
        kelimeler = ((kilk, kson, True),) if kilk is not None and kson is not None else ()
        _anlam(sure, (ayet,), kelimeler, span)
        return AnchorRef(Q(sure, ayet, kilk, kson))
    if tur == "konu":
        return AnchorRef(Konu(_slug(g("konu"))))
    if tur == "meal":
        ad = _slug(g("meal"))
        sure, ayet = _sayi(g("sure")), _sayi(g("ayet"))
        _anlam(sure, (ayet,), (), span)
        anchor = Meal(ad, sure, ayet)
    elif tur == "tf":
        eser = _slug(g("eser"))
        p = _sayi(g("p"))
        if grup["bolum"] is not None:
            bolum = _slug(g("bolum"))  # slug siniri anlam denetiminden once (K-35 madde 1)
            _anlam(None, (), (), span)
            anchor = Tfb(eser, bolum, p)
        else:
            sure, ilk, son = _sayi(g("sure")), _sayi(g("ilk")), _sayi(g("son"))
            _anlam(sure, (ilk, son), ((ilk, son, False),), span)
            anchor = Tf(eser, sure, ilk, son, p)
    elif tur == "rn":
        yol, p, s = _yol(g("yol")), _sayi(g("p")), opt("s")
        _anlam(None, (), (), span)
        anchor = Rn(yol, p, s)
    elif tur == "h":
        koleksiyon, no = _slug(g("koleksiyon")), _sayi(g("no"))
        _anlam(None, (), (), span)
        anchor = H(koleksiyon, no)
    elif tur == "ht":
        ceviri, koleksiyon = _slug(g("ceviri")), _slug(g("koleksiyon"))
        no = _sayi(g("no"))
        _anlam(None, (), (), span)
        anchor = Ht(ceviri, koleksiyon, no)
    else:
        yol, p = _yol(g("yol")), _sayi(g("p"))
        _anlam(None, (), (), span)
        anchor = K(yol, p)
    return AnchorRef(anchor, span)


def parse(s: str) -> AnchorRef:
    """Capa dizgisini ayristirir; gecersizse `AnchorError`."""
    if _KARAKTER.fullmatch(s) is None:
        raise AnchorError("BICIM", "izin verilmeyen karakter")
    if len(s) > MAX_UZUNLUK:
        raise AnchorError("UZUNLUK", "capa 256 karakteri asiyor")
    tur = _tur(s)
    eslesme = None if tur is None else _DESENLER[tur].fullmatch(s)
    if tur is None or eslesme is None:
        raise AnchorError("BICIM", "capa gramere uymuyor")
    return _kur(tur, dict(eslesme.groupdict()))


def try_parse(s: str) -> AnchorRef | None:
    """`parse` gibi, ama gecersizde `None` doner."""
    try:
        return parse(s)
    except AnchorError:
        return None


# ---------------------------------------------------------------------------
# Bicimleme


def _govde(a: Anchor) -> str:
    match a:
        case Q(sure, ayet, None, _):
            return f"q:{sure}:{ayet}"
        case Q(sure, ayet, ilk, None):
            return f"q:{sure}:{ayet}:{ilk}"
        case Q(sure, ayet, ilk, son):
            return f"q:{sure}:{ayet}:{ilk}-{son}"
        case Qa(sure, ilk, son):
            return f"q:{sure}:{ilk}-{son}"
        case Konu(slug):
            return f"konu:{slug}"
        case Meal(meal, sure, ayet):
            return f"meal:{meal}:{sure}:{ayet}"
        case Tf(eser, sure, ilk, son, p):
            return f"tf:{eser}:{sure}-{ilk}-{son}:p{p}"
        case Tfb(eser, bolum, p):
            return f"tf:{eser}:{bolum}:p{p}"
        case Rn(yol, p, None):
            return f"rn:{':'.join(yol)}:p{p}"
        case Rn(yol, p, s):
            return f"rn:{':'.join(yol)}:p{p}:s{s}"
        case H(koleksiyon, no):
            return f"h:{koleksiyon}:{no}"
        case Ht(ceviri, koleksiyon, no):
            return f"ht:{ceviri}:{koleksiyon}:{no}"
        case K(yol, p):
            return f"k:{':'.join(yol)}:p{p}"


def _aralik_kabul_eder(a: Anchor) -> bool:
    """`@` araligi Kur'an, konu ve cumle capasina eklenmez."""
    match a:
        case Q() | Qa() | Konu():
            return False
        case Rn(s=s):
            return s is None
        case _:
            return True


def format(r: AnchorRef) -> str:
    """Kanonik dizgiyi uretir; `parse(format(r)) == r`."""
    govde = _govde(r.anchor)
    if r.span is None:
        return govde
    if not _aralik_kabul_eder(r.anchor):
        raise ValueError("bu capa turune '@' araligi eklenemez")
    return f"{govde}@{r.span.start}-{r.span.end}"


# ---------------------------------------------------------------------------
# Siralama (K-35 madde 3)

type _Parca = int | str | tuple[int | str, ...]
type SortKey = tuple[_Parca, ...]


def _istege_bagli(deger: int | None) -> tuple[int, ...]:
    return (0,) if deger is None else (1, deger)


def _aralik_anahtari(span: Span | None) -> tuple[int, ...]:
    return (0,) if span is None else (1, span.start, span.end)


def sort_key(r: AnchorRef) -> SortKey:
    """Okuma sirasini veren karsilastirilabilir anahtar; ayni tur ayni bicimdedir."""
    a = r.anchor
    sp = _aralik_anahtari(r.span)
    match a:
        case Q(sure, ayet, None, _):
            return (0, sure, ayet, 0, 0, 0, 0)
        case Q(sure, ayet, ilk, None):
            return (0, sure, ayet, 1, ilk or 0, 0, 0)
        case Q(sure, ayet, ilk, son):
            return (0, sure, ayet, 1, ilk or 0, 1, son or 0)
        case Qa(sure, ilk, son):
            return (0, sure, ilk, 2, son, 0, 0)
        case Meal(meal, sure, ayet):
            return (1, meal, sure, ayet, sp)
        case Tf(eser, sure, ilk, son, p):
            return (2, eser, sure, ilk, son, p, sp)
        case Tfb(eser, bolum, p):
            return (3, eser, bolum, p, sp)
        case Rn(yol, p, s):
            return (4, yol, p, _istege_bagli(s), sp)
        case H(koleksiyon, no):
            return (5, koleksiyon, no, sp)
        case Ht(ceviri, koleksiyon, no):
            return (6, ceviri, koleksiyon, no, sp)
        case K(yol, p):
            return (7, yol, p, sp)
        case Konu(slug):
            return (8, slug)


# ---------------------------------------------------------------------------
# Kapsama (bolum 11 ve K-35 madde 4)


def _span_kapsar(dis: Span | None, ic: Span | None) -> bool:
    if dis is None:
        return True
    return ic is not None and dis.start <= ic.start and ic.end <= dis.end


def _kelime_siniri(q: Q) -> tuple[int, int] | None:
    if q.ilk is None:
        return None
    return (q.ilk, q.ilk if q.son is None else q.son)


def contains(a: AnchorRef, b: AnchorRef) -> bool:
    """`a`, `b`yi kapsiyor mu? Ayni capa her zaman kapsar."""
    if a == b:
        return True
    da, db = a.anchor, b.anchor
    match da, db:
        case Qa(), Q():
            return da.sure == db.sure and da.ilk <= db.ayet <= da.son
        case Qa(), Qa():
            return da.sure == db.sure and da.ilk <= db.ilk and db.son <= da.son
        case Q(), Q():
            if (da.sure, da.ayet) != (db.sure, db.ayet):
                return False
            dis, ic = _kelime_siniri(da), _kelime_siniri(db)
            if dis is None:
                return True
            return ic is not None and dis[0] <= ic[0] and ic[1] <= dis[1]
        case Rn(), Rn():
            if (da.yol, da.p) != (db.yol, db.p):
                return False
            if da.s is not None:
                return False  # cumle yalniz kendini kapsar (esitlik yukarida)
            if db.s is not None:
                return a.span is None  # araliksiz paragraf cumlelerini kapsar
            return _span_kapsar(a.span, b.span)
        case _:
            if type(da) is not type(db) or isinstance(da, (Q, Qa, Konu)):
                return False
            return da == db and _span_kapsar(a.span, b.span)


# ---------------------------------------------------------------------------
# Birim islevleri (K-35 madde 5)


def unit_of(r: AnchorRef) -> AnchorRef:
    """Kelime(ler) ayete, cumle paragrafa iner; `@` araligi atilir."""
    match r.anchor:
        case Q(sure, ayet):
            return AnchorRef(Q(sure, ayet))
        case Rn(yol, p):
            return AnchorRef(Rn(yol, p))
        case anchor:
            return AnchorRef(anchor)


def to_unit_span(r: AnchorRef) -> UnitSpan:
    """Depolama bicimi; ayet araligi ve cumle capasi icin `ValueError`."""
    match r.anchor:
        case Qa():
            raise ValueError("ayet araligi icin covered_ayahs kullanilir")
        case Rn(s=s) if s is not None:
            raise ValueError("cumle sinirini icerik verisi belirler")
        case Q(_, _, ilk, son) if ilk is not None:
            bitis = ilk if son is None else son
            return UnitSpan(format(unit_of(r)), (ilk, bitis + 1))
    birim = format(unit_of(r))
    return UnitSpan(birim, None if r.span is None else (r.span.start, r.span.end))


def covered_ayahs(r: AnchorRef) -> tuple[Ayah, ...]:
    """`q`, `qa`, `tf` ve `meal` icin kapsanan ayetler; digerlerinde bos."""
    match r.anchor:
        case Q(sure, ayet) | Meal(_, sure, ayet):
            return (Ayah(sure, ayet),)
        case Qa(sure, ilk, son) | Tf(_, sure, ilk, son, _):
            return tuple(Ayah(sure, ayet) for ayet in range(ilk, son + 1))
        case _:
            return ()


# ---------------------------------------------------------------------------
# Rota (bolum 11, K-35 madde 6)


def _yerel(r: AnchorRef, sema: str) -> str:
    yol = format(AnchorRef(r.anchor)).replace(":", "/")
    sorgu = "" if r.span is None else f"?aralik={r.span.start}-{r.span.end}"
    return f"{sema}://{yol}{sorgu}"


def _web(r: AnchorRef) -> str:
    a = r.anchor
    tablo_disi = ValueError("bu capa icin web rotasi tanimli degil")
    match a:
        case Q(sure, ayet, None, _) if r.span is None:
            return f"/kuran/{sure}/{ayet}"
        case Q(sure, ayet, ilk, son) if ilk is not None and son is not None:
            return f"/kuran/{sure}/{ayet}?k={ilk}-{son}"
        case Qa(sure, ilk, son):
            return f"/kuran/{sure}/{ilk}-{son}"
        case Konu(slug):
            return f"/konu/{slug}"
        case Meal(meal, sure, ayet) if r.span is None:
            return f"/meal/{meal}/{sure}#{ayet}"
        case Tf(eser, sure, ilk, _, p) if r.span is None:
            return f"/tefsir/{eser}/{sure}/{ilk}#p{p}"
        case Rn(yol, p, None):
            return f"/risale/{'/'.join(yol)}#p{p}"
        case H(koleksiyon, no) if r.span is None:
            return f"/hadis/{koleksiyon}/{no}"
        case _:
            raise tablo_disi


def to_route(r: AnchorRef, hedef: Literal["native", "web"], sema: str | None = None) -> str:
    """Yerel ya da web rotasi; web yalniz bolum 11 tablosundaki bicimler icin (digerinde hata)."""
    if hedef == "native":
        kullanilan = "mutalaa" if sema is None else sema
        if kullanilan not in SEMALAR:
            raise ValueError("bilinmeyen sema")
        return _yerel(r, kullanilan)
    if hedef == "web":
        return _web(r)
    raise ValueError("hedef 'native' ya da 'web' olmali")
