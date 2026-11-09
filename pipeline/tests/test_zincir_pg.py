"""Zincirden PostgreSQL'e: ingest x2 -> normalize -> anchor -> qa -> `export pg` (A10.4; SENTETIK).

6.236 ayetlik sentetik zincir (`tam_sablon`, gercek komutlarla kurulur) `mutalaa_test` veritabanina
yuklenir. Testler dis islem icinde kosar ve sonunda geri alinir (`test_export_pg.py` ile ayni
duzen). Sentetik Uthmani metni bilerek NFC degildir: yuklenen birimlerden dosya yeniden
kurulunca ham dosyayla bayt bayt ayni olmali (K-26). Gercek Kur'an metni testte yoktur.
"""

import json
import os
from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest
from hat_yardimci import ayarlar_kur
from zincir_yardimci import Zincir, ortam_kur, sablon_kopyala

from mutalaa_pipeline import lineage
from mutalaa_pipeline.adimlar.normalize_tanzil import EK_KAYNAK, KAYNAK
from mutalaa_pipeline.config import Ayarlar
from mutalaa_pipeline.db import baglan
from mutalaa_pipeline.export import pg
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.qa.run import komut_qa_run

TANZIL_KAYNAKLARI = (KAYNAK, EK_KAYNAK)


def _yok(neden: str) -> None:
    if os.environ.get("MUTALAA_DEGISMEZLIK_ZORUNLU") == "1":
        pytest.fail(neden)
    pytest.skip(neden)


@pytest.fixture
def conn() -> Iterator[psycopg.Connection]:
    """Test veritabanina baglanir (dis islem, sonunda geri alinir); Tanzil satiri kalmissa atlar."""
    try:
        baglanti = baglan(Ayarlar(), test=True)
    except GirdiHatasi as hata:
        _yok(f"test veritabani yok: {hata}")
        return
    try:
        kalinti = baglanti.execute(
            "SELECT (SELECT count(*) FROM icerik.unit WHERE source_id = ANY(%s))"
            " + (SELECT count(*) FROM icerik.source WHERE slug = ANY(%s))",
            (list(TANZIL_KAYNAKLARI), list(TANZIL_KAYNAKLARI)),
        ).fetchone()
        assert kalinti is not None
        if kalinti[0] != 0:
            baglanti.rollback()
            _yok("mutalaa_test icinde Tanzil kaynagi ya da birimi kalmis")
        yield baglanti
    finally:
        baglanti.rollback()
        baglanti.close()


@pytest.fixture
def z(tam_sablon: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Zincir:
    zincir = sablon_kopyala(tam_sablon, tmp_path / "t")
    ortam_kur(zincir, monkeypatch)
    kod = komut_qa_run(source=KAYNAK, run=None, gate=None, config=None, kok=zincir.kok)
    assert kod == 0
    return zincir


def yukle(z: Zincir, conn: psycopg.Connection, **kw: object) -> int:
    return pg.komut_export_pg(
        ayarlar_kur(z.tmp),
        depo_kok=z.kok,
        source=KAYNAK,
        baglanti=lambda: conn,
        **kw,  # type: ignore[arg-type]
    )


def son_sayilar(z: Zincir) -> dict[str, int]:
    raporlar = [
        json.loads(yol.read_bytes()) for yol in sorted((z.veri_kok / "reports").glob("*.json"))
    ]
    yuklemeler = [r for r in raporlar if r["komut"] == "export pg"]
    assert yuklemeler
    sayilar = yuklemeler[-1]["sayilar"]
    assert isinstance(sayilar, dict)
    return sayilar


def say(conn: psycopg.Connection, sorgu: str, *param: object) -> int:
    satir = conn.execute(sorgu, param).fetchone()  # type: ignore[arg-type]
    assert satir is not None
    return int(satir[0])


@pytest.mark.veritabani
def test_zincirden_ilk_yukleme_sonra_ikinci_kosu_sifir_degisiklik(
    z: Zincir, conn: psycopg.Connection
) -> None:
    assert yukle(z, conn) == 0
    ilk = son_sayilar(z)
    assert (ilk["staging"], ilk["eklenen"], ilk["guncellenen"], ilk["degismeyen"]) == (
        6236,
        6236,
        0,
        0,
    )
    assert (ilk["kaynak_eklenen"], ilk["kaynak_guncellenen"]) == (2, 0)
    assert say(conn, "SELECT count(*) FROM icerik.unit WHERE source_id = %s", KAYNAK) == 6236
    assert say(conn, "SELECT count(*) FROM icerik.unit") == 6236
    assert (
        say(conn, "SELECT count(*) FROM icerik.source WHERE slug = ANY(%s)", [*TANZIL_KAYNAKLARI])
        == 2
    )
    bozuk = say(
        conn,
        "SELECT count(*) FROM icerik.unit WHERE source_id = %s"
        " AND content_hash <> encode(sha256(convert_to(metin, 'UTF8')), 'hex')",
        KAYNAK,
    )
    assert bozuk == 0

    assert yukle(z, conn) == 0  # ikinci kosu: hicbir satir degismez
    ikinci = son_sayilar(z)
    assert (ikinci["eklenen"], ikinci["guncellenen"], ikinci["degismeyen"]) == (0, 0, 6236)
    assert (ikinci["kaynak_eklenen"], ikinci["kaynak_guncellenen"]) == (0, 0)
    assert ikinci["kaynak_degismeyen"] == 2
    assert say(conn, "SELECT count(*) FROM icerik.pipeline_run WHERE komut = 'export pg'") == 2


@pytest.mark.veritabani
def test_yuklenen_birimlerden_dosya_bayt_bayt_yeniden_kurulur(
    z: Zincir, conn: psycopg.Connection
) -> None:
    """K-26 dairesi: ham dosya -> PostgreSQL -> dosya; NFC olmayan metin de aynen kalir."""
    assert yukle(z, conn) == 0
    satirlar = conn.execute(
        "SELECT anchor, metin, ord FROM icerik.unit WHERE source_id = %s ORDER BY ord", (KAYNAK,)
    ).fetchall()
    bildirim = conn.execute(
        "SELECT notice_text FROM icerik.source WHERE slug = %s", (KAYNAK,)
    ).fetchone()
    assert bildirim is not None
    govde = b""
    for sira, (capa, metin, ord_) in enumerate(satirlar, start=1):
        _, sure, ayet = capa.split(":")
        assert ord_ == sira
        govde += f"{sure}|{ayet}|{metin}\n".encode()
    yeniden = govde + bildirim[0].encode("utf-8")
    assert lineage.sha256_bayt(yeniden) == lineage.sha256_bayt(z.veriler["uthmani"])
    assert yeniden == z.veriler["uthmani"]


@pytest.mark.veritabani
def test_ar_norm_provenance_ve_surum_yuklenir(z: Zincir, conn: psycopg.Connection) -> None:
    assert yukle(z, conn) == 0
    satir = conn.execute(
        "SELECT ar_norm, data_version, provenance->'ar_norm'->>'kaynak',"
        " (provenance->'ar_norm'->>'ar4')::boolean, kind::text, metin_durumu::text,"
        " lower(ayah_range), upper(ayah_range) FROM icerik.unit WHERE anchor = 'q:2:255'"
    ).fetchone()
    assert satir is not None
    assert satir[0] and satir[0].strip() != ""
    assert satir[1:6] == ("tanzil-uthmani@1.1", EK_KAYNAK, True, "ayet", "onayli")
    assert satir[6:] == (262, 263)  # 2:255 kuresel sira 7 + 255
    assert say(conn, "SELECT count(*) FROM icerik.unit WHERE ar_norm IS NULL OR ar_norm = ''") == 0


@pytest.mark.veritabani
def test_dry_run_veritabanina_hicbir_sey_yazmaz(z: Zincir, conn: psycopg.Connection) -> None:
    assert yukle(z, conn, dry_run=True) == 0
    rapor = son_sayilar(z)
    assert (rapor["eklenen"], rapor["kaynak_eklenen"]) == (6236, 2)  # yazilsaydi
    assert say(conn, "SELECT count(*) FROM icerik.unit WHERE source_id = %s", KAYNAK) == 0
    assert (
        say(conn, "SELECT count(*) FROM icerik.source WHERE slug = ANY(%s)", [*TANZIL_KAYNAKLARI])
        == 0
    )


# --- quran_word (A11.2, K-43 madde 3) ----------------------------------------------------------

QAC_SUTUNLARI = ("root_id", "lemma_id", "pos", "features", "morph_source")
TANZIL_SUTUNLARI = (
    "surah",
    "ayah",
    "word",
    "ayah_index",
    "text_uthmani",
    "norm",
    "char_start",
    "char_end",
    "source_id",
    "data_version",
)


def kelime_dosyasi(z: Zincir) -> list[dict[str, object]]:
    """Son anchor calismasinin `words.jsonl` satirlari (staged'den okunur)."""
    son = lineage.son_basarili(z.veri_kok / "staged" / KAYNAK, "anchor")
    assert son is not None
    satirlar = (son[1] / "words.jsonl").read_bytes().splitlines()
    return [json.loads(s) for s in satirlar]


def kelime_say(conn: psycopg.Connection) -> int:
    return say(conn, "SELECT count(*) FROM icerik.quran_word WHERE source_id = %s", KAYNAK)


def export_hatasi(z: Zincir) -> int:
    """Baglanti acilmadan biten (dosya onkosulu) export pg cikis kodu."""

    def baglanti() -> psycopg.Connection:
        raise AssertionError("baglanti acilmamali")

    return pg.komut_export_pg(ayarlar_kur(z.tmp), depo_kok=z.kok, source=KAYNAK, baglanti=baglanti)


@pytest.mark.veritabani
def test_kelimeler_ilk_yuklemede_yazilir_ikinci_kosu_sifir_degisiklik(
    z: Zincir, conn: psycopg.Connection
) -> None:
    beklenen = kelime_dosyasi(z)
    assert beklenen
    assert yukle(z, conn) == 0
    ilk = son_sayilar(z)
    assert ilk["kelime_staging"] == ilk["kelime_eklenen"] == len(beklenen)
    assert ilk["kelime_degismeyen"] == 0
    assert kelime_say(conn) == len(beklenen)
    # Her ayetin en az bir kelimesi var (6.236 ayet) ve QAC sutunlari bos.
    assert say(conn, "SELECT count(DISTINCT ayah_index) FROM icerik.quran_word") == 6236
    qac = " OR ".join(f"{s} IS NOT NULL" for s in QAC_SUTUNLARI)
    assert say(conn, f"SELECT count(*) FROM icerik.quran_word WHERE {qac}") == 0  # type: ignore[arg-type]
    assert say(conn, "SELECT count(root_id) FROM icerik.quran_word") == 0

    once = conn.execute("SELECT * FROM icerik.quran_word ORDER BY anchor").fetchall()
    assert yukle(z, conn) == 0  # ikinci kosu: hicbir satir degismez
    ikinci = son_sayilar(z)
    assert (ikinci["kelime_eklenen"], ikinci["kelime_degismeyen"]) == (0, len(beklenen))
    assert conn.execute("SELECT * FROM icerik.quran_word ORDER BY anchor").fetchall() == once


@pytest.mark.veritabani
def test_yuklenen_kelime_satiri_staged_satirla_ve_ayet_metniyle_ayni(
    z: Zincir, conn: psycopg.Connection
) -> None:
    assert yukle(z, conn) == 0
    satirlar = kelime_dosyasi(z)
    for k in satirlar[:: max(1, len(satirlar) // 200)]:  # seyrek orneklem: ~200 kelime
        db = conn.execute(
            "SELECT " + ", ".join(TANZIL_SUTUNLARI) + " FROM icerik.quran_word WHERE anchor = %s",  # type: ignore[arg-type]
            (k["anchor"],),
        ).fetchone()
        assert db == tuple(k[a] for a in TANZIL_SUTUNLARI)
    # text_uthmani birimin metninin dilimidir (bayt bayt; NFC olmayan sentetik metin dahil).
    farkli = say(
        conn,
        "SELECT count(*) FROM icerik.quran_word w JOIN icerik.unit u ON u.ord = w.ayah_index"
        " WHERE substr(u.metin, w.char_start + 1, w.char_end - w.char_start) <> w.text_uthmani",
    )
    assert farkli == 0
    assert say(conn, "SELECT count(*) FROM icerik.quran_word WHERE norm = ''") == 0


@pytest.mark.veritabani
def test_degismis_kelime_satiri_cikis_1_ve_geri_alinir(z: Zincir, conn: psycopg.Connection) -> None:
    assert yukle(z, conn) == 0
    toplam = kelime_say(conn)
    conn.execute("UPDATE icerik.quran_word SET norm = 'Deneme' WHERE anchor = 'q:2:255:1'")
    conn.execute("DELETE FROM icerik.quran_word WHERE anchor = 'q:2:255:2'")
    assert yukle(z, conn) == 1
    # Eksik satir yeniden eklenmedi (islem geri alindi), degisen satir duzeltilmedi.
    assert kelime_say(conn) == toplam - 1
    norm = conn.execute("SELECT norm FROM icerik.quran_word WHERE anchor = 'q:2:255:1'")
    assert norm.fetchone() == ("Deneme",)


@pytest.mark.veritabani
@pytest.mark.parametrize(
    "degisim",
    [
        "surah = 3",
        "ayah = ayah + 1000",
        "ayah_index = 1",
        "text_uthmani = 'Deneme'",
        "char_start = char_start + 1",
        "char_end = char_end + 1",
        "data_version = 'tanzil-uthmani@0.9'",
    ],
)
def test_her_tanzil_sutunu_degisince_cikis_1(
    z: Zincir, conn: psycopg.Connection, degisim: str
) -> None:
    assert yukle(z, conn) == 0
    conn.execute(f"UPDATE icerik.quran_word SET {degisim} WHERE anchor = 'q:2:255:1'")  # type: ignore[arg-type]
    assert yukle(z, conn) == 1


@pytest.mark.veritabani
def test_veritabaninda_olup_staged_de_olmayan_kelime_cikis_1_ve_silinmez(
    z: Zincir, conn: psycopg.Connection
) -> None:
    assert yukle(z, conn) == 0
    toplam = kelime_say(conn)
    conn.execute(
        "INSERT INTO icerik.quran_word (anchor, surah, ayah, word, ayah_index, text_uthmani, norm,"
        " char_start, char_end, source_id, data_version)"
        " VALUES ('q:1:1:99', 1, 1, 99, 1, 'Deneme', 'deneme', 0, 6, %s, 'tanzil-uthmani@1.1')",
        (KAYNAK,),
    )
    assert yukle(z, conn) == 1
    assert kelime_say(conn) == toplam + 1  # fazladan satir silinmedi


@pytest.mark.veritabani
def test_qac_sutunlarina_dokunulmaz(z: Zincir, conn: psycopg.Connection) -> None:
    assert yukle(z, conn) == 0
    conn.execute(
        "UPDATE icerik.quran_word SET pos = 'DENEME', features = '[1]'::jsonb"
        " WHERE anchor = 'q:2:255:1'"
    )
    assert yukle(z, conn) == 0
    kayit = conn.execute(
        "SELECT pos, features::text FROM icerik.quran_word WHERE anchor = 'q:2:255:1'"
    ).fetchone()
    assert kayit == ("DENEME", "[1]")
    assert say(conn, "SELECT count(pos) FROM icerik.quran_word") == 1


@pytest.mark.veritabani
def test_dry_run_kelime_yazmaz(z: Zincir, conn: psycopg.Connection) -> None:
    assert yukle(z, conn, dry_run=True) == 0
    rapor = son_sayilar(z)
    assert rapor["kelime_eklenen"] == len(kelime_dosyasi(z))  # yazilsaydi
    assert kelime_say(conn) == 0


def test_yukleme_sozlesmesi_yalniz_tanzil_sutunlarini_adlandirir() -> None:
    """INSERT QAC sutunlarini (root_id, lemma_id, pos, features, morph_source) hic anmaz."""
    for sutun in QAC_SUTUNLARI:
        assert sutun not in pg.INSERT_KELIME
        assert sutun not in pg.FARKLI_KELIME
    assert set(pg.KELIME_SUTUNLARI) == {"anchor", *TANZIL_SUTUNLARI}
    assert "DELETE" not in pg.INSERT_KELIME.upper()
    assert "UPDATE" not in pg.INSERT_KELIME.upper()


def test_anchor_manifestinde_kelime_dosyasi_yoksa_cikis_2(
    z: Zincir, capsys: pytest.CaptureFixture[str]
) -> None:
    son = lineage.son_basarili(z.veri_kok / "staged" / KAYNAK, "anchor")
    assert son is not None
    manifest = dict(son[2])
    ciktilar = manifest["ciktilar"]
    assert isinstance(ciktilar, list)
    manifest["ciktilar"] = [c for c in ciktilar if not c["yol"].endswith("/words.jsonl")]
    lineage.manifest_yaz(son[1], manifest)
    assert export_hatasi(z) == 2
    assert "words.jsonl" in capsys.readouterr().err


def test_kelime_dosyasi_bozulmussa_cikis_2(z: Zincir, capsys: pytest.CaptureFixture[str]) -> None:
    son = lineage.son_basarili(z.veri_kok / "staged" / KAYNAK, "anchor")
    assert son is not None
    (son[1] / "words.jsonl").write_bytes(b"{}\n")
    assert export_hatasi(z) == 2  # cikti saglam degil: ozet manifestle tutmuyor
    assert "words.jsonl" not in capsys.readouterr().out
