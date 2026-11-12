# ruff: noqa: RUF001
"""RNK CLI ve `qa run` testleri (A20.1b; ACIKCA SENTETIK veri, veritabani yok).

`ingest risale --source risale-rnk-metin` ve `qa run --source risale-rnk-metin`: yonlendirme,
yardim metni, cikis kodlari (0, 1, 2), rapor alanlari ve metin yazilmamasi. Sentetik gelen
klasoru, sentetik kilit ve tek kitaplik sentetik tablo yamayla baglanir.
"""

import json
from dataclasses import dataclass
from pathlib import Path

import pytest
from hat_yardimci import ansisiz
from test_risale_rnk import _gelen_kur, kitap_kaydi, sentetik_json, sentetik_txt
from test_sources import alanlar_kur, kayit_yaz, kok_kur
from typer.testing import CliRunner

from mutalaa_pipeline import cli
from mutalaa_pipeline.export.ortak import depo_koku
from mutalaa_pipeline.ingest import risale_kaynaklari
from mutalaa_pipeline.ingest import risale_rnk_kaynaklari as kaynak_modulu
from mutalaa_pipeline.ingest import risale_rnk_kilit as kilit_modulu
from mutalaa_pipeline.ingest.risale_rnk_kilit import KAYNAK, kilit_metni
from mutalaa_pipeline.qa import kaynak_kapilari
from mutalaa_pipeline.qa import run_risale_rnk as qa_modulu

runner = CliRunner()


@dataclass
class RnkKoku:
    tmp: Path
    kok: Path
    veri_kok: Path
    kilit_yolu: Path

    def ingest(self, *arg: str) -> int:
        return runner.invoke(
            cli.app, ["ingest", "risale", "--source", KAYNAK, *arg, "--kok", str(self.kok)]
        ).exit_code

    def adim(self, komut: str, *arg: str) -> int:
        return runner.invoke(
            cli.app, [komut, "--source", KAYNAK, *arg, "--kok", str(self.kok)]
        ).exit_code

    def zincir(self, *arg: str) -> int:
        """ingest, normalize ve anchor (ilk basarisizlikta o kod doner)."""
        for kod in (self.ingest(*arg), self.adim("normalize", *arg), self.adim("anchor", *arg)):
            if kod != 0:
                return kod
        return 0

    def qa(self, *arg: str) -> tuple[int, str]:
        sonuc = runner.invoke(
            cli.app, ["qa", "run", "--source", KAYNAK, *arg, "--kok", str(self.kok)]
        )
        return sonuc.exit_code, sonuc.output

    def staged(self) -> list[Path]:
        kok = self.veri_kok / "staged" / KAYNAK
        return sorted(kok.iterdir()) if kok.is_dir() else []

    def raporlar(self) -> list[Path]:
        kok = self.veri_kok / "reports"
        return sorted(kok.glob("*.json")) if kok.is_dir() else []


@pytest.fixture
def rk(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> RnkKoku:
    txt, js = sentetik_txt(), sentetik_json()
    kilit = _gelen_kur(tmp_path, txt, js)
    kilit_yolu = tmp_path / "sentetik.lock.json"
    kilit_yolu.write_bytes(kilit_metni(kilit).encode("utf-8"))
    tablo = (kitap_kaydi(),)
    monkeypatch.setenv("MUTALAA_VERI_KOK", str(tmp_path / "data"))
    monkeypatch.setattr(kilit_modulu, "KILIT_YOLU", kilit_yolu)
    monkeypatch.setattr(kaynak_modulu, "kitaplar", lambda: tablo)
    monkeypatch.setattr(qa_modulu, "kitaplar", lambda: tablo)
    kok = kok_kur(tmp_path)
    for ad in ("tr.jsonl", "ar.jsonl"):  # G-NOR vektorleri sahte depo kokunde de bulunur
        hedef = kok / "shared" / "test-vectors" / "normalize" / ad
        hedef.parent.mkdir(parents=True, exist_ok=True)
        hedef.write_bytes((depo_koku() / "shared" / "test-vectors" / "normalize" / ad).read_bytes())
    kayit_yaz(
        kok,
        alanlar_kur(
            KAYNAK,
            tur="risale",
            baslik="Deneme RNK",
            surum="deneme-surum",
            kaynak_url="https://example.test/shelves.json",
        ),
    )
    return RnkKoku(tmp_path, kok, tmp_path / "data", kilit_yolu)


def test_rnk_kaynak_kaydi_ve_kapilar() -> None:
    assert risale_kaynaklari.risale_mi(KAYNAK)
    k = risale_kaynaklari.kaynak(KAYNAK)
    assert k.yukleme and k.kapilar == ("G-KAY", "G-BUT", "G-CAP", "G-NOR")
    assert risale_kaynaklari.bagdastirici_modulu(KAYNAK) is kaynak_modulu
    assert kaynak_kapilari(KAYNAK) == ("G-KAY", "G-BUT", "G-CAP", "G-NOR")
    # Diyanet: karsilastirma verisi, davranis degismedi
    diyanet = risale_kaynaklari.kaynak("risale-asil-nusha")
    assert not diyanet.yukleme and diyanet.kapilar == ("G-KAY", "G-BUT")


def test_rnk_cli_yardim_iki_kaynagi_anlatir() -> None:
    yardim = ansisiz(runner.invoke(cli.app, ["ingest", "risale", "--help"]).output)
    for ad in ("--source", "--gelen-tarih", "--kilit-oner", "--dry-run", "--force", "--limit"):
        assert ad in yardim
    assert "risale-rnk-metin" in yardim and "risale-asil-nusha" in yardim
    assert "--gate" in ansisiz(runner.invoke(cli.app, ["qa", "run", "--help"]).output)


def test_rnk_cli_bilinmeyen_kaynak_iki_kaynagi_sayar(rk: RnkKoku) -> None:
    sonuc = runner.invoke(
        cli.app, ["ingest", "risale", "--source", "bilinmeyen", "--kok", str(rk.kok)]
    )
    assert sonuc.exit_code == 2
    assert "risale-rnk-metin" in sonuc.output and "risale-asil-nusha" in sonuc.output


def test_rnk_cli_ingest_cikis_kodlari_ve_idempotentlik(rk: RnkKoku) -> None:
    assert rk.ingest("--limit", "5") == 2
    assert rk.ingest("--kilit-oner", "--dry-run") == 2
    assert rk.ingest("--kilit-oner", "--force") == 2
    assert rk.ingest("--gelen-tarih", "2026-13-45") == 2
    assert rk.ingest("--dry-run") == 0
    assert rk.staged() == [] and not (rk.veri_kok / "raw" / KAYNAK).exists()
    assert rk.ingest() == 0
    ilk = rk.staged()
    assert len(ilk) == 1
    assert rk.ingest("--force") == 0
    ikinci = rk.staged()
    assert len(ikinci) == 2
    for ad in ("units.jsonl", "sayfalar.jsonl", "yapi.jsonl", "kitaplar.jsonl"):
        assert (ikinci[0] / ad).read_bytes() == (ikinci[1] / ad).read_bytes()


def test_rnk_cli_kilit_oner_hesaplanan_kilitle_ayni_ve_hicbir_sey_yazmaz(rk: RnkKoku) -> None:
    sonuc = runner.invoke(
        cli.app, ["ingest", "risale", "--source", KAYNAK, "--kilit-oner", "--kok", str(rk.kok)]
    )
    assert sonuc.exit_code == 0, sonuc.output
    assert sonuc.output.encode("utf-8") == rk.kilit_yolu.read_bytes()
    assert not (rk.veri_kok / "raw" / KAYNAK).exists() and rk.staged() == []


def test_rnk_cli_kilitle_tutmayan_gelen_dosya_cikis_2(rk: RnkKoku) -> None:
    gelen = rk.veri_kok / "gelen" / "risale-baski-rnk" / "2026-11-12" / "tr_k" / "deneme.txt"
    gelen.write_bytes(gelen.read_bytes() + b"#99\n")
    assert rk.ingest() == 2
    assert not (rk.veri_kok / "raw" / KAYNAK).exists()


def test_rnk_normalize_anchor_komutlari_cikis_kodlari_ve_idempotentlik(rk: RnkKoku) -> None:
    # ingest yokken normalize ve anchor girdi hatasi (2); --limit ve bilinmeyen kaynak 2
    assert rk.adim("normalize") == 2 and rk.adim("anchor") == 2
    assert rk.ingest() == 0
    assert rk.adim("anchor") == 2  # normalize yok
    assert rk.adim("normalize", "--limit", "5") == 2 and rk.adim("anchor", "--limit", "5") == 2
    n_once = rk.staged()
    assert rk.adim("normalize", "--dry-run") == 0 and rk.staged() == n_once  # dry-run yazmaz
    assert rk.adim("normalize") == 0 and rk.adim("anchor", "--dry-run") == 0
    assert len(rk.staged()) == 2  # ingest + normalize
    assert rk.adim("anchor") == 0 and len(rk.staged()) == 3
    # --force: yeniden uretilir, cikti bayt bayt ayni (capa ve content_hash dosya ozeti)
    assert rk.zincir("--force") == 0
    klasorler = rk.staged()
    assert len(klasorler) == 6
    sirali = sorted(klasorler, key=lambda yol: yol.name)
    for ilk, ikinci in ((0, 3), (1, 4), (2, 5)):
        assert (sirali[ilk] / "units.jsonl").read_bytes() == (
            sirali[ikinci] / "units.jsonl"
        ).read_bytes()


def test_rnk_normalize_anchor_yardim_ve_bilinmeyen_kaynak(rk: RnkKoku) -> None:
    for komut in ("normalize", "anchor"):
        yardim = ansisiz(runner.invoke(cli.app, [komut, "--help"]).output)
        for ad in ("--source", "--dry-run", "--force", "--limit", "--config"):
            assert ad in yardim
    sonuc = runner.invoke(
        cli.app, ["normalize", "--source", "risale-asil-nusha", "--kok", str(rk.kok)]
    )
    assert sonuc.exit_code == 2  # Diyanet karsilastirma verisi normalize/anchor'a girmez


def test_rnk_qa_run_dort_kapi_gecer_cikis_0_rapor_alanlari(rk: RnkKoku) -> None:
    assert rk.zincir() == 0
    kod, cikti = rk.qa()
    assert kod == 0, cikti
    for kapi in ("G-KAY", "G-BUT", "G-CAP", "G-NOR"):
        assert f"{kapi} gecti" in cikti
    rapor = json.loads(rk.raporlar()[-1].read_bytes())
    assert rapor["kaynak"] == KAYNAK and rapor["komut"] == "qa run"
    assert rapor["kapilar"] == {k: "gecti" for k in ("G-KAY", "G-BUT", "G-CAP", "G-NOR")}
    assert set(rapor["kapi_bulgulari"]) == set(rapor["kapi_sayilari"]) == set(rapor["kapilar"])
    assert rapor["ingest_run_id"] == rapor["zincir"]["ingest"]
    assert rapor["anchor_run_id"] == rapor["zincir"]["anchor"]
    assert rapor["onceki_anchor_run_id"] is None
    assert len(rapor["units_sha256"]) == 64
    assert rapor["cikis_kodu"] == 0
    # rapor ve gunluk sentetik metin tasimaz
    ham = rk.raporlar()[-1].read_text(encoding="utf-8")
    assert "Deneme paragrafı" not in ham


def test_rnk_qa_run_ikinci_kosuda_onceki_calismayla_ayni_capalar(rk: RnkKoku) -> None:
    assert rk.zincir() == 0 and rk.qa()[0] == 0
    assert rk.zincir("--force") == 0
    kod, cikti = rk.qa()
    assert kod == 0, cikti
    rapor = json.loads(rk.raporlar()[-1].read_bytes())
    assert rapor["onceki_anchor_run_id"] is not None
    assert rapor["kapi_sayilari"]["G-CAP"]["onceki_run"] == 1
    assert rapor["kapi_sayilari"]["G-CAP"]["hash_degisen"] == 0


def test_rnk_qa_run_kismi_gate_ve_gecersiz_gate(rk: RnkKoku) -> None:
    assert rk.zincir() == 0
    kod, cikti = rk.qa("--gate", "G-KAY")
    assert kod == 0 and "G-KAY gecti" in cikti and "G-BUT" not in cikti
    kod, cikti = rk.qa("--gate", "G-CAP")
    assert kod == 0 and "G-CAP gecti" in cikti
    assert rk.qa("--gate", "G-HIZ")[0] == 2


def test_rnk_qa_run_anchor_yoksa_cikis_2(rk: RnkKoku) -> None:
    assert rk.qa()[0] == 2  # hicbir calisma yok
    assert rk.ingest() == 0
    assert rk.qa()[0] == 2  # yalniz ingest: anchor zinciri yok


def test_rnk_qa_run_kapi_kalirsa_cikis_1(rk: RnkKoku) -> None:
    assert rk.zincir() == 0
    birimler = rk.staged()[-1] / "units.jsonl"
    # staged dosya bozulursa manifest ozeti tutmaz (cikis 2); kilidi bozmak G-BUT'u kaldirir
    veri = json.loads(rk.kilit_yolu.read_bytes())
    veri["kitaplar"]["tr_k/deneme"]["isaretler"]["\\"] += 1
    rk.kilit_yolu.write_bytes((json.dumps(veri, ensure_ascii=True, indent=2) + "\n").encode())
    kod, cikti = rk.qa()
    assert kod == 1, cikti
    assert "G-BUT kaldi" in cikti
    rapor = json.loads(rk.raporlar()[-1].read_bytes())
    assert rapor["kapilar"]["G-BUT"] == "kaldi" and rapor["cikis_kodu"] == 1
    assert birimler.is_file()


def test_rnk_qa_run_staged_ozeti_bozulursa_cikis_2(rk: RnkKoku) -> None:
    assert rk.zincir() == 0
    birimler = rk.staged()[-1] / "units.jsonl"  # anchor ciktisi
    birimler.write_bytes(birimler.read_bytes() + b"\n")
    assert rk.qa()[0] == 2


def test_rnk_qa_run_ingest_ozeti_bozulursa_cikis_2(rk: RnkKoku) -> None:
    assert rk.zincir() == 0
    birimler = rk.staged()[0] / "units.jsonl"  # ingest ciktisi
    birimler.write_bytes(birimler.read_bytes() + b"\n")
    assert rk.qa()[0] == 2
