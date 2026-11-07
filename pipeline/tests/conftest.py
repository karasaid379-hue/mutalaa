"""Ortak test ayarlari: gercek ortam degiskenleri testlere sizmaz."""

from pathlib import Path

import pytest

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
