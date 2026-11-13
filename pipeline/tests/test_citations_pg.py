"""`enrich citations`, `qa run` ve `export pg --source xref-atif-iktibas` (A18.4): SENTETIK dunya.

`citations_yardimci.CitDunyasi` `mutalaa_test` veritabanina yuklenir: kaynak, ayet ve meal birimleri
ve kelimeler testte SQL ile kurulur. Testler dis islem icinde kosar ve sonunda geri alinir.
Veritabani yoksa atlanir (`MUTALAA_DEGISMEZLIK_ZORUNLU=1` atlamayi hataya cevirir). Hicbir Kur'an,
meal ya da sure adi metni hafizadan yazilmaz.
"""

import os
from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest
from citations_yardimci import (
    AYET_TOKENLERI,
    KAYNAK,
    MEAL_O,
    MEAL_S,
    SIMPLE,
    UTHMANI,
    CitDunyasi,
    ayet_ozeti,
    dunya_kur,
    paragraf,
    tohumla,
)
from links_yardimci import sozcuk

from mutalaa_pipeline.anchor import content_hash
from mutalaa_pipeline.config import Ayarlar
from mutalaa_pipeline.db import baglan
from mutalaa_pipeline.enrich.citations import girdi as cit_girdi
from mutalaa_pipeline.enrich.citations.kalip import veritabanindan_oku
from mutalaa_pipeline.enrich.citations.normalizasyon import anahtar_dizisi
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.normalize import normalize_tr
from mutalaa_pipeline.qa.checks.xref_atif import sql_hatalari

SLUGLAR = [UTHMANI, MEAL_O, MEAL_S]
KALIP_METNI = " ".join(sozcuk(i) for i in range(140, 146))


def ar(capa: str, bas: int = 0, son: int | None = None) -> str:
    return " ".join(AYET_TOKENLERI[capa][bas:son])


def mealler() -> dict[str, list[tuple[str, str]]]:
    return {
        MEAL_O: [
            (
                "meal:elmalili:2:1",
                paragraf(ar("q:2:1"), "Deneme (2:1)"),
            ),  # iktibas + atif (tutarli)
            ("meal:elmalili:2:2", paragraf(ar("q:2:2", 0, 5), "Deneme sonu.")),  # yalniz iktibas
            (
                "meal:elmalili:2:3",
                "Deneme paragrafi 3 (2:3-4) Arapca yok.",
            ),  # yalniz atif (2 satir)
        ],
        MEAL_S: [
            ("meal:elmalili-sade:2:1", paragraf(ar("q:2:3", 2, 9), "Deneme (2:5)")),  # tutarsiz
            ("meal:elmalili-sade:2:2", "Deneme paragrafi 4 hicbir sey yok."),
        ],
    }


def _yok(neden: str) -> None:
    if os.environ.get("MUTALAA_DEGISMEZLIK_ZORUNLU") == "1":
        pytest.fail(neden)
    pytest.skip(neden)


@pytest.fixture
def conn() -> Iterator[psycopg.Connection]:
    """Test veritabanina baglanir (dis islem, sonunda geri alinir); kalinti varsa atlar."""
    try:
        baglanti = baglan(Ayarlar(), test=True)
    except GirdiHatasi as hata:
        _yok(f"test veritabani yok: {hata}")
        return
    try:
        kalinti = baglanti.execute(
            "SELECT (SELECT count(*) FROM icerik.quran_word) + (SELECT count(*) FROM icerik.xref)"
            " + (SELECT count(*) FROM icerik.unit WHERE kind IN ('ayet', 'meal'))"
            " + (SELECT count(*) FROM icerik.review WHERE hedef_tablo IN ('xref', 'unit'))"
            " + (SELECT count(*) FROM icerik.surah_alias)"
            " + (SELECT count(*) FROM icerik.tr_form)"
            " + (SELECT count(*) FROM icerik.source WHERE slug = ANY(%s))",
            (SLUGLAR,),
        ).fetchone()
        assert kalinti is not None
        if kalinti[0] != 0:
            baglanti.rollback()
            _yok("mutalaa_test icinde quran_word/xref/ayet/meal/alias satiri kalmis")
        yield baglanti
    finally:
        baglanti.rollback()
        baglanti.close()


@pytest.fixture
def d(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, conn: psycopg.Connection) -> CitDunyasi:
    tohumla(conn, mealler())
    return dunya_kur(tmp_path, monkeypatch, conn)


def say(conn: psycopg.Connection, sorgu: str, *param: object) -> int:
    satir = conn.execute(sorgu, param).fetchone()  # type: ignore[arg-type]
    assert satir is not None
    return int(satir[0])


def goruntu(conn: psycopg.Connection) -> dict[str, list[tuple[object, ...]]]:
    return {
        "xref": [
            tuple(s)
            for s in conn.execute(
                "SELECT * FROM icerik.xref ORDER BY src_anchor, dst_anchor, id"
            ).fetchall()
        ],
        "review": [
            tuple(s) for s in conn.execute("SELECT * FROM icerik.review ORDER BY id").fetchall()
        ],
        "unit": [
            tuple(s)
            for s in conn.execute(
                "SELECT anchor, metin, content_hash, rev FROM icerik.unit ORDER BY anchor"
            ).fetchall()
        ],
    }


def xref_satirlari(conn: psycopg.Connection, tur: str | None = None) -> list[tuple[object, ...]]:
    kosul = "" if tur is None else f" WHERE type = '{tur}'"
    return [
        tuple(s)
        for s in conn.execute(
            "SELECT src_anchor, lower(src_span), upper(src_span), dst_anchor, lower(dst_span),"
            " upper(dst_span), confidence, status::text FROM icerik.xref"
            + kosul
            + " ORDER BY src_anchor, lower(src_span), dst_anchor"
        ).fetchall()
    ]


# --- ilk yukleme -----------------------------------------------------------------------------


def test_ilk_yukleme_satirlar_ve_review(d: CitDunyasi, conn: psycopg.Connection) -> None:
    assert d.hepsi() == 0
    assert say(conn, "SELECT count(*) FROM icerik.xref WHERE type = 'iktibas'") == 3
    assert say(conn, "SELECT count(*) FROM icerik.xref WHERE type = 'atif'") == 4  # 1 + 2 + 1
    satirlar = {(s[0], s[3]): s for s in xref_satirlari(conn)}
    # meal:elmalili:2:1: iktibas q:2:1 (tam) ve atif (2:1)
    assert ("meal:elmalili:2:1", "q:2:1") in satirlar
    assert (
        say(conn, "SELECT count(*) FROM icerik.xref WHERE origin = 'hat' AND status = 'aday'") == 7
    )
    # her aday icin tek review (hedef xref, alan status, eylem oner, koken hat)
    assert say(conn, "SELECT count(*) FROM icerik.review WHERE hedef_tablo = 'xref'") == 7
    r = conn.execute(
        "SELECT r.hedef_tablo, r.hedef_anahtar, r.xref_id, r.alan, r.eylem, r.durum::text,"
        " r.koken::text, r.oneren, r.guven, r.onerilen, x.id::text, x.confidence"
        " FROM icerik.review r JOIN icerik.xref x ON x.id = r.xref_id"
    ).fetchall()
    assert len(r) == 7
    for tablo, anahtar, xid, alan, eylem, durum, koken, oneren, guven, onerilen, xtext, conf in r:
        assert (tablo, alan, eylem, durum, koken, oneren) == (
            "xref",
            "status",
            "oner",
            "acik",
            "hat",
            "hat",
        )
        assert anahtar == xtext and str(xid) == xtext
        assert guven == conf
        assert set(onerilen) == {"score", "confidence", "sinif_ipucu"}
        assert onerilen["sinif_ipucu"] in {"tutarsiz", "toplu", "gri", "diger"}
    s = d.yukleme_sayilari()
    assert s["xref_eklenen"] == 7 and s["review_aday_acilan"] == 7 and s["xref_silinen"] == 0


def test_yuklenen_satir_aralik_ve_kanit_alanlari(d: CitDunyasi, conn: psycopg.Connection) -> None:
    assert d.hepsi() == 0
    metin = conn.execute(
        "SELECT metin FROM icerik.unit WHERE anchor = 'meal:elmalili:2:1'"
    ).fetchone()
    assert metin is not None
    satir = conn.execute(
        "SELECT lower(src_span), upper(src_span), lower(dst_span), upper(dst_span), score,"
        " confidence, evidence, data_version, origin::text, status::text FROM icerik.xref"
        " WHERE type = 'iktibas' AND src_anchor = 'meal:elmalili:2:1'"
    ).fetchone()
    assert satir is not None
    bas, son, ilk, son1, skor, guven, kanit, surum, origin, durum = satir
    assert metin[0][bas:son] == ar("q:2:1")  # kod noktasi, yari acik, kanonik metin
    assert (ilk, son1) == (1, 11) and (origin, durum) == ("hat", "aday")
    assert surum.startswith("citations@1/tanzil-uthmani@1.1/tanzil-simple-clean@1.1")
    # kanit: sayilar JSON sayisi (dizge degil), hash ilk 16 hane
    tipler = conn.execute(
        "SELECT jsonb_typeof(evidence -> 'coverage'), jsonb_typeof(evidence -> 'identity'),"
        " jsonb_typeof(evidence -> 'matched_words'), jsonb_typeof(evidence -> 'src_span'),"
        " evidence ->> 'dst_hash', evidence ->> 'index' FROM icerik.xref WHERE type = 'iktibas'"
        " AND src_anchor = 'meal:elmalili:2:1'"
    ).fetchone()
    assert tipler is not None
    assert tuple(tipler[:4]) == ("number", "number", "number", "array")
    assert tipler[4] == ayet_ozeti("q:2:1") and tipler[5] == "uthmani"
    assert kanit["phrase_freq"] == 1 and kanit["consistent_quote"] is True
    assert skor == pytest.approx(1.0) and guven == pytest.approx(0.99)  # tutarli acik atif
    atif = conn.execute(
        "SELECT lower(src_span), upper(src_span), dst_span, score, confidence, evidence"
        " FROM icerik.xref WHERE type = 'atif' AND src_anchor = 'meal:elmalili:2:1'"
    ).fetchone()
    assert atif is not None and atif[2] is None and metin[0][atif[0] : atif[1]] == "(2:1)"
    assert atif[3] == 1.0 and atif[4] == pytest.approx(0.99) and atif[5]["consistent_quote"] is True


def test_ikili_atif_grubu_ve_tutarsiz_satirlar(d: CitDunyasi, conn: psycopg.Connection) -> None:
    assert d.hepsi() == 0
    grup = conn.execute(
        "SELECT dst_anchor, evidence ->> 'group', confidence FROM icerik.xref WHERE type = 'atif'"
        " AND src_anchor = 'meal:elmalili:2:3' ORDER BY dst_anchor"
    ).fetchall()
    assert [g[0] for g in grup] == ["q:2:3", "q:2:4"] and grup[0][1] == grup[1][1] is not None
    tutarsiz = conn.execute(
        "SELECT type::text, confidence, evidence -> 'consistent_quote' FROM icerik.xref"
        " WHERE src_anchor = 'meal:elmalili-sade:2:1' ORDER BY type"
    ).fetchall()
    assert [(t, round(c, 2), cq) for t, c, cq in tutarsiz] == [
        ("atif", 0.3, False),
        ("iktibas", 0.3, False),
    ]


def test_source_satiri_yazilmaz(d: CitDunyasi, conn: psycopg.Connection) -> None:
    once = say(conn, "SELECT count(*) FROM icerik.source")
    assert d.hepsi() == 0
    assert say(conn, "SELECT count(*) FROM icerik.source") == once
    assert say(conn, "SELECT count(*) FROM icerik.source WHERE slug = %s", SIMPLE) == 0


def test_hat_meal_metnine_yazmaz(d: CitDunyasi, conn: psycopg.Connection) -> None:
    once = goruntu(conn)["unit"]
    assert d.hepsi() == 0
    assert goruntu(conn)["unit"] == once


# --- idempotentlik -----------------------------------------------------------------------------


def test_ikinci_yukleme_sifir_degisiklik(d: CitDunyasi, conn: psycopg.Connection) -> None:
    assert d.hepsi() == 0
    ilk = goruntu(conn)
    assert d.hepsi() == 0  # yeni enrich calismasi, ayni girdi
    s = d.yukleme_sayilari()
    for ad in (
        "xref_eklenen",
        "xref_guncellenen",
        "xref_silinen",
        "review_aday_acilan",
        "review_aday_silinen",
        "review_uretilmedi_acilan",
        "review_uc_metni_degisti_acilan",
    ):
        assert s[ad] == 0, ad
    assert s["xref_degismeyen"] == 7
    assert goruntu(conn) == ilk


def test_dry_run_hicbir_sey_yazmaz(d: CitDunyasi, conn: psycopg.Connection) -> None:
    assert d.enrich() == 0 and d.qa() == 0
    once = goruntu(conn)
    assert d.yukle(dry_run=True) == 0
    assert goruntu(conn) == once
    assert say(conn, "SELECT count(*) FROM icerik.xref") == 0


def test_enrich_dry_run_dosya_yazmaz(d: CitDunyasi) -> None:
    assert d.enrich(dry_run=True) == 0
    assert not (d.veri / "staged" / KAYNAK).exists()


# --- onayli, red ve editor satirlarina dokunulmaz ---------------------------------------------


def test_onayli_satira_dokunulmaz_ve_yeniden_dogrulama_acilir(
    d: CitDunyasi, conn: psycopg.Connection
) -> None:
    assert d.hepsi() == 0
    xid = conn.execute(
        "SELECT id FROM icerik.xref WHERE type = 'iktibas' AND src_anchor = 'meal:elmalili:2:2'"
    ).fetchone()
    assert xid is not None
    conn.execute("UPDATE icerik.xref SET status = 'onayli' WHERE id = %s", (xid[0],))
    conn.execute("UPDATE icerik.review SET durum = 'onaylandi' WHERE xref_id = %s", (xid[0],))
    # metin degisti ama ozet ayni (test SQL'i): Arapca dizi yok, satir artik uretilmiyor
    conn.execute(
        "UPDATE icerik.unit SET metin = 'Deneme paragrafi 2 Arapca kalmadi' WHERE anchor = %s",
        ("meal:elmalili:2:2",),
    )
    once = tuple(conn.execute("SELECT * FROM icerik.xref WHERE id = %s", (xid[0],)).fetchone())  # type: ignore[arg-type]
    assert d.hepsi() == 0
    simdi = tuple(conn.execute("SELECT * FROM icerik.xref WHERE id = %s", (xid[0],)).fetchone())  # type: ignore[arg-type]
    assert simdi == once  # onayli satir silinmez ve guncellenmez
    r = conn.execute(
        "SELECT hedef_tablo, alan, eylem, koken::text, oneren, onerilen, durum::text"
        " FROM icerik.review"
        " WHERE xref_id = %s AND onerilen ? 'yeniden_dogrula'",
        (xid[0],),
    ).fetchall()
    assert len(r) == 1
    assert tuple(r[0][:5]) == ("xref", "status", "oner", "hat", "hat")
    assert r[0][5] == {"yeniden_dogrula": True, "neden": "uretilmedi"} and r[0][6] == "acik"
    s = d.yukleme_sayilari()
    assert s["review_uretilmedi_acilan"] == 1 and s["xref_korunan_onayli"] == 0
    # ucuncu kosu: acik kayit var, ikinci acilmaz
    assert d.hepsi() == 0
    assert d.yukleme_sayilari()["review_uretilmedi_acilan"] == 0
    assert d.yukleme_sayilari()["review_zaten_acik"] == 1


def test_uc_metni_degisince_neden_uc_metni_degisti(d: CitDunyasi, conn: psycopg.Connection) -> None:
    assert d.hepsi() == 0
    xid = conn.execute(
        "SELECT id FROM icerik.xref WHERE type = 'iktibas' AND src_anchor = 'meal:elmalili:2:2'"
    ).fetchone()
    assert xid is not None
    conn.execute("UPDATE icerik.xref SET status = 'onayli' WHERE id = %s", (xid[0],))
    conn.execute("UPDATE icerik.review SET durum = 'onaylandi' WHERE xref_id = %s", (xid[0],))
    # hedef ayetin ozeti degisti (duzeltme): staged ozet de guncel, onayli satirin ozeti eski
    conn.execute("UPDATE icerik.unit SET content_hash = repeat('a', 64) WHERE anchor = 'q:2:2'")
    assert d.hepsi() == 0
    n = conn.execute(
        "SELECT onerilen ->> 'neden' FROM icerik.review WHERE xref_id = %s"
        " AND onerilen ? 'yeniden_dogrula'",
        (xid[0],),
    ).fetchall()
    assert [x[0] for x in n] == ["uc_metni_degisti"]
    assert d.yukleme_sayilari()["review_uc_metni_degisti_acilan"] == 1
    # satir hala onayli ve ozeti eski; yeni (ayni dogal anahtarli) aday acilmadi: dokunulmayan
    assert (
        say(conn, "SELECT count(*) FROM icerik.xref WHERE id = %s AND status = 'onayli'", xid[0])
        == 1
    )


def test_red_ve_editor_satirlarina_dokunulmaz(d: CitDunyasi, conn: psycopg.Connection) -> None:
    assert d.enrich() == 0 and d.qa() == 0
    satirlar = d.satirlar()
    iktibas = next(s for s in satirlar if s["type"] == "iktibas")
    sp, dp = iktibas["src_span"], iktibas["dst_span"]
    # ayni dogal anahtarli editor satiri ve red satiri (once tohumlanir)
    conn.execute(
        "INSERT INTO icerik.xref (src_anchor, src_span, dst_anchor, dst_span, type, score,"
        " confidence, evidence, origin, status, data_version) VALUES (%s, int4range(%s, %s),"
        " %s, int4range(%s, %s), 'iktibas', 0.5, 0.5, '{}'::jsonb, 'editor', 'onayli', 'x')",
        (iktibas["src_anchor"], sp[0], sp[1], iktibas["dst_anchor"], dp[0], dp[1]),
    )
    red = next(s for s in satirlar if s["type"] == "atif")
    conn.execute(
        "INSERT INTO icerik.xref (src_anchor, src_span, dst_anchor, dst_span, type, score,"
        " confidence, evidence, origin, status, data_version) VALUES (%s, int4range(%s, %s),"
        " %s, NULL, 'atif', 1, 0.9, %s::jsonb, 'hat', 'red', 'x')",
        (
            red["src_anchor"],
            red["src_span"][0],
            red["src_span"][1],
            red["dst_anchor"],
            '{"source_id": "tanzil-uthmani"}',
        ),
    )
    once = goruntu(conn)["xref"]
    assert d.yukle() == 0
    s = d.yukleme_sayilari()
    assert s["xref_korunan_red"] == 1 and s["xref_korunan_editor_ve_diger"] == 1
    sonra = goruntu(conn)["xref"]
    assert [x for x in sonra if "editor" in x or "red" in x] == [
        x for x in once if "editor" in x or "red" in x
    ]
    assert say(conn, "SELECT count(*) FROM icerik.xref WHERE origin = 'editor'") == 1
    assert say(conn, "SELECT count(*) FROM icerik.xref WHERE status = 'red'") == 1
    # editor ve red satirlari icin review acilmadi; kalan 5 yeni aday icin acildi
    assert say(conn, "SELECT count(*) FROM icerik.review WHERE hedef_tablo = 'xref'") == 5


# --- uretilmeyen aday silinir (kapsam: tur ve hedef kumesi) -------------------------------------


def test_uretilmeyen_aday_ve_acik_review_silinir(d: CitDunyasi, conn: psycopg.Connection) -> None:
    assert d.hepsi() == 0
    conn.execute(
        "UPDATE icerik.unit SET metin = 'Deneme paragrafi 2 Arapca kalmadi' WHERE anchor = %s",
        ("meal:elmalili:2:2",),
    )
    assert d.hepsi() == 0
    s = d.yukleme_sayilari()
    assert s["xref_silinen"] == 1 and s["review_aday_silinen"] == 1
    assert say(conn, "SELECT count(*) FROM icerik.xref WHERE src_anchor = 'meal:elmalili:2:2'") == 0
    assert say(conn, "SELECT count(*) FROM icerik.xref") == 6
    assert say(conn, "SELECT count(*) FROM icerik.review WHERE hedef_tablo = 'xref'") == 6


def test_baska_hedefteki_satir_silinmez(d: CitDunyasi, conn: psycopg.Connection) -> None:
    assert d.hepsi() == 0  # her iki meal
    assert d.enrich((MEAL_O,)) == 0 and d.qa() == 0
    assert d.yukle() == 0  # yalniz elmalili-meal tarandi
    assert d.yukleme_sayilari()["xref_silinen"] == 0
    assert (
        say(
            conn,
            "SELECT count(*) FROM icerik.xref WHERE starts_with(src_anchor, 'meal:elmalili-sade:')",
        )
        == 2
    )


def test_kapali_review_bagli_aday_silinmez(d: CitDunyasi, conn: psycopg.Connection) -> None:
    assert d.hepsi() == 0
    conn.execute(
        "UPDATE icerik.review SET durum = 'reddedildi' WHERE xref_id IN (SELECT id FROM icerik.xref"
        " WHERE src_anchor = 'meal:elmalili:2:2')"
    )
    conn.execute(
        "UPDATE icerik.unit SET metin = 'Deneme paragrafi 2 Arapca kalmadi' WHERE anchor = %s",
        ("meal:elmalili:2:2",),
    )
    assert d.hepsi() == 0
    s = d.yukleme_sayilari()
    assert s["xref_silinen"] == 0 and s["xref_silinmeyen_review_bagli"] == 1
    assert say(conn, "SELECT count(*) FROM icerik.xref WHERE src_anchor = 'meal:elmalili:2:2'") == 1


@pytest.mark.parametrize("durum", ["acik", "onaylandi", "reddedildi", "geri_alindi"])
def test_herhangi_durumda_review_varsa_yenisi_acilmaz(
    d: CitDunyasi, conn: psycopg.Connection, durum: str
) -> None:
    assert d.hepsi() == 0
    xid = conn.execute(
        "SELECT id FROM icerik.xref WHERE type = 'iktibas' AND src_anchor = 'meal:elmalili:2:2'"
    ).fetchone()
    assert xid is not None
    conn.execute(
        "UPDATE icerik.review SET durum = %s::icerik.inceleme_durumu WHERE xref_id = %s",
        (durum, xid[0]),
    )
    conn.execute("UPDATE icerik.xref SET score = 0.01, confidence = 0.01 WHERE id = %s", (xid[0],))
    assert d.hepsi() == 0
    assert d.yukleme_sayilari()["xref_guncellenen"] == 1  # aday: skor yeniden yazildi
    assert d.yukleme_sayilari()["review_aday_acilan"] == 0
    assert say(conn, "SELECT count(*) FROM icerik.review WHERE xref_id = %s", xid[0]) == 1


def test_degisen_aday_guncellenir_id_ve_status_korunur(
    d: CitDunyasi, conn: psycopg.Connection
) -> None:
    assert d.hepsi() == 0
    xid = conn.execute(
        "SELECT id FROM icerik.xref WHERE type = 'iktibas' AND src_anchor = 'meal:elmalili:2:2'"
    ).fetchone()
    assert xid is not None
    conn.execute(
        "UPDATE icerik.xref SET confidence = 0.5, data_version = 'eski' WHERE id = %s", (xid[0],)
    )
    assert d.hepsi() == 0
    assert d.yukleme_sayilari()["xref_guncellenen"] == 1
    satir = conn.execute(
        "SELECT id, status::text, data_version FROM icerik.xref WHERE id = %s", (xid[0],)
    ).fetchone()
    assert satir is not None and satir[1] == "aday" and satir[2].startswith("citations@1/")


# --- kalip listesi (veritabani) ve onayli alias -----------------------------------------------


def test_kalip_listesi_veritabani_onayli_kayitlari(d: CitDunyasi, conn: psycopg.Connection) -> None:
    kalip_metni = {"meal:elmalili:2:2": paragraf(KALIP_METNI)}
    conn.execute(
        "UPDATE icerik.unit SET metin = %s, content_hash = %s WHERE anchor = %s",
        (
            kalip_metni["meal:elmalili:2:2"],
            content_hash(kalip_metni["meal:elmalili:2:2"]),
            "meal:elmalili:2:2",
        ),
    )
    assert d.enrich() == 0
    once = [s for s in d.satirlar() if s["src_anchor"] == "meal:elmalili:2:2"]
    assert len(once) == 3 and all(s["evidence"]["phrase_freq"] == 4 for s in once)  # type: ignore[index]
    anahtar = " ".join(anahtar_dizisi(KALIP_METNI))
    for durum, ad in (("acik", "x"), ("reddedildi", "y")):  # onaylanmamis kayitlar sayilmaz
        conn.execute(
            "INSERT INTO icerik.review (hedef_tablo, hedef_anahtar, alan, eylem, onerilen, durum,"
            " koken, oneren) VALUES ('unit', %s, 'kalip', 'kalip_ekle', %s::jsonb,"
            " %s::icerik.inceleme_durumu, 'hat', 'hat')",
            (ad, f'{{"anahtar": "{anahtar}"}}', durum),
        )
    assert veritabanindan_oku(conn) == frozenset()
    assert d.enrich() == 0
    assert len([s for s in d.satirlar() if s["src_anchor"] == "meal:elmalili:2:2"]) == 3
    conn.execute(
        "INSERT INTO icerik.review (hedef_tablo, hedef_anahtar, alan, eylem, onerilen, durum,"
        " koken, oneren) VALUES ('unit', 'z', 'kalip', 'kalip_ekle', %s::jsonb,"
        " 'onaylandi', 'editor', 'ed')",
        (f'{{"anahtar": "{anahtar}"}}',),
    )
    assert veritabanindan_oku(conn) == frozenset({anahtar})
    assert d.enrich() == 0
    assert [s for s in d.satirlar() if s["src_anchor"] == "meal:elmalili:2:2"] == []
    ist = d.manifest()["ayrintilar"]["istatistik"]  # type: ignore[index]
    assert ist["sayaclar"]["kalip_listesinde_kume"] == 1 and ist["kalip_listesi_girdi"] == 1  # type: ignore[index]


def test_ad_tabanli_yalniz_onayli_alias_ile_acilir(d: CitDunyasi, conn: psycopg.Connection) -> None:
    conn.execute(
        "UPDATE icerik.unit SET metin = 'Deneme (Alfa Sûresi, 2) ve Alfa: 3' WHERE anchor = %s",
        ("meal:elmalili:2:3",),
    )
    conn.execute(
        "INSERT INTO icerik.surah_alias (surah_no, alias, alias_key, kind, risky, status)"
        " VALUES (2, 'Alfa', %s, 'kanonik', false, 'aday')",
        (normalize_tr("Alfa", "genis"),),
    )
    assert d.enrich() == 0
    ist = d.manifest()["ayrintilar"]["istatistik"]  # type: ignore[index]
    assert ist["ad_tabanli_etkin"] is False and ist["sayaclar"]["ad_tabanli_kapali"] > 0  # type: ignore[index]
    assert [s for s in d.satirlar() if s["src_anchor"] == "meal:elmalili:2:3"] == []
    conn.execute("UPDATE icerik.surah_alias SET status = 'onayli' WHERE alias = 'Alfa'")
    assert d.enrich() == 0
    ist = d.manifest()["ayrintilar"]["istatistik"]  # type: ignore[index]
    assert ist["ad_tabanli_etkin"] is True and ist["alias_onayli"] == 1  # type: ignore[index]
    satirlar = [s for s in d.satirlar() if s["src_anchor"] == "meal:elmalili:2:3"]
    assert sorted((s["dst_anchor"], s["confidence"]) for s in satirlar) == [
        ("q:2:2", "0.950000"),
        ("q:2:3", "0.850000"),
    ]
    assert d.qa() == 0 and d.yukle() == 0


# --- QA ve komut hatalari -----------------------------------------------------------------------


def test_qa_db_uzantisi_hatalari(d: CitDunyasi, conn: psycopg.Connection) -> None:
    from mutalaa_pipeline.qa.checks.xref_atif import db_staged_hatalari
    from mutalaa_pipeline.staged import Satir

    assert d.enrich() == 0
    satirlar = [Satir("t", i, s) for i, s in enumerate(d.satirlar(), start=1)]
    assert all(v == 0 for v in db_staged_hatalari(conn, satirlar).values())
    conn.execute("UPDATE icerik.unit SET content_hash = repeat('b', 64) WHERE anchor = 'q:2:1'")
    conn.execute("UPDATE icerik.unit SET metin = 'Deneme' WHERE anchor = 'meal:elmalili:2:1'")
    h = db_staged_hatalari(conn, satirlar)
    assert h["dst_ozet_eski"] >= 1 and h["src_span_metin_disi"] >= 1
    conn.execute("DELETE FROM icerik.unit WHERE anchor = 'meal:elmalili:2:3'")
    assert db_staged_hatalari(conn, satirlar)["meal_birimi_yok"] >= 1


def test_qa_raporu_yoksa_yukleme_yapilmaz(d: CitDunyasi, conn: psycopg.Connection) -> None:
    assert d.enrich() == 0
    assert d.yukle() != 0
    assert say(conn, "SELECT count(*) FROM icerik.xref") == 0


def test_enrich_calismasi_yoksa_yukleme_cikis_2(d: CitDunyasi) -> None:
    assert d.yukle() == 2


def test_hedefsiz_ya_da_bilinmeyen_hedef_cikis_2(d: CitDunyasi) -> None:
    assert d.enrich(()) == 2
    assert d.enrich(("tanzil-uthmani",)) == 2


def test_eski_staged_ozet_yuklemeyi_durdurur(d: CitDunyasi, conn: psycopg.Connection) -> None:
    assert d.enrich() == 0 and d.qa() == 0
    conn.execute("UPDATE icerik.unit SET content_hash = repeat('c', 64) WHERE anchor = 'q:2:1'")
    assert d.yukle() == 2  # staged ozet veritabaniyla tutmuyor: once enrich citations


def test_sql_denetimi_aday_review_yoksa_ihlal(d: CitDunyasi, conn: psycopg.Connection) -> None:
    assert d.hepsi() == 0
    onekler = ["meal:elmalili:", "meal:elmalili-sade:"]
    assert all(v == 0 for v in sql_hatalari(conn, ["atif", "iktibas"], onekler).values())
    conn.execute("DELETE FROM icerik.review WHERE hedef_tablo = 'xref'")
    assert sql_hatalari(conn, ["atif", "iktibas"], onekler)["aday_review_yok"] == 7


def test_meal_birimleri_taslak_dahil_okunur(d: CitDunyasi, conn: psycopg.Connection) -> None:
    durumlar = conn.execute(
        "SELECT DISTINCT metin_durumu::text FROM icerik.unit WHERE kind = 'meal'"
    ).fetchall()
    assert [x[0] for x in durumlar] == ["taslak"]
    db = cit_girdi.db_oku(conn, (MEAL_O, MEAL_S))
    assert len(db.mealler[MEAL_O]) == 3 and len(db.mealler[MEAL_S]) == 2
    assert [b.anchor for b in db.mealler[MEAL_O]] == sorted(b.anchor for b in db.mealler[MEAL_O])


# --- staged cikti, kapilar ve komut -------------------------------------------------------------


def test_staged_cikti_belirleyici_ve_ondalik_dizgeli(d: CitDunyasi) -> None:
    from mutalaa_pipeline.enrich.citations.uret import sayisal

    assert d.enrich() == 0
    ilk = (d.son_enrich() / "xref_citations.jsonl").read_bytes()
    satirlar = d.satirlar()
    assert [(s["tur_no"], s["src_no"], s["src_bas"]) for s in satirlar] == sorted(
        (s["tur_no"], s["src_no"], s["src_bas"])
        for s in satirlar  # type: ignore[type-var]
    )
    for s in satirlar:
        assert isinstance(s["score"], str) and isinstance(s["confidence"], str)
        v = sayisal(s)
        assert isinstance(v["score"], float) and 0.0 <= v["score"] <= 1.0
    iktibas = next(s for s in satirlar if s["type"] == "iktibas")
    assert isinstance(iktibas["evidence"]["coverage"], str)  # type: ignore[index]
    assert d.enrich() == 0  # yeni calisma, ayni girdi: ayni baytlar
    assert (d.son_enrich() / "xref_citations.jsonl").read_bytes() == ilk


def test_manifest_hedefler_surum_ve_istatistik(d: CitDunyasi) -> None:
    assert d.enrich() == 0
    a = d.manifest()["ayrintilar"]
    assert a["hedefler"] == [MEAL_O, MEAL_S] and a["turler"] == ["atif", "iktibas"]  # type: ignore[index]
    ist = a["istatistik"]  # type: ignore[index]
    assert ist["tur"] == {"atif": 4, "iktibas": 3} and ist["satir_toplam"] == 7
    assert set(ist["sinif"]) == {"atif", "iktibas"} and ist["indeksler"] == ["uthmani", "imlai"]
    assert ist["sayaclar"]["arapca_dizi"] == 3 and ist["sayaclar"]["ad_tabanli_kapali"] == 5
    assert ist["meal_birim"] == {MEAL_O: 3, MEAL_S: 2}


def _girdi(d: CitDunyasi):
    from mutalaa_pipeline.enrich.citations.uret import sayisal
    from mutalaa_pipeline.qa.checks.xref_atif import AtifGirdisi
    from mutalaa_pipeline.staged import Satir

    satirlar = [Satir("t", i, sayisal(s)) for i, s in enumerate(d.satirlar(), start=1)]
    return AtifGirdisi({}, satirlar, [MEAL_O, MEAL_S], {"atif": 4, "iktibas": 3})


def test_g_but_bozuk_satirlari_yakalar(d: CitDunyasi) -> None:
    import copy

    from mutalaa_pipeline.qa.checks.xref_atif import g_but

    assert d.enrich() == 0
    g = _girdi(d)
    assert g_but(g).gecti
    ikt = next(s for s in g.satirlar if s.veri["type"] == "iktibas")
    kopya = copy.deepcopy(ikt.veri)

    def bozuk(degisim) -> str:
        ikt.veri.clear()
        ikt.veri.update(copy.deepcopy(kopya))
        degisim(ikt.veri)
        return " ".join(g_but(g).bulgular)

    assert "tutarsiz_guven" in bozuk(
        lambda v: (v["evidence"].update(consistent_quote=False), v.update(confidence=0.5))
    )
    assert "tutarli_guven" in bozuk(
        lambda v: (v["evidence"].update(consistent_quote=True), v.update(confidence=0.5))
    )
    assert "skor_formulu" in bozuk(lambda v: v.update(score=0.1))
    assert "dst_span" in bozuk(lambda v: v.update(dst_span=[1, 99]))
    assert "coverage" in bozuk(lambda v: v["evidence"].update(coverage=0.5))
    assert "evidence_alanlari" in bozuk(lambda v: v["evidence"].pop("phrase_key"))
    assert "index" in bozuk(lambda v: v["evidence"].update(index="baska"))
    assert "skor_guven_araligi" in bozuk(lambda v: v.update(confidence=1.5))
    assert "satir_alanlari" in bozuk(lambda v: v.pop("data_version"))


def test_g_cap_ve_g_kay_bozuk_satirlari_yakalar(d: CitDunyasi) -> None:
    from mutalaa_pipeline.qa.checks.xref_atif import g_cap, g_kay

    assert d.enrich() == 0
    g = _girdi(d)
    assert g_cap(g).gecti
    s = g.satirlar[0]
    eski = dict(s.veri)
    s.veri["src_anchor"] = "q:2:255"
    assert any("src_hedef_meal_degil" in b for b in g_cap(g).bulgular)
    s.veri.clear()
    s.veri.update(eski)
    s.veri["dst_anchor"] = "q:2:255:3"
    assert any("dst_ayet_capasi_degil" in b for b in g_cap(g).bulgular)
    s.veri.clear()
    s.veri.update(eski)
    s.veri["src_span"] = [5, 5]
    assert any("src_span" in b for b in g_cap(g).bulgular)
    s.veri.clear()
    s.veri.update(eski)
    assert g_cap(g).gecti
    # G-KAY: kayitsiz source_id
    s.veri["evidence"]["source_id"] = "bilinmeyen"  # type: ignore[index]
    assert not g_kay(g).gecti


def test_komut_kaydi_ve_target_zorunlu() -> None:
    from typer.testing import CliRunner

    from mutalaa_pipeline.cli import app

    yardim = CliRunner().invoke(app, ["enrich", "citations", "--help"])
    assert yardim.exit_code == 0 and "--target" in yardim.output
    eksik = CliRunner().invoke(app, ["enrich", "citations"])
    assert eksik.exit_code == 2  # --target zorunlu (kullanim hatasi)
