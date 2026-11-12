"""QuranWBW gercek veri testleri (A17.6): veri varsa kosar, yoksa atlanir.

`data/` CI'da yoktur; `MUTALAA_DEGISMEZLIK_ZORUNLU=1` atlamayi hataya cevirir. Indirilen dosya
(`data/gelen/quranwbw-tr`) guvenilmeyen VERIDIR: onu okuyan Python `-I` ile ayri surecte calisir
(`test_qac_gercek.py` deseni). Test yalniz SAYI ve kume farki dogrular; anlam metni ciktiya girmez.
Sayilar teste yazilmaz: dosyadan ve QAC ham dosyasindan yeniden hesaplanir.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from mutalaa_pipeline.anchor.ayet_sayilari import AYET_SAYILARI
from mutalaa_pipeline.config import Ayarlar
from mutalaa_pipeline.ingest import qac, quranwbw

BETIK = r"""
import hashlib, json, sys
from collections import Counter
from pathlib import Path

from mutalaa_pipeline.anchor.metin import kanonik_metin
from mutalaa_pipeline.enrich.morphology import kelimelere_topla
from mutalaa_pipeline.ingest import qac, quranwbw

kok = Path(sys.argv[1])
tarih = sys.argv[2]
qac_tarih = sys.argv[3]

klasor = kok / "gelen" / "quranwbw-tr" / tarih
ham = (klasor / quranwbw.DOSYA_ADI).read_bytes()
sums = {}
for satir in (klasor / "SHA256SUMS").read_bytes().decode("utf-8").split("\n"):
    if satir:
        sums[satir[66:]] = satir[:64]
sonuc = {"sums_tutar": hashlib.sha256(ham).hexdigest() == sums[quranwbw.DOSYA_ADI]}

# --- bagimsiz sayim (paketin cikaricisini kullanmaz) ---
govde = json.loads(ham.decode("utf-8"))
bag = Counter()
bos = 0
for sure, ayetler in govde.items():
    for ayet, icerik in ayetler.items():
        assert len(icerik) == 1
        bag[(int(sure), int(ayet))] = len(icerik[0])
        bos += sum(1 for m in icerik[0] if kanonik_metin(m) == "")
sonuc["bagimsiz"] = {
    "girdi": sum(bag.values()),
    "ayet": len(bag),
    "sure": len({s for s, _ in bag}),
    "bos": bos,
}

# --- paketin cikaricisi ---
satirlar = quranwbw.cikar(ham, hashlib.sha256(ham).hexdigest(), "v4-version-1")
sonuc["paket"] = quranwbw.sayilar_hesapla(satirlar)
sayi = Counter((s["surah"], s["ayah"]) for s in satirlar)
sonuc["paket_ayet_sayilari_ayni"] = sayi == bag

# metin ham dosyadan yeniden uretilebilir: JSON isaretcisi ham metni bulur
bulunamayan = 0
for s in satirlar:
    parcalar = s["provenance"]["yol"].split("/")[1:]
    deger = govde[parcalar[0]][parcalar[1]][int(parcalar[2])][int(parcalar[3])]
    if kanonik_metin(deger) != s["text"]:
        bulunamayan += 1
sonuc["yeniden_uretilemeyen"] = bulunamayan
sonuc["kanonik_degil"] = sum(1 for s in satirlar if kanonik_metin(s["text"]) != s["text"])

# --- QAC ile kelime sayisi karsilastirmasi ---
qac_dosya = kok / "gelen" / "qac-morfoloji" / qac_tarih / qac.DOSYA_ADI
if qac_dosya.is_file():
    kelimeler = kelimelere_topla(qac.ayristir(qac_dosya.read_bytes()).segmentler)
    qsayi = Counter((k.sure, k.ayet) for k in kelimeler)
    sonuc["qac"] = {
        "kelime": len(kelimeler),
        "ayet_ayni": qsayi == bag,
        "capa_kumesi_ayni": {(k.sure, k.ayet, k.kelime) for k in kelimeler}
        == {(s["surah"], s["ayah"], s["word"]) for s in satirlar},
    }
else:
    sonuc["qac"] = None
print(json.dumps(sonuc))
"""


def _yok(neden: str) -> None:
    if os.environ.get("MUTALAA_DEGISMEZLIK_ZORUNLU") == "1":
        pytest.fail(f"zorunlu gercek veri testi veri bulamadi: {neden}")
    pytest.skip(neden)


def _veri_kok() -> Path:
    ortam = os.environ.get("MUTALAA_VERI_KOK")
    return Ayarlar(veri_kok=Path(ortam)).veri_kok if ortam is not None else Ayarlar().veri_kok


@pytest.fixture(scope="module")
def olcum() -> dict[str, object]:
    kok = _veri_kok() / "gelen"
    tarih = quranwbw.kilit_yukle().alinma_tarihi
    if not (kok / "quranwbw-tr" / tarih / "SHA256SUMS").is_file():
        _yok(f"gelen dosyasi yok: gelen/quranwbw-tr/{tarih}")
    sonuc = subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            BETIK,
            str(_veri_kok()),
            tarih,
            qac.kilit_yukle().alinma_tarihi,
        ],
        capture_output=True,
        check=False,
        timeout=900,
    )
    assert sonuc.returncode == 0, sonuc.stderr.decode("utf-8", "replace")[-600:]
    veri: dict[str, object] = json.loads(sonuc.stdout.decode("utf-8"))
    return veri


def test_sha256sums_kilitle_ve_paket_sayimlari_bagimsiz_sayimla_ayni(
    olcum: dict[str, object],
) -> None:
    assert olcum["sums_tutar"] is True
    bag, paket = olcum["bagimsiz"], olcum["paket"]
    assert isinstance(bag, dict) and isinstance(paket, dict)
    assert bag["girdi"] == paket["girdi"] and bag["ayet"] == paket["ayet"]
    assert bag["sure"] == paket["sure"] == len(AYET_SAYILARI)
    assert bag["ayet"] == sum(AYET_SAYILARI)
    assert olcum["paket_ayet_sayilari_ayni"] is True


def test_bos_girdi_sifir_metin_ham_dosyadan_yeniden_uretilir_ve_kanonik(
    olcum: dict[str, object],
) -> None:
    bag = olcum["bagimsiz"]
    assert isinstance(bag, dict) and bag["bos"] == 0
    assert olcum["yeniden_uretilemeyen"] == 0
    assert olcum["kanonik_degil"] == 0


def test_her_ayetin_kelime_sayisi_qac_ile_ayni(olcum: dict[str, object]) -> None:
    qac_olcum = olcum["qac"]
    if qac_olcum is None:
        _yok("gelen/qac-morfoloji dosyasi yok")
    assert isinstance(qac_olcum, dict)
    bag = olcum["bagimsiz"]
    assert isinstance(bag, dict)
    assert qac_olcum["kelime"] == bag["girdi"]
    assert qac_olcum["ayet_ayni"] is True and qac_olcum["capa_kumesi_ayni"] is True


def test_gercek_staged_adaylar_secilen_dalgalarda_ve_kapsama_raporu_tutarli() -> None:
    """Son `enrich glosses` calismasi (varsa): dalga kumesi, tutarli/tutarsiz toplami, rapor."""
    from mutalaa_pipeline import lineage
    from mutalaa_pipeline.enrich.glosses import GLOSSES_ADI, secilen_dalgalar
    from mutalaa_pipeline.staged import satirlari_oku

    kok = _veri_kok()
    son = lineage.son_basarili(kok / "staged" / "quranwbw-tr", "anchor")
    if son is None:
        _yok("staged/quranwbw-tr icinde enrich glosses calismasi yok")
    run_id, klasor, manifest = son
    wave = manifest["ayrintilar"]["wave"]  # type: ignore[index]
    satirlar = [s.veri for s in satirlari_oku((klasor / GLOSSES_ADI).read_bytes(), GLOSSES_ADI)]
    assert {int(str(s["dalga"])) for s in satirlar} <= set(secilen_dalgalar(int(str(wave))))
    tutarsiz = sum(1 for s in satirlar if s["tutarsiz_hazir_anlam"] is True)
    assert all(
        int(str(s["baskin_sayi"])) * 10 >= int(str(s["toplam"])) * 8
        for s in satirlar
        if not s["tutarsiz_hazir_anlam"]
    )
    rapor = json.loads((kok / "reports" / f"{run_id}-kapsama.json").read_bytes())
    assert rapor["lemma"] == len(satirlar) and rapor["tutarsiz"] == tutarsiz
    assert rapor["tutarli"] + rapor["tutarsiz"] == len(satirlar)
    anlamlar = {str(d["anlam"]) for s in satirlar for d in s["dagilim"]}  # type: ignore[attr-defined]
    metin = json.dumps(rapor, ensure_ascii=False)
    assert not any(a in metin for a in list(anlamlar)[:2000] if len(a) > 8)  # anlam metni yok
