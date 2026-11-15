"""Lugat kaynaklari QA kapilari (A20.6b; SENTETIK veri, veritabani yok)."""

import copy
import dataclasses
import json
from pathlib import Path

import pytest
from lugat_kaynak_yardimci import (
    NFD_TANIM,
    TANIM_RG,
    TANIM_RNK,
    KaynakKoku,
    kaynak_hazirla,
    tam_zincir,
)

from mutalaa_pipeline.ingest import lugat_kaynak
from mutalaa_pipeline.ingest.lugat_kaynak import KAYNAK_RGANEYEV, KAYNAK_RNK
from mutalaa_pipeline.ingest.lugat_madde import madde_hash
from mutalaa_pipeline.qa import KAPILAR, kaynak_kapilari, run_risale_lugat
from mutalaa_pipeline.qa.checks.risale_lugat import KAYNAK_KAPI_ISLEVLERI, KaynakGirdisi
from mutalaa_pipeline.qa.checks.risale_lugat_kaynak import (
    g_but,
    g_cap,
    g_kay,
    g_nor,
    olcumler,
)
from mutalaa_pipeline.staged import Satir


@pytest.fixture
def kz(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> KaynakKoku:
    kok = kaynak_hazirla(tmp_path, monkeypatch)
    tam_zincir(kok)
    return kok


def girdi(kz: KaynakKoku, slug: str) -> KaynakGirdisi:
    ctx = kz.lk.ctx("qa", [slug])
    kayitlar = ctx.require_sources(run_risale_lugat.kaynak_idleri(slug))
    return run_risale_lugat.yukle_kaynak(ctx, slug, kayitlar, run=None)[0]


def degistir(g: KaynakGirdisi, baslik: str, no: int = 1, **alanlar: object) -> KaynakGirdisi:
    """Bir maddenin alanlarini degistirir (derin kopya)."""
    liste = list(g.satirlar)
    (i,) = [
        i for i, s in enumerate(liste) if s.veri["basliksoz"] == baslik and s.veri["anlam_no"] == no
    ]
    ilk = liste[i]
    liste[i] = Satir(ilk.etiket, ilk.no, {**copy.deepcopy(ilk.veri), **alanlar})
    return dataclasses.replace(g, satirlar=liste)


def bulgular(kapi: str, g: KaynakGirdisi) -> tuple[str, ...]:
    return KAYNAK_KAPI_ISLEVLERI[kapi](g).bulgular


# --- komut ve rapor ----------------------------------------------------------------------------


@pytest.mark.parametrize("slug", [KAYNAK_RNK, KAYNAK_RGANEYEV])
def test_dort_kapi_gecer_rapor_kapilari_ve_sayilar(kz: KaynakKoku, slug: str) -> None:
    assert kz.qa(slug) == 0
    raporlar = [
        json.loads(p.read_bytes())
        for p in sorted((kz.veri_kok / "reports").glob("*.json"), key=lambda p: p.name)
    ]
    rapor = [r for r in raporlar if r.get("komut") == "qa run" and r.get("kaynak") == slug][-1]
    assert rapor["cikis_kodu"] == 0
    assert rapor["kapilar"] == {k: "gecti" for k in KAPILAR}
    assert rapor["kapi_sayilari"]["G-CAP"]["uygulanmaz"] == 1
    assert rapor["anchor_run_id"] == rapor["zincir"]["ingest"]
    assert len(rapor["units_sha256"]) == 64
    assert rapor["olcumler"]["madde"] == (8 if slug == KAYNAK_RNK else 5)
    metin = json.dumps(rapor)
    for imza in (TANIM_RNK, TANIM_RG, "denemea", "denemed", "rgyeni"):
        assert imza not in metin  # rapor metin tasimaz
    assert kaynak_kapilari(slug) == KAPILAR  # `export pg` dort kapi bekler


def test_rnk_olcumleri_yalniz_sayi(kz: KaynakKoku) -> None:
    o = olcumler(girdi(kz, KAYNAK_RNK))
    assert o["madde"] == 8 and o["benzersiz_baslik"] == 7
    assert o["cok_anlamli_baslik"] == 1 and o["en_cok_anlam"] == 2
    assert o["duzey"] == {"1": 3, "2": 1, "3": 1, "4": 3}
    assert o["risale_eslesen_madde"] == 5 and o["risale_eslesmeyen_madde"] == 3


@pytest.mark.parametrize("slug", [KAYNAK_RNK, KAYNAK_RGANEYEV])
def test_ingest_yoksa_cikis_2(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, slug: str) -> None:
    kok = kaynak_hazirla(tmp_path, monkeypatch)
    assert kok.qa(slug) == 2


def test_gate_kismi_kosu_ve_bilinmeyen_kapi(kz: KaynakKoku) -> None:
    assert kz.qa(KAYNAK_RNK, gate=["G-KAY"]) == 0
    assert kz.qa(KAYNAK_RNK, gate=["G-HIZ"]) == 2


def test_staged_ozeti_manifestle_tutmazsa_cikis_2(kz: KaynakKoku) -> None:
    dosya = kz.staged_klasorleri(KAYNAK_RNK)[-1] / "lugat.jsonl"
    dosya.write_bytes(dosya.read_bytes() + b"\n")
    assert kz.qa(KAYNAK_RNK) == 2


def test_ham_dosya_ozeti_manifestle_tutmazsa_cikis_2(kz: KaynakKoku) -> None:
    ham = next((kz.veri_kok / "raw" / KAYNAK_RNK).rglob("lugat.txt"))
    ham.write_bytes(ham.read_bytes() + b"x")
    assert kz.qa(KAYNAK_RNK) == 2


def test_risale_staged_girdisi_ozeti_tutmazsa_cikis_2(kz: KaynakKoku) -> None:
    kf = next((kz.veri_kok / "staged" / "risale-kelime-frekans").rglob("lugat.jsonl"))
    kf.write_bytes(kf.read_bytes() + b"\n")
    assert kz.qa(KAYNAK_RNK) == 2


def test_kaynak_kapilari_kalirsa_cikis_1(kz: KaynakKoku, monkeypatch: pytest.MonkeyPatch) -> None:
    yol = lugat_kaynak.KILIT_YOLLARI[KAYNAK_RNK]
    kilit = json.loads(yol.read_bytes())
    kilit["sayilar"]["bozuk_nul"] += 1  # kilit sayisi artik tutmuyor
    yol.write_bytes(json.dumps(kilit).encode())
    assert kz.qa(KAYNAK_RNK) == 1


# --- G-KAY ---------------------------------------------------------------------------------------


def test_g_kay_gecer_ve_kayit_kilit_tutarsizligini_yakalar(kz: KaynakKoku) -> None:
    g = girdi(kz, KAYNAK_RGANEYEV)
    assert bulgular("G-KAY", g) == ()
    kotu = dataclasses.replace(g, kayit=dataclasses.replace(g.kayit, surum="c" * 40))
    assert any("kayit_surumu" in b for b in g_kay(kotu).bulgular)
    kotu = dataclasses.replace(g, kayit=dataclasses.replace(g.kayit, kaynak_url="https://baska"))
    assert any("kaynak_url" in b for b in g_kay(kotu).bulgular)
    kotu = dataclasses.replace(g, kayit=dataclasses.replace(g.kayit, atif_metni="  "))
    assert any("atif_metni" in b for b in g_kay(kotu).bulgular)
    kotu = dataclasses.replace(g, ham=g.ham + b"x")
    assert any("sha256 ve boyutla tutmuyor" in b for b in g_kay(kotu).bulgular)
    assert g.bagimli_kayit is not None
    kotu = dataclasses.replace(
        g, bagimli_kayit=dataclasses.replace(g.bagimli_kayit, atif_metni="\n")
    )
    assert any(KAYNAK_RNK in b and "atif_metni" in b for b in g_kay(kotu).bulgular)
    kotu = dataclasses.replace(g, rnk_ham=(g.rnk_ham or b"") + b"x")
    assert any(KAYNAK_RNK in b for b in g_kay(kotu).bulgular)
    assert g.rnk_kilit is not None
    kotu = dataclasses.replace(g, kilit=dataclasses.replace(g.kilit, bagimli_sha256="0" * 64))
    assert any("RNK kilidiyle" in b for b in g_kay(kotu).bulgular)


# --- G-BUT: tanim bayt esitligi, anlam_no, anlam sizintisi ---------------------------------------


def test_g_but_gecer_iki_kaynak(kz: KaynakKoku) -> None:
    for slug in (KAYNAK_RNK, KAYNAK_RGANEYEV):
        assert bulgular("G-BUT", girdi(kz, slug)) == ()


def test_g_but_tanim_degisirse_bayt_esitligi_bozulur(kz: KaynakKoku) -> None:
    g = girdi(kz, KAYNAK_RNK)
    kotu = degistir(g, "denemea", 1, tanim_tr=f"{TANIM_RNK}-1 DEGISTI")
    assert any("tanimi kaynak satiriyla bayt esit degil" in b for b in bulgular("G-BUT", kotu))


def test_g_but_nfc_uygulanmis_tanim_yakalanir(kz: KaynakKoku) -> None:
    import unicodedata

    g = girdi(kz, KAYNAK_RNK)
    nfc = unicodedata.normalize("NFC", NFD_TANIM)
    assert nfc != NFD_TANIM
    kotu = degistir(g, "yenia", 1, tanim_tr=nfc, content_hash=madde_hash("yenia", nfc))
    assert any("bayt esit degil" in b for b in bulgular("G-BUT", kotu))


def test_g_but_kirpilmamis_tanim_yakalanir(kz: KaynakKoku) -> None:
    g = girdi(kz, KAYNAK_RNK)
    bosluklu = f"{TANIM_RNK}-1 "
    kotu = degistir(
        g, "denemea", 1, tanim_tr=bosluklu, content_hash=madde_hash("denemea", bosluklu)
    )
    assert any("kirpma kurali" in b for b in bulgular("G-BUT", kotu))


def test_g_but_bos_tanim_ve_hash(kz: KaynakKoku) -> None:
    g = girdi(kz, KAYNAK_RNK)
    assert any("tanim_tr bos" in b for b in bulgular("G-BUT", degistir(g, "denemea", tanim_tr="")))
    assert any(
        "content_hash" in b
        for b in bulgular("G-BUT", degistir(g, "denemea", content_hash="a" * 64))
    )
    assert any(
        "tanim_tr bos" in b for b in bulgular("G-BUT", degistir(g, "denemea", tanim_tr=None))
    )


def test_g_but_eksik_ve_fazla_madde(kz: KaynakKoku) -> None:
    g = girdi(kz, KAYNAK_RNK)
    eksik = dataclasses.replace(g, satirlar=list(g.satirlar)[1:])
    b = bulgular("G-BUT", eksik)
    assert any("eksik" in x for x in b) and any("kilitteki alinan" in x for x in b)
    ek = Satir(g.satirlar[0].etiket, 99, {**g.satirlar[0].veri, "basliksoz": "yenic"})
    fazla = dataclasses.replace(g, satirlar=[*g.satirlar, ek])
    assert any("fazla" in x for x in bulgular("G-BUT", fazla))


def test_g_but_anlam_no_ardisik_degilse_kalir(kz: KaynakKoku) -> None:
    g = girdi(kz, KAYNAK_RNK)
    kotu = degistir(g, "denemea", 2, anlam_no=3)
    assert any("anlam_no" in b and "ardisik" in b for b in bulgular("G-BUT", kotu))
    sifir = degistir(g, "denemea", 2, anlam_no=0)
    assert any("anlam_no tam sayi degil ya da aralik" in b for b in bulgular("G-BUT", sifir))


def test_g_but_yinelenen_ve_sirasiz_satir(kz: KaynakKoku) -> None:
    g = girdi(kz, KAYNAK_RNK)
    ters = dataclasses.replace(g, satirlar=list(reversed(g.satirlar)))
    assert any("sirali degil" in b for b in bulgular("G-BUT", ters))
    cift = dataclasses.replace(g, satirlar=[*g.satirlar, g.satirlar[0]])
    assert any("yinelenen" in b for b in bulgular("G-BUT", cift))


@pytest.mark.parametrize(
    "sizinti",
    [
        {"anlam": "ANLAM-X"},
        {"anlam_basvuru": [{"anlam": "ANLAM-X", "sayi": 1}]},
        {"tanim": f"{TANIM_RNK}-1"},
        {"baska": "ANLAM-X"},
    ],
)
def test_g_but_kaynaklar_icinde_anlam_dizesi_yok(
    kz: KaynakKoku, sizinti: dict[str, object]
) -> None:
    g = girdi(kz, KAYNAK_RNK)
    mevcut = g.satirlar[0].veri["kaynaklar"]
    assert isinstance(mevcut, dict)
    baslik = str(g.satirlar[0].veri["basliksoz"])
    no = int(str(g.satirlar[0].veri["anlam_no"]))
    kotu = degistir(g, baslik, no, kaynaklar={**mevcut, **sizinti})
    assert any("anlam" in b or "kaynaklar" in b for b in bulgular("G-BUT", kotu))


def test_g_but_risale_basliksozu_listede_yoksa_sizinti_sayilir(kz: KaynakKoku) -> None:
    g = girdi(kz, KAYNAK_RNK)
    eslesen = next(s for s in g.satirlar if s.veri["duzey"] == 1)
    kaynaklar = {**eslesen.veri["kaynaklar"], "risale_basliksoz": f"{TANIM_RNK}-1"}  # type: ignore[dict-item]
    kotu = degistir(
        g, str(eslesen.veri["basliksoz"]), int(str(eslesen.veri["anlam_no"])), kaynaklar=kaynaklar
    )
    assert any("anlam ya da tanim dizesi" in b for b in bulgular("G-BUT", kotu))


def test_g_but_duzey_ve_sabitler(kz: KaynakKoku) -> None:
    g = girdi(kz, KAYNAK_RNK)
    assert any("duzey" in b for b in bulgular("G-BUT", degistir(g, "denemea", duzey=3)))
    assert any("duzey" in b for b in bulgular("G-BUT", degistir(g, "yenia", duzey=1)))
    assert any("sabit" in b for b in bulgular("G-BUT", degistir(g, "denemea", origin="hat")))
    assert any("sabit" in b for b in bulgular("G-BUT", degistir(g, "denemea", status="onayli")))
    assert any("sabit" in b for b in bulgular("G-BUT", degistir(g, "denemea", version=2)))
    eksik_alan = dataclasses.replace(
        g,
        satirlar=[Satir("x", 1, {"basliksoz": "denemea"}), *list(g.satirlar)[1:]],
    )
    assert any("alan kumesi" in b for b in bulgular("G-BUT", eksik_alan))


def test_g_but_eslesen_maddede_siklik_toplami_kitaplarla_tutmali(kz: KaynakKoku) -> None:
    g = girdi(kz, KAYNAK_RNK)
    eslesen = next(s for s in g.satirlar if s.veri["duzey"] == 2)
    kaynaklar = {**eslesen.veri["kaynaklar"], "siklik": 31}  # type: ignore[dict-item]
    kotu = degistir(
        g, str(eslesen.veri["basliksoz"]), int(str(eslesen.veri["anlam_no"])), kaynaklar=kaynaklar
    )
    assert any("kaynaklar bicimi" in b for b in bulgular("G-BUT", kotu))


def test_g_but_rganeyevde_rnkdaki_baslik_alinmis_olamaz(kz: KaynakKoku) -> None:
    g = girdi(kz, KAYNAK_RGANEYEV)
    ilk = dict(g.satirlar[0].veri)
    ek = Satir(g.satirlar[0].etiket, 99, {**ilk, "basliksoz": "denemea", "anlam_no": 1})
    kotu = dataclasses.replace(g, satirlar=[*g.satirlar, ek])
    assert any("rnk-cakisma" in b for b in bulgular("G-BUT", kotu))


def test_g_but_kilit_sayisi_tutmazsa_kalir(kz: KaynakKoku) -> None:
    g = girdi(kz, KAYNAK_RNK)
    sayilar = {**g.kilit.sayilar, "cok_anlamli_baslik": 5}
    kotu = dataclasses.replace(g, kilit=dataclasses.replace(g.kilit, sayilar=sayilar))
    assert any("sayilar kilitle tutmuyor" in b for b in bulgular("G-BUT", kotu))


def test_g_but_staged_ham_dosyadan_uretilenle_ayni_olmali(kz: KaynakKoku) -> None:
    g = girdi(kz, KAYNAK_RNK)
    kalan = [s for s in g.risale_satirlari if s.veri["basliksoz"] != "denemeb"]
    kotu = dataclasses.replace(g, risale_satirlari=kalan)
    # Kelime-Frekans satirlari eksilince eslesme/duzey yeniden uretimle tutmaz
    assert any("yeniden uretilenle ayni degil" in b for b in bulgular("G-BUT", kotu))


# --- G-CAP ve G-NOR -----------------------------------------------------------------------------


def test_g_cap_uygulanmaz_capa_alani_varsa_kalir(kz: KaynakKoku) -> None:
    g = girdi(kz, KAYNAK_RNK)
    assert g_cap(g).gecti and g_cap(g).sayilar["uygulanmaz"] == 1
    assert not g_cap(degistir(g, "denemea", anchor="q:1:1")).gecti


def test_g_nor_bos_ya_da_farkli_norm_kalir(kz: KaynakKoku) -> None:
    g = girdi(kz, KAYNAK_RNK)
    assert g_nor(g).gecti
    assert any(
        "norm-bos" in b for b in bulgular("G-NOR", degistir(g, "denemea", basliksoz_norm=""))
    )
    assert any(
        "norm-fark" in b for b in bulgular("G-NOR", degistir(g, "denemea", basliksoz_norm="x"))
    )


def test_butun_kapilar_kayitli(kz: KaynakKoku) -> None:
    assert tuple(KAYNAK_KAPI_ISLEVLERI) == KAPILAR
    g = girdi(kz, KAYNAK_RNK)
    assert g_but(g).sayilar["madde"] == 8
    assert g_kay(g).sayilar["kaynak_kaydi"] == 1
    assert g_kay(girdi(kz, KAYNAK_RGANEYEV)).sayilar["kaynak_kaydi"] == 2
