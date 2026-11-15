"""Diyanet Risale alimi: txt, hizalama, cikarma, kimlik ve kilit (A20.1; SENTETIK, `data/` yok)."""

import dataclasses
import json
import unicodedata
from pathlib import Path

import pytest
from risale_yardimci import (
    ARAPCA_1,
    ARAPCA_2,
    ARAPCA_3,
    COMMIT,
    KIMLIK,
    NFC_DEGIL,
    TXT_1,
    UYELER_1,
    kimlik_baytlari,
    risale_hazirla,
    zip_yap,
)

from mutalaa_pipeline.anchor import parse, risale
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.ingest import risale_diyanet as D
from mutalaa_pipeline.ingest.risale_md import md_coz
from mutalaa_pipeline.ingest.risale_zip import GuvenliZip

KOK_DOSYASI = Path(__file__).resolve().parents[2]


@pytest.fixture
def cikarim(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> D.Cikarim:
    kok = risale_hazirla(tmp_path, monkeypatch)
    return D.yeniden_uret(kok.zip_baytlari, D.kilit_yukle(), D.kimlik_yukle())


def birim(c: D.Cikarim, capa: str) -> D.StagedUnit:
    (b,) = (b for b in c.birimler if b.anchor == capa)
    return b


# --- txt -----------------------------------------------------------------------------------


def test_txt_satirlari_bayt_bayt_ve_ayiraclar_birim_degil() -> None:
    t = D.txt_coz("Deneme\u00adbir\n***\n  \n\nDeneme\u200c iki \u00a0\n \u00a0 \n")
    assert t.govde == [(1, "Deneme\u00adbir"), (5, "Deneme\u200c iki \u00a0")]  # kirpma yok
    assert t.ayirici == 1
    assert t.yalniz_bosluk == 2  # "  " ve " \u00a0 "
    assert t.bos_olmayan == 3  # iki metin + ayirac


def test_txt_bom_ve_crlf_metne_girmez_dosya_duzeyi_sayilir() -> None:
    t = D.txt_coz("\ufeffDeneme bir\r\nDeneme iki\r\n")
    assert [m for _, m in t.govde] == ["Deneme bir", "Deneme iki"]
    assert t.bom and t.crlf == 2


def test_txt_tek_cr_metinde_kalir_kapi_karakter_kuralinda_yakalar() -> None:
    t = D.txt_coz("Deneme\rbir\nDeneme iki")
    assert t.govde[0][1] == "Deneme\rbir" and t.crlf == 0


def test_txt_ilk_dipnot_satirindan_sonrasi_dipnot_bolumudur() -> None:
    t = D.txt_coz(
        "Deneme (H\u00e2\u015fiye[1]) paragrafi\n***\n[1] Birinci dipnot\nDevam satiri\n"
        "[2] \u0130kinci dipnot\n***\nSon devam\n"
    )
    assert [m for _, m in t.govde] == ["Deneme (H\u00e2\u015fiye[1]) paragrafi"]
    assert [(d.etiket, [m for _, m in d.satirlar]) for d in t.dipnotlar] == [
        ("1", ["Birinci dipnot", "Devam satiri"]),
        ("2", ["\u0130kinci dipnot", "Son devam"]),
    ]
    assert t.atif == 1


def test_txt_dipnot_etiketi_arap_hindi_rakamlari_da_olabilir() -> None:
    t = D.txt_coz("Deneme\n[\u0661] Dipnot\n")
    assert t.dipnotlar[0].etiket == "\u0661"


def test_txt_kelime_sayimi_w_ile_ve_etiket_dahil() -> None:
    assert D.txt_coz("Deneme iki\n[1] Dipnot").kelime == 4  # Deneme, iki, 1, Dipnot


# --- hizalama ve isaretler ------------------------------------------------------------------


def test_hizala_baslik_ve_arapca_isaretini_anahtar_esitligiyle_eslestirir() -> None:
    md = md_coz(f'# Deneme\n\n<p class="arabic" dir="rtl">{ARAPCA_1}</p>\n\nDeneme paragrafi 1\n')
    txt = [(1, "Deneme"), (2, ARAPCA_1), (3, "Deneme paragrafi 1"), (4, "Fazla satir")]
    eslesme, eslesen = D.hizala(txt, md.govde)
    assert sorted(eslesme) == [0, 1, 2] and eslesen == {0, 1, 2}
    assert eslesme[0].tur == "baslik" and eslesme[1].tam_arapca
    # hizalanamayan txt satiri (3) tahmin edilmez
    assert 3 not in eslesme


def test_hizala_baslik_txt_de_yoksa_hizalanamayan_baslik_olur() -> None:
    md = md_coz("# Deneme\n\n## Yalniz markdown\n\nDeneme paragrafi 1\n")
    eslesme, eslesen = D.hizala([(1, "Deneme"), (2, "Deneme paragrafi 1")], md.govde)
    assert len(eslesme) == 2
    assert [i for i, s in enumerate(md.govde) if s.tur == "baslik" and i not in eslesen] == [1]


def test_hizala_br_ile_bolunmus_blok_txt_de_tek_satirsa_ikinci_gecis_eslestirir() -> None:
    md = md_coz(f'<p class="arabic" dir="rtl">{ARAPCA_2}<br/>{ARAPCA_3}</p>\n')
    metin = f"{ARAPCA_2} {ARAPCA_3}"
    eslesme, eslesen = D.hizala([(1, metin)], md.govde)
    assert eslesen == {0, 1} and eslesme[0].tam_arapca
    isaretler, cozulemeyen = D.arapca_isaretleri(metin, eslesme[0])
    assert isaretler == [{"s": 0, "e": len(metin), "t": "ar"}] and cozulemeyen == 0


def test_arapca_isareti_satir_ici_kod_noktasi_araligi() -> None:
    md = md_coz(f'Deneme <span class="arabic" dir="rtl">{ARAPCA_1}</span> paragrafi\n')
    metin = f"Deneme {ARAPCA_1} paragrafi"
    eslesme, _ = D.hizala([(1, metin)], md.govde)
    (isaret,) = D.arapca_isaretleri(metin, eslesme[0])[0]
    assert metin[isaret["s"] : isaret["e"]] == ARAPCA_1  # type: ignore[index]
    assert isaret["t"] == "ar"


def test_arapca_isareti_txt_de_bulunamazsa_cozulemeyen_sayilir() -> None:
    md = md_coz(f'Deneme <span class="arabic" dir="rtl">{ARAPCA_1}</span> paragrafi\n')
    isaretler, cozulemeyen = D.arapca_isaretleri("Deneme baska paragrafi", md.govde[0])
    assert isaretler == [] and cozulemeyen == 1


# --- cikarma -------------------------------------------------------------------------------


def test_capalar_bolum_dosya_basina_ve_dipnot_hasiye_yolu(cikarim: D.Cikarim) -> None:
    capalar = [b.anchor for b in cikarim.birimler]
    assert capalar == [
        *(f"rn:deneme:soz-1:p{n}" for n in range(1, 8)),
        "rn:deneme:soz-1:hasiye-1:p1",
        "rn:deneme:soz-1:hasiye-1:p2",
        "rn:deneme:soz-1:hasiye-2:p1",
        "rn:deneme:soz-1:hasiye-3:p1",
        *(f"rn:deneme:soz-3:p{n}" for n in range(1, 4)),
        "rn:kucuk-deneme:p1",
        "rn:kucuk-deneme:p2",
    ]
    assert len(set(capalar)) == len(capalar)
    for capa in capalar:
        parse(capa)  # ortak ayristirici kabul eder (kanonik)
    assert risale.capa_paket_kimligi("rn:deneme:soz-1:p1") == "risale-deneme"


def test_bolum_numarasi_kaynakta_yoksa_doldurulmaz_eksik_yazilir(cikarim: D.Cikarim) -> None:
    # tablo soz-1 ve soz-3 verir; soz-2 uydurulmaz, rapora yazilir
    assert cikarim.eksik_numaralar["deneme"] == ["soz-2"]
    assert cikarim.eksik_numaralar["kucuk-deneme"] == []
    assert not any(":soz-2:" in b.anchor for b in cikarim.birimler)


def test_metin_txt_satir_baytlariyla_ayni_nfc_yok(cikarim: D.Cikarim) -> None:
    satirlar = TXT_1.split("\n")
    metinler = [birim(cikarim, f"rn:deneme:soz-1:p{n}").text for n in range(1, 8)]
    assert metinler == [satirlar[i] for i in (0, 1, 2, 3, 4, 6, 7)]
    p5 = metinler[4]
    assert "\u00ad" in p5 and "\u200c" in p5 and "\u00a0" in p5  # korunur
    p7 = metinler[6]
    assert NFC_DEGIL in p7 and unicodedata.normalize("NFC", p7) != p7  # NFC uygulanmadi


def test_baslik_duzeyi_markdowndan_ve_hizalama_attrs(cikarim: D.Cikarim) -> None:
    p1 = birim(cikarim, "rn:deneme:soz-1:p1").attrs
    p6 = birim(cikarim, "rn:deneme:soz-1:p6").attrs
    p3 = birim(cikarim, "rn:deneme:soz-1:p3").attrs
    assert (p1["rol"], p1["baslik_duzeyi"], p1["hizalama"]) == ("baslik", 1, "md")
    assert (p6["rol"], p6["baslik_duzeyi"]) == ("baslik", 2)
    assert (p3["rol"], p3["hizalama"]) == ("paragraf", "md")
    assert "marks" not in p3


def test_arapca_isaretleri_marks_olur_metin_degismez(cikarim: D.Cikarim) -> None:
    p2 = birim(cikarim, "rn:deneme:soz-1:p2")
    assert p2.text == ARAPCA_1 and p2.attrs["marks"] == [{"s": 0, "e": len(ARAPCA_1), "t": "ar"}]
    p4 = birim(cikarim, "rn:deneme:soz-1:p4")
    (m,) = p4.attrs["marks"]  # type: ignore[misc]
    assert p4.text[m["s"] : m["e"]] == ARAPCA_2
    # br ile bolunmus blok txt'de tek satir: ikinci gecis
    iki = birim(cikarim, "rn:deneme:soz-3:p2")
    assert iki.attrs["marks"] == [{"s": 0, "e": len(iki.text), "t": "ar"}]


def test_dipnot_metni_txt_den_yoksa_markdowndan_ve_provenance_md(cikarim: D.Cikarim) -> None:
    d1 = birim(cikarim, "rn:deneme:soz-1:hasiye-1:p1")
    # `[1] ` etiketi atilir, kalan txt baytlari ("Hasiye: ..." dahil) oldugu gibi kalir
    assert d1.text == "Hâşiye: Deneme dipnotu 1." and d1.provenance["kaynak"] == "txt"
    assert d1.attrs == {"rol": "dipnot", "etiket": "1"}
    devam = birim(cikarim, "rn:deneme:soz-1:hasiye-1:p2")
    assert devam.text == "Deneme dipnotu devam sat\u0131r\u0131." and devam.attrs["devam"] is True
    md_dipnot = birim(cikarim, "rn:deneme:soz-1:hasiye-3:p1")
    assert md_dipnot.text == "Yaln\u0131z markdown dipnotu."
    assert md_dipnot.provenance["kaynak"] == "md"
    assert md_dipnot.provenance["dosya"].endswith("01 Birinci.md")  # type: ignore[union-attr]
    # dipnot atifi paragraf metninde oldugu gibi kalir
    assert "(H\u00e2\u015fiye[1])" in birim(cikarim, "rn:deneme:soz-1:p3").text


def test_bom_ve_crlf_dosya_duzeyi_sayilir_metne_girmez(cikarim: D.Cikarim) -> None:
    s = cikarim.sayilar["deneme"]
    assert s["bom_dosya"] == 1 and s["crlf_dosya"] == 1
    assert not any("\ufeff" in b.text or "\r" in b.text for b in cikarim.birimler)


def test_md_karsiligi_olmayan_dosya_hizalama_md_yok_ve_raporlanir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    kimlik = json.loads(json.dumps(KIMLIK))
    kimlik["kitaplar"][0]["dosyalar"][1]["md"] = None
    kok = risale_hazirla(tmp_path, monkeypatch, kimlik=kimlik)
    c = D.yeniden_uret(kok.zip_baytlari, D.kilit_yukle(), D.kimlik_yukle())
    assert birim(c, "rn:deneme:soz-3:p1").attrs["hizalama"] == "md-yok"
    assert c.md_karsiligi_yok == ["deneme: txt/01 Deneme/Deneme-02-Ikinci.txt"]
    assert c.sayilar["deneme"]["md_karsiligi_yok_dosya"] == 1


def test_karakter_sayilari_kilitli_siniflar_ve_nfc_sayisi(cikarim: D.Cikarim) -> None:
    assert cikarim.karakterler["deneme"] == {"U+00A0": 1, "U+00AD": 1, "U+200C": 1}
    assert cikarim.sayilar["deneme"]["nfc_degil_birim"] == 1
    assert cikarim.karakterler["kucuk-deneme"] == {}


def test_kitap_sayilari_ve_birim_toplami(cikarim: D.Cikarim) -> None:
    s = cikarim.sayilar["deneme"]
    assert (s["dosya"], s["md_dosya"], s["baslik"], s["paragraf"]) == (2, 2, 3, 7)
    assert s["dipnot_tanimi_md"] == 3 and s["dipnot_tanimi_txt"] == 2
    assert s["dipnot_tanimi_md_kaynakli"] == 1 and s["dipnot_birimi_md"] == 1
    assert s["birim"] == 14 and cikarim.sayilar["kucuk-deneme"]["birim"] == 2
    # txt birimleri = bos olmayan satirlar - ayiraclar
    assert s["paragraf"] + s["baslik"] + s["dipnot_birimi_txt"] == (
        s["bos_olmayan_satir"] - s["ayirici_satir"]
    )
    assert s["ayirici_satir"] == 2


# --- kimlik tablosu ------------------------------------------------------------------------


def _kimlik(**degisim: object) -> bytes:
    veri = json.loads(json.dumps(KIMLIK))
    veri.update(degisim)
    return kimlik_baytlari(veri)


def test_kimlik_gecerli_tablo_okunur() -> None:
    k = D.kimlik_coz(kimlik_baytlari())
    assert [x.slug for x in k.kitaplar] == ["deneme", "kucuk-deneme"]
    assert k.kitaplar[1].bolum_yolu(k.kitaplar[1].dosyalar[0]) == ("kucuk-deneme",)
    assert (
        k.kitaplar[0].txt_uyesi(k.kitaplar[0].dosyalar[0]) == "txt/01 Deneme/Deneme-01-Birinci.txt"
    )


@pytest.mark.parametrize(
    "degistir",
    [
        lambda v: v["kitaplar"][0].update(slug="dizin"),
        lambda v: v["kitaplar"][0].update(slug="p1"),
        lambda v: v["kitaplar"][0]["dosyalar"][0].update(bolum="soz-01"),
        lambda v: v["kitaplar"][0]["dosyalar"][0].update(bolum="p2"),
        lambda v: v["kitaplar"][0]["dosyalar"][1].update(bolum="soz-1"),  # yinelenen bolum
        lambda v: v["kitaplar"][0]["dosyalar"][1].update(bolum=None),  # cok dosyada bolum zorunlu
        lambda v: v["kitaplar"][0]["dosyalar"][0].update(txt="../x.txt"),
        lambda v: v["kitaplar"][0]["dosyalar"][0].update(txt="x.md"),
        lambda v: v["kitaplar"][0].update(txt_klasor="/mutlak"),
        lambda v: v["kitaplar"][0]["dosyalar"][0].update(md="C:/x.md"),
        lambda v: v["kitaplar"][0]["dosyalar"][0].update(fazla=1),
        lambda v: v["kitaplar"].append(dict(v["kitaplar"][0])),  # yinelenen slug
        lambda v: v.update(surum=2),
        lambda v: v["kitaplar"][1].update(md_klasor=None),  # md var ama klasor yok
    ],
)
def test_kimlik_gecersiz_tablo_reddedilir(degistir: object) -> None:
    veri = json.loads(json.dumps(KIMLIK))
    degistir(veri)  # type: ignore[operator]
    with pytest.raises(GirdiHatasi, match=r"risale_diyanet_kimlik\.json"):
        D.kimlik_coz(kimlik_baytlari(veri))


def test_kimlik_bom_ve_cr_ve_yinelenen_anahtar_reddedilir() -> None:
    govde = kimlik_baytlari()
    with pytest.raises(GirdiHatasi):
        D.kimlik_coz(b"\xef\xbb\xbf" + govde)
    with pytest.raises(GirdiHatasi):
        D.kimlik_coz(govde.replace(b"\n", b"\r\n"))
    with pytest.raises(GirdiHatasi):
        D.kimlik_coz(b'{"surum": 1, "surum": 1, "kitaplar": [], "md_yalniz": {}}')


# --- kilit ---------------------------------------------------------------------------------


def test_kilit_gidis_donus_ve_kimlik_uyumu(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    risale_hazirla(tmp_path, monkeypatch)
    kilit = D.kilit_yukle()
    assert kilit.commit == COMMIT and kilit.kok == f"Risale-i-Nur-Diyanet-{COMMIT}"
    assert D.kilit_coz(D.kilit_metni(kilit).encode("utf-8")) == kilit
    D.kilit_kimlik_denetle(kilit, D.kimlik_yukle())
    eksik = dataclasses.replace(kilit, kitaplar={"deneme": kilit.kitaplar["deneme"]})
    with pytest.raises(GirdiHatasi, match="kimlik tablosuyla ayni degil"):
        D.kilit_kimlik_denetle(eksik, D.kimlik_yukle())


@pytest.mark.parametrize(
    "degistir",
    [
        lambda v: v.update(commit="abc"),
        lambda v: v.update(kok="baska"),
        lambda v: v.update(alinma_tarihi="2026-13-45"),
        lambda v: v.update(depo_url="https://deneme.invalid/x"),
        lambda v: v["zip"].update(sha256="xyz"),
        lambda v: v["zip"].update(boyut=0),
        lambda v: v["zip"].update(ad="../x.zip"),
        lambda v: v["kitaplar"]["deneme"]["sayilar"].pop("birim"),
        lambda v: v["kitaplar"]["deneme"]["sayilar"].update(birim=-1),
        lambda v: v["kitaplar"]["deneme"]["sayilar"].update(birim="1"),
        lambda v: v["kitaplar"]["deneme"]["uyeler"].update(x="kisa"),
        lambda v: v["kitaplar"]["deneme"].update(fazla=1),
        lambda v: v.update(fazla=1),
        lambda v: v.update(surum=2),
    ],
)
def test_kilit_gecersiz_bicim_reddedilir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, degistir: object
) -> None:
    kok = risale_hazirla(tmp_path, monkeypatch)
    veri = json.loads(kok.kilit_yolu.read_text(encoding="utf-8"))
    degistir(veri)  # type: ignore[operator]
    with pytest.raises(GirdiHatasi, match=r"risale\.lock\.json"):
        D.kilit_coz(json.dumps(veri).encode("utf-8"))


def test_kilit_bom_cr_ve_ondalik_reddedilir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    kok = risale_hazirla(tmp_path, monkeypatch)
    ham = kok.kilit_yolu.read_bytes()
    for kotu in (
        b"\xef\xbb\xbf" + ham,
        ham.replace(b"\n", b"\r\n"),
        ham.replace(b'"surum": 1', b'"surum": 1.0'),
    ):
        with pytest.raises(GirdiHatasi):
            D.kilit_coz(kotu)


def test_zip_denetle_ozet_uye_sayisi_ve_uye_ozeti(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    kok = risale_hazirla(tmp_path, monkeypatch)
    kilit = D.kilit_yukle()
    D.zip_denetle(kilit, kok.zip_baytlari)  # tutar
    with pytest.raises(GirdiHatasi, match="zip ozeti kilitle tutmuyor"):
        D.zip_denetle(kilit, kok.zip_baytlari + b"x")
    fazla = dict(UYELER_1) | {"ek.txt": b"x"}
    fazla_zip = zip_yap(fazla)
    kilit_fazla = dataclasses.replace(
        kilit, zip_sha256=D.lineage.sha256_bayt(fazla_zip), zip_boyut=len(fazla_zip)
    )
    with pytest.raises(GirdiHatasi, match="uye sayisi kilitle tutmuyor"):
        D.zip_denetle(kilit_fazla, fazla_zip)
    degisen = dict(UYELER_1)
    degisen["txt/01 Deneme/Deneme-01-Birinci.txt"] = TXT_1.replace("Deneme", "Baska").encode(
        "utf-8"
    )
    degisen_zip = zip_yap(degisen)
    kilit_degisen = dataclasses.replace(
        kilit, zip_sha256=D.lineage.sha256_bayt(degisen_zip), zip_boyut=len(degisen_zip)
    )
    with pytest.raises(GirdiHatasi, match="uye ozeti kilitle tutmuyor"):
        D.zip_denetle(kilit_degisen, degisen_zip)


def test_cikar_zip_te_uye_yoksa_cikis_hatasi(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    kok = risale_hazirla(tmp_path, monkeypatch)
    eksik = {a: v for a, v in UYELER_1.items() if not a.endswith("Kucuk.txt")}
    with pytest.raises(GirdiHatasi, match="uye yok"):
        D.cikar(GuvenliZip(zip_yap(eksik)), D.kimlik_yukle(), D.kilit_yukle())
    assert kok.zip_baytlari  # zip degismedi


def test_txt_utf8_degilse_cikis_hatasi(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    risale_hazirla(tmp_path, monkeypatch)
    kotu = dict(UYELER_1)
    kotu["txt/02 Kucuk/Kucuk.txt"] = b"Deneme \xff\xfe"
    with pytest.raises(GirdiHatasi, match="UTF-8 degil"):
        D.cikar(GuvenliZip(zip_yap(kotu)), D.kimlik_yukle(), D.kilit_yukle())


# --- gercek tablolar (sentetik degil; yalniz yapi ve sayi) -----------------------------------


def test_gercek_kimlik_tablosu_gecerli_ve_kitap_tablosuyla_uyumlu() -> None:
    kimlik = D.kimlik_yukle()
    assert len(kimlik.kitaplar) == 25
    assert sum(len(k.dosyalar) for k in kimlik.kitaplar) == 298  # txt dosya sayisi
    for kitap in kimlik.kitaplar:
        yollar = [kitap.bolum_yolu(d) for d in kitap.dosyalar]
        for yol in yollar:
            risale.yol_denetle(yol)
            risale.rn_capa((*yol, "hasiye-1"), 1)  # capa kanonik ve uzunluk sinirinda
        assert len(set(yollar)) == len(yollar)
    ham = json.loads((KOK_DOSYASI / "shared" / "data" / "risale-kitaplar.json").read_bytes())
    tablo = {k["slug"]: k for k in ham["kitaplar"] if k.get("diyanet")}
    for kitap in kimlik.kitaplar:
        assert kitap.slug in tablo
        diyanet = tablo[kitap.slug]["diyanet"]
        assert diyanet["klasor"] == kitap.txt_klasor
        assert diyanet["dosyalar"] == [d.txt for d in kitap.dosyalar]


def test_gercek_kilit_kimlikle_uyumlu_ve_yalniz_sayi_ve_ozet() -> None:
    kilit, kimlik = D.kilit_yukle(), D.kimlik_yukle()
    D.kilit_kimlik_denetle(kilit, kimlik)
    assert kilit.commit == "a5abc3f3556aefbab830963996c4576ed660e059"
    assert kilit.zip_sha256 == "aec1ce15d1fd8061fd36942f4ff1e08bf3cc8bac4f5b368e2c38717a348981ab"
    for kitap in kimlik.kitaplar:
        uyeler = kilit.kitaplar[kitap.slug].uyeler
        for dosya in kitap.dosyalar:
            assert kitap.txt_uyesi(dosya) in uyeler  # her txt uyesinin ozeti kilitte
            md = kitap.md_uyesi(dosya)
            assert md is None or md in uyeler
    toplam = sum(k.sayilar["bos_olmayan_satir"] for k in kilit.kitaplar.values())
    assert toplam == 47558  # kaynak-secimi olcumuyle ayni
    assert sum(k.sayilar["kelime_w"] for k in kilit.kitaplar.values()) == 2000363
    assert sum(k.sayilar["dipnot_tanimi_md"] for k in kilit.kitaplar.values()) == 777
    assert sum(k.sayilar["dipnot_atfi_md"] for k in kilit.kitaplar.values()) == 775
    izinli = [d for k in kilit.kitaplar.values() for d in k.dipnot_uyusmazliklari]
    assert len(izinli) == 2  # 777 tanim ve 775 atif: iki Sualar dosyasi
    assert all(abs(t - a) == 1 for _, t, a in izinli)
