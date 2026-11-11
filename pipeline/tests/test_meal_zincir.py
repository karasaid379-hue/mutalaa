# ruff: noqa: RUF001
"""Meal zinciri: ingest -> normalize -> anchor -> qa (A16.2, A16.3; SENTETIK veri).

Zincir gercek komutlarla, `tmp_path` altindaki 6.236 ayetlik sentetik gelen klasorleriyle ve
sentetik kilitle kosar (`meal_yardimci`). Hicbir meal metni gercek degildir.
"""

import json
from pathlib import Path

import pytest
from meal_yardimci import (
    TARIH,
    MealKoku,
    baslik,
    ingest,
    komut,
    kopya_al,
    meal_kok_kur,
    sayfa_wikitext,
)

from mutalaa_pipeline import lineage
from mutalaa_pipeline.anchor import content_hash
from mutalaa_pipeline.anchor.ayet_sayilari import AYET_SAYILARI
from mutalaa_pipeline.ingest import meal_kilit
from mutalaa_pipeline.ingest.meal_kaynaklari import (
    KAYNAK_EPUB,
    KAYNAK_ORIJINAL,
    KAYNAK_SADE,
)
from mutalaa_pipeline.qa.checks import meal as kapilar_meal
from mutalaa_pipeline.qa.checks.tanzil import KapiSonucu
from mutalaa_pipeline.qa.rapor import QaRaporlari
from mutalaa_pipeline.runctx import QaKaldi

TOPLAM = sum(AYET_SAYILARI)


@pytest.fixture
def kok(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> MealKoku:
    return meal_kok_kur(tmp_path, monkeypatch)


def calismalar(veri: Path, slug: str, adim: str) -> list[tuple[str, Path, dict[str, object]]]:
    return [c for c in lineage.calismalar(veri / "staged" / slug) if c[2].get("adim") == adim]


def satirlar(veri: Path, slug: str, adim: str, ad: str = "units.jsonl") -> list[dict[str, object]]:
    klasor = calismalar(veri, slug, adim)[-1][1]
    return [json.loads(s) for s in (klasor / ad).read_bytes().decode("utf-8").splitlines()]


@pytest.fixture
def tam_zincir(meal_sablon: MealKoku, monkeypatch: pytest.MonkeyPatch) -> MealKoku:
    """Salt okunur sablon: testler yalniz okur (degistiren testler `kopya` kullanir)."""
    monkeypatch.setenv("MUTALAA_VERI_KOK", str(meal_sablon.veri))
    monkeypatch.setattr(meal_kilit, "KILIT_YOLU", meal_sablon.kilit_yolu)
    return meal_sablon


@pytest.fixture
def kopya(meal_sablon: MealKoku, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> MealKoku:
    """Sablonun yazilabilir kopyasi (staged, raw, reports, gelen)."""
    return kopya_al(meal_sablon, tmp_path, monkeypatch)


def birim(veri: Path, slug: str, sure: int, ayet: int, adim: str = "anchor") -> dict[str, object]:
    eser = "elmalili" if slug == KAYNAK_ORIJINAL else "elmalili-sade"
    hedef = f"meal:{eser}:{sure}:{ayet}"
    for s in satirlar(veri, slug, adim):
        if s["anchor"] == hedef:
            return s
    raise AssertionError(hedef)


# --- ingest: sayim, ham kopya, kilit ---------------------------------------------------------


def test_ingest_uc_kaynak_birimleri_ve_tanik_uretir(kok: MealKoku) -> None:
    assert ingest(KAYNAK_ORIJINAL).exit_code == 0
    assert ingest(KAYNAK_SADE).exit_code == 0
    sonuc = ingest(KAYNAK_EPUB)
    assert sonuc.exit_code == 0, sonuc.stderr
    assert len(satirlar(kok.veri, KAYNAK_ORIJINAL, "ingest")) == TOPLAM
    assert len(satirlar(kok.veri, KAYNAK_SADE, "ingest")) == TOPLAM
    tanik = satirlar(kok.veri, KAYNAK_EPUB, "ingest", lineage.TANIK_ADI)
    assert tanik
    assert not (calismalar(kok.veri, KAYNAK_EPUB, "ingest")[-1][1] / "units.jsonl").exists()
    # ham kopya: kilitli dosyalar ve fetch.json, data/raw altinda
    ham = kok.veri / "raw" / KAYNAK_ORIJINAL / TARIH
    assert sorted(p.name for p in ham.iterdir()) == [
        "basliklar.tsv",
        "fetch.json",
        "vikikaynak-01.json",
        "vikikaynak-02.json",
        "vikikaynak-03.json",
    ]


def test_ingest_dry_run_raw_ve_staged_yazmaz(kok: MealKoku) -> None:
    sonuc = ingest(KAYNAK_ORIJINAL, "--dry-run")
    assert sonuc.exit_code == 0, sonuc.stderr
    assert not (kok.veri / "raw").exists()
    assert not (kok.veri / "staged").exists()


def test_force_iki_kosu_ayni_staged_baytlarini_uretir(kok: MealKoku) -> None:
    for slug in (KAYNAK_ORIJINAL, KAYNAK_SADE):
        assert ingest(slug).exit_code == 0
        assert ingest(slug, "--force").exit_code == 0
        ilk, ikinci = calismalar(kok.veri, slug, "ingest")[-2:]
        assert ilk[0] != ikinci[0]
        assert (ilk[1] / "units.jsonl").read_bytes() == (ikinci[1] / "units.jsonl").read_bytes()
    assert ingest(KAYNAK_EPUB).exit_code == 0
    assert ingest(KAYNAK_EPUB, "--force").exit_code == 0
    a, b = calismalar(kok.veri, KAYNAK_EPUB, "ingest")[-2:]
    assert (a[1] / "tanik.jsonl").read_bytes() == (b[1] / "tanik.jsonl").read_bytes()
    # ham klasor yeniden kullanildi: ikinci kosu yeni klasor acmadi
    assert [p.name for p in (kok.veri / "raw" / KAYNAK_ORIJINAL).iterdir()] == [TARIH]


def test_ingest_limit_cikis_2(kok: MealKoku) -> None:
    for slug in (KAYNAK_ORIJINAL, KAYNAK_SADE, KAYNAK_EPUB):
        assert ingest(slug, "--limit", "10").exit_code == 2
    assert not (kok.veri / "raw").exists()


def test_bilinmeyen_kaynak_cikis_2(kok: MealKoku) -> None:
    assert ingest("tanzil-uthmani").exit_code == 2
    assert komut("normalize", "--source", KAYNAK_EPUB).exit_code == 2  # tanik normalize edilmez


def test_kilit_uyusmazligi_cikis_2_ve_raw_yazilmaz(kok: MealKoku) -> None:
    dosya = kok.veri / "gelen" / KAYNAK_ORIJINAL / TARIH / "vikikaynak-02.json"
    dosya.write_bytes(dosya.read_bytes() + b" ")
    sonuc = ingest(KAYNAK_ORIJINAL)
    assert sonuc.exit_code == 2
    assert "kilit guncellenerek (/karar)" in sonuc.stderr
    assert not (kok.veri / "raw").exists()
    # sade ve tanik icin de ayni
    sade = kok.veri / "gelen" / KAYNAK_SADE / TARIH / "tur-elmallsadelesti.json"
    sade.write_bytes(sade.read_bytes() + b" ")
    assert ingest(KAYNAK_SADE).exit_code == 2
    epub = kok.veri / "gelen" / KAYNAK_EPUB / TARIH / "meal-i-serif.epub"
    epub.write_bytes(epub.read_bytes() + b"x")
    assert ingest(KAYNAK_EPUB).exit_code == 2


def _ozel_kok(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, sure: int, wikitext: str
) -> MealKoku:
    return meal_kok_kur(tmp_path, monkeypatch, ozel_wikitext={sure: wikitext})


@pytest.mark.parametrize(
    ("neden", "degisim"),
    [
        ("bilinmeyen sablon", lambda w: w.replace("{{kısım||3}}", "{{Bilinmeyen|x}}{{kısım||3}}")),
        ("bozuk wikitext", lambda w: w.replace("{{kısım||3}}", "{{kısım||3}}{{ acik ")),
        ("bilinmeyen etiket", lambda w: w.replace("{{kısım||3}}", "{{kısım||3}}<span>x</span>")),
        ("eksik ayet", lambda w: w.replace("{{kısım||3}}", "{{kısım||99}}")),
    ],
)
def test_bozuk_sayfa_cikis_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, neden: str, degisim: object
) -> None:
    """Kilit sayfanin yeni baytlariyla guncel olsa bile cikarim bozuk sayfada 2 ile durur."""
    wt = degisim(sayfa_wikitext(11))  # type: ignore[operator]
    kok = _ozel_kok(tmp_path, monkeypatch, 11, wt)
    sonuc = ingest(KAYNAK_ORIJINAL)
    assert sonuc.exit_code == 2, neden
    assert "sure 11" in sonuc.stderr
    assert not calismalar(kok.veri, KAYNAK_ORIJINAL, "ingest")


# --- sinir kurallari (uctan uca): her biri ayri sinanir ---------------------------------------


def test_sarmalayici_ve_basliklar(tam_zincir: MealKoku) -> None:
    b = birim(tam_zincir.veri, KAYNAK_ORIJINAL, 2, 1)
    assert b["text"] == "Deneme meal parçası 2-1"


def test_aralikli_isaret_birlesik_bas_ve_izleyen(tam_zincir: MealKoku) -> None:
    veri = tam_zincir.veri
    bas = birim(veri, KAYNAK_ORIJINAL, 3, 10)
    izleyen = birim(veri, KAYNAK_ORIJINAL, 3, 11)
    assert bas["text"] == "Deneme birleşik parça 3-10-11"
    assert bas["attrs"] == {"kapsam": "q:3:10-11"}
    assert izleyen["text"] == ""
    assert izleyen["attrs"] == {"birlesik_ile": "meal:elmalili:3:10"}
    assert content_hash("") == izleyen["content_hash"]
    # ayah_range bas birimde kapsami orter; izleyen kendi ayetini gosterir
    assert (bas["ayah_hi"], bas["ayah_lo"]) == (int(bas["ayah_lo"]) + 2, bas["ayah_lo"])  # type: ignore[call-overload]
    assert izleyen["ayah_hi"] == int(izleyen["ayah_lo"]) + 1  # type: ignore[call-overload]
    assert izleyen["ord"] == int(bas["ord"]) + 1  # type: ignore[call-overload]


def test_ardisik_isaretler_birlesik(tam_zincir: MealKoku) -> None:
    bas = birim(tam_zincir.veri, KAYNAK_ORIJINAL, 4, 20)
    assert bas["attrs"] == {"kapsam": "q:4:20-21"}
    assert bas["text"] == "Deneme birleşik parça 4-20-21"
    assert birim(tam_zincir.veri, KAYNAK_ORIJINAL, 4, 21)["attrs"] == {
        "birlesik_ile": "meal:elmalili:4:20"
    }


def test_ardisik_olmayan_isaretler_ortak_metin(tam_zincir: MealKoku) -> None:
    a = birim(tam_zincir.veri, KAYNAK_ORIJINAL, 5, 30)
    b = birim(tam_zincir.veri, KAYNAK_ORIJINAL, 5, 40)
    assert a["text"] == b["text"] == "Deneme ortak parça 5"
    assert a["attrs"] == b["attrs"] == {}
    assert "ortak_metin" in a["provenance"]["uyari"]  # type: ignore[index]
    assert "ortak_metin" in b["provenance"]["uyari"]  # type: ignore[index]


def test_numarasiz_parca_onceki_ayete_tek_bosluk(tam_zincir: MealKoku) -> None:
    b = birim(tam_zincir.veri, KAYNAK_ORIJINAL, 6, 5)
    assert b["text"] == "Deneme meal parçası 6-5 Deneme numarasız ek parça"
    assert b["provenance"]["uyari"] == ["numarasiz_parca"]  # type: ignore[index]
    assert len(b["provenance"]["konum"]["araliklar"]) == 2  # type: ignore[index]


def test_yinelenen_numara_sirayla_birlestirilir(tam_zincir: MealKoku) -> None:
    b = birim(tam_zincir.veri, KAYNAK_ORIJINAL, 7, 12)
    assert b["text"] == "Deneme meal parçası 7-12 a Deneme meal parçası 7-12 b"
    assert b["provenance"]["uyari"] == ["yinelenen_numara"]  # type: ignore[index]


def test_sayfa_sonu_ve_basi_bolgeleri_metne_girmez_manifestte_gorunur(tam_zincir: MealKoku) -> None:
    son = birim(tam_zincir.veri, KAYNAK_ORIJINAL, 8, AYET_SAYILARI[7])
    assert "</div>" not in str(son["text"])
    manifest = calismalar(tam_zincir.veri, KAYNAK_ORIJINAL, "ingest")[-1][2]
    bolgeler = manifest["ayrintilar"]["bolgeler"]  # type: ignore[index]
    assert {b["sure"] for b in bolgeler} == {8, 10}
    for b in bolgeler:  # yalniz uzunluk ve ozet; metin yok
        for taraf in ("on", "son"):
            if b[taraf] is not None:
                assert set(b[taraf]) == {"uzunluk", "sha256"}
    assert "sayfa başı notu" not in json.dumps(manifest, ensure_ascii=False)


def test_provenance_konum_ve_surumleri_tasir(tam_zincir: MealKoku) -> None:
    b = birim(tam_zincir.veri, KAYNAK_ORIJINAL, 5, 1)
    p = b["provenance"]
    assert set(p) >= {"file", "sha256", "sayfa", "revid", "wikitext_sha256", "konum", "cikarici"}  # type: ignore[arg-type]
    assert set(p["cikarici"]) == {"surum", "mwparserfromhell", "unidata"}  # type: ignore[index]
    ((bas, son),) = p["konum"]["araliklar"]  # type: ignore[index]
    wt = tam_zincir.wikitextler[5]
    assert wt[bas:son].strip(" \n") == "Deneme meal parçası 5-1"  # yari acik kod noktasi araligi
    assert p["konum"]["ayirici"] == " "  # type: ignore[index]
    s = birim(tam_zincir.veri, KAYNAK_SADE, 5, 1)
    assert s["provenance"]["konum"] == {"json_yolu": f"quran[{sum(AYET_SAYILARI[:4])}]"}  # type: ignore[index]


def test_konum_sarmalayici_icinde_de_dogrudur(tam_zincir: MealKoku) -> None:
    b = birim(tam_zincir.veri, KAYNAK_ORIJINAL, 2, 3)
    ((bas, son),) = b["provenance"]["konum"]["araliklar"]  # type: ignore[index]
    assert tam_zincir.wikitextler[2][bas:son].strip(" \n") == "Deneme meal parçası 2-3"


# --- normalize ve anchor ---------------------------------------------------------------------


def test_anchor_alanlari_ve_taslak(tam_zincir: MealKoku) -> None:
    for slug, eser in ((KAYNAK_ORIJINAL, "elmalili"), (KAYNAK_SADE, "elmalili-sade")):
        sat = satirlar(tam_zincir.veri, slug, "anchor")
        assert len(sat) == TOPLAM
        assert [s["ord"] for s in sat] == list(range(1, TOPLAM + 1))
        assert {s["kind"] for s in sat} == {"meal"}
        assert {s["metin_durumu"] for s in sat} == {"taslak"}
        assert {s["ar_norm"] for s in sat} == {None}
        assert sat[0]["anchor"] == f"meal:{eser}:1:1"
        assert str(sat[0]["data_version"]).startswith(f"{slug}@")
        assert sat[0]["tr_narrow"] and sat[0]["tr_stem"]
        assert all(s["content_hash"] == content_hash(str(s["text"])) for s in sat)
    # tanik yalniz orijinalde
    assert all(s["tanik"] is None for s in satirlar(tam_zincir.veri, KAYNAK_SADE, "anchor"))


def test_tanik_skoru_kapsam_ve_yontem(tam_zincir: MealKoku) -> None:
    b = birim(tam_zincir.veri, KAYNAK_ORIJINAL, 5, 1)
    t = b["tanik"]
    assert isinstance(t, dict)
    assert t["yontem"] == "rapidfuzz.fuzz.ratio/tr_narrow"
    assert t["yontem_surumu"] == "1"
    assert type(t["skor"]) is int
    assert 0 <= t["skor"] <= 100
    assert t["kaynak"] == KAYNAK_EPUB
    # numara boslugu: sure 12 ayet 3 ve 4 tek tanik parcasinin kapsami
    a3 = birim(tam_zincir.veri, KAYNAK_ORIJINAL, 12, 3)["tanik"]
    a4 = birim(tam_zincir.veri, KAYNAK_ORIJINAL, 12, 4)["tanik"]
    assert a3 is not None and a3 == a4  # type: ignore[comparison-overlap]
    assert a3["kapsam"] == [3, 4]  # type: ignore[index]
    # birlesik izleyen birim kendi bos metniyle degil kumenin metniyle puanlanir
    izleyen = birim(tam_zincir.veri, KAYNAK_ORIJINAL, 3, 11)["tanik"]
    bas = birim(tam_zincir.veri, KAYNAK_ORIJINAL, 3, 10)["tanik"]
    assert izleyen == bas


def test_tanik_yinelenen_isaret_birlestirilir(tam_zincir: MealKoku) -> None:
    sat = satirlar(tam_zincir.veri, KAYNAK_EPUB, "ingest", lineage.TANIK_ADI)
    parca = [s for s in sat if s["sure"] == 13 and s["ayet"] == 4]
    assert len(parca) == 1
    assert "yinelenen parça" in str(parca[0]["metin"])


def test_anchor_tanik_olmadan_orijinalde_2(kok: MealKoku) -> None:
    assert ingest(KAYNAK_ORIJINAL).exit_code == 0
    assert komut("normalize", "--source", KAYNAK_ORIJINAL).exit_code == 0
    sonuc = komut("anchor", "--source", KAYNAK_ORIJINAL)
    assert sonuc.exit_code == 2
    assert "ingest meal --source elmalili-meal-epub" in sonuc.stderr


def test_atlama_ayni_girdide_ve_force(kopya: MealKoku) -> None:
    once = len(calismalar(kopya.veri, KAYNAK_SADE, "normalize"))
    assert komut("normalize", "--source", KAYNAK_SADE, "--force").exit_code == 0
    assert len(calismalar(kopya.veri, KAYNAK_SADE, "normalize")) == once + 1


# --- qa: bes kapi ----------------------------------------------------------------------------


def test_qa_bes_kapi_gecer_ve_rapor_kabul_edilir(tam_zincir: MealKoku) -> None:
    for slug in (KAYNAK_ORIJINAL, KAYNAK_SADE):
        anchor = calismalar(tam_zincir.veri, slug, "anchor")[-1]
        rapor = [
            json.loads(p.read_bytes())
            for p in sorted((tam_zincir.veri / "reports").glob("*.json"))
            if json.loads(p.read_bytes()).get("komut") == "qa run"
            and json.loads(p.read_bytes()).get("kaynak") == slug
        ][-1]
        assert rapor["kapilar"] == dict.fromkeys(
            ("G-KAY", "G-BUT", "G-CAP", "G-NOR", "G-HIZ"), "gecti"
        )
        assert rapor["anchor_run_id"] == anchor[0]
        ozet = lineage.sha256_dosya(anchor[1] / "units.jsonl")
        assert QaRaporlari(tam_zincir.veri).onayli_mi(slug, anchor[0], ozet)
        assert rapor["kapi_sayilari"]["G-HIZ"]["eksik"] == 0


def test_qa_meal_raporlari_dosyasi_metin_icermez(tam_zincir: MealKoku) -> None:
    dosyalar = sorted((tam_zincir.veri / "reports").glob("*-meal-raporlari.json"))
    assert len(dosyalar) == 2
    icerik = "\n".join(d.read_text(encoding="utf-8") for d in dosyalar)
    for yasak in ("Deneme", "meal parça", "sade parça"):
        assert yasak not in icerik
    orijinal = next(
        r for r in (json.loads(d.read_bytes()) for d in dosyalar) if r["kaynak"] == KAYNAK_ORIJINAL
    )
    assert orijinal["kapsam"]["birim"] == TOPLAM
    assert orijinal["capraz_tanik"]["tanikli_birim"] == TOPLAM
    assert orijinal["sadelestirme_taramasi"]["taranan_parca"] > 0


def test_qa_kismi_kosu_karari_degistirmez_bilinmeyen_kapi_2(kopya: MealKoku) -> None:
    anchor = calismalar(kopya.veri, KAYNAK_SADE, "anchor")[-1]
    ozet = lineage.sha256_dosya(anchor[1] / "units.jsonl")
    sonuc = komut("qa", "run", "--source", KAYNAK_SADE, "--gate", "G-HIZ")
    assert sonuc.exit_code == 0, sonuc.stderr
    # basarili kismi kosu daha eski tam raporun kabulunu degistirmez
    assert QaRaporlari(kopya.veri).onayli_mi(KAYNAK_SADE, anchor[0], ozet)
    assert komut("qa", "run", "--source", KAYNAK_SADE, "--gate", "G-MET").exit_code == 2


def test_qa_tanik_kaynagi_2(tam_zincir: MealKoku) -> None:
    assert komut("qa", "run", "--source", KAYNAK_EPUB).exit_code == 2


def test_qa_hiz_kalinca_cikis_1_ve_export_icin_kabul_edilmez(
    kopya: MealKoku, monkeypatch: pytest.MonkeyPatch
) -> None:
    """G-HIZ sert kapidir: kalirsa `qa run` 1 verir ve rapor export pg'ye yetmez."""
    kalan = KapiSonucu("G-HIZ", ("eksik ayet: 1 birim",), {"eksik": 1})
    monkeypatch.setitem(kapilar_meal.KAPI_ISLEVLERI, "G-HIZ", lambda g: kalan)
    sonuc = komut("qa", "run", "--source", KAYNAK_SADE)
    assert sonuc.exit_code == 1
    assert "G-HIZ kaldi" in sonuc.stdout
    anchor = calismalar(kopya.veri, KAYNAK_SADE, "anchor")[-1]
    ozet = lineage.sha256_dosya(anchor[1] / "units.jsonl")
    with pytest.raises(QaKaldi, match="G-HIZ"):
        QaRaporlari(kopya.veri).onayla(KAYNAK_SADE, anchor[0], ozet)


def test_qa_bozuk_zincir_cikis_2(kopya: MealKoku) -> None:
    """Staged anchor ciktisi manifestle tutmazsa zincir bozuktur: cikis 2 (girdi hatasi)."""
    klasor = calismalar(kopya.veri, KAYNAK_SADE, "anchor")[-1][1]
    satir = (klasor / "units.jsonl").read_bytes().split(b"\n")
    (klasor / "units.jsonl").write_bytes(b"\n".join(satir[1:]))
    assert komut("qa", "run", "--source", KAYNAK_SADE).exit_code == 2


def test_baslik_yardimcisi() -> None:
    assert baslik(5) == "Kur'an/Deneme 005 Suresi"
