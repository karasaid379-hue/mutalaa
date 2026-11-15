"""Risale (Diyanet) zinciri: ingest -> qa run (A20.1; SENTETIK zip, veritabani yok).

Zip bellekte uretilir ve sahte `data/gelen` altina konur; kilit ve kimlik tablosu gecici
dosyalardir. Gercek `data/` ve gercek Risale metni kullanilmaz. Veritabanina hicbir sey yazilmaz.
"""

import dataclasses
import json
from pathlib import Path

import pytest
from hat_yardimci import TEMIZ_GIT, ansisiz
from risale_yardimci import (
    COMMIT,
    KAYNAK,
    TARIH,
    UYELER_1,
    ZIP_ADI,
    RisaleKoku,
    risale_hazirla,
    zip_yap,
)
from typer.testing import CliRunner

from mutalaa_pipeline import cli, lineage
from mutalaa_pipeline.ingest import risale_diyanet, risale_kaynaklari
from mutalaa_pipeline.qa import run_risale
from mutalaa_pipeline.qa.checks.risale import RisaleGirdisi, g_but, g_kay
from mutalaa_pipeline.staged import Satir

runner = CliRunner()


@pytest.fixture
def rk(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> RisaleKoku:
    return risale_hazirla(tmp_path, monkeypatch)


def girdi(rk: RisaleKoku) -> RisaleGirdisi:
    ctx = rk.ctx("qa")
    kayitlar = ctx.require_sources((KAYNAK,))
    return run_risale.yukle(ctx, kayitlar[KAYNAK], run=None)[0]


def son_rapor(rk: RisaleKoku) -> dict[str, object]:
    raporlar = [
        json.loads(r.read_bytes()) for r in sorted((rk.veri_kok / "reports").glob("*.json"))
    ]
    return [r for r in raporlar if r.get("komut") == "qa run" and r.get("kaynak") == KAYNAK][-1]  # type: ignore[no-any-return]


def satir_degistir(satirlar: object, indeks: int, **alanlar: object) -> list[Satir]:
    liste = list(satirlar)  # type: ignore[call-overload]
    ilk = liste[indeks]
    liste[indeks] = Satir(ilk.etiket, ilk.no, {**ilk.veri, **alanlar})
    return liste


def indeks(g: RisaleGirdisi, capa: str) -> int:
    return next(i for i, s in enumerate(g.birim_satirlari) if s.veri["anchor"] == capa)


# --- ingest --------------------------------------------------------------------------------


def test_ingest_ham_kopya_staged_ve_manifest(rk: RisaleKoku) -> None:
    assert rk.ingest() == 0
    ham = rk.veri_kok / "raw" / KAYNAK / TARIH / ZIP_ADI
    assert ham.read_bytes() == rk.zip_baytlari  # data/raw bayt bayt, zip islenmeden
    assert (rk.veri_kok / "raw" / KAYNAK / TARIH / "fetch.json").is_file()
    (klasor,) = rk.staged_klasorleri()
    manifest = lineage.manifest_oku(klasor)
    assert manifest is not None and manifest["adim"] == "ingest"
    ayrinti = manifest["ayrintilar"]
    assert ayrinti["commit"] == COMMIT and ayrinti["birim"] == 16  # type: ignore[index]
    assert ayrinti["kitaplar"]["deneme"]["birim"] == 14  # type: ignore[index]
    assert ayrinti["eksik_bolum_numaralari"] == {"deneme": ["soz-2"]}  # type: ignore[index]
    units = rk.units()
    assert len(units) == 16 and all(u["source_id"] == KAYNAK for u in units)
    # veri kokunde zip acilmis dosya yok: raw ve gelen disinda yalniz staged/logs/reports
    assert not list((rk.veri_kok).rglob("*.txt")) and not list((rk.veri_kok).rglob("*.md"))


def test_staged_ascii_kacisli_ve_capaya_gore_sirali(rk: RisaleKoku) -> None:
    assert rk.ingest() == 0
    klasor = rk.staged_klasorleri()[-1]
    ham = (klasor / "units.jsonl").read_bytes()
    assert ham.isascii() and b"\r" not in ham and ham.endswith(b"\n")
    capalar = [u["anchor"] for u in rk.units()]
    assert capalar[0] == "rn:deneme:soz-1:p1" and capalar[-1] == "rn:kucuk-deneme:p2"
    assert len(capalar) == len(set(capalar))


def test_ingest_kilit_uyusmazligi_cikis_2_raw_ve_staged_bos(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    degisen = dict(UYELER_1) | {"txt/02 Kucuk/Kucuk.txt": b"Deneme baska icerik\n"}
    rk = risale_hazirla(tmp_path, monkeypatch, uyeler=degisen, kilit_uyeleri=UYELER_1)
    assert rk.ingest() == 2
    assert not (rk.veri_kok / "raw" / KAYNAK).exists()
    assert rk.staged_klasorleri() == []


def test_ingest_gelen_zip_yoksa_cikis_2(rk: RisaleKoku) -> None:
    rk.gelen_zip.unlink()
    assert rk.ingest() == 2
    assert not (rk.veri_kok / "raw" / KAYNAK).exists()


def test_ingest_guvensiz_zip_cikis_2(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rk = risale_hazirla(tmp_path, monkeypatch)
    kotu = zip_yap(UYELER_1) + b"x"  # bozuk ek bayt: ozet kilitle tutmaz
    rk.gelen_zip.write_bytes(kotu)
    assert rk.ingest() == 2
    assert not (rk.veri_kok / "raw" / KAYNAK).exists()


def test_ingest_dry_run_hicbir_sey_yazmaz(rk: RisaleKoku) -> None:
    assert rk.ingest(dry_run=True) == 0
    assert not (rk.veri_kok / "raw" / KAYNAK).exists()
    assert rk.staged_klasorleri() == []


def test_ingest_ikinci_kosu_temiz_agacta_atlanir(
    rk: RisaleKoku, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(lineage, "git_durumu", lambda _kok: TEMIZ_GIT)
    assert rk.ingest() == 0
    assert rk.ingest() == 0
    assert len(rk.staged_klasorleri()) == 1  # yeni staged klasoru acilmadi (parmak izi ayni)
    assert len(list((rk.veri_kok / "raw" / KAYNAK).iterdir())) == 1


def test_ingest_ikinci_kosu_kirli_agacta_ayni_bayt_ve_ham_degismez(rk: RisaleKoku) -> None:
    assert rk.ingest() == 0
    ilk = (rk.staged_klasorleri()[-1] / "units.jsonl").read_bytes()
    assert rk.ingest() == 0  # kirli agac atlamayi kapatir: yeni calisma, AYNI bayt
    klasorler = rk.staged_klasorleri()
    assert len(klasorler) == 2
    assert (klasorler[-1] / "units.jsonl").read_bytes() == ilk  # idempotent: 0 degisiklik
    ham_klasorler = list((rk.veri_kok / "raw" / KAYNAK).iterdir())
    assert len(ham_klasorler) == 1  # ayni baytlar icin yeni ham kopya acilmaz
    assert (ham_klasorler[0] / ZIP_ADI).read_bytes() == rk.zip_baytlari


def test_ingest_force_atlanmayi_kapatir(rk: RisaleKoku, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(lineage, "git_durumu", lambda _kok: TEMIZ_GIT)
    assert rk.ingest() == 0
    assert rk.ingest(force=True) == 0
    assert len(rk.staged_klasorleri()) == 2


def test_kayit_yoksa_cikis_2(rk: RisaleKoku) -> None:
    (rk.kok / "pipeline" / "sources" / f"{KAYNAK}.toml").unlink()
    assert rk.ingest() == 2
    assert rk.staged_klasorleri() == []


# --- CLI -----------------------------------------------------------------------------------


def test_cli_ingest_risale_calisir_ve_yardim_metni(rk: RisaleKoku) -> None:
    sonuc = runner.invoke(cli.app, ["ingest", "risale", "--source", KAYNAK, "--kok", str(rk.kok)])
    assert sonuc.exit_code == 0, sonuc.output
    assert "16 birim" in sonuc.output
    yardim = ansisiz(runner.invoke(cli.app, ["ingest", "risale", "--help"]).output)
    for ad in ("--source", "--gelen-tarih", "--kilit-oner", "--dry-run", "--force", "--limit"):
        assert ad in yardim
    assert "risale" in ansisiz(runner.invoke(cli.app, ["ingest", "--help"]).output)


def test_cli_cikis_kodlari(rk: RisaleKoku) -> None:
    def kos(*arg: str) -> int:
        return runner.invoke(cli.app, ["ingest", "risale", *arg, "--kok", str(rk.kok)]).exit_code

    assert kos("--source", "bilinmeyen") == 2
    assert kos("--source", KAYNAK, "--limit", "5") == 2
    assert kos("--source", KAYNAK, "--kilit-oner", "--dry-run") == 2
    assert kos("--source", KAYNAK, "--kilit-oner", "--force") == 2
    assert kos("--source", KAYNAK, "--gelen-tarih", "2026-13-45") == 2
    assert kos("--source", KAYNAK, "--dry-run") == 0
    assert rk.staged_klasorleri() == []
    assert (
        runner.invoke(cli.app, ["ingest", "risale", "--kok", str(rk.kok)]).exit_code == 2
    )  # --source yok


def test_cli_kilit_oner_hesaplanan_kilitle_ayni_ve_hicbir_sey_yazmaz(rk: RisaleKoku) -> None:
    sonuc = runner.invoke(
        cli.app, ["ingest", "risale", "--source", KAYNAK, "--kilit-oner", "--kok", str(rk.kok)]
    )
    assert sonuc.exit_code == 0
    assert sonuc.output.encode("utf-8") == rk.kilit_yolu.read_bytes()
    assert not (rk.veri_kok / "raw" / KAYNAK).exists() and rk.staged_klasorleri() == []


def test_cli_qa_run_yardimi_ve_cikis(rk: RisaleKoku) -> None:
    assert rk.ingest() == 0
    sonuc = runner.invoke(cli.app, ["qa", "run", "--source", KAYNAK, "--kok", str(rk.kok)])
    assert sonuc.exit_code == 0, sonuc.output
    assert "G-KAY gecti" in sonuc.output and "G-BUT gecti" in sonuc.output
    assert "--gate" in ansisiz(runner.invoke(cli.app, ["qa", "run", "--help"]).output)


def test_kaynak_kaydi_modulu() -> None:
    assert risale_kaynaklari.risale_mi(KAYNAK) and not risale_kaynaklari.risale_mi("tanzil-uthmani")
    assert not risale_kaynaklari.risale_mi(None)
    k = risale_kaynaklari.kaynak(KAYNAK)
    assert not k.yukleme and k.kapilar == ("G-KAY", "G-BUT")  # DB'ye yuklenmez, G-CAP yok
    assert risale_kaynaklari.bagdastirici_modulu(KAYNAK) is risale_diyanet


# --- QA ------------------------------------------------------------------------------------


def test_qa_iki_kapi_gecer_rapor_alanlari_ve_metin_yok(rk: RisaleKoku) -> None:
    assert rk.ingest() == 0
    assert rk.qa() == 0
    rapor = son_rapor(rk)
    assert rapor["kapilar"] == {"G-KAY": "gecti", "G-BUT": "gecti"}
    assert rapor["olcumler"]["toplam_birim"] == 16  # type: ignore[index]
    assert rapor["kapi_sayilari"]["G-BUT"]["staged_birim"] == 16  # type: ignore[index]
    assert rapor["ingest_run_id"] and rapor["units_sha256"]
    # rapor ve gunluklerde birim metni yok
    for dosya in (rk.veri_kok).rglob("*"):
        if (
            dosya.is_file()
            and dosya.suffix in {".json", ".jsonl", ".log"}
            and "staged" not in dosya.parts
        ):
            govde = dosya.read_bytes().decode("utf-8", "replace")
            assert "Deneme paragraf" not in govde and "Deneme dipnotu" not in govde


def test_qa_zincir_yoksa_cikis_2_gate_gecersizse_2_kismi_gate_0(rk: RisaleKoku) -> None:
    assert rk.qa() == 2  # ingest yok
    assert rk.ingest() == 0
    assert rk.qa(gate=["G-CAP"]) == 2  # G-CAP bu kaynakta yok
    assert rk.qa(gate=["G-NOR"]) == 2
    assert rk.qa(gate=["G-BUT"]) == 0
    assert son_rapor(rk)["kapilar"] == {"G-BUT": "gecti"}


def test_qa_g_kay_kayit_surumu_kilitle_ayni_degilse_kalir(rk: RisaleKoku) -> None:
    assert rk.ingest() == 0
    g = girdi(rk)
    assert g_kay(g).gecti
    yanlis = dataclasses.replace(g, kayit=dataclasses.replace(g.kayit, surum="0" * 40))
    assert not g_kay(yanlis).gecti
    adres = dataclasses.replace(
        g, kayit=dataclasses.replace(g.kayit, kaynak_url="https://x.invalid")
    )
    assert not g_kay(adres).gecti
    bos = dataclasses.replace(g, kayit=dataclasses.replace(g.kayit, atif_metni="  "))
    assert any("atif_metni bos" in b for b in g_kay(bos).bulgular)
    tur = dataclasses.replace(g, kayit=dataclasses.replace(g.kayit, tur="kuran_metni"))
    assert not g_kay(tur).gecti
    ham = dataclasses.replace(g, ham=g.ham + b"x")
    assert not g_kay(ham).gecti
    commit = dataclasses.replace(g, ingest_commit="1" * 40)
    assert not g_kay(commit).gecti


def test_qa_g_kay_kilit_degisince_cikis_1(rk: RisaleKoku) -> None:
    assert rk.ingest() == 0
    veri = json.loads(rk.kilit_yolu.read_text(encoding="utf-8"))
    veri["depo_url"] = risale_diyanet.DEPO_ONEKI + "-baska"
    rk.kilit_yolu.write_bytes((json.dumps(veri, indent=1, sort_keys=True) + "\n").encode("utf-8"))
    assert rk.qa() == 1  # kayit kaynak_url kilitle ayni degil


def test_g_but_temiz_zincirde_gecer_ve_sayilar(rk: RisaleKoku) -> None:
    assert rk.ingest() == 0
    sonuc = g_but(girdi(rk))
    assert sonuc.gecti, sonuc.bulgular
    assert sonuc.sayilar["staged_birim"] == 16 and sonuc.sayilar["md_birimi"] == 1
    assert sonuc.sayilar["txt_birimi"] == 15 and sonuc.sayilar["bos_birim"] == 0


def test_g_but_degisen_metin_eksik_ve_fazla_birim_yakalar(rk: RisaleKoku) -> None:
    assert rk.ingest() == 0
    g = girdi(rk)
    i = indeks(g, "rn:deneme:soz-1:p3")
    degisen = dataclasses.replace(
        g, birim_satirlari=satir_degistir(g.birim_satirlari, i, text="Deneme degisti")
    )
    sonuc = g_but(degisen)
    assert not sonuc.gecti
    assert any("farkli birim" in b for b in sonuc.bulgular)
    assert any("kaynak satir baytlariyla ayni degil" in b for b in sonuc.bulgular)
    eksik = dataclasses.replace(g, birim_satirlari=list(g.birim_satirlari)[1:])
    assert any("eksik birim" in b for b in g_but(eksik).bulgular)
    fazla = [
        *g.birim_satirlari,
        Satir("x", 99, {**g.birim_satirlari[0].veri, "anchor": "rn:deneme:soz-1:p99"}),
    ]
    assert any(
        "fazla birim" in b for b in g_but(dataclasses.replace(g, birim_satirlari=fazla)).bulgular
    )


def test_g_but_bos_birim_yakalar(rk: RisaleKoku) -> None:
    assert rk.ingest() == 0
    g = girdi(rk)
    i = indeks(g, "rn:deneme:soz-1:p3")
    bos = dataclasses.replace(
        g, birim_satirlari=satir_degistir(g.birim_satirlari, i, text=" \N{NO-BREAK SPACE}")
    )
    sonuc = g_but(bos)
    assert sonuc.sayilar["bos_birim"] == 1 and not sonuc.gecti


def test_g_but_txt_birimi_baska_satirin_baytlarini_tasirsa_yakalar(rk: RisaleKoku) -> None:
    """Yeniden uretilenle ayni gorunse de bagimsiz satir denetimi bayt esitligini kanitlar."""
    assert rk.ingest() == 0
    g = girdi(rk)
    i = indeks(g, "rn:deneme:soz-1:p3")
    satir = g.birim_satirlari[i]
    prov = {**satir.veri["provenance"], "satir": 1}  # type: ignore[dict-item]
    kaydirilmis = dataclasses.replace(
        g, birim_satirlari=satir_degistir(g.birim_satirlari, i, provenance=prov)
    )
    assert any("kaynak satir baytlariyla" in b for b in g_but(kaydirilmis).bulgular)


def test_g_but_nfc_uygulanmis_metin_yakalar(rk: RisaleKoku) -> None:
    assert rk.ingest() == 0
    g = girdi(rk)
    i = indeks(g, "rn:deneme:soz-1:p7")
    nfc = __import__("unicodedata").normalize("NFC", str(g.birim_satirlari[i].veri["text"]))
    assert nfc != g.birim_satirlari[i].veri["text"]  # sentetik satir gercekten NFC degil
    sonuc = g_but(
        dataclasses.replace(g, birim_satirlari=satir_degistir(g.birim_satirlari, i, text=nfc))
    )
    assert not sonuc.gecti


def test_g_but_md_kaynagi_yalniz_dipnotta_kabul_edilir(rk: RisaleKoku) -> None:
    assert rk.ingest() == 0
    g = girdi(rk)
    i = indeks(g, "rn:deneme:soz-1:p3")
    prov = {**g.birim_satirlari[i].veri["provenance"], "kaynak": "md"}  # type: ignore[dict-item]
    sonuc = g_but(
        dataclasses.replace(
            g, birim_satirlari=satir_degistir(g.birim_satirlari, i, provenance=prov)
        )
    )
    assert not sonuc.gecti


def test_g_but_kilit_disi_karakter_kapiyi_kaldirir(rk: RisaleKoku) -> None:
    assert rk.ingest() == 0
    g = girdi(rk)
    kitap = g.kilit.kitaplar["deneme"]
    assert kitap.karakterler == {"U+00A0": 1, "U+00AD": 1, "U+200C": 1}
    # 1) kilitte bir karakter eksik: staged'de ona esit karakter "kilit disi" kalir
    eksik = dict(kitap.karakterler)
    eksik.pop("U+00AD")
    kilit = dataclasses.replace(
        g.kilit,
        kitaplar={**g.kilit.kitaplar, "deneme": dataclasses.replace(kitap, karakterler=eksik)},
    )
    sonuc = g_but(dataclasses.replace(g, kilit=kilit))
    assert any("kilitli karakter sayilari kilitle ayni degil (U+00AD" in b for b in sonuc.bulgular)
    # 2) kilitteki sayi farkli
    fazla = {**kitap.karakterler, "U+200C": 2}
    kilit2 = dataclasses.replace(
        g.kilit,
        kitaplar={**g.kilit.kitaplar, "deneme": dataclasses.replace(kitap, karakterler=fazla)},
    )
    assert not g_but(dataclasses.replace(g, kilit=kilit2)).gecti
    # 3) staged metne kilit disi Cf (U+200B) girerse
    i = indeks(g, "rn:deneme:soz-1:p3")
    metin = str(g.birim_satirlari[i].veri["text"]) + "\N{ZERO WIDTH SPACE}"
    cf = dataclasses.replace(g, birim_satirlari=satir_degistir(g.birim_satirlari, i, text=metin))
    sonuc = g_but(cf)
    assert any("kilitli karakter sayilari" in b for b in sonuc.bulgular)
    # 4) degistirme karakteri
    fffd = dataclasses.replace(
        g,
        birim_satirlari=satir_degistir(
            g.birim_satirlari,
            i,
            text=metin.replace("\N{ZERO WIDTH SPACE}", "\N{REPLACEMENT CHARACTER}"),
        ),
    )
    assert any("U+FFFD" in b for b in g_but(fffd).bulgular)


def test_g_but_kilitli_sayi_ve_izinli_dipnot_listesi(rk: RisaleKoku) -> None:
    assert rk.ingest() == 0
    g = girdi(rk)
    kitap = g.kilit.kitaplar["deneme"]
    sayilar = {**kitap.sayilar, "dipnot_tanimi_md": kitap.sayilar["dipnot_tanimi_md"] + 1}
    kilit = dataclasses.replace(
        g.kilit,
        kitaplar={**g.kilit.kitaplar, "deneme": dataclasses.replace(kitap, sayilar=sayilar)},
    )
    sonuc = g_but(dataclasses.replace(g, kilit=kilit))
    assert any("deneme: kilitli sayilar" in b and "dipnot_tanimi_md" in b for b in sonuc.bulgular)
    # yeni (izinli listede olmayan) tanim/atif uyusmazligi: kilitte listelenen sayida degil
    liste = dataclasses.replace(kitap, dipnot_uyusmazliklari=(("txt/x.txt", 2, 1),))
    kilit2 = dataclasses.replace(g.kilit, kitaplar={**g.kilit.kitaplar, "deneme": liste})
    assert any(
        "izinli listeyle ayni degil" in b
        for b in g_but(dataclasses.replace(g, kilit=kilit2)).bulgular
    )


def test_g_but_yeni_dipnot_uyusmazligi_izinli_listede_degilse_kalir(
    rk: RisaleKoku, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert rk.ingest() == 0
    g = girdi(rk)
    # ham zip'te markdown'a atifsiz bir tanim eklenir: kilitte yok
    degisen = dict(UYELER_1)
    md_ad = "obsidian-markdown/01 Deneme/01 Birinci.md"
    degisen[md_ad] = degisen[md_ad] + "\n[^hâşiye9]: Deneme atifsiz dipnot.\n".encode()
    yeni = zip_yap(degisen)
    sonuc = g_but(dataclasses.replace(g, ham=yeni))
    assert not sonuc.gecti
    assert any("izinli listeyle ayni degil" in b for b in sonuc.bulgular)


def test_g_but_ham_zip_bozuksa_bulgu_yazar_cikmaz(rk: RisaleKoku) -> None:
    assert rk.ingest() == 0
    g = girdi(rk)
    sonuc = g_but(dataclasses.replace(g, ham=b"zip degil"))
    assert not sonuc.gecti
    assert any("guvenli bicimde okunamadi" in b for b in sonuc.bulgular)


def test_qa_ham_dosya_degisirse_cikis_2(rk: RisaleKoku) -> None:
    assert rk.ingest() == 0
    ham = next((rk.veri_kok / "raw" / KAYNAK).iterdir()) / ZIP_ADI
    ham.write_bytes(ham.read_bytes() + b"x")  # data/raw degismez: ozet tutmaz
    assert rk.qa() == 2
