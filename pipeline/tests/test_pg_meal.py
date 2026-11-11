# ruff: noqa: RUF001
"""`export pg` meal: taslak yukleme ve inceleme kuyrugu (A16.4; SENTETIK veri).

Zincir `conftest.meal_sablon` ile (gercek komutlar, sentetik 6.236 ayetlik gelen dosyalar) bir kez
kurulur; her test kendi kopyasini `mutalaa_test` veritabanina yukler. Testler dis islem icinde
kosar ve sonunda geri alinir (`test_fikstur_pg.py` ile ayni duzen); meal kaynaklari kalici olarak
veritabaninda kalmaz. Veritabani yoksa atlanir (`MUTALAA_DEGISMEZLIK_ZORUNLU=1` atlamayi hataya
cevirir). Hicbir metin gercek degildir ("Deneme meal parcasi S-N").
"""

import json
import os
from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest
from hat_yardimci import ayarlar_kur
from meal_yardimci import MealKoku, kopya_al
from psycopg.types.json import Jsonb

from mutalaa_pipeline import lineage
from mutalaa_pipeline.anchor import content_hash
from mutalaa_pipeline.config import Ayarlar
from mutalaa_pipeline.db import baglan
from mutalaa_pipeline.export import pg
from mutalaa_pipeline.export.ortak import GirdiHatasi, depo_koku
from mutalaa_pipeline.ingest import meal_kaynaklari as mk
from mutalaa_pipeline.normalize import tr_stem
from mutalaa_pipeline.staged import satirlari_oku

ORIJINAL = "elmalili-meal"
SADE = "elmalili-sade-meal"
SLUGLAR = (ORIJINAL, SADE)
TOPLAM = 6236
IZLEYEN_ORIJINAL = 2  # sure 3 (ayet 11) ve sure 4 (ayet 21): sentetik birlesik izleyenler


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
            "SELECT (SELECT count(*) FROM icerik.unit WHERE source_id = ANY(%s))"
            " + (SELECT count(*) FROM icerik.source WHERE slug = ANY(%s))",
            (list(SLUGLAR), list(SLUGLAR)),
        ).fetchone()
        assert kalinti is not None
        if kalinti[0] != 0:
            baglanti.rollback()
            _yok("mutalaa_test icinde meal kaynagi ya da birimi kalmis")
        yield baglanti
    finally:
        baglanti.rollback()
        baglanti.close()


@pytest.fixture
def kopya(meal_sablon: MealKoku, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> MealKoku:
    return kopya_al(meal_sablon, tmp_path, monkeypatch)


def yukle(tmp_path: Path, conn: psycopg.Connection, slug: str, **kw: object) -> int:
    return pg.komut_export_pg(
        ayarlar_kur(tmp_path),
        depo_kok=depo_koku(),
        source=slug,
        baglanti=lambda: conn,
        **kw,  # type: ignore[arg-type]
    )


def son_sayilar(veri: Path) -> dict[str, int]:
    raporlar = [json.loads(p.read_bytes()) for p in sorted((veri / "reports").glob("*.json"))]
    export = [r for r in raporlar if r.get("komut") == "export pg"]
    assert export
    return export[-1]["sayilar"]  # type: ignore[no-any-return]


def say(conn: psycopg.Connection, sorgu: str, *param: object) -> int:
    satir = conn.execute(sorgu, param).fetchone()  # type: ignore[arg-type]
    assert satir is not None
    return int(satir[0])


def acik(conn: psycopg.Connection, slug: str) -> int:
    return say(
        conn,
        "SELECT count(*) FROM icerik.review r JOIN icerik.unit u ON u.anchor = r.hedef_anahtar"
        " WHERE r.hedef_tablo = 'unit' AND r.alan = 'metin' AND r.durum = 'acik'"
        " AND u.source_id = %s",
        slug,
    )


def staged_satirlari(veri: Path, slug: str) -> list[dict[str, object]]:
    klasor = [
        c for c in lineage.calismalar(veri / "staged" / slug) if c[2].get("adim") == "anchor"
    ][-1][1]
    return [s.veri for s in satirlari_oku((klasor / "units.jsonl").read_bytes(), "units.jsonl")]


# --- ilk yukleme, kuyruk ve ikinci kosu -----------------------------------------------------


@pytest.mark.veritabani
def test_ilk_yukleme_taslak_ve_kuyruk_ikinci_kosu_sifir(
    tmp_path: Path, kopya: MealKoku, conn: psycopg.Connection
) -> None:
    veri = kopya.veri
    for slug in SLUGLAR:
        assert yukle(tmp_path, conn, slug) == 0
        s = son_sayilar(veri)
        assert (s["staging"], s["eklenen"], s["guncellenen"], s["degismeyen"]) == (
            TOPLAM,
            TOPLAM,
            0,
            0,
        )
        assert (s["review_eklenen"], s["korunan"], s["korunan_duzeltilmis"]) == (TOPLAM, 0, 0)
        assert s["kaynak_eklenen"] == 1
        assert (
            say(
                conn,
                "SELECT count(*) FROM icerik.unit WHERE source_id = %s AND kind = 'meal'"
                " AND metin_durumu = 'taslak' AND role = 'govde' AND status = 'etkin'",
                slug,
            )
            == TOPLAM
        )
        assert acik(conn, slug) == TOPLAM  # birlesik izleyenler dahil
    # birim alanlari
    satir = conn.execute(
        "SELECT kind::text, metin_durumu::text, ord, lower(ayah_range), upper(ayah_range),"
        " ar_norm, tr_stem <> '', rev, attrs, provenance ? 'konum', data_version, parent_path"
        " FROM icerik.unit WHERE anchor = 'meal:elmalili:3:10'"
    ).fetchone()
    assert satir is not None
    assert satir[:3] == (
        "meal",
        "taslak",
        say(conn, "SELECT ord FROM icerik.unit WHERE anchor = 'meal:elmalili:3:10'"),
    )
    assert satir[4] - satir[3] == 2  # birlesik bas birim kapsami orter
    assert satir[5] is None and satir[6] is True and satir[7] == 1
    assert satir[8] == {"kapsam": "q:3:10-11"} and satir[9] is True
    assert str(satir[10]).startswith("elmalili-meal@") and satir[11] is None
    # inceleme kaydi: K-49 madde 9
    r = conn.execute(
        "SELECT hedef_tablo, alan, eylem, koken::text, oneren, durum::text, onceki,"
        " onerilen ->> 'content_hash', onerilen ? 'tanik', onerilen -> 'tanik' ->> 'yontem'"
        " FROM icerik.review WHERE hedef_anahtar = 'meal:elmalili:2:2'"
    ).fetchone()
    assert r is not None
    assert r[:7] == ("unit", "metin", "oner", "hat", "hat", "acik", None)
    assert r[7] == content_hash("Deneme meal parçası 2-2") and r[8] is True
    assert r[9] == "rapidfuzz.fuzz.ratio/tr_narrow"
    # sadelestirilmis mealde tanik yok
    assert (
        say(
            conn,
            "SELECT count(*) FROM icerik.review WHERE hedef_anahtar = 'meal:elmalili-sade:2:2'"
            " AND NOT (onerilen ? 'tanik')",
        )
        == 1
    )
    # ikinci kosu: sifir degisiklik
    for slug in SLUGLAR:
        assert yukle(tmp_path, conn, slug, force=True) == 0
        s = son_sayilar(veri)
        assert (s["eklenen"], s["guncellenen"], s["degismeyen"]) == (0, 0, TOPLAM)
        assert (s["review_eklenen"], s["review_yeniden_kuyruk"], s["review_kaynak_farki"]) == (
            0,
            0,
            0,
        )
        assert (s["korunan_duzeltilmis"], s["bekleyen_kaynak_farki"], s["tr_stem_dolan"]) == (
            0,
            0,
            0,
        )
        assert (s["kaynak_eklenen"], s["kaynak_guncellenen"]) == (0, 0)
        assert acik(conn, slug) == TOPLAM


@pytest.mark.veritabani
def test_ilk_yukleme_tanik_skoruna_gore_artan_sirada_eklenir(
    tmp_path: Path, kopya: MealKoku, conn: psycopg.Connection
) -> None:
    assert yukle(tmp_path, conn, ORIJINAL) == 0
    beklenen = sorted(
        staged_satirlari(kopya.veri, ORIJINAL),
        key=lambda s: (
            s["tanik"]["skor"] if isinstance(s["tanik"], dict) else 10_000,  # type: ignore[index]
            s["ord"],
        ),
    )
    sirali = [
        str(r[0])
        for r in conn.execute(
            "SELECT hedef_anahtar FROM icerik.review WHERE hedef_tablo = 'unit' ORDER BY id"
        ).fetchall()
    ]
    assert sirali == [str(s["anchor"]) for s in beklenen]


@pytest.mark.veritabani
def test_birlesik_izleyen_icin_onerilen_null(
    tmp_path: Path, kopya: MealKoku, conn: psycopg.Connection
) -> None:
    assert yukle(tmp_path, conn, ORIJINAL) == 0
    assert (
        say(
            conn,
            "SELECT count(*) FROM icerik.review r JOIN icerik.unit u ON u.anchor = r.hedef_anahtar"
            " WHERE u.source_id = %s AND r.onerilen IS NULL",
            ORIJINAL,
        )
        == IZLEYEN_ORIJINAL
    )
    # NULL onerilen yalniz izleyen birimlerde; baska her kayit metin ve ozet tasir
    izleyen = {
        r[0]
        for r in conn.execute(
            "SELECT hedef_anahtar FROM icerik.review WHERE onerilen IS NULL"
            " AND hedef_anahtar LIKE 'meal:elmalili:%'"
        ).fetchall()
    }
    assert izleyen == {"meal:elmalili:3:11", "meal:elmalili:4:21"}
    assert (
        say(
            conn,
            "SELECT count(*) FROM icerik.unit WHERE source_id = %s"
            " AND attrs ? 'birlesik_ile' AND metin = ''",
            ORIJINAL,
        )
        == IZLEYEN_ORIJINAL
    )


@pytest.mark.veritabani
def test_tanik_yuklenmez_ve_kaynak_satiri_atif_ile_yazilir(
    tmp_path: Path, kopya: MealKoku, conn: psycopg.Connection
) -> None:
    assert yukle(tmp_path, conn, ORIJINAL) == 0
    assert say(conn, "SELECT count(*) FROM icerik.source WHERE slug = 'elmalili-meal-epub'") == 0
    assert say(conn, "SELECT count(*) FROM icerik.unit WHERE source_id = 'elmalili-meal-epub'") == 0
    assert yukle(tmp_path, conn, mk.KAYNAK_EPUB) == 2  # tanimsiz kaynak: girdi hatasi
    kaynak = conn.execute(
        "SELECT tur::text, atif_metni, surum, provider FROM icerik.source"
        " WHERE slug = 'elmalili-meal'"
    ).fetchone()
    assert kaynak == (
        "meal",
        mk.ATIF_ORIJINAL,
        "revid-liste-965a6249f61c-2026-11-11",
        "vikikaynak",
    )


# --- karar benzetimi: ret, ilk onay, ikinci onay, duzeltme --------------------------------------


@pytest.mark.veritabani
def test_ret_onay_duzeltme_sonrasi_koşu_cikis_0_ve_yeni_kayit_acmaz(
    tmp_path: Path, kopya: MealKoku, conn: psycopg.Connection
) -> None:
    veri = kopya.veri
    assert yukle(tmp_path, conn, SADE) == 0
    capa = {
        k: f"meal:elmalili-sade:2:{n}"
        for k, n in (("ret", 2), ("ilk", 3), ("ikinci", 4), ("duz", 5))
    }

    # ret: taslak birimin son kaydi reddedildi -> yeniden kuyruga girer (tek istisna)
    conn.execute(
        "UPDATE icerik.review SET durum = 'reddedildi', inceleyen = 'e1', gerekce = 'x'"
        " WHERE hedef_anahtar = %s",
        (capa["ret"],),
    )
    # ilk onay: kayit acik kalir, birim incelemede
    conn.execute(
        "UPDATE icerik.review SET inceleyen = 'e1', gerekce = 'x' WHERE hedef_anahtar = %s",
        (capa["ilk"],),
    )
    conn.execute(
        "UPDATE icerik.unit SET metin_durumu = 'incelemede', tr_wide = 'korunmali'"
        " WHERE anchor = %s",
        (capa["ilk"],),
    )
    # ikinci onay: birim onayli, kayit onaylandi
    conn.execute(
        "UPDATE icerik.review SET durum = 'onaylandi', inceleyen = 'e1', ikinci_inceleyen = 'e2',"
        " gerekce = 'x' WHERE hedef_anahtar = %s",
        (capa["ikinci"],),
    )
    conn.execute(
        "UPDATE icerik.unit SET metin_durumu = 'onayli', tr_wide = 'korunmali' WHERE anchor = %s",
        (capa["ikinci"],),
    )
    # duzeltme: editor metni degistirdi (rev 2, tr_stem NULL), onaylandi
    yeni_metin = "Deneme düzeltilmiş metin"
    conn.execute(
        "UPDATE icerik.unit SET metin = %s, content_hash = %s, metin_durumu = 'onayli', rev = 2,"
        " tr_stem = NULL WHERE anchor = %s",
        (yeni_metin, content_hash(yeni_metin), capa["duz"]),
    )
    conn.execute(
        "INSERT INTO icerik.review (hedef_tablo, hedef_anahtar, alan, eylem, onerilen, durum,"
        " koken, oneren, inceleyen, ikinci_inceleyen, gerekce) VALUES ('unit', %s, 'metin',"
        " 'duzenle_onayla', %s, 'onaylandi', 'editor', 'e1', 'e1', 'e2', 'x')",
        (capa["duz"], Jsonb({"metin": yeni_metin, "content_hash": content_hash(yeni_metin)})),
    )
    conn.execute(
        "UPDATE icerik.review SET durum = 'onaylandi' WHERE hedef_anahtar = %s AND koken = 'hat'",
        (capa["duz"],),
    )
    metin_once = conn.execute(
        "SELECT metin FROM icerik.unit WHERE anchor = %s", (capa["duz"],)
    ).fetchone()

    assert yukle(tmp_path, conn, SADE) == 0
    s = son_sayilar(veri)
    assert s["review_yeniden_kuyruk"] == 1 and s["review_eklenen"] == 1  # yalniz ret
    assert (s["korunan_duzeltilmis"], s["tr_stem_dolan"]) == (1, 1)
    assert s["korunan"] == 3  # incelemede, onayli ve duzeltilmis birimler
    assert (s["review_kaynak_farki"], s["bekleyen_kaynak_farki"]) == (0, 0)
    # ret: yeni acik kayit, taslak birim degismedi
    assert (
        say(
            conn,
            "SELECT count(*) FROM icerik.review WHERE hedef_anahtar = %s AND durum = 'acik'",
            capa["ret"],
        )
        == 1
    )
    # hat metne ve onayli/incelemedeki birimin turetilmis sutunlarina dokunmadi
    assert (
        conn.execute("SELECT metin FROM icerik.unit WHERE anchor = %s", (capa["duz"],)).fetchone()
        == metin_once
    )
    for anahtar in ("ilk", "ikinci"):
        assert conn.execute(
            "SELECT tr_wide, metin_durumu::text FROM icerik.unit WHERE anchor = %s",
            (capa[anahtar],),
        ).fetchone() == ("korunmali", "incelemede" if anahtar == "ilk" else "onayli")
    # tr_stem veritabanindaki GUNCEL metinden hesaplandi
    assert conn.execute(
        "SELECT tr_stem, rev, content_hash FROM icerik.unit WHERE anchor = %s", (capa["duz"],)
    ).fetchone() == (tr_stem(yeni_metin), 2, content_hash(yeni_metin))
    # ilk onaydaki acik kayit icin yeni kayit acilmadi
    assert (
        say(conn, "SELECT count(*) FROM icerik.review WHERE hedef_anahtar = %s", capa["ilk"]) == 1
    )

    # sonraki kosu: 0 degisiklik, 0 yeni kayit; korunan_duzeltilmis sayaci gorunur
    assert yukle(tmp_path, conn, SADE) == 0
    s = son_sayilar(veri)
    assert (s["review_eklenen"], s["eklenen"], s["guncellenen"], s["tr_stem_dolan"]) == (0, 0, 0, 0)
    assert s["korunan_duzeltilmis"] == 1 and s["korunan"] == 3


@pytest.mark.veritabani
def test_taslak_birimde_yalniz_turetilmis_sutunlar_staged_den_gelir(
    tmp_path: Path, kopya: MealKoku, conn: psycopg.Connection
) -> None:
    assert yukle(tmp_path, conn, SADE) == 0
    capa = "meal:elmalili-sade:2:2"
    conn.execute(
        "UPDATE icerik.unit SET tr_wide = 'bozuk', ord = 999999, data_version = 'eski'"
        " WHERE anchor = %s",
        (capa,),
    )
    assert yukle(tmp_path, conn, SADE) == 0
    s = son_sayilar(kopya.veri)
    assert (s["guncellenen"], s["eklenen"], s["review_eklenen"]) == (1, 0, 0)
    satir = conn.execute(
        "SELECT tr_wide <> 'bozuk', ord < 999999, data_version <> 'eski', metin_durumu::text"
        " FROM icerik.unit WHERE anchor = %s",
        (capa,),
    ).fetchone()
    assert satir == (True, True, True, "taslak")


# --- kaynak surumu degisimi (K-49 madde 11) --------------------------------------------------


def _eski_surum_benzet(conn: psycopg.Connection, capa: str, *, acik_kayit: bool) -> str:
    """Birimi eski kaynak surumuyle yuklenmis gibi gosterir; eski metnin ozetini dondurur."""
    eski = "Deneme eski kaynak metni"
    conn.execute(
        "UPDATE icerik.unit SET metin = %s, content_hash = %s WHERE anchor = %s",
        (eski, content_hash(eski), capa),
    )
    conn.execute(
        "UPDATE icerik.review SET onerilen = %s, durum = %s WHERE hedef_anahtar = %s",
        (
            Jsonb({"metin": eski, "content_hash": content_hash(eski)}),
            "acik" if acik_kayit else "onaylandi",
            capa,
        ),
    )
    return content_hash(eski)


@pytest.mark.veritabani
def test_kaynak_surumu_degisince_yeni_inceleme_acilir_metin_degismez(
    tmp_path: Path, kopya: MealKoku, conn: psycopg.Connection
) -> None:
    assert yukle(tmp_path, conn, SADE) == 0
    capa = "meal:elmalili-sade:2:2"
    eski_ozet = _eski_surum_benzet(conn, capa, acik_kayit=False)
    assert yukle(tmp_path, conn, SADE) == 0
    s = son_sayilar(kopya.veri)
    assert (s["review_kaynak_farki"], s["review_eklenen"], s["bekleyen_kaynak_farki"]) == (1, 1, 0)
    assert s["korunan_duzeltilmis"] == 0
    # hat metne yazmadi
    assert (
        say(
            conn,
            "SELECT count(*) FROM icerik.unit WHERE anchor = %s AND content_hash = %s",
            capa,
            eski_ozet,
        )
        == 1
    )
    yeni = conn.execute(
        "SELECT onceki ->> 'content_hash', onerilen ->> 'content_hash', onceki ->> 'metin'"
        " FROM icerik.review WHERE hedef_anahtar = %s AND durum = 'acik'",
        (capa,),
    ).fetchone()
    assert yeni == (eski_ozet, content_hash("Deneme sade parça 2-2"), "Deneme eski kaynak metni")
    # tekrar kosu: staged ozeti artik bir kayitta var -> yeni kayit yok
    assert yukle(tmp_path, conn, SADE) == 0
    s = son_sayilar(kopya.veri)
    assert (s["review_eklenen"], s["review_kaynak_farki"]) == (0, 0)
    assert s["korunan_duzeltilmis"] == 1  # ozeti farkli birim artik "duzeltilmis" korunur


@pytest.mark.veritabani
def test_acik_inceleme_varken_kaynak_farki_bekler(
    tmp_path: Path, kopya: MealKoku, conn: psycopg.Connection
) -> None:
    assert yukle(tmp_path, conn, SADE) == 0
    capa = "meal:elmalili-sade:2:2"
    _eski_surum_benzet(conn, capa, acik_kayit=True)
    assert yukle(tmp_path, conn, SADE) == 0
    s = son_sayilar(kopya.veri)
    assert (s["bekleyen_kaynak_farki"], s["review_eklenen"], s["review_kaynak_farki"]) == (1, 0, 0)
    assert say(conn, "SELECT count(*) FROM icerik.review WHERE hedef_anahtar = %s", capa) == 1


# --- cikis kodlari, dry-run ve guvenlik ------------------------------------------------------


@pytest.mark.veritabani
def test_dry_run_hicbir_satir_yazmaz(
    tmp_path: Path, kopya: MealKoku, conn: psycopg.Connection
) -> None:
    assert yukle(tmp_path, conn, SADE, dry_run=True) == 0
    assert say(conn, "SELECT count(*) FROM icerik.unit WHERE source_id = %s", SADE) == 0
    assert say(conn, "SELECT count(*) FROM icerik.source WHERE slug = %s", SADE) == 0
    assert (
        say(
            conn,
            "SELECT count(*) FROM icerik.review WHERE hedef_anahtar LIKE 'meal:elmalili-sade:%%'",
        )
        == 0
    )


@pytest.mark.veritabani
def test_qa_raporu_yoksa_ya_da_hiz_kaldiysa_cikis_1(
    tmp_path: Path, kopya: MealKoku, conn: psycopg.Connection
) -> None:
    rapor_dizini = kopya.veri / "reports"
    # G-HIZ kalmis rapor: en yeni qa raporunda G-HIZ 'kaldi'
    qa = [
        (p, json.loads(p.read_bytes()))
        for p in sorted(rapor_dizini.glob("*.json"))
        if not p.name.endswith("-meal-raporlari.json")
    ]
    qa = [(p, r) for p, r in qa if r.get("komut") == "qa run" and r.get("kaynak") == SADE]
    p, r = qa[-1]
    r["kapilar"]["G-HIZ"] = "kaldi"
    p.write_bytes(json.dumps(r).encode("utf-8"))
    assert yukle(tmp_path, conn, SADE) == 1
    assert say(conn, "SELECT count(*) FROM icerik.unit WHERE source_id = %s", SADE) == 0
    # qa raporu hic yok
    for dosya, _ in qa:
        dosya.unlink()
    assert yukle(tmp_path, conn, SADE) == 1


@pytest.mark.veritabani
def test_dorduncu_kapi_yetmez_bes_kapi_gerekir(
    tmp_path: Path, kopya: MealKoku, conn: psycopg.Connection
) -> None:
    """Dort kapili (G-HIZ'siz) bir rapor meal icin kabul edilmez (cikis 1)."""
    for p in sorted((kopya.veri / "reports").glob("*.json")):
        r = json.loads(p.read_bytes())
        if r.get("komut") == "qa run" and r.get("kaynak") == SADE:
            r["kapilar"].pop("G-HIZ")
            p.write_bytes(json.dumps(r).encode("utf-8"))
    assert yukle(tmp_path, conn, SADE) == 1


@pytest.mark.veritabani
def test_anchor_calistirmasi_yoksa_cikis_2(
    tmp_path: Path, kopya: MealKoku, conn: psycopg.Connection
) -> None:
    import shutil

    shutil.rmtree(kopya.veri / "staged" / SADE)
    assert yukle(tmp_path, conn, SADE) == 2


@pytest.mark.veritabani
def test_staged_da_olmayan_meal_capasi_cikis_1_ve_geri_alinir(
    tmp_path: Path, kopya: MealKoku, conn: psycopg.Connection
) -> None:
    assert yukle(tmp_path, conn, SADE) == 0
    conn.execute(
        "INSERT INTO icerik.unit (anchor, kind, source_id, ord, ayah_range, metin, content_hash,"
        " data_version) VALUES ('meal:elmalili-sade:2:999', 'meal', %s, 99999, int4range(1, 2),"
        " 'Deneme', %s, 'x')",
        (SADE, content_hash("Deneme")),
    )
    onceki = say(conn, "SELECT count(*) FROM icerik.review")
    assert yukle(tmp_path, conn, SADE) == 1  # capa durur kurali: eksik capa
    assert say(conn, "SELECT count(*) FROM icerik.review") == onceki


@pytest.mark.veritabani
def test_iletiler_metin_icermez(tmp_path: Path, kopya: MealKoku, conn: psycopg.Connection) -> None:
    assert yukle(tmp_path, conn, SADE) == 0
    rapor = [
        p
        for p in sorted((kopya.veri / "reports").glob("*.json"))
        if json.loads(p.read_bytes()).get("komut") == "export pg"
    ][-1]
    gunluk = (kopya.veri / "logs" / f"{rapor.stem}.jsonl").read_text(encoding="utf-8")
    for icerik in (rapor.read_text(encoding="utf-8"), gunluk):
        assert "Deneme sade" not in icerik


# --- okuyucu: birlesik degismezi ters yon, advisory kilit, sayac ayriligi ----------------------


def test_okuyucu_birlesik_ile_ve_dolu_metin_reddedilir(meal_sablon: MealKoku) -> None:
    from mutalaa_pipeline.export.pg_meal import satirlari_oku_meal
    from mutalaa_pipeline.staged import satir_baytlari

    anchorlar = [
        c
        for c in lineage.calismalar(meal_sablon.veri / "staged" / ORIJINAL)
        if c[2].get("adim") == "anchor"
    ]
    veri = (anchorlar[-1][1] / "units.jsonl").read_bytes()
    satirlar = [s.veri for s in satirlari_oku(veri, "units.jsonl")]
    assert len(satirlari_oku_meal(veri, ORIJINAL)) == TOPLAM

    def izleyen_mi(s: dict[str, object]) -> bool:
        attrs = s["attrs"]
        return isinstance(attrs, dict) and "birlesik_ile" in attrs

    izleyen = next(s for s in satirlar if izleyen_mi(s))
    dolu = dict(izleyen, text="Deneme dolu")
    bozuk = b"".join(satir_baytlari(dolu if s is izleyen else s) for s in satirlar)
    with pytest.raises(GirdiHatasi, match="birlesik_ile"):
        satirlari_oku_meal(bozuk, ORIJINAL)
    bos = next(s for s in satirlar if not izleyen_mi(s))
    bozuk = b"".join(satir_baytlari(dict(bos, text="") if s is bos else s) for s in satirlar)
    with pytest.raises(GirdiHatasi):
        satirlari_oku_meal(bozuk, ORIJINAL)


def _kilitler(conn: psycopg.Connection, capa: str) -> int:
    return say(
        conn,
        "SELECT count(*) FROM pg_locks WHERE locktype = 'advisory' AND pid = pg_backend_pid()"
        " AND ((classid::bigint << 32) | objid::bigint) = hashtextextended(%s, 0)",
        "unit-correction:" + capa,
    )


@pytest.mark.veritabani
def test_inceleme_acilirken_sunucunun_duzeltme_kilidi_alinir(
    tmp_path: Path, kopya: MealKoku, conn: psycopg.Connection
) -> None:
    capa = "meal:elmalili-sade:2:2"
    assert yukle(tmp_path, conn, SADE) == 0
    assert _kilitler(conn, capa) == 0  # ilk yuklemede birim yoktu: kilit gerekmez
    _eski_surum_benzet(conn, capa, acik_kayit=False)
    assert yukle(tmp_path, conn, SADE) == 0
    assert _kilitler(conn, capa) == 1  # sunucu ile ayni anahtar: 'unit-correction:{capa}'
    assert son_sayilar(kopya.veri)["review_eklenen"] == 1
    # idempotentlik: sonraki kosu yeni kayit acmaz
    assert yukle(tmp_path, conn, SADE) == 0
    assert son_sayilar(kopya.veri)["review_eklenen"] == 0


@pytest.mark.veritabani
def test_yeniden_kuyruga_giren_birim_korunan_duzeltilmis_sayilmaz(
    tmp_path: Path, kopya: MealKoku, conn: psycopg.Connection
) -> None:
    assert yukle(tmp_path, conn, SADE) == 0
    capa = "meal:elmalili-sade:2:2"
    eski = "Deneme eski metin"
    conn.execute(
        "UPDATE icerik.unit SET metin = %s, content_hash = %s WHERE anchor = %s",
        (eski, content_hash(eski), capa),
    )
    # staged ozetiyle hat kaydi var, son kayit reddedildi: taslak birim yeniden kuyruga girer
    conn.execute(
        "UPDATE icerik.review SET durum = 'reddedildi', inceleyen = 'e1', gerekce = 'x'"
        " WHERE hedef_anahtar = %s",
        (capa,),
    )
    assert yukle(tmp_path, conn, SADE) == 0
    s = son_sayilar(kopya.veri)
    assert (s["review_yeniden_kuyruk"], s["review_eklenen"]) == (1, 1)
    assert s["korunan_duzeltilmis"] == 0  # cifte sayim yok: iki sayac ayrik kumeler
    yeni = conn.execute(
        "SELECT onceki ->> 'content_hash' FROM icerik.review WHERE hedef_anahtar = %s"
        " AND durum = 'acik'",
        (capa,),
    ).fetchone()
    assert yeni == (content_hash(eski),)
