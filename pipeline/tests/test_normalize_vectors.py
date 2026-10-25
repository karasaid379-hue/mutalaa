"""Normalizasyon vektorleri kosucusu (A05.5): `normalize/tr.jsonl` ve `normalize/ar.jsonl`.

Vektorler depo kokunden okunur (`pnpm-workspace.yaml` yukari aranir); dosya yoksa ya da
bossa acik hata verilir. Dosyalar `\\n` ile satirlara bolunur (`str.splitlines` U+2028 gibi
ayiricilarla da boler). Kaynak yalniz ASCII'dir; ASCII disi karakterler `\\N{...}` ve
`chr()` ile yazilir. `expected` degerleri elle yazilmistir ve degistirilmez.
"""

import json
from pathlib import Path
from typing import Any

import pytest

from mutalaa_pipeline.normalize import (
    NORMALIZER_VERSION,
    lower_turkish,
    normalize_ar,
    normalize_tr,
    search_keys,
    tr_stem,
)

KOK_ISARETI = "pnpm-workspace.yaml"


def _depo_koku() -> Path:
    yol = Path(__file__).resolve()
    for aday in yol.parents:
        if (aday / KOK_ISARETI).is_file():
            return aday
    raise RuntimeError(f"depo koku bulunamadi ({KOK_ISARETI} yok)")


VEKTOR_KOKU = _depo_koku() / "shared" / "test-vectors"


def _yukle(goreli: str, onek: str) -> list[dict[str, Any]]:
    yol = VEKTOR_KOKU / goreli
    if not yol.is_file():
        raise RuntimeError(f"vektor dosyasi yok: {goreli}")
    veri = yol.read_bytes()
    assert not veri.startswith(b"\xef\xbb\xbf"), f"{goreli}: BOM var"
    assert b"\r" not in veri, f"{goreli}: CR var"
    satirlar = veri.decode("utf-8").split("\n")
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
    assert all(k.startswith(f"{onek}-") for k in kimlikler)
    return sonuc


TR = _yukle("normalize/tr.jsonl", "tr")
AR = _yukle("normalize/ar.jsonl", "ar")


def test_vektor_dosyalari_bos_degil() -> None:
    assert len(TR) > 0
    assert len(AR) > 0


@pytest.mark.parametrize("vektor", TR, ids=[v["id"] for v in TR])
def test_turkce_vektoru(vektor: dict[str, Any]) -> None:
    girdi = vektor["input"]
    beklenen = vektor["expected"]
    assert isinstance(girdi, str)
    assert list(beklenen) == ["dar", "genis"]
    kopya = str(girdi)
    assert normalize_tr(girdi, "dar") == beklenen["dar"]
    assert normalize_tr(girdi, "genis") == beklenen["genis"]
    assert girdi == kopya  # girdi degismez
    anahtarlar = search_keys(girdi)
    assert anahtarlar.tr_narrow == beklenen["dar"]
    assert anahtarlar.tr_wide == beklenen["genis"]
    assert anahtarlar.tr_stem == tr_stem(girdi)


@pytest.mark.parametrize("vektor", AR, ids=[v["id"] for v in AR])
def test_arapca_vektoru(vektor: dict[str, Any]) -> None:
    girdi = vektor["input"]
    beklenen = vektor["expected"]
    assert isinstance(girdi, str)
    assert isinstance(beklenen, str)
    assert normalize_ar(girdi) == beklenen
    assert search_keys(girdi).ar_norm == beklenen


def test_vektor_notlari_dizgi() -> None:
    for vektor in (*TR, *AR):
        assert isinstance(vektor.get("note", ""), str)


def test_surum_sabiti() -> None:
    assert NORMALIZER_VERSION == "1.0"


def test_lower_turkish_vektor_girdilerinde_dize_lower_ile_ayrisir() -> None:
    """str.lower() I ve noktali I icin yanlis sonuc verir; acik eslem dogrudur."""
    assert lower_turkish("I") == "\N{LATIN SMALL LETTER DOTLESS I}"
    assert "\N{LATIN CAPITAL LETTER I WITH DOT ABOVE}".lower() != "i"
    assert lower_turkish("\N{LATIN CAPITAL LETTER I WITH DOT ABOVE}") == "i"
