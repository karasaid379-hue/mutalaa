"""`export pg --source risale-kelime-frekans`: lugat adaylari ve review (A20.6; SENTETIK veri).

Testler VERITABANISIZDIR: zincir (ingest lugat -> qa run) sentetik zipten gercek koduyla uretilir,
baglanti sahte bir nesnedir (`SahteBaglanti`: calisan SQL metinleri, parametreler, `COPY`
satirlari ve islem sinirlari kaydedilir). SQL'in editor satirina yazmamasi statik olarak
(WHERE kosulu ve guncellenen sutun listesi) sinanir. Baslik soz, anlam ve OCR metni yalniz
anlamsiz sentetik imzalardir; ciktilara sizmadigi sinanir.
"""

import copy
import json
import os
import re
from collections.abc import Callable, Iterator
from pathlib import Path

import psycopg
import pytest
from hat_yardimci import ansisiz, ayarlar_kur, ctx_kur
from lugat_yardimci import ANLAM_IMZASI, COMMIT, OCR_IMZASI, TARIH, LugatKoku, lugat_hazirla
from psycopg.types.json import Jsonb
from test_export_pg import Cagrilmaz
from test_pg_risale import SahteBaglanti, SahteSonuc, esle
from typer.testing import CliRunner

from mutalaa_pipeline import cli, qa
from mutalaa_pipeline.config import Ayarlar
from mutalaa_pipeline.db import baglan
from mutalaa_pipeline.export import pg, pg_lugat
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.ingest import kelime_frekans
from mutalaa_pipeline.ingest.kelime_frekans import KAYNAK
from mutalaa_pipeline.ingest.lugat_madde import MADDE_ALANLARI, madde_hash
from mutalaa_pipeline.runctx import QaKaldi
from mutalaa_pipeline.staged import Satir

KAPILAR = ("G-KAY", "G-BUT", "G-CAP", "G-NOR")
runner = CliRunner()
YENI = "count(*) FILTER (WHERE o.m_id IS NULL),"  # SAYAC sorgusu
FAZLA = "NOT EXISTS (SELECT 1 FROM pg_temp.staging_lugat"


@pytest.fixture
def kk(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> LugatKoku:
    kok = lugat_hazirla(tmp_path, monkeypatch)
    assert kok.ingest() == 0
    assert kok.qa() == 0
    return kok


def calistir(
    kk: LugatKoku,
    baglanti: Callable[[], psycopg.Connection] | SahteBaglanti | None = None,
    *,
    source: str = KAYNAK,
    **kw: object,
) -> int:
    if baglanti is None:
        fabrika: Callable[[], psycopg.Connection] = Cagrilmaz()
    elif isinstance(baglanti, SahteBaglanti):
        fabrika = lambda: baglanti  # type: ignore[assignment,return-value]  # noqa: E731
    else:
        fabrika = baglanti
    return pg.komut_export_pg(
        ayarlar_kur(kk.tmp), depo_kok=kk.kok, source=source, baglanti=fabrika, **kw
    )  # type: ignore[arg-type]


def raporlar(kk: LugatKoku, komut: str) -> list[dict[str, object]]:
    sonuc = []
    for yol in sorted((kk.veri_kok / "reports").glob("*.json"), key=lambda p: p.name):
        veri = json.loads(yol.read_text(encoding="utf-8"))
        if veri.get("komut") == komut:
            sonuc.append(veri)
    return sonuc


def sayilar(kk: LugatKoku) -> dict[str, int]:
    deger = raporlar(kk, "export pg")[-1]["sayilar"]
    assert isinstance(deger, dict)
    return deger


def db_kur(
    n: int,
    *,
    sayac: tuple[int, int, int, int, int] | None = None,
    upsert: int | None = None,
    review: int | None = None,
    fazla: int = 0,
) -> SahteBaglanti:
    """Ilk yukleme varsayilani: n madde yeni, hepsi icin review."""
    sayac = sayac if sayac is not None else (n, 0, 0, n, 0)
    return SahteBaglanti(
        esle(
            (
                "INSERT INTO icerik.lugat_madde",
                SahteSonuc(rowcount=upsert if upsert is not None else sayac[0] + sayac[2]),
            ),
            (
                "INSERT INTO icerik.review",
                SahteSonuc(rowcount=review if review is not None else sayac[3]),
            ),
            (YENI, SahteSonuc([sayac])),
            (FAZLA, SahteSonuc([(fazla,)])),
        )
    )


def sutun_adlari(sorgu: str) -> list[str]:
    parca = re.search(r"\((.*?)\)", sorgu)
    assert parca is not None
    return [a.strip() for a in parca.group(1).split(",")]


# --- ilk yukleme: SQL, COPY ve sayaclar -----------------------------------------------------


def test_ilk_yukleme_tek_islemde_sayaclar_ve_kaynak_satiri(kk: LugatKoku) -> None:
    n = len(kk.satirlar())
    db = db_kur(n)
    assert calistir(kk, db) == 0
    assert [i.durum for i in db.islemler] == ["onaylandi"]
    # tek islem: danisma kilidi, pipeline_run, kaynak satiri, staging, upsert, review
    sorgular = [m for i in db.islemler for m, _ in i.sorgular]
    sira = [
        next(i for i, m in enumerate(sorgular) if parca in m)
        for parca in (
            "pg_advisory_xact_lock",
            "INSERT INTO icerik.pipeline_run",
            "INSERT INTO icerik.source",
            "CREATE TEMP TABLE staging_lugat",
            "CREATE TEMP TABLE lugat_durum",
            "INSERT INTO icerik.lugat_madde",
            "INSERT INTO icerik.review",
        )
    ]
    assert sira == sorted(sira) and len(set(sira)) == 7
    assert sayilar(kk) == {
        "lugat_staging": n,
        "lugat_eklenen": n,
        "lugat_ayni_kalan": 0,
        "lugat_guncellenen": 0,
        "lugat_atlanan_editor": 0,
        "lugat_review_acilan": n,
        "lugat_review_acik_nedeniyle_atlanan": 0,
        "lugat_veritabaninda_fazla": 0,
        "kaynak_eklenen": 1,
        "kaynak_guncellenen": 0,
        "kaynak_degismeyen": 0,
    }


def test_kaynak_satiri_zip_dosyasindan_alinma_tarihi_ve_ozetle_ilk_yazimda(kk: LugatKoku) -> None:
    db = db_kur(len(kk.satirlar()))
    assert calistir(kk, db) == 0
    ((_, params),) = db.sorgular("INSERT INTO icerik.source")
    assert isinstance(params, dict)
    assert params["slug"] == KAYNAK and params["tur"] == "sozluk"
    assert params["surum"] == COMMIT  # kaynak kaydinda surum zorunlu: commit
    assert str(params["alinma_tarihi"]) == TARIH
    assert re.fullmatch(r"[0-9a-f]{64}", str(params["dosya_sha256"]))
    ((_, kilit),) = db.sorgular("pg_advisory_xact_lock")
    assert kilit == (KAYNAK,)


def test_copy_satirlari_sutun_sirasiyla_tanimsiz_ve_anlam_basvurusu_yalniz_onerilende(
    kk: LugatKoku,
) -> None:
    staged = kk.satirlar()
    db = db_kur(len(staged))
    assert calistir(kk, db) == 0
    (sorgu, _) = db.kopyalar[0]
    assert sutun_adlari(sorgu) == [
        "sira", "basliksoz", "basliksoz_norm", "tanim_tr", "kaynaklar", "duzey",
        "data_version", "content_hash", "onerilen",
    ]  # fmt: skip
    satirlar = db.kopya_satirlari()
    assert [r[0] for r in satirlar] == list(range(1, len(staged) + 1))  # dosya sirasi
    for kopya, ham in zip(satirlar, staged, strict=True):
        assert kopya[1] == ham["basliksoz"] and kopya[2] == ham["basliksoz_norm"]
        assert kopya[3] is None  # tanim_tr: editor yazar
        assert isinstance(kopya[4], Jsonb) and isinstance(kopya[8], Jsonb)
        kaynaklar, onerilen = kopya[4].obj, kopya[8].obj
        assert "anlam_basvuru" not in kaynaklar  # madde sutununa girmez
        assert set(onerilen) == {"anlam_basvuru", "siklik", "kitaplar"}
        assert onerilen == ham["onerilen_basvuru"] and kaynaklar == ham["kaynaklar"]
        assert kopya[7] == madde_hash(str(ham["basliksoz"]), None)  # staged content_hash
        assert kopya[5] == ham["duzey"] and kopya[6] == ham["data_version"]
    assert any(  # basvuru dolu: ANLAM imzasi yalniz review.onerilen'de
        ANLAM_IMZASI in json.dumps(k[8].obj, ensure_ascii=False)  # type: ignore[union-attr]
        for k in satirlar
    )
    assert not any(
        ANLAM_IMZASI in json.dumps(k[4].obj, ensure_ascii=False)  # type: ignore[union-attr]
        for k in satirlar
    )


# --- statik SQL denetimi: editor satirina yazmama -------------------------------------------


def upsert_sql() -> str:
    return pg_lugat.UPSERT


def test_upsert_sql_cakisma_kisiti_ve_yalniz_hat_aday_satiri_gunceller() -> None:
    sql = upsert_sql()
    assert (
        "ON CONFLICT ON CONSTRAINT lugat_madde_source_id_basliksoz_anlam_no_key DO UPDATE SET"
        in sql
    )
    assert pg_lugat.CONSTRAINT == "lugat_madde_source_id_basliksoz_anlam_no_key"
    # guncelleme yalniz origin = 'hat' AND status = 'aday' satirda ve yalniz degeri farkliysa
    kosul = sql.split(" WHERE ", 1)[1].split(" WHERE ")[-1]
    assert "icerik.lugat_madde.origin = 'hat'" in kosul
    assert "icerik.lugat_madde.status = 'aday'" in kosul
    assert "IS DISTINCT FROM" in kosul


def test_upsert_sql_guncellenen_sutun_listesi_yalniz_turetilmis_alanlar() -> None:
    sql = upsert_sql()
    atama = sql.split("DO UPDATE SET", 1)[1].split(" WHERE ", 1)[0]
    sutunlar = [parca.split("=")[0].strip() for parca in atama.split(",")]
    assert sorted(sutunlar) == sorted(
        ["kaynaklar", "duzey", "data_version", "basliksoz_norm", "updated_at"]
    )
    for yasak in (
        "tanim_tr", "status", "version", "content_hash", "origin", "osmanlica_yazim",
        "koken_dil", "ar_kok_id", "source_id", "basliksoz",
    ):  # fmt: skip
        assert yasak not in sutunlar  # tam sutun adi (data_version ve basliksoz_norm ayri)
    assert "updated_at = now()" in atama


def test_upsert_sql_ekleme_degerleri_aday_hat_surum_1_metin() -> None:
    sql = pg_lugat.UPSERT.split(" ON CONFLICT ", 1)[0]
    assert "'aday'" in sql and "'hat'" in sql
    assert "%s::text, s.content_hash" in sql  # version '1' (metin) parametreyle
    assert pg_lugat.VERSION == "1"
    assert "tanim_tr" in sql  # sutun listesinde; degeri staged (gercek kaynakta NULL)


def test_upsert_parametreleri_kaynak_ve_surum_metin(kk: LugatKoku) -> None:
    db = db_kur(len(kk.satirlar()))
    assert calistir(kk, db) == 0
    ((_, params),) = db.sorgular("INSERT INTO icerik.lugat_madde")
    assert params == (KAYNAK, "1")


def test_review_sql_yalniz_yeni_madde_ve_acik_review_yoksa() -> None:
    sql = pg_lugat.INSERT_REVIEW
    assert "WHERE o.m_id IS NULL AND NOT o.acik_review" in sql  # var olan maddeye review yok
    assert "'lugat_madde'" in sql and "'tanim_tr'" in sql and "'oner'" in sql
    assert "%s::text || ':' || o.basliksoz" in sql  # hedef_anahtar '{source_id}:{basliksoz}'
    assert "NULL, o.onerilen, 'hat', 'hat'" in sql  # onceki NULL, koken ve oneren hat
    assert sutun_adlari(sql) == [
        "hedef_tablo", "hedef_anahtar", "alan", "eylem", "onceki", "onerilen", "koken", "oneren"
    ]  # fmt: skip  # yz_modeli, yz_kaydi, guven, duzenlenen ve durum yazilmaz (durum varsayilan)
    assert "DO UPDATE" not in sql and "UPDATE " not in sql  # var olan review yenilenmez
    # acik review: yalniz durum = 'acik' olan hedefler sayilir
    assert "r.hedef_tablo = 'lugat_madde' AND r.durum = 'acik'" in pg_lugat.DURUM


def test_review_parametresi_kaynak_kimligi(kk: LugatKoku) -> None:
    db = db_kur(len(kk.satirlar()))
    assert calistir(kk, db) == 0
    ((_, params),) = db.sorgular("INSERT INTO icerik.review")
    assert params == (KAYNAK,)
    ((_, durum),) = db.sorgular("CREATE TEMP TABLE lugat_durum")
    assert durum == (KAYNAK, KAYNAK)


# --- tekrar kosu, editor satiri ve review davranisi -----------------------------------------


def test_ikinci_kosu_sifir_degisiklik_review_acilmaz(kk: LugatKoku) -> None:
    n = len(kk.satirlar())
    db = db_kur(n, sayac=(0, 0, 0, 0, 0))
    assert calistir(kk, db) == 0
    s = sayilar(kk)
    assert (s["lugat_eklenen"], s["lugat_guncellenen"], s["lugat_review_acilan"]) == (0, 0, 0)
    assert s["lugat_ayni_kalan"] == n and s["kaynak_degismeyen"] == 0  # kaynak satiri ayri sayac


def test_guncelleme_yalniz_turetilmis_sayac_ve_review_acilmaz(kk: LugatKoku) -> None:
    n = len(kk.satirlar())
    db = db_kur(n, sayac=(0, 0, 3, 0, 0))
    assert calistir(kk, db) == 0
    s = sayilar(kk)
    assert (s["lugat_eklenen"], s["lugat_guncellenen"], s["lugat_review_acilan"]) == (0, 3, 0)
    assert s["lugat_ayni_kalan"] == n - 3


def test_editor_ya_da_aday_olmayan_satir_atlanir_uyari_yazilir(kk: LugatKoku) -> None:
    n = len(kk.satirlar())
    db = db_kur(n, sayac=(0, 4, 0, 0, 0))
    assert calistir(kk, db) == 0
    s = sayilar(kk)
    assert s["lugat_atlanan_editor"] == 4 and s["lugat_ayni_kalan"] == n - 4
    assert s["lugat_eklenen"] == 0 and s["lugat_review_acilan"] == 0
    assert any("origin=editor" in u for u in raporlar(kk, "export pg")[-1]["uyarilar"])  # type: ignore[attr-defined]


def test_acik_review_varsa_yeni_review_acilmaz(kk: LugatKoku) -> None:
    n = len(kk.satirlar())
    db = db_kur(n, sayac=(2, 0, 0, 1, 1))  # iki yeni madde, birinin acik review'u var
    assert calistir(kk, db) == 0
    s = sayilar(kk)
    assert s["lugat_review_acilan"] == 1 and s["lugat_review_acik_nedeniyle_atlanan"] == 1
    assert s["lugat_eklenen"] == 2


def test_veritabaninda_olup_stagedde_olmayan_madde_silinmez_uyari(kk: LugatKoku) -> None:
    n = len(kk.satirlar())
    db = db_kur(n, fazla=2)
    assert calistir(kk, db) == 0
    assert sayilar(kk)["lugat_veritabaninda_fazla"] == 2
    assert not [m for i in db.islemler for m, _ in i.sorgular if "DELETE" in m.upper()]


def test_upsert_satir_sayisi_beklenenden_farkliysa_cikis_1_ve_geri_alinir(kk: LugatKoku) -> None:
    n = len(kk.satirlar())
    db = db_kur(n, upsert=n - 1)
    assert calistir(kk, db) == 1
    assert db.islemler[0].durum == "geri_alindi"


def test_review_satir_sayisi_beklenenden_farkliysa_cikis_1_ve_geri_alinir(kk: LugatKoku) -> None:
    n = len(kk.satirlar())
    db = db_kur(n, review=n - 1)
    assert calistir(kk, db) == 1
    assert db.islemler[0].durum == "geri_alindi"


def test_sql_hatasi_butun_islemi_geri_alir_basarisiz_satiri_yazilir(kk: LugatKoku) -> None:
    db = SahteBaglanti(hata=("INSERT INTO icerik.review", psycopg.errors.DeadlockDetected("x")))
    assert calistir(kk, db) == 2
    assert [i.durum for i in db.islemler] == ["geri_alindi", "onaylandi"]
    assert any("INSERT INTO icerik.lugat_madde" in m for m, _ in db.islemler[0].sorgular)
    assert [m for m, _ in db.islemler[1].sorgular if "INSERT INTO icerik.pipeline_run" in m]
    assert not [m for m, _ in db.islemler[1].sorgular if "lugat_madde" in m]


# --- dry-run ---------------------------------------------------------------------------------


def test_dry_run_baglanir_yazim_akisini_calistirir_ve_geri_alir(kk: LugatKoku) -> None:
    """`--dry-run` veritabanina BAGLANIR (pg_risale ile ayni); islemi geri alir."""
    n = len(kk.satirlar())
    db = db_kur(n)
    baglanti = {"sayi": 0}

    def fabrika() -> psycopg.Connection:
        baglanti["sayi"] += 1
        return db  # type: ignore[return-value]

    assert calistir(kk, fabrika, dry_run=True) == 0
    assert baglanti["sayi"] == 1
    assert [i.durum for i in db.islemler] == ["geri_alindi"]
    assert db.sorgular("INSERT INTO icerik.lugat_madde") and db.kopyalar
    assert sayilar(kk)["lugat_eklenen"] == n  # sayac gercek, ama hicbir sey kalici degil


# --- dosya onkosullari: baglanti acilmaz ----------------------------------------------------


def hata_ile(kk: LugatKoku, kod: int, parca: str, capsys: pytest.CaptureFixture[str]) -> str:
    capsys.readouterr()
    sonuc = calistir(kk)  # Cagrilmaz: baglanti acilirsa test kirilir
    hata = capsys.readouterr().err
    assert sonuc == kod, hata
    assert parca in hata, hata
    assert hata.isascii()
    return hata


def rapor_degistir(kk: LugatKoku, degisim: Callable[[dict[str, object]], None]) -> None:
    for yol in (kk.veri_kok / "reports").glob("*.json"):
        veri = json.loads(yol.read_text(encoding="utf-8"))
        if veri.get("komut") == "qa run":
            degisim(veri)
            yol.write_text(json.dumps(veri), encoding="utf-8", newline="\n")


@pytest.mark.parametrize("kapi", KAPILAR)
def test_kapi_kaldiysa_yukleme_yok_cikis_1(
    kk: LugatKoku, capsys: pytest.CaptureFixture[str], kapi: str
) -> None:
    rapor_degistir(kk, lambda r: r["kapilar"].__setitem__(kapi, "kaldi"))  # type: ignore[attr-defined]
    hata_ile(kk, 1, kapi, capsys)


@pytest.mark.parametrize("kapi", KAPILAR)
def test_kapi_eksikse_rapor_dort_kapiyi_icermiyor_cikis_1(
    kk: LugatKoku, capsys: pytest.CaptureFixture[str], kapi: str
) -> None:
    rapor_degistir(kk, lambda r: r["kapilar"].pop(kapi))  # type: ignore[attr-defined]
    hata_ile(kk, 1, "dort kapiyi da icermiyor", capsys)


def test_qa_raporu_yoksa_cikis_1(kk: LugatKoku, capsys: pytest.CaptureFixture[str]) -> None:
    for yol in (kk.veri_kok / "reports").glob("*.json"):
        if json.loads(yol.read_text(encoding="utf-8")).get("komut") == "qa run":
            yol.unlink()
    hata_ile(kk, 1, "QA raporu yok", capsys)


def test_qa_raporu_baska_ozetle_ise_yukleme_yok(
    kk: LugatKoku, capsys: pytest.CaptureFixture[str]
) -> None:
    rapor_degistir(kk, lambda r: r.__setitem__("units_sha256", "0" * 64))
    hata_ile(kk, 1, "QA raporu yok", capsys)


def test_ingest_yoksa_cikis_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    kk = lugat_hazirla(tmp_path, monkeypatch)  # ingest kosulmadi
    hata_ile(kk, 2, "ingest", capsys)


def test_lugat_dosyasi_degisirse_cikis_2(kk: LugatKoku, capsys: pytest.CaptureFixture[str]) -> None:
    yol = kk.staged_klasorleri()[-1] / "lugat.jsonl"
    yol.write_bytes(yol.read_bytes() + b"\n")
    hata_ile(kk, 2, "saglam degil", capsys)


def test_content_hash_uyusmazligi_cikis_1(
    kk: LugatKoku, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(pg_lugat, "madde_hash", lambda b, t: "0" * 64)
    hata_ile(kk, 1, "content_hash", capsys)


def test_kayit_yoksa_cikis_2(kk: LugatKoku, capsys: pytest.CaptureFixture[str]) -> None:
    (kk.kok / "pipeline" / "sources" / f"{KAYNAK}.toml").unlink()
    hata_ile(kk, 2, KAYNAK, capsys)


# --- kaynak reddi ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "kaynak", ["risale-asil-nusha", "risale-rnk-metin", "lugat-naci", "tanzil-uthmani"]
)
def test_lugat_yolu_baska_kaynagi_reddeder(kaynak: str) -> None:
    with pytest.raises(GirdiHatasi, match="yalniz risale-kelime-frekans"):
        pg_lugat.kaynak_denetle(kaynak)


def test_diyanet_export_pg_ile_reddedilir_cikis_2(
    kk: LugatKoku, capsys: pytest.CaptureFixture[str]
) -> None:
    capsys.readouterr()
    assert calistir(kk, source="risale-asil-nusha") == 2  # baglanti acilmaz
    assert "karsilastirma verisi" in capsys.readouterr().err


def test_fikstur_kaynagi_lugat_hazirlayicisindan_ayri_hazirlanamaz(kk: LugatKoku) -> None:
    ctx = ctx_kur(kk.tmp, kk.kok, adim="export", kaynaklar=["test-risale-ornek"])
    with pytest.raises(GirdiHatasi, match="birimlerle birlikte"):
        pg_lugat.hazirla(ctx, "test-risale-ornek", None, ())


def test_kayit_tablosu_lugat_kaynagi_var_oteki_lugat_sozlukleri_yok() -> None:
    assert pg.EK_KAYNAKLAR[KAYNAK] == ()
    for sozluk in ("lugat-naci", "lugat-redhouse-1890", "lugat-kamus-i-turki"):
        assert sozluk not in pg.EK_KAYNAKLAR  # OCR sozlukleri girdidir: yuklenmez
    assert {KAYNAK, "test-risale-ornek"} == pg_lugat.KAYNAKLAR


# --- pg.hazirla (yalniz dosya tarafi) --------------------------------------------------------


def test_pg_hazirla_dosya_tarafi_lugat_satirlarini_ve_zip_ozetini_dondurur(kk: LugatKoku) -> None:
    ctx = ctx_kur(kk.tmp, kk.kok, adim="export", kaynaklar=[KAYNAK])
    h = pg.hazirla(ctx, KAYNAK, None, ())  # DB acilmaz
    staged = kk.satirlar()
    assert h.source_id == KAYNAK and h.kaynak_idleri == (KAYNAK,)
    assert [m.basliksoz for m in h.lugat] == [str(s["basliksoz"]) for s in staged]
    assert h.satirlar == [] and h.risale is None and h.risale_sayfa == []
    assert h.units_yol.endswith("/lugat.jsonl") and len(h.units_sha256) == 64
    assert len(h.zincir) == 1 and h.zincir[0].adim == "ingest"
    assert h.anchor_run_id == h.zincir[0].run_id  # lugatin anchor adimi yoktur
    # source satiri yalniz zip'ten dolar (alinma tarihi ve dosya ozeti); parmak izi dortunu kapsar
    assert [d["yol"].split("/")[1] for d in h.ham[KAYNAK]] == [KAYNAK]
    assert len(h.parmak) == 64
    assert all(m.tanim_tr is None and m.source_id == KAYNAK for m in h.lugat)


def test_pg_hazirla_qa_kalmissa_reddeder(kk: LugatKoku) -> None:
    rapor_degistir(kk, lambda r: r["kapilar"].__setitem__("G-BUT", "kaldi"))  # type: ignore[attr-defined]
    ctx = ctx_kur(kk.tmp, kk.kok, adim="export", kaynaklar=[KAYNAK])
    with pytest.raises(QaKaldi, match="G-BUT"):
        pg.hazirla(ctx, KAYNAK, None, ())


# --- satir dogrulamasi -----------------------------------------------------------------------


def ilk_satir(kk: LugatKoku) -> Satir:
    veri = kk.satirlar()[0]
    return Satir("ingest lugat.jsonl", 1, copy.deepcopy(veri))


def degistir(kk: LugatKoku, **alanlar: object) -> Satir:
    s = ilk_satir(kk)
    return Satir(s.etiket, s.no, {**s.veri, **alanlar})


def test_satir_coz_gecerli_satiri_kabul_eder(kk: LugatKoku) -> None:
    m = pg_lugat.satir_coz(ilk_satir(kk), KAYNAK)
    assert set(MADDE_ALANLARI) == set(ilk_satir(kk).veri)
    assert m.tanim_tr is None and m.source_id == KAYNAK


@pytest.mark.parametrize(
    ("alan", "deger"),
    [
        ("status", "onayli"),
        ("origin", "editor"),
        ("version", 2),
        ("tanim_tr", "Deneme tanimi"),
        ("osmanlica_yazim", "x"),
        ("koken_dil", "x"),
        ("ar_kok_id", 1),
        ("source_id", "baska-kaynak"),
        ("duzey", 2),
        ("basliksoz_norm", "baska"),
        ("basliksoz", ""),
        ("content_hash", "kisa"),
    ],
)
def test_satir_coz_gecersiz_alan_girdi_hatasi(kk: LugatKoku, alan: str, deger: object) -> None:
    with pytest.raises(GirdiHatasi) as hata:
        pg_lugat.satir_coz(degistir(kk, **{alan: deger}), KAYNAK)
    assert str(hata.value).isascii() and "satir 1" in str(hata.value)


def test_satir_coz_alan_kumesi_eksik_ya_da_fazla_girdi_hatasi(kk: LugatKoku) -> None:
    s = ilk_satir(kk)
    eksik = {a: d for a, d in s.veri.items() if a != "kaynaklar"}
    with pytest.raises(GirdiHatasi, match="alan kumesi"):
        pg_lugat.satir_coz(Satir(s.etiket, 1, eksik), KAYNAK)
    with pytest.raises(GirdiHatasi, match="alan kumesi"):
        pg_lugat.satir_coz(Satir(s.etiket, 1, {**s.veri, "ek": 1}), KAYNAK)


def test_satir_coz_content_hash_maddeyle_tutmuyorsa_qakaldi(kk: LugatKoku) -> None:
    with pytest.raises(QaKaldi, match="content_hash"):
        pg_lugat.satir_coz(degistir(kk, content_hash="a" * 64), KAYNAK)


def test_satir_coz_kaynaklarda_anlam_basvurusu_reddedilir(kk: LugatKoku) -> None:
    s = ilk_satir(kk)
    kaynaklar = copy.deepcopy(s.veri["kaynaklar"])
    assert isinstance(kaynaklar, dict)
    for yol in ("ust", "ic"):
        kotu = copy.deepcopy(kaynaklar)
        sizinti = [{"anlam": f"{ANLAM_IMZASI}-1", "sayi": 1}]
        if yol == "ust":
            kotu["anlam_basvuru"] = sizinti
        else:
            kotu["sozluk_isabet"] = {"anlam": f"{ANLAM_IMZASI}-1"}
        with pytest.raises(GirdiHatasi, match="anlam basvurusu girmez"):
            pg_lugat.satir_coz(Satir(s.etiket, 1, {**s.veri, "kaynaklar": kotu}), KAYNAK)
    bilinmeyen = {**kaynaklar, "baska": 1}
    with pytest.raises(GirdiHatasi, match="anahtar kumesi"):
        pg_lugat.satir_coz(Satir(s.etiket, 1, {**s.veri, "kaynaklar": bilinmeyen}), KAYNAK)


def test_satir_coz_onerilen_basvuru_bicimi(kk: LugatKoku) -> None:
    s = ilk_satir(kk)
    for kotu in (
        {"anlam_basvuru": [], "siklik": 1},  # kitaplar yok
        {"anlam_basvuru": [{"anlam": "x"}], "siklik": 1, "kitaplar": 1},
        {"anlam_basvuru": [], "siklik": 9999999, "kitaplar": 1},  # kaynaklar.siklik ile ayni degil
    ):
        with pytest.raises(GirdiHatasi, match=r"onerilen_basvuru|anlam_basvuru"):
            pg_lugat.satir_coz(Satir(s.etiket, 1, {**s.veri, "onerilen_basvuru": kotu}), KAYNAK)


def test_satirlari_coz_yinelenen_basliksoz_girdi_hatasi(kk: LugatKoku) -> None:
    veri = (kk.staged_klasorleri()[-1] / "lugat.jsonl").read_bytes()
    ilk = veri.split(b"\n", 1)[0] + b"\n"
    with pytest.raises(GirdiHatasi, match="yinelenen basliksoz"):
        pg_lugat.satirlari_coz(veri + ilk, KAYNAK)


# --- rapor ve iletilerde metin yok -----------------------------------------------------------


def test_rapor_gunluk_ve_cikti_baslik_soz_anlam_ve_ocr_metni_tasimaz(
    kk: LugatKoku, capsys: pytest.CaptureFixture[str]
) -> None:
    staged = kk.satirlar()
    db = db_kur(len(staged))
    capsys.readouterr()
    assert calistir(kk, db) == 0
    cikti = capsys.readouterr()
    metin = cikti.out + cikti.err
    for yol, veri in kk.tum_cikti_baytlari().items():
        if yol.startswith("staged/"):
            continue  # staged dosyalar kaynak verisinin kendisidir
        metin += veri.decode("utf-8")
    for imza in (ANLAM_IMZASI, OCR_IMZASI):
        assert imza not in metin
    for satir in staged:
        assert str(satir["basliksoz"]) not in metin
    # SQL parametreleri de baslik soz tasimaz: yalniz kaynak kimligi ve surum
    sorgu_parametreleri = json.dumps(
        [
            str(p)
            for i in db.islemler
            for m, p in i.sorgular
            if "INSERT INTO icerik.pipeline_run" in m
        ]
    )
    assert ANLAM_IMZASI not in sorgu_parametreleri


# --- CLI -------------------------------------------------------------------------------------


def test_cli_ingest_lugat_yardimi_secenekleri_listeler(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FORCE_COLOR", "1")
    sonuc = runner.invoke(cli.app, ["ingest", "lugat", "--help"])
    assert sonuc.exit_code == 0, sonuc.stderr
    cikti = ansisiz(sonuc.stdout)
    for secenek in (
        "--source", "--gelen-tarih", "--dry-run", "--force", "--config", "--kok", "--kilit-oner",
    ):  # fmt: skip
        assert secenek in cikti, secenek
    assert "risale-kelime-frekans" in cikti
    assert "--limit" not in cikti  # kismi alim yok


def test_cli_ingest_komut_listesinde_lugat_var(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FORCE_COLOR", "1")
    sonuc = runner.invoke(cli.app, ["ingest", "--help"])
    assert sonuc.exit_code == 0
    assert "lugat" in ansisiz(sonuc.stdout)


def test_cli_ingest_lugat_bilinmeyen_kaynak_cikis_2(kk: LugatKoku) -> None:
    for kaynak in ("risale-rnk-metin", "lugat-naci", "test-risale-ornek"):
        sonuc = runner.invoke(
            cli.app, ["ingest", "lugat", "--source", kaynak, "--kok", str(kk.kok)]
        )
        assert sonuc.exit_code == 2, kaynak
        assert "bilinmeyen lugat kaynagi" in sonuc.stderr


def test_cli_ingest_lugat_kilit_oner_dry_run_ile_cikis_2(kk: LugatKoku) -> None:
    sonuc = runner.invoke(
        cli.app,
        ["ingest", "lugat", "--source", KAYNAK, "--kilit-oner", "--dry-run", "--kok", str(kk.kok)],
    )
    assert sonuc.exit_code == 2
    assert "--kilit-oner ile" in sonuc.stderr


def test_cli_ingest_lugat_kilit_oner_kilit_metnini_yazar_dosya_yazmaz(kk: LugatKoku) -> None:
    once = kk.tum_cikti_baytlari()
    sonuc = runner.invoke(
        cli.app, ["ingest", "lugat", "--source", KAYNAK, "--kilit-oner", "--kok", str(kk.kok)]
    )
    assert sonuc.exit_code == 0, sonuc.stderr
    kilit = json.loads(sonuc.stdout)
    assert kilit["commit"] == COMMIT
    assert kk.tum_cikti_baytlari() == once


def test_cli_ingest_lugat_dry_run_ve_force(kk: LugatKoku) -> None:
    once = len(kk.staged_klasorleri())
    sonuc = runner.invoke(
        cli.app,
        ["ingest", "lugat", "--source", KAYNAK, "--dry-run", "--force", "--kok", str(kk.kok)],
    )
    assert sonuc.exit_code == 0, sonuc.stderr
    assert "dry-run" in sonuc.stdout and len(kk.staged_klasorleri()) == once
    sonuc = runner.invoke(
        cli.app, ["ingest", "lugat", "--source", KAYNAK, "--force", "--kok", str(kk.kok)]
    )
    assert sonuc.exit_code == 0, sonuc.stderr
    assert len(kk.staged_klasorleri()) == once + 1


def test_cli_ingest_lugat_gelen_tarihi_olmayan_klasor_cikis_2(kk: LugatKoku) -> None:
    sonuc = runner.invoke(
        cli.app,
        [
            "ingest",
            "lugat",
            "--source",
            KAYNAK,
            "--gelen-tarih",
            "2020-01-01",
            "--kok",
            str(kk.kok),
        ],
    )
    assert sonuc.exit_code == 2


def test_cli_qa_run_lugat_dort_kapi_cikis_0(kk: LugatKoku) -> None:
    sonuc = runner.invoke(cli.app, ["qa", "run", "--source", KAYNAK, "--kok", str(kk.kok)])
    assert sonuc.exit_code == 0, sonuc.stderr
    for kapi in KAPILAR:
        assert f"{kapi} gecti" in sonuc.stdout
    assert raporlar(kk, "qa run")[-1]["kaynak"] == KAYNAK


def test_cli_qa_run_lugat_gate_kismi_kosu_export_pg_ye_yetmez(
    kk: LugatKoku, capsys: pytest.CaptureFixture[str]
) -> None:
    rapor_degistir(kk, lambda r: r["kapilar"].pop("G-NOR"))  # kismi rapor gibi
    hata_ile(kk, 1, "dort kapiyi da icermiyor", capsys)


def test_cli_export_pg_yardimi_calisir(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FORCE_COLOR", "1")
    sonuc = runner.invoke(cli.app, ["export", "pg", "--help"])
    assert sonuc.exit_code == 0
    cikti = ansisiz(sonuc.stdout)
    for secenek in ("--source", "--run", "--dry-run", "--force"):
        assert secenek in cikti


def test_qa_kaynak_kapilari_lugat_dort_kapi() -> None:
    assert qa.kaynak_kapilari(KAYNAK) == KAPILAR == qa.LUGAT_KAPILARI
    assert qa.LUGAT_KAYNAGI == KAYNAK == kelime_frekans.KAYNAK


# --- gercek veritabani (mutalaa_test; yoksa atlanir) -----------------------------------------


@pytest.fixture
def conn() -> Iterator[psycopg.Connection]:
    """Test veritabanina baglanir (dis islem, sonunda geri alinir); kalinti varsa atlar."""
    try:
        baglanti = baglan(Ayarlar(), test=True)
    except GirdiHatasi as hata:
        if os.environ.get("MUTALAA_DEGISMEZLIK_ZORUNLU") == "1":
            pytest.fail(f"test veritabani yok: {hata}")
        pytest.skip(f"test veritabani yok: {hata}")
        return
    try:
        kalinti = baglanti.execute(
            "SELECT (SELECT count(*) FROM icerik.lugat_madde)"
            " + (SELECT count(*) FROM icerik.review WHERE hedef_tablo = 'lugat_madde')"
            " + (SELECT count(*) FROM icerik.source WHERE slug = %s)",
            (KAYNAK,),
        ).fetchone()
        assert kalinti is not None
        if kalinti[0] != 0:
            baglanti.rollback()
            pytest.skip("mutalaa_test icinde lugat_madde, review ya da kaynak satiri kalmis")
        yield baglanti
    finally:
        baglanti.rollback()
        baglanti.close()


def say(conn: psycopg.Connection, sorgu: str, *param: object) -> int:
    satir = conn.execute(sorgu, param).fetchone()  # type: ignore[arg-type]
    assert satir is not None
    return int(satir[0])


@pytest.mark.veritabani
def test_db_ilk_yukleme_ikinci_kosu_sifir_degisiklik(
    kk: LugatKoku, conn: psycopg.Connection
) -> None:
    staged = kk.satirlar()
    assert calistir(kk, lambda: conn) == 0
    ilk = sayilar(kk)
    assert ilk["lugat_eklenen"] == ilk["lugat_review_acilan"] == len(staged)
    assert say(conn, "SELECT count(*) FROM icerik.lugat_madde WHERE source_id = %s", KAYNAK) == len(
        staged
    )
    assert say(
        conn,
        "SELECT count(*) FROM icerik.lugat_madde WHERE status = 'aday' AND origin = 'hat'"
        " AND version = '1' AND tanim_tr IS NULL AND NOT (kaynaklar ? 'anlam_basvuru')"
        " AND source_id = %s",
        KAYNAK,
    ) == len(staged)
    assert say(
        conn,
        "SELECT count(*) FROM icerik.review WHERE hedef_tablo = 'lugat_madde' AND alan = 'tanim_tr'"
        " AND eylem = 'oner' AND koken = 'hat' AND oneren = 'hat' AND onceki IS NULL"
        " AND yz_modeli IS NULL AND durum = 'acik' AND onerilen ? 'anlam_basvuru'"
        " AND hedef_anahtar LIKE %s",
        f"{KAYNAK}:%",
    ) == len(staged)
    once = [tuple(r) for r in conn.execute("SELECT * FROM icerik.lugat_madde ORDER BY id")]
    review_once = say(conn, "SELECT count(*) FROM icerik.review")
    assert calistir(kk, lambda: conn) == 0
    ikinci = sayilar(kk)
    assert (ikinci["lugat_eklenen"], ikinci["lugat_guncellenen"]) == (0, 0)
    assert ikinci["lugat_review_acilan"] == 0 and ikinci["lugat_ayni_kalan"] == len(staged)
    assert say(conn, "SELECT count(*) FROM icerik.review") == review_once
    assert [tuple(r) for r in conn.execute("SELECT * FROM icerik.lugat_madde ORDER BY id")] == once


@pytest.mark.veritabani
def test_db_editor_satirina_ve_review_a_dokunulmaz_turetilen_hat_adayda_yenilenir(
    kk: LugatKoku, conn: psycopg.Connection
) -> None:
    staged = kk.satirlar()
    assert calistir(kk, lambda: conn) == 0
    editor, bayat = str(staged[0]["basliksoz"]), str(staged[1]["basliksoz"])
    conn.execute(
        "UPDATE icerik.lugat_madde SET origin = 'editor', status = 'onayli', version = '2',"
        " tanim_tr = 'Deneme tanimi', content_hash = %s, kaynaklar = '{}', duzey = 3,"
        " data_version = 'eski' WHERE source_id = %s AND basliksoz = %s",
        (madde_hash(editor, "Deneme tanimi"), KAYNAK, editor),
    )
    conn.execute(
        'UPDATE icerik.lugat_madde SET kaynaklar = \'{"siklik": 1, "kitaplar": {}}\','
        " data_version = 'eski' WHERE source_id = %s AND basliksoz = %s",
        (KAYNAK, bayat),
    )
    conn.execute(
        "UPDATE icerik.review SET durum = 'onaylandi' WHERE hedef_tablo = 'lugat_madde'"
        " AND hedef_anahtar = %s",
        (f"{KAYNAK}:{editor}",),
    )
    review_once = say(conn, "SELECT count(*) FROM icerik.review")
    editor_once = conn.execute(
        "SELECT * FROM icerik.lugat_madde WHERE source_id = %s AND basliksoz = %s",
        (KAYNAK, editor),
    ).fetchone()
    assert calistir(kk, lambda: conn) == 0
    s = sayilar(kk)
    assert (s["lugat_eklenen"], s["lugat_atlanan_editor"], s["lugat_guncellenen"]) == (0, 1, 1)
    assert s["lugat_review_acilan"] == 0
    assert say(conn, "SELECT count(*) FROM icerik.review") == review_once  # yeni review yok
    assert (
        conn.execute(
            "SELECT * FROM icerik.lugat_madde WHERE source_id = %s AND basliksoz = %s",
            (KAYNAK, editor),
        ).fetchone()
        == editor_once
    )  # editor satiri: hicbir sutun (updated_at dahil) degismedi
    yeni = conn.execute(
        "SELECT kaynaklar, data_version, status::text, origin, tanim_tr, version"
        " FROM icerik.lugat_madde WHERE source_id = %s AND basliksoz = %s",
        (KAYNAK, bayat),
    ).fetchone()
    assert yeni is not None
    assert yeni[0] == staged[1]["kaynaklar"] and yeni[1] == staged[1]["data_version"]
    assert yeni[2:] == ("aday", "hat", None, "1")
