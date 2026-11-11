# ruff: noqa: RUF001
"""Meal kayit modulu, kaynak kayitlari ve kilit tutarliligi (A16.2).

`ingest/meal_kaynaklari.py` tek kayit modulu: cli, qa ve export ondan turer. Bu test kayitlarin,
TOML dosyalarinin, kilidin ve yonlendirmelerin ayni kaynak kumesini ve ayni kapi kumesini
gosterdigini sinar. Gercek meal metni yoktur.
"""

import json
from collections.abc import Callable
from typing import Any

import pytest
from typer.testing import CliRunner

from mutalaa_pipeline import cli, qa, sources
from mutalaa_pipeline.export import pg
from mutalaa_pipeline.export.ortak import GirdiHatasi, depo_koku
from mutalaa_pipeline.ingest import meal_kaynaklari as mk
from mutalaa_pipeline.ingest import meal_kilit
from mutalaa_pipeline.ingest.meal_kilit import kilit_coz, kilit_metni, kilit_ozeti, kilit_yukle

runner = CliRunner()


def _kayitlar() -> dict[str, sources.Kaynak]:
    return {s.kaynak.slug: s.kaynak for s in sources.yukle(depo_koku()) if s.kaynak is not None}


def test_uc_kaynak_kayitlidir_ve_roller_dogrudur() -> None:
    assert set(mk.KAYNAKLAR) == {"elmalili-meal", "elmalili-sade-meal", "elmalili-meal-epub"}
    assert mk.MEAL_KAYNAKLARI == ("elmalili-meal", "elmalili-sade-meal")
    assert mk.TANIK_KAYNAKLARI == ("elmalili-meal-epub",)
    assert mk.capa_eseri("elmalili-meal") == "elmalili"
    assert mk.capa_eseri("elmalili-sade-meal") == "elmalili-sade"
    assert mk.capa_onegi("elmalili-sade-meal") == "meal:elmalili-sade:"
    with pytest.raises(KeyError):
        mk.capa_eseri("elmalili-meal-epub")  # tanikta capa yok
    assert mk.kaynak("elmalili-meal").tanik == "elmalili-meal-epub"
    assert mk.kaynak("elmalili-sade-meal").tanik is None
    assert not mk.meal_mi("elmalili-meal-epub")
    assert mk.tanik_mi("elmalili-meal-epub")
    assert not mk.meal_mi("tanzil-uthmani")
    assert not mk.meal_mi(None)


def test_kaynak_kayitlari_gecerli_ve_k49_atifini_tasir() -> None:
    kayitlar = _kayitlar()
    for slug in mk.KAYNAKLAR:
        k = kayitlar[slug]
        assert k.tur.value == "meal"
        assert k.surum is not None
        assert k.kaynak_url is not None
        assert k.provider is not None
        assert "{sürüm}" not in k.atif_metni
    assert kayitlar["elmalili-meal"].atif_metni == mk.ATIF_ORIJINAL
    assert kayitlar["elmalili-sade-meal"].atif_metni == mk.ATIF_SADE
    assert kayitlar["elmalili-meal"].atif_metni == (
        "Meal: Elmalılı Muhammed Hamdi Yazır, Hak Dini Kur'an Dili, İstanbul 1935–1939."
        " Metin Vikikaynak 'Kur'an' sayfalarından alınmıştır."
    )
    assert kayitlar["elmalili-sade-meal"].atif_metni == (
        "Meal: Elmalılı Muhammed Hamdi Yazır, sadeleştirilmiş metin (sadeleştiren belirtilmemiş)."
        " fawazahmed0/quran-api üzerinden alınmıştır."
    )
    assert kayitlar["elmalili-meal"].surum == "revid-liste-965a6249f61c-2026-11-11"
    assert kayitlar["elmalili-sade-meal"].surum == (
        "commit-93e6f64925ae76273520d636fcaaf061129f2316"
    )


def test_kapi_kumeleri_kayit_modulunden_turer() -> None:
    bes = ("G-KAY", "G-BUT", "G-CAP", "G-NOR", "G-HIZ")
    assert bes == mk.MEAL_KAPILARI
    for slug in mk.MEAL_KAYNAKLARI:
        assert qa.kaynak_kapilari(slug) == bes
        assert mk.kaynak(slug).kapilar == bes
    assert mk.kaynak("elmalili-meal-epub").kapilar == ()
    assert qa.kaynak_kapilari("tanzil-uthmani") == qa.KAPILAR  # dortlu kume degismedi


def test_export_yonlendirmesi_yalniz_iki_meali_tanir() -> None:
    for slug in mk.MEAL_KAYNAKLARI:
        assert pg.EK_KAYNAKLAR[slug] == ()
    assert "elmalili-meal-epub" not in pg.EK_KAYNAKLAR  # tanik yuklenmez
    sonuc = runner.invoke(cli.app, ["export", "pg", "--source", "elmalili-meal-epub"])
    assert sonuc.exit_code == 2


def test_cli_yalniz_kayitli_kaynaklari_alir() -> None:
    sonuc = runner.invoke(cli.app, ["ingest", "meal", "--source", "baska-kaynak"])
    assert sonuc.exit_code == 2
    for adim in ("normalize", "anchor"):
        sonuc = runner.invoke(cli.app, [adim, "--source", "elmalili-meal-epub"])
        assert sonuc.exit_code == 2
    sonuc = runner.invoke(cli.app, ["ingest", "meal", "--help"])
    assert sonuc.exit_code == 0
    assert "--kilit-oner" in sonuc.stdout


def test_qa_yardim_metni_bes_kapiyi_soyler() -> None:
    assert "G-HIZ" in (cli.qa_app.info.help or "")


def test_her_bagdastirici_fabrika_ve_yeniden_uretim_tanimlar() -> None:
    for slug in mk.KAYNAKLAR:
        assert callable(getattr(mk.bagdastirici_modulu(slug), "bagdastirici_olustur", None))
    for slug in mk.MEAL_KAYNAKLARI:
        assert callable(getattr(mk.bagdastirici_modulu(slug), "yeniden_uret", None))


# --- kilit -----------------------------------------------------------------------------------


def test_paketteki_kilit_gecerli_ve_kanonik_yazimdadir() -> None:
    ham = meal_kilit.KILIT_YOLU.read_bytes()
    kilit = kilit_coz(ham)
    assert kilit_metni(kilit).encode("utf-8") == ham  # dosya kilit_metni ciktisi (ASCII, LF)
    v = kilit.vikikaynak
    assert len(v.sayfalar) == 114
    assert sorted(s.sure for s in v.sayfalar) == list(range(1, 115))
    assert len({s.baslik for s in v.sayfalar}) == 114
    assert v.liste_sha256 == v.dosya("basliklar.tsv").sha256
    assert [d.ad for d in v.yanit_dosyalari] == [
        "vikikaynak-01.json",
        "vikikaynak-02.json",
        "vikikaynak-03.json",
    ]
    assert not ham.startswith(b"\xef\xbb\xbf")
    assert b"\r" not in ham


def test_kilit_kayit_surumleriyle_tutarli() -> None:
    kilit = kilit_yukle()
    kayitlar = _kayitlar()
    assert kayitlar["elmalili-sade-meal"].surum == f"commit-{kilit.sade.commit}"
    assert kilit.sade.url.endswith(f"/{kilit.sade.commit}/editions/tur-elmallsadelesti.json")
    assert kilit.vikikaynak.liste_sha256[:12] in str(kayitlar["elmalili-meal"].surum)
    assert kilit.tanik_epub.sha1[:12] in str(kayitlar["elmalili-meal-epub"].surum)


def test_kilit_ozeti_bolum_icerigine_baglidir() -> None:
    kilit = kilit_yukle()
    a = kilit_ozeti(kilit.bolum_sozlugu("sade"))
    assert a == kilit_ozeti(kilit.bolum_sozlugu("sade"))
    assert a != kilit_ozeti(kilit.bolum_sozlugu("tanik_epub"))
    degisen = dict(kilit.bolum_sozlugu("sade"), commit="0" * 40)
    assert kilit_ozeti(degisen) != a


def _kilit_json() -> dict[str, Any]:
    veri = json.loads(meal_kilit.KILIT_YOLU.read_bytes())
    assert isinstance(veri, dict)
    return veri


def _sil(d: dict[str, Any]) -> None:
    d.pop("sade")


def _fazla(d: dict[str, Any]) -> None:
    d["fazla"] = {}


def _sayfa_eksik(d: dict[str, Any]) -> None:
    d["vikikaynak"]["sayfalar"].pop()


def _sure_yinelenir(d: dict[str, Any]) -> None:
    d["vikikaynak"]["sayfalar"][0]["sure"] = 2


def _sha1_bozuk(d: dict[str, Any]) -> None:
    d["vikikaynak"]["sayfalar"][0]["sha1"] = "x"


def _revid_sifir(d: dict[str, Any]) -> None:
    d["vikikaynak"]["sayfalar"][0]["revid"] = 0


def _liste_yok(d: dict[str, Any]) -> None:
    d["vikikaynak"]["dosyalar"].pop(0)  # basliklar.tsv


def _http(d: dict[str, Any]) -> None:
    d["vikikaynak"]["url"] = "http://x"


def _commit_kisa(d: dict[str, Any]) -> None:
    d["sade"]["commit"] = "abc"


def _dosya_adi_yol(d: dict[str, Any]) -> None:
    d["sade"]["dosya"]["ad"] = "../x.json"


def _sha1_buyuk(d: dict[str, Any]) -> None:
    d["tanik_epub"]["sha1"] = "A" * 40


def _tarih_gecersiz(d: dict[str, Any]) -> None:
    d["vikikaynak"]["alinma_tarihi"] = "2026-13-40"


@pytest.mark.parametrize(
    "bozma",
    [
        _sil,
        _fazla,
        _sayfa_eksik,
        _sure_yinelenir,
        _sha1_bozuk,
        _revid_sifir,
        _liste_yok,
        _http,
        _commit_kisa,
        _dosya_adi_yol,
        _sha1_buyuk,
        _tarih_gecersiz,
    ],
)
def test_bozuk_kilit_girdi_hatasi(bozma: Callable[[dict[str, Any]], None]) -> None:
    d = _kilit_json()
    bozma(d)
    with pytest.raises(GirdiHatasi):
        kilit_coz(json.dumps(d).encode("utf-8"))


def test_kilit_bom_cr_ve_yinelenen_anahtar_reddedilir() -> None:
    ham = meal_kilit.KILIT_YOLU.read_bytes()
    for bozuk in (b"\xef\xbb\xbf" + ham, ham.replace(b"\n", b"\r\n", 1)):
        with pytest.raises(GirdiHatasi):
            kilit_coz(bozuk)
    with pytest.raises(GirdiHatasi):
        kilit_coz(b'{"sade": {}, "sade": {}}')


# --- U+00B4 aynen kalir (kesme bicimi donusturulmez) -------------------------------------------


def test_u00b4_kanonik_metinde_ve_sade_yolunda_aynen_kalir() -> None:
    from mutalaa_pipeline.anchor import kanonik_metin
    from mutalaa_pipeline.anchor.ayet_sayilari import AYET_SAYILARI
    from mutalaa_pipeline.ingest import elmalili_sade

    assert kanonik_metin("Deneme´ metin") == "Deneme´ metin"
    assert elmalili_sade.metin_cikar("Deneme´ metin") == "Deneme´ metin"
    kayitlar = [
        {"chapter": s, "verse": a, "text": f"Deneme sade parca {s}-{a}"}
        for s in range(1, 115)
        for a in range(1, AYET_SAYILARI[s - 1] + 1)
    ]
    kayitlar[0]["text"] = "Deneme´ metin"
    veri = json.dumps({"quran": kayitlar}).encode("utf-8")
    ad = kilit_yukle().sade.dosya.ad
    sonuc = elmalili_sade.yeniden_uret({ad: veri})
    metin, attrs = sonuc["meal:elmalili-sade:1:1"]
    assert metin == "Deneme´ metin" and "'" not in metin and attrs == {}
