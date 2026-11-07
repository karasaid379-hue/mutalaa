"""Hat sabitlerinin tek tanimi: kopyalar sessizce ayrismasin.

`staged` calistirma klasorunun dosya adlari (`units.jsonl`, `notice.txt`) ile SHA-256 ve run_id
desenleri `lineage` modulunde tanimlidir; baska modul kendi kopyasini tasimaz, `lineage`den alir.
Kaynak agaci AST ile taranir: modul duzeyindeki atamalar ve `re.compile` cagrilari.
"""

import ast
from pathlib import Path

import mutalaa_pipeline
from mutalaa_pipeline import lineage
from mutalaa_pipeline.export import pg
from mutalaa_pipeline.ingest import base, tanzil
from mutalaa_pipeline.qa import run as qa_run
from mutalaa_pipeline.qa.checks import tanzil as qa_tanzil
from mutalaa_pipeline.staged import UNITS_ADI as STAGED_UNITS_ADI

PAKET = Path(mutalaa_pipeline.__file__).parent
TEKIL_DIZGELER = {"units.jsonl", "notice.txt"}
TEKIL_DESENLER = {
    r"[0-9a-f]{64}",  # SHA-256 (64 kucuk harfli onaltilik)
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",  # run_id (UUID)
}
TEKIL_ISLEVLER = {"_kisa"}  # kisaltilmis ozet: lineage.kisa_ozet


def _tanimlar() -> list[tuple[str, str]]:
    """Paket icindeki modul duzeyi tekil tanimlar: `(goreli dosya, ne)` ciftleri."""
    bulunan: list[tuple[str, str]] = []
    for yol in sorted(PAKET.rglob("*.py")):
        goreli = yol.relative_to(PAKET).as_posix()
        agac = ast.parse(yol.read_text(encoding="utf-8"))
        for dugum in agac.body:
            if isinstance(dugum, ast.FunctionDef) and dugum.name in TEKIL_ISLEVLER:
                bulunan.append((goreli, f"def {dugum.name}"))
            deger = dugum.value if isinstance(dugum, ast.Assign | ast.AnnAssign) else None
            if isinstance(deger, ast.Constant) and deger.value in TEKIL_DIZGELER:
                bulunan.append((goreli, f"dizge {deger.value}"))
            elif (
                isinstance(deger, ast.Call)
                and ast.unparse(deger.func) == "re.compile"
                and deger.args
                and isinstance(deger.args[0], ast.Constant)
                and deger.args[0].value in TEKIL_DESENLER
            ):
                bulunan.append((goreli, f"desen {deger.args[0].value}"))
    return bulunan


def test_ortak_sabitler_yalniz_lineage_da_tanimlanir() -> None:
    tanimlar = _tanimlar()
    assert tanimlar, "tarama hicbir tekil tanim bulamadi: test bozuk"
    disarida = [(dosya, ne) for dosya, ne in tanimlar if dosya != "lineage.py"]
    assert disarida == []


def test_lineage_tanimlari_beklenen_degerleri_tasir() -> None:
    assert lineage.UNITS_ADI == "units.jsonl"
    assert lineage.NOTICE_ADI == "notice.txt"
    assert lineage.OZET_DESENI.fullmatch("a" * 64) is not None
    assert lineage.OZET_DESENI.fullmatch("A" * 64) is None
    assert lineage.OZET_DESENI.fullmatch("a" * 63) is None
    run_id = "01a1a103-06ea-76ae-8635-168a4452dad5"
    assert lineage.RUN_ID_DESENI.fullmatch(run_id) is not None
    assert len(run_id) == lineage.UUID_UZUNLUGU
    assert lineage.kisa_ozet("0123456789abcdef" * 4) == "0123456789ab"


def test_moduller_ayni_degeri_kullanir() -> None:
    """Modul adlari (testler ve komutlar bunlara basvurur) lineage ile ayni degerdedir."""
    assert pg.UNITS_ADI == base.UNITS_ADI == STAGED_UNITS_ADI == lineage.UNITS_ADI
    assert pg.NOTICE_ADI == tanzil.NOTICE_ADI == qa_run.NOTICE_ADI == lineage.NOTICE_ADI
    for modul in (pg, tanzil, qa_tanzil):
        assert modul.OZET_DESENI is lineage.OZET_DESENI
    assert pg.RUN_ID_DESENI is lineage.RUN_ID_DESENI
