"""Kur'an ici baglantilar: gercek veritabani denetimleri (A18.3); yalniz OKUR (SELECT).

Yerel `mutalaa` veritabaninda `export pg --source xref-baglantilar` kosulmussa calisir; veritabani
yoksa ya da baglantilar yuklenmemisse atlanir (`MUTALAA_DEGISMEZLIK_ZORUNLU=1` atlamayi hataya
cevirir). Test hicbir satir yazmaz; yalniz sayi ve kume farki sorgular, Arapca metin ciktiya girmez.
"""

import os
from collections.abc import Iterator

import psycopg
import pytest

from mutalaa_pipeline.config import Ayarlar
from mutalaa_pipeline.db import VeritabaniHatasi, baglan
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.qa.checks.xref import sql_hatalari


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
        satir = baglanti.execute(
            "SELECT count(*) FROM icerik.xref WHERE origin = 'hat'"
            " AND type IN ('kok', 'lemma', 'benzer_ayet')"
        ).fetchone()
        toplam = baglanti.execute("SELECT count(*) FROM icerik.quran_word").fetchone()
        if satir is None or satir[0] == 0 or toplam is None or toplam[0] != 77429:
            _yok("yerel veritabaninda baglantilar yok (export pg --source xref-baglantilar)")
        yield baglanti
    finally:
        baglanti.rollback()
        baglanti.close()


def say(conn: psycopg.Connection, sorgu: str) -> int:
    satir = conn.execute(sorgu).fetchone()  # type: ignore[call-overload]
    assert satir is not None
    return int(satir[0])


def test_sql_tutarlilik_ihlali_yok(conn: psycopg.Connection) -> None:
    """kok ve lemma tutarliligi %100, kayitsiz source_id 0, aday ozetleri guncel."""
    hatalar = sql_hatalari(conn)
    assert hatalar == dict.fromkeys(hatalar, 0)


def test_evidence_source_id_kayitli_kaynaktir(conn: psycopg.Connection) -> None:
    kaynaklar = {
        str(s): int(n)
        for s, n in conn.execute(
            "SELECT evidence ->> 'source_id', count(*) FROM icerik.xref WHERE origin = 'hat'"
            " AND type IN ('kok', 'lemma', 'benzer_ayet') GROUP BY 1"
        ).fetchall()
    }
    assert set(kaynaklar) <= {"qac-morfoloji", "tanzil-uthmani", "qursim"}
    assert (
        say(
            conn,
            "SELECT count(*) FROM icerik.xref x WHERE NOT EXISTS (SELECT 1 FROM icerik.source s"
            " WHERE s.slug = x.evidence ->> 'source_id')",
        )
        == 0
    )


@pytest.mark.parametrize(
    ("tur", "anahtar", "sutun"), [("kok", "root", "root_id"), ("lemma", "lemma", "lemma_id")]
)
def test_idf_degeri_ayet_sayisindan_yeniden_hesaplanir(
    conn: psycopg.Connection, tur: str, anahtar: str, sutun: str
) -> None:
    """Her `shared.idf`, ayri bir SQL df hesabindan `ln(6236/df)/ln(6236)` ile tutar ve >= 0,3."""
    sorgu = (
        f"WITH df AS (SELECT {sutun} AS kimlik, count(DISTINCT (surah, ayah)) AS n FROM"
        f" icerik.quran_word WHERE {sutun} IS NOT NULL GROUP BY 1), ortak AS (SELECT DISTINCT"
        f" (s ->> '{anahtar}')::int AS kimlik, (s ->> 'idf')::float8 AS idf FROM icerik.xref x"
        " CROSS JOIN LATERAL jsonb_array_elements(x.evidence -> 'shared') s"
        f" WHERE x.type = '{tur}')"
        " SELECT count(*) FROM ortak o LEFT JOIN df ON df.kimlik = o.kimlik WHERE df.n IS NULL"
        " OR abs(o.idf - ln(6236.0 / df.n) / ln(6236.0)) > 0.000001 OR o.idf < 0.3"
    )
    assert say(conn, sorgu) == 0
    assert say(conn, f"SELECT count(*) FROM icerik.xref WHERE type = '{tur}'") > 0


@pytest.mark.parametrize("tur", ["kok", "lemma"])
def test_birim_basina_en_cok_bes_komsu_ve_yaygin_kok_satir_uretmez(
    conn: psycopg.Connection, tur: str
) -> None:
    assert (
        say(
            conn,
            "SELECT count(*) FROM (SELECT src_anchor FROM icerik.xref WHERE type = '"
            + tur
            + "' GROUP BY src_anchor HAVING count(*) > 5) t",
        )
        == 0
    )
    assert (
        say(
            conn,
            f"SELECT count(*) FROM icerik.xref WHERE type = '{tur}' AND src_anchor = dst_anchor",
        )
        == 0
    )


def test_benzer_ayet_tek_satir_yon_ve_sabit_qursim_puani(conn: psycopg.Connection) -> None:
    assert (
        say(
            conn,
            "SELECT count(*) FROM icerik.xref a JOIN icerik.xref b ON b.type = a.type AND"
            " b.src_anchor = a.dst_anchor AND b.dst_anchor = a.src_anchor"
            " WHERE a.type = 'benzer_ayet'",
        )
        == 0
    )  # (A, B) ve (B, A) birlikte yok
    assert (
        say(
            conn,
            "SELECT count(*) FROM icerik.xref WHERE type = 'benzer_ayet'"
            " AND evidence ->> 'source_id' = 'qursim' AND (score <> 0.5 OR confidence <> 0.5"
            " OR evidence ->> 'subtype' <> 'alim')",
        )
        == 0
    )
    # QurSim ile kendi indeksimizin ortusen ciftleri isaretlidir (K-51 madde 10)
    assert (
        say(
            conn,
            "SELECT count(*) FROM icerik.xref WHERE type = 'benzer_ayet' AND evidence ? 'qursim'"
            " AND (evidence ->> 'subtype' <> 'sozluksel'"
            " OR evidence -> 'dongusel' <> 'true'::jsonb)",
        )
        == 0
    )
    assert (
        say(
            conn,
            "SELECT count(*) FROM icerik.xref WHERE type = 'benzer_ayet' AND evidence ->> 'subtype'"
            " = 'sozluksel' AND (evidence ->> 'matched_words')::int < 4",
        )
        == 0
    )
