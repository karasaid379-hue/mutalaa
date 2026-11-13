"""`export pg --source kaikki-tr`: Turkce lemma, review, tr_root_index ve tr_form (A18.2).

SENTETIK dunya (`tr_yardimci`) `mutalaa_test` veritabanina yuklenir: kok, Arapca lemma ve meal
birimleri testte SQL ile kurulur (zincir kosulmaz). Testler dis islem icinde kosar ve sonunda
geri alinir. Veritabani yoksa atlanir (`MUTALAA_DEGISMEZLIK_ZORUNLU=1` atlamayi hataya cevirir).
Hicbir Kur'an, meal ya da sozluk metni hafizadan yazilmaz.
"""

import json
import os
from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest
from hat_yardimci import ayarlar_kur
from tr_yardimci import (
    KAIKKI,
    MEAL_METINLERI,
    MEAL_O,
    MEAL_S,
    QAC,
    QAC_KOKLER,
    QAC_LEMMALAR,
    TrDunya,
    dunya_kur,
    kaikki_ota_satirlari,
    kaikki_tr_satirlari,
    kaikki_yaz,
)

from mutalaa_pipeline.anchor import content_hash
from mutalaa_pipeline.config import Ayarlar
from mutalaa_pipeline.db import baglan
from mutalaa_pipeline.export import pg
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.normalize.turkish import lower_turkish
from mutalaa_pipeline.qa.checks.tr_roots import db_g_cap, span_hatalari

SLUGLAR = [KAIKKI, QAC, MEAL_O, MEAL_S]
ROOT_ID = {"bnr": 1, "Sml": 2, "Amn": 3}
AR_ID = {"banar": 11, "samal": 12, "mrt1": 13, "mrt2": 14}


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
            " + (SELECT count(*) FROM icerik.tr_root_index) + (SELECT count(*) FROM icerik.tr_form)"
            " + (SELECT count(*) FROM icerik.unit WHERE source_id = ANY(%s))"
            " + (SELECT count(*) FROM icerik.review WHERE hedef_tablo = 'lemma')"
            " + (SELECT count(*) FROM icerik.source WHERE slug = ANY(%s))",
            (SLUGLAR, SLUGLAR),
        ).fetchone()
        assert kalinti is not None
        if kalinti[0] != 0:
            baglanti.rollback()
            _yok("mutalaa_test icinde root/lemma/unit/tr_* satiri kalmis")
        yield baglanti
    finally:
        baglanti.rollback()
        baglanti.close()


def tohumla(conn: psycopg.Connection, *, kok_ekle: bool = True) -> None:
    """Kaynak, kok, Arapca lemma ve meal birimleri (testin onkosulu; hat bunlari yazmaz)."""
    for slug, tur in ((QAC, "morfoloji"), (MEAL_O, "meal"), (MEAL_S, "meal")):
        conn.execute(
            "INSERT INTO icerik.source (slug, tur, baslik, surum, atif_metni)"
            " VALUES (%s, %s::icerik.source_kind, 'Deneme', '1', 'Deneme atif')",
            (slug, tur),
        )
    kok_haritasi = {k["letters_bw"]: k["letters"] for k in QAC_KOKLER}
    for bw, kimlik in ROOT_ID.items():
        if bw == "Amn" and not kok_ekle:
            continue
        conn.execute(
            "INSERT INTO icerik.root (id, letters, letters_bw, source_id, data_version)"
            " VALUES (%s, %s, %s, %s, 'deneme')",
            (kimlik, kok_haritasi[bw], bw, QAC),
        )
    for lm in QAC_LEMMALAR:
        ref = str(lm["qac_ref"])
        koku = lm["root_letters_bw"]
        if koku == "Amn" and not kok_ekle:
            continue
        conn.execute(
            "INSERT INTO icerik.lemma (id, lang, text, text_clean, root_id, qac_ref, origin,"
            " status, source_id, data_version) VALUES (%s, 'ar', %s, %s, %s, %s, 'qac', 'onayli',"
            " %s, 'deneme')",
            (AR_ID[ref], lm["text_clean"], lm["text_clean"], ROOT_ID[str(koku)], ref, QAC),
        )
    sira = 0
    for slug, birimler in MEAL_METINLERI.items():
        for capa, metin in birimler:
            sira += 1
            conn.execute(
                "INSERT INTO icerik.unit (anchor, kind, role, source_id, ord, metin, content_hash,"
                " data_version) VALUES (%s, 'meal', 'govde', %s, %s, %s, %s, 'deneme')",
                (capa, slug, sira, metin, content_hash(metin)),
            )


@pytest.fixture
def d(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TrDunya:
    return dunya_kur(tmp_path, monkeypatch)


def yukle(d: TrDunya, conn: psycopg.Connection, *, dry_run: bool = False) -> int:
    return pg.komut_export_pg(
        ayarlar_kur(d.tmp),
        depo_kok=d.kok,
        source=KAIKKI,
        dry_run=dry_run,
        baglanti=lambda: conn,
    )


def hepsi(d: TrDunya, conn: psycopg.Connection, **kw: object) -> int:
    """`enrich` + `qa run` + `export pg`."""
    assert d.enrich(min_sik=2) == 0
    assert d.qa() == 0
    return yukle(d, conn, **kw)  # type: ignore[arg-type]


def sayilar(d: TrDunya) -> dict[str, int]:
    raporlar = [json.loads(p.read_bytes()) for p in sorted((d.veri / "reports").glob("*.json"))]
    yuklemeler = [
        r
        for r in raporlar
        if r.get("komut") == "export pg" and r["parametreler"]["source"] == KAIKKI
    ]
    assert yuklemeler
    s = yuklemeler[-1]["sayilar"]
    assert isinstance(s, dict)
    return s


def say(conn: psycopg.Connection, sorgu: str, *param: object) -> int:
    satir = conn.execute(sorgu, param).fetchone()  # type: ignore[arg-type]
    assert satir is not None
    return int(satir[0])


def goruntu(conn: psycopg.Connection) -> dict[str, list[tuple[object, ...]]]:
    tablolar = {
        "lemma": "SELECT * FROM icerik.lemma WHERE lang = 'tr' ORDER BY id",
        "review": "SELECT * FROM icerik.review ORDER BY id",
        "tri": "SELECT * FROM icerik.tr_root_index ORDER BY anchor, span_start",
        "form": "SELECT * FROM icerik.tr_form ORDER BY key_narrow, tr_lemma_id",
        "unit": "SELECT anchor, metin, content_hash, rev, metin_durumu::text FROM icerik.unit"
        " ORDER BY anchor",
    }
    return {ad: [tuple(s) for s in conn.execute(q).fetchall()] for ad, q in tablolar.items()}


def tr_lemma(conn: psycopg.Connection, ad: str) -> tuple[object, ...]:
    satir = conn.execute(
        "SELECT id, status::text, onay_yolu, origin, root_id, ar_lemma_id, etymological_only,"
        " kanit, freq, source_id FROM icerik.lemma WHERE lang = 'tr' AND text_clean = %s",
        (ad,),
    ).fetchone()
    assert satir is not None
    return tuple(satir)


# --- ilk yukleme -----------------------------------------------------------------------------


def test_ilk_yukleme_lemma_review_indeks_ve_formlar(d: TrDunya, conn: psycopg.Connection) -> None:
    tohumla(conn)
    assert hepsi(d, conn) == 0
    s = sayilar(d)
    durumlar = conn.execute(
        "SELECT text_clean, status::text, onay_yolu FROM icerik.lemma WHERE lang = 'tr'"
        " ORDER BY text_clean"
    ).fetchall()
    assert [tuple(x) for x in durumlar] == [
        ("bobin", "aday", None),
        ("dolap", "onayli", "otomatik"),
        ("emin", "onayli", "otomatik"),
        ("fisto", "aday", None),
        ("kalem", "aday", None),
        ("kelin", "aday", None),
        ("morta", "aday", None),
        ("pelin", "onayli", "otomatik"),
        ("tavan", "onayli", "otomatik"),
        ("zorba", "aday", None),
    ]  # K-51 madde 9: kok onerisi olmayan adaylar da satir ve editor kuyrugu alir
    assert s["lemma_eklenen"] == 10 and s["lemma_aday_kok_onerisiz_eklenen"] == 4
    assert s["span_hata"] == 0 and s["onayli_lemma"] == 4

    kimlik, durum, yol, koken, kok, ar, etim, kanit, freq, kaynak = tr_lemma(conn, "dolap")
    assert (durum, yol, koken, kaynak, etim, freq) == (
        "onayli",
        "otomatik",
        "kaikki",
        KAIKKI,
        False,
        3,
    )
    assert kok == ROOT_ID["Sml"] and ar == AR_ID["samal"]
    assert isinstance(kanit, dict) and kanit["qac"]["root_id"] == kok  # type: ignore[index]
    assert kanit["qac"]["ar_lemma_id"] == ar and kanit["politika_surumu"] == "1"  # type: ignore[index]
    tavan = tr_lemma(conn, "tavan")
    assert tavan[4] == ROOT_ID["bnr"] and tavan[5] is None and tavan[6] is False
    # aday: kok onerisi lemma satirinda DEGIL (review ve kanit icinde)
    kalem = tr_lemma(conn, "kalem")
    assert kalem[1] == "aday" and kalem[2] is None and kalem[4] is None and kalem[7] is not None
    assert kimlik > max(AR_ID.values())  # yeni kimlikler Arapca lemmalarin ustunden


def test_kok_onerisiz_adaylar_satir_ve_review_alir(d: TrDunya, conn: psycopg.Connection) -> None:
    """Homograf, cok adayli QAC, kok cakismasi ve serbest metin kanitli adaylar (K-51 madde 9)."""
    tohumla(conn)
    assert d.enrich(min_sik=1) == 0
    assert d.qa() == 0
    assert yukle(d, conn) == 0
    s = sayilar(d)
    assert s["lemma_aday_kok_onerisiz_eklenen"] == 4 and s["review_esik_alti"] == 0
    for ad, neden in (
        ("zorba", "kok_cakismasi"),
        ("morta", "cok_adayli_qac"),
        ("kelin", "tr_ota_kok_cakismasi"),
        ("fisto", "yalniz_serbest_metin"),
    ):
        kimlik, durum, yol, koken, kok, ar, etim, kanit, freq, kaynak = tr_lemma(conn, ad)
        assert (durum, yol, kok, ar, etim, koken, kaynak) == (
            "aday",
            None,
            None,
            None,
            False,
            "kaikki",
            KAIKKI,
        )
        assert isinstance(kanit, dict) and kanit["neden"] == neden and freq == 1
        satirlar = conn.execute(
            "SELECT hedef_tablo, alan, eylem, durum::text, koken::text, oneren, guven, xref_id,"
            " onerilen FROM icerik.review WHERE hedef_anahtar = %s",
            (str(kimlik),),
        ).fetchall()
        assert len(satirlar) == 1, ad
        tablo, alan, eylem, rdurum, rkoken, oneren, guven, xref_id, onerilen = satirlar[0]
        assert (tablo, alan, eylem, rdurum, rkoken, oneren) == (
            "lemma",
            "kok_eslemesi",
            "oner",
            "acik",
            "hat",
            "hat",
        )
        assert guven is None and xref_id is None
        assert onerilen["root_id"] is None and onerilen["ar_lemma_id"] is None
        assert onerilen["etymological_only"] is False and onerilen["neden"] == neden
        assert set(onerilen) == {
            "root_id",
            "ar_lemma_id",
            "etymological_only",
            "neden",
            "kanit_ozeti",
            "aday_kokler",
        }
    zorba = conn.execute(
        "SELECT onerilen -> 'aday_kokler' FROM icerik.review WHERE hedef_anahtar = %s",
        (str(tr_lemma(conn, "zorba")[0]),),
    ).fetchone()
    assert zorba is not None and len(zorba[0]) == 2
    assert {k["kaynak"] for k in zorba[0]} == {QAC} and all(k["letters"] for k in zorba[0])
    # fisto: serbest metin, QAC adayi yok -> aday_kokler bos
    fisto = conn.execute(
        "SELECT onerilen -> 'aday_kokler' FROM icerik.review WHERE hedef_anahtar = %s",
        (str(tr_lemma(conn, "fisto")[0]),),
    ).fetchone()
    assert fisto is not None and fisto[0] == []
    # ikinci kosu: 0 degisiklik
    ilk = goruntu(conn)
    assert d.enrich(min_sik=1, force=True) == 0
    assert d.qa() == 0
    assert yukle(d, conn) == 0
    assert sayilar(d)["review_eklenen"] == 0 and sayilar(d)["lemma_eklenen"] == 0
    assert goruntu(conn) == ilk


def test_kok_onerisiz_aday_editor_satirina_dokunulmaz(d: TrDunya, conn: psycopg.Connection) -> None:
    tohumla(conn)
    assert d.enrich(min_sik=1) == 0
    assert d.qa() == 0
    assert yukle(d, conn) == 0
    conn.execute(
        "UPDATE icerik.lemma SET status = 'onayli', onay_yolu = 'editor', origin = 'editor',"
        " root_id = %s WHERE lang = 'tr' AND text_clean = 'zorba'",
        (ROOT_ID["Sml"],),
    )
    conn.execute(
        "UPDATE icerik.review SET durum = 'onaylandi' WHERE hedef_anahtar = %s",
        (str(tr_lemma(conn, "zorba")[0]),),
    )
    once = tr_lemma(conn, "zorba")
    assert d.enrich(min_sik=1, force=True) == 0
    assert d.qa() == 0
    assert yukle(d, conn) == 0
    assert tr_lemma(conn, "zorba") == once
    assert sayilar(d)["lemma_editor_korunan"] == 1 and sayilar(d)["review_eklenen"] == 0


def test_review_yalniz_esigi_gecen_adaya_acilir(d: TrDunya, conn: psycopg.Connection) -> None:
    tohumla(conn)
    assert hepsi(d, conn) == 0
    satirlar = conn.execute(
        "SELECT hedef_tablo, hedef_anahtar, alan, eylem, durum::text, koken::text, oneren, guven,"
        " onceki, onerilen FROM icerik.review"
    ).fetchall()
    assert len(satirlar) == 1  # kalem (siklik 3); bobin ve 4 oneri-siz aday siklik 1 < 2
    tablo, anahtar, alan, eylem, durum, koken, oneren, guven, onceki, onerilen = satirlar[0]
    kalem_id = tr_lemma(conn, "kalem")[0]
    assert (tablo, anahtar, alan, eylem) == ("lemma", str(kalem_id), "kok_eslemesi", "oner")
    assert (durum, koken, oneren, guven, onceki) == ("acik", "hat", "hat", None, None)
    assert onerilen["root_id"] == ROOT_ID["bnr"] and onerilen["ar_lemma_id"] is None
    assert onerilen["etymological_only"] is False and onerilen["neden"] == "pos_uyusmazligi"
    assert set(onerilen["kanit_ozeti"]) == {
        "politika_surumu",
        "eslesme",
        "kaynak_sayisi",
        "maddeler",
    }
    assert sayilar(d)["review_esik_alti"] == 5  # esik alti rapora yazilir (bobin + 4 aday)


def test_tr_root_index_aralik_hash_ve_guncel_metin(d: TrDunya, conn: psycopg.Connection) -> None:
    tohumla(conn)
    assert hepsi(d, conn) == 0
    assert sayilar(d)["tri_eklenen"] == 10  # tavan 3, dolap 3, emin 2, pelin 2
    satirlar = conn.execute(
        "SELECT t.anchor, t.span_start, t.span_end, t.root_id, t.tr_lemma_id, t.etymological_only,"
        " t.unit_hash, u.metin, u.content_hash, l.text_clean FROM icerik.tr_root_index t"
        " JOIN icerik.unit u ON u.anchor = t.anchor JOIN icerik.lemma l ON l.id = t.tr_lemma_id"
    ).fetchall()
    assert len(satirlar) == 10
    for _capa, bas, son, kok, _lemma_id, etim, ozet, metin, tam_ozet, lemma in satirlar:
        assert 0 <= bas < son <= len(metin)  # yari acik, metin uzunlugu icinde
        assert lower_turkish(metin[bas:son]) == lemma  # kod noktasi dilimi lemmanin bicimi
        assert ozet == tam_ozet[:16] and etim is False
        assert kok == tr_lemma(conn, lemma)[4]
    # izafet ekinin (`tavan-i`) `i` parcasi ve kesme eki (`Tavan'in`) indekse girmez
    sade = [r for r in satirlar if r[0] == "meal:elmalili-sade:1:1"]
    assert [(r[1], r[2]) for r in sade] == [(0, 5)]  # yalniz `Tavan`
    assert say(conn, "SELECT count(*) FROM icerik.tr_root_index WHERE span_start = span_end") == 0
    assert span_hatalari(conn) == {
        "aralik_gecersiz": 0,
        "birim_yok": 0,
        "metin_disi": 0,
        "ozet_eski": 0,
        "onaysiz_lemma": 0,
    }
    assert db_g_cap(conn).gecti


def test_tr_form_onayli_lemmalarin_bicimleri(d: TrDunya, conn: psycopg.Connection) -> None:
    tohumla(conn)
    assert hepsi(d, conn) == 0
    satirlar = conn.execute(
        "SELECT f.key_narrow, f.key_wide, f.freq, l.text_clean FROM icerik.tr_form f"
        " JOIN icerik.lemma l ON l.id = f.tr_lemma_id ORDER BY f.key_narrow"
    ).fetchall()
    assert [tuple(r) for r in satirlar] == [
        ("dolap", "dolap", 3, "dolap"),
        ("emin", "emin", 2, "emin"),
        ("pelin", "pelin", 2, "pelin"),
        ("tavan", "tavan", 3, "tavan"),
    ]


def test_hat_meal_metnine_yazmaz(d: TrDunya, conn: psycopg.Connection) -> None:
    tohumla(conn)
    once = goruntu(conn)["unit"]
    assert hepsi(d, conn) == 0
    assert goruntu(conn)["unit"] == once


# --- idempotentlik ---------------------------------------------------------------------------


def test_ikinci_yukleme_sifir_degisiklik(d: TrDunya, conn: psycopg.Connection) -> None:
    tohumla(conn)
    assert hepsi(d, conn) == 0
    ilk = goruntu(conn)
    assert hepsi(d, conn) == 0  # yeni enrich calismasi, ayni girdi
    s = sayilar(d)
    for ad in (
        "lemma_eklenen",
        "lemma_guncellenen",
        "lemma_adaya_donen",
        "lemma_yukselen",
        "lemma_yenilenen",
        "review_eklenen",
        "tri_eklenen",
        "tri_silinen",
        "tri_guncellenen",
        "form_eklenen",
        "form_silinen",
        "form_guncellenen",
    ):
        assert s[ad] == 0, ad
    assert s["tri_degismeyen"] == 10 and s["form_degismeyen"] == 4
    assert goruntu(conn) == ilk


def test_dry_run_hicbir_sey_yazmaz(d: TrDunya, conn: psycopg.Connection) -> None:
    tohumla(conn)
    once = goruntu(conn)
    assert hepsi(d, conn, dry_run=True) == 0
    assert goruntu(conn) == once
    assert say(conn, "SELECT count(*) FROM icerik.source WHERE slug = %s", KAIKKI) == 0


# --- koruma kurallari ------------------------------------------------------------------------


def _kaikki_degistir(d: TrDunya, *, tavan_kanitsiz: bool = False, bobin_tek: bool = False) -> None:
    tr = kaikki_tr_satirlari()
    if tavan_kanitsiz:
        for s in tr:
            if s["word"] == "tavan":
                s["etymology_templates"] = []
    if bobin_tek:
        tr = [s for s in tr if not (s["word"] == "bobin" and not s["etymology_templates"])]
    kaikki_yaz(d, tr, kaikki_ota_satirlari())


def test_editor_satirina_hic_dokunulmaz(d: TrDunya, conn: psycopg.Connection) -> None:
    tohumla(conn)
    assert hepsi(d, conn) == 0
    conn.execute(
        "UPDATE icerik.lemma SET onay_yolu = 'editor', origin = 'editor', root_id = %s,"
        " etymological_only = true, kanit = NULL WHERE lang = 'tr' AND text_clean = 'tavan'",
        (ROOT_ID["Sml"],),
    )
    editor_once = tr_lemma(conn, "tavan")
    _kaikki_degistir(d, tavan_kanitsiz=True)  # hat artik kosulu saglamiyor
    assert hepsi(d, conn) == 0
    assert tr_lemma(conn, "tavan") == editor_once
    s = sayilar(d)
    assert s["lemma_editor_korunan"] == 1 and s["lemma_adaya_donen"] == 0
    # onayli editor lemmasi indekste kalir ve editorun kokunu kullanir
    kokler = conn.execute(
        "SELECT DISTINCT t.root_id, t.etymological_only FROM icerik.tr_root_index t"
        " WHERE t.tr_lemma_id = %s",
        (editor_once[0],),
    ).fetchall()
    assert [tuple(k) for k in kokler] == [(ROOT_ID["Sml"], True)]
    assert (
        say(
            conn, "SELECT count(*) FROM icerik.review WHERE hedef_anahtar = %s", str(editor_once[0])
        )
        == 0
    )


def test_otomatik_satirin_kaniti_kaybolursa_aday_ve_review(
    d: TrDunya, conn: psycopg.Connection
) -> None:
    tohumla(conn)
    assert hepsi(d, conn) == 0
    once = tr_lemma(conn, "tavan")
    assert once[1] == "onayli" and once[2] == "otomatik"
    _kaikki_degistir(d, tavan_kanitsiz=True)
    assert hepsi(d, conn) == 0
    simdi = tr_lemma(conn, "tavan")
    assert simdi[1] == "aday" and simdi[2] is None  # onay yolu da temizlenir
    assert simdi[4] == once[4]  # eski kok bilgisi satirda kalir (review.onceki)
    assert simdi[7]["karar"] == "kok_yok"  # type: ignore[index]
    s = sayilar(d)
    assert s["lemma_adaya_donen"] == 1 and s["review_eklenen"] == 1
    review = conn.execute(
        "SELECT onceki, onerilen, durum::text FROM icerik.review WHERE hedef_anahtar = %s",
        (str(once[0]),),
    ).fetchall()
    assert len(review) == 1 and review[0][2] == "acik"
    assert review[0][0]["root_id"] == once[4] and review[0][0]["onay_yolu"] == "otomatik"
    assert review[0][1]["neden"] == "kanit_yok" and review[0][1]["etymological_only"] is False
    # tr_root_index ve tr_form artik tavan'i icermez
    assert (
        say(conn, "SELECT count(*) FROM icerik.tr_root_index WHERE tr_lemma_id = %s", once[0]) == 0
    )
    assert say(conn, "SELECT count(*) FROM icerik.tr_form WHERE tr_lemma_id = %s", once[0]) == 0
    assert s["tri_silinen"] == 3 and s["form_silinen"] == 1
    # ucuncu kosu: ayni durum, ikinci review acilmaz
    assert hepsi(d, conn) == 0
    assert sayilar(d)["review_eklenen"] == 0 and sayilar(d)["lemma_adaya_donen"] == 0


def test_red_satiri_geri_acilmaz(d: TrDunya, conn: psycopg.Connection) -> None:
    tohumla(conn)
    assert hepsi(d, conn) == 0
    conn.execute("UPDATE icerik.lemma SET status = 'red' WHERE text_clean = 'kalem'")
    conn.execute("UPDATE icerik.review SET durum = 'reddedildi' WHERE hedef_tablo = 'lemma'")
    once = tr_lemma(conn, "kalem")
    assert hepsi(d, conn) == 0
    assert tr_lemma(conn, "kalem") == once
    assert sayilar(d)["lemma_red_korunan"] == 1 and sayilar(d)["review_eklenen"] == 0


@pytest.mark.parametrize("durum", ["acik", "onaylandi", "reddedildi", "geri_alindi"])
def test_ayni_hedef_icin_herhangi_durumda_review_varsa_yenisi_acilmaz(
    d: TrDunya, conn: psycopg.Connection, durum: str
) -> None:
    tohumla(conn)
    assert hepsi(d, conn) == 0
    conn.execute(
        "UPDATE icerik.review SET durum = %s::icerik.inceleme_durumu WHERE hedef_tablo = 'lemma'",
        (durum,),
    )
    assert hepsi(d, conn) == 0
    assert say(conn, "SELECT count(*) FROM icerik.review WHERE hedef_tablo = 'lemma'") == 1
    assert sayilar(d)["review_eklenen"] == 0


def test_hat_adayi_review_yoksa_kosul_saglaninca_otomatiğe_yukselir(
    d: TrDunya, conn: psycopg.Connection
) -> None:
    """`bobin` homograf adayiydi (review yok: siklik esik altinda); kaynak duzelince onaylanir."""
    tohumla(conn)
    assert hepsi(d, conn) == 0
    assert tr_lemma(conn, "bobin")[1] == "aday"
    _kaikki_degistir(d, bobin_tek=True)
    assert hepsi(d, conn) == 0
    bobin = tr_lemma(conn, "bobin")
    assert (bobin[1], bobin[2], bobin[4]) == ("onayli", "otomatik", ROOT_ID["bnr"])
    assert sayilar(d)["lemma_yukselen"] == 1
    # review'u olan aday (kalem) yukseltilmez; yalnizca kanit/siklik yenilenir
    assert tr_lemma(conn, "kalem")[1] == "aday"
    assert (
        say(conn, "SELECT count(*) FROM icerik.tr_root_index WHERE tr_lemma_id = %s", bobin[0]) == 1
    )


# --- metin degisimi ve G-CAP uzantisi --------------------------------------------------------


def test_aralik_veritabanindaki_guncel_metinden_yeniden_hesaplanir(
    d: TrDunya, conn: psycopg.Connection
) -> None:
    tohumla(conn)
    assert hepsi(d, conn) == 0
    capa = "meal:elmalili:1:1"
    yeni = "Deneme Deneme tavan ve dolap, tavan-i dolap."  # editor duzeltmesi: metin degisti
    conn.execute(
        "UPDATE icerik.unit SET metin = %s, content_hash = %s WHERE anchor = %s",
        (yeni, content_hash(yeni), capa),
    )
    # yukleme oncesi: eski aralik ve ozet eskidir (G-CAP uzantisi bunu yakalar)
    hatalar = span_hatalari(conn)
    assert hatalar["ozet_eski"] > 0
    assert not db_g_cap(conn).gecti
    assert yukle(d, conn) == 0  # ayni staged calismasi; metin veritabanindan okunur
    s = sayilar(d)
    assert s["tri_guncellenen"] + s["tri_eklenen"] + s["tri_silinen"] > 0
    assert span_hatalari(conn)["ozet_eski"] == 0 and db_g_cap(conn).gecti
    satirlar = conn.execute(
        "SELECT span_start, span_end, unit_hash FROM icerik.tr_root_index WHERE anchor = %s"
        " ORDER BY span_start",
        (capa,),
    ).fetchall()
    assert all(r[2] == content_hash(yeni)[:16] for r in satirlar)
    assert [yeni[r[0] : r[1]] for r in satirlar] == ["tavan", "dolap", "tavan", "dolap"]


def test_g_cap_uzantisi_metin_disi_ve_birim_yok_ihlallerini_yakalar(
    d: TrDunya, conn: psycopg.Connection
) -> None:
    tohumla(conn)
    assert hepsi(d, conn) == 0
    conn.execute(
        "UPDATE icerik.unit SET metin = 'Deneme', content_hash = %s"
        " WHERE anchor = 'meal:elmalili:1:2'",
        (content_hash("Deneme"),),
    )
    assert span_hatalari(conn)["metin_disi"] >= 1
    assert not db_g_cap(conn).gecti
    assert any("metin_disi" in b for b in db_g_cap(conn).bulgular)


# --- onkosullar ------------------------------------------------------------------------------


def test_qac_koku_veritabaninda_yoksa_cikis_2(d: TrDunya, conn: psycopg.Connection) -> None:
    tohumla(conn, kok_ekle=False)
    assert d.enrich(min_sik=2) == 0 and d.qa() == 0
    assert yukle(d, conn) == 2
    assert say(conn, "SELECT count(*) FROM icerik.lemma WHERE lang = 'tr'") == 0


def test_qa_raporu_yoksa_yukleme_yapilmaz(d: TrDunya, conn: psycopg.Connection) -> None:
    tohumla(conn)
    assert d.enrich(min_sik=2) == 0
    assert yukle(d, conn) == 1  # QA raporu yok: cikis 1
    assert say(conn, "SELECT count(*) FROM icerik.lemma WHERE lang = 'tr'") == 0


def test_enrich_calismasi_yoksa_cikis_2(d: TrDunya, conn: psycopg.Connection) -> None:
    tohumla(conn)
    assert yukle(d, conn) == 2
