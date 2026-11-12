"""Buckwalter eslemesi (A17.1): tablo kaynak sayfa parcasindan yeniden turetilir; yaprak modul.

Sayfa parcasi `tests/fixtures/qac/buckwalter-tablo.html` (kaynak notu: KAYNAK.txt) QAC sayfasinin
tablosudur ve ASCII'dir. Arapca beklentiler tablodan hesaplanir; hicbir Arapca harf hafizadan
yazilmaz. Gercek veri testleri `test_qac_gercek.py`'dedir.
"""

import hashlib
import re
from pathlib import Path

import pytest
from test_yaprak_kitapliklar import PAKET_KOKU, ihlaller

from mutalaa_pipeline.enrich.buckwalter import (
    TABLO,
    BuckwalterHatasi,
    bw_arapca,
    eslenemeyenler,
    tablo_ayristir,
)

FIKSTUR = Path(__file__).resolve().parent / "fixtures" / "qac"
PARCA = FIKSTUR / "buckwalter-tablo.html"
ARAPCA_BLOGU = range(0x0600, 0x0700)


def _parca() -> str:
    return PARCA.read_bytes().decode("utf-8")


def test_tablo_kaynak_parcasindan_yeniden_uretilir() -> None:
    assert tablo_ayristir(_parca()) == TABLO
    assert list(tablo_ayristir(_parca()).items()) == list(TABLO.items())  # sira da ayni


def test_fikstur_kaynak_notuyla_tutarli() -> None:
    not_ = (FIKSTUR / "KAYNAK.txt").read_bytes().decode("utf-8")
    ozet = hashlib.sha256(PARCA.read_bytes()).hexdigest()
    assert ozet in not_
    assert "https://corpus.quran.com/java/buckwalter.jsp" in not_
    assert "2026-11-12" in not_
    assert PARCA.read_bytes().isascii()
    assert b"\r" not in PARCA.read_bytes()


def test_tablo_ozellikleri() -> None:
    assert len(TABLO) == len(set(TABLO.values()))  # kod noktasi tekil
    for ascii_, arapca in TABLO.items():
        assert len(ascii_) == 1 and ascii_.isascii()
        assert len(arapca) == 1 and ord(arapca) in ARAPCA_BLOGU
    assert list(TABLO.values()) == sorted(TABLO.values())  # kod noktasina gore sirali


def test_modul_kaynagi_arapca_harf_icermez_ve_kacislidir() -> None:
    kaynak = (PAKET_KOKU / "enrich" / "buckwalter.py").read_bytes().decode("utf-8")
    assert kaynak.isascii()  # Arapca harf dogrudan yazilmamis, `\u` kacisli
    assert len(re.findall(r'"\\u0[67][0-9a-f]{2}"', kaynak)) == len(TABLO)


def test_modul_yaprak_kitaplik() -> None:
    kaynak = (PAKET_KOKU / "enrich" / "buckwalter.py").read_bytes().decode("utf-8")
    assert ihlaller(kaynak, ()) == []


def test_donusum_tablodan_hesaplanir() -> None:
    anahtarlar = "".join(TABLO)
    assert bw_arapca(anahtarlar) == "".join(TABLO.values())
    assert bw_arapca("") == ""
    assert eslenemeyenler(anahtarlar) == set()


def test_tabloda_olmayan_karakter_sessizce_atlanmaz() -> None:
    assert "2" not in TABLO and " " not in TABLO
    with pytest.raises(BuckwalterHatasi) as hata:
        bw_arapca("b2")
    assert str(hata.value) == "tabloda olmayan karakter: konum 1, U+0032"  # dizge yok
    assert eslenemeyenler("b2 b") == {"2", " "}


def test_bozuk_sayfa_reddedilir() -> None:
    parca = _parca()
    with pytest.raises(BuckwalterHatasi):
        tablo_ayristir("<html></html>")
    with pytest.raises(BuckwalterHatasi):
        tablo_ayristir(parca.replace("U+0621", "U+0622", 1))  # Decimal ve Hex tutmuyor
    ikiz = parca.replace('<td class="g4">\'</td>', '<td class="g4">&gt;</td>', 1)
    assert ikiz != parca
    with pytest.raises(BuckwalterHatasi):  # ayni ASCII karakter iki satirda
        tablo_ayristir(ikiz)
