"""Gercek fikstur parcasiyla uctan uca zincir: ingest x2 -> normalize -> anchor -> qa (A10.4-5).

Fikstur `fixtures/tanzil` parcalaridir: dosyadan betikle kesilmis 40 ayet (1:1 ... 2:33) ve tam
bildirim blogu (KAYNAK.txt). Adimlar gercek islevleriyle diskte kosulur; QA 40 ayetlik tabloyla
`(7, 33)` calisir. Beklenen degerler formullerle hesaplanir; Kur'an metni testte hafizadan
yazilmaz.
"""

import json
from pathlib import Path
from typing import Any

import pytest
from tanzil_yardimci import PARCA_AYET, PARCA_CAPALAR, parca_oku
from typer.testing import CliRunner
from zincir_yardimci import Zincir, ortam_kur, zincir_hazirla

from mutalaa_pipeline import cli
from mutalaa_pipeline.adimlar.normalize_tanzil import EK_KAYNAK, KAYNAK
from mutalaa_pipeline.export import pg
from mutalaa_pipeline.ingest import tanzil
from mutalaa_pipeline.qa import KAPILAR
from mutalaa_pipeline.qa.run import QaSonucu, run_qa
from mutalaa_pipeline.runctx import RunContext, komut_calistir
from mutalaa_pipeline.zincir import calismalar

runner = CliRunner()
PARCA_TABLOSU = (7, 33)  # parcanin sure sure ayet sayisi: 1:1-7 ve 2:1-33


@pytest.fixture
def z(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Zincir:
    """Parcalardan kosulmus zincir (ingest x2, normalize, anchor) ve parcanin gecici kilidi."""
    zincir = zincir_hazirla(
        tmp_path, {v: parca_oku(v) for v in ("uthmani", "simple-clean")}, PARCA_TABLOSU
    )
    zincir.hepsi()
    ortam_kur(zincir, monkeypatch)
    zincir.kilit_dosyasi()  # ortam_kur'un gosterdigi gecici kilit dosyasini yazar
    return zincir


def qa_kos(z: Zincir) -> tuple[RunContext, QaSonucu, int]:
    """`qa run` govdesi parca tablosuyla; rapor `komut_calistir` ile yazilir (komut: qa run)."""
    ctx = z.ctx("qa", [KAYNAK, EK_KAYNAK])
    ctx.komut = "qa run"
    sonuclar: list[QaSonucu] = []

    def govde(c: RunContext) -> int:
        sonuclar.append(run_qa(c, sure_tablosu=PARCA_TABLOSU))
        return 0

    kod = komut_calistir(ctx, govde)
    return ctx, sonuclar[0], kod


def rapor_oku(ctx: RunContext) -> dict[str, Any]:
    veri = (ctx.veri_kok / "reports" / f"{ctx.run_id}.json").read_bytes()
    rapor = json.loads(veri)
    assert isinstance(rapor, dict)
    return rapor


def test_parca_zinciri_dort_kapidan_gecer_ve_rapor_yazilir(z: Zincir) -> None:
    ctx, sonuc, kod = qa_kos(z)
    assert kod == 0
    assert sonuc.kalanlar == []
    assert tuple(sonuc.kapilar) == KAPILAR
    rapor = rapor_oku(ctx)
    anchor = calismalar(ctx, KAYNAK, "anchor")[-1]
    assert rapor["komut"] == "qa run"
    assert rapor["kaynak"] == KAYNAK
    assert rapor["anchor_run_id"] == anchor.run_id
    assert rapor["units_sha256"] == anchor.cikti_ozeti()
    assert rapor["kapilar"] == dict.fromkeys(KAPILAR, "gecti")
    assert rapor["kapi_bulgulari"] == {kapi: [] for kapi in KAPILAR}
    assert rapor["sayilar"]["birim"] == PARCA_AYET
    assert rapor["kapi_sayilari"]["G-BUT"]["birim"] == PARCA_AYET
    assert rapor["kapi_sayilari"]["G-BUT"]["sure"] == len(PARCA_TABLOSU)
    assert rapor["kapi_sayilari"]["G-CAP"]["capa"] == PARCA_AYET
    olcum = rapor["olcumler"]
    assert olcum["ayet_sayilari"][KAYNAK] == {"sure": 2, "ayet": PARCA_AYET}
    assert olcum["ayet_sayilari"][EK_KAYNAK] == {"sure": 2, "ayet": PARCA_AYET}
    assert olcum["nfc"][KAYNAK]["nfc_olmayan_ayet"] > 0  # Uthmani NFC degil; NFC uygulanmadi
    assert olcum["nfc"][EK_KAYNAK]["nfc_olmayan_ayet"] == 0
    assert olcum["ar4"]["ek_sozcuklu_ayet"] > 0


def test_parca_zinciri_export_pg_dosya_onkosullarindan_gecer(z: Zincir) -> None:
    """QA raporu, zincir, satirlar ve bildirim: `export pg`nin veritabani oncesi denetimleri."""
    ctx, _, kod = qa_kos(z)
    assert kod == 0
    export = z.ctx("export", [KAYNAK, EK_KAYNAK])
    h = pg.hazirla(export, KAYNAK, None, (EK_KAYNAK,))
    assert h.qa_rapor_id == ctx.run_id
    assert [s.anchor for s in h.satirlar] == PARCA_CAPALAR
    assert [s.ord for s in h.satirlar] == list(range(1, PARCA_AYET + 1))
    assert all(s.ayah_hi == s.ayah_lo + 1 == s.ord + 1 for s in h.satirlar)
    assert {s.kind for s in h.satirlar} == {"ayet"}
    assert {s.metin_durumu for s in h.satirlar} == {"onayli"}
    assert all(s.ar_norm and "ar_norm" in s.provenance for s in h.satirlar)
    assert sorted(h.ingest) == [EK_KAYNAK, KAYNAK]
    for slug in (KAYNAK, EK_KAYNAK):
        assert h.bildirimler[slug] == h.kaynaklar[slug].notice_text  # bayt bayt


def test_parca_zinciri_metni_ham_dosyanin_baytlaridir(z: Zincir) -> None:
    """Kanonik metin zincirin sonunda da ham parcanin aynen bir dilimidir (K-26)."""
    ham = z.veriler["uthmani"]
    anchor = calismalar(z.ctx("qa", [KAYNAK]), KAYNAK, "anchor")[-1]
    satirlar = [
        json.loads(s) for s in (anchor.klasor / "units.jsonl").read_bytes().split(b"\n") if s
    ]
    assert len(satirlar) == PARCA_AYET
    for satir in satirlar:
        bas, son = satir["provenance"]["bayt"]
        assert satir["text"].encode("utf-8") == ham[bas:son]
        assert satir["provenance"]["steps"] == []


def test_parca_zinciri_tam_tabloyla_qa_cikis_2(z: Zincir) -> None:
    """Parca 6.236 ayet degildir: komut gercek tabloyu kullanir ve eksik ham dosyayi reddeder."""
    sonuc = runner.invoke(cli.app, ["qa", "run", "--source", KAYNAK, "--kok", str(z.kok)])
    assert sonuc.exit_code == 2
    assert "ayet sayisi eksik" in sonuc.stderr
    assert sonuc.stderr.isascii()


def test_parca_zincirinde_ham_dosya_degisirse_qa_cikis_2(z: Zincir) -> None:
    (ham,) = (z.veri_kok / "raw" / KAYNAK).rglob(tanzil.dosya_adi("uthmani"))
    ham.write_bytes(ham.read_bytes().replace(b"1|1|", b"1|1|X", 1))
    ctx = z.ctx("qa", [KAYNAK, EK_KAYNAK])
    ctx.komut = "qa run"
    kod = komut_calistir(ctx, lambda c: int(bool(run_qa(c, sure_tablosu=PARCA_TABLOSU).kalanlar)))
    assert kod == 2  # data/raw degismez: ozet manifestle tutmuyor
    assert "kapilar" not in rapor_oku(ctx)
