"""Lugat kapsama raporu `qa risale-rapor --rapor lugat` (A20.6b; SENTETIK veri, veritabani yok).

Birimler "denemea", "denemeb" ... gibi anlamsiz sozcuklerden olusur; kitap tablosu iki sahte kitap
(`deneme-tr` Turkce, `deneme-ota` Osmanlica) tasir. Rapor yalniz sayi ve oran icerir; karsiliksiz
sozcuk listesi ayri yerel dosyadadir (rapora girmez).
"""

import hashlib
import json
from pathlib import Path

import pytest
from lugat_kaynak_yardimci import (
    TANIM_RG,
    TANIM_RNK,
    KaynakKoku,
    kaynak_hazirla,
    tam_zincir,
)
from lugat_yardimci import KITAP_A, KITAP_B, sentetik_zip
from typer.testing import CliRunner

from mutalaa_pipeline import cli
from mutalaa_pipeline.anchor import risale
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.qa import lugat_kapsama
from mutalaa_pipeline.qa.lugat_kapsama import (
    KARSILIKSIZ_ADI,
    RAPOR_ADI,
    metin_sozcukleri_raporu,
    sozcuk_say,
    terkip_raporu,
    terkipli_oku,
)

runner = CliRunner()
RUN_UUID = "01a1d225-8f55-7309-b24f-34684721026c"
TR_KITAP = "deneme-tr"
OTA_KITAP = "deneme-ota"
TERKIPLI_A = "kelime,frekans\ndenemee deneme f,5\ndenemea denemeb,3\nbozuk satir\n"
TERKIPLI_B = "kelime,frekans\ndenemee deneme f,2\n"


def kitap(slug: str, dil: risale.Dil) -> risale.Kitap:
    return risale.Kitap(
        slug=slug,
        baslik="Deneme",
        dil=dil,
        yon="ltr" if dil == "tr" else "rtl",
        metin_kaynagi="rnk",
        diyanet_karsiligi="rnk",
        diyanet=None,
        rnk=risale.RnkBaglanti("tr", "uid", "Deneme"),
        dogrulandi=False,
    )


def birim(slug: str, no: int, dar: str | None, kok: str | None) -> dict[str, object]:
    return {"anchor": f"rn:{slug}:p{no}", "tr_narrow": dar, "tr_stem": kok}


BIRIMLER = [
    birim(
        TR_KITAP,
        1,
        "denemea denemeb yenia xyzzy denemedx 12 denemea",
        "denemea denemeb yenia xyzzy denemed 12 denemea",
    ),
    birim(TR_KITAP, 2, "xyzzy denemea", "xyzzy denemea"),
    birim(TR_KITAP, 3, "", ""),  # metinsiz
    birim(OTA_KITAP, 1, None, None),  # Turkce olmayan kitap
    birim(OTA_KITAP, 2, "yabanci", "yabanci"),  # okunmaz
]


def anchor_run_yaz(kz: KaynakKoku, birimler: list[dict[str, object]], adim: str = "anchor") -> None:
    klasor = kz.veri_kok / "staged" / "risale-rnk-metin" / RUN_UUID
    klasor.mkdir(parents=True, exist_ok=True)
    govde = "".join(json.dumps(b, sort_keys=True) + "\n" for b in birimler).encode("utf-8")
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


@pytest.fixture
def kz(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> KaynakKoku:
    zip_verisi = sentetik_zip(terkipli={KITAP_A: TERKIPLI_A, KITAP_B: TERKIPLI_B})
    kok = kaynak_hazirla(tmp_path, monkeypatch, zip_verisi=zip_verisi)
    tam_zincir(kok)
    anchor_run_yaz(kok, BIRIMLER)
    tablo = (kitap(TR_KITAP, "tr"), kitap(OTA_KITAP, "ota"))
    monkeypatch.setattr(lugat_kapsama.risale, "kitaplar", lambda: tablo)
    return kok


def rapor_calistir(kz: KaynakKoku, *ek: str) -> int:
    return runner.invoke(
        cli.app, ["qa", "risale-rapor", "--rapor", "lugat", *ek, "--kok", str(kz.kok)]
    ).exit_code


def rapor_oku(kz: KaynakKoku) -> dict[str, object]:
    return json.loads((kz.veri_kok / "reports" / "a20" / RAPOR_ADI).read_bytes())


# --- saf islevler ------------------------------------------------------------------------------


def test_sozcuk_say_yalniz_turkce_kitap_rakamlari_ve_metinsizi_atlar() -> None:
    gecis, govde, sayilar = sozcuk_say(BIRIMLER, frozenset({TR_KITAP}))
    assert sayilar == {"birim": 5, "turkce_birim": 3, "metinsiz_birim": 1}
    assert gecis["denemea"] == 3 and gecis["xyzzy"] == 2 and "12" not in gecis
    assert "yabanci" not in gecis  # Osmanlica kitap okunmaz
    assert govde["denemedx"] == "denemed"  # tr_stem ayni konumdaki sozcuk


def test_sozcuk_say_konum_sayisi_tutmazsa_govde_sozcugun_kendisi() -> None:
    gecis, govde, _ = sozcuk_say([birim(TR_KITAP, 1, "abc def", "abc")], frozenset({TR_KITAP}))
    assert gecis == {"abc": 1, "def": 1} and govde == {"abc": "abc", "def": "def"}


def test_sozcuk_say_capasiz_birim_girdi_hatasi() -> None:
    with pytest.raises(GirdiHatasi):
        sozcuk_say([{"tr_narrow": "a"}], frozenset())


def test_metin_sozcukleri_raporu_yalin_govde_ve_siklik_dilimleri() -> None:
    gecis = {"denemea": 120, "denemedx": 3, "xyzzy": 2, "qqqq": 1}
    govde = {"denemea": "denemea", "denemedx": "denemed", "xyzzy": "xyzzy", "qqqq": "qqqq"}
    rnk = [("denemea", "denemea")]
    rg = [("denemed", "denemed")]
    rapor, karsiliksiz = metin_sozcukleri_raporu(gecis, govde, rnk, rg)
    assert rapor["benzersiz_sozcuk"] == 4 and rapor["toplam_gecis"] == 126
    hepsi = rapor["rnk_ve_rganeyev"]
    assert hepsi["yalin"]["sozcuk"] == {"sayi": 1, "yuzde": 25.0}  # type: ignore[index]
    assert hepsi["yalniz_govde"]["gecis"] == {"sayi": 3, "yuzde": 2.38}  # type: ignore[index]
    assert hepsi["karsiliksiz"]["sozcuk"]["sayi"] == 2  # type: ignore[index]
    yalniz_rnk = rapor["yalniz_rnk"]
    assert yalniz_rnk["yalniz_govde"]["sozcuk"]["sayi"] == 0  # type: ignore[index]  # rganeyev katkisi
    assert karsiliksiz == [("xyzzy", 2), ("qqqq", 1)]  # gecis azalan, esitlikte alfabetik
    assert rapor["karsiliksiz_siklik_dilimleri"] == {
        "1": {"sozcuk": 1, "gecis": 1},
        "2-4": {"sozcuk": 1, "gecis": 2},
        "5-19": {"sozcuk": 0, "gecis": 0},
        "20-99": {"sozcuk": 0, "gecis": 0},
        "100+": {"sozcuk": 0, "gecis": 0},
    }


def test_terkipli_oku_bosluklu_terkip_baslik_ve_bozuk_satir() -> None:
    sayac, bozuk = terkipli_oku(TERKIPLI_A.encode())
    assert sayac == {"denemee deneme f": 5, "denemea denemeb": 3} and bozuk == 1
    with pytest.raises(GirdiHatasi, match="baslik"):
        terkipli_oku(b"kelime;frekans\na,1\n")
    with pytest.raises(GirdiHatasi, match="UTF-8"):
        terkipli_oku(b"kelime,frekans\n\xff,1\n")
    sayac, bozuk = terkipli_oku(b"kelime,frekans\n,3\na b,x\n")
    assert sayac == {} and bozuk == 2


def test_terkip_raporu_rnk_cok_sozcuklu_baslik_ve_sozcuk_siniri() -> None:
    rnk = [("denemee deneme f", "x"), ("denemea", "x"), ("a  (b) c", "x")]
    rapor = terkip_raporu({"denemee  deneme f": 7, "denemea denemeb": 3, "a b c": 1}, rnk, [])
    assert rapor["risale_terkip"] == 3 and rapor["risale_terkip_toplam_siklik"] == 11
    assert rapor["rnk_cok_sozcuklu_baslik"] == 2  # bosluk iceren iki baslik
    assert rapor["rnk"]["terkip"] == {"sayi": 2, "yuzde": 66.67}  # type: ignore[index]
    assert rapor["hicbiri"]["siklikli"]["sayi"] == 3  # type: ignore[index]
    # "denemeed" ile "denemee d" ayri anahtardir: bitisik yazim terkibe esitlenmez
    ayri = terkip_raporu({"denemeed f": 1}, [("denemee d f", "x")], [])
    assert ayri["rnk"]["terkip"]["sayi"] == 0  # type: ignore[index]


# --- komut: rapor, yerel liste ve metin tasimama ------------------------------------------------


def test_komut_rapor_ve_yerel_liste_yazar(kz: KaynakKoku) -> None:
    assert rapor_calistir(kz) == 0
    rapor = rapor_oku(kz)
    assert rapor["tur"] == "lugat-kapsama" and rapor["lugat"] == {
        "rnk_madde": 8,
        "rganeyev_alinan_madde": 5,
    }
    baslik = rapor["baslik_soz"]
    assert baslik["baslik_soz"] == 8 and baslik["toplam_siklik"] == 194  # type: ignore[index]
    assert baslik["rnk"]["soz"] == {"sayi": 4, "yuzde": 50.0}  # type: ignore[index]
    assert baslik["rnk"]["siklikli"]["sayi"] == 178  # type: ignore[index]  # 140+1+30+7
    assert baslik["yalniz_rganeyev"]["soz"]["sayi"] == 1  # type: ignore[index]  # denemed
    assert baslik["hicbiri"]["soz"]["sayi"] == 3  # type: ignore[index]
    assert baslik["secilen_anahtar"] == "esleme_anahtari"  # type: ignore[index]
    assert set(baslik["anahtar_olcumu"]) == {  # type: ignore[index]
        "basliksoz_norm",
        "sozluk_ocr_anahtar",
        "esleme_anahtari",
    }
    metin = rapor["metin_sozcukleri"]
    assert metin["benzersiz_sozcuk"] == 5 and metin["toplam_gecis"] == 8  # type: ignore[index]
    assert metin["birim"] == {"birim": 5, "turkce_birim": 3, "metinsiz_birim": 1}  # type: ignore[index]
    hepsi, yalniz_rnk = metin["rnk_ve_rganeyev"], metin["yalniz_rnk"]  # type: ignore[index]
    assert hepsi["toplam"]["sozcuk"]["sayi"] == 4  # denemea, denemeb, yenia, denemedx (govde)
    assert yalniz_rnk["toplam"]["sozcuk"]["sayi"] == 3  # rganeyev katkisi: denemedx
    assert hepsi["karsiliksiz"]["sozcuk"]["sayi"] == 1  # xyzzy
    terkip = rapor["terkipler"]
    assert terkip["risale_terkip"] == 2 and terkip["risale_terkip_toplam_siklik"] == 10  # type: ignore[index]
    assert terkip["rnk"]["siklikli"]["sayi"] == 7 and terkip["girdi"]["bozuk_satir"] == 1  # type: ignore[index]
    assert terkip["rnk_cok_sozcuklu_baslik"] == 1  # type: ignore[index]
    liste = (kz.veri_kok / "reports" / "a20" / KARSILIKSIZ_ADI).read_bytes()
    assert liste == b"xyzzy\t2\n"  # yalniz karsiliksiz sozcuk ve gecis


def test_rapor_json_metin_tasimaz_yalniz_sayi_ve_oran(kz: KaynakKoku) -> None:
    assert rapor_calistir(kz) == 0
    ham = (kz.veri_kok / "reports" / "a20" / RAPOR_ADI).read_text(encoding="utf-8")
    for imza in (
        TANIM_RNK, TANIM_RG, "denemea", "denemeb", "yenia", "xyzzy", "denemedx", "rgyeni", "TANIM",
    ):  # fmt: skip
        assert imza not in ham, imza
    assert ham.isascii() and ham.endswith("\n")

    def yapraklar(d: object) -> list[object]:
        if isinstance(d, dict):
            return [y for v in d.values() for y in yapraklar(v)]
        return [d]

    for yaprak in yapraklar(json.loads(ham)):
        if isinstance(yaprak, str):
            assert " " not in yaprak or yaprak.startswith("Karsilik"), (
                yaprak
            )  # tek serbest metin: not
    for yol, veri in kz.tum_cikti_baytlari().items():
        if "reports/" in yol and not yol.endswith(KARSILIKSIZ_ADI):
            assert b"xyzzy" not in veri, yol  # liste yalniz yerel dosyada


def test_rapor_ikinci_kosuda_bayt_bayt_ayni(kz: KaynakKoku) -> None:
    assert rapor_calistir(kz) == 0
    ilk = (kz.veri_kok / "reports" / "a20" / RAPOR_ADI).read_bytes()
    assert rapor_calistir(kz) == 0
    assert (kz.veri_kok / "reports" / "a20" / RAPOR_ADI).read_bytes() == ilk


def test_dry_run_dosya_yazmaz(kz: KaynakKoku) -> None:
    assert rapor_calistir(kz, "--dry-run") == 0
    for ad in (
        RAPOR_ADI,
        KARSILIKSIZ_ADI,
    ):  # (Kelime-Frekans ingest'i a20 klasorunu acmis olabilir)
        assert not (kz.veri_kok / "reports" / "a20" / ad).exists()


def test_hepsi_lugat_raporunu_icermez(kz: KaynakKoku) -> None:
    sonuc = runner.invoke(
        cli.app, ["qa", "risale-rapor", "--rapor", "hepsi", "--dry-run", "--kok", str(kz.kok)]
    )
    assert "lugat" not in sonuc.output  # `hepsi` yalniz icindekiler ve diyanet


def test_gecersiz_rapor_turu_cikis_2(kz: KaynakKoku) -> None:
    assert rapor_calistir(kz) == 0
    sonuc = runner.invoke(cli.app, ["qa", "risale-rapor", "--rapor", "baska", "--kok", str(kz.kok)])
    assert sonuc.exit_code == 2


@pytest.mark.parametrize(
    "silinecek",
    ["staged/risale-rnk-metin", "staged/lugat-rnk", "staged/lugat-sozluk-rganeyev"],
)
def test_girdi_yoksa_cikis_2(kz: KaynakKoku, silinecek: str) -> None:
    import shutil

    shutil.rmtree(kz.veri_kok / silinecek)
    assert rapor_calistir(kz) == 2
    assert not (kz.veri_kok / "reports" / "a20" / RAPOR_ADI).exists()


def test_kelime_frekans_staged_yoksa_cikis_2(kz: KaynakKoku) -> None:
    import shutil

    shutil.rmtree(kz.veri_kok / "staged" / "risale-kelime-frekans")
    assert rapor_calistir(kz) == 2


def test_anchor_degil_ingest_calismasi_kabul_edilmez(kz: KaynakKoku) -> None:
    anchor_run_yaz(kz, BIRIMLER, adim="ingest")  # ayni klasorde manifestin adimi `ingest`
    assert rapor_calistir(kz) == 2


def test_units_ozeti_manifestle_tutmazsa_cikis_2(kz: KaynakKoku) -> None:
    yol = kz.veri_kok / "staged" / "risale-rnk-metin" / RUN_UUID / "units.jsonl"
    yol.write_bytes(yol.read_bytes() + b"\n")
    assert rapor_calistir(kz) == 2


def test_cli_yardim_lugat_secenegini_anlatir() -> None:
    from hat_yardimci import ansisiz

    sonuc = runner.invoke(cli.app, ["qa", "risale-rapor", "--help"])
    assert sonuc.exit_code == 0
    metin = ansisiz(sonuc.output)
    assert "lugat" in metin and "hepsi" in metin
