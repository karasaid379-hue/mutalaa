"""`export pg --source risale-rnk-metin`: RNK Risale birim yuklemesi (A20.2b; SENTETIK veri).

Metinler "Deneme paragrafi N ..." biciminde sentetiktir; gercek Risale metni yoktur. Testlerin
cogu VERITABANISIZDIR: baglanti sahte bir nesnedir (`SahteBaglanti`), calisan SQL metinleri,
parametreler, `COPY` satirlari ve islem sinirlari kaydedilir. `veritabani` isaretli birkac test
gercek test veritabanina (`mutalaa_test`) baglanir ve veritabani yoksa atlanir.
"""

import json
import os
import re
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

import psycopg
import pytest
from hat_yardimci import ansisiz, ayarlar_kur, ctx_kur
from psycopg.types.range import Range
from test_export_pg import Cagrilmaz, Senaryo, _staged_calisma
from test_sources import alanlar_kur, kayit_yaz, kok_kur
from typer.testing import CliRunner

from mutalaa_pipeline import cli, lineage, qa
from mutalaa_pipeline.adimlar.risale import ANCHOR_ALANLARI, parent_yolu
from mutalaa_pipeline.anchor import content_hash
from mutalaa_pipeline.config import Ayarlar
from mutalaa_pipeline.db import baglan
from mutalaa_pipeline.export import pg, pg_risale
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.ingest.risale_kaynaklari import KAYNAK_DIYANET, KAYNAK_RNK
from mutalaa_pipeline.normalize import tr_stem
from mutalaa_pipeline.runctx import RunContext

KAYNAK = KAYNAK_RNK
TARIH = "2026-11-13"
KAPILAR = ("G-KAY", "G-BUT", "G-CAP", "G-NOR")
TUM_GECTI = dict.fromkeys(KAPILAR, "gecti")
KITAP = "deneme-kitap"
KITAP_OTA = "deneme-kitap-osmanlica"
runner = CliRunner()


# --- sentetik satirlar ---------------------------------------------------------------------


def satir(
    no: int,
    *,
    kitap: str = KITAP,
    dil: str = "tr",
    rol: str = "govde",
    metin: str | None = None,
    **degisim: object,
) -> dict[str, object]:
    """`anchor` adiminin cikti bicimi (ANCHOR_ALANLARI) ile ayni alanlari tasiyan sentetik satir."""
    metin = metin if metin is not None else f"Deneme paragrafi {no}. Ikinci cumle {no}."
    ilk = metin.index(".") + 1
    cumleler = [] if rol == "baslik" else [[0, ilk], [ilk + 1, len(metin)]]
    tr = dil == "tr"
    kayit: dict[str, object] = {
        "anchor": f"rn:{kitap}:soz-1:p{no}",
        "kind": "risale",
        "role": rol,
        "parent_path": parent_yolu((kitap, "soz-1")),
        "ord": no,
        "ayah_lo": None,
        "ayah_hi": None,
        "text": metin,
        "marks": [{"s": 0, "e": 7, "t": "ar"}] if rol == "govde" else [],
        "sentences": cumleler,
        "content_hash": content_hash(metin),
        "metin_durumu": "taslak",
        "attrs": {"dil": dil, "yon": "ltr" if tr else "rtl", "baslik_yolu": ["Deneme"], "p": no},
        "tr_narrow": f"deneme {no}" if tr else None,
        "tr_wide": f"deneme {no}" if tr else None,
        "tr_stem": f"deneme {no}" if tr else None,
        "ar_norm": f"deneme {no}",
        "data_version": f"{KAYNAK}@deneme-1.0",
        "provenance": {"file": "deneme.txt", "konum": {"satir": [no]}, "cumle": {"surum": "1.0"}},
        "source_id": KAYNAK,
    }
    kayit.update(degisim)
    return kayit


def varsayilan_satirlar() -> list[dict[str, object]]:
    return [
        satir(1, rol="baslik"),
        satir(2),
        satir(3),
        satir(1, kitap=KITAP_OTA, dil="ota"),
    ]


# --- sahte baglanti ------------------------------------------------------------------------


class SahteSonuc:
    def __init__(self, satirlar: Sequence[tuple[object, ...]] = (), rowcount: int = 0) -> None:
        self._satirlar = list(satirlar)
        self.rowcount = rowcount

    def fetchone(self) -> tuple[object, ...] | None:
        return self._satirlar[0] if self._satirlar else None

    def fetchall(self) -> list[tuple[object, ...]]:
        return list(self._satirlar)


@dataclass
class Islem:
    durum: str = "acik"  # acik, onaylandi, geri_alindi
    sorgular: list[tuple[str, object]] = field(default_factory=list)


class SahteKopya:
    def __init__(self, baglanti: "SahteBaglanti", sorgu: str) -> None:
        self.baglanti = baglanti
        self.parti: list[tuple[object, ...]] = []
        baglanti.kopyalar.append((sorgu, self.parti))

    def __enter__(self) -> "SahteKopya":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def write_row(self, satir_: Sequence[object]) -> None:
        self.parti.append(tuple(satir_))


class SahteImlec:
    def __init__(self, baglanti: "SahteBaglanti") -> None:
        self.baglanti = baglanti
        self._son = SahteSonuc()

    def __enter__(self) -> "SahteImlec":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def execute(self, sorgu: object, params: object = None) -> "SahteImlec":
        self._son = self.baglanti.execute(sorgu, params)
        return self

    def fetchone(self) -> object:
        return self._son.fetchone()

    def fetchall(self) -> list[tuple[object, ...]]:
        return self._son.fetchall()

    def copy(self, sorgu: str) -> SahteKopya:
        return SahteKopya(self.baglanti, sorgu)

    def executemany(self, sorgu: str, satirlar: Sequence[object]) -> None:
        self.baglanti.coklu.append((sorgu, list(satirlar)))


Yanit = Callable[[str, object], SahteSonuc | None]


class SahteBaglanti:
    """`psycopg.Connection` yerine gecen kayitci; DB'ye hicbir sey gitmez."""

    def __init__(self, yanit: Yanit | None = None, *, hata: tuple[str, Exception] | None = None):
        self.yanit = yanit
        self.hata = hata
        self.islemler: list[Islem] = []
        self.kopyalar: list[tuple[str, list[tuple[object, ...]]]] = []
        self.coklu: list[tuple[str, list[object]]] = []

    def transaction(self):  # type: ignore[no-untyped-def]
        return self._islem()

    @contextmanager
    def _islem(self) -> Iterator[None]:
        islem = Islem()
        self.islemler.append(islem)
        try:
            yield
        except psycopg.Rollback:
            islem.durum = "geri_alindi"
            return
        except BaseException:
            islem.durum = "geri_alindi"
            raise
        islem.durum = "onaylandi"

    def cursor(self, **kw: object) -> SahteImlec:
        return SahteImlec(self)

    def execute(self, sorgu: object, params: object = None) -> SahteSonuc:
        metin = sorgu if isinstance(sorgu, str) else sorgu.as_string()  # type: ignore[attr-defined]
        if self.islemler:
            self.islemler[-1].sorgular.append((metin, params))
        if self.hata is not None and self.hata[0] in metin:
            raise self.hata[1]
        sonuc = self.yanit(metin, params) if self.yanit is not None else None
        return sonuc if sonuc is not None else SahteSonuc()

    # -- sorgulama yardimcilari --
    def sorgular(self, parca: str) -> list[tuple[str, object]]:
        return [(m, p) for i in self.islemler for m, p in i.sorgular if parca in m]

    def kopya_satirlari(self) -> list[tuple[object, ...]]:
        return [satir_ for _, parti in self.kopyalar for satir_ in parti]


def esle(*cifter: tuple[str, SahteSonuc]) -> Yanit:
    def yanit(metin: str, params: object) -> SahteSonuc | None:
        for parca, sonuc in cifter:
            if parca in metin:
                return sonuc
        return None

    return yanit


# --- senaryo -------------------------------------------------------------------------------


def senaryo_kur(tmp_path: Path, **kaynak_alanlari: object) -> Senaryo:
    kok = kok_kur(tmp_path)
    alanlar: dict[str, object] = {
        "tur": "risale",
        "surum": "deneme-1.0",
        "baslik": "Deneme Risale kaynagi",
        "kaynak_url": "https://deneme.invalid/",
        "notlar": "Deneme notu",
        "baski_bilgisi": {"yayinevi": "Deneme Yayinevi"},
    }
    alanlar.update(kaynak_alanlari)
    kayit_yaz(kok, alanlar_kur(KAYNAK, **alanlar))
    return Senaryo(tmp_path, kok, ayarlar_kur(tmp_path))


def _units_baytlari(satirlar: Sequence[dict[str, object]]) -> bytes:
    return "".join(
        json.dumps(k, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n"
        for k in satirlar
    ).encode("utf-8")


def zincir_kur(
    s: Senaryo,
    satirlar: Sequence[dict[str, object]] | None = None,
    *,
    kapilar: dict[str, str] | None = None,
    qa_yaz: bool = True,
    units_bayt: bytes | None = None,
) -> str:
    """ingest -> normalize -> anchor zinciri ve QA raporu; anchor run_id doner."""
    satirlar = satirlar if satirlar is not None else varsayilan_satirlar()
    ing, norm, anc, qa_id = (str(s.uretici.uret()) for _ in range(4))
    ham: list[lineage.Girdi] = []
    for ad in ("deneme-a.txt", "deneme-b.txt"):  # iki ham dosya: alinma_tarihi/dosya_sha256 NULL
        yol = s.veri / "raw" / KAYNAK / TARIH / ad
        yol.parent.mkdir(parents=True, exist_ok=True)
        yol.write_bytes(f"Deneme ham dosya {ad}\n".encode())
        ham.append(lineage.Girdi(f"raw/{KAYNAK}/{TARIH}/{ad}", lineage.sha256_dosya(yol)))
    ing_units = b'{"deneme":1}\n'
    _staged_calisma(s, KAYNAK, ing, "ingest", {"units.jsonl": ing_units}, ham)
    ust = lineage.Girdi(f"staged/{KAYNAK}/{ing}/units.jsonl", lineage.sha256_bayt(ing_units), ing)
    norm_units = b'{"deneme":2}\n'
    _staged_calisma(s, KAYNAK, norm, "normalize", {"units.jsonl": norm_units}, [ust])
    norm_girdi = lineage.Girdi(
        f"staged/{KAYNAK}/{norm}/units.jsonl", lineage.sha256_bayt(norm_units), norm
    )
    units = units_bayt if units_bayt is not None else _units_baytlari(satirlar)
    _staged_calisma(s, KAYNAK, anc, "anchor", {"units.jsonl": units}, [norm_girdi])
    s.anchor_run = anc
    if qa_yaz:
        klasor = s.veri / "reports"
        klasor.mkdir(parents=True, exist_ok=True)
        rapor = {
            "komut": "qa run",
            "kaynak": KAYNAK,
            "anchor_run_id": anc,
            "units_sha256": lineage.sha256_bayt(units),
            "kapilar": kapilar if kapilar is not None else TUM_GECTI,
        }
        (klasor / f"{qa_id}.json").write_text(json.dumps(rapor), encoding="utf-8", newline="\n")
    return anc


def calistir(
    s: Senaryo,
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
    return pg.komut_export_pg(s.ayarlar, depo_kok=s.kok, source=source, baglanti=fabrika, **kw)  # type: ignore[arg-type]


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


def hata_ile(
    s: Senaryo, kod: int, parca: str, capsys: pytest.CaptureFixture[str], **kw: object
) -> str:
    """Dosya onkosulu hatasi: cikis kodu ve neden birlikte sinanir; baglanti acilmamalidir."""
    capsys.readouterr()
    sonuc = calistir(s, **kw)
    hata = capsys.readouterr().err
    assert sonuc == kod, hata
    assert parca in hata, hata
    assert hata.isascii()
    return hata


# --- ilk yukleme: SQL ve parametreler ------------------------------------------------------


def test_ilk_yukleme_ekleme_sql_ve_parametreleri(tmp_path: Path) -> None:
    s = senaryo_kur(tmp_path)
    anc = zincir_kur(s)
    db = SahteBaglanti(
        esle(
            ("INSERT INTO icerik.unit", SahteSonuc(rowcount=4)),
            ("FROM icerik.source", SahteSonuc()),
        )
    )
    assert calistir(s, db) == 0
    # tek islem, onaylandi; gecici tablo ve COPY ayni islemde
    assert [i.durum for i in db.islemler] == ["onaylandi"]
    (ekleme,) = db.sorgular("INSERT INTO icerik.unit")
    metin, params = ekleme
    assert "WHERE NOT EXISTS (SELECT 1 FROM icerik.unit u WHERE u.anchor = s.anchor)" in metin
    assert "'risale'" in metin and "'taslak'" in metin and "ORDER BY s.sira" in metin
    assert isinstance(params, tuple) and len(params) == 1
    assert re.fullmatch(r"[0-9a-f-]{36}", str(params[0]))
    assert son_rapor(s)["komut"] == "export pg"
    assert sayilar(s) == {
        "staging": 4,
        "kitap": 2,
        "eklenen": 4,
        "ayni_kalan": 0,
        "guncellenen": 0,
        "metin_degisti": 0,
        "atlanan_onayli": 0,
        "atlanan_metin_degisti": 0,
        "tr_stem_dolan": 0,
        "kaynak_eklenen": 1,
        "kaynak_guncellenen": 0,
        "kaynak_degismeyen": 0,
    }
    assert anc  # anchor calistirmasi kullanildi


def test_copy_satirlari_sutun_sirasiyla_ve_dosya_sirasiyla(tmp_path: Path) -> None:
    s = senaryo_kur(tmp_path)
    zincir_kur(s)
    db = SahteBaglanti()
    assert calistir(s, db) == 0
    (sorgu, _) = db.kopyalar[0]
    sutunlar = re.search(r"\((.*)\)", sorgu)
    assert sutunlar is not None
    adlar = [a.strip() for a in sutunlar.group(1).split(",")]
    assert adlar == [
        "sira", "anchor", "role", "parent_path", "ord", "metin", "marks", "sentences", "attrs",
        "content_hash", "tr_narrow", "tr_wide", "tr_stem", "ar_norm", "data_version",
        "provenance", "source_id",
    ]  # fmt: skip
    satirlar = db.kopya_satirlari()
    assert [r[0] for r in satirlar] == [1, 2, 3, 4]  # sira: dosya sirasi
    assert all(len(r) == len(adlar) for r in satirlar)
    baslik, govde, _, ota = satirlar
    assert baslik[1] == f"rn:{KITAP}:soz-1:p1" and baslik[2] == "baslik"
    assert baslik[3] == f"rn:{KITAP}:soz-1" and baslik[7] == []  # baslikta cumle yok
    assert govde[2] == "govde" and govde[5] == "Deneme paragrafi 2. Ikinci cumle 2."
    assert govde[7] == [Range(0, 19, "[)"), Range(20, 35, "[)")]  # kod noktasi, yari acik
    assert govde[9] == content_hash(str(govde[5]))
    assert govde[10:13] == ("deneme 2", "deneme 2", "deneme 2")
    assert govde[16] == KAYNAK
    # Osmanlica kitap: yalniz ar_norm, tr_* NULL
    assert ota[10:13] == (None, None, None) and ota[13] == "deneme 1"
    # NUL ve sayac disinda hat metni donusturmez: metin staged ile bayt bayt ayni
    assert [r[5] for r in satirlar] == [str(k["text"]) for k in varsayilan_satirlar()]


def test_source_satiri_ilk_yuklemede_notlar_ve_baski_bilgisi_ile(tmp_path: Path) -> None:
    s = senaryo_kur(tmp_path)
    zincir_kur(s)
    db = SahteBaglanti()
    assert calistir(s, db) == 0
    (kaynak_ekle,) = db.sorgular("INSERT INTO icerik.source")
    metin, params = kaynak_ekle
    assert isinstance(params, dict)
    assert params["slug"] == KAYNAK and params["tur"] == "risale"
    assert params["surum"] == "deneme-1.0" and params["notlar"] == "Deneme notu"
    assert params["baski_bilgisi"] is not None
    # iki ham dosya: tek dosya varsayimi yok, alinma tarihi ve ozet NULL
    assert params["alinma_tarihi"] is None and params["dosya_sha256"] is None
    assert "notlar" in metin and "baski_bilgisi" in metin


def test_source_varsa_yalniz_betimleyici_alan_guncellenir(tmp_path: Path) -> None:
    s = senaryo_kur(tmp_path)
    zincir_kur(s)
    kayit = {
        "baslik": "Deneme Risale kaynagi",
        "surum": "eski-surum",
        "kaynak_url": "https://deneme.invalid/",
        "atif_metni": "Deneme atif metni.",
        "atif_url": None,
        "notice_text": None,
        "alinma_tarihi": None,
        "dosya_sha256": None,
    }
    db = SahteBaglanti()

    # dict_row yerine duz sozluk: sahte imlec satiri sozluk olarak dondurur
    class DictImlec(SahteImlec):
        def fetchone(self) -> object:
            return dict(kayit)

    db.cursor = lambda **kw: DictImlec(db)  # type: ignore[method-assign,assignment]
    assert calistir(s, db) == 0
    assert db.sorgular("INSERT INTO icerik.source") == []
    (guncelle,) = db.sorgular("UPDATE icerik.source SET")
    metin, params = guncelle
    assert '"surum" = %(surum)s' in metin
    assert "notlar" not in metin and "baski_bilgisi" not in metin and "yazar" not in metin
    assert isinstance(params, dict) and params["surum"] == "deneme-1.0"
    assert sayilar(s)["kaynak_guncellenen"] == 1


def test_surum_yoksa_cikis_2(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    s = senaryo_kur(tmp_path, surum=None)
    zincir_kur(s)
    db = SahteBaglanti()
    capsys.readouterr()
    assert calistir(s, db) == 2
    assert "surum cozulemedi" in capsys.readouterr().err
    assert db.islemler[0].durum == "geri_alindi"
    assert db.sorgular("INSERT INTO icerik.unit") == []


def test_danisma_kilidi_alinir_ilk_ifadelerden_biridir(tmp_path: Path) -> None:
    s = senaryo_kur(tmp_path)
    zincir_kur(s)
    db = SahteBaglanti()
    assert calistir(s, db) == 0
    ilk = db.islemler[0].sorgular[0][0]
    assert "pg_advisory_xact_lock(hashtext('mutalaa:'" in ilk
    assert db.islemler[0].sorgular[0][1] == (KAYNAK,)


# --- guncelleme ve koruma kurallari --------------------------------------------------------


def _set_sutunlari(sorgu: str) -> list[str]:
    govde = sorgu.split(" SET ", 1)[1].split(" FROM ", 1)[0]
    return [parca.split("=")[0].strip() for parca in re.split(r",\s*(?![^()]*\))", govde)]


def test_guncelleme_yalniz_turetilmis_sutunlar_ve_yalniz_taslak() -> None:
    sutunlar = _set_sutunlari(pg_risale.UPDATE_UNIT)
    assert sorted(sutunlar) == sorted(
        [
            "parent_path", "ord", "marks", "sentences", "ar_norm", "tr_narrow", "tr_wide",
            "tr_stem", "provenance", "data_version", "run_id", "updated_at",
        ]
    )  # fmt: skip
    for yasak in ("metin", "content_hash", "role", "attrs", "rev", "status", "successors",
                  "metin_durumu", "source_id", "anchor"):  # fmt: skip
        assert yasak not in sutunlar
    kosul = pg_risale.UPDATE_UNIT.split(" WHERE ", 1)[1]
    assert "u.metin_durumu = 'taslak'" in kosul
    assert "u.content_hash = s.content_hash" in kosul and "u.metin = s.metin" in kosul
    assert "u.source_id = s.source_id" in kosul
    assert "IS DISTINCT FROM" in kosul  # degismeyen satir yazilmaz
    assert "onayli" not in pg_risale.UPDATE_UNIT and "red" not in pg_risale.UPDATE_UNIT.split()


def test_ekleme_yalniz_yeni_capa_ve_taslak_etkin() -> None:
    assert "NOT EXISTS" in pg_risale.INSERT_UNIT and "u.anchor = s.anchor" in pg_risale.INSERT_UNIT
    assert "ON CONFLICT" not in pg_risale.INSERT_UNIT  # upsert yok: var olan satir hic ezilmez
    assert "'taslak'" in pg_risale.INSERT_UNIT and "status" not in pg_risale.INSERT_UNIT
    assert "ayah_range" not in pg_risale.INSERT_UNIT  # Risale birimi aya bagli degil


def test_ikinci_kosu_ayni_kalan_guncellenen_ve_rapor(tmp_path: Path) -> None:
    s = senaryo_kur(tmp_path)
    zincir_kur(s)
    db = SahteBaglanti(
        esle(
            ("count(*) FILTER", SahteSonuc([(0, 0, 0)])),
            ("INSERT INTO icerik.unit", SahteSonuc(rowcount=0)),
            ("UPDATE icerik.unit u SET", SahteSonuc(rowcount=1)),
        )
    )
    assert calistir(s, db) == 0
    assert sayilar(s)["eklenen"] == 0
    assert sayilar(s)["guncellenen"] == 1
    assert sayilar(s)["ayni_kalan"] == 3


def test_metin_degisti_hata_degil_sayilir_ve_satir_degismez(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    s = senaryo_kur(tmp_path)
    zincir_kur(s)
    db = SahteBaglanti(
        esle(
            ("count(*) FILTER", SahteSonuc([(2, 1, 1)])),
            (
                "u.metin_durumu = 'taslak' AND (u.content_hash <> s.content_hash",
                SahteSonuc([("rn:deneme-kitap:soz-1:p2",), ("rn:deneme-kitap:soz-1:p3",)]),
            ),
            ("INSERT INTO icerik.unit", SahteSonuc(rowcount=0)),
            ("UPDATE icerik.unit u SET", SahteSonuc(rowcount=0)),
        )
    )
    capsys.readouterr()
    assert calistir(s, db) == 0  # yukleme hatasi degil
    rapor = son_rapor(s)
    assert sayilar(s)["metin_degisti"] == 2
    assert sayilar(s)["atlanan_onayli"] == 1
    assert sayilar(s)["atlanan_metin_degisti"] == 1
    assert sayilar(s)["ayni_kalan"] == 1
    uyarilar = " ".join(str(u) for u in rapor.get("uyarilar", []))
    assert "degistirilmedi" in uyarilar and "rn:deneme-kitap:soz-1:p2" in uyarilar
    assert "Deneme paragrafi" not in uyarilar  # uyari metin tasimaz
    # metin ve content_hash SET listesinde yok: hicbir yazma ifadesi bunlara dokunmaz
    for metin_, _ in db.sorgular("UPDATE icerik.unit u SET"):
        assert "metin =" not in _set_sutunlari(metin_)


def test_baska_kaynaktaki_capa_cikis_2_ve_geri_alinir(tmp_path: Path) -> None:
    s = senaryo_kur(tmp_path)
    zincir_kur(s)
    db = SahteBaglanti(
        esle(("WHERE u.source_id <> s.source_id", SahteSonuc([("rn:deneme-kitap:soz-1:p2",)])))
    )
    assert calistir(s, db) == 2
    assert db.islemler[0].durum == "geri_alindi"
    assert db.sorgular("INSERT INTO icerik.unit") == []


def test_onceki_yuklemedeki_capa_stagedde_yoksa_cikis_1_ve_geri_alinir(tmp_path: Path) -> None:
    s = senaryo_kur(tmp_path)
    zincir_kur(s)
    db = SahteBaglanti(
        esle(
            (
                "NOT EXISTS (SELECT 1 FROM pg_temp.staging_risale",
                SahteSonuc([("rn:deneme-kitap:p9",)]),
            )
        )
    )
    assert calistir(s, db) == 1
    assert db.islemler[0].durum == "geri_alindi"
    assert db.sorgular("INSERT INTO icerik.unit") == []


def test_sql_hatasi_butun_islemi_geri_alir_basarisiz_satiri_yazilir(tmp_path: Path) -> None:
    s = senaryo_kur(tmp_path)
    zincir_kur(s)
    db = SahteBaglanti(hata=("UPDATE icerik.unit u SET", psycopg.errors.DeadlockDetected("x")))
    assert calistir(s, db) == 2
    assert [i.durum for i in db.islemler] == ["geri_alindi", "onaylandi"]
    ana, basarisiz = db.islemler
    assert any("INSERT INTO icerik.unit" in m for m, _ in ana.sorgular)  # ekleme de geri alindi
    assert [m for m, _ in basarisiz.sorgular if "INSERT INTO icerik.pipeline_run" in m]
    assert not [m for m, _ in basarisiz.sorgular if "icerik.unit" in m]


def test_tr_stem_bos_turkce_taslak_birimde_metinden_hesaplanir(tmp_path: Path) -> None:
    s = senaryo_kur(tmp_path)
    zincir_kur(s)
    metin = "Deneme paragrafi 7. Ikinci cumle."
    db = SahteBaglanti(
        esle(("tr_stem IS NULL AND attrs", SahteSonuc([("rn:deneme-kitap:soz-1:p7", metin)])))
    )
    assert calistir(s, db) == 0
    (sorgu, satirlar) = db.coklu[0]
    assert "SET tr_stem" in sorgu and "tr_stem IS NULL" in sorgu
    assert "metin_durumu = 'taslak'" in sorgu
    assert satirlar == [(tr_stem(metin), "rn:deneme-kitap:soz-1:p7")]
    assert sayilar(s)["tr_stem_dolan"] == 1
    secim, _ = db.sorgular("tr_stem IS NULL AND attrs")[0]
    assert "attrs ->> 'dil' = 'tr'" in secim and "metin_durumu = 'taslak'" in secim


def test_parti_parti_copy_tek_islemde(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    s = senaryo_kur(tmp_path)
    satirlar = [satir(n) for n in range(1, 6)]
    zincir_kur(s, satirlar)
    monkeypatch.setattr(pg_risale, "PARTI", 2)
    db = SahteBaglanti()
    assert calistir(s, db) == 0
    assert [len(parti) for _, parti in db.kopyalar] == [2, 2, 1]
    assert [r[0] for r in db.kopya_satirlari()] == [1, 2, 3, 4, 5]
    assert [i.durum for i in db.islemler] == ["onaylandi"]  # partiler ayri islem degil


def test_dry_run_gercek_yazim_akisini_calistirir_ve_geri_alir(tmp_path: Path) -> None:
    """`--dry-run` veritabanina BAGLANIR; tum yazim ifadelerini calistirip islemi geri alir."""
    s = senaryo_kur(tmp_path)
    zincir_kur(s)
    sayac = {"baglanti": 0}
    db = SahteBaglanti(esle(("INSERT INTO icerik.unit", SahteSonuc(rowcount=4))))

    def fabrika() -> psycopg.Connection:
        sayac["baglanti"] += 1
        return db  # type: ignore[return-value]

    assert calistir(s, fabrika, dry_run=True) == 0
    assert sayac["baglanti"] == 1
    assert [i.durum for i in db.islemler] == ["geri_alindi"]
    assert db.sorgular("INSERT INTO icerik.unit") and db.kopyalar  # yazim ifadeleri calisti
    assert sayilar(s)["eklenen"] == 4  # sayac gercek, ama hicbir sey kalici degil


# --- dosya onkosullari: baglanti acilmaz ---------------------------------------------------


def test_diyanet_kaynagi_export_pg_ile_reddedilir_cikis_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    s = senaryo_kur(tmp_path)
    capsys.readouterr()
    sonuc = calistir(s, source=KAYNAK_DIYANET)  # baglanti acilirsa BaglantiAcildi firlar
    hata = capsys.readouterr().err
    assert sonuc == 2
    assert "karsilastirma verisi" in hata and KAYNAK_RNK in hata
    assert hata.isascii()


def test_diyanet_reddi_pg_hazirla_yolunda_da_gecerli(tmp_path: Path) -> None:
    s = senaryo_kur(tmp_path)
    ctx = ctx_kur(tmp_path, s.kok, adim="export", kaynaklar=[KAYNAK_DIYANET])
    with pytest.raises(GirdiHatasi, match="karsilastirma verisi"):
        pg.hazirla(ctx, KAYNAK_DIYANET, None, ())


def test_export_pg_kayit_tablosu_rnk_var_diyanet_yok() -> None:
    assert pg.EK_KAYNAKLAR[KAYNAK_RNK] == ()
    assert KAYNAK_DIYANET not in pg.EK_KAYNAKLAR


def test_cli_diyanet_cikis_2(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    kok = kok_kur(tmp_path)
    monkeypatch.setenv("MUTALAA_VERI_KOK", str(tmp_path / "data"))
    sonuc = runner.invoke(cli.app, ["export", "pg", "--source", KAYNAK_DIYANET, "--kok", str(kok)])
    assert sonuc.exit_code == 2, sonuc.stderr
    assert "karsilastirma verisi" in sonuc.stderr


def test_cli_yardim_calisir(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FORCE_COLOR", "1")
    sonuc = runner.invoke(cli.app, ["export", "pg", "--help"])
    assert sonuc.exit_code == 0, sonuc.stderr
    cikti = ansisiz(sonuc.stdout)
    for secenek in ("--source", "--run", "--dry-run", "--force"):
        assert secenek in cikti


def test_qa_kapilari_dort_kapi_gerektirir() -> None:
    assert qa.kaynak_kapilari(KAYNAK_RNK) == ("G-KAY", "G-BUT", "G-CAP", "G-NOR")


def test_qa_raporu_yoksa_cikis_1(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    s = senaryo_kur(tmp_path)
    zincir_kur(s, qa_yaz=False)
    hata_ile(s, 1, "QA raporu yok", capsys)


@pytest.mark.parametrize("kapi", KAPILAR)
def test_kapi_kaldiysa_yukleme_yok_cikis_1(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], kapi: str
) -> None:
    s = senaryo_kur(tmp_path)
    zincir_kur(s, kapilar={**TUM_GECTI, kapi: "kaldi"})
    hata_ile(s, 1, kapi, capsys)  # Cagrilmaz: baglanti acilmadi


def test_g_cap_eksik_rapor_yetmez_cikis_1(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    s = senaryo_kur(tmp_path)
    zincir_kur(s, kapilar={"G-KAY": "gecti", "G-BUT": "gecti", "G-NOR": "gecti"})
    hata_ile(s, 1, "G-CAP", capsys)


def test_anchor_calistirmasi_yoksa_cikis_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    s = senaryo_kur(tmp_path)
    hata_ile(s, 2, "anchor", capsys)


def test_kayitsiz_kaynak_cikis_2(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    s = Senaryo(tmp_path, kok_kur(tmp_path), ayarlar_kur(tmp_path))
    hata_ile(s, 2, "kaynak", capsys)


def test_staged_content_hash_metinle_tutmuyorsa_cikis_1(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    s = senaryo_kur(tmp_path)
    satirlar = varsayilan_satirlar()
    satirlar[1]["content_hash"] = "0" * 64
    zincir_kur(s, satirlar)
    hata_ile(s, 1, "content_hash metinle tutmuyor", capsys)


def test_anchor_manifestindeki_ozet_tutmuyorsa_cikis_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    s = senaryo_kur(tmp_path)
    anc = zincir_kur(s)
    (s.veri / "staged" / KAYNAK / anc / "units.jsonl").write_bytes(b'{"x":1}\n')
    hata_ile(s, 2, "ciktilari saglam degil", capsys)


@pytest.mark.parametrize(
    ("degisim", "parca"),
    [
        ({"role": "siir"}, "role gecersiz"),
        ({"kind": "meal"}, "kind risale degil"),
        ({"metin_durumu": "onayli"}, "metin_durumu taslak degil"),
        ({"source_id": "baska"}, "source_id"),
        ({"ayah_lo": 1}, "ayah_lo/ayah_hi"),
        ({"ord": 0}, "ord gecersiz"),
        ({"parent_path": "rn:baska"}, "parent_path"),
        ({"text": ""}, "text bos"),
        ({"attrs": {"dil": "fr"}}, "attrs.dil"),
        ({"marks": [{"s": 0, "e": 9999, "t": "ar"}]}, "marks araligi"),
        ({"marks": [{"s": 0, "e": 2, "t": "satir"}]}, "marks bilinmeyen"),
        ({"sentences": [[0, 9999]]}, "sentences"),
        ({"sentences": [[5, 9], [3, 4]]}, "sentences"),
        ({"sentences": None}, "sentences liste degil"),
        ({"tr_stem": None}, "tr_stem gecersiz"),
        ({"content_hash": "ABC"}, "content_hash 64 haneli"),
        ({"data_version": ""}, "data_version"),
        ({"ar_norm": "a\x00b"}, "ar_norm gecersiz"),
        ({"provenance": {"x": "a\x00b"}}, "NUL"),
        ({"anchor": "rn:deneme-kitap:soz-1:p2:s1"}, "capa"),
    ],
)
def test_bozuk_satir_cikis_2_ve_baglanti_acilmaz(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], degisim: dict[str, object], parca: str
) -> None:
    s = senaryo_kur(tmp_path)
    satirlar = varsayilan_satirlar()
    satirlar[1].update(degisim)
    if "text" in degisim:  # ozet metinle tutarli kalsin: bos metin ayri denetimdir
        satirlar[1]["content_hash"] = content_hash(str(degisim["text"]))
    zincir_kur(s, satirlar)
    hata_ile(s, 2, parca, capsys)


def test_ota_kitapta_tr_anahtari_dolu_cikis_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    s = senaryo_kur(tmp_path)
    satirlar = varsayilan_satirlar()
    satirlar[3]["tr_wide"] = "deneme"
    zincir_kur(s, satirlar)
    hata_ile(s, 2, "tr_wide", capsys)


def test_alan_kumesi_ve_yinelenen_capa_cikis_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    s = senaryo_kur(tmp_path)
    satirlar = varsayilan_satirlar()
    del satirlar[2]["marks"]
    zincir_kur(s, satirlar)
    hata_ile(s, 2, "alan kumesi", capsys)
    s2 = senaryo_kur(tmp_path / "ikinci")
    ikili = [*varsayilan_satirlar(), satir(2)]
    zincir_kur(s2, ikili)
    hata_ile(s2, 2, "yinelenen anchor", capsys)


def test_units_bicim_hatalari_cikis_2(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    s = senaryo_kur(tmp_path)
    zincir_kur(s, units_bayt=b'{"anchor":')  # LF ile bitmiyor
    hata_ile(s, 2, "LF", capsys)


def test_ozet_hazirliktan_sonra_degisirse_yukleme_durur(tmp_path: Path) -> None:
    s = senaryo_kur(tmp_path)
    anc = zincir_kur(s)
    ctx = RunContext.olustur(
        s.ayarlar, komut="export pg", adim="export", depo_kok=s.kok, kaynaklar=(KAYNAK,),
        parametreler={"source": KAYNAK},
    )  # fmt: skip
    h = pg_risale.hazirla(ctx, KAYNAK, None, ())
    assert h.risale is not None and h.risale.satir_sayisi == 4 and h.risale.kitap_sayisi == 2
    assert h.satirlar == []  # dosya bellekte tutulmaz
    (s.veri / "staged" / KAYNAK / anc / "units.jsonl").write_bytes(b'{"x":1}\n')
    db = SahteBaglanti()
    with pytest.raises(GirdiHatasi, match="hazirliktan sonra degisti"):
        pg_risale.yukle(db, ctx, h)  # type: ignore[arg-type]
    assert db.kopyalar == []


def test_rapor_ve_gunluk_metin_tasimaz(tmp_path: Path) -> None:
    s = senaryo_kur(tmp_path)
    satirlar = varsayilan_satirlar()
    zincir_kur(s, satirlar)
    degisen_capa = "u.metin_durumu = 'taslak' AND (u.content_hash <> s.content_hash"
    db = SahteBaglanti(
        esle(
            ("count(*) FILTER", SahteSonuc([(1, 0, 0)])),
            (degisen_capa, SahteSonuc([("rn:deneme-kitap:soz-1:p2",)])),
        )
    )
    assert calistir(s, db) == 0
    kayitlar = b"".join(p.read_bytes() for p in (s.veri / "reports").glob("*.json"))
    kayitlar += b"".join(p.read_bytes() for p in (s.veri / "logs").glob("*.jsonl"))
    assert kayitlar and b"Deneme paragrafi" not in kayitlar and b"Ikinci cumle" not in kayitlar


def test_satir_alan_kumesi_adimin_ciktisiyla_ayni() -> None:
    """Sahte satir `adimlar.risale.ANCHOR_ALANLARI` ile birebir ayni alan kumesidir."""
    assert set(satir(1)) == set(ANCHOR_ALANLARI)


# --- gercek veritabani (yoksa atlanir) -----------------------------------------------------


def _zorunlu_veritabani(neden: str) -> None:
    if os.environ.get("MUTALAA_DEGISMEZLIK_ZORUNLU") == "1":
        pytest.fail(neden)
    pytest.skip(neden)


@pytest.fixture
def conn() -> Iterator[psycopg.Connection]:
    """Test veritabanina baglanir (dis islem, sonunda geri alinir); kalinti varsa atlar."""
    try:
        baglanti = baglan(Ayarlar(), test=True)
    except GirdiHatasi as hata:
        _zorunlu_veritabani(f"test veritabani yok: {hata}")
        return
    try:
        kalinti = baglanti.execute(
            "SELECT (SELECT count(*) FROM icerik.unit WHERE source_id = %s)"
            " + (SELECT count(*) FROM icerik.source WHERE slug = %s)",
            (KAYNAK, KAYNAK),
        ).fetchone()
        assert kalinti is not None
        if kalinti[0] != 0:
            baglanti.rollback()
            _zorunlu_veritabani(f"mutalaa_test icinde {KAYNAK} kalintisi var")
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
    tmp_path: Path, conn: psycopg.Connection
) -> None:
    s = senaryo_kur(tmp_path)
    zincir_kur(s)
    assert calistir(s, lambda: conn) == 0
    assert sayilar(s)["eklenen"] == 4
    assert _say(conn, "SELECT count(*) FROM icerik.unit WHERE source_id = %s", KAYNAK) == 4
    assert (
        _say(
            conn,
            "SELECT count(*) FROM icerik.unit WHERE source_id = %s AND metin_durumu = 'taslak'"
            " AND status = 'etkin' AND kind = 'risale'",
            KAYNAK,
        )
        == 4
    )
    assert calistir(s, lambda: conn) == 0
    ikinci = sayilar(s)
    assert (ikinci["eklenen"], ikinci["guncellenen"], ikinci["ayni_kalan"]) == (0, 0, 4)


@pytest.mark.veritabani
def test_gercek_onayli_satira_yazilmaz_taslak_metni_degismez(
    tmp_path: Path, conn: psycopg.Connection
) -> None:
    s = senaryo_kur(tmp_path)
    zincir_kur(s)
    assert calistir(s, lambda: conn) == 0
    conn.execute(
        "UPDATE icerik.unit SET metin_durumu = 'onayli' WHERE anchor = %s",
        (f"rn:{KITAP}:soz-1:p2",),
    )
    degisen = varsayilan_satirlar()
    degisen[1]["data_version"] = f"{KAYNAK}@deneme-2.0"  # onayli satir: yazilmamali
    degisen[2]["data_version"] = f"{KAYNAK}@deneme-2.0"  # taslak, ayni ozet: guncellenir
    degisen[3] = satir(1, kitap=KITAP_OTA, dil="ota", metin="Deneme baska metin.")  # metin farki
    zincir_kur(s, degisen)
    assert calistir(s, lambda: conn) == 0
    sayi = sayilar(s)
    assert (sayi["guncellenen"], sayi["atlanan_onayli"], sayi["metin_degisti"]) == (1, 1, 1)
    ana = conn.execute(
        "SELECT anchor, data_version, metin FROM icerik.unit WHERE source_id = %s ORDER BY anchor",
        (KAYNAK,),
    ).fetchall()
    surum = {r[0]: r[1] for r in ana}
    assert surum[f"rn:{KITAP}:soz-1:p2"].endswith("deneme-1.0")
    assert surum[f"rn:{KITAP}:soz-1:p3"].endswith("deneme-2.0")
    metinler = {r[0]: r[2] for r in ana}
    assert metinler[f"rn:{KITAP_OTA}:soz-1:p1"] == "Deneme paragrafi 1. Ikinci cumle 1."
