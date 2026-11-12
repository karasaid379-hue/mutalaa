# ruff: noqa: RUF001
"""RNK Risale normalize ve anchor adimlari ile G-CAP/G-NOR (A20.2b; ACIKCA SENTETIK veri).

Hicbir Risale metni yoktur: sentetik RNK satirlari "Deneme ..." yer tutucu metinleri ve Arap
alfabesi harfleriyle uretilir (`test_risale_rnk.py` yardimcilari). Adimlar bellekte satir
duzeyinde (`normalize_satiri`, `anchor_satiri`, `ord_haritasi`) ve dosya zincirinde
(`test_risale_rnk.py`, `test_risale_rnk_cli.py`) sinanir; burada kapi bulgulari ve alan kurallari
vardir.
"""

import copy
import hashlib
import json
import unicodedata
from typing import Any

import pytest
from test_risale_rnk import (
    AR,
    AR_SEDDE,
    SENTETIK_JSON,
    donustur,
    girdi_kur,
    kitap_kaydi,
    sentetik_txt,
)

from mutalaa_pipeline.adimlar import risale as A
from mutalaa_pipeline.anchor import parse, sort_key
from mutalaa_pipeline.anchor.cumle import CUMLE_SURUMU, cumleleri_ayir
from mutalaa_pipeline.anchor.risale import Bolunme, BolunmeParcasi
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.ingest import risale_rnk_staged as S
from mutalaa_pipeline.ingest.base import units_satiri
from mutalaa_pipeline.ingest.risale_rnk_kilit import KAYNAK
from mutalaa_pipeline.normalize import NORMALIZER_VERSION, normalize_ar, search_keys
from mutalaa_pipeline.qa.checks import risale_rnk as Q
from mutalaa_pipeline.qa.checks.tanzil import Onceki
from mutalaa_pipeline.staged import Satir

SURUM = "deneme-surum"


def ingest_satirlari(sonuc: S.KitapSonucu) -> list[Satir]:
    """Ingest `units.jsonl` satirlari (tam alan kumesi), dosyadaki gibi JSON'dan gecmis."""
    return [
        Satir("ingest", i, json.loads(units_satiri(KAYNAK, u)))
        for i, u in enumerate(sonuc.birimler, start=1)
    ]


def zincir(sonuc: S.KitapSonucu) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """(normalize satirlari, anchor satirlari); her halka JSON'dan gecer (dosya gibi)."""
    normal = [
        json.loads(json.dumps(A.normalize_satiri(KAYNAK, s))) for s in ingest_satirlari(sonuc)
    ]
    satirlar = [Satir("normalize", i, n) for i, n in enumerate(normal, start=1)]
    siralar = A.ord_haritasi(satirlar)
    anchor: list[dict[str, Any]] = []
    for s in satirlar:
        satir = A.anchor_satiri(KAYNAK, s, SURUM)
        satir["ord"] = siralar[str(satir["anchor"])]
        anchor.append(json.loads(json.dumps(satir)))
    # dosyadaki gibi capa (sort_key) sirasinda
    anchor.sort(key=lambda a: sort_key(parse(a["anchor"])))
    return normal, anchor


def harita(satirlar: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {s["anchor"]: s for s in satirlar}


# --- rn_yolu ---------------------------------------------------------------------------------


def test_rn_yolu_kanonik_birim_capasi() -> None:
    assert A.rn_yolu("rn:sozler:soz-10:hakikat-3:p4") == ("sozler", "soz-10", "hakikat-3")
    assert A.rn_yolu("rn:sozler:p1") == ("sozler",)
    assert A.hasiye_bolumu_mu(("sozler", "soz-1", "hasiye-2"))
    assert not A.hasiye_bolumu_mu(("sozler", "soz-1"))
    assert A.parent_yolu(("sozler", "soz-10")) == "rn:sozler:soz-10"


@pytest.mark.parametrize(
    "capa",
    [
        "rn:sozler:p1:s2",  # cumle birim capasi degil
        "rn:sozler:p1@0-5",  # aralikli
        "q:2:255",
        "rn:Sozler:p1",
        "rn:sozler:soz-01:p1",  # sifirla baslayan kalip
        "rn:dizin:p1",  # dizin kitap slug'i olamaz
        "rn:sozler:" + "a" * 65 + ":p1",  # 65 karakter slug
    ],
)
def test_rn_yolu_gecersiz_capa_girdi_hatasi(capa: str) -> None:
    with pytest.raises(GirdiHatasi):
        A.rn_yolu(capa)


# --- normalize -------------------------------------------------------------------------------


def test_normalize_turkce_kitapta_tr_ve_ar_norm_sutunlari() -> None:
    sonuc = donustur(sentetik_txt())
    normal, _ = zincir(sonuc)
    ingest = {s.veri["anchor"]: s.veri for s in ingest_satirlari(sonuc)}
    assert len(normal) == len(ingest)
    arapca = 0
    for n in normal:
        assert set(n) == A.NORMALIZE_ALANLARI
        ham = ingest[n["anchor"]]
        # metin, capa ve attrs degismez
        assert n["text"] == ham["text"] and n["attrs"] == ham["attrs"]
        k = search_keys(n["text"])
        assert (n["tr_narrow"], n["tr_wide"], n["tr_stem"]) == (k.tr_narrow, k.tr_wide, k.tr_stem)
        assert n["ar_norm"] == (k.ar_norm or None)
        assert n["provenance"]["arama"] == {"normalizer_version": NORMALIZER_VERSION}
        arapca += n["ar_norm"] is not None
    assert arapca >= 1  # Arapca bloklu birimlerde ar_norm dolu
    assert any(n["ar_norm"] is None for n in normal)  # Arapca olmayan birimde null
    assert all(isinstance(n["tr_narrow"], str) for n in normal)
    # yalniz Turkce kisim tr_narrow'a girer, Arapca harf girmez
    ar_birimi = next(
        n for n in normal if n["ar_norm"] is not None and AR_SEDDE not in n["tr_narrow"]
    )
    assert not any("؀" <= c <= "ۿ" for c in ar_birimi["tr_narrow"])


@pytest.mark.parametrize("dil", ["ota", "ar"])
def test_normalize_osmanlica_arapca_yalniz_ar_norm(dil: str) -> None:
    satirlar = [
        "#4",
        "<Deneme Kitap>",
        f"   {AR} {AR_SEDDE}",
        "   Deneme Latin paragrafı",  # Arapca harfi olmayan birim: ar_norm null
    ]
    kitap = [kitap_kaydi(f"deneme-kitap-{'osmanlica' if dil == 'ota' else 'arapca'}", dil=dil)]
    sonuc = donustur(sentetik_txt(satirlar), kitap=kitap)
    normal, _ = zincir(sonuc)
    govde = [n for n in normal if n["text"].startswith(AR[:3])]
    assert len(govde) == 1
    assert all(
        n["tr_narrow"] is None and n["tr_wide"] is None and n["tr_stem"] is None for n in normal
    )
    assert govde[0]["ar_norm"] == normalize_ar(govde[0]["text"]) != ""
    assert normal[-1]["ar_norm"] is None  # Latin metin: Arapca anahtar yok
    assert all(n["attrs"]["dil"] == dil for n in normal)


def test_normalize_satiri_alan_kumesi_ve_kaynak_denetimi() -> None:
    sonuc = donustur(sentetik_txt())
    satir = ingest_satirlari(sonuc)[0]
    fazla = Satir("ingest", 1, {**satir.veri, "fazla": 1})
    with pytest.raises(GirdiHatasi, match="alan kumesi"):
        A.normalize_satiri(KAYNAK, fazla)
    with pytest.raises(GirdiHatasi, match="source_id"):
        A.normalize_satiri("baska-kaynak", satir)
    dil_yok = copy.deepcopy(satir.veri)
    dil_yok["attrs"]["dil"] = "fr"
    with pytest.raises(GirdiHatasi, match=r"attrs.dil"):
        A.normalize_satiri(KAYNAK, Satir("ingest", 1, dil_yok))


# --- anchor ----------------------------------------------------------------------------------


def test_anchor_alanlari_rol_parent_path_ve_attrs() -> None:
    sonuc = donustur(sentetik_txt())
    _, anchor = zincir(sonuc)
    for a in anchor:
        assert set(a) == A.ANCHOR_ALANLARI
        assert a["kind"] == "risale" and a["metin_durumu"] == "taslak"
        assert a["ayah_lo"] is None and a["ayah_hi"] is None
        assert a["data_version"] == f"{KAYNAK}@{SURUM}"
        assert a["provenance"]["cumle"] == {"surum": CUMLE_SURUMU}
        assert a["provenance"]["arama"] == {"normalizer_version": NORMALIZER_VERSION}
        # attrs: kind, marks, bolum_yolu ve slug ust alanlara tasindi
        for ad in A.TASINAN_ATTRS:
            assert ad not in a["attrs"]
        assert a["attrs"]["dil"] == "tr" and a["attrs"]["yon"] == "ltr"
        assert len(a["attrs"]["baslik_yolu"]) == a["parent_path"].count(":") - 1 - int(
            a["role"] == "dipnot"
        )
    h = harita(anchor)
    assert h["rn:deneme-kitap:deneme-bolum-1:p1"]["role"] == "baslik"
    assert h["rn:deneme-kitap:deneme-bolum-1:p1"]["parent_path"] == "rn:deneme-kitap:deneme-bolum-1"
    assert h["rn:deneme-kitap:deneme-bolum-1:p2"]["role"] == "govde"
    dipnot = h["rn:deneme-kitap:deneme-bolum-1:hasiye-1:p1"]
    assert dipnot["role"] == "dipnot"
    assert dipnot["parent_path"] == "rn:deneme-kitap:deneme-bolum-1:hasiye-1"
    assert h["rn:deneme-kitap:p1"]["parent_path"] == "rn:deneme-kitap"  # kok seviye


def test_anchor_marks_ar_hasiye_rnk_kalir_satir_isareti_atilir() -> None:
    sonuc = donustur(sentetik_txt())
    ham = {b.anchor: b for b in sonuc.birimler}
    _, anchor = zincir(sonuc)
    turler: set[str] = set()
    for a in anchor:
        marks = a["marks"]
        turler |= {m["t"] for m in marks}
        # satir (birlestirme bosluk) isareti atilir; ingest'tekinden yalniz o fark eder
        beklenen = [m for m in ham[a["anchor"]].attrs["marks"] if m["t"] != "satir"]  # type: ignore[attr-defined]
        assert marks == beklenen
        for m in marks:  # yari acik aralik metne sigar
            assert 0 <= m["s"] <= m.get("e", m["s"]) <= len(a["text"])
    assert {"ar", "hasiye", "rnk"} <= turler
    assert "satir" not in turler
    assert any(
        m["t"] == "satir"
        for b in sonuc.birimler
        for m in b.attrs["marks"]  # type: ignore[attr-defined]
    )  # ingest'te vardi


def test_anchor_sentences_yari_acik_ve_baslik_birimi_bos() -> None:
    sonuc = donustur(sentetik_txt())
    h = harita(zincir(sonuc)[1])
    p = h["rn:deneme-kitap:deneme-bolum-1:p2"]  # sayfa kirilan paragraf, iki cumle
    metin = p["text"]
    (b1, s1), (b2, s2) = p["sentences"]
    assert 0 == b1 < s1 < b2 < s2 <= len(metin)
    assert metin[b1:s1].endswith("kesildi.") and metin[b2:s2] == "Deneme paragrafı 1 sonu."
    assert metin[s1:b2].strip(" ") == ""  # cumleler arasi yalniz bosluk
    assert h["rn:deneme-kitap:deneme-bolum-1:p1"]["sentences"] == []  # baslik birimi
    for a in h.values():  # kod noktasi, yari acik, artan, ayrik
        onceki = 0
        for bas, son in a["sentences"]:
            assert onceki <= bas < son <= len(a["text"])
            onceki = son


def test_anchor_sentences_ar_isaretinde_bolunmez() -> None:
    satirlar = [
        "#4",
        "<Deneme Kitap>",
        f"   Deneme cümle bir. Deneme ﹛{AR}. {AR}|﹜ Deneme sonu. Deneme son cümle.",
    ]
    sonuc = donustur(sentetik_txt(satirlar))
    a = next(x for x in zincir(sonuc)[1] if x["role"] == "govde")
    metin = a["text"]
    (ar,) = [(m["s"], m["e"]) for m in a["marks"] if m["t"] == "ar"]
    # ar araligi korunmazsa nokta + Arap harfi cumleyi boler (Arap harfi kucuk harf degildir)
    korumasiz = cumleleri_ayir(metin)
    assert any(ar[0] < son < ar[1] for _, son in korumasiz)
    korumali = a["sentences"]
    assert not any(ar[0] < son < ar[1] for _, son in korumali)
    assert not any(ar[0] < bas < ar[1] for bas, _ in korumali)
    assert [metin[b:s].startswith("Deneme") for b, s in korumali] == [True, True, True]


def test_anchor_content_hash_nfc_uygulanmaz() -> None:
    nfc_degisir = "ا\u0651\u064eب"  # sedde sonra fetha: NFC fetha, sedde sirasina cevirirdi
    satirlar = ["#4", "<Deneme Kitap>", f"   Deneme paragrafı {nfc_degisir} sonu."]
    sonuc = donustur(sentetik_txt(satirlar))
    a = next(x for x in zincir(sonuc)[1] if nfc_degisir in x["text"])
    ham = a["text"]
    assert unicodedata.normalize("NFC", ham) != ham
    assert a["content_hash"] == hashlib.sha256(ham.encode("utf-8")).hexdigest()
    nfc = hashlib.sha256(unicodedata.normalize("NFC", ham).encode("utf-8")).hexdigest()
    assert a["content_hash"] != nfc


def test_anchor_ord_okuma_sirasi_hasiye_ana_paragrafin_ardindan() -> None:
    sonuc = donustur(sentetik_txt())
    _, anchor = zincir(sonuc)
    ordlar = [a["ord"] for a in anchor]
    assert sorted(ordlar) == list(range(1, len(anchor) + 1))
    h = harita(anchor)
    ana = h["rn:deneme-kitap:deneme-bolum-1:p3"]
    dipnot = h["rn:deneme-kitap:deneme-bolum-1:hasiye-1:p1"]
    assert dipnot["ord"] == ana["ord"] + 1  # ayni satirdan baslayan dipnot ana paragrafi izler
    kok = h["rn:deneme-kitap:p1"]
    assert kok["ord"] == 1  # kitap basligi ilk
    # okuma sirasi dosya satir sirasidir
    sirali = sorted(anchor, key=lambda a: a["ord"])
    satirlar = [a["provenance"]["konum"]["satir"][0] for a in sirali]
    assert satirlar == sorted(satirlar)


def test_anchor_ord_bolunmus_kitapta_her_kitap_birden_baslar() -> None:
    bol = Bolunme(7, (BolunmeParcasi("deneme-a", 4), BolunmeParcasi("deneme-b", 6)))
    kitap = [kitap_kaydi("deneme-a", bolunme=bol), kitap_kaydi("deneme-b", bolunme=bol)]
    sonuc = donustur(sentetik_txt(), kitap=kitap)
    _, anchor = zincir(sonuc)
    for slug in ("deneme-a", "deneme-b"):
        ordlar = sorted(a["ord"] for a in anchor if a["anchor"].split(":")[1] == slug)
        assert ordlar == list(range(1, len(ordlar) + 1)) and ordlar


def test_anchor_satiri_tutarsiz_attrs_ve_isaret_girdi_hatasi() -> None:
    sonuc = donustur(sentetik_txt())
    normal, _ = zincir(sonuc)
    ilk = normal[1]

    def dene(degis: Any, mesaj: str) -> None:
        veri = copy.deepcopy(ilk)
        degis(veri)
        with pytest.raises(GirdiHatasi, match=mesaj):
            A.anchor_satiri(KAYNAK, Satir("normalize", 1, veri), SURUM)

    dene(lambda v: v["attrs"].__setitem__("bolum_yolu", ["baska"]), "capayla tutarsiz")
    dene(lambda v: v["attrs"].__setitem__("slug", "baska"), "capayla tutarsiz")
    dene(lambda v: v["attrs"].__setitem__("marks", [{"t": "yok", "s": 0}]), "isaret turu")
    dene(lambda v: v["attrs"].__setitem__("marks", [{"t": "ar", "s": 0, "e": 10**6}]), "aralig")
    dene(lambda v: v.pop("ar_norm"), "alan kumesi")
    dene(lambda v: v.__setitem__("anchor", "rn:deneme-kitap:deneme-bolum-1:p1:s1"), "capa")


# --- G-CAP -----------------------------------------------------------------------------------


def capa_girdisi(degistir: Any = None) -> Q.RnkGirdisi:
    """Sentetik anchor zinciri olan `RnkGirdisi`; `degistir(satirlar)` anchor satirlarini bozar."""
    _, satirlar = zincir(donustur(sentetik_txt()))
    if degistir is not None:
        degistir(satirlar)
    g = girdi_kur()
    g.anchor = lambda: iter(copy.deepcopy(satirlar))
    return g


def bulgu(g: Q.RnkGirdisi, kapi: str = "G-CAP", parca: str | None = None) -> list[str]:
    sonuc = Q.KAPI_ISLEVLERI[kapi](g)
    return [b for b in sonuc.bulgular if parca is None or parca in b]


def test_g_cap_sentetik_gecer_ve_sayilar() -> None:
    sonuc = Q.g_cap(capa_girdisi())
    assert sonuc.gecti, sonuc.bulgular
    assert sonuc.sayilar["kitap"] == 1 and sonuc.sayilar["capa"] == len(
        donustur(sentetik_txt()).birimler
    )
    assert sonuc.sayilar["onceki_run"] == 0
    assert any(k.startswith("derinlik_") for k in sonuc.sayilar)


def test_g_cap_yinelenen_capa_kalir() -> None:
    g = capa_girdisi(lambda s: s.append(copy.deepcopy(s[2])))
    assert bulgu(g, parca="yinelenen capa")


def test_g_cap_dizin_slugi_kalir() -> None:
    g = capa_girdisi(lambda s: s[0].__setitem__("anchor", "rn:dizin:p1"))
    assert bulgu(g, parca="paket kimligi risale-dizin")
    assert not Q.g_cap(g).gecti


def test_g_cap_65_karakter_slug_kalir() -> None:
    g = capa_girdisi(lambda s: s[0].__setitem__("anchor", "rn:deneme-kitap:" + "a" * 65 + ":p1"))
    assert bulgu(g, parca="gecersiz capa")


def test_g_cap_64_karakter_slug_gramerden_gecer_ama_parent_path_tutmaz() -> None:
    g = capa_girdisi(lambda s: s[0].__setitem__("anchor", "rn:deneme-kitap:" + "a" * 64 + ":p1"))
    assert not bulgu(g, parca="gecersiz capa")
    assert bulgu(g, parca="parent_path")


def test_g_cap_oz_yinelenen_capa_ve_onek_kurali() -> None:
    g = capa_girdisi(lambda s: s[0].__setitem__("anchor", "rn:deneme-kitap:deneme-kitap:p1"))
    assert bulgu(g, parca="oz yinelenen capa")
    g = capa_girdisi(lambda s: s[0].__setitem__("anchor", "meal:elmalili:2:255"))
    assert bulgu(g, parca="gecersiz capa")  # rn: onekli degil
    g = capa_girdisi(lambda s: s[0].__setitem__("anchor", "rn:baska-kitap:p1"))
    assert bulgu(g, parca="kitap tabloda yok")


def test_g_cap_sabit_alanlar_hash_ve_parent_path() -> None:
    assert bulgu(
        capa_girdisi(lambda s: s[3].__setitem__("content_hash", "0" * 64)), parca="content_hash"
    )
    assert bulgu(capa_girdisi(lambda s: s[3].__setitem__("content_hash", "ABC")), parca="biciminde")
    assert bulgu(
        capa_girdisi(lambda s: s[3].__setitem__("parent_path", "rn:x")), parca="parent_path"
    )
    assert bulgu(capa_girdisi(lambda s: s[3].__setitem__("kind", "kitap")), parca="sabit alan")
    assert bulgu(
        capa_girdisi(lambda s: s[3].__setitem__("metin_durumu", "onayli")), parca="sabit alan"
    )
    govde = lambda s: next(x for x in s if x["role"] == "govde")  # noqa: E731
    assert bulgu(capa_girdisi(lambda s: govde(s).__setitem__("role", "dipnot")), parca="role")
    assert bulgu(capa_girdisi(lambda s: s[3].pop("marks")), parca="alan kumesi")
    assert bulgu(
        capa_girdisi(lambda s: s[3]["attrs"].__setitem__("dil", "ota")), parca="dil ve yon"
    )


def test_g_cap_ord_ve_aralik_hatalari() -> None:
    assert bulgu(capa_girdisi(lambda s: s[3].__setitem__("ord", 99)), parca="ord")
    sec = lambda s: next(x for x in s if x["sentences"])  # noqa: E731
    assert bulgu(
        capa_girdisi(lambda s: sec(s).__setitem__("sentences", [[0, 10**6]])),
        parca="sentences araligi",
    )
    assert bulgu(
        capa_girdisi(lambda s: sec(s).__setitem__("sentences", [[0, 3], [2, 5]])),
        parca="sentences araligi",
    )  # ust uste binen aralik
    assert bulgu(
        capa_girdisi(lambda s: sec(s).__setitem__("sentences", [[0, 3]])),
        parca="ayiriciyla yeniden uretilemedi",
    )
    assert bulgu(
        capa_girdisi(lambda s: sec(s)["marks"].append({"t": "rnk", "s": 0, "e": 10**6, "c": "~"})),
        parca="marks araligi",
    )
    assert bulgu(
        capa_girdisi(lambda s: s[0].__setitem__("sentences", [[0, 1]])),
        parca="baslik biriminde cumle",
    )
    assert bulgu(
        capa_girdisi(lambda s: s[3]["provenance"].pop("cumle")), parca="provenance.cumle.surum"
    )


def test_g_cap_cumle_ar_isaretinde_bolunmus_kalir() -> None:
    def boz(satirlar: list[dict[str, Any]]) -> None:
        a = next(
            x for x in satirlar if any(m["t"] == "ar" for m in x["marks"]) and x["role"] == "govde"
        )
        ar = next((m["s"], m["e"]) for m in a["marks"] if m["t"] == "ar")
        # sahte sinir: ar araligini iki cumleye boler
        orta = (ar[0] + ar[1]) // 2
        a["sentences"] = [[0, orta], [orta + 1, len(a["text"])]]

    g = capa_girdisi(boz)
    assert bulgu(g, parca="ar isaretinde cumle siniri")


def test_g_cap_capasiz_kitap_ve_okuma_sirasi() -> None:
    g = capa_girdisi()
    g.tablo = (*g.tablo, kitap_kaydi("baska-deneme", uid="baska"))
    assert bulgu(g, parca="capasiz kitap")
    g = capa_girdisi(lambda s: s.reverse())
    assert bulgu(g, parca="okuma sirasi")


def test_g_cap_anchor_ciktisi_yoksa_kalir() -> None:
    g = girdi_kur()
    assert g.anchor is None and not Q.g_cap(g).gecti


def test_g_cap_onceki_calisma_yoksa_atlanir_varsa_capalar_ve_hash_tutar() -> None:
    g = capa_girdisi()
    anchor = list(g.anchor())  # type: ignore[misc]
    ozetler = {a["anchor"]: a["content_hash"] for a in anchor}
    assert Q.g_cap(g).sayilar["onceki_run"] == 0  # onceki yok: atlandi
    g.onceki = Onceki("0" * 36, dict(ozetler))
    g.onceki_kilit_ozeti = g.kilit_ozeti_manifest
    sonuc = Q.g_cap(g)
    assert sonuc.gecti and sonuc.sayilar["onceki_run"] == 1 and sonuc.sayilar["hash_degisen"] == 0
    # onceki surumde olup kaybolan capa kapiyi kaldirir (capa yeniden numaralanmaz)
    g.onceki = Onceki("0" * 36, {**ozetler, "rn:deneme-kitap:eski-bolum:p1": "1" * 64})
    assert bulgu(g, parca="kaybolan capa")
    # ayni kilit iken content_hash farki kaldirir
    ilk = next(iter(ozetler))
    g.onceki = Onceki("0" * 36, {**ozetler, ilk: "2" * 64})
    assert bulgu(g, parca="content_hash farkli")
    # kaynak kilidi degistiyse hash farki kabul edilir, kaybolan capa yine kalir
    g.onceki_kilit_ozeti = "9" * 64
    assert Q.g_cap(g).gecti
    g.onceki = Onceki("0" * 36, {**ozetler, "rn:deneme-kitap:eski-bolum:p1": "1" * 64})
    assert bulgu(g, parca="kaybolan capa")


# --- G-NOR (anchor ciktisi) ------------------------------------------------------------------


def test_g_nor_anchor_ciktisi_sentetik_gecer() -> None:
    sonuc = Q.g_nor(capa_girdisi())
    assert sonuc.gecti, sonuc.bulgular
    assert sonuc.sayilar["tr_denetlenen"] == sonuc.sayilar["ar_norm_denetlenen"] > 0
    assert sonuc.sayilar["ar_norm_dolu"] >= 1 and sonuc.sayilar["ota_ar_birim"] == 0


def test_g_nor_tr_kitapta_tr_sutunu_null_ya_da_yanlis_kalir() -> None:
    assert bulgu(capa_girdisi(lambda s: s[3].__setitem__("tr_narrow", None)), "G-NOR", "null")
    assert bulgu(capa_girdisi(lambda s: s[3].__setitem__("tr_stem", "yanlis")), "G-NOR", "tr_*")
    assert bulgu(capa_girdisi(lambda s: s[3].__setitem__("ar_norm", "yanlis")), "G-NOR", "ar_norm")
    assert bulgu(
        capa_girdisi(lambda s: s[3]["provenance"].pop("arama")), "G-NOR", "normalizer_version"
    )


def test_g_nor_osmanlica_arapca_tr_dolu_ya_da_ar_norm_bos_kalir() -> None:
    def ota(satirlar: list[dict[str, Any]]) -> None:
        for a in satirlar:
            a["attrs"]["dil"] = "ota"
            a["tr_narrow"] = a["tr_wide"] = a["tr_stem"] = None
            a["ar_norm"] = normalize_ar(a["text"]) or None

    g = capa_girdisi(ota)
    assert Q.g_nor(g).gecti, Q.g_nor(g).bulgular
    assert Q.g_nor(g).sayilar["ota_ar_birim"] > 0

    def tr_dolu(satirlar: list[dict[str, Any]]) -> None:
        ota(satirlar)
        satirlar[3]["tr_wide"] = "x"

    assert bulgu(capa_girdisi(tr_dolu), "G-NOR", "Osmanlica/Arapca birimde tr_*")

    def ar_bos(satirlar: list[dict[str, Any]]) -> None:
        ota(satirlar)
        arapca = next(a for a in satirlar if a["ar_norm"] is not None)
        arapca["ar_norm"] = None

    assert bulgu(capa_girdisi(ar_bos), "G-NOR", "ar_norm")


def test_sentetik_json_sabit_kalir() -> None:
    """Yardimci: bu dosyanin kullandigi sentetik sayfa araligi test_risale_rnk ile ayni."""
    assert SENTETIK_JSON["meta_data"]["first_page"] == 4
