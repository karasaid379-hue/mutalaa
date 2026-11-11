"""`qa sample`: tabakali ikinci okuma orneklemi ve G-INC olcumu (A16.7; SENTETIK veri).

Hesap testleri veritabanisiz; veritabani testleri `mutalaa_test` uzerinde (dis islem, geri alinir)
sentetik meal zinciriyle kosar. Raporlar meal metni icermez.
"""

import json
import math
from itertools import pairwise
from pathlib import Path

import psycopg
import pytest
from meal_yardimci import MealKoku
from test_pg_meal import conn, kopya, yukle  # noqa: F401  (fikstur ve yardimci)

from mutalaa_pipeline.anchor import parse
from mutalaa_pipeline.anchor.ayet_sayilari import AYET_SAYILARI
from mutalaa_pipeline.qa import ornekleme as o

ORIJINAL = "elmalili-meal"
SADE = "elmalili-sade-meal"


def _evren() -> list[tuple[str, int]]:
    return [
        (f"meal:elmalili-sade:{s}:{a}", s)
        for s in range(1, 115)
        for a in range(1, AYET_SAYILARI[s - 1] + 1)
    ]


# --- hesap -------------------------------------------------------------------------------------


def test_sure_gruplari_ardisik_ve_dengeli() -> None:
    gruplar = o.sure_gruplari()
    assert len(gruplar) == o.GRUP_SAYISI
    assert gruplar[0][0] == 1 and gruplar[-1][1] == 114
    for (_, son), (ilk, _) in pairwise(gruplar):
        assert ilk == son + 1
    adetler = [sum(AYET_SAYILARI[s - 1] for s in range(i, j + 1)) for i, j in gruplar]
    assert sum(adetler) == 6236
    assert max(adetler) - min(adetler) < 6236 // o.GRUP_SAYISI // 2  # yaklasik esit buyuklukte


def test_orantili_dagitim_toplami_tam_n() -> None:
    assert o.orantili_dagit([10, 20, 30], 6) == [1, 2, 3]
    assert sum(o.orantili_dagit([7, 11, 13, 17], 10)) == 10
    assert o.orantili_dagit([1, 1, 1], 2) == [1, 1, 0]  # esit kalanlarda kucuk indeks
    assert o.orantili_dagit([5, 0, 5], 4) == [2, 0, 2]


def test_tohum_yeniden_uretilebilir_ve_tabaka_dagilimi() -> None:
    evren = _evren()
    g1, d1, c1 = o.ornekle(evren, 600, 20261111)
    g2, d2, c2 = o.ornekle(evren, 600, 20261111)
    assert (g1, d1, c1) == (g2, d2, c2)  # ayni tohum, ayni liste
    assert len(c1) == len(set(c1)) == 600
    assert c1 != o.ornekle(evren, 600, 1)[2]  # baska tohum, baska liste
    sure_of = dict(evren)
    for (ilk, son), hedef in zip(g1, d1, strict=True):
        secilen = sum(1 for c in c1 if ilk <= sure_of[c] <= son)
        assert secilen == hedef
        grup_evreni = sum(1 for _, s in evren if ilk <= s <= son)
        assert abs(hedef - 600 * grup_evreni / len(evren)) < 1  # orantili
    sira = [parse(c).anchor for c in c1]
    assert [(a.sure, a.ayet) for a in sira] == sorted((a.sure, a.ayet) for a in sira)  # type: ignore[attr-defined]


def test_ornek_buyuklugu_siniri() -> None:
    evren = _evren()
    for bozuk in (0, -1, len(evren) + 1):
        with pytest.raises(o.GirdiHatasi):
            o.ornekle(evren, bozuk, 1)
    assert len(o.ornekle(evren, len(evren), 1)[2]) == len(evren)


def test_clopper_pearson_bilinen_degerler() -> None:
    # hata yok: kapali bicim 1 - 0,05^(1/n)
    for n in (100, 600, 1000):
        assert o.clopper_pearson_ust(0, n) == pytest.approx(1 - 0.05 ** (1 / n), abs=1e-9)
    assert o.clopper_pearson_ust(0, 600) == pytest.approx(0.0049804, abs=1e-7)
    assert o.clopper_pearson_ust(0, 600) < o.ESIK_ORAN  # n = 600 ve 0 hata esigi gecer
    assert o.clopper_pearson_ust(5, 5) == 1.0
    # tanim: P(X <= k | n, p_ust) = 0,05
    for k, n in ((1, 100), (1, 600), (3, 600), (10, 1000)):
        p = o.clopper_pearson_ust(k, n)
        assert o._iki_terimli_cdf(k, n, p) == pytest.approx(0.05, abs=1e-9)
        assert p > k / n
    assert 0.0465 < o.clopper_pearson_ust(1, 100) < 0.0474  # Poisson siniri 4,744 / 100
    assert o.clopper_pearson_ust(1, 600) > o.ESIK_ORAN  # tek hata 600'de esigi gecirir
    assert o.clopper_pearson_ust(0, 599) > o.clopper_pearson_ust(0, 600)  # n arttikca azalir
    for bozuk in ((0, 0), (-1, 5), (6, 5)):
        with pytest.raises(o.GirdiHatasi):
            o.clopper_pearson_ust(*bozuk)


def test_iki_terimli_cdf_tasmaz() -> None:
    assert o._iki_terimli_cdf(0, 5000, 0.5) == pytest.approx(0.0, abs=1e-300)
    assert o._iki_terimli_cdf(5000, 5000, 0.3) == pytest.approx(1.0)
    assert math.isfinite(o._iki_terimli_cdf(2, 5000, 0.001))


def test_g_inc_kapisi_bilinen_degerlerle() -> None:
    tamam = {"tamami_onayli": True}
    eksik = {"tamami_onayli": False}
    assert o.g_inc(tamam, 600, 0)["kapi"] == "gecti"
    assert o.g_inc(tamam, 600, 1)["kapi"] == "kaldi"
    assert o.g_inc(tamam, 599, 0)["kapi"] == "kaldi"  # en az 600 okunmali
    assert o.g_inc(tamam, 1200, 3)["kapi"] == "kaldi"  # ust sinir ~%0,64
    assert o.g_inc(eksik, 600, 0)["kapi"] == "kaldi"  # tum birimler onayli degil
    assert o.g_inc(tamam, None, None)["kapi"] == "kaldi"
    tur2 = o.g_inc(tamam, 600, 0)["tur2"]
    assert isinstance(tur2, dict)
    assert tur2["yontem"].startswith("Clopper-Pearson") and tur2["ust_sinir_95"] == 0.00498  # type: ignore[union-attr]


def test_sablondan_say(tmp_path: Path) -> None:
    yol = tmp_path / "s.jsonl"
    satirlar = [
        {"capa": "meal:elmalili:1:1", "karar": "dogru", "not": None},
        {"capa": "meal:elmalili:1:2", "karar": "hata", "not": None},
        {"capa": "meal:elmalili:1:3", "karar": None, "not": None},
    ]
    yol.write_text("".join(json.dumps(s) + "\n" for s in satirlar), encoding="utf-8")
    assert o.sablondan_say(yol) == (2, 1)
    yol.write_text('{"capa": "a", "karar": "belki"}\n', encoding="utf-8")
    with pytest.raises(o.GirdiHatasi):
        o.sablondan_say(yol)
    yol.write_text('{"capa": "a"}\n{"capa": "a"}\n', encoding="utf-8")
    with pytest.raises(o.GirdiHatasi):
        o.sablondan_say(yol)


# --- komut ve veritabani -----------------------------------------------------------------------


def _komut(conn_: psycopg.Connection, kaynak: str, **kw: object) -> int:
    varsayilan: dict[str, object] = {
        "source": kaynak,
        "n": 600,
        "seed": 20261111,
        "dry_run": False,
        "yalniz_onayli": False,
        "okunan": None,
        "hatali": None,
        "sablon": None,
        "config": None,
        "kok": None,
    }
    varsayilan.update(kw)
    return o.komut_qa_sample(baglanti=lambda: conn_, **varsayilan)  # type: ignore[arg-type]


def _rapor(veri: Path) -> tuple[dict[str, object], Path]:
    dosyalar = sorted(veri.glob("reports/*-qa-sample.json"))
    assert dosyalar
    return json.loads(dosyalar[-1].read_bytes()), dosyalar[-1]


@pytest.mark.veritabani
def test_kimlik_reddi_cikis_2(kopya: MealKoku, conn: psycopg.Connection) -> None:  # noqa: F811
    for kimlik in ("elmalili-meal-epub", "tanzil-uthmani", "baska"):
        assert _komut(conn, kimlik) == 2
    assert not list(kopya.veri.glob("reports/*-qa-sample.json"))
    assert _komut(conn, SADE, n=0) == 2  # evren bos: kaynak yuklenmemis
    assert _komut(conn, SADE, okunan=10) == 2  # --okunan tek basina
    assert _komut(conn, SADE, okunan=10, hatali=11) == 2


@pytest.mark.veritabani
def test_dry_run_dosya_yazmaz_ve_normal_kosu_iki_dosya_yazar(
    tmp_path: Path,
    kopya: MealKoku,  # noqa: F811
    conn: psycopg.Connection,  # noqa: F811
) -> None:
    assert yukle(tmp_path, conn, SADE) == 0
    assert _komut(conn, SADE, dry_run=True) == 0
    assert not list(kopya.veri.glob("reports/*-qa-sample.json"))
    assert not list(kopya.veri.glob("reports/*-ikinci-okuma.jsonl"))
    assert _komut(conn, SADE) == 0
    rapor, _ = _rapor(kopya.veri)
    sablon = sorted(kopya.veri.glob("reports/*-ikinci-okuma.jsonl"))[-1]
    satirlar = [json.loads(s) for s in sablon.read_text(encoding="utf-8").splitlines()]
    assert len(satirlar) == 600 == rapor["n"]
    assert all(set(s) == {"capa", "karar", "not"} and s["karar"] is None for s in satirlar)
    assert [s["capa"] for s in satirlar] == rapor["capalar"]


@pytest.mark.veritabani
def test_seed_ayni_liste_ve_rapor_metin_icermez(
    tmp_path: Path,
    kopya: MealKoku,  # noqa: F811
    conn: psycopg.Connection,  # noqa: F811
) -> None:
    assert yukle(tmp_path, conn, SADE) == 0
    assert _komut(conn, SADE, seed=7) == 0
    ilk, _ = _rapor(kopya.veri)
    assert _komut(conn, SADE, seed=7) == 0
    ikinci, _ = _rapor(kopya.veri)
    assert ilk["capalar"] == ikinci["capalar"] and ilk["capalar_sha256"] == ikinci["capalar_sha256"]
    assert _komut(conn, SADE, seed=8) == 0
    assert _rapor(kopya.veri)[0]["capalar"] != ilk["capalar"]
    for dosya in kopya.veri.glob("reports/*-qa-sample.json"):
        ham = dosya.read_text(encoding="utf-8")
        assert "Deneme" not in ham and "sade parça" not in ham
    toplam = sum(g["secilen"] for g in ilk["gruplar"])  # type: ignore[index]
    assert toplam == 600
    assert all(g["secilen"] == g["hedef"] for g in ilk["gruplar"])  # type: ignore[index]
    assert ilk["evren"] == 6236 and ilk["cilt_tabakasi"] == "S-15"


@pytest.mark.veritabani
def test_evren_birlesik_izleyeni_icermez(
    tmp_path: Path,
    kopya: MealKoku,  # noqa: F811
    conn: psycopg.Connection,  # noqa: F811
) -> None:
    assert yukle(tmp_path, conn, ORIJINAL) == 0
    assert _komut(conn, ORIJINAL, n=6234) == 0  # evrenin tamami: 6236 - 2 izleyen
    rapor, _ = _rapor(kopya.veri)
    assert rapor["evren"] == 6234
    assert "meal:elmalili:3:11" not in rapor["capalar"]  # type: ignore[operator]
    assert "meal:elmalili:3:10" in rapor["capalar"]  # type: ignore[operator]
    assert _komut(conn, ORIJINAL, n=6235) == 2  # evrenden buyuk


@pytest.mark.veritabani
def test_g_inc_veritabani_olcumu_ve_kapi(
    tmp_path: Path,
    kopya: MealKoku,  # noqa: F811
    conn: psycopg.Connection,  # noqa: F811
) -> None:
    assert yukle(tmp_path, conn, ORIJINAL) == 0
    assert _komut(conn, ORIJINAL, okunan=600, hatali=0) == 0
    db = _rapor(kopya.veri)[0]["veritabani"]
    assert db["birim"] == 6236 and db["birlesik_izleyen"] == 2  # type: ignore[index]
    assert db["durum_dagilimi"] == {"taslak": 6236} and db["onayli"] == 0  # type: ignore[index]
    assert (db["acik_hat_inceleme"], db["acik_inceleme"]) == (6236, 6236)  # type: ignore[index]
    assert db["ikinci_onayli"] == 0 and db["tamami_onayli"] is False  # type: ignore[index]
    gi = _rapor(kopya.veri)[0]["g_inc"]
    assert gi["kapi"] == "kaldi" and gi["tur2"]["gecti"] is True  # type: ignore[index]  # onay eksik
    # hepsi onayli + bir ikinci onay
    conn.execute("UPDATE icerik.unit SET metin_durumu = 'onayli' WHERE source_id = %s", (ORIJINAL,))
    conn.execute(
        "UPDATE icerik.review SET durum = 'onaylandi', inceleyen = 'e1', ikinci_inceleyen = 'e2'"
        " WHERE hedef_anahtar = 'meal:elmalili:2:2'"
    )
    cases = [(600, 0, "gecti"), (600, 1, "kaldi"), (599, 0, "kaldi"), (2000, 4, "gecti")]
    for okunan, hatali, beklenen in cases:
        assert _komut(conn, ORIJINAL, okunan=okunan, hatali=hatali) == 0  # cikis kodu etkilenmez
        rapor, _ = _rapor(kopya.veri)
        assert rapor["g_inc"]["kapi"] == beklenen, (okunan, hatali)  # type: ignore[index]
    db = rapor["veritabani"]
    assert (db["onayli"], db["ikinci_onayli"], db["tamami_onayli"]) == (6236, 1, True)  # type: ignore[index]
    assert db["acik_hat_inceleme"] == 6235  # type: ignore[index]
    # n ve hata sayisi sablondan
    sablon = sorted(kopya.veri.glob("reports/*-ikinci-okuma.jsonl"))[-1]
    satirlar = [json.loads(s) for s in sablon.read_text(encoding="utf-8").splitlines()]
    for s in satirlar:
        s["karar"] = "dogru"
    yeni = tmp_path / "doldurulmus.jsonl"
    yeni.write_text("".join(json.dumps(s) + "\n" for s in satirlar), encoding="utf-8")
    assert _komut(conn, ORIJINAL, sablon=yeni) == 0
    tur2 = _rapor(kopya.veri)[0]["g_inc"]["tur2"]  # type: ignore[index]
    assert (tur2["okunan"], tur2["hatali"], tur2["gecti"]) == (600, 0, True)  # type: ignore[index]
    assert _komut(conn, ORIJINAL, sablon=yeni, okunan=1, hatali=0) == 2  # ikisi birlikte verilmez


@pytest.mark.veritabani
def test_komut_yalniz_okur(
    tmp_path: Path,
    kopya: MealKoku,  # noqa: F811
    conn: psycopg.Connection,  # noqa: F811
) -> None:
    assert yukle(tmp_path, conn, SADE) == 0
    once = conn.execute(
        "SELECT (SELECT count(*) FROM icerik.unit), (SELECT count(*) FROM icerik.review),"
        " (SELECT count(*) FROM icerik.pipeline_run), (SELECT count(*) FROM icerik.source)"
    ).fetchone()
    assert _komut(conn, SADE) == 0
    sonra = conn.execute(
        "SELECT (SELECT count(*) FROM icerik.unit), (SELECT count(*) FROM icerik.review),"
        " (SELECT count(*) FROM icerik.pipeline_run), (SELECT count(*) FROM icerik.source)"
    ).fetchone()
    assert once == sonra
