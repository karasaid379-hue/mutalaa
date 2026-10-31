"""`export pg`: kaynak zinciri, QA kapisi, K-39 yazim kurallari (SENTETIK veri).

Butun metinler "Deneme ..." biciminde sentetiktir; kaynaklar `test-` onekli, TOML'lari `tmp_path`
altindaki sahte kokte durur. `veritabani` isaretli testler yalniz turetilmis test adresine
(`Ayarlar.test_db_adresi()`) baglanir, hepsi dis islem icinde kosar ve sonunda geri alinir.
"""

import json
import os
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

import psycopg
import pytest
from hat_yardimci import ayarlar_kur
from test_sources import alanlar_kur, kayit_yaz, kok_kur
from typer.testing import CliRunner

from mutalaa_pipeline import cli, lineage
from mutalaa_pipeline.config import Ayarlar
from mutalaa_pipeline.db import baglan
from mutalaa_pipeline.export import pg
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.runctx import Uuid7Uretici

ANA = "test-ana"
EK = "test-ek"
TARIH = "2026-10-28"
BILDIRIM = "Deneme bildirimi\n\n  Ikinci satir \n"
KAPILAR = ("G-LIS", "G-BUT", "G-CAP", "G-NOR")
TUM_GECTI = dict.fromkeys(KAPILAR, "gecti")


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
        "kurul_gerekli": True,
        "kisitlar": {"degistirme_yasak": True},
        "notice_text": BILDIRIM,
        "kaynak_url": "https://deneme.invalid/",
    }
    ana.update(ana_alanlar)
    kayit_yaz(kok, alanlar_kur(ANA, kok, **ana))
    kayit_yaz(kok, alanlar_kur(EK, kok, surum="1.1", baslik="Deneme ek kaynak"))
    return Senaryo(tmp_path, kok, ayarlar_kur(tmp_path))


def toml_yeniden(s: Senaryo, slug: str, **degisim: object) -> None:
    """Kaynak TOML'unu degisiklikle yeniden yazar (lisans kopyasi ayni kalir)."""
    taban: dict[str, object] = (
        {
            "tur": "kuran_metni",
            "surum": "1.0",
            "kurul_gerekli": True,
            "kisitlar": {"degistirme_yasak": True},
            "notice_text": BILDIRIM,
            "kaynak_url": "https://deneme.invalid/",
        }
        if slug == ANA
        else {"surum": "1.1", "baslik": "Deneme ek kaynak"}
    )
    taban.update(degisim)
    kayit_yaz(s.kok, alanlar_kur(slug, s.kok, **taban))


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
        lisans_kopyalari={},
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
) -> str:
    """ingest (iki kaynak) -> normalize -> anchor zinciri ve QA raporu; anchor run_id doner."""
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


class Cagrilmaz:
    """Dosya onkosulu hatasinda veritabani baglantisi acilmamali."""

    def __init__(self) -> None:
        self.sayi = 0

    def __call__(self) -> psycopg.Connection:
        self.sayi += 1
        raise AssertionError("baglanti acilmamali")


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
        "SELECT notice_text, surum, license_status::text, kurul_gerekli, embed_ok,"
        " alinma_tarihi::text, dosya_sha256 FROM icerik.source WHERE slug = %s",
        (ANA,),
    ).fetchone()
    assert kaynak is not None
    assert kaynak[0] == BILDIRIM
    assert kaynak[1:5] == ("1.0", "serbest", True, True)
    assert kaynak[5] == TARIH
    assert kaynak[6] == lineage.sha256_bayt(b"Deneme ham dosya test-ana\n")
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
@pytest.mark.parametrize(
    ("db_degisimi", "beklenen"),
    [
        ("license_status = 'ic_kullanim'", 3),  # veritabani daha kisitlayici
        ("embed_ok = false", 3),
        ("kurul_gerekli = true", 0),  # TOML'la ayni: fark yok
        ("license_status = 'kapali'", 3),  # kapali: lisans kapisi
    ],
)
def test_ikinci_onay_alani_veritabani_kisitlayici(
    tmp_path: Path, conn: psycopg.Connection, db_degisimi: str, beklenen: int
) -> None:
    s = senaryo_kur(tmp_path)
    zincir_kur(s)
    assert calistir(s, conn) == 0
    conn.execute(f"UPDATE icerik.source SET {db_degisimi} WHERE slug = %s", (ANA,))  # type: ignore[call-overload]
    once = conn.execute(
        "SELECT license_status::text, embed_ok, kurul_gerekli, baslik FROM icerik.source"
        " WHERE slug = %s",
        (ANA,),
    ).fetchone()
    toml_yeniden(s, ANA, baslik="Deneme yeni baslik")
    zincir_kur(s, [satir(1, ar_norm="degisti"), satir(2), satir(3)])
    assert calistir(s, conn) == beklenen
    sonra = conn.execute(
        "SELECT license_status::text, embed_ok, kurul_gerekli, baslik FROM icerik.source"
        " WHERE slug = %s",
        (ANA,),
    ).fetchone()
    assert sonra is not None
    assert once is not None
    assert sonra[:3] == once[:3]  # ikinci onayli alanlar hic yazilmaz
    if beklenen != 0:
        assert sonra[3] == once[3]  # durdu: betimleyici alan da yazilmadi
        assert (
            say(conn, "SELECT count(*) FROM icerik.unit WHERE ar_norm = 'degisti'") == 0
        )  # satirlar degismedi
    else:
        assert sonra[3] == "Deneme yeni baslik"


@pytest.mark.veritabani
def test_toml_veritabanindan_kisitlayici_degilse_cikis_2(
    tmp_path: Path, conn: psycopg.Connection
) -> None:
    s = senaryo_kur(tmp_path)
    zincir_kur(s)
    assert calistir(s, conn) == 0
    # TOML 'bekliyor' (daha kisitlayici), veritabani 'serbest': hat ikinci onayi atlayamaz.
    toml_yeniden(s, ANA, license_status="bekliyor")
    zincir_kur(s)
    assert calistir(s, conn) == 2
    assert conn.execute(
        "SELECT license_status::text FROM icerik.source WHERE slug = %s", (ANA,)
    ).fetchone() == ("serbest",)


@pytest.mark.veritabani
def test_source_varsa_yalniz_betimleyici_alan_guncellenir(
    tmp_path: Path, conn: psycopg.Connection
) -> None:
    s = senaryo_kur(tmp_path)
    zincir_kur(s)
    assert calistir(s, conn) == 0
    conn.execute("UPDATE icerik.source SET notlar = 'Deneme editor notu' WHERE slug = %s", (ANA,))
    toml_yeniden(s, ANA, baslik="Deneme yeni baslik", notlar="Deneme baska not", surum="1.2")
    zincir_kur(s)
    assert calistir(s, conn) == 0
    rapor = sayilar(s)
    assert (rapor["kaynak_guncellenen"], rapor["kaynak_degismeyen"]) == (1, 1)
    kaynak = conn.execute(
        "SELECT baslik, surum, notlar FROM icerik.source WHERE slug = %s", (ANA,)
    ).fetchone()
    assert kaynak == ("Deneme yeni baslik", "1.2", "Deneme editor notu")  # notlar betimleyici degil


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


# --- dosya onkosullari (veritabani gerekmez) ---------------------------------------------


def test_qa_raporu_yoksa_cikis_1(tmp_path: Path) -> None:
    s = senaryo_kur(tmp_path)
    zincir_kur(s, qa_yaz=False)
    bag = Cagrilmaz()
    assert (
        pg.komut_export_pg(s.ayarlar, depo_kok=s.kok, source=ANA, kayit={ANA: (EK,)}, baglanti=bag)
        == 1
    )
    assert bag.sayi == 0


def test_qa_kapisi_kaldiysa_cikis_1(tmp_path: Path) -> None:
    s = senaryo_kur(tmp_path)
    zincir_kur(s, kapilar={**TUM_GECTI, "G-CAP": "kaldi"})
    assert calistir(s) == 1


def test_qa_raporu_dort_kapiyi_icermiyorsa_cikis_1(tmp_path: Path) -> None:
    s = senaryo_kur(tmp_path)
    zincir_kur(s, kapilar={"G-CAP": "gecti"})
    assert calistir(s) == 1


def test_qa_raporu_ozeti_uyusmuyorsa_cikis_1(tmp_path: Path) -> None:
    s = senaryo_kur(tmp_path)
    zincir_kur(s, qa_sha="0" * 64)
    assert calistir(s) == 1


def test_zincirdeki_ingest_en_son_degilse_cikis_1(tmp_path: Path) -> None:
    s = senaryo_kur(tmp_path)
    zincir_kur(s)
    # EK icin daha yeni bir ingest calistirmasi: zincirdeki artik en son degil.
    yeni = str(s.uretici.uret())
    _staged_calisma(s, EK, yeni, "ingest", {"units.jsonl": b'{"deneme":3}\n'}, [])
    assert calistir(s) == 1


def test_staged_content_hash_metinle_tutmuyorsa_cikis_1(tmp_path: Path) -> None:
    s = senaryo_kur(tmp_path)
    zincir_kur(s, [satir(1, content_hash="0" * 64), satir(2)])
    assert calistir(s) == 1


def test_notice_txt_toml_ile_farkliysa_cikis_2(tmp_path: Path) -> None:
    s = senaryo_kur(tmp_path)
    zincir_kur(s, notice=BILDIRIM + "\n")  # TOML'dakinden bir LF fazla: rstrip yok
    assert calistir(s) == 2


def test_bozuk_units_satiri_cikis_2(tmp_path: Path) -> None:
    s = senaryo_kur(tmp_path)
    zincir_kur(s, [satir(1, kind="yok"), satir(2)])
    assert calistir(s) == 2
    zincir_kur(s, [satir(1, ayah_hi=1)])  # bos aralik
    assert calistir(s) == 2
    zincir_kur(s, [satir(1, metin_durumu="taslak")])
    assert calistir(s) == 2
    zincir_kur(s, [satir(1), satir(1)])  # yinelenen capa
    assert calistir(s) == 2
    zincir_kur(s, [satir(1, source_id=EK)])
    assert calistir(s) == 2


def test_kapali_kaynak_cikis_3(tmp_path: Path) -> None:
    s = senaryo_kur(tmp_path)
    zincir_kur(s)
    toml_yeniden(s, EK, license_status="kapali", lisans_kopyasi=None, lisans_sha256=None)
    bag = Cagrilmaz()
    assert (
        pg.komut_export_pg(s.ayarlar, depo_kok=s.kok, source=ANA, kayit={ANA: (EK,)}, baglanti=bag)
        == 3
    )
    assert bag.sayi == 0


def test_tanimsiz_kaynak_cikis_2(tmp_path: Path) -> None:
    s = senaryo_kur(tmp_path)
    assert calistir(s, source="test-baska") == 2


def test_anchor_calismasi_yoksa_ve_run_gecersizse_cikis_2(tmp_path: Path) -> None:
    s = senaryo_kur(tmp_path)
    assert calistir(s) == 2
    zincir_kur(s)
    assert calistir(s, run="uuid-degil") == 2
    assert calistir(s, run=str(s.uretici.uret())) == 2


def test_rapor_baglanti_dizesi_ve_icerik_yazmaz(tmp_path: Path) -> None:
    s = senaryo_kur(tmp_path)
    zincir_kur(s, kapilar={**TUM_GECTI, "G-LIS": "kaldi"})
    assert calistir(s) == 1
    raporlar = b"".join(p.read_bytes() for p in (s.veri / "reports").glob("*.json"))
    raporlar += b"".join(p.read_bytes() for p in (s.veri / "logs").glob("*.jsonl"))
    assert b"Deneme metni" not in raporlar


def test_cli_export_pg_kayitsiz_kaynak_cikis_3(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    kok = kok_kur(tmp_path)
    monkeypatch.setenv("MUTALAA_VERI_KOK", str(tmp_path / "data"))
    sonuc = CliRunner().invoke(
        cli.app, ["export", "pg", "--source", "tanzil-uthmani", "--kok", str(kok)]
    )
    assert sonuc.exit_code == 3, sonuc.stderr
    assert "lisans kapisi" in sonuc.stderr
