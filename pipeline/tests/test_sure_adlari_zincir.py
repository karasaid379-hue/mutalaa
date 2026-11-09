"""Sure adi zinciri: ingest -> anchor -> qa (A11.3; SENTETIK, veritabani yok).

`sure_adlari_zinciri` (conftest) sentetik Vikipedi/quran-meta dosyalariyla ve ust veri zinciriyle
gercek komut islevlerini kosar. Kapi testleri bellekteki `SureAdlariGirdisi` uzerinde tek bir
kusur uretir. Hicbir sure adi ya da sayi hafizadan yazilmaz.
"""

import dataclasses
import json
import shutil
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from sure_adlari_yardimci import (
    REVID,
    SURE_SAYISI,
    SureAdlariZinciri,
    ad,
    baslik,
    sentetik_dosyalar,
)
from typer.testing import CliRunner
from zincir_yardimci import ortam_kur, sablon_kopyala

from mutalaa_pipeline import cli, lineage
from mutalaa_pipeline.adimlar.anchor_sure_adlari import run_anchor_sure_adlari
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.ingest.sure_adlari import KAYNAK, TabloSatiri, komut_ingest_sure_adlari
from mutalaa_pipeline.lineage import ALIASLAR_ADI
from mutalaa_pipeline.qa import SURE_ADI_KAPILARI
from mutalaa_pipeline.qa.checks.sure_adlari import (
    KAPI_ISLEVLERI,
    SureAdlariGirdisi,
    g_but,
    g_kay,
    olcumler,
)
from mutalaa_pipeline.qa.checks.tanzil import KapiSonucu
from mutalaa_pipeline.qa.run_sure_adlari import kapilari_sec, yukle
from mutalaa_pipeline.staged import Satir
from mutalaa_pipeline.zincir import calismalar, girdiler, ust_calismalar

runner = CliRunner()


@pytest.fixture
def sz(
    sure_adlari_zinciri: SureAdlariZinciri, monkeypatch: pytest.MonkeyPatch
) -> SureAdlariZinciri:
    sure_adlari_zinciri.ortam(monkeypatch)
    return sure_adlari_zinciri


@pytest.fixture(scope="module")
def girdi_modul(sure_adlari_zinciri: SureAdlariZinciri) -> Iterator[SureAdlariGirdisi]:
    with pytest.MonkeyPatch.context() as mp:
        sure_adlari_zinciri.ortam(mp)
        ctx = sure_adlari_zinciri.uz.ctx("qa", [KAYNAK])
        kayitlar = ctx.require_sources((KAYNAK, "quran-meta", "tanzil-ust-veri"))
        girdi, _, _ = yukle(ctx, kayitlar, run=None)
        yield girdi


@pytest.fixture
def girdi(girdi_modul: SureAdlariGirdisi, sz: SureAdlariZinciri) -> SureAdlariGirdisi:
    return girdi_modul


def son(sz: SureAdlariZinciri, adim: str) -> Any:
    return calismalar(sz.uz.ctx(adim, [KAYNAK]), KAYNAK, adim)[-1]


# --- adimlar ----------------------------------------


def test_anchor_manifesti_tek_cikti_ve_dort_girdi_zincir(sz: SureAdlariZinciri) -> None:
    anchor = son(sz, "anchor")
    assert [c["yol"].rsplit("/", 1)[-1] for c in anchor.manifest["ciktilar"]] == [ALIASLAR_ADI]
    adlar = sorted(yol.rsplit("/", 1)[-1] for yol, _ in girdiler(anchor.manifest))
    assert adlar == sorted(
        ["tablo.jsonl", "yonlendirmeler.jsonl", "quran-meta.jsonl", "sure.jsonl"]
    )
    ustler = ust_calismalar(sz.uz.ctx("qa", [KAYNAK]), anchor)
    assert {(u.adim, u.source_id) for u in ustler} == {
        ("ingest", KAYNAK),
        ("ingest", "tanzil-ust-veri"),
    }
    assert lineage.ciktilar_saglam(sz.uz.z.veri_kok, anchor.manifest)
    ayrinti = anchor.manifest["ayrintilar"]
    assert ayrinti["aday"] == anchor.manifest["ciktilar"][0]["satir"]
    assert ayrinti["kind"]["kanonik"] == SURE_SAYISI
    # riskli ad metni manifeste yazilmaz: anahtar ad sirasidir
    assert set(ayrinti["riskli_eslesme"]) == {"1", "2"}


def test_aday_dosyasi_ascii_kacisli_sirali_kanonik_sure_basina_bir(sz: SureAdlariZinciri) -> None:
    anchor = son(sz, "anchor")
    veri = (anchor.klasor / ALIASLAR_ADI).read_bytes()
    assert veri.isascii() and b"\r" not in veri and veri.endswith(b"\n")
    satirlar = [json.loads(s) for s in veri.splitlines()]
    assert [(s["surah_no"], s["alias"]) for s in satirlar] == sorted(
        (s["surah_no"], s["alias"]) for s in satirlar
    )
    assert sum(1 for s in satirlar if s["kind"] == "kanonik") == SURE_SAYISI
    assert all(s["status"] == "aday" for s in satirlar)


def test_ikinci_anchor_atlanir_yeni_ust_calismada_atlanmaz(
    sz: SureAdlariZinciri, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Paylasilan zinciri bozmamak icin kopya uzerinde calisir."""
    kopya = sablon_kopyala(sz.uz.z.tmp, tmp_path / "k")
    sz.ortam(monkeypatch)
    ortam_kur(kopya, monkeypatch)  # veri koku kopyaya (kilit/riskli yollari sz'den kalir)
    ilk = run_anchor_sure_adlari(kopya.ctx("anchor", [KAYNAK], temiz_git=True))
    assert ilk.atlandi is False
    ikinci = run_anchor_sure_adlari(kopya.ctx("anchor", [KAYNAK], temiz_git=True))
    assert (ikinci.atlandi, ikinci.onceki_run_id) == (True, ilk.run_id)
    zorla = run_anchor_sure_adlari(kopya.ctx("anchor", [KAYNAK], temiz_git=True, force=True))
    assert zorla.atlandi is False
    kod = komut_ingest_sure_adlari(
        gelen_tarih=None, dry_run=False, force=True, config=None, kok=kopya.kok
    )
    assert kod == 0  # ust calisma degisti: ayni ciktiyla yeni ingest
    assert run_anchor_sure_adlari(kopya.ctx("anchor", [KAYNAK], temiz_git=True)).atlandi is False


def test_anchor_dry_run_hicbir_sey_yazmaz(sz: SureAdlariZinciri) -> None:
    once = sorted((sz.uz.z.veri_kok / "staged" / KAYNAK).iterdir())
    sonuc = run_anchor_sure_adlari(sz.uz.ctx("anchor", [KAYNAK], dry_run=True))
    assert sonuc.klasor is None and sonuc.aday_sayisi > 0
    assert sorted((sz.uz.z.veri_kok / "staged" / KAYNAK).iterdir()) == once


def test_anchor_ingest_yoksa_ipucuyla_hata(
    sz: SureAdlariZinciri, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    kopya = sablon_kopyala(sz.uz.z.tmp, tmp_path / "k")
    ortam_kur(kopya, monkeypatch)
    shutil.rmtree(kopya.veri_kok / "staged" / KAYNAK)
    with pytest.raises(GirdiHatasi, match="ingest sure-adlari"):
        run_anchor_sure_adlari(kopya.ctx("anchor", [KAYNAK, "tanzil-ust-veri"]))


# --- QA raporu ----------------------------------------


def son_qa_raporu(sz: SureAdlariZinciri) -> dict[str, Any]:
    raporlar = [
        json.loads(p.read_bytes()) for p in sorted((sz.uz.z.veri_kok / "reports").glob("*.json"))
    ]
    return [r for r in raporlar if r["komut"] == "qa run" and r.get("kaynak") == KAYNAK][-1]


def test_qa_raporu_iki_kapi_g_cap_ve_g_nor_yok(sz: SureAdlariZinciri) -> None:
    rapor = son_qa_raporu(sz)
    assert rapor["cikis_kodu"] == 0
    assert rapor["kapilar"] == dict.fromkeys(SURE_ADI_KAPILARI, "gecti")
    assert set(rapor["kapilar"]) == {"G-KAY", "G-BUT"}
    anchor = son(sz, "anchor")
    assert (rapor["anchor_run_id"], rapor["units_sha256"]) == (
        anchor.run_id,
        anchor.cikti_ozeti(ALIASLAR_ADI),
    )


def test_qa_olcumleri_icerik_tasimaz_ve_arapca_anahtar_olculur(sz: SureAdlariZinciri) -> None:
    olcum = son_qa_raporu(sz)["olcumler"]
    assert olcum["kanonik_olan_sure"] == SURE_SAYISI
    assert olcum["riskli_aday"] == 2 and set(olcum["riskli_eslesme"]) == {"1", "2"}
    assert olcum["riskli_eslesme"] == {"1": [5], "2": [9]}
    assert olcum["tanzil_fark_sure"] == []
    arapca = olcum["arapca_anahtar"]
    assert arapca["aday"] == 2 * SURE_SAYISI
    assert arapca["genis_anahtar_bos"] == 2 * SURE_SAYISI  # normalize_tr Arapcada bos doner
    assert arapca["normalize_ar_benzersiz_sure_basina"] is True
    assert arapca["ad_ar_benzersiz"] == SURE_SAYISI
    assert olcum["yonlendirme"] == {"kabul": 2 * SURE_SAYISI, "elenen": 0}
    assert olcum["kaynak_ozetleri"]["vikipedi_revizyon"] == str(REVID)
    assert son_qa_raporu(sz)["kapi_sayilari"]["G-BUT"]["kanonik"] == SURE_SAYISI


def test_kapilari_sec_g_cap_ve_g_nor_bu_kaynakta_yok() -> None:
    assert kapilari_sec(None) == SURE_ADI_KAPILARI
    assert kapilari_sec(["G-BUT"]) == ("G-BUT",)
    for gecersiz in ("G-CAP", "G-NOR", "G-X"):
        with pytest.raises(GirdiHatasi):
            kapilari_sec([gecersiz])


def test_cli_ingest_anchor_ve_qa_komutlari(sz: SureAdlariZinciri) -> None:
    kok = ["--kok", str(sz.uz.z.kok)]
    ingest = runner.invoke(cli.app, ["ingest", "sure-adlari", "--dry-run", *kok])
    assert ingest.exit_code == 0, ingest.stderr
    assert "dry-run" in ingest.stdout
    anchor = runner.invoke(cli.app, ["anchor", "--source", KAYNAK, "--dry-run", *kok])
    assert anchor.exit_code == 0, anchor.stderr
    assert "aday" in anchor.stdout
    qa = runner.invoke(cli.app, ["qa", "run", "--source", KAYNAK, "--gate", "G-NOR", *kok])
    assert qa.exit_code == 2
    limit = runner.invoke(cli.app, ["ingest", "sure-adlari", "--limit", "3", *kok])
    assert limit.exit_code == 2


# --- kapilar: gecen temel girdi ----------------------------------------


def bulgu_var(sonuc: KapiSonucu, parca: str) -> bool:
    return any(parca in b for b in sonuc.bulgular)


def satirlari_degistir(g: SureAdlariGirdisi, secici: Any, **alanlar: Any) -> SureAdlariGirdisi:
    yeni = [
        Satir(s.etiket, s.no, {**s.veri, **alanlar}) if secici(s.veri) else s for s in g.adaylar
    ]
    return dataclasses.replace(g, adaylar=yeni)


def satirlari_cikar(g: SureAdlariGirdisi, secici: Any) -> SureAdlariGirdisi:
    return dataclasses.replace(g, adaylar=[s for s in g.adaylar if not secici(s.veri)])


def test_temel_girdi_iki_kapidan_gecer(girdi: SureAdlariGirdisi) -> None:
    sonuclar = {k: f(girdi) for k, f in KAPI_ISLEVLERI.items()}
    assert tuple(sonuclar) == SURE_ADI_KAPILARI
    assert all(s.gecti for s in sonuclar.values()), {k: s.bulgular for k, s in sonuclar.items()}
    assert sonuclar["G-BUT"].sayilar["kanonik"] == SURE_SAYISI


def test_g_but_kanonik_aday_eksikse_ya_cogaldiysa_kalir(girdi: SureAdlariGirdisi) -> None:
    eksik = satirlari_cikar(girdi, lambda v: v["surah_no"] == 9 and v["kind"] == "kanonik")
    sonuc = g_but(eksik)
    assert bulgu_var(sonuc, "kanonik aday sayisi")
    fazla = satirlari_degistir(
        girdi, lambda v: v["surah_no"] == 9 and v["kind"] == "yazim", kind="kanonik"
    )
    assert bulgu_var(g_but(fazla), "kanonik aday sayisi")


def test_g_but_yinelenen_alias_ve_alias_key(girdi: SureAdlariGirdisi) -> None:
    kopya = dataclasses.replace(girdi, adaylar=[*girdi.adaylar, girdi.adaylar[0]])
    assert bulgu_var(g_but(kopya), "yinelenen (surah_no, alias)")
    cakisan = satirlari_degistir(
        girdi,
        lambda v: v["surah_no"] == 2 and v["kind"] == "yazim",
        alias_key=next(
            s.veri["alias_key"]
            for s in girdi.adaylar
            if s.veri["surah_no"] == 2 and s.veri["kind"] == "kanonik"
        ),
    )
    assert bulgu_var(g_but(cakisan), "yinelenen (surah_no, alias_key)")


def test_g_but_alias_key_yeniden_uretilenden_farkliysa_kalir(girdi: SureAdlariGirdisi) -> None:
    sonuc = g_but(
        satirlari_degistir(
            girdi, lambda v: v["surah_no"] == 4 and v["kind"] == "kanonik", alias_key="x"
        )
    )
    assert bulgu_var(sonuc, "alias_key")
    assert bulgu_var(sonuc, "aliases.jsonl yeniden uretilenle ayni degil")


@pytest.mark.parametrize(
    "degisim",
    [{"status": "onayli"}, {"kind": "baska"}, {"risky": "evet"}, {"surah_no": 115}, {"alias": " "}],
)
def test_g_but_gecersiz_aday_satiri(girdi: SureAdlariGirdisi, degisim: dict[str, Any]) -> None:
    sonuc = g_but(
        satirlari_degistir(
            girdi, lambda v: v["surah_no"] == 6 and v["kind"] == "kanonik", **degisim
        )
    )
    assert not sonuc.gecti


def test_g_but_arapca_ad_eksikse_kalir(girdi: SureAdlariGirdisi) -> None:
    eksik = satirlari_cikar(
        girdi,
        lambda v: (
            v["surah_no"] == 12
            and v["kind"] == "arapca"
            and v["onerilen"]["kaynaklar"][0].get("alan") == "ad_ar"
        ),
    )
    assert bulgu_var(g_but(eksik), "Arapca ad")


def test_g_but_riskli_ad_tam_bir_sureye_eslenmeli(girdi: SureAdlariGirdisi) -> None:
    sifir = dataclasses.replace(girdi, riskli_adlar=[*girdi.riskli_adlar, "Hicbirsurede"])
    assert bulgu_var(g_but(sifir), "riskli ad")
    iki_sure = satirlari_degistir(
        girdi,
        lambda v: v["surah_no"] == 6 and v["kind"] == "kanonik",
        alias_key=next(
            s.veri["alias_key"]
            for s in girdi.adaylar
            if s.veri["surah_no"] == 5 and s.veri["kind"] == "kanonik"
        ),
    )
    assert bulgu_var(g_but(iki_sure), "riskli ad")  # ayni ad iki surede


def test_g_but_risky_bayragi_listeyle_ayni_olmali(girdi: SureAdlariGirdisi) -> None:
    sahte = satirlari_degistir(
        girdi, lambda v: v["surah_no"] == 20 and v["kind"] == "kanonik", risky=True
    )
    assert bulgu_var(g_but(sahte), "risky bayragi")
    eksik = satirlari_degistir(
        girdi, lambda v: v["surah_no"] == 5 and v["kind"] == "kanonik", risky=False
    )
    assert bulgu_var(g_but(eksik), "risky bayragi")


def test_g_but_tanzil_fark_isareti_yeniden_hesaplananla_ayni_olmali(
    girdi: SureAdlariGirdisi,
) -> None:
    tanzil = [dict(t) for t in girdi.tanzil]
    tanzil[2]["ayas"] = int(tanzil[2]["ayas"]) + 1
    sonuc = g_but(dataclasses.replace(girdi, tanzil=tanzil))
    assert bulgu_var(sonuc, "Tanzil fark isaretleri")
    # fark ham dosyalardan yeniden uretimde de gorulur (staged'de isaret yok)
    assert bulgu_var(sonuc, "aliases.jsonl yeniden uretilenle ayni degil")


def test_g_but_staged_tablo_ham_vikimetinden_farkliysa_kalir(girdi: SureAdlariGirdisi) -> None:
    tablo = list(girdi.tablo)
    tablo[0] = TabloSatiri(**{**tablo[0].sozluk(), "anlam": "baska"})
    assert bulgu_var(g_but(dataclasses.replace(girdi, tablo=tablo)), "tablo.jsonl ham vikimetinden")


def test_g_but_suzgecten_gecmeyen_yonlendirme_staged_te_olamaz(girdi: SureAdlariGirdisi) -> None:
    from mutalaa_pipeline.ingest.sure_adlari import Yonlendirme

    yon = [*girdi.yonlendirmeler, Yonlendirme(1, ad(1) + " (sure)", baslik(1), "x.json", "p")]
    assert bulgu_var(g_but(dataclasses.replace(girdi, yonlendirmeler=yon)), "yonlendirme")


def test_g_but_ham_dosya_degisirse_yeniden_uretilemez(girdi: SureAdlariGirdisi) -> None:
    viki, _ = sentetik_dosyalar()
    bozuk = {**girdi.ham["sure-adlari-vikipedi"], "sureler-listesi.wikitext": b"{|\n|}\n"}
    sonuc = g_but(dataclasses.replace(girdi, ham={**girdi.ham, "sure-adlari-vikipedi": bozuk}))
    assert bulgu_var(sonuc, "ham dosyalar yeniden ayristirilamadi")
    assert viki


def test_g_kay_ham_dosya_kilit_kayit_ve_revizyon_tutarliligi(girdi: SureAdlariGirdisi) -> None:
    assert g_kay(girdi).gecti
    bozuk = {**girdi.ham["sure-adlari-vikipedi"], "yonlendirmeler-01.json": b"{}"}
    sonuc = g_kay(dataclasses.replace(girdi, ham={**girdi.ham, "sure-adlari-vikipedi": bozuk}))
    assert bulgu_var(sonuc, "yonlendirmeler-01.json ham dosya kilitle tutmuyor")
    eksik = {k: v for k, v in girdi.ham["quran-meta"].items() if k != "quran-meta-7.0.0.tgz"}
    assert bulgu_var(
        g_kay(dataclasses.replace(girdi, ham={**girdi.ham, "quran-meta": eksik})), "ham dosyada yok"
    )
    kayit = dataclasses.replace(girdi.kayit, atif_metni=" ")
    assert bulgu_var(g_kay(dataclasses.replace(girdi, kayit=kayit)), "atif_metni bos")
    adres = dataclasses.replace(girdi.kayit, kaynak_url="https://baska.invalid/")
    assert bulgu_var(g_kay(dataclasses.replace(girdi, kayit=adres)), "kaynak_url")
    surum = dataclasses.replace(girdi.kayit, surum="revizyon 1")
    assert bulgu_var(g_kay(dataclasses.replace(girdi, kayit=surum)), "revizyon numarasini anmiyor")
    meta = dataclasses.replace(girdi.diger_kayitlar["quran-meta"], surum="1.0.0")
    diger = {**girdi.diger_kayitlar, "quran-meta": meta}
    assert bulgu_var(g_kay(dataclasses.replace(girdi, diger_kayitlar=diger)), "surumu kilit")


def test_kapi_bulgulari_ad_metni_tasimaz(girdi: SureAdlariGirdisi) -> None:
    gizli = "GIZLI-DENEME-ADI"
    g = satirlari_degistir(
        girdi, lambda v: v["surah_no"] == 3 and v["kind"] == "kanonik", alias=gizli
    )
    for islev in (g_but, g_kay):
        for bulgu in islev(g).bulgular:
            assert gizli not in bulgu and bulgu.isascii()


def test_olcumler_capraz_sure_anahtar_ve_tanzil_fark(girdi: SureAdlariGirdisi) -> None:
    olcum = olcumler(girdi)
    assert olcum["capraz_sure_anahtar"] == {}
    tanzil = [dict(t) for t in girdi.tanzil]
    tanzil[0]["order"] = 99
    # staged'de isaret yok ama olcum staged'deki isaretlerden okunur: bos kalir
    assert olcumler(dataclasses.replace(girdi, tanzil=tanzil))["tanzil_fark_sure"] == []
