"""`export pg --source sure-adlari-vikipedi`: surah_alias adaylari ve review (A11.3; SENTETIK).

Sentetik sure adi zinciri (`sure_adlari_zinciri`) `mutalaa_test` veritabanina yuklenir. Testler dis
islem icinde kosar ve sonunda geri alinir. Veritabani yoksa atlanir
(`MUTALAA_DEGISMEZLIK_ZORUNLU=1` atlamayi hataya cevirir). Yazma kurali: yalniz ekler; var olan
satira ve var olan review'a dokunulmaz. Hicbir sure adi ya da sayi hafizadan yazilmaz.
"""

import json
import os
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import psycopg
import pytest
from hat_yardimci import ayarlar_kur
from sure_adlari_yardimci import SURE_SAYISI, SureAdlariZinciri, ad
from zincir_yardimci import ortam_kur, sablon_kopyala

from mutalaa_pipeline import lineage
from mutalaa_pipeline.config import Ayarlar
from mutalaa_pipeline.db import baglan
from mutalaa_pipeline.export import pg
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.ingest.sure_adlari import KAYNAK, QURAN_META
from mutalaa_pipeline.lineage import ALIASLAR_ADI


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
            "SELECT (SELECT count(*) FROM icerik.surah_alias)"
            " + (SELECT count(*) FROM icerik.review WHERE hedef_tablo = 'surah_alias')"
            " + (SELECT count(*) FROM icerik.source WHERE slug = ANY(%s))",
            ([KAYNAK, QURAN_META],),
        ).fetchone()
        assert kalinti is not None
        if kalinti[0] != 0:
            baglanti.rollback()
            _yok("mutalaa_test icinde surah_alias/review/sure-adlari-vikipedi satiri kalmis")
        yield baglanti
    finally:
        baglanti.rollback()
        baglanti.close()


@pytest.fixture
def sz(
    sure_adlari_zinciri: SureAdlariZinciri, monkeypatch: pytest.MonkeyPatch
) -> SureAdlariZinciri:
    sure_adlari_zinciri.ortam(monkeypatch)
    return sure_adlari_zinciri


def yukle(sz: SureAdlariZinciri, conn: psycopg.Connection, **kw: object) -> int:
    return pg.komut_export_pg(
        ayarlar_kur(sz.uz.z.tmp),
        depo_kok=sz.uz.z.kok,
        source=KAYNAK,
        baglanti=lambda: conn,
        **kw,  # type: ignore[arg-type]
    )


def son_sayilar(sz: SureAdlariZinciri) -> dict[str, int]:
    raporlar = [
        json.loads(yol.read_bytes())
        for yol in sorted((sz.uz.z.veri_kok / "reports").glob("*.json"))
    ]
    yuklemeler = [
        r for r in raporlar if r["komut"] == "export pg" and r["parametreler"]["source"] == KAYNAK
    ]
    assert yuklemeler
    sayilar = yuklemeler[-1]["sayilar"]
    assert isinstance(sayilar, dict)
    return sayilar


def say(conn: psycopg.Connection, sorgu: str, *param: object) -> int:
    satir = conn.execute(sorgu, param).fetchone()  # type: ignore[arg-type]
    assert satir is not None
    return int(satir[0])


def staged(sz: SureAdlariZinciri) -> list[dict[str, Any]]:
    son = lineage.son_basarili(sz.uz.z.veri_kok / "staged" / KAYNAK, "anchor")
    assert son is not None
    return [json.loads(s) for s in (son[1] / ALIASLAR_ADI).read_bytes().splitlines()]


DOKUZ_SORGUSU = (
    "SELECT kind, risky, status::text FROM icerik.surah_alias WHERE surah_no = 9 AND alias = %s"
)


def alias_say(conn: psycopg.Connection) -> int:
    return say(conn, "SELECT count(*) FROM icerik.surah_alias")


def review_say(conn: psycopg.Connection) -> int:
    return say(conn, "SELECT count(*) FROM icerik.review WHERE hedef_tablo = 'surah_alias'")


@pytest.mark.veritabani
def test_ilk_yukleme_aday_ve_review_ikinci_kosu_sifir_degisiklik(
    sz: SureAdlariZinciri, conn: psycopg.Connection
) -> None:
    adaylar = staged(sz)
    assert yukle(sz, conn) == 0
    ilk = son_sayilar(sz)
    assert ilk["aday_staging"] == ilk["aday_eklenen"] == ilk["review_eklenen"] == len(adaylar)
    assert (ilk["aday_degismeyen"], ilk["mevcut_farkli"], ilk["mevcut_aday_disi"]) == (0, 0, 0)
    assert (ilk["kaynak_eklenen"], ilk["kaynak_guncellenen"]) == (1, 0)
    assert alias_say(conn) == review_say(conn) == len(adaylar)
    assert say(conn, "SELECT count(*) FROM icerik.surah_alias WHERE status <> 'aday'") == 0
    # 114 sure icin tam bir kanonik aday ve onun review kaydi
    assert (
        say(conn, "SELECT count(DISTINCT surah_no) FROM icerik.surah_alias WHERE kind = 'kanonik'")
        == SURE_SAYISI
    )
    assert (
        say(conn, "SELECT count(*) FROM icerik.surah_alias WHERE kind = 'kanonik'") == SURE_SAYISI
    )
    assert (
        say(
            conn,
            "SELECT count(*) FROM icerik.review r JOIN icerik.surah_alias a"
            " ON r.hedef_anahtar = a.surah_no::text || ':' || a.alias"
            " WHERE r.hedef_tablo = 'surah_alias' AND a.kind = 'kanonik'",
        )
        == SURE_SAYISI
    )
    # yalniz sure-adlari-vikipedi kaynagi yazilir
    assert say(conn, "SELECT count(*) FROM icerik.source WHERE slug = %s", KAYNAK) == 1
    assert say(conn, "SELECT count(*) FROM icerik.source WHERE slug = %s", QURAN_META) == 0

    once = conn.execute("SELECT * FROM icerik.review ORDER BY id").fetchall()
    kimlik = conn.execute(
        "SELECT last_value FROM pg_sequences WHERE sequencename = 'review_id_seq'"
    ).fetchone()
    assert yukle(sz, conn) == 0  # ikinci kosu: hicbir satir degismez
    ikinci = son_sayilar(sz)
    assert (ikinci["aday_eklenen"], ikinci["review_eklenen"]) == (0, 0)
    assert ikinci["aday_degismeyen"] == len(adaylar) and ikinci["kaynak_degismeyen"] == 1
    assert conn.execute("SELECT * FROM icerik.review ORDER BY id").fetchall() == once
    assert (
        conn.execute(
            "SELECT last_value FROM pg_sequences WHERE sequencename = 'review_id_seq'"
        ).fetchone()
        == kimlik
    )  # IDENTITY harcanmadi


@pytest.mark.veritabani
def test_review_satiri_k43_madde_4_alanlari(
    sz: SureAdlariZinciri, conn: psycopg.Connection
) -> None:
    assert yukle(sz, conn) == 0
    for aday in staged(sz)[:: max(1, len(staged(sz)) // 60)]:  # seyrek orneklem
        satir = conn.execute(
            "SELECT alan, eylem, onceki, onerilen, durum::text, koken::text, oneren, xref_id,"
            " yz_modeli, yz_kaydi, guven FROM icerik.review"
            " WHERE hedef_tablo = 'surah_alias' AND hedef_anahtar = %s",
            (f"{aday['surah_no']}:{aday['alias']}",),
        ).fetchone()
        assert satir is not None
        assert satir[:2] == ("status", "oner")
        assert satir[2] is None
        assert satir[3] == aday["onerilen"]
        assert satir[4:7] == ("acik", "hat", "hat")
        assert satir[7:] == (None, None, None, None)
        alanlar = set(satir[3])
        assert {"kind", "alias", "risky", "kaynaklar", "yazimlar"} <= alanlar
        assert ("anlam" in alanlar) == (aday["kind"] == "kanonik")


@pytest.mark.veritabani
def test_surah_alias_satiri_staged_ile_ayni_ve_sutunlar(
    sz: SureAdlariZinciri, conn: psycopg.Connection
) -> None:
    assert yukle(sz, conn) == 0
    sutunlar = [
        r[0]
        for r in conn.execute(
            "SELECT column_name FROM information_schema.columns"
            " WHERE table_schema = 'icerik' AND table_name = 'surah_alias'"
            " ORDER BY ordinal_position"
        ).fetchall()
    ]
    assert sutunlar == ["surah_no", "alias", "alias_key", "kind", "risky", "status"]
    for a in staged(sz)[::7]:
        satir = conn.execute(
            "SELECT alias_key, kind, risky, status::text FROM icerik.surah_alias"
            " WHERE surah_no = %s AND alias = %s",
            (a["surah_no"], a["alias"]),
        ).fetchone()
        assert satir == (a["alias_key"], a["kind"], a["risky"], "aday")
    assert say(conn, "SELECT count(*) FROM icerik.surah_alias WHERE risky") == sum(
        1 for a in staged(sz) if a["risky"]
    )


@pytest.mark.veritabani
def test_dry_run_hicbir_satir_yazmaz(sz: SureAdlariZinciri, conn: psycopg.Connection) -> None:
    assert yukle(sz, conn, dry_run=True) == 0
    assert son_sayilar(sz)["aday_eklenen"] == len(staged(sz))  # yazilsaydi
    assert (alias_say(conn), review_say(conn)) == (0, 0)
    assert say(conn, "SELECT count(*) FROM icerik.source WHERE slug = %s", KAYNAK) == 0


@pytest.mark.veritabani
def test_onayli_ya_da_red_satir_ve_editor_degeri_uzerine_yazilmaz(
    sz: SureAdlariZinciri, conn: psycopg.Connection
) -> None:
    assert yukle(sz, conn) == 0
    toplam, inceleme = alias_say(conn), review_say(conn)
    kanonik = ad(5)
    conn.execute(
        "UPDATE icerik.surah_alias SET status = 'onayli', risky = false, alias_key = 'editor'"
        " WHERE surah_no = 5 AND alias = %s",
        (kanonik,),
    )
    conn.execute(
        "UPDATE icerik.surah_alias SET status = 'red' WHERE surah_no = 6 AND kind = 'kanonik'"
    )
    conn.execute(
        "UPDATE icerik.review SET durum = 'onaylandi', inceleyen = 'editor'"
        " WHERE hedef_tablo = 'surah_alias' AND hedef_anahtar = %s",
        (f"5:{kanonik}",),
    )
    assert yukle(sz, conn) == 0
    sayilar = son_sayilar(sz)
    assert (sayilar["aday_eklenen"], sayilar["review_eklenen"]) == (0, 0)
    assert sayilar["mevcut_farkli"] >= 1 and sayilar["mevcut_aday_disi"] == 2
    satir = conn.execute(
        "SELECT status::text, risky, alias_key FROM icerik.surah_alias"
        " WHERE surah_no = 5 AND alias = %s",
        (kanonik,),
    ).fetchone()
    assert satir == ("onayli", False, "editor")  # editorun degeri korunur
    assert (
        say(conn, "SELECT count(*) FROM icerik.surah_alias WHERE surah_no = 6 AND status = 'red'")
        == 1
    )
    assert (alias_say(conn), review_say(conn)) == (toplam, inceleme)
    durum = conn.execute(
        "SELECT durum::text, inceleyen FROM icerik.review WHERE hedef_anahtar = %s",
        (f"5:{kanonik}",),
    ).fetchone()
    assert durum == ("onaylandi", "editor")


@pytest.mark.veritabani
def test_aday_satir_farkli_degerle_gelirse_degistirilmez_ve_sayilir(
    sz: SureAdlariZinciri, conn: psycopg.Connection
) -> None:
    assert yukle(sz, conn) == 0
    conn.execute(
        "UPDATE icerik.surah_alias SET kind = 'diger_ad', risky = NOT risky"
        " WHERE surah_no = 9 AND kind = 'kanonik'"
    )
    onceki = conn.execute(
        DOKUZ_SORGUSU,
        (ad(9),),
    ).fetchone()
    assert yukle(sz, conn) == 0
    assert son_sayilar(sz)["mevcut_farkli"] == 1
    assert (
        conn.execute(
            DOKUZ_SORGUSU,
            (ad(9),),
        ).fetchone()
        == onceki
    )


@pytest.mark.veritabani
def test_silinen_alias_yeniden_eklenir_ama_var_olan_review_icin_yenisi_acilmaz(
    sz: SureAdlariZinciri, conn: psycopg.Connection
) -> None:
    assert yukle(sz, conn) == 0
    inceleme = review_say(conn)
    conn.execute("DELETE FROM icerik.surah_alias WHERE surah_no = 7 AND kind = 'kanonik'")
    assert yukle(sz, conn) == 0
    sayilar = son_sayilar(sz)
    assert sayilar["aday_eklenen"] == 1 and sayilar["review_eklenen"] == 0
    assert review_say(conn) == inceleme


@pytest.mark.veritabani
def test_staged_de_olmayan_aday_silinmez_ve_sayilir(
    sz: SureAdlariZinciri, conn: psycopg.Connection
) -> None:
    assert yukle(sz, conn) == 0
    conn.execute(
        "INSERT INTO icerik.surah_alias (surah_no, alias, alias_key, kind)"
        " VALUES (1, 'Elle', 'elle', 'diger_ad')"
    )
    assert yukle(sz, conn) == 0
    assert son_sayilar(sz)["db_disi_aday"] == 1
    assert say(conn, "SELECT count(*) FROM icerik.surah_alias WHERE alias = 'Elle'") == 1


@pytest.mark.veritabani
def test_qa_raporu_olmadan_ya_da_ozet_tutmuyorsa_cikis_1_baglanti_acilmaz(
    sz: SureAdlariZinciri, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    kopya = sablon_kopyala(sz.uz.z.tmp, tmp_path / "k")
    sz.ortam(monkeypatch)
    ortam_kur(kopya, monkeypatch)
    for rapor in (kopya.veri_kok / "reports").glob("*.json"):
        veri = json.loads(rapor.read_bytes())
        if veri.get("komut") == "qa run" and veri.get("kaynak") == KAYNAK:
            veri["units_sha256"] = "0" * 64
            rapor.write_bytes(json.dumps(veri).encode("utf-8"))

    def baglanti() -> psycopg.Connection:
        raise AssertionError("baglanti acilmamali")

    kod = pg.komut_export_pg(
        ayarlar_kur(kopya.tmp), depo_kok=kopya.kok, source=KAYNAK, baglanti=baglanti
    )
    assert kod == 1


def test_yukleme_sozlesmesi_yalniz_ekler() -> None:
    from mutalaa_pipeline.export import pg_sure_adlari

    for sorgu in (pg_sure_adlari.INSERT_REVIEW, pg_sure_adlari.INSERT_ALIAS):
        buyuk = sorgu.upper()
        assert "DELETE" not in buyuk and "UPDATE" not in buyuk
        assert "ON CONFLICT" not in buyuk
    assert "'aday'" not in pg_sure_adlari.INSERT_ALIAS  # status sutun varsayilanidir
    assert KAYNAK in pg.SURE_ADI_KAYNAKLARI and pg.EK_KAYNAKLAR[KAYNAK] == ()
