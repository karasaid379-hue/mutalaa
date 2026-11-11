"""Gercek meal verisi sayim testi (A16.2): veri varsa kosar, yoksa atlanir (CI'da `data/` yoktur).

Indirilen dosyalar guvenilmeyen VERIDIR: onlari okuyan Python `-I` ile ayri surecte calisir.
Test yalniz SAYI ve capa kumesi dogrular; meal metni teste ve ciktisina girmez.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from mutalaa_pipeline.export.ortak import depo_koku

GELEN = depo_koku() / "data" / "gelen"
TARIH = "2026-11-11"
BETIK = """
import json, sys
from pathlib import Path
from mutalaa_pipeline.ingest import elmalili_sade, elmalili_vikikaynak, meal_kilit
kok = Path(sys.argv[1])
kilit = meal_kilit.kilit_yukle()
def oku(slug, adlar):
    return {a: (kok / slug / sys.argv[2] / a).read_bytes() for a in adlar}
vdosyalar = [d.ad for d in kilit.vikikaynak.dosyalar]
viki = elmalili_vikikaynak.yeniden_uret(oku("elmalili-meal", vdosyalar), kilit)
sade = elmalili_sade.yeniden_uret(oku("elmalili-sade-meal", [kilit.sade.dosya.ad]), kilit)
def ozet(d):
    return {
        "birim": len(d),
        "bos": sum(1 for t, a in d.values() if t == ""),
        "izleyen": sum(1 for t, a in d.values() if "birlesik_ile" in a),
        "kapsam": sum(1 for t, a in d.values() if "kapsam" in a),
        "besmele": sum(1 for t, a in d.values() if "besmele_meali" in a),
    }
print(json.dumps({"viki": ozet(viki), "sade": ozet(sade)}))
"""


def _veri_var() -> bool:
    return all(
        (GELEN / s / TARIH / "SHA256SUMS").is_file()
        for s in ("elmalili-meal", "elmalili-sade-meal")
    )


@pytest.mark.skipif(not _veri_var(), reason="data/gelen meal dosyalari yok")
def test_gercek_veri_sayimlari_kilitle_tutar() -> None:
    sonuc = subprocess.run(
        [sys.executable, "-I", "-c", BETIK, str(Path(GELEN)), TARIH],
        capture_output=True,
        check=False,
        timeout=300,
    )
    assert sonuc.returncode == 0, sonuc.stderr.decode("utf-8", "replace")[-300:]
    s = json.loads(sonuc.stdout.decode("utf-8"))
    assert s["viki"]["birim"] == s["sade"]["birim"] == 6236
    # 19 birlesik bas ve 19 izleyen (2 aralikli + 17 ardisik grup); bos metin yalniz izleyenler
    assert (s["viki"]["kapsam"], s["viki"]["izleyen"], s["viki"]["bos"]) == (19, 19, 19)
    assert s["viki"]["besmele"] == 0
    assert (s["sade"]["bos"], s["sade"]["izleyen"], s["sade"]["kapsam"]) == (0, 0, 0)
