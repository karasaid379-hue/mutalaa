"""`normalize --source tanzil-uthmani` (A10.4): `ar_norm`, AR-4 ve zincir halkasi.

AR-4 birim testleri SENTETIK harf dizileriyle yazilir (`chr()` ile kurulur; hicbir ayet ya da
baska metinden alinti degildir). Gercek bayt gereken testler `fixtures/tanzil` parcalarini
(dosyadan betikle kesilmis 40 ayet) kullanir ve beklenen degeri formulden hesaplar; Kur'an
metni testte hafizadan yazilmaz.
"""

import json
from pathlib import Path
from typing import Any

import pytest
from tanzil_yardimci import PARCA_AYET, PARCA_CAPALAR, parca_oku
from typer.testing import CliRunner, Result
from zincir_yardimci import Zincir, sentetik_dosya, zincir_hazirla

from mutalaa_pipeline import cli, lineage
from mutalaa_pipeline.adimlar.normalize_tanzil import (
    EK_KAYNAK,
    KAYNAK,
    ar4_birlestir,
    ar_norm_uret,
    run_normalize,
)
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.ingest import tanzil_bicim
from mutalaa_pipeline.normalize import NORMALIZER_VERSION, normalize_ar
from mutalaa_pipeline.staged import satir_baytlari
from mutalaa_pipeline.zincir import calismalar, ust_calismalar

runner = CliRunner()

BEH, TEH, THEH, JEEM, HAH, KHAH = (chr(k) for k in (0x0628, 0x062A, 0x062B, 0x062C, 0x062D, 0x062E))
ELIF, ELIF_VASLA = chr(0x0627), chr(0x0671)
FETHA, SEDDE, HANCER_ELIF = chr(0x064E), chr(0x0651), chr(0x0670)
LATINCE = "Deneme latince"  # Arapca bloklarda harf yok: normalize_ar bos doner


def cumle(*kelimeler: str) -> str:
    return " ".join(kelimeler)


A, B, C = BEH + TEH, THEH + JEEM, HAH + KHAH  # sentetik "kelimeler"


# --- AR-4 birim testleri (sentetik) --------------------------------------------------------


def test_ek_yoksa_ar_norm_simple_clean_normalize_halidir() -> None:
    simple = cumle(A, B)
    uthmani = cumle(BEH + FETHA + TEH + HANCER_ELIF, THEH + SEDDE + FETHA + JEEM)  # yalniz isaret
    assert normalize_ar(uthmani) == normalize_ar(simple)
    assert ar_norm_uret(simple, uthmani) == normalize_ar(simple) == cumle(A, B)
    assert ar4_birlestir(normalize_ar(simple), normalize_ar(uthmani)) == (cumle(A, B), 0)


def test_ek_sozcukler_uthmani_sirasiyla_sona_eklenir() -> None:
    simple = cumle(A, B)
    uthmani = cumle(A, C, B, A + ELIF)  # C ve A+ELIF Simple Clean'de yok
    assert ar_norm_uret(simple, uthmani) == cumle(A, B, C, A + ELIF)
    assert ar4_birlestir(cumle(A, B), cumle(A, C, B, A + ELIF)) == (cumle(A, B, C, A + ELIF), 2)


def test_ek_sozcukler_tekrarsizdir_ilk_gorulme_sirasi_korunur() -> None:
    assert ar4_birlestir(cumle(A), cumle(C, B, C, B, C)) == (cumle(A, C, B), 2)


def test_simple_clean_tarafi_tekrarlariyla_aynen_korunur() -> None:
    assert ar4_birlestir(cumle(A, A, B), cumle(A, B, C)) == (cumle(A, A, B, C), 1)


def test_sozcuk_kumesi_uyeligi_siraya_bakmaz() -> None:
    assert ar4_birlestir(cumle(A, B), cumle(B, A, C)) == (cumle(A, B, C), 1)
    assert ar4_birlestir(cumle(A, B), cumle(B, A)) == (cumle(A, B), 0)


def test_yazim_farki_normalizeden_sonra_esitse_eklenmez() -> None:
    simple = cumle(ELIF + BEH, TEH)
    uthmani = cumle(ELIF_VASLA + BEH, TEH)  # elif vasla normalize edilince elif olur
    assert ar_norm_uret(simple, uthmani) == normalize_ar(simple)


def test_bos_taraflar() -> None:
    assert ar4_birlestir("", "") == ("", 0)
    assert ar4_birlestir("", cumle(A, B)) == (cumle(A, B), 2)  # yalniz ek sozcukler
    assert ar4_birlestir(cumle(A), "") == (cumle(A), 0)
    assert ar_norm_uret(LATINCE, LATINCE) == ""
    assert ar_norm_uret(LATINCE, A) == A


def test_ar_norm_uret_girdiyi_degistirmez_ve_belirlenimcidir() -> None:
    simple = cumle(A + FETHA, B)
    uthmani = cumle(A, C + SEDDE + FETHA, B)
    kopyalar = (str(simple), str(uthmani))
    ilk = ar_norm_uret(simple, uthmani)
    assert (simple, uthmani) == kopyalar
    assert all(ar_norm_uret(simple, uthmani) == ilk for _ in range(3))


# --- gercek parca uzerinde AR-4 (formulle hesaplanan beklenen) ------------------------------


def parca_ayetleri(varyant: str) -> dict[str, str]:
    ayrisma = tanzil_bicim.ayristir(parca_oku(varyant), tam=False)
    return {ay.capa: ay.metin for ay in ayrisma.ayetler}


def test_gercek_parcada_ar4_ozellikleri() -> None:
    uthmani, simple = parca_ayetleri("uthmani"), parca_ayetleri("simple-clean")
    assert list(uthmani) == list(simple) == PARCA_CAPALAR
    ekli = 0
    for capa in PARCA_CAPALAR:
        taban = normalize_ar(simple[capa])
        ar_norm = ar_norm_uret(simple[capa], uthmani[capa])
        assert ar_norm.startswith(taban)
        ek = ar_norm[len(taban) :].split(" ")[1:]
        assert len(ek) == len(set(ek))  # tekrarsiz
        assert not set(ek) & set(taban.split(" "))  # Simple Clean kumesindekiler eklenmez
        uthmani_sozcukler = normalize_ar(uthmani[capa]).split(" ")
        assert set(ek) <= set(uthmani_sozcukler)
        assert ek == [s for s in dict.fromkeys(uthmani_sozcukler) if s in set(ek)]  # ilk gorulme
        ekli += 1 if ek else 0
    assert 0 < ekli < PARCA_AYET  # parcada hem eki olan hem olmayan ayet var


# --- komut: zincir halkasi -----------------------------------------------------------------


def parca_zinciri(tmp_path: Path) -> Zincir:
    """Gercek parcalardan ingest x2 (normalize henuz kosulmadi)."""
    z = zincir_hazirla(
        tmp_path, {v: parca_oku(v) for v in ("uthmani", "simple-clean")}, tablo=(7, 33)
    )
    z.ingest("uthmani")
    z.ingest("simple-clean")
    return z


def satirlar(klasor: Path) -> list[dict[str, Any]]:
    return [json.loads(s) for s in (klasor / "units.jsonl").read_bytes().splitlines()]


def son_klasor(z: Zincir, kaynak: str, adim: str) -> Path:
    kayitlar = calismalar(z.ctx(adim, [kaynak]), kaynak, adim)
    assert kayitlar
    return kayitlar[-1].klasor


def test_normalize_satirlari_ve_provenance(tmp_path: Path) -> None:
    z = parca_zinciri(tmp_path)
    ctx = z.normalize()
    ingest_u = satirlar(son_klasor(z, KAYNAK, "ingest"))
    ingest_s = satirlar(son_klasor(z, EK_KAYNAK, "ingest"))
    cikti = satirlar(z.veri_kok / "staged" / KAYNAK / ctx.run_id)
    assert [s["anchor"] for s in cikti] == PARCA_CAPALAR
    ham_simple = lineage.sha256_bayt(z.veriler["simple-clean"])
    for u, s, c in zip(ingest_u, ingest_s, cikti, strict=True):
        beklenen_kok = dict(u["provenance"])
        beklenen_kok["ar_norm"] = {
            "kaynak": "tanzil-simple-clean",
            "sha256": ham_simple,
            "line": s["provenance"]["line"],
            "normalizer_version": NORMALIZER_VERSION,
            "ar4": True,
        }
        assert set(c) == set(u) | {"ar_norm"}
        assert c["text"] == u["text"]  # kanonik metin dokunulmadi
        assert (c["source_id"], c["attrs"]) == (KAYNAK, {})
        assert c["provenance"] == beklenen_kok
        assert c["ar_norm"] == ar_norm_uret(s["text"], u["text"])
    assert not any(alan in c for c in cikti for alan in ("tr_narrow", "tr_wide", "tr_stem"))


def test_kanonik_metin_ham_dosyanin_bayt_dilimidir_ar_norm_ayri_alandir(tmp_path: Path) -> None:
    z = parca_zinciri(tmp_path)
    ctx = z.normalize()
    ham = z.veriler["uthmani"]
    ayrisma = tanzil_bicim.ayristir(ham, (7, 33))
    cikti = satirlar(z.veri_kok / "staged" / KAYNAK / ctx.run_id)
    for satir, ay in zip(cikti, ayrisma.ayetler, strict=True):
        assert satir["text"].encode("utf-8") == ham[ay.bayt_bas : ay.bayt_son]
        assert satir["provenance"]["bayt"] == [ay.bayt_bas, ay.bayt_son]
        assert satir["ar_norm"] != satir["text"]


def test_manifest_zincir_halkasi(tmp_path: Path) -> None:
    z = parca_zinciri(tmp_path)
    ctx = z.normalize()
    klasor = z.veri_kok / "staged" / KAYNAK / ctx.run_id
    manifest = json.loads((klasor / "manifest.json").read_bytes())
    ing_u = son_klasor(z, KAYNAK, "ingest").name
    ing_s = son_klasor(z, EK_KAYNAK, "ingest").name
    assert manifest["adim"] == "normalize"
    girdiler = {g["yol"]: g for g in manifest["girdiler"]}
    assert set(girdiler) == {
        f"staged/{KAYNAK}/{ing_u}/units.jsonl",
        f"staged/{EK_KAYNAK}/{ing_s}/units.jsonl",
    }
    assert girdiler[f"staged/{KAYNAK}/{ing_u}/units.jsonl"]["ust_run_id"] == ing_u
    assert girdiler[f"staged/{EK_KAYNAK}/{ing_s}/units.jsonl"]["ust_run_id"] == ing_s
    assert [c["yol"] for c in manifest["ciktilar"]] == [f"staged/{KAYNAK}/{ctx.run_id}/units.jsonl"]
    assert manifest["ciktilar"][0]["satir"] == PARCA_AYET
    ayrintilar = manifest["ayrintilar"]
    assert ayrintilar["ingest"] == {KAYNAK: ing_u, EK_KAYNAK: ing_s}
    assert ayrintilar["normalizer_version"] == NORMALIZER_VERSION
    assert ayrintilar["ar4"] is True
    assert ayrintilar["birim"] == PARCA_AYET
    assert 0 < ayrintilar["ar4_ek_ayet"] < PARCA_AYET
    assert lineage.ciktilar_saglam(z.veri_kok, manifest)
    # export pg'nin zincir yuruyusu: normalize iki ingest calistirmasina baglanir
    ustler = ust_calismalar(ctx, calismalar(ctx, KAYNAK, "normalize")[-1])
    assert sorted((u.adim, u.source_id) for u in ustler) == [
        ("ingest", EK_KAYNAK),
        ("ingest", KAYNAK),
    ]


def test_ikinci_calistirma_ayni_cikti(tmp_path: Path) -> None:
    z = parca_zinciri(tmp_path)
    ilk = z.normalize(temiz_git=False)
    ikinci = z.normalize(temiz_git=False)  # kirli agac: atlama yok, yeniden uretilir
    assert ilk.run_id != ikinci.run_id
    ilk_bayt = (z.veri_kok / "staged" / KAYNAK / ilk.run_id / "units.jsonl").read_bytes()
    ikinci_bayt = (z.veri_kok / "staged" / KAYNAK / ikinci.run_id / "units.jsonl").read_bytes()
    assert ilk_bayt == ikinci_bayt
    assert ilk_bayt.isascii()  # ASCII kacisli: editor NFC'si metni degistirmesin


def test_parmak_izi_ayniysa_atlanir_force_ve_kirli_agac_atlamaz(tmp_path: Path) -> None:
    z = parca_zinciri(tmp_path)
    ilk = z.normalize()
    klasorler = sorted((z.veri_kok / "staged" / KAYNAK).iterdir())
    ikinci_ctx = z.ctx("normalize", [KAYNAK, EK_KAYNAK], temiz_git=True)
    sonuc = run_normalize(ikinci_ctx)
    assert sonuc.atlandi is True
    assert sonuc.onceki_run_id == ilk.run_id
    assert sonuc.klasor is None
    assert ikinci_ctx.sayilar["atlandi"] == 1
    assert sorted((z.veri_kok / "staged" / KAYNAK).iterdir()) == klasorler  # yeni klasor yok

    zorla = run_normalize(z.ctx("normalize", [KAYNAK, EK_KAYNAK], temiz_git=True, force=True))
    assert zorla.atlandi is False
    kirli = run_normalize(z.ctx("normalize", [KAYNAK, EK_KAYNAK], temiz_git=False))
    assert kirli.atlandi is False


def test_ust_ingest_yeniden_kosulunca_normalize_atlanmaz_ve_yeni_calismaya_baglanir(
    tmp_path: Path,
) -> None:
    """Parmak izi run_id icermez; ama zincir `export pg` icin en son ingest'e bagli kalmalidir."""
    z = parca_zinciri(tmp_path)
    ilk = z.normalize()
    z.ingest("uthmani", force=True)  # ayni baytlarla yeni ingest calismasi
    yeni_ingest = son_klasor(z, KAYNAK, "ingest").name
    ilk_ingest = {c.run_id for c in calismalar(ilk, KAYNAK, "ingest")} - {yeni_ingest}
    assert len(ilk_ingest) == 1

    sonuc = run_normalize(z.ctx("normalize", [KAYNAK, EK_KAYNAK], temiz_git=True))
    assert sonuc.atlandi is False  # ust calisma degisti: yeniden uretilir
    manifest = json.loads((son_klasor(z, KAYNAK, "normalize") / "manifest.json").read_bytes())
    yollar = {g["yol"] for g in manifest["girdiler"]}
    assert f"staged/{KAYNAK}/{yeni_ingest}/units.jsonl" in yollar
    assert not any(ilk_ingest & set(yol.split("/")) for yol in yollar)
    ilk_bayt = (z.veri_kok / "staged" / KAYNAK / ilk.run_id / "units.jsonl").read_bytes()
    assert (son_klasor(z, KAYNAK, "normalize") / "units.jsonl").read_bytes() == ilk_bayt

    assert run_normalize(z.ctx("normalize", [KAYNAK, EK_KAYNAK], temiz_git=True)).atlandi is True


def test_dry_run_hicbir_sey_yazmaz(tmp_path: Path) -> None:
    z = parca_zinciri(tmp_path)
    once = sorted((z.veri_kok / "staged").rglob("*"))
    ctx = z.ctx("normalize", [KAYNAK, EK_KAYNAK], temiz_git=True, dry_run=True)
    sonuc = run_normalize(ctx)
    assert sonuc.birim_sayisi == PARCA_AYET
    assert sonuc.klasor is None
    assert sorted((z.veri_kok / "staged").rglob("*")) == once
    assert ctx.sayilar["birim"] == PARCA_AYET


def test_ingest_yoksa_ipucuyla_hata(tmp_path: Path) -> None:
    z = zincir_hazirla(tmp_path, {v: parca_oku(v) for v in ("uthmani", "simple-clean")}, (7, 33))
    with pytest.raises(GirdiHatasi, match="ingest tanzil --variant uthmani"):
        z.normalize()
    z.ingest("uthmani")
    with pytest.raises(GirdiHatasi, match="ingest tanzil --variant simple-clean"):
        z.normalize()


def test_ingest_ciktisi_bozulmussa_hata(tmp_path: Path) -> None:
    z = parca_zinciri(tmp_path)
    units = son_klasor(z, EK_KAYNAK, "ingest") / "units.jsonl"
    units.write_bytes(units.read_bytes().replace(b"q:1:1", b"q:1:2", 1))
    with pytest.raises(GirdiHatasi, match="ciktilari saglam degil"):
        z.normalize()


def test_capa_kumeleri_farkliysa_hata(tmp_path: Path) -> None:
    z = zincir_hazirla(
        tmp_path,
        {
            "uthmani": sentetik_dosya("uthmani", (7, 5)),
            "simple-clean": sentetik_dosya("simple-clean", (7, 4)),
        },
        (7, 5),
    )
    z.ingest("uthmani")
    z.tablo = (7, 4)  # Simple Clean dosyasi bir ayet eksik
    z.ingest("simple-clean")
    with pytest.raises(GirdiHatasi, match=r"capa kumeleri ayni degil: yalniz uthmani 1 \(q:2:5\)"):
        z.normalize()


def test_ingest_alan_kumesi_beklenenden_farkliysa_hata(tmp_path: Path) -> None:
    z = parca_zinciri(tmp_path)
    klasor = son_klasor(z, KAYNAK, "ingest")
    kayitlar = satirlar(klasor)
    kayitlar[0]["ar_norm"] = "x"  # normalize cikisi ingest girdisi olamaz
    yeni = b"".join(satir_baytlari(k) for k in kayitlar)
    (klasor / "units.jsonl").write_bytes(yeni)
    manifest = json.loads((klasor / "manifest.json").read_bytes())
    for cikti in manifest["ciktilar"]:
        if cikti["yol"].endswith("units.jsonl"):
            cikti["sha256"] = lineage.sha256_bayt(yeni)
    lineage.manifest_yaz(klasor, manifest)  # manifest ozeti tutar: alan kumesi tek kusur
    with pytest.raises(GirdiHatasi, match="alan kumesi ingest cikisi degil"):
        z.normalize()


def test_kayitsiz_kaynak_hata(tmp_path: Path) -> None:
    z = parca_zinciri(tmp_path)
    (z.kok / "pipeline" / "sources" / f"{EK_KAYNAK}.toml").unlink()
    with pytest.raises(GirdiHatasi, match="kayitsiz"):
        z.normalize()


# --- CLI -----------------------------------------------------------------------------------


def cli_normalize(z: Zincir, monkeypatch: pytest.MonkeyPatch, *argumanlar: str) -> Result:
    monkeypatch.setenv("MUTALAA_VERI_KOK", str(z.veri_kok))
    return runner.invoke(cli.app, ["normalize", *argumanlar, "--kok", str(z.kok)])


def staged_klasorleri(z: Zincir, kaynak: str) -> list[str]:
    return sorted(p.name for p in (z.veri_kok / "staged" / kaynak).iterdir())


def test_cli_normalize_basarili_ozet_ve_rapor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    z = parca_zinciri(tmp_path)
    once = staged_klasorleri(z, KAYNAK)
    sonuc = cli_normalize(z, monkeypatch, "--source", KAYNAK)
    assert sonuc.exit_code == 0, sonuc.stderr
    assert sonuc.stdout.startswith(f"normalize {KAYNAK}: {PARCA_AYET} birim, run ")
    (yeni,) = set(staged_klasorleri(z, KAYNAK)) - set(once)
    assert (
        json.loads((z.veri_kok / "staged" / KAYNAK / yeni / "manifest.json").read_bytes())["komut"]
        == f"normalize --source {KAYNAK}"
    )
    raporlar = [json.loads(p.read_bytes()) for p in (z.veri_kok / "reports").glob("*.json")]
    (rapor,) = [r for r in raporlar if r["adim"] == "normalize"]
    assert rapor["cikis_kodu"] == 0
    assert rapor["kaynaklar"] == [KAYNAK, EK_KAYNAK]
    assert rapor["sayilar"]["birim"] == PARCA_AYET
    assert rapor["parametreler"] == {"source": KAYNAK}
    yazilanlar = b"".join(p.read_bytes() for p in (z.veri_kok / "reports").glob("*.json"))
    yazilanlar += b"".join(p.read_bytes() for p in (z.veri_kok / "logs").glob("*.jsonl"))
    assert b"\\u06" not in yazilanlar  # Arapca metin rapora ve gunluge girmez


def test_cli_dry_run_yazmaz(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    z = parca_zinciri(tmp_path)
    once = staged_klasorleri(z, KAYNAK)
    sonuc = cli_normalize(z, monkeypatch, "--source", KAYNAK, "--dry-run")
    assert sonuc.exit_code == 0, sonuc.stderr
    assert "dry-run, hicbir sey yazilmadi" in sonuc.stdout
    assert staged_klasorleri(z, KAYNAK) == once


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
    once = staged_klasorleri(z, KAYNAK)
    sonuc = cli_normalize(z, monkeypatch, *argumanlar)
    assert sonuc.exit_code == 2
    assert parca in sonuc.stderr
    assert staged_klasorleri(z, KAYNAK) == once


def test_cli_ingest_yoksa_cikis_2(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    z = zincir_hazirla(tmp_path, {v: parca_oku(v) for v in ("uthmani", "simple-clean")}, (7, 33))
    sonuc = cli_normalize(z, monkeypatch, "--source", KAYNAK)
    assert sonuc.exit_code == 2
    assert "ingest tanzil --variant uthmani" in sonuc.stderr
