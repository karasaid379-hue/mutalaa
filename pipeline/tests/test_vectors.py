"""Ortak test vektorleri kosucusu (A04.5): `shared/test-vectors` altindaki yedi dosya.

Vektorler depo kokunden okunur (`pnpm-workspace.yaml` yukari aranir); dosya yoksa ya da
bossa acik hata verilir. Dosyalar `\\n` ile satirlara bolunur (`str.splitlines` U+2028 gibi
ayiricilarla da boler). `expected` degerleri tur-guvenli karsilastirilir (`True != 1`).
Kaynak yalniz ASCII'dir; ASCII disi karakterler `\\N{...}` ile yazilir.
"""

import hashlib
import itertools
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

from mutalaa_pipeline.anchor import (
    AnchorError,
    AnchorRef,
    H,
    Ht,
    K,
    Konu,
    Meal,
    Q,
    Qa,
    Rn,
    Tf,
    Tfb,
    contains,
    content_hash,
    covered_ayahs,
    format,
    kanonik_metin,
    parse,
    snap_span,
    sort_key,
    to_route,
    to_unit_span,
    try_parse,
    unit_of,
)

KOK_ISARETI = "pnpm-workspace.yaml"


def _depo_koku() -> Path:
    yol = Path(__file__).resolve()
    for aday in yol.parents:
        if (aday / KOK_ISARETI).is_file():
            return aday
    raise RuntimeError(f"depo koku bulunamadi ({KOK_ISARETI} yok)")


VEKTOR_KOKU = _depo_koku() / "shared" / "test-vectors"


def _yukle(goreli: str) -> list[dict[str, Any]]:
    yol = VEKTOR_KOKU / goreli
    if not yol.is_file():
        raise RuntimeError(f"vektor dosyasi yok: {goreli}")
    metin = yol.read_bytes().decode("utf-8")
    satirlar = metin.split("\n")
    if satirlar and satirlar[-1] == "":
        satirlar.pop()
    if not satirlar:
        raise RuntimeError(f"vektor dosyasi bos: {goreli}")
    sonuc: list[dict[str, Any]] = []
    for sira, satir in enumerate(satirlar, start=1):
        if satir == "":
            raise RuntimeError(f"{goreli}:{sira}: bos satir")
        sonuc.append(json.loads(satir))
    kimlikler = [v["id"] for v in sonuc]
    if len(set(kimlikler)) != len(kimlikler):
        raise RuntimeError(f"{goreli}: yinelenen id")
    return sonuc


VALID = _yukle("anchors/valid.jsonl")
INVALID = _yukle("anchors/invalid.jsonl")
COMPARE = _yukle("anchors/compare.jsonl")
CONTAINS = _yukle("anchors/contains.jsonl")
ROUTE = _yukle("anchors/route.jsonl")
OFFSETS = _yukle("offsets/offsets.jsonl")
HASH = _yukle("content-hash/hash.jsonl")


def kimlik(vektorler: list[dict[str, Any]]) -> list[str]:
    return [v["id"] for v in vektorler]


def tam_esit(a: object, b: object) -> bool:
    """Tur-guvenli derin esitlik: `True` ile `1` esit sayilmaz."""
    if type(a) is not type(b):
        return False
    if isinstance(a, Mapping) and isinstance(b, Mapping):
        return list(a.keys()) == list(b.keys()) and all(tam_esit(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(tam_esit(x, y) for x, y in zip(a, b, strict=True))
    return a == b


def ref_to_json(r: AnchorRef) -> dict[str, Any]:
    """AnchorRef -> vektor dosyasindaki `ref` nesnesi."""
    a = r.anchor
    govde: dict[str, Any]
    match a:
        case Q():
            govde = {"t": "q", "sure": a.sure, "ayet": a.ayet}
            if a.ilk is not None:
                govde["ilk"] = a.ilk
            if a.son is not None:
                govde["son"] = a.son
        case Qa():
            govde = {"t": "qa", "sure": a.sure, "ilk": a.ilk, "son": a.son}
        case Konu():
            govde = {"t": "konu", "slug": a.slug}
        case Meal():
            govde = {"t": "meal", "meal": a.meal, "sure": a.sure, "ayet": a.ayet}
        case Tf():
            govde = {
                "t": "tf",
                "eser": a.eser,
                "sure": a.sure,
                "ilk": a.ilk,
                "son": a.son,
                "p": a.p,
            }
        case Tfb():
            govde = {"t": "tfb", "eser": a.eser, "bolum": a.bolum, "p": a.p}
        case Rn():
            govde = {"t": "rn", "yol": list(a.yol), "p": a.p}
            if a.s is not None:
                govde["s"] = a.s
        case H():
            govde = {"t": "h", "koleksiyon": a.koleksiyon, "no": a.no}
        case Ht():
            govde = {"t": "ht", "ceviri": a.ceviri, "koleksiyon": a.koleksiyon, "no": a.no}
        case K():
            govde = {"t": "k", "yol": list(a.yol), "p": a.p}
    sonuc: dict[str, Any] = {"anchor": govde}
    if r.span is not None:
        sonuc["span"] = {"start": r.span.start, "end": r.span.end}
    return sonuc


def isaret(a: tuple[Any, ...], b: tuple[Any, ...]) -> int:
    return (a > b) - (a < b)


# --- gecerli ---------------------------------------------------------------


@pytest.mark.parametrize("v", VALID, ids=kimlik(VALID))
def test_valid_ref_ve_canonical(v: dict[str, Any]) -> None:
    ref = parse(v["input"])
    beklenen = v["expected"]
    assert tam_esit(ref_to_json(ref), beklenen["ref"])
    assert format(ref) == beklenen["canonical"]
    assert str(ref) == beklenen["canonical"]


@pytest.mark.parametrize("v", VALID, ids=kimlik(VALID))
def test_valid_birim_islevleri(v: dict[str, Any]) -> None:
    ref = parse(v["input"])
    beklenen = v["expected"]
    assert format(unit_of(ref)) == beklenen["unit"]
    if beklenen["unit_span"] is None:
        with pytest.raises(ValueError):
            to_unit_span(ref)
    else:
        us = to_unit_span(ref)
        sonuc: dict[str, Any] = {"unit": us.unit}
        if us.span is not None:
            sonuc["span"] = [us.span[0], us.span[1]]
        assert tam_esit(sonuc, beklenen["unit_span"])
    ayetler = [{"sure": a.sure, "ayet": a.ayet} for a in covered_ayahs(ref)]
    assert tam_esit(ayetler, beklenen["ayahs"])


@pytest.mark.parametrize("v", VALID, ids=kimlik(VALID))
def test_valid_ozellikler(v: dict[str, Any]) -> None:
    ref = parse(v["input"])
    assert parse(format(ref)) == ref
    assert try_parse(v["input"]) == ref
    assert hash(ref) == hash(parse(v["input"]))
    assert contains(ref, ref)
    anahtar = sort_key(ref)
    assert isaret(anahtar, sort_key(ref)) == 0


def test_valid_anahtar_tekil_ve_siralanabilir() -> None:
    """Karisik turlerde TypeError yok; sort_key esitligi yalniz ayni capada."""
    refler = [parse(v["input"]) for v in VALID]
    sirali = sorted(refler, key=sort_key)
    assert len(sirali) == len(refler)
    anahtarlar = [sort_key(r) for r in refler]
    assert len(set(anahtarlar)) == len(set(refler))
    for onceki, sonraki in itertools.pairwise(sirali):
        assert sort_key(onceki) <= sort_key(sonraki)


# --- gecersiz --------------------------------------------------------------


@pytest.mark.parametrize("v", INVALID, ids=kimlik(INVALID))
def test_invalid_kod(v: dict[str, Any]) -> None:
    with pytest.raises(AnchorError) as hata:
        parse(v["input"])
    assert hata.value.code == v["expected"]
    assert try_parse(v["input"]) is None


# --- karsilastirma ---------------------------------------------------------


@pytest.mark.parametrize("v", COMPARE, ids=kimlik(COMPARE))
def test_compare(v: dict[str, Any]) -> None:
    a, b = (sort_key(parse(s)) for s in v["input"])
    beklenen = v["expected"]
    assert type(beklenen) is int
    assert isaret(a, b) == beklenen
    assert isaret(b, a) == -beklenen
    assert (a == b) is (beklenen == 0)


# --- kapsama ---------------------------------------------------------------


@pytest.mark.parametrize("v", CONTAINS, ids=kimlik(CONTAINS))
def test_contains(v: dict[str, Any]) -> None:
    dis, ic = (parse(s) for s in v["input"])
    beklenen = v["expected"]
    assert type(beklenen) is bool
    assert contains(dis, ic) is beklenen


# --- rota ------------------------------------------------------------------


@pytest.mark.parametrize("v", ROUTE, ids=kimlik(ROUTE))
def test_route(v: dict[str, Any]) -> None:
    girdi = v["input"]
    ref = parse(girdi["capa"])
    sema = girdi.get("sema")
    beklenen = v["expected"]
    assert to_route(ref, "native", sema) == beklenen["native"]
    if beklenen["web"] is None:
        with pytest.raises(ValueError):
            to_route(ref, "web", sema)
    else:
        assert to_route(ref, "web", sema) == beklenen["web"]


# --- ofsetler --------------------------------------------------------------


@pytest.mark.parametrize("v", OFFSETS, ids=kimlik(OFFSETS))
def test_offsets(v: dict[str, Any]) -> None:
    metin = v["input"]
    beklenen = v["expected"]
    assert tam_esit(len(metin), beklenen["codepoints"])
    for satir in beklenen.get("snap", []):
        giris, cikis = satir["in"], satir["out"]
        assert snap_span(metin, giris[0], giris[1]) == (cikis[0], cikis[1])


# --- content_hash ----------------------------------------------------------


@pytest.mark.parametrize("v", HASH, ids=kimlik(HASH))
def test_content_hash(v: dict[str, Any]) -> None:
    metin, islem = v["input"]["text"], v["input"]["op"]
    beklenen = v["expected"]
    assert len(beklenen["sha256"]) == 64
    if islem == "ham":
        assert content_hash(metin) == beklenen["sha256"]
        assert hashlib.sha256(metin.encode("utf-8")).hexdigest() == beklenen["sha256"]
    else:
        assert islem == "kanonik"
        assert kanonik_metin(metin) == beklenen["text"]
        assert content_hash(beklenen["text"]) == beklenen["sha256"]
        assert content_hash(kanonik_metin(metin)) == beklenen["sha256"]
        # Kanonik metin zaten kanoniktir (idempotent).
        assert kanonik_metin(beklenen["text"]) == beklenen["text"]


# --- vektor disi birim testleri --------------------------------------------

NBSP = "\N{NO-BREAK SPACE}"
ARAP_INDIK_IKI = "\N{ARABIC-INDIC DIGIT TWO}"
VEKIL = chr(0xD800)  # tek basina vekil


@pytest.mark.parametrize(
    "girdi",
    ["q:1:1\n", "\nq:1:1", "q:1:1 ", f"q:{ARAP_INDIK_IKI}:1", "Q:2:255", "q:2:255\r", ""],
)
def test_bicim_siniri(girdi: str) -> None:
    with pytest.raises(AnchorError) as hata:
        parse(girdi)
    assert hata.value.code == "BICIM"


def test_uzunluk_karakter_kumesinden_sonra() -> None:
    """ASCII disi karakter 256'yi asan dizgide de once BICIM verir."""
    with pytest.raises(AnchorError) as hata:
        parse("q:2:" + "a" * 300 + ARAP_INDIK_IKI)
    assert hata.value.code == "BICIM"
    with pytest.raises(AnchorError) as hata:
        parse("konu:" + "a" * 300)
    assert hata.value.code == "UZUNLUK"


def test_ters_aralik_sure_oncelikli() -> None:
    with pytest.raises(AnchorError) as hata:
        parse("q:115:1:7-3")
    assert hata.value.code == "SURE_ARALIGI"
    with pytest.raises(AnchorError) as hata:
        parse("q:2:287:7-3")
    assert hata.value.code == "AYET_ARALIGI"


@pytest.mark.parametrize(
    ("girdi", "kod"),
    [
        ("tf:elmalili:" + "a" * 65 + ":p1@5-3", "UZUNLUK"),
        ("tf:elmalili:" + "a" * 64 + ":p1@5-3", "TERS_ARALIK"),
        ("tf:elmalili:" + "a" * 65 + ":p1", "UZUNLUK"),
        ("meal:" + "a" * 65 + ":2:255@5-3", "UZUNLUK"),
        ("h:" + "a" * 65 + ":1@5-3", "UZUNLUK"),
        ("ht:naim:" + "a" * 65 + ":1@5-3", "UZUNLUK"),
        ("k:a:" + "a" * 65 + ":p1@5-3", "UZUNLUK"),
        ("rn:" + "a:" * 8 + "b:p1@5-3", "UZUNLUK"),
        ("q:115:1:7-3", "SURE_ARALIGI"),
    ],
)
def test_slug_siniri_anlam_denetiminden_once(girdi: str, kod: str) -> None:
    with pytest.raises(AnchorError) as hata:
        parse(girdi)
    assert hata.value.code == kod


def test_sort_key_tur_guvenli() -> None:
    karisik = ["konu:a", "k:a:p1", "q:1:1", "rn:a:p1", "rn:a:p1:s1", "rn:a:p1@0-5", "h:a:1"]
    sirali = [format(r) for r in sorted((parse(s) for s in karisik), key=sort_key)]
    assert sirali == ["q:1:1", "rn:a:p1", "rn:a:p1@0-5", "rn:a:p1:s1", "h:a:1", "k:a:p1", "konu:a"]


def test_to_route_hatalari() -> None:
    ref = parse("q:2:255")
    with pytest.raises(ValueError):
        to_route(ref, "native", "http")
    with pytest.raises(ValueError):
        to_route(ref, "ios")  # type: ignore[arg-type]


def test_kanonik_metin_u00a0_korunur() -> None:
    assert kanonik_metin(f"{NBSP}a{NBSP}") == f"{NBSP}a{NBSP}"
    assert kanonik_metin(" \t\n a \t b \n\t ") == "a b"


def test_content_hash_vekil_hata_verir() -> None:
    with pytest.raises(UnicodeEncodeError):
        content_hash(VEKIL)


@pytest.mark.parametrize("aralik", [(-1, 0), (2, 1), (0, 4), (4, 4)])
def test_snap_span_gecersiz_aralik(aralik: tuple[int, int]) -> None:
    with pytest.raises(ValueError):
        snap_span("abc", aralik[0], aralik[1])


@pytest.mark.parametrize(
    "kodlar",
    [[0x61, 0xD800, 0x62], [0xDC00], [0x20, 0xD800, 0x20]],
    ids=["ortada", "alt-vekil", "bosluk-arasi"],
)
def test_kanonik_metin_vekilde_hata_verir(kodlar: list[int]) -> None:
    metin = "".join(chr(kod) for kod in kodlar)
    with pytest.raises(UnicodeEncodeError):
        kanonik_metin(metin)
