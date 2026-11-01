# ruff: noqa: RUF001
"""`mutalaa sources list` ve `sources check` testleri (A06.1, G-KAY, K-42).

Fiksturler `tmp_path` altinda kodla uretilir: her senaryo kendi sahte kokunu
(`pnpm-workspace.yaml` + `pipeline/sources/`) kurar ve `--kok` ile verir. Tum kayitlar
`test-` onekli SENTETIK kayittir; gercek kaynak metni yoktur.
"""

import dataclasses
import json
import re
import tomllib
from collections.abc import Iterator
from datetime import date
from pathlib import Path

import pytest
from typer.testing import CliRunner, Result

from mutalaa_pipeline import cli, sources
from mutalaa_pipeline.enums import SourceKind
from mutalaa_pipeline.export.ortak import depo_koku
from mutalaa_pipeline.sources import kayit

runner = CliRunner()

ATIF = "Deneme atif metni."

ZORUNLU = ("slug", "tur", "baslik", "atif_metni")
ISTEGE_BAGLI = (
    "yazar",
    "surum",
    "provider",
    "kaynak_url",
    "atif_url",
    "notice_text",
    "baski_bilgisi",
    "notlar",
)
# K-42: kayit semasindan cikan alanlar; her biri "bilinmeyen alan" hatasidir.
ESKI_ALANLAR: dict[str, object] = {
    "license_name": "Deneme",
    "license_url": "https://example.invalid/x",
    "license_status": "serbest",
    "kisitlar": {"degistirme_yasak": True},
    "embed_ok": True,
    "kurul_gerekli": False,
    "yeniden_kontrol": date(2999, 1, 1),
    "lisans_kopyasi": "licenses/test-eski-2026-10-19.txt",
    "lisans_sha256": "0" * 64,
    "yazar_vefat_yili": 1900,
    "kamu_mali_tarihi": date(2030, 1, 1),
}


# --- Yardimcilar -------------------------------------------------------------------------


def kok_kur(tmp_path: Path) -> Path:
    kok = tmp_path / "kok"
    (kok / "pipeline" / "sources").mkdir(parents=True)
    (kok / "pnpm-workspace.yaml").write_bytes(b"")
    return kok


def kaynaklar(kok: Path) -> Path:
    return kok / "pipeline" / "sources"


def deger_yaz(deger: object) -> str:
    if isinstance(deger, bool):
        return "true" if deger else "false"
    if isinstance(deger, date):
        return deger.isoformat()
    if isinstance(deger, int):
        return str(deger)
    if isinstance(deger, str | list):
        return json.dumps(deger)
    if isinstance(deger, dict):
        ic = ", ".join(f"{ad} = {deger_yaz(v)}" for ad, v in deger.items())
        return "{ " + ic + " }"
    raise TypeError(type(deger))


def toml_metni(alanlar: dict[str, object]) -> str:
    return "".join(f"{ad} = {deger_yaz(v)}\n" for ad, v in alanlar.items())


def alanlar_kur(slug: str, /, **degisim: object) -> dict[str, object]:
    """Gecerli bir kayit (yalniz zorunlu alanlar); `None` verilen alan kayittan cikar."""
    alanlar: dict[str, object] = {
        "slug": slug,
        "tur": "kuran_metni",
        "baslik": "Deneme kaynak",
        "atif_metni": ATIF,
    }
    alanlar.update(degisim)
    return {ad: v for ad, v in alanlar.items() if v is not None}


def kayit_yaz(kok: Path, alanlar: dict[str, object], dosya: str | None = None) -> None:
    ad = dosya if dosya is not None else f"{alanlar['slug']}.toml"
    (kaynaklar(kok) / ad).write_bytes(toml_metni(alanlar).encode("utf-8"))


def calistir(kok: Path, *argumanlar: str) -> Result:
    return runner.invoke(cli.app, ["sources", *argumanlar, "--kok", str(kok)])


def check(kok: Path) -> Result:
    return calistir(kok, "check")


# --- check: gecerli ve bos ---------------------------------------------------------------


def test_gecerli_kayit_sifir(tmp_path: Path) -> None:
    kok = kok_kur(tmp_path)
    kayit_yaz(kok, alanlar_kur("test-gecerli"))
    sonuc = check(kok)
    assert sonuc.exit_code == 0, sonuc.stderr
    assert "1 kayit, 0 hata, 0 uyari" in sonuc.stdout
    assert sonuc.stderr == ""


def test_gecerli_kayit_tum_istege_bagli_alanlarla(tmp_path: Path) -> None:
    kok = kok_kur(tmp_path)
    kayit_yaz(
        kok,
        alanlar_kur(
            "test-tam",
            yazar="Deneme Yazar",
            surum="1",
            provider="deneme",
            kaynak_url="https://example.invalid/kaynak",
            atif_url="https://example.invalid/atif",
            notice_text="Deneme bildirim.",
            baski_bilgisi={"yil": 1935, "yayinevi": "Deneme"},
            notlar="Deneme notu.",
        ),
    )
    sonuc = check(kok)
    assert sonuc.exit_code == 0, sonuc.stderr
    assert sonuc.stderr == ""
    kaynak = sources.yukle(kok)[0].kaynak
    assert kaynak is not None
    assert kaynak.baski_bilgisi == {"yil": 1935, "yayinevi": "Deneme"}
    assert kaynak.notice_text == "Deneme bildirim."


def test_bos_dizin_sifir_ve_not(tmp_path: Path) -> None:
    kok = kok_kur(tmp_path)
    sonuc = check(kok)
    assert sonuc.exit_code == 0
    assert "kayit yok" in sonuc.stdout


def test_toml_olmayan_dosyalar_yok_sayilir(tmp_path: Path) -> None:
    kok = kok_kur(tmp_path)
    (kaynaklar(kok) / "README.txt").write_bytes(b"not\n")
    sonuc = check(kok)
    assert sonuc.exit_code == 0
    assert "kayit yok" in sonuc.stdout


def test_kaynak_klasoru_yoksa_iki(tmp_path: Path) -> None:
    kok = tmp_path / "kok"
    kok.mkdir()
    sonuc = check(kok)
    assert sonuc.exit_code == 2
    assert "hata:" in sonuc.stderr


def test_gercek_depoda_check_sifir() -> None:
    sonuc = runner.invoke(cli.app, ["sources", "check"])
    assert sonuc.exit_code == 0, sonuc.stderr


# --- check: hata senaryolari -------------------------------------------------------------


def test_bozuk_toml(tmp_path: Path) -> None:
    kok = kok_kur(tmp_path)
    (kaynaklar(kok) / "test-bozuk.toml").write_bytes(b'slug = "test-bozuk\nbaslik = =\n')
    sonuc = check(kok)
    assert sonuc.exit_code == 2
    assert "hata: test-bozuk.toml: TOML ayristirilamadi" in sonuc.stderr


def test_bom_hata(tmp_path: Path) -> None:
    kok = kok_kur(tmp_path)
    veri = toml_metni(alanlar_kur("test-bom")).encode("utf-8")
    (kaynaklar(kok) / "test-bom.toml").write_bytes(b"\xef\xbb\xbf" + veri)
    sonuc = check(kok)
    assert sonuc.exit_code == 2
    assert "hata: test-bom.toml: BOM var" in sonuc.stderr


def test_crlf_hata(tmp_path: Path) -> None:
    kok = kok_kur(tmp_path)
    veri = toml_metni(alanlar_kur("test-crlf")).replace("\n", "\r\n").encode("utf-8")
    (kaynaklar(kok) / "test-crlf.toml").write_bytes(veri)
    sonuc = check(kok)
    assert sonuc.exit_code == 2
    assert "hata: test-crlf.toml: CR/CRLF" in sonuc.stderr


def test_utf8_degil_hata(tmp_path: Path) -> None:
    kok = kok_kur(tmp_path)
    (kaynaklar(kok) / "test-latin.toml").write_bytes(b'baslik = "\xe7"\n')
    sonuc = check(kok)
    assert sonuc.exit_code == 2
    assert "hata: test-latin.toml: UTF-8 degil" in sonuc.stderr


def test_bilinmeyen_tur(tmp_path: Path) -> None:
    kok = kok_kur(tmp_path)
    kayit_yaz(kok, alanlar_kur("test-tur", tur="roman"))
    sonuc = check(kok)
    assert sonuc.exit_code == 2
    assert "hata: test-tur.toml: tur: bilinmeyen deger" in sonuc.stderr


def test_dosya_adi_slug_ile_ayni_degil(tmp_path: Path) -> None:
    kok = kok_kur(tmp_path)
    kayit_yaz(kok, alanlar_kur("test-slug"), dosya="test-baska.toml")
    sonuc = check(kok)
    assert sonuc.exit_code == 2
    assert "hata: test-baska.toml: slug (test-slug) dosya adiyla (test-baska) ayni degil" in (
        sonuc.stderr
    )


@pytest.mark.parametrize("dosya", ["Test-Buyuk.toml", "test_alt.toml", "test--cift.toml"])
def test_dosya_adi_deseni(tmp_path: Path, dosya: str) -> None:
    kok = kok_kur(tmp_path)
    slug = dosya[: -len(".toml")]
    kayit_yaz(kok, alanlar_kur(slug), dosya=dosya)
    sonuc = check(kok)
    assert sonuc.exit_code == 2
    assert "desenine uymuyor" in sonuc.stderr


def test_ascii_olmayan_dosya_adi(tmp_path: Path) -> None:
    kok = kok_kur(tmp_path)
    ad = f"test-{chr(0x131)}"  # noktasiz i: ASCII olmayan dosya adi
    kayit_yaz(kok, alanlar_kur(ad), dosya=f"{ad}.toml")
    sonuc = check(kok)
    assert sonuc.exit_code == 2
    assert "desenine uymuyor" in sonuc.stderr
    assert sonuc.stderr.isascii()


def test_bilinmeyen_alan(tmp_path: Path) -> None:
    kok = kok_kur(tmp_path)
    kayit_yaz(kok, alanlar_kur("test-alan", fazladan="x"))
    sonuc = check(kok)
    assert sonuc.exit_code == 2
    assert "hata: test-alan.toml: bilinmeyen alan: fazladan" in sonuc.stderr


def test_sema_alanlari_sabit() -> None:
    assert tuple(kayit.ZORUNLU_ALANLAR) == ZORUNLU
    assert tuple(kayit.ISTEGE_BAGLI_ALANLAR) == ISTEGE_BAGLI
    assert [f.name for f in dataclasses.fields(sources.Kaynak)] == [*ZORUNLU, *ISTEGE_BAGLI]
    assert not set(ESKI_ALANLAR) & (set(ZORUNLU) | set(ISTEGE_BAGLI))
    assert len(ESKI_ALANLAR) == 11


@pytest.mark.parametrize("ad", sorted(ESKI_ALANLAR))
def test_eski_lisans_alani_bilinmeyen_alan_hatasi(tmp_path: Path, ad: str) -> None:
    kok = kok_kur(tmp_path)
    kayit_yaz(kok, alanlar_kur("test-eski", **{ad: ESKI_ALANLAR[ad]}))
    sonuc = check(kok)
    assert sonuc.exit_code == 2
    assert f"hata: test-eski.toml: bilinmeyen alan: {ad}" in sonuc.stderr
    assert "1 kayit, 1 hata" in sonuc.stdout
    assert calistir(kok, "list").exit_code == 2


def test_butun_eski_alanlar_birlikte_her_biri_ayri_hata(tmp_path: Path) -> None:
    kok = kok_kur(tmp_path)
    kayit_yaz(kok, alanlar_kur("test-eski", **ESKI_ALANLAR))
    sonuc = check(kok)
    assert sonuc.exit_code == 2
    assert sonuc.stderr.count("bilinmeyen alan:") == len(ESKI_ALANLAR)
    assert f"1 kayit, {len(ESKI_ALANLAR)} hata" in sonuc.stdout


@pytest.mark.parametrize("eksik", ZORUNLU)
def test_zorunlu_alan_eksik(tmp_path: Path, eksik: str) -> None:
    kok = kok_kur(tmp_path)
    alanlar = alanlar_kur("test-zorunlu")
    del alanlar[eksik]
    kayit_yaz(kok, alanlar, dosya="test-zorunlu.toml")
    sonuc = check(kok)
    assert sonuc.exit_code == 2
    assert f"zorunlu alan eksik: {eksik}" in sonuc.stderr


def test_atif_metni_eksikse_hata(tmp_path: Path) -> None:
    kok = kok_kur(tmp_path)
    kayit_yaz(kok, alanlar_kur("test-atifsiz", atif_metni=None))
    sonuc = check(kok)
    assert sonuc.exit_code == 2
    assert "hata: test-atifsiz.toml: zorunlu alan eksik: atif_metni" in sonuc.stderr
    assert "1 kayit, 1 hata" in sonuc.stdout


@pytest.mark.parametrize("alan", ["atif_metni", "baslik"])
@pytest.mark.parametrize("metin", ["", "   ", " \t\n"])
def test_zorunlu_metin_alani_bos(tmp_path: Path, alan: str, metin: str) -> None:
    kok = kok_kur(tmp_path)
    kayit_yaz(kok, alanlar_kur("test-bos", **{alan: metin}))
    sonuc = check(kok)
    assert sonuc.exit_code == 2
    assert f"hata: test-bos.toml: {alan} bos olamaz" in sonuc.stderr


@pytest.mark.parametrize(
    ("alan", "deger", "beklenen"),
    [
        ("slug", 5, "slug: metin olmali"),
        ("tur", 5, "tur: metin olmali"),
        ("surum", 1, "surum: metin olmali"),
        ("yazar", True, "yazar: metin olmali"),
        ("notice_text", 5, "notice_text: metin olmali"),
        ("notlar", ["a"], "notlar: metin olmali"),
        ("baski_bilgisi", "x", "baski_bilgisi: tablo olmali"),
    ],
)
def test_tip_hatalari(tmp_path: Path, alan: str, deger: object, beklenen: str) -> None:
    kok = kok_kur(tmp_path)
    alanlar = alanlar_kur("test-tip")
    alanlar[alan] = deger
    kayit_yaz(kok, alanlar, dosya="test-tip.toml")
    sonuc = check(kok)
    assert sonuc.exit_code == 2
    assert beklenen in sonuc.stderr


# --- check: toplama ve gizlilik ----------------------------------------------------------


def test_hatalar_toplanir_ilkinde_durmaz(tmp_path: Path) -> None:
    kok = kok_kur(tmp_path)
    kayit_yaz(kok, alanlar_kur("test-a", tur="roman", fazladan=1, license_status="serbest"))
    kayit_yaz(kok, alanlar_kur("test-b", atif_metni=None))
    (kaynaklar(kok) / "test-c.toml").write_bytes(b"=\n")
    sonuc = check(kok)
    assert sonuc.exit_code == 2
    assert "hata: test-a.toml: tur:" in sonuc.stderr
    assert "hata: test-a.toml: bilinmeyen alan: fazladan" in sonuc.stderr
    assert "hata: test-a.toml: bilinmeyen alan: license_status" in sonuc.stderr
    assert "hata: test-b.toml: zorunlu alan eksik: atif_metni" in sonuc.stderr
    assert "hata: test-c.toml: TOML ayristirilamadi" in sonuc.stderr
    assert "3 kayit, 5 hata" in sonuc.stdout


def test_cikti_icerik_metni_tasimaz(tmp_path: Path) -> None:
    kok = kok_kur(tmp_path)
    gizli = "GIZLI-ATIF-ICERIGI-XYZ"
    kayit_yaz(kok, alanlar_kur("test-gizli", atif_metni=gizli, tur="roman"))
    kayit_yaz(kok, alanlar_kur("test-gizli-iki", atif_metni=gizli))
    sonuc = check(kok)
    assert sonuc.exit_code == 2
    assert gizli not in sonuc.stdout
    assert gizli not in sonuc.stderr
    listeleme = calistir(kok, "list", "--format", "json")
    assert gizli not in listeleme.stdout


# --- list --------------------------------------------------------------------------------


def test_list_json_siralama_ve_alanlar(tmp_path: Path) -> None:
    kok = kok_kur(tmp_path)
    kayit_yaz(kok, alanlar_kur("test-z", surum="2", kaynak_url="https://example.invalid/z"))
    kayit_yaz(kok, alanlar_kur("test-a", tur="risale"))
    kayit_yaz(kok, alanlar_kur("test-m", surum="1.1"))
    sonuc = calistir(kok, "list", "--format", "json")
    assert sonuc.exit_code == 0, sonuc.stderr
    veri = json.loads(sonuc.stdout)
    assert [s["slug"] for s in veri] == ["test-a", "test-m", "test-z"]
    assert veri[0] == {"slug": "test-a", "tur": "risale", "surum": None, "kaynak_url": None}
    assert veri[2] == {
        "slug": "test-z",
        "tur": "kuran_metni",
        "surum": "2",
        "kaynak_url": "https://example.invalid/z",
    }
    assert sonuc.stdout.isascii()


def test_list_varsayilan_bicim_tablo(tmp_path: Path) -> None:
    kok = kok_kur(tmp_path)
    kayit_yaz(kok, alanlar_kur("test-eski", surum="1.0", kaynak_url="https://example.invalid/e"))
    kayit_yaz(kok, alanlar_kur("test-yeni", tur="meal"))
    sonuc = calistir(kok, "list")
    assert sonuc.exit_code == 0, sonuc.stderr
    satirlar = sonuc.stdout.splitlines()
    assert satirlar[0].isascii()
    assert satirlar[0].split() == ["slug", "tur", "surum", "kaynak_url"]
    eski = next(s for s in satirlar if s.startswith("test-eski"))
    yeni = next(s for s in satirlar if s.startswith("test-yeni"))
    assert eski.split() == ["test-eski", "kuran_metni", "1.0", "https://example.invalid/e"]
    assert yeni.split() == ["test-yeni", "meal", "-", "-"]
    assert len(satirlar) == 3


def test_list_tablo_ascii_olmayan_degeri_kacislar(tmp_path: Path) -> None:
    kok = kok_kur(tmp_path)
    adres = f"https://example.invalid/{chr(0x131)}"  # noktasiz i
    kayit_yaz(kok, alanlar_kur("test-asci", kaynak_url=adres))
    sonuc = calistir(kok, "list")
    assert sonuc.exit_code == 0, sonuc.stderr
    assert sonuc.stdout.isascii()
    assert "\\u0131" in sonuc.stdout


def test_list_bos_dizin(tmp_path: Path) -> None:
    kok = kok_kur(tmp_path)
    tablo = calistir(kok, "list")
    assert tablo.exit_code == 0
    assert "kayit yok" in tablo.stdout
    bicim_json = calistir(kok, "list", "--format", "json")
    assert bicim_json.exit_code == 0
    assert json.loads(bicim_json.stdout) == []


def test_list_bozuk_toml_iki(tmp_path: Path) -> None:
    kok = kok_kur(tmp_path)
    kayit_yaz(kok, alanlar_kur("test-iyi"))
    (kaynaklar(kok) / "test-bozuk.toml").write_bytes(b"slug = \n")
    sonuc = calistir(kok, "list", "--format", "json")
    assert sonuc.exit_code == 2
    assert "hata: test-bozuk.toml: TOML ayristirilamadi" in sonuc.stderr


def test_list_gecersiz_sema_iki(tmp_path: Path) -> None:
    kok = kok_kur(tmp_path)
    kayit_yaz(kok, alanlar_kur("test-tur", tur="roman"))
    sonuc = calistir(kok, "list")
    assert sonuc.exit_code == 2
    assert "tur: bilinmeyen deger" in sonuc.stderr


def test_list_gecersiz_format() -> None:
    sonuc = runner.invoke(cli.app, ["sources", "list", "--format", "xml"])
    assert sonuc.exit_code == 2


def test_gercek_depoda_list_calisir() -> None:
    sonuc = runner.invoke(cli.app, ["sources", "list", "--format", "json"])
    assert sonuc.exit_code == 0, sonuc.stderr
    veri = json.loads(sonuc.stdout)
    assert len(veri) > 0
    assert all(set(s) == {"slug", "tur", "surum", "kaynak_url"} for s in veri)


# --- Kutuphane katmani -------------------------------------------------------------------


def test_yukle_kaynak_dondurur(tmp_path: Path) -> None:
    kok = kok_kur(tmp_path)
    kayit_yaz(kok, alanlar_kur("test-sinir", yazar="Deneme Yazar"))
    sonuc = sources.yukle(kok)[0]
    assert sonuc.hatalar == []
    assert sonuc.kaynak is not None
    assert sonuc.kaynak.slug == "test-sinir"
    assert sonuc.kaynak.tur is SourceKind.KURAN_METNI
    assert sonuc.kaynak.atif_metni == ATIF
    assert sonuc.kaynak.yazar == "Deneme Yazar"
    assert sonuc.kaynak.surum is None


def test_gercek_kaynak_dizini_depo_icinde() -> None:
    assert sources.kaynak_dizini(depo_koku()).is_dir()


# --- Gercek depo: kalici sabitleme -------------------------------------------------------

# K-42: kullanilmayan ya da anahtar/hesap isteyen kaynaklarin kayitlari silindi.
SILINEN_SLUGLAR = (
    "ses-everyayah",
    "ses-quranicaudio",
    "quran-align",
    "hadis-sunnah-api",
    "ses-qf-api",
)
# Betimleyici alanlarda (adres ve notice_text haric) hukuk ya da izin yapisinin izi kalmamali
# (K-42 madde 0). Silinen insan adimi numaralari buyuk-kucuk harfe duyarlidir.
HUKUK_IZI = re.compile(
    r"lisans|license|kurul|avukat|embed_ok|kisitlar|ic_kullanim|kapali|yazışma|yazisma|hukuki"
    r"|Unlicense|CC BY|CC0|\bOFL\b|\bGPL\b",
    re.IGNORECASE,
)
SILINEN_ADIM_NO = re.compile(r"İ-(0[2-8]|19|2[569]|30)(?![0-9])")
TARANAN_ALANLAR = ("baslik", "yazar", "atif_metni", "baski_bilgisi", "notlar")


def gercek_kayitlar() -> dict[str, sources.Kaynak]:
    sonuclar = sources.yukle(depo_koku())
    return {s.kaynak.slug: s.kaynak for s in sonuclar if s.kaynak is not None}


def gercek_toml() -> dict[str, dict[str, object]]:
    dizin = sources.kaynak_dizini(depo_koku())
    return {
        yol.stem: tomllib.loads(yol.read_bytes().decode("utf-8"))
        for yol in sorted(dizin.glob("*.toml"), key=lambda p: p.name)
    }


def metin_degerleri(deger: object) -> Iterator[str]:
    if isinstance(deger, str):
        yield deger
    elif isinstance(deger, dict):
        for v in deger.values():
            yield from metin_degerleri(v)


def test_gercek_depo_her_dosya_gecerli_kayit() -> None:
    dosyalar = {p.stem for p in sources.kaynak_dizini(depo_koku()).glob("*.toml")}
    assert dosyalar
    assert set(gercek_kayitlar()) == dosyalar


@pytest.mark.parametrize("slug", SILINEN_SLUGLAR)
def test_gercek_depo_silinen_kayit_yok(slug: str) -> None:
    assert not (sources.kaynak_dizini(depo_koku()) / f"{slug}.toml").exists()


def test_gercek_depo_lisans_klasoru_yok() -> None:
    assert not (sources.kaynak_dizini(depo_koku()) / "licenses").exists()


def test_gercek_depo_eski_alan_yok() -> None:
    izinli = set(ZORUNLU) | set(ISTEGE_BAGLI)
    for slug, veri in gercek_toml().items():
        assert not set(veri) & set(ESKI_ALANLAR), slug
        assert set(veri) <= izinli, slug
        assert set(ZORUNLU) <= set(veri), slug


def test_gercek_depo_hukuk_izi_yok() -> None:
    for slug, veri in gercek_toml().items():
        for alan in TARANAN_ALANLAR:
            for metin in metin_degerleri(veri.get(alan)):
                assert HUKUK_IZI.search(metin) is None, f"{slug}.{alan}"
                assert SILINEN_ADIM_NO.search(metin) is None, f"{slug}.{alan}"


def test_gercek_depoda_check_sifir_uyari() -> None:
    sonuc = runner.invoke(cli.app, ["sources", "check"])
    assert sonuc.exit_code == 0, sonuc.stderr
    assert re.search(r"^sources check: [0-9]+ kayit, 0 hata, 0 uyari$", sonuc.stdout, re.MULTILINE)


def test_gercek_depo_tanzil_notice_text() -> None:
    kayitlar = gercek_kayitlar()
    uthmani = kayitlar["tanzil-uthmani"].notice_text
    sade = kayitlar["tanzil-simple-clean"].notice_text
    assert uthmani is not None
    assert uthmani.strip(" \t\n") != ""
    assert uthmani == sade  # iki varyantin dosya basligi ayni bildirimi tasir
    assert "\r" not in uthmani
    # kanonik kaynak Tanzil'in iki varyanti bildirimi tasir; baska kaynak da tasiyabilir
    assert {"tanzil-uthmani", "tanzil-simple-clean"} <= {
        s for s, k in kayitlar.items() if k.notice_text is not None
    }
