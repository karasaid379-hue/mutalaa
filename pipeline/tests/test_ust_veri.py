"""Tanzil ust veri alimi, kilit, isaret ve sayfa satirlari, `anchor/sayfa.py` (A11; SENTETIK).

XML sentetiktir (`ust_veri_yardimci.sentetik_xml`): gercek sure tablosu, esit aralikli sentetik
baslangiclar. Gercek `quran-data.xml` ile sinama `test_ust_veri_gercek.py` ve
`test_degismezlik.py` Test 7'dedir (veri yoksa atlanir). Hicbir deger hafizadan yazilmaz.
"""

import copy
import json
from pathlib import Path
from typing import Any

import pytest
from hat_yardimci import ctx_kur
from test_sources import kok_kur
from ust_veri_yardimci import (
    GRUP_BOYUTLARI,
    SECDE_SAYISI,
    TARIH,
    URL,
    kayitlari_yaz,
    kilit_xml_icin,
    konum,
    sentetik_kelimeler,
    sentetik_xml,
)

from mutalaa_pipeline import lineage
from mutalaa_pipeline.adimlar.anchor_ust_veri import (
    ayet_bilgisi,
    isaret_satirlari,
    sayfa_satirlari,
)
from mutalaa_pipeline.anchor.ayet_sayilari import AYET_SAYILARI
from mutalaa_pipeline.anchor.sayfa import SayfaHatasi, SayfaTablosu, sayfa_araligi, sayfa_bul
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.ingest import tanzil, tanzil_ust_veri
from mutalaa_pipeline.ingest.tanzil_ust_veri import (
    KAYNAK,
    YAPI_DOSYALARI,
    kilit_denetle,
    run_ust_veri,
    yapi_ayristir,
)

# --- XML ayristirma ----------------------------------------------------------------------------


def test_sentetik_xml_yapisi_ve_sayilar_dosyadan() -> None:
    yapi = yapi_ayristir(sentetik_xml(), "1.0")
    assert set(yapi) == set(YAPI_DOSYALARI)
    assert len(yapi["sure"]) == len(AYET_SAYILARI)
    assert len(yapi["cuz"]) == GRUP_BOYUTLARI["juzs"]
    assert len(yapi["rub"]) == GRUP_BOYUTLARI["hizbs"]
    assert len(yapi["menzil"]) == GRUP_BOYUTLARI["manzils"]
    assert len(yapi["ruku"]) == GRUP_BOYUTLARI["rukus"]
    assert len(yapi["sayfa"]) == GRUP_BOYUTLARI["pages"]
    assert len(yapi["secde"]) == SECDE_SAYISI
    assert [s["ayas"] for s in yapi["sure"]] == list(AYET_SAYILARI)


def test_satir_alanlari_tur_no_sura_aya() -> None:
    yapi = yapi_ayristir(sentetik_xml(), "1.0")
    for tur, satirlar in yapi.items():
        assert [s["no"] for s in satirlar] == list(range(1, len(satirlar) + 1)), tur
        assert all(s["tur"] == tur for s in satirlar)
        assert all("sura" in s and "aya" in s for s in satirlar)
    sure = yapi["sure"][1]
    assert set(sure) == {
        "tur",
        "no",
        "sura",
        "aya",
        "ad_ar",
        "tname",
        "ename",
        "type",
        "order",
        "ayas",
        "start",
        "rukus",
    }
    assert (sure["ad_ar"], sure["tname"], sure["ename"]) == ("Deneme 2", "Deneme-2", "Deneme 2")
    assert {s["type"] for s in yapi["secde"]} == {"recommended", "obligatory"}
    assert all("type" not in s for s in yapi["cuz"])


def test_okuma_sirasi_artan_ve_ilk_konum_dosyadan() -> None:
    yapi = yapi_ayristir(sentetik_xml(), "1.0")
    for tur in ("cuz", "rub", "menzil", "ruku", "sayfa", "secde"):
        konumlar = [(s["sura"], s["aya"]) for s in yapi[tur]]
        assert konumlar == sorted(set(konumlar)), tur


def _degistir(islev: Any) -> bytes:
    return sentetik_xml(degistir=islev)


BOZUK_XML: dict[str, Any] = {
    "indeks_atlamis": lambda g: g["juzs"][3].update(index=9),
    "sura_tabloda_yok": lambda g: g["juzs"][1].update(sura=115),
    "aya_tabloda_yok": lambda g: g["juzs"][1].update(sura=1, aya=8),
    "sira_azalan": lambda g: g["pages"][5].update(sura=1, aya=1),
    "secde_etiketi_bilinmeyen": lambda g: g["sajdas"][0].update(type="wajib"),
    "secde_etiketi_yok": lambda g: g["sajdas"][0].pop("type"),
    "sayi_degil": lambda g: g["rukus"][0].update(sura="x"),
    "grup_bos": lambda g: g.update(manzils=[]),
    "sure_adi_bos": lambda g: g["suras"][0].update(name=""),
    "sure_sirasiz": lambda g: g["suras"][0].update(index=2),
    "ayet_toplami": lambda g: g["suras"][0].update(ayas=8),
}


@pytest.mark.parametrize("kimlik", sorted(BOZUK_XML))
def test_bozuk_xml_reddedilir(kimlik: str) -> None:
    with pytest.raises(GirdiHatasi) as hata:
        yapi_ayristir(_degistir(BOZUK_XML[kimlik]), "1.0")
    assert str(hata.value).isascii()


def test_eksik_grup_ve_bilinmeyen_oge_reddedilir() -> None:
    def grubu_sil(g: dict[str, list[dict[str, object]]]) -> None:
        g.pop("pages")

    with pytest.raises(GirdiHatasi, match="pages"):
        yapi_ayristir(_degistir(grubu_sil), "1.0")


def test_surum_kilitle_ayni_olmali() -> None:
    with pytest.raises(GirdiHatasi, match="surum"):
        yapi_ayristir(sentetik_xml(surum="2.0"), "1.0")
    assert yapi_ayristir(sentetik_xml(surum="2.0"), "2.0")


@pytest.mark.parametrize(
    "onek",
    [
        '<!DOCTYPE quran [ <!ENTITY a "b"> ]>\n',
        '<!DOCTYPE quran SYSTEM "http://deneme.invalid/x.dtd">\n',
    ],
)
def test_doctype_ve_entity_reddedilir(onek: str) -> None:
    with pytest.raises(GirdiHatasi, match="DOCTYPE"):
        yapi_ayristir(sentetik_xml(onek=onek), "1.0")


def test_utf8_olmayan_xml_reddedilir() -> None:
    with pytest.raises(GirdiHatasi, match="UTF-8"):
        yapi_ayristir(sentetik_xml() + b"\xff", "1.0")


def test_ayet_sayilari_ayristiricisi_ayni_koruma_ile_calisir() -> None:
    """A04'un ayristiricisi ortak `guvenli_kok` uzerinden calisir (davranis degismedi)."""
    from mutalaa_pipeline.export import ayet_sayilari

    assert ayet_sayilari.ayristir(sentetik_xml()).sayilar == tuple(AYET_SAYILARI)
    with pytest.raises(GirdiHatasi, match="DOCTYPE"):
        ayet_sayilari.ayristir(sentetik_xml(onek="<!DOCTYPE x>\n"))


# --- kilit ---------------------------------------------------------------------------------------


def test_gercek_kilit_ust_veri_bolumu_ve_kayit_tutarli() -> None:
    kilit = tanzil.ust_veri_kilidi_yukle()
    assert list(tanzil.kilit_yukle()) == ["uthmani", "simple-clean"]  # varyantlar degismedi
    ham = tanzil.KILIT_YOLU.read_bytes()
    varyantlar, ust = tanzil.kilit_coz_tam(ham)
    assert ust == kilit
    assert tanzil.kilit_metni(varyantlar, ust).encode("utf-8") == ham  # kanonik bicim
    from mutalaa_pipeline import sources
    from mutalaa_pipeline.export.ortak import depo_koku

    sonuc = sources.oku(depo_koku() / "pipeline" / "sources" / f"{KAYNAK}.toml")
    assert sonuc.kaynak is not None, sonuc.hatalar
    assert (sonuc.kaynak.surum, sonuc.kaynak.kaynak_url) == (kilit.surum, kilit.url)
    # sha256 shared/data/ayet-sayilari.json ile ayni (A04 ayni dosyayi okudu)
    from mutalaa_pipeline.export import ayet_sayilari

    assert ayet_sayilari.json_oku(depo_koku()).sha256 == kilit.sha256


def _kilit_nesnesi() -> dict[str, Any]:
    nesne = json.loads(tanzil.KILIT_YOLU.read_bytes().decode("utf-8"))
    assert isinstance(nesne, dict)
    return nesne


BOZUK_KILIT: dict[str, Any] = {
    "nesne_degil": lambda n: n.update(ust_veri=[]),
    "alan_fazla": lambda n: n["ust_veri"].update(metin_sha256="a" * 64),
    "bildirim_alani": lambda n: n["ust_veri"].update(bildirim_sha256="a" * 64),
    "alan_eksik": lambda n: n["ust_veri"].pop("sha256"),
    "sha256_kisa": lambda n: n["ust_veri"].update(sha256="a" * 63),
    "sha256_buyuk": lambda n: n["ust_veri"].update(sha256="A" * 64),
    "boyut_sifir": lambda n: n["ust_veri"].update(boyut=0),
    "boyut_bool": lambda n: n["ust_veri"].update(boyut=True),
    "tarih_gecersiz": lambda n: n["ust_veri"].update(alinma_tarihi="2026-02-30"),
    "surum_harfli": lambda n: n["ust_veri"].update(surum="1.x"),
    "url_http": lambda n: n["ust_veri"].update(url="http://tanzil.net/x.xml"),
    "ust_alan_fazla": lambda n: n.update(baska=1),
}


@pytest.mark.parametrize("kimlik", sorted(BOZUK_KILIT))
def test_bozuk_ust_veri_kilidi_reddedilir(kimlik: str) -> None:
    nesne = _kilit_nesnesi()
    BOZUK_KILIT[kimlik](nesne)
    with pytest.raises(GirdiHatasi) as hata:
        tanzil.kilit_coz(json.dumps(nesne).encode("utf-8"))
    assert str(hata.value).startswith("tanzil.lock.json")
    assert str(hata.value).isascii()


def test_ust_veri_bolumu_istege_bagli_ama_yoksa_yuklenemez(tmp_path: Path) -> None:
    nesne = _kilit_nesnesi()
    del nesne["ust_veri"]
    yol = tmp_path / "kilit.json"
    yol.write_bytes(json.dumps(nesne).encode("utf-8"))
    assert list(tanzil.kilit_yukle(yol)) == ["uthmani", "simple-clean"]
    with pytest.raises(GirdiHatasi, match="ust_veri"):
        tanzil.ust_veri_kilidi_yukle(yol)


def test_kilit_metni_ust_veri_bolumunu_sona_yazar() -> None:
    varyantlar = tanzil.kilit_yukle()
    metin = tanzil.kilit_metni(varyantlar, kilit_xml_icin(b"deneme"))
    assert list(json.loads(metin)) == ["varyantlar", "ust_veri"]
    assert "ust_veri" not in json.loads(tanzil.kilit_metni(varyantlar))


def test_kilit_denetle_ozet_ve_boyut_uyusmazligi_cikis_2_uyarisiyla() -> None:
    veri = sentetik_xml()
    kilit = kilit_xml_icin(veri)
    kilit_denetle(kilit, veri)
    with pytest.raises(GirdiHatasi, match=r"kilit guncellenerek \(/karar\)"):
        kilit_denetle(kilit, veri + b" ")
    with pytest.raises(GirdiHatasi, match="ozeti kilitle tutmuyor"):
        kilit_denetle(kilit_xml_icin(b"baska"), veri)


# --- ingest calistirmasi (sahte depo) ------------------------------------------------------------


def _ingest_kur(tmp: Path, xml: bytes | None = None) -> tuple[Path, Path, bytes]:
    kok = kok_kur(tmp)
    kayitlari_yaz(kok)
    veri = xml if xml is not None else sentetik_xml()
    gelen = tmp / "data" / "gelen" / "tanzil-ust-veri" / TARIH
    gelen.mkdir(parents=True)
    (gelen / "quran-data.xml").write_bytes(veri)
    return kok, tmp / "data", veri


def _ingest_ctx(tmp: Path, kok: Path, **kw: object) -> Any:
    return ctx_kur(tmp, kok, adim="ingest", kaynaklar=[KAYNAK], **kw)  # type: ignore[arg-type]


def test_ingest_ham_kopya_staged_dosyalari_ve_manifest(tmp_path: Path) -> None:
    kok, veri_kok, xml = _ingest_kur(tmp_path)
    kilit = kilit_xml_icin(xml)
    ctx = _ingest_ctx(tmp_path, kok)
    sonuc = run_ust_veri(ctx, None, kilit)
    assert not sonuc.atlandi and sonuc.klasor is not None
    ham = veri_kok / "raw" / KAYNAK / TARIH
    assert (ham / "quran-data.xml").read_bytes() == xml
    kayit = json.loads((ham / "fetch.json").read_bytes())
    assert (kayit["sha256"], kayit["boyut"], kayit["url"]) == (kilit.sha256, kilit.boyut, URL)
    manifest = lineage.manifest_oku(sonuc.klasor)
    assert manifest is not None
    assert [c["yol"].rsplit("/", 1)[-1] for c in manifest["ciktilar"]] == sorted(  # type: ignore[index]
        YAPI_DOSYALARI.values()
    )
    assert lineage.ciktilar_saglam(veri_kok, manifest)
    ayrintilar = manifest["ayrintilar"]
    assert isinstance(ayrintilar, dict)
    assert ayrintilar["sayilar"]["sayfa"] == GRUP_BOYUTLARI["pages"]
    assert ayrintilar["kilit"] == {"boyut": kilit.boyut, "sha256": kilit.sha256}
    # staged dosyalari ASCII kacisli, LF'li, satir basina bir nesne
    for ad in YAPI_DOSYALARI.values():
        veri = (sonuc.klasor / ad).read_bytes()
        assert veri.isascii() and veri.endswith(b"\n") and b"\r" not in veri
    assert sonuc.satir_sayisi == sum(
        len((sonuc.klasor / ad).read_bytes().splitlines()) for ad in YAPI_DOSYALARI.values()
    )


def test_ingest_ayni_baytlar_raw_altinda_yeni_kopya_acmaz_ve_atlanir(tmp_path: Path) -> None:
    kok, veri_kok, xml = _ingest_kur(tmp_path)
    kilit = kilit_xml_icin(xml)
    run_ust_veri(_ingest_ctx(tmp_path, kok, temiz_git=True), None, kilit)
    raw_once = sorted((veri_kok / "raw" / KAYNAK).iterdir())
    ikinci = run_ust_veri(_ingest_ctx(tmp_path, kok, temiz_git=True), None, kilit)
    assert ikinci.atlandi is True and ikinci.klasor is None
    zorla = run_ust_veri(_ingest_ctx(tmp_path, kok, temiz_git=True, force=True), None, kilit)
    assert zorla.atlandi is False
    assert sorted((veri_kok / "raw" / KAYNAK).iterdir()) == raw_once


def test_ingest_dry_run_hicbir_sey_yazmaz(tmp_path: Path) -> None:
    kok, veri_kok, xml = _ingest_kur(tmp_path)
    sonuc = run_ust_veri(_ingest_ctx(tmp_path, kok, dry_run=True), None, kilit_xml_icin(xml))
    assert sonuc.klasor is None and sonuc.satir_sayisi > 0
    assert not (veri_kok / "raw").exists()
    assert not (veri_kok / "staged").exists()


def test_ingest_kilit_tutmazsa_raw_a_yazmaz(tmp_path: Path) -> None:
    kok, veri_kok, xml = _ingest_kur(tmp_path)
    yanlis = kilit_xml_icin(xml + b" ")
    with pytest.raises(GirdiHatasi, match="ozeti kilitle tutmuyor"):
        run_ust_veri(_ingest_ctx(tmp_path, kok), None, yanlis)
    assert not (veri_kok / "raw").exists()


def test_ingest_ayni_tarihte_farkli_bayt_raw_degismez_hatasi(tmp_path: Path) -> None:
    kok, veri_kok, xml = _ingest_kur(tmp_path)
    run_ust_veri(_ingest_ctx(tmp_path, kok), None, kilit_xml_icin(xml))
    yeni = sentetik_xml(surum="1.1")
    (veri_kok / "gelen" / "tanzil-ust-veri" / TARIH / "quran-data.xml").write_bytes(yeni)
    with pytest.raises(GirdiHatasi, match="data/raw degismez"):
        run_ust_veri(_ingest_ctx(tmp_path, kok), None, kilit_xml_icin(yeni, surum="1.1"))


def test_ingest_gelen_dosyasi_yoksa_ve_tarih_gecersizse(tmp_path: Path) -> None:
    kok = kok_kur(tmp_path)
    kayitlari_yaz(kok)
    with pytest.raises(GirdiHatasi, match="tarih klasoru yok"):
        run_ust_veri(_ingest_ctx(tmp_path, kok), None, kilit_xml_icin(b"x"))
    with pytest.raises(GirdiHatasi, match="YYYY-AA-GG"):
        run_ust_veri(_ingest_ctx(tmp_path, kok), "2026-13-45", kilit_xml_icin(b"x"))
    (tmp_path / "data" / "gelen" / "tanzil-ust-veri" / TARIH).mkdir(parents=True)
    with pytest.raises(GirdiHatasi, match="yok"):
        run_ust_veri(_ingest_ctx(tmp_path, kok), None, kilit_xml_icin(b"x"))


def test_ingest_kayitsiz_kaynak_cikis_2_hatasi(tmp_path: Path) -> None:
    kok = kok_kur(tmp_path)  # kayit yok
    with pytest.raises(GirdiHatasi, match="kayitsiz"):
        run_ust_veri(_ingest_ctx(tmp_path, kok), None, kilit_xml_icin(b"x"))


def test_metin_varyantlarinin_gelen_koku_degismedi() -> None:
    assert tanzil_ust_veri.gelen_dizini(Path("v")).as_posix() == "v/gelen/tanzil-ust-veri"
    assert tanzil.gelen_kok(Path("v")).as_posix() == "v/gelen/tanzil"


# --- isaret ve sayfa satirlari -------------------------------------------------------------------


def _yapi_ve_ayetler() -> tuple[dict[str, list[dict[str, object]]], Any]:
    yapi = yapi_ayristir(sentetik_xml(), "1.0")
    return yapi, ayet_bilgisi(sentetik_kelimeler())


def test_isaret_satirlari_sayilar_ve_hizb_dorduncu_ceyrek() -> None:
    yapi, ayetler = _yapi_ve_ayetler()
    satirlar = isaret_satirlari(yapi, ayetler, "1.0")
    turler = [s["kind"] for s in satirlar]
    assert turler.count("cuz") == len(yapi["cuz"])
    assert turler.count("rub") == len(yapi["rub"])
    assert turler.count("hizb") == len(yapi["rub"]) // 4
    assert turler.count("secde") == len(yapi["secde"])
    ceyrek = {s["no"]: s for s in yapi["rub"]}
    for s in satirlar:
        if s["kind"] == "hizb":
            kaynak = ceyrek[4 * (int(str(s["no"])) - 1) + 1]
            assert s["anchor"] == f"q:{kaynak['sura']}:{kaynak['aya']}"
        if s["kind"] == "rub":
            kaynak = ceyrek[s["no"]]
            assert s["anchor"] == f"q:{kaynak['sura']}:{kaynak['aya']}"
    for s in satirlar:
        assert (s["kind"] == "secde") == (s["secde_turu"] is not None)
        assert (s["source_id"], s["data_version"]) == (KAYNAK, "tanzil-ust-veri@1.0")
    secde = [s for s in satirlar if s["kind"] == "secde"]
    assert [s["secde_turu"] for s in secde] == [s["type"] for s in yapi["secde"]]


def test_isaret_ceyrek_sayisi_dortun_kati_degilse_hata() -> None:
    yapi, ayetler = _yapi_ve_ayetler()
    yapi["rub"] = yapi["rub"][:-1]
    with pytest.raises(GirdiHatasi, match="kati degil"):
        isaret_satirlari(yapi, ayetler, "1.0")


def test_isaret_baslangic_ayeti_kelime_dosyasinda_yoksa_hata() -> None:
    yapi, ayetler = _yapi_ve_ayetler()
    yapi["cuz"] = [{**s} for s in yapi["cuz"]]
    yapi["cuz"][0]["aya"] = 999
    with pytest.raises(GirdiHatasi, match="kelime dosyasinda yok"):
        isaret_satirlari(yapi, ayetler, "1.0")


def test_sayfa_satirlari_baslangic_ilk_kelime_bitis_onceki_ayetin_son_kelimesi() -> None:
    yapi, ayetler = _yapi_ve_ayetler()
    satirlar = sayfa_satirlari(yapi, ayetler, "1.0")
    assert [s["page"] for s in satirlar] == list(range(1, len(yapi["sayfa"]) + 1))
    for i, s in enumerate(satirlar):
        sure, ayet = yapi["sayfa"][i]["sura"], yapi["sayfa"][i]["aya"]
        assert s["start_anchor"] == f"q:{sure}:{ayet}:1"
        if i + 1 < len(satirlar):
            sira = ayetler.sira[(yapi["sayfa"][i + 1]["sura"], yapi["sayfa"][i + 1]["aya"])] - 1
            son = ayetler.konum[sira]
            assert s["end_anchor"] == f"q:{son[0]}:{son[1]}:{ayetler.kelime_sayisi[son]}"
    son_ayet = ayetler.konum[max(ayetler.konum)]
    assert satirlar[-1]["end_anchor"] == (
        f"q:{son_ayet[0]}:{son_ayet[1]}:{ayetler.kelime_sayisi[son_ayet]}"
    )


def test_sayfa_satirlari_kelime_sayisi_degisince_bitis_kelimesi_degisir() -> None:
    """Birlestirme listesinin etkisi dahil: bitis kelimesi kelime dosyasindan gelir."""
    yapi = yapi_ayristir(sentetik_xml(), "1.0")
    az = sayfa_satirlari(yapi, ayet_bilgisi(sentetik_kelimeler(lambda s, a: 2)), "1.0")
    cok = sayfa_satirlari(yapi, ayet_bilgisi(sentetik_kelimeler(lambda s, a: 7)), "1.0")
    assert all(a["end_anchor"].endswith(":2") for a in az)
    assert all(c["end_anchor"].endswith(":7") for c in cok)


def test_sayfa_baslangic_ayeti_kelime_dosyasinda_yoksa_hata() -> None:
    yapi, ayetler = _yapi_ve_ayetler()
    yapi["sayfa"] = copy.deepcopy(yapi["sayfa"])
    yapi["sayfa"][3]["aya"] = 999
    with pytest.raises(GirdiHatasi, match="kelime dosyasinda yok"):
        sayfa_satirlari(yapi, ayetler, "1.0")


def test_ayet_bilgisi_tutarsiz_kelime_dosyasi_hata() -> None:
    satirlar = sentetik_kelimeler()
    satirlar[1] = {**satirlar[1], "ayah_index": 99}
    with pytest.raises(GirdiHatasi, match="tutarsiz"):
        ayet_bilgisi(satirlar)
    with pytest.raises(GirdiHatasi, match="bos"):
        ayet_bilgisi([])


# --- anchor/sayfa.py -----------------------------------------------------------------------------


def _tablo() -> SayfaTablosu:
    yapi, ayetler = _yapi_ve_ayetler()
    satirlar = sayfa_satirlari(yapi, ayetler, "1.0")
    return SayfaTablosu.kur((s["page"], s["start_anchor"], s["end_anchor"]) for s in satirlar)  # type: ignore[misc]


def test_sayfa_araligi_ve_sayfa_bul_gidis_donus() -> None:
    tablo = _tablo()
    assert len(tablo) == GRUP_BOYUTLARI["pages"]
    for sayfa in (1, 2, 300, len(tablo)):
        ilk, son = sayfa_araligi(tablo, sayfa)
        assert sayfa_bul(tablo, ilk) == sayfa
        assert sayfa_bul(tablo, son) == sayfa
    ilk, _ = sayfa_araligi(tablo, 1)
    assert ilk == "q:1:1:1"


def test_ayet_capasi_ayetin_ilk_kelimesinin_sayfasini_verir() -> None:
    tablo = _tablo()
    ilk, _ = sayfa_araligi(tablo, 7)
    sure, ayet, _k = (int(x) for x in ilk.split(":")[1:])
    assert sayfa_bul(tablo, f"q:{sure}:{ayet}") == 7


@pytest.mark.parametrize("sayfa", [0, -1, 605, 10**6])
def test_sayfa_araligi_gecersiz_sayfa_hata(sayfa: int) -> None:
    with pytest.raises(SayfaHatasi):
        sayfa_araligi(_tablo(), sayfa)


def test_sayfa_araligi_tablo_uzunlugu_sinirdir() -> None:
    tablo = _tablo()
    assert sayfa_araligi(tablo, len(tablo))
    with pytest.raises(SayfaHatasi):
        sayfa_araligi(tablo, len(tablo) + 1)
    with pytest.raises(SayfaHatasi):
        sayfa_araligi(tablo, True)  # bool sayfa numarasi degildir


@pytest.mark.parametrize(
    "capa",
    ["q:2:255:3-7", "q:2:255-257", "q:2:255@0-5", "meal:elmalili:2:255", "q:115:1", "x", ""],
)
def test_sayfa_bul_gecersiz_capa_hata(capa: str) -> None:
    with pytest.raises(SayfaHatasi):
        sayfa_bul(_tablo(), capa)


def test_sayfa_bul_tabloda_olmayan_kelime_hata() -> None:
    tablo = SayfaTablosu.kur([(1, "q:1:1:1", "q:1:7:5"), (2, "q:2:1:1", "q:2:3:2")])
    assert sayfa_bul(tablo, "q:1:7:5") == 1
    with pytest.raises(SayfaHatasi):
        sayfa_bul(tablo, "q:1:7:6")  # sayfa 1'in bitisinden sonra, sayfa 2'den once
    with pytest.raises(SayfaHatasi):
        sayfa_bul(tablo, "q:2:3:3")
    with pytest.raises(SayfaHatasi):
        sayfa_bul(tablo, "q:114:6")


@pytest.mark.parametrize(
    "satirlar",
    [
        [],
        [(2, "q:1:1:1", "q:1:7:5")],  # numara 1'den baslamiyor
        [(1, "q:1:1:1", "q:1:7:5"), (3, "q:2:1:1", "q:2:3:2")],  # kesintili
        [(1, "q:1:1:1", "q:1:7:5"), (2, "q:1:7:5", "q:2:3:2")],  # ortusuyor
        [(1, "q:1:1:1", "q:1:7:5"), (2, "q:1:3:1", "q:2:3:2")],  # sirasiz
        [(1, "q:1:7:5", "q:1:1:1")],  # bitis baslangictan once
        [(1, "q:1:1", "q:1:7:5")],  # baslangic kelime capasi degil
        [(1, "q:1:1:1-3", "q:1:7:5")],
        [(1, "q:1:1:01", "q:1:7:5")],  # kanonik degil
    ],
)
def test_sayfa_tablosu_gecersiz_satirlar_hata(satirlar: list[tuple[int, str, str]]) -> None:
    with pytest.raises(SayfaHatasi):
        SayfaTablosu.kur(satirlar)


def test_sayfa_tablosu_sirasiz_girdiyi_siralar() -> None:
    tablo = SayfaTablosu.kur([(2, "q:2:1:1", "q:2:3:2"), (1, "q:1:1:1", "q:1:7:5")])
    assert sayfa_araligi(tablo, 1) == ("q:1:1:1", "q:1:7:5")


def test_konum_yardimcisi_tablo_sinirlarinda_dogru() -> None:
    assert konum(1) == (1, 1)
    assert konum(AYET_SAYILARI[0]) == (1, AYET_SAYILARI[0])
    assert konum(AYET_SAYILARI[0] + 1) == (2, 1)
    assert konum(sum(AYET_SAYILARI)) == (len(AYET_SAYILARI), AYET_SAYILARI[-1])
