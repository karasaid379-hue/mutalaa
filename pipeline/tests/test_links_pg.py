"""`enrich links`, `qa run` ve `export pg --source xref-baglantilar` (A18.3): SENTETIK dunya.

`links_yardimci.LinksDunyasi` `mutalaa_test` veritabanina yuklenir: kaynak, ayet birimi, kok, lemma
ve kelimeler testte SQL ile kurulur. Testler dis islem icinde kosar ve sonunda geri alinir.
Veritabani yoksa atlanir (`MUTALAA_DEGISMEZLIK_ZORUNLU=1` atlamayi hataya cevirir). Hicbir
Kur'an metni hafizadan yazilmaz.
"""

import os
from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest
from links_yardimci import (
    AYETLER,
    KAYNAK,
    QAC,
    QURSIM,
    UTHMANI,
    LinksDunyasi,
    dunya_kur,
    tohumla,
)

from mutalaa_pipeline.config import Ayarlar
from mutalaa_pipeline.db import baglan
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.qa.checks.xref import sql_hatalari

SLUGLAR = [QAC, UTHMANI, QURSIM]


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
            "SELECT (SELECT count(*) FROM icerik.root) + (SELECT count(*) FROM icerik.lemma)"
            " + (SELECT count(*) FROM icerik.quran_word) + (SELECT count(*) FROM icerik.xref)"
            " + (SELECT count(*) FROM icerik.unit WHERE kind = 'ayet')"
            " + (SELECT count(*) FROM icerik.review WHERE hedef_tablo = 'xref')"
            " + (SELECT count(*) FROM icerik.source WHERE slug = ANY(%s))",
            (SLUGLAR,),
        ).fetchone()
        assert kalinti is not None
        if kalinti[0] != 0:
            baglanti.rollback()
            _yok("mutalaa_test icinde root/lemma/quran_word/xref/ayet satiri kalmis")
        yield baglanti
    finally:
        baglanti.rollback()
        baglanti.close()


@pytest.fixture
def d(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, conn: psycopg.Connection) -> LinksDunyasi:
    tohumla(conn)
    return dunya_kur(tmp_path, monkeypatch, conn)


def say(conn: psycopg.Connection, sorgu: str, *param: object) -> int:
    satir = conn.execute(sorgu, param).fetchone()  # type: ignore[arg-type]
    assert satir is not None
    return int(satir[0])


def tur_sayilari(conn: psycopg.Connection) -> dict[tuple[str, str], int]:
    return {
        (str(t), str(s)): int(n)
        for t, s, n in conn.execute(
            "SELECT type::text, status::text, count(*) FROM icerik.xref GROUP BY 1, 2"
        ).fetchall()
    }


def goruntu(conn: psycopg.Connection) -> list[tuple[object, ...]]:
    return [
        tuple(s)
        for s in conn.execute(
            "SELECT id, type::text, src_anchor, dst_anchor, score, confidence, evidence,"
            " origin::text, status::text, data_version FROM icerik.xref ORDER BY id"
        ).fetchall()
    ]


def satir_id(conn: psycopg.Connection, tur: str, src: str, dst: str) -> str:
    satir = conn.execute(
        "SELECT id::text FROM icerik.xref WHERE type = %s::icerik.xref_type AND src_anchor = %s"
        " AND dst_anchor = %s",
        (tur, src, dst),
    ).fetchone()
    assert satir is not None
    return str(satir[0])


# --- ilk yukleme -----------------------------------------------------------------------------


def test_ilk_yukleme_uc_tur_aday_ve_review_yok(d: LinksDunyasi, conn: psycopg.Connection) -> None:
    assert d.hepsi() == 0
    assert tur_sayilari(conn) == {
        ("kok", "aday"): 6,
        ("lemma", "aday"): 4,
        ("benzer_ayet", "aday"): 4,
    }
    # otomatik turler review acmaz (K-51 madde 8)
    assert say(conn, "SELECT count(*) FROM icerik.review WHERE hedef_tablo = 'xref'") == 0
    assert say(conn, "SELECT count(*) FROM icerik.xref WHERE origin <> 'hat'") == 0
    sayilar = d.yukleme_sayilari()
    assert sayilar["xref_eklenen"] == 14 and sayilar["xref_guncellenen"] == 0
    assert sayilar["kaynak_eklenen"] == 1  # qursim kaynak satiri bu yuklemede eklenir
    assert say(conn, "SELECT count(*) FROM icerik.source WHERE slug = 'qursim'") == 1
    # kok skoru: ortak idf toplami / kaynak kumesinin idf toplami; yaygin kok (8) satir uretmez
    skor = conn.execute(
        "SELECT score, confidence FROM icerik.xref WHERE type = 'kok' AND src_anchor = 'q:2:3'"
        " AND dst_anchor = 'q:2:1'"
    ).fetchone()
    assert skor is not None and skor[0] == skor[1] == 1.0
    assert (
        say(
            conn,
            "SELECT count(*) FROM icerik.xref WHERE type IN ('kok', 'lemma')"
            " AND src_anchor >= 'q:2:4' AND src_anchor <= 'q:2:9'",
        )
        == 0
    )  # q:2:4..9 yalniz esigin altindaki kokleri tasir: satir yok


def test_evidence_biciminde_kaynak_ve_ozetler(d: LinksDunyasi, conn: psycopg.Connection) -> None:
    assert d.hepsi() == 0
    kaynaklar = {
        (str(t), str(s)): int(n)
        for t, s, n in conn.execute(
            "SELECT type::text, evidence ->> 'source_id', count(*) FROM icerik.xref GROUP BY 1, 2"
        ).fetchall()
    }
    assert kaynaklar == {
        ("kok", QAC): 6,
        ("lemma", QAC): 4,
        ("benzer_ayet", UTHMANI): 2,
        ("benzer_ayet", QURSIM): 2,
    }
    # her ozet birimin guncel content_hash ilk 16 hanesi; kayitsiz source_id yok
    assert (
        say(
            conn,
            "SELECT count(*) FROM icerik.xref x WHERE x.evidence ->> 'src_hash' <> (SELECT left("
            "u.content_hash, 16) FROM icerik.unit u WHERE u.anchor = x.src_anchor)",
        )
        == 0
    )
    assert sql_hatalari(conn) == dict.fromkeys(sql_hatalari(conn), 0)
    assert sql_hatalari(conn)["kok_tutarsiz"] == 0
    assert sql_hatalari(conn)["lemma_tutarsiz"] == 0
    assert sql_hatalari(conn)["kayitsiz_source_id"] == 0
    # benzer_ayet: sozluksel cift (q:2:4, q:2:5) ve QurSim ile ortusen (q:2:7, q:2:8)
    s = conn.execute(
        "SELECT evidence FROM icerik.xref WHERE type = 'benzer_ayet' AND src_anchor = 'q:2:7'"
        " AND dst_anchor = 'q:2:8'"
    ).fetchone()
    assert s is not None
    kanit = s[0]
    assert kanit["subtype"] == "sozluksel" and kanit["qursim"] == {"label": 2}
    assert kanit["dongusel"] is True and kanit["source_id"] == UTHMANI
    saf = conn.execute(
        "SELECT score, confidence, evidence FROM icerik.xref WHERE type = 'benzer_ayet'"
        " AND src_anchor = 'q:2:2' AND dst_anchor = 'q:2:9'"
    ).fetchone()
    assert saf is not None
    assert saf[0] == saf[1] == 0.5 and saf[2]["subtype"] == "alim" and saf[2]["label"] == 1


# --- ikinci kosu ve korunanlar ----------------------------------------------------------------


def test_ikinci_kosu_sifir_degisiklik(d: LinksDunyasi, conn: psycopg.Connection) -> None:
    assert d.hepsi() == 0
    onceki = goruntu(conn)
    assert d.hepsi() == 0
    s = d.yukleme_sayilari()
    assert s["xref_eklenen"] == s["xref_guncellenen"] == s["xref_silinen"] == 0
    assert s["xref_degismeyen"] == 14
    assert s["review_uretilmedi_acilan"] == s["review_uc_metni_degisti_acilan"] == 0
    assert goruntu(conn) == onceki  # id, skor, evidence ve durum ayni


def test_aday_satir_guncellenir_id_ve_durum_korunur(
    d: LinksDunyasi, conn: psycopg.Connection
) -> None:
    assert d.hepsi() == 0
    kimlik = satir_id(conn, "kok", "q:2:1", "q:2:2")
    conn.execute(
        "UPDATE icerik.xref SET score = 0.1, confidence = 0.1, data_version = 'eski'"
        " WHERE id = %s::uuid",
        (kimlik,),
    )
    assert d.hepsi() == 0
    assert d.yukleme_sayilari()["xref_guncellenen"] == 1
    assert satir_id(conn, "kok", "q:2:1", "q:2:2") == kimlik
    satir = conn.execute(
        "SELECT score, status::text, data_version FROM icerik.xref WHERE id = %s::uuid", (kimlik,)
    ).fetchone()
    assert satir is not None and satir[0] > 0.5 and satir[1] == "aday" and satir[2] != "eski"


def test_onayli_ve_red_satirlara_dokunulmaz(d: LinksDunyasi, conn: psycopg.Connection) -> None:
    assert d.hepsi() == 0
    onayli = satir_id(conn, "kok", "q:2:1", "q:2:2")
    red = satir_id(conn, "lemma", "q:2:1", "q:2:2")
    editor = satir_id(conn, "kok", "q:2:2", "q:2:1")
    conn.execute(
        "UPDATE icerik.xref SET status = 'onayli', score = 0.25, data_version = 'elle'"
        " WHERE id = %s::uuid",
        (onayli,),
    )
    conn.execute(
        "UPDATE icerik.xref SET status = 'red', score = 0.2, data_version = 'elle'"
        " WHERE id = %s::uuid",
        (red,),
    )
    conn.execute(
        "UPDATE icerik.xref SET origin = 'editor', score = 0.3, data_version = 'elle'"
        " WHERE id = %s::uuid",
        (editor,),
    )
    onceki = {
        k: conn.execute(
            "SELECT score, status::text, origin::text, evidence, data_version FROM icerik.xref"
            " WHERE id = %s::uuid",
            (k,),
        ).fetchone()
        for k in (onayli, red, editor)
    }
    assert d.hepsi() == 0
    s = d.yukleme_sayilari()
    assert s["xref_korunan_onayli"] == 1 and s["xref_korunan_red"] == 1
    assert s["xref_korunan_editor_ve_diger"] == 1
    assert s["xref_guncellenen"] == 0 and s["xref_eklenen"] == 0
    for k, once in onceki.items():
        sonra = conn.execute(
            "SELECT score, status::text, origin::text, evidence, data_version FROM icerik.xref"
            " WHERE id = %s::uuid",
            (k,),
        ).fetchone()
        assert sonra == once
    # uretilen onayli satir icin yeniden dogrulama gerekmez (uc ozetleri guncel)
    assert say(conn, "SELECT count(*) FROM icerik.review WHERE hedef_tablo = 'xref'") == 0


# --- uretilmeyen satirlar ---------------------------------------------------------------------


def _ekle(conn: psycopg.Connection, tur: str, src: str, dst: str, durum: str, origin: str) -> str:
    """Uretilmeyen bir satir; evidence ozetleri birimlerin guncel ozetleridir."""
    satir = conn.execute(
        "INSERT INTO icerik.xref (type, src_anchor, dst_anchor, score, confidence, evidence,"
        " origin, status, data_version) SELECT %s::icerik.xref_type, %s, %s, 0.4, 0.4,"
        " jsonb_build_object('src_hash', (SELECT left(content_hash, 16) FROM icerik.unit"
        " WHERE anchor = %s), 'dst_hash', (SELECT left(content_hash, 16) FROM icerik.unit"
        " WHERE anchor = %s), 'source_id', 'qac-morfoloji', 'shared', '[]'::jsonb),"
        " %s::icerik.xref_origin, %s::icerik.xref_status, 'elle' RETURNING id::text",
        (tur, src, dst, src, dst, origin, durum),
    ).fetchone()
    assert satir is not None
    return str(satir[0])


def test_uretilmeyen_aday_silinir_yalniz_ayni_tur_kapsaminda(
    d: LinksDunyasi, conn: psycopg.Connection
) -> None:
    assert d.hepsi() == 0
    kok_fazla = _ekle(conn, "kok", "q:2:4", "q:2:9", "aday", "hat")
    lemma_fazla = _ekle(conn, "lemma", "q:2:4", "q:2:9", "aday", "hat")
    editor_fazla = _ekle(conn, "lemma", "q:2:5", "q:2:9", "aday", "editor")
    # yalniz lemma kosusu: kok satirina ve editor satirina dokunmaz
    assert d.hepsi("lemma") == 0
    s = d.yukleme_sayilari()
    assert s["xref_silinen"] == 1
    kalan = {
        k
        for (k,) in conn.execute(
            "SELECT id::text FROM icerik.xref WHERE id = ANY(%s::uuid[])",
            ([kok_fazla, lemma_fazla, editor_fazla],),
        ).fetchall()
    }
    assert kalan == {kok_fazla, editor_fazla}
    assert say(conn, "SELECT count(*) FROM icerik.xref WHERE type = 'kok'") == 7
    # tum turler: kok fazlasi da silinir
    assert d.hepsi() == 0
    assert d.yukleme_sayilari()["xref_silinen"] == 1
    assert say(conn, "SELECT count(*) FROM icerik.xref WHERE type = 'kok'") == 6
    assert say(conn, "SELECT count(*) FROM icerik.xref WHERE id = %s::uuid", editor_fazla) == 1


def test_uretilmeyen_aday_review_bagliysa_silinmez(
    d: LinksDunyasi, conn: psycopg.Connection
) -> None:
    assert d.hepsi() == 0
    fazla = _ekle(conn, "benzer_ayet", "q:2:4", "q:2:9", "aday", "hat")
    conn.execute(
        "INSERT INTO icerik.review (hedef_tablo, hedef_anahtar, xref_id, alan, eylem, koken,"
        " oneren) VALUES ('xref', %s, %s::uuid, 'status', 'oner', 'editor', 'deneme')",
        (fazla, fazla),
    )
    assert d.hepsi() == 0
    s = d.yukleme_sayilari()
    assert s["xref_silinen"] == 0 and s["xref_silinmeyen_review_bagli"] == 1
    assert say(conn, "SELECT count(*) FROM icerik.xref WHERE id = %s::uuid", fazla) == 1


def yeniden_dogrulama(conn: psycopg.Connection, kimlik: str) -> list[tuple[object, ...]]:
    return [
        tuple(s)
        for s in conn.execute(
            "SELECT hedef_tablo, hedef_anahtar, xref_id::text, alan, eylem, onerilen, koken,"
            " oneren, durum::text, guven FROM icerik.review WHERE xref_id = %s::uuid ORDER BY id",
            (kimlik,),
        ).fetchall()
    ]


def test_uretilmeyen_onayli_silinmez_yeniden_dogrulama_review_tekil(
    d: LinksDunyasi, conn: psycopg.Connection
) -> None:
    assert d.hepsi() == 0
    fazla = _ekle(conn, "kok", "q:2:4", "q:2:9", "onayli", "hat")
    assert d.hepsi() == 0
    assert say(conn, "SELECT count(*) FROM icerik.xref WHERE id = %s::uuid", fazla) == 1
    kayitlar = yeniden_dogrulama(conn, fazla)
    assert kayitlar == [
        (
            "xref",
            fazla,
            fazla,
            "status",
            "oner",
            {"yeniden_dogrula": True, "neden": "uretilmedi"},
            "hat",
            "hat",
            "acik",
            None,
        )
    ]
    assert d.yukleme_sayilari()["review_uretilmedi_acilan"] == 1
    # ikinci ve ucuncu kosu: acik kayit varken yenisi acilmaz
    assert d.hepsi() == 0
    assert d.hepsi() == 0
    assert len(yeniden_dogrulama(conn, fazla)) == 1
    s = d.yukleme_sayilari()
    assert s["review_uretilmedi_acilan"] == 0 and s["review_zaten_acik"] == 1
    # editor karari verildiyse (kayit kapali) ve satir hala uretilmiyorsa yeni kayit acilir
    conn.execute("UPDATE icerik.review SET durum = 'onaylandi' WHERE xref_id = %s::uuid", (fazla,))
    assert d.hepsi() == 0
    assert len(yeniden_dogrulama(conn, fazla)) == 2
    # otomatik turler icin baska review acilmaz
    assert say(conn, "SELECT count(*) FROM icerik.review WHERE hedef_tablo = 'xref'") == 2


def test_uc_metni_degisen_onayli_satir_yeniden_dogrulanir_aday_guncellenir(
    d: LinksDunyasi, conn: psycopg.Connection
) -> None:
    assert d.hepsi() == 0
    onayli = satir_id(conn, "kok", "q:2:1", "q:2:2")
    aday = satir_id(conn, "kok", "q:2:1", "q:2:3")
    conn.execute("UPDATE icerik.xref SET status = 'onayli' WHERE id = %s::uuid", (onayli,))
    eski = say(conn, "SELECT count(*) FROM icerik.xref WHERE evidence ->> 'src_hash' IS NOT NULL")
    assert eski == 14
    # q:2:1 biriminin metni (ozeti) degisti
    conn.execute("UPDATE icerik.unit SET content_hash = repeat('a', 64) WHERE anchor = 'q:2:1'")
    # enrich yeniden kosulmadan yukleme reddedilir (staged ozeti eski): cikis 2
    assert d.qa() == 0
    assert d.yukle() == 2
    assert say(conn, "SELECT count(*) FROM icerik.review WHERE hedef_tablo = 'xref'") == 0
    # enrich + qa + yukle: aday satirlar yeni ozetle guncellenir; onayli satir kuyruga duser
    assert d.hepsi() == 0
    s = d.yukleme_sayilari()
    assert s["review_uc_metni_degisti_acilan"] == 1
    assert yeniden_dogrulama(conn, onayli)[0][5] == {
        "yeniden_dogrula": True,
        "neden": "uc_metni_degisti",
    }
    yeni = conn.execute(
        "SELECT evidence ->> 'src_hash' FROM icerik.xref WHERE id = %s::uuid", (aday,)
    ).fetchone()
    assert yeni is not None and yeni[0] == "a" * 16
    eski_onayli = conn.execute(
        "SELECT evidence ->> 'src_hash', status::text FROM icerik.xref WHERE id = %s::uuid",
        (onayli,),
    ).fetchone()
    assert eski_onayli is not None and eski_onayli[0] != "a" * 16 and eski_onayli[1] == "onayli"
    # ikinci koşu: acik kayit varken tekrar acilmaz
    assert d.hepsi() == 0
    assert len(yeniden_dogrulama(conn, onayli)) == 1


# --- hatalar ----------------------------------------------------------------------------------


def test_kayitsiz_kaynak_ya_da_eksik_zincirde_cikis_2(
    d: LinksDunyasi, conn: psycopg.Connection
) -> None:
    assert d.yukle() == 2  # enrich calistirmasi yok
    assert d.enrich() == 0
    assert d.yukle() == 1  # QA raporu yok (QA kapisi)
    conn.execute("DELETE FROM icerik.quran_word WHERE ayah_index = 4")
    assert d.enrich("kok") == 2  # ayah_index kesintisiz degil


def test_kok_ayah_count_uyumsuzsa_enrich_cikis_2(d: LinksDunyasi, conn: psycopg.Connection) -> None:
    conn.execute("UPDATE icerik.root SET ayah_count = ayah_count + 1 WHERE id = 1")
    assert d.enrich("kok") == 2
    assert d.enrich("lemma") == 0  # lemma icin root.ayah_count kullanilmaz


def test_gecersiz_tur_cikis_2(d: LinksDunyasi) -> None:
    assert d.enrich("anlamsal") == 2


def test_dry_run_hicbir_sey_yazmaz(d: LinksDunyasi, conn: psycopg.Connection) -> None:
    assert d.enrich(dry_run=True) == 0
    assert not (d.veri / "staged" / KAYNAK).exists()
    assert d.enrich() == 0
    assert d.qa() == 0
    assert d.yukle(dry_run=True) == 0
    assert say(conn, "SELECT count(*) FROM icerik.xref") == 0
    assert d.yukle() == 0
    assert say(conn, "SELECT count(*) FROM icerik.xref") == 14


def test_staged_dunya_besmele_kirpilir(d: LinksDunyasi) -> None:
    assert d.enrich() == 0
    manifest = d.manifest()
    ayrintilar = manifest["ayrintilar"]
    assert isinstance(ayrintilar, dict)
    benzer = ayrintilar["istatistik"]["benzer_ayet"]  # type: ignore[index]
    assert benzer["simple_besmele_kirpilan"] == 1 and benzer["simple_besmele_bulunmayan"] == 0
    assert benzer["qursim_gecerli_cift"] == 3 and benzer["qursim_gecersiz"] == 1
    assert benzer["qursim_kendi_indeksimizde"] == 1 and benzer["satir_dongusel"] == 1
    # imlai ve uthmani ayni kelime sayisini verir: ayet sayilari farkli degil
    assert benzer["imlai_uthmani_kelime_sayisi_farkli_ayet"] == 0
    assert len(AYETLER) == ayrintilar["ayet_sayisi"]
