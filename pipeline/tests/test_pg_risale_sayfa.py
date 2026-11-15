# ruff: noqa: F811
"""`export pg --source risale-baski-rnk`: RNK baski sayfa esleme yuklemesi (A20.3; SENTETIK veri).

VERITABANISIZ: baglanti sahte bir nesnedir (`SahteBaglanti`, `test_pg_risale`): calisan SQL
metinleri, parametreler, `COPY` satirlari ve islem sinirlari kaydedilir. Zincir (ingest ->
normalize -> anchor -> sayfa esleme -> qa) sentetik RNK dosyasindan gercek adimlarla kurulur;
hicbir Risale metni yoktur.
"""

import json
import re
from collections.abc import Callable

import psycopg
import pytest
from hat_yardimci import ansisiz, ayarlar_kur
from test_export_pg import Cagrilmaz
from test_pg_risale import SahteBaglanti, SahteSonuc, esle
from test_risale_rnk_cli import RnkKoku, rk  # noqa: F401  (rk: fixture)
from test_risale_sayfa import (  # noqa: F401  (bk: fixture)
    KAYNAK,
    SURUM,
    baski,
    baski_klasorleri,
    baski_qa,
    bk,
)
from typer.testing import CliRunner

from mutalaa_pipeline import cli
from mutalaa_pipeline.export import pg, pg_risale_sayfa
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.ingest.risale_kaynaklari import KAYNAK_RNK

runner = CliRunner()
OZET = re.compile(r"[0-9a-f]{64}")
UPSERT_ESLESME = "INSERT INTO icerik.page_map"
SAYAC_ESLESME = "count(*) FILTER (WHERE (p.start_anchor"
EKSIK_CAPA_ESLESME = "FROM (SELECT start_anchor AS anchor"
TASAN_ESLESME = "char_length(b.metin)"
OZET_ESLESME = "b.content_hash IS DISTINCT FROM"
EKSIK_SATIR_ESLESME = "AND NOT EXISTS (SELECT 1 FROM pg_temp.staging_risale_sayfa s"


def hazir(bk_: RnkKoku) -> None:
    """Sentetik zincir + sayfa esleme + dort kapili QA raporu."""
    assert bk_.zincir() == 0 and baski(bk_) == 0
    kod, cikti = baski_qa(bk_)
    assert kod == 0, cikti


def calistir(
    bk_: RnkKoku,
    baglanti: SahteBaglanti | Callable[[], psycopg.Connection] | None = None,
    **kw: object,
) -> int:
    if baglanti is None:
        fabrika: Callable[[], psycopg.Connection] = Cagrilmaz()
    elif isinstance(baglanti, SahteBaglanti):
        fabrika = lambda: baglanti  # type: ignore[assignment,return-value]  # noqa: E731
    else:
        fabrika = baglanti
    return pg.komut_export_pg(
        ayarlar_kur(bk_.tmp),
        depo_kok=bk_.kok,
        source=KAYNAK,
        baglanti=fabrika,
        **kw,  # type: ignore[arg-type]
    )


def son_rapor(bk_: RnkKoku) -> dict[str, object]:
    raporlar = [
        json.loads(p.read_text(encoding="utf-8"))
        for p in sorted((bk_.veri_kok / "reports").glob("*.json"), key=lambda p: p.name)
    ]
    export = [r for r in raporlar if r.get("komut") == "export pg"]
    assert export
    return export[-1]


def sayilar(bk_: RnkKoku) -> dict[str, int]:
    deger = son_rapor(bk_)["sayilar"]
    assert isinstance(deger, dict)
    return deger


def tum_sorgular(db: SahteBaglanti) -> list[str]:
    return [m for islem in db.islemler for m, _ in islem.sorgular]


# --- ilk yukleme: SQL ve parametreler ------------------------------------------------------


def test_ilk_yukleme_tek_islem_kilit_kaynak_copy_ve_upsert(bk: RnkKoku) -> None:
    hazir(bk)
    db = SahteBaglanti(
        esle((SAYAC_ESLESME, SahteSonuc([(0, 0)])), (UPSERT_ESLESME, SahteSonuc(rowcount=4)))
    )
    assert calistir(bk, db) == 0
    assert [i.durum for i in db.islemler] == ["onaylandi"]  # tek islem
    sorgular = tum_sorgular(db)
    assert "pg_advisory_xact_lock(hashtext('mutalaa:'" in sorgular[0]  # kilit ilk ifade
    assert db.islemler[0].sorgular[0][1] == (KAYNAK,)
    (kaynak_ekle,) = db.sorgular("INSERT INTO icerik.source")
    _, params = kaynak_ekle
    assert isinstance(params, dict)
    assert params["slug"] == KAYNAK and params["tur"] == "baski" and params["surum"] == SURUM
    assert params["baski_bilgisi"] is not None  # ilk yazimda baski_bilgisi ve notlar
    assert params["alinma_tarihi"] is None and params["dosya_sha256"] is None
    # sira: kaynak, staging, onkosullar (capa, ofset, eksik satir), sayac, upsert
    siralama = [
        next(i for i, m in enumerate(sorgular) if parca in m)
        for parca in (
            "INSERT INTO icerik.source",
            "CREATE TEMP TABLE staging_risale_sayfa",
            EKSIK_CAPA_ESLESME,
            OZET_ESLESME,
            TASAN_ESLESME,
            EKSIK_SATIR_ESLESME,
            SAYAC_ESLESME,
            UPSERT_ESLESME,
        )
    ]
    assert siralama == sorted(siralama)
    assert sayilar(bk) == {
        "sayfa_staging": 4,
        "sayfa_eklenen": 4,
        "sayfa_guncellenen": 0,
        "sayfa_degismeyen": 0,
        "sayfa_bolum_basi": 0,
        "sayfa_dosya": 1,
        "kaynak_eklenen": 1,
        "kaynak_guncellenen": 0,
        "kaynak_degismeyen": 0,
    }


def test_copy_satirlari_sutun_sirasiyla_ve_sayfa_sirasiyla(bk: RnkKoku) -> None:
    hazir(bk)
    db = SahteBaglanti(esle((UPSERT_ESLESME, SahteSonuc(rowcount=4))))
    assert calistir(bk, db) == 0
    ((sorgu, _),) = db.kopyalar
    sutunlar = re.search(r"\((.*?)\)", sorgu)
    assert sutunlar is not None
    assert [a.strip() for a in sutunlar.group(1).split(",")] == [
        "volume", "page", "start_anchor", "start_offset", "end_anchor", "end_offset",
        "source_id", "data_version", "start_hash", "end_hash",
    ]  # fmt: skip
    satirlar = db.kopya_satirlari()
    assert [r[1] for r in satirlar] == [4, 5, 6, 7]
    assert satirlar[2][:6] == (
        1,
        6,
        "rn:deneme-kitap:deneme-bolum-1:p2",
        31,
        "rn:deneme-kitap:deneme-bolum-1:p4",
        29,
    )
    assert all(r[6] == KAYNAK and r[7] == f"{KAYNAK}@{SURUM}" for r in satirlar)


def test_upsert_yalniz_turetilmis_sutunlar_satir_silinmez() -> None:
    sql = pg_risale_sayfa.UPSERT
    assert "ON CONFLICT (source_id, volume, page, line) DO UPDATE SET" in sql
    set_kismi = sql.split("DO UPDATE SET", 1)[1].split(" WHERE ", 1)[0]
    atananlar = [a.split("=")[0].strip() for a in set_kismi.split(",")]
    assert atananlar == [
        "start_anchor",
        "start_offset",
        "end_anchor",
        "end_offset",
        "data_version",
    ]
    govde = sql.split(" ON CONFLICT", 1)[0]
    yasak = re.compile(r"(line|line_type|centered|glyphs|id)")
    assert yasak.search(govde) is None and yasak.search(set_kismi) is None
    assert "IS DISTINCT FROM" in sql.split(" WHERE ", 1)[1]  # degismeyen satir yazilmaz
    tum = " ".join(
        getattr(pg_risale_sayfa, ad)
        for ad in dir(pg_risale_sayfa)
        if ad.isupper() and isinstance(getattr(pg_risale_sayfa, ad), str)
    ).upper()
    assert "DELETE" not in tum and "TRUNCATE" not in tum  # satir silinmez
    assert "review" not in tum.lower()  # inceleme kaydi acilmaz


def test_ikinci_kosu_degismeyen_ve_guncelleme_sayaclari(bk: RnkKoku) -> None:
    hazir(bk)
    db = SahteBaglanti(
        esle((SAYAC_ESLESME, SahteSonuc([(4, 0)])), (UPSERT_ESLESME, SahteSonuc(rowcount=0)))
    )
    assert calistir(bk, db) == 0
    s = sayilar(bk)
    assert (s["sayfa_eklenen"], s["sayfa_guncellenen"], s["sayfa_degismeyen"]) == (0, 0, 4)
    db = SahteBaglanti(
        esle((SAYAC_ESLESME, SahteSonuc([(3, 2)])), (UPSERT_ESLESME, SahteSonuc(rowcount=3)))
    )
    assert calistir(bk, db) == 0
    s = sayilar(bk)
    assert (s["sayfa_eklenen"], s["sayfa_guncellenen"], s["sayfa_degismeyen"]) == (1, 2, 1)


def test_source_varsa_yalniz_betimleyici_alan_guncellenir(bk: RnkKoku) -> None:
    hazir(bk)
    var = {
        "baslik": "Deneme baski",
        "surum": "eski-surum",
        "kaynak_url": "https://example.test/x",
        "atif_metni": "Deneme atif metni.",
        "atif_url": None,
        "notice_text": None,
        "alinma_tarihi": None,
        "dosya_sha256": None,
    }
    db = SahteBaglanti(esle((UPSERT_ESLESME, SahteSonuc(rowcount=4))))

    class DictImlec:
        def __init__(self, b: SahteBaglanti) -> None:
            self.b = b
            self.son = SahteSonuc()

        def __enter__(self) -> "DictImlec":
            return self

        def __exit__(self, *a: object) -> None:
            return None

        def execute(self, sorgu: object, params: object = None) -> "DictImlec":
            self.son = self.b.execute(sorgu, params)
            return self

        def fetchone(self) -> object:
            return dict(var)

        def copy(self, sorgu: str):  # type: ignore[no-untyped-def]
            from test_pg_risale import SahteKopya

            return SahteKopya(self.b, sorgu)

    db.cursor = lambda **kw: DictImlec(db)  # type: ignore[method-assign,assignment]
    assert calistir(bk, db) == 0
    assert db.sorgular("INSERT INTO icerik.source") == []
    ((metin, params),) = db.sorgular("UPDATE icerik.source SET")
    assert '"surum" = %(surum)s' in metin and "baski_bilgisi" not in metin
    assert isinstance(params, dict) and params["surum"] == SURUM


# --- onkosullar: islem geri alinir, hicbir sey yazilmaz ------------------------------------


@pytest.mark.parametrize(
    ("eslesme", "parca"),
    [
        (EKSIK_CAPA_ESLESME, "biriminde yok"),
        (OZET_ESLESME, "staged'den sonra degismis"),
        (TASAN_ESLESME, "metnine sigmiyor"),
        (EKSIK_SATIR_ESLESME, "staged icinde yok"),
    ],
)
def test_veritabani_onkosulu_tutmazsa_cikis_1_ve_upsert_yok(
    bk: RnkKoku, capsys: pytest.CaptureFixture[str], eslesme: str, parca: str
) -> None:
    hazir(bk)
    db = SahteBaglanti(esle((eslesme, SahteSonuc([("rn:deneme-kitap:p9",)]))))
    capsys.readouterr()
    assert calistir(bk, db) == 1
    hata = capsys.readouterr().err
    assert parca in hata and hata.isascii()
    assert "risale-rnk-metin" in hata or eslesme != EKSIK_CAPA_ESLESME
    assert db.islemler[0].durum == "geri_alindi"
    assert db.sorgular(UPSERT_ESLESME) == []  # page_map'e hicbir sey yazilmadi
    # basarisiz pipeline_run satiri ayri kisa islemde yazilir; page_map'e dokunmaz
    assert not [m for m, _ in db.islemler[-1].sorgular if "icerik.page_map" in m]


def test_upsert_satir_sayisi_beklenenden_farkliysa_cikis_1(bk: RnkKoku) -> None:
    hazir(bk)
    db = SahteBaglanti(
        esle((SAYAC_ESLESME, SahteSonuc([(0, 0)])), (UPSERT_ESLESME, SahteSonuc(rowcount=3)))
    )
    assert calistir(bk, db) == 1
    assert db.islemler[0].durum == "geri_alindi"


def test_sql_hatasi_butun_islemi_geri_alir(bk: RnkKoku) -> None:
    hazir(bk)
    db = SahteBaglanti(hata=(UPSERT_ESLESME, psycopg.errors.DeadlockDetected("x")))
    assert calistir(bk, db) == 2
    assert [i.durum for i in db.islemler] == ["geri_alindi", "onaylandi"]
    assert not [m for m, _ in db.islemler[1].sorgular if "icerik.page_map" in m]


def test_dry_run_gercek_akisi_calistirir_ve_geri_alir(bk: RnkKoku) -> None:
    hazir(bk)
    db = SahteBaglanti(
        esle((SAYAC_ESLESME, SahteSonuc([(0, 0)])), (UPSERT_ESLESME, SahteSonuc(rowcount=4)))
    )
    assert calistir(bk, db, dry_run=True) == 0
    assert [i.durum for i in db.islemler] == ["geri_alindi"]
    assert db.sorgular(UPSERT_ESLESME) and db.kopyalar  # yazim ifadeleri calisti
    assert sayilar(bk)["sayfa_eklenen"] == 4  # sayac gercek, ama hicbir sey kalici degil


# --- dosya onkosullari: baglanti acilmaz ---------------------------------------------------


def hata_ile(
    bk_: RnkKoku, kod: int, parca: str, capsys: pytest.CaptureFixture[str], **kw: object
) -> None:
    capsys.readouterr()
    sonuc = calistir(bk_, **kw)  # Cagrilmaz: baglanti acilirsa test kirilir
    hata = capsys.readouterr().err
    assert sonuc == kod, hata
    assert parca in hata, hata
    assert hata.isascii()


def test_qa_raporu_yoksa_cikis_1(bk: RnkKoku, capsys: pytest.CaptureFixture[str]) -> None:
    assert bk.zincir() == 0 and baski(bk) == 0
    hata_ile(bk, 1, "QA raporu yok", capsys)


def test_kapi_kaldiysa_yukleme_yok_cikis_1(bk: RnkKoku, capsys: pytest.CaptureFixture[str]) -> None:
    assert bk.zincir() == 0 and baski(bk) == 0
    veri = json.loads(bk.kilit_yolu.read_bytes())
    veri["kitaplar"]["tr_k/deneme"]["sayfa_sayisi"] += 1
    bk.kilit_yolu.write_bytes((json.dumps(veri, ensure_ascii=True, indent=2) + "\n").encode())
    assert baski_qa(bk)[0] == 1
    hata_ile(bk, 1, "G-BUT", capsys)


def test_sayfa_esleme_calistirmasi_yoksa_cikis_2(
    bk: RnkKoku, capsys: pytest.CaptureFixture[str]
) -> None:
    assert bk.zincir() == 0
    hata_ile(bk, 2, "anchor", capsys)


def test_kayitsiz_kaynak_cikis_2(
    rk: RnkKoku,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert rk.zincir() == 0
    capsys.readouterr()
    sonuc = pg.komut_export_pg(
        ayarlar_kur(rk.tmp),
        depo_kok=rk.kok,
        source=KAYNAK,
        baglanti=Cagrilmaz(),  # type: ignore[arg-type]
    )
    assert sonuc == 2


def test_page_map_ozeti_manifestle_tutmazsa_cikis_2(
    bk: RnkKoku, capsys: pytest.CaptureFixture[str]
) -> None:
    hazir(bk)
    (klasor,) = baski_klasorleri(bk)
    dosya = klasor / "page_map.jsonl"
    dosya.write_bytes(dosya.read_bytes() + b"\n")
    hata_ile(bk, 2, "saglam degil", capsys)


def test_diyanet_ve_metin_kaynaklari_bu_yoldan_gitmez() -> None:
    with pytest.raises(GirdiHatasi, match="yalniz"):
        pg_risale_sayfa.kaynak_denetle(KAYNAK_RNK)
    assert pg.EK_KAYNAKLAR[KAYNAK] == ()


# --- satirlari kati okuma ------------------------------------------------------------------


def _satir(**degisim: object) -> bytes:
    taban: dict[str, object] = {
        "source_id": KAYNAK,
        "volume": 1,
        "page": 1,
        "start_anchor": "rn:deneme-kitap:p1",
        "start_offset": 0,
        "end_anchor": "rn:deneme-kitap:p1",
        "end_offset": 5,
        "data_version": f"{KAYNAK}@{SURUM}",
        "start_hash": "a" * 64,
        "end_hash": "b" * 64,
    }
    taban.update(degisim)
    return (json.dumps(taban, sort_keys=True, separators=(",", ":")) + "\n").encode()


def test_satirlari_coz_gecerli_satir() -> None:
    (s,) = pg_risale_sayfa.satirlari_coz(_satir(), KAYNAK)
    assert (s.volume, s.page, s.start_offset, s.end_offset) == (1, 1, 0, 5)
    assert (s.start_hash, s.end_hash) == ("a" * 64, "b" * 64)


@pytest.mark.parametrize(
    "degisim",
    [
        {"metin": "x"},  # fazla alan
        {"source_id": "baska"},
        {"volume": 0},
        {"volume": 40000},  # smallint disi
        {"page": 0},
        {"start_offset": -1},
        {"end_offset": True},
        {"start_anchor": "q:2:255"},  # rn: degil
        {"start_anchor": "rn:deneme-kitap:p1:s2"},  # cumle capasi birim degil
        {"end_anchor": "rn:Deneme:p1"},
        {"data_version": ""},
        {"start_hash": ""},
        {"end_hash": "A" * 64},  # buyuk harf
        {"start_hash": "a" * 63},
        {"start_hash": 5},
    ],
)
def test_satirlari_coz_bozuk_satir_girdi_hatasi(degisim: dict[str, object]) -> None:
    with pytest.raises(GirdiHatasi):
        pg_risale_sayfa.satirlari_coz(_satir(**degisim), KAYNAK)


def test_satirlari_coz_yinelenen_anahtar_ve_bos_dosya() -> None:
    with pytest.raises(GirdiHatasi, match="yinelenen"):
        pg_risale_sayfa.satirlari_coz(_satir() + _satir(), KAYNAK)
    with pytest.raises(GirdiHatasi):
        pg_risale_sayfa.satirlari_coz(b"", KAYNAK)


# --- rapor ve gunluk ----------------------------------------------------------------------


def test_rapor_ve_gunluk_metin_tasimaz(bk: RnkKoku) -> None:
    hazir(bk)
    db = SahteBaglanti(
        esle((SAYAC_ESLESME, SahteSonuc([(0, 0)])), (UPSERT_ESLESME, SahteSonuc(rowcount=4)))
    )
    assert calistir(bk, db) == 0
    kayitlar = b"".join(p.read_bytes() for p in (bk.veri_kok / "reports").glob("*.json"))
    kayitlar += b"".join(p.read_bytes() for p in (bk.veri_kok / "logs").glob("*.jsonl"))
    assert kayitlar and b"Deneme paragraf" not in kayitlar and b"Deneme dipnot" not in kayitlar
    # COPY satirlari da yalniz capa ve sayi tasir
    assert all(
        not isinstance(a, str) or a.startswith(("rn:", KAYNAK)) or OZET.fullmatch(a)
        for r in db.kopya_satirlari()
        for a in r
    )


def test_cli_yardim_ve_kayit_tablosu(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FORCE_COLOR", "1")
    sonuc = runner.invoke(cli.app, ["export", "pg", "--help"])
    assert sonuc.exit_code == 0
    for secenek in ("--source", "--run", "--dry-run", "--force"):
        assert secenek in ansisiz(sonuc.output)


def test_staged_satirlar_uc_birimlerin_content_hash_degerini_tasir(bk: RnkKoku) -> None:
    """`start_hash`/`end_hash` anchor ciktisindaki birimlerin `content_hash` degeridir ve
    COPY ile staging'e gider; `page_map` tablosuna yazilmaz (UPSERT sutun listesinde yok)."""
    hazir(bk)
    (klasor,) = baski_klasorleri(bk)
    satirlar = [
        json.loads(k) for k in (klasor / "page_map.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    anchor = sorted((bk.veri_kok / "staged" / KAYNAK_RNK).glob("*/units.jsonl"))[-1]
    ozet = {
        (u := json.loads(k))["anchor"]: u["content_hash"]
        for k in anchor.read_text(encoding="utf-8").splitlines()
    }
    assert satirlar
    for s in satirlar:
        assert s["start_hash"] == ozet[s["start_anchor"]]
        assert s["end_hash"] == ozet[s["end_anchor"]]
    db = SahteBaglanti(esle((UPSERT_ESLESME, SahteSonuc(rowcount=4))))
    assert calistir(bk, db) == 0
    kopya = db.kopya_satirlari()
    assert [(r[8], r[9]) for r in kopya] == [(s["start_hash"], s["end_hash"]) for s in satirlar]
    assert "hash" not in pg_risale_sayfa.UPSERT


def test_ozet_farki_sorgusu_staged_ozeti_veritabaniyla_karsilastirir() -> None:
    sql = pg_risale_sayfa.OZET_FARKI
    assert "b.content_hash IS DISTINCT FROM s.start_hash" in sql
    assert "e.content_hash IS DISTINCT FROM s.end_hash" in sql
