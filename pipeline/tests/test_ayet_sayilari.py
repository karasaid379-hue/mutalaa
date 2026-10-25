"""`mutalaa export ayet-sayilari` testleri (A04.1).

Gercek JSON testleri depodaki `shared/data/ayet-sayilari.json` dosyasini yalniz okur.
Ayristirici testleri `tmp_path` altinda sentetik XML kullanir: sayilar uydurmadir, ad
oznitelikleri ASCII yer tutucudur (gercek sure adi yok).
"""

import hashlib
import json
from collections.abc import Sequence
from pathlib import Path

import pytest
from typer.testing import CliRunner, Result

from mutalaa_pipeline.anchor.ayet_sayilari import AYET_SAYILARI
from mutalaa_pipeline.cli import app
from mutalaa_pipeline.export import ayet_sayilari
from mutalaa_pipeline.export.ortak import GirdiHatasi, depo_koku

runner = CliRunner()

URL = "https://example.invalid/quran-data.xml"
TARIH = "2026-01-02"


def _sentetik_sayilar() -> tuple[int, ...]:
    """114 sentetik sayi; 2. eleman 286, toplam 6236 (ayristir bu sabitleri denetler)."""
    sayilar = [(sira % 7) + 1 for sira in range(114)]
    sayilar[1] = 286
    sayilar[-1] += 6236 - sum(sayilar)
    return tuple(sayilar)


SENTETIK_SAYILAR = _sentetik_sayilar()
URETILEN_YOLLAR = (
    ayet_sayilari.JSON_YOLU,
    ayet_sayilari.TS_YOLU,
    ayet_sayilari.PY_YOLU,
    ayet_sayilari.CS_YOLU,
)


def sentetik_xml(
    sayilar: Sequence[int] = SENTETIK_SAYILAR,
    *,
    baslangiclar: Sequence[int] | None = None,
    indisler: Sequence[int] | None = None,
    kok_turu: str = "metadata",
    on_ek: str = "",
    ayas_metni: dict[int, str] | None = None,
) -> bytes:
    """Tanzil `quran-data.xml` bicimini taklit eden sentetik XML."""
    if baslangiclar is None:
        toplam = 0
        hesaplanan = []
        for sayi in sayilar:
            hesaplanan.append(toplam)
            toplam += sayi
        baslangiclar = hesaplanan
    if indisler is None:
        indisler = range(1, len(sayilar) + 1)
    satirlar = ['<?xml version="1.0" encoding="utf-8" ?>']
    if on_ek:
        satirlar.append(on_ek)
    satirlar.append(
        f'<quran type="{kok_turu}" version="9.9" copyright="(C) deneme" license="deneme-lisans">'
    )
    satirlar.append('\t<suras alias="chapters">')
    for sira, (indis, sayi, bas) in enumerate(zip(indisler, sayilar, baslangiclar, strict=True)):
        ayas = (ayas_metni or {}).get(sira, str(sayi))
        ad = f"ad-{sira + 1:03d}"
        satirlar.append(
            f'\t\t<sura index="{indis}" ayas="{ayas}" start="{bas}" '
            f'name="{ad}" tname="{ad}" ename="{ad}" type="Deneme" order="1" rukus="1" />'
        )
    satirlar.append("\t</suras>")
    satirlar.append("</quran>")
    return ("\n".join(satirlar) + "\n").encode("utf-8")


def xml_yaz(tmp_path: Path, veri: bytes) -> Path:
    yol = tmp_path / "girdi" / "quran-data.xml"
    yol.parent.mkdir(parents=True, exist_ok=True)
    yol.write_bytes(veri)
    return yol


def calistir(kok: Path, *ek: str) -> Result:
    return runner.invoke(app, ["export", "ayet-sayilari", "--kok", str(kok), *ek])


def uret(tmp_path: Path, veri: bytes) -> tuple[Path, Result]:
    kok = tmp_path / "kok"
    kok.mkdir(exist_ok=True)
    kaynak = xml_yaz(tmp_path, veri)
    sonuc = calistir(kok, "--kaynak", str(kaynak), "--url", URL, "--tarih", TARIH)
    return kok, sonuc


# --- Gercek depo -------------------------------------------------------------------------


def test_gercek_json_114_eleman_6236_toplam_ikinci_sure_286() -> None:
    belge = ayet_sayilari.json_oku(depo_koku())
    assert len(belge.sayilar) == 114
    assert sum(belge.sayilar) == 6236
    assert belge.sayilar[1] == 286
    assert belge.kaynak_url.startswith("https://")
    assert len(belge.sha256) == 64


def test_python_kopyasi_json_ile_ayni() -> None:
    belge = ayet_sayilari.json_oku(depo_koku())
    assert belge.sayilar == AYET_SAYILARI
    assert isinstance(AYET_SAYILARI, tuple)


def test_gercek_depoda_check_sifir() -> None:
    sonuc = runner.invoke(app, ["export", "ayet-sayilari", "--check"])
    assert sonuc.exit_code == 0, sonuc.output


# --- Sentetik XML ------------------------------------------------------------------------


def test_sentetik_xml_dort_dosya_uretir_ve_check_gecer(tmp_path: Path) -> None:
    veri = sentetik_xml()
    kok, sonuc = uret(tmp_path, veri)
    assert sonuc.exit_code == 0, sonuc.output
    for goreli in URETILEN_YOLLAR:
        icerik = (kok / goreli).read_bytes()
        assert not icerik.startswith(b"\xef\xbb\xbf")
        assert b"\r" not in icerik
        assert icerik.endswith(b"\n")
        assert b"ad-0" not in icerik  # sure adi yer tutuculari hicbir dosyaya gecmez

    belge = json.loads((kok / ayet_sayilari.JSON_YOLU).read_text(encoding="utf-8"))
    assert list(belge) == [
        "kaynak_url",
        "alinma_tarihi",
        "sha256",
        "lisans",
        "telif",
        "surum",
        "sayilar",
    ]
    assert belge["kaynak_url"] == URL
    assert belge["alinma_tarihi"] == TARIH
    assert belge["sha256"] == hashlib.sha256(veri).hexdigest()
    assert belge["lisans"] == "deneme-lisans"
    assert belge["telif"] == "(C) deneme"
    assert belge["surum"] == "9.9"
    assert tuple(belge["sayilar"]) == SENTETIK_SAYILAR

    assert calistir(kok, "--check").exit_code == 0


def test_kopyalarin_basligi_ve_bicimi(tmp_path: Path) -> None:
    veri = sentetik_xml()
    kok, sonuc = uret(tmp_path, veri)
    assert sonuc.exit_code == 0, sonuc.output
    ozet = hashlib.sha256(veri).hexdigest()
    ts = (kok / ayet_sayilari.TS_YOLU).read_text(encoding="utf-8")
    py = (kok / ayet_sayilari.PY_YOLU).read_text(encoding="utf-8")
    cs = (kok / ayet_sayilari.CS_YOLU).read_text(encoding="utf-8")
    for metin in (ts, py, cs):
        assert ayet_sayilari.UYARI in metin
        assert URL in metin
        assert ozet in metin
    assert cs.startswith("// <auto-generated/>\n")
    assert "export const AYET_SAYILARI: readonly number[] = Object.freeze([" in ts
    assert "AYET_SAYILARI: Final[tuple[int, ...]] = (" in py
    assert "public static ImmutableArray<int> Sayilar { get; } =" in cs
    satir_sayisi = sum(1 for satir in py.split("\n") if satir.startswith("    ") and satir[4:-1])
    assert satir_sayisi == 114


def test_iki_kez_calistirmak_ayni_bayti_verir(tmp_path: Path) -> None:
    kok, ilk = uret(tmp_path, sentetik_xml())
    assert ilk.exit_code == 0, ilk.output
    once = {goreli: (kok / goreli).read_bytes() for goreli in URETILEN_YOLLAR}
    _, ikinci = uret(tmp_path, sentetik_xml())
    assert ikinci.exit_code == 0, ikinci.output
    assert "degisiklik yok" in ikinci.output
    assert {goreli: (kok / goreli).read_bytes() for goreli in URETILEN_YOLLAR} == once


@pytest.mark.parametrize(
    "on_ek",
    ['<!DOCTYPE quran [<!ENTITY x "y">]>', '<!DOCTYPE quran SYSTEM "deneme.dtd">'],
    ids=["entity", "doctype"],
)
def test_doctype_ve_entity_reddedilir(tmp_path: Path, on_ek: str) -> None:
    kok, sonuc = uret(tmp_path, sentetik_xml(on_ek=on_ek))
    assert sonuc.exit_code == 2
    assert "DOCTYPE" in sonuc.output
    assert not (kok / ayet_sayilari.JSON_YOLU).exists()


def test_eksik_sure_reddedilir(tmp_path: Path) -> None:
    kok, sonuc = uret(tmp_path, sentetik_xml(SENTETIK_SAYILAR[:113]))
    assert sonuc.exit_code == 2
    assert "113 <sura>" in sonuc.output
    assert not (kok / ayet_sayilari.JSON_YOLU).exists()


def test_bozuk_start_reddedilir(tmp_path: Path) -> None:
    baslangiclar = [0]
    for sayi in SENTETIK_SAYILAR[:-1]:
        baslangiclar.append(baslangiclar[-1] + sayi)
    baslangiclar[50] += 1
    kok, sonuc = uret(tmp_path, sentetik_xml(baslangiclar=baslangiclar))
    assert sonuc.exit_code == 2
    assert "51. <sura>: start" in sonuc.output
    assert not (kok / ayet_sayilari.JSON_YOLU).exists()


def test_ardisik_olmayan_index_reddedilir(tmp_path: Path) -> None:
    indisler = list(range(1, 115))
    indisler[9], indisler[10] = indisler[10], indisler[9]
    _, sonuc = uret(tmp_path, sentetik_xml(indisler=indisler))
    assert sonuc.exit_code == 2
    assert "ardisik degil" in sonuc.output


@pytest.mark.parametrize(
    "ayas",
    [" 3", "3.0", "+3", "03", "1_0", "\N{ARABIC-INDIC DIGIT THREE}", ""],
    ids=["bosluk", "ondalik", "arti", "bas-sifir", "alt-cizgi", "arap-rakami", "bos"],
)
def test_ascii_ondalik_olmayan_sayi_reddedilir(tmp_path: Path, ayas: str) -> None:
    _, sonuc = uret(tmp_path, sentetik_xml(ayas_metni={4: ayas}))
    assert sonuc.exit_code == 2
    assert "5. <sura>" in sonuc.output


def test_sifir_ayet_reddedilir(tmp_path: Path) -> None:
    sayilar = list(SENTETIK_SAYILAR)
    sayilar[0] = 0
    _, sonuc = uret(tmp_path, sentetik_xml(sayilar))
    assert sonuc.exit_code == 2
    assert "1. <sura>: ayas" in sonuc.output


def test_kok_turu_metadata_degilse_reddedilir(tmp_path: Path) -> None:
    _, sonuc = uret(tmp_path, sentetik_xml(kok_turu="baska"))
    assert sonuc.exit_code == 2


def test_bozuk_xml_reddedilir(tmp_path: Path) -> None:
    _, sonuc = uret(tmp_path, sentetik_xml()[:-20])
    assert sonuc.exit_code == 2
    assert "XML ayristirilamadi" in sonuc.output


def test_check_farki_bir_ile_cikar_ve_yazmaz(tmp_path: Path) -> None:
    kok, sonuc = uret(tmp_path, sentetik_xml())
    assert sonuc.exit_code == 0, sonuc.output
    ts = kok / ayet_sayilari.TS_YOLU
    bozuk = ts.read_bytes().replace(b"  1,\n", b"  9,\n", 1)
    ts.write_bytes(bozuk)
    denetim = calistir(kok, "--check")
    assert denetim.exit_code == 1
    assert ayet_sayilari.TS_YOLU in denetim.output
    assert ayet_sayilari.PY_YOLU not in denetim.output
    assert ts.read_bytes() == bozuk  # --check diske yazmaz


def test_check_json_bicim_farkini_da_yakalar(tmp_path: Path) -> None:
    kok, _ = uret(tmp_path, sentetik_xml())
    yol = kok / ayet_sayilari.JSON_YOLU
    yol.write_text(
        json.dumps(json.loads(yol.read_text(encoding="utf-8"))), encoding="utf-8", newline="\n"
    )
    denetim = calistir(kok, "--check")
    assert denetim.exit_code == 1
    assert ayet_sayilari.JSON_YOLU in denetim.output


def test_check_json_yoksa_iki(tmp_path: Path) -> None:
    assert calistir(tmp_path, "--check").exit_code == 2


@pytest.mark.parametrize(
    "bozma",
    ["{", '{"sayilar": []}', "[]"],
    ids=["json-hatasi", "eksik-alan", "kok-dizi"],
)
def test_check_json_bozuksa_iki(tmp_path: Path, bozma: str) -> None:
    yol = tmp_path / ayet_sayilari.JSON_YOLU
    yol.parent.mkdir(parents=True)
    yol.write_text(bozma, encoding="utf-8", newline="\n")
    assert calistir(tmp_path, "--check").exit_code == 2


def test_check_113_elemanli_json_iki(tmp_path: Path) -> None:
    kok, _ = uret(tmp_path, sentetik_xml())
    yol = kok / ayet_sayilari.JSON_YOLU
    belge = json.loads(yol.read_text(encoding="utf-8"))
    belge["sayilar"] = belge["sayilar"][:113]
    yol.write_text(json.dumps(belge, indent=2) + "\n", encoding="utf-8", newline="\n")
    assert calistir(kok, "--check").exit_code == 2


@pytest.mark.parametrize(
    ("ek", "ileti"),
    [
        (["--check", "--url", URL], "--check ile"),
        (["--url", URL, "--tarih", TARIH], "birlikte verilmeli"),
        (["--kaynak", "yok.xml", "--url", URL, "--tarih", TARIH], "bulunamadi"),
    ],
    ids=["check-ile-url", "kaynak-eksik", "kaynak-yok"],
)
def test_secenek_hatalari_iki(tmp_path: Path, ek: list[str], ileti: str) -> None:
    sonuc = calistir(tmp_path, *ek)
    assert sonuc.exit_code == 2
    assert ileti in sonuc.output


@pytest.mark.parametrize(
    ("url", "tarih"),
    [
        ("http://example.invalid/x.xml", TARIH),
        ("https://example.invalid/x y.xml", TARIH),
        ("https://example.invalid/x.xml\n// enjeksiyon", TARIH),
        (URL, "2026-13-01"),
        (URL, "26-01-02"),
    ],
    ids=["http", "bosluk", "satir-sonu", "gecersiz-ay", "kisa-yil"],
)
def test_url_ve_tarih_denetlenir(tmp_path: Path, url: str, tarih: str) -> None:
    kaynak = xml_yaz(tmp_path, sentetik_xml())
    sonuc = calistir(tmp_path, "--kaynak", str(kaynak), "--url", url, "--tarih", tarih)
    assert sonuc.exit_code == 2
    assert not (tmp_path / ayet_sayilari.JSON_YOLU).exists()


# --- UTF-16 ve bildirim atlatma ------------------------------------------------------------

VARLIK_ON_EKI = '<!DOCTYPE quran [<!ENTITY x "y">]>'


def utf16_xml(kodek: str) -> bytes:
    metin = sentetik_xml(on_ek=VARLIK_ON_EKI).decode("utf-8")
    return metin.replace('encoding="utf-8"', 'encoding="utf-16"').encode(kodek)


@pytest.mark.parametrize("kodek", ["utf-16-le", "utf-16-be", "utf-16"])
def test_utf16_xml_reddedilir(tmp_path: Path, kodek: str) -> None:
    veri = utf16_xml(kodek)
    with pytest.raises(GirdiHatasi):
        ayet_sayilari.ayristir(veri)
    kok, sonuc = uret(tmp_path, veri)
    assert sonuc.exit_code == 2
    assert not (kok / ayet_sayilari.JSON_YOLU).exists()


def test_nul_bayt_reddedilir() -> None:
    with pytest.raises(GirdiHatasi, match="NUL"):
        ayet_sayilari.ayristir(sentetik_xml() + b"\x00")


def test_yedek_denetim_utf16_bildirimi_yakalar() -> None:
    """Bayt aramasi UTF-16'yi kacirsa bile expat yedegi DOCTYPE/ENTITY'yi reddeder."""
    with pytest.raises(GirdiHatasi, match="DOCTYPE"):
        ayet_sayilari._bildirim_yedek_denetimi(utf16_xml("utf-16"))
    ayet_sayilari._bildirim_yedek_denetimi(sentetik_xml())  # temiz XML gecer


# --- Sabit toplamlar -----------------------------------------------------------------------


def test_toplam_yanlissa_reddedilir(tmp_path: Path) -> None:
    sayilar = list(SENTETIK_SAYILAR)
    sayilar[-1] += 1
    kok, sonuc = uret(tmp_path, sentetik_xml(sayilar))
    assert sonuc.exit_code == 2
    assert "toplami" in sonuc.output
    assert not (kok / ayet_sayilari.JSON_YOLU).exists()


def test_ikinci_sure_yanlissa_reddedilir(tmp_path: Path) -> None:
    sayilar = list(SENTETIK_SAYILAR)
    sayilar[1] -= 1
    sayilar[-1] += 1  # toplam korunur; yalniz 2. sure sapar
    kok, sonuc = uret(tmp_path, sentetik_xml(sayilar))
    assert sonuc.exit_code == 2
    assert "2. sure" in sonuc.output
    assert not (kok / ayet_sayilari.JSON_YOLU).exists()
