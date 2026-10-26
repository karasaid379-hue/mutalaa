"""`mutalaa_pipeline.enums` testleri (A06.2): siniflar `enums.json` ile ayni."""

import json
from enum import StrEnum
from pathlib import Path

import pytest

from mutalaa_pipeline.enums import (
    DerlemeTuru,
    IncelemeDurumu,
    LicenseStatus,
    MetinDurumu,
    SourceKind,
    SurumDurumu,
    UnitKind,
    UnitStatus,
    XrefOrigin,
    XrefStatus,
    XrefType,
)
from mutalaa_pipeline.export.ortak import GirdiHatasi, depo_koku, kati_json, utf8_oku

JSON_YOLU = "packages/content-schema/enums.json"

SINIFLAR: dict[str, type[StrEnum]] = {
    "license_status": LicenseStatus,
    "xref_type": XrefType,
    "xref_status": XrefStatus,
    "xref_origin": XrefOrigin,
    "source_kind": SourceKind,
    "derleme_turu": DerlemeTuru,
    "unit_kind": UnitKind,
    "unit_status": UnitStatus,
    "metin_durumu": MetinDurumu,
    "inceleme_durumu": IncelemeDurumu,
    "surum_durumu": SurumDurumu,
}

BEKLENEN_SAYILAR = {
    "license_status": 4,
    "xref_type": 8,
    "xref_status": 3,
    "xref_origin": 3,
    "unit_kind": 7,
    "unit_status": 2,
    "metin_durumu": 3,
    "inceleme_durumu": 4,
    "surum_durumu": 5,
}


def enums_yukle(yol: Path | None = None) -> dict[str, tuple[str, ...]]:
    """Enum JSON'unu kati okur; `yol` verilmezse depodaki dosya okunur."""
    hedef = yol if yol is not None else depo_koku() / JSON_YOLU
    veri = kati_json(utf8_oku(hedef, hedef.name))
    assert isinstance(veri, dict)
    enums = veri["enums"]
    assert isinstance(enums, dict)
    sonuc: dict[str, tuple[str, ...]] = {}
    for ad, degerler in enums.items():
        assert isinstance(degerler, list)
        assert all(isinstance(d, str) for d in degerler)
        sonuc[ad] = tuple(degerler)
    return sonuc


def farklar(
    json_enums: dict[str, tuple[str, ...]],
    siniflar: dict[str, type[StrEnum]] = SINIFLAR,
) -> list[str]:
    """JSON ile siniflar arasindaki farklari listeler (bos liste = ayni)."""
    sonuc: list[str] = []
    for ad in sorted(set(json_enums) - set(siniflar)):
        sonuc.append(f"{ad}: JSON'da var, Python'da sinif yok")
    for ad in sorted(set(siniflar) - set(json_enums)):
        sonuc.append(f"{ad}: Python'da sinif var, JSON'da yok")
    for ad in sorted(set(json_enums) & set(siniflar)):
        python = tuple(uye.value for uye in siniflar[ad])
        if python != json_enums[ad]:
            sonuc.append(f"{ad}: JSON {json_enums[ad]} != Python {python}")
    return sonuc


def test_json_yuklenir_ve_tur_kumesi_tam() -> None:
    json_enums = enums_yukle()
    assert set(json_enums) == set(SINIFLAR)
    for ad, sayi in BEKLENEN_SAYILAR.items():
        assert len(json_enums[ad]) == sayi


@pytest.mark.parametrize("ad", sorted(SINIFLAR))
def test_degerler_json_ile_ayni_sirada(ad: str) -> None:
    json_enums = enums_yukle()
    python = tuple(uye.value for uye in SINIFLAR[ad])
    assert python == json_enums[ad]


@pytest.mark.parametrize("ad", sorted(SINIFLAR))
def test_uye_adi_deger_buyuk_harf(ad: str) -> None:
    for uye in SINIFLAR[ad]:
        assert uye.name == uye.value.upper()
        assert SINIFLAR[ad](uye.value) is uye


def test_degerler_tekil() -> None:
    for ad, degerler in enums_yukle().items():
        assert len(set(degerler)) == len(degerler), ad


def test_farklar_gercek_dosyada_bos() -> None:
    assert farklar(enums_yukle()) == []


def test_kisitlilik_sirasi_json_sirasidir() -> None:
    json_etiketleri = enums_yukle()["license_status"]
    assert json_etiketleri == ("serbest", "bekliyor", "ic_kullanim", "kapali")
    for sira, etiket in enumerate(json_etiketleri):
        assert LicenseStatus(etiket).kisitlilik_sirasi() == sira
    assert LicenseStatus.SERBEST.kisitlilik_sirasi() < LicenseStatus.BEKLIYOR.kisitlilik_sirasi()
    assert LicenseStatus.IC_KULLANIM.kisitlilik_sirasi() < LicenseStatus.KAPALI.kisitlilik_sirasi()


# --- Bozma denemesi: gercek dosyaya dokunulmaz, gecici kopya kullanilir ---------------------


def kopya_yaz(tmp_path: Path, degistir: dict[str, list[str]]) -> Path:
    kaynak = depo_koku() / JSON_YOLU
    veri = json.loads(kaynak.read_bytes().decode("utf-8"))
    for ad, degerler in degistir.items():
        veri["enums"][ad] = degerler
    hedef = tmp_path / "enums.json"
    hedef.write_text(json.dumps(veri, indent=2), encoding="utf-8", newline="\n")
    return hedef


def test_kopya_degismeden_yesil(tmp_path: Path) -> None:
    assert farklar(enums_yukle(kopya_yaz(tmp_path, {}))) == []


def test_silinen_deger_kirmizi(tmp_path: Path) -> None:
    gercek = list(enums_yukle()["license_status"])
    silinmis = [d for d in gercek if d != "ic_kullanim"]
    bulunan = farklar(enums_yukle(kopya_yaz(tmp_path, {"license_status": silinmis})))
    assert len(bulunan) == 1
    assert bulunan[0].startswith("license_status:")


def test_sira_degisikligi_kirmizi(tmp_path: Path) -> None:
    gercek = list(enums_yukle()["xref_status"])
    ters = list(reversed(gercek))
    assert farklar(enums_yukle(kopya_yaz(tmp_path, {"xref_status": ters})))


def test_eklenen_deger_kirmizi(tmp_path: Path) -> None:
    gercek = list(enums_yukle()["derleme_turu"])
    assert farklar(enums_yukle(kopya_yaz(tmp_path, {"derleme_turu": [*gercek, "yeni"]})))


def test_eksik_tur_kirmizi(tmp_path: Path) -> None:
    json_enums = enums_yukle(kopya_yaz(tmp_path, {}))
    del json_enums["source_kind"]
    bulunan = farklar(json_enums)
    assert bulunan == ["source_kind: Python'da sinif var, JSON'da yok"]


def test_ek_tur_kirmizi() -> None:
    json_enums = enums_yukle()
    json_enums["yeni_tur"] = ("a",)
    assert farklar(json_enums) == ["yeni_tur: JSON'da var, Python'da sinif yok"]


def test_yinelenen_anahtar_girdi_hatasi(tmp_path: Path) -> None:
    yol = tmp_path / "enums.json"
    yol.write_text('{"enums": {"a": [], "a": []}}', encoding="utf-8", newline="\n")
    with pytest.raises(GirdiHatasi):
        enums_yukle(yol)
