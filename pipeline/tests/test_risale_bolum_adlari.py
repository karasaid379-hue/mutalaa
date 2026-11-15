# ruff: noqa: RUF001
"""Risale bolum adlari (A20.2b; ACIKCA SENTETIK veri): sayili kalip, kalip disi baslik, kardes eki.

Basliklar yalniz yapisal kalip dizgileridir ("Yirmi Besinci Soz", "Deneme Bolum"); Risale metni
yoktur. Bolum adi `anchor.risale.baslik_bolum_adi` ve `ingest.risale_rnk_staged.bolum_agaci` ile
uretilir; cumle, paragraf ve capa testleri `test_risale_rnk.py` ve `test_risale_adimlar.py`'dedir.
"""

import json
from typing import Any

import pytest
from test_risale_rnk import donustur, kitap_kaydi, sentetik_txt

from mutalaa_pipeline.anchor.risale import (
    Bolunme,
    BolunmeParcasi,
    baslik_bolum_adi,
    bolum_kalibi,
    kitaplar,
    lahika_mi,
    sira_sayisi,
)
from mutalaa_pipeline.ingest import risale_rnk_staged as S


@pytest.mark.parametrize(
    ("ad", "beklenen"),
    [
        ("birinci", 1),
        ("dokuzuncu", 9),
        ("onuncu", 10),
        ("on-birinci", 11),
        ("onbirinci", 11),
        ("yirmi-besinci", 25),
        ("yirmibesinci", 25),
        ("otuz-ucuncu", 33),
        ("doksan-dokuzuncu", 99),
        ("yirminci", 20),
        ("yirmi", None),  # sayi sozcugu, sira degil
        ("besinci-yirmi", None),
        ("yuzuncu", None),
        ("", None),
    ],
)
def test_sira_sayisi(ad: str, beklenen: int | None) -> None:
    assert sira_sayisi(ad) == beklenen


@pytest.mark.parametrize(
    ("baslik", "beklenen"),
    [
        ("Birinci Söz", "soz-1"),
        ("Yirmi Beşinci Söz", "soz-25"),
        ("Yirmibeşinci SÖZ", "soz-25"),
        ("Otuz Üçüncü Mektup", "mektup-33"),
        ("Altıncı Mektub", "mektup-6"),
        ("Onuncu Lem'a", "lema-10"),
        ("On Birinci Şuâ", "sua-11"),
        ("Dokuzuncu Makam", "makam-9"),
        ("İkinci Hakikat", "hakikat-2"),
        ("Üçüncü Nükte", "nukte-3"),
        ("Dördüncü Mesele", "mesele-4"),
        ("Beşinci İşaret", "isaret-5"),
        ("1. Söz", "soz-1"),
        ("Söz 12", "soz-12"),
        ("Mukaddime", "mukaddime"),
        ("Hâtime", "hatime"),
        ("ZEYL", "zeyl"),
    ],
)
def test_baslik_sayili_kalibi_taniyor(baslik: str, beklenen: str) -> None:
    ad = baslik_bolum_adi(baslik)
    assert ad == beklenen
    assert bolum_kalibi(ad) is not None


@pytest.mark.parametrize(
    "baslik",
    [
        "Deneme Bölüm 1",
        "Söz",  # yalniz tur sozcugu
        "Birinci",  # tur yok
        "Birinci Kelime",  # kalip listesinde olmayan tur
        "Birinci Söz'ün Zeyli",  # ardindan baska sozcuk
        "01. Söz",  # sifirla baslayan sayi kanonik degil
        "Yüzüncü Söz",  # 100 ve uzeri desteklenmez
        "İkinci Hâşiye",  # hasiye basliktan uretilmez
        "Mukaddime-i Deneme",
        "ابتثجح",  # Arap harfli baslik slug'a cevrilemez
        "",
    ],
)
def test_baslik_kalip_disi_none(baslik: str) -> None:
    assert baslik_bolum_adi(baslik) is None


# ---------------------------------------------------------------------------
# bolum agaci


def _dugum(
    baslik: str, sayfa: int = 4, cocuklar: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    return {
        "key": f"{baslik}-{sayfa}",
        "title": baslik,
        "textInBook": "",
        "pageNo": sayfa,
        "children": cocuklar or [],
    }


def _json(kok: dict[str, Any], son: int = 20) -> bytes:
    veri = {
        "meta_data": {
            "uid": "deneme",
            "shelf_id": "tr_k",
            "name": "Deneme",
            "language": "tr",
            "first_page": 4,
            "last_page": son,
        },
        "contents": kok,
    }
    return json.dumps(veri, ensure_ascii=False).encode("utf-8")


def _agac(cocuklar: list[dict[str, Any]], **kw: Any) -> S.BolumAgaci:
    bilgi = S.json_oku(_json(_dugum("Deneme Kitap", 4, cocuklar)))
    return S.bolum_agaci(bilgi.dugumler, **kw)


def test_bolum_agaci_kalip_ve_kalip_disi_baslik() -> None:
    agac = _agac(
        [
            _dugum("Yirmi Beşinci Söz", 4, [_dugum("Birinci Nükte"), _dugum("Deneme Bölüm")]),
            _dugum("Hâtime", 9),
        ]
    )
    assert agac.yollar == (
        (),
        ("soz-25",),
        ("soz-25", "nukte-1"),
        ("soz-25", "deneme-bolum"),
        ("hatime",),
    )
    assert agac.istatistik["kalip_soz"] == 1
    assert agac.istatistik["kalip_nukte"] == 1
    assert agac.istatistik["kalip_hatime"] == 1
    assert agac.istatistik["baslik_turetilen"] == 1
    assert agac.istatistik["kardes_eki"] == 0


def test_bolum_agaci_kardes_cakismasinda_ek() -> None:
    agac = _agac(
        [
            _dugum("Birinci Söz"),
            _dugum("Birinci Söz"),
            _dugum("Birinci Söz"),
            _dugum("Deneme Bölüm"),
            _dugum("Deneme Bölüm"),
        ]
    )
    adlar = [y[0] for y in agac.yollar[1:]]
    assert adlar == ["soz-1", "soz-1-2", "soz-1-3", "deneme-bolum", "deneme-bolum-2"]
    assert agac.istatistik["kardes_eki"] == 3
    # ek bir kalip adi degildir: `soz-1-2` kalip sayilmaz
    assert bolum_kalibi("soz-1-2") is None


def test_bolum_agaci_tur_sozcugu_ve_hasiye_kalip_adiyla_karismaz() -> None:
    """Basligi yalniz `Soz` olan bolum `soz-2` (kalip) adini almaz; oneklenir."""
    agac = _agac([_dugum("Söz"), _dugum("Söz"), _dugum("İkinci Söz"), _dugum("Hâşiye")])
    adlar = [y[0] for y in agac.yollar[1:]]
    assert adlar == ["bolum-soz", "bolum-soz-2", "soz-2", "bolum-hasiye"]
    assert agac.istatistik["bolum_onekli"] == 3
    # kalip adlari yalniz kalip taniyan basliktan gelir
    assert [bolum_kalibi(a) is not None for a in adlar] == [False, False, True, False]


def test_bolum_agaci_basliksiz_baslik_bolum_n_olur() -> None:
    """Slug turetilemeyen baslik `bolum-{n}` (n kardes sirasi, 1'den); `bolum` yalin olmaz."""
    agac = _agac([_dugum("???"), _dugum("ابتث"), _dugum("Soz 03"), _dugum("ابتث")])
    adlar = [y[0] for y in agac.yollar[1:]]
    assert adlar == ["bolum-1", "bolum-2", "bolum-soz-03", "bolum-3"]
    assert agac.istatistik["bolum_n"] == 3
    assert agac.istatistik["bolum_onekli"] == 1 and agac.istatistik["kardes_eki"] == 0


def test_bolum_agaci_bolum_n_her_ustun_altinda_birden_baslar() -> None:
    agac = _agac(
        [
            _dugum("ابتث", 4, [_dugum("ابتث"), _dugum("ابتث")]),
            _dugum("ابتث", 6, [_dugum("ابتث")]),
        ]
    )
    # dugumler: 0 kok, 1 bolum-1, 2 bolum-1/bolum-1, 3 bolum-1/bolum-2, 4 bolum-2, 5 bolum-2/bolum-1
    assert agac.yollar[1:] == (
        ("bolum-1",),
        ("bolum-1", "bolum-1"),
        ("bolum-1", "bolum-2"),
        ("bolum-2",),
        ("bolum-2", "bolum-1"),
    )


def test_bolum_agaci_rakam_basligi_ile_bolum_n_cakismasinda_ek() -> None:
    agac = _agac([_dugum("???"), _dugum("1")])  # "1" -> bolum-1 (onekli), ilk basliksiz de bolum-1
    assert [y[0] for y in agac.yollar[1:]] == ["bolum-1", "bolum-1-2"]


def test_bolum_agaci_baslik_en_cok_64_karakter_40ta_kesilmez() -> None:
    orta = " ".join(["deneme"] * 8)  # 8 * 6 + 7 = 55 karakter: kesilmez
    uzun = " ".join(["deneme"] * 12)  # 12 * 6 + 11 = 83 karakter
    agac = _agac([_dugum(orta), _dugum(uzun)])
    ad1, ad2 = agac.yollar[1][0], agac.yollar[2][0]
    assert ad1 == "-".join(["deneme"] * 8) and len(ad1) == 55
    assert len(ad2) <= 64 and not ad2.endswith("-")
    assert len(ad2) > 40  # eski 40 sinirinda kesilmiyor
    assert ad2 == "-".join(["deneme"] * 9)  # son tire sinirinda (9 * 6 + 8 = 62)
    assert agac.istatistik["kesildi_64"] == 1 and "kesildi_40" not in agac.istatistik


def test_bolum_agaci_64te_cakisma_eki_de_64_icinde_kalir() -> None:
    uzun = " ".join(["deneme"] * 12)
    agac = _agac([_dugum(uzun), _dugum(uzun), _dugum(uzun)])
    adlar = [y[0] for y in agac.yollar[1:]]
    assert len(set(adlar)) == 3 and all(len(a) <= 64 for a in adlar)
    assert adlar[1].endswith("-2") and adlar[2].endswith("-3")
    # taban 64 karakter dolu olsa da ek 64 icinde kalir
    tam = "a" * 64
    agac = _agac([_dugum(tam), _dugum(tam)])
    assert [len(y[0]) for y in agac.yollar[1:]] == [64, 64]
    assert agac.yollar[2][0].endswith("-2") and agac.yollar[1][0] != agac.yollar[2][0]


def test_bolum_agaci_ayrilmis_p_ve_s_adlari_onek_alir() -> None:
    agac = _agac([_dugum("p12"), _dugum("S3")])
    assert [y[0] for y in agac.yollar[1:]] == ["bolum-p12", "bolum-s3"]


def test_lahika_kitap_tanima() -> None:
    for slug in (
        "barla-lahikasi",
        "kastamonu-lahikasi",
        "emirdag-lahikasi-1",
        "emirdag-lahikasi-2",
        "barla-lahikasi-osmanlica",
        "emirdag-lahikasi-2-osmanlica",
        "kastamonu-lahikasi-arapca",
    ):
        assert lahika_mi(slug), slug
    for slug in ("sozler", "mektubat-osmanlica", "lahika", "lahikasi-sozler"):
        assert not lahika_mi(slug), slug


def test_lahika_tablo_kitaplari_tam_yedi() -> None:
    """Lahika kitaplari tablodan tanir: 4 Turkce + 3 Osmanlica (uydurma yok)."""
    bulunan = sorted(k.slug for k in kitaplar() if lahika_mi(k.slug))
    assert bulunan == [
        "barla-lahikasi",
        "barla-lahikasi-osmanlica",
        "emirdag-lahikasi-1",
        "emirdag-lahikasi-1-osmanlica",
        "emirdag-lahikasi-2",
        "emirdag-lahikasi-2-osmanlica",
        "kastamonu-lahikasi",
        "kastamonu-lahikasi-osmanlica",
    ]


def _lahika_agac(cocuklar: list[dict[str, Any]], slug: str = "deneme-lahikasi") -> S.BolumAgaci:
    bilgi = S.json_oku(_json(_dugum("Deneme Kitap", 4, cocuklar)))
    return S.bolum_agaci(bilgi.dugumler, parca_adi=lambda _sayfa: slug)


def test_lahika_kalip_disi_bolum_parca_n_olur_baslik_slugi_kullanilmaz() -> None:
    agac = _lahika_agac(
        [
            _dugum("Deneme Mektup A", 4, [_dugum("Deneme Alt"), _dugum("Başka Başlık")]),
            _dugum("Deneme Mektup B", 5),
            _dugum("Birinci Nükte", 6),  # sayili kalip korunur
            _dugum("Mukaddime", 6),
            _dugum("ابتث", 7),  # slug turetilemeyen de parca
        ]
    )
    assert agac.yollar[1:] == (
        ("parca-1",),
        ("parca-1", "parca-1"),
        ("parca-1", "parca-2"),
        ("parca-2",),
        ("nukte-1",),
        ("mukaddime",),
        ("parca-3",),
    )
    assert agac.istatistik["parca"] == 5
    assert "baslik_turetilen" not in agac.istatistik and "bolum_n" not in agac.istatistik
    assert agac.basliklar[1] == ("Deneme Mektup A",)  # gorunen baslik zinciri korunur


def test_lahika_kaynakta_numara_varsa_o_numara() -> None:
    agac = _lahika_agac([_dugum("12."), _dugum("Deneme"), _dugum("7")])
    assert [y[0] for y in agac.yollar[1:]] == ["parca-12", "parca-2", "parca-7"]


def test_lahika_numara_cakismasinda_ek() -> None:
    agac = _lahika_agac([_dugum("2"), _dugum("Deneme")])  # kaynak 2 ve kardes sirasi 2
    assert [y[0] for y in agac.yollar[1:]] == ["parca-2", "parca-2-2"]


def test_lahika_disi_kitapta_parca_n_uretilmez() -> None:
    bilgi = S.json_oku(_json(_dugum("Deneme Kitap", 4, [_dugum("Deneme Bölüm")])))
    agac = S.bolum_agaci(bilgi.dugumler, parca_adi=lambda _s: "deneme-kitap")
    assert agac.yollar[1] == ("deneme-bolum",) and "parca" not in agac.istatistik


def test_lahika_ilk_duzey_kitap_slugiyla_ayniysa_yine_daraltilir() -> None:
    agac = _lahika_agac([_dugum("Deneme Lahikası", 4, [_dugum("Deneme")])])
    assert agac.yollar[1:] == ((), ("parca-1",))
    assert agac.istatistik["daraltildi"] == 1


def test_bolum_agaci_baslik_zinciri_kok_ve_daraltilan_yok() -> None:
    agac = _agac([_dugum("Birinci Söz", 4, [_dugum("Birinci Nükte")])])
    assert agac.basliklar[0] == ()
    assert agac.basliklar[2] == ("Birinci Söz", "Birinci Nükte")
    assert len(agac.basliklar[2]) == len(agac.yollar[2])


def test_bolum_agaci_ilk_duzey_kitap_slugiyla_ayniysa_daraltilir() -> None:
    kok = [
        _dugum("Deneme Kitap", 4, [_dugum("Birinci Söz"), _dugum("Deneme Bölüm")]),
        _dugum("Hâtime", 9),
    ]
    daralt = _agac(kok, parca_adi=lambda _sayfa: "deneme-kitap")
    # daraltilan dugum ustunun yolunu tasir; cocuklari kokun altina baglanir
    assert daralt.yollar == ((), (), ("soz-1",), ("deneme-bolum",), ("hatime",))
    assert daralt.basliklar[2] == ("Birinci Söz",)
    assert daralt.istatistik["daraltildi"] == 1
    # parca_adi verilmezse daraltma yapilmaz (eski davranis)
    assert _agac(kok).yollar[1] == ("deneme-kitap",)


def test_bolum_agaci_bolunmus_kitapta_kardes_adlari_parcaya_gore_tekil() -> None:
    """Ayni agactaki iki kitap (parca) ayni bolum adini `-2` eki almadan kullanir."""
    kok = [_dugum("Mukaddime", 4), _dugum("Mukaddime", 8)]

    def parca(sayfa: int) -> str:
        return "deneme-a" if sayfa < 8 else "deneme-b"

    agac = _agac(kok, parca_adi=parca)
    assert agac.yollar[1:] == (("mukaddime",), ("mukaddime",))
    assert agac.istatistik["kardes_eki"] == 0
    # parca bilinmiyorsa (tek kitap) ikinci kardes `-2` alir
    assert _agac(kok).yollar[1:] == (("mukaddime",), ("mukaddime-2",))


# ---------------------------------------------------------------------------
# kitap_donustur: sayili kalip capa, p{n} sirasi, hasiye capasi


SATIRLAR = [
    "#4",
    "<Deneme Kitap>",
    "   Deneme kök paragraf 1.",
    "&Yirmi Beşinci Söz>",
    "   Deneme paragrafı 1 {(*)|Deneme dipnotu 1.} devam.",
    "   Deneme paragrafı 2.",
    "&Birinci Nükte>",
    "   Deneme paragrafı 3.",
    "&Birinci Nükte>",
    "   Deneme paragrafı 4.",
    "#5",
    "&Hâtime>",
    "   Deneme paragrafı 5 {(*)|Deneme dipnotu 2.} sonu {(**)|Deneme dipnotu 3.} bitti.",
]


def _kitap_json() -> bytes:
    kok = _dugum(
        "Deneme Kitap",
        4,
        [
            _dugum(
                "Yirmi Beşinci Söz", 4, [_dugum("Birinci Nükte", 4), _dugum("Birinci Nükte", 4)]
            ),
            _dugum("Hâtime", 5),
        ],
    )
    return _json(kok, 5)


def _sonuc() -> S.KitapSonucu:
    return donustur(sentetik_txt(SATIRLAR), _kitap_json())


def test_kitap_donustur_sayili_kalip_capalar_ve_p_sirasi() -> None:
    sonuc = _sonuc()
    capalar = {b.anchor: b for b in sonuc.birimler}
    # kok seviye: rn:{kitap}:p{n} (baslik p1, kok paragraf p2)
    assert capalar["rn:deneme-kitap:p1"].text == "Deneme Kitap"
    assert capalar["rn:deneme-kitap:p2"].text == "Deneme kök paragraf 1."
    # soz-25: baslik p1, sonra belge sirasiyla
    assert capalar["rn:deneme-kitap:soz-25:p1"].attrs["kind"] == "baslik"
    assert capalar["rn:deneme-kitap:soz-25:p2"].text.startswith("Deneme paragrafı 1")
    assert capalar["rn:deneme-kitap:soz-25:p3"].text == "Deneme paragrafı 2."
    # kardes cakismasi: ikinci `Birinci Nukte` -> nukte-1-2
    assert capalar["rn:deneme-kitap:soz-25:nukte-1:p2"].text == "Deneme paragrafı 3."
    assert capalar["rn:deneme-kitap:soz-25:nukte-1-2:p2"].text == "Deneme paragrafı 4."
    assert capalar["rn:deneme-kitap:hatime:p1"].attrs["kind"] == "baslik"
    for b in sonuc.birimler:
        if b.attrs["kind"] != "hasiye":
            n = b.anchor.rsplit(":p", 1)[1]
            assert n == str(b.attrs["p"])
    assert sonuc.kitap["bolum_adlari"]["kalip_soz"] == 1  # type: ignore[index]
    assert sonuc.kitap["bolum_adlari"]["kardes_eki"] == 1  # type: ignore[index]


def test_kitap_donustur_hasiye_capasi_ve_isareti() -> None:
    sonuc = _sonuc()
    capalar = {b.anchor: b for b in sonuc.birimler}
    h1 = capalar["rn:deneme-kitap:soz-25:hasiye-1:p1"]
    assert h1.text == "Deneme dipnotu 1." and h1.attrs["kind"] == "hasiye"
    assert h1.attrs["hasiye_no"] == 1
    ana = capalar["rn:deneme-kitap:soz-25:p2"]
    isaret = [m for m in ana.attrs["marks"] if m["t"] == "hasiye"]  # type: ignore[attr-defined]
    assert isaret == [{"t": "hasiye", "s": ana.text.index(" devam"), "a": h1.anchor}]
    # hatime: iki dipnot, bolumdeki atif sirasiyla hasiye-1 ve hasiye-2
    assert "rn:deneme-kitap:hatime:hasiye-1:p1" in capalar
    assert "rn:deneme-kitap:hatime:hasiye-2:p1" in capalar
    assert capalar["rn:deneme-kitap:hatime:hasiye-2:p1"].text == "Deneme dipnotu 3."
    # baslik zinciri: dipnot ana paragrafinin bolum basliklarini tasir
    assert h1.attrs["baslik_yolu"] == ["Yirmi Beşinci Söz"]
    assert capalar["rn:deneme-kitap:soz-25:nukte-1:p1"].attrs["baslik_yolu"] == [
        "Yirmi Beşinci Söz",
        "Birinci Nükte",
    ]
    assert capalar["rn:deneme-kitap:p2"].attrs["baslik_yolu"] == []


def test_kitap_donustur_ikinci_kosuda_ayni_capalar() -> None:
    a = [(b.anchor, b.text, json.dumps(b.attrs, sort_keys=True)) for b in _sonuc().birimler]
    b = [(b.anchor, b.text, json.dumps(b.attrs, sort_keys=True)) for b in _sonuc().birimler]
    assert a == b


def test_kitap_donustur_bolunmus_kitapta_ilk_duzey_adi_daraltilir() -> None:
    """Sunuhat/Tuluat/Isarat kalibi: ilk duzey dugum adi kitap slug'ina esitse duzey kalkar."""
    satirlar = [
        "#4",
        "<Deneme A>",
        "&Deneme A>",
        "   Deneme paragrafı 1.",
        "#6",
        "&Deneme B>",
        "   Deneme paragrafı 2.",
    ]
    kok = _dugum(
        "Deneme Kitap",
        4,
        [_dugum("Deneme A", 4, [_dugum("Mukaddime", 4)]), _dugum("Deneme B", 6)],
    )
    bol = Bolunme(7, (BolunmeParcasi("deneme-a", 4), BolunmeParcasi("deneme-b", 6)))
    kitap = [kitap_kaydi("deneme-a", bolunme=bol), kitap_kaydi("deneme-b", bolunme=bol)]
    sonuc = donustur(sentetik_txt(satirlar), _json(kok, 7), kitap)
    capalar = {b.anchor for b in sonuc.birimler}
    assert "rn:deneme-a:p1" in capalar and "rn:deneme-b:p1" in capalar
    assert not any(c.startswith("rn:deneme-a:deneme-a") for c in capalar)
    assert not any(c.startswith("rn:deneme-b:deneme-b") for c in capalar)
    assert sonuc.kitap["bolum_adlari"]["daraltildi"] == 2  # type: ignore[index]


def test_kitap_donustur_lahika_parca_capalari_ve_ikinci_kosu() -> None:
    satirlar = [
        "#4",
        "<Deneme Kitap>",
        "&Deneme Mektup A>",
        "   Deneme paragrafı 1.",
        "&Deneme Mektup B>",
        "   Deneme paragrafı 2 {(*)|Deneme dipnotu 1.} devam.",
        "&Birinci Nükte>",
        "   Deneme paragrafı 3.",
    ]
    kok = _dugum(
        "Deneme Kitap",
        4,
        [_dugum("Deneme Mektup A"), _dugum("Deneme Mektup B"), _dugum("Birinci Nükte")],
    )

    def calistir() -> S.KitapSonucu:
        return donustur(sentetik_txt(satirlar), _json(kok, 4), [kitap_kaydi("deneme-lahikasi")])

    sonuc = calistir()
    capalar = {b.anchor: b for b in sonuc.birimler}
    assert capalar["rn:deneme-lahikasi:parca-1:p1"].attrs["kind"] == "baslik"
    assert capalar["rn:deneme-lahikasi:parca-1:p2"].text == "Deneme paragrafı 1."
    assert capalar["rn:deneme-lahikasi:parca-2:p2"].text.startswith("Deneme paragrafı 2")
    assert "rn:deneme-lahikasi:parca-2:hasiye-1:p1" in capalar
    assert "rn:deneme-lahikasi:nukte-1:p2" in capalar
    assert not any("mektup" in c for c in capalar)  # baslik slug'i kullanilmaz
    assert sonuc.kitap["bolum_adlari"]["parca"] == 2  # type: ignore[index]
    # ikinci kosuda ayni capalar
    assert [b.anchor for b in calistir().birimler] == [b.anchor for b in sonuc.birimler]
