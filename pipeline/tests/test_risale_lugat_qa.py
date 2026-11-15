# ruff: noqa: RUF003
"""Risale lugat QA kapilari (A20.6; SENTETIK veri, veritabani yok)."""

import copy
import dataclasses
import json
from collections.abc import Callable
from pathlib import Path

import pytest
from lugat_yardimci import ALT_A, ANLAM_IMZASI, LugatKoku, lugat_hazirla

from mutalaa_pipeline.ingest.kelime_frekans import KAYNAK
from mutalaa_pipeline.qa import KAPILAR, kaynak_kapilari, run_risale_lugat
from mutalaa_pipeline.qa.checks.risale_lugat import (
    KAPI_ISLEVLERI,
    LugatGirdisi,
    g_but,
    g_cap,
    g_kay,
    g_nor,
    olcumler,
)
from mutalaa_pipeline.staged import Satir


@pytest.fixture
def kk(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> LugatKoku:
    kok = lugat_hazirla(tmp_path, monkeypatch)
    assert kok.ingest() == 0
    return kok


def girdi(kk: LugatKoku) -> LugatGirdisi:
    ctx = kk.ctx("qa", [KAYNAK])
    kayitlar = ctx.require_sources(
        (KAYNAK, "lugat-redhouse-1890", "lugat-kamus-i-turki", "lugat-naci")
    )
    return run_risale_lugat.yukle(ctx, kayitlar, run=None)[0]


def satir_degistir(g: LugatGirdisi, **alanlar: object) -> LugatGirdisi:
    """Ilk satirin alanlarini degistirir (denemea degil: ilk satir basliksoza gore siralidir)."""
    return satirlari_degistir(g, 0, alanlar)


def satirlari_degistir(g: LugatGirdisi, indeks: int, alanlar: dict[str, object]) -> LugatGirdisi:
    liste = list(g.satirlar)
    ilk = liste[indeks]
    liste[indeks] = Satir(ilk.etiket, ilk.no, {**copy.deepcopy(ilk.veri), **alanlar})
    return dataclasses.replace(g, satirlar=liste)


def bulgular(kapi: str, g: LugatGirdisi) -> tuple[str, ...]:
    return KAPI_ISLEVLERI[kapi](g).bulgular


# --- komut ve rapor ----------------------------------------------------------------------------


def test_dort_kapi_gecer_rapor_kapilari_ve_sayilar(kk: LugatKoku) -> None:
    assert kk.qa() == 0
    rapor = json.loads(sorted((kk.veri_kok / "reports").glob("*.json"))[-1].read_bytes())
    assert rapor["komut"] == "qa run" and rapor["kaynak"] == KAYNAK and rapor["cikis_kodu"] == 0
    assert rapor["kapilar"] == {k: "gecti" for k in KAPILAR}
    assert rapor["kapi_sayilari"]["G-CAP"] == {"uygulanmaz": 1, "madde": 8}
    assert rapor["olcumler"]["duzey"] == {"1": 1, "2": 1, "3": 6}
    assert rapor["anchor_run_id"] == rapor["zincir"]["ingest"]
    assert len(rapor["units_sha256"]) == 64
    metin = json.dumps(rapor)
    assert ANLAM_IMZASI not in metin and "denemea" not in metin  # rapor metin tasimaz
    assert kaynak_kapilari(KAYNAK) == KAPILAR  # `export pg` dort kapi bekler


def test_ingest_yoksa_cikis_2(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    kok = lugat_hazirla(tmp_path, monkeypatch)
    assert kok.qa() == 2


def test_gate_kismi_kosu_ve_bilinmeyen_kapi(kk: LugatKoku) -> None:
    assert (
        run_risale_lugat.komut_qa_run_lugat(run=None, gate=["G-KAY"], config=None, kok=kk.kok) == 0
    )
    assert (
        run_risale_lugat.komut_qa_run_lugat(run=None, gate=["G-HIZ"], config=None, kok=kk.kok) == 2
    )


def test_staged_ozeti_manifestle_tutmazsa_cikis_2(kk: LugatKoku) -> None:
    dosya = kk.staged_klasorleri()[-1] / "lugat.jsonl"
    dosya.write_bytes(dosya.read_bytes() + b"\n")
    assert kk.qa() == 2


def test_ham_dosya_ozeti_manifestle_tutmazsa_cikis_2(kk: LugatKoku) -> None:
    ham = next((kk.veri_kok / "raw" / "lugat-naci").rglob("ocr_djvu.txt"))
    ham.write_bytes(ham.read_bytes() + b"x")
    assert kk.qa() == 2


def test_olcumler_yalniz_sayi(kk: LugatKoku) -> None:
    o = olcumler(girdi(kk))
    assert o["madde"] == 8 and o["norm_paylasan_grup"] == 2  # denemea+Denemea, denemeI+denemeı
    assert o["norm_paylasan_madde"] == 4


# --- G-KAY ---


def test_g_kay_gecer_ve_kayit_surumu_kilitle_tutmazsa_kalir(kk: LugatKoku) -> None:
    g = girdi(kk)
    assert bulgular("G-KAY", g) == ()
    kotu = dataclasses.replace(g, kayit=dataclasses.replace(g.kayit, surum="b" * 40))
    assert any("surumu kilitteki commit" in b for b in g_kay(kotu).bulgular)
    kotu = dataclasses.replace(g, kayit=dataclasses.replace(g.kayit, kaynak_url="https://baska"))
    assert any("kaynak_url" in b for b in g_kay(kotu).bulgular)
    kotu = dataclasses.replace(g, kayit=dataclasses.replace(g.kayit, atif_metni="  "))
    assert any("atif_metni" in b for b in g_kay(kotu).bulgular)
    kotu = dataclasses.replace(g, ingest_commit="c" * 40)
    assert any("ingest manifestindeki commit" in b for b in g_kay(kotu).bulgular)


def test_g_kay_ham_dosya_kilitle_tutmazsa_kalir(kk: LugatKoku) -> None:
    g = girdi(kk)
    assert any(
        "ham zip" in b
        for b in g_kay(dataclasses.replace(g, zip_verisi=g.zip_verisi + b"x")).bulgular
    )
    ocr = {**g.ocr_verileri, "lugat-naci": b"baska"}
    assert any("ham OCR" in b for b in g_kay(dataclasses.replace(g, ocr_verileri=ocr)).bulgular)
    sozluk = {k: v for k, v in g.sozluk_kayitlari.items() if k != "lugat-naci"}
    assert any(
        "kayit yok" in b for b in g_kay(dataclasses.replace(g, sozluk_kayitlari=sozluk)).bulgular
    )


# --- G-BUT ---


def test_g_but_gecer(kk: LugatKoku) -> None:
    g = girdi(kk)
    sonuc = g_but(g)
    assert sonuc.bulgular == () and sonuc.sayilar["madde"] == 8
    assert sonuc.sayilar["alt_kume"] == 1 and sonuc.sayilar["kitap"] == 2


MUTASYONLAR: list[tuple[str, Callable[[LugatGirdisi], LugatGirdisi], str]] = [
    ("tanim", lambda g: satir_degistir(g, tanim_tr="Deneme tanimi"), "tanim_tr"),
    ("yazim", lambda g: satir_degistir(g, osmanlica_yazim="x"), "osmanlica_yazim"),
    ("koken", lambda g: satir_degistir(g, ar_kok_id=3), "ar_kok_id"),
    ("durum", lambda g: satir_degistir(g, status="onayli"), "status, origin"),
    ("kok", lambda g: satir_degistir(g, origin="editor"), "status, origin"),
    ("surum-metin", lambda g: satir_degistir(g, version="1"), "status, origin"),
    ("kaynak", lambda g: satir_degistir(g, source_id="baska"), "status, origin"),
    ("hash", lambda g: satir_degistir(g, content_hash="0" * 64), "content_hash"),
    ("duzey", lambda g: satir_degistir(g, duzey=2), "duzey"),
    ("alan-eksik", lambda g: satir_degistir(g, fazla="x"), "alan kumesi"),
    (
        "anlam-tanimda",
        lambda g: satir_degistir(g, tanim_tr=f"{ANLAM_IMZASI}-1"),
        "anlam dizesi maddeye gecmis",
    ),
]


@pytest.mark.parametrize(("ad", "mutasyon", "parca"), MUTASYONLAR, ids=[m[0] for m in MUTASYONLAR])
def test_g_but_satir_degismezleri_kalir(
    kk: LugatKoku, ad: str, mutasyon: Callable[[LugatGirdisi], LugatGirdisi], parca: str
) -> None:
    kotu = bulgular("G-BUT", mutasyon(girdi(kk)))
    assert any(parca in b for b in kotu), (ad, kotu)


def test_g_but_anlam_kaynaklara_sizarsa_kalir(kk: LugatKoku) -> None:
    g = girdi(kk)
    kaynaklar = copy.deepcopy(g.satirlar[0].veri["kaynaklar"])
    assert isinstance(kaynaklar, dict)
    kaynaklar["anlam_basvuru"] = [{"anlam": f"{ANLAM_IMZASI}-1", "sayi": 1}]
    kotu = bulgular("G-BUT", satir_degistir(g, kaynaklar=kaynaklar))
    assert any("anlam dizesi maddeye gecmis" in b for b in kotu)
    kaynaklar = copy.deepcopy(g.satirlar[0].veri["kaynaklar"])
    assert isinstance(kaynaklar, dict)
    kaynaklar["sozluk_guvenilmez"] = [f"{ANLAM_IMZASI}-2"]
    assert bulgular("G-BUT", satir_degistir(g, kaynaklar=kaynaklar))


def test_g_but_kaynaklar_bozuksa_kalir(kk: LugatKoku) -> None:
    g = girdi(kk)
    ilk = g.satirlar[0].veri["kaynaklar"]
    assert isinstance(ilk, dict)

    def deneme(**degisim: object) -> tuple[str, ...]:
        yeni = {**copy.deepcopy(ilk), **degisim}
        return bulgular("G-BUT", satir_degistir(g, kaynaklar=yeni))

    assert any("kaynaklar" in b for b in deneme(siklik=999))  # kitap toplamiyla tutmaz
    assert any("kaynaklar" in b for b in deneme(kitaplar={ALT_A: 1}, siklik=1))  # alt kume adi
    assert any("sozluk_isabet" in b for b in deneme(sozluk_isabet=[]))
    bozuk = [{"sozluk": "lugat-naci", "bulundu": True, "satir_no": None}] * 3
    assert any("sozluk_isabet" in b for b in deneme(sozluk_isabet=bozuk))
    assert any("kaynaklar" in b for b in deneme(fazla=1))


def test_g_but_basliksoz_kumesi_ve_tekillik(kk: LugatKoku) -> None:
    g = girdi(kk)
    eksik = dataclasses.replace(g, satirlar=list(g.satirlar)[1:])
    kotu = bulgular("G-BUT", eksik)
    assert any("madde sayisi" in b for b in kotu) and any("bayt bayt ayni degil" in b for b in kotu)
    cift = dataclasses.replace(g, satirlar=[*g.satirlar, g.satirlar[-1]])
    assert any("birden cok maddede" in b for b in bulgular("G-BUT", cift))
    degisik = satir_degistir(g, basliksoz="baska")
    assert any("bayt bayt ayni degil" in b for b in bulgular("G-BUT", degisik))
    ters = dataclasses.replace(g, satirlar=list(reversed(g.satirlar)))
    assert any("sirali degil" in b for b in bulgular("G-BUT", ters))


def test_g_but_staged_yeniden_uretilenle_ayni_degilse_kalir(kk: LugatKoku) -> None:
    g = girdi(kk)
    onerilen = copy.deepcopy(g.satirlar[0].veri["onerilen_basvuru"])
    assert isinstance(onerilen, dict)
    onerilen["anlam_basvuru"] = []
    kotu = bulgular("G-BUT", satir_degistir(g, onerilen_basvuru=onerilen))
    assert any("yeniden uretilenle ayni degil" in b for b in kotu)


def test_g_but_ham_zip_kilitle_tutmazsa_kalir(kk: LugatKoku) -> None:
    g = girdi(kk)
    kilit = dataclasses.replace(g.kilit, birlesik={**g.kilit.birlesik, "toplam_frekans": 1})
    kotu = bulgular("G-BUT", dataclasses.replace(g, kilit=kilit))
    assert any("birlesik" in b for b in kotu)
    cozulmez = dataclasses.replace(g, zip_verisi=b"zip degil")
    assert any("yeniden okunamadi" in b for b in bulgular("G-BUT", cozulmez))


# --- G-CAP ve G-NOR ------------------------------------------------------------------------------


def test_g_cap_uygulanmaz_capa_alani_varsa_kalir(kk: LugatKoku) -> None:
    g = girdi(kk)
    sonuc = g_cap(g)
    assert sonuc.gecti and sonuc.sayilar["uygulanmaz"] == 1
    assert any("capa" in b for b in g_cap(satir_degistir(g, anchor="rn:x:p1")).bulgular)


def test_g_nor_bos_ya_da_uyusmayan_norm_kalir(kk: LugatKoku) -> None:
    g = girdi(kk)
    assert g_nor(g).gecti
    assert any("norm-bos" in b for b in g_nor(satir_degistir(g, basliksoz_norm="")).bulgular)
    assert any("norm-fark" in b for b in g_nor(satir_degistir(g, basliksoz_norm="baska")).bulgular)
