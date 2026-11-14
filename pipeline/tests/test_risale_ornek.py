# ruff: noqa: RUF001
"""Sentetik Risale fiksturu `test-risale-ornek` (A20.5a; ACIKCA SENTETIK veri, veritabani yok).

Uretec, kayit, normalize, anchor, `page_map` ve `xref` ciktilari, dort QA kapisi ve `export pg`
hazirlik duzeyi (DB'siz) sinanir. Hicbir Risale metni yoktur: paragraflar "Deneme paragrafi N ..."
metinleridir; Arapca blok Arap alfabesinin harflerinden olusur. Zincir gercek depo kokunun gercek
kaynak kaydiyla ama `tmp_path` altindaki veri kokuyle kosar (gercek `data/` kullanilmaz).
"""

import copy
import json
import unicodedata
from dataclasses import replace
from pathlib import Path

import pytest
from hat_yardimci import TEMIZ_GIT, ansisiz, ayarlar_kur, ctx_kur
from test_pg_risale import SahteBaglanti, SahteSonuc, esle
from typer.testing import CliRunner

from mutalaa_pipeline import cli, lineage, sources
from mutalaa_pipeline.adimlar import risale as risale_adimlari
from mutalaa_pipeline.adimlar import risale_ornek as adimlar
from mutalaa_pipeline.anchor import format as anchor_format
from mutalaa_pipeline.anchor import parse, sort_key, to_unit_span
from mutalaa_pipeline.anchor.cumle import cumleleri_ayir
from mutalaa_pipeline.export import pg, pg_risale, pg_risale_sayfa
from mutalaa_pipeline.export.ortak import GirdiHatasi, depo_koku
from mutalaa_pipeline.ingest import risale_kaynaklari, risale_ornek
from mutalaa_pipeline.qa import KAPILAR, kaynak_kapilari
from mutalaa_pipeline.qa import run_risale_ornek as qa_ornek
from mutalaa_pipeline.qa.checks import risale_ornek as kapilar
from mutalaa_pipeline.sources.kayit import Kaynak
from mutalaa_pipeline.staged import Satir, satirlari_oku

KAYNAK = risale_ornek.KAYNAK
runner = CliRunner()
BIRIM_SAYISI = 13
SAYFA_SAYISI = 5


@pytest.fixture
def veri(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    kok = tmp_path / "data"
    monkeypatch.setenv("MUTALAA_VERI_KOK", str(kok))
    return kok


def ingest(*, dry_run: bool = False, force: bool = False) -> int:
    return risale_ornek.komut_ingest_ornek(
        gelen_tarih=None, dry_run=dry_run, force=force, config=None, kok=None
    )


def normalize(*, force: bool = False) -> int:
    return adimlar.komut_normalize(source=KAYNAK, dry_run=False, force=force, config=None, kok=None)


def anchor(*, force: bool = False, dry_run: bool = False) -> int:
    return adimlar.komut_anchor(source=KAYNAK, dry_run=dry_run, force=force, config=None, kok=None)


def qa(*gate: str) -> int:
    return qa_ornek.komut_qa_run_ornek(run=None, gate=list(gate) or None, config=None, kok=None)


def zincir() -> None:
    for ad, kod in (("ingest", ingest()), ("normalize", normalize()), ("anchor", anchor())):
        assert kod == 0, ad
    assert qa() == 0


def calismalar(veri: Path, adim: str) -> list[tuple[str, Path, dict[str, object]]]:
    return [c for c in lineage.calismalar(veri / "staged" / KAYNAK) if c[2].get("adim") == adim]


def satirlar(veri: Path, adim: str, ad: str = "units.jsonl") -> list[Satir]:
    klasor = calismalar(veri, adim)[-1][1]
    return satirlari_oku((klasor / ad).read_bytes(), f"{adim} {ad}")


def kayit() -> Kaynak:
    k = next(s.kaynak for s in sources.yukle(depo_koku()) if s.kaynak and s.kaynak.slug == KAYNAK)
    return k


# --- kayit ---------------------------------------------------------------------------------


def test_kaynak_kaydi_gecerli_ve_sentetik() -> None:
    k = kayit()
    assert k.tur.value == "risale"
    assert k.slug.startswith("test-")
    assert k.surum == "1"
    assert k.atif_metni.startswith("Sentetik")
    assert k.notlar is not None
    assert "sentetik fikstür, a20.5a" in k.notlar.lower()
    assert "public" in k.notlar and "dev" in k.notlar
    assert k.notice_text is None


def test_sources_check_sifir_hata_sifir_uyari() -> None:
    sonuc = runner.invoke(cli.app, ["sources", "check"])
    assert sonuc.exit_code == 0
    assert "0 hata, 0 uyari" in sonuc.output


def test_qa_kapilari_varsayilan_dort_kapi() -> None:
    assert kaynak_kapilari(KAYNAK) == KAPILAR == ("G-KAY", "G-BUT", "G-CAP", "G-NOR")


# --- uretec --------------------------------------------------------------------------------


def test_uretec_belirlenimci_ayni_bayt() -> None:
    assert risale_ornek.icerik_baytlari() == risale_ornek.icerik_baytlari()
    assert len(risale_ornek.birimler()) == BIRIM_SAYISI
    assert len(risale_ornek.sayfalar()) == SAYFA_SAYISI


def test_capalar_rn_test_ornek_ve_dizin_yok() -> None:
    capalar = [b.anchor for b in risale_ornek.birimler()]
    assert len(set(capalar)) == len(capalar)
    for capa in capalar:
        assert capa.startswith("rn:test-ornek:")
        assert anchor_format(parse(capa)) == capa
        yol = risale_adimlari.rn_yolu(capa)
        assert yol[0] == "test-ornek"
        assert "dizin" not in yol
    parcalar = {tuple(c.split(":")[2:-1]) for c in capalar}
    assert {
        ("bolum-1",),
        ("bolum-1", "hakikat-1"),
        ("bolum-1", "hasiye-1"),
        ("parca-1",),
    } <= parcalar
    assert "rn:test-ornek:bolum-1:hasiye-1:p1" in capalar


def test_metin_sentetik_ve_nfc() -> None:
    for t, b in zip(risale_ornek.TASLAKLAR, risale_ornek.birimler(), strict=True):
        assert unicodedata.is_normalized("NFC", b.text)
        assert b.text.startswith("Deneme ")
        assert b.text == risale_ornek.kanonik_metin(t.ham)
    ayrisan = [t for t in risale_ornek.TASLAKLAR if t.ham != risale_ornek.kanonik_metin(t.ham)]
    assert len(ayrisan) == 1  # NFD "I + U+0307" ilk kayitta "İ" olur
    assert "̇" in ayrisan[0].ham and "̇" not in risale_ornek.kanonik_metin(ayrisan[0].ham)
    assert "İlk" in risale_ornek.kanonik_metin(ayrisan[0].ham)


def test_isaretler_ar_blok_ve_hasiye() -> None:
    harita = {b.anchor: b for b in risale_ornek.birimler()}
    arapca = harita[risale_ornek.ARAPCA_CAPASI]
    (ar,) = arapca.marks
    assert ar["t"] == "ar"
    assert arapca.text[ar["s"] : ar["e"]] == risale_ornek.ARAPCA_BLOK  # type: ignore[index]
    assert all("؀" <= h <= "ۿ" or h in " !" for h in risale_ornek.ARAPCA_BLOK)
    ana = harita["rn:test-ornek:bolum-1:p5"]
    (hasiye,) = ana.marks
    assert hasiye["t"] == "hasiye" and hasiye["s"] == hasiye["e"]
    assert hasiye["a"] == risale_ornek.HASIYE_CAPASI
    assert 0 < hasiye["s"] < len(ana.text)  # type: ignore[operator]
    assert harita[risale_ornek.HASIYE_CAPASI].tur == "hasiye"


def test_sayfalar_rnk_bicimi_ve_cumle_ortasi() -> None:
    harita = {b.anchor: b for b in risale_ornek.birimler()}
    sayfalar = risale_ornek.sayfalar()
    for s in sayfalar:
        assert set(s) == {"dosya", "n", "satir", "capa", "ofs", "tur"}
        assert s["dosya"] == risale_ornek.DOSYA
    assert [s["n"] for s in sayfalar] == [1, 2, 3, 4, 5]
    assert [s["tur"] for s in sayfalar] == ["bas", "ortasi", "bas", "bas", "icerik-yok"]
    ortasi = sayfalar[1]
    assert ortasi["capa"] == risale_ornek.UZUN_CAPA
    ofs = ortasi["ofs"]
    assert isinstance(ofs, int) and ofs > 0
    uzun = harita[risale_ornek.UZUN_CAPA].text
    assert uzun[ofs:].startswith("ve metin")
    cumleler = cumleleri_ayir(uzun, [])
    assert len(cumleler) == 5
    assert any(bas < ofs < son for bas, son in cumleler)  # cumle ortasi
    assert sayfalar[-1]["capa"] is None
    satirlar_ = [s["satir"] for s in sayfalar]
    assert satirlar_ == sorted(satirlar_) and len(set(satirlar_)) == len(satirlar_)


def test_xref_k46_fikstur_kurallari() -> None:
    metinler = {b.anchor: b.text for b in risale_ornek.birimler()}
    satirlar_ = risale_ornek.xref_satirlari(metinler, "1")
    assert len(satirlar_) == 2
    assert len({risale_ornek.dogal_anahtar(x) for x in satirlar_}) == 2
    for x in satirlar_:
        assert x["status"] == "aday" and x["origin"] == "hat"
        assert x["evidence"] == {"fikstur": True, "source_id": KAYNAK, "yontem": "sentetik"}
        assert x["data_version"] == f"{KAYNAK}@1"
        assert str(x["src_anchor"]).startswith("rn:test-ornek:")
        assert str(x["dst_anchor"]).startswith("q:")
        assert isinstance(x["score"], int) and isinstance(x["confidence"], int)
        bas, son = x["src_span"]  # type: ignore[misc]
        assert 0 <= bas < son <= len(metinler[str(x["src_anchor"])])
        # aralik `src_span` sutununda; capa `@` tasimaz
        assert "@" not in str(x["src_anchor"])
    atif, iktibas = satirlar_
    assert atif["type"] == "atif" and atif["dst_span"] is None
    assert metinler[str(atif["src_anchor"])][atif["src_span"][0] : atif["src_span"][1]] == (  # type: ignore[index]
        risale_ornek.ATIF_PARCASI
    )
    assert iktibas["type"] == "iktibas"
    assert iktibas["dst_anchor"] == "q:1:1" and iktibas["dst_span"] == [1, 3]
    assert to_unit_span(parse("q:1:1:1-2")).span == (1, 3)
    # bayt bayt belirlenimci
    assert risale_ornek.xref_satirlari(metinler, "1") == satirlar_


def test_xref_kaynak_parcasi_yoksa_girdi_hatasi() -> None:
    metinler = {b.anchor: b.text for b in risale_ornek.birimler()}
    metinler[risale_ornek.ATIF_CAPASI] = "Deneme paragrafı 2 parça yok."
    with pytest.raises(GirdiHatasi):
        risale_ornek.xref_satirlari(metinler, "1")


# --- ingest ---------------------------------------------------------------------------------


def test_ingest_dosya_almaz_raw_yazmaz_manifest(veri: Path) -> None:
    assert ingest() == 0
    assert not (veri / "raw").exists() and not (veri / "gelen").exists()
    (_, klasor, manifest) = calismalar(veri, "ingest")[-1]
    assert manifest["girdiler"] == []
    ayrinti = manifest["ayrintilar"]
    assert isinstance(ayrinti, dict)
    assert ayrinti["birim"] == BIRIM_SAYISI and ayrinti["sayfa"] == SAYFA_SAYISI
    assert ayrinti["lugat_madde"] == 15
    assert {p.name for p in klasor.iterdir()} == {
        "units.jsonl",
        "sayfalar.jsonl",
        "lugat.jsonl",
        "manifest.json",
    }
    assert (
        (klasor / "units.jsonl").read_bytes()
        + (klasor / "sayfalar.jsonl").read_bytes()
        + (klasor / "lugat.jsonl").read_bytes()
    ) == risale_ornek.icerik_baytlari()


def test_ingest_iki_kosu_ayni_baytlar_force(veri: Path) -> None:
    assert ingest() == 0
    assert ingest(force=True) == 0
    ilk, ikinci = (c[1] for c in calismalar(veri, "ingest"))
    for ad in ("units.jsonl", "sayfalar.jsonl", "lugat.jsonl"):
        assert (ilk / ad).read_bytes() == (ikinci / ad).read_bytes()


def test_ingest_atlama_ayni_girdide(veri: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(lineage, "git_durumu", lambda _kok: TEMIZ_GIT)
    assert ingest() == 0
    assert ingest() == 0
    assert len(calismalar(veri, "ingest")) == 1
    assert ingest(force=True) == 0
    assert len(calismalar(veri, "ingest")) == 2


def test_ingest_dry_run_yazmaz(veri: Path) -> None:
    assert ingest(dry_run=True) == 0
    assert calismalar(veri, "ingest") == []


def test_ingest_gelen_tarih_cikis_iki(veri: Path) -> None:
    kod = risale_ornek.komut_ingest_ornek(
        gelen_tarih="2026-11-13", dry_run=False, force=False, config=None, kok=None
    )
    assert kod == 2
    assert calismalar(veri, "ingest") == []


def test_normalize_ve_anchor_ingestsiz_cikis_iki(veri: Path) -> None:
    assert normalize() == 2
    assert anchor() == 2


def test_normalize_baska_kaynak_cikis_iki(veri: Path) -> None:
    kod = adimlar.komut_normalize(
        source="risale-rnk-metin", dry_run=False, force=False, config=None, kok=None
    )
    assert kod == 2


# --- normalize ve anchor ------------------------------------------------------------------


def test_anchor_gercek_risale_semasiyla_ayni_alan_kumesi(veri: Path) -> None:
    zincir()
    units = satirlar(veri, "anchor")
    assert len(units) == BIRIM_SAYISI
    capalar = [s.metin("anchor") for s in units]
    assert capalar == sorted(capalar, key=lambda c: sort_key(parse(c)))
    for s in units:
        assert set(s.veri) == risale_adimlari.ANCHOR_ALANLARI
        assert s.metin("source_id") == KAYNAK
        assert s.metin("kind") == "risale" and s.metin("metin_durumu") == "taslak"
        assert s.metin("data_version") == f"{KAYNAK}@1"
        assert s.veri["ayah_lo"] is None and s.veri["ayah_hi"] is None
        attrs = s.nesne("attrs")
        assert attrs["dil"] == "tr" and attrs["yon"] == "ltr"
        for atilan in risale_adimlari.TASINAN_ATTRS:
            assert atilan not in attrs
        assert s.nesne("provenance")["cumle"] == {"surum": "1.0"}
    roller = {s.metin("anchor"): s.metin("role") for s in units}
    assert roller["rn:test-ornek:bolum-1:hasiye-1:p1"] == "dipnot"
    assert roller["rn:test-ornek:bolum-1:p1"] == "baslik"
    assert roller["rn:test-ornek:bolum-1:p2"] == "govde"
    # okuma sirasi: dipnot kendi ana paragrafindan sonra, sonraki bolumden once
    sira = {s.metin("anchor"): s.sayi("ord") for s in units}
    assert sorted(sira.values()) == list(range(1, BIRIM_SAYISI + 1))
    assert (
        sira["rn:test-ornek:bolum-1:p5"]
        < sira["rn:test-ornek:bolum-1:hasiye-1:p1"]
        < sira["rn:test-ornek:bolum-1:hakikat-1:p1"]
    )


def test_cumleler_ar_isareti_boldurmez(veri: Path) -> None:
    zincir()
    harita = {s.metin("anchor"): s for s in satirlar(veri, "anchor")}
    uzun = harita[risale_ornek.UZUN_CAPA]
    assert len(uzun.veri["sentences"]) == 5  # type: ignore[arg-type]
    arapca = harita[risale_ornek.ARAPCA_CAPASI]
    metin = arapca.metin("text")
    assert len(arapca.veri["sentences"]) == 2  # type: ignore[arg-type]
    assert harita["rn:test-ornek:bolum-1:p1"].veri["sentences"] == []  # baslik cumle tasimaz
    # isaret olmasa ayni metin ar blokta bolunurdu
    assert len(cumleleri_ayir(metin, [])) > 2
    assert arapca.veri["ar_norm"] is not None
    assert harita["rn:test-ornek:bolum-1:p2"].veri["ar_norm"] is None


def test_page_map_kendi_kaynagi_altinda(veri: Path) -> None:
    zincir()
    satirlar_ = satirlar(veri, "anchor", "page_map.jsonl")
    assert len(satirlar_) == 4  # sayfa 5 icerik-yok: satir yok
    for s in satirlar_:
        assert set(s.veri) == {
            "source_id",
            "volume",
            "page",
            "start_anchor",
            "start_offset",
            "end_anchor",
            "end_offset",
            "data_version",
        }
        assert s.metin("source_id") == KAYNAK != risale_kaynaklari.KAYNAK_BASKI
        assert s.sayi("volume") == risale_ornek.CILT
        assert s.metin("data_version").startswith(f"{KAYNAK}@1")
    sayfalar_ = {s.sayi("page"): s for s in satirlar_}
    assert sorted(sayfalar_) == [1, 2, 3, 4]
    cumle_ortasi = sayfalar_[2]
    assert cumle_ortasi.metin("start_anchor") == risale_ornek.UZUN_CAPA
    assert cumle_ortasi.sayi("start_offset") == risale_ornek.sayfalar()[1]["ofs"]
    assert sayfalar_[3].metin("start_anchor") == "rn:test-ornek:bolum-1:hakikat-1:p1"
    assert sayfalar_[3].sayi("start_offset") == 0
    # bolum basi satiri yok: bolumlerin sayfalari ya gercek satirdir ya ayni sayfadadir
    assert not any(s.metin("data_version").endswith("/bolum-basi") for s in satirlar_)
    (rapor,) = satirlar(veri, "anchor", "page_map_rapor.jsonl")
    assert rapor.veri["dosya"] == risale_ornek.DOSYA
    assert rapor.veri["gercek_satir"] == 4 and rapor.veri["icerik_yok"] == 1
    assert rapor.veri["bolum_basi_sayfa_ortasi"] == 1
    assert rapor.veri["bolum_basi_yerine_gecen"] == 1
    assert rapor.veri["bolum_basi_ayni_sayfada_ikinci"] == 1
    assert rapor.veri["bolum_basi_json_sayfa_farkli"] == 1
    assert rapor.veri["sayfa_basi_cumle_ortasi"] == 1


def test_xref_dosyasi_ve_manifest(veri: Path) -> None:
    zincir()
    (_, _, manifest) = calismalar(veri, "anchor")[-1]
    yollar = {c["yol"].rsplit("/", 1)[1] for c in manifest["ciktilar"]}  # type: ignore[index, union-attr]
    assert yollar == {"units.jsonl", "page_map.jsonl", "page_map_rapor.jsonl", "xref.jsonl"}
    girdiler = {g["yol"].rsplit("/", 1)[1] for g in manifest["girdiler"]}  # type: ignore[index, union-attr]
    assert girdiler == {"units.jsonl", "sayfalar.jsonl"}
    xrefler = satirlar(veri, "anchor", "xref.jsonl")
    assert len(xrefler) == 2
    assert {x.metin("status") for x in xrefler} == {"aday"}
    assert {x.metin("origin") for x in xrefler} == {"hat"}
    assert all(x.nesne("evidence")["fikstur"] is True for x in xrefler)


def test_anchor_idempotent_iki_kosu_ayni_baytlar(veri: Path) -> None:
    zincir()
    assert normalize(force=True) == 0
    assert anchor(force=True) == 0
    ilk, ikinci = (c[1] for c in calismalar(veri, "anchor")[-2:])
    for ad in ("units.jsonl", "page_map.jsonl", "page_map_rapor.jsonl", "xref.jsonl"):
        assert (ilk / ad).read_bytes() == (ikinci / ad).read_bytes(), ad


def test_anchor_dry_run_yazmaz(veri: Path) -> None:
    assert ingest() == 0 and normalize() == 0
    assert anchor(dry_run=True) == 0
    assert calismalar(veri, "anchor") == []


# --- QA kapilari ----------------------------------------------------------------------------


def girdi_kur(veri: Path) -> kapilar.OrnekGirdisi:
    return kapilar.OrnekGirdisi(
        kayit=kayit(),
        anchor_satirlari=satirlar(veri, "anchor"),
        sayfalar=satirlar(veri, "ingest", "sayfalar.jsonl"),
        page_map=satirlar(veri, "anchor", "page_map.jsonl"),
        xref=satirlar(veri, "anchor", "xref.jsonl"),
        beklenen=risale_ornek.birimler(),
        depo_kok=depo_koku(),
        lugat=satirlar(veri, "ingest", "lugat.jsonl"),
    )


def kopya(satir: Satir, **degisim: object) -> Satir:
    veri = copy.deepcopy(satir.veri)
    veri.update(degisim)
    return Satir(satir.etiket, satir.no, veri)


def test_dort_kapi_gecer_ve_rapor_yazilir(veri: Path) -> None:
    zincir()
    sonuclar = qa_ornek.kapilari_kos(girdi_kur(veri))
    assert {k: s.bulgular for k, s in sonuclar.items()} == {k: () for k in KAPILAR}
    assert sonuclar["G-CAP"].sayilar["xref"] == 2 and sonuclar["G-CAP"].sayilar["sayfa_satiri"] == 4
    assert sonuclar["G-BUT"].sayilar["sayfa_ortasi"] == 1
    qa_raporu = next(
        r
        for r in (
            json.loads(p.read_text(encoding="utf-8")) for p in (veri / "reports").glob("*.json")
        )
        if r.get("kapilar")
    )
    assert qa_raporu["kaynak"] == KAYNAK
    assert qa_raporu["kapilar"] == {k: "gecti" for k in KAPILAR}


def test_qa_gate_kismi_kosu_ve_gecersiz_kapi(veri: Path) -> None:
    zincir()
    assert qa("G-KAY", "G-CAP") == 0
    assert qa("G-YOK") == 2


def test_qa_ingestsiz_cikis_iki(veri: Path) -> None:
    assert qa() == 2


def test_g_kay_kayit_hatalari(veri: Path) -> None:
    zincir()
    g = girdi_kur(veri)
    k = g.kayit
    g.kayit = replace(k, atif_metni="Baska bir atif.")
    assert any("atif_metni" in b for b in kapilar.g_kay(g).bulgular)
    g.kayit = replace(k, slug="risale-deneme")
    assert kapilar.g_kay(g).bulgular
    g.kayit = replace(k, notice_text="x")
    assert kapilar.g_kay(g).bulgular


def test_g_but_metin_degisince_kalir(veri: Path) -> None:
    zincir()
    g = girdi_kur(veri)
    degisen = list(g.anchor_satirlari)
    degisen[0] = kopya(degisen[0], text=degisen[0].metin("text") + " x")
    g.anchor_satirlari = degisen
    bulgular = kapilar.g_but(g).bulgular
    assert any(b.startswith("metin:") for b in bulgular)


def test_g_but_lugat_degisince_kalir_ve_none_denetlenmez(veri: Path) -> None:
    zincir()
    g = girdi_kur(veri)
    assert kapilar.g_but(g).sayilar["lugat_madde"] == 15
    assert g.lugat is not None
    degisen = list(g.lugat)
    degisen[0] = kopya(degisen[0], duzey=3)
    g.lugat = degisen
    assert "lugat.jsonl uretecin cikisiyla ayni degil" in kapilar.g_but(g).bulgular
    g.lugat = None  # yuklenmemis: denetlenmez (eski cagrilar)
    assert kapilar.g_but(g).bulgular == ()
    assert "lugat_madde" not in kapilar.g_but(g).sayilar


def test_g_but_nfc_degil_ve_kontrol_karakteri_kalir(veri: Path) -> None:
    zincir()
    g = girdi_kur(veri)
    degisen = list(g.anchor_satirlari)
    degisen[0] = kopya(degisen[0], text="Deneme İlk")
    degisen[1] = kopya(degisen[1], text="Deneme‎paragraf")
    g.anchor_satirlari = degisen
    bulgular = kapilar.g_but(g).bulgular
    assert any(b.startswith("kanonik olmayan metin") for b in bulgular)
    assert any(b.startswith("kontrol karakteri") for b in bulgular)


def test_g_but_dizin_adi_kalir(veri: Path) -> None:
    zincir()
    g = girdi_kur(veri)
    degisen = list(g.anchor_satirlari)
    degisen[0] = kopya(degisen[0], anchor="rn:dizin:p1")
    g.anchor_satirlari = degisen
    assert any(b.startswith("dizin adi") for b in kapilar.g_but(g).bulgular)
    assert any(b.startswith("gecersiz capa") for b in kapilar.g_cap(g).bulgular)


def test_g_cap_k46_fikstur_kurallari_kalir(veri: Path) -> None:
    zincir()
    g = girdi_kur(veri)
    ilk = g.xref[0]
    ornekler = {
        "evidence.fikstur": kopya(ilk, evidence={"fikstur": False, "source_id": KAYNAK}),
        "status ya da origin": kopya(ilk, status="onayli"),
        "kaynak ucu": kopya(ilk, src_span=[0, 99999]),
        "hedef ucu": kopya(ilk, dst_anchor="rn:test-ornek:bolum-1:p2"),
        "tur": kopya(ilk, type="kok"),
        "score ya da confidence": kopya(ilk, score=2),
    }
    for ad, bozuk in ornekler.items():
        g.xref = [bozuk, *g.xref[1:]]
        bulgular = kapilar.g_cap(g).bulgular
        assert any(b.startswith(ad) for b in bulgular), ad
    g.xref = [ilk, kopya(ilk)]  # ayni dogal anahtar
    assert any(b.startswith("dogal anahtar") for b in kapilar.g_cap(g).bulgular)
    g.xref = []
    assert "xref bos" in kapilar.g_cap(g).bulgular


def test_g_cap_page_map_hatalari_kalir(veri: Path) -> None:
    zincir()
    g = girdi_kur(veri)
    ilk = g.page_map[0]
    ornekler = {
        "kaynak ya da cilt": kopya(ilk, source_id="risale-baski-rnk"),
        "capa": kopya(ilk, start_anchor="rn:test-ornek:p99"),
        "ofset": kopya(ilk, start_offset=99999),
        "data_version": kopya(ilk, data_version="risale-baski-rnk@1"),
    }
    for ad, bozuk in ornekler.items():
        g.page_map = [bozuk, *g.page_map[1:]]
        assert any(b.startswith(ad) for b in kapilar.g_cap(g).bulgular), ad


def test_g_cap_content_hash_cumle_ve_onceki_kalir(veri: Path) -> None:
    zincir()
    g = girdi_kur(veri)
    degisen = list(g.anchor_satirlari)
    degisen[2] = kopya(degisen[2], content_hash="0" * 64)
    degisen[3] = kopya(degisen[3], sentences=[[0, 3]])
    g.anchor_satirlari = degisen
    bulgular = kapilar.g_cap(g).bulgular
    assert any(b.startswith("content_hash:") for b in bulgular)
    assert any(b.startswith("sentences ayiriciyla") for b in bulgular)
    g = girdi_kur(veri)
    g.onceki = kapilar.Onceki(
        "onceki", {"rn:test-ornek:p1": "0" * 64, "rn:test-ornek:yok:p1": "1" * 64}
    )
    bulgular = kapilar.g_cap(g).bulgular
    assert any(b.startswith("onceki surumde olup kaybolan") for b in bulgular)
    assert any(b.startswith("onceki surumle content_hash") for b in bulgular)


def test_g_nor_arama_anahtari_bozulunca_kalir(veri: Path) -> None:
    zincir()
    g = girdi_kur(veri)
    degisen = list(g.anchor_satirlari)
    degisen[2] = kopya(degisen[2], tr_narrow="bozuk")
    arapca = next(
        i for i, s in enumerate(degisen) if s.metin("anchor") == risale_ornek.ARAPCA_CAPASI
    )
    degisen[arapca] = kopya(degisen[arapca], ar_norm=None)
    g.anchor_satirlari = degisen
    bulgular = kapilar.g_nor(g).bulgular
    assert any(b.startswith("arama anahtari") for b in bulgular)
    assert any(b.startswith("ar_norm") for b in bulgular)
    assert any("ar_norm dolu degil" in b for b in bulgular)


def test_g_nor_provenance_arama_surumu(veri: Path) -> None:
    zincir()
    g = girdi_kur(veri)
    degisen = list(g.anchor_satirlari)
    saglayici = copy.deepcopy(degisen[0].nesne("provenance"))
    saglayici["arama"] = {"normalizer_version": "0"}
    degisen[0] = kopya(degisen[0], provenance=saglayici)
    g.anchor_satirlari = degisen
    assert any(b.startswith("provenance.arama") for b in kapilar.g_nor(g).bulgular)


# --- export pg hazirlik (DB'siz) --------------------------------------------------------------


def test_export_hazirla_fikstur_birimlerini_ve_page_mapi_kabul_eder(
    veri: Path, tmp_path: Path
) -> None:
    """`pg.hazirla` fiksturu kabul eder (birimler ve page_map): DB acilmaz."""
    zincir()
    ctx = ctx_kur(tmp_path, depo_koku(), adim="export", kaynaklar=[KAYNAK])
    h = pg.hazirla(ctx, KAYNAK, None, ())
    assert h.source_id == KAYNAK
    assert h.risale is not None
    assert h.risale.satir_sayisi == BIRIM_SAYISI and h.risale.kitap_sayisi == 1
    assert h.ham[KAYNAK] == []  # ham dosya yok (veri koddan uretilir)
    # page_map ayni anchor calismasindan, ayni hazirlikta (gercek RNK'da ayri kaynak)
    assert len(h.risale_sayfa) == 4
    assert {r.source_id for r in h.risale_sayfa} == {KAYNAK}
    assert {r.volume for r in h.risale_sayfa} == {risale_ornek.CILT}
    assert pg_risale_sayfa.METIN_KAYNAGI[KAYNAK] == KAYNAK
    # her satir `pg_risale.satir_coz` katiligindan gecer
    parcalar = list(pg_risale.satirlari_akit_risale(Path(h.risale.yol), KAYNAK))
    assert len(parcalar) == BIRIM_SAYISI
    assert {p.source_id for p in parcalar} == {KAYNAK}
    assert {p.attrs["dil"] for p in parcalar} == {"tr"}
    # fiksturun iki sentetik xref'i (A20.7b): ayni hazirlikta, binde puanla
    assert {x.tur for x in h.xref} == {"atif", "iktibas"}
    assert {(x.score_binde, x.confidence_binde) for x in h.xref} == {(1000, 1000)}
    assert {x.dst_anchor for x in h.xref} == {"q:1:2", "q:1:1"}
    assert [x.dst_span for x in sorted(h.xref, key=lambda x: x.tur)] == [None, (1, 3)]
    assert all(x.evidence["fikstur"] is True for x in h.xref)


def test_export_hazirla_fikstur_lugatini_ayni_kaynak_adinda_okur(
    veri: Path, tmp_path: Path
) -> None:
    """Fikstur lugati `test-risale-ornek` adinda (risale-dizin Glossary kaynagi ile ayni)."""
    zincir()
    ctx = ctx_kur(tmp_path, depo_koku(), adim="export", kaynaklar=[KAYNAK])
    h = pg.hazirla(ctx, KAYNAK, None, ())
    assert len(h.lugat) == 15
    assert {m.source_id for m in h.lugat} == {KAYNAK} and KAYNAK.startswith("test-")
    assert sum(1 for m in h.lugat if m.tanim_tr is None) == 5  # her ucuncu madde tanimsiz
    assert all(m.kaynaklar["fikstur"] is True for m in h.lugat)
    assert all(
        "anlam_basvuru" not in m.kaynaklar and "anlam_basvuru" in m.onerilen for m in h.lugat
    )
    assert {m.duzey for m in h.lugat} == {1, 2, 3}


def test_export_hazirla_qa_kalmissa_reddeder(veri: Path, tmp_path: Path) -> None:
    assert ingest() == 0 and normalize() == 0 and anchor() == 0  # qa raporu yok
    ctx = ctx_kur(tmp_path, depo_koku(), adim="export", kaynaklar=[KAYNAK])
    with pytest.raises(Exception, match=r"QA|rapor"):
        pg.hazirla(ctx, KAYNAK, None, ())


def test_pg_risale_sayfa_kaynak_eslemesi_geriye_uyumlu(tmp_path: Path) -> None:
    assert pg_risale_sayfa.kaynak_denetle(risale_kaynaklari.KAYNAK_BASKI) == (
        risale_kaynaklari.KAYNAK_RNK
    )
    assert pg_risale_sayfa.kaynak_denetle(KAYNAK) == KAYNAK
    for yanlis in ("risale-rnk-metin", "risale-asil-nusha", "test-kucuk"):
        with pytest.raises(GirdiHatasi):
            pg_risale_sayfa.kaynak_denetle(yanlis)
    # fiksturun page_map'i ayri hazirlanamaz: birimlerle birlikte (pg_risale.hazirla)
    ctx = ctx_kur(tmp_path, depo_koku(), adim="export", kaynaklar=[KAYNAK])
    with pytest.raises(GirdiHatasi, match="birimlerle birlikte"):
        pg_risale_sayfa.hazirla(ctx, KAYNAK, None, ())


def test_export_yukleme_tek_islemde_birimler_sonra_page_map(veri: Path, tmp_path: Path) -> None:
    """Sahte baglanti: birimler ve page_map TEK islemde, birimlerden sonra (DB yok)."""
    zincir()
    db = SahteBaglanti(
        esle(
            ("INSERT INTO icerik.unit", SahteSonuc(rowcount=BIRIM_SAYISI)),
            ("count(*) FILTER (WHERE (p.start_anchor", SahteSonuc([(0, 0)])),
            ("INSERT INTO icerik.page_map", SahteSonuc(rowcount=4)),
            ("count(*) FILTER (WHERE o.m_id IS NULL)", SahteSonuc([(15, 0, 0, 15, 0)])),
            ("INSERT INTO icerik.lugat_madde", SahteSonuc(rowcount=15)),
            ("INSERT INTO icerik.review", SahteSonuc(rowcount=15)),
            ("LEFT JOIN icerik.xref x ON", SahteSonuc([(2, 0, 0, 0, 0, 0)])),
            ("INSERT INTO icerik.xref", SahteSonuc(rowcount=2)),
        )
    )
    kod = pg.komut_export_pg(
        ayarlar_kur(tmp_path),
        depo_kok=depo_koku(),
        source=KAYNAK,
        baglanti=lambda: db,  # type: ignore[arg-type, return-value]
    )
    assert kod == 0
    assert [i.durum for i in db.islemler] == ["onaylandi"]
    sorgular = [m for i in db.islemler for m, _ in i.sorgular]
    sira = [
        next(i for i, m in enumerate(sorgular) if parca in m)
        for parca in (
            "INSERT INTO icerik.source",
            "INSERT INTO icerik.unit",
            "CREATE TEMP TABLE staging_risale_sayfa",
            "FROM (SELECT start_anchor AS anchor",
            "INSERT INTO icerik.page_map",
            "CREATE TEMP TABLE staging_lugat",
            "INSERT INTO icerik.lugat_madde",
            "INSERT INTO icerik.review",
            "CREATE TEMP TABLE staging_xref",
            "INSERT INTO icerik.xref",
        )
    ]
    # lugat: birimlerden ve page_map'ten sonra; xref en son (iki ucu da ayni islemde)
    assert sira == sorted(sira) and len(set(sira)) == 10
    ((_, capa_params),) = db.sorgular("FROM (SELECT start_anchor AS anchor")
    assert capa_params == (KAYNAK,)  # sayfa capalari fiksturun kendi birimlerinde aranir
    sayfa_satirlari = [r for r in db.kopya_satirlari() if len(r) == 8]
    assert len(sayfa_satirlari) == 4
    assert {r[6] for r in sayfa_satirlari} == {KAYNAK}  # source_id sutunu
    rapor = next(
        r
        for r in (
            json.loads(p.read_text(encoding="utf-8")) for p in (veri / "reports").glob("*.json")
        )
        if r.get("komut") == "export pg"
    )
    assert rapor["sayilar"]["staging"] == BIRIM_SAYISI  # type: ignore[index]
    assert rapor["sayilar"]["sayfa_staging"] == 4  # type: ignore[index]
    assert rapor["sayilar"]["lugat_staging"] == 15  # type: ignore[index]
    assert rapor["sayilar"]["lugat_eklenen"] == 15  # type: ignore[index]
    assert rapor["sayilar"]["lugat_review_acilan"] == 15  # type: ignore[index]
    assert rapor["sayilar"]["xref_staging"] == 2  # type: ignore[index]
    assert rapor["sayilar"]["xref_eklenen"] == 2  # type: ignore[index]
    xref_kopya = [r for r in db.kopya_satirlari() if len(r) == 10]
    assert len(xref_kopya) == 2
    assert {r[6] for r in xref_kopya} == {1.0}  # score: 1 -> binde 1000 -> 1,0
    assert any(r[5] is not None for r in xref_kopya)  # kelime araligi q:1:1:1-2 -> [1, 3)


def test_export_fikstur_xref_hedefi_yoksa_yazilmaz_uyari_verir(veri: Path, tmp_path: Path) -> None:
    """Tanzil yuklenmemisse fikstur birimleri yine yuklenir; xref yazilmaz (uyari, sayac)."""
    zincir()
    db = SahteBaglanti(
        esle(
            ("INSERT INTO icerik.unit", SahteSonuc(rowcount=BIRIM_SAYISI)),
            ("count(*) FILTER (WHERE (p.start_anchor", SahteSonuc([(0, 0)])),
            ("INSERT INTO icerik.page_map", SahteSonuc(rowcount=4)),
            ("count(*) FILTER (WHERE o.m_id IS NULL)", SahteSonuc([(15, 0, 0, 15, 0)])),
            ("INSERT INTO icerik.lugat_madde", SahteSonuc(rowcount=15)),
            ("INSERT INTO icerik.review", SahteSonuc(rowcount=15)),
            ("s.dst_anchor) ORDER BY", SahteSonuc([("q:1:1",), ("q:1:2",)])),
        )
    )
    kod = pg.komut_export_pg(
        ayarlar_kur(tmp_path),
        depo_kok=depo_koku(),
        source=KAYNAK,
        baglanti=lambda: db,  # type: ignore[arg-type, return-value]
    )
    assert kod == 0
    assert [i.durum for i in db.islemler] == ["onaylandi"]
    assert not db.sorgular("INSERT INTO icerik.xref")
    assert db.sorgular("INSERT INTO icerik.unit")  # birimler yine yuklendi
    rapor = next(
        r
        for r in (
            json.loads(p.read_text(encoding="utf-8")) for p in (veri / "reports").glob("*.json")
        )
        if r.get("komut") == "export pg"
    )
    assert rapor["sayilar"]["xref_hedefi_yok"] == 2  # type: ignore[index]
    assert any("hedef ayeti" in u for u in rapor["uyarilar"])  # type: ignore[union-attr]


def test_export_fikstur_xref_kaynak_ucu_yoksa_cikis_bir(veri: Path, tmp_path: Path) -> None:
    zincir()
    db = SahteBaglanti(
        esle(
            ("INSERT INTO icerik.unit", SahteSonuc(rowcount=BIRIM_SAYISI)),
            ("count(*) FILTER (WHERE (p.start_anchor", SahteSonuc([(0, 0)])),
            ("INSERT INTO icerik.page_map", SahteSonuc(rowcount=4)),
            ("count(*) FILTER (WHERE o.m_id IS NULL)", SahteSonuc([(15, 0, 0, 15, 0)])),
            ("INSERT INTO icerik.lugat_madde", SahteSonuc(rowcount=15)),
            ("INSERT INTO icerik.review", SahteSonuc(rowcount=15)),
            ("s.src_anchor) ORDER BY", SahteSonuc([("rn:test-ornek:bolum-1:p1",)])),
        )
    )
    kod = pg.komut_export_pg(
        ayarlar_kur(tmp_path),
        depo_kok=depo_koku(),
        source=KAYNAK,
        baglanti=lambda: db,  # type: ignore[arg-type, return-value]
    )
    assert kod == 1
    assert db.islemler[0].durum == "geri_alindi"  # ardindan basarisiz pipeline_run satiri


# --- kayit ve CLI -----------------------------------------------------------------------------


def test_risale_kaynaklari_kaydi_ve_diger_kaynaklar_ayni() -> None:
    k = risale_kaynaklari.kaynak(KAYNAK)
    assert risale_kaynaklari.risale_mi(KAYNAK) and k.yukleme
    assert k.kapilar == risale_kaynaklari.RNK_KAPILARI
    assert risale_kaynaklari.bagdastirici_modulu(KAYNAK) is risale_ornek
    diyanet = risale_kaynaklari.kaynak(risale_kaynaklari.KAYNAK_DIYANET)
    assert not diyanet.yukleme and diyanet.kapilar == ("G-KAY", "G-BUT")
    rnk = risale_kaynaklari.kaynak(risale_kaynaklari.KAYNAK_RNK)
    assert rnk.yukleme and rnk.kapilar == risale_kaynaklari.RNK_KAPILARI
    assert not risale_kaynaklari.baski_mi(KAYNAK)
    assert pg.EK_KAYNAKLAR[KAYNAK] == ()


def cli_kos(*arg: str) -> int:
    return runner.invoke(cli.app, list(arg)).exit_code


def test_cli_zincir_ingest_normalize_anchor_qa(veri: Path) -> None:
    assert cli_kos("ingest", "risale", "--source", KAYNAK, "--dry-run") == 0
    assert calismalar(veri, "ingest") == []
    assert cli_kos("ingest", "risale", "--source", KAYNAK) == 0
    assert cli_kos("normalize", "--source", KAYNAK) == 0
    assert cli_kos("anchor", "--source", KAYNAK) == 0
    assert cli_kos("qa", "run", "--source", KAYNAK) == 0
    assert cli_kos("qa", "run", "--source", KAYNAK, "--gate", "G-CAP") == 0
    assert cli_kos("qa", "run", "--source", KAYNAK, "--gate", "G-YOK") == 2
    assert len(satirlar(veri, "anchor")) == BIRIM_SAYISI
    assert len(satirlar(veri, "anchor", "xref.jsonl")) == 2


@pytest.mark.parametrize(
    "arg",
    [["--kilit-oner"], ["--limit", "3"], ["--gelen-tarih", "2026-11-13"]],
)
def test_cli_ingest_reddedilenler_cikis_iki(veri: Path, arg: list[str]) -> None:
    assert cli_kos("ingest", "risale", "--source", KAYNAK, *arg) == 2
    assert calismalar(veri, "ingest") == []


def test_cli_yardim_ve_bilinmeyen_kaynak(veri: Path) -> None:
    yardim = ansisiz(runner.invoke(cli.app, ["ingest", "risale", "--help"]).output)
    assert KAYNAK in yardim and "risale-rnk-metin" in yardim and "risale-asil-nusha" in yardim
    sonuc = runner.invoke(cli.app, ["ingest", "risale", "--source", "bilinmeyen"])
    assert sonuc.exit_code == 2
    assert KAYNAK in sonuc.output


def test_cli_normalize_anchor_ingestsiz_cikis_iki(veri: Path) -> None:
    assert cli_kos("normalize", "--source", KAYNAK) == 2
    assert cli_kos("anchor", "--source", KAYNAK) == 2
    assert cli_kos("qa", "run", "--source", KAYNAK) == 2
