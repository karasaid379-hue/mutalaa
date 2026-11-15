"""Atif araci olcum duzenegi (A20.7a): orneklem, kontroller ve rapor.

Birim satirlari sentetiktir ("Deneme paragrafi ...", Arap alfabesi harfleri). Kur'an metni
gercek dosyadan yalniz sayi denetimi icin (varsa) okunur; hicbir test metin yazdirmaz.
"""

import json
from pathlib import Path
from typing import Any

import pytest

from mutalaa_pipeline.enrich import arac_olcumu as olcum
from mutalaa_pipeline.staged import satir_baytlari

DIZI = "ابت ثجح خدذ هوز"  # sentetik
KISA_DIZI = "ابت"
BOS_KOK = Path(__file__).resolve().parents[2]


def _birim(sira: int, dil: str, kitap: str, ar: int, sayi: int) -> dict[str, object]:
    """Sentetik `units.jsonl` satiri: `ar` = 0 (isaret yok), 1 (tek kelimelik) ya da 3 (uzun).

    `sayi` adet rakam dizisi eklenir (capa numarasi metne girmez).
    """
    metin = "Deneme paragrafi " + " ".join(f"{i + 100}" for i in range(sayi))
    marks: list[dict[str, object]] = []
    dizi = KISA_DIZI if ar == 1 else DIZI
    for _ in range(ar):
        bas = len(metin) + 1
        metin += " " + dizi
        marks.append({"t": "ar", "s": bas, "e": bas + len(dizi), "tur": "blok"})
    return {
        "anchor": f"rn:{kitap}:p{sira}",
        "attrs": {"dil": dil},
        "content_hash": f"{sira:064x}",
        "marks": marks,
        "role": "govde",
        "text": metin,
    }


def _birimler() -> list[dict[str, object]]:
    sonuc: list[dict[str, object]] = []
    sira = 0
    for dil in ("tr", "ota", "ar"):
        for kitap in (f"{dil}-kitap-a", f"{dil}-kitap-b"):
            for ar in (0, 1, 3):
                for sayi in (0, 2, 5):
                    for _ in range(4):
                        sira += 1
                        sonuc.append(_birim(sira, dil, kitap, ar, sayi))
    return sonuc


def _adaylar() -> list[olcum.Aday]:
    adaylar = [olcum.aday_olustur(v) for v in _birimler()]
    return [a for a in adaylar if a is not None]


def test_sayi_say() -> None:
    assert olcum.sayi_say("Deneme 12 ve 345, ve ٢٣ x7") == 4
    assert olcum.sayi_say("Deneme paragrafi") == 0


def test_aday_ozellikleri_ve_tabaka() -> None:
    kisa = olcum.aday_olustur(_birim(1, "tr", "tr-kitap-a", 1, 0))
    assert kisa is not None
    assert (kisa.ar_isaret, kisa.ar_kelime, kisa.sayi) == (1, 1, 0)
    assert kisa.tabaka == "tr|kisa|yok"
    uzun = olcum.aday_olustur(_birim(4, "tr", "tr-kitap-a", 3, 1))
    assert uzun is not None
    assert (uzun.ar_isaret, uzun.ar_kelime, uzun.sayi) == (3, 12, 1)
    assert uzun.tabaka == "tr|uzun|az"  # 4 kelime ve uzeri: uzun (kisa: 4 kelimeden az)
    kucuk = _birim(2, "ota", "ota-kitap-a", 0, 3)
    kucuk["marks"] = [{"t": "ar", "s": 0, "e": 3, "tur": "alinti"}]
    aday = olcum.aday_olustur(kucuk)
    assert aday is not None
    assert (aday.tabaka_ar, aday.tabaka_sayi) == ("kisa", "cok")
    assert olcum.aday_olustur({**_birim(3, "tr", "tr-kitap-a", 0, 0), "text": ""}) is None


def test_dagit() -> None:
    assert olcum.dagit({"a": 100, "b": 100, "c": 100}, 9) == {"a": 3, "b": 3, "c": 3}
    # kucuk tabakanin payi digerlerine gecer
    assert olcum.dagit({"a": 1, "b": 100, "c": 100}, 11) == {"a": 1, "b": 5, "c": 5}
    assert olcum.dagit({"a": 2, "b": 3}, 100) == {"a": 2, "b": 3}
    assert sum(olcum.dagit({"a": 7, "b": 50, "c": 50, "d": 3}, 40).values()) == 40


def test_orneklem_sabit_tohumla_ayni() -> None:
    adaylar = _adaylar()
    a = olcum.orneklem_sec(adaylar, 60, olcum.TOHUM)
    b = olcum.orneklem_sec(list(reversed(adaylar)), 60, olcum.TOHUM)
    assert [x.anchor for x in a] == [x.anchor for x in b]
    assert len(a) == len({x.anchor for x in a}) == 60
    assert olcum.ornek_baytlari(a) == olcum.ornek_baytlari(b)
    baska = olcum.orneklem_sec(adaylar, 60, olcum.TOHUM + 1)
    assert [x.anchor for x in baska] != [x.anchor for x in a]


def test_orneklem_tabakali_ve_kitaplara_dagilir() -> None:
    adaylar = _adaylar()
    secilen = olcum.orneklem_sec(adaylar, 54, olcum.TOHUM)  # 3 dil x 3 ar x 3 sayi = 27 x 2
    tabakalar: dict[str, int] = {}
    for a in secilen:
        tabakalar[a.tabaka] = tabakalar.get(a.tabaka, 0) + 1
    assert len(tabakalar) == 27
    assert set(tabakalar.values()) == {2}
    kitaplar = {(a.tabaka, a.kitap) for a in secilen}
    assert len(kitaplar) == 54  # her tabakada iki kitap birden


def test_orneklem_capaya_gore_sirali() -> None:
    secilen = olcum.orneklem_sec(_adaylar(), 30, olcum.TOHUM)
    capalar = [a.anchor for a in secilen]
    assert capalar == sorted(capalar, key=lambda c: (c.split(":")[1], int(c.rsplit(":p", 1)[1])))


def test_ornek_dosyasi_metin_tasimaz(tmp_path: Path) -> None:
    secilen = olcum.orneklem_sec(_adaylar(), 20, olcum.TOHUM)
    veri = olcum.ornek_baytlari(secilen)
    assert veri.isascii()
    assert b"Deneme" not in veri
    for satir in veri.decode("ascii").splitlines():
        kayit = json.loads(satir)
        assert set(kayit) == {
            "anchor",
            "ar_isaret",
            "ar_kelime",
            "content_hash",
            "dil",
            "kitap",
            "role",
            "sayi",
            "tabaka",
            "uzunluk",
        }


def test_ornek_uret_idempotent(tmp_path: Path) -> None:
    units = tmp_path / "units.jsonl"
    units.write_bytes(b"".join(satir_baytlari(v) for v in _birimler()))
    cikti = tmp_path / "gold" / "ornek.jsonl"
    assert olcum.ornek_uret(units, cikti, 25, olcum.TOHUM) == 25
    ilk = cikti.read_bytes()
    cikti.touch()
    once = cikti.stat().st_mtime_ns
    assert olcum.ornek_uret(units, cikti, 25, olcum.TOHUM) == 25
    assert cikti.read_bytes() == ilk
    assert cikti.stat().st_mtime_ns == once
    assert len(olcum.ornegi_oku(cikti)) == 25


def test_ornek_komutu_cikis_kodlari(tmp_path: Path) -> None:
    units = tmp_path / "units.jsonl"
    units.write_bytes(b"".join(satir_baytlari(v) for v in _birimler()))
    cikti = tmp_path / "ornek.jsonl"
    assert olcum.main(["ornek", "--units", str(units), "--cikti", str(cikti), "--n", "10"]) == 0
    bozuk = tmp_path / "bozuk.jsonl"
    bozuk.write_bytes(b"{yanlis\n")
    assert olcum.main(["ornek", "--units", str(bozuk), "--cikti", str(tmp_path / "x.jsonl")]) == 2


def test_dagilim_ve_yuzdelik() -> None:
    assert olcum.dagilim([]) == {"n": 0}
    d = olcum.dagilim([1, 2, 3, 4, 5])
    assert (d["n"], d["min"], d["p50"], d["maks"], d["ort"]) == (5, 1, 3, 5, 3.0)
    assert olcum.yuzdelik([], 0.5) is None


def _ayetler() -> list[tuple[int, int, str, str]]:
    kelimeler = [f"{chr(0x0628 + (i % 20))}{chr(0x0628 + ((i * 3) % 20))}ب" for i in range(40)]
    sonuc = []
    for ayet in range(1, 7):
        metin = " ".join(kelimeler[ayet : ayet + 9])
        sonuc.append((1, ayet, metin, metin))
    return sonuc


def test_kontrol_uret_sabit_tohum_ve_turler() -> None:
    a = olcum.kontrol_uret(_ayetler(), olcum.TOHUM, 3)
    b = olcum.kontrol_uret(_ayetler(), olcum.TOHUM, 3)
    assert a == b
    turler = [k["tur"] for k in a]
    assert turler.count("negatif") == 3
    assert {t for t in turler if t != "negatif"} == {
        "uthmani_tam",
        "basit_tam",
        "yalin_tam",
        "yalin_kismi",
    }
    for kontrol in a:
        kelime = len(kontrol["metin"].split())
        if kontrol["tur"] == "negatif":
            assert kontrol["hedef"] is None and kelime == 8
        elif kontrol["tur"] == "yalin_kismi":
            assert kelime == 5
    assert olcum.kontrol_uret(_ayetler(), olcum.TOHUM + 1, 3) != a


def _ham_arac(ad: str, bulan: dict[tuple[str, int], list[Any]]) -> dict[str, Any]:
    """Sentetik ham kosu ciktisi: `bulan` (capa, dizi sirasi) -> eslesme listesi."""
    dizi = []
    for (capa, sira), es in sorted(bulan.items()):
        dizi.append(
            {
                "a": capa,
                "i": sira,
                "dil": "tr",
                "tur": "alinti",
                "b": 0,
                "cp": 20,
                "kelime": 4,
                "sn": 0.001,
                "es": es,
                "hata": None,
            }
        )
    return {
        "rapor_surumu": 1,
        "arac": ad,
        "surum": "1.0",
        "python": "3.13.0",
        "kurulum_sn": 0.1,
        "bellek_mb": {"baslangic_simdiki": 1.0, "kurulum_sonrasi_simdiki": 2.0, "tepe": 3.0},
        "dizi_modu": dizi,
        "tam_modu": [
            {
                "a": capa,
                "dil": "tr",
                "cp": 100,
                "sn": 0.002,
                "isaretler": [[0, 20, "alinti"]],
                "es": es,
                "hata": None,
            }
            for (capa, sira), es in sorted(bulan.items())
            if sira == 0
        ],
        "kontrol": [
            {
                "tur": "uthmani_tam",
                "hedef": [2, 255],
                "adaylar": [[2, 255]],
                "es": 1,
                "sn": 0.1,
                "hata": None,
            },
            {"tur": "negatif", "hedef": None, "adaylar": [], "es": 0, "sn": 0.1, "hata": None},
        ],
    }


def test_rapor_birlestirme_metin_tasimaz(tmp_path: Path) -> None:
    birimler = [_birim(i, "tr", "tr-kitap-a", 1, 2) for i in range(1, 4)]
    units = tmp_path / "units.jsonl"
    units.write_bytes(b"".join(satir_baytlari(v) for v in birimler))
    ornek = tmp_path / "ornek.jsonl"
    olcum.ornek_uret(units, ornek, 3, olcum.TOHUM)
    capalar = [s["anchor"] for s in olcum.ornegi_oku(ornek)]
    es_a = [[0, 10, [[2, 255]], 0.9, 3]]
    es_b = [[0, 10, [[2, 255], [2, 256]], None, 3]]
    ham = tmp_path / "ham"
    ham.mkdir()
    for ad, es in (("ijaza", es_a), ("quran-detector", es_b)):
        govde = _ham_arac(ad, {(capalar[0], 0): es, (capalar[1], 0): [], (capalar[2], 0): es})
        (ham / f"{ad}.json").write_text(json.dumps(govde), encoding="utf-8")
    cikti = tmp_path / "reports" / "a20-atif-araclari.json"
    rapor = olcum.rapor_uret(ham, ornek, units, cikti)
    assert rapor["etiket_durumu"] == "etiketlenmemis"
    assert rapor["kosulmayan_araclar"] == ["quran-toolkit"]
    assert rapor["orneklem"]["n"] == 3
    assert rapor["uyum"]["ortak_dizi"] == 3
    cift = rapor["uyum"]["dizi_modu_ciftler"]["ijaza+quran-detector"]
    assert (cift["ikisi_de_buldu"], cift["kesisim_orani"], cift["tam_ayni_kume_orani"]) == (
        2,
        1.0,
        0.0,
    )
    assert rapor["araclar"]["ijaza"]["dizi_modu"]["bulunan_dizi"] == 2
    assert rapor["araclar"]["ijaza"]["kontrol"]["negatif"]["yanlis_bulma_orani"] == 0.0
    assert rapor["alinti_ve_blok_yoklamasi"]["alinti"]["tumu"]["en_az_bir_arac"]["bulan"] == 2
    # rapor ham dosyadaki gibi yalniz sayi tasir; birim metni ve Arapca harf yok
    metin = cikti.read_text(encoding="utf-8")
    assert metin.isascii()
    assert "Deneme" not in metin
    assert json.loads(metin) == rapor


def test_rapor_arac_kurulamazsa_kosulamadi(tmp_path: Path) -> None:
    ozet = olcum.arac_ozeti({"arac": "x", "surum": "1.0", "kurulum_hatasi": "ImportError"})
    assert ozet == {"surum": "1.0", "kosulamadi": "ImportError"}


def test_uyum_tek_arac_yetersiz() -> None:
    ham = _ham_arac("ijaza", {("rn:k:p1", 0): []})
    assert olcum.uyum_ozeti({"ijaza": ham}) == {"yetersiz_arac": True}


def test_tanzil_gercek_dosya_sayilari() -> None:
    uthmani = BOS_KOK / "data/gelen/tanzil-uthmani/2026-11-13/quran-uthmani.txt"
    basit = BOS_KOK / "data/gelen/tanzil-simple-clean/2026-11-13/quran-simple-clean.txt"
    if not (uthmani.is_file() and basit.is_file()):
        pytest.skip("Tanzil dosyalari data/gelen altinda yok")
    ayetler = olcum.tanzil_oku(uthmani, basit)
    assert len(ayetler) == 6236
    assert (ayetler[0][0], ayetler[0][1]) == (1, 1)
    assert (ayetler[-1][0], ayetler[-1][1]) == (114, 6)
