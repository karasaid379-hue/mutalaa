"""Dalga tablosu raporu (A17.5; SENTETIK): `enrich morphology` -> `reports/{run_id}-dalga.json`.

Rapor yalniz sayi tasir (dalga basina lemma ve kumulatif kapsama); lemma ya da kok metni, `qac_ref`
ve baska tanimlayici icermez. Fatiha ve 30. cuz lemmalarinin hepsi dalga 0 ya da 1'dedir.
"""

import json
from pathlib import Path

import pytest
from qac_yardimci import QacZinciri, qac_hazirla
from ust_veri_yardimci import UstVeriZinciri

from mutalaa_pipeline import lineage
from mutalaa_pipeline.enrich.morphology import cuz_baslangici

KAYNAK = "qac-morfoloji"
IZINLI_METIN = {"dalga-tablosu", KAYNAK}


@pytest.fixture
def qz(
    ust_veri_zinciri: UstVeriZinciri, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> QacZinciri:
    zincir = qac_hazirla(ust_veri_zinciri, tmp_path / "t", monkeypatch)
    zincir.hepsi()
    return zincir


def rapor_yolu(qz: QacZinciri) -> Path:
    son = lineage.son_basarili(qz.z.veri_kok / "staged" / KAYNAK, "anchor")
    assert son is not None
    yol = qz.z.veri_kok / "reports" / f"{son[0]}-dalga.json"
    assert yol.is_file()
    return yol


def metinler(deger: object) -> list[str]:
    """Raporun her metin yaprag (anahtarlar haric)."""
    if isinstance(deger, dict):
        return [m for v in deger.values() for m in metinler(v)]
    if isinstance(deger, list):
        return [m for v in deger for m in metinler(v)]
    return [deger] if isinstance(deger, str) else []


def test_rapor_dalga_basina_lemma_ve_kumulatif_kapsama(qz: QacZinciri) -> None:
    rapor = json.loads(rapor_yolu(qz).read_bytes())
    waves = qz.staged(KAYNAK, "waves.jsonl")
    lemmas = {
        str(s["qac_ref"]): int(str(s["occurrences"])) for s in qz.staged(KAYNAK, "lemmas.jsonl")
    }
    assert rapor["tur"] == "dalga-tablosu" and rapor["lemma"] == len(waves)
    toplam = sum(lemmas.values())
    assert rapor["lemmali_kelime"] == toplam
    kum_lemma = kum_kelime = 0
    for satir in rapor["dalgalar"]:
        grup = [w for w in waves if w["dalga"] == satir["dalga"]]
        kum_lemma += len(grup)
        kum_kelime += sum(lemmas[str(w["qac_ref"])] for w in grup)
        assert satir["lemma"] == len(grup)
        assert satir["kelime"] == sum(lemmas[str(w["qac_ref"])] for w in grup)
        assert satir["kumulatif_lemma"] == kum_lemma and satir["kumulatif_kelime"] == kum_kelime
        assert satir["kumulatif_kelime_orani"] == round(kum_kelime / toplam, 6)
    assert [s["dalga"] for s in rapor["dalgalar"]] == [0, 1, 2, 3, 4]
    assert kum_lemma == len(waves) and kum_kelime == toplam  # son dalga her seyi kapsar


def test_rapor_yalniz_sayi_metin_ve_tanimlayici_yok(qz: QacZinciri) -> None:
    yol = rapor_yolu(qz)
    ham = yol.read_bytes()
    assert ham.isascii()
    rapor = json.loads(ham)
    assert set(metinler(rapor)) <= {
        *IZINLI_METIN,
        str(rapor["data_version"]),
    }  # yalniz sabit etiketler
    govde = ham.decode("ascii")
    for satir in qz.staged(KAYNAK, "lemmas.jsonl"):
        assert f'"{satir["qac_ref"]}"' not in govde  # lemma dizgisi (qac_ref) yok
        assert str(satir["text"]) not in govde  # Arapca lemma metni yok
    for satir in qz.staged(KAYNAK, "roots.jsonl"):
        assert str(satir["letters"]) not in govde and str(satir["letters_bw"]) not in govde


def test_fatiha_ve_cuz30_lemmalari_dalga_0_ya_da_1(qz: QacZinciri) -> None:
    manifest = lineage.son_basarili(qz.z.veri_kok / "staged" / KAYNAK, "anchor")
    assert manifest is not None
    cuz = cuz_baslangici(qz.staged("tanzil-ust-veri", "markers.jsonl"))
    assert manifest[2]["ayrintilar"]["cuz30_baslangic"] == list(cuz)  # type: ignore[index]
    dalga = {str(w["qac_ref"]): int(str(w["dalga"])) for w in qz.staged(KAYNAK, "waves.jsonl")}
    ozel = {
        str(k["lemma_qac_ref"])
        for k in qz.staged(KAYNAK, "words.jsonl")
        if k["lemma_qac_ref"] is not None
        and (k["surah"] == 1 or (int(str(k["surah"])), int(str(k["ayah"]))) >= cuz)
    }
    assert ozel and all(dalga[r] in (0, 1) for r in ozel)
    rapor = json.loads(rapor_yolu(qz).read_bytes())
    assert rapor["fatiha_cuz30_dalga_0_1_disinda"] == 0
    assert rapor["cuz30_baslangic"] == list(cuz)
    assert rapor["fatiha_lemma"] + rapor["cuz30_lemma"] >= len(ozel)


def test_dry_run_rapor_yazmaz(qz: QacZinciri) -> None:
    once = sorted((qz.z.veri_kok / "reports").glob("*-dalga.json"))
    assert qz.enrich(dry_run=True) == 0
    assert sorted((qz.z.veri_kok / "reports").glob("*-dalga.json")) == once
