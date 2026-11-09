"""`logs`: JSON satirli gunluk ve sizinti korumasi (SENTETIK)."""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from hat_yardimci import PAROLA, SAHTE_DSN

from mutalaa_pipeline.logs import Gunluk, guvenli_deger, ileti_temizle, maskele

SABIT = datetime(2026, 10, 28, 12, 30, 45, 123456, tzinfo=UTC)


def gunluk_kur(tmp_path: Path, **kw: object) -> Gunluk:
    return Gunluk(tmp_path / "logs", "RUN-1", "ingest", saat=lambda: SABIT, **kw)  # type: ignore[arg-type]


def test_satir_bicimi(tmp_path: Path) -> None:
    g = gunluk_kur(tmp_path)
    g.yaz("INFO", "birim_yazildi", source_id="test-kaynak", sayilar={"birim": 6236, "oran": 0.5})
    g.bilgi("bitti", n=1)
    satirlar = g.yol.read_bytes().decode("utf-8").split("\n")
    assert satirlar[-1] == ""
    ilk = json.loads(satirlar[0])
    assert ilk == {
        "ts": "2026-10-28T12:30:45.123Z",
        "level": "INFO",
        "run_id": "RUN-1",
        "source_id": "test-kaynak",
        "adim": "ingest",
        "olay": "birim_yazildi",
        "sayilar": {"birim": 6236, "oran": 0.5},
    }
    assert g.yol.name == "RUN-1.jsonl"
    assert b"\r" not in g.yol.read_bytes()


def test_duzey_esigi(tmp_path: Path) -> None:
    g = gunluk_kur(tmp_path, duzey="WARNING")
    g.bilgi("gorunmez")
    g.uyari("gorunur")
    satirlar = g.yol.read_text(encoding="utf-8").splitlines()
    assert len(satirlar) == 1
    assert json.loads(satirlar[0])["olay"] == "gorunur"
    with pytest.raises(ValueError):
        g.yaz("TRACE", "x")


def test_dsn_ve_parola_maskelenir(tmp_path: Path) -> None:
    g = gunluk_kur(tmp_path, gizliler=[SAHTE_DSN, PAROLA])
    g.yaz("INFO", f"adres {SAHTE_DSN}", source_id=SAHTE_DSN, sayilar={"adres": SAHTE_DSN})
    g.yaz("INFO", f"password={PAROLA} host=h")
    g.yaz("INFO", "postgresql://k:baska-parola@h/db kullanildi")
    ham = g.yol.read_text(encoding="utf-8")
    assert PAROLA not in ham
    assert "baska-parola" not in ham
    assert "@127.0.0.1" not in ham


def test_ascii_disi_metin_icerik_olarak_yazilmaz(tmp_path: Path) -> None:
    g = gunluk_kur(tmp_path)
    g.yaz("INFO", "satir", sayilar={"metin": "Deneme çş", "dizi": ["a", "bç"]})  # type: ignore[dict-item]
    ham = g.yol.read_text(encoding="utf-8")
    assert "ç" not in ham
    assert "[metin:" in ham


def test_cok_uzun_metin_ozete_cevrilir() -> None:
    sonuc = guvenli_deger("a" * 500)
    assert isinstance(sonuc, str)
    assert sonuc.startswith("[metin:500:")


def test_guvenli_deger_turleri() -> None:
    assert guvenli_deger(None) is None
    assert guvenli_deger(True) is True
    assert guvenli_deger(3) == 3
    assert guvenli_deger({"a": [1, "b"]}) == {"a": [1, "b"]}
    assert guvenli_deger(object()) == "[object]"


def test_maskele_ve_ileti_temizle() -> None:
    assert maskele("x postgres://u:p@h:1/db y") == "x [gizli] y"
    assert PAROLA not in maskele(f"PASSWORD = {PAROLA}")
    assert ileti_temizle("satir 5: bayt 10-20 U+0651") == "satir 5: bayt 10-20 U+0651"
    gizli = ileti_temizle("Deneme ç")
    assert gizli.startswith("[ileti gizlendi:")
    assert len(ileti_temizle("a" * 1000)) == 300


def test_kapi_alani_yalniz_verilirse_yazilir(tmp_path: Path) -> None:
    g = gunluk_kur(tmp_path)
    g.yaz("INFO", "qa_kapi", source_id="test-kaynak", sayilar={"bulgu": 0}, kapi="G-BUT")
    g.yaz("INFO", "qa_basla", source_id="test-kaynak")
    ilk, ikinci = (json.loads(s) for s in g.yol.read_bytes().decode("utf-8").splitlines())
    assert ilk["kapi"] == "G-BUT"
    assert ilk["olay"] == "qa_kapi"
    assert "kapi" not in ikinci  # onceki kayit bicimi korunur
