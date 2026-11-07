"""Katman kurallari: yaprak kitapliklar ve ortak yardimcilar (Proje yapisi §2 kural 6).

`normalize/` ve `anchor/` TypeScript ve C# karsiliklariyla ayni rolu tasiyan yaprak kitapliktir:
kendi paketi disinda hat modulu (`export`, `cli`, `runctx`, `staged`, `zincir`, `adimlar`, `qa` ...)
ice aktarmaz; bagimlilik tek yonludur. `config`, `db` ve `logs` hat adimlarina baglanmaz; yalniz
yaprak modul `export/ortak.py`'yi (hata turu, depo koku, kati JSON) ve `db` ayrica `config`'i ice
aktarir.
"""

import ast
from pathlib import Path

import pytest

PAKET_KOKU = Path(__file__).resolve().parent.parent / "src" / "mutalaa_pipeline"
KOK_PAKET = "mutalaa_pipeline"


def ice_aktarilanlar(kaynak: str) -> set[str]:
    """`mutalaa_pipeline.` altindaki mutlak ice aktarmalar; ust pakete goreli olan `..` olur."""
    bulunan: set[str] = set()
    for dugum in ast.walk(ast.parse(kaynak)):
        if isinstance(dugum, ast.Import):
            bulunan.update(oge.name for oge in dugum.names if oge.name.split(".")[0] == KOK_PAKET)
        elif isinstance(dugum, ast.ImportFrom):
            if dugum.level >= 2:
                bulunan.add("..")
            elif dugum.level == 0 and (dugum.module or "").split(".")[0] == KOK_PAKET:
                modul = dugum.module or ""
                if modul == KOK_PAKET:  # `from mutalaa_pipeline import x`: x paket ya da modul
                    bulunan.update(f"{modul}.{oge.name}" for oge in dugum.names)
                else:
                    bulunan.add(modul)
    return bulunan


def ihlaller(kaynak: str, izinli: tuple[str, ...]) -> list[str]:
    """`izinli` onekleriyle baslamayan ice aktarmalar."""
    return sorted(
        ad
        for ad in ice_aktarilanlar(kaynak)
        if not any(ad == oge or ad.startswith(oge + ".") for oge in izinli)
    )


@pytest.mark.parametrize("paket", ["normalize", "anchor"])
def test_yaprak_kitaplik_yalniz_kendi_paketini_ice_aktarir(paket: str) -> None:
    dosyalar = sorted((PAKET_KOKU / paket).glob("*.py"))
    assert dosyalar
    for yol in dosyalar:
        kaynak = yol.read_bytes().decode("utf-8")
        assert ihlaller(kaynak, (f"{KOK_PAKET}.{paket}",)) == [], yol.name


@pytest.mark.parametrize(
    ("modul", "izinli"),
    [
        ("logs", ()),
        ("config", (f"{KOK_PAKET}.export.ortak",)),
        ("db", (f"{KOK_PAKET}.export.ortak", f"{KOK_PAKET}.config")),
    ],
)
def test_ortak_yardimcilar_hat_adimlarina_baglanmaz(modul: str, izinli: tuple[str, ...]) -> None:
    kaynak = (PAKET_KOKU / f"{modul}.py").read_bytes().decode("utf-8")
    assert ihlaller(kaynak, izinli) == []


def test_ihlal_denetimi_yasak_ice_aktarmalari_yakalar() -> None:
    """Denetim gercekten calisiyor: yasak bicimlerin hepsi bulunur."""
    kotu = (
        "from mutalaa_pipeline.export.ortak import GirdiHatasi\n"
        "from mutalaa_pipeline import runctx\n"
        "import mutalaa_pipeline.staged\n"
        "from mutalaa_pipeline.zincir import calismalar\n"
        "from .. import cli\n"
        "from . import capa\n"
        "import json\n"
    )
    assert ihlaller(kotu, (f"{KOK_PAKET}.anchor",)) == [
        "..",
        "mutalaa_pipeline.export.ortak",
        "mutalaa_pipeline.runctx",
        "mutalaa_pipeline.staged",
        "mutalaa_pipeline.zincir",
    ]
    iyi = (
        "from mutalaa_pipeline.anchor.capa import x\n"
        "from mutalaa_pipeline.anchor import y\n"
        "from . import z\n"
        "import json\n"
    )
    assert ihlaller(iyi, (f"{KOK_PAKET}.anchor",)) == []
