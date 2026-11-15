"""`enrich citations`, `qa run` ve `export pg --source risale-atif-dizini` (A20.7b; SENTETIK veri).

Testler VERITABANISIZDIR: anchor zinciri sentetik birimlerle kurulur ("Deneme paragrafi N ...",
Arap alfabesi harflerinden uydurulmus kelimeler), Kur'an metni uydurma bir ayet kumesidir
(`test_atif_arac.sentetik_kuran`; `kuran_metni.yukle` ona yonlendirilir), baglanti sahte bir
nesnedir (`SahteBaglanti`). Gercek Kur'an ya da Risale metni yoktur.
"""

import dataclasses
import json
from collections.abc import Callable
from pathlib import Path

import psycopg
import pytest
from hat_yardimci import ansisiz, ayarlar_kur, ctx_kur
from test_atif_arac import cumle, sentetik_kuran
from test_export_pg import Cagrilmaz, Senaryo
from test_pg_risale import KITAP, SahteBaglanti, SahteSonuc, esle, zincir_kur
from test_pg_risale import senaryo_kur as risale_senaryo
from test_sources import alanlar_kur, kayit_yaz
from typer.testing import CliRunner

from mutalaa_pipeline import cli, lineage
from mutalaa_pipeline.adimlar import enrich_citations
from mutalaa_pipeline.anchor import content_hash
from mutalaa_pipeline.enrich import citations, kuran_metni
from mutalaa_pipeline.export import pg, pg_risale_atif
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.ingest.risale_kaynaklari import KAYNAK_RNK
from mutalaa_pipeline.qa import checks as _checks  # noqa: F401  (paket yuklensin)
from mutalaa_pipeline.qa import run_risale_atif
from mutalaa_pipeline.qa.checks import risale_atif as kapilar
from mutalaa_pipeline.staged import satirlari_oku

ATIF = citations.KAYNAK_ID
runner = CliRunner()
D1 = cumle(3, 4, 5, 6, 7)  # 1:1 sonu + 1:2 basi (iki ayet)
D2 = cumle(11, 12, 13, 14, 15, 16)  # 1:3'un tamami
D3 = cumle(30, 31, 32, 33)  # 9:2 (konum bilinmeyen ayet)
D4 = cumle(0, 1, 2, 3)  # 1:1 ve 9:1 basi (tekrar = 2)
D5 = cumle(11, 12, 13)  # uc kelime: arac bulmaz
ONEK1 = "Deneme paragrafi 1 "
METIN1 = f"{ONEK1}{D1} ve (1:3) sonu."
METIN3 = f"{D2} {D3}"


def birim(
    no: int, metin: str, marks: list[dict[str, object]], dil: str = "tr", kitap: str = KITAP
) -> dict[str, object]:
    return {
        "anchor": f"rn:{kitap}:soz-1:p{no}",
        "kind": "risale",
        "role": "govde",
        "text": metin,
        "marks": marks,
        "attrs": {"dil": dil},
        "content_hash": content_hash(metin),
        "source_id": KAYNAK_RNK,
    }


def isaret(bas: int, uzunluk: int, tur: str) -> dict[str, object]:
    return {"t": "ar", "s": bas, "e": bas + uzunluk, "tur": tur}


def birimler() -> list[dict[str, object]]:
    return [
        birim(1, METIN1, [isaret(len(ONEK1), len(D1), "blok")]),
        birim(2, "Deneme paragrafi 2. Ikinci cumle 2.", []),
        # Osmanlica kitap: blok atlanir, yalniz alinti isareti araca gider
        birim(
            3,
            METIN3,
            [isaret(0, len(D2), "blok"), isaret(len(D2) + 1, len(D3), "alinti")],
            dil="ota",
            kitap=KITAP + "-osmanlica",
        ),
        birim(4, D4, [isaret(0, len(D4), "blok")]),
        birim(5, D5, [isaret(0, len(D5), "blok")]),
        birim(6, D2, [isaret(0, len(D2), "blok")]),
    ]


@pytest.fixture
def s(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Senaryo:
    sen = risale_senaryo(tmp_path)
    kayit_yaz(
        sen.kok,
        alanlar_kur(
            ATIF, tur="baglanti_verisi", surum="deneme-atif-1.0", baslik="Deneme atif dizini"
        ),
    )
    monkeypatch.setenv("MUTALAA_VERI_KOK", str(sen.veri))
    monkeypatch.setattr(kuran_metni, "yukle", sahte_yukle)
    zincir_kur(sen, birimler())
    return sen


def sahte_yukle(
    veri_kok: Path, gelen_tarih: str | dict[str, str] | None = None
) -> kuran_metni.KuranMetni:
    kuran = sentetik_kuran()
    girdiler = tuple(
        lineage.Girdi(f"gelen/tanzil-{v}/2026-11-13/quran-{v}.txt", lineage.sha256_bayt(v.encode()))
        for v in kuran_metni.VARYANTLAR
    )
    tarihler = dict.fromkeys(kuran_metni.VARYANTLAR, "2026-11-13")
    return kuran_metni.KuranMetni(kuran.ayetler, girdiler, tarihler)


def uret(s: Senaryo, **kw: object) -> int:
    return enrich_citations.komut_enrich_citations(
        source=str(kw.get("source", KAYNAK_RNK)),
        gelen_tarih=None,
        dry_run=bool(kw.get("dry_run", False)),
        force=bool(kw.get("force", False)),
        config=None,
        kok=s.kok,
    )


def qa(s: Senaryo, gate: list[str] | None = None, run: str | None = None) -> int:
    return run_risale_atif.komut_qa_run_risale_atif(run=run, gate=gate, config=None, kok=s.kok)


def atif_calismalari(s: Senaryo) -> list[Path]:
    kok = s.veri / "staged" / ATIF
    return sorted(p for p in kok.iterdir() if p.is_dir()) if kok.is_dir() else []


def xref_satirlari(s: Senaryo) -> list[dict[str, object]]:
    veri = (atif_calismalari(s)[-1] / "xrefs.jsonl").read_bytes()
    return [x.veri for x in satirlari_oku(veri, "xrefs.jsonl")]


def raporlar(s: Senaryo, komut: str) -> list[dict[str, object]]:
    sonuc = []
    for yol in sorted((s.veri / "reports").glob("*.json"), key=lambda p: p.name):
        if yol.name.endswith("-atif.json"):
            continue
        veri = json.loads(yol.read_text(encoding="utf-8"))
        if veri.get("komut") == komut:
            sonuc.append(veri)
    return sonuc


# --- enrich citations ----------------------------------------------------------------------


def test_komut_beklenen_adaylari_uretir(s: Senaryo) -> None:
    assert uret(s) == 0
    satirlar = xref_satirlari(s)
    assert len(satirlar) == 6
    ozet = sorted(
        (str(x["src_anchor"]).rsplit(":", 1)[1], x["type"], x["dst_anchor"], x["dst_span"])
        for x in satirlar
    )
    assert ozet == [
        ("p1", "atif", "q:1:3", None),
        ("p1", "iktibas", "q:1:1", [4, 7]),  # kelime 4-6 -> [4, 7)
        ("p1", "iktibas", "q:1:2", [1, 3]),
        ("p3", "iktibas", "q:9:2", None),  # hizasiz ayet: konum yok
        ("p4", "iktibas", "q:1:1", [1, 5]),  # kelime 1-4; 9:1'de de gecer
        ("p6", "iktibas", "q:1:3", None),  # ayetin tamami
    ]
    for x in satirlar:
        assert x["origin"] == "hat" and x["status"] == "aday"
        assert set(x) == citations.XREF_ALANLARI
        for alan in ("score_binde", "confidence_binde"):
            assert type(x[alan]) is int and 0 <= x[alan] <= 1000  # type: ignore[operator]
        evidence = x["evidence"]
        assert isinstance(evidence, dict)
        assert evidence["source_id"] == ATIF
        assert evidence["src_hash"] == content_hash(_metin_of(str(x["src_anchor"])))[:16]


def _metin_of(capa: str) -> str:
    return next(str(b["text"]) for b in birimler() if b["anchor"] == capa)


def test_src_span_birim_metnindeki_parcadir(s: Senaryo) -> None:
    uret(s)
    metinler = {str(b["anchor"]): str(b["text"]) for b in birimler()}
    for x in xref_satirlari(s):
        bas, son = x["src_span"]  # type: ignore[misc]
        parca = metinler[str(x["src_anchor"])][bas:son]
        if x["type"] == "atif":
            assert parca == "(1:3)"
        elif x["src_anchor"].endswith(":p1"):  # type: ignore[union-attr]
            assert parca == D1
        elif x["src_anchor"].endswith(":p3"):  # type: ignore[union-attr]
            assert parca == D3  # blok atlandi, yalniz alinti isareti


def test_guven_kurallari_satirlarda(s: Senaryo) -> None:
    uret(s)
    satirlar = {
        (str(x["src_anchor"]).rsplit(":", 1)[1], x["dst_anchor"]): x for x in xref_satirlari(s)
    }
    atif = satirlar[("p1", "q:1:3")]
    assert (atif["score_binde"], atif["confidence_binde"]) == (1000, 850)
    tam = satirlar[("p6", "q:1:3")]
    assert tam["evidence"]["kapsama"] == 1000  # type: ignore[index]
    assert (tam["score_binde"], tam["confidence_binde"]) == (857, 800)  # n = N = 6
    tekrarli = satirlar[("p4", "q:1:1")]
    assert tekrarli["evidence"]["tekrar"] == 2  # type: ignore[index]
    assert tekrarli["confidence_binde"] < 600  # n = 4: tekrar cezasi
    for x in satirlar.values():
        if x["type"] == "iktibas":
            assert x["evidence"]["skor_yok"] is True  # type: ignore[index]  # arac skor vermez
            assert x["evidence"]["arac"] == "quran-toolkit"  # type: ignore[index]
            assert "skor_binde" not in x["evidence"]  # type: ignore[operator]
    konumsuz = satirlar[("p3", "q:9:2")]
    assert konumsuz["evidence"]["kelime_konumu_yok"] is True  # type: ignore[index]


def test_kati_json_ve_ondalik_yok(s: Senaryo) -> None:
    uret(s)
    veri = (atif_calismalari(s)[-1] / "xrefs.jsonl").read_bytes()
    assert veri.isascii() and b"\r" not in veri and veri.endswith(b"\n")
    satirlari_oku(veri, "xrefs.jsonl")  # kati okuma geciyor


def test_idempotent_ikinci_kosu_ayni_baytlar_ve_sirali(s: Senaryo) -> None:
    assert uret(s) == 0
    assert uret(s, force=True) == 0
    ilk, ikinci = (k / "xrefs.jsonl" for k in atif_calismalari(s)[-2:])
    assert ilk.read_bytes() == ikinci.read_bytes()
    manifestler = [
        json.loads((k / "manifest.json").read_text("utf-8")) for k in atif_calismalari(s)
    ]
    assert manifestler[0]["ciktilar"][0]["sha256"] == manifestler[1]["ciktilar"][0]["sha256"]
    # capa sirasi: p1 < p3 < p4 < p6
    satirlar = xref_satirlari(s)
    assert satirlar == sorted(satirlar, key=citations.siralama_anahtari)


def test_manifest_zincir_ve_ayrintilar(s: Senaryo) -> None:
    uret(s)
    manifest = json.loads((atif_calismalari(s)[-1] / "manifest.json").read_text("utf-8"))
    assert manifest["adim"] == "anchor" and manifest["komut"] == "enrich citations"
    yollar = [g["yol"] for g in manifest["girdiler"]]
    assert f"staged/{KAYNAK_RNK}/{s.anchor_run}/units.jsonl" in yollar
    assert sum(1 for y in yollar if y.startswith("gelen/tanzil-")) == 2
    a = manifest["ayrintilar"]
    assert (a["arac"], a["arac_surumu"]) == ("quran-toolkit", "0.1.0")
    assert a["sayilar"] == {"birim": 6, "xref": 6, "atif": 1, "iktibas": 5}
    assert a["data_version"].startswith(f"{ATIF}@deneme-atif-1.0/")


def test_dry_run_yazmaz(s: Senaryo, capsys: pytest.CaptureFixture[str]) -> None:
    assert uret(s, dry_run=True) == 0
    assert "6 aday" in capsys.readouterr().out
    assert atif_calismalari(s) == []


def test_yan_rapor_yalniz_sayi(s: Senaryo) -> None:
    uret(s)
    (yol,) = list((s.veri / "reports").glob("*-atif.json"))
    metin = yol.read_text(encoding="utf-8")
    rapor = json.loads(metin)
    assert rapor["satir"] == 6 and rapor["tespit_ham"] == 6
    assert rapor["tur_dil"] == {"atif|tr": 1, "iktibas|ota": 1, "iktibas|tr": 4}
    assert rapor["ayet_sayisi_dagilimi"] == {"1": 3, "2": 2}
    assert rapor["tanzil_hizasiz_ayet"] == 1
    assert rapor["sure_adi_tablosu"].startswith("yok")
    assert "Deneme" not in metin and metin.isascii()
    for harf in D1 + D2 + D3:
        assert harf not in metin or harf == " "


def test_gunluk_ve_rapor_metin_tasimaz(s: Senaryo) -> None:
    uret(s)
    for yol in list((s.veri / "reports").glob("*.json")) + list((s.veri / "logs").rglob("*")):
        if yol.is_file():
            icerik = yol.read_text(encoding="utf-8", errors="replace")
            assert "Deneme paragrafi" not in icerik
            assert D1 not in icerik and D2 not in icerik


def test_hatalar_cikis_iki(s: Senaryo, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert uret(s, source="risale-asil-nusha") == 2  # yalniz risale-rnk-metin
    (s.kok / "pipeline" / "sources" / f"{ATIF}.toml").unlink()  # kayitsiz kaynak
    assert uret(s) == 2
    assert "kayitsiz" in capsys.readouterr().err
    assert atif_calismalari(s) == []


def test_anchor_calismasi_yoksa_cikis_iki(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    sen = risale_senaryo(tmp_path)
    kayit_yaz(sen.kok, alanlar_kur(ATIF, tur="baglanti_verisi", surum="x-1"))
    monkeypatch.setenv("MUTALAA_VERI_KOK", str(sen.veri))
    monkeypatch.setattr(kuran_metni, "yukle", sahte_yukle)
    assert uret(sen) == 2


def test_hic_aday_yoksa_cikis_iki(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    sen = risale_senaryo(tmp_path)
    kayit_yaz(sen.kok, alanlar_kur(ATIF, tur="baglanti_verisi", surum="x-1"))
    monkeypatch.setenv("MUTALAA_VERI_KOK", str(sen.veri))
    monkeypatch.setattr(kuran_metni, "yukle", sahte_yukle)
    zincir_kur(sen, [birim(2, "Deneme paragrafi 2.", [])])
    assert uret(sen) == 2  # bos xrefs.jsonl yazilmaz


# --- qa run --------------------------------------------------------------------------------


def test_qa_dort_kapi_gecer_ve_rapor_alanlari(s: Senaryo) -> None:
    uret(s)
    assert qa(s) == 0
    (rapor,) = [r for r in raporlar(s, "qa run") if r.get("kaynak") == ATIF]
    assert rapor["kaynak"] == ATIF
    assert rapor["kapilar"] == dict.fromkeys(kapilar.KAPILAR, "gecti")
    assert rapor["anchor_run_id"] == atif_calismalari(s)[-1].name
    assert rapor["units_sha256"] == lineage.sha256_dosya(atif_calismalari(s)[-1] / "xrefs.jsonl")
    assert rapor["kapi_sayilari"]["G-NOR"]["uygulanmaz"] == 1  # type: ignore[index]
    assert rapor["kapi_sayilari"]["G-BUT"]["satir"] == 6  # type: ignore[index]


def test_qa_gate_kismi_ve_gecersiz_kapi(s: Senaryo) -> None:
    uret(s)
    assert qa(s, gate=["G-CAP"]) == 0
    assert qa(s, gate=["G-HIZ"]) == 2
    assert qa(s, run="yok") == 2


def test_qa_atif_calismasi_yoksa_cikis_iki(s: Senaryo) -> None:
    assert qa(s) == 2


def test_qa_kapisi_kaynak_kaydi() -> None:
    from mutalaa_pipeline import qa as qa_paketi

    assert qa_paketi.kaynak_kapilari(ATIF) == ("G-KAY", "G-BUT", "G-CAP", "G-NOR")


def girdi(s: Senaryo) -> kapilar.AtifGirdisi:
    uret(s)
    ctx = ctx_kur(s.tmp, s.kok, adim="qa", kaynaklar=[ATIF, KAYNAK_RNK])
    sonuc, _, _ = run_risale_atif.yukle(ctx, run=None)
    return sonuc


def degistir(g: kapilar.AtifGirdisi, **alan: object) -> kapilar.AtifGirdisi:
    return dataclasses.replace(g, **alan)


def satir_degistir(g: kapilar.AtifGirdisi, sira: int, **degisim: object) -> kapilar.AtifGirdisi:
    satirlar = [dict(x) for x in g.satirlar]
    satirlar[sira].update(degisim)
    return degistir(g, satirlar=satirlar)


def sirasi(g: kapilar.AtifGirdisi, anchor_sonu: str, tur: str) -> int:
    return next(
        i
        for i, x in enumerate(g.satirlar)
        if str(x["src_anchor"]).endswith(anchor_sonu) and x["type"] == tur
    )


def kapi(g: kapilar.AtifGirdisi, ad: str) -> tuple[str, ...]:
    return kapilar.KAPI_ISLEVLERI[ad](g).bulgular


def test_gecerli_girdide_bulgu_yok(s: Senaryo) -> None:
    g = girdi(s)
    for ad in kapilar.KAPILAR:
        assert kapi(g, ad) == (), ad


@pytest.mark.parametrize(
    ("ad", "degisim", "parca"),
    [
        ("G-BUT", {"src_span": [0, 99999]}, "src_span"),
        ("G-BUT", {"src_span": [5, 5]}, "src_span"),
        ("G-BUT", {"dst_anchor": "q:5:1"}, "dst"),
        ("G-BUT", {"dst_anchor": "q:1:2:1"}, "dst"),
        ("G-BUT", {"dst_span": [1, 99]}, "dst_span"),
        ("G-BUT", {"origin": "editor"}, "sabit"),
        ("G-BUT", {"status": "onayli"}, "sabit"),
        ("G-BUT", {"type": "ima"}, "tur"),
        ("G-BUT", {"score_binde": 1500}, "puan"),
        ("G-BUT", {"confidence_binde": 0.5}, "puan"),
        ("G-BUT", {"evidence": {"serbest": 1, "source_id": ATIF}}, "evidence"),
        (
            "G-BUT",
            {"evidence": {"yontem": "Deneme paragrafi 1 sonu", "source_id": ATIF}},
            "evidence",
        ),
        ("G-BUT", {"evidence": {"source_id": "baska"}}, "evidence"),
        ("G-BUT", {"extra": 1}, "alan"),
        ("G-KAY", {"data_version": "yanlis"}, "data_version"),
        ("G-CAP", {"src_anchor": "q:1:1"}, "src_anchor"),
        ("G-CAP", {"src_anchor": "rn:Deneme:p1"}, "src_anchor"),
        ("G-CAP", {"src_anchor": f"rn:{KITAP}:soz-1:p1@0-5"}, "src_anchor"),
        ("G-CAP", {"dst_anchor": "q:1:2:1-2"}, "dst_anchor"),
        ("G-CAP", {"dst_span": [3, 3]}, "dst_anchor"),
    ],
)
def test_kapilar_bozuk_satiri_yakalar(
    s: Senaryo, ad: str, degisim: dict[str, object], parca: str
) -> None:
    g = girdi(s)
    sira = sirasi(g, ":p1", "iktibas")
    if ad == "G-BUT" and "extra" in degisim:
        satirlar = [dict(x) for x in g.satirlar]
        satirlar[sira].update(degisim)
        g = degistir(g, satirlar=satirlar)
    else:
        g = satir_degistir(g, sira, **degisim)
    bulgular = kapi(g, ad)
    assert any(parca in b for b in bulgular), bulgular
    assert all(b.isascii() and len(b) < 400 for b in bulgular)


def test_g_but_iktibas_ar_isareti_disinda_ve_blok(s: Senaryo) -> None:
    g = girdi(s)
    sira = sirasi(g, ":p1", "iktibas")
    disinda = satir_degistir(g, sira, src_span=[0, 5])  # "Deneme": ar isareti disinda
    assert any("ar isareti" in b for b in kapi(disinda, "G-BUT"))
    # Osmanlica kitapta blok icindeki aralik kabul edilmez
    p3 = sirasi(g, ":p3", "iktibas")
    blokta = satir_degistir(g, p3, src_span=[0, len(D2)])
    assert any("alinti" in b for b in kapi(blokta, "G-BUT"))


def test_g_but_atif_metinden_uretilemiyorsa(s: Senaryo) -> None:
    g = girdi(s)
    sira = sirasi(g, ":p1", "atif")
    bas, son = g.satirlar[sira]["src_span"]  # type: ignore[misc]
    yanlis = satir_degistir(g, sira, src_span=[bas, son - 1])
    assert any("atif" in b for b in kapi(yanlis, "G-BUT"))
    baska_ayet = satir_degistir(g, sira, dst_anchor="q:1:2")
    assert any("atif" in b for b in kapi(baska_ayet, "G-BUT"))


def test_g_but_src_hash_ve_birim_yok(s: Senaryo) -> None:
    g = girdi(s)
    sira = sirasi(g, ":p4", "iktibas")
    evidence = dict(g.satirlar[sira]["evidence"])  # type: ignore[call-overload]
    evidence["src_hash"] = "0" * 16
    assert any("src_hash" in b for b in kapi(satir_degistir(g, sira, evidence=evidence), "G-BUT"))
    eksik = {k: v for k, v in g.birimler.items() if not k.endswith(":p4")}
    assert any("src_anchor birimi" in b for b in kapi(degistir(g, birimler=eksik), "G-BUT"))


def test_g_but_satir_sayisi_manifestle_ayni_olmali(s: Senaryo) -> None:
    g = girdi(s)
    assert any("satir sayisi" in b for b in kapi(degistir(g, satirlar=g.satirlar[:-1]), "G-BUT"))
    assert any("bos" in b for b in kapi(degistir(g, satirlar=[]), "G-BUT"))


def test_g_cap_yineleme_ve_siralama(s: Senaryo) -> None:
    g = girdi(s)
    yinelenen = [*g.satirlar, g.satirlar[0]]
    assert any("yinelenen" in b for b in kapi(degistir(g, satirlar=yinelenen), "G-CAP"))
    ters = list(reversed(g.satirlar))
    assert any("capa sirasinda" in b for b in kapi(degistir(g, satirlar=ters), "G-CAP"))


def test_g_kay_kayit_ve_arac(s: Senaryo) -> None:
    g = girdi(s)
    kotu = dataclasses.replace(g.kayit, tur=g.kayit.tur.__class__("risale"))
    assert any("baglanti_verisi" in b for b in kapi(degistir(g, kayit=kotu), "G-KAY"))
    manifest = {**g.manifest, "arac": "ijaza"}
    assert any("arac" in b for b in kapi(degistir(g, manifest=manifest), "G-KAY"))
    sira = sirasi(g, ":p4", "iktibas")
    evidence = {**g.satirlar[sira]["evidence"], "arac_surumu": "9.9"}  # type: ignore[dict-item]
    assert any("arac adi" in b for b in kapi(satir_degistir(g, sira, evidence=evidence), "G-KAY"))


def test_g_nor_uygulanmaz_ve_metin_yok(s: Senaryo) -> None:
    g = girdi(s)
    sonuc = kapilar.KAPI_ISLEVLERI["G-NOR"](g)
    assert sonuc.gecti and sonuc.sayilar["uygulanmaz"] == 1
    uzun = satir_degistir(g, 0, data_version="x" * 400)
    assert not kapilar.KAPI_ISLEVLERI["G-NOR"](uzun).gecti


def test_birlesen_isaret_siniri() -> None:
    assert kapilar._sinir_mn("abَc", 0, 2) is True  # bitis, hareke oncesine dusuyor
    assert kapilar._sinir_mn("aَbc", 1, 3) is True  # baslangic hareke ustunde
    assert kapilar._sinir_mn("abc", 0, 2) is False


def test_qa_bozuk_dosya_cikis_iki(s: Senaryo) -> None:
    uret(s)
    dosya = atif_calismalari(s)[-1] / "xrefs.jsonl"
    dosya.write_bytes(dosya.read_bytes() + b"\n")  # ozet manifestle tutmaz
    assert qa(s) == 2


def test_qa_tanzil_dosyasi_degismisse_cikis_iki(
    s: Senaryo, monkeypatch: pytest.MonkeyPatch
) -> None:
    uret(s)

    def baska(veri_kok: Path, gelen_tarih: object = None) -> kuran_metni.KuranMetni:
        k = sahte_yukle(veri_kok)
        girdiler = (lineage.Girdi("gelen/tanzil-uthmani/2026-11-13/quran-uthmani.txt", "0" * 64),)
        return kuran_metni.KuranMetni(k.ayetler, girdiler, k.tarihler)

    monkeypatch.setattr(kuran_metni, "yukle", baska)
    assert qa(s) == 2


# --- export pg (sahte baglanti) ------------------------------------------------------------


def hazir(s: Senaryo) -> None:
    uret(s)
    assert qa(s) == 0


def calistir(
    s: Senaryo,
    baglanti: SahteBaglanti | Callable[[], psycopg.Connection] | None = None,
    **kw: object,
) -> int:
    if baglanti is None:
        fabrika: Callable[[], psycopg.Connection] = Cagrilmaz()
    elif isinstance(baglanti, SahteBaglanti):
        fabrika = lambda: baglanti  # type: ignore[assignment,return-value]  # noqa: E731
    else:
        fabrika = baglanti
    kaynak = str(kw.pop("source", ATIF))
    return pg.komut_export_pg(
        ayarlar_kur(s.tmp),
        depo_kok=s.kok,
        source=kaynak,
        baglanti=fabrika,
        **kw,  # type: ignore[arg-type]
    )


SAYAC_PARCASI = "FROM pg_temp.staging_xref s LEFT JOIN icerik.xref x ON"


def sahte(**yanit: SahteSonuc) -> SahteBaglanti:
    cifter = {
        "INSERT INTO icerik.xref": yanit.get("upsert", SahteSonuc(rowcount=6)),
        SAYAC_PARCASI: yanit.get("sayac", SahteSonuc([(6, 0, 0, 0, 0, 0)])),
        "SELECT count(*) FROM icerik.xref x WHERE": yanit.get("artik", SahteSonuc([(0,)])),
        "NOT EXISTS (SELECT 1 FROM icerik.unit u WHERE u.anchor = s.dst_anchor)": yanit.get(
            "eksik_dst", SahteSonuc()
        ),
        "NOT EXISTS (SELECT 1 FROM icerik.unit u WHERE u.anchor = s.src_anchor)": yanit.get(
            "eksik_src", SahteSonuc()
        ),
    }
    return SahteBaglanti(esle(*[(k, v) for k, v in cifter.items() if v is not None]))


def sayilar(s: Senaryo) -> dict[str, int]:
    deger = raporlar(s, "export pg")[-1]["sayilar"]
    assert isinstance(deger, dict)
    return deger


def test_export_tek_islemde_sirali_ve_sayaclar(s: Senaryo) -> None:
    hazir(s)
    db = sahte()
    assert calistir(s, db) == 0
    assert [i.durum for i in db.islemler] == ["onaylandi"]
    sorgular = [m for i in db.islemler for m, _ in i.sorgular]
    sira = [
        next(i for i, m in enumerate(sorgular) if parca in m)
        for parca in (
            "pg_advisory_xact_lock",
            "INSERT INTO icerik.source",
            "CREATE TEMP TABLE staging_xref",
            "u.anchor = s.src_anchor",
            "u.anchor = s.dst_anchor",
            SAYAC_PARCASI,
            "INSERT INTO icerik.xref",
        )
    ]
    assert sira == sorted(sira) and len(set(sira)) == 7
    sa = sayilar(s)
    assert sa["xref_staging"] == 6 and sa["xref_eklenen"] == 6
    assert sa["xref_guncellenen"] == 0 and sa["xref_silinen"] == 0
    assert sa["onceki_aday_artik"] == 0
    # COPY satirlari: score = binde / 1000, aralik yari acik
    satirlar = db.kopya_satirlari()
    assert len(satirlar) == 6
    assert {type(r[6]) for r in satirlar} == {float}
    assert all(0.0 <= r[6] <= 1.0 and 0.0 <= r[7] <= 1.0 for r in satirlar)  # type: ignore[operator]
    assert any(r[5] is None for r in satirlar) and any(r[5] is not None for r in satirlar)


def test_export_src_yoksa_ya_da_hedef_yoksa_cikis_bir_geri_alinir(
    s: Senaryo, capsys: pytest.CaptureFixture[str]
) -> None:
    hazir(s)
    for ad, parca in (("eksik_dst", "hedef ayeti"), ("eksik_src", "kaynak ucu")):
        db = sahte(**{ad: SahteSonuc([("q:1:1",)])})
        assert calistir(s, db) == 1
        assert db.islemler[0].durum == "geri_alindi"
        assert not db.sorgular("INSERT INTO icerik.xref")  # hicbir sey yazilmadi
        hata = capsys.readouterr().err
        assert parca in hata and "once export pg" in hata and hata.isascii()


def test_export_span_tasarsa_ya_da_ozet_degismisse_cikis_bir(s: Senaryo) -> None:
    hazir(s)
    for parca in ("upper(s.src_span) > char_length", "left(u.content_hash, 16)"):
        db = SahteBaglanti(esle((parca, SahteSonuc([("rn:deneme:p1",)]))))
        assert calistir(s, db) == 1
        assert db.islemler[0].durum == "geri_alindi"
        assert not db.sorgular("INSERT INTO icerik.xref")


def test_export_yazim_sayisi_tutmazsa_geri_alinir(s: Senaryo) -> None:
    hazir(s)
    db = sahte(upsert=SahteSonuc(rowcount=3))
    assert calistir(s, db) == 1
    assert db.islemler[0].durum == "geri_alindi"


def test_export_dry_run_geri_alir(s: Senaryo) -> None:
    hazir(s)
    db = sahte()
    assert calistir(s, db, dry_run=True) == 0
    assert db.islemler[0].durum == "geri_alindi"


def test_export_onayli_red_korunur_sayaci(s: Senaryo) -> None:
    hazir(s)
    db = sahte(sayac=SahteSonuc([(1, 2, 1, 1, 1, 0)]), upsert=SahteSonuc(rowcount=3))
    assert calistir(s, db) == 0
    sa = sayilar(s)
    assert (sa["xref_eklenen"], sa["xref_guncellenen"], sa["xref_ayni_kalan"]) == (1, 2, 1)
    assert (sa["xref_korunan_onayli"], sa["xref_korunan_red"]) == (1, 1)
    assert any("dokunulmadi" in u for u in raporlar(s, "export pg")[-1]["uyarilar"])  # type: ignore[union-attr]


def test_export_artik_aday_yalniz_sayilir_silinmez(s: Senaryo) -> None:
    hazir(s)
    db = sahte(artik=SahteSonuc([(3,)]))
    assert calistir(s, db) == 0
    assert sayilar(s)["onceki_aday_artik"] == 3
    assert sayilar(s)["xref_silinen"] == 0
    assert not db.sorgular("DELETE FROM")


def test_export_prune_varsayilan_kapali_ve_onay_ister(s: Senaryo) -> None:
    import inspect

    assert inspect.signature(pg.komut_export_pg).parameters["prune"].default is False
    assert inspect.signature(pg.komut_export_pg).parameters["yedek_alindi"].default is False
    hazir(s)
    db = sahte()
    assert calistir(s, db, prune=True) == 2  # yedek onayi yok
    assert calistir(s, db, yedek_alindi=True) == 2  # prune olmadan anlamsiz
    assert calistir(s, db, prune=True, yedek_alindi=True, source="test-kucuk") == 2
    assert not db.islemler  # baglanti ve islem acilmadi


def test_export_prune_kapsamli_silme(s: Senaryo, capsys: pytest.CaptureFixture[str]) -> None:
    hazir(s)
    db = SahteBaglanti(
        esle(
            ("INSERT INTO icerik.xref", SahteSonuc(rowcount=6)),
            (SAYAC_PARCASI, SahteSonuc([(6, 0, 0, 0, 0, 0)])),
            ("DELETE FROM icerik.xref", SahteSonuc(rowcount=2)),
            ("EXISTS (SELECT 1 FROM icerik.review r", SahteSonuc([(1,)])),
            ("SELECT count(*) FROM icerik.xref x WHERE", SahteSonuc([(3,)])),
        )
    )
    assert calistir(s, db, prune=True, yedek_alindi=True) == 0
    sa = sayilar(s)
    assert sa["xref_silinen"] == 2
    assert sa["xref_prune_review_nedeniyle_atlanan"] == 1
    ((metin, params),) = db.sorgular("DELETE FROM icerik.xref")
    assert params == (ATIF,)
    assert "x.origin = 'hat' AND x.status = 'aday'" in metin
    assert "x.evidence->>'source_id' = %s" in metin
    assert "icerik.review r WHERE r.xref_id = x.id" in metin
    assert any("VERI SILER" in u for u in raporlar(s, "export pg")[-1]["uyarilar"])  # type: ignore[union-attr]


def test_sql_statik_denetim_onayli_red_dokunulmaz() -> None:
    sql = pg_risale_atif.UPSERT
    assert "ON CONFLICT ON CONSTRAINT xref_natural_key DO UPDATE" in sql
    atama = sql.split("DO UPDATE SET")[1].split(" WHERE ")[0]
    sutunlar = [a.split("=")[0].strip() for a in atama.split(",")]
    assert sutunlar == ["score", "confidence", "evidence", "data_version"]  # yalniz turetilmis
    kosul = sql.split(" WHERE ")[1]
    assert kosul.startswith("x.origin = 'hat' AND x.status = 'aday'")
    assert "IS DISTINCT FROM" in kosul  # yalniz degeri farkliysa
    for yasak in ("votes_up", "votes_down", "x.status =", "x.origin =", "id ="):
        assert yasak not in atama
    # yeni satir hat + aday girer; baska sutun yazilmaz
    assert "'hat', 'aday'" in sql
    assert "DELETE" not in sql and "TRUNCATE" not in sql
    # prune kapsami
    assert "x.origin = 'hat' AND x.status = 'aday' AND x.evidence->>'source_id' = %s" in (
        pg_risale_atif.PRUNE
    )
    assert "NOT EXISTS (SELECT 1 FROM icerik.review r" in pg_risale_atif.PRUNE
    # onayli ve red: SAYAC yalniz sayar
    assert (
        "x.status = 'onayli'" in pg_risale_atif.SAYAC and "x.status = 'red'" in pg_risale_atif.SAYAC
    )
    assert "UPDATE" not in pg_risale_atif.SAYAC


def test_export_qa_kalmissa_ya_da_yoksa_yuklemez(
    s: Senaryo, capsys: pytest.CaptureFixture[str]
) -> None:
    uret(s)  # qa raporu yok
    cagrilmaz = Cagrilmaz()
    assert calistir(s, cagrilmaz) in (1, 2)
    assert cagrilmaz.sayi == 0  # baglanti acilmadi
    assert "QA" in capsys.readouterr().err


def test_export_hazirla_dosya_tarafi(s: Senaryo) -> None:
    hazir(s)
    ctx = ctx_kur(s.tmp, s.kok, adim="export", kaynaklar=[ATIF])
    h = pg.hazirla(ctx, ATIF, None, ())
    assert len(h.xref) == 6 and h.xref_prune is False
    assert {x.tur for x in h.xref} == {"atif", "iktibas"}
    assert h.ham == {ATIF: []}
    assert [r.adim for r in h.zincir] == ["ingest", "normalize", "anchor"]
    assert all(0 <= x.score_binde <= 1000 for x in h.xref)
    with pytest.raises(GirdiHatasi, match="birimlerle birlikte"):
        pg_risale_atif.hazirla(ctx, "test-risale-ornek", None, ())


def test_export_rapor_metin_tasimaz(s: Senaryo) -> None:
    hazir(s)
    assert calistir(s, sahte()) == 0
    for yol in (s.veri / "reports").glob("*.json"):
        metin = yol.read_text(encoding="utf-8")
        assert "Deneme paragrafi" not in metin
        assert D1 not in metin and D2 not in metin


def test_satirlari_coz_katiligi(s: Senaryo) -> None:
    hazir(s)
    veri = (atif_calismalari(s)[-1] / "xrefs.jsonl").read_bytes()
    assert len(pg_risale_atif.satirlari_coz(veri, ATIF, "xrefs.jsonl")) == 6
    ilk = json.loads(veri.splitlines()[0])
    for kotu in (
        {**ilk, "origin": "editor"},
        {**ilk, "status": "onayli"},
        {**ilk, "type": "ima"},
        {**ilk, "score_binde": 1001},
        {**ilk, "dst_anchor": "q:1:2:1"},
        {**ilk, "src_anchor": "rn:Deneme:p1"},
        {**ilk, "evidence": {**ilk["evidence"], "source_id": "baska"}},
        {**ilk, "fazla": 1},
        {k: v for k, v in ilk.items() if k != "evidence"},
    ):
        baytlar = (json.dumps(kotu, sort_keys=True) + "\n").encode()
        with pytest.raises(GirdiHatasi):
            pg_risale_atif.satirlari_coz(baytlar, ATIF, "xrefs.jsonl")
    with pytest.raises(GirdiHatasi, match="yinelenen"):
        pg_risale_atif.satirlari_coz(
            veri.splitlines()[0] + b"\n" + veri.splitlines()[0] + b"\n", ATIF, "x"
        )


# --- CLI -----------------------------------------------------------------------------------


def test_cli_yardim_renkli_de_gecer(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FORCE_COLOR", "1")
    r = runner.invoke(cli.app, ["enrich", "citations", "--help"])
    assert r.exit_code == 0
    metin = ansisiz(r.output)
    for secenek in ("--source", "--gelen-tarih", "--dry-run", "--force", "--config", "--kok"):
        assert secenek in metin
    r = runner.invoke(cli.app, ["export", "pg", "--help"])
    metin = ansisiz(r.output)
    assert "--prune" in metin and "--yedek-alindi" in metin
    assert "SILER" in metin
    r = runner.invoke(cli.app, ["enrich", "--help"])
    assert "citations" in ansisiz(r.output)


def test_cli_source_zorunlu_ve_yanlis_kaynak(s: Senaryo) -> None:
    r = runner.invoke(cli.app, ["enrich", "citations", "--kok", str(s.kok)])
    assert r.exit_code == 2  # --source eksik (Typer kullanim hatasi)
    r = runner.invoke(
        cli.app, ["enrich", "citations", "--source", "risale-asil-nusha", "--kok", str(s.kok)]
    )
    assert r.exit_code == 2


def test_cli_uctan_uca(s: Senaryo) -> None:
    r = runner.invoke(cli.app, ["enrich", "citations", "--source", KAYNAK_RNK, "--kok", str(s.kok)])
    assert r.exit_code == 0, r.output
    assert "6 aday" in r.output
    r = runner.invoke(cli.app, ["qa", "run", "--source", ATIF, "--kok", str(s.kok)])
    assert r.exit_code == 0, r.output
    assert "G-KAY gecti" in r.output and "G-NOR gecti" in r.output
    r = runner.invoke(cli.app, ["export", "pg", "--source", ATIF, "--prune", "--kok", str(s.kok)])
    assert r.exit_code == 2  # --prune --yedek-alindi olmadan reddedilir (DB'ye baglanmadan)


def test_prune_run_ile_birlikte_reddedilir(s: Senaryo) -> None:
    """Eski bir `--run` ile `--prune`: guncel adaylar silinirdi; cikis 2, DB'ye baglanmadan."""
    from mutalaa_pipeline.export import pg_risale_atif as atif_modulu

    with pytest.raises(GirdiHatasi, match="--run"):
        atif_modulu.prune_denetle(ATIF, True, True, "01a1d225-8f55-7309-b24f-34684721026c")
    atif_modulu.prune_denetle(ATIF, True, True, None)  # varsayilan calisma: gecer
    atif_modulu.prune_denetle(ATIF, False, False, "01a1d225-8f55-7309-b24f-34684721026c")
    r = runner.invoke(
        cli.app,
        [
            "export", "pg", "--source", ATIF, "--prune", "--yedek-alindi",
            "--run", "01a1d225-8f55-7309-b24f-34684721026c", "--kok", str(s.kok),
        ],
    )  # fmt: skip
    assert r.exit_code == 2
    assert "--run" in ansisiz(r.output)
