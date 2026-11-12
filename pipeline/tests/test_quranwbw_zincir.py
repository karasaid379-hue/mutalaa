"""QuranWBW zinciri: ingest -> enrich glosses -> qa run (A17.6; SENTETIK, veritabani yok).

Sentetik QAC zinciri (`qac_hazirla`; 6.236 ayet) kosulmus olarak kopyalanir; ustune sentetik
`6.json` ("Deneme anlam N" metinleri), kilit ve kaynak kaydi konur; adimlar gercek komut
islevleriyle kosar. Hicbir Kur'an kelimesi ya da gercek anlam yoktur.
"""

import dataclasses
import json
from pathlib import Path

import pytest
from hat_yardimci import TEMIZ_GIT
from qac_yardimci import TARIH, QacZinciri, qac_hazirla
from quranwbw_yardimci import (
    KAYNAK,
    QAC,
    QuranwbwZinciri,
    quranwbw_hazirla,
    sentetik_6_json,
)
from typer.testing import CliRunner
from ust_veri_yardimci import UstVeriZinciri

from mutalaa_pipeline import cli, lineage
from mutalaa_pipeline.enrich.glosses import GLOSSES_ADI
from mutalaa_pipeline.ingest import quranwbw
from mutalaa_pipeline.ingest.quranwbw import ANLAMLAR_ADI, DOSYA_ADI
from mutalaa_pipeline.qa import kaynak_kapilari, run_quranwbw
from mutalaa_pipeline.qa.checks.quranwbw import KAPI_ISLEVLERI, QuranwbwGirdisi, g_but, g_cap, g_kay
from mutalaa_pipeline.staged import Satir

runner = CliRunner()


@pytest.fixture
def wz(
    ust_veri_zinciri: UstVeriZinciri, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> QuranwbwZinciri:
    qz: QacZinciri = qac_hazirla(ust_veri_zinciri, tmp_path / "t", monkeypatch)
    qz.hepsi()
    return quranwbw_hazirla(qz, monkeypatch)


def klasorler(wz: QuranwbwZinciri, kaynak: str = KAYNAK) -> list[Path]:
    kok = wz.z.veri_kok / "staged" / kaynak
    return sorted(p for p in kok.iterdir() if p.is_dir()) if kok.is_dir() else []


def son_qa_raporu(wz: QuranwbwZinciri) -> dict[str, object]:
    raporlar = [
        json.loads(r.read_bytes()) for r in sorted((wz.z.veri_kok / "reports").glob("*.json"))
    ]
    return [r for r in raporlar if r.get("komut") == "qa run" and r.get("kaynak") == KAYNAK][-1]  # type: ignore[no-any-return]


def girdi(wz: QuranwbwZinciri) -> QuranwbwGirdisi:
    ctx = wz.ctx("qa", [KAYNAK, QAC])
    kayitlar = ctx.require_sources((KAYNAK, QAC))
    return run_quranwbw.yukle(ctx, kayitlar, run=None)[0]


def satir_degistir(satirlar: object, indeks: int, **alanlar: object) -> list[Satir]:
    liste = list(satirlar)  # type: ignore[call-overload]
    ilk = liste[indeks]
    liste[indeks] = Satir(ilk.etiket, ilk.no, {**ilk.veri, **alanlar})
    return liste


# --- ingest ------------------------------------------------------------------------------


def test_ingest_ham_kopya_staged_ve_manifest(wz: QuranwbwZinciri) -> None:
    assert wz.ingest() == 0
    ham = wz.z.veri_kok / "raw" / KAYNAK / TARIH / DOSYA_ADI
    assert ham.read_bytes() == wz.ham  # data/raw bayt bayt, degismez
    (klasor,) = klasorler(wz)
    manifest = lineage.manifest_oku(klasor)
    assert manifest is not None and manifest["adim"] == "ingest"
    anlamlar = wz.staged(KAYNAK, ANLAMLAR_ADI)
    assert len(anlamlar) == len(wz.staged(QAC, "words.jsonl"))  # her QAC kelimesine bir girdi
    ilk = anlamlar[0]
    assert ilk["provenance"]["ham_sha256"] == lineage.sha256_bayt(wz.ham)  # type: ignore[index]
    assert all(a["source_id"] == KAYNAK for a in anlamlar)


def test_ingest_kilit_uyusmazligi_cikis_2_ve_raw_bos(wz: QuranwbwZinciri) -> None:
    gelen = wz.z.veri_kok / "gelen" / KAYNAK / TARIH / DOSYA_ADI
    gelen.write_bytes(wz.ham + b" ")
    assert wz.ingest() == 2
    assert not (wz.z.veri_kok / "raw" / KAYNAK).exists()
    assert klasorler(wz) == []


def test_ingest_dry_run_hicbir_sey_yazmaz(wz: QuranwbwZinciri) -> None:
    assert wz.ingest(dry_run=True) == 0
    assert not (wz.z.veri_kok / "raw" / KAYNAK).exists()
    assert klasorler(wz) == []


def test_ingest_ikinci_kosu_atlanir(wz: QuranwbwZinciri, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(lineage, "git_durumu", lambda _kok: TEMIZ_GIT)
    assert wz.ingest() == 0
    assert wz.ingest() == 0
    assert len(klasorler(wz)) == 1  # yeni staged klasoru acilmadi (parmak izi ayni)


def test_ingest_bos_girdi_cikis_2_ve_raw_ya_da_staged_yok(
    ust_veri_zinciri: UstVeriZinciri, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    qz = qac_hazirla(ust_veri_zinciri, tmp_path / "t", monkeypatch)
    qz.hepsi()
    kelimeler = qz.staged(QAC, "words.jsonl")
    veri = json.loads(sentetik_6_json(kelimeler))
    veri["1"]["1"][0][0] = "  "  # kanonik hali bos
    wz = quranwbw_hazirla(qz, monkeypatch, ham=json.dumps(veri).encode("utf-8"))
    assert wz.ingest() == 2
    assert klasorler(wz) == []


def test_kilit_oner_hesaplanan_kilitle_ayni_ve_hicbir_sey_yazmaz(wz: QuranwbwZinciri) -> None:
    sonuc = runner.invoke(
        cli.app, ["ingest", "quranwbw-tr", "--kilit-oner", "--kok", str(wz.z.kok)]
    )
    assert sonuc.exit_code == 0
    assert sonuc.output.encode("utf-8") == wz.kilit_yolu.read_bytes()
    assert not (wz.z.veri_kok / "raw" / KAYNAK).exists() and klasorler(wz) == []
    kotu = runner.invoke(
        cli.app, ["ingest", "quranwbw-tr", "--kilit-oner", "--dry-run", "--kok", str(wz.z.kok)]
    )
    assert kotu.exit_code == 2


# --- enrich glosses ----------------------------------------------------------------------


def test_enrich_zincir_eksikse_cikis_2(
    ust_veri_zinciri: UstVeriZinciri, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    qz = qac_hazirla(ust_veri_zinciri, tmp_path / "t", monkeypatch)
    qz.hepsi()
    wz = quranwbw_hazirla(qz, monkeypatch)
    assert wz.enrich(1) == 2  # once ingest quranwbw-tr


def test_enrich_wave_1_dalga_0_ve_1_birlikte_ve_her_lemma_aday(wz: QuranwbwZinciri) -> None:
    assert wz.ingest() == 0
    assert wz.enrich(1) == 0
    dalgalar = {str(s["qac_ref"]): int(str(s["dalga"])) for s in wz.staged(QAC, "waves.jsonl")}
    glosses = wz.staged(KAYNAK, GLOSSES_ADI)
    beklenen = {r for r, d in dalgalar.items() if d in (0, 1)}
    assert {str(g["qac_ref"]) for g in glosses} == beklenen
    assert {int(str(g["dalga"])) for g in glosses} == {d for d in dalgalar.values() if d <= 1}
    # her lemmanin toplami QAC gecis sayisidir (her kelimenin bir anlami var)
    gecis = {str(s["qac_ref"]): int(str(s["occurrences"])) for s in wz.staged(QAC, "lemmas.jsonl")}
    assert all(int(str(g["toplam"])) == gecis[str(g["qac_ref"])] for g in glosses)
    assert all(g["tutarsiz_hazir_anlam"] in (True, False) for g in glosses)
    klasor = klasorler(wz)[-1]
    manifest = lineage.manifest_oku(klasor)
    assert manifest is not None and manifest["adim"] == "anchor"
    assert manifest["ayrintilar"]["wave"] == 1  # type: ignore[index]
    assert manifest["ayrintilar"]["secilen_dalgalar"] == [0, 1]  # type: ignore[index]


def test_enrich_wave_2_yalniz_dalga_2_ya_da_bos_dalga_cikis_2(wz: QuranwbwZinciri) -> None:
    assert wz.ingest() == 0
    dalgalar = {str(s["qac_ref"]): int(str(s["dalga"])) for s in wz.staged(QAC, "waves.jsonl")}
    ikiler = {r for r, d in dalgalar.items() if d == 2}
    if not ikiler:  # sentetik zincirde dalga 2 yok: bos dalga yazilmaz, cikis 2
        assert wz.enrich(2) == 2
        assert not any((k / GLOSSES_ADI).is_file() for k in klasorler(wz))
        return
    assert wz.enrich(2) == 0
    glosses = wz.staged(KAYNAK, GLOSSES_ADI)
    assert {str(g["qac_ref"]) for g in glosses} == ikiler
    assert {int(str(g["dalga"])) for g in glosses} == {2}


def test_enrich_ikinci_kosu_atlanir_force_ayni_bayt_farkli_wave_yeni_calisma(
    wz: QuranwbwZinciri, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(lineage, "git_durumu", lambda _kok: TEMIZ_GIT)
    assert wz.ingest() == 0
    assert wz.enrich(1) == 0
    assert wz.enrich(1) == 0
    anchorlar = [k for k in klasorler(wz) if (k / GLOSSES_ADI).is_file()]
    assert len(anchorlar) == 1  # parmak izi ayni: atlandi
    assert wz.enrich(1, force=True) == 0
    anchorlar = [k for k in klasorler(wz) if (k / GLOSSES_ADI).is_file()]
    assert len(anchorlar) == 2
    assert (anchorlar[0] / GLOSSES_ADI).read_bytes() == (anchorlar[1] / GLOSSES_ADI).read_bytes()
    bir = wz.ctx("anchor", [KAYNAK], parametreler={"source": KAYNAK, "wave": 1})
    iki = wz.ctx("anchor", [KAYNAK], parametreler={"source": KAYNAK, "wave": 2})
    assert bir.parmak_izi([]) != iki.parmak_izi([])  # wave parmak izine girer


def test_enrich_dry_run_hicbir_sey_yazmaz(wz: QuranwbwZinciri) -> None:
    assert wz.ingest() == 0
    assert wz.enrich(1, dry_run=True) == 0
    assert not any((k / GLOSSES_ADI).is_file() for k in klasorler(wz))
    assert not list((wz.z.veri_kok / "reports").glob("*-kapsama.json"))


@pytest.mark.parametrize("deger", ["0", "5", "-1", "x"])
def test_enrich_gecersiz_wave_cikis_2(wz: QuranwbwZinciri, deger: str) -> None:
    sonuc = runner.invoke(cli.app, ["enrich", "glosses", "--wave", deger, "--kok", str(wz.z.kok)])
    assert sonuc.exit_code == 2


def test_enrich_yardimi_dalga_0_ve_1_birlikte_acilir_der() -> None:
    sonuc = runner.invoke(cli.app, ["enrich", "glosses", "--help"], terminal_width=200)
    assert sonuc.exit_code == 0
    metin = " ".join(sonuc.output.split())
    assert "dalga 0 ve 1" in metin and "birlikte" in metin.lower()
    assert "--wave N" in metin


def test_kapsama_raporu_yalniz_sayi_ve_anlam_metni_yok(wz: QuranwbwZinciri) -> None:
    assert wz.ingest() == 0
    assert wz.enrich(1) == 0
    (yol,) = (wz.z.veri_kok / "reports").glob("*-kapsama.json")
    metin = yol.read_text(encoding="utf-8")
    rapor = json.loads(metin)
    assert rapor["tur"] == "anlam-kapsama" and rapor["wave"] == 1
    glosses = wz.staged(KAYNAK, GLOSSES_ADI)
    assert rapor["lemma"] == len(glosses)
    assert rapor["tutarli"] + rapor["tutarsiz"] == len(glosses)
    assert rapor["tutarsiz"] == sum(1 for g in glosses if g["tutarsiz_hazir_anlam"])
    assert sum(rapor["baskin_pay_dagilimi"].values()) == len(glosses)
    anlamlar = {str(a["text"]) for a in wz.staged(KAYNAK, ANLAMLAR_ADI)}
    assert not any(a in metin for a in anlamlar)  # hicbir anlam metni raporda yok
    refler = {str(g["qac_ref"]) for g in glosses}
    assert not any(f'"{r}"' in metin for r in refler)  # qac_ref bile yok: yalniz sayi


# --- qa run ------------------------------------------------------------------------------


def test_qa_uc_kapi_gecer_rapor_alanlari_ve_metin_yok(wz: QuranwbwZinciri) -> None:
    wz.hepsi(1)
    rapor = son_qa_raporu(wz)
    assert rapor["kapilar"] == {"G-KAY": "gecti", "G-BUT": "gecti", "G-CAP": "gecti"}
    assert rapor["cikis_kodu"] == 0 and rapor["wave"] == 1
    assert rapor["anchor_run_id"] == klasorler(wz)[-1].name
    ozet = lineage.sha256_bayt((klasorler(wz)[-1] / GLOSSES_ADI).read_bytes())
    assert rapor["units_sha256"] == ozet
    anlamlar = {str(a["text"]) for a in wz.staged(KAYNAK, ANLAMLAR_ADI)}
    metin = json.dumps(rapor)
    assert not any(a in metin for a in anlamlar)
    assert kaynak_kapilari(KAYNAK) == ("G-KAY", "G-BUT", "G-CAP")


def test_qa_zincir_yoksa_cikis_2(wz: QuranwbwZinciri) -> None:
    assert wz.qa() == 2  # enrich glosses yok


def test_qa_gate_gecersiz_cikis_2_ve_kismi_gate(wz: QuranwbwZinciri) -> None:
    wz.hepsi(1)
    assert (
        run_quranwbw.komut_qa_run_quranwbw(run=None, gate=["G-NOR"], config=None, kok=wz.z.kok) == 2
    )
    assert (
        run_quranwbw.komut_qa_run_quranwbw(run=None, gate=["G-CAP"], config=None, kok=wz.z.kok) == 0
    )


def test_qa_kilit_degisince_g_kay_kalir_cikis_1(wz: QuranwbwZinciri) -> None:
    wz.hepsi(1)
    kilit = json.loads(wz.kilit_yolu.read_text(encoding="utf-8"))
    kilit["url"] = "https://baska.invalid/6.json"
    wz.kilit_yolu.write_text(json.dumps(kilit, indent=2) + "\n", encoding="utf-8", newline="\n")
    assert wz.qa() == 1
    assert son_qa_raporu(wz)["kapilar"]["G-KAY"] == "kaldi"  # type: ignore[index]


def test_g_but_bos_girdi_ve_eksik_kelime_ve_degisen_anlam_yakalar(wz: QuranwbwZinciri) -> None:
    wz.hepsi(1)
    g = girdi(wz)
    assert all(KAPI_ISLEVLERI[k](g).gecti for k in KAPI_ISLEVLERI)
    bos = dataclasses.replace(g, anlam_satirlari=satir_degistir(g.anlam_satirlari, 3, text=""))
    sonuc = g_but(bos)
    assert not sonuc.gecti and any("bos anlam" in b for b in sonuc.bulgular)
    eksik = dataclasses.replace(g, anlam_satirlari=list(g.anlam_satirlari)[1:])
    assert any("farkli" in b or "eksik" in b for b in g_but(eksik).bulgular)
    degisen = dataclasses.replace(
        g, anlam_satirlari=satir_degistir(g.anlam_satirlari, 10, text="Deneme degisti")
    )
    assert any("ham dosyadan yeniden" in b for b in g_but(degisen).bulgular)
    assert all("Deneme degisti" not in b for b in g_but(degisen).bulgular)  # bulgu metin tasimaz
    kontrol = dataclasses.replace(
        g, anlam_satirlari=satir_degistir(g.anlam_satirlari, 4, text="Deneme\x07")
    )
    assert any("kontrol karakteri" in b for b in g_but(kontrol).bulgular)


def test_g_but_ham_dosya_bozuksa_ve_gloss_degisirse_kalir(wz: QuranwbwZinciri) -> None:
    wz.hepsi(1)
    g = girdi(wz)
    bozuk = dataclasses.replace(g, ham=b"{}")
    assert any("yeniden cikarilamadi" in b for b in g_but(bozuk).bulgular)
    degisik = dataclasses.replace(
        g, gloss_satirlari=satir_degistir(g.gloss_satirlari, 0, anlam_kisa="Deneme degisti")
    )
    assert any("glosses" in b for b in g_but(degisik).bulgular)


def test_g_cap_yinelenen_capa_provenance_ve_dalga_farki_yakalar(wz: QuranwbwZinciri) -> None:
    wz.hepsi(1)
    g = girdi(wz)
    ikiz = dataclasses.replace(g, anlam_satirlari=[*g.anlam_satirlari, g.anlam_satirlari[0]])
    assert any("yinelenen" in b or "sirasi" in b for b in g_cap(ikiz).bulgular)
    yanlis = dataclasses.replace(
        g,
        anlam_satirlari=satir_degistir(
            g.anlam_satirlari, 0, provenance={"ham_sha256": "0" * 64, "yol": "/", "cikarici": "x"}
        ),
    )
    assert any("provenance" in b for b in g_cap(yanlis).bulgular)
    dalga = dataclasses.replace(g, gloss_satirlari=satir_degistir(g.gloss_satirlari, 0, dalga=4))
    assert any("dalga" in b for b in g_cap(dalga).bulgular)
    bilinmeyen = dataclasses.replace(
        g, gloss_satirlari=satir_degistir(g.gloss_satirlari, 0, qac_ref="yok-boyle-lemma")
    )
    assert any("QAC lemma" in b for b in g_cap(bilinmeyen).bulgular)
    kay = dataclasses.replace(g, ham=g.ham + b" ")
    assert not g_kay(kay).gecti


def test_ham_dosya_degismez_ve_staged_ikinci_ingest_ayni_bayt(wz: QuranwbwZinciri) -> None:
    assert wz.ingest() == 0
    ilk = wz.staged(KAYNAK, ANLAMLAR_ADI)
    assert wz.ingest(force=True) == 0
    assert wz.staged(KAYNAK, ANLAMLAR_ADI) == ilk
    ham = wz.z.veri_kok / "raw" / KAYNAK / TARIH / DOSYA_ADI
    assert ham.read_bytes() == wz.ham
    assert quranwbw.kilit_yukle(wz.kilit_yolu).sha256 == lineage.sha256_bayt(wz.ham)
