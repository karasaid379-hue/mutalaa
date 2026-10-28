"""Ortak test ayarlari: gercek ortam degiskenleri testlere sizmaz."""

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
