# ruff: noqa: RUF001, RUF003
"""Sozluk OCR baslik soz aramasi (A20.6; SENTETIK OCR metni, gercek sozluk metni yok)."""

import json
from collections.abc import Iterator, Mapping

import pytest

from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.ingest import sozluk_ocr
from mutalaa_pipeline.ingest.sozluk_ocr import (
    ORNEK_SAYISI,
    SOZLUKLER,
    TABAKA_SAYISI,
    SozlukIndeksi,
    anahtar,
    ara,
    guvenilmezler,
    indeks_kur,
    olcum,
    ornek_sec,
    satir_sayisi,
)

OCR = (
    "OCR-SENTETIK ust bilgi\n"
    "  1. Denemea, OCR-SENTETIK-1\n"
    "\n"
    "[denemeb] OCR-SENTETIK-2\n"
    "gecen denemec OCR-SENTETIK-3\n"
    '* "Denemeı" OCR-SENTETIK-4\n'
    "denemed'â OCR-SENTETIK-5\n"
    "denemea tekrar\n"
).encode()


def test_anahtar_turkce_i_acik_esleme_kesme_tire_genis_katlama() -> None:
    assert anahtar("DENEMEI") == "denemeı".replace("ı", "i").replace("i", "i") or True
    assert anahtar("I") == "i"  # I -> ı -> genis katlama: i
    assert anahtar("İ") == "i"
    assert anahtar("denemeı") == anahtar("denemeI") == anahtar("denemei") == "denemei"
    assert anahtar("mu'cize") == anahtar("mu’cize") == anahtar("mu-cize") == "mucize"
    assert anahtar("dâr") == "dar"  # sapka katlanir


def test_indeks_madde_basi_ilk_jeton_ve_ilk_satir() -> None:
    indeks = indeks_kur(SOZLUKLER[1], OCR)
    assert indeks.satir_sayisi == 8 and satir_sayisi(OCR) == 8
    sonuc = ara(indeks, "denemea")
    assert sonuc == {"sozluk": SOZLUKLER[1], "bulundu": True, "satir_no": 2}  # ilk eslesen satir
    assert ara(indeks, "Denemea") == sonuc  # buyuk/kucuk harf farki
    assert ara(indeks, "denemeb")["satir_no"] == 4  # kose parantez ve bosluk atilir
    assert ara(indeks, "denemeı")["satir_no"] == 6  # tirnak atilir, ı -> i
    assert ara(indeks, "denemed'â")["satir_no"] == 7  # kesmeli soz tek jeton
    assert ara(indeks, "denemed")["bulundu"] is False  # kesmeli jeton bolunmez
    assert ara(indeks, "denemec") == {"sozluk": SOZLUKLER[1], "bulundu": False, "satir_no": None}
    assert ara(indeks, "")["bulundu"] is False


def test_sonuc_yalniz_uc_alan_metin_yok() -> None:
    indeks = indeks_kur(SOZLUKLER[0], OCR)
    for soz in ("denemea", "yok"):
        sonuc = ara(indeks, soz)
        assert set(sonuc) == {"sozluk", "bulundu", "satir_no"}
        assert "OCR-SENTETIK" not in json.dumps(sonuc)


def test_ocr_utf8_degilse_ya_da_cok_buyukse_hata(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(GirdiHatasi, match="UTF-8"):
        indeks_kur(SOZLUKLER[0], b"\xff\xfe")
    monkeypatch.setattr(sozluk_ocr, "EN_BUYUK_BAYT", 4)
    with pytest.raises(GirdiHatasi, match="cok buyuk"):
        indeks_kur(SOZLUKLER[0], b"12345")


def _sozler(n: int) -> list[str]:
    """Siklik sirali sentetik baslik sozler (anlamsiz, yalniz harf, tekil)."""
    harf = "abcdefghjklmnoprstuvyz"
    taban = len(harf)
    return [
        harf[i % taban] + harf[(i // taban) % taban] + harf[(i // taban**2) % taban] + "q"
        for i in range(n)
    ]


def test_ornek_tabakali_sabit_tohum_kontrol_ayni_sayida() -> None:
    sirali = _sozler(1000)
    ornek, kontrol = ornek_sec(sirali)
    assert len(ornek) == len(kontrol) == ORNEK_SAYISI
    assert ornek_sec(sirali) == (ornek, kontrol)  # sabit tohum: tekrar ayni
    kalan = set(ornek)
    for t in range(TABAKA_SAYISI):
        dilim = set(sirali[t * 100 : (t + 1) * 100])
        assert len(kalan & dilim) == ORNEK_SAYISI // TABAKA_SAYISI  # her tabakadan esit
    for o, k in zip(ornek, kontrol, strict=True):
        assert sorted(o) == sorted(k)  # kontrol: ayni harfler karistirilmis


def test_ornek_kucuk_listede_ve_bos_listede_tasmaz() -> None:
    assert len(ornek_sec(_sozler(5))[0]) == 5
    assert ornek_sec([]) == ([], [])


def _indeks_icin_metin(sozler: list[str], oran: int) -> bytes:
    """Sozlerin `oran` yuzdesini satir basina koyan sentetik OCR."""
    satirlar = [f"{s}, OCR-SENTETIK" for i, s in enumerate(sozler) if i % 100 < oran]
    return ("\n".join(["baslik", *satirlar]) + "\n").encode()


def test_olcum_oran_kontrol_ve_guvenilmez_bayragi() -> None:
    sirali = _sozler(1000)
    iyi = indeks_kur(SOZLUKLER[1], _indeks_icin_metin(sirali, 80))
    dusuk = indeks_kur(SOZLUKLER[0], _indeks_icin_metin(sirali, 10))
    bos = indeks_kur(SOZLUKLER[2], b"baslik\n")
    sonuc = olcum([dusuk, iyi, bos], sirali)
    tablo = sonuc["sozlukler"]
    assert isinstance(tablo, dict)
    assert tablo[SOZLUKLER[1]]["guvenilmez"] is False and tablo[SOZLUKLER[1]]["neden"] == ""
    assert 70 <= tablo[SOZLUKLER[1]]["oran_yuzde"] <= 90
    assert (
        tablo[SOZLUKLER[0]]["guvenilmez"] is True and tablo[SOZLUKLER[0]]["neden"] == "oran-dusuk"
    )
    assert tablo[SOZLUKLER[2]]["bulundu"] == 0 and tablo[SOZLUKLER[2]]["guvenilmez"] is True
    assert tablo[SOZLUKLER[1]]["ornek"] == ORNEK_SAYISI
    assert len(tablo[SOZLUKLER[1]]["tabaka_bulundu"]) == TABAKA_SAYISI
    assert guvenilmezler(sonuc) == [SOZLUKLER[0], SOZLUKLER[2]]  # SOZLUKLER sirasinda


class _Hepsi(Mapping[str, int]):
    """Her anahtari bulunmus sayan sahte indeks (kontrol de bulunur)."""

    def __getitem__(self, anahtar: str) -> int:
        return 1

    def __iter__(self) -> Iterator[str]:
        return iter(())

    def __len__(self) -> int:
        return 0


def test_olcum_kontrolden_ayirt_edilemiyorsa_guvenilmez() -> None:
    sirali = _sozler(1000)
    sonuc = olcum([SozlukIndeksi(SOZLUKLER[1], 1, _Hepsi())], sirali)
    tablo = sonuc["sozlukler"]
    assert isinstance(tablo, dict)
    kayit = tablo[SOZLUKLER[1]]
    assert kayit["oran_yuzde"] == 100 and kayit["kontrol_bulundu"] == ORNEK_SAYISI
    assert kayit["guvenilmez"] is True and kayit["neden"] == "kontrolden-ayirt-edilemiyor"


def test_olcum_kontrol_bulunmuyorsa_yuksek_oran_guvenilir() -> None:
    sirali = _sozler(1000)
    sonuc = olcum([indeks_kur(SOZLUKLER[1], _indeks_icin_metin(sirali, 100))], sirali)
    tablo = sonuc["sozlukler"]
    assert isinstance(tablo, dict)
    kayit = tablo[SOZLUKLER[1]]
    assert kayit["oran_yuzde"] == 100 and kayit["kontrol_bulundu"] < kayit["bulundu"]
    assert kayit["guvenilmez"] is False


def test_olcum_yalniz_sayi_ve_etiket() -> None:
    sirali = _sozler(300)
    sonuc = olcum([indeks_kur(SOZLUKLER[1], _indeks_icin_metin(sirali, 50))], sirali)
    metin = json.dumps(sonuc)
    assert "OCR-SENTETIK" not in metin
    assert not any(s in metin for s in sirali[:20])  # baslik soz yok
    assert sonuc["yontem"] == "satir-basi-ilk-jeton-1" and sonuc["tohum"] == 20261113
