"""`qa/gold/setler.py`: manifest zorunlu alanlari, bolme, surum, dongusellik (A18.5; SENTETIK)."""

import json
from datetime import date
from pathlib import Path

import pytest

from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.qa.gold import setler

KAYNAK = {"source_id": "kaynak-a", "surum": "1", "madde": "satir 1"}


def _ornek(i: int, **degisim: object) -> dict[str, object]:
    o: dict[str, object] = {
        "id": f"ornek-{i}",
        "sinif": "silver",
        "kaynak": dict(KAYNAK),
        "dogrulama_yontemi": "sentetik deneme",
        "uretim_komutu": "deneme komutu",
        "veri": i,
    }
    o.update(degisim)
    return o


def _taslak(**degisim: object) -> dict[str, object]:
    t: dict[str, object] = {
        "sinif": "silver",
        "olcum_turu": "dogruluk",
        "kaynak": [{**KAYNAK, "rol": "kanit"}],
        "dogrulama_yontemi": "sentetik deneme",
        "uretim_komutu": "deneme komutu",
        "tohum": 7,
    }
    t.update(degisim)
    return t


# --- bolme ---------------------------------------------------------------------------------------


def test_bolme_deterministik_ve_tohuma_bagli() -> None:
    a = [setler.bolme("kok", f"id-{i}", 1) for i in range(200)]
    assert a == [setler.bolme("kok", f"id-{i}", 1) for i in range(200)]
    assert a != [setler.bolme("kok", f"id-{i}", 2) for i in range(200)]
    assert a != [setler.bolme("lemma", f"id-{i}", 1) for i in range(200)]


def test_bolme_yuzde_40_60() -> None:
    n = 20000
    gel = sum(1 for i in range(n) if setler.bolme("kok", f"id-{i}") == setler.GELISTIRME)
    assert abs(gel / n - 0.40) < 0.01  # sha256 dagilimi: sapma 1 puanin altinda
    assert {setler.bolme("kok", f"x{i}") for i in range(50)} == {
        setler.GELISTIRME,
        setler.DONDURULMUS,
    }


def test_bolme_bilinen_deger_kilidi() -> None:
    # sha256("1:kok:id-0") ilk 8 hane mod 100: degisirse bolme degisir (dondurulmus parca kayar)
    import hashlib

    ozet = hashlib.sha256(b"1:kok:id-0").hexdigest()
    beklenen = setler.GELISTIRME if int(ozet[:8], 16) % 100 < 40 else setler.DONDURULMUS
    assert setler.bolme("kok", "id-0", 1) == beklenen


# --- zorunlu alanlar -----------------------------------------------------------------------------


@pytest.mark.parametrize("alan", ["id", "sinif", "kaynak", "dogrulama_yontemi", "uretim_komutu"])
def test_ornek_zorunlu_alan_eksikse_hata(alan: str) -> None:
    o = _ornek(1)
    del o[alan]
    with pytest.raises(GirdiHatasi, match=alan):
        setler.ornek_dogrula(o)
    with pytest.raises(GirdiHatasi, match=alan):
        setler.ornek_dogrula({**_ornek(1), alan: ""})


def test_ornek_gecersiz_sinif_ve_kaynak() -> None:
    with pytest.raises(GirdiHatasi, match="sinif"):
        setler.ornek_dogrula(_ornek(1, sinif="gumus"))
    with pytest.raises(GirdiHatasi, match="kaynak"):
        setler.ornek_dogrula(_ornek(1, kaynak={"source_id": "x"}))  # surum, madde yok
    setler.ornek_dogrula(_ornek(1, kaynak=[KAYNAK, KAYNAK]))  # kaynak listesi gecerli


@pytest.mark.parametrize(
    "alan", ["sinif", "olcum_turu", "kaynak", "dogrulama_yontemi", "uretim_komutu", "tohum"]
)
def test_manifest_zorunlu_alan_eksikse_hata(alan: str, tmp_path: Path) -> None:
    taslak = _taslak()
    del taslak[alan]
    with pytest.raises(GirdiHatasi):
        setler.set_yaz(tmp_path, "kok", taslak, [_ornek(1)])


def test_manifest_rol_zorunlu() -> None:
    kotu = _taslak(kaynak=[dict(KAYNAK)])  # rol yok
    with pytest.raises(GirdiHatasi, match="rol"):
        setler.set_hazirla("kok", kotu, [_ornek(1)])
    with pytest.raises(GirdiHatasi, match="olcum_turu"):
        setler.set_hazirla("kok", _taslak(olcum_turu="belirsiz"), [_ornek(1)])


def test_set_hazirla_eksik_ornek_alani_hata() -> None:
    kotu = _ornek(1)
    del kotu["uretim_komutu"]
    with pytest.raises(GirdiHatasi, match="uretim_komutu"):
        setler.set_hazirla("kok", _taslak(), [kotu])


def test_ornek_kimlikleri_tekil_olmali() -> None:
    with pytest.raises(GirdiHatasi, match="tekil"):
        setler.set_hazirla("kok", _taslak(), [_ornek(1), _ornek(1)])


# --- yazma, okuma, surum -------------------------------------------------------------------------


def test_set_yaz_oku_gidis_donus_ve_surum(tmp_path: Path) -> None:
    ornekler = [_ornek(i) for i in range(10)]
    manifest, klasor = setler.set_yaz(
        tmp_path, "kok", _taslak(), ornekler, bugun=date(2026, 11, 13)
    )
    assert str(manifest["surum"]).startswith("2026-11-13-")
    assert setler.SURUM_DESENI.fullmatch(str(manifest["surum"]))
    assert klasor == tmp_path / "gold" / "kok" / str(manifest["surum"])
    assert manifest["ornek_sayisi"] == 10
    assert int(str(manifest["gelistirme_sayisi"])) + int(str(manifest["dondurulmus_sayisi"])) == 10
    okunan, okunan_ornekler, yol = setler.set_oku(tmp_path, "kok")
    assert okunan == json.loads((klasor / "manifest.json").read_bytes().decode("ascii"))
    assert okunan_ornekler == ornekler and yol == klasor
    assert okunan["sinif"] == "silver" and okunan["tohum"] == 7


def test_ayni_icerik_ayni_surum_farkli_icerik_yeni_surum(tmp_path: Path) -> None:
    gun = date(2026, 11, 13)
    m1, k1 = setler.set_yaz(tmp_path, "kok", _taslak(), [_ornek(1)], bugun=gun)
    m2, k2 = setler.set_yaz(tmp_path, "kok", _taslak(), [_ornek(1)], bugun=gun)
    assert m1["surum"] == m2["surum"] and k1 == k2
    m3, k3 = setler.set_yaz(tmp_path, "kok", _taslak(), [_ornek(1), _ornek(2)], bugun=gun)
    assert m3["surum"] != m1["surum"] and k3 != k1
    assert setler.son_surum(tmp_path, "kok") == max(str(m1["surum"]), str(m3["surum"]))


def test_set_oku_degismis_icerik_hata(tmp_path: Path) -> None:
    _, klasor = setler.set_yaz(tmp_path, "kok", _taslak(), [_ornek(1)])
    (klasor / "ornekler.jsonl").write_bytes(b'{"id":"x"}\n')
    with pytest.raises(GirdiHatasi, match="ozet"):
        setler.set_oku(tmp_path, "kok")


def test_set_oku_set_yoksa_ve_bilinmeyen_set(tmp_path: Path) -> None:
    with pytest.raises(GirdiHatasi, match="build"):
        setler.set_oku(tmp_path, "kok")
    with pytest.raises(GirdiHatasi, match="bilinmeyen"):
        setler.set_dizini(tmp_path, "olmayan")


def test_dry_run_icin_set_hazirla_dosya_yazmaz(tmp_path: Path) -> None:
    manifest, baytlar = setler.set_hazirla("kok", _taslak(), [_ornek(1)])
    assert manifest["ornek_sayisi"] == 1 and baytlar.endswith(b"\n")
    assert not (tmp_path / "gold").exists()


# --- dongusellik ---------------------------------------------------------------------------------


def test_dongusellik_kesisim_hata_yalniz_kaynak_adlari() -> None:
    set_kaynak = [
        {**KAYNAK, "rol": "kanit"},
        {"source_id": "ortak-sozluk", "surum": "1", "madde": "x", "rol": "sozluk"},
    ]
    setler.dongusellik_denetle(set_kaynak, {"baska-kaynak"})  # kesisim yok
    with pytest.raises(GirdiHatasi) as hata:
        setler.dongusellik_denetle(set_kaynak, {"kaynak-a", "baska"})
    assert "kaynak-a" in str(hata.value)
    assert "satir 1" not in str(hata.value)  # madde/icerik yazilmaz
    assert "dongusellik" in str(hata.value)


def test_dongusellik_sozluk_ve_arac_rolu_sayilmaz() -> None:
    set_kaynak = [
        {"source_id": "ortak", "surum": "1", "madde": "x", "rol": "sozluk"},
        {"source_id": "arac", "surum": "1", "madde": "x", "rol": "arac"},
    ]
    setler.dongusellik_denetle(set_kaynak, {"ortak", "arac"})


def test_manifest_dongusellik_olcum_turune_gore() -> None:
    manifest = _taslak()
    with pytest.raises(GirdiHatasi, match="kaynak-a"):
        setler.manifest_dongusellik_denetle(manifest, {"kaynak-a"})
    for tur in ("tutarlilik", "motor_testi"):  # muaf turler
        setler.manifest_dongusellik_denetle(_taslak(olcum_turu=tur), {"kaynak-a"})
