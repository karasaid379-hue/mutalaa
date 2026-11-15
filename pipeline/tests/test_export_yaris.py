"""`export pg` silme deyimlerinde eszamanli karar korumasi (A18 inceleme 5): SENTETIK satirlar.

Senaryo (iki gercek baglanti): `A` yuklemenin SIL deyimlerini calistirir; `B` ayni satirlari
onaylar ama henuz commit etmemistir, bu yuzden `A` satir kilidinde bekler. `B` commit edince
PostgreSQL (READ COMMITTED) yalniz DIS tablonun yeni satir surumunu yeniden sinar; `IN (alt sorgu)`
listesi deyim basinda hesaplandigi icin onay eski listede hala "silinebilir" gorunur. Koruma, hat
sahipligi ve dokunulmamislik kosullarinin DIS `DELETE`'te de yazili olmasidir (`pg_xref.SIL`
deseni).

Test kalici (commit edilmis) satir yazar ve `finally` ile temizler; `mutalaa_test` icinde baska
`xref`/`review` satiri varsa atlanir. Veritabani yoksa atlanir (`MUTALAA_DEGISMEZLIK_ZORUNLU=1`
atlamayi hataya cevirir). Capalar uydurmadir; hicbir Kur'an ya da meal metni yoktur.
"""

import os
import threading
import time
from collections.abc import Iterator
from dataclasses import dataclass

import psycopg
import pytest

from mutalaa_pipeline.config import Ayarlar
from mutalaa_pipeline.db import baglan
from mutalaa_pipeline.export import pg_xref, pg_xref_atif
from mutalaa_pipeline.export.ortak import GirdiHatasi

KAYNAK_CAPA = "meal:elmalili:900:1"  # sentetik; birim satiri gerekmez (xref'te capa FK'si yok)
HEDEF_CAPA = "q:900:1"
BEKLEME_SINIRI = 20.0


def _yok(neden: str) -> None:
    if os.environ.get("MUTALAA_DEGISMEZLIK_ZORUNLU") == "1":
        pytest.fail(neden)
    pytest.skip(neden)


@dataclass
class Yaris:
    a: psycopg.Connection  # silen yukleme
    b: psycopg.Connection  # eszamanli editor karari
    c: psycopg.Connection  # kurulum, gozlem ve temizlik (autocommit)
    xref_id: str


def _kur(tur: str) -> Iterator[Yaris]:
    try:
        a = baglan(Ayarlar(), test=True)
        b = baglan(Ayarlar(), test=True)
        c = baglan(Ayarlar(), test=True, autocommit=True)
    except GirdiHatasi as hata:
        _yok(f"test veritabani yok: {hata}")
        return
    xref_id: str | None = None
    try:
        kalinti = c.execute(
            "SELECT (SELECT count(*) FROM icerik.xref) + (SELECT count(*) FROM icerik.review"
            " WHERE hedef_tablo = 'xref')"
        ).fetchone()
        assert kalinti is not None
        if kalinti[0] != 0:
            _yok("mutalaa_test icinde xref/review satiri kalmis")
        satir = c.execute(
            "INSERT INTO icerik.xref (src_anchor, dst_anchor, type, score, confidence, origin,"
            " status, data_version) VALUES (%s, %s, %s::icerik.xref_type, 0.5, 0.5, 'hat', 'aday',"
            " 'yaris-testi') RETURNING id::text",
            (KAYNAK_CAPA, HEDEF_CAPA, tur),
        ).fetchone()
        assert satir is not None
        xref_id = str(satir[0])
        yield Yaris(a, b, c, xref_id)
    finally:
        a.rollback()
        b.rollback()
        if xref_id is not None:
            c.execute("DELETE FROM icerik.review WHERE xref_id = %s::uuid", (xref_id,))
            c.execute("DELETE FROM icerik.xref WHERE id = %s::uuid", (xref_id,))
        for k in (a, b, c):
            k.close()


@pytest.fixture
def atif_yarisi() -> Iterator[Yaris]:
    yield from _kur("atif")


@pytest.fixture
def baglanti_yarisi() -> Iterator[Yaris]:
    yield from _kur("benzer_ayet")


def _acik_review_ekle(y: Yaris) -> int:
    satir = y.c.execute(
        "INSERT INTO icerik.review (hedef_tablo, hedef_anahtar, xref_id, alan, eylem, onerilen,"
        " koken, oneren) VALUES ('xref', %s, %s::uuid, 'status', 'oner', '{}'::jsonb, 'hat', 'hat')"
        " RETURNING id",
        (y.xref_id, y.xref_id),
    ).fetchone()
    assert satir is not None
    return int(satir[0])


def _bos_staging(conn: psycopg.Connection, modul: object) -> None:
    """Hicbir satir uretilmedi: eldeki hat adayi 'uretilmeyen' sayilir (silinmeye aday)."""
    if modul is pg_xref_atif:
        pg_xref_atif._staging_yukle(conn, [])
    else:
        pg_xref._staging_yukle(conn, [])


def _eszamanli(
    y: Yaris, sorgular: list[tuple[str, dict[str, object]]], onay: list[str]
) -> list[int]:
    """`A` `sorgular`i calistirirken `B` `onay` deyimlerini commit eder; her deyimin rowcount'u."""
    sonuc: list[int] = []
    hata: list[BaseException] = []

    def silen() -> None:
        try:
            for sorgu, param in sorgular:
                sonuc.append(y.a.execute(sorgu, param).rowcount)
        except BaseException as e:  # ana is parcacigina aktarilir
            hata.append(e)

    for sorgu in onay:  # B degistirir, commit ETMEZ: satir kilitleri B'de
        y.b.execute(sorgu)
    kilit_bekleyen = y.a.info.backend_pid
    is_parcacigi = threading.Thread(target=silen)
    is_parcacigi.start()
    bitis = time.monotonic() + BEKLEME_SINIRI
    bekliyor = False
    while time.monotonic() < bitis and is_parcacigi.is_alive():
        satir = y.c.execute(
            "SELECT count(*) FROM pg_stat_activity WHERE pid = %s AND wait_event_type = 'Lock'",
            (kilit_bekleyen,),
        ).fetchone()
        assert satir is not None
        if satir[0]:
            bekliyor = True
            break
        time.sleep(0.05)
    assert bekliyor, "silen deyim kilitte beklemedi (senaryo kurulamadi)"
    y.b.commit()  # onay gorunur olur; A kaldigi yerden devam eder
    is_parcacigi.join(BEKLEME_SINIRI)
    assert not is_parcacigi.is_alive(), "silen deyim tamamlanmadi"
    if hata:
        raise hata[0]
    return sonuc


def _say(y: Yaris, tablo: str, kosul: str) -> int:
    satir = y.c.execute(f"SELECT count(*) FROM icerik.{tablo} WHERE {kosul}").fetchone()
    assert satir is not None
    return int(satir[0])


def test_atif_sil_araya_giren_onay_silinmez(atif_yarisi: Yaris) -> None:
    """xref onaylandi ve review kapandi: ne `REVIEW_SIL` ne `SIL` onlari siler."""
    y = atif_yarisi
    review_id = _acik_review_ekle(y)
    _bos_staging(y.a, pg_xref_atif)
    param = {"kaynak": "tanzil-uthmani", "turler": ["atif"], "onekler": ["meal:elmalili:"]}
    onay = [
        f"UPDATE icerik.xref SET status = 'onayli' WHERE id = '{y.xref_id}'::uuid",
        "UPDATE icerik.review SET durum = 'onaylandi', inceleyen = 'test-editor',"
        f" incelendi_at = now() WHERE id = {review_id}",
    ]
    review_silinen, xref_silinen = _eszamanli(
        y, [(pg_xref_atif.REVIEW_SIL, param), (pg_xref_atif.SIL, param)], onay
    )
    y.a.commit()
    assert (review_silinen, xref_silinen) == (0, 0)
    assert _say(y, "xref", f"id = '{y.xref_id}'::uuid AND status = 'onayli'") == 1
    assert _say(y, "review", f"id = {review_id} AND durum = 'onaylandi'") == 1


def test_atif_sil_yalniz_xref_onaylandiysa_xref_silinmez(atif_yarisi: Yaris) -> None:
    """REVIEW_SIL bekletmeden gecer; SIL xref kilidinde bekler ve onayli xref silinmez."""
    y = atif_yarisi
    _acik_review_ekle(y)
    _bos_staging(y.a, pg_xref_atif)
    param = {"kaynak": "tanzil-uthmani", "turler": ["atif"], "onekler": ["meal:elmalili:"]}
    onay = [f"UPDATE icerik.xref SET status = 'onayli' WHERE id = '{y.xref_id}'::uuid"]
    _, xref_silinen = _eszamanli(
        y, [(pg_xref_atif.REVIEW_SIL, param), (pg_xref_atif.SIL, param)], onay
    )
    y.a.commit()
    assert xref_silinen == 0
    assert _say(y, "xref", f"id = '{y.xref_id}'::uuid AND status = 'onayli'") == 1


def test_atif_sil_onay_yoksa_ayni_deyimler_siler(atif_yarisi: Yaris) -> None:
    """Kontrol: karar araya girmezse uretilmeyen aday ve dokunulmamis acik review silinir."""
    y = atif_yarisi
    _acik_review_ekle(y)
    _bos_staging(y.a, pg_xref_atif)
    param = {"kaynak": "tanzil-uthmani", "turler": ["atif"], "onekler": ["meal:elmalili:"]}
    assert y.a.execute(pg_xref_atif.REVIEW_SIL, param).rowcount == 1
    assert y.a.execute(pg_xref_atif.SIL, param).rowcount == 1
    y.a.commit()
    assert _say(y, "xref", f"id = '{y.xref_id}'::uuid") == 0


def test_atif_review_sil_inceleyen_atanmissa_silmez(atif_yarisi: Yaris) -> None:
    """Editor review'u kapatmadan inceleme baslatti (`inceleyen`): review ve xref korunur."""
    y = atif_yarisi
    review_id = _acik_review_ekle(y)
    _bos_staging(y.a, pg_xref_atif)
    param = {"kaynak": "tanzil-uthmani", "turler": ["atif"], "onekler": ["meal:elmalili:"]}
    onay = [f"UPDATE icerik.review SET inceleyen = 'test-editor' WHERE id = {review_id}"]
    review_silinen, xref_silinen = _eszamanli(
        y, [(pg_xref_atif.REVIEW_SIL, param), (pg_xref_atif.SIL, param)], onay
    )
    y.a.commit()
    assert (review_silinen, xref_silinen) == (0, 0)
    assert _say(y, "review", f"id = {review_id}") == 1
    assert _say(y, "xref", f"id = '{y.xref_id}'::uuid") == 1


def test_pg_xref_sil_araya_giren_onay_silinmez(baglanti_yarisi: Yaris) -> None:
    """`pg_xref.SIL` (baglantilar) ayni desenle korunur: xref onaylandi, silinmez."""
    y = baglanti_yarisi
    _bos_staging(y.a, pg_xref)
    param = {"kaynak": "tanzil-uthmani", "turler": ["benzer_ayet"]}
    onay = [f"UPDATE icerik.xref SET status = 'onayli' WHERE id = '{y.xref_id}'::uuid"]
    (silinen,) = _eszamanli(y, [(pg_xref.SIL, param)], onay)
    y.a.commit()
    assert silinen == 0
    assert _say(y, "xref", f"id = '{y.xref_id}'::uuid AND status = 'onayli'") == 1


def test_sil_deyimleri_dis_deleteta_koruma_kosullarini_tasir() -> None:
    """Veritabansiz yapisal denetim: koruma kosullari DIS DELETE'te yazili (alt sorguda degil)."""
    dis_xref = pg_xref_atif.SIL.split(" AND x.id IN (", 1)[0]
    assert "x.origin = 'hat'" in dis_xref and "x.status = 'aday'" in dis_xref
    assert "FROM icerik.review r WHERE r.xref_id = x.id" in dis_xref
    dis_review = pg_xref_atif.REVIEW_SIL.split(" AND r.xref_id IN (", 1)[0]
    for kosul in ("r.durum = 'acik'", "r.inceleyen IS NULL", "r.koken = 'hat'"):
        assert kosul in dis_review
