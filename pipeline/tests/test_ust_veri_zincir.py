"""Ust veri zinciri: ingest -> anchor -> qa (A11; SENTETIK, veritabani yok).

Tam sentetik Uthmani zinciri (`tam_sablon`, 6.236 ayet) uzerine sentetik `quran-data.xml`
eklenir; adimlar gercek komut islevleriyle kosulur. Kapi testleri bellekteki `UstVeriGirdisi`
uzerinde tek bir kusur uretir. Hicbir deger hafizadan yazilmaz.
"""

import dataclasses
import hashlib
import io
import json
import tarfile
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner
from ust_veri_yardimci import (
    TARIH,
    UstVeriZinciri,
    ust_veri_hazirla,
)
from zincir_yardimci import ortam_kur

from mutalaa_pipeline import cli, lineage
from mutalaa_pipeline.adimlar.anchor_ust_veri import run_anchor_ust_veri
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.ingest.tanzil_ust_veri import KAYNAK, YAPI_DOSYALARI
from mutalaa_pipeline.lineage import ISARETLER_ADI, SAYFALAR_ADI
from mutalaa_pipeline.qa import YAPI_KAPILARI
from mutalaa_pipeline.qa.checks.tanzil import KapiSonucu
from mutalaa_pipeline.qa.checks.ust_veri import (
    KAPI_ISLEVLERI,
    UstVeriGirdisi,
    g_but,
    g_cap,
    g_kay,
    olcumler,
)
from mutalaa_pipeline.qa.dogrulama import Qpc1, QuranMeta, qpc1_oku, quran_meta_oku
from mutalaa_pipeline.qa.run_ust_veri import kapilari_sec, yukle
from mutalaa_pipeline.staged import Satir
from mutalaa_pipeline.zincir import calismalar, ust_calismalar

runner = CliRunner()


@pytest.fixture
def uz(ust_veri_zinciri: UstVeriZinciri, monkeypatch: pytest.MonkeyPatch) -> UstVeriZinciri:
    ortam_kur(ust_veri_zinciri.z, monkeypatch)
    return ust_veri_zinciri


@pytest.fixture(scope="module")
def girdi_modul(ust_veri_zinciri: UstVeriZinciri) -> Iterator[UstVeriGirdisi]:
    with pytest.MonkeyPatch.context() as mp:
        ortam_kur(ust_veri_zinciri.z, mp)
        ctx = ust_veri_zinciri.ctx("qa", [KAYNAK])
        kayitlar = ctx.require_sources((KAYNAK, "medine-604-duzen", "quran-meta"))
        girdi, _, _ = yukle(ctx, kayitlar, run=None)
        yield girdi


@pytest.fixture
def girdi(girdi_modul: UstVeriGirdisi, uz: UstVeriZinciri) -> UstVeriGirdisi:
    return girdi_modul


def son(uz: UstVeriZinciri, kaynak: str, adim: str) -> Any:
    return calismalar(uz.ctx(adim, [kaynak]), kaynak, adim)[-1]


# --- adimlar --------------------------------------------------


def test_anchor_manifesti_iki_cikti_ve_yedi_yapi_dosyasi_ile_kelime_dosyasi_girdisi(
    uz: UstVeriZinciri,
) -> None:
    anchor = son(uz, KAYNAK, "anchor")
    ciktilar = [c["yol"].rsplit("/", 1)[-1] for c in anchor.manifest["ciktilar"]]
    assert ciktilar == [ISARETLER_ADI, SAYFALAR_ADI]
    girdiler = [yol.rsplit("/", 1)[-1] for yol, _ in lineage_girdiler(anchor)]
    assert sorted(girdiler) == sorted([*YAPI_DOSYALARI.values(), "words.jsonl"])
    ustler = ust_calismalar(uz.ctx("qa", [KAYNAK]), anchor)
    assert {(u.adim, u.source_id) for u in ustler} == {
        ("ingest", KAYNAK),
        ("anchor", "tanzil-uthmani"),
    }
    assert lineage.ciktilar_saglam(uz.z.veri_kok, anchor.manifest)


def lineage_girdiler(calisma: Any) -> list[tuple[str, str | None]]:
    from mutalaa_pipeline.zincir import girdiler

    return girdiler(calisma.manifest)


def test_ikinci_anchor_ayni_girdiyle_atlanir_yeni_ust_calismada_atlanmaz(
    tam_sablon: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    uz = ust_veri_hazirla(tam_sablon, tmp_path / "t", monkeypatch)
    assert uz.ingest() == 0
    ilk = run_anchor_ust_veri(uz.ctx("anchor", [KAYNAK], temiz_git=True))
    assert ilk.atlandi is False
    ikinci = run_anchor_ust_veri(uz.ctx("anchor", [KAYNAK], temiz_git=True))
    assert (ikinci.atlandi, ikinci.onceki_run_id) == (True, ilk.run_id)
    assert (
        run_anchor_ust_veri(uz.ctx("anchor", [KAYNAK], temiz_git=True, force=True)).atlandi is False
    )
    assert uz.ingest(force=True) == 0  # ust calisma degisti: ayni ciktiyla yeni ingest
    assert run_anchor_ust_veri(uz.ctx("anchor", [KAYNAK], temiz_git=True)).atlandi is False


def test_anchor_dry_run_hicbir_sey_yazmaz(
    tam_sablon: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    uz = ust_veri_hazirla(tam_sablon, tmp_path / "t", monkeypatch)
    assert uz.ingest() == 0
    once = sorted((uz.z.veri_kok / "staged" / KAYNAK).iterdir())
    sonuc = run_anchor_ust_veri(uz.ctx("anchor", [KAYNAK], dry_run=True))
    assert (sonuc.klasor, sonuc.isaret_sayisi > 0, sonuc.sayfa_sayisi > 0) == (None, True, True)
    assert sorted((uz.z.veri_kok / "staged" / KAYNAK).iterdir()) == once


def test_anchor_ingest_yoksa_ipucuyla_hata(
    tam_sablon: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    uz = ust_veri_hazirla(tam_sablon, tmp_path / "t", monkeypatch)
    with pytest.raises(GirdiHatasi, match="ingest tanzil --variant ust-veri"):
        run_anchor_ust_veri(uz.ctx("anchor", [KAYNAK]))


# --- QA raporu --------------------------------------------------


def son_qa_raporu(uz: UstVeriZinciri) -> dict[str, Any]:
    raporlar = [
        json.loads(p.read_bytes()) for p in sorted((uz.z.veri_kok / "reports").glob("*.json"))
    ]
    return [r for r in raporlar if r["komut"] == "qa run" and r.get("kaynak") == KAYNAK][-1]


def test_qa_raporu_uc_kapi_g_nor_yok_ve_ozetler(uz: UstVeriZinciri) -> None:
    rapor = son_qa_raporu(uz)
    assert rapor["cikis_kodu"] == 0
    assert rapor["kapilar"] == dict.fromkeys(YAPI_KAPILARI, "gecti")
    assert "G-NOR" not in rapor["kapilar"]
    anchor = son(uz, KAYNAK, "anchor")
    assert rapor["anchor_run_id"] == anchor.run_id
    assert rapor["units_sha256"] == anchor.cikti_ozeti(ISARETLER_ADI)
    assert rapor["sayfalar_sha256"] == anchor.cikti_ozeti(SAYFALAR_ADI)


def test_qa_olcumleri_dogrulama_girdisi_yoksa_atlandi(uz: UstVeriZinciri) -> None:
    olcum = son_qa_raporu(uz)["olcumler"]
    assert olcum["qpc1"] == {"durum": "atlandi"}
    assert olcum["quran_meta"] == {"durum": "atlandi"}
    assert olcum["ayet_sayisi"]["uc_yonlu_ayni"] is True
    assert olcum["kelime_toplami"] > olcum["ayet_sayisi"]["birim_ayet"]
    assert olcum["isaret_sayilari"]["hizb"] * 4 == olcum["isaret_sayilari"]["rub"]
    assert sum(olcum["secde_etiketleri"].values()) == olcum["isaret_sayilari"]["secde"]
    assert olcum["dosya_ozetleri"]["quran_data_xml_sha256"] == uz.kilit.sha256
    assert any("atlandi" in u for u in son_qa_raporu(uz)["uyarilar"])


def test_kapilari_sec_g_nor_bu_kaynakta_yok() -> None:
    assert kapilari_sec(None) == YAPI_KAPILARI
    assert kapilari_sec(["G-CAP", "G-KAY"]) == ("G-KAY", "G-CAP")
    with pytest.raises(GirdiHatasi):
        kapilari_sec(["G-NOR"])


def test_cli_qa_g_nor_cikis_2(uz: UstVeriZinciri) -> None:
    sonuc = runner.invoke(
        cli.app, ["qa", "run", "--source", KAYNAK, "--gate", "G-NOR", "--kok", str(uz.z.kok)]
    )
    assert sonuc.exit_code == 2


def test_cli_anchor_ve_ingest_ust_veri_komutlari(uz: UstVeriZinciri) -> None:
    kok = ["--kok", str(uz.z.kok)]
    ingest = runner.invoke(
        cli.app, ["ingest", "tanzil", "--variant", "ust-veri", "--dry-run", *kok]
    )
    assert ingest.exit_code == 0, ingest.stderr
    assert "dry-run" in ingest.stdout
    anchor = runner.invoke(cli.app, ["anchor", "--source", KAYNAK, "--dry-run", *kok])
    assert anchor.exit_code == 0, anchor.stderr
    assert "isaret" in anchor.stdout and "sayfa" in anchor.stdout
    oner = runner.invoke(
        cli.app, ["ingest", "tanzil", "--variant", "ust-veri", "--kilit-oner", *kok]
    )
    assert oner.exit_code == 0, oner.stderr
    assert json.loads(oner.stdout)["ust_veri"]["sha256"] == uz.kilit.sha256
    limit = runner.invoke(cli.app, ["anchor", "--source", KAYNAK, "--limit", "5", *kok])
    assert limit.exit_code == 2


# --- kapilar: gecen temel girdi --------------------------------------------------


def kalan(g: UstVeriGirdisi) -> dict[str, KapiSonucu]:
    return {ad: islev(g) for ad, islev in KAPI_ISLEVLERI.items()}


def bulgu_var(sonuc: KapiSonucu, parca: str) -> bool:
    return any(parca in b for b in sonuc.bulgular)


def test_temel_girdi_uc_kapidan_gecer(girdi: UstVeriGirdisi) -> None:
    sonuclar = kalan(girdi)
    assert tuple(sonuclar) == YAPI_KAPILARI
    assert all(s.gecti for s in sonuclar.values()), {k: s.bulgular for k, s in sonuclar.items()}
    assert sonuclar["G-BUT"].sayilar["sayfa"] == len(girdi.yapi["sayfa"])
    assert sonuclar["G-CAP"].sayilar["sayfada_olmayan"] == 0


def satirlari_degistir(
    satirlar: list[Satir], secici: Callable[[dict[str, object]], bool], **alanlar: object
) -> list[Satir]:
    return [Satir(s.etiket, s.no, {**s.veri, **alanlar}) if secici(s.veri) else s for s in satirlar]


def isaret(g: UstVeriGirdisi, **kosul: object) -> Callable[[dict[str, object]], bool]:
    return lambda v: all(v.get(a) == d for a, d in kosul.items())


def test_g_but_isaret_satiri_eksikse_kalir(girdi: UstVeriGirdisi) -> None:
    kalanlar = [
        s for s in girdi.isaret_satirlari if not (s.veri["kind"] == "cuz" and s.veri["no"] == 5)
    ]
    g = dataclasses.replace(girdi, isaret_satirlari=kalanlar)
    sonuc = g_but(g)
    assert bulgu_var(sonuc, "cuz:")
    assert bulgu_var(sonuc, "kesintisiz")


def test_g_but_isaret_baslangiclari_okuma_sirasinda_artmali(girdi: UstVeriGirdisi) -> None:
    ilk = next(s for s in girdi.isaret_satirlari if s.veri["kind"] == "cuz" and s.veri["no"] == 2)
    sonraki = next(
        s for s in girdi.isaret_satirlari if s.veri["kind"] == "cuz" and s.veri["no"] == 3
    )
    satirlar = satirlari_degistir(
        list(girdi.isaret_satirlari), isaret(girdi, kind="cuz", no=3), anchor=ilk.veri["anchor"]
    )
    assert sonraki.veri["anchor"] != ilk.veri["anchor"]
    sonuc = g_but(dataclasses.replace(girdi, isaret_satirlari=satirlar))
    assert bulgu_var(sonuc, "cuz: baslangiclar okuma sirasinda artmiyor")


def test_g_but_ilk_cuz_kitabin_ilk_ayeti_olmali(girdi: UstVeriGirdisi) -> None:
    satirlar = satirlari_degistir(
        list(girdi.isaret_satirlari), isaret(girdi, kind="cuz", no=1), anchor="q:1:2"
    )
    sonuc = g_but(dataclasses.replace(girdi, isaret_satirlari=satirlar))
    assert bulgu_var(sonuc, "ilk cuz kitabin ilk ayetiyle baslamiyor")


def test_g_but_secde_turu_yalniz_secdede_ve_tanzil_etiketiyle(girdi: UstVeriGirdisi) -> None:
    cuzde = satirlari_degistir(
        list(girdi.isaret_satirlari), isaret(girdi, kind="cuz", no=1), secde_turu="recommended"
    )
    assert bulgu_var(g_but(dataclasses.replace(girdi, isaret_satirlari=cuzde)), "secde_turu")
    degisik = satirlari_degistir(
        list(girdi.isaret_satirlari), isaret(girdi, kind="secde", no=1), secde_turu="wajib"
    )
    assert bulgu_var(g_but(dataclasses.replace(girdi, isaret_satirlari=degisik)), "secde_turu")
    eksik = satirlari_degistir(
        list(girdi.isaret_satirlari), isaret(girdi, kind="secde", no=1), secde_turu=None
    )
    assert bulgu_var(g_but(dataclasses.replace(girdi, isaret_satirlari=eksik)), "secde_turu")


def test_g_but_hizb_ceyregin_dorduncusu_olmali(girdi: UstVeriGirdisi) -> None:
    """Hizb 2 ceyrek 5'tir; ceyrek 6'nin ayetine cekilirse yeniden uretilenden farkli olur."""
    ceyrek6 = next(
        s.veri["anchor"]
        for s in girdi.isaret_satirlari
        if s.veri["kind"] == "rub" and s.veri["no"] == 6
    )
    satirlar = satirlari_degistir(
        list(girdi.isaret_satirlari), isaret(girdi, kind="hizb", no=2), anchor=ceyrek6
    )
    sonuc = g_but(dataclasses.replace(girdi, isaret_satirlari=satirlar))
    assert bulgu_var(sonuc, "markers.jsonl kaynak dosyadan yeniden uretilenle ayni degil")


def test_g_but_sayfa_kesintisi_ve_ortusme(girdi: UstVeriGirdisi) -> None:
    sayfalar = list(girdi.sayfa_satirlari)
    bosluklu = satirlari_degistir(
        sayfalar, lambda v: v["page"] == 10, start_anchor=_bir_sonraki_kelime(sayfalar[9], girdi)
    )
    sonuc = g_but(dataclasses.replace(girdi, sayfa_satirlari=bosluklu))
    assert bulgu_var(sonuc, "sayfa kesintisi")
    assert bulgu_var(sonuc, "ayet sinirinda degil")
    ortusen = satirlari_degistir(
        sayfalar, lambda v: v["page"] == 10, start_anchor=sayfalar[8].veri["end_anchor"]
    )
    assert bulgu_var(g_but(dataclasses.replace(girdi, sayfa_satirlari=ortusen)), "sayfa kesintisi")


def _bir_sonraki_kelime(satir: Satir, g: UstVeriGirdisi) -> str:
    sure, ayet, kelime = (int(x) for x in str(satir.veri["start_anchor"]).split(":")[1:])
    return f"q:{sure}:{ayet}:{kelime + 1}"


def test_g_but_ilk_ve_son_sayfa_kitabin_uclariyla_ortusmeli(girdi: UstVeriGirdisi) -> None:
    sayfalar = list(girdi.sayfa_satirlari)
    ilk = satirlari_degistir(sayfalar, lambda v: v["page"] == 1, start_anchor="q:1:1:2")
    assert bulgu_var(
        g_but(dataclasses.replace(girdi, sayfa_satirlari=ilk)),
        "ilk sayfa kitabin ilk kelimesiyle baslamiyor",
    )
    son_sayfa = len(sayfalar)
    kisa = satirlari_degistir(sayfalar, lambda v: v["page"] == son_sayfa, end_anchor="q:114:5:1")
    assert bulgu_var(
        g_but(dataclasses.replace(girdi, sayfa_satirlari=kisa)),
        "son sayfa kitabin son kelimesiyle bitmiyor",
    )


def test_g_but_sayfa_numaralari_kesintisiz_ve_kaynak_sayisiyla_ayni(girdi: UstVeriGirdisi) -> None:
    eksik = [s for s in girdi.sayfa_satirlari if s.veri["page"] != 7]
    sonuc = g_but(dataclasses.replace(girdi, sayfa_satirlari=eksik))
    assert bulgu_var(sonuc, "sayfa: numaralar 1'den kesintisiz degil")
    assert bulgu_var(sonuc, "sayfa:")


def test_g_but_ust_veri_ayet_sayisi_birimlerle_ayni_olmali(girdi: UstVeriGirdisi) -> None:
    eksik_birim = list(girdi.birim_satirlari)[:-1]
    sonuc = g_but(dataclasses.replace(girdi, birim_satirlari=eksik_birim))
    assert bulgu_var(sonuc, "ayet sayisi")
    yapi = {**girdi.yapi, "sure": [{**s} for s in girdi.yapi["sure"]]}
    yapi["sure"][0]["ayas"] = 8
    assert bulgu_var(g_but(dataclasses.replace(girdi, yapi=yapi)), "ayet sayisi")


def test_g_but_ingest_ciktisi_ham_xml_den_farkliysa_kalir(girdi: UstVeriGirdisi) -> None:
    ingest = {**girdi.ingest_yapi, "cuz": [{**s} for s in girdi.ingest_yapi["cuz"]]}
    ingest["cuz"][3]["aya"] = 1
    sonuc = g_but(dataclasses.replace(girdi, ingest_yapi=ingest))
    assert bulgu_var(sonuc, "ingest ciktisi ham XML")


def test_g_but_sayfa_satiri_yeniden_uretilenden_farkliysa_kalir(girdi: UstVeriGirdisi) -> None:
    sayfalar = satirlari_degistir(
        list(girdi.sayfa_satirlari), lambda v: v["page"] == 3, data_version="x@1"
    )
    sonuc = g_but(dataclasses.replace(girdi, sayfa_satirlari=sayfalar))
    assert bulgu_var(sonuc, "pages.jsonl")


@pytest.mark.parametrize("anchor", ["q:1:01", "q:2:3:4", "q:2:999", "meal:elmalili:2:3"])
def test_g_cap_isaret_capasi_kanonik_ayet_capasi_ve_kelime_dosyasinda_olmali(
    girdi: UstVeriGirdisi, anchor: str
) -> None:
    satirlar = satirlari_degistir(
        list(girdi.isaret_satirlari), isaret(girdi, kind="cuz", no=2), anchor=anchor
    )
    sonuc = g_cap(dataclasses.replace(girdi, isaret_satirlari=satirlar))
    assert not sonuc.gecti
    assert bulgu_var(sonuc, "isaret capasi")


def test_g_cap_yinelenen_isaret_ve_sayfa(girdi: UstVeriGirdisi) -> None:
    kopya = [*girdi.isaret_satirlari, girdi.isaret_satirlari[0]]
    assert bulgu_var(g_cap(dataclasses.replace(girdi, isaret_satirlari=kopya)), "yinelenen isaret")
    sayfa_kopya = [*girdi.sayfa_satirlari, girdi.sayfa_satirlari[0]]
    assert bulgu_var(
        g_cap(dataclasses.replace(girdi, sayfa_satirlari=sayfa_kopya)), "yinelenen sayfa"
    )


@pytest.mark.parametrize(
    ("alan", "deger"),
    [
        ("start_anchor", "q:2:255"),  # ayet capasi, kelime capasi degil
        ("end_anchor", "q:2:255:3-5"),  # kelime araligi
        ("start_anchor", "q:2:255:03"),  # kanonik degil
    ],
)
def test_g_cap_sayfa_capalari_kanonik_tekil_kelime_olmali(
    girdi: UstVeriGirdisi, alan: str, deger: str
) -> None:
    sayfalar = satirlari_degistir(
        list(girdi.sayfa_satirlari), lambda v: v["page"] == 4, **{alan: deger}
    )
    sonuc = g_cap(dataclasses.replace(girdi, sayfa_satirlari=sayfalar))
    assert bulgu_var(sonuc, "gecersiz sayfa capasi")


def test_g_cap_sayfa_kelimesi_kelime_dosyasinda_olmali(girdi: UstVeriGirdisi) -> None:
    sayfalar = satirlari_degistir(
        list(girdi.sayfa_satirlari), lambda v: v["page"] == 4, end_anchor="q:2:255:99"
    )
    assert bulgu_var(g_cap(dataclasses.replace(girdi, sayfa_satirlari=sayfalar)), "sayfa capasi")


def test_g_cap_sabit_alanlar(girdi: UstVeriGirdisi) -> None:
    isaretler = satirlari_degistir(
        list(girdi.isaret_satirlari), isaret(girdi, kind="rub", no=3), source_id="baska"
    )
    assert bulgu_var(
        g_cap(dataclasses.replace(girdi, isaret_satirlari=isaretler)), "isaret sabit alani"
    )
    sayfalar = satirlari_degistir(
        list(girdi.sayfa_satirlari), lambda v: v["page"] == 3, data_version="x@1"
    )
    assert bulgu_var(
        g_cap(dataclasses.replace(girdi, sayfa_satirlari=sayfalar)), "sayfa sabit alani"
    )


def test_g_cap_sayfa_tablosu_kurulamazsa_kalir(girdi: UstVeriGirdisi) -> None:
    sayfalar = satirlari_degistir(
        list(girdi.sayfa_satirlari), lambda v: v["page"] == 5, start_anchor="q:114:6:1"
    )
    sonuc = g_cap(dataclasses.replace(girdi, sayfa_satirlari=sayfalar))
    assert bulgu_var(sonuc, "sayfa tablosu kurulamadi")


def test_g_kay_kayit_ham_dosya_ve_json_tutarliligi(girdi: UstVeriGirdisi) -> None:
    assert g_kay(girdi).gecti
    kilit = dataclasses.replace(girdi.kilit, sha256="a" * 64)
    assert bulgu_var(g_kay(dataclasses.replace(girdi, kilit=kilit)), "ham XML kilitteki sha256")
    assert bulgu_var(g_kay(dataclasses.replace(girdi, kilit=kilit)), "ayet-sayilari.json sha256")
    surum = dataclasses.replace(girdi.kilit, surum="9.9")
    assert bulgu_var(g_kay(dataclasses.replace(girdi, kilit=surum)), "kok version")
    kayit = dataclasses.replace(girdi.kayit, atif_metni=" ")
    assert bulgu_var(g_kay(dataclasses.replace(girdi, kayit=kayit)), "atif_metni bos")
    diger = {k: dataclasses.replace(v, atif_metni="") for k, v in girdi.diger_kayitlar.items()}
    assert bulgu_var(g_kay(dataclasses.replace(girdi, diger_kayitlar=diger)), "atif_metni bos")
    adres = dataclasses.replace(girdi.kayit, kaynak_url="https://baska.invalid/")
    assert bulgu_var(g_kay(dataclasses.replace(girdi, kayit=adres)), "kaynak_url")


def test_kapi_bulgulari_icerik_tasimaz(girdi: UstVeriGirdisi) -> None:
    sayfalar = satirlari_degistir(
        list(girdi.sayfa_satirlari), lambda v: v["page"] == 3, start_anchor="GIZLI-DENEME"
    )
    g = dataclasses.replace(girdi, sayfa_satirlari=sayfalar)
    for islev in (g_but, g_cap):
        for bulgu in islev(g).bulgular:
            assert bulgu.isascii()


# --- dogrulama girdileri: QPC1 ve quran-meta (bellekte) ----------------------------


def qpc1_uygun(g: UstVeriGirdisi) -> Qpc1:
    ilk, son_ = {}, {}
    for s in g.sayfa_satirlari:
        ilk[s.sayi("page")] = s.metin("start_anchor").removeprefix("q:")
        son_[s.sayi("page")] = s.metin("end_anchor").removeprefix("q:")
    return Qpc1(TARIH, ilk, son_, "0" * 64)


def meta_uygun(g: UstVeriGirdisi) -> QuranMeta:
    sira = g.ayetler.sira
    listeler = {
        ad: tuple(sira[(int(str(s["sura"])), int(str(s["aya"])))] for s in g.yapi[tur])
        for ad, tur in (
            ("JuzList", "cuz"),
            ("HizbQuarterList", "rub"),
            ("ManzilList", "menzil"),
            ("RukuList", "ruku"),
            ("PageList", "sayfa"),
            ("SajdaList", "secde"),
        )
    }
    return QuranMeta(TARIH, "0" * 64, listeler, len(sira) + 1)


def test_dogrulama_girdileri_uygunsa_gecer_ve_olcum_yapildi(girdi: UstVeriGirdisi) -> None:
    g = dataclasses.replace(girdi, qpc1=qpc1_uygun(girdi), quran_meta=meta_uygun(girdi))
    assert g_but(g).gecti
    olcum = olcumler(g)
    sayfa = len(g.sayfa_satirlari)
    assert olcum["qpc1"]["durum"] == "yapildi"  # type: ignore[index]
    assert olcum["qpc1"]["baslangic_ayni"] == olcum["qpc1"]["bitis_ayni"] == sayfa  # type: ignore[index]
    assert olcum["qpc1"]["ayet_ortasinda_baslayan"] == 0  # type: ignore[index]
    assert olcum["quran_meta"]["farklar"] == dict.fromkeys(  # type: ignore[index]
        ("JuzList", "HizbQuarterList", "ManzilList", "RukuList", "PageList", "SajdaList"), 0
    )


def test_qpc1_sayfa_baslangici_farkliysa_kalir(girdi: UstVeriGirdisi) -> None:
    qpc1 = qpc1_uygun(girdi)
    qpc1.ilk[10] = "1:1:1"
    sonuc = g_but(dataclasses.replace(girdi, qpc1=qpc1))
    assert bulgu_var(sonuc, "sayfa baslangic ayeti Tanzil ve QPC1'de ayni degil: 1 sayfa")


def test_qpc1_ayet_ortasinda_baslayan_ve_biten_sayfa_sayilir(girdi: UstVeriGirdisi) -> None:
    qpc1 = qpc1_uygun(girdi)
    sure, ayet, _ = qpc1.ilk[20].split(":")
    qpc1.ilk[20] = f"{sure}:{ayet}:2"
    sure, ayet, kelime = qpc1.son[21].split(":")
    qpc1.son[21] = f"{sure}:{ayet}:{int(kelime) - 1}"
    g = dataclasses.replace(girdi, qpc1=qpc1)
    sonuc = g_but(g)
    assert bulgu_var(sonuc, "QPC1'de ayet ortasinda baslayan sayfa: 1 sayfa")
    assert bulgu_var(sonuc, "QPC1'de ayet ortasinda biten sayfa: 1 sayfa")
    assert olcumler(g)["qpc1"]["ayet_ortasinda_baslayan"] == 1  # type: ignore[index]


def test_qpc1_sayfa_kumesi_farkliysa_kalir(girdi: UstVeriGirdisi) -> None:
    qpc1 = qpc1_uygun(girdi)
    del qpc1.ilk[604]
    del qpc1.son[604]
    assert bulgu_var(g_but(dataclasses.replace(girdi, qpc1=qpc1)), "sayfa kumesi farkli")


@pytest.mark.parametrize("liste", ["JuzList", "HizbQuarterList", "PageList", "SajdaList"])
def test_quran_meta_farki_kalir(girdi: UstVeriGirdisi, liste: str) -> None:
    meta = meta_uygun(girdi)
    degerler = list(meta.listeler[liste])
    degerler[1] += 1
    meta = dataclasses.replace(meta, listeler={**meta.listeler, liste: tuple(degerler)})
    sonuc = g_but(dataclasses.replace(girdi, quran_meta=meta))
    assert bulgu_var(sonuc, f"quran-meta {liste} Tanzil ile 1 konumda farkli")


def test_quran_meta_uzunluk_ve_sentinel_farki_kalir(girdi: UstVeriGirdisi) -> None:
    meta = meta_uygun(girdi)
    kisa = dataclasses.replace(
        meta, listeler={**meta.listeler, "RukuList": meta.listeler["RukuList"][:-1]}
    )
    assert bulgu_var(g_but(dataclasses.replace(girdi, quran_meta=kisa)), "quran-meta RukuList")
    sentinel = dataclasses.replace(meta, sentinel=meta.sentinel + 1)
    assert bulgu_var(g_but(dataclasses.replace(girdi, quran_meta=sentinel)), "sentinel")


# --- dogrulama girdileri: dosya okuyuculari --------------------------------------------------


def _sha256sums(klasor: Path, dosyalar: list[Path]) -> None:
    satirlar = [
        f"{hashlib.sha256(d.read_bytes()).hexdigest()} *{d.relative_to(klasor).as_posix()}\n"
        for d in dosyalar
    ]
    (klasor / "SHA256SUMS").write_bytes("".join(satirlar).encode("utf-8"))


def _qpc1_yaz(veri_kok: Path, sayfalar: dict[int, list[dict[str, object]]]) -> Path:
    klasor = veri_kok / "gelen" / "medine-604-duzen" / TARIH
    hedef = klasor / "mushaf" / "QPC1"
    hedef.mkdir(parents=True)
    dosyalar = []
    for no, kelimeler in sayfalar.items():
        yol = hedef / f"page-{no:03d}.json"
        yol.write_bytes(
            json.dumps(
                {"page": no, "lines": [{"line": 1, "type": "text", "words": kelimeler}]}
            ).encode()
        )
        dosyalar.append(yol)
    _sha256sums(klasor, dosyalar)
    return klasor


def test_qpc1_oku_ilk_son_kelime_ve_ayet_sonu_girdisi_atlanir(tmp_path: Path) -> None:
    hint = "".join(chr(0x0661 + i) for i in range(3))  # yalniz rakam: ayet sonu isareti
    _qpc1_yaz(
        tmp_path,
        {
            1: [
                {"location": "1:1:1", "word": "Deneme1", "qpcV1": "a"},
                {"location": "1:1:2", "word": "Deneme2" + hint[:1], "qpcV1": "b"},
                {"location": "1:1:3", "word": hint, "qpcV1": "c"},
            ],
            2: [{"location": "1:2:1", "word": "Deneme3", "qpcV1": "d"}],
        },
    )
    qpc1 = qpc1_oku(tmp_path)
    assert qpc1 is not None
    assert (qpc1.ilk, qpc1.son) == ({1: "1:1:1", 2: "1:2:1"}, {1: "1:1:2", 2: "1:2:1"})
    assert qpc1.sayfa_sayisi == 2
    assert qpc1.tarih == TARIH


def test_qpc1_oku_dosya_yoksa_none_ozet_tutmazsa_hata(tmp_path: Path) -> None:
    assert qpc1_oku(tmp_path) is None
    klasor = _qpc1_yaz(tmp_path, {1: [{"location": "1:1:1", "word": "Deneme", "qpcV1": "a"}]})
    (klasor / "mushaf" / "QPC1" / "page-001.json").write_bytes(b"{}")
    with pytest.raises(GirdiHatasi, match="ozeti SHA256SUMS ile tutmuyor"):
        qpc1_oku(tmp_path)


@pytest.mark.parametrize(
    "sayfa",
    [
        {"lines": "x"},
        {"lines": [{"words": "x"}]},
        {"lines": [{"words": [{"location": "1:1:1", "word": 5}]}]},
        {"lines": [{"words": [{"location": "bozuk", "word": "Deneme"}]}]},
        {"lines": []},
    ],
)
def test_qpc1_oku_bozuk_yapi_hata(tmp_path: Path, sayfa: dict[str, object]) -> None:
    klasor = tmp_path / "gelen" / "medine-604-duzen" / TARIH
    hedef = klasor / "mushaf" / "QPC1"
    hedef.mkdir(parents=True)
    yol = hedef / "page-001.json"
    yol.write_bytes(json.dumps(sayfa).encode())
    _sha256sums(klasor, [yol])
    with pytest.raises(GirdiHatasi):
        qpc1_oku(tmp_path)


def _meta_js(listeler: dict[str, list[int]]) -> bytes:
    govde = ",\n".join(f"\t{ad}: [\n\t\t{','.join(map(str, v))}\n\t]" for ad, v in listeler.items())
    return f"const HafsLists = {{\n{govde}\n}};\nexport {{ HafsLists }};\n".encode()


def _meta_yaz(veri_kok: Path, js: bytes, uye: str = "package/dist/HafsLists-Abc123.js") -> Path:
    klasor = veri_kok / "gelen" / "quran-meta" / TARIH
    klasor.mkdir(parents=True)
    tgz = klasor / "quran-meta-7.0.0.tgz"
    with tarfile.open(tgz, "w:gz") as arsiv:
        bilgi = tarfile.TarInfo(uye)
        bilgi.size = len(js)
        arsiv.addfile(bilgi, io.BytesIO(js))
    _sha256sums(klasor, [tgz])
    return tgz


SENTETIK_LISTELER = {
    "HizbQuarterList": [0, 1, 40, 90, 6237],
    "JuzList": [0, 1, 500, 6237],
    "ManzilList": [0, 1, 6237],
    "PageList": [0, 1, 20, 6237],
    "RukuList": [0, 1, 8, 6237],
    "SajdaList": [50, 700],
}


def test_quran_meta_oku_dizileri_ayristirir_js_calistirilmaz(tmp_path: Path) -> None:
    _meta_yaz(tmp_path, _meta_js(SENTETIK_LISTELER))
    meta = quran_meta_oku(tmp_path)
    assert meta is not None
    assert meta.listeler["JuzList"] == (1, 500)
    assert meta.listeler["HizbQuarterList"] == (1, 40, 90)
    assert meta.listeler["SajdaList"] == (50, 700)
    assert meta.sentinel == 6237
    assert (
        meta.tgz_sha256
        == hashlib.sha256(
            (tmp_path / "gelen" / "quran-meta" / TARIH / "quran-meta-7.0.0.tgz").read_bytes()
        ).hexdigest()
    )


def test_quran_meta_oku_dosya_yoksa_none(tmp_path: Path) -> None:
    assert quran_meta_oku(tmp_path) is None


@pytest.mark.parametrize(
    "bozuk",
    [
        lambda: {k: v for k, v in SENTETIK_LISTELER.items() if k != "PageList"},
        lambda: {**SENTETIK_LISTELER, "JuzList": [3, 500, 6237]},  # baslangic 0 degil
        lambda: {**SENTETIK_LISTELER, "PageList": [0, 1, 20, 6238]},  # sentinel tutarsiz
    ],
)
def test_quran_meta_oku_bozuk_dizi_hata(
    tmp_path: Path, bozuk: Callable[[], dict[str, list[int]]]
) -> None:
    _meta_yaz(tmp_path, _meta_js(bozuk()))
    with pytest.raises(GirdiHatasi):
        quran_meta_oku(tmp_path)


def test_quran_meta_oku_hafs_uyesi_yoksa_hata(tmp_path: Path) -> None:
    _meta_yaz(tmp_path, _meta_js(SENTETIK_LISTELER), uye="package/dist/Baska.js")
    with pytest.raises(GirdiHatasi, match="HafsLists"):
        quran_meta_oku(tmp_path)
