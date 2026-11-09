"""Degismezlik testleri 1-4 (A10.6): Tanzil metni hicbir adimda degismez (K-26, K-39).

Iki katman vardir; hepsi `degismezlik` isaretini tasir (`pytest -m degismezlik`):

* FIKSTUR katmani her ortamda kosar (CI dahil): `tests/fixtures/tanzil` parcalari (dosyadan
  betikle kesilmis 40 ayet + tam bildirim) gercek komut islevleriyle ingest -> normalize -> anchor
  zincirinden gecer; sonuc kaynak parcayla bayt bayt karsilastirilir. Kilit denetimi ile TOML
  kaydi arasindaki `sha256(notice_text) == bildirim_sha256` esitligi de burada, veri istemez.
* GERCEK VERI katmani `data/` altindaki tam dosyalarla kosar; veri yoksa atlanir. Atlanmasi
  istenmeyen kosularda (`scripts/nightly.ps1`, CI `database` isi) `MUTALAA_DEGISMEZLIK_ZORUNLU=1`
  atlamayi basarisizliga cevirir. PostgreSQL yarisi (test adinda `postgresql`) veritabani
  baglantisi ve yuklenmis birim ister; veritabani olmayan kosuda `-k "not postgresql"` ile
  disarida birakilir.

Testler 5-8'in sahibi bu dosya degildir (5 reader-core A24, 6 core paketi A13, 7 sayfa esleme A11,
8 terfide icerik ozeti A13); sahipleri A10 asama dosyasi ve ilerleme notundadir.

`conftest.py` MUTALAA_* degiskenlerini testlerden siler; gercek koku ve veritabanini gostermek
icin bu modul degiskenleri toplama sirasinda (silinmeden once) okur. Hata iletileri yalniz
sayi, kisaltilmis ozet ve goreli yol tasir; metin yazilmaz.
"""

import hashlib
import json
import os
from collections.abc import Iterator
from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path
from typing import Any

import psycopg
import pytest
from tanzil_yardimci import (
    PARCA_AYET,
    PARCA_BILDIRIM_SATIR,
    PARCA_CAPALAR,
    VARYANTLAR,
    parca_oku,
)
from zincir_yardimci import Zincir, zincir_hazirla

from mutalaa_pipeline import lineage, staged
from mutalaa_pipeline.adimlar.normalize_tanzil import EK_KAYNAK, KAYNAK
from mutalaa_pipeline.anchor.ayet_sayilari import AYET_SAYILARI
from mutalaa_pipeline.anchor.sayfa import SayfaHatasi, SayfaTablosu, sayfa_araligi, sayfa_bul
from mutalaa_pipeline.config import Ayarlar
from mutalaa_pipeline.db import baglan
from mutalaa_pipeline.export import ayet_sayilari
from mutalaa_pipeline.export.ortak import GirdiHatasi, depo_koku
from mutalaa_pipeline.ingest import tanzil, tanzil_bicim, tanzil_ust_veri
from mutalaa_pipeline.qa.dogrulama import qpc1_oku
from mutalaa_pipeline.sources import kayit

pytestmark = pytest.mark.degismezlik

PARCA_TABLOSU = (7, 33)  # parcanin sure sure ayet sayisi: 1:1-7 ve 2:1-33
KAYNAKLAR = {"uthmani": KAYNAK, "simple-clean": EK_KAYNAK}
# conftest MUTALAA_* degiskenlerini testten once siler: toplama sirasinda okunur.
_ORTAM_VERI_KOK = os.environ.get("MUTALAA_VERI_KOK")
_ORTAM_DB_URL = os.environ.get("MUTALAA_DB_URL")


def _yok(neden: str) -> None:
    """Veri/veritabani yoksa atlar; `MUTALAA_DEGISMEZLIK_ZORUNLU=1` ise basarisiz sayar."""
    if os.environ.get("MUTALAA_DEGISMEZLIK_ZORUNLU") == "1":
        pytest.fail(f"zorunlu degismezlik testi veri bulamadi: {neden}")
    pytest.skip(neden)


def _kisa(ozet: str) -> str:
    return ozet[:12]


def _sha(veri: bytes) -> str:
    return hashlib.sha256(veri).hexdigest()


def _kaynak_kaydi(depo: Path, varyant: str) -> kayit.Kaynak:
    sonuc = kayit.oku(kayit.kaynak_dizini(depo) / f"{KAYNAKLAR[varyant]}.toml")
    assert sonuc.hatalar == []
    assert sonuc.kaynak is not None
    return sonuc.kaynak


def _manifest_ayrinti(manifest: dict[str, object], ad: str) -> dict[str, object]:
    ayrintilar = manifest["ayrintilar"]
    assert isinstance(ayrintilar, dict)
    deger = ayrintilar[ad]
    assert isinstance(deger, dict)
    return deger


def _staged_ingest_yeniden_kur(klasor: Path, manifest: dict[str, object]) -> bytes:
    """Ingest cikisi (units.jsonl + notice.txt + duzen) -> Tanzil dosyasinin tum baytlari."""
    satirlar = staged.satirlari_oku((klasor / "units.jsonl").read_bytes(), "units.jsonl")
    birimler = [(s.metin("anchor"), s.metin("text")) for s in satirlar]
    bildirim = (klasor / "notice.txt").read_bytes()
    duzen = tanzil_bicim.Duzen.sozlukten(_manifest_ayrinti(manifest, "duzen"))
    return tanzil_bicim.yeniden_kur(birimler, bildirim, duzen)


def _anchor_birimleri(klasor: Path) -> list[staged.Satir]:
    return staged.satirlari_oku((klasor / "units.jsonl").read_bytes(), "units.jsonl")


def _icerik_ozeti_denetle(birimler: list[staged.Satir], ham: bytes) -> None:
    """Her birim: metin ham dosyanin bayt dilimi ve content_hash = sha256(metin) (test 4)."""
    for birim in birimler:
        capa = birim.metin("anchor")
        metin = birim.metin("text").encode("utf-8")
        bas, son = birim.nesne("provenance")["bayt"]  # type: ignore[misc]
        assert metin == ham[bas:son], f"{capa}: metin ham dosyanin dilimi degil"
        assert birim.metin("content_hash") == _sha(metin), f"{capa}: content_hash tutmuyor"


# --- FIKSTUR katmani (her ortamda kosar) -------------------------------------------------------


@pytest.fixture(scope="module")
def parca_zinciri(tmp_path_factory: pytest.TempPathFactory) -> Zincir:
    """Iki parcayla gercek islevlerle kosulmus ingest x2, normalize ve anchor."""
    z = zincir_hazirla(
        tmp_path_factory.mktemp("degismezlik"),
        {v: parca_oku(v) for v in VARYANTLAR},
        PARCA_TABLOSU,
    )
    z.hepsi()
    return z


def _son(z: Zincir, kaynak: str, adim: str) -> tuple[Path, dict[str, object]]:
    kayit_ = lineage.son_basarili(z.veri_kok / "staged" / kaynak, adim)
    assert kayit_ is not None, f"{kaynak}: {adim} calismasi yok"
    return kayit_[1], kayit_[2]


@pytest.mark.parametrize("varyant", VARYANTLAR)
def test_kayit_bildirimi_kilitteki_ozetle_ayni(varyant: str) -> None:
    """Test 1 (veri istemez): sha256(notice_text) == kilit bildirim_sha256; surum ve adres de."""
    k = _kaynak_kaydi(depo_koku(), varyant)
    girdi = tanzil.kilit_yukle()[varyant]
    assert k.notice_text is not None
    assert _sha(k.notice_text.encode("utf-8")) == girdi.bildirim_sha256
    assert k.surum == girdi.surum
    assert k.kaynak_url == girdi.url


@pytest.mark.parametrize("varyant", VARYANTLAR)
def test_parca_bildirim_dosyadaki_blokla_bayt_bayt_ayni(
    parca_zinciri: Zincir, varyant: str
) -> None:
    """notice.txt = parcadaki bildirim blogu (30 satir: 2 bos + 28 '#'); aynen saklanir."""
    klasor, _ = _son(parca_zinciri, KAYNAKLAR[varyant], "ingest")
    bildirim = (klasor / "notice.txt").read_bytes()
    ham = parca_oku(varyant)
    assert bildirim == tanzil_bicim.ayristir(ham, PARCA_TABLOSU).bildirim
    assert ham.endswith(bildirim)
    assert bildirim.count(b"\n") == PARCA_BILDIRIM_SATIR


@pytest.mark.parametrize("varyant", VARYANTLAR)
def test_parca_sure_ve_ayet_sayilari(parca_zinciri: Zincir, varyant: str) -> None:
    """Test 2 (parca): 2 sure, 40 ayet, sure sure sayim tablo ile ayni, capalar kesintisiz."""
    klasor, _ = _son(parca_zinciri, KAYNAKLAR[varyant], "ingest")
    capalar = [b.metin("anchor") for b in _anchor_birimleri(klasor)]
    assert capalar == PARCA_CAPALAR
    assert len(capalar) == PARCA_AYET
    sureler = [int(c.split(":")[1]) for c in capalar]
    assert [sureler.count(s) for s in sorted(set(sureler))] == list(PARCA_TABLOSU)


@pytest.mark.parametrize("varyant", VARYANTLAR)
def test_parca_staged_birimlerden_dosya_bayt_bayt_yeniden_kurulur(
    parca_zinciri: Zincir, varyant: str
) -> None:
    """Test 3 (staged, parca): units.jsonl + notice.txt -> parca; bildirim haric de ayni."""
    klasor, manifest = _son(parca_zinciri, KAYNAKLAR[varyant], "ingest")
    yeniden = _staged_ingest_yeniden_kur(klasor, manifest)
    ham = parca_oku(varyant)
    assert yeniden == ham
    bildirim = tanzil_bicim.ayristir(ham, PARCA_TABLOSU).bildirim
    assert yeniden[: -len(bildirim)] == ham[: -len(bildirim)]


def test_parca_anchor_birimleri_ham_dilimdir_ve_content_hash_tutar(parca_zinciri: Zincir) -> None:
    """Test 4 (parca): metin ham parcanin dilimi (NFC yok), content_hash = sha256(metin)."""
    klasor, _ = _son(parca_zinciri, KAYNAK, "anchor")
    birimler = _anchor_birimleri(klasor)
    assert len(birimler) == PARCA_AYET
    _icerik_ozeti_denetle(birimler, parca_oku("uthmani"))
    assert [b.sayi("ord") for b in birimler] == list(range(1, PARCA_AYET + 1))


def test_parca_uthmani_nfc_olmayan_ayet_degismeden_kalir(parca_zinciri: Zincir) -> None:
    """Kaynak NFC degilse birim de NFC degildir: NFC kanonik metne uygulanmaz."""
    import unicodedata

    klasor, _ = _son(parca_zinciri, KAYNAK, "anchor")
    nfc_degil = [
        b.metin("anchor")
        for b in _anchor_birimleri(klasor)
        if unicodedata.normalize("NFC", b.metin("text")) != b.metin("text")
    ]
    assert nfc_degil, "parcada NFC olmayan ayet beklenir (Uthmani)"


# --- GERCEK VERI katmani -----------------------------------------------------------------------


@dataclass(frozen=True)
class GercekVeri:
    depo: Path
    veri_kok: Path
    ayarlar: Ayarlar


@pytest.fixture(scope="module")
def gercek() -> GercekVeri:
    """Gercek `data/` kokunu verir; `data/gelen/tanzil` yoksa atlar (ZORUNLU ise basarisiz)."""
    kwargs: dict[str, Any] = {}
    if _ORTAM_VERI_KOK is not None:
        kwargs["veri_kok"] = Path(_ORTAM_VERI_KOK)
    if _ORTAM_DB_URL is not None:
        kwargs["db_url"] = _ORTAM_DB_URL
    ayarlar = Ayarlar(**kwargs)
    if not (ayarlar.veri_kok / "gelen" / "tanzil").is_dir():
        _yok("data/gelen/tanzil yok (gercek veri indirilmemis)")
    return GercekVeri(depo_koku(), ayarlar.veri_kok, ayarlar)


def _gelen_dosyasi(g: GercekVeri, varyant: str) -> tuple[Path, bytes]:
    tarih = tanzil.kilit_yukle()[varyant].alinma_tarihi
    yol = g.veri_kok / "gelen" / "tanzil" / tarih / tanzil.dosya_adi(varyant)
    if not yol.is_file():
        _yok(f"gelen dosyasi yok: gelen/tanzil/{tarih}/{tanzil.dosya_adi(varyant)}")
    return yol, yol.read_bytes()


def _gercek_son(g: GercekVeri, varyant: str, adim: str) -> tuple[Path, dict[str, object]]:
    bulunan = lineage.son_basarili(g.veri_kok / "staged" / KAYNAKLAR[varyant], adim)
    if bulunan is None:
        _yok(f"staged/{KAYNAKLAR[varyant]}: {adim} calismasi yok (hat calistirilmamis)")
        raise AssertionError  # _yok her zaman cikar
    return bulunan[1], bulunan[2]


@pytest.mark.parametrize("varyant", VARYANTLAR)
def test_gercek_dosya_ozeti_kilitle_ayni(gercek: GercekVeri, varyant: str) -> None:
    """Test 1: gelen ve raw dosyasinin SHA-256'si kilitle ayni; uc ozet de tutuyor."""
    girdi = tanzil.kilit_yukle()[varyant]
    yol, ham = _gelen_dosyasi(gercek, varyant)
    assert _sha(ham) == girdi.sha256
    assert len(ham) == girdi.boyut
    tanzil.kilit_denetle(girdi, ham)  # sha256, boyut, bicim, metin_sha256, bildirim_sha256
    # `sha256sum` bicimi: "<ozet> <kip><ad>" (kip: bosluk metin, * ikili).
    sums = (yol.parent / "SHA256SUMS").read_text(encoding="utf-8").split("\n")
    kayitlar = {s[66:]: s[:64] for s in sums if len(s) > 66}
    assert kayitlar[yol.name] == girdi.sha256
    raw = gercek.veri_kok / "raw" / KAYNAKLAR[varyant] / girdi.alinma_tarihi / yol.name
    if not raw.is_file():
        _yok(f"raw dosyasi yok: raw/{KAYNAKLAR[varyant]}/{girdi.alinma_tarihi}")
    assert _sha(raw.read_bytes()) == girdi.sha256


@pytest.mark.parametrize("varyant", VARYANTLAR)
def test_gercek_bildirim_kayit_dosya_ve_staged_ayni(gercek: GercekVeri, varyant: str) -> None:
    """Test 1: notice_text (TOML) == dosyadaki bildirim blogu == notice.txt; ozeti kilitte."""
    girdi = tanzil.kilit_yukle()[varyant]
    _, ham = _gelen_dosyasi(gercek, varyant)
    bildirim = tanzil_bicim.ayristir(ham).bildirim
    k = _kaynak_kaydi(gercek.depo, varyant)
    assert k.notice_text is not None
    assert k.notice_text.encode("utf-8") == bildirim
    assert _sha(bildirim) == girdi.bildirim_sha256
    klasor, _ = _gercek_son(gercek, varyant, "ingest")
    assert (klasor / "notice.txt").read_bytes() == bildirim


@pytest.mark.parametrize("varyant", VARYANTLAR)
def test_gercek_114_sure_6236_ayet(gercek: GercekVeri, varyant: str) -> None:
    """Test 2: 114 sure, 6.236 ayet; sure sure sayim ayet-sayilari.json'daki dizi ile ayni."""
    _, ham = _gelen_dosyasi(gercek, varyant)
    ayetler = tanzil_bicim.ayristir(ham).ayetler
    assert len(ayetler) == 6236
    sureler = [a.sure for a in ayetler]
    assert sorted(set(sureler)) == list(range(1, 115))
    assert [sureler.count(s) for s in range(1, 115)] == list(AYET_SAYILARI)
    klasor, _ = _gercek_son(gercek, varyant, "ingest")
    assert len(_anchor_birimleri(klasor)) == 6236


@pytest.mark.parametrize("varyant", VARYANTLAR)
def test_gercek_staged_birimlerden_dosya_bayt_bayt_yeniden_kurulur(
    gercek: GercekVeri, varyant: str
) -> None:
    """Test 3 (staged): units.jsonl + notice.txt gelen dosyayi bayt bayt yeniden uretir."""
    _, ham = _gelen_dosyasi(gercek, varyant)
    klasor, manifest = _gercek_son(gercek, varyant, "ingest")
    yeniden = _staged_ingest_yeniden_kur(klasor, manifest)
    assert _sha(yeniden) == _sha(ham)
    assert yeniden == ham
    bildirim = tanzil_bicim.ayristir(ham).bildirim
    assert yeniden[: -len(bildirim)] == ham[: -len(bildirim)]  # bildirim satirlari haric


def test_gercek_anchor_birimleri_ham_dilimdir_ve_content_hash_tutar(gercek: GercekVeri) -> None:
    """Test 4 (staged): 6.236 anchor birimi: metin ham dilim, content_hash = sha256(metin)."""
    _, ham = _gelen_dosyasi(gercek, "uthmani")
    klasor, _ = _gercek_son(gercek, "uthmani", "anchor")
    birimler = _anchor_birimleri(klasor)
    assert len(birimler) == 6236
    _icerik_ozeti_denetle(birimler, ham)


@pytest.fixture
def pg_baglanti(gercek: GercekVeri) -> Iterator[psycopg.Connection]:
    """Yalniz okuma baglantisi; baglanti kurulamazsa ya da birim yuklenmemisse atlar."""
    try:
        baglanti = baglan(gercek.ayarlar)
    except GirdiHatasi as hata:
        _yok(f"veritabani yok ({hata})")
        return
    try:
        baglanti.read_only = True
        sayi = baglanti.execute(
            "SELECT count(*) FROM icerik.unit WHERE source_id = %s", (KAYNAK,)
        ).fetchone()
        if sayi is None or sayi[0] == 0:
            _yok(f"icerik.unit icinde {KAYNAK} birimi yok (export pg calistirilmamis)")
        yield baglanti
    finally:
        baglanti.rollback()
        baglanti.close()


def test_gercek_postgresql_birimlerinden_dosya_bayt_bayt_yeniden_kurulur(
    gercek: GercekVeri, pg_baglanti: psycopg.Connection
) -> None:
    """Test 3 (PostgreSQL): birimler + source.notice_text gelen dosyayi bayt bayt yeniden uretir."""
    _, ham = _gelen_dosyasi(gercek, "uthmani")
    satirlar = pg_baglanti.execute(
        "SELECT anchor, metin FROM icerik.unit WHERE source_id = %s ORDER BY ord", (KAYNAK,)
    ).fetchall()
    assert len(satirlar) == 6236
    bildirim_satiri = pg_baglanti.execute(
        "SELECT notice_text FROM icerik.source WHERE slug = %s", (KAYNAK,)
    ).fetchone()
    assert bildirim_satiri is not None
    bildirim = bildirim_satiri[0].encode("utf-8")
    ayrisma = tanzil_bicim.ayristir(ham)
    yeniden = tanzil_bicim.yeniden_kur(satirlar, bildirim, ayrisma.duzen)
    assert yeniden == ham
    assert _sha(yeniden) == tanzil.kilit_yukle()["uthmani"].sha256
    ayet_baytlari = tanzil_bicim.yeniden_kur(satirlar, b"", ayrisma.duzen)
    assert ayet_baytlari == ayrisma.metin_baytlari  # bildirim haric


def test_gercek_postgresql_content_hash_metnin_sha256sidir(
    pg_baglanti: psycopg.Connection,
) -> None:
    """Test 4 (PostgreSQL): her birimin content_hash degeri metnin SHA-256'sidir."""
    sql_uyusmayan = pg_baglanti.execute(
        "SELECT count(*) FROM icerik.unit WHERE source_id = %s"
        " AND content_hash <> encode(sha256(convert_to(metin, 'UTF8')), 'hex')",
        (KAYNAK,),
    ).fetchone()
    assert sql_uyusmayan is not None
    assert sql_uyusmayan[0] == 0
    uyusmayan = [
        capa
        for capa, metin, ozet in pg_baglanti.execute(
            "SELECT anchor, metin, content_hash FROM icerik.unit WHERE source_id = %s", (KAYNAK,)
        )
        if _sha(metin.encode("utf-8")) != ozet
    ]
    assert uyusmayan == []


# --- Test 7 (A11.5): Medine 604 sayfa esleme ----------------------------------------------------
# Sayfa tablosu Tanzil `pages` grubundan uretilir; QPC1 duzeni yalniz dogrulayicidir. Hicbir
# sayi teste yazilmaz: sayfa sayisi kaynak XML'den, ayet ve kelime sayilari `ayet-sayilari.json`
# ile kelime dosyasindan gelir. Veri yoksa atlanir (ZORUNLU ise basarisiz).

UST_VERI_KAYNAGI = "tanzil-ust-veri"


@dataclass(frozen=True)
class SayfaVerisi:
    tablo: SayfaTablosu
    satirlar: list[dict[str, Any]]
    kelime_sayisi: dict[tuple[int, int], int]  # (sure, ayet) -> kelime sayisi (words.jsonl)
    xml_sayfa_sayisi: int


def _staged_json(klasor: Path, ad: str) -> list[dict[str, Any]]:
    return [json.loads(s) for s in (klasor / ad).read_bytes().splitlines()]


@pytest.fixture(scope="module")
def sayfa_verisi(gercek: GercekVeri) -> SayfaVerisi:
    ust = lineage.son_basarili(gercek.veri_kok / "staged" / UST_VERI_KAYNAGI, "anchor")
    kelime = lineage.son_basarili(gercek.veri_kok / "staged" / KAYNAK, "anchor")
    if ust is None or kelime is None:
        _yok("staged tanzil-ust-veri ya da tanzil-uthmani anchor calismasi yok (hat calismamis)")
        raise AssertionError
    satirlar = _staged_json(ust[1], "pages.jsonl")
    sayilar: dict[tuple[int, int], int] = {}
    for k in _staged_json(kelime[1], "words.jsonl"):
        anahtar = (k["surah"], k["ayah"])
        sayilar[anahtar] = max(sayilar.get(anahtar, 0), k["word"])
    xml = gercek.veri_kok / "gelen" / "tanzil-ust-veri"
    tarihler = sorted(p for p in xml.iterdir() if p.is_dir()) if xml.is_dir() else []
    if not tarihler:
        _yok("data/gelen/tanzil-ust-veri yok")
        raise AssertionError
    yapi = tanzil_ust_veri.yapi_ayristir((tarihler[-1] / "quran-data.xml").read_bytes())
    tablo = SayfaTablosu.kur((s["page"], s["start_anchor"], s["end_anchor"]) for s in satirlar)
    return SayfaVerisi(tablo, satirlar, sayilar, len(yapi["sayfa"]))


def _kelime_sirasi(v: SayfaVerisi, capa: str) -> int:
    """Kelimenin kitap icindeki 1 tabanli sirasi (kelime dosyasindaki ayet sirasina gore)."""
    sure, ayet, kelime = (int(x) for x in capa.split(":")[1:])
    onceki = sum(adet for (s, a), adet in v.kelime_sayisi.items() if (s, a) < (sure, ayet))
    return onceki + kelime


def test_sayfa_1_ilk_surenin_butun_ayetlerini_kapsar(sayfa_verisi: SayfaVerisi) -> None:
    """Test 7: 1. sayfa ilk surenin ilk ayetinden son ayetine kadardir (sure uzunlugu JSON'dan)."""
    v = sayfa_verisi
    ayet_sayisi = ayet_sayilari.json_oku(depo_koku()).sayilar[0]
    ilk, son = sayfa_araligi(v.tablo, 1)
    assert ilk == "q:1:1:1"
    assert son == f"q:1:{ayet_sayisi}:{v.kelime_sayisi[(1, ayet_sayisi)]}"
    assert all(sayfa_bul(v.tablo, f"q:1:{a}") == 1 for a in range(1, ayet_sayisi + 1))


def test_son_sayfa_son_surenin_son_ayetinin_son_kelimesiyle_biter(
    sayfa_verisi: SayfaVerisi,
) -> None:
    v = sayfa_verisi
    sayilar = ayet_sayilari.json_oku(depo_koku()).sayilar
    sure, ayet = len(sayilar), sayilar[-1]
    son_kelime = f"q:{sure}:{ayet}:{v.kelime_sayisi[(sure, ayet)]}"
    assert sayfa_araligi(v.tablo, len(v.tablo))[1] == son_kelime
    assert sayfa_bul(v.tablo, son_kelime) == len(v.tablo)


def test_sayfa_0_ve_son_sayfadan_sonrasi_gecersiz(sayfa_verisi: SayfaVerisi) -> None:
    tablo = sayfa_verisi.tablo
    for sayfa in (0, -1, len(tablo) + 1):
        with pytest.raises(SayfaHatasi):
            sayfa_araligi(tablo, sayfa)
    assert sayfa_araligi(tablo, len(tablo))


def test_sayfalar_1den_kesintisiz_kaynak_xml_ile_ayni_sayida(sayfa_verisi: SayfaVerisi) -> None:
    v = sayfa_verisi
    assert [s["page"] for s in v.satirlar] == list(range(1, len(v.satirlar) + 1))
    assert len(v.tablo) == len(v.satirlar) == v.xml_sayfa_sayisi


def test_sayfalar_arasinda_bosluk_ve_ortusme_yok(sayfa_verisi: SayfaVerisi) -> None:
    v = sayfa_verisi
    siralar = [
        (_kelime_sirasi(v, s["start_anchor"]), _kelime_sirasi(v, s["end_anchor"]))
        for s in v.satirlar
    ]
    assert siralar[0][0] == 1
    assert siralar[-1][1] == sum(v.kelime_sayisi.values())
    for (_, onceki_son), (sonraki_bas, _) in pairwise(siralar):
        assert sonraki_bas == onceki_son + 1
    assert all(bas <= son for bas, son in siralar)


def _ayet_sayfada(v: SayfaVerisi, sure: int, ayet: int) -> bool:
    try:
        sayfa_bul(v.tablo, f"q:{sure}:{ayet}")
        sayfa_bul(v.tablo, f"q:{sure}:{ayet}:{v.kelime_sayisi[(sure, ayet)]}")
    except SayfaHatasi:
        return False
    return True


def test_her_ayet_en_az_bir_sayfada(sayfa_verisi: SayfaVerisi) -> None:
    sayilar = ayet_sayilari.json_oku(depo_koku()).sayilar
    kapsanmayan = [
        f"q:{s}:{a}"
        for s, adet in enumerate(sayilar, start=1)
        for a in range(1, adet + 1)
        if not _ayet_sayfada(sayfa_verisi, s, a)
    ]
    assert kapsanmayan == []


def test_sayfa_baslangiclari_qpc1_duzeniyle_ayni(
    gercek: GercekVeri, sayfa_verisi: SayfaVerisi
) -> None:
    """Test 7: Tanzil `pages` ile QPC1 her sayfada ayni baslangic ve bitis kelimesini verir;
    hicbir sayfa ayet ortasinda baslamaz ya da bitmez (AS-10)."""
    qpc1 = qpc1_oku(gercek.veri_kok)
    if qpc1 is None:
        _yok("data/gelen/medine-604-duzen/<tarih>/mushaf/QPC1 yok (QPC1 duzeni indirilmemis)")
        raise AssertionError
    v = sayfa_verisi
    assert qpc1.sayfa_sayisi == len(v.tablo)
    for sayfa in range(1, len(v.tablo) + 1):
        ilk, son = sayfa_araligi(v.tablo, sayfa)
        assert qpc1.ilk[sayfa] == ilk.removeprefix("q:"), f"sayfa {sayfa}: baslangic"
        assert qpc1.son[sayfa] == son.removeprefix("q:"), f"sayfa {sayfa}: bitis"
        assert ilk.endswith(":1")  # sayfa ayet basinda baslar
        sure, ayet, kelime = (int(x) for x in son.split(":")[1:])
        assert kelime == v.kelime_sayisi[(sure, ayet)]  # ve ayet sonunda biter


def test_gercek_postgresql_page_map_staged_sayfalarla_ayni(
    sayfa_verisi: SayfaVerisi, pg_baglanti: psycopg.Connection
) -> None:
    """Test 7 (PostgreSQL): page_map sayfa satirlari staged tabloyla ayni, 1..N kesintisiz."""
    satirlar = pg_baglanti.execute(
        "SELECT page, start_anchor, end_anchor FROM icerik.page_map"
        " WHERE source_id = %s AND line IS NULL ORDER BY page",
        (UST_VERI_KAYNAGI,),
    ).fetchall()
    if not satirlar:
        _yok("icerik.page_map icinde tanzil-ust-veri satiri yok (export pg calistirilmamis)")
    beklenen = [(s["page"], s["start_anchor"], s["end_anchor"]) for s in sayfa_verisi.satirlar]
    assert satirlar == beklenen
    assert [s[0] for s in satirlar] == list(range(1, len(satirlar) + 1))
