"""`shared/test-vectors` ureteci ve denetleyicisi (A04.2, `.tmp/a04/vektor-sartnamesi.md` 1-4).

Hesaplanan alanlar standart kitaplikla yeniden yazilir: `offsets` icin `codepoints`, `utf16`,
`cp_to_utf16`; `content-hash` icin `sha256`. Elle yazilan alanlara (`ref`, `canonical`, `unit`,
`unit_span`, `ayahs`, hata kodlari, compare/contains/route sonuclari, `snap`, kanonik `text`)
dokunulmaz; yalniz bicimleri denetlenir ve anahtar sirasi normalize edilir.

Sinir satirlari (`an-s...`, `an-u-...`) her calistirmada atilip yeniden kurulur. Ayet sayilari
`shared/data/ayet-sayilari.json` dosyasindan okunur. Bu modul capa ayristiricisini ice aktarmaz:
beklenen degerler ayristiricidan uretilirse vektor kendini dogrular (totoloji).
"""

import hashlib
import re
import unicodedata
from collections.abc import Collection, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

from mutalaa_pipeline.export.ayet_sayilari import json_oku
from mutalaa_pipeline.export.ortak import GirdiHatasi, ayni_mi, kati_json, utf8_oku, yaz

VEKTOR_KLASORU: Final = "shared/test-vectors"

VALID: Final = "anchors/valid.jsonl"
INVALID: Final = "anchors/invalid.jsonl"
COMPARE: Final = "anchors/compare.jsonl"
CONTAINS: Final = "anchors/contains.jsonl"
ROUTE: Final = "anchors/route.jsonl"
OFFSETS: Final = "offsets/offsets.jsonl"
HASH: Final = "content-hash/hash.jsonl"
DOSYALAR: Final = (VALID, INVALID, COMPARE, CONTAINS, ROUTE, OFFSETS, HASH)

_ONEKLER: Final = {
    VALID: "an",
    INVALID: "an",
    COMPARE: "cm",
    CONTAINS: "ct",
    ROUTE: "ro",
    OFFSETS: "of",
    HASH: "ch",
}
# Kimlik benzersizligi bu gruplarin her birinde ayri ayri aranir (valid ve invalid birlikte).
_KIMLIK_GRUPLARI: Final = ((VALID, INVALID), (COMPARE,), (CONTAINS,), (ROUTE,), (OFFSETS,), (HASH,))

HATA_KODLARI: Final = frozenset(
    {"BICIM", "SURE_ARALIGI", "AYET_ARALIGI", "TERS_ARALIK", "KANONIK_DEGIL", "UZUNLUK"}
)

_KIMLIK: Final = re.compile(r"(?P<onek>[a-z]{2})-[a-z0-9]+(?:-[a-z0-9]+)*")
URETILEN_ONEKLER: Final = ("an-s", "an-u-")
_BOM: Final = chr(0xFEFF)  # kaynakta gorunmez karakter olmasin diye chr ile

_SATIR_ALANLARI: Final = ("id", "input", "expected", "note")
_ANCHOR_ALANLARI: Final[dict[str, tuple[tuple[str, ...], frozenset[str]]]] = {
    "q": (("t", "sure", "ayet", "ilk", "son"), frozenset({"t", "sure", "ayet"})),
    "qa": (("t", "sure", "ilk", "son"), frozenset({"t", "sure", "ilk", "son"})),
    "konu": (("t", "slug"), frozenset({"t", "slug"})),
    "meal": (("t", "meal", "sure", "ayet"), frozenset({"t", "meal", "sure", "ayet"})),
    "tf": (
        ("t", "eser", "sure", "ilk", "son", "p"),
        frozenset({"t", "eser", "sure", "ilk", "son", "p"}),
    ),
    "tfb": (("t", "eser", "bolum", "p"), frozenset({"t", "eser", "bolum", "p"})),
    "rn": (("t", "yol", "p", "s"), frozenset({"t", "yol", "p"})),
    "h": (("t", "koleksiyon", "no"), frozenset({"t", "koleksiyon", "no"})),
    "ht": (("t", "ceviri", "koleksiyon", "no"), frozenset({"t", "ceviri", "koleksiyon", "no"})),
    "k": (("t", "yol", "p"), frozenset({"t", "yol", "p"})),
}
_ANCHOR_SAYI_ALANLARI: Final = frozenset({"sure", "ayet", "ilk", "son", "p", "s", "no"})

# Sartname 1: bu kategoriler, BMP disi karakterler ve Arapca bloklari \uXXXX ile yazilir.
_KACAN_KATEGORILER: Final = frozenset(
    {"Mn", "Mc", "Me", "Cc", "Cf", "Zl", "Zp", "Zs", "Co", "Cs", "Cn"}
)
_ARAPCA_BLOKLARI: Final = (
    (0x0600, 0x06FF),
    (0x0750, 0x077F),
    (0x08A0, 0x08FF),
    (0xFB50, 0xFDFF),
    (0xFE70, 0xFEFF),
)
_KISA_KACISLAR: Final = {
    '"': '\\"',
    "\\": "\\\\",
    "\b": "\\b",
    "\f": "\\f",
    "\n": "\\n",
    "\r": "\\r",
    "\t": "\\t",
}


@dataclass(frozen=True)
class Satir:
    """Bir vektor satiri; `konum` yalniz hata iletisi icindir, dosyaya yazilmaz."""

    id: str
    input: object
    expected: object
    note: str | None = None
    konum: str = field(default="uretildi", compare=False)


# --- Bicim denetimi -----------------------------------------------------------------------


def _nesne(
    deger: object, sira: Sequence[str], zorunlu: Collection[str], baglam: str
) -> dict[str, object]:
    """Nesneyi denetler; anahtarlari `sira`ya gore dizilmis yeni bir sozluk dondurur."""
    if not isinstance(deger, dict):
        raise GirdiHatasi(f"{baglam}: nesne bekleniyor")
    tanimsiz = sorted(anahtar for anahtar in deger if anahtar not in sira)
    if tanimsiz:
        raise GirdiHatasi(f"{baglam}: tanimsiz alan: {', '.join(tanimsiz)}")
    eksik = [anahtar for anahtar in sira if anahtar in zorunlu and anahtar not in deger]
    if eksik:
        raise GirdiHatasi(f"{baglam}: eksik alan: {', '.join(eksik)}")
    return {anahtar: deger[anahtar] for anahtar in sira if anahtar in deger}


def _tam(deger: object, baglam: str) -> int:
    if isinstance(deger, bool) or not isinstance(deger, int):
        raise GirdiHatasi(f"{baglam}: tam sayi bekleniyor")
    return deger


def _dizgi(deger: object, baglam: str) -> str:
    if not isinstance(deger, str):
        raise GirdiHatasi(f"{baglam}: dizgi bekleniyor")
    return deger


def _liste(deger: object, baglam: str) -> list[object]:
    if not isinstance(deger, list):
        raise GirdiHatasi(f"{baglam}: dizi bekleniyor")
    return list(deger)


def _dizgi_cifti(deger: object, baglam: str) -> list[object]:
    liste = _liste(deger, baglam)
    if len(liste) != 2:
        raise GirdiHatasi(f"{baglam}: iki elemanli dizi bekleniyor")
    return [_dizgi(liste[0], f"{baglam}[0]"), _dizgi(liste[1], f"{baglam}[1]")]


def _sayi_cifti(deger: object, baglam: str) -> list[object]:
    liste = _liste(deger, baglam)
    if len(liste) != 2:
        raise GirdiHatasi(f"{baglam}: iki elemanli dizi bekleniyor")
    return [_tam(liste[0], f"{baglam}[0]"), _tam(liste[1], f"{baglam}[1]")]


def _anchor(deger: object, baglam: str) -> dict[str, object]:
    if not isinstance(deger, dict):
        raise GirdiHatasi(f"{baglam}: nesne bekleniyor")
    tur = deger.get("t")
    if not isinstance(tur, str) or tur not in _ANCHOR_ALANLARI:
        raise GirdiHatasi(f"{baglam}: 't' bilinen bir capa turu degil")
    sira, zorunlu = _ANCHOR_ALANLARI[tur]
    nesne = _nesne(deger, sira, zorunlu, baglam)
    for ad, alan in nesne.items():
        if ad in _ANCHOR_SAYI_ALANLARI:
            _tam(alan, f"{baglam}.{ad}")
        elif ad == "yol":
            yol = _liste(alan, f"{baglam}.yol")
            for sira_no, parca in enumerate(yol):
                _dizgi(parca, f"{baglam}.yol[{sira_no}]")
        else:
            _dizgi(alan, f"{baglam}.{ad}")
    return nesne


def _valid_beklenen(deger: object, baglam: str) -> dict[str, object]:
    nesne = _nesne(
        deger, ("ref", "canonical", "unit", "unit_span", "ayahs"), ("ref", "canonical"), baglam
    )
    ref = _nesne(nesne["ref"], ("anchor", "span"), ("anchor",), f"{baglam}.ref")
    ref["anchor"] = _anchor(ref["anchor"], f"{baglam}.ref.anchor")
    if "span" in ref:
        span = _nesne(ref["span"], ("start", "end"), ("start", "end"), f"{baglam}.ref.span")
        _tam(span["start"], f"{baglam}.ref.span.start")
        _tam(span["end"], f"{baglam}.ref.span.end")
        ref["span"] = span
    nesne["ref"] = ref
    _dizgi(nesne["canonical"], f"{baglam}.canonical")
    if "unit" in nesne:
        _dizgi(nesne["unit"], f"{baglam}.unit")
    if "unit_span" in nesne and nesne["unit_span"] is not None:
        birim = _nesne(nesne["unit_span"], ("unit", "span"), ("unit",), f"{baglam}.unit_span")
        _dizgi(birim["unit"], f"{baglam}.unit_span.unit")
        if "span" in birim:
            birim["span"] = _sayi_cifti(birim["span"], f"{baglam}.unit_span.span")
        nesne["unit_span"] = birim
    if "ayahs" in nesne:
        ayetler: list[object] = []
        for sira_no, oge in enumerate(_liste(nesne["ayahs"], f"{baglam}.ayahs")):
            ayet_baglami = f"{baglam}.ayahs[{sira_no}]"
            ayet = _nesne(oge, ("sure", "ayet"), ("sure", "ayet"), ayet_baglami)
            _tam(ayet["sure"], f"{ayet_baglami}.sure")
            _tam(ayet["ayet"], f"{ayet_baglami}.ayet")
            ayetler.append(ayet)
        nesne["ayahs"] = ayetler
    return nesne


def _sha256(metin: str, baglam: str) -> str:
    try:
        return hashlib.sha256(metin.encode("utf-8")).hexdigest()
    except UnicodeEncodeError as hata:
        raise GirdiHatasi(f"{baglam}: metinde tek basina vekil (surrogate) var") from hata


def _utf16_konumlari(metin: str, baglam: str) -> tuple[int, list[object]]:
    """UTF-16 uzunlugu ve her kod noktasi konumu (0..n) icin `[cp, utf16]` ciftleri."""
    try:
        uzunluk = len(metin.encode("utf-16-le")) // 2
    except UnicodeEncodeError as hata:
        raise GirdiHatasi(f"{baglam}: metinde tek basina vekil (surrogate) var") from hata
    ciftler: list[object] = []
    birim = 0
    for kod_noktasi, karakter in enumerate(metin):
        ciftler.append([kod_noktasi, birim])
        birim += 2 if ord(karakter) > 0xFFFF else 1
    ciftler.append([len(metin), birim])
    if birim != uzunluk:
        raise GirdiHatasi(f"{baglam}: UTF-16 uzunlugu tutarsiz")
    return uzunluk, ciftler


def _normalize(dosya: str, satir: Satir) -> Satir:
    """Dosyaya gore bicimi denetler, anahtar sirasini dizer, hesaplanan alanlari yazar."""
    b = f"{satir.konum} ({satir.id})"
    girdi: object
    beklenen: object
    if dosya == VALID:
        girdi = _dizgi(satir.input, f"{b} input")
        beklenen = _valid_beklenen(satir.expected, f"{b} expected")
    elif dosya == INVALID:
        girdi = _dizgi(satir.input, f"{b} input")
        kod = _dizgi(satir.expected, f"{b} expected")
        if kod not in HATA_KODLARI:
            raise GirdiHatasi(f"{b} expected: bilinmeyen hata kodu")
        beklenen = kod
    elif dosya == COMPARE:
        girdi = _dizgi_cifti(satir.input, f"{b} input")
        sonuc = _tam(satir.expected, f"{b} expected")
        if sonuc not in (-1, 0, 1):
            raise GirdiHatasi(f"{b} expected: -1, 0 ya da 1 bekleniyor")
        beklenen = sonuc
    elif dosya == CONTAINS:
        girdi = _dizgi_cifti(satir.input, f"{b} input")
        if not isinstance(satir.expected, bool):
            raise GirdiHatasi(f"{b} expected: true ya da false bekleniyor")
        beklenen = satir.expected
    elif dosya == ROUTE:
        rota_girdisi = _nesne(satir.input, ("capa", "sema"), ("capa",), f"{b} input")
        for ad, deger in rota_girdisi.items():
            _dizgi(deger, f"{b} input.{ad}")
        rota = _nesne(satir.expected, ("native", "web"), ("native", "web"), f"{b} expected")
        _dizgi(rota["native"], f"{b} expected.native")
        if rota["web"] is not None:
            _dizgi(rota["web"], f"{b} expected.web")
        girdi, beklenen = rota_girdisi, rota
    elif dosya == OFFSETS:
        metin = _dizgi(satir.input, f"{b} input")
        eski = _nesne(
            satir.expected, ("codepoints", "utf16", "cp_to_utf16", "snap"), (), f"{b} expected"
        )
        uzunluk, ciftler = _utf16_konumlari(metin, f"{b} input")
        yeni: dict[str, object] = {
            "codepoints": len(metin),
            "utf16": uzunluk,
            "cp_to_utf16": ciftler,
        }
        if "snap" in eski:
            yeni["snap"] = _snap(eski["snap"], len(metin), f"{b} expected.snap")
        girdi, beklenen = metin, yeni
    elif dosya == HASH:
        girdi, beklenen = _hash(satir, b)
    else:  # pragma: no cover - DOSYALAR disinda dosya yok
        raise GirdiHatasi(f"bilinmeyen vektor dosyasi: {dosya}")
    return Satir(satir.id, girdi, beklenen, satir.note, satir.konum)


def _snap(deger: object, uzunluk: int, baglam: str) -> list[object]:
    sonuc: list[object] = []
    for sira_no, oge in enumerate(_liste(deger, baglam)):
        oge_baglami = f"{baglam}[{sira_no}]"
        cift = _nesne(oge, ("in", "out"), ("in", "out"), oge_baglami)
        for ad in ("in", "out"):
            aralik = _sayi_cifti(cift[ad], f"{oge_baglami}.{ad}")
            bas, bit = _tam(aralik[0], oge_baglami), _tam(aralik[1], oge_baglami)
            if not 0 <= bas <= bit <= uzunluk:
                raise GirdiHatasi(f"{oge_baglami}.{ad}: 0 <= s <= e <= codepoints degil")
            cift[ad] = aralik
        sonuc.append(cift)
    return sonuc


def _hash(satir: Satir, b: str) -> tuple[object, object]:
    girdi = _nesne(satir.input, ("text", "op"), ("text", "op"), f"{b} input")
    metin = _dizgi(girdi["text"], f"{b} input.text")
    islem = _dizgi(girdi["op"], f"{b} input.op")
    eski = _nesne(satir.expected, ("sha256", "text"), (), f"{b} expected")
    if islem == "ham":
        if "text" in eski:
            raise GirdiHatasi(f"{b} expected: 'ham' satirda 'text' tanimsiz")
        return girdi, {"sha256": _sha256(metin, f"{b} input.text")}
    if islem == "kanonik":
        if "text" not in eski:
            raise GirdiHatasi(f"{b} expected: 'kanonik' satirda 'text' eksik")
        kanonik = _dizgi(eski["text"], f"{b} expected.text")
        return girdi, {"sha256": _sha256(kanonik, f"{b} expected.text"), "text": kanonik}
    raise GirdiHatasi(f"{b} input.op: 'ham' ya da 'kanonik' bekleniyor")


# --- Okuma ------------------------------------------------------------------------------


def _satir_coz(metin: str, konum: str, dosya: str) -> Satir:
    try:
        veri = kati_json(metin)
    except GirdiHatasi as hata:
        raise GirdiHatasi(f"{konum}: {hata}") from hata
    nesne = _nesne(veri, _SATIR_ALANLARI, ("id", "input", "expected"), konum)
    kimlik = _dizgi(nesne["id"], f"{konum} id")
    eslesme = _KIMLIK.fullmatch(kimlik)
    if eslesme is None:
        raise GirdiHatasi(f"{konum}: id kucuk harf ASCII, rakam ve tire olmali")
    if eslesme.group("onek") != _ONEKLER[dosya]:
        raise GirdiHatasi(f"{konum}: id '{_ONEKLER[dosya]}-' ile baslamali")
    not_metni = _dizgi(nesne["note"], f"{konum} note") if "note" in nesne else None
    return Satir(kimlik, nesne["input"], nesne["expected"], not_metni, konum)


def _dosya_oku(kok: Path, dosya: str) -> list[Satir]:
    goreli = f"{VEKTOR_KLASORU}/{dosya}"
    yol = kok / goreli
    if not yol.exists():
        return []
    if not yol.is_file():
        raise GirdiHatasi(f"{goreli}: dosya degil")
    metin = utf8_oku(yol, goreli)
    if metin.startswith(_BOM):
        metin = metin[1:]  # BOM yazimda atilir; --check farki raporlar
    satirlar: list[Satir] = []
    # str.splitlines kullanilmaz: U+2028, U+0085 gibi karakterleri de satir sonu sayar.
    for no, ham in enumerate(metin.split("\n"), start=1):
        if ham.strip(" \t\r") == "":
            continue
        satirlar.append(_satir_coz(ham, f"{goreli}:{no}", dosya))
    return satirlar


def _yinelenenleri_denetle(okunan: dict[str, list[Satir]]) -> None:
    for grup in _KIMLIK_GRUPLARI:
        gorulen: dict[str, str] = {}
        for dosya in grup:
            for satir in okunan[dosya]:
                onceki = gorulen.get(satir.id)
                if onceki is not None:
                    raise GirdiHatasi(f"yinelenen id {satir.id}: {onceki} ve {satir.konum}")
                gorulen[satir.id] = satir.konum


# --- Sinir satirlari ----------------------------------------------------------------------


def _gecerli_beklenen(
    anchor: dict[str, object], capa: str, ayetler: list[object]
) -> dict[str, object]:
    return {
        "ref": {"anchor": anchor},
        "canonical": capa,
        "unit": capa,
        "unit_span": {"unit": capa},
        "ayahs": ayetler,
    }


def _uzunluk_denetle(capa: str, beklenen: int) -> str:
    if len(capa) != beklenen:
        raise GirdiHatasi(f"sinir capasi {len(capa)} karakter; {beklenen} bekleniyordu")
    return capa


def sinir_satirlari(sayilar: Sequence[int]) -> tuple[list[Satir], list[Satir]]:
    """Ayet sayilarindan ve uzunluk kurallarindan (gecerli, gecersiz) sinir satirlarini kurar."""
    gecerli: list[Satir] = []
    gecersiz: list[Satir] = []
    for sure, son in enumerate(sayilar, start=1):
        capa = f"q:{sure}:{son}"
        anchor: dict[str, object] = {"t": "q", "sure": sure, "ayet": son}
        ayetler: list[object] = [{"sure": sure, "ayet": son}]
        gecerli.append(Satir(f"an-s{sure:03d}-son", capa, _gecerli_beklenen(anchor, capa, ayetler)))
        gecersiz.append(Satir(f"an-s{sure:03d}-fazla", f"q:{sure}:{son + 1}", "AYET_ARALIGI"))

    # Uretilmis satirlar `note` tasimaz; kimlik siniri anlatir.
    slug_64 = "a" * 64
    capa = f"konu:{slug_64}"
    anchor = {"t": "konu", "slug": slug_64}
    gecerli.append(Satir("an-u-slug-64", capa, _gecerli_beklenen(anchor, capa, [])))
    gecersiz.append(Satir("an-u-slug-65", "konu:" + "a" * 65, "UZUNLUK"))

    yol_8 = ["a", "b", "c", "d", "e", "f", "g", "h"]
    capa = "rn:" + ":".join(yol_8) + ":p1"
    anchor = {"t": "rn", "yol": list(yol_8), "p": 1}
    gecerli.append(Satir("an-u-derinlik-8", capa, _gecerli_beklenen(anchor, capa, [])))
    gecersiz.append(Satir("an-u-derinlik-9", "rn:" + ":".join([*yol_8, "i"]) + ":p1", "UZUNLUK"))

    yol_256 = ["a" * 64, "b" * 64, "c" * 64, "d" * 55]
    capa = _uzunluk_denetle("rn:" + ":".join(yol_256) + ":p1", 256)
    anchor = {"t": "rn", "yol": list(yol_256), "p": 1}
    gecerli.append(Satir("an-u-toplam-256", capa, _gecerli_beklenen(anchor, capa, [])))
    yol_257 = ["a" * 64, "b" * 64, "c" * 64, "d" * 56]
    capa = _uzunluk_denetle("rn:" + ":".join(yol_257) + ":p1", 257)
    gecersiz.append(Satir("an-u-toplam-257", capa, "UZUNLUK"))

    en_buyuk = 2_147_483_647
    capa = f"h:deneme:{en_buyuk}"
    anchor = {"t": "h", "koleksiyon": "deneme", "no": en_buyuk}
    gecerli.append(Satir(f"an-u-sayi-{en_buyuk}", capa, _gecerli_beklenen(anchor, capa, [])))
    gecersiz.append(Satir(f"an-u-sayi-{en_buyuk + 1}", f"h:deneme:{en_buyuk + 1}", "UZUNLUK"))
    return gecerli, gecersiz


# --- Yazim --------------------------------------------------------------------------------


def _kacmali(kod: int, karakter: str) -> bool:
    if kod == 0x20:
        return False
    if any(bas <= kod <= son for bas, son in _ARAPCA_BLOKLARI):
        return True
    return unicodedata.category(karakter) in _KACAN_KATEGORILER


def dizgi_yaz(metin: str) -> str:
    """JSON dizgisi; sartname 1'deki kacis kurali (kucuk harf onaltilik)."""
    parcalar = ['"']
    for karakter in metin:
        kod = ord(karakter)
        kisa = _KISA_KACISLAR.get(karakter)
        if kisa is not None:
            parcalar.append(kisa)
        elif kod > 0xFFFF:
            fazla = kod - 0x10000
            parcalar.append(f"\\u{0xD800 + (fazla >> 10):04x}\\u{0xDC00 + (fazla & 0x3FF):04x}")
        elif _kacmali(kod, karakter):
            parcalar.append(f"\\u{kod:04x}")
        else:
            parcalar.append(karakter)
    parcalar.append('"')
    return "".join(parcalar)


def deger_yaz(deger: object) -> str:
    """Boslugsuz JSON; nesne anahtarlari verilen sirada yazilir."""
    if deger is None:
        return "null"
    if deger is True:
        return "true"
    if deger is False:
        return "false"
    if isinstance(deger, int):
        return str(deger)
    if isinstance(deger, str):
        return dizgi_yaz(deger)
    if isinstance(deger, list):
        return "[" + ",".join(deger_yaz(oge) for oge in deger) + "]"
    if isinstance(deger, dict):
        return "{" + ",".join(f"{dizgi_yaz(str(a))}:{deger_yaz(d)}" for a, d in deger.items()) + "}"
    raise GirdiHatasi("yazilamayan JSON degeri")


def satir_yaz(satir: Satir) -> str:
    """Bir satir: `id`, `input`, `expected`, istege bagli `note`."""
    parcalar = [
        f'"id":{dizgi_yaz(satir.id)}',
        f'"input":{deger_yaz(satir.input)}',
        f'"expected":{deger_yaz(satir.expected)}',
    ]
    if satir.note is not None:
        parcalar.append(f'"note":{dizgi_yaz(satir.note)}')
    return "{" + ",".join(parcalar) + "}"


def dosya_metni(satirlar: Sequence[Satir]) -> str:
    """Satirlar LF ile; sonda satir sonu, BOM yok."""
    return "".join(satir_yaz(satir) + "\n" for satir in satirlar)


# --- Komutlar -----------------------------------------------------------------------------


def hazirla(kok: Path) -> dict[str, list[Satir]]:
    """Yedi dosyayi okur, denetler, sinir satirlarini yeniler; dosya -> siralanmis satirlar."""
    belge = json_oku(kok)
    okunan = {dosya: _dosya_oku(kok, dosya) for dosya in DOSYALAR}
    # Eski sinir satirlari normalize edilmeden atilir; her calistirmada yeniden kurulur.
    for dosya in (VALID, INVALID):
        okunan[dosya] = [s for s in okunan[dosya] if not s.id.startswith(URETILEN_ONEKLER)]
    _yinelenenleri_denetle(okunan)
    sonuc = {
        dosya: [_normalize(dosya, satir) for satir in satirlar]
        for dosya, satirlar in okunan.items()
    }
    gecerli, gecersiz = sinir_satirlari(belge.sayilar)
    sonuc[VALID] += gecerli
    sonuc[INVALID] += gecersiz
    _yinelenenleri_denetle(sonuc)
    return {dosya: sorted(satirlar, key=lambda s: s.id) for dosya, satirlar in sonuc.items()}


def uret(kok: Path) -> list[str]:
    """Yedi dosyayi yazar; degisen dosyalarin goreli yollarini dondurur."""
    yazilan: list[str] = []
    for dosya, satirlar in hazirla(kok).items():
        goreli = f"{VEKTOR_KLASORU}/{dosya}"
        if yaz(kok, goreli, dosya_metni(satirlar)):
            yazilan.append(goreli)
    return yazilan


def _mevcut_kimlik(satir: str) -> str | None:
    try:
        veri = kati_json(satir)
    except GirdiHatasi:
        return None
    if isinstance(veri, dict):
        kimlik = veri.get("id")
        if isinstance(kimlik, str) and _KIMLIK.fullmatch(kimlik):
            return kimlik
    return None


def _ilk_fark(kok: Path, goreli: str, satirlar: Sequence[Satir]) -> str:
    yol = kok / goreli
    if not yol.is_file():
        return f"{goreli} (dosya yok)"
    mevcut = utf8_oku(yol, goreli)
    if mevcut.startswith(_BOM):
        return f"{goreli} (BOM var)"
    if "\r" in mevcut:
        return f"{goreli} (CR satir sonu var)"
    mevcut_satirlar = mevcut.split("\n")
    for sira, satir in enumerate(satirlar):
        if sira >= len(mevcut_satirlar) or mevcut_satirlar[sira] != satir_yaz(satir):
            adaylar = [satir.id]
            if sira < len(mevcut_satirlar):
                mevcut_kimlik = _mevcut_kimlik(mevcut_satirlar[sira])
                if mevcut_kimlik is not None:
                    adaylar.append(mevcut_kimlik)
            # Iki taraf da id sirasinda oldugundan ilk fark kucuk olan kimliktedir.
            return f"{goreli} (ilk farkli id: {min(adaylar)})"
    for fazla in mevcut_satirlar[len(satirlar) :]:
        kimlik = _mevcut_kimlik(fazla)
        if kimlik is not None:
            return f"{goreli} (ilk farkli id: {kimlik})"
    return f"{goreli} (bos satir ya da dosya sonu farki)"


def denetle(kok: Path) -> list[str]:
    """Yazmadan uretir ve diskle bayt bayt karsilastirir; farkli dosyalarin iletilerini dondurur."""
    farklar: list[str] = []
    for dosya, satirlar in hazirla(kok).items():
        goreli = f"{VEKTOR_KLASORU}/{dosya}"
        if not ayni_mi(kok, goreli, dosya_metni(satirlar)):
            farklar.append(_ilk_fark(kok, goreli, satirlar))
    return farklar
