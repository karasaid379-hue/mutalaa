"""`ingest.tanzil`: kilit, bagdastirici ve `mutalaa ingest tanzil` komutu (K-39).

Bagdastirici testleri gercek dosyalardan betikle kesilmis parcalarla kosar (`fixtures/tanzil`,
KAYNAK.txt); kilit her testte parcanin kendi baytlarindan hesaplanir. Komut testleri 6.236
satirlik SENTETIK "Deneme" dosyasi ve gecici kilit dosyasiyla kosar. Gercek kilit yalniz yapi
ve kaynak kaydi tutarliligi acisindan sinanir; gercek dosyayla karsilastirma data/gelen'li
degismezlik testlerindedir. Kur'an metni testlerde hafizadan yazilmaz.
"""

import dataclasses
import hashlib
import json
import os
import re
import shutil
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import pytest
from hat_yardimci import ctx_kur, depo_kur
from tanzil_yardimci import (
    PARCA_AYET,
    PARCA_CAPALAR,
    TARIH,
    VARYANTLAR,
    ayet_bitisi,
    gelen_yaz,
    kilit_kur,
    parca_oku,
    sentetik_bildirim,
    sentetik_tam,
)
from test_sources import alanlar_kur, kayit_yaz
from typer.testing import CliRunner, Result

from mutalaa_pipeline import cli, lineage, sources
from mutalaa_pipeline.enums import SourceKind
from mutalaa_pipeline.export import pg
from mutalaa_pipeline.export.ortak import GirdiHatasi, depo_koku
from mutalaa_pipeline.ingest import tanzil, tanzil_bicim
from mutalaa_pipeline.ingest.base import IngestSonucu, RawFile, run_ingest
from mutalaa_pipeline.logs import ILETI_EN_UZUN
from mutalaa_pipeline.runctx import RunContext
from mutalaa_pipeline.sources.kayit import Kaynak

runner = CliRunner()

GERCEK_DOSYA_OZETLERI = {  # A10.0 Tedarik tablosu: SHA-256 ve bayt sayisi
    "uthmani": ("6933e133dd56db778c801bf738848454e43648105a151e8d84d86a7cae39ec5f", 1396087),
    "simple-clean": ("054b3d9f79c0c2e44df7f9ddf42561797b3b5cb4fbdafbf2e99c805ccf1a6b49", 794313),
}


@pytest.fixture(params=VARYANTLAR)
def varyant(request: pytest.FixtureRequest) -> str:
    return str(request.param)


# --- yardimcilar -------------------------------------------------------------------------


@dataclass
class Kurulum:
    tmp: Path
    kok: Path
    veri_kok: Path
    varyant: str
    veri: bytes
    kilit: tanzil.KilitGirdisi

    @property
    def kaynak(self) -> str:
        return tanzil.kaynak_kimligi(self.varyant)

    @property
    def ad(self) -> str:
        return tanzil.dosya_adi(self.varyant)

    @property
    def ham_klasor(self) -> Path:
        return self.veri_kok / "raw" / self.kaynak

    @property
    def staged_klasor(self) -> Path:
        return self.veri_kok / "staged" / self.kaynak

    @property
    def gelen_yolu(self) -> Path:
        return self.veri_kok / "gelen" / "tanzil" / TARIH / self.ad


def kur(tmp_path: Path, varyant: str, *, veri: bytes | None = None) -> Kurulum:
    """Sahte depo kokunde kaynak kaydi + gelen dosyasi (parca) + parcanin kendi kilidi."""
    kok = depo_kur(tmp_path, tanzil.kaynak_kimligi(varyant))
    veri = veri if veri is not None else parca_oku(varyant)
    veri_kok = tmp_path / "data"
    gelen_yaz(veri_kok, varyant, veri)
    return Kurulum(tmp_path, kok, veri_kok, varyant, veri, kilit_kur(varyant, veri))


def kos(
    k: Kurulum,
    *,
    gelen_tarih: str | None = None,
    temiz_git: bool = True,
    **ctx_kw: Any,
) -> tuple[IngestSonucu, RunContext]:
    ctx = ctx_kur(
        k.tmp,
        k.kok,
        kaynaklar=[k.kaynak],
        temiz_git=temiz_git,
        parametreler={"variant": k.varyant},
        **ctx_kw,
    )
    bagdastirici = tanzil.TanzilBagdastirici(
        k.varyant, gelen_tarih=gelen_tarih, kilit=k.kilit, tam=False
    )
    return run_ingest(bagdastirici, ctx), ctx


def manifest_oku(sonuc: IngestSonucu) -> dict[str, Any]:
    assert sonuc.klasor is not None
    veri = json.loads((sonuc.klasor / "manifest.json").read_bytes().decode("utf-8"))
    assert isinstance(veri, dict)
    return veri


def ozet(yol: Path) -> str:
    return hashlib.sha256(yol.read_bytes()).hexdigest()


def altlar(klasor: Path) -> list[str]:
    return sorted(p.name for p in klasor.iterdir())


# --- iyi bicimli parca: ham kopya, staged ve manifest ------------------------------------


def test_birimler_staged_duzeni_ve_provenance(tmp_path: Path, varyant: str) -> None:
    k = kur(tmp_path, varyant)
    sonuc, ctx = kos(k)
    assert sonuc.atlandi is False
    assert sonuc.birim_sayisi == PARCA_AYET
    assert sonuc.klasor == k.staged_klasor / ctx.run_id
    assert sonuc.klasor is not None
    assert altlar(sonuc.klasor) == ["manifest.json", "notice.txt", "units.jsonl"]
    assert (sonuc.klasor / "notice.txt").read_bytes() == k.veri[ayet_bitisi(k.veri) :]

    ham = (k.ham_klasor / TARIH / k.ad).read_bytes()
    assert ham == k.veri
    satirlar = (sonuc.klasor / "units.jsonl").read_bytes().split(b"\n")
    assert satirlar[-1] == b""
    assert b"".join(satirlar).isascii()  # ASCII kacisli: editor NFC'si metni degistirmesin
    birimler = [json.loads(s) for s in satirlar[:-1]]
    assert [b["anchor"] for b in birimler] == PARCA_CAPALAR
    ham_satirlar = ham.split(b"\n")
    for no, b in enumerate(birimler, start=1):
        assert set(b) == {"anchor", "source_id", "text", "attrs", "provenance"}
        assert b["source_id"] == k.kaynak
        assert b["attrs"] == {}
        baslangic, bitis = b["provenance"]["bayt"]
        assert b["provenance"] == {
            "file": k.ad,
            "sha256": k.kilit.sha256,
            "line": no,
            "bayt": [baslangic, bitis],
            "steps": [],
        }
        # metin, ham dosyanin aynen dilimidir (NFC ve baska donusum yok)
        assert ham[baslangic:bitis] == b["text"].encode("utf-8")
        _, sure, ayet = b["anchor"].split(":")
        assert ham_satirlar[no - 1] == f"{sure}|{ayet}|".encode("ascii") + ham[baslangic:bitis]


def test_ham_kopya_ve_fetch_json(tmp_path: Path, varyant: str) -> None:
    k = kur(tmp_path, varyant)
    sonuc, ctx = kos(k)
    ham_klasor = k.ham_klasor / TARIH
    assert altlar(k.ham_klasor) == [TARIH]  # gecici klasor kalmadi
    assert altlar(ham_klasor) == ["fetch.json", k.ad]
    assert (ham_klasor / k.ad).read_bytes() == k.veri
    assert json.loads((ham_klasor / "fetch.json").read_bytes()) == {
        "kaynak": k.kaynak,
        "varyant": varyant,
        "dosya": k.ad,
        "url": "https://tanzil.net/download/",
        "secenekler": dict(tanzil.SECENEKLER),
        "surum": "1.1",
        "alinma_tarihi": TARIH,
        "boyut": len(k.veri),
        "sha256": k.kilit.sha256,
        "gelen_yol": f"gelen/tanzil/{TARIH}/{k.ad}",
    }
    assert k.gelen_yolu.read_bytes() == k.veri  # gelen dosyasina dokunulmaz
    manifest = manifest_oku(sonuc)
    assert [g["yol"] for g in manifest["girdiler"]] == [f"raw/{k.kaynak}/{TARIH}/{k.ad}"]
    assert manifest["girdiler"][0]["sha256"] == k.kilit.sha256
    assert ctx.sayilar["ham_yeni"] == 1
    assert ctx.sayilar["ham_boyut"] == len(k.veri)


def test_manifest_cikti_ozetleri_ve_satir_duzeni(tmp_path: Path, varyant: str) -> None:
    k = kur(tmp_path, varyant)
    sonuc, _ = kos(k)
    manifest = manifest_oku(sonuc)
    assert sonuc.klasor is not None
    ciktilar = {c["yol"].rsplit("/", 1)[1]: c for c in manifest["ciktilar"]}
    assert set(ciktilar) == {"notice.txt", "units.jsonl"}
    assert ciktilar["units.jsonl"]["satir"] == PARCA_AYET
    for ad, kayit in ciktilar.items():
        assert kayit["sha256"] == ozet(sonuc.klasor / ad)
    assert lineage.ciktilar_saglam(k.veri_kok, manifest)
    ayrisma = tanzil_bicim.ayristir(k.veri, tam=False)
    ayrintilar = manifest["ayrintilar"]
    assert ayrintilar == {
        "varyant": varyant,
        "surum": "1.1",
        "gelen_tarih": TARIH,
        "kilit": {
            "boyut": len(k.veri),
            "sha256": k.kilit.sha256,
            "metin_sha256": ayrisma.metin_sha256,
            "bildirim_sha256": ayrisma.bildirim_sha256,
        },
        "duzen": ayrisma.duzen.sozluk(),
    }
    assert tanzil_bicim.Duzen.sozlukten(ayrintilar["duzen"]) == ayrisma.duzen
    assert manifest["adim"] == "ingest"
    assert manifest["komut"] == "ingest deneme"  # hat_yardimci'nin sahte komut adi


def test_manifest_ayrintilari_parse_oncesi_bos(varyant: str) -> None:
    bagdastirici = tanzil.TanzilBagdastirici(varyant, kilit=kilit_kur(varyant, parca_oku(varyant)))
    assert bagdastirici.manifest_ayrintilari() == {}


def test_ciktilar_export_pg_sozlesmesine_uyar(tmp_path: Path, varyant: str) -> None:
    """`export pg` ingest cikisini su adlarla bekler: notice.txt ve raw/<kaynak>/<tarih>/."""
    k = kur(tmp_path, varyant)
    sonuc, _ = kos(k)
    assert sonuc.klasor is not None
    manifest = manifest_oku(sonuc)
    assert tanzil.NOTICE_ADI == pg.NOTICE_ADI
    assert pg.NOTICE_ADI == "notice.txt"
    assert pg.UNITS_ADI == "units.jsonl"
    assert manifest["adim"] == pg.INGEST_ADIMI
    # tek ham dosya: alinma tarihi raw klasor adindan, dosya ozeti girdi kaydindan cozulur
    ham = [
        {"yol": g["yol"], "sha256": g["sha256"]}
        for g in manifest["girdiler"]
        if g["yol"].startswith("raw/")
    ]
    assert pg._alinma(ham) == (date.fromisoformat(TARIH), k.kilit.sha256)
    # G-KAY bildirim denetimi: notice.txt baytlarinin kati UTF-8 cozumu notice_text ile ayni
    notice = (sonuc.klasor / "notice.txt").read_bytes().decode("utf-8")
    kayit = Kaynak(
        slug=k.kaynak,
        tur=SourceKind.KURAN_METNI,
        baslik="Deneme",
        atif_metni="Deneme",
        notice_text=notice,
    )
    zincir = pg.ZincirRun(sonuc.run_id, "ingest", k.kaynak, sonuc.klasor, manifest)
    assert pg._bildirim(zincir, kayit) == notice
    farkli = dataclasses.replace(
        kayit, notice_text=notice.rstrip("\n")
    )  # rstrip yok (K-39 madde 6)
    with pytest.raises(GirdiHatasi, match="notice_text ayni degil"):
        pg._bildirim(zincir, farkli)
    assert lineage.ciktilar_saglam(k.veri_kok, manifest)


# --- idempotentlik ve raw degismezligi ---------------------------------------------------


def test_ikinci_kosu_atlanir_force_ve_kirli_agac_atlamaz(tmp_path: Path, varyant: str) -> None:
    k = kur(tmp_path, varyant)
    ilk, ctx1 = kos(k)
    assert ilk.atlandi is False
    assert ctx1.sayilar["ham_yeni"] == 1

    ikinci, ctx2 = kos(k)
    assert ikinci.atlandi is True  # parmak izi ayni
    assert ikinci.klasor is None
    assert ikinci.onceki_run_id == ilk.run_id
    assert ctx2.sayilar["atlandi"] == 1
    assert ctx2.sayilar["ham_yeni"] == 0  # raw'a yeni kopya acilmadi
    assert len(altlar(k.staged_klasor)) == 1

    uc, _ = kos(k, force=True)
    assert uc.atlandi is False
    assert uc.klasor is not None
    assert ilk.klasor is not None
    for ad in ("units.jsonl", "notice.txt"):  # ayni girdi -> ayni staged ozetleri
        assert ozet(uc.klasor / ad) == ozet(ilk.klasor / ad)
    assert altlar(k.ham_klasor) == [TARIH]

    dort, _ = kos(k, temiz_git=False)  # kirli calisma agaci atlamayi kapatir
    assert dort.atlandi is False


def test_ayni_baytlar_baska_gelen_klasorunde_yeni_ham_kopya_acmaz(
    tmp_path: Path, varyant: str
) -> None:
    k = kur(tmp_path, varyant)
    kos(k)
    gelen_yaz(k.veri_kok, varyant, k.veri, tarih="2026-11-03")
    sonuc, ctx = kos(k)  # varsayilan: en yeni gelen klasoru (2026-11-03)
    assert sonuc.atlandi is True
    assert ctx.sayilar["ham_yeni"] == 0
    assert altlar(k.ham_klasor) == [TARIH]  # raw'da tek kopya, en eski tarihle


def test_ayni_gun_farkli_icerikli_ham_klasor_cakisir(tmp_path: Path, varyant: str) -> None:
    k = kur(tmp_path, varyant)
    onceki = k.ham_klasor / TARIH
    onceki.mkdir(parents=True)
    (onceki / k.ad).write_bytes(b"Deneme eski icerik\n")
    with pytest.raises(GirdiHatasi, match="data/raw degismez"):
        kos(k)
    assert (onceki / k.ad).read_bytes() == b"Deneme eski icerik\n"  # raw degismedi
    assert altlar(k.ham_klasor) == [TARIH]  # gecici klasor kalmadi
    assert not (k.veri_kok / "staged").exists()


def test_raw_yazilamazsa_gecici_klasor_kalmaz(tmp_path: Path, varyant: str) -> None:
    k = kur(tmp_path, varyant)
    k.ham_klasor.parent.mkdir(parents=True)
    k.ham_klasor.write_bytes(b"")  # raw/<kaynak> bir DOSYA: klasor acilamaz
    with pytest.raises(GirdiHatasi, match="yazilamadi"):
        kos(k)
    assert not (k.veri_kok / "staged").exists()


def test_es_zamanli_kosu_ayni_baytlari_almissa_hata_vermez(
    tmp_path: Path, varyant: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Rename yarisi: baska bir kosu ayni baytlari az once raw'a almissa onun kopyasi kullanilir."""
    k = kur(tmp_path, varyant)

    def yarisli_rename(self: Path, hedef: str | Path) -> Path:
        klasor = Path(hedef)
        klasor.mkdir(parents=True)
        (klasor / k.ad).write_bytes(k.veri)
        raise FileExistsError

    monkeypatch.setattr(Path, "rename", yarisli_rename)
    sonuc, ctx = kos(k)
    assert sonuc.birim_sayisi == PARCA_AYET
    assert ctx.sayilar["ham_yeni"] == 0
    assert altlar(k.ham_klasor) == [TARIH]  # gecici klasor temizlendi
    assert (k.ham_klasor / TARIH / k.ad).read_bytes() == k.veri


def test_gecici_izin_hatasinda_yeniden_adlandirma_tekrarlanir(
    tmp_path: Path, varyant: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """OneDrive/antivirus klasoru tararken rename PermissionError verebilir (windows-sorun)."""
    k = kur(tmp_path, varyant)
    gercek_rename = Path.rename
    cagrilar: list[Path] = []

    def kilitli_rename(self: Path, hedef: str | Path) -> Path:
        cagrilar.append(self)
        if len(cagrilar) <= 2:
            raise PermissionError
        return gercek_rename(self, hedef)

    monkeypatch.setattr(Path, "rename", kilitli_rename)
    monkeypatch.setattr(tanzil.time, "sleep", lambda _saniye: None)
    sonuc, ctx = kos(k)
    assert len(cagrilar) == 3
    assert sonuc.birim_sayisi == PARCA_AYET
    assert ctx.sayilar["ham_yeni"] == 1
    assert altlar(k.ham_klasor) == [TARIH]
    assert (k.ham_klasor / TARIH / k.ad).read_bytes() == k.veri


def test_kalici_izin_hatasi_sinirli_denemeden_sonra_cikis_2(
    tmp_path: Path, varyant: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    k = kur(tmp_path, varyant)
    cagrilar: list[Path] = []

    def kilitli_rename(self: Path, hedef: str | Path) -> Path:
        cagrilar.append(self)
        raise PermissionError

    monkeypatch.setattr(Path, "rename", kilitli_rename)
    monkeypatch.setattr(tanzil.time, "sleep", lambda _saniye: None)
    with pytest.raises(GirdiHatasi, match="yazilamadi"):
        kos(k)
    assert len(cagrilar) == tanzil.YENIDEN_ADLANDIRMA_DENEMESI
    assert altlar(k.ham_klasor) == []  # gecici klasor temizlendi, raw'da yarim kopya yok
    assert not (k.veri_kok / "staged").exists()


def test_ham_kopya_yeniden_adlandirmadan_once_diske_esitlenir(
    tmp_path: Path, varyant: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ham dosya ve fetch.json, klasor gorunur olmadan once `fsync` ile diske esitlenir.

    Esitleme yoksa guc kesintisi raw altinda sifir uzunluklu dosya birakabilir; sonraki kosu
    `data/raw degismez` hatasiyla durur ve elle temizlik gerekir.
    """
    k = kur(tmp_path, varyant)
    olaylar: list[str] = []
    gercek_fsync, gercek_rename = os.fsync, Path.rename

    def fsync(fd: int) -> None:
        olaylar.append("fsync")
        gercek_fsync(fd)

    def rename(self: Path, hedef: str | Path) -> Path:
        olaylar.append("rename")
        return gercek_rename(self, hedef)

    monkeypatch.setattr(os, "fsync", fsync)
    monkeypatch.setattr(Path, "rename", rename)
    kos(k)
    assert olaylar.count("rename") == 1
    assert olaylar[: olaylar.index("rename")] == ["fsync", "fsync"]  # ham dosya, fetch.json
    assert (k.ham_klasor / TARIH / k.ad).read_bytes() == k.veri


def test_dry_run_da_ham_cakismasini_bildirir(tmp_path: Path, varyant: str) -> None:
    """Dry-run gercek kosunun duracagi yerde durur; yanlis guvence vermez."""
    k = kur(tmp_path, varyant)
    onceki = k.ham_klasor / TARIH
    onceki.mkdir(parents=True)
    (onceki / k.ad).write_bytes(b"Deneme eski icerik\n")
    with pytest.raises(GirdiHatasi, match="data/raw degismez"):
        kos(k, dry_run=True)
    assert (onceki / k.ad).read_bytes() == b"Deneme eski icerik\n"


def test_dry_run_raw_ve_staged_yazmaz(tmp_path: Path, varyant: str) -> None:
    k = kur(tmp_path, varyant)
    sonuc, ctx = kos(k, dry_run=True)
    assert sonuc.birim_sayisi == PARCA_AYET
    assert sonuc.klasor is None
    assert not (k.veri_kok / "raw").exists()
    assert not (k.veri_kok / "staged").exists()
    assert ctx.sayilar["ham_yeni"] == 0
    # gercek kosudan sonra dry-run mevcut ham kopyayi kullanir, hicbir sey eklemez
    kos(k)
    onceki = (altlar(k.ham_klasor), altlar(k.staged_klasor))
    sonuc2, _ = kos(k, dry_run=True, force=True)
    assert sonuc2.klasor is None
    assert (altlar(k.ham_klasor), altlar(k.staged_klasor)) == onceki


# --- kilit sinamasi ----------------------------------------------------------------------


def bozuk_kopyalar(veri: bytes) -> dict[str, tuple[bytes, str]]:
    """Gelen dosyasinin bozulmus kopyalari: kimlik -> (bayt, iletide beklenen fark)."""
    # tek baytlik degisiklikler
    uc_bayt = next(
        i for i in range(4, len(veri)) if 0xC2 <= veri[i - 1] <= 0xDF and 0x80 <= veri[i] < 0xBF
    )
    ayet_bayti = bytearray(veri)
    ayet_bayti[uc_bayt] += 1  # gecerli UTF-8 kalir, baska bir harf olur
    gecersiz_utf8 = bytearray(veri)
    gecersiz_utf8[uc_bayt] = 0xFF
    bildirim = veri.replace(b"PLEASE", b"PLEASF", 1)
    fark_bildirim = "fark yalniz bildirim blogunda (ayet satirlari kilitle ayni)"
    fark_ayet = "fark ayet satirlarinda (bildirim blogu kilitle ayni)"
    gecersiz = "dosya bicimi gecersiz ("
    return {
        "tek_bayt_bildirim": (bildirim, fark_bildirim),
        "bildirim_yili": (veri.replace(b"2007-2026", b"2007-2027", 1), fark_bildirim),
        "sonuna_lf_eklenmis": (veri + b"\n", fark_bildirim),
        "tek_bayt_ayet": (bytes(ayet_bayti), fark_ayet),
        "ayet_basina_karakter": (veri.replace(b"1|1|", b"1|1|X", 1), fark_ayet),
        "ikisi_de": (
            bildirim.replace(b"1|1|", b"1|1|X", 1),
            "fark hem ayet satirlarinda hem bildirim blogunda",
        ),
        "gecersiz_utf8": (bytes(gecersiz_utf8), gecersiz + "satir 1: gecersiz UTF-8 (bayt"),
        "cr": (veri.replace(b"\n", b"\r\n", 1), gecersiz + "CR (0x0D) var"),
        "bom": (tanzil_bicim.BOM + veri, gecersiz + "BOM var"),
        "sondaki_lf_silinmis": (veri[:-1], gecersiz + "dosya LF ile bitmiyor"),
        "kesik": (veri[: len(veri) // 2], gecersiz),
        "bos": (b"", gecersiz + "dosya bos"),
    }


KOPYA_KIMLIKLERI = sorted(bozuk_kopyalar(parca_oku("uthmani")))


@pytest.mark.parametrize("kimlik", KOPYA_KIMLIKLERI)
def test_kilit_uyusmazliginda_ileti_farki_ayirir_ve_hicbir_sey_yazmaz(
    tmp_path: Path, varyant: str, kimlik: str
) -> None:
    k = kur(tmp_path, varyant)
    bozuk, fark = bozuk_kopyalar(k.veri)[kimlik]
    assert bozuk != k.veri
    gelen_yaz(k.veri_kok, varyant, bozuk)  # kilit orijinalinden hesaplandi
    with pytest.raises(GirdiHatasi) as hata:
        kos(k)
    mesaj = str(hata.value)
    assert "dosya ozeti kilitle tutmuyor" in mesaj
    assert fark in mesaj
    assert "Yeni Tanzil surumu kilit guncellenerek (/karar) alinir." in mesaj
    assert mesaj.startswith(f"{k.kaynak}: ")
    assert mesaj.isascii()  # dosya icerigi (Arapca ve bildirim metni) iletide yok
    assert "PLEASE" not in mesaj
    assert not (k.veri_kok / "raw").exists()  # kilitten gecmeden raw'a kopyalanmaz
    assert not (k.veri_kok / "staged").exists()
    assert k.gelen_yolu.read_bytes() == bozuk  # gelen dosyasina dokunulmaz


def test_uzun_bicim_hatasinda_ileti_sinira_sigar_ve_uyari_sonda_kalir(varyant: str) -> None:
    """Gercek boyutlu dosyada 'tanimsiz satir' iletisi 300 karakteri asardi; UYARI kesilirdi."""
    veri = sentetik_tam(varyant)
    kilit = kilit_kur(varyant, veri, tam=True)
    bozuk = veri + b"Deneme tanimsiz satir\n"
    with pytest.raises(GirdiHatasi) as hata:
        tanzil.kilit_denetle(kilit, bozuk)
    mesaj = str(hata.value)
    assert len(mesaj) <= ILETI_EN_UZUN
    assert mesaj.endswith(tanzil.UYARI)
    assert "dosya bicimi gecersiz (satir 6242: tanimsiz satir" in mesaj
    assert mesaj.isascii()
    assert "Deneme" not in mesaj


@pytest.mark.parametrize("fark_uzunlugu", [0, 1, 80, 119, 120, 121, 500, 5000])
def test_ileti_her_fark_uzunlugunda_sinira_sigar(varyant: str, fark_uzunlugu: int) -> None:
    """Degisken `fark` parcasi ne kadar uzun olursa olsun UYARI tam ve en sonda kalir."""
    kilit = kilit_kur(varyant, parca_oku(varyant))
    mesaj = tanzil.uyusmazlik_iletisi(kilit, "f" * 64, 1396087, "x" * fark_uzunlugu)
    assert len(mesaj) <= ILETI_EN_UZUN
    assert mesaj.endswith(f". {tanzil.UYARI}")
    assert mesaj.startswith(f"{kilit.kaynak}: dosya ozeti kilitle tutmuyor (beklenen ")


def test_komut_uzun_bicim_hatasinda_stderr_uyariyi_tam_tasir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, varyant: str
) -> None:
    """stderr iletisi `ileti_temizle` ile 300 karakterde kesilir; UYARI yarim kalmamalidir."""
    kok = cli_kur(tmp_path, monkeypatch, varyant)
    yol = tmp_path / "data" / "gelen" / "tanzil" / TARIH / tanzil.dosya_adi(varyant)
    yol.write_bytes(yol.read_bytes() + b"Deneme tanimsiz satir\n")
    sonuc = komut(kok, varyant=varyant)
    assert sonuc.exit_code == 2
    hata = sonuc.stderr.rstrip("\n")
    assert hata.startswith(f"hata: tanzil-{varyant}: dosya ozeti kilitle tutmuyor")
    assert "dosya bicimi gecersiz (satir 6242: tanimsiz satir" in hata
    assert hata.endswith(". " + tanzil.UYARI)
    assert not (tmp_path / "data" / "raw").exists()


def test_kilit_atlama_yolunda_da_denetlenir(tmp_path: Path, varyant: str) -> None:
    """Parmak izi onceki calistirmayla ayni olsa da kilit her kosuda denetlenir."""
    k = kur(tmp_path, varyant)
    kos(k)
    assert kos(k)[0].atlandi is True
    gelen_yaz(k.veri_kok, varyant, k.veri.replace(b"PLEASE", b"PLEASF", 1))
    with pytest.raises(GirdiHatasi, match="kilitle tutmuyor"):
        kos(k)


def test_kilit_denetle_basarili_ayrisma_dondurur(varyant: str) -> None:
    veri = parca_oku(varyant)
    ayrisma = tanzil.kilit_denetle(kilit_kur(varyant, veri), veri, tam=False)
    assert len(ayrisma.ayetler) == PARCA_AYET


def test_kilit_denetle_tutarsiz_kayit_ve_bicim(varyant: str) -> None:
    veri = parca_oku(varyant)
    kilit = kilit_kur(varyant, veri)
    # dosya ozeti tutuyor ama boyut tutmuyor: kilit kaydi guvenilmez, dosya kabul edilmez
    yanlis_boyut = dataclasses.replace(kilit, boyut=len(veri) + 1)
    with pytest.raises(GirdiHatasi, match="kilitle tutmuyor") as boyut_hatasi:
        tanzil.kilit_denetle(yanlis_boyut, veri, tam=False)
    assert "kilit kaydi tutarsiz" in str(boyut_hatasi.value)
    # dosya ozeti tutuyor ama parca ozeti tutmuyor: kayit tutarsiz
    tutarsiz = dataclasses.replace(kilit, metin_sha256="0" * 64)
    with pytest.raises(GirdiHatasi, match="kilit kaydi tutarsiz"):
        tanzil.kilit_denetle(tutarsiz, veri, tam=False)
    tutarsiz = dataclasses.replace(kilit, bildirim_sha256="0" * 64)
    with pytest.raises(GirdiHatasi, match="kilit kaydi tutarsiz"):
        tanzil.kilit_denetle(tutarsiz, veri, tam=False)
    # kilitle tutan ama tam olmayan dosya `tam=True` ile reddedilir
    with pytest.raises(GirdiHatasi, match="kilitle tutan dosyanin bicimi gecersiz"):
        tanzil.kilit_denetle(kilit, veri)


def test_kayitsiz_kaynakta_gelen_dosyasi_okunmaz(tmp_path: Path) -> None:
    kok = depo_kur(tmp_path)  # hic kayit yok
    ctx = ctx_kur(tmp_path, kok, kaynaklar=["tanzil-uthmani"], temiz_git=True)
    bagdastirici = tanzil.TanzilBagdastirici(
        "uthmani", kilit=kilit_kur("uthmani", parca_oku("uthmani"))
    )
    with pytest.raises(GirdiHatasi, match="kayitsiz"):  # gelen dosyasi da yok: sira kanitlanir
        run_ingest(bagdastirici, ctx)
    assert not (tmp_path / "data" / "raw").exists()
    assert not (tmp_path / "data" / "staged").exists()


def test_gecersiz_varyant_reddedilir() -> None:
    with pytest.raises(GirdiHatasi):
        tanzil.TanzilBagdastirici("hafs")
    with pytest.raises(GirdiHatasi):
        tanzil.kaynak_kimligi("uthmani/../x")
    with pytest.raises(GirdiHatasi):
        tanzil.dosya_adi("")


# --- gelen klasoru -----------------------------------------------------------------------


def test_gelen_tarihi_en_yeni_gecerli_klasor(tmp_path: Path) -> None:
    gelen = tmp_path / "gelen"
    assert tanzil.gelen_tarihleri(gelen) == []
    gelen.mkdir()
    with pytest.raises(GirdiHatasi, match="tarih klasoru yok"):
        tanzil.gelen_tarihi_coz(gelen, None)
    for ad in ("2026-11-02", "2026-11-05", "2026-13-40", "deneme", "2026-1-2"):
        (gelen / ad).mkdir()
    (gelen / "2026-12-01").write_bytes(b"")  # dosya, klasor degil
    assert tanzil.gelen_tarihleri(gelen) == ["2026-11-02", "2026-11-05"]
    assert tanzil.gelen_tarihi_coz(gelen, None) == "2026-11-05"
    assert tanzil.gelen_tarihi_coz(gelen, "2026-11-02") == "2026-11-02"


@pytest.mark.parametrize(
    "istenen",
    ["", "../x", "..", "2026-13-01", "2026-02-30", "20261102", "2026-1-2", "2026-11-02/..", "x"],
)
def test_gecersiz_gelen_tarihi_reddedilir(tmp_path: Path, istenen: str) -> None:
    with pytest.raises(GirdiHatasi, match="--gelen-tarih"):
        tanzil.gelen_tarihi_coz(tmp_path, istenen)


def test_gelen_dosyasi_yok_ya_da_cok_buyuk(
    tmp_path: Path, varyant: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    k = kur(tmp_path, varyant)
    gelen = k.veri_kok / "gelen" / "tanzil"
    with pytest.raises(GirdiHatasi) as hata:
        tanzil.gelen_oku(gelen, "2026-11-09", varyant)
    assert str(hata.value).startswith(f"gelen/tanzil/2026-11-09/{k.ad} yok")
    assert str(hata.value).isascii()  # mutlak yol (kullanici klasoru) iletiye girmez
    assert tanzil.gelen_oku(gelen, TARIH, varyant) == k.veri
    monkeypatch.setattr(tanzil, "EN_BUYUK_GELEN_BAYT", len(k.veri) - 1)
    with pytest.raises(GirdiHatasi, match="cok buyuk"):
        tanzil.gelen_oku(gelen, TARIH, varyant)
    with pytest.raises(GirdiHatasi, match=r"gelen/tanzil/2026-11-02/quran-.*\.txt cok buyuk"):
        kos(k)
    assert not (k.veri_kok / "raw").exists()


def test_gelen_dosyasi_bir_klasorse_okunamaz(tmp_path: Path, varyant: str) -> None:
    k = kur(tmp_path, varyant)
    k.gelen_yolu.unlink()
    k.gelen_yolu.mkdir()
    with pytest.raises(GirdiHatasi, match="yok"):
        kos(k)


# --- kilit dosyasi -----------------------------------------------------------------------


def test_gercek_kilit_yapisi_ve_sabit_degerleri() -> None:
    kilit = tanzil.kilit_yukle()
    assert list(kilit) == ["uthmani", "simple-clean"]
    for ad, k in kilit.items():
        assert k.varyant == ad
        ozetler = (k.sha256, k.metin_sha256, k.bildirim_sha256)
        assert all(re.fullmatch(r"[0-9a-f]{64}", o) for o in ozetler)
        assert len(set(ozetler)) == 3
        assert k.url == "https://tanzil.net/download/"
        assert k.secenekler == {
            "marks": True,
            "sajdah": True,
            "tatweel": True,
            "rub": False,
            "stanween": False,
        }
        assert k.surum == "1.1"
        assert k.alinma_tarihi == "2026-11-02"
        assert (k.sha256, k.boyut) == GERCEK_DOSYA_OZETLERI[ad]  # A10.0 olcumu
    ham = tanzil.KILIT_YOLU.read_bytes()
    assert ham.isascii()
    assert ham.endswith(b"}\n")
    assert (
        tanzil.kilit_metni(kilit, tanzil.ust_veri_kilidi_yukle()).encode("utf-8") == ham
    )  # kanonik


def test_gercek_kilit_kaynak_kayitlariyla_tutarli(varyant: str) -> None:
    k = tanzil.kilit_yukle()[varyant]
    sonuc = sources.oku(
        depo_koku() / "pipeline" / "sources" / f"{tanzil.kaynak_kimligi(varyant)}.toml"
    )
    assert sonuc.kaynak is not None, sonuc.hatalar
    assert sonuc.kaynak.surum == k.surum
    assert sonuc.kaynak.kaynak_url == k.url
    assert sonuc.kaynak.notice_text is not None
    # K-39 madde 6: notice_text baytlari kilitteki bildirim ozetiyle ayni
    assert hashlib.sha256(sonuc.kaynak.notice_text.encode("utf-8")).hexdigest() == k.bildirim_sha256


def gecerli_kilit_nesnesi() -> dict[str, Any]:
    nesne = json.loads(tanzil.KILIT_YOLU.read_bytes().decode("utf-8"))
    assert isinstance(nesne, dict)
    return nesne


def kilit_bozulmus(degistir: Any) -> dict[str, Any]:
    nesne = gecerli_kilit_nesnesi()
    degistir(nesne)
    return nesne


BOZUK_KILITLER: dict[str, Any] = {
    "ust_alan_fazla": lambda n: n.update(ek=1),
    "ust_alan_yok": lambda n: n.pop("varyantlar"),
    "varyant_eksik": lambda n: n["varyantlar"].pop("simple-clean"),
    "varyant_fazla": lambda n: n["varyantlar"].update(hafs={}),
    "nesne_degil": lambda n: n["varyantlar"].update(uthmani=[]),
    "alan_fazla": lambda n: n["varyantlar"]["uthmani"].update(ek="x"),
    "alan_eksik": lambda n: n["varyantlar"]["uthmani"].pop("sha256"),
    "sha256_buyuk_harf": lambda n: n["varyantlar"]["uthmani"].update(sha256="A" * 64),
    "sha256_kisa": lambda n: n["varyantlar"]["uthmani"].update(metin_sha256="a" * 63),
    "sha256_metin_degil": lambda n: n["varyantlar"]["uthmani"].update(bildirim_sha256=7),
    "boyut_sifir": lambda n: n["varyantlar"]["uthmani"].update(boyut=0),
    "boyut_negatif": lambda n: n["varyantlar"]["uthmani"].update(boyut=-5),
    "boyut_bool": lambda n: n["varyantlar"]["uthmani"].update(boyut=True),
    "boyut_metin": lambda n: n["varyantlar"]["uthmani"].update(boyut="1"),
    "tarih_gecersiz": lambda n: n["varyantlar"]["uthmani"].update(alinma_tarihi="2026-13-01"),
    "tarih_bicimi": lambda n: n["varyantlar"]["uthmani"].update(alinma_tarihi="20261102"),
    "tarih_metin_degil": lambda n: n["varyantlar"]["uthmani"].update(alinma_tarihi=5),
    "secenek_eksik": lambda n: n["varyantlar"]["uthmani"]["secenekler"].pop("rub"),
    "secenek_fazla": lambda n: n["varyantlar"]["uthmani"]["secenekler"].update(alef=True),
    "secenek_bool_degil": lambda n: n["varyantlar"]["uthmani"]["secenekler"].update(rub=1),
    "surum_bos": lambda n: n["varyantlar"]["uthmani"].update(surum=""),
    "surum_harfli": lambda n: n["varyantlar"]["uthmani"].update(surum="1.x"),
    "url_http": lambda n: n["varyantlar"]["uthmani"].update(url="http://tanzil.net/download/"),
    "url_metin_degil": lambda n: n["varyantlar"]["uthmani"].update(url=None),
}


@pytest.mark.parametrize("kimlik", sorted(BOZUK_KILITLER))
def test_bozuk_kilit_dosyasi_reddedilir(kimlik: str) -> None:
    nesne = kilit_bozulmus(BOZUK_KILITLER[kimlik])
    with pytest.raises(GirdiHatasi) as hata:
        tanzil.kilit_coz(json.dumps(nesne).encode("utf-8"))
    assert str(hata.value).startswith("tanzil.lock.json")
    assert str(hata.value).isascii()


def test_bozuk_kilit_bayt_duzeyi() -> None:
    gecerli = tanzil.KILIT_YOLU.read_bytes()
    tanzil.kilit_coz(gecerli)
    kopya = b'{"varyantlar": {"uthmani": {}, "uthmani": {}}}'
    for bozuk in (
        b"\xef\xbb\xbf" + gecerli,
        gecerli.replace(b"\n", b"\r\n"),
        gecerli + b"\xff",
        b"[]",
        b"{",
        b"",
        kopya,  # yinelenen anahtar
        gecerli.replace(b'"boyut": 1396087', b'"boyut": 1396087.5'),
    ):
        with pytest.raises(GirdiHatasi, match=r"tanzil\.lock\.json"):
            tanzil.kilit_coz(bozuk)


def test_kilit_yukle_dosya_yoksa_ve_yol_verilince(tmp_path: Path) -> None:
    with pytest.raises(GirdiHatasi, match="okunamadi"):
        tanzil.kilit_yukle(tmp_path / "yok.json")
    kopya = tmp_path / "kilit.json"
    kopya.write_bytes(tanzil.KILIT_YOLU.read_bytes())
    assert tanzil.kilit_yukle(kopya) == tanzil.kilit_yukle()


# --- kilit onerisi -----------------------------------------------------------------------


def test_kilit_onerisi_dosyadan_hesaplanir(varyant: str) -> None:
    veri = sentetik_tam(varyant)
    kilit = tanzil.kilit_onerisi(varyant, veri, "2026-12-01")
    ayrisma = tanzil_bicim.ayristir(veri)
    assert kilit == tanzil.KilitGirdisi(
        varyant=varyant,
        url="https://tanzil.net/download/",
        secenekler=dict(tanzil.SECENEKLER),
        surum="1.1",
        alinma_tarihi="2026-12-01",
        boyut=len(veri),
        sha256=hashlib.sha256(veri).hexdigest(),
        metin_sha256=ayrisma.metin_sha256,
        bildirim_sha256=ayrisma.bildirim_sha256,
    )
    assert len(ayrisma.ayetler) == 6236


def test_kilit_onerisi_yanlis_varyant_ve_bozuk_dosya_reddedilir() -> None:
    with pytest.raises(GirdiHatasi, match="uyusmuyor"):
        tanzil.kilit_onerisi("uthmani", sentetik_tam("simple-clean"), TARIH)
    with pytest.raises(GirdiHatasi, match="ayet sayisi eksik"):
        tanzil.kilit_onerisi("uthmani", parca_oku("uthmani"), TARIH)
    basliksiz = sentetik_tam("uthmani", bildirim=b"\n\n# Deneme\n")
    with pytest.raises(GirdiHatasi, match="bildirim basligi"):
        tanzil.kilit_onerisi("uthmani", basliksiz, TARIH)


# --- komut -------------------------------------------------------------------------------


def cli_kur(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, varyant: str = "uthmani") -> Path:
    """Sahte depo kokunde kaynak kaydi, 6.236 satirlik SENTETIK gelen dosyasi ve gecici kilit."""
    kok = depo_kur(tmp_path, tanzil.kaynak_kimligi(varyant))
    veri_kok = tmp_path / "data"
    gelen_yaz(veri_kok, varyant, sentetik_tam(varyant))
    kilitler = {v: kilit_kur(v, sentetik_tam(v), tam=True) for v in VARYANTLAR}
    kilit_dosyasi = tmp_path / "kilit.json"
    kilit_dosyasi.write_bytes(tanzil.kilit_metni(kilitler).encode("utf-8"))
    monkeypatch.setattr(tanzil, "KILIT_YOLU", kilit_dosyasi)
    monkeypatch.setenv("MUTALAA_VERI_KOK", str(veri_kok))
    return kok


def komut(kok: Path, *argumanlar: str, varyant: str = "uthmani") -> Result:
    return runner.invoke(
        cli.app, ["ingest", "tanzil", "--variant", varyant, *argumanlar, "--kok", str(kok)]
    )


def test_komut_sentetik_dosyayi_alir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    kok = cli_kur(tmp_path, monkeypatch)
    sonuc = komut(kok)
    assert sonuc.exit_code == 0, sonuc.stderr
    assert sonuc.stdout.startswith("ingest tanzil-uthmani: 6236 birim, run ")
    veri_kok = tmp_path / "data"
    (staged,) = (veri_kok / "staged" / "tanzil-uthmani").iterdir()
    assert (staged / "notice.txt").read_bytes() == sentetik_bildirim("uthmani")
    satirlar = (staged / "units.jsonl").read_bytes().split(b"\n")
    assert len(satirlar) == 6237
    assert json.loads(satirlar[0])["anchor"] == "q:1:1"
    assert json.loads(satirlar[-2])["anchor"] == "q:114:6"
    ham = veri_kok / "raw" / "tanzil-uthmani" / TARIH
    assert altlar(ham) == ["fetch.json", "quran-uthmani.txt"]
    manifest = json.loads((staged / "manifest.json").read_bytes())
    assert manifest["komut"] == "ingest tanzil --variant uthmani"
    assert manifest["adim"] == "ingest"
    # rapor ve gunluk: yalniz sayilar, icerik metni yok
    rapor = json.loads(next((veri_kok / "reports").glob("*.json")).read_bytes())
    assert rapor["cikis_kodu"] == 0
    assert rapor["parametreler"] == {"variant": "uthmani"}
    assert rapor["sayilar"]["birim"] == 6236
    kayitlar = b"".join(p.read_bytes() for p in (veri_kok / "reports").glob("*.json"))
    kayitlar += b"".join(p.read_bytes() for p in (veri_kok / "logs").glob("*.jsonl"))
    assert b"Deneme" not in kayitlar


def test_komut_iki_varyant_ayri_kaynak_olarak_alinir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    kok = cli_kur(tmp_path, monkeypatch)
    gelen_yaz(tmp_path / "data", "simple-clean", sentetik_tam("simple-clean"))
    kayit_yaz(kok, alanlar_kur("tanzil-simple-clean"))
    assert komut(kok).exit_code == 0
    sonuc = komut(kok, varyant="simple-clean")
    assert sonuc.exit_code == 0, sonuc.stderr
    assert "ingest tanzil-simple-clean: 6236 birim" in sonuc.stdout
    assert altlar(tmp_path / "data" / "raw") == ["tanzil-simple-clean", "tanzil-uthmani"]


def test_komut_tek_bayt_degisince_cikis_2(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    kok = cli_kur(tmp_path, monkeypatch)
    yol = tmp_path / "data" / "gelen" / "tanzil" / TARIH / "quran-uthmani.txt"
    veri = yol.read_bytes()
    bozuk = veri.replace(b"Deneme 1 1", b"Deneme 1 2", 1)  # tek bayt
    assert len(bozuk) == len(veri) and bozuk != veri
    yol.write_bytes(bozuk)
    sonuc = komut(kok)
    assert sonuc.exit_code == 2
    assert "dosya ozeti kilitle tutmuyor" in sonuc.stderr
    assert "fark ayet satirlarinda" in sonuc.stderr
    assert "kilit guncellenerek (/karar) alinir" in sonuc.stderr
    assert "Deneme" not in sonuc.stderr
    assert not (tmp_path / "data" / "raw").exists()
    assert not (tmp_path / "data" / "staged").exists()
    # bildirimdeki bir bayt: ileti bildirim farkini soyler
    yol.write_bytes(veri.replace(b"Deneme bildirim", b"Deneme bildirin", 1))
    sonuc = komut(kok)
    assert sonuc.exit_code == 2
    assert "fark yalniz bildirim blogunda" in sonuc.stderr


def test_komut_gercek_kilit_sentetik_dosyayi_reddeder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Gecici kilit verilmezse paketteki gercek kilit gecerlidir."""
    kok = cli_kur(tmp_path, monkeypatch)
    monkeypatch.setattr(tanzil, "KILIT_YOLU", Path(tanzil.__file__).with_name("tanzil.lock.json"))
    sonuc = komut(kok)
    assert sonuc.exit_code == 2
    assert "kilit guncellenerek (/karar) alinir" in sonuc.stderr
    assert not (tmp_path / "data" / "raw").exists()


def test_komut_kilit_oner_hicbir_sey_yazmaz(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    kok = cli_kur(tmp_path, monkeypatch)
    sonuc = komut(kok, "--kilit-oner")
    assert sonuc.exit_code == 0, sonuc.stderr
    beklenen = tanzil.kilit_onerisi("uthmani", sentetik_tam("uthmani"), TARIH)
    assert json.loads(sonuc.stdout) == {"varyantlar": {"uthmani": beklenen.sozluk()}}
    assert sonuc.stdout.endswith("}\n")
    assert altlar(tmp_path / "data") == ["gelen"]  # raw, staged, reports, logs yok
    tarihli = komut(kok, "--kilit-oner", "--gelen-tarih", TARIH)
    assert tarihli.stdout == sonuc.stdout


def test_komut_kilit_oner_kaydi_olmayan_kaynakta_cikis_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    kok = cli_kur(tmp_path, monkeypatch)
    gelen_yaz(tmp_path / "data", "simple-clean", sentetik_tam("simple-clean"))
    sonuc = komut(kok, "--kilit-oner", varyant="simple-clean")  # tanzil-simple-clean kaydi yok
    assert sonuc.exit_code == 2
    assert "kayitsiz" in sonuc.stderr
    assert sonuc.stdout == ""


@pytest.mark.parametrize(
    ("argumanlar", "parca"),
    [
        (["--limit", "5"], "--limit"),
        (["--kilit-oner", "--dry-run"], "--kilit-oner"),
        (["--kilit-oner", "--force"], "--kilit-oner"),
        (["--gelen-tarih", "../x"], "--gelen-tarih"),
        (["--gelen-tarih", "2026-13-01"], "--gelen-tarih"),
        (["--kilit-oner", "--gelen-tarih", "2026-02-30"], "--gelen-tarih"),
    ],
)
def test_komut_bayrak_hatalari_cikis_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, argumanlar: list[str], parca: str
) -> None:
    kok = cli_kur(tmp_path, monkeypatch)
    sonuc = komut(kok, *argumanlar)
    assert sonuc.exit_code == 2
    assert parca in sonuc.stderr
    assert not (tmp_path / "data" / "raw").exists()
    assert not (tmp_path / "data" / "staged").exists()


def test_komut_bilinmeyen_varyant_cikis_2(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    kok = cli_kur(tmp_path, monkeypatch)
    assert komut(kok, varyant="hafs").exit_code == 2
    assert {v.value for v in cli.TanzilVaryanti} == {*VARYANTLAR, tanzil.UST_VERI}


def test_komut_dry_run_raw_ve_staged_yazmaz(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    kok = cli_kur(tmp_path, monkeypatch)
    sonuc = komut(kok, "--dry-run")
    assert sonuc.exit_code == 0, sonuc.stderr
    assert "ingest tanzil-uthmani: 6236 birim (dry-run, hicbir sey yazilmadi)" in sonuc.stdout
    assert not (tmp_path / "data" / "raw").exists()
    assert not (tmp_path / "data" / "staged").exists()
    rapor = json.loads(next((tmp_path / "data" / "reports").glob("*.json")).read_bytes())
    assert rapor["dry_run"] is True


def test_komut_kaynak_kaydi_yoksa_cikis_2(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    kok = cli_kur(tmp_path, monkeypatch)
    (kok / "pipeline" / "sources" / "tanzil-uthmani.toml").unlink()
    sonuc = komut(kok)
    assert sonuc.exit_code == 2
    assert "kaynak kaydi" in sonuc.stderr
    assert not (tmp_path / "data" / "raw").exists()


def test_komut_gelen_dosyasi_yoksa_cikis_2(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    kok = cli_kur(tmp_path, monkeypatch)
    (tmp_path / "data" / "gelen" / "tanzil" / TARIH / "quran-uthmani.txt").unlink()
    sonuc = komut(kok)
    assert sonuc.exit_code == 2
    assert f"gelen/tanzil/{TARIH}/quran-uthmani.txt yok" in sonuc.stderr
    assert not (tmp_path / "data" / "raw").exists()


def test_komut_gelen_klasoru_yoksa_cikis_2(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    kok = cli_kur(tmp_path, monkeypatch)
    shutil.rmtree(tmp_path / "data" / "gelen" / "tanzil")
    sonuc = komut(kok)
    assert sonuc.exit_code == 2
    assert "tarih klasoru yok" in sonuc.stderr


def test_komut_iki_kosu_ayni_staged_ozetini_uretir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    kok = cli_kur(tmp_path, monkeypatch)
    assert komut(kok).exit_code == 0
    assert komut(kok, "--force").exit_code == 0
    ilk, ikinci = sorted((tmp_path / "data" / "staged" / "tanzil-uthmani").iterdir())
    for ad in ("units.jsonl", "notice.txt"):
        assert ozet(ilk / ad) == ozet(ikinci / ad)
    assert altlar(tmp_path / "data" / "raw" / "tanzil-uthmani") == [TARIH]  # tek ham kopya


@pytest.mark.parametrize("alan", ["metin_sha256", "bildirim_sha256"])
def test_parse_ayristirilan_ozetler_kilitle_tutmuyorsa_girdi_hatasi(
    tmp_path: Path, varyant: str, alan: str
) -> None:
    """Savunma derinligi: `fetch` kilidi denetler, `parse` ozetleri yeniden dogrular."""
    veri = parca_oku(varyant)
    kilit = dataclasses.replace(kilit_kur(varyant, veri), **{alan: "0" * 64})
    yol = tmp_path / tanzil.dosya_adi(varyant)
    yol.write_bytes(veri)
    ctx = ctx_kur(tmp_path, depo_kur(tmp_path))
    bagdastirici = tanzil.TanzilBagdastirici(varyant, kilit=kilit, tam=False)  # fiksturdeki parca
    with pytest.raises(GirdiHatasi, match="ayristirilan ozetler kilitle tutmuyor"):
        list(bagdastirici.parse(ctx, [RawFile(yol, kilit.sha256, kilit.url)]))
