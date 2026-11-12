# ruff: noqa: RUF001
"""RNK ayristirici, staged, kilit, bagdastirici ve QA testleri (A20.1b; ACIKCA SENTETIK veri).

Hicbir Risale metni yoktur: sentetik RNK dosyalari "Deneme ..." yer tutucu metinleri ve Arap
alfabesi harfleriyle test icinde uretilir; `data/` altina baglanmaz. Gercek kilit dosyasi
(`risale_rnk.lock.json`) yalniz sayilar tasir; kilit testleri onu okur.
"""

import json
from collections import Counter
from pathlib import Path
from typing import Any

import pytest
from hat_yardimci import ctx_kur, depo_kur

from mutalaa_pipeline.adimlar import risale as A
from mutalaa_pipeline.anchor.risale import (
    Bolunme,
    BolunmeParcasi,
    Kitap,
    RnkBaglanti,
    kitap_haritasi,
    kitaplar,
)
from mutalaa_pipeline.enums import SourceKind
from mutalaa_pipeline.export.ortak import GirdiHatasi, depo_koku
from mutalaa_pipeline.ingest import risale_rnk as R
from mutalaa_pipeline.ingest import risale_rnk_kilit as kilit_modulu
from mutalaa_pipeline.ingest import risale_rnk_staged as S
from mutalaa_pipeline.ingest.base import run_ingest
from mutalaa_pipeline.ingest.risale_rnk_kaynaklari import (
    RnkBagdastirici,
    kilit_dosyalari,
    kilit_tablo_uyumu,
    rnk_dosyalari,
)
from mutalaa_pipeline.ingest.risale_rnk_kilit import (
    KAYNAK,
    KitapKilidi,
    RnkKilidi,
    kilit_metni,
    kilit_ozeti,
    kilit_uret,
    kilit_yukle,
)
from mutalaa_pipeline.lineage import sha256_bayt
from mutalaa_pipeline.qa import run_risale_rnk as qa_run_modulu
from mutalaa_pipeline.qa.checks import risale_rnk as Q
from mutalaa_pipeline.qa.run_risale_rnk import kapilari_kos, kapilari_sec
from mutalaa_pipeline.qa.run_risale_rnk import yukle as qa_yukle
from mutalaa_pipeline.sources.kayit import Kaynak

AR = "ابتثجحخ"  # Arap alfabesi harfleri (sentetik)
AR_SEDDE = "اَّب"  # fatha + shedde: NFC siralamayi degistirirdi
BIRIM_ISARETLERI = "~@|\\<>{}€∑∫﹛﹜§÷`%½&"

SENTETIK_SATIRLAR = [
    "#4",
    "<Deneme Kitap>",
    "&Deneme Bölüm 1>",
    "#5",
    "   Deneme paragrafı 1 başı, cümle",
    "#6",
    " ortasında kesildi. Deneme paragrafı 1 sonu.",
    "   \\Deneme vurgu:> Deneme paragrafı 2 {(*)|Deneme dipnotu 1.} devam.",
    f"~{AR}|@",
    "devam metni sonrası",
    f"   Deneme paragrafı 3 ﹛{AR_SEDDE}|﹜ sonu.",
    ",* * *>",
    "#7",
    "<Deneme Bölüm 2>",
    "&Deneme Eşleşmeyen>",
    "   ∫Deneme stil:> Deneme paragrafı 4.",
    "{(Deneme)|Deneme dipnotu 2 satır bir",
    "  Deneme dipnotu 2 satır iki.}",
    "§Deneme kapanış satırı>",
    "   ½Deneme yarım½ metni",
    "   Deneme paragrafı 5  nbsp ‌zwnj ­tire",
    f"~{AR}|@",
]
SENTETIK_JSON = {
    "meta_data": {
        "uid": "deneme",
        "shelf_id": "tr_k",
        "name": "Deneme",
        "language": "tr",
        "first_page": 4,
        "last_page": 7,
    },
    "contents": {
        "key": "x-4",
        "title": "Deneme Kitap",
        "textInBook": "",
        "pageNo": 4,
        "children": [
            {
                "key": "a-4",
                "title": "Deneme Bölüm 1",
                "textInBook": "",
                "pageNo": 4,
                "children": [],
            },
            {
                "key": "b-7",
                "title": "Deneme Bölüm 2",
                "textInBook": "",
                "pageNo": 7,
                "children": [],
            },
        ],
    },
}


def sentetik_txt(satirlar: list[str] | None = None, *, son_lf: bool = True) -> bytes:
    govde = "\n".join(satirlar if satirlar is not None else SENTETIK_SATIRLAR)
    return (govde + ("\n" if son_lf else "")).encode("utf-8")


def sentetik_json(**degisim: Any) -> bytes:
    veri = json.loads(json.dumps(SENTETIK_JSON))
    veri.update(degisim)
    return json.dumps(veri, ensure_ascii=False, indent=2).encode("utf-8")


def kitap_kaydi(
    slug: str = "deneme-kitap",
    raf: str = "tr_k",
    uid: str = "deneme",
    bolunme: Bolunme | None = None,
    dil: str = "tr",
) -> Kitap:
    return Kitap(
        slug=slug,
        baslik="Deneme Kitap",
        dil=dil,  # type: ignore[arg-type]
        yon="ltr" if dil == "tr" else "rtl",
        metin_kaynagi="rnk",
        diyanet_karsiligi="rnk",
        diyanet=None,
        rnk=RnkBaglanti(raf, uid, "Deneme Kitap", bolunme),
        dogrulandi=False,
    )


def donustur(
    txt: bytes, js: bytes | None = None, kitap: list[Kitap] | None = None
) -> S.KitapSonucu:
    return S.kitap_donustur(
        raf="tr_k",
        uid="deneme",
        txt=txt,
        json_veri=js if js is not None else sentetik_json(),
        txt_sha256=sha256_bayt(txt),
        kitaplar=kitap if kitap is not None else [kitap_kaydi()],
    )


def birim_haritasi(sonuc: S.KitapSonucu) -> dict[str, Any]:
    return {b.anchor: b for b in sonuc.birimler}


# ---------------------------------------------------------------------------
# ayristirici: sayfa, paragraf, devam


def test_rnk_sayfa_kirilma_ofseti_cumle_ortasinda() -> None:
    a = R.ayristir(sentetik_txt(), "tr_k")
    assert [s.n for s in a.sayfalar] == [4, 5, 6, 7]
    sayfa6 = a.sayfalar[2]
    birim = a.birimler[sayfa6.birim]  # type: ignore[index]
    assert birim.tur == "paragraf"
    assert birim.metin.startswith("Deneme paragrafı 1 başı, cümle ortasında")
    # sayfa 6 cumle ortasinda baslar: ofset devam satirinin ilk harfidir (bosluktan sonra)
    assert birim.metin[sayfa6.ofs :].startswith("ortasında kesildi.")
    assert sayfa6.ofs > 0
    # sayfa 5: paragraf basi (ofset 0)
    assert a.sayfalar[1].ofs == 0
    assert a.birimler[a.sayfalar[1].birim].ilk_satir == 5  # type: ignore[index]


def test_rnk_sayfa_ve_ayirac_birim_uretmez() -> None:
    a = R.ayristir(sentetik_txt(), "tr_k")
    assert all("#" not in b.metin for b in a.birimler)
    assert [n for n, _ in a.yapi] == [12]  # yalniz ayirac satiri (bos satir yok)
    assert a.satir_turleri["ayirac"] == 1
    assert a.satir_turleri["sayfa"] == 4


def test_rnk_baslik_paragraf_hasiye_sayilari() -> None:
    a = R.ayristir(sentetik_txt(), "tr_k")
    sayac = Counter(b.tur for b in a.birimler)
    assert sayac["baslik"] == 4  # kitap, bolum 1, bolum 2, eslesmeyen
    assert sayac["hasiye"] == 3  # tek satirlik + iki paragraflik dipnot
    baslik = [b for b in a.birimler if b.tur == "baslik"]
    assert [b.ozellik["baslik_isareti"] for b in baslik] == ["<", "&", "<", "&"]


def test_rnk_metin_baytlari_nfc_uygulanmaz_ve_ozel_bosluklar_korunur() -> None:
    a = R.ayristir(sentetik_txt(), "tr_k")
    metinler = "\n".join(b.metin for b in a.birimler)
    assert AR_SEDDE in metinler  # fatha + shedde sirasi aynen (NFC bunu degistirirdi)
    assert " nbsp ‌zwnj ­tire" in metinler
    assert not any(c in R.ISARETLER for c in metinler)


def test_rnk_arapca_blok_ar_isareti_yari_acik_aralik() -> None:
    a = R.ayristir(sentetik_txt(), "tr_k")
    ana = next(b for b in a.birimler if b.metin.startswith("Deneme vurgu: Deneme paragrafı 2"))
    ar = [m for m in ana.isaretler if m["t"] == "ar"]
    assert len(ar) == 1 and ar[0]["tur"] == "blok"
    s, e = ar[0]["s"], ar[0]["e"]
    assert ana.metin[s:e] == AR  # [s, e) kod noktasi
    # devam satiri ayni paragrafa eklendi; birlestirme bosluk isareti
    assert ana.metin.endswith(f"{AR} devam metni sonrası")
    assert [m for m in ana.isaretler if m["t"] == "satir"]


def test_rnk_alinti_araligi_ar_alinti_olarak_isaretlenir() -> None:
    a = R.ayristir(sentetik_txt(), "tr_k")
    b = next(b for b in a.birimler if b.metin.startswith("Deneme paragrafı 3"))
    alinti = [m for m in b.isaretler if m["t"] == "ar" and m["tur"] == "alinti"]
    assert len(alinti) == 1
    assert b.metin[alinti[0]["s"] : alinti[0]["e"]] == AR_SEDDE
    # ﹛ ve ﹜ ayri rnk cifti, "|" ayri tek isaret
    ham = [m["c"] for m in b.isaretler if m["t"] == "rnk"]
    assert "﹛" in ham and "|" in ham


# ---------------------------------------------------------------------------
# isaretlerin cikarilip marks'tan geri kurulmasi (bayt bayt gidis-donus)


@pytest.mark.parametrize(
    "satir",
    [
        "   \\Deneme vurgu> sonu",
        "  \\Deneme vurgu> sonu",
        "   ∫Deneme stil> sonu",
        "  ∫Deneme stil> sonu",
        "§Deneme kapanis>",
        "÷Deneme kapanis>",
        "`Deneme etiket:>",
        "%Deneme beyit>",
        "   ½Deneme yarim½ metni",
        "   Deneme ½yarim:> metni",
        ",Deneme ortali satir>",
        "   Deneme ﹛" + AR + "|﹜ metni",
        "   Deneme paragrafi {(*)|Deneme dipnotu.} devam",
        "   Deneme paragrafi {Deneme|Deneme dipnotu.} devam",
        "   Deneme paragrafi {(1) Deneme dipnotu.} devam",
        "   ",  # yalniz bosluk: yapi satiri
        "",  # bos satir
        f"~{AR}|@",
        "   Deneme dengesiz > kapanis ve \\ acik",
        "   Deneme \\ic ∫ice> \\ice>>",
    ],
)
def test_rnk_isaret_gidis_donus_bayt_bayt(satir: str) -> None:
    satirlar = ["#1", "   Deneme paragrafı 0", satir, "   Deneme son"]
    for ayirici, sonda in (("\n", True), ("\n", False), ("\r\n", True)):
        txt = (ayirici.join(satirlar) + (ayirici if sonda else "")).encode()
        a = R.ayristir(txt, "tr")
        assert R.yeniden_kur_ayristirma(a) == txt
        for b in a.birimler:
            assert not any(c in R.ISARETLER for c in b.metin)


def test_rnk_gidis_donus_sentetik_kitap_ve_ar_rafi() -> None:
    for raf in ("tr_k", "ar"):
        txt = sentetik_txt()
        assert R.yeniden_kur_ayristirma(R.ayristir(txt, raf)) == txt


def test_rnk_gidis_donus_isaretler_marks_icinden() -> None:
    """Yeniden kurma yalniz metin + marks + segmentler + yapi ile calisir (ayristiriciya bakmaz)."""
    txt = sentetik_txt()
    a = R.ayristir(txt, "tr_k")
    birimler = [
        {"text": b.metin, "marks": json.loads(json.dumps(b.isaretler)), "segmentler": b.segmentler}
        for b in a.birimler
    ]
    kurulan = R.yeniden_kur(
        birimler=birimler,
        sayfalar=[(s.n, s.satir) for s in a.sayfalar],
        yapi=a.yapi,
        satir_sayisi=a.satir_sayisi,
        bom=a.bom,
        cr_satir=a.cr_satir,
        cr_son=a.cr_son,
        son_lf=a.son_lf,
    )
    assert kurulan == txt
    # bir isaret silinirse yeniden kurma tutmaz
    birimler[2]["marks"] = [m for m in birimler[2]["marks"] if m.get("t") != "rnk"]  # type: ignore[union-attr]
    assert (
        R.yeniden_kur(
            birimler=birimler,
            sayfalar=[(s.n, s.satir) for s in a.sayfalar],
            yapi=a.yapi,
            satir_sayisi=a.satir_sayisi,
            bom=a.bom,
            cr_satir=a.cr_satir,
            cr_son=a.cr_son,
            son_lf=a.son_lf,
        )
        != txt
    )


# ---------------------------------------------------------------------------
# haşiye


def test_rnk_hasiye_ayri_birim_ve_ek_noktasi() -> None:
    sonuc = donustur(sentetik_txt())
    ana = next(b for b in sonuc.birimler if b.text.startswith("Deneme vurgu: Deneme paragrafı 2"))
    isaret = [m for m in ana.attrs["marks"] if m["t"] == "hasiye"]  # type: ignore[union-attr]
    assert len(isaret) == 1
    s = isaret[0]["s"]
    assert ana.text[:s].endswith("Deneme paragrafı 2 ")  # ek noktasi dipnottan once
    assert ana.text[s:].startswith(" devam.")
    hedef = birim_haritasi(sonuc)[isaret[0]["a"]]
    assert hedef.attrs["kind"] == "hasiye"
    assert hedef.text == "Deneme dipnotu 1."
    assert hedef.attrs["etiket_bicimi"] == "(e)|"
    assert ".hasiye-1:p1" in isaret[0]["a"] or ":hasiye-1:p1" in isaret[0]["a"]


def test_rnk_hasiye_cok_satirli_ic_paragraflar() -> None:
    sonuc = donustur(sentetik_txt())
    harita = birim_haritasi(sonuc)
    capalar = sorted(c for c, b in harita.items() if b.attrs["kind"] == "hasiye")
    # bolum 2: hasiye-1 (iki paragraf); bolum 1: hasiye-1 (tek paragraf)
    assert any(c.endswith(":hasiye-1:p2") for c in capalar)
    iki = next(c for c in capalar if c.endswith(":hasiye-1:p2"))
    assert harita[iki].text == "Deneme dipnotu 2 satır iki."
    assert harita[iki.replace(":p2", ":p1")].text == "Deneme dipnotu 2 satır bir"


def test_rnk_hasiye_govdesi_sonraki_satirda_baslarsa_ayni_birim_surer() -> None:
    txt = sentetik_txt(["   Deneme paragrafı 1", "{(*)|", "  Deneme dipnotu satırı 2.}"])
    a = R.ayristir(txt, "tr_k")
    assert [b.tur for b in a.birimler] == ["paragraf", "hasiye"]
    assert a.birimler[1].metin == "Deneme dipnotu satırı 2."
    assert R.yeniden_kur_ayristirma(a) == txt


# ---------------------------------------------------------------------------
# ar rafi


def test_rnk_ar_rafinda_girintisiz_satir_paragraftir() -> None:
    satirlar = [
        "#1",
        f"Deneme {AR}.",
        f"Deneme {AR}",
        "#2",
        f"devam {AR}",
        "Deneme sonu.",
        "#3",
        "yeni satır",
    ]
    txt = sentetik_txt(satirlar)
    a = R.ayristir(txt, "ar")
    assert [b.metin for b in a.birimler] == [
        f"Deneme {AR}.",
        f"Deneme {AR} devam {AR}",  # sayfa sonrasi cumle bitmemis: devam
        "Deneme sonu.",
        "yeni satır",  # sayfa sonrasi ama onceki cumle bitmis: yeni paragraf
    ]
    assert R.yeniden_kur_ayristirma(a) == txt
    # sayfa 2 cumle ortasinda: ofset > 0
    sayfa2 = a.sayfalar[1]
    assert sayfa2.ofs > 0


def test_rnk_ar_olmayan_rafta_girintisiz_satir_devamdir() -> None:
    txt = sentetik_txt(["   Deneme paragrafı 1", "devam satırı", "   Deneme paragrafı 2"])
    a = R.ayristir(txt, "tr")
    assert [b.metin for b in a.birimler] == [
        "Deneme paragrafı 1 devam satırı",
        "Deneme paragrafı 2",
    ]


# ---------------------------------------------------------------------------
# BOM ve CR


def test_rnk_bom_ve_cr_metne_girmez_dosya_duzeyi_bilgidir() -> None:
    duz = sentetik_txt()
    crlf = "﻿".encode() + duz.replace(b"\n", b"\r\n")
    a_duz = R.ayristir(duz, "tr_k")
    a_crlf = R.ayristir(crlf, "tr_k")
    assert a_crlf.bom and not a_duz.bom
    assert a_crlf.cr_satir == a_crlf.satir_sayisi and a_crlf.cr_son
    assert a_duz.cr_satir == 0
    assert [b.metin for b in a_crlf.birimler] == [b.metin for b in a_duz.birimler]
    assert all("﻿" not in b.metin and "\r" not in b.metin for b in a_crlf.birimler)
    assert R.yeniden_kur_ayristirma(a_crlf) == crlf


def test_rnk_son_satirda_lf_olmayan_crlf_dosya() -> None:
    txt = b"#1\r\n   Deneme\r\n   Deneme son"  # son satir CR'siz ve LF'siz
    a = R.ayristir(txt, "tr")
    assert not a.son_lf and not a.cr_son and a.cr_satir == 2
    assert R.yeniden_kur_ayristirma(a) == txt


def test_rnk_karisik_cr_yeniden_kurulamaz() -> None:
    txt = b"#1\r\n   Deneme\n   Deneme son\r\n   Daha\n"
    a = R.ayristir(txt, "tr")
    assert R.yeniden_kur_ayristirma(a) is None  # tum ya da hic: karisik CR G-BUT'u kaldirir


def test_rnk_utf8_olmayan_bayt_girdi_hatasi() -> None:
    with pytest.raises(GirdiHatasi):
        R.ayristir(b"\xff\xfe#1\n", "tr")


# ---------------------------------------------------------------------------
# staged: capa, bolum agaci, baslik duzeyi


def test_rnk_baslik_duzeyi_json_eslesmesi_ve_p1() -> None:
    sonuc = donustur(sentetik_txt())
    harita = birim_haritasi(sonuc)
    b1 = harita["rn:deneme-kitap:deneme-bolum-1:p1"]
    assert b1.text == "Deneme Bölüm 1"
    assert b1.attrs["baslik_duzeyi"] == 1
    assert b1.attrs["json_dugum"] == {"sira": 1, "pageNo": 4}
    assert harita["rn:deneme-kitap:p1"].attrs["baslik_duzeyi"] == 0  # kok dugum
    # bolum 2 ve eslesmeyen baslik duzeysiz
    assert harita["rn:deneme-kitap:deneme-bolum-2:p1"].attrs["baslik_duzeyi"] == 1
    duzeysiz = [b for b in sonuc.birimler if b.attrs.get("baslik_duzeysiz")]
    assert [b.text for b in duzeysiz] == ["Deneme Eşleşmeyen"]
    assert duzeysiz[0].anchor == "rn:deneme-kitap:deneme-bolum-2:p2"
    assert sonuc.uyarilar["baslik_eslesmedi"] == 1


def test_rnk_paragraf_numaralari_bolum_basina_okuma_sirasinda() -> None:
    sonuc = donustur(sentetik_txt())
    bolum1 = sorted(
        (b.attrs["p"], b.text[:20])
        for b in sonuc.birimler
        if b.attrs["kind"] != "hasiye" and b.attrs["bolum_yolu"] == ["deneme-bolum-1"]
    )
    assert [p for p, _ in bolum1] == [1, 2, 3, 4]
    assert bolum1[1][1].startswith("Deneme paragrafı 1")


def test_rnk_capalar_tekil_ve_dogrulanir() -> None:
    from mutalaa_pipeline.anchor import parse

    sonuc = donustur(sentetik_txt())
    capalar = [b.anchor for b in sonuc.birimler]
    assert len(capalar) == len(set(capalar))
    for c in capalar:
        parse(c)


def test_rnk_kardes_bolum_adi_cakismasinda_ek() -> None:
    js = sentetik_json()
    veri = json.loads(js)
    veri["contents"]["children"].append(
        {"key": "c-7", "title": "Deneme Bölüm 1", "textInBook": "", "pageNo": 7, "children": []}
    )
    dugumler = S.json_oku(json.dumps(veri).encode()).dugumler
    yollar = S.bolum_yollari(dugumler)
    assert yollar[1] == ("deneme-bolum-1",) and yollar[3] == ("deneme-bolum-1-2",)


def test_rnk_json_meta_dosyayla_uyusmazsa_girdi_hatasi() -> None:
    veri = json.loads(sentetik_json())
    veri["meta_data"]["uid"] = "baska"
    with pytest.raises(GirdiHatasi):
        donustur(sentetik_txt(), json.dumps(veri).encode())


def test_rnk_bolunme_sayfaya_gore_slug_ve_sayfalar_dosya_duzeyinde() -> None:
    bol = Bolunme(7, (BolunmeParcasi("deneme-a", 4), BolunmeParcasi("deneme-b", 6)))
    kitap = [kitap_kaydi("deneme-a", bolunme=bol), kitap_kaydi("deneme-b", bolunme=bol)]
    sonuc = donustur(sentetik_txt(), kitap=kitap)
    slug = Counter(str(b.attrs["slug"]) for b in sonuc.birimler)
    assert set(slug) == {"deneme-a", "deneme-b"}
    for b in sonuc.birimler:
        sayfa = b.attrs["sayfa"]
        beklenen = "deneme-a" if sayfa < 6 else "deneme-b"  # type: ignore[operator]
        assert b.attrs["slug"] == beklenen
        assert b.anchor.startswith(f"rn:{beklenen}:")
    # sayfa listesi dosya duzeyindedir: her sayfa bir kez, capasi kendi parcasinda
    assert [s["n"] for s in sonuc.sayfalar] == [4, 5, 6, 7]
    assert all(s["dosya"] == "tr_k/deneme" for s in sonuc.sayfalar)
    assert sonuc.sayfalar[2]["capa"].startswith("rn:deneme-a:")  # type: ignore[union-attr]
    assert sonuc.kitap["slug"] == ["deneme-a", "deneme-b"]


def test_rnk_birim_provenance_segmentler_ve_attrs() -> None:
    sonuc = donustur(sentetik_txt())
    b = birim_haritasi(sonuc)["rn:deneme-kitap:deneme-bolum-1:p2"]
    assert b.provenance["kaynak"] == "rnk"
    assert b.provenance["file"] == "tr_k/deneme.txt"
    assert b.attrs["dil"] == "tr" and b.attrs["yon"] == "ltr"
    konum: Any = b.provenance["konum"]
    assert konum["satir"] == [5, 7]  # sayfa kirilmasi satirlar arasinda
    assert all(len(s) == 4 for s in konum["segmentler"])


def test_rnk_idempotent_ayni_baytlar_ayni_cikti() -> None:
    a = donustur(sentetik_txt())
    b = donustur(sentetik_txt())

    def ozet(s: S.KitapSonucu) -> str:
        return json.dumps(
            [(u.anchor, u.text, u.attrs, u.provenance) for u in s.birimler]
            + [s.sayfalar, s.yapi, s.kitap],
            sort_keys=True,
        )

    assert ozet(a) == ozet(b)


# ---------------------------------------------------------------------------
# kilit ve gercek kilit dosyasi (yalniz sayilar)


def test_rnk_kilit_dosyasi_85_kitap_tabloyla_uyumlu() -> None:
    kilit = kilit_yukle()
    assert len(kilit.kitaplar) == 85
    kilit_tablo_uyumu(kilit)
    assert len(rnk_dosyalari()) == 85
    assert len(kitaplar()) == 87
    sunuhat = rnk_dosyalari()[("tr_k", "sunuhat")]
    assert {k.slug for k in sunuhat} == {"sunuhat", "tuluat", "isarat"}
    assert kilit_ozeti(kilit) == kilit_ozeti(kilit_yukle())


def test_rnk_kilit_toplamlari_olcumle_ayni() -> None:
    kilit = kilit_yukle()
    k = list(kilit.kitaplar.values())
    assert sum(x.sayi("sayfa_sayisi") for x in k) == 26009
    assert sum(1 for x in k if x.mantiksal("bom")) == 19
    assert sum(1 for x in k if x.sayi("cr_satir") > 0) == 7
    assert sum(x.sayi("baslik_satiri") for x in k) == 8552
    karakter: Counter[str] = Counter()
    isaret: Counter[str] = Counter()
    for x in k:
        karakter.update(x.sayilar("karakterler"))
        isaret.update(x.sayilar("isaretler"))
    assert karakter["U+200F"] == 20 and karakter["U+00AD"] == 25
    assert karakter["U+EEE3"] == karakter["U+EEE4"] == karakter["U+EEE5"] == 1
    assert isaret["~"] == isaret["@"] == 15804
    assert all(int(kod[2:], 16) in R.S12_KUMESI for kod in karakter)  # kilit disi karakter yok
    mesnevi = kilit.kitaplar["ar/ar_mesnevi"]
    assert [kod for _, kod in mesnevi.ozel_kullanim()] == ["U+EEE3", "U+EEE4", "U+EEE5"]


def test_rnk_kilit_dosyalari_katalog_ve_171_dosya() -> None:
    dosyalar = kilit_dosyalari(kilit_yukle())
    assert len(dosyalar) == 171  # 85 x (txt + json) + shelves.json
    assert any(d.ad == "shelves.json" for d in dosyalar)


def test_rnk_tablo_hepsi_rnk_kaynakli_ve_diyanet_karsiligi() -> None:
    harita = kitap_haritasi()
    assert all(k.metin_kaynagi == "rnk" for k in harita.values())
    assert Counter(k.diyanet_karsiligi for k in harita.values()) == {
        "diyanet": 25,
        "derleme": 34,
        "rnk": 28,
    }


# ---------------------------------------------------------------------------
# QA: G-KAY, G-BUT, G-NOR (sentetik)


def kilit_kur(txt: bytes, js: bytes, katalog: bytes = b"{}") -> RnkKilidi:
    import hashlib

    veri = R_istatistik(txt, js)
    assert veri["md5_txt"] == hashlib.md5(txt, usedforsecurity=False).hexdigest()
    return RnkKilidi(
        "2026-11-12",
        len(katalog),
        sha256_bayt(katalog),
        {"tr_k/deneme": KitapKilidi("tr_k/deneme", veri)},
    )


def R_istatistik(txt: bytes, js: bytes) -> dict[str, object]:
    from mutalaa_pipeline.ingest.risale_rnk_kilit import kitap_istatistigi

    return kitap_istatistigi(txt, js)


def girdi_kur(
    txt: bytes | None = None,
    *,
    kilit_txt: bytes | None = None,
    ozet: str | None = None,
    degistir: Any = None,
) -> Q.RnkGirdisi:
    txt = txt if txt is not None else sentetik_txt()
    js = sentetik_json()
    sonuc = donustur(txt, js)
    kilit = kilit_kur(kilit_txt if kilit_txt is not None else txt, js)
    satirlar = [
        {"anchor": u.anchor, "text": u.text, "attrs": u.attrs, "provenance": u.provenance}
        for u in sonuc.birimler
    ]
    satirlar = json.loads(json.dumps(satirlar))
    sayfalar = json.loads(json.dumps(sonuc.sayfalar))
    yapi = json.loads(json.dumps(sonuc.yapi))
    kitap_satirlari = json.loads(json.dumps([sonuc.kitap]))
    if degistir is not None:
        degistir(satirlar, sayfalar, yapi, kitap_satirlari)
    return Q.RnkGirdisi(
        kayit=Kaynak(
            slug=KAYNAK,
            tur=SourceKind.RISALE,
            baslik="Deneme",
            atif_metni="Deneme atif",
            surum="deneme-surum",
            kaynak_url="https://example.test/x",
        ),
        kilit=kilit,
        kilit_ozeti_manifest=ozet if ozet is not None else kilit_ozeti(kilit),
        ham={"tr_k/deneme.txt": txt, "tr_k/deneme.json": js},
        birimler=satirlar,
        sayfalar=sayfalar,
        yapi=yapi,
        kitaplar=kitap_satirlari,
        tablo=(kitap_kaydi(),),
        depo_kok=depo_koku(),
    )


def test_rnk_qa_sentetik_ingest_kapilari_gecer_g_cap_anchor_ister() -> None:
    """Ingest ciktisiyla G-KAY, G-BUT, G-NOR gecer; G-CAP anchor ciktisi olmadan kalir."""
    g = girdi_kur()
    for ad in ("G-KAY", "G-BUT", "G-NOR"):
        sonuc = Q.KAPI_ISLEVLERI[ad](g)
        assert sonuc.gecti, (ad, sonuc.bulgular)
    but = Q.g_but(g)
    assert but.sayilar["yeniden_kurulan"] == 1 and but.sayilar["kapsamsiz"] == 0
    cap = Q.g_cap(g)
    assert not cap.gecti and any("anchor ciktisi yok" in b for b in cap.bulgular)
    assert tuple(Q.KAPI_ISLEVLERI) == Q.RNK_KAPILARI == ("G-KAY", "G-BUT", "G-CAP", "G-NOR")


def test_rnk_g_kay_eski_kilit_ozeti_kalir() -> None:
    sonuc = Q.g_kay(girdi_kur(ozet="0" * 64))
    assert not sonuc.gecti and any("eski bir kilitle" in b for b in sonuc.bulgular)
    g = girdi_kur()
    g.kilit_ozeti_manifest = None
    assert not Q.g_kay(g).gecti


def test_rnk_g_but_kilit_disi_karakter_kapiyi_kaldirir() -> None:
    txt = sentetik_txt()
    degisik = txt.replace("Deneme paragrafı 5".encode(), "Deneme paragrafı 5".encode())
    # kilit eski dosyaya gore: ham dosya degismis, ozet tutmaz
    sonuc = Q.g_but(girdi_kur(degisik, kilit_txt=txt))
    assert not sonuc.gecti
    assert any("ham dosya ozeti kilitle tutmuyor" in b for b in sonuc.bulgular)


def test_rnk_g_but_kilitte_s12_disi_karakter_bulgusu() -> None:
    """Ham dosya kilitle ayni ama kilit S12 disi bir karakter listeliyorsa kapi kalir."""
    txt = sentetik_txt().replace("Deneme paragrafı 5".encode(), "Deneme paragrafı 5".encode())
    g = girdi_kur(txt)
    sonuc = Q.g_but(g)
    assert not sonuc.gecti
    assert any("S12 kumesi disinda" in b for b in sonuc.bulgular)


def test_rnk_g_but_sayi_farki_kapiyi_kaldirir() -> None:
    txt = sentetik_txt()
    g = girdi_kur(txt)
    kitap = g.kilit.kitaplar["tr_k/deneme"]
    kitap.veri["isaretler"]["\\"] += 1  # type: ignore[index]
    sonuc = Q.g_but(g)
    assert not sonuc.gecti
    assert any("isaretler[\\]" in b for b in sonuc.bulgular)


def test_rnk_g_but_yeniden_kurma_bozulunca_kalir() -> None:
    def boz(birimler: list[Any], *_: Any) -> None:
        birimler[3]["text"] = birimler[3]["text"] + "x"  # metin kaynakla ayni degil

    sonuc = Q.g_but(girdi_kur(degistir=boz))
    assert not sonuc.gecti
    assert any("yeniden kurma" in b or "segment kapsami" in b for b in sonuc.bulgular)


def test_rnk_g_but_isaret_karakteri_metinde_kalirsa_kalir() -> None:
    def boz(birimler: list[Any], *_: Any) -> None:
        birimler[3]["text"] = "\\" + birimler[3]["text"]

    sonuc = Q.g_but(girdi_kur(degistir=boz))
    assert any("isaret karakteri" in b for b in sonuc.bulgular)


def test_rnk_g_but_sayfa_sirasi_bozulunca_kalir() -> None:
    def boz(_b: list[Any], sayfalar: list[Any], *_: Any) -> None:
        sayfalar[2]["n"] = 9

    sonuc = Q.g_but(girdi_kur(degistir=boz))
    assert not sonuc.gecti
    assert any("sayfa ve baslik sayilari" in b for b in sonuc.bulgular)


def test_rnk_g_but_baslik_birimi_sayisi_satir_sayisiyla_ayni() -> None:
    g = girdi_kur()
    kitap = g.kilit.kitaplar["tr_k/deneme"]
    assert kitap.sayi("baslik_satiri") == 4
    assert Q.g_but(g).gecti


def test_rnk_g_nor_osmanlica_arapca_yalniz_ar_norm() -> None:
    from mutalaa_pipeline.normalize import normalize_ar

    def ota(birimler: list[Any], *_: Any) -> None:
        for b in birimler:
            b["attrs"]["dil"] = "ota"
            b["ar_norm"] = normalize_ar(b["text"])

    g = girdi_kur(degistir=ota)
    sonuc = Q.g_nor(g)
    assert sonuc.gecti, sonuc.bulgular
    assert sonuc.sayilar["ar_norm_denetlenen"] > 0

    def tr_dolu(birimler: list[Any], *_: Any) -> None:
        ota(birimler)
        birimler[3]["tr_narrow"] = "x"

    assert not Q.g_nor(girdi_kur(degistir=tr_dolu)).gecti

    def yanlis(birimler: list[Any], *_: Any) -> None:
        ota(birimler)
        birimler[3]["ar_norm"] = "yanlis"

    assert any("ar_norm" in b for b in Q.g_nor(girdi_kur(degistir=yanlis)).bulgular)


# ---------------------------------------------------------------------------
# uctan uca: sentetik gelen klasoru -> run_ingest -> staged -> kapilar


def _gelen_kur(tmp_path: Path, txt: bytes, js: bytes) -> RnkKilidi:
    import hashlib

    tarih = "2026-11-12"
    kok = tmp_path / "data" / "gelen" / "risale-baski-rnk" / tarih
    (kok / "tr_k").mkdir(parents=True)
    (kok / "tr_k" / "deneme.txt").write_bytes(txt)
    (kok / "tr_k" / "deneme.json").write_bytes(js)
    katalog = {
        "shelves": [
            {
                "id": "tr_k",
                "books": [
                    {
                        "uid": "deneme",
                        "hash_txt": hashlib.md5(txt, usedforsecurity=False).hexdigest(),
                        "hash_json": hashlib.md5(js, usedforsecurity=False).hexdigest(),
                    }
                ],
            }
        ]
    }
    (kok / "shelves.json").write_bytes(json.dumps(katalog).encode())
    return kilit_uret(gelen=kok.parent, tarih=tarih, dosyalar=[("tr_k", "deneme")])


def test_rnk_uctan_uca_ingest_idempotent_ve_kapilar(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    txt, js = sentetik_txt(), sentetik_json()
    kilit = _gelen_kur(tmp_path, txt, js)
    kok = depo_kur(
        tmp_path,
        KAYNAK,
        tur="risale",
        surum="deneme-surum",
        kaynak_url="https://example.test/shelves.json",
    )
    tablo = (kitap_kaydi(),)

    def kos(**kw: Any) -> Any:
        ctx = ctx_kur(tmp_path, kok, kaynaklar=[KAYNAK], temiz_git=True, **kw)
        return ctx, run_ingest(RnkBagdastirici(kilit=kilit, tablo=tablo), ctx)

    ctx1, s1 = kos()
    assert not s1.atlandi and s1.birim_sayisi == len(donustur(txt, js).birimler)
    assert s1.klasor is not None
    ham = ctx1.veri_kok / "raw" / KAYNAK / "2026-11-12" / "tr_k" / "deneme.txt"
    assert ham.read_bytes() == txt  # ham kopya bayt bayt
    for ad in ("units.jsonl", "sayfalar.jsonl", "yapi.jsonl", "kitaplar.jsonl", "manifest.json"):
        assert (s1.klasor / ad).is_file()
    # ikinci kosu: parmak izi ayni (temiz git): atlanir
    _, s2 = kos()
    assert s2.atlandi
    # --force: yeniden uretilir, cikti ayni
    _, s3 = kos(force=True)
    assert not s3.atlandi and s3.klasor is not None
    for ad in ("units.jsonl", "sayfalar.jsonl", "yapi.jsonl", "kitaplar.jsonl"):
        assert (s1.klasor / ad).read_bytes() == (s3.klasor / ad).read_bytes()

    # normalize ve anchor: ikinci kosu atlanir, --force ayni baytlari uretir
    def adim(ad: str, islev: Any, **kw: Any) -> Any:
        ctx = ctx_kur(tmp_path, kok, adim=ad, kaynaklar=[KAYNAK], temiz_git=True, **kw)
        return ctx, islev(ctx)

    _, n1 = adim("normalize", A.run_normalize)
    assert not n1.atlandi and n1.klasor is not None and n1.birim_sayisi == s1.birim_sayisi
    assert adim("normalize", A.run_normalize)[1].atlandi
    _, n2 = adim("normalize", A.run_normalize, force=True)
    assert (n1.klasor / "units.jsonl").read_bytes() == (n2.klasor / "units.jsonl").read_bytes()
    _, a1 = adim("anchor", A.run_anchor)
    assert not a1.atlandi and a1.klasor is not None and a1.birim_sayisi == s1.birim_sayisi
    assert adim("anchor", A.run_anchor)[1].atlandi
    _, a2 = adim("anchor", A.run_anchor, force=True)
    assert (a1.klasor / "units.jsonl").read_bytes() == (a2.klasor / "units.jsonl").read_bytes()
    # zincir yukleyicisi: son anchor -> normalize -> ingest (sentetik kilit yamayla)
    kilit_yolu = tmp_path / "sentetik.lock.json"
    kilit_yolu.write_bytes(kilit_metni(kilit).encode("utf-8"))
    monkeypatch.setattr(kilit_modulu, "KILIT_YOLU", kilit_yolu)
    monkeypatch.setattr(qa_run_modulu, "kitaplar", lambda: tablo)
    ctx_qa = ctx_kur(tmp_path, kok, adim="qa", kaynaklar=[KAYNAK], temiz_git=True)
    y = qa_yukle(ctx_qa)
    assert y.anchor.run_id == a2.run_id and y.normalize.run_id == n2.run_id  # en son calisma
    assert y.ingest.run_id == s3.run_id
    g = y.girdi
    g.depo_kok = depo_koku()  # G-NOR vektorleri gercek depo kokunden
    assert len(g.birimler) == s1.birim_sayisi
    assert set(g.ham) == {"shelves.json", "tr_k/deneme.txt", "tr_k/deneme.json"}
    assert g.onceki is None  # kapilari gecmis onceki anchor calismasi yok
    assert sum(1 for _ in g.anchor()) == s1.birim_sayisi  # type: ignore[misc]
    for ad, sonuc in kapilari_kos(g, kapilari_sec(None)).items():
        assert sonuc.gecti, (ad, sonuc.bulgular)
    assert kapilari_sec(None) == ("G-KAY", "G-BUT", "G-CAP", "G-NOR")
    assert kapilari_sec(["G-CAP", "G-KAY"]) == ("G-KAY", "G-CAP")
    with pytest.raises(GirdiHatasi):
        kapilari_sec(["G-HIZ"])


def test_rnk_ingest_kilitle_tutmayan_dosya_girdi_hatasi(tmp_path: Path) -> None:
    txt, js = sentetik_txt(), sentetik_json()
    kilit = _gelen_kur(tmp_path, txt, js)
    gelen = tmp_path / "data" / "gelen" / "risale-baski-rnk" / "2026-11-12" / "tr_k" / "deneme.txt"
    gelen.write_bytes(txt + b"#99\n")
    kok = depo_kur(tmp_path, KAYNAK, tur="risale")
    ctx = ctx_kur(tmp_path, kok, kaynaklar=[KAYNAK], temiz_git=True)
    with pytest.raises(GirdiHatasi, match="kilitle tutmuyor"):
        run_ingest(RnkBagdastirici(kilit=kilit, tablo=(kitap_kaydi(),)), ctx)
    assert not (tmp_path / "data" / "raw" / KAYNAK).exists()  # raw'a hicbir sey yazilmadi


def test_rnk_kilit_tablo_uyumsuzlugu_girdi_hatasi() -> None:
    kilit = kilit_kur(sentetik_txt(), sentetik_json())
    with pytest.raises(GirdiHatasi):
        kilit_tablo_uyumu(kilit, (kitap_kaydi(uid="baska"),))
