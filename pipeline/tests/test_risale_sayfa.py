# ruff: noqa: F811
"""RNK baski sayfa esleme: adim, QA kapilari ve CLI (A20.3; ACIKCA SENTETIK veri, DB yok).

Hicbir Risale metni yoktur: birimler yalniz capa ve uzunluktur ya da "Deneme ..." yer tutucu
metinli sentetik RNK dosyasindan (`test_risale_rnk`) gelir. Gercek `risale-kitaplar.json` yalniz
cilt tablosu testlerinde okunur.
"""

import copy
import json
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from hat_yardimci import ansisiz, ctx_kur
from test_risale_rnk import kitap_kaydi
from test_risale_rnk_cli import RnkKoku, rk  # noqa: F401  (rk: fixture)
from test_sources import alanlar_kur, kayit_yaz
from typer.testing import CliRunner

from mutalaa_pipeline import cli, qa
from mutalaa_pipeline.adimlar import risale_sayfa as S
from mutalaa_pipeline.adimlar.risale_sayfa import BirimKonumu, Konum
from mutalaa_pipeline.anchor import parse, sort_key
from mutalaa_pipeline.anchor.risale import Bolunme, BolunmeParcasi, kitaplar
from mutalaa_pipeline.enums import SourceKind
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.ingest import risale_kaynaklari
from mutalaa_pipeline.qa import run_risale_sayfa as QS
from mutalaa_pipeline.qa.checks import risale_sayfa as Q

KAYNAK = "risale-baski-rnk"
SURUM = "deneme-baski"
DOSYA = "tr_k/deneme"
runner = CliRunner()


# --- sentetik birim ve sayfa kayitlari -------------------------------------------------------


def birim(
    capa: str,
    uzunluk: int,
    satir: int,
    *,
    dosya: str = DOSYA,
    bolum: int | None = None,
    sayfa: int | None = None,
    cumle: tuple[tuple[int, int], ...] | None = None,
    hasiye: int = 0,
) -> BirimKonumu:
    return BirimKonumu(
        capa=capa,
        uzunluk=uzunluk,
        dosya=dosya,
        anahtar=(satir, hasiye, sort_key(parse(capa))),
        bolum_sayfasi=bolum,
        sayfa=sayfa,
        cumle_baslari=cumle,
    )


def kayit(n: int, capa: str | None, ofs: int = 0, dosya: str = DOSYA) -> dict[str, object]:
    tur = "icerik-yok" if capa is None else ("bas" if ofs == 0 else "ortasi")
    return {"dosya": dosya, "n": n, "satir": n * 10, "capa": capa, "ofs": ofs, "tur": tur}


def uret(
    birimler: list[BirimKonumu],
    sayfalar: list[dict[str, object]],
    *,
    cilt: int = 7,
    dosya: str = DOSYA,
) -> S.DosyaSonucu:
    return S.dosya_satirlari(dosya, cilt, sayfalar, birimler, SURUM)


def kisa(satir: dict[str, object]) -> tuple[object, ...]:
    return (
        satir["page"],
        satir["start_anchor"],
        satir["start_offset"],
        satir["end_anchor"],
        satir["end_offset"],
        str(satir["data_version"]).removeprefix(f"{KAYNAK}@{SURUM}"),
    )


P1, P2, P3, P4 = (f"rn:deneme:soz-1:p{i}" for i in (1, 2, 3, 4))


# --- sayfa basi: birim basi ve birim ortasi --------------------------------------------------


def test_sayfa_basi_birim_basinda_ve_ortasinda_bitisikler() -> None:
    birimler = [birim(P1, 20, 2), birim(P2, 30, 3), birim(P3, 10, 4)]
    sonuc = uret(birimler, [kayit(1, P1), kayit(2, P2, 12), kayit(3, P3)])
    assert [kisa(s) for s in sonuc.satirlar] == [
        (1, P1, 0, P2, 12, ""),  # sonraki sayfa birim ortasinda: ayni birim, end_offset = ofs
        (2, P2, 12, P2, 30, ""),  # sonraki birim basinda: onceki birimin sonu
        (3, P3, 0, P3, 10, ""),  # son sayfa: dosyanin son birimi
    ]
    assert all(s["source_id"] == KAYNAK and s["volume"] == 7 for s in sonuc.satirlar)
    r = sonuc.rapor
    assert (r["sayfa"], r["gercek_satir"], r["ardisik"]) == (3, 3, True)
    assert (r["sayfa_basi_birim_basi"], r["sayfa_basi_cumle_ortasi"]) == (2, 0)
    assert r["sayfa_basi_cumle_basi"] == 1  # cumle bilgisi yok: ofs>0 ve cumle icinde degil
    assert (r["ilk_sayfa"], r["son_sayfa"]) == (1, 3)


def test_cumle_ortasi_ve_cumle_basi_ayrimi() -> None:
    cumle = ((0, 10), (11, 20))
    birimler = [birim(P1, 20, 2, cumle=cumle), birim(P2, 5, 3)]
    sonuc = uret(birimler, [kayit(1, P1, 5), kayit(2, P1, 10), kayit(3, P1, 11), kayit(4, P2)])
    r = sonuc.rapor
    assert (
        r["sayfa_basi_cumle_ortasi"],
        r["sayfa_basi_cumle_basi"],
        r["sayfa_basi_birim_basi"],
    ) == (
        1,
        2,
        1,
    )


def test_bos_sayfa_sifir_uzunluklu_satir_ve_icerik_yok_satir_uretmez() -> None:
    birimler = [birim(P1, 20, 2), birim(P2, 30, 3)]
    sayfalar = [kayit(1, P1), kayit(2, P2), kayit(3, P2), kayit(4, None)]
    sonuc = uret(birimler, sayfalar)
    assert [kisa(s)[:5] for s in sonuc.satirlar] == [
        (1, P1, 0, P1, 20),
        (2, P2, 0, P2, 0),  # kaynakta #2 var, metin yok: sifir uzunluk
        (3, P2, 0, P2, 30),
    ]
    r = sonuc.rapor
    assert (r["sayfa"], r["gercek_satir"], r["bos_sayfa"], r["icerik_yok"]) == (4, 3, 1, 1)
    assert all(s["page"] != 4 for s in sonuc.satirlar)  # kaynakta metni olmayan sayfa doldurulmaz


def test_sayfa_numarasi_atlarsa_ardisik_false_satir_doldurulmaz() -> None:
    birimler = [birim(P1, 20, 2), birim(P2, 30, 3)]
    sonuc = uret(birimler, [kayit(1, P1), kayit(3, P2)])
    assert sonuc.rapor["ardisik"] is False
    assert [s["page"] for s in sonuc.satirlar] == [1, 3]  # 2. sayfa kaynakta yok: uydurulmaz


# --- bolum basi ----------------------------------------------------------------------------


def test_bolum_basi_hizali_sayfanin_gercek_satiri_yerine_gecer_cift_yazma_yok() -> None:
    birimler = [birim(P1, 14, 2, bolum=1, sayfa=1), birim(P2, 30, 3)]
    sonuc = uret(birimler, [kayit(1, P1), kayit(2, P2)])
    assert len(sonuc.satirlar) == 2
    assert all("/bolum-basi" not in str(s["data_version"]) for s in sonuc.satirlar)
    r = sonuc.rapor
    assert (r["bolum_basi_yerine_gecen"], r["bolum_basi_yazilan"]) == (1, 0)


def test_bolum_sayfa_ortasinda_ya_da_ayni_sayfada_ikinci_satir_yazilmaz_rapora_sayilir() -> None:
    birimler = [
        birim(P1, 14, 2, bolum=1, sayfa=1),  # hizali
        birim(P2, 30, 3),
        birim(P3, 14, 4, bolum=2, sayfa=2),  # sayfa 2 P2 ortasinda basladi: sayfa ortasi
        birim(P4, 14, 5, bolum=2, sayfa=2),  # ayni sayfada ikinci bolum
    ]
    sonuc = uret(birimler, [kayit(1, P1), kayit(2, P2, 9)])
    assert len(sonuc.satirlar) == 2  # tekil anahtar: sayfa basina tek satir
    r = sonuc.rapor
    assert (
        r["bolum_basi_yerine_gecen"],
        r["bolum_basi_sayfa_ortasi"],
        r["bolum_basi_ayni_sayfada_ikinci"],
        r["bolum_basi_yazilan"],
    ) == (1, 1, 1, 0)


def test_bolumun_sayfasi_gercek_sayfadir_json_pageno_degil_fark_raporlanir() -> None:
    # json pageNo 5, gercek #n sayfasi 2: gercek sayfa esas alinir (K-52 madde 6)
    birimler = [birim(P1, 14, 2, bolum=1, sayfa=1), birim(P2, 14, 3, bolum=5, sayfa=2)]
    sonuc = uret(birimler, [kayit(1, P1), kayit(2, P2)])
    r = sonuc.rapor
    assert (r["bolum_basi_yerine_gecen"], r["bolum_basi_json_sayfa_farkli"]) == (2, 1)
    assert r["bolum_basi_yazilan"] == 0 and len(sonuc.satirlar) == 2


def test_gercek_satiri_olmayan_sayfada_ilk_bolum_yazilir_sayfasiz_baslik_sayilir() -> None:
    birimler = [
        birim(P1, 14, 2, bolum=1, sayfa=None),  # ilk #n isaretinden once: sayfasiz
        birim(P2, 30, 3, bolum=2, sayfa=2),  # sayfa 2'nin satiri yok (kaynakta #2 yok)
        birim(P3, 14, 4, bolum=2, sayfa=2),  # ayni sayfada ikinci bolum
        birim(P4, 10, 5),
    ]
    sonuc = uret(birimler, [kayit(1, P1, 3), kayit(3, P4)])
    r = sonuc.rapor
    assert (r["bolum_basi_sayfasiz"], r["bolum_basi_yazilan"]) == (1, 1)
    assert r["bolum_basi_ayni_sayfada_ikinci"] == 1
    (bolum,) = [s for s in sonuc.satirlar if "/bolum-basi" in str(s["data_version"])]
    assert (bolum["page"], bolum["start_anchor"], bolum["start_offset"]) == (2, P2, 0)
    assert (bolum["end_anchor"], bolum["end_offset"]) == (P3, 14)  # sonraki baslangic: sayfa 3


# --- sunuhat bolunmesi ---------------------------------------------------------------------


def test_bolunen_dosyada_satir_capanin_kendi_slugini_gosterir() -> None:
    sunuhat, tuluat, isarat = "rn:sunuhat:p1", "rn:tuluat:p1", "rn:isarat:p1"
    birimler = [
        birim(sunuhat, 20, 2),
        birim("rn:sunuhat:p2", 30, 3),
        birim(tuluat, 10, 4),
        birim(isarat, 10, 5),
    ]
    sayfalar = [kayit(1, sunuhat), kayit(2, "rn:sunuhat:p2", 5), kayit(3, tuluat), kayit(4, isarat)]
    sonuc = uret(birimler, sayfalar)
    assert [(s["page"], str(s["start_anchor"]).split(":")[1]) for s in sonuc.satirlar] == [
        (1, "sunuhat"),
        (2, "sunuhat"),
        (3, "tuluat"),
        (4, "isarat"),
    ]
    # kitap sinirindaki sayfa: bitis onceki kitabin son biriminde (kitap atlanmaz)
    assert (sonuc.satirlar[1]["end_anchor"], sonuc.satirlar[1]["end_offset"]) == (
        "rn:sunuhat:p2",
        30,
    )
    assert sonuc.rapor["slug_sayfa"] == {"isarat": 1, "sunuhat": 2, "tuluat": 1}


# --- girdi hatalari (cikis 2) --------------------------------------------------------------


@pytest.mark.parametrize(
    ("sayfalar", "neden"),
    [
        ([kayit(1, P1), kayit(1, P1)], "yinelenen sayfa numarasi"),
        ([kayit(1, "rn:deneme:soz-1:p9")], "anchor ciktisinda yok"),
        ([kayit(1, P1, 99)], "metnine sigmiyor"),
        ([kayit(1, P2, 3), kayit(2, P1)], "oncesinde basliyor"),
        ([{**kayit(1, P1, 3), "tur": "bas"}], "tur ofsetle tutmuyor"),
    ],
)
def test_sayfa_girdisi_bozuksa_girdi_hatasi(sayfalar: list[dict[str, object]], neden: str) -> None:
    birimler = [birim(P1, 20, 2), birim(P2, 30, 3)]
    with pytest.raises(GirdiHatasi, match=neden):
        uret(birimler, sayfalar)


def test_birimsiz_dosya_ve_tabloda_olmayan_dosya_girdi_hatasi() -> None:
    with pytest.raises(GirdiHatasi, match="birim yok"):
        uret([], [kayit(1, P1)])
    with pytest.raises(GirdiHatasi, match="kitap tablosunda olmayan"):
        S.sayfa_esleme_uret({DOSYA: [birim(P1, 5, 2)]}, {}, {"baska/dosya": 1}, SURUM)


def test_sayfa_satiri_alan_kumesi_ve_tur_denetimi() -> None:
    from mutalaa_pipeline.staged import Satir

    iyi = Satir("t", 1, kayit(1, P1))
    fazla = Satir("t", 2, {**kayit(2, P1), "metin": "x"})
    assert S.sayfa_baslari_oku([iyi])[DOSYA][0]["n"] == 1
    with pytest.raises(GirdiHatasi, match="alan kumesi"):
        S.sayfa_baslari_oku([fazla])
    with pytest.raises(GirdiHatasi, match="capa ile tur tutarsiz"):
        S.sayfa_baslari_oku([Satir("t", 3, {**kayit(3, P1), "tur": "icerik-yok"})])


# --- cilt tablosu --------------------------------------------------------------------------


def test_cilt_tablosu_gercek_tablo_kalici_cilt_alanindan() -> None:
    tablo = kitaplar()
    cilt = S.cilt_tablosu(tablo)
    dosyalar = {(k.rnk.raf, k.rnk.uid) for k in tablo if k.rnk}
    assert len(cilt) == len(dosyalar) == 85  # 87 kitap, bolunen sunuhat tek RNK dosyasi
    assert sorted(cilt.values()) == list(range(1, 86))  # tekil, 1'den kesintisiz
    assert max(cilt.values()) <= S.SMALLINT_USTU
    assert all(cilt[f"{k.rnk.raf}/{k.rnk.uid}"] == k.rnk.cilt for k in tablo if k.rnk)
    assert "tr_k/sunuhat" in cilt and next(iter(cilt)) == "tr/sozler"


def test_cilt_tablosu_tablodaki_cilt_alanini_kullanir_ilk_gorunme_hesaplamaz() -> None:
    bolunme = Bolunme(
        20,
        (
            BolunmeParcasi("deneme-a", 1),
            BolunmeParcasi("deneme-b", 10),
            BolunmeParcasi("deneme-c", 15),
        ),
    )
    tablo = (
        kitap_kaydi("deneme-a", "tr_k", "x", bolunme, cilt=40),
        kitap_kaydi("deneme-b", "tr_k", "x", bolunme, cilt=40),
        kitap_kaydi("deneme-c", "tr_k", "x", bolunme, cilt=40),
        kitap_kaydi("deneme-d", "osm", "osm_y", cilt=2),
    )
    assert S.cilt_tablosu(tablo) == {"tr_k/x": 40, "osm/osm_y": 2}  # sira degil alan
    with pytest.raises(GirdiHatasi, match="iki cilt"):
        S.cilt_tablosu(
            (
                kitap_kaydi("deneme-a", "tr_k", "x", bolunme, cilt=1),
                kitap_kaydi("deneme-b", "tr_k", "x", bolunme, cilt=2),
            )
        )
    with pytest.raises(GirdiHatasi, match="tekil"):
        S.cilt_tablosu(
            (
                kitap_kaydi("deneme-a", "tr_k", "a", cilt=1),
                kitap_kaydi("deneme-b", "tr_k", "b", cilt=1),
            )
        )


def test_data_versiyonu_ve_konum_sirasi() -> None:
    assert S.data_versiyonu("v1") == "risale-baski-rnk@v1"
    assert S.data_versiyonu("v1", bolum_basi=True) == "risale-baski-rnk@v1/bolum-basi"
    assert Konum(1, 5) < Konum(2, 0) and Konum(2, 0) < Konum(2, 3)


# --- kaynak kaydi ve yonlendirme -----------------------------------------------------------


def test_kaynak_yonlendirmesi_ingest_kaynagi_degil_adim_ciktisi() -> None:
    assert risale_kaynaklari.baski_mi(KAYNAK) and not risale_kaynaklari.baski_mi("risale-rnk-metin")
    assert not risale_kaynaklari.risale_mi(KAYNAK)  # ingest/export-birim yolu kullanmaz
    assert qa.kaynak_kapilari(KAYNAK) == ("G-KAY", "G-BUT", "G-CAP", "G-NOR")
    assert risale_kaynaklari.BASKI_KAPILARI == ("G-KAY", "G-BUT", "G-CAP", "G-NOR")


def test_gercek_kaynak_kaydi_gecerli_baski_kaydi() -> None:
    from mutalaa_pipeline.sources import kayit as kayit_modulu

    yol = Path(__file__).resolve().parents[1] / "sources" / f"{KAYNAK}.toml"
    sonuc = kayit_modulu.oku(yol)
    assert sonuc.hatalar == [] and sonuc.kaynak is not None
    k = sonuc.kaynak
    assert k.tur is SourceKind.BASKI and k.surum and k.kaynak_url and k.atif_metni
    assert (k.baski_bilgisi or {}).get("yayinevi")


# --- zincir: sentetik RNK dosyasindan adim ve QA --------------------------------------------


@pytest.fixture
def bk(rk: RnkKoku, monkeypatch: pytest.MonkeyPatch) -> RnkKoku:
    """`rk` + `risale-baski-rnk` kaynak kaydi + tek kitaplik tablo."""
    kayit_yaz(
        rk.kok,
        alanlar_kur(
            KAYNAK,
            tur="baski",
            baslik="Deneme baski",
            surum=SURUM,
            kaynak_url="https://example.test/x",
            baski_bilgisi={"yayinevi": "Deneme Yayinevi"},
        ),
    )
    tablo = (kitap_kaydi(),)
    monkeypatch.setattr(S, "kitaplar", lambda: tablo)
    monkeypatch.setattr(QS, "kitaplar", lambda: tablo)
    return rk


def baski(rk_: RnkKoku, *arg: str) -> int:
    return runner.invoke(
        cli.app, ["anchor", "--source", KAYNAK, *arg, "--kok", str(rk_.kok)]
    ).exit_code


def baski_qa(rk_: RnkKoku, *arg: str) -> tuple[int, str]:
    sonuc = runner.invoke(cli.app, ["qa", "run", "--source", KAYNAK, *arg, "--kok", str(rk_.kok)])
    return sonuc.exit_code, sonuc.output


def baski_klasorleri(rk_: RnkKoku) -> list[Path]:
    kok = rk_.veri_kok / "staged" / KAYNAK
    return sorted(kok.iterdir()) if kok.is_dir() else []


def satirlari_oku(klasor: Path, ad: str = S.SAYFA_ESLEME_ADI) -> list[dict[str, Any]]:
    return [json.loads(s) for s in (klasor / ad).read_text(encoding="utf-8").splitlines()]


def test_adim_sentetik_dosyada_beklenen_satirlar(bk: RnkKoku) -> None:
    assert bk.zincir() == 0 and baski(bk) == 0
    (klasor,) = baski_klasorleri(bk)
    satirlar = satirlari_oku(klasor)
    assert [(s["page"], s["start_anchor"], s["start_offset"]) for s in satirlar] == [
        (4, "rn:deneme-kitap:p1", 0),
        (5, "rn:deneme-kitap:deneme-bolum-1:p2", 0),
        (6, "rn:deneme-kitap:deneme-bolum-1:p2", 31),  # sayfa paragrafin ortasinda basliyor
        (7, "rn:deneme-kitap:deneme-bolum-2:p1", 0),
    ]
    assert {(s["source_id"], s["volume"]) for s in satirlar} == {(KAYNAK, 1)}
    assert all(s["data_version"] == f"{KAYNAK}@{SURUM}" for s in satirlar)  # bolum basi yok
    assert satirlar[2]["end_anchor"] == "rn:deneme-kitap:deneme-bolum-1:p4"
    (rapor,) = satirlari_oku(klasor, S.SAYFA_RAPOR_ADI)
    assert (rapor["sayfa"], rapor["bolum_basi_yerine_gecen"], rapor["sayfa_basi_cumle_ortasi"]) == (
        4,
        2,
        1,
    )
    manifest = json.loads((klasor / "manifest.json").read_bytes())
    assert manifest["adim"] == "anchor" and manifest["ayrintilar"]["cilt"] == {"tr_k/deneme": 1}
    assert manifest["ayrintilar"]["data_version"] == f"{KAYNAK}@{SURUM}"
    assert {c["yol"].split("/")[-1] for c in manifest["ciktilar"]} == {
        "page_map.jsonl",
        "page_map_rapor.jsonl",
    }
    # girdiler: risale-rnk-metin anchor units.jsonl ve ingest sayfalar.jsonl (ust_run_id'li)
    assert {g["yol"].split("/")[-1] for g in manifest["girdiler"]} == {
        "units.jsonl",
        "sayfalar.jsonl",
    }
    assert all(g["ust_run_id"] for g in manifest["girdiler"])


def test_adim_cikti_ve_rapor_metin_tasimaz(bk: RnkKoku) -> None:
    assert bk.zincir() == 0 and baski(bk) == 0 and baski_qa(bk)[0] == 0
    (klasor,) = baski_klasorleri(bk)
    ham = b"".join(p.read_bytes() for p in klasor.iterdir())
    ham += b"".join(p.read_bytes() for p in (bk.veri_kok / "reports").glob("*.json"))
    ham += b"".join(p.read_bytes() for p in (bk.veri_kok / "logs").glob("*.jsonl"))
    assert ham and b"Deneme paragraf" not in ham and b"Deneme dipnot" not in ham
    assert b"Deneme B" not in ham  # baslik metni de yok
    for satir in satirlari_oku(klasor):
        assert set(satir) == S.SATIR_ALANLARI  # yalniz capa, sayi ve surum


def test_adim_idempotent_ayni_girdi_ayni_baytlar_dry_run_yazmaz(bk: RnkKoku) -> None:
    assert bk.zincir() == 0
    assert baski(bk, "--dry-run") == 0 and baski_klasorleri(bk) == []
    assert baski(bk) == 0 and baski(bk, "--force") == 0
    ilk, ikinci = baski_klasorleri(bk)
    for ad in (S.SAYFA_ESLEME_ADI, S.SAYFA_RAPOR_ADI):
        assert (ilk / ad).read_bytes() == (ikinci / ad).read_bytes()
    assert (ilk / S.SAYFA_ESLEME_ADI).read_bytes().endswith(b"\n")
    assert b"\r" not in (ilk / S.SAYFA_ESLEME_ADI).read_bytes()


def test_adim_anchor_zinciri_yoksa_cikis_2_ve_yanlis_kaynak(bk: RnkKoku) -> None:
    assert baski(bk) == 2  # risale-rnk-metin anchor calistirmasi yok
    assert bk.ingest() == 0 and baski(bk) == 2  # yalniz ingest
    assert bk.zincir() == 0
    sonuc = runner.invoke(
        cli.app, ["anchor", "--source", KAYNAK, "--limit", "3", "--kok", str(bk.kok)]
    )
    assert sonuc.exit_code == 2  # --limit reddedilir


def test_adim_kayitsiz_kaynak_kaydi_cikis_2(
    rk: RnkKoku,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert rk.zincir() == 0
    assert baski(rk) == 2  # risale-baski-rnk kaydi yok: kaydi olmayan kaynak hatta alinmaz


def test_adim_cikti_ozeti_bozulursa_ve_ust_degisirse(bk: RnkKoku) -> None:
    assert bk.zincir() == 0 and baski(bk) == 0
    (klasor,) = baski_klasorleri(bk)
    assert baski_qa(bk)[0] == 0
    (klasor / S.SAYFA_ESLEME_ADI).write_bytes((klasor / S.SAYFA_ESLEME_ADI).read_bytes() + b"\n")
    assert baski_qa(bk)[0] == 2  # manifestteki ozet tutmuyor


def test_yardim_ve_cli_secenekleri(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FORCE_COLOR", "1")
    for komut in (["anchor", "--help"], ["qa", "run", "--help"], ["export", "pg", "--help"]):
        sonuc = runner.invoke(cli.app, komut)
        assert sonuc.exit_code == 0, sonuc.output
        yardim = ansisiz(sonuc.output)
        assert "--source" in yardim
    assert "--gate" in ansisiz(runner.invoke(cli.app, ["qa", "run", "--help"]).output)
    assert "--dry-run" in ansisiz(runner.invoke(cli.app, ["anchor", "--help"]).output)


# --- QA: dort kapi -------------------------------------------------------------------------


def test_qa_dort_kapi_gecer_rapor_alanlari(bk: RnkKoku) -> None:
    assert bk.zincir() == 0 and baski(bk) == 0
    kod, cikti = baski_qa(bk)
    assert kod == 0, cikti
    for kapi in ("G-KAY", "G-BUT", "G-CAP", "G-NOR"):
        assert f"{kapi} gecti" in cikti
    rapor = json.loads(sorted((bk.veri_kok / "reports").glob("*.json"))[-1].read_bytes())
    (klasor,) = baski_klasorleri(bk)
    assert rapor["kaynak"] == KAYNAK and rapor["anchor_run_id"] == klasor.name
    assert len(rapor["units_sha256"]) == 64 and rapor["onceki_anchor_run_id"] is None
    assert rapor["kapilar"] == {k: "gecti" for k in qa.kaynak_kapilari(KAYNAK)}
    sayilar = rapor["kapi_sayilari"]
    assert sayilar["G-BUT"]["kilit_sayfa"] == sayilar["G-BUT"]["gercek_satir"] == 4
    assert sayilar["G-NOR"]["uygulanmaz"] == 1
    assert rapor["cikis_kodu"] == 0


def test_qa_ikinci_kosuda_onceki_calisma_tabani(bk: RnkKoku) -> None:
    assert bk.zincir() == 0 and baski(bk) == 0 and baski_qa(bk)[0] == 0
    assert baski(bk, "--force") == 0
    assert baski_qa(bk)[0] == 0
    rapor = json.loads(sorted((bk.veri_kok / "reports").glob("*.json"))[-1].read_bytes())
    assert rapor["onceki_anchor_run_id"] == baski_klasorleri(bk)[0].name
    assert rapor["kapi_sayilari"]["G-CAP"]["onceki_run"] == 1


def test_qa_kismi_gate_gecersiz_gate_ve_adim_yoksa(bk: RnkKoku) -> None:
    assert baski_qa(bk)[0] == 2  # sayfa esleme calistirmasi yok
    assert bk.zincir() == 0 and baski(bk) == 0
    kod, cikti = baski_qa(bk, "--gate", "G-KAY")
    assert kod == 0 and "G-KAY gecti" in cikti and "G-BUT" not in cikti
    assert baski_qa(bk, "--gate", "G-HIZ")[0] == 2


def girdi_yukle(rk_: RnkKoku) -> Q.SayfaGirdisi:
    ctx = ctx_kur(rk_.tmp, rk_.kok, adim="qa", kaynaklar=[KAYNAK])
    girdi, _, _ = QS.yukle(ctx)
    return girdi


def bozulmus(
    g: Q.SayfaGirdisi, degistir: Callable[[list[dict[str, object]]], None]
) -> Q.SayfaGirdisi:
    kopya = copy.copy(g)
    satirlar = [dict(s) for s in g.satirlar]
    degistir(satirlar)
    kopya.satirlar = satirlar
    return kopya


def kalan(g: Q.SayfaGirdisi, kapi: str) -> str:
    sonuc = Q.KAPI_ISLEVLERI[kapi](g)
    assert not sonuc.gecti
    assert all(b.isascii() for b in sonuc.bulgular)
    return " | ".join(sonuc.bulgular)


def test_qa_kapilar_temiz_girdide_gecer(bk: RnkKoku) -> None:
    assert bk.zincir() == 0 and baski(bk) == 0
    g = girdi_yukle(bk)
    for kapi, islev in Q.KAPI_ISLEVLERI.items():
        sonuc = islev(g)
        assert sonuc.gecti, (kapi, sonuc.bulgular)


def test_g_but_sayfa_sayisi_ve_ardisiklik_kalir(bk: RnkKoku) -> None:
    assert bk.zincir() == 0 and baski(bk) == 0
    g = girdi_yukle(bk)
    assert "kilitle farkli" in kalan(bozulmus(g, lambda s: s.pop()), "G-BUT")  # eksik sayfa
    assert "yinelenen sayfa" in kalan(bozulmus(g, lambda s: s.append(dict(s[0]))), "G-BUT")
    # sayfa 5 -> 9: kumeler ve +1 ardisiklik bozulur
    assert "ardisik degil" in kalan(bozulmus(g, lambda s: s[1].update(page=9)), "G-BUT")


def test_g_but_bitisiklik_ofset_ve_capa_kalir(bk: RnkKoku) -> None:
    assert bk.zincir() == 0 and baski(bk) == 0
    g = girdi_yukle(bk)
    assert "bitisik degil" in kalan(bozulmus(g, lambda s: s[1].update(end_offset=30)), "G-BUT")
    assert "metne sigmiyor" in kalan(bozulmus(g, lambda s: s[0].update(start_offset=999)), "G-BUT")
    assert "ayni dosyada degil" in kalan(
        bozulmus(g, lambda s: s[0].update(start_anchor="rn:baska-kitap:p1")), "G-BUT"
    )
    assert "cilt tablosunda yok" in kalan(bozulmus(g, lambda s: s[0].update(volume=99)), "G-BUT")
    assert "alan kumesi" in kalan(bozulmus(g, lambda s: s[0].update(metin="x")), "G-BUT")
    assert "baslangictan once" in kalan(
        bozulmus(g, lambda s: s[2].update(end_anchor=s[2]["start_anchor"], end_offset=1)), "G-BUT"
    )
    # son sayfa dosya sonunda bitmeli
    assert "dosya sonunda" in kalan(bozulmus(g, lambda s: s[3].update(end_offset=1)), "G-BUT")


def test_g_cap_satir_birim_ozetleri_tasir_ve_birimle_ayni_olmali(bk: RnkKoku) -> None:
    """`start_hash`/`end_hash`: 64 haneli onaltilik ve anchor ciktisindaki ozetle ayni."""
    assert bk.zincir() == 0 and baski(bk) == 0
    g = girdi_yukle(bk)
    assert all(
        len(str(s["start_hash"])) == 64 and len(str(s["end_hash"])) == 64 for s in g.satirlar
    )
    assert "ozet biciminde" in kalan(bozulmus(g, lambda s: s[0].update(start_hash="x")), "G-CAP")
    assert "ozet biciminde" in kalan(bozulmus(g, lambda s: s[0].update(end_hash="A" * 64)), "G-CAP")
    assert "ozet birimle farkli" in kalan(
        bozulmus(g, lambda s: s[1].update(end_hash="0" * 64)), "G-CAP"
    )
    assert "alan kumesi" in kalan(bozulmus(g, lambda s: s[0].pop("start_hash")), "G-BUT")


def test_g_but_json_meta_ve_kilit_sayfa_sayisi_kalir(bk: RnkKoku) -> None:
    assert bk.zincir() == 0 and baski(bk) == 0
    g = girdi_yukle(bk)
    kopya = copy.copy(g)
    kopya.kitaplar = [{**k, "json_son_sayfa": 99} for k in g.kitaplar]
    assert "ilk/son sayfa" in kalan(kopya, "G-BUT")
    kopya = copy.copy(g)
    ((ad, kitap),) = g.kilit.kitaplar.items()
    veri = {**kitap.veri, "sayfa_sayisi": 5}
    kopya.kilit = replace(g.kilit, kitaplar={ad: replace(kitap, veri=veri)})
    assert "kilitle farkli" in kalan(kopya, "G-BUT")


def test_g_but_rapor_ve_yeniden_uretim_farki_kalir(bk: RnkKoku) -> None:
    assert bk.zincir() == 0 and baski(bk) == 0
    g = girdi_yukle(bk)
    kopya = copy.copy(g)
    kopya.raporlar = [{**r, "bos_sayfa": 5} for r in g.raporlar]
    assert "yeniden uretilince ayni degil" in kalan(kopya, "G-BUT")


def test_g_but_bolum_basi_satiri_baslik_birimine_bagli_olmali(bk: RnkKoku) -> None:
    assert bk.zincir() == 0 and baski(bk) == 0
    g = girdi_yukle(bk)
    surum = f"{KAYNAK}@{SURUM}/bolum-basi"
    # gercek bir satiri bolum basi diye isaretlemek yeniden uretimle tutmaz; baslangici baslik
    # birimi olmayan satir (sayfa 5: paragraf) baslik birimine bagli degildir
    sonuc = kalan(bozulmus(g, lambda s: s[1].update(data_version=surum)), "G-BUT")
    assert "baslik birimine" in sonuc and "yeniden uretilince" in sonuc


def test_g_cap_capa_tekillik_surum_ve_onceki_satir_kalir(bk: RnkKoku) -> None:
    assert bk.zincir() == 0 and baski(bk) == 0
    g = girdi_yukle(bk)
    assert "gecersiz capa" in kalan(
        bozulmus(g, lambda s: s[0].update(start_anchor="rn:Deneme")), "G-CAP"
    )
    assert "kitap tabloda yok" in kalan(
        bozulmus(g, lambda s: s[0].update(end_anchor="rn:baska-kitap:p1")), "G-CAP"
    )
    assert "data_version" in kalan(bozulmus(g, lambda s: s[0].update(data_version="x@y")), "G-CAP")
    assert "source_id" in kalan(bozulmus(g, lambda s: s[0].update(source_id="baska")), "G-CAP")
    assert "yinelenen anahtar" in kalan(bozulmus(g, lambda s: s.append(dict(s[1]))), "G-CAP")
    # onceki calismada olup kaybolan satir ve kullanim disi kalan capa
    kopya = copy.copy(g)
    kopya.onceki = Q.SayfaOnceki("onceki", {(1, 42): ("rn:deneme-kitap:p1", "rn:deneme-kitap:p1")})
    assert "kaybolan satir" in kalan(kopya, "G-CAP")
    kopya.onceki = Q.SayfaOnceki("onceki", {(1, 4): ("rn:deneme-kitap:p9", "rn:deneme-kitap:p1")})
    assert "anchor ciktisinda yok" in kalan(kopya, "G-CAP")


def test_g_kay_kayit_tur_ve_surum_kalir(bk: RnkKoku) -> None:
    assert bk.zincir() == 0 and baski(bk) == 0
    g = girdi_yukle(bk)
    kopya = copy.copy(g)
    kopya.kayit = replace(g.kayit, tur=SourceKind.RISALE)
    assert "tur baski" in kalan(kopya, "G-KAY")
    kopya = copy.copy(g)
    kopya.kayit = replace(g.kayit, baski_bilgisi=None)
    assert "yayinevi" in kalan(kopya, "G-KAY")
    kopya = copy.copy(g)
    kopya.manifest_data_version = "x@eski"
    assert "data_version" in kalan(kopya, "G-KAY")


def test_g_nor_uygulanmaz_ama_metin_tasimayi_reddeder(bk: RnkKoku) -> None:
    assert bk.zincir() == 0 and baski(bk) == 0
    g = girdi_yukle(bk)
    assert Q.g_nor(g).gecti and Q.g_nor(g).sayilar["uygulanmaz"] == 1
    uzun = "Deneme " * 60
    assert "metin" in kalan(bozulmus(g, lambda s: s[0].update(data_version=uzun)), "G-NOR")


def test_qa_kapi_kalirsa_cikis_1_rapor_kaldi(bk: RnkKoku, monkeypatch: pytest.MonkeyPatch) -> None:
    assert bk.zincir() == 0 and baski(bk) == 0
    veri = json.loads(bk.kilit_yolu.read_bytes())
    veri["kitaplar"]["tr_k/deneme"]["sayfa_sayisi"] += 1  # kilitle sayfa sayisi farkli
    bk.kilit_yolu.write_bytes((json.dumps(veri, ensure_ascii=True, indent=2) + "\n").encode())
    kod, cikti = baski_qa(bk)
    assert kod == 1, cikti
    assert "G-BUT kaldi" in cikti and cikti.isascii()
    rapor = json.loads(sorted((bk.veri_kok / "reports").glob("*.json"))[-1].read_bytes())
    assert rapor["kapilar"]["G-BUT"] == "kaldi" and rapor["cikis_kodu"] == 1
