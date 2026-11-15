# ruff: noqa: RUF001
"""Risale icindekiler karsilastirma testleri (A20.2b; ACIKCA SENTETIK veri).

Basliklar "Deneme Baslik N" ve "Deneme Bolum ..." yer tutuculari; hicbir Risale basligi yoktur.
Gercek `data/` kullanilmaz.
"""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from mutalaa_pipeline import cli, cli_risale_rapor
from mutalaa_pipeline.anchor.risale import (
    Bolunme,
    BolunmeParcasi,
    Kitap,
    RnkBaglanti,
)
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.ingest.risale_rnk_staged import Dugum, JsonBilgisi
from mutalaa_pipeline.qa import risale_raporlari as rr
from mutalaa_pipeline.qa.risale_raporlari import Baslik

# --- baslik anahtari -----------------------------------------------------------------------


def test_karsilastirma_baslik_normalize_turkce_i() -> None:
    assert rr.baslik_normalize("İKİNCİ BAŞLIK") == "ikincibaslik"
    assert rr.baslik_normalize("IŞIK İŞİK ışık") == "isikisikisik"
    assert rr.baslik_normalize("Deneme") == rr.baslik_normalize("DENEME")


def test_karsilastirma_baslik_normalize_bosluk_isaret_ve_kesme() -> None:
    assert rr.baslik_normalize("On Dördüncü Bölüm") == rr.baslik_normalize("Ondördüncü Bölüm")
    assert rr.baslik_normalize("Âlem'in Deneme-si") == "alemindenemesi"
    assert rr.baslik_normalize("  ...  ") == ""
    assert rr.baslik_normalize("") == ""


def test_karsilastirma_baslik_normalize_bas_rakam_sira_sozcugu() -> None:
    assert rr.baslik_normalize("1. Bölüm") == rr.baslik_normalize("Birinci Bölüm")
    assert rr.baslik_normalize("11 Bölüm") == rr.baslik_normalize("Onbirinci Bölüm")
    assert rr.baslik_normalize("23. Bölüm") == rr.baslik_normalize("Yirmi Üçüncü Bölüm")
    assert rr.baslik_normalize("100 Bölüm") == "100bolum"  # 1-99 disinda rakam kalir
    assert rr.baslik_normalize("Bölüm 1") == "bolum1"  # yalniz bas rakam


@pytest.mark.parametrize(
    ("n", "sira"),
    [(1, "birinci"), (9, "dokuzuncu"), (10, "onuncu"), (20, "yirminci"), (37, "otuzyedinci"),
     (99, "doksandokuzuncu")],
)  # fmt: skip
def test_karsilastirma_sira_sozcugu(n: int, sira: str) -> None:
    assert rr.sira_sozcugu(n) == sira


def test_karsilastirma_sira_sozcugu_aralik_disi() -> None:
    assert rr.sira_sozcugu(0) is None
    assert rr.sira_sozcugu(100) is None


def test_karsilastirma_baslik_adaylari_rakam_onekisiz_aday() -> None:
    assert rr.baslik_adaylari("1.  Deneme Baslik") == ("birincidenemebaslik", "denemebaslik")
    assert rr.baslik_adaylari("Deneme Baslik") == ("denemebaslik",)
    assert rr.baslik_adaylari("", "...") == ()
    assert rr.baslik_adaylari("Bir", "#11") == ("bir",)  # sayfa gonderimi aday degil


# --- eslestirme ----------------------------------------------------------------------------


def basliklar(*metinler: str, onek: str = "r") -> list[Baslik]:
    return [Baslik(f"{onek}{i}", rr.baslik_adaylari(m)) for i, m in enumerate(metinler)]


def test_karsilastirma_eslestir_esit_listeler_ve_sira_farki() -> None:
    sol = basliklar("Deneme Bir", "Deneme Iki", "Deneme Uc")
    sag = basliklar("Deneme Uc", "Deneme Bir", "Deneme Iki", onek="e")
    e = rr.eslestir(sol, sag)
    assert len(e.eslesen) == 3 and e.farkli == [] and e.yalniz_sol == [] and e.yalniz_sag == []


def test_karsilastirma_eslestir_tekrarlayan_baslik_adet_kadar() -> None:
    sol = basliklar("Deneme Nokta", "Deneme Nokta", "Deneme Nokta")
    sag = basliklar("Deneme Nokta", "Deneme Nokta", onek="e")
    e = rr.eslestir(sol, sag)
    assert len(e.eslesen) == 2 and e.yalniz_sol == ["r2"] and e.yalniz_sag == []


def test_karsilastirma_eslestir_yazim_farki_ve_yalniz_basliklar() -> None:
    sol = basliklar("Deneme Bolum Alti", "Yalniz Solda Baslik")
    sag = basliklar("Deneme Bolum Altisi", "Yalniz Sagda Farkli Cok Baska", onek="e")
    e = rr.eslestir(sol, sag)
    assert e.eslesen == []
    assert e.farkli == [("r0", "e0")]  # fuzz.ratio >= esik
    assert e.yalniz_sol == ["r1"] and e.yalniz_sag == ["e1"]


def test_karsilastirma_eslestir_onek_farkli_yazilan_sayilir() -> None:
    sol = basliklar("Deneme Bolum")
    sag = basliklar("Deneme Bolum Ek Aciklama Uzun Baslik", onek="e")
    e = rr.eslestir(sol, sag)
    assert e.farkli == [("r0", "e0")]


def test_karsilastirma_eslestir_rakam_adaylari() -> None:
    sol = basliklar("Deneme Baslik")  # RNK numarasiz
    sag = basliklar("1.  Deneme Baslik", onek="e")  # eRisale numarali
    assert len(rr.eslestir(sol, sag).eslesen) == 1
    sol2 = basliklar("1 Nokta")
    sag2 = basliklar("Birinci Nokta", onek="e")
    assert len(rr.eslestir(sol2, sag2).eslesen) == 1


def test_karsilastirma_eslestir_adaysiz_basliklar_dislanir() -> None:
    sol = [Baslik("r0", ()), *basliklar("Deneme Bir", onek="s")]
    e = rr.eslestir(sol, basliklar("Deneme Bir", onek="e"))
    assert len(e.eslesen) == 1 and e.yalniz_sol == []


def test_karsilastirma_eslesme_ozeti_sayilar_tutarli() -> None:
    sol = basliklar("Deneme A", "Deneme B", "Zz Yalniz")
    sag = basliklar("Deneme A", "Deneme B", "Baska Yalniz Qq", "Fazla Qq Ww", onek="e")
    e = rr.eslestir(sol, sag)
    ozet = rr.eslesme_ozeti(e, 3, 4, "rnk", "erisale")
    assert ozet["eslesen"] == 2
    assert ozet["sayilar_tutarli"] is True
    assert ozet["eslesme_orani"] == round(2 / 3, 6)
    assert ozet["rnk_baslik"] == 3 and ozet["erisale_baslik"] == 4
    assert rr.eslesme_ozeti(e, 5, 4, "rnk", "erisale")["sayilar_tutarli"] is False


def test_karsilastirma_eslesme_ozeti_bos_sol_oran_yok() -> None:
    ozet = rr.eslesme_ozeti(rr.eslestir([], []), 0, 0, "json", "staged")
    assert ozet["karsilik_orani"] is None and ozet["eslesme_orani"] is None


# --- onerilen_dogrulandi esigi -------------------------------------------------------------


def ozet(oran: float | None, tutarli: bool = True) -> dict[str, object]:
    return {"karsilik_orani": oran, "sayilar_tutarli": tutarli}


def test_karsilastirma_onerilen_dogrulandi_esik() -> None:
    assert rr.onerilen_dogrulandi(
        slug="deneme", json_dugum=20, staged=ozet(0.95), erisale=ozet(1.0)
    ) == (True, [])
    ok, gerekce = rr.onerilen_dogrulandi(
        slug="deneme", json_dugum=20, staged=ozet(0.949), erisale=ozet(1.0)
    )
    assert not ok and gerekce == ["staged_orani_dusuk"]
    ok, gerekce = rr.onerilen_dogrulandi(
        slug="deneme", json_dugum=20, staged=ozet(1.0), erisale=ozet(0.5)
    )
    assert not ok and gerekce == ["erisale_orani_dusuk"]


def test_karsilastirma_onerilen_dogrulandi_erisalesiz_yalniz_staged() -> None:
    assert rr.onerilen_dogrulandi(slug="deneme", json_dugum=9, staged=ozet(1.0), erisale=None)[0]


def test_karsilastirma_onerilen_dogrulandi_diger_engeller() -> None:
    ok, g = rr.onerilen_dogrulandi(slug="deneme", json_dugum=4, staged=ozet(1.0), erisale=None)
    assert not ok and g == ["yetersiz_dugum"]
    ok, g = rr.onerilen_dogrulandi(slug="deneme", json_dugum=0, staged=ozet(None), erisale=None)
    assert not ok and g == ["json_dugum_yok", "staged_orani_dusuk"]
    ok, g = rr.onerilen_dogrulandi(
        slug="deneme", json_dugum=20, staged=ozet(1.0, tutarli=False), erisale=None
    )
    assert not ok and g == ["staged_sayilar_tutarsiz"]
    for slug in rr.SLUG_BELIRSIZ:
        ok, g = rr.onerilen_dogrulandi(slug=slug, json_dugum=50, staged=ozet(1.0), erisale=None)
        assert not ok and g == ["slug_belirsiz"]


# --- girdi okuma ---------------------------------------------------------------------------


def dugum(sira: int, baslik: str, sayfa: int, kitapta: str = "") -> Dugum:
    return Dugum(sira, baslik, kitapta, sayfa, 1, 0, frozenset())


def json_bilgisi(*dugumler: Dugum) -> JsonBilgisi:
    kok = dugum(0, "", 1)
    return JsonBilgisi("deneme", "tr_k", 1, 99, (kok, *dugumler))


def kitap_kaydi(
    slug: str, uid: str = "deneme", raf: str = "tr_k", bolunme: Bolunme | None = None
) -> Kitap:
    return Kitap(
        slug=slug,
        baslik="Deneme",
        dil="tr",
        yon="ltr",
        metin_kaynagi="rnk",
        diyanet_karsiligi="rnk",
        diyanet=None,
        rnk=RnkBaglanti(raf, uid, "Deneme", bolunme),
        dogrulandi=False,
    )


def test_karsilastirma_json_basliklari_bolunme_sayfaya_gore() -> None:
    bolunme = Bolunme(
        son_sayfa=99,
        parcalar=(
            BolunmeParcasi("deneme-a", 5),
            BolunmeParcasi("deneme-b", 40),
            BolunmeParcasi("deneme-c", 70),
        ),
    )
    bilgi = json_bilgisi(
        dugum(1, "Deneme A1", 5),
        dugum(2, "Deneme A2", 39),
        dugum(3, "Deneme B1", 40),
        dugum(4, "Deneme C1", 70),
        dugum(5, "", 71, kitapta=""),
    )
    kimlikler = {}
    for slug in ("deneme-a", "deneme-b", "deneme-c"):
        kitap = kitap_kaydi(slug, bolunme=bolunme)
        liste, basliksiz = rr.json_basliklari(bilgi, slug, kitap)
        kimlikler[slug] = ([b.ref for b in liste], basliksiz)
    assert kimlikler == {
        "deneme-a": ([1, 2], 0),
        "deneme-b": ([3], 0),
        "deneme-c": ([4], 1),
    }


def test_karsilastirma_json_basliklari_textinbook_adayi() -> None:
    bilgi = json_bilgisi(dugum(1, "", 3, kitapta="Deneme Baslik"))
    liste, basliksiz = rr.json_basliklari(bilgi, "deneme", kitap_kaydi("deneme"))
    assert basliksiz == 0 and liste[0].adaylar == ("denemebaslik",)


def erisale_yaz(yol: Path, ogeler: list[dict[str, object]]) -> Path:
    yol.parent.mkdir(parents=True, exist_ok=True)
    yol.write_text(json.dumps(ogeler), encoding="utf-8")
    return yol


def toc(kimlik: int, kitap: str, baslik: str, duzey: int) -> dict[str, object]:
    return {"id": kimlik, "bookId": kitap, "title": baslik, "level": duzey}


def test_karsilastirma_erisale_oku_kok_ve_kulliyat_atlanir(tmp_path: Path) -> None:
    yol = erisale_yaz(
        tmp_path / "toc.json",
        [
            toc(0, "kulliyat", "Deneme Kulliyat", -1),
            toc(1, "deneme", "Deneme Kitap", 0),
            toc(2, "deneme", "Deneme Baslik 1", 1),
            toc(3, "deneme", "Deneme Baslik 2", 2),
        ],
    )
    kitaplar = rr.erisale_oku(yol)
    assert list(kitaplar) == ["deneme"]
    assert [b.ref for b in kitaplar["deneme"]] == [2, 3]


@pytest.mark.parametrize(
    "icerik",
    [b"[bozuk", b'{"a": 1}', b"[1, 2]", b'[{"id": 1, "bookId": "x", "title": 3, "level": 1}]'],
)
def test_karsilastirma_erisale_oku_gecersiz_girdi(tmp_path: Path, icerik: bytes) -> None:
    yol = tmp_path / "toc.json"
    yol.write_bytes(icerik)
    with pytest.raises(GirdiHatasi):
        rr.erisale_oku(yol)


def test_karsilastirma_staged_basliklari_yalniz_baslik_birimleri(tmp_path: Path) -> None:
    satirlar = [
        {
            "anchor": "rn:deneme:p1",
            "attrs": {"kind": "baslik", "slug": "deneme"},
            "text": "Deneme Bir",
        },
        {
            "anchor": "rn:deneme:p2",
            "attrs": {"kind": "paragraf", "slug": "deneme"},
            "text": "baslik gecer",
        },
        {
            "anchor": "rn:diger:p1",
            "attrs": {"kind": "baslik", "slug": "diger"},
            "text": "Deneme Iki",
        },
        {"anchor": "rn:deneme:p3", "attrs": {"kind": "baslik", "slug": "deneme"}, "text": "..."},
    ]
    yol = tmp_path / "units.jsonl"
    yol.write_text("".join(json.dumps(s) + "\n" for s in satirlar), encoding="utf-8")
    sonuc = rr.staged_basliklari(yol, ["deneme"])
    assert list(sonuc) == ["deneme"]
    assert [b.ref for b in sonuc["deneme"]] == ["rn:deneme:p1"]  # "..." adaysiz


def test_karsilastirma_son_tarih(tmp_path: Path) -> None:
    for ad in ("2026-11-12", "2026-11-13", "2025-01-01"):
        (tmp_path / ad).mkdir()
    (tmp_path / "SHA256SUMS").write_bytes(b"")
    assert rr.son_tarih(tmp_path) == "2026-11-13"
    with pytest.raises(GirdiHatasi, match="bulunamadi"):
        rr.son_tarih(tmp_path / "2026-11-12")


# --- rapor ---------------------------------------------------------------------------------


def sentetik_rapor() -> dict[str, object]:
    kayit_a = kitap_kaydi("deneme-a", uid="uid-a")
    emirdag_1 = kitap_kaydi("emirdag-lahikasi-1", uid="uid-e1")
    emirdag_2 = kitap_kaydi("emirdag-lahikasi-2", uid="uid-e2")
    tablo = (kayit_a, emirdag_1, emirdag_2)
    adlar = [f"Deneme Bolum {c}" for c in "ABCDEFGHIJ"]
    rnk_json = {
        "tr_k/uid-a": json_bilgisi(*[dugum(i + 1, ad, i + 1) for i, ad in enumerate(adlar)]),
        "tr_k/uid-e1": json_bilgisi(*[dugum(i + 1, ad, i + 1) for i, ad in enumerate(adlar[:5])]),
        "tr_k/uid-e2": json_bilgisi(*[dugum(i + 1, ad, i + 1) for i, ad in enumerate(adlar[5:])]),
    }
    staged = {
        "deneme-a": basliklar(*adlar, "Fazla Staged Baslik Zz", onek="rn:deneme-a:p"),
        "emirdag-lahikasi-1": basliklar(*adlar[:5], onek="rn:e1:p"),
        "emirdag-lahikasi-2": basliklar(*adlar[5:9], "Yalniz Baska Qq", onek="rn:e2:p"),
    }
    erisale = {
        "deneme-a": basliklar(*adlar, "Ince Taneli Ek Baslik", onek="e"),
        "emirdag-lahikasi": basliklar(*adlar, onek="g"),
    }
    return rr.rapor_uret(tablo, rnk_json, staged, erisale, {"staged_rnk": "deneme/run"})


def test_karsilastirma_rapor_icindekiler_yapisi() -> None:
    rapor = sentetik_rapor()
    satirlar = {s["slug"]: s for s in rapor["kitaplar"]}  # type: ignore[attr-defined,union-attr]
    assert list(satirlar) == ["deneme-a", "emirdag-lahikasi-1", "emirdag-lahikasi-2"]
    gruplar = rapor["erisale_gruplari"]
    assert isinstance(gruplar, dict) and set(gruplar) == {"deneme-a", "emirdag-lahikasi"}
    emirdag = gruplar["emirdag-lahikasi"]
    assert emirdag["slug"] == ["emirdag-lahikasi-1", "emirdag-lahikasi-2"]
    assert emirdag["rnk_baslik"] == 10 and emirdag["eslesen"] == 10
    assert gruplar["deneme-a"]["yalniz_erisale"] == 1  # eRisale daha ince taneli: sayilir
    assert gruplar["deneme-a"]["karsilik_orani"] == 1.0

    a = satirlar["deneme-a"]
    assert a["json_staged"]["eslesen"] == 10 and a["json_staged"]["yalniz_staged"] == 1
    assert a["onerilen_dogrulandi"] is True and a["dayanak"] == "erisale+staged"
    assert a["mevcut_dogrulandi"] is False  # tablodaki alan degismez
    e2 = satirlar["emirdag-lahikasi-2"]
    assert e2["erisale_grup"] == "emirdag-lahikasi"
    assert e2["json_staged"]["yalniz_staged"] == 1
    assert e2["onerilen_dogrulandi"] is False  # 4 / 5 = 0.8 < 0.95
    assert e2["gerekce"] == ["staged_orani_dusuk"]
    ozet_ = rapor["ozet"]
    assert ozet_["kitap"] == 3  # type: ignore[index]
    assert ozet_["onerilen_dogrulandi_true"] + ozet_["onerilen_dogrulandi_false"] == 3  # type: ignore[index]


def test_karsilastirma_rapor_baslik_metni_sizdirmaz() -> None:
    govde = json.dumps(sentetik_rapor(), ensure_ascii=False)
    for sizinti in ("Deneme Bolum", "Ince Taneli", "Fazla Staged", "Yalniz Baska"):
        assert sizinti not in govde
    assert "rn:deneme-a:p10" in govde  # yalniz staged capa


def test_karsilastirma_rapor_eksik_json_hata() -> None:
    tablo = (kitap_kaydi("deneme-a", uid="yok"),)
    with pytest.raises(GirdiHatasi, match="json eksik"):
        rr.rapor_uret(tablo, {}, {}, {})
    with pytest.raises(GirdiHatasi, match="tabloda yok"):
        rr.rapor_uret(
            tablo,
            {"tr_k/yok": json_bilgisi()},
            {},
            {"bilinmeyen-kitap": basliklar("Deneme")},
        )


def test_karsilastirma_rapor_liste_siniri(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(rr, "LISTE_SINIRI", 2)
    sol = basliklar("Aa Aaa", "Bb Bbb", "Cc Ccc", "Dd Ddd")
    e = rr.eslestir(sol, [])
    ozet_ = rr.eslesme_ozeti(e, 4, 0, "json", "staged")
    assert ozet_["yalniz_json"] == 4 and len(ozet_["yalniz_json_listesi"]) == 2  # type: ignore[arg-type]


# --- CLI -----------------------------------------------------------------------------------

runner = CliRunner()


def test_karsilastirma_cli_icindekiler_dry_run_ve_yazim(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from test_sources import kok_kur

    tablo = (kitap_kaydi("deneme-a", uid="uid-a", raf="tr"),)
    monkeypatch.setattr(cli_risale_rapor.risale, "kitaplar", lambda: tablo)
    kok = kok_kur(tmp_path)
    veri = tmp_path / "data"
    monkeypatch.setenv("MUTALAA_VERI_KOK", str(veri))
    adlar = [f"Deneme Bolum {c}" for c in "ABCDEF"]
    json_yol = veri / "gelen" / "risale-baski-rnk" / "2026-11-12" / "tr" / "uid-a.json"
    json_yol.parent.mkdir(parents=True)
    agac = {
        "meta_data": {"uid": "uid-a", "shelf_id": "tr", "first_page": 1, "last_page": 9},
        "contents": {
            "title": "Deneme",
            "pageNo": 1,
            "children": [{"title": a, "pageNo": i + 1} for i, a in enumerate(adlar)],
        },
    }
    json_yol.write_text(json.dumps(agac), encoding="utf-8")
    erisale_yaz(
        veri / "gelen" / "erisale-icindekiler" / "2026-11-12" / "toc-tr.json",
        [toc(i, "deneme-a", a, 1) for i, a in enumerate(adlar, start=1)],
    )
    staged_yol = veri / "staged" / "risale-rnk-metin" / "01run" / "units.jsonl"
    staged_yol.parent.mkdir(parents=True)
    (staged_yol.parent / "manifest.json").write_text(
        json.dumps({"adim": "ingest"}), encoding="utf-8"
    )
    staged_yol.write_text(
        "".join(
            json.dumps(
                {
                    "anchor": f"rn:deneme-a:p{i}",
                    "attrs": {"kind": "baslik", "slug": "deneme-a"},
                    "text": a,
                }
            )
            + "\n"
            for i, a in enumerate(adlar, start=1)
        ),
        encoding="utf-8",
    )
    temel = ["qa", "risale-rapor", "--rapor", "icindekiler", "--kok", str(kok)]
    kuru = runner.invoke(cli.app, [*temel, "--dry-run"])
    assert kuru.exit_code == 0, kuru.output
    hedef = veri / "reports" / "a20" / "icindekiler-karsilastirma.json"
    assert not hedef.exists()
    gercek = runner.invoke(cli.app, temel)
    assert gercek.exit_code == 0, gercek.output
    rapor = json.loads(hedef.read_text(encoding="utf-8"))
    assert rapor["ozet"]["onerilen_dogrulandi_true"] == 1
    assert rapor["kaynaklar"]["staged_rnk"] == "risale-rnk-metin/01run"
    assert "Deneme Bolum" not in hedef.read_text(encoding="utf-8")


def test_karsilastirma_cli_gecersiz_rapor_cikis_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from test_sources import kok_kur

    monkeypatch.setenv("MUTALAA_VERI_KOK", str(tmp_path / "data"))
    kok = kok_kur(tmp_path)
    sonuc = runner.invoke(cli.app, ["qa", "risale-rapor", "--rapor", "yok", "--kok", str(kok)])
    assert sonuc.exit_code == 2
    eksik = runner.invoke(
        cli.app, ["qa", "risale-rapor", "--rapor", "icindekiler", "--kok", str(kok)]
    )
    assert eksik.exit_code == 2  # staged klasoru yok
