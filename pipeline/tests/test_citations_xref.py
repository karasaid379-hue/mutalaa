"""`Tespit` -> `xref` aday satiri, dogal anahtar tekilligi ve idempotentlik (A20.7a).

Girdiler sentetiktir ("Deneme paragrafi ...", Arap alfabesi harfleri, uydurma sure adi). Gercek
bir Kur'an ya da Risale metni kullanilmaz; `q:` capalarindaki sayilar serbesttir.
"""

import json
from collections.abc import Sequence
from pathlib import Path

import pytest

from mutalaa_pipeline.enrich import atif_gramer, citations
from mutalaa_pipeline.enrich.citations import DiziEslesmesi, Tespit
from mutalaa_pipeline.export.ortak import GirdiHatasi

SRC = "rn:deneme-kitap:bolum-1:p3"
SRC_2 = "rn:deneme-kitap:bolum-1:p12"
SURUM = "risale-atif-dizini@test"
DIZI = "ابت ثجح خدذ هوز"  # sentetik harf dizisi


def _tespit(**degisen: object) -> Tespit:
    temel: dict[str, object] = {
        "src_anchor": SRC,
        "src_bas": 10,
        "src_son": 25,
        "sure": 2,
        "ayet": 255,
        "tur": citations.TUR_IKTIBAS,
        "yontem": citations.YONTEM_ARAC,
        "arac": "sahte-arac",
        "arac_surumu": "1.0.0",
        "skor": 0.9,
        "guven": 0.9,
        "ayrintilar": {"kelime_sayisi": 4},
    }
    temel.update(degisen)
    return Tespit(**temel)  # type: ignore[arg-type]


class SahteArac:
    """`DiziTespitcisi` gerceklemesi: dizinin ilk iki kelimesini sure 2'nin iki ayetine esler."""

    ad = "sahte-arac"
    surum = "1.0.0"

    def __init__(self, skor: float | None = 0.9) -> None:
        self.skor = skor
        self.cagrilar: list[str] = []

    def tespit_et(self, dizi_metni: str) -> Sequence[DiziEslesmesi]:
        self.cagrilar.append(dizi_metni)
        ilk_iki = len(" ".join(dizi_metni.split()[:2]))
        return [DiziEslesmesi(0, ilk_iki, ((2, 255), (2, 256)), self.skor, 2)]


def test_tespit_dogrulamalari() -> None:
    _tespit()  # gecerli
    for kotu in (
        {"src_anchor": "q:2:255"},
        {"src_anchor": "rn:deneme-kitap:p3@0-5"},
        {"src_anchor": "rn:deneme-kitap:p3:s2"},
        {"src_anchor": "rn:Deneme:p3"},
        {"src_bas": 5, "src_son": 5},
        {"src_bas": -1},
        {"sure": 115},
        {"ayet": 287},
        {"tur": "ima"},
        {"yontem": "elle"},
        {"skor": 1.5},
        {"guven": -0.1},
        {"ayrintilar": {"serbest": 1}},
        {"ayrintilar": {"sinyal": "Deneme paragrafi 1 bir cumle"}},
    ):
        with pytest.raises(GirdiHatasi):
            _tespit(**kotu)


def test_xref_satiri_alanlari() -> None:
    satir = citations.tespitten_xref(_tespit(), SURUM)
    assert satir["origin"] == "hat"
    assert satir["status"] == "aday"
    assert satir["type"] == "iktibas"
    assert satir["src_anchor"] == SRC
    assert satir["src_span"] == [10, 25]
    assert satir["dst_anchor"] == "q:2:255"
    assert satir["dst_span"] is None
    assert satir["score"] == 0.9
    assert satir["confidence"] == 0.9
    assert satir["data_version"] == SURUM
    assert satir["evidence"] == {
        "arac": "sahte-arac",
        "arac_surumu": "1.0.0",
        "kelime_sayisi": 4,
        "skor": 0.9,
        "source_id": "risale-atif-dizini",
        "yontem": "arac",
    }
    assert citations.KAYNAK_ID == "risale-atif-dizini"


def test_dogal_anahtar() -> None:
    satir = citations.tespitten_xref(_tespit(), SURUM)
    assert citations.xref_natural_key(satir) == ("iktibas", SRC, (10, 25), "q:2:255", None)
    satir["dst_span"] = [3, 8]
    assert citations.xref_natural_key(satir)[4] == (3, 8)
    with pytest.raises(GirdiHatasi):
        citations.xref_natural_key({"type": "atif", "src_anchor": SRC})
    with pytest.raises(GirdiHatasi):
        citations.xref_natural_key({**satir, "src_span": [1, 2, 3]})


def test_ayni_anahtar_birlesir_en_yuksek_guven_kalir() -> None:
    dusuk = _tespit(arac="a-arac", guven=0.6, skor=0.6)
    yuksek = _tespit(arac="b-arac", guven=0.9, skor=0.9)
    baska_aralik = _tespit(src_bas=30, src_son=40)
    baska_tur = _tespit(tur=citations.TUR_ATIF, yontem=citations.YONTEM_GRAMER, arac="x")
    satirlar = citations.xrefleri_birlestir([dusuk, baska_aralik, yuksek, baska_tur], SURUM)
    anahtarlar = [citations.xref_natural_key(s) for s in satirlar]
    assert len(anahtarlar) == len(set(anahtarlar)) == 3
    birlesen = next(s for s in satirlar if s["src_span"] == [10, 25] and s["type"] == "iktibas")
    assert birlesen["confidence"] == 0.9
    assert birlesen["evidence"]["arac"] == "b-arac"  # type: ignore[index]
    assert birlesen["evidence"]["birlesen"] == 2  # type: ignore[index]
    tekli = next(s for s in satirlar if s["src_span"] == [30, 40])
    assert "birlesen" not in tekli["evidence"]  # type: ignore[operator]


def test_birlestirme_giris_sirasindan_bagimsiz() -> None:
    girdiler = [
        _tespit(sure=2, ayet=a, src_bas=b, src_son=b + 5)
        for a in (255, 256, 1)
        for b in (40, 10, 20)
    ]
    a = citations.xrefleri_birlestir(girdiler, SURUM)
    b = citations.xrefleri_birlestir(list(reversed(girdiler)), SURUM)
    assert a == b
    assert citations.xrefs_baytlari(a) == citations.xrefs_baytlari(b)


def test_birimden_tespitler_atif_ve_iktibas() -> None:
    onek = "Deneme paragrafi 1 "
    metin = f"{onek}{DIZI} ve devam (2:255) sonu."
    marks = [{"t": "ar", "s": len(onek), "e": len(onek) + len(DIZI), "tur": "alinti"}]
    arac = SahteArac()
    tespitler = citations.birimden_tespitler(SRC, metin, marks, tespitci=arac)
    assert arac.cagrilar == [DIZI]
    iktibas = [t for t in tespitler if t.tur == "iktibas"]
    atif = [t for t in tespitler if t.tur == "atif"]
    assert [(t.sure, t.ayet) for t in iktibas] == [(2, 255), (2, 256)]
    ilk_iki = len(" ".join(DIZI.split()[:2]))
    assert (iktibas[0].src_bas, iktibas[0].src_son) == (len(onek), len(onek) + ilk_iki)
    assert iktibas[0].ayrintilar["grup"] == f"g{len(onek)}-{len(onek) + ilk_iki}"
    assert iktibas[0].ayrintilar["grup_boyutu"] == 2
    assert iktibas[0].ayrintilar["dizi_turu"] == "alinti"
    assert (iktibas[0].yontem, iktibas[0].arac) == ("arac", "sahte-arac")
    assert len(atif) == 1
    assert (atif[0].sure, atif[0].ayet, atif[0].yontem) == (2, 255, "atif_gramer")
    assert metin[atif[0].src_bas : atif[0].src_son] == "(2:255)"
    assert atif[0].guven == atif_gramer.GUVEN_ADSIZ_PARANTEZ


def test_arac_skor_vermezse_varsayilan_ve_isaret() -> None:
    marks = [{"t": "ar", "s": 0, "e": len(DIZI), "tur": "blok"}]
    tespitler = citations.birimden_tespitler(SRC, DIZI, marks, tespitci=SahteArac(None))
    assert {t.skor for t in tespitler} == {citations.VARSAYILAN_SKOR}
    assert tespitler[0].ayrintilar["skor_yok"] is True
    satir = citations.tespitten_xref(tespitler[0], SURUM)
    assert "skor" not in satir["evidence"]  # type: ignore[operator]
    assert satir["evidence"]["guven_kaynagi"] == "varsayilan"  # type: ignore[index]


def test_min_skor_suzer_ve_arac_yoksa_yalniz_atif() -> None:
    marks = [{"t": "ar", "s": 0, "e": len(DIZI), "tur": "blok"}]
    assert (
        citations.birimden_tespitler(SRC, DIZI, marks, tespitci=SahteArac(0.3), min_skor=0.5) == []
    )
    assert citations.birimden_tespitler(SRC, DIZI, marks) == []


def test_arac_dizi_disi_aralik_verirse_hata() -> None:
    class Tasan:
        ad = "tasan"
        surum = "1"

        def tespit_et(self, dizi_metni: str) -> Sequence[DiziEslesmesi]:
            return [DiziEslesmesi(0, len(dizi_metni) + 1, ((2, 255),), 0.9, 3)]

    marks = [{"t": "ar", "s": 0, "e": len(DIZI), "tur": "blok"}]
    with pytest.raises(GirdiHatasi):
        citations.birimden_tespitler(SRC, DIZI, marks, tespitci=Tasan())


def test_xrefs_baytlari_kanonik_ascii_ve_tekil() -> None:
    satirlar = citations.xrefleri_birlestir([_tespit(), _tespit(src_anchor=SRC_2, ayet=1)], SURUM)
    veri, sayi = citations.xrefs_baytlari(satirlar)
    assert sayi == 2
    assert veri.endswith(b"\n")
    assert b"\r" not in veri
    assert veri.isascii()
    okunan = [json.loads(s) for s in veri.decode("ascii").splitlines()]
    assert [o["src_anchor"] for o in okunan] == [SRC, SRC_2]  # capa sirasi (p3 < p12)
    with pytest.raises(GirdiHatasi, match="yinelenen"):
        citations.xrefs_baytlari([satirlar[0], satirlar[0]])


def test_idempotent_yazim(tmp_path: Path) -> None:
    satirlar = citations.xrefleri_birlestir([_tespit(), _tespit(ayet=256)], SURUM)
    yol = tmp_path / "ara" / "xrefs.jsonl"
    ilk = citations.xrefs_yaz(yol, satirlar)
    assert ilk.satir == 2
    veri = yol.read_bytes()
    yol.touch()
    once = yol.stat().st_mtime_ns
    ikinci = citations.xrefs_yaz(yol, list(reversed(satirlar)))
    assert ikinci.sha256 == ilk.sha256
    assert yol.read_bytes() == veri
    assert yol.stat().st_mtime_ns == once  # ayni baytlar: dosyaya dokunulmaz
    assert not list(yol.parent.glob("*.tmp"))
    # icerik degisirse yeniden yazilir
    degisen = citations.xrefleri_birlestir([_tespit()], SURUM)
    assert citations.xrefs_yaz(yol, degisen).sha256 != ilk.sha256


def test_cikti_birim_metni_tasimaz(tmp_path: Path) -> None:
    onek = "Deneme paragrafi 7 gizli cumle "
    metin = f"{onek}{DIZI} (2:255)"
    marks = [{"t": "ar", "s": len(onek), "e": len(onek) + len(DIZI), "tur": "blok"}]
    tespitler = citations.birimden_tespitler(SRC, metin, marks, tespitci=SahteArac())
    satirlar = citations.xrefleri_birlestir(tespitler, SURUM)
    yol = tmp_path / "xrefs.jsonl"
    citations.xrefs_yaz(yol, satirlar)
    veri = yol.read_text(encoding="ascii")  # ASCII degilse okuma hata verir
    assert "Deneme" not in veri
    assert "gizli" not in veri
    assert all(ord(k) < 128 for k in veri)
    for satir in satirlar:
        evidence = satir["evidence"]
        assert isinstance(evidence, dict)
        assert set(evidence) <= citations.EVIDENCE_ANAHTARLARI
        assert evidence["source_id"] == "risale-atif-dizini"
        assert satir["origin"] == "hat"
        assert satir["status"] == "aday"
