"""`qa risale-rapor` secenek dogrulamasi (yola eklenen run_id ve tarih; ACIKCA SENTETIK veri).

`--rnk-run`, `--diyanet-run`, `--rnk-tarih` ve `--erisale-tarih` dosya yoluna eklenir: UUID ya da
`YYYY-AA-GG` degilse dosya aranmadan cikis 2; acik run manifestli, adimi `ingest` ve ciktilari
saglam olmali. Basliklar "Deneme Bolum ..." yer tutucularidir; veritabani yoktur.
"""

import hashlib
import json
import shutil
from pathlib import Path

import pytest
from test_risale_icindekiler_karsilastirma import erisale_yaz, kitap_kaydi, toc
from test_sources import kok_kur
from typer.testing import CliRunner

from mutalaa_pipeline import cli, cli_risale_rapor

runner = CliRunner()
RUN_UUID = "01a1d225-8f55-7309-b24f-34684721026c"


def _ortam(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, adim: str = "ingest"
) -> tuple[Path, Path]:
    """Sentetik gelen + manifestli staged RNK calismasi; `(kok, veri)` doner."""
    tablo = (kitap_kaydi("deneme-a", uid="uid-a", raf="tr"),)
    monkeypatch.setattr(cli_risale_rapor.risale, "kitaplar", lambda: tablo)
    kok = kok_kur(tmp_path)
    veri = tmp_path / "data"
    monkeypatch.setenv("MUTALAA_VERI_KOK", str(veri))
    adlar = [f"Deneme Bolum {c}" for c in "ABCDEF"]
    json_yol = veri / "gelen" / "risale-baski-rnk" / "2026-11-12" / "tr" / "uid-a.json"
    json_yol.parent.mkdir(parents=True)
    agac = {
        "meta_data": {"uid": "uid-a", "shelf_id": "tr", "first_page": 1, "last_page": 9},
        "contents": {
            "title": "Deneme",
            "pageNo": 1,
            "children": [{"title": a, "pageNo": i + 1} for i, a in enumerate(adlar)],
        },
    }
    json_yol.write_text(json.dumps(agac), encoding="utf-8")
    erisale_yaz(
        veri / "gelen" / "erisale-icindekiler" / "2026-11-12" / "toc-tr.json",
        [toc(i, "deneme-a", a, 1) for i, a in enumerate(adlar, start=1)],
    )
    klasor = veri / "staged" / "risale-rnk-metin" / RUN_UUID
    klasor.mkdir(parents=True)
    govde = "".join(
        json.dumps(
            {
                "anchor": f"rn:deneme-a:p{i}",
                "attrs": {"kind": "baslik", "slug": "deneme-a"},
                "text": a,
            }
        )
        + "\n"
        for i, a in enumerate(adlar, start=1)
    ).encode("utf-8")
    (klasor / "units.jsonl").write_bytes(govde)
    manifest = {
        "run_id": RUN_UUID,
        "adim": adim,
        "ciktilar": [
            {
                "yol": f"staged/risale-rnk-metin/{RUN_UUID}/units.jsonl",
                "sha256": hashlib.sha256(govde).hexdigest(),
            }
        ],
    }
    (klasor / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return kok, veri


def _icindekiler(kok: Path, *secenek: str) -> int:
    return runner.invoke(
        cli.app,
        ["qa", "risale-rapor", "--rapor", "icindekiler", "--dry-run", *secenek, "--kok", str(kok)],
    ).exit_code


def test_acik_run_kimligi_dogrulanir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    kok, veri = _ortam(tmp_path, monkeypatch)
    assert _icindekiler(kok, "--rnk-run", RUN_UUID) == 0
    # UUID olmayan ve yol ayiracli kimlikler: baska bir klasore cikmaya calisan hedef GERCEKTEN var
    (veri / "staged" / "baska-kaynak" / "x").mkdir(parents=True)
    (veri / "staged" / "baska-kaynak" / "x" / "units.jsonl").write_bytes(b"")
    for kotu in ("../baska-kaynak/x", "..", "01run", RUN_UUID.upper(), RUN_UUID + "/..", ""):
        assert _icindekiler(kok, "--rnk-run", kotu) == 2, kotu
    assert _icindekiler(kok, "--rnk-run", "01a1d225-0000-7000-8000-000000000000") == 2


def test_diyanet_run_kimligi_dogrulanir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    kok, _ = _ortam(tmp_path, monkeypatch)
    for kotu in ("../risale-rnk-metin/" + RUN_UUID, "01run", ".."):
        sonuc = runner.invoke(
            cli.app,
            [
                "qa",
                "risale-rapor",
                "--rapor",
                "diyanet",
                "--dry-run",
                "--diyanet-run",
                kotu,
                "--kok",
                str(kok),
            ],
        )
        assert sonuc.exit_code == 2, kotu


def test_run_adimi_ve_butunluk_denetlenir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    kok, veri = _ortam(tmp_path, monkeypatch, adim="anchor")  # adim ingest degil
    assert _icindekiler(kok, "--rnk-run", RUN_UUID) == 2
    manifest = veri / "staged" / "risale-rnk-metin" / RUN_UUID / "manifest.json"
    belge = json.loads(manifest.read_text(encoding="utf-8"))
    belge["adim"] = "ingest"
    manifest.write_text(json.dumps(belge), encoding="utf-8")
    assert _icindekiler(kok, "--rnk-run", RUN_UUID) == 0
    units = manifest.with_name("units.jsonl")  # cikti ozeti tutmazsa reddedilir
    units.write_bytes(units.read_bytes() + b"\n")
    assert _icindekiler(kok, "--rnk-run", RUN_UUID) == 2


def test_tarih_secenekleri_dogrulanir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    kok, veri = _ortam(tmp_path, monkeypatch)
    gelen = veri / "gelen"
    shutil.copytree(gelen / "risale-baski-rnk" / "2026-11-12", gelen / "baska-klasor")
    shutil.copytree(gelen / "erisale-icindekiler" / "2026-11-12", gelen / "baska-erisale")
    mutlak = str((gelen / "baska-klasor").resolve())
    assert _icindekiler(kok, "--rnk-tarih", "2026-11-12", "--erisale-tarih", "2026-11-12") == 0
    for kotu in ("../baska-klasor", "..", mutlak, "2026-13-45", "2026-11-12/..", ""):
        assert _icindekiler(kok, "--rnk-tarih", kotu) == 2, kotu
    for kotu in ("../baska-erisale", "..", "2026-02-30", ""):
        assert _icindekiler(kok, "--erisale-tarih", kotu) == 2, kotu
    # tarih verilmediginde yalniz gecerli tarih adli klasorler en yeni sayilir
    (gelen / "risale-baski-rnk" / "zzz-gecersiz").mkdir()
    assert _icindekiler(kok) == 0
