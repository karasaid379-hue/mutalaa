"""Kelime katmani gercek veritabani denetimleri (A17.3, A17.5, A17.6): yalniz OKUR (SELECT).

Yerel `mutalaa` veritabaninda `export pg --source qac-morfoloji` (ve `quranwbw-tr`) yuklenmisse
kosar; veritabani yoksa ya da QAC henuz yuklenmemisse atlanir (`MUTALAA_DEGISMEZLIK_ZORUNLU=1`
atlamayi hataya cevirir). Test hicbir satir yazmaz ve yalniz sayi ve kume farki sorgular; Arapca
ya da Turkce metin ciktiya girmez.
"""

import os
from collections.abc import Iterator

import psycopg
import pytest
from test_qac_pg import SIRA_SQL

from mutalaa_pipeline.config import Ayarlar
from mutalaa_pipeline.db import VeritabaniHatasi, baglan
from mutalaa_pipeline.export.ortak import GirdiHatasi


def _yok(neden: str) -> None:
    if os.environ.get("MUTALAA_DEGISMEZLIK_ZORUNLU") == "1":
        pytest.fail(f"zorunlu gercek veri testi veri bulamadi: {neden}")
    pytest.skip(neden)


@pytest.fixture(scope="module")
def conn() -> Iterator[psycopg.Connection]:
    try:
        baglanti = baglan(Ayarlar())
    except (GirdiHatasi, VeritabaniHatasi) as hata:
        _yok(f"yerel veritabani yok: {hata}")
        return
    try:
        satir = baglanti.execute("SELECT count(*) FROM icerik.lemma WHERE lang = 'ar'").fetchone()
        if satir is None or satir[0] == 0:
            _yok("yerel veritabaninda QAC lemmasi yok (export pg --source qac-morfoloji)")
        yield baglanti
    finally:
        baglanti.rollback()
        baglanti.close()


def say(conn: psycopg.Connection, sorgu: str) -> int:
    satir = conn.execute(sorgu).fetchone()  # type: ignore[call-overload]
    assert satir is not None
    return int(satir[0])


def test_her_kelimenin_morfolojisi_var_ve_kimlikler_tutarli(conn: psycopg.Connection) -> None:
    assert say(conn, "SELECT count(*) FROM icerik.quran_word WHERE morph_source IS NULL") == 0
    assert (
        say(conn, "SELECT count(*) FROM icerik.quran_word WHERE morph_source <> 'qac-morfoloji'")
        == 0
    )
    # govde lemmasinin koku govde kokuyle ayni (lemma tek kokle gecer)
    assert (
        say(
            conn,
            "SELECT count(*) FROM icerik.quran_word w JOIN icerik.lemma l ON l.id = w.lemma_id"
            " WHERE w.root_id IS DISTINCT FROM l.root_id",
        )
        == 0
    )
    assert (
        say(conn, "SELECT count(*) FROM icerik.lemma WHERE lang = 'ar' AND status <> 'onayli'") == 0
    )
    assert (
        say(conn, "SELECT count(*) FROM icerik.lemma WHERE origin = 'qac' AND qac_ref IS NULL") == 0
    )


def test_lemma_dalga_sirasi_sql_ile_ayni(conn: psycopg.Connection) -> None:
    kayitli = [
        tuple(s)
        for s in conn.execute(
            "SELECT lemma_id, sira FROM icerik.lemma_dalga ORDER BY lemma_id"
        ).fetchall()
    ]
    beklenen = [tuple(s) for s in conn.execute(SIRA_SQL).fetchall()]  # type: ignore[call-overload]
    assert kayitli == beklenen
    assert len(kayitli) == say(conn, "SELECT count(*) FROM icerik.lemma WHERE lang = 'ar'")


def test_fatiha_ve_cuz30_lemmalari_dalga_0_ya_da_1(conn: psycopg.Connection) -> None:
    cuz = conn.execute(
        "SELECT anchor FROM icerik.quran_marker WHERE kind = 'cuz' AND no = 30"
    ).fetchone()
    if cuz is None:
        _yok("quran_marker'da 30. cuz yok (export pg --source tanzil-ust-veri)")
    _, sure, ayet = str(cuz[0]).split(":")
    sorgu = (
        "SELECT count(DISTINCT w.lemma_id) FROM icerik.quran_word w JOIN icerik.lemma_dalga d"
        " ON d.lemma_id = w.lemma_id WHERE (w.surah = 1 OR (w.surah, w.ayah) >= (%s, %s))"
        " AND d.dalga > 1"
    )
    satir = conn.execute(sorgu, (int(sure), int(ayet))).fetchone()
    assert satir is not None and satir[0] == 0


def test_lemma_gloss_adaylari_hazir_kaynaktan_yz_alani_bos_ve_review_i_var(
    conn: psycopg.Connection,
) -> None:
    toplam = say(conn, "SELECT count(*) FROM icerik.lemma_gloss")
    if toplam == 0:
        _yok("lemma_gloss yok (export pg --source quranwbw-tr)")
    kaynak = say(
        conn, "SELECT count(*) FROM icerik.lemma_gloss WHERE origin = 'kaynak:quranwbw-tr'"
    )
    assert kaynak > 0
    assert (
        say(
            conn,
            "SELECT count(*) FROM icerik.review WHERE hedef_tablo = 'lemma_gloss'"
            " AND (yz_modeli IS NOT NULL OR yz_kaydi IS NOT NULL)",
        )
        == 0
    )
    assert (
        say(
            conn,
            "SELECT count(*) FROM icerik.lemma_gloss g WHERE g.origin = 'kaynak:quranwbw-tr'"
            " AND NOT EXISTS (SELECT 1 FROM icerik.review r WHERE r.hedef_tablo = 'lemma_gloss'"
            " AND r.hedef_anahtar = g.lemma_id::text)",
        )
        == 0
    )
