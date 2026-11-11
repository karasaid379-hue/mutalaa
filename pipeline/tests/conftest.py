"""Ortak test ayarlari: gercek ortam degiskenleri testlere sizmaz."""

from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from meal_yardimci import MealKoku
    from sure_adlari_yardimci import SureAdlariZinciri
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

    with pytest.MonkeyPatch.context() as mp:  # yama yalniz kurulum sirasinda gecerlidir
        uz = ust_veri_hazirla(tam_sablon, tmp_path_factory.mktemp("ustveri") / "t", mp)
        json_kopyalarini_yaz(uz.z.kok, uz.xml)
        uz.hepsi()
    yield uz


@pytest.fixture(scope="session")
def sure_adlari_zinciri(ust_veri_zinciri: "UstVeriZinciri") -> Iterator["SureAdlariZinciri"]:
    """Sentetik sure adi zinciri (A11.3): ingest, anchor ve qa kosulmus; bir kez kurulur.

    `ust_veri_zinciri` kokune sentetik Vikipedi/quran-meta dosyalari, kilit ve riskli ad listesi
    eklenir. Her test `zincir.ortam(monkeypatch)` ile kilit ve liste yollarini kurar.
    """
    from sure_adlari_yardimci import SureAdlariZinciri
    from zincir_yardimci import ortam_kur

    sz = SureAdlariZinciri(ust_veri_zinciri)
    with pytest.MonkeyPatch.context() as mp:  # yama yalniz kurulum sirasinda gecerlidir
        ortam_kur(ust_veri_zinciri.z, mp)
        sz.ortam(mp)
        sz.hepsi()
    yield sz


@pytest.fixture(scope="session")
def meal_sablon(tmp_path_factory: pytest.TempPathFactory) -> Iterator["MealKoku"]:
    """Tam SENTETIK meal zinciri (A16; ingest x3, normalize x2, anchor x2, qa x2); bir kez kurulur.

    Testler yalniz okur ya da `meal_yardimci.kopya_al` ile kendi kopyasini alir.
    """
    from meal_yardimci import tam_zincir_kur

    with pytest.MonkeyPatch.context() as mp:  # yama yalniz kurulum sirasinda gecerlidir
        kok = tam_zincir_kur(tmp_path_factory.mktemp("meal-sablon"), mp)
    yield kok
