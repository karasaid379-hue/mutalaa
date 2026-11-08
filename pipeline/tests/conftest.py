"""Ortak test ayarlari: gercek ortam degiskenleri testlere sizmaz."""

from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from ust_veri_yardimci import UstVeriZinciri

MUTALAA_DEGISKENLERI = (
    "MUTALAA_DB_URL",
    "MUTALAA_VERI_KOK",
    "MUTALAA_LOG_DUZEYI",
    "MUTALAA_CONFIG_DOSYASI",
)


@pytest.fixture(autouse=True)
def _mutalaa_ortamini_temizle(monkeypatch: pytest.MonkeyPatch) -> None:
    for ad in MUTALAA_DEGISKENLERI:
        monkeypatch.delenv(ad, raising=False)


@pytest.fixture(scope="session")
def tam_sablon(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """6.236 ayetlik SENTETIK zincir sablonu (ingest x2, normalize, anchor); bir kez kurulur."""
    from zincir_yardimci import tam_zincir_kur

    return tam_zincir_kur(tmp_path_factory.mktemp("tam-sablon"))


@pytest.fixture(scope="session")
def ust_veri_zinciri(
    tam_sablon: Path, tmp_path_factory: pytest.TempPathFactory
) -> Iterator["UstVeriZinciri"]:
    """Sentetik ust veri zinciri (A11): ingest, anchor ve qa kosulmus; bir kez kurulur.

    Tam sentetik Uthmani sablonunun kopyasina sentetik `quran-data.xml` eklenir. Testler yalniz
    okur ya da `sablon_kopyala` ile kendi kopyasini alir; her test `ortam_kur` ile ortami kurar.
    """
    from ust_veri_yardimci import json_kopyalarini_yaz, ust_veri_hazirla

    with pytest.MonkeyPatch.context() as mp:
        uz = ust_veri_hazirla(tam_sablon, tmp_path_factory.mktemp("ustveri") / "t", mp)
        json_kopyalarini_yaz(uz.z.kok, uz.xml)
        uz.hepsi()
        yield uz
