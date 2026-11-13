"""`enrich tr-roots` adimi ve `qa run --source kaikki-tr` (A18.2): SENTETIK zincir.

`tr_yardimci.dunya_kur` sahte kaynak kayitlari, iki meal ve QAC `anchor` calismalari, iki kaikki
dokumu ve `SHA256SUMS` kurar; lemmatizer sahtedir (zeyrek gerekmez). Hicbir Kur'an, meal ya da
sozluk metni yoktur.
"""

import json
from pathlib import Path

import pytest
from tr_yardimci import (
    KAIKKI,
    MEAL_O,
    MEAL_S,
    TARIH,
    TrDunya,
    dunya_kur,
)

from mutalaa_pipeline import lineage
from mutalaa_pipeline.adimlar.enrich_tr_roots import run_enrich_tr_roots
from mutalaa_pipeline.qa.checks.tr_roots import KAPI_ISLEVLERI, TrRootsGirdisi
from mutalaa_pipeline.qa.run_tr_roots import yukle
from mutalaa_pipeline.sources.kayit import Kaynak


@pytest.fixture
def d(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TrDunya:
    return dunya_kur(tmp_path, monkeypatch)


def lemmalar(d: TrDunya) -> dict[str, dict[str, object]]:
    return {str(s["lemma"]): s for s in d.satirlar("tr_lemmas.jsonl")}


def formlar(d: TrDunya) -> dict[str, dict[str, object]]:
    return {str(s["form"]): s for s in d.satirlar("tr_forms.jsonl")}


def test_adim_staged_satirlari_ve_siniflar(d: TrDunya) -> None:
    assert d.enrich() == 0
    f = formlar(d)
    karar = {ad: (s["karar"], s["neden"]) for ad, s in f.items()}
    assert karar == {
        "tavan": ("onayli_otomatik", "kosullar_saglandi"),
        "dolap": ("onayli_otomatik", "kosullar_saglandi"),
        "emin": ("onayli_otomatik", "kosullar_saglandi"),
        "pelin": ("onayli_otomatik", "kosullar_saglandi"),
        "kalem": ("aday", "pos_uyusmazligi"),
        "bobin": ("aday", "homograf_madde_celisiyor"),
        "zorba": ("aday", "kok_cakismasi"),
        "morta": ("aday", "cok_adayli_qac"),
        "kelin": ("aday", "tr_ota_kok_cakismasi"),
        "fisto": ("aday", "yalniz_serbest_metin"),
        "okur": ("aday", "belirsiz_lemma"),
        "ve": ("kok_yok", "kapali_sinif"),
        "oldu": ("kok_yok", "kapali_sinif"),
        "yokluk": ("kok_yok", "bilinmeyen_sozcuk"),
        "deneme": ("kok_yok", "bilinmeyen_sozcuk"),
    }
    # iki mealin sayilari birlesir; sade mealdeki `Tavan'in` ek ayrilarak `tavan` sayilir
    assert f["tavan"]["freq"] == 3 and f["tavan"]["freq_kaynak"] == {MEAL_O: 2, MEAL_S: 1}
    assert f["kalem"]["freq"] == 3 and f["emin"]["freq"] == 2
    assert f["okur"]["lemma"] is None and f["tavan"]["lemma"] == "tavan"


def test_lemma_satirlari_kanit_kok_ve_siklik(d: TrDunya) -> None:
    assert d.enrich(min_sik=2) == 0
    lm = lemmalar(d)
    assert set(lm) == {
        "tavan",
        "dolap",
        "emin",
        "pelin",
        "kalem",
        "bobin",
        "zorba",
        "morta",
        "kelin",
        "fisto",
    }
    onayli = {a for a, s in lm.items() if s["karar"] == "onayli_otomatik"}
    assert onayli == {"tavan", "dolap", "emin", "pelin"}
    for ad in onayli:
        k = lm[ad]["kanit"]
        assert isinstance(k, dict) and k["politika_surumu"] == "1" and k["kaynaklar"]
        assert lm[ad]["root_letters_bw"] is not None
    assert lm["dolap"]["ar_lemma_qac_ref"] == "samal" and lm["tavan"]["ar_lemma_qac_ref"] is None
    assert lm["tavan"]["freq"] == 3
    # kok onerisi olan aday: kalem (siklik 3 >= 2), bobin (siklik 1 < 2: esik alti)
    assert lm["kalem"]["review_onerilir"] is True and lm["bobin"]["review_onerilir"] is False
    assert lm["kalem"]["root_letters_bw"] == "bnr" and lm["zorba"]["root_letters_bw"] is None
    assert {s["source_id"] for s in lm.values()} == {KAIKKI}


def test_min_freq_esigi_review_onerisini_belirler(d: TrDunya) -> None:
    assert d.enrich(min_sik=4) == 0
    assert not any(s["review_onerilir"] for s in lemmalar(d).values())


def test_ayni_girdi_ayni_baytlar_ve_manifest(d: TrDunya) -> None:
    assert d.enrich() == 0
    birinci = d.son_calisma(KAIKKI, "enrich")
    assert d.enrich(force=True) == 0
    ikinci = d.son_calisma(KAIKKI, "enrich")
    assert birinci != ikinci
    for ad in ("tr_lemmas.jsonl", "tr_forms.jsonl"):
        assert (birinci / ad).read_bytes() == (ikinci / ad).read_bytes()
    m = lineage.manifest_oku(ikinci)
    assert m is not None and m["adim"] == "enrich" and m["komut"] == "enrich tr-roots"
    ayrinti = m["ayrintilar"]
    assert isinstance(ayrinti, dict)
    assert ayrinti["mealler"] == [MEAL_O, MEAL_S] and ayrinti["min_siklik"] == 2
    assert ayrinti["sayilar"]["token"] == 24 and ayrinti["sayilar"]["tr_lemma"] == 10  # type: ignore[index]
    yollar = {g["yol"].rsplit("/", 1)[-1] for g in m["girdiler"]}  # type: ignore[index, union-attr]
    assert {"units.jsonl", "roots.jsonl", "lemmas.jsonl"} <= yollar
    assert any(y.startswith("kaikki.org-dictionary-") for y in yollar)
    dosya = d.veri / "reports"
    yan = [json.loads(p.read_bytes()) for p in dosya.glob("*-tr-roots.json")]
    assert len(yan) == 2 and yan[0]["istatistik"]["siniflar"]["onayli_otomatik"]["tur"] == 4


def test_satirlar_sirali_ve_zaman_damgasiz(d: TrDunya) -> None:
    assert d.enrich() == 0
    ham = (d.son_calisma(KAIKKI, "enrich") / "tr_forms.jsonl").read_bytes()
    assert b"\r" not in ham and ham.endswith(b"\n") and ham.isascii()
    anahtarlar = [s["form"] for s in d.satirlar("tr_forms.jsonl")]
    assert anahtarlar == sorted(anahtarlar)


def test_dry_run_hicbir_sey_yazmaz(d: TrDunya) -> None:
    assert d.enrich(dry_run=True) == 0
    assert not (d.veri / "staged" / KAIKKI).exists()
    assert not list((d.veri / "reports").glob("*-tr-roots.json"))


def test_tek_meal_da_calisir_ve_kaynak_listesi_denetlenir(d: TrDunya) -> None:
    assert d.enrich(kaynaklar=[MEAL_S]) == 0
    assert d.manifest()["ayrintilar"]["mealler"] == [MEAL_S]  # type: ignore[index]
    assert d.enrich(kaynaklar=["elmalili-meal-epub"]) == 2
    assert d.enrich(kaynaklar=[]) == 2


def test_min_freq_sifir_girdi_hatasi(d: TrDunya) -> None:
    assert d.enrich(min_sik=0) == 2


def test_kaikki_ozeti_tutmazsa_cikis_2(d: TrDunya) -> None:
    yol = d.veri / "gelen" / "kaikki-tr" / TARIH / "kaikki.org-dictionary-OttomanTurkish.jsonl"
    yol.write_bytes(yol.read_bytes() + b"\n")
    assert d.enrich() == 2
    assert not (d.veri / "staged" / KAIKKI).exists()


def test_kaikki_klasoru_ya_da_dosyasi_yoksa_cikis_2(d: TrDunya) -> None:
    assert d.enrich(tarih="2020-01-01") == 2
    assert d.enrich(tarih="bozuk") == 2
    (d.veri / "gelen" / "kaikki-tr" / TARIH / "SHA256SUMS").unlink()
    assert d.enrich() == 2


def test_kayitsiz_kaynak_cikis_2(d: TrDunya) -> None:
    (d.kok / "pipeline" / "sources" / f"{KAIKKI}.toml").unlink()
    assert d.enrich() == 2


def test_meal_calismasi_yoksa_cikis_2(d: TrDunya) -> None:
    import shutil

    shutil.rmtree(d.veri / "staged" / MEAL_S)
    assert d.enrich() == 2


# --- QA kapilari -----------------------------------------------------------------------------


def test_qa_uc_kapi_gecer_ve_rapor_enrich_calismasina_baglanir(d: TrDunya) -> None:
    assert d.enrich() == 0
    assert d.qa() == 0
    run_id = d.son_calisma(KAIKKI, "enrich").name
    raporlar = [json.loads(p.read_bytes()) for p in (d.veri / "reports").glob("*.json")]
    qa = [r for r in raporlar if r.get("komut") == "qa run"]
    assert len(qa) == 1
    assert qa[0]["kaynak"] == KAIKKI and qa[0]["anchor_run_id"] == run_id
    assert qa[0]["kapilar"] == {"G-KAY": "gecti", "G-BUT": "gecti", "G-CAP": "gecti"}
    ciktilar = d.manifest()["ciktilar"]
    assert isinstance(ciktilar, list)
    lemma_ozeti = next(c["sha256"] for c in ciktilar if c["yol"].endswith("tr_lemmas.jsonl"))
    assert qa[0]["units_sha256"] == lemma_ozeti


def test_qa_kismi_kapi_ve_bilinmeyen_kapi(d: TrDunya) -> None:
    assert d.enrich() == 0
    assert d.qa(gate=["G-CAP"]) == 0
    assert d.qa(gate=["G-NOR"]) == 2


def test_qa_enrich_calismasi_yoksa_cikis_2(d: TrDunya) -> None:
    assert d.qa() == 2


def _girdi(d: TrDunya) -> TrRootsGirdisi:
    ctx = d.ctx("qa", [KAIKKI])
    kayitlar: dict[str, Kaynak] = ctx.require_sources((KAIKKI, "qac-morfoloji"))
    girdi, _, _ = yukle(ctx, kayitlar, run=None)
    return girdi


def test_g_kay_dokum_ozeti_ya_da_surum_tutmazsa_kalir(d: TrDunya) -> None:
    assert d.enrich() == 0
    girdi = _girdi(d)
    assert KAPI_ISLEVLERI["G-KAY"](girdi).gecti
    ad = next(iter(girdi.kayitli_ozetler))
    girdi.kayitli_ozetler = {**girdi.kayitli_ozetler, ad: "0" * 64}
    assert not KAPI_ISLEVLERI["G-KAY"](girdi).gecti
    girdi = _girdi(d)
    girdi.manifest_surum = "baska"
    assert not KAPI_ISLEVLERI["G-KAY"](girdi).gecti


def test_g_but_otomatik_onayli_lemmada_gecersiz_kanit_kalir(d: TrDunya) -> None:
    assert d.enrich() == 0
    girdi = _girdi(d)
    assert KAPI_ISLEVLERI["G-BUT"](girdi).gecti
    onayli = next(s for s in girdi.lemma_satirlari if s.veri["karar"] == "onayli_otomatik")
    onayli.veri["kanit"] = {**onayli.nesne("kanit"), "kaynaklar": []}
    sonuc = KAPI_ISLEVLERI["G-BUT"](girdi)
    assert not sonuc.gecti and any("kanit_kaynak_yok" in b for b in sonuc.bulgular)


def test_g_but_freq_toplami_manifestle_tutmazsa_kalir(d: TrDunya) -> None:
    assert d.enrich() == 0
    girdi = _girdi(d)
    girdi.manifest_token = (girdi.manifest_token or 0) + 1
    assert not KAPI_ISLEVLERI["G-BUT"](girdi).gecti


def test_g_cap_qac_kumesi_disindaki_kok_ve_lemma_kalir(d: TrDunya) -> None:
    assert d.enrich() == 0
    girdi = _girdi(d)
    assert KAPI_ISLEVLERI["G-CAP"](girdi).gecti
    dolap = next(s for s in girdi.lemma_satirlari if s.veri["lemma"] == "dolap")
    dolap.veri["ar_lemma_qac_ref"] = "yok-boyle-lemma"
    tavan = next(s for s in girdi.lemma_satirlari if s.veri["lemma"] == "tavan")
    tavan.veri["root_letters_bw"] = "zzz"
    sonuc = KAPI_ISLEVLERI["G-CAP"](girdi)
    assert not sonuc.gecti and len(sonuc.bulgular) >= 2


def test_g_cap_yinelenen_text_clean_kalir(d: TrDunya) -> None:
    assert d.enrich() == 0
    girdi = _girdi(d)
    girdi.lemma_satirlari[1].veri["text_clean"] = girdi.lemma_satirlari[0].veri["text_clean"]
    assert not KAPI_ISLEVLERI["G-CAP"](girdi).gecti


def test_adim_atlama_parmak_izi_ayni_girdide(d: TrDunya) -> None:
    """Ayni girdi ve temiz calisma agacinda ikinci kosu atlanir; `--force` atlamaz."""
    kaynaklar = [KAIKKI, "qac-morfoloji", MEAL_O, MEAL_S]
    ctx1 = d.ctx("enrich", kaynaklar)
    ilk = run_enrich_tr_roots(ctx1, [MEAL_O, MEAL_S], lemmatizer_kur=lambda: d.lemmatizer)
    assert ilk.atlandi is False
    ctx2 = d.ctx("enrich", kaynaklar)
    ikinci = run_enrich_tr_roots(ctx2, [MEAL_O, MEAL_S], lemmatizer_kur=lambda: d.lemmatizer)
    assert ikinci.atlandi is True and ikinci.onceki_run_id == ctx1.run_id
    ctx3 = d.ctx("enrich", kaynaklar)
    ctx3.force = True
    ucuncu = run_enrich_tr_roots(ctx3, [MEAL_O, MEAL_S], lemmatizer_kur=lambda: d.lemmatizer)
    assert ucuncu.atlandi is False


def test_kok_yok_lemmalar_da_staged_satiri_tasir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Kok adayi olmayan lemma satiri (yukleme satir acmaz) onayin geri alinma nedenini tasir."""
    d = dunya_kur(
        tmp_path,
        monkeypatch,
        mealler={MEAL_O: [("meal:elmalili:1:1", "Yalin yalin.")]},
        lemmatizer_tablosu={"yalin": [("yalin", "Noun")]},
        tr_satirlari=[
            {"word": "yalin", "lang_code": "tr", "pos": "noun", "etymology_templates": []}
        ],
        ota_satirlari=[],
    )
    assert d.enrich(kaynaklar=[MEAL_O]) == 0
    satirlar = d.satirlar("tr_lemmas.jsonl")
    assert [(s["lemma"], s["karar"], s["neden"], s["freq"]) for s in satirlar] == [
        ("yalin", "kok_yok", "kanit_yok", 2)
    ]
    assert satirlar[0]["root_letters_bw"] is None and satirlar[0]["kanit"]["kaynaklar"] == []  # type: ignore[index]
    assert d.qa() == 0


def test_kok_onerisiz_aday_da_review_onerilir_esige_gore(d: TrDunya) -> None:
    """K-51 madde 9: kok onerisi olmayan adaylar da editor kuyruguna gider (esik: --min-freq)."""
    assert d.enrich(min_sik=1) == 0
    lm = lemmalar(d)
    for ad in ("zorba", "morta", "kelin", "fisto"):
        assert lm[ad]["karar"] == "aday" and lm[ad]["root_letters_bw"] is None
        assert lm[ad]["review_onerilir"] is True
    assert lm["tavan"]["review_onerilir"] is False  # onayli otomatik: review gerekmez
    assert d.enrich(min_sik=2, force=True) == 0
    lm = lemmalar(d)
    assert not any(lm[a]["review_onerilir"] for a in ("zorba", "morta", "kelin", "fisto"))
