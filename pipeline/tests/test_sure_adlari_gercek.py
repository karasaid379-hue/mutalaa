"""Sure adi adaylari gercek veriyle (A11.3): Vikipedi, yonlendirmeler, quran-meta, Tanzil ust veri.

Veri yoksa atlanir (CI'da `data/` yoktur; `MUTALAA_DEGISMEZLIK_ZORUNLU=1` atlamayi hataya cevirir).
Dosyalar `sure_adlari.lock.json` ile dogrulanarak yalniz VERI olarak okunur. Testler sure adi ya da
sayi ezberlemez: beklentiler dosyalardan ve yapisal kurallardan turetilir; hata iletileri yalniz
sure numarasi ve sayi tasir.
"""

import json
import os
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from mutalaa_pipeline.adimlar.sure_adlari_adaylar import (
    adaylari_uret,
    alias_anahtari,
    capraz_sure_cakismalari,
    riskli_adlari_oku,
    riskli_eslesme,
    tanzil_farki,
)
from mutalaa_pipeline.config import Ayarlar
from mutalaa_pipeline.ingest import sure_adlari as s
from mutalaa_pipeline.ingest import tanzil_ust_veri
from mutalaa_pipeline.normalize import normalize_tr

_ORTAM_VERI_KOK = os.environ.get("MUTALAA_VERI_KOK")


def _yok(neden: str) -> None:
    if os.environ.get("MUTALAA_DEGISMEZLIK_ZORUNLU") == "1":
        pytest.fail(f"zorunlu gercek veri testi veri bulamadi: {neden}")
    pytest.skip(neden)


@dataclass(frozen=True)
class Gercek:
    tablo: list[s.TabloSatiri]
    yonlendirmeler: list[s.Yonlendirme]
    elenen: int
    meta: list[s.MetaSatiri]
    tanzil: list[dict[str, Any]]
    adaylar: list[dict[str, Any]]
    riskli: list[str]
    viki_dosyalari: dict[str, bytes]


@pytest.fixture(scope="module")
def gercek() -> Gercek:
    veri_kok = (
        Ayarlar(veri_kok=Path(_ORTAM_VERI_KOK)).veri_kok if _ORTAM_VERI_KOK else Ayarlar().veri_kok
    )
    kilit = s.kilit_yukle()
    gelen = {slug: s.gelen_dizini(veri_kok, slug) for slug in (s.KAYNAK, s.QURAN_META)}
    if not all(g.is_dir() for g in gelen.values()):
        _yok("data/gelen/sure-adlari-vikipedi ya da data/gelen/quran-meta yok")
    tarihler = {slug: s.gelen_tarihi_coz(g, None) for slug, g in gelen.items()}
    viki = s.gelen_oku(gelen[s.KAYNAK], tarihler[s.KAYNAK], kilit.vikipedi)
    meta_dosyalar = s.gelen_oku(gelen[s.QURAN_META], tarihler[s.QURAN_META], kilit.quran_meta)
    ust = veri_kok / "gelen" / "tanzil-ust-veri"
    ust_tarihler = sorted(p for p in ust.iterdir() if p.is_dir()) if ust.is_dir() else []
    if not ust_tarihler:
        _yok("data/gelen/tanzil-ust-veri yok")
    xml = (ust_tarihler[-1] / "quran-data.xml").read_bytes()
    tanzil = tanzil_ust_veri.yapi_ayristir(xml)["sure"]
    tablo = s.tablo_ayristir(viki[s.VIKIPEDI_TABLO].decode("utf-8"))
    yon, elenen = s.yonlendirmeleri_ayikla(
        {a: v for a, v in viki.items() if a.startswith("yonlendirmeler-")}, tablo
    )
    meta = s.quran_meta_ayristir(meta_dosyalar["quran-meta-7.0.0.tgz"])
    riskli = riskli_adlari_oku()
    adaylar = adaylari_uret(tablo, yon, meta, tanzil, riskli)
    return Gercek(tablo, yon, elenen, meta, tanzil, adaylar, riskli, viki)  # type: ignore[arg-type]


def test_tablo_114_satir_kesintisiz_ve_madde_basliklari_tekil(gercek: Gercek) -> None:
    assert [t.no for t in gercek.tablo] == list(range(1, 115))
    assert len({t.baslik for t in gercek.tablo}) == 114
    assert all(t.ad and t.baslik and t.ayas > 0 and t.inis > 0 for t in gercek.tablo)


def test_revizyon_json_kilitteki_revizyonu_ve_dosya_boyutunu_dogrular(gercek: Gercek) -> None:
    kilit = s.kilit_yukle().vikipedi
    revid = s.revizyon_denetle(
        gercek.viki_dosyalari[s.VIKIPEDI_REVIZYON],
        kilit,
        len(gercek.viki_dosyalari[s.VIKIPEDI_TABLO]),
    )
    assert str(revid) == kilit.surum


def test_vikipedi_ile_tanzil_ayet_yer_ve_inis_sirasi_farki_yok(gercek: Gercek) -> None:
    farklar = [t.no for t in gercek.tablo if tanzil_farki(t, gercek.tanzil[t.no - 1]) is not None]
    assert farklar == []  # Tedarik olcumu (0 fark); fark cikarsa aday satiri isaretli girer


def test_yonlendirmeler_yalniz_tablo_maddelerinin_ve_suzgecten_gecen(gercek: Gercek) -> None:
    basliklar = {t.baslik: t.no for t in gercek.tablo}
    assert gercek.yonlendirmeler
    assert all(basliklar[y.hedef] == y.no for y in gercek.yonlendirmeler)
    assert all(s.yonlendirme_adi_uygun(y.baslik) for y in gercek.yonlendirmeler)
    # dosyalardaki tablo maddesi yonlendirmeleri == kabul + elenen (ayni baslik tekrar sayilmaz)
    ham: set[tuple[str, str]] = set()
    for ad, veri in gercek.viki_dosyalari.items():
        if not ad.startswith("yonlendirmeler-"):
            continue
        for sayfa in json.loads(veri)["query"]["pages"]:
            if sayfa["title"] in basliklar:
                ham |= {(sayfa["title"], r["title"]) for r in sayfa.get("redirects", [])}
    assert len(ham) == len(gercek.yonlendirmeler) + gercek.elenen
    # tablo disi sayfalarin yonlendirmeleri alinmamistir
    assert len(ham) < sum(
        len(sayfa.get("redirects", []))
        for veri in (v for a, v in gercek.viki_dosyalari.items() if a.startswith("yonlendirmeler-"))
        for sayfa in json.loads(veri)["query"]["pages"]
    )


def test_quran_meta_114_girdi_kesintisiz(gercek: Gercek) -> None:
    assert [m.no for m in gercek.meta] == list(range(1, 115))
    assert all(m.ad and m.anlam and m.satir > 0 for m in gercek.meta)


def test_her_surede_tam_bir_kanonik_aday_ve_tablo_adidir(gercek: Gercek) -> None:
    sayim = Counter(a["surah_no"] for a in gercek.adaylar if a["kind"] == "kanonik")
    assert [sayim[n] for n in range(1, 115)] == [1] * 114
    for a in gercek.adaylar:
        if a["kind"] == "kanonik":
            assert a["alias"] == gercek.tablo[a["surah_no"] - 1].ad
            assert a["onerilen"]["anlam"] == gercek.tablo[a["surah_no"] - 1].anlam


def test_adaylar_tekil_gecerli_ve_anahtarlari_yeniden_uretilir(gercek: Gercek) -> None:
    assert len({(a["surah_no"], a["alias"]) for a in gercek.adaylar}) == len(gercek.adaylar)
    assert len(
        {(a["surah_no"], a["alias_key"], a["kind"] == "arapca") for a in gercek.adaylar}
    ) == len(gercek.adaylar)
    assert all(a["status"] == "aday" and a["alias_key"] for a in gercek.adaylar)
    assert all(
        alias_anahtari(a["alias"], a["kind"] == "arapca") == a["alias_key"] for a in gercek.adaylar
    )
    assert {a["kind"] for a in gercek.adaylar} == {"kanonik", "yazim", "diger_ad", "arapca"}


def test_her_surede_tanzil_ad_ar_arapca_aday(gercek: Gercek) -> None:
    arapca = {(a["surah_no"], a["alias"]) for a in gercek.adaylar if a["kind"] == "arapca"}
    assert all((t["no"], t["ad_ar"]) in arapca for t in gercek.tanzil)


def test_arapca_icin_genis_anahtar_bos_normalize_ar_ayirt_eder(gercek: Gercek) -> None:
    """A05 genis anahtari Arapca harfleri Turkce parca saymaz (bos); normalize_ar ayirt eder."""
    arapca = [a for a in gercek.adaylar if a["kind"] == "arapca"]
    assert all(normalize_tr(a["alias"], "genis") == "" for a in arapca)
    ad_ar_anahtarlari = [
        a["alias_key"] for a in arapca if a["onerilen"]["kaynaklar"][0].get("alan") == "ad_ar"
    ]
    assert len(ad_ar_anahtarlari) == 114 and len(set(ad_ar_anahtarlari)) == 114


def test_riskli_adlarin_her_biri_tam_bir_sureye_eslenir(gercek: Gercek) -> None:
    eslesme = riskli_eslesme(gercek.adaylar, gercek.riskli)
    sorunlu = [i + 1 for i, v in enumerate(eslesme.values()) if len(v) != 1]
    assert sorunlu == []
    assert len(eslesme) == len(gercek.riskli) > 0
    riskli_adaylar = [a for a in gercek.adaylar if a["risky"]]
    assert {a["surah_no"] for a in riskli_adaylar} == {v[0] for v in eslesme.values()}
    assert all(a["kind"] != "arapca" for a in riskli_adaylar)


def test_capraz_sure_anahtar_cakismalari_kesme_isaretli_adlardan_gelir(gercek: Gercek) -> None:
    """A05 kesme isaretinden sonrasini ek sayar; cakisan anahtarlar kesmeli adlardan uretilir."""
    cakismalar = capraz_sure_cakismalari(gercek.adaylar)
    kanonik = {a["surah_no"]: a["alias"] for a in gercek.adaylar if a["kind"] == "kanonik"}
    for anahtar, sureler in cakismalar.items():
        assert len(sureler) > 1
        assert all("'" in kanonik[n] or chr(0x2019) in kanonik[n] for n in sureler), anahtar


def test_adaylar_siralidir_ve_yeniden_uretimde_ayni(gercek: Gercek) -> None:
    yeni = adaylari_uret(
        gercek.tablo, gercek.yonlendirmeler, gercek.meta, gercek.tanzil, gercek.riskli
    )
    assert yeni == gercek.adaylar
    assert gercek.adaylar == sorted(gercek.adaylar, key=lambda a: (a["surah_no"], a["alias"]))
