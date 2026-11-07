"""`export pg`: kaynak zinciri, QA kapisi, K-39 yazim kurallari (SENTETIK veri).

Butun metinler "Deneme ..." biciminde sentetiktir; kaynaklar `test-` onekli, TOML'lari `tmp_path`
altindaki sahte kokte durur. `veritabani` isaretli testler yalniz turetilmis test adresine
(`Ayarlar.test_db_adresi()`) baglanir, hepsi dis islem icinde kosar ve sonunda geri alinir.
"""

import json
import os
import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

import psycopg
import pytest
from hat_yardimci import ayarlar_kur
from test_sources import alanlar_kur, kayit_yaz, kok_kur
from typer.testing import CliRunner

from mutalaa_pipeline import cli, lineage, qa, sources
from mutalaa_pipeline.config import Ayarlar
from mutalaa_pipeline.db import baglan
from mutalaa_pipeline.export import pg
from mutalaa_pipeline.export.ortak import GirdiHatasi, depo_koku
from mutalaa_pipeline.runctx import Uuid7Uretici
from mutalaa_pipeline.sources.kayit import Kaynak

ANA = "test-ana"
EK = "test-ek"
TARIH = "2026-10-28"
BILDIRIM = "Deneme bildirimi\n\n  Ikinci satir \n"
KAPILAR = ("G-KAY", "G-BUT", "G-CAP", "G-NOR")
TUM_GECTI = dict.fromkeys(KAPILAR, "gecti")
# `icerik.source` hedef sema: 16 sutun, `id` yok (birincil anahtar `slug`).
HEDEF_SUTUNLAR = (
    "slug",
    "tur",
    "baslik",
    "yazar",
    "surum",
    "provider",
    "kaynak_url",
    "alinma_tarihi",
    "dosya_sha256",
    "baski_bilgisi",
    "atif_metni",
    "atif_url",
    "notice_text",
    "notlar",
    "created_at",
    "updated_at",
)


def ozet(metin: str) -> str:
    return lineage.sha256_bayt(metin.encode("utf-8"))


def satir(no: int, metin: str | None = None, **degisim: object) -> dict[str, object]:
    metin = metin if metin is not None else f"Deneme metni {no}"
    kayit: dict[str, object] = {
        "anchor": f"q:1:{no}",
        "kind": "ayet",
        "ord": no,
        "ayah_lo": no,
        "ayah_hi": no + 1,
        "text": metin,
        "content_hash": ozet(metin),
        "metin_durumu": "onayli",
        "ar_norm": f"deneme {no}",
        "data_version": "test@1.0",
        "provenance": {"file": "deneme.txt", "sha256": "0" * 64, "line": no, "steps": []},
        "source_id": ANA,
    }
    kayit.update(degisim)
    return kayit


def varsayilan_satirlar() -> list[dict[str, object]]:
    return [satir(1), satir(2), satir(3)]


@dataclass
class Senaryo:
    tmp: Path
    kok: Path
    ayarlar: Ayarlar
    uretici: Uuid7Uretici = field(default_factory=Uuid7Uretici)
    anchor_run: str = ""

    @property
    def veri(self) -> Path:
        return self.ayarlar.veri_kok


def senaryo_kur(tmp_path: Path, **ana_alanlar: object) -> Senaryo:
    kok = kok_kur(tmp_path)
    ana = {
        "tur": "kuran_metni",
        "surum": "1.0",
        "notice_text": BILDIRIM,
        "kaynak_url": "https://deneme.invalid/",
    }
    ana.update(ana_alanlar)
    kayit_yaz(kok, alanlar_kur(ANA, **ana))
    kayit_yaz(kok, alanlar_kur(EK, surum="1.1", baslik="Deneme ek kaynak"))
    return Senaryo(tmp_path, kok, ayarlar_kur(tmp_path))


def toml_yeniden(s: Senaryo, slug: str, **degisim: object) -> None:
    """Kaynak TOML'unu degisiklikle yeniden yazar (`None` verilen alan kayittan cikar)."""
    taban: dict[str, object] = (
        {
            "tur": "kuran_metni",
            "surum": "1.0",
            "notice_text": BILDIRIM,
            "kaynak_url": "https://deneme.invalid/",
        }
        if slug == ANA
        else {"surum": "1.1", "baslik": "Deneme ek kaynak"}
    )
    taban.update(degisim)
    kayit_yaz(s.kok, alanlar_kur(slug, **taban))


def _staged_calisma(
    s: Senaryo,
    kaynak: str,
    run_id: str,
    adim: str,
    dosyalar: dict[str, bytes],
    girdiler: list[lineage.Girdi],
) -> None:
    klasor = s.veri / "staged" / kaynak / run_id
    klasor.mkdir(parents=True)
    ciktilar = []
    for ad, veri in dosyalar.items():
        (klasor / ad).write_bytes(veri)
        ciktilar.append(
            lineage.Cikti(f"staged/{kaynak}/{run_id}/{ad}", lineage.sha256_bayt(veri), None)
        )
    manifest = lineage.manifest_kur(
        run_id=run_id,
        adim=adim,
        komut=f"{adim} deneme",
        git=lineage.GitDurumu(commit=None, kirli=True),
        uv_lock=None,
        config_sha=None,
        girdiler=girdiler,
        araclar={},
        ciktilar=ciktilar,
        parmak="0" * 64,
    )
    lineage.manifest_yaz(klasor, manifest)


def zincir_kur(
    s: Senaryo,
    satirlar: list[dict[str, object]] | None = None,
    *,
    kapilar: dict[str, str] | None = None,
    qa_sha: str | None = None,
    qa_yaz: bool = True,
    notice: str | None = BILDIRIM,
    units_bayt: bytes | None = None,
) -> str:
    """ingest (iki kaynak) -> normalize -> anchor zinciri ve QA raporu; anchor run_id doner.

    `units_bayt` verilirse anchor `units.jsonl` dosyasi satirlardan degil bu baytlardan kurulur
    (bozuk JSON, UTF-8 olmayan bayt gibi satir duzeyinde kurulamayan girdiler icin).
    """
    satirlar = satirlar if satirlar is not None else varsayilan_satirlar()
    yeni = [str(s.uretici.uret()) for _ in range(5)]
    ing_ana, ing_ek, norm, anc, qa = yeni
    ingestler = {ANA: ing_ana, EK: ing_ek}
    ust: list[lineage.Girdi] = []
    for slug, run_id in ingestler.items():
        ham_yol = s.veri / "raw" / slug / TARIH / f"{slug}.txt"
        ham_yol.parent.mkdir(parents=True, exist_ok=True)
        ham_yol.write_bytes(f"Deneme ham dosya {slug}\n".encode())
        ham = lineage.Girdi(f"raw/{slug}/{TARIH}/{slug}.txt", lineage.sha256_dosya(ham_yol))
        dosyalar = {"units.jsonl": b'{"deneme":1}\n'}
        if slug == ANA and notice is not None:
            dosyalar["notice.txt"] = notice.encode("utf-8")
        _staged_calisma(s, slug, run_id, "ingest", dosyalar, [ham])
        ust.append(
            lineage.Girdi(
                f"staged/{slug}/{run_id}/units.jsonl",
                lineage.sha256_bayt(dosyalar["units.jsonl"]),
                run_id,
            )
        )
    _staged_calisma(s, ANA, norm, "normalize", {"units.jsonl": b'{"deneme":2}\n'}, ust)
    norm_girdi = lineage.Girdi(
        f"staged/{ANA}/{norm}/units.jsonl", lineage.sha256_bayt(b'{"deneme":2}\n'), norm
    )
    units = "".join(
        json.dumps(k, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n"
        for k in satirlar
    ).encode("utf-8")
    if units_bayt is not None:
        units = units_bayt
    _staged_calisma(s, ANA, anc, "anchor", {"units.jsonl": units}, [norm_girdi])
    s.anchor_run = anc
    if qa_yaz:
        klasor = s.veri / "reports"
        klasor.mkdir(parents=True, exist_ok=True)
        rapor = {
            "komut": "qa run",
            "kaynak": ANA,
            "anchor_run_id": anc,
            "units_sha256": qa_sha if qa_sha is not None else lineage.sha256_bayt(units),
            "kapilar": kapilar if kapilar is not None else TUM_GECTI,
        }
        (klasor / f"{qa}.json").write_text(json.dumps(rapor), encoding="utf-8", newline="\n")
    return anc


class BaglantiAcildi(BaseException):
    """Dosya onkosulu hatasinda veritabani baglantisi acilmamali.

    `Exception` degil `BaseException`: `komut_calistir` her `Exception`i cikis 2'ye cevirir. Bir
    dogrulama kalksa ve akis baglantiya kadar ilerlese bile "== 2" iddiasi YANLIS NEDENLE gecmez;
    bu istisna komuttan disari cikar ve test hatayla biter.
    """


class Cagrilmaz:
    """Dosya onkosulu hatasinda veritabani baglantisi acilmamali."""

    def __init__(self) -> None:
        self.sayi = 0

    def __call__(self) -> psycopg.Connection:
        self.sayi += 1
        raise BaglantiAcildi("baglanti acilmamali")


def calistir(
    s: Senaryo,
    conn: psycopg.Connection | None = None,
    *,
    source: str = ANA,
    **kw: object,
) -> int:
    baglanti = (lambda: conn) if conn is not None else Cagrilmaz()
    return pg.komut_export_pg(
        s.ayarlar,
        depo_kok=s.kok,
        source=source,
        kayit={ANA: (EK,)},
        baglanti=baglanti,  # type: ignore[arg-type]
        **kw,  # type: ignore[arg-type]
    )


def hata_ile(
    s: Senaryo,
    kod: int,
    parca: str,
    capsys: pytest.CaptureFixture[str],
    **kw: object,
) -> str:
    """Dosya onkosulu hatasi: cikis kodu VE iletideki neden birlikte sinanir (stderr doner).

    Baglanti acilsaydi `BaglantiAcildi` komuttan cikar; ileti de bos gecemez: ayni cikis kodunu
    veren baska bir denetim, sinanan denetimin yerine gecemez.
    """
    capsys.readouterr()
    sonuc = calistir(s, **kw)
    hata = capsys.readouterr().err
    assert sonuc == kod, hata
    assert parca in hata, hata
    assert hata.isascii()
    return hata


def son_rapor(s: Senaryo) -> dict[str, object]:
    raporlar = []
    for yol in sorted((s.veri / "reports").glob("*.json"), key=lambda p: p.name):
        veri = json.loads(yol.read_text(encoding="utf-8"))
        if veri.get("komut") == "export pg":
            raporlar.append(veri)
    assert raporlar
    return raporlar[-1]


def sayilar(s: Senaryo) -> dict[str, int]:
    deger = son_rapor(s)["sayilar"]
    assert isinstance(deger, dict)
    return deger


# --- veritabani -------------------------------------------------------------------------


def _zorunlu() -> bool:
    return os.environ.get("MUTALAA_DEGISMEZLIK_ZORUNLU") == "1"


def _yok(neden: str) -> None:
    if _zorunlu():
        pytest.fail(neden)
    pytest.skip(neden)


@pytest.fixture
def conn() -> Iterator[psycopg.Connection]:
    """Test veritabanina (`mutalaa_test`) baglanir; dis islem acik, sonunda geri alinir."""
    try:
        baglanti = baglan(Ayarlar(), test=True)
    except GirdiHatasi as hata:
        _yok(f"test veritabani yok: {hata}")
        return
    try:
        ilk = baglanti.execute("SELECT count(*) FROM icerik.pipeline_run").fetchone()
        kalinti = baglanti.execute(
            "SELECT (SELECT count(*) FROM icerik.unit WHERE anchor LIKE 'q:1:%%' OR"
            " source_id LIKE 'test-%%') + (SELECT count(*) FROM icerik.source"
            " WHERE slug LIKE 'test-%%')"
        ).fetchone()
        assert ilk is not None
        assert kalinti is not None
        if kalinti[0] != 0:
            baglanti.rollback()
            _yok("mutalaa_test icinde test- kaynak ya da q:1:% capasi kalmis")
        yield baglanti
    finally:
        baglanti.rollback()
        son = baglanti.execute("SELECT count(*) FROM icerik.pipeline_run").fetchone()
        baglanti.rollback()
        baglanti.close()
    assert son is not None
    assert son[0] == ilk[0], "pipeline_run satir sayisi degismemeli"


def say(conn: psycopg.Connection, sorgu: str, *param: object) -> int:
    satir_ = conn.execute(sorgu, param).fetchone()  # type: ignore[arg-type]
    assert satir_ is not None
    return int(satir_[0])


def unit_say(conn: psycopg.Connection, kaynak: str = ANA) -> int:
    return say(conn, "SELECT count(*) FROM icerik.unit WHERE source_id = %s", kaynak)


def kimlik_son_deger(conn: psycopg.Connection) -> object:
    return conn.execute(
        "SELECT last_value FROM pg_sequences"
        " WHERE schemaname || '.' || sequencename = pg_get_serial_sequence('icerik.unit', 'id')"
    ).fetchone()


@pytest.mark.veritabani
def test_ilk_yukleme_sonra_ikinci_kosu_sifir_degisiklik(
    tmp_path: Path, conn: psycopg.Connection
) -> None:
    s = senaryo_kur(tmp_path)
    zincir_kur(s)
    assert calistir(s, conn) == 0
    ilk = sayilar(s)
    assert (ilk["eklenen"], ilk["guncellenen"], ilk["degismeyen"], ilk["staging"]) == (3, 0, 0, 3)
    assert (ilk["kaynak_eklenen"], ilk["kaynak_guncellenen"]) == (2, 0)
    assert unit_say(conn) == 3
    satirlar = conn.execute(
        "SELECT metin_durumu::text, kind::text, status::text, rev, run_id::text,"
        " lower(ayah_range), upper(ayah_range) FROM icerik.unit WHERE anchor = 'q:1:2'"
    ).fetchall()
    assert satirlar[0][:4] == ("onayli", "ayet", "etkin", 1)
    assert satirlar[0][5:] == (2, 3)
    run = conn.execute(
        "SELECT run_id::text, durum, manifest->>'source_id', parmak_izi"
        " FROM icerik.pipeline_run WHERE komut = 'export pg'"
    ).fetchall()
    assert len(run) == 1
    assert run[0][1:3] == ("basarili", ANA)
    assert len(str(run[0][3]).strip()) == 64
    assert satirlar[0][4] == run[0][0]
    kaynak = conn.execute(
        "SELECT notice_text, surum, alinma_tarihi::text, dosya_sha256 FROM icerik.source"
        " WHERE slug = %s",
        (ANA,),
    ).fetchone()
    assert kaynak is not None
    assert kaynak[0] == BILDIRIM
    assert kaynak[1] == "1.0"
    assert kaynak[2] == TARIH
    assert kaynak[3] == lineage.sha256_bayt(b"Deneme ham dosya test-ana\n")
    assert say(conn, "SELECT count(*) FROM icerik.source WHERE slug = %s", EK) == 1

    # Ikinci kosu: yeni zincir ayni icerikle; --force etkisiz, hicbir satir degismez.
    zincir_kur(s)
    onceki_kimlik = kimlik_son_deger(conn)
    guncelleme = conn.execute(
        "SELECT max(updated_at) FROM icerik.unit UNION ALL SELECT max(updated_at)"
        " FROM icerik.source"
    ).fetchall()
    assert calistir(s, conn, force=True) == 0
    ikinci = sayilar(s)
    assert (ikinci["eklenen"], ikinci["guncellenen"], ikinci["degismeyen"]) == (0, 0, 3)
    assert (ikinci["kaynak_eklenen"], ikinci["kaynak_guncellenen"]) == (0, 0)
    assert ikinci["kaynak_degismeyen"] == 2
    assert kimlik_son_deger(conn) == onceki_kimlik  # IDENTITY harcanmadi
    assert (
        conn.execute(
            "SELECT max(updated_at) FROM icerik.unit UNION ALL SELECT max(updated_at)"
            " FROM icerik.source"
        ).fetchall()
        == guncelleme
    )
    assert say(conn, "SELECT count(*) FROM icerik.pipeline_run WHERE komut = 'export pg'") == 2


@pytest.mark.veritabani
def test_turetilmis_alanlar_guncellenir_metin_degismez_yeni_capa_eklenir(
    tmp_path: Path, conn: psycopg.Connection
) -> None:
    s = senaryo_kur(tmp_path)
    zincir_kur(s)
    assert calistir(s, conn) == 0
    korunan = (
        "SELECT anchor, metin, content_hash, metin_durumu::text, status::text, rev,"
        " marks::text, successors::text, source_id, run_id::text FROM icerik.unit"
        " ORDER BY anchor"
    )
    once = conn.execute(korunan).fetchall()
    yeni = [
        satir(1),
        satir(2, ar_norm="degisti", data_version="test@2.0"),
        satir(3, ord=30, ayah_lo=30, ayah_hi=31),
        satir(4),
    ]
    zincir_kur(s, yeni)
    assert calistir(s, conn) == 0
    rapor = sayilar(s)
    assert (rapor["eklenen"], rapor["guncellenen"], rapor["degismeyen"]) == (1, 2, 1)
    sonra = conn.execute(korunan).fetchall()
    assert len(sonra) == 4
    for eski, yeni_satir in zip(once, sonra[:3], strict=True):
        # metin, content_hash, metin_durumu, status, rev, marks, successors, source_id ayni
        assert eski[:9] == yeni_satir[:9]
    kayit = conn.execute(
        "SELECT ar_norm, data_version, ord, lower(ayah_range), run_id::text FROM icerik.unit"
        " WHERE anchor IN ('q:1:2', 'q:1:3', 'q:1:1') ORDER BY anchor"
    ).fetchall()
    assert kayit[1][:2] == ("degisti", "test@2.0")
    assert kayit[2][2:4] == (30, 30)
    assert kayit[0][4] == once[0][9]  # degismeyen satirin run_id'si korunur
    assert kayit[1][4] != once[1][9]


@pytest.mark.veritabani
def test_ozet_farki_cikis_1_ve_geri_alinir(tmp_path: Path, conn: psycopg.Connection) -> None:
    s = senaryo_kur(tmp_path)
    zincir_kur(s)
    assert calistir(s, conn) == 0
    zincir_kur(s, [satir(1, "Deneme degisen metin 1"), satir(2), satir(3), satir(4)])
    assert calistir(s, conn) == 1
    assert unit_say(conn) == 3  # q:1:4 de eklenmedi: islem geri alindi
    assert say(conn, "SELECT count(*) FROM icerik.unit WHERE metin = 'Deneme metni 1'") == 1
    # basarisiz satiri dis islemin icinde gorulur; calisiyor satiri kalmaz
    assert say(conn, "SELECT count(*) FROM icerik.pipeline_run WHERE durum = 'basarisiz'") == 1
    assert say(conn, "SELECT count(*) FROM icerik.pipeline_run WHERE durum = 'calisiyor'") == 0


@pytest.mark.veritabani
def test_yalniz_metin_farki_content_hash_ayni_olsa_da_cikis_1_ve_geri_alinir(
    tmp_path: Path, conn: psycopg.Connection, capsys: pytest.CaptureFixture[str]
) -> None:
    """K-39 madde 2: veritabanindaki metin staged'den farkliysa `content_hash` ayni olsa da durur.

    Metni elle (ya da bir hatayla) degismis ama `content_hash`i eski kalmis satir sessizce
    gecilmez ve hat tarafindan duzeltilmez (UPDATE listesinde `metin` yok): islem geri alinir.
    """
    s = senaryo_kur(tmp_path)
    zincir_kur(s)
    assert calistir(s, conn) == 0
    conn.execute("UPDATE icerik.unit SET metin = metin || 'x' WHERE anchor = 'q:1:2'")
    zincir_kur(s)  # staged ayni: yalnizca veritabanindaki metin kaymis
    capsys.readouterr()
    assert calistir(s, conn) == 1
    assert "var olan capada content_hash/metin farki (1): q:1:2" in capsys.readouterr().err
    assert say(conn, "SELECT count(*) FROM icerik.unit WHERE metin = 'Deneme metni 2x'") == 1
    assert (
        say(
            conn,
            "SELECT count(*) FROM icerik.unit WHERE anchor = 'q:1:2' AND content_hash = %s",
            ozet("Deneme metni 2"),
        )
        == 1
    )  # content_hash eski kaldi: fark yalniz metinde
    assert unit_say(conn) == 3
    assert say(conn, "SELECT count(*) FROM icerik.pipeline_run WHERE durum = 'basarisiz'") == 1
    assert say(conn, "SELECT count(*) FROM icerik.pipeline_run WHERE durum = 'calisiyor'") == 0


@pytest.mark.veritabani
def test_onceki_yuklemedeki_capa_eksikse_cikis_1(tmp_path: Path, conn: psycopg.Connection) -> None:
    s = senaryo_kur(tmp_path)
    zincir_kur(s)
    assert calistir(s, conn) == 0
    zincir_kur(s, [satir(1), satir(2)])
    assert calistir(s, conn) == 1
    assert unit_say(conn) == 3


@pytest.mark.veritabani
def test_baska_kaynaga_ait_capa_cikis_2(tmp_path: Path, conn: psycopg.Connection) -> None:
    s = senaryo_kur(tmp_path)
    zincir_kur(s)
    assert calistir(s, conn) == 0
    conn.execute(
        "INSERT INTO icerik.unit (anchor, kind, source_id, ord, metin, content_hash,"
        " data_version) VALUES ('q:1:9', 'ayet', %s, 9, 'Deneme baska', %s, 'x')",
        (EK, ozet("Deneme baska")),
    )
    zincir_kur(s, [satir(1), satir(2), satir(3), satir(9, "Deneme baska")])
    assert calistir(s, conn) == 2
    assert unit_say(conn) == 3
    assert unit_say(conn, EK) == 1


@pytest.mark.veritabani
def test_source_tablosu_hedef_sutunlara_sahip(conn: psycopg.Connection) -> None:
    """Sema A07'nin yeniden uretilen ilk gocudur: `icerik.source` 16 sutun, `id` yok."""
    sutunlar = [
        str(satir_[0])
        for satir_ in conn.execute(
            "SELECT column_name FROM information_schema.columns"
            " WHERE table_schema = 'icerik' AND table_name = 'source' ORDER BY ordinal_position"
        ).fetchall()
    ]
    assert sutunlar == list(HEDEF_SUTUNLAR)


@pytest.mark.veritabani
def test_source_ilk_ekleme_butun_toml_alanlariyla(tmp_path: Path, conn: psycopg.Connection) -> None:
    s = senaryo_kur(
        tmp_path,
        yazar="Deneme Yazar",
        provider="deneme",
        baski_bilgisi={"yil": 1935},
        notlar="Deneme teknik not.",
        atif_url="https://deneme.invalid/atif",
    )
    zincir_kur(s)
    assert calistir(s, conn) == 0
    kaynak = conn.execute(
        "SELECT tur::text, baslik, yazar, provider, kaynak_url, baski_bilgisi, atif_metni,"
        " atif_url, notlar FROM icerik.source WHERE slug = %s",
        (ANA,),
    ).fetchone()
    assert kaynak == (
        "kuran_metni",
        "Deneme kaynak",
        "Deneme Yazar",
        "deneme",
        "https://deneme.invalid/",
        {"yil": 1935},
        "Deneme atif metni.",
        "https://deneme.invalid/atif",
        "Deneme teknik not.",
    )


@pytest.mark.veritabani
def test_betimleyici_alanlar_degisince_guncellenir(
    tmp_path: Path, conn: psycopg.Connection
) -> None:
    """K-39 madde 3: TOML'daki betimleyici alan degisince hat satiri gunceller."""
    s = senaryo_kur(tmp_path)
    zincir_kur(s)
    assert calistir(s, conn) == 0
    toml_yeniden(
        s,
        ANA,
        baslik="Deneme yeni baslik",
        atif_metni="Deneme yeni atif",
        atif_url="https://deneme.invalid/atif",
        kaynak_url="https://deneme.invalid/yeni",
    )
    zincir_kur(s)
    assert calistir(s, conn) == 0
    rapor = sayilar(s)
    assert (rapor["kaynak_guncellenen"], rapor["kaynak_degismeyen"]) == (1, 1)
    kaynak = conn.execute(
        "SELECT baslik, atif_metni, atif_url, kaynak_url, notice_text FROM icerik.source"
        " WHERE slug = %s",
        (ANA,),
    ).fetchone()
    assert kaynak == (
        "Deneme yeni baslik",
        "Deneme yeni atif",
        "https://deneme.invalid/atif",
        "https://deneme.invalid/yeni",
        BILDIRIM,
    )


@pytest.mark.veritabani
def test_source_varsa_yalniz_betimleyici_alan_guncellenir(
    tmp_path: Path, conn: psycopg.Connection
) -> None:
    s = senaryo_kur(tmp_path)
    zincir_kur(s)
    assert calistir(s, conn) == 0
    conn.execute(
        "UPDATE icerik.source SET notlar = 'Deneme editor notu', yazar = 'Deneme editor yazar'"
        " WHERE slug = %s",
        (ANA,),
    )
    toml_yeniden(
        s,
        ANA,
        baslik="Deneme yeni baslik",
        notlar="Deneme baska not",
        surum="1.2",
        yazar="Deneme baska yazar",
        provider="deneme",
        tur="meal",
    )
    zincir_kur(s)
    assert calistir(s, conn) == 0
    rapor = sayilar(s)
    assert (rapor["kaynak_guncellenen"], rapor["kaynak_degismeyen"]) == (1, 1)
    kaynak = conn.execute(
        "SELECT baslik, surum, notlar, yazar, provider, tur::text FROM icerik.source"
        " WHERE slug = %s",
        (ANA,),
    ).fetchone()
    # Betimleyici: baslik, surum. Betimleyici olmayan: notlar, yazar, provider, tur (editorundur).
    assert kaynak == (
        "Deneme yeni baslik",
        "1.2",
        "Deneme editor notu",
        "Deneme editor yazar",
        None,
        "kuran_metni",
    )


@pytest.mark.veritabani
def test_surum_cozulemezse_cikis_2(tmp_path: Path, conn: psycopg.Connection) -> None:
    s = senaryo_kur(tmp_path, surum=None)
    zincir_kur(s)
    assert calistir(s, conn) == 2
    assert say(conn, "SELECT count(*) FROM icerik.source WHERE slug LIKE 'test-%%'") == 0
    assert say(conn, "SELECT count(*) FROM icerik.pipeline_run WHERE durum = 'basarisiz'") == 1


@pytest.mark.veritabani
def test_dry_run_hicbir_satir_yazmaz(tmp_path: Path, conn: psycopg.Connection) -> None:
    s = senaryo_kur(tmp_path)
    zincir_kur(s)
    onceki_kosu = say(conn, "SELECT count(*) FROM icerik.pipeline_run")
    assert calistir(s, conn, dry_run=True) == 0
    rapor = sayilar(s)
    assert (rapor["eklenen"], rapor["kaynak_eklenen"]) == (3, 2)
    assert son_rapor(s)["dry_run"] is True
    assert unit_say(conn) == 0
    assert say(conn, "SELECT count(*) FROM icerik.source WHERE slug LIKE 'test-%%'") == 0
    assert say(conn, "SELECT count(*) FROM icerik.pipeline_run") == onceki_kosu
    assert calistir(s, conn) == 0  # gercek kosu: dry-run izi birakmadi
    assert sayilar(s)["eklenen"] == 3


@pytest.mark.veritabani
def test_veritabaninda_bildirim_notice_txt_ile_tutarli(
    tmp_path: Path, conn: psycopg.Connection
) -> None:
    s = senaryo_kur(tmp_path)
    zincir_kur(s)
    assert calistir(s, conn) == 0
    kayit = conn.execute(
        "SELECT encode(sha256(convert_to(notice_text, 'UTF8')), 'hex') FROM icerik.source"
        " WHERE slug = %s",
        (ANA,),
    ).fetchone()
    assert kayit == (ozet(BILDIRIM),)


# --- hedef sema ve K-39 madde 3 (veritabani gerekmez) -------------------------------------


def test_betimleyici_alanlar_k39_madde_3() -> None:
    assert pg.BETIMLEYICI_ALANLAR == (
        "baslik",
        "surum",
        "kaynak_url",
        "atif_metni",
        "atif_url",
        "notice_text",
        "alinma_tarihi",
        "dosya_sha256",
    )
    assert qa.KAPILAR == ("G-KAY", "G-BUT", "G-CAP", "G-NOR")


def test_insert_ve_select_yalniz_hedef_sutunlari_kullanir() -> None:
    ekleme = re.search(r"INSERT INTO icerik\.source \((.*?)\) VALUES", pg.INSERT_SOURCE)
    assert ekleme is not None
    eklenen = [sutun.strip() for sutun in ekleme.group(1).split(",")]
    assert set(eklenen) <= set(HEDEF_SUTUNLAR)
    assert "id" not in eklenen
    assert set(pg.BETIMLEYICI_ALANLAR) <= set(HEDEF_SUTUNLAR)
    secim = pg.SELECT_SOURCE.as_string()
    for alan in pg.BETIMLEYICI_ALANLAR:
        assert f'"{alan}"' in secim
    for eski in ("license", "lisans", "kurul", "embed_ok", "kisitlar", "yeniden_kontrol"):
        assert eski not in pg.INSERT_SOURCE
        assert eski not in secim
    for eski in ("kamu_mali", "vefat"):
        assert eski not in pg.INSERT_SOURCE


def _ana_kaynak(s: Senaryo) -> Kaynak:
    kayitlar = {r.kaynak.slug: r.kaynak for r in sources.yukle(s.kok) if r.kaynak is not None}
    return kayitlar[ANA]


def _hazirlik_ornegi(kaynak: Kaynak) -> pg.Hazirlik:
    """`_istenen` icin yeterli, dosya ve veritabani gerektirmeyen hazirlik."""
    ham = [{"yol": f"raw/{kaynak.slug}/{TARIH}/deneme.txt", "sha256": "0" * 64}]
    return pg.Hazirlik(
        source_id=kaynak.slug,
        kaynak_idleri=(kaynak.slug,),
        anchor_run_id="",
        units_yol="",
        units_sha256="",
        satirlar=[],
        zincir=[],
        ingest={},
        ham={kaynak.slug: ham},
        qa_rapor_id="",
        kaynaklar={kaynak.slug: kaynak},
        bildirimler={kaynak.slug: kaynak.notice_text},
        parmak="",
    )


def test_insert_parametreleri_sutunlarla_ayni_sirada_ve_eksiksiz(tmp_path: Path) -> None:
    """CI'da veritabani yokken de: INSERT yer tutucusu, sutun ve kodun verdigi parametre uyusur."""
    ekleme = re.fullmatch(r"INSERT INTO icerik\.source \((.*?)\) VALUES \((.*)\)", pg.INSERT_SOURCE)
    assert ekleme is not None
    sutunlar = [sutun.strip() for sutun in ekleme.group(1).split(",")]
    parametreler = re.findall(r"%\((\w+)\)s", ekleme.group(2))
    assert parametreler == sutunlar  # yer tutucu adi sutun adidir ve ayni siradadir
    kaynak = _ana_kaynak(senaryo_kur(tmp_path))
    istenen = pg._istenen(kaynak, _hazirlik_ornegi(kaynak))
    assert tuple(istenen) == pg.BETIMLEYICI_ALANLAR
    assert set(pg._ekleme_parametreleri(kaynak, istenen)) == set(parametreler)


def test_hedef_sutunlar_sunucu_sema_goruntusuyle_ayni() -> None:
    """`icerik.source` sutunlari ve sirasi, EF modelinden uretilen sema goruntusuyle ayni."""
    yol = depo_koku() / "server/tests/Mutalaa.Api.Tests/Snapshots/editoryal-sema.sql"
    sema = yol.read_bytes().decode("utf-8")
    blok = re.search(r"^CREATE TABLE icerik\.source \((.*?)^\);", sema, re.DOTALL | re.MULTILINE)
    assert blok is not None
    sutunlar = tuple(satir.split()[0] for satir in blok.group(1).splitlines() if satir.strip())
    assert sutunlar == HEDEF_SUTUNLAR


# --- dosya onkosullari (veritabani gerekmez) ---------------------------------------------


def test_qa_raporu_yoksa_cikis_1(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    s = senaryo_kur(tmp_path)
    zincir_kur(s, qa_yaz=False)
    hata_ile(s, 1, "QA raporu yok", capsys)


def test_qa_kapisi_kaldiysa_cikis_1(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    s = senaryo_kur(tmp_path)
    zincir_kur(s, kapilar={**TUM_GECTI, "G-CAP": "kaldi"})
    hata_ile(s, 1, "QA kapisi gecmedi: G-CAP", capsys)


def test_qa_raporu_dort_kapiyi_icermiyorsa_cikis_1(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    s = senaryo_kur(tmp_path)
    zincir_kur(s, kapilar={"G-CAP": "gecti"})
    hata_ile(s, 1, "dort kapiyi da icermiyor", capsys)


def test_qa_raporu_eski_g_lis_adiyla_cikis_1(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Kapi G-LIS'ten G-KAY'a donustu: eski adli rapor dort kapiyi da icermez."""
    s = senaryo_kur(tmp_path)
    zincir_kur(s, kapilar=dict.fromkeys(("G-LIS", "G-BUT", "G-CAP", "G-NOR"), "gecti"))
    hata_ile(s, 1, "dort kapiyi da icermiyor", capsys)


def test_qa_raporu_ozeti_uyusmuyorsa_cikis_1(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    s = senaryo_kur(tmp_path)
    zincir_kur(s, qa_sha="0" * 64)
    hata_ile(s, 1, "ozeti icin QA raporu yok", capsys)


def qa_raporu_ekle(s: Senaryo, **alanlar: object) -> None:
    """Ayni anchor calismasi icin, mevcut raporlardan SONRA gelen bir `qa run` raporu."""
    anchor = lineage.son_basarili(s.veri / "staged" / ANA, "anchor")
    assert anchor is not None
    rapor: dict[str, object] = {
        "komut": "qa run",
        "kaynak": ANA,
        "anchor_run_id": anchor[0],
        "units_sha256": lineage.sha256_dosya(anchor[1] / "units.jsonl"),
        "cikis_kodu": 0,
    }
    rapor.update(alanlar)
    yol = s.veri / "reports" / f"{s.uretici.uret()}.json"
    yol.write_text(json.dumps(rapor), encoding="utf-8", newline="\n")


def test_sonraki_tamamlanamayan_qa_kosusu_gecen_raporu_gecersiz_kilar(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`qa run` vektor dosyasi hatasi gibi bir nedenle 2 ile bitti: kapi iddia etmez."""
    s = senaryo_kur(tmp_path)
    zincir_kur(s)
    qa_raporu_ekle(s, cikis_kodu=2)
    hata_ile(s, 1, "son QA kosusu tamamlanmadi (cikis 2)", capsys)


def test_sonraki_kalan_kismi_qa_kosusu_gecen_raporu_gecersiz_kilar(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    s = senaryo_kur(tmp_path)
    zincir_kur(s)
    qa_raporu_ekle(s, cikis_kodu=1, kapilar={"G-KAY": "kaldi"})
    hata_ile(s, 1, "QA kapisi gecmedi: G-KAY", capsys)


def test_zincirdeki_ingest_en_son_degilse_cikis_1(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    s = senaryo_kur(tmp_path)
    zincir_kur(s)
    # EK icin daha yeni bir ingest calistirmasi: zincirdeki artik en son degil.
    yeni = str(s.uretici.uret())
    _staged_calisma(s, EK, yeni, "ingest", {"units.jsonl": b'{"deneme":3}\n'}, [])
    hata_ile(s, 1, "icin en son ingest degil", capsys)


def test_staged_content_hash_metinle_tutmuyorsa_cikis_1(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    s = senaryo_kur(tmp_path)
    zincir_kur(s, [satir(1, content_hash="0" * 64), satir(2)])
    hata_ile(s, 1, "staged content_hash metinle tutmuyor (1): q:1:1", capsys)


def test_notice_txt_toml_ile_farkliysa_cikis_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    s = senaryo_kur(tmp_path)
    zincir_kur(s, notice=BILDIRIM + "\n")  # TOML'dakinden bir LF fazla: rstrip yok
    hata_ile(s, 2, "notice.txt ile TOML notice_text ayni degil", capsys)


BOZUK_SATIRLAR = [
    ("kind", [satir(1, kind="yok"), satir(2)], "satir 1: kind gecersiz"),
    ("kind_metin_degil", [satir(1, kind=7)], "satir 1: kind gecersiz"),
    ("bos_aralik", [satir(1, ayah_hi=1)], "satir 1: ord ya da ayah_lo/ayah_hi gecersiz"),
    ("ord_sifir", [satir(1, ord=0)], "satir 1: ord ya da ayah_lo/ayah_hi gecersiz"),
    ("ord_bool", [satir(1, ord=True)], "satir 1: ord ya da ayah_lo/ayah_hi gecersiz"),
    ("ord_ondalik", [satir(1, ord=1.5)], "satir 1: JSON gecersiz"),  # ondalik sayi desteklenmez
    ("metin_durumu", [satir(1, metin_durumu="taslak")], "satir 1: metin_durumu onayli degil"),
    ("yinelenen_capa", [satir(1), satir(1)], "satir 2: yinelenen anchor"),
    ("source_id", [satir(1, source_id=EK)], "satir 1: source_id --source ile ayni degil"),
    ("provenance_metin", [satir(1, provenance="deneme")], "satir 1: provenance nesne degil"),
    ("provenance_liste", [satir(1, provenance=[])], "satir 1: provenance nesne degil"),
    ("anchor_metin_degil", [satir(1, anchor=5)], "satir 1: anchor metin degil"),
    ("anchor_gecersiz", [satir(1, anchor="q:1:300")], "satir 1: anchor gecersiz"),
    ("anchor_buyuk_harf", [satir(1, anchor="Q:1:1")], "satir 1: anchor gecersiz"),
    ("metin_bos", [satir(1, text="")], "satir 1: text bos ya da NUL iceriyor"),
    ("metin_nul", [satir(1, text="Deneme\x00")], "satir 1: text bos ya da NUL iceriyor"),
    ("metin_degil", [satir(1, text=3)], "satir 1: text bos ya da NUL iceriyor"),
    ("content_hash_bicim", [satir(1, content_hash="ABC")], "content_hash 64 haneli"),
    ("ar_norm_sayi", [satir(1, ar_norm=3)], "satir 1: ar_norm gecersiz"),
    ("ar_norm_nul", [satir(1, ar_norm="a\x00")], "satir 1: ar_norm gecersiz"),
    ("data_version_bos", [satir(1, data_version="")], "satir 1: data_version gecersiz"),
    ("data_version_sayi", [satir(1, data_version=1)], "satir 1: data_version gecersiz"),
]


@pytest.mark.parametrize(
    ("satirlar", "ileti"),
    [pytest.param(s, i, id=kimlik) for kimlik, s, i in BOZUK_SATIRLAR],
)
def test_bozuk_units_satiri_cikis_2(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    satirlar: list[dict[str, object]],
    ileti: str,
) -> None:
    s = senaryo_kur(tmp_path)
    zincir_kur(s, satirlar)
    hata_ile(s, 2, ileti, capsys)


@pytest.mark.parametrize("eksik", ["anchor", "kind", "ord", "ayah_lo", "text", "provenance"])
def test_units_satirinda_alan_eksikse_cikis_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], eksik: str
) -> None:
    kayit = satir(1)
    del kayit[eksik]
    s = senaryo_kur(tmp_path)
    zincir_kur(s, [kayit])
    hata_ile(s, 2, f"satir 1: alan eksik: {eksik}", capsys)


@pytest.mark.parametrize(
    ("baytlar", "ileti"),
    [
        pytest.param(b"", "bos ya da son satir LF ile bitmiyor", id="bos"),
        pytest.param(b'{"anchor":"q:1:1"}', "bos ya da son satir LF ile bitmiyor", id="lf_yok"),
        pytest.param(b"{bozuk\n", "satir 1: JSON gecersiz", id="json_bozuk"),
        pytest.param(b'{"a":1,"a":2}\n', "satir 1: JSON gecersiz", id="yinelenen_anahtar"),
        pytest.param(b'{"a":1.5}\n', "satir 1: JSON gecersiz", id="ondalik_sayi"),
        pytest.param(b"\xff\n", "satir 1: UTF-8 degil", id="utf8_degil"),
        pytest.param(b"[1]\n", "satir 1: nesne degil", id="nesne_degil"),
    ],
)
def test_units_jsonl_bicim_hatalari_cikis_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], baytlar: bytes, ileti: str
) -> None:
    s = senaryo_kur(tmp_path)
    zincir_kur(s, units_bayt=baytlar)
    hata_ile(s, 2, ileti, capsys)


def test_kayitsiz_ek_kaynak_cikis_2(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """G-KAY: kayitsiz kaynak hatta alinmaz (cikis 2); veritabani baglantisi acilmaz."""
    s = senaryo_kur(tmp_path)
    zincir_kur(s)
    (s.kok / "pipeline" / "sources" / f"{EK}.toml").unlink()
    hata_ile(s, 2, "kayitsiz", capsys)


def test_gecersiz_kayit_cikis_2(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """G-KAY: kayit gecerli olmali; eski lisans alani bilinmeyen alan olarak kaydi bozar."""
    s = senaryo_kur(tmp_path)
    zincir_kur(s)
    toml_yeniden(s, EK, license_status="serbest")
    hata_ile(s, 2, "kayit gecersiz", capsys)


@pytest.mark.parametrize("atif", ["", "   "])
def test_atif_metni_bos_cikis_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], atif: str
) -> None:
    """G-KAY: `atif_metni` dolu olmali."""
    s = senaryo_kur(tmp_path)
    zincir_kur(s)
    toml_yeniden(s, ANA, atif_metni=atif)
    hata_ile(s, 2, "kayit gecersiz", capsys)


def test_notice_txt_var_toml_notice_yoksa_cikis_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """G-KAY: dosyada bildirim blogu varsa TOML'daki `notice_text` bayt bayt ayni olmali."""
    s = senaryo_kur(tmp_path)
    zincir_kur(s)
    toml_yeniden(s, ANA, notice_text=None)
    hata_ile(s, 2, "notice.txt ile TOML notice_text ayni degil", capsys)


def test_kanonik_kaynakta_notice_txt_yoksa_cikis_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """G-KAY: TOML bildirim tasiyan kanonik kaynakta `notice.txt` yoksa bayt denetimi atlanmaz."""
    s = senaryo_kur(tmp_path)
    zincir_kur(s, notice=None)
    hata_ile(s, 2, "TOML notice_text var ama notice.txt yok", capsys)


def test_tanimsiz_kaynak_cikis_2(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    s = senaryo_kur(tmp_path)
    hata_ile(s, 2, "tanimsiz kaynak", capsys, source="test-baska")


def test_anchor_calismasi_yoksa_ve_run_gecersizse_cikis_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    s = senaryo_kur(tmp_path)
    hata_ile(s, 2, "manifestli anchor calistirmasi yok", capsys)
    zincir_kur(s)
    hata_ile(s, 2, "--run bir UUID degil", capsys, run="uuid-degil")
    hata_ile(
        s, 2, "--run icin manifestli anchor calistirmasi yok", capsys, run=str(s.uretici.uret())
    )


# --- zincir butunlugu: ham dosya, manifest ve cikti ozetleri -------------------------------


def calisma(s: Senaryo, kaynak: str, adim: str) -> tuple[Path, dict[str, object]]:
    """Kaynagin en son `adim` calistirmasi: (klasor, manifest)."""
    kayit = lineage.son_basarili(s.veri / "staged" / kaynak, adim)
    assert kayit is not None, (kaynak, adim)
    return kayit[1], kayit[2]


def test_ham_dosya_degismisse_cikis_2(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Ham dosya manifestteki ozetle tutmuyor (`data/raw` degismez)."""
    s = senaryo_kur(tmp_path)
    zincir_kur(s)
    ham = s.veri / "raw" / ANA / TARIH / f"{ANA}.txt"
    ham.write_bytes(ham.read_bytes() + b"Deneme degisiklik\n")
    hata_ile(s, 2, "ham dosya yok ya da ozeti tutmuyor", capsys)


def test_ham_dosya_yoksa_cikis_2(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    s = senaryo_kur(tmp_path)
    zincir_kur(s)
    (s.veri / "raw" / EK / TARIH / f"{EK}.txt").unlink()
    hata_ile(s, 2, "ham dosya yok ya da ozeti tutmuyor", capsys)


def test_ham_girdi_ozeti_gecersizse_cikis_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    s = senaryo_kur(tmp_path)
    zincir_kur(s)
    klasor, manifest = calisma(s, ANA, "ingest")
    girdiler = manifest["girdiler"]
    assert isinstance(girdiler, list)
    girdiler[0]["sha256"] = "ABC"
    lineage.manifest_yaz(klasor, manifest)
    hata_ile(s, 2, "ham dosya ozeti gecersiz", capsys)


def test_anchor_ciktisi_bozulmussa_cikis_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Anchor `units.jsonl` dosyasi manifestteki ozetle tutmuyor: ilk eleyen cikti denetimidir."""
    s = senaryo_kur(tmp_path)
    zincir_kur(s)
    klasor, _ = calisma(s, ANA, "anchor")
    units = klasor / "units.jsonl"
    units.write_bytes(units.read_bytes() + b"\n")
    hata_ile(s, 2, "anchor calistirmasinin ciktilari saglam degil", capsys)


def test_anchor_manifestinde_units_ozeti_yoksa_cikis_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Manifest saglam bir baska cikti listeler ama `units.jsonl` ozeti tasimaz."""
    s = senaryo_kur(tmp_path)
    zincir_kur(s)
    klasor, manifest = calisma(s, ANA, "anchor")
    baska = klasor / "baska.txt"
    baska.write_bytes(b"Deneme baska cikti\n")
    manifest["ciktilar"] = [
        {
            "yol": f"staged/{ANA}/{klasor.name}/baska.txt",
            "sha256": lineage.sha256_bayt(baska.read_bytes()),
        }
    ]
    lineage.manifest_yaz(klasor, manifest)
    assert lineage.ciktilar_saglam(s.veri, manifest)  # cikti denetimi bunu yakalamaz
    hata_ile(s, 2, "units.jsonl ozeti manifestle tutmuyor", capsys)


@pytest.mark.parametrize(("kaynak", "adim"), [(ANA, "normalize"), (ANA, "ingest"), (EK, "ingest")])
def test_zincirdeki_calismanin_ciktisi_bozulmussa_cikis_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], kaynak: str, adim: str
) -> None:
    s = senaryo_kur(tmp_path)
    zincir_kur(s)
    klasor, _ = calisma(s, kaynak, adim)
    units = klasor / "units.jsonl"
    units.write_bytes(units.read_bytes() + b"\n")
    hata_ile(s, 2, "zincirdeki calistirmanin ciktilari saglam degil", capsys)


def test_zincirde_manifesti_olmayan_calisma_cikis_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    s = senaryo_kur(tmp_path)
    zincir_kur(s)
    klasor, _ = calisma(s, EK, "ingest")
    (klasor / "manifest.json").unlink()
    hata_ile(s, 2, "zincirde manifesti olmayan calistirma", capsys)


def test_rapor_baglanti_dizesi_ve_icerik_yazmaz(tmp_path: Path) -> None:
    s = senaryo_kur(tmp_path)
    zincir_kur(s, kapilar={**TUM_GECTI, "G-KAY": "kaldi"})
    assert calistir(s) == 1
    raporlar = b"".join(p.read_bytes() for p in (s.veri / "reports").glob("*.json"))
    raporlar += b"".join(p.read_bytes() for p in (s.veri / "logs").glob("*.jsonl"))
    assert b"Deneme metni" not in raporlar


def test_cli_export_pg_kayitsiz_kaynak_cikis_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    kok = kok_kur(tmp_path)
    monkeypatch.setenv("MUTALAA_VERI_KOK", str(tmp_path / "data"))
    sonuc = CliRunner().invoke(
        cli.app, ["export", "pg", "--source", "tanzil-uthmani", "--kok", str(kok)]
    )
    assert sonuc.exit_code == 2, sonuc.stderr
    assert "kaynak kaydi" in sonuc.stderr
    assert "lisans" not in sonuc.stderr
