"""`export pg --source lugat-rnk|lugat-sozluk-rganeyev` (A20.6b; SENTETIK veri).

Testler VERITABANISIZDIR (`SahteBaglanti`): calisan SQL metinleri, parametreler, `COPY` satirlari
ve islem sinirlari kaydedilir; SQL'in editor satirina yazmamasi ve review'u yalniz `duzey` 1-3
maddeler icin acmasi statik olarak sinanir. `veritabani` isaretli testler yalniz test
veritabanina (`mutalaa_test`) baglanir ve veritabani yoksa atlanir; bu ajan onlari KOSMAZ.
Baslik soz, tanim ve anlam metni yalniz anlamsiz sentetik imzalardir; ciktilara sizmadigi sinanir.
"""

import json
import os
import re
from collections.abc import Callable, Iterator
from pathlib import Path

import psycopg
import pytest
from hat_yardimci import ayarlar_kur, ctx_kur
from lugat_kaynak_yardimci import (
    TANIM_RG,
    TANIM_RNK,
    TARIH_LUGAT,
    KaynakKoku,
    kaynak_hazirla,
    tam_zincir,
)
from psycopg.types.json import Jsonb
from test_export_pg import Cagrilmaz
from test_pg_risale import SahteBaglanti, SahteSonuc, esle

from mutalaa_pipeline import lineage
from mutalaa_pipeline.config import Ayarlar
from mutalaa_pipeline.db import baglan
from mutalaa_pipeline.export import pg, pg_lugat
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.ingest import lugat_kaynak
from mutalaa_pipeline.ingest.kelime_frekans import KAYNAK as KF
from mutalaa_pipeline.ingest.lugat_kaynak import BICIMLER, KAYNAK_RGANEYEV, KAYNAK_RNK
from mutalaa_pipeline.ingest.lugat_madde import MADDE_ALANLARI_KAYNAK, madde_hash
from mutalaa_pipeline.runctx import QaKaldi
from mutalaa_pipeline.staged import Satir

KAPILAR = ("G-KAY", "G-BUT", "G-CAP", "G-NOR")
SLUGLAR = (KAYNAK_RNK, KAYNAK_RGANEYEV)
YENI = "SELECT count(*) FILTER (WHERE o.m_id IS NULL),"  # SAYAC_K
FAZLA = "NOT EXISTS (SELECT 1 FROM pg_temp.staging_lugat_k"


@pytest.fixture
def kz(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> KaynakKoku:
    kok = kaynak_hazirla(tmp_path, monkeypatch)
    tam_zincir(kok)
    return kok


def calistir(
    kz: KaynakKoku,
    slug: str,
    baglanti: Callable[[], psycopg.Connection] | SahteBaglanti | None = None,
    **kw: object,
) -> int:
    if baglanti is None:
        fabrika: Callable[[], psycopg.Connection] = Cagrilmaz()
    elif isinstance(baglanti, SahteBaglanti):
        fabrika = lambda: baglanti  # type: ignore[assignment,return-value]  # noqa: E731
    else:
        fabrika = baglanti
    return pg.komut_export_pg(
        ayarlar_kur(kz.lk.tmp), depo_kok=kz.kok, source=slug, baglanti=fabrika, **kw
    )  # type: ignore[arg-type]


def raporlar(kz: KaynakKoku, komut: str) -> list[dict[str, object]]:
    sonuc = []
    for yol in sorted((kz.veri_kok / "reports").glob("*.json"), key=lambda p: p.name):
        veri = json.loads(yol.read_text(encoding="utf-8"))
        if veri.get("komut") == komut:
            sonuc.append(veri)
    return sonuc


def sayilar(kz: KaynakKoku) -> dict[str, int]:
    deger = raporlar(kz, "export pg")[-1]["sayilar"]
    assert isinstance(deger, dict)
    return deger


def db_kur(
    n: int,
    *,
    sayac: tuple[int, int, int, int, int, int, int] | None = None,
    upsert: int | None = None,
    review: int | None = None,
    fazla: int = 0,
    gerekmeyen: int = 0,
) -> SahteBaglanti:
    """Ilk yukleme varsayilani: n madde yeni, `review` sayisi verilen kadar."""
    review_n = review if review is not None else 0
    sayac = sayac if sayac is not None else (n, 0, 0, 0, review_n, 0, gerekmeyen)
    return SahteBaglanti(
        esle(
            (
                "INSERT INTO icerik.lugat_madde",
                SahteSonuc(rowcount=upsert if upsert is not None else sayac[0] + sayac[2]),
            ),
            ("INSERT INTO icerik.review", SahteSonuc(rowcount=review_n)),
            (YENI, SahteSonuc([sayac])),
            (FAZLA, SahteSonuc([(fazla,)])),
        )
    )


def sutun_adlari(sorgu: str) -> list[str]:
    parca = re.search(r"\((.*?)\)", sorgu)
    assert parca is not None
    return [a.strip() for a in parca.group(1).split(",")]


def yeni_review_sayisi(kz: KaynakKoku, slug: str) -> int:
    return sum(1 for s in kz.satirlar(slug) if 1 <= int(str(s["duzey"])) <= 3)


# --- statik SQL denetimi: editor satirina yazmama ----------------------------------------------


def test_kaynakli_upsert_kisit_adi_ve_yalniz_editor_olmayan_aday_satiri_gunceller() -> None:
    sql = pg_lugat.UPSERT_K
    assert "ON CONFLICT ON CONSTRAINT lugat_madde_source_id_basliksoz_anlam_no_key DO UPDATE" in sql
    assert pg_lugat.CONSTRAINT == "lugat_madde_source_id_basliksoz_anlam_no_key"
    kosul = sql.split(" WHERE ", 1)[1].split(" WHERE ")[-1]
    assert "icerik.lugat_madde.origin <> 'editor'" in kosul
    assert "icerik.lugat_madde.status = 'aday'" in kosul
    assert "IS DISTINCT FROM" in kosul


def test_kaynakli_upsert_guncellenen_sutunlar_yalniz_turetilmis_tanim_dokunulmaz() -> None:
    sql = pg_lugat.UPSERT_K
    atama = sql.split("DO UPDATE SET", 1)[1].split(" WHERE ", 1)[0]
    sutunlar = [parca.split("=")[0].strip() for parca in atama.split(",")]
    assert sorted(sutunlar) == sorted(
        ["kaynaklar", "duzey", "data_version", "basliksoz_norm", "updated_at"]
    )
    for yasak in (
        "tanim_tr", "content_hash", "status", "version", "origin", "anlam_no", "source_id",
        "basliksoz", "osmanlica_yazim", "koken_dil", "ar_kok_id",
    ):  # fmt: skip
        assert yasak not in sutunlar
    assert "updated_at = now()" in atama


def test_kaynakli_upsert_ekleme_degerleri() -> None:
    sql = pg_lugat.UPSERT_K.split(" ON CONFLICT ", 1)[0]
    assert "'aday', 'kaynak', %s::text, s.content_hash" in sql  # version '1' (metin)
    assert "anlam_no" in sql.split("SELECT", 1)[0] and "tanim_tr" in sql.split("SELECT", 1)[0]
    assert "s.tanim_tr" in sql and "s.anlam_no" in sql
    assert "'hat'" not in sql  # lugat kaynagi maddesi hat kokenli girmez


def test_kaynakli_review_sql_yalniz_duzey_1_3_ve_review_yoksa_ve_editor_degilse() -> None:
    sql = pg_lugat.INSERT_REVIEW_K
    assert "o.duzey BETWEEN 1 AND 3" in sql  # duzey 4 review'siz aday kalir
    assert "NOT o.var_review" in sql  # ayni hedefte acik ya da kapali review varsa acilmaz
    assert "o.m_origin <> 'editor' AND o.m_durum = 'aday'" in sql  # editor satirina review yok
    assert "%s::text || ':' || o.anlam_no::text || ':' || o.basliksoz" in sql  # {src}:{no}:{soz}
    assert "'lugat_madde'" in sql and "'tanim_tr'" in sql and "'oner'" in sql
    assert "NULL, o.onerilen, 'hat', 'hat'" in sql
    assert sutun_adlari(sql) == [
        "hedef_tablo", "hedef_anahtar", "alan", "eylem", "onceki", "onerilen", "koken", "oneren"
    ]  # fmt: skip
    assert "DO UPDATE" not in sql and "UPDATE " not in sql
    assert "starts_with(r.hedef_anahtar" in pg_lugat.DURUM_K  # kapali review de sayilir
    assert "r.durum" not in pg_lugat.DURUM_K  # acik/kapali ayrimi yok: HERHANGI bir review


def test_kaynakli_sayac_ve_durum_sql_metin_degisimi_icin_tanim_ve_ozeti_karsilastirir() -> None:
    assert "(m.tanim_tr, m.content_hash) IS DISTINCT FROM (s.tanim_tr, s.content_hash)" in (
        pg_lugat.DURUM_K
    )
    assert "AND m.anlam_no = s.anlam_no" in pg_lugat.DURUM_K  # anahtar (basliksoz, anlam_no)
    assert "DELETE" not in pg_lugat.SAYAC_K.upper()


def test_kelime_frekans_yolu_degismedi_yalniz_kisit_adi() -> None:
    sql = pg_lugat.UPSERT
    assert "ON CONFLICT ON CONSTRAINT lugat_madde_source_id_basliksoz_anlam_no_key" in sql
    kosul = sql.split(" WHERE ", 1)[1].split(" WHERE ")[-1]
    assert "icerik.lugat_madde.origin = 'hat'" in kosul  # Kelime-Frekans: yalniz hat satiri
    assert (
        "anlam_no" not in sql.split(" ON CONFLICT ", 1)[0]
    )  # ekleme anlam_no yazmaz (varsayilan 1)
    assert "'aday'" in sql and "'hat'" in sql
    # review hedef anahtari Kelime-Frekans'ta eski bicim: '{source_id}:{basliksoz}'
    assert "%s::text || ':' || o.basliksoz" in pg_lugat.INSERT_REVIEW
    assert "anlam_no" not in pg_lugat.INSERT_REVIEW
    assert "r.hedef_tablo = 'lugat_madde' AND r.durum = 'acik'" in pg_lugat.DURUM
    assert {KF, "test-risale-ornek"} == pg_lugat.KAYNAKLAR  # yeni kaynaklar ayri kume


def test_kaynak_denetle_yeni_kaynaklari_kabul_digerlerini_reddeder() -> None:
    for slug in SLUGLAR:
        pg_lugat.kaynak_denetle(slug)
    for slug in ("lugat-naci", "risale-rnk-metin", "tanzil-uthmani", "lugat-yegin-yeni-lugat"):
        with pytest.raises(GirdiHatasi, match="yalniz risale-kelime-frekans"):
            pg_lugat.kaynak_denetle(slug)
    for slug in SLUGLAR:
        assert pg.EK_KAYNAKLAR[slug] == ()  # `export pg --source` kaydi
    assert "lugat-yegin-yeni-lugat" not in pg.EK_KAYNAKLAR  # kunye kaydi yuklenmez


# --- ilk yukleme: tek islem, COPY, parametreler, sayaclar --------------------------------------


@pytest.mark.parametrize("slug", SLUGLAR)
def test_ilk_yukleme_tek_islemde_sirali_ve_sayaclar(kz: KaynakKoku, slug: str) -> None:
    satirlar = kz.satirlar(slug)
    n = len(satirlar)
    review = yeni_review_sayisi(kz, slug)
    db = db_kur(n, review=review, gerekmeyen=n - review)
    assert calistir(kz, slug, db) == 0
    assert [i.durum for i in db.islemler] == ["onaylandi"]
    sorgular = [m for i in db.islemler for m, _ in i.sorgular]
    sira = [
        next(i for i, m in enumerate(sorgular) if parca in m)
        for parca in (
            "pg_advisory_xact_lock",
            "INSERT INTO icerik.pipeline_run",
            "INSERT INTO icerik.source",
            "CREATE TEMP TABLE staging_lugat_k",
            "CREATE TEMP TABLE lugat_durum_k",
            "INSERT INTO icerik.lugat_madde",
            "INSERT INTO icerik.review",
        )
    ]
    assert sira == sorted(sira) and len(set(sira)) == 7
    s = sayilar(kz)
    assert s["lugat_staging"] == n and s["lugat_eklenen"] == n
    assert s["lugat_ayni_kalan"] == 0 and s["lugat_guncellenen"] == 0
    assert s["lugat_atlanan_editor"] == 0 and s["lugat_metin_degisti"] == 0
    assert s["lugat_review_acilan"] == review and s["lugat_review_gerektirmeyen"] == n - review
    assert s["lugat_veritabaninda_fazla"] == 0 and s["kaynak_eklenen"] == 1  # yalniz kendi kaynagi
    assert all(isinstance(d, int) for d in s.values())
    assert not [m for m in sorgular if "DELETE" in m.upper()]


@pytest.mark.parametrize("slug", SLUGLAR)
def test_copy_satirlari_tanim_bayt_bayt_anlam_no_ve_onerilen(kz: KaynakKoku, slug: str) -> None:
    satirlar = kz.satirlar(slug)
    db = db_kur(len(satirlar))
    assert calistir(kz, slug, db) == 0
    kopya = db.kopya_satirlari()
    assert len(kopya) == len(satirlar)
    for sira, (k, s) in enumerate(zip(kopya, satirlar, strict=True), start=1):
        assert k[0] == sira and k[1] == s["basliksoz"] and k[2] == s["anlam_no"]
        assert k[4] == s["tanim_tr"]  # bayt bayt (NFC ve kirpma disinda degisim yok)
        assert k[3] == s["basliksoz_norm"] and k[6] == s["duzey"]
        assert k[8] == madde_hash(str(s["basliksoz"]), str(s["tanim_tr"]))
        assert isinstance(k[5], Jsonb) and k[5].obj == s["kaynaklar"]
        onerilen = k[9]
        if 1 <= int(str(s["duzey"])) <= 3:
            assert isinstance(onerilen, Jsonb)
            siklik = s["kaynaklar"]["siklik"]  # type: ignore[index]
            assert onerilen.obj == {"kaynak": slug, "siklik": siklik}  # anlam basvurusu yok
        else:
            assert onerilen is None
        assert "anlam" not in json.dumps(k[5].obj) and "anlam_basvuru" not in json.dumps(k[5].obj)


@pytest.mark.parametrize("slug", SLUGLAR)
def test_parametreler_kaynak_surum_ve_hedef(kz: KaynakKoku, slug: str) -> None:
    db = db_kur(len(kz.satirlar(slug)))
    assert calistir(kz, slug, db) == 0
    ((_, params),) = db.sorgular("INSERT INTO icerik.lugat_madde")
    assert params == (slug, "1")
    ((_, durum),) = db.sorgular("CREATE TEMP TABLE lugat_durum_k")
    assert durum == (slug, slug, slug)
    ((_, rparams),) = db.sorgular("INSERT INTO icerik.review")
    assert rparams == (slug,)


@pytest.mark.parametrize("slug", SLUGLAR)
def test_source_satiri_ilk_yazim_kurali_alinma_tarihi_ve_dosya_ozeti(
    kz: KaynakKoku, slug: str
) -> None:
    db = db_kur(len(kz.satirlar(slug)))
    assert calistir(kz, slug, db) == 0
    ((_, params),) = db.sorgular("INSERT INTO icerik.source")
    assert isinstance(params, dict) and params["slug"] == slug
    assert str(params["alinma_tarihi"]) == TARIH_LUGAT
    assert params["dosya_sha256"] == lineage.sha256_bayt(kz.gelen(slug).read_bytes())
    assert params["tur"] == "sozluk"
    assert len(db.sorgular("INSERT INTO icerik.source")) == 1


def test_review_yalniz_risalede_gecen_maddeler_icin_acilir(kz: KaynakKoku) -> None:
    satirlar = kz.satirlar(KAYNAK_RNK)
    assert {s["duzey"] for s in satirlar} == {1, 2, 3, 4}
    assert yeni_review_sayisi(kz, KAYNAK_RNK) == 5
    db = db_kur(len(satirlar), review=5, gerekmeyen=3)
    assert calistir(kz, KAYNAK_RNK, db) == 0
    assert sayilar(kz)["lugat_review_acilan"] == 5


# --- tekrar kosu, editor satiri ve review davranisi ---------------------------------------------


def test_ikinci_kosu_sifir_degisiklik_review_acilmaz(kz: KaynakKoku) -> None:
    n = len(kz.satirlar(KAYNAK_RNK))
    db = db_kur(n, sayac=(0, 0, 0, 0, 0, 0, 3))
    assert calistir(kz, KAYNAK_RNK, db) == 0
    s = sayilar(kz)
    assert (s["lugat_eklenen"], s["lugat_guncellenen"], s["lugat_review_acilan"]) == (0, 0, 0)
    assert s["lugat_ayni_kalan"] == n and s["kaynak_degismeyen"] == 0


def test_guncelleme_yalniz_turetilmis_sayac_review_acilmaz(kz: KaynakKoku) -> None:
    n = len(kz.satirlar(KAYNAK_RNK))
    db = db_kur(n, sayac=(0, 0, 3, 0, 0, 0, 3))
    assert calistir(kz, KAYNAK_RNK, db) == 0
    s = sayilar(kz)
    assert (s["lugat_eklenen"], s["lugat_guncellenen"], s["lugat_review_acilan"]) == (0, 3, 0)
    assert s["lugat_ayni_kalan"] == n - 3


def test_editor_ya_da_aday_olmayan_satir_atlanir_uyari_yazilir(kz: KaynakKoku) -> None:
    n = len(kz.satirlar(KAYNAK_RNK))
    db = db_kur(n, sayac=(0, 4, 0, 0, 0, 0, 3))
    assert calistir(kz, KAYNAK_RNK, db) == 0
    s = sayilar(kz)
    assert s["lugat_atlanan_editor"] == 4 and s["lugat_ayni_kalan"] == n - 4
    assert s["lugat_eklenen"] == 0 and s["lugat_review_acilan"] == 0
    assert any("origin=editor" in u for u in raporlar(kz, "export pg")[-1]["uyarilar"])  # type: ignore[attr-defined]


def test_kaynak_tanimi_degisen_madde_degismez_metin_degisti_sayilir(kz: KaynakKoku) -> None:
    n = len(kz.satirlar(KAYNAK_RNK))
    db = db_kur(n, sayac=(0, 0, 0, 2, 0, 0, 3))
    assert calistir(kz, KAYNAK_RNK, db) == 0
    s = sayilar(kz)
    assert s["lugat_metin_degisti"] == 2 and s["lugat_guncellenen"] == 0
    assert s["lugat_ayni_kalan"] == n  # satir degismedi
    assert any("tanim degismedi" in u for u in raporlar(kz, "export pg")[-1]["uyarilar"])  # type: ignore[attr-defined]


def test_review_zaten_varsa_yeni_review_acilmaz(kz: KaynakKoku) -> None:
    n = len(kz.satirlar(KAYNAK_RNK))
    db = db_kur(n, sayac=(n, 0, 0, 0, 3, 2, 3), review=3)
    assert calistir(kz, KAYNAK_RNK, db) == 0
    s = sayilar(kz)
    assert s["lugat_review_acilan"] == 3 and s["lugat_review_var_nedeniyle_atlanan"] == 2


def test_veritabaninda_olup_stagedde_olmayan_madde_silinmez_uyari(kz: KaynakKoku) -> None:
    n = len(kz.satirlar(KAYNAK_RNK))
    db = db_kur(n, fazla=2)
    assert calistir(kz, KAYNAK_RNK, db) == 0
    assert sayilar(kz)["lugat_veritabaninda_fazla"] == 2
    assert not [m for i in db.islemler for m, _ in i.sorgular if "DELETE" in m.upper()]


def test_upsert_satir_sayisi_beklenenden_farkliysa_cikis_1_ve_geri_alinir(kz: KaynakKoku) -> None:
    n = len(kz.satirlar(KAYNAK_RNK))
    db = db_kur(n, upsert=n - 1)
    assert calistir(kz, KAYNAK_RNK, db) == 1
    assert db.islemler[0].durum == "geri_alindi"


def test_review_satir_sayisi_beklenenden_farkliysa_cikis_1_ve_geri_alinir(kz: KaynakKoku) -> None:
    n = len(kz.satirlar(KAYNAK_RNK))
    db = SahteBaglanti(
        esle(
            ("INSERT INTO icerik.lugat_madde", SahteSonuc(rowcount=n)),
            ("INSERT INTO icerik.review", SahteSonuc(rowcount=1)),
            (YENI, SahteSonuc([(n, 0, 0, 0, 5, 0, 3)])),
            (FAZLA, SahteSonuc([(0,)])),
        )
    )
    assert calistir(kz, KAYNAK_RNK, db) == 1
    assert db.islemler[0].durum == "geri_alindi"


def test_dry_run_baglanir_yazim_akisini_calistirir_ve_geri_alir(kz: KaynakKoku) -> None:
    n = len(kz.satirlar(KAYNAK_RNK))
    db = db_kur(n)
    sayi = {"n": 0}

    def fabrika() -> psycopg.Connection:
        sayi["n"] += 1
        return db  # type: ignore[return-value]

    assert calistir(kz, KAYNAK_RNK, fabrika, dry_run=True) == 0
    assert sayi["n"] == 1
    assert [i.durum for i in db.islemler] == ["geri_alindi"]
    assert db.sorgular("INSERT INTO icerik.lugat_madde") and db.kopyalar


# --- dosya onkosullari: baglanti acilmaz ----------------------------------------------------------


def hata_ile(
    kz: KaynakKoku, slug: str, kod: int, parca: str, capsys: pytest.CaptureFixture[str]
) -> str:
    capsys.readouterr()
    sonuc = calistir(kz, slug)  # Cagrilmaz: baglanti acilirsa test kirilir
    hata = capsys.readouterr().err
    assert sonuc == kod, hata
    assert parca in hata, hata
    assert hata.isascii()
    return hata


def rapor_degistir(kz: KaynakKoku, slug: str, degisim: Callable[[dict[str, object]], None]) -> None:
    for yol in (kz.veri_kok / "reports").glob("*.json"):
        veri = json.loads(yol.read_text(encoding="utf-8"))
        if veri.get("komut") == "qa run" and veri.get("kaynak") == slug:
            degisim(veri)
            yol.write_text(json.dumps(veri), encoding="utf-8", newline="\n")


@pytest.mark.parametrize("kapi", KAPILAR)
def test_kapi_kaldiysa_yukleme_yok_cikis_1(
    kz: KaynakKoku, capsys: pytest.CaptureFixture[str], kapi: str
) -> None:
    rapor_degistir(kz, KAYNAK_RNK, lambda r: r["kapilar"].__setitem__(kapi, "kaldi"))  # type: ignore[attr-defined]
    hata_ile(kz, KAYNAK_RNK, 1, kapi, capsys)


@pytest.mark.parametrize("kapi", KAPILAR)
def test_kapi_eksikse_cikis_1(
    kz: KaynakKoku, capsys: pytest.CaptureFixture[str], kapi: str
) -> None:
    rapor_degistir(kz, KAYNAK_RGANEYEV, lambda r: r["kapilar"].pop(kapi))  # type: ignore[attr-defined]
    hata_ile(kz, KAYNAK_RGANEYEV, 1, "dort kapiyi da icermiyor", capsys)


def test_qa_raporu_yoksa_cikis_1(kz: KaynakKoku, capsys: pytest.CaptureFixture[str]) -> None:
    for yol in (kz.veri_kok / "reports").glob("*.json"):
        v = json.loads(yol.read_text(encoding="utf-8"))
        if v.get("komut") == "qa run" and v.get("kaynak") == KAYNAK_RNK:
            yol.unlink()
    hata_ile(kz, KAYNAK_RNK, 1, "QA raporu yok", capsys)


def test_qa_raporu_baska_ozetle_ise_yukleme_yok(
    kz: KaynakKoku, capsys: pytest.CaptureFixture[str]
) -> None:
    rapor_degistir(kz, KAYNAK_RNK, lambda r: r.__setitem__("units_sha256", "0" * 64))
    hata_ile(kz, KAYNAK_RNK, 1, "QA raporu yok", capsys)


def test_ingest_yoksa_cikis_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    kok = kaynak_hazirla(tmp_path, monkeypatch)  # lugat ingest'i kosulmadi
    hata_ile(kok, KAYNAK_RNK, 2, "ingest", capsys)


def test_lugat_dosyasi_degisirse_cikis_2(
    kz: KaynakKoku, capsys: pytest.CaptureFixture[str]
) -> None:
    yol = kz.staged_klasorleri(KAYNAK_RNK)[-1] / "lugat.jsonl"
    yol.write_bytes(yol.read_bytes() + b"\n")
    hata_ile(kz, KAYNAK_RNK, 2, "saglam degil", capsys)


def test_ham_dosya_degisirse_cikis_2(kz: KaynakKoku, capsys: pytest.CaptureFixture[str]) -> None:
    ham = next((kz.veri_kok / "raw" / KAYNAK_RGANEYEV).rglob("words.txt"))
    ham.write_bytes(ham.read_bytes() + b"x")
    hata_ile(kz, KAYNAK_RGANEYEV, 2, "ozeti tutmuyor", capsys)


def test_content_hash_uyusmazligi_cikis_1(
    kz: KaynakKoku, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(pg_lugat, "madde_hash", lambda b, t: "0" * 64)
    hata_ile(kz, KAYNAK_RNK, 1, "content_hash", capsys)


def test_kayit_yoksa_cikis_2(kz: KaynakKoku, capsys: pytest.CaptureFixture[str]) -> None:
    (kz.kok / "pipeline" / "sources" / f"{KAYNAK_RGANEYEV}.toml").unlink()
    hata_ile(kz, KAYNAK_RGANEYEV, 2, KAYNAK_RGANEYEV, capsys)


def test_rapor_ve_gunluk_metin_tasimaz(kz: KaynakKoku) -> None:
    for slug in SLUGLAR:
        assert calistir(kz, slug, db_kur(len(kz.satirlar(slug)))) == 0
    for yol, veri in kz.tum_cikti_baytlari().items():
        if yol.endswith("lugat.jsonl"):
            continue
        metin = veri.decode("utf-8", "replace")
        assert TANIM_RNK not in metin and TANIM_RG not in metin, yol


# --- satir dogrulama ---------------------------------------------------------------------------


def ilk_satir(kz: KaynakKoku, slug: str = KAYNAK_RNK, duzey: int | None = None) -> Satir:
    veri = (kz.staged_klasorleri(slug)[-1] / "lugat.jsonl").read_bytes()
    from mutalaa_pipeline.staged import satirlari_oku

    for s in satirlari_oku(veri, "ingest lugat.jsonl"):
        if duzey is None or s.veri["duzey"] == duzey:
            return s
    raise AssertionError("satir yok")


def degistir(s: Satir, **alanlar: object) -> Satir:
    return Satir(s.etiket, s.no, {**s.veri, **alanlar})


def test_satir_coz_gecerli_madde(kz: KaynakKoku) -> None:
    m = pg_lugat.kaynakli_satir_coz(ilk_satir(kz, duzey=1), KAYNAK_RNK)
    assert m.source_id == KAYNAK_RNK and m.anlam_no >= 1 and m.duzey == 1
    assert m.onerilen == {"kaynak": KAYNAK_RNK, "siklik": m.kaynaklar["siklik"]}
    assert set(ilk_satir(kz).veri) == set(MADDE_ALANLARI_KAYNAK)
    gerekmeyen = pg_lugat.kaynakli_satir_coz(ilk_satir(kz, duzey=4), KAYNAK_RNK)
    assert gerekmeyen.onerilen is None and gerekmeyen.kaynaklar == {
        "kelime_frekans_karsiligi": False
    }


@pytest.mark.parametrize(
    ("alan", "deger"),
    [
        ("origin", "hat"),
        ("origin", "editor"),
        ("status", "onayli"),
        ("version", 2),
        ("source_id", "baska"),
        ("tanim_tr", ""),
        ("tanim_tr", "   "),
        ("tanim_tr", None),
        ("tanim_tr", "a\x00b"),
        ("anlam_no", 0),
        ("anlam_no", 32768),
        ("anlam_no", "1"),
        ("basliksoz_norm", "x"),
        ("osmanlica_yazim", "x"),
        ("duzey", 4),
        ("content_hash", "zz"),
    ],
)
def test_satir_coz_gecersiz_alan_girdi_hatasi(kz: KaynakKoku, alan: str, deger: object) -> None:
    s = ilk_satir(kz, duzey=1)
    with pytest.raises(GirdiHatasi) as hata:
        pg_lugat.kaynakli_satir_coz(degistir(s, **{alan: deger}), KAYNAK_RNK)
    assert hata.value.args[0].isascii() and TANIM_RNK not in hata.value.args[0]


@pytest.mark.parametrize(
    "kotu",
    [
        {"kelime_frekans_karsiligi": True},
        {"kelime_frekans_karsiligi": False, "siklik": 1},
        {"kelime_frekans_karsiligi": True, "anlam": "x"},
        {"kelime_frekans_karsiligi": True, "anlam_basvuru": []},
        {"siklik": 3, "kitaplar": {"k": 3}},
    ],
)
def test_satir_coz_kaynaklar_gecersiz_ya_da_anlam_iceriyor(
    kz: KaynakKoku, kotu: dict[str, object]
) -> None:
    s = ilk_satir(kz, duzey=1)
    with pytest.raises(GirdiHatasi):
        pg_lugat.kaynakli_satir_coz(degistir(s, kaynaklar=kotu), KAYNAK_RNK)


def test_satir_coz_eksik_ve_fazla_alan_ve_hash(kz: KaynakKoku) -> None:
    s = ilk_satir(kz)
    eksik = {a: v for a, v in s.veri.items() if a != "anlam_no"}
    with pytest.raises(GirdiHatasi):
        pg_lugat.kaynakli_satir_coz(Satir(s.etiket, 1, eksik), KAYNAK_RNK)
    with pytest.raises(GirdiHatasi):
        pg_lugat.kaynakli_satir_coz(Satir(s.etiket, 1, {**s.veri, "ek": 1}), KAYNAK_RNK)
    with pytest.raises(QaKaldi):  # hat hatasi: cikis 1
        pg_lugat.kaynakli_satir_coz(degistir(s, content_hash="a" * 64), KAYNAK_RNK)


def test_kaynakli_satirlari_coz_yinelenen_ve_dogru_sayida(kz: KaynakKoku) -> None:
    veri = (kz.staged_klasorleri(KAYNAK_RNK)[-1] / "lugat.jsonl").read_bytes()
    assert len(pg_lugat.kaynakli_satirlari_coz(veri, KAYNAK_RNK)) == 8
    ilk = veri.split(b"\n", 1)[0] + b"\n"
    with pytest.raises(GirdiHatasi, match="yinelenen"):
        pg_lugat.kaynakli_satirlari_coz(veri + ilk, KAYNAK_RNK)
    with pytest.raises(GirdiHatasi, match="source_id"):
        pg_lugat.kaynakli_satirlari_coz(veri, KAYNAK_RGANEYEV)


def test_kelime_frekans_satiri_yeni_yoldan_okunamaz(kz: KaynakKoku) -> None:
    """Kelime-Frekans staged satiri (anlam_no yok, origin hat) yeni dogrulayiciya girmez."""
    kf = next((kz.veri_kok / "staged" / KF).rglob("lugat.jsonl"))
    from mutalaa_pipeline.staged import satirlari_oku

    s = satirlari_oku(kf.read_bytes(), "kf")[0]
    with pytest.raises(GirdiHatasi):
        pg_lugat.kaynakli_satir_coz(s, KAYNAK_RNK)


def test_hazirla_yalniz_dosya_tarafi_iki_kaynak(kz: KaynakKoku) -> None:
    for slug in SLUGLAR:
        ctx = ctx_kur(kz.lk.tmp, kz.kok, adim="export", kaynaklar=[slug])
        h = pg.hazirla(ctx, slug, None, pg.EK_KAYNAKLAR[slug])
        assert len(h.lugat) == len(kz.satirlar(slug))
        assert all(isinstance(s, pg_lugat.LugatKaynakSatiri) for s in h.lugat)
        assert list(h.ham) == [slug] and len(h.ham[slug]) == 1  # kaynagin kendi ham dosyasi
        assert h.ham[slug][0]["yol"].startswith(f"raw/{slug}/")
        assert h.satirlar == [] and h.units_yol.endswith("lugat.jsonl")
    assert BICIMLER[KAYNAK_RGANEYEV].rnk_bagimli and lugat_kaynak.KAYNAKLAR == SLUGLAR


# --- gercek veritabani (yoksa atlanir; bu ajan KOSMAZ) ------------------------------------------


def _zorunlu(neden: str) -> None:
    if os.environ.get("MUTALAA_DEGISMEZLIK_ZORUNLU") == "1":
        pytest.fail(neden)
    pytest.skip(neden)


@pytest.fixture
def conn() -> Iterator[psycopg.Connection]:
    """Test veritabanina baglanir (dis islem, sonunda geri alinir); kalinti varsa atlar."""
    try:
        baglanti = baglan(Ayarlar(), test=True)
    except GirdiHatasi as hata:
        _zorunlu(f"test veritabani yok: {hata}")
        return
    try:
        kalinti = baglanti.execute(
            "SELECT (SELECT count(*) FROM icerik.lugat_madde WHERE source_id = ANY(%s))"
            " + (SELECT count(*) FROM icerik.source WHERE slug = ANY(%s))",
            (list(SLUGLAR), list(SLUGLAR)),
        ).fetchone()
        assert kalinti is not None
        if kalinti[0] != 0:
            baglanti.rollback()
            _zorunlu("mutalaa_test icinde lugat kaynagi kalintisi var")
        yield baglanti
    finally:
        baglanti.rollback()
        baglanti.close()


def _say(conn: psycopg.Connection, sorgu: str, *param: object) -> int:
    satir_ = conn.execute(sorgu, param).fetchone()  # type: ignore[arg-type]
    assert satir_ is not None
    return int(satir_[0])


@pytest.mark.veritabani
def test_gercek_ilk_yukleme_ikinci_kosu_sifir_degisiklik(
    kz: KaynakKoku, conn: psycopg.Connection
) -> None:
    n = len(kz.satirlar(KAYNAK_RNK))
    assert calistir(kz, KAYNAK_RNK, lambda: conn) == 0
    ilk = sayilar(kz)
    assert ilk["lugat_eklenen"] == n and ilk["lugat_review_acilan"] == yeni_review_sayisi(
        kz, KAYNAK_RNK
    )
    assert (
        _say(conn, "SELECT count(*) FROM icerik.lugat_madde WHERE source_id = %s", KAYNAK_RNK) == n
    )
    assert (
        _say(
            conn,
            "SELECT count(*) FROM icerik.lugat_madde WHERE source_id = %s AND origin = 'kaynak'"
            " AND status = 'aday' AND version = '1' AND tanim_tr IS NOT NULL",
            KAYNAK_RNK,
        )
        == n
    )
    # ayni baslik, iki anlam: anlam_no 1 ve 2, tanimlar bayt bayt
    anlamlar = conn.execute(
        "SELECT anlam_no, tanim_tr FROM icerik.lugat_madde WHERE source_id = %s"
        " AND basliksoz = 'denemea' ORDER BY anlam_no",
        (KAYNAK_RNK,),
    ).fetchall()
    assert [a[0] for a in anlamlar] == [1, 2]
    assert [a[1] for a in anlamlar] == [f"{TANIM_RNK}-1", f"{TANIM_RNK}-2"]
    # review: yalniz duzey 1-3, hedef_anahtar {kaynak}:{anlam_no}:{basliksoz}, anlam basvurusu yok
    assert _say(
        conn,
        "SELECT count(*) FROM icerik.review WHERE hedef_tablo = 'lugat_madde'"
        " AND starts_with(hedef_anahtar, %s)",
        f"{KAYNAK_RNK}:",
    ) == yeni_review_sayisi(kz, KAYNAK_RNK)
    assert (
        _say(
            conn,
            "SELECT count(*) FROM icerik.review WHERE hedef_anahtar = %s AND alan = 'tanim_tr'"
            " AND koken = 'hat' AND oneren = 'hat' AND onceki IS NULL"
            " AND onerilen ? 'kaynak' AND onerilen ? 'siklik' AND NOT onerilen ? 'anlam_basvuru'",
            f"{KAYNAK_RNK}:1:denemea",
        )
        == 1
    )
    assert (
        _say(
            conn,
            "SELECT count(*) FROM icerik.review WHERE hedef_anahtar = %s",
            f"{KAYNAK_RNK}:1:yenia",  # duzey 4: review yok
        )
        == 0
    )
    assert calistir(kz, KAYNAK_RNK, lambda: conn) == 0
    ikinci = sayilar(kz)
    assert (
        ikinci["lugat_eklenen"],
        ikinci["lugat_guncellenen"],
        ikinci["lugat_review_acilan"],
    ) == (0, 0, 0)
    assert ikinci["lugat_ayni_kalan"] == n


@pytest.mark.veritabani
def test_gercek_editor_satirina_yazilmaz_review_acilmaz(
    kz: KaynakKoku, conn: psycopg.Connection
) -> None:
    assert calistir(kz, KAYNAK_RNK, lambda: conn) == 0
    conn.execute(
        "UPDATE icerik.lugat_madde SET origin = 'editor', tanim_tr = 'EDITOR-TANIMI',"
        " kaynaklar = '{}'::jsonb WHERE source_id = %s AND basliksoz = 'denemea' AND anlam_no = 1",
        (KAYNAK_RNK,),
    )
    conn.execute("DELETE FROM icerik.review WHERE hedef_anahtar = %s", (f"{KAYNAK_RNK}:1:denemea",))
    assert calistir(kz, KAYNAK_RNK, lambda: conn) == 0
    s = sayilar(kz)
    assert s["lugat_atlanan_editor"] == 1 and s["lugat_guncellenen"] == 0
    satir_ = conn.execute(
        "SELECT origin, tanim_tr, kaynaklar::text FROM icerik.lugat_madde WHERE source_id = %s"
        " AND basliksoz = 'denemea' AND anlam_no = 1",
        (KAYNAK_RNK,),
    ).fetchone()
    assert satir_ == ("editor", "EDITOR-TANIMI", "{}")
    assert (
        _say(
            conn,
            "SELECT count(*) FROM icerik.review WHERE hedef_anahtar = %s",
            f"{KAYNAK_RNK}:1:denemea",
        )
        == 0
    )  # editor satirina review acilmadi


@pytest.mark.veritabani
def test_gercek_kaynak_tanimi_degisirse_satir_degismez_metin_degisti_sayilir(
    kz: KaynakKoku, conn: psycopg.Connection
) -> None:
    assert calistir(kz, KAYNAK_RNK, lambda: conn) == 0
    conn.execute(
        "UPDATE icerik.lugat_madde SET tanim_tr = 'ESKI-TANIM' WHERE source_id = %s"
        " AND basliksoz = 'yenia' AND anlam_no = 1",
        (KAYNAK_RNK,),
    )
    assert calistir(kz, KAYNAK_RNK, lambda: conn) == 0
    assert sayilar(kz)["lugat_metin_degisti"] == 1
    assert conn.execute(
        "SELECT tanim_tr FROM icerik.lugat_madde WHERE source_id = %s AND basliksoz = 'yenia'",
        (KAYNAK_RNK,),
    ).fetchone() == ("ESKI-TANIM",)


@pytest.mark.veritabani
def test_gercek_kapali_review_yeniden_acilmaz_ve_turetilmis_sutunlar_guncellenir(
    kz: KaynakKoku, conn: psycopg.Connection
) -> None:
    assert calistir(kz, KAYNAK_RNK, lambda: conn) == 0
    conn.execute(
        "UPDATE icerik.review SET durum = 'onaylandi' WHERE hedef_anahtar = %s",
        (f"{KAYNAK_RNK}:1:denemea",),
    )
    conn.execute(
        "UPDATE icerik.lugat_madde SET duzey = 4,"
        " kaynaklar = '{\"kelime_frekans_karsiligi\": false}'::jsonb"
        " WHERE source_id = %s AND basliksoz = 'denemea'",
        (KAYNAK_RNK,),
    )
    assert calistir(kz, KAYNAK_RNK, lambda: conn) == 0
    s = sayilar(kz)
    # UPDATE ham basligi tam "denemea" olan iki satiri (anlam 1 ve 2) bozdu; "Denemea" aynidir.
    assert s["lugat_guncellenen"] == 2 and s["lugat_review_acilan"] == 0  # kapali review var
    assert (
        _say(
            conn,
            "SELECT count(*) FROM icerik.lugat_madde WHERE source_id = %s AND duzey = 1",
            KAYNAK_RNK,
        )
        == 3
    )
    assert (
        _say(
            conn,
            "SELECT count(*) FROM icerik.review WHERE hedef_anahtar = %s",
            f"{KAYNAK_RNK}:1:denemea",
        )
        == 1
    )


@pytest.mark.veritabani
def test_gercek_rganeyev_yukleme_ve_kelime_frekans_yolu_ayni_kisitla_calisir(
    kz: KaynakKoku, conn: psycopg.Connection
) -> None:
    assert calistir(kz, KAYNAK_RGANEYEV, lambda: conn) == 0
    assert (
        _say(
            conn,
            "SELECT count(*) FROM icerik.lugat_madde WHERE source_id = %s AND origin = 'kaynak'",
            KAYNAK_RGANEYEV,
        )
        == 5
    )
    anlamlar = conn.execute(
        "SELECT anlam_no FROM icerik.lugat_madde WHERE source_id = %s AND basliksoz = 'denemed'"
        " ORDER BY anlam_no",
        (KAYNAK_RGANEYEV,),
    ).fetchall()
    assert [a[0] for a in anlamlar] == [1, 2]
    # Kelime-Frekans yolu: anlam_no = 1, origin hat (degismedi); kaynak satiri da girebilir
    assert calistir_kf(kz, conn) == 0
    assert (
        _say(
            conn,
            "SELECT count(*) FROM icerik.lugat_madde WHERE source_id = %s AND origin = 'hat'"
            " AND anlam_no = 1 AND tanim_tr IS NULL",
            KF,
        )
        > 0
    )


def calistir_kf(kz: KaynakKoku, conn: psycopg.Connection) -> int:
    assert kz.lk.qa() == 0
    return pg.komut_export_pg(
        ayarlar_kur(kz.lk.tmp), depo_kok=kz.kok, source=KF, baglanti=lambda: conn
    )  # type: ignore[arg-type]
