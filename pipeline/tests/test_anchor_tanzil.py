"""`anchor --source tanzil-uthmani` (A10.4): capa, `content_hash`, kuresel ayet sirasi.

Sinirlar ve bicim SENTETIK satirlarla, gercek bayt gereken testler `fixtures/tanzil`
parcalariyla (dosyadan betikle kesilmis 40 ayet) sinanir. Kur'an metni hafizadan yazilmaz.
"""

import hashlib
import json
import unicodedata
from itertools import pairwise
from pathlib import Path
from typing import Any

import pytest
from tanzil_yardimci import PARCA_AYET, PARCA_CAPALAR, parca_oku
from typer.testing import CliRunner, Result
from zincir_yardimci import Zincir, sentetik_dosya, zincir_hazirla

from mutalaa_pipeline import cli, lineage
from mutalaa_pipeline.adimlar.anchor_tanzil import (
    BASLANGIC,
    anchor_satirlari,
    ayet_coz,
    capa_ozetleri,
    kelime_satirlari,
    kuresel_sira,
    onceki_ile_karsilastir,
    run_anchor,
)
from mutalaa_pipeline.adimlar.normalize_tanzil import EK_KAYNAK, KAYNAK
from mutalaa_pipeline.anchor import AnchorRef, Q, parse, sort_key
from mutalaa_pipeline.anchor import format as anchor_format
from mutalaa_pipeline.anchor.ayet_sayilari import AYET_SAYILARI
from mutalaa_pipeline.export import ayet_sayilari, pg
from mutalaa_pipeline.export.ortak import GirdiHatasi, depo_koku
from mutalaa_pipeline.normalize import normalize_ar
from mutalaa_pipeline.staged import Satir
from mutalaa_pipeline.zincir import calismalar, ust_calismalar

runner = CliRunner()

BEH, FETHA, SEDDE = chr(0x0628), chr(0x064E), chr(0x0651)


# --- kuresel sira ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("sure", "ayet", "sira"),
    [(1, 1, 1), (1, 7, 7), (2, 1, 8), (2, 255, 262), (2, 286, 293), (3, 1, 294), (114, 6, 6236)],
)
def test_kuresel_sira_sinirlari(sure: int, ayet: int, sira: int) -> None:
    assert kuresel_sira(sure, ayet) == sira


def test_kuresel_sira_tablodan_bagimsiz_hesapla_ayni_ve_kesintisiz() -> None:
    sayilar = ayet_sayilari.json_oku(depo_koku()).sayilar  # JSON: kodun tablosundan bagimsiz
    beklenen = 0
    for sure, adet in enumerate(sayilar, start=1):
        for ayet in range(1, adet + 1):
            beklenen += 1
            assert kuresel_sira(sure, ayet) == beklenen
    assert beklenen == 6236
    assert BASLANGIC[0] == 0
    assert BASLANGIC[-1] == 6236
    assert len(BASLANGIC) == len(AYET_SAYILARI) + 1


@pytest.mark.parametrize(
    ("capa", "beklenen"),
    [
        ("q:1:1", (1, 1)),
        ("q:2:255", (2, 255)),
        ("q:114:6", (114, 6)),
        ("q:2:255:3", None),  # kelime
        ("q:2:255:3-7", None),  # kelime araligi
        ("q:2:255-257", None),  # ayet araligi
        ("q:2:255@0-10", None),  # kesin aralik
        # Gecerli bicimli kesin aralik bile ayet capasi sayilmaz: gramer `@`i Kur'an capasina
        # eklemez (K-35 madde 6), `ayet_coz` ek bir `span` denetimi tasimaz.
        ("q:2:255@10-20", None),
        ("q:2:255@120-184", None),
        ("meal:elmalili:2:255", None),
        ("q:02:5", None),
        ("Q:2:255", None),
        ("q:115:1", None),
        ("q:2:287", None),
        ("q:0:1", None),
        ("", None),
        ("q:2:255 ", None),
    ],
)
def test_ayet_coz(capa: str, beklenen: tuple[int, int] | None) -> None:
    assert ayet_coz(capa) == beklenen


def test_ayet_coz_ortak_bicimlemeyle_gidis_donus() -> None:
    for sure, ayet in ((1, 1), (2, 255), (114, 6)):
        assert ayet_coz(anchor_format(AnchorRef(Q(sure, ayet)))) == (sure, ayet)


# --- satir donusumu (sentetik) --------------------------------------------------------------

NORMALIZE_ALANLARI = ("anchor", "attrs", "ar_norm", "provenance", "source_id", "text")


def normalize_satiri(capa: str, metin: str, **degisim: object) -> Satir:
    veri: dict[str, object] = {
        "anchor": capa,
        "attrs": {},
        "ar_norm": "x",
        "provenance": {"file": "d.txt", "line": 1, "sha256": "0" * 64, "bayt": [4, 9], "steps": []},
        "source_id": KAYNAK,
        "text": metin,
    }
    veri.update(degisim)
    return Satir("normalize deneme", 1, veri)


def test_anchor_alanlari_ve_kanonik_metin_dokunulmaz() -> None:
    metin = "Deneme " + BEH + SEDDE + FETHA  # sedde + fetha: NFC olmayan sira
    assert unicodedata.normalize("NFC", metin) != metin
    satir = normalize_satiri("q:2:255", metin)
    kopya = json.dumps(satir.veri, sort_keys=True)
    (cikti,) = anchor_satirlari([satir], "1.1")
    assert json.dumps(satir.veri, sort_keys=True) == kopya  # girdi degismez
    assert cikti["text"] == metin  # NFC uygulanmadi
    assert cikti["content_hash"] == hashlib.sha256(metin.encode("utf-8")).hexdigest()
    nfc = unicodedata.normalize("NFC", metin)
    assert cikti["content_hash"] != hashlib.sha256(nfc.encode("utf-8")).hexdigest()
    assert {k: v for k, v in cikti.items() if k in satir.veri} == satir.veri
    assert cikti["kind"] == "ayet"
    assert cikti["metin_durumu"] == "onayli"
    assert cikti["data_version"] == "tanzil-uthmani@1.1"
    assert (cikti["ord"], cikti["ayah_lo"], cikti["ayah_hi"]) == (262, 262, 263)
    assert set(cikti) == set(NORMALIZE_ALANLARI) | {
        "kind",
        "ord",
        "ayah_lo",
        "ayah_hi",
        "content_hash",
        "metin_durumu",
        "data_version",
    }


def test_content_hash_bicimi_64_kucuk_harfli_onaltilik_oneksiz() -> None:
    (cikti,) = anchor_satirlari([normalize_satiri("q:1:1", "Deneme")], "1.1")
    ozet = str(cikti["content_hash"])
    assert len(ozet) == 64
    assert ozet == ozet.lower()
    assert all(c in "0123456789abcdef" for c in ozet)
    assert not ozet.startswith("sha256")


def test_ord_ve_ayah_araligi_sinirlari() -> None:
    satirlar = [normalize_satiri(c, f"Deneme {c}") for c in ("q:1:1", "q:1:7", "q:2:1", "q:114:6")]
    cikti = anchor_satirlari(satirlar, "1.1")
    assert [(c["ord"], c["ayah_lo"], c["ayah_hi"]) for c in cikti] == [
        (1, 1, 2),
        (7, 7, 8),
        (8, 8, 9),
        (6236, 6236, 6237),
    ]
    assert all(int(str(c["ayah_lo"])) < int(str(c["ayah_hi"])) for c in cikti)  # export pg kosulu


@pytest.mark.parametrize("capa", ["q:2:255:3", "q:2:255-257", "q:115:1", "kotu", "Q:2:255"])
def test_ayet_olmayan_capa_reddedilir(capa: str) -> None:
    with pytest.raises(GirdiHatasi, match="kanonik bir ayet capasi degil"):
        anchor_satirlari([normalize_satiri(capa, "Deneme")], "1.1")


def test_alan_kumesi_ve_source_id_kati() -> None:
    eksik = normalize_satiri("q:1:1", "Deneme")
    del eksik.veri["ar_norm"]
    with pytest.raises(GirdiHatasi, match="alan kumesi normalize cikisi degil"):
        anchor_satirlari([eksik], "1.1")
    fazla = normalize_satiri("q:1:1", "Deneme", content_hash="0" * 64)
    with pytest.raises(GirdiHatasi, match="alan kumesi normalize cikisi degil"):
        anchor_satirlari([fazla], "1.1")
    with pytest.raises(GirdiHatasi, match="source_id"):
        anchor_satirlari([normalize_satiri("q:1:1", "Deneme", source_id=EK_KAYNAK)], "1.1")
    with pytest.raises(GirdiHatasi, match="'ar_norm' metin degil"):
        anchor_satirlari([normalize_satiri("q:1:1", "Deneme", ar_norm=5)], "1.1")


# --- onceki calismayla karsilastirma ---------------------------------------------------------


def test_karsilastirma_onceki_yoksa() -> None:
    fark = onceki_ile_karsilastir(None, {"q:1:1": "a" * 64}, None)
    assert (fark.onceki_run_id, fark.ortak, fark.eklenen, fark.kaldirilan, fark.degisen) == (
        None,
        0,
        1,
        (),
        (),
    )


def test_karsilastirma_eklenen_kaldirilan_ve_degisen() -> None:
    onceki = {"q:1:1": "a" * 64, "q:1:2": "b" * 64, "q:1:3": "c" * 64}
    simdiki = {"q:1:1": "a" * 64, "q:1:2": "d" * 64, "q:1:4": "e" * 64}
    fark = onceki_ile_karsilastir(onceki, simdiki, "run-1")
    assert fark.onceki_run_id == "run-1"
    assert fark.ortak == 2
    assert fark.eklenen == 1
    assert fark.kaldirilan == ("q:1:3",)
    assert fark.degisen == ("q:1:2",)
    assert fark.ayrinti() == {
        "run_id": "run-1",
        "ortak": 2,
        "eklenen": 1,
        "kaldirilan": 1,
        "degisen_hash": 1,
    }


def test_capa_ozetleri() -> None:
    satir = Satir("e", 1, {"anchor": "q:1:1", "content_hash": "a" * 64})
    assert capa_ozetleri([satir]) == {"q:1:1": "a" * 64}


# --- komut: zincir halkasi -------------------------------------------------------------------


def parca_zinciri(tmp_path: Path) -> Zincir:
    """Gercek parcalardan ingest x2 ve normalize (anchor henuz kosulmadi)."""
    z = zincir_hazirla(
        tmp_path, {v: parca_oku(v) for v in ("uthmani", "simple-clean")}, tablo=(7, 33)
    )
    z.ingest("uthmani")
    z.ingest("simple-clean")
    z.normalize()
    return z


def satirlar(klasor: Path) -> list[dict[str, Any]]:
    return satirlar_dosya(klasor, "units.jsonl")


def satirlar_dosya(klasor: Path, ad: str) -> list[dict[str, Any]]:
    return [json.loads(s) for s in (klasor / ad).read_bytes().splitlines()]


def anchor_klasoru(z: Zincir, run_id: str) -> Path:
    return z.veri_kok / "staged" / KAYNAK / run_id


def test_anchor_cikti_satirlari(tmp_path: Path) -> None:
    z = parca_zinciri(tmp_path)
    ctx = z.anchor()
    cikti = satirlar(anchor_klasoru(z, ctx.run_id))
    normalize_klasoru = calismalar(ctx, KAYNAK, "normalize")[-1].klasor
    girdi = satirlar(normalize_klasoru)
    assert [c["anchor"] for c in cikti] == PARCA_CAPALAR
    for sira, (g, c) in enumerate(zip(girdi, cikti, strict=True), start=1):
        sure, ayet = (int(x) for x in c["anchor"].split(":")[1:])
        assert (c["ord"], c["ayah_lo"], c["ayah_hi"]) == (kuresel_sira(sure, ayet),) * 2 + (
            kuresel_sira(sure, ayet) + 1,
        )
        assert c["ord"] == sira  # parca 1:1'den kesintisiz
        assert c["text"] == g["text"]
        assert c["content_hash"] == hashlib.sha256(g["text"].encode("utf-8")).hexdigest()
        assert (c["kind"], c["metin_durumu"], c["data_version"]) == (
            "ayet",
            "onayli",
            "tanzil-uthmani@1.1",
        )
        assert {k: v for k, v in c.items() if k in g} == g
    assert cikti[0]["ord"] == 1
    assert cikti[-1]["ord"] == PARCA_AYET


def test_anchor_cikisi_export_pg_sozlesmesine_uyar(tmp_path: Path) -> None:
    z = parca_zinciri(tmp_path)
    ctx = z.anchor()
    veri = (anchor_klasoru(z, ctx.run_id) / "units.jsonl").read_bytes()
    assert veri.isascii()
    satirlar_pg = pg._satirlari_oku(veri, KAYNAK)  # veritabani gerekmez
    assert len(satirlar_pg) == PARCA_AYET
    pg._icerik_ozeti_denetle(satirlar_pg)  # content_hash metnin SHA-256'si
    for alan in pg.GEREKLI_ALANLAR:
        assert alan in json.loads(veri.splitlines()[0])
    assert all(s.ar_norm and s.metin_durumu == "onayli" and s.kind == "ayet" for s in satirlar_pg)
    assert all("ar_norm" in s.provenance for s in satirlar_pg)


def test_manifest_zincir_halkasi(tmp_path: Path) -> None:
    z = parca_zinciri(tmp_path)
    ctx = z.anchor()
    klasor = anchor_klasoru(z, ctx.run_id)
    manifest = json.loads((klasor / "manifest.json").read_bytes())
    normalize = calismalar(ctx, KAYNAK, "normalize")[-1]
    assert manifest["adim"] == pg.ANCHOR_ADIMI == "anchor"
    assert manifest["girdiler"] == [
        {
            "yol": f"staged/{KAYNAK}/{normalize.run_id}/units.jsonl",
            "sha256": normalize.cikti_ozeti(),
            "ust_run_id": normalize.run_id,
        }
    ]
    assert [c["yol"] for c in manifest["ciktilar"]] == [
        f"staged/{KAYNAK}/{ctx.run_id}/units.jsonl",
        f"staged/{KAYNAK}/{ctx.run_id}/words.jsonl",
    ]
    assert manifest["ciktilar"][0]["satir"] == PARCA_AYET
    kelime_sayisi = len(satirlar_dosya(klasor, "words.jsonl"))
    assert manifest["ciktilar"][1]["satir"] == kelime_sayisi > PARCA_AYET
    assert manifest["ayrintilar"]["kelime"] == kelime_sayisi
    ayrintilar = manifest["ayrintilar"]
    assert ayrintilar["normalize_run"] == normalize.run_id
    assert ayrintilar["data_version"] == "tanzil-uthmani@1.1"
    assert ayrintilar["ord_araligi"] == [1, PARCA_AYET]
    assert ayrintilar["onceki"]["run_id"] is None
    assert lineage.ciktilar_saglam(z.veri_kok, manifest)
    # export pg'nin zincir yuruyusu: anchor -> normalize -> iki ingest
    anchor = calismalar(ctx, KAYNAK, "anchor")[-1]
    assert [(u.adim, u.source_id) for u in ust_calismalar(ctx, anchor)] == [("normalize", KAYNAK)]


def test_ikinci_calistirma_ayni_cikti_ve_onceki_karsilastirma(tmp_path: Path) -> None:
    z = parca_zinciri(tmp_path)
    ilk = z.anchor(temiz_git=False)
    ikinci = z.anchor(temiz_git=False)
    assert (anchor_klasoru(z, ilk.run_id) / "units.jsonl").read_bytes() == (
        anchor_klasoru(z, ikinci.run_id) / "units.jsonl"
    ).read_bytes()
    manifest = json.loads((anchor_klasoru(z, ikinci.run_id) / "manifest.json").read_bytes())
    assert manifest["ayrintilar"]["onceki"] == {
        "run_id": ilk.run_id,
        "ortak": PARCA_AYET,
        "eklenen": 0,
        "kaldirilan": 0,
        "degisen_hash": 0,
    }
    assert ikinci.uyarilar == []
    assert ikinci.sayilar["onceki_ortak"] == PARCA_AYET


def test_parmak_izi_ayniysa_atlanir_force_ve_kirli_agac_atlamaz(tmp_path: Path) -> None:
    z = parca_zinciri(tmp_path)
    ilk = z.anchor()
    klasorler = sorted((z.veri_kok / "staged" / KAYNAK).iterdir())
    ctx = z.ctx("anchor", [KAYNAK], temiz_git=True)
    sonuc = run_anchor(ctx)
    assert (sonuc.atlandi, sonuc.klasor, sonuc.onceki_run_id) == (True, None, ilk.run_id)
    assert ctx.sayilar["atlandi"] == 1
    assert sorted((z.veri_kok / "staged" / KAYNAK).iterdir()) == klasorler
    assert run_anchor(z.ctx("anchor", [KAYNAK], temiz_git=True, force=True)).atlandi is False
    assert run_anchor(z.ctx("anchor", [KAYNAK], temiz_git=False)).atlandi is False


def test_normalize_yeniden_kosulunca_anchor_atlanmaz_ve_yeni_calismaya_baglanir(
    tmp_path: Path,
) -> None:
    """Parmak izi run_id icermez; ama anchor en son normalize calismasina bagli kalmalidir."""
    z = parca_zinciri(tmp_path)
    ilk = z.anchor()
    z.normalize(force=True)  # ayni ciktiyla yeni normalize calismasi
    normalizeler = calismalar(ilk, KAYNAK, "normalize")
    assert len(normalizeler) == 2

    sonuc = run_anchor(z.ctx("anchor", [KAYNAK], temiz_git=True))
    assert sonuc.atlandi is False  # ust calisma degisti: yeniden uretilir
    son = calismalar(ilk, KAYNAK, "anchor")[-1]
    assert son.run_id != ilk.run_id
    assert [(u.adim, u.run_id) for u in ust_calismalar(ilk, son)] == [
        ("normalize", normalizeler[-1].run_id)
    ]
    assert (son.klasor / "units.jsonl").read_bytes() == (
        anchor_klasoru(z, ilk.run_id) / "units.jsonl"
    ).read_bytes()

    assert run_anchor(z.ctx("anchor", [KAYNAK], temiz_git=True)).atlandi is True


def test_dry_run_hicbir_sey_yazmaz(tmp_path: Path) -> None:
    z = parca_zinciri(tmp_path)
    once = sorted((z.veri_kok / "staged").rglob("*"))
    ctx = z.ctx("anchor", [KAYNAK], temiz_git=True, dry_run=True)
    sonuc = run_anchor(ctx)
    assert (sonuc.birim_sayisi, sonuc.klasor) == (PARCA_AYET, None)
    assert sorted((z.veri_kok / "staged").rglob("*")) == once


def test_kaybolan_capa_ve_degisen_ozet_uyari_verir(tmp_path: Path) -> None:
    uthmani_5 = sentetik_dosya("uthmani", (7, 5))
    simple_5 = sentetik_dosya("simple-clean", (7, 5))
    z = zincir_hazirla(tmp_path, {"uthmani": uthmani_5, "simple-clean": simple_5}, (7, 5))
    z.ingest("uthmani")
    z.ingest("simple-clean")
    z.normalize(temiz_git=False)
    z.anchor(temiz_git=False)
    # yeni surum: 2:5 yok (kaybolan capa) ve 1:1 metni degisti (ozet farki)
    z.tablo = (7, 4)
    yeni_u = sentetik_dosya("uthmani", (7, 4)).replace(b"1|1|", b"1|1|X", 1)
    yeni_s = sentetik_dosya("simple-clean", (7, 4)).replace(b"1|1|", b"1|1|X", 1)
    z.ingest("uthmani", tarih="2026-11-03", veri=yeni_u)
    z.ingest("simple-clean", tarih="2026-11-03", veri=yeni_s)
    z.normalize(temiz_git=False)
    ctx = z.anchor(temiz_git=False)
    assert ctx.sayilar["onceki_kaldirilan"] == 1
    assert ctx.sayilar["onceki_degisen_hash"] == 1
    assert ctx.sayilar["onceki_ortak"] == 11
    assert any("1 capa kayip" in u for u in ctx.uyarilar)
    assert any("1 capada content_hash degisti" in u for u in ctx.uyarilar)
    manifest = json.loads((anchor_klasoru(z, ctx.run_id) / "manifest.json").read_bytes())
    assert manifest["ayrintilar"]["onceki"]["kaldirilan"] == 1


def test_normalize_yoksa_ipucuyla_hata(tmp_path: Path) -> None:
    z = zincir_hazirla(tmp_path, {v: parca_oku(v) for v in ("uthmani", "simple-clean")}, (7, 33))
    z.ingest("uthmani")
    z.ingest("simple-clean")
    with pytest.raises(GirdiHatasi, match="normalize --source"):
        z.anchor()


def test_normalize_ciktisi_bozulmussa_hata(tmp_path: Path) -> None:
    z = parca_zinciri(tmp_path)
    units = calismalar(z.ctx("anchor", [KAYNAK]), KAYNAK, "normalize")[-1].klasor / "units.jsonl"
    units.write_bytes(units.read_bytes() + b"\n")
    with pytest.raises(GirdiHatasi, match="ciktilari saglam degil"):
        z.anchor()


def test_kayitta_surum_yoksa_hata(tmp_path: Path) -> None:
    z = parca_zinciri(tmp_path)
    yol = z.kok / "pipeline" / "sources" / f"{KAYNAK}.toml"
    yol.write_text(
        "".join(
            s for s in yol.read_text(encoding="utf-8").splitlines(keepends=True) if "surum" not in s
        ),
        encoding="utf-8",
        newline="\n",
    )
    with pytest.raises(GirdiHatasi, match="surum cozulemedi"):
        z.anchor()
    assert not any(
        json.loads((p.parent / "manifest.json").read_bytes())["adim"] == "anchor"
        for p in (z.veri_kok / "staged" / KAYNAK).glob("*/units.jsonl")
    )


# --- CLI -------------------------------------------------------------------------------------


def cli_anchor(z: Zincir, monkeypatch: pytest.MonkeyPatch, *argumanlar: str) -> Result:
    monkeypatch.setenv("MUTALAA_VERI_KOK", str(z.veri_kok))
    return runner.invoke(cli.app, ["anchor", *argumanlar, "--kok", str(z.kok)])


def staged_klasorleri(z: Zincir) -> list[str]:
    return sorted(p.name for p in (z.veri_kok / "staged" / KAYNAK).iterdir())


def test_cli_anchor_basarili(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    z = parca_zinciri(tmp_path)
    once = staged_klasorleri(z)
    sonuc = cli_anchor(z, monkeypatch, "--source", KAYNAK)
    assert sonuc.exit_code == 0, sonuc.stderr
    assert sonuc.stdout.startswith(f"anchor {KAYNAK}: {PARCA_AYET} birim, ")
    assert " kelime, run " in sonuc.stdout
    (yeni,) = set(staged_klasorleri(z)) - set(once)
    manifest = json.loads((z.veri_kok / "staged" / KAYNAK / yeni / "manifest.json").read_bytes())
    assert (manifest["adim"], manifest["komut"]) == ("anchor", f"anchor --source {KAYNAK}")
    raporlar = [json.loads(p.read_bytes()) for p in (z.veri_kok / "reports").glob("*.json")]
    (rapor,) = [r for r in raporlar if r["adim"] == "anchor"]
    assert rapor["kaynaklar"] == [KAYNAK]
    assert rapor["sayilar"]["birim"] == PARCA_AYET
    yazilanlar = b"".join(p.read_bytes() for p in (z.veri_kok / "reports").glob("*.json"))
    yazilanlar += b"".join(p.read_bytes() for p in (z.veri_kok / "logs").glob("*.jsonl"))
    assert b"\\u06" not in yazilanlar


def test_cli_dry_run_yazmaz(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    z = parca_zinciri(tmp_path)
    once = staged_klasorleri(z)
    sonuc = cli_anchor(z, monkeypatch, "--source", KAYNAK, "--dry-run")
    assert sonuc.exit_code == 0, sonuc.stderr
    assert "dry-run, hicbir sey yazilmadi" in sonuc.stdout
    assert staged_klasorleri(z) == once


@pytest.mark.parametrize(
    ("argumanlar", "parca"),
    [
        (["--source", EK_KAYNAK], "tanimli degil"),
        (["--source", "baska-kaynak"], "tanimli degil"),
        (["--source", KAYNAK, "--limit", "5"], "--limit"),
    ],
)
def test_cli_hatali_cagrilar_cikis_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, argumanlar: list[str], parca: str
) -> None:
    z = parca_zinciri(tmp_path)
    once = staged_klasorleri(z)
    sonuc = cli_anchor(z, monkeypatch, *argumanlar)
    assert sonuc.exit_code == 2
    assert parca in sonuc.stderr
    assert staged_klasorleri(z) == once


# --- kelime bolmesi: words.jsonl (A11.2, K-43) -----------------------------------------------

DURAK = chr(0x06D6)


def test_kelime_satirlari_alanlari_ve_dilim_esitligi(tmp_path: Path) -> None:
    z = parca_zinciri(tmp_path)
    ctx = z.anchor()
    klasor = anchor_klasoru(z, ctx.run_id)
    ayetler = {s["anchor"]: s for s in satirlar(klasor)}
    kelimeler = satirlar_dosya(klasor, "words.jsonl")
    assert (klasor / "words.jsonl").read_bytes().isascii()  # ASCII kacisli (editor NFC yapmasin)
    alanlar = {
        "anchor",
        "surah",
        "ayah",
        "word",
        "ayah_index",
        "text_uthmani",
        "norm",
        "char_start",
        "char_end",
        "source_id",
        "data_version",
    }
    beklenen_sira = [sort_key(parse(k["anchor"])) for k in kelimeler]  # satirlar okuma sirasinda
    assert beklenen_sira == sorted(beklenen_sira)
    for k in kelimeler:
        assert set(k) == alanlar
        assert k["anchor"] == f"q:{k['surah']}:{k['ayah']}:{k['word']}"
        ayet = ayetler[f"q:{k['surah']}:{k['ayah']}"]
        assert k["ayah_index"] == ayet["ord"]
        assert ayet["text"][k["char_start"] : k["char_end"]] == k["text_uthmani"]
        assert k["norm"] == normalize_ar(k["text_uthmani"]) != ""
        assert (k["source_id"], k["data_version"]) == (KAYNAK, ayet["data_version"])
    assert {f"q:{k['surah']}:{k['ayah']}" for k in kelimeler} == set(ayetler)  # her ayette kelime


def test_kelime_numaralari_ayet_icinde_1den_kesintisiz_araliklar_ortusmez(tmp_path: Path) -> None:
    z = parca_zinciri(tmp_path)
    klasor = anchor_klasoru(z, z.anchor().run_id)
    gruplar: dict[str, list[dict[str, Any]]] = {}
    for k in satirlar_dosya(klasor, "words.jsonl"):
        gruplar.setdefault(f"q:{k['surah']}:{k['ayah']}", []).append(k)
    for capa, grup in gruplar.items():
        assert [k["word"] for k in grup] == list(range(1, len(grup) + 1)), capa
        for onceki, sonraki in pairwise(grup):
            assert onceki["char_end"] <= sonraki["char_start"], capa


def test_gercek_parcada_besmele_oneki_atilir_sure_1_in_besmelesi_sayilir(tmp_path: Path) -> None:
    """Parca gercek Tanzil metnidir: 2:1'in ilk dort belirteci kelime almaz, 1:1'inki alir."""
    z = parca_zinciri(tmp_path)
    klasor = anchor_klasoru(z, z.anchor().run_id)
    ayetler = {s["anchor"]: s["text"] for s in satirlar(klasor)}
    kelimeler = satirlar_dosya(klasor, "words.jsonl")

    def ayet_kelimeleri(capa: str) -> list[dict[str, Any]]:
        return [k for k in kelimeler if f"q:{k['surah']}:{k['ayah']}" == capa]

    for capa, besmele_onekli in (("q:1:1", False), ("q:2:1", True), ("q:2:2", False)):
        belirtecler = ayetler[capa].split(" ")
        kelime_belirteci = [
            b for b in belirtecler[4 if besmele_onekli else 0 :] if not durak_yalniz(b)
        ]
        grup = ayet_kelimeleri(capa)
        assert [k["text_uthmani"] for k in grup] == kelime_belirteci, capa
        if besmele_onekli:
            assert grup[0]["char_start"] == len(" ".join(belirtecler[:4])) + 1
        else:
            assert grup[0]["char_start"] == 0 or durak_yalniz(belirtecler[0])


def durak_yalniz(belirtec: str) -> bool:
    return belirtec != "" and all(0x06D6 <= ord(h) <= 0x06ED for h in belirtec)


def test_kelime_dosyasi_ikinci_calistirmada_ayni(tmp_path: Path) -> None:
    z = parca_zinciri(tmp_path)
    ilk = z.anchor(temiz_git=False)
    ikinci = z.anchor(temiz_git=False)
    assert (anchor_klasoru(z, ilk.run_id) / "words.jsonl").read_bytes() == (
        anchor_klasoru(z, ikinci.run_id) / "words.jsonl"
    ).read_bytes()
    assert ikinci.sayilar["kelime"] == ilk.sayilar["kelime"] > PARCA_AYET


def test_eski_bicim_anchor_calismasi_kelime_dosyasi_yoksa_atlanmaz(tmp_path: Path) -> None:
    """A11.2 oncesi anchor calismasi `words.jsonl` listelemez: atlanmaz, yeniden uretilir."""
    z = parca_zinciri(tmp_path)
    ilk = z.anchor()
    klasor = anchor_klasoru(z, ilk.run_id)
    manifest = json.loads((klasor / "manifest.json").read_bytes())
    manifest["ciktilar"] = [
        c for c in manifest["ciktilar"] if not c["yol"].endswith("/words.jsonl")
    ]
    lineage.manifest_yaz(klasor, manifest)
    sonuc = run_anchor(z.ctx("anchor", [KAYNAK], temiz_git=True))
    assert sonuc.atlandi is False
    assert sonuc.kelime_sayisi > 0


def test_dry_run_kelime_dosyasi_yazmaz_ama_sayar(tmp_path: Path) -> None:
    z = parca_zinciri(tmp_path)
    once = sorted((z.veri_kok / "staged").rglob("*"))
    sonuc = run_anchor(z.ctx("anchor", [KAYNAK], temiz_git=True, dry_run=True))
    assert sonuc.kelime_sayisi > PARCA_AYET
    assert sorted((z.veri_kok / "staged").rglob("*")) == once


def anchor_birimi(capa: str, metin: str) -> dict[str, object]:
    return {"anchor": capa, "text": metin, "ord": 8}


def test_kelime_satirlari_besmele_icin_yetersiz_belirtec_girdi_hatasi() -> None:
    with pytest.raises(GirdiHatasi) as hata:
        kelime_satirlari([anchor_birimi("q:2:1", "Deneme bir iki")], "1.1")
    assert "q:2:1" in str(hata.value)
    assert "Deneme" not in str(hata.value)


def test_kelime_satirlari_norm_bos_cikarsa_girdi_hatasi() -> None:
    """Tatweel (U+0640) kelimedir (durak degil) ama normalize sonrasi bos kalir: hata."""
    with pytest.raises(GirdiHatasi) as hata:
        kelime_satirlari([anchor_birimi("q:3:2", BEH + " " + chr(0x0640))], "1.1")
    assert "q:3:2:2" in str(hata.value)
    assert "norm bos" in str(hata.value)


def test_kelime_satirlari_gecersiz_anchor_satiri() -> None:
    for birim in (
        {"anchor": "q:2:255:3", "text": "a b", "ord": 1},  # ayet capasi degil
        {"anchor": "q:3:2", "text": 5, "ord": 1},
        {"anchor": "q:3:2", "text": "a b"},
    ):
        with pytest.raises(GirdiHatasi):
            kelime_satirlari([birim], "1.1")


def test_kelime_satirlari_durak_belirteci_atlanir_ve_metin_donusturulmez() -> None:
    metin = f"{BEH}{FETHA}{SEDDE} {DURAK} {BEH}"
    satir = kelime_satirlari([anchor_birimi("q:3:2", metin)], "1.1")
    assert [(k["word"], k["text_uthmani"]) for k in satir] == [
        (1, f"{BEH}{FETHA}{SEDDE}"),
        (2, BEH),
    ]
    assert satir[0]["text_uthmani"] == metin[0:3]  # NFC degil dizi aynen
    assert (satir[0]["char_start"], satir[0]["char_end"]) == (0, 3)
    assert (satir[1]["char_start"], satir[1]["char_end"]) == (6, 7)
