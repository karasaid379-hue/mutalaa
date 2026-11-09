# ruff: noqa: RUF001
"""Sentetik fiksturler (A13.6): uretec, normalize, capa, QA kapilari (SENTETIK veri).

`test-kucuk` ve `test-tefsir-ornek` birimleri kodla uretilir; zincir gercek depo kokunun gercek
kaynak kayitlariyla (`pipeline/sources/test-*.toml`) ama `tmp_path` altindaki veri kokuyle kosar.
Hicbir metin bir dini kaynaktan alinmaz; hepsi "Deneme paragrafi N ..." biciminde uretilir.
"""

import json
import unicodedata
from pathlib import Path

import pytest
from hat_yardimci import TEMIZ_GIT
from typer.testing import CliRunner, Result

from mutalaa_pipeline import cli, lineage, sources
from mutalaa_pipeline.adimlar import fikstur as adimlar
from mutalaa_pipeline.anchor import AnchorError, K, Tf, kanonik_metin, parse, sort_key
from mutalaa_pipeline.anchor import format as anchor_format
from mutalaa_pipeline.export.ortak import depo_koku
from mutalaa_pipeline.ingest import fikstur
from mutalaa_pipeline.normalize import lower_turkish
from mutalaa_pipeline.qa import KAPILAR
from mutalaa_pipeline.qa.checks import fikstur as kapilar
from mutalaa_pipeline.qa.checks.tanzil import Onceki
from mutalaa_pipeline.staged import Satir

runner = CliRunner()
SLUGLAR = fikstur.KAYNAKLAR
SAYILAR = {"test-kucuk": 12, "test-tefsir-ornek": 7}


@pytest.fixture
def veri(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Gecici veri koku; `MUTALAA_VERI_KOK` bu testte kok olur (gercek `data/` kullanilmaz)."""
    kok = tmp_path / "data"
    monkeypatch.setenv("MUTALAA_VERI_KOK", str(kok))
    return kok


def komut(*arglar: str) -> Result:
    return runner.invoke(cli.app, list(arglar))


def zincir_kos(slug: str) -> None:
    """ingest -> normalize -> anchor -> qa; her adim 0 ile bitmeli."""
    for adim in (["ingest", "fikstur"], ["normalize"], ["anchor"], ["qa", "run"]):
        sonuc = komut(*adim, "--source", slug)
        assert sonuc.exit_code == 0, (adim, sonuc.stdout, sonuc.stderr)


def calismalar(veri: Path, slug: str, adim: str) -> list[tuple[str, Path, dict[str, object]]]:
    return [c for c in lineage.calismalar(veri / "staged" / slug) if c[2].get("adim") == adim]


def units(veri: Path, slug: str, adim: str) -> list[dict[str, object]]:
    klasor = calismalar(veri, slug, adim)[-1][1]
    return [
        json.loads(satir)
        for satir in (klasor / "units.jsonl").read_bytes().decode("utf-8").splitlines()
    ]


# --- kayit ve uretec -----------------------------------------------------------------------


def test_uc_kaynak_kaydi_gecerli() -> None:
    kayitlar = {s.kaynak.slug: s.kaynak for s in sources.yukle(depo_koku()) if s.kaynak is not None}
    for slug, tur in (
        ("test-kucuk", "kitap"),
        ("test-tefsir-ornek", "tefsir"),
        ("test-ses", "ses"),
    ):
        kayit = kayitlar[slug]
        assert kayit.tur.value == tur
        assert kayit.atif_metni == kapilar.ATIF_METNI
        assert kayit.surum == "1"
        assert kayit.notlar is not None
        assert "sentetik fikstür, a13" in kayit.notlar.lower()


def test_uretec_belirlenimci_ayni_bayt() -> None:
    for slug in SLUGLAR:
        assert fikstur.icerik_baytlari(slug) == fikstur.icerik_baytlari(slug)
        assert len(fikstur.birimler(slug)) == SAYILAR[slug]


def test_kitap_capalari_ve_metni() -> None:
    birimler = fikstur.birimler("test-kucuk")
    capalar = [b.anchor for b in birimler]
    assert capalar[0] == "k:test-kucuk:bolum-1:p1"
    assert "k:test-kucuk:bolum-2:p6" in capalar
    for b in birimler:
        ref = parse(b.anchor)
        assert anchor_format(ref) == b.anchor
        assert isinstance(ref.anchor, K)
        assert b.kind == "kitap"
        assert b.parent_path == f"k:test-kucuk:{ref.anchor.yol[1]}"
        assert b.text.startswith(f"Deneme paragrafı {ref.anchor.p} ")
        # kendi metnimiz: ilk kayit kanonik hali degismez, NFC
        assert kanonik_metin(b.text) == b.text
        assert unicodedata.is_normalized("NFC", b.text)
    assert len(set(capalar)) == len(capalar)


def test_kitapta_isik_tek_paragrafta_ve_i_dotsuz_cumle() -> None:
    metinler = [b.text for b in fikstur.birimler("test-kucuk")]
    assert sum("Işık" in m for m in metinler) == 1
    assert sum("ışık" in lower_turkish(m) for m in metinler) == 1  # baska yerde isik yok
    assert any("İ" in m and "ı" in m for m in metinler)


def test_tefsir_capalari_ve_ayet_araligi() -> None:
    birimler = fikstur.birimler("test-tefsir-ornek")
    for b in birimler:
        ref = parse(b.anchor)
        assert anchor_format(ref) == b.anchor
        assert isinstance(ref.anchor, Tf)
        assert ref.anchor.eser == "test-ornek"
        assert b.kind == "tefsir"
        assert b.parent_path is None
        assert kanonik_metin(b.text) == b.text
    assert adimlar.ayet_araligi("tf:test-ornek:1-1-7:p1") == (1, 8)
    assert adimlar.ayet_araligi("tf:test-ornek:2-255-257:p1") == (262, 265)
    assert adimlar.ayet_araligi("tf:test-ornek:2-256-256:p1") == (263, 264)
    assert adimlar.ayet_araligi("k:test-kucuk:bolum-1:p1") is None


def test_capa_ailesi_yabanci_capayi_reddeder() -> None:
    assert adimlar.capa_ailesine_uyar("test-kucuk", "k:test-kucuk:bolum-1:p1")
    assert not adimlar.capa_ailesine_uyar("test-kucuk", "k:baska:bolum-1:p1")
    assert not adimlar.capa_ailesine_uyar("test-kucuk", "q:1:1")
    assert not adimlar.capa_ailesine_uyar("test-tefsir-ornek", "tf:elmalili:1-1-7:p1")
    assert not adimlar.capa_ailesine_uyar("test-tefsir-ornek", "tf:test-ornek:1-1-7:p1@0-5")
    assert not adimlar.capa_ailesine_uyar("test-kucuk", "kitap bozuk")
    with pytest.raises(AnchorError):
        parse("kitap bozuk")


def test_ingest_iki_kosu_ayni_baytlar(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ozetler = []
    for ad in ("bir", "iki"):
        monkeypatch.setenv("MUTALAA_VERI_KOK", str(tmp_path / ad))
        assert komut("ingest", "fikstur", "--source", "test-kucuk").exit_code == 0
        klasor = calismalar(tmp_path / ad, "test-kucuk", "ingest")[-1][1]
        ozetler.append(lineage.sha256_dosya(klasor / "units.jsonl"))
    assert ozetler[0] == ozetler[1]
    assert ozetler[0] == lineage.sha256_bayt(fikstur.icerik_baytlari("test-kucuk"))


def test_ingest_dosya_almaz_ve_raw_yazmaz(veri: Path) -> None:
    assert komut("ingest", "fikstur", "--source", "test-kucuk").exit_code == 0
    assert not (veri / "raw").exists()
    assert not (veri / "gelen").exists()
    manifest = calismalar(veri, "test-kucuk", "ingest")[-1][2]
    assert manifest["girdiler"] == []
    ayrinti = manifest["ayrintilar"]
    assert isinstance(ayrinti, dict)
    assert ayrinti["birim"] == 12
    assert ayrinti["uretec_surumu"] == fikstur.URETEC_SURUMU


def test_ingest_atlama_ayni_girdide(veri: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(lineage, "git_durumu", lambda _kok: TEMIZ_GIT)
    assert komut("ingest", "fikstur", "--source", "test-kucuk").exit_code == 0
    ikinci = komut("ingest", "fikstur", "--source", "test-kucuk")
    assert ikinci.exit_code == 0
    assert "atlandi" in ikinci.stdout
    assert len(calismalar(veri, "test-kucuk", "ingest")) == 1
    zorla = komut("ingest", "fikstur", "--source", "test-kucuk", "--force")
    assert "atlandi" not in zorla.stdout
    assert len(calismalar(veri, "test-kucuk", "ingest")) == 2


def test_ingest_dry_run_yazmaz(veri: Path) -> None:
    sonuc = komut("ingest", "fikstur", "--source", "test-kucuk", "--dry-run")
    assert sonuc.exit_code == 0
    assert calismalar(veri, "test-kucuk", "ingest") == []


@pytest.mark.parametrize(
    "arglar",
    [
        ["--source", "test-ses"],  # birim uretmez (A27.2)
        ["--source", "test-yok"],
        ["--source", "tanzil-uthmani"],
        ["--source", "test-kucuk", "--limit", "3"],
    ],
)
def test_ingest_reddedilenler_cikis_iki(veri: Path, arglar: list[str]) -> None:
    sonuc = komut("ingest", "fikstur", *arglar)
    assert sonuc.exit_code == 2
    assert calismalar(veri, "test-kucuk", "ingest") == []


@pytest.mark.parametrize("adim", ["normalize", "anchor"])
def test_adimlar_ingestsiz_cikis_iki(veri: Path, adim: str) -> None:
    sonuc = komut(adim, "--source", "test-kucuk")
    assert sonuc.exit_code == 2
    assert "once:" in sonuc.stderr


def test_qa_zincirsiz_cikis_iki(veri: Path) -> None:
    assert komut("qa", "run", "--source", "test-kucuk").exit_code == 2


# --- zincir --------------------------------------------------------------------------------


@pytest.mark.parametrize("slug", SLUGLAR)
def test_zincir_dort_kapi_gecer(veri: Path, slug: str) -> None:
    zincir_kos(slug)
    rapor = max(
        (json.loads(p.read_bytes()) for p in (veri / "reports").glob("*.json")),
        key=lambda r: r["run_id"],
    )
    assert rapor["komut"] == "qa run"
    assert rapor["kaynak"] == slug
    assert rapor["kapilar"] == dict.fromkeys(KAPILAR, "gecti")
    assert rapor["cikis_kodu"] == 0
    satirlar = units(veri, slug, "anchor")
    assert len(satirlar) == SAYILAR[slug]
    assert [s["ord"] for s in satirlar] == list(range(1, SAYILAR[slug] + 1))
    for s in satirlar:
        assert s["metin_durumu"] == "taslak"
        assert s["role"] == "govde"
        assert s["ar_norm"] is None
        assert s["source_id"] == slug
        assert s["data_version"] == f"{slug}@1"
        assert s["content_hash"] == lineage.sha256_bayt(str(s["text"]).encode("utf-8"))
    # QA kapi olaylari kapi adini tasir
    gunluk = (veri / "logs" / f"{rapor['run_id']}.jsonl").read_bytes().decode("utf-8")
    olaylar = [json.loads(s) for s in gunluk.splitlines()]
    kapi_olaylari = [o for o in olaylar if o["olay"] == "qa_kapi"]
    assert [o["kapi"] for o in kapi_olaylari] == list(KAPILAR)
    assert all(o["level"] == "INFO" and o["source_id"] == slug for o in kapi_olaylari)


def test_zincir_kitap_alanlari_ve_arama_anahtarlari(veri: Path) -> None:
    zincir_kos("test-kucuk")
    satirlar = {str(s["anchor"]): s for s in units(veri, "test-kucuk", "anchor")}
    ilk = satirlar["k:test-kucuk:bolum-1:p1"]
    assert ilk["kind"] == "kitap"
    assert ilk["parent_path"] == "k:test-kucuk:bolum-1"
    assert ilk["ayah_lo"] is None
    assert ilk["ayah_hi"] is None
    assert ilk["attrs"] == {}
    assert satirlar["k:test-kucuk:bolum-2:p1"]["parent_path"] == "k:test-kucuk:bolum-2"
    isik = satirlar["k:test-kucuk:bolum-1:p3"]
    assert "isik" in str(isik["tr_wide"]).split(" ")  # Maestro arama akisi `isik` yazar
    assert "ışık" in str(isik["tr_narrow"]).split(" ")
    assert isik["provenance"]["arama"] == {"normalizer_version": "1.0"}  # type: ignore[index]
    # anchor cikisi capa sirasinda
    capalar = [str(s["anchor"]) for s in units(veri, "test-kucuk", "anchor")]
    assert capalar == sorted(capalar, key=lambda c: sort_key(parse(c)))


def test_zincir_tefsir_ayet_araligi(veri: Path) -> None:
    zincir_kos("test-tefsir-ornek")
    satirlar = {str(s["anchor"]): s for s in units(veri, "test-tefsir-ornek", "anchor")}
    s = satirlar["tf:test-ornek:2-255-257:p1"]
    assert (s["kind"], s["ayah_lo"], s["ayah_hi"], s["parent_path"]) == ("tefsir", 262, 265, None)
    assert satirlar["tf:test-ornek:1-1-7:p1"]["ayah_lo"] == 1


def test_anchor_dry_run_ve_qa_kismi_kapi(veri: Path) -> None:
    zincir_kos("test-kucuk")
    assert len(calismalar(veri, "test-kucuk", "anchor")) == 1
    assert komut("anchor", "--source", "test-kucuk", "--dry-run").exit_code == 0
    assert len(calismalar(veri, "test-kucuk", "anchor")) == 1
    assert komut("qa", "run", "--source", "test-kucuk", "--gate", "G-KAY").exit_code == 0
    assert komut("qa", "run", "--source", "test-kucuk", "--gate", "G-XYZ").exit_code == 2


def test_qa_onceki_calisma_tabani(veri: Path) -> None:
    """Ikinci anchor calismasi: onceki (QA'dan gecmis) calismanin capalari G-CAP tabanidir."""
    zincir_kos("test-kucuk")
    assert komut("anchor", "--source", "test-kucuk", "--force").exit_code == 0
    sonuc = komut("qa", "run", "--source", "test-kucuk")
    assert sonuc.exit_code == 0, sonuc.stdout
    rapor = max(
        (json.loads(p.read_bytes()) for p in (veri / "reports").glob("*.json")),
        key=lambda r: r["run_id"],
    )
    ilk = calismalar(veri, "test-kucuk", "anchor")[0][0]
    assert rapor["onceki_anchor_run_id"] == ilk
    assert rapor["kapi_sayilari"]["G-CAP"]["onceki_run"] == 1
    assert rapor["kapi_sayilari"]["G-CAP"]["onceki_capa"] == 12


# --- kapi islevleri (bellekte bozulmus girdi) --------------------------------------------


def bellek_girdisi(slug: str) -> kapilar.FiksturGirdisi:
    """Zincirin iki ilk adimini bellekte kosar ve gecerli bir G-* girdisi kurar."""
    ingest = [
        Satir(
            "ingest",
            no,
            {
                "anchor": b.anchor,
                "source_id": slug,
                "text": b.text,
                "attrs": {
                    "kind": b.kind,
                    **({"parent_path": b.parent_path} if b.parent_path else {}),
                },
                "provenance": {"line": no},
            },
        )
        for no, b in enumerate(fikstur.birimler(slug), start=1)
    ]
    normalize = [
        Satir("normalize", no, d)
        for no, d in enumerate(adimlar.normalize_satirlari(slug, ingest), start=1)
    ]
    kayit = next(
        s.kaynak
        for s in sources.yukle(depo_koku())
        if s.kaynak is not None and s.kaynak.slug == slug
    )
    anchor = [
        Satir("anchor", no, d)
        for no, d in enumerate(adimlar.anchor_satirlari(slug, normalize, "1"), start=1)
    ]
    return kapilar.FiksturGirdisi(
        slug=slug,
        kayit=kayit,
        anchor_satirlari=anchor,
        beklenen=fikstur.birimler(slug),
        depo_kok=depo_koku(),
    )


def hepsi(g: kapilar.FiksturGirdisi) -> dict[str, list[str]]:
    return {k: list(f(g).bulgular) for k, f in kapilar.KAPI_ISLEVLERI.items()}


def test_kapilar_gecerli_girdide_temiz() -> None:
    for slug in SLUGLAR:
        assert hepsi(bellek_girdisi(slug)) == {k: [] for k in KAPILAR}


def test_g_kay_yanlis_kayit() -> None:
    g = bellek_girdisi("test-kucuk")
    yanlis = kapilar.FiksturGirdisi(
        **{**g.__dict__, "kayit": g.kayit.__class__(**{**g.kayit.__dict__, "atif_metni": "x"})}
    )
    bulgu = kapilar.g_kay(yanlis).bulgular
    assert len(bulgu) == 1
    assert "atif_metni" in bulgu[0]


def test_g_but_metin_degisimi_ve_nfc() -> None:
    g = bellek_girdisi("test-kucuk")
    satir = g.anchor_satirlari[0]
    satir.veri["text"] = unicodedata.normalize("NFD", str(satir.veri["text"]))
    bulgular = " | ".join(kapilar.g_but(g).bulgular)
    assert "bayt bayt ayni degil" in bulgular
    assert "kanonik" in bulgular
    # kontrol karakteri
    g2 = bellek_girdisi("test-kucuk")
    g2.anchor_satirlari[1].veri["text"] = str(g2.anchor_satirlari[1].veri["text"]) + "​"
    assert "kontrol" in " | ".join(kapilar.g_but(g2).bulgular)


def test_g_but_eksik_ve_isik_sayisi() -> None:
    g = bellek_girdisi("test-kucuk")
    g.anchor_satirlari = list(g.anchor_satirlari)[:-1]  # type: ignore[misc]
    bulgular = " | ".join(kapilar.g_but(g).bulgular)
    assert "birim sayisi 11" in bulgular
    assert "eksik birim" in bulgular
    g2 = bellek_girdisi("test-kucuk")
    g2.anchor_satirlari[0].veri["text"] = "Deneme paragrafı 1 Işık"
    assert "sayisi 2" in " | ".join(kapilar.g_but(g2).bulgular)


def test_g_cap_bozuk_alanlar() -> None:
    g = bellek_girdisi("test-tefsir-ornek")
    s = g.anchor_satirlari
    s[0].veri["ord"] = 9
    s[1].veri["ayah_hi"] = 99
    s[2].veri["content_hash"] = "0" * 64
    s[3].veri["metin_durumu"] = "onayli"
    s[4].veri["anchor"] = "tf:elmalili:1-1-7:p1"
    bulgular = " | ".join(kapilar.g_cap(g).bulgular)
    for parca in ("ord:", "ayah_lo/ayah_hi:", "content_hash:", "sabit alan:", "gecersiz capa:"):
        assert parca in bulgular, bulgular


def test_g_cap_onceki_surumden_kaybolan_capa() -> None:
    g = bellek_girdisi("test-kucuk")
    ozetler = {str(s.veri["anchor"]): str(s.veri["content_hash"]) for s in g.anchor_satirlari}
    ozetler["k:test-kucuk:bolum-9:p1"] = "a" * 64
    ozetler["k:test-kucuk:bolum-1:p1"] = "b" * 64
    g.onceki = Onceki("onceki", ozetler)
    bulgular = " | ".join(kapilar.g_cap(g).bulgular)
    assert "kaybolan capa: 1 birim" in bulgular
    assert "content_hash farkli: 1 birim" in bulgular


def test_g_nor_bozuk_anahtar() -> None:
    g = bellek_girdisi("test-kucuk")
    g.anchor_satirlari[0].veri["tr_wide"] = "yanlis"
    g.anchor_satirlari[1].veri["ar_norm"] = "x"
    g.anchor_satirlari[2].veri["provenance"] = {}
    bulgular = " | ".join(kapilar.g_nor(g).bulgular)
    assert "arama anahtari: 1 birim" in bulgular
    assert "ar_norm: 1 birim" in bulgular
    assert "provenance.arama: 1 birim" in bulgular


def test_hicbir_bulgu_metin_tasimaz() -> None:
    g = bellek_girdisi("test-kucuk")
    g.anchor_satirlari[0].veri["text"] = "Deneme paragrafı değişti"
    for kapi in kapilar.KAPI_ISLEVLERI.values():
        for bulgu in kapi(g).bulgular:
            assert bulgu.isascii()
            assert "Deneme" not in bulgu
