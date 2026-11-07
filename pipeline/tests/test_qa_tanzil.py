"""QA kapilari G-KAY, G-BUT, G-CAP, G-NOR ve olcumler (A10.5; bellekte, SENTETIK veri).

Her kapi icin gecen bir temel girdi ve tek bir kusur tasiyan kalan girdiler kurulur. Girdi, 9
ayetlik sentetik bir tablodan (`(7, 5)`) adimlarin kendi islevleriyle uretilir (`qa_girdisi`);
gercek bayt gereken testler `fixtures/tanzil` parcalarini kullanir. Kur'an metni hafizadan
yazilmaz.
"""

import dataclasses
import json
import shutil
import unicodedata
from pathlib import Path

import pytest
from tanzil_yardimci import parca_oku, sentetik_bildirim
from zincir_yardimci import (
    PAYLASILAN_DOSYALAR,
    kilit_tablodan,
    qa_girdisi,
    satiri_cikar,
    satiri_degistir,
    sentetik_dosya,
    varyant_kur,
    vektor_sayisi,
)

from mutalaa_pipeline.adimlar.normalize_tanzil import EK_KAYNAK, KAYNAK
from mutalaa_pipeline.anchor.ayet_sayilari import AYET_SAYILARI
from mutalaa_pipeline.export.ortak import GirdiHatasi, depo_koku
from mutalaa_pipeline.normalize import NORMALIZER_VERSION
from mutalaa_pipeline.qa import GECTI, KALDI, KAPILAR, QA_KOMUTU
from mutalaa_pipeline.qa import rapor as qa_rapor
from mutalaa_pipeline.qa.checks.tanzil import (
    KAPI_ISLEVLERI,
    Onceki,
    QaGirdisi,
    g_but,
    g_cap,
    g_kay,
    g_nor,
    olcumler,
)
from mutalaa_pipeline.staged import Satir

TABLO = (7, 5)  # gercek tablonun oneki: kuresel sira gercek tabloyla ayni
CAPALAR = [f"q:1:{a}" for a in range(1, 8)] + [f"q:2:{a}" for a in range(1, 6)]
ARAPCA_YE, ARAPCA_KEF = chr(0x06CC), chr(0x06A9)
HINT_BIR, DOGU_HINT_BIR = chr(0x0661), chr(0x06F1)
C_CEDILLA, S_CEDILLA, NBSP = (
    chr(0xE7),
    chr(0x15F),
    chr(0xA0),
)  # iletiye girmemesi gereken karakterler


@pytest.fixture(scope="module")
def temel() -> QaGirdisi:
    return qa_girdisi(TABLO)


def bulgu_var(sonuc: object, parca: str) -> bool:
    return any(parca in b for b in sonuc.bulgular)


def varyant_degistir(g: QaGirdisi, hangisi: str, **alanlar: object) -> QaGirdisi:
    return dataclasses.replace(g, **{hangisi: dataclasses.replace(getattr(g, hangisi), **alanlar)})


def kayit_degistir(g: QaGirdisi, hangisi: str, **alanlar: object) -> QaGirdisi:
    kayit = dataclasses.replace(getattr(g, hangisi).kayit, **alanlar)
    return varyant_degistir(g, hangisi, kayit=kayit)


def kilit_degistir(g: QaGirdisi, hangisi: str, **alanlar: object) -> QaGirdisi:
    kilit = dataclasses.replace(getattr(g, hangisi).kilit, **alanlar)
    return varyant_degistir(g, hangisi, kilit=kilit)


def satir_al(g: QaGirdisi, capa: str) -> Satir:
    return next(s for s in g.anchor_satirlari if s.veri["anchor"] == capa)


def satir_ekle(g: QaGirdisi, kopya_capa: str, yeni_capa: str) -> QaGirdisi:
    kaynak = next(s for s in g.anchor_satirlari if s.veri["anchor"] == kopya_capa)
    yeni = Satir("anchor", 99, {**kaynak.veri, "anchor": yeni_capa})
    return dataclasses.replace(g, anchor_satirlari=[*g.anchor_satirlari, yeni])


def satirlar_sirala(g: QaGirdisi, sira: list[int]) -> QaGirdisi:
    eski = list(g.anchor_satirlari)
    return dataclasses.replace(g, anchor_satirlari=[eski[i] for i in sira])


def sahte_kok(tmp_path: Path, goreliler: tuple[str, ...] = PAYLASILAN_DOSYALAR) -> Path:
    """Gercek degismez veri dosyalarinin kopyalarini tasiyan sahte depo koku."""
    kok = tmp_path / "kok"
    for goreli in goreliler:
        hedef = kok / goreli
        hedef.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(depo_koku() / goreli, hedef)
    return kok


# --- sozlesme -----------------------------------------------------------------------------


def test_kapi_sozlesmesi_export_pg_ile_ayni() -> None:
    """Kapi adlari, `gecti`/`kaldi` ve rapor komutu elle sabitlenir; `export pg` raporu
    `qa/rapor.py` ile arar ve ayni nesneleri kullanir (kopya yok)."""
    assert tuple(KAPI_ISLEVLERI) == KAPILAR == ("G-KAY", "G-BUT", "G-CAP", "G-NOR")
    assert (GECTI, KALDI) == ("gecti", "kaldi")
    assert QA_KOMUTU == "qa run"
    assert qa_rapor.KAPILAR is KAPILAR
    assert qa_rapor.QA_KOMUTU is QA_KOMUTU


def test_temel_girdi_dort_kapidan_gecer(temel: QaGirdisi) -> None:
    assert [s.veri["anchor"] for s in temel.anchor_satirlari] == CAPALAR
    for ad, islev in KAPI_ISLEVLERI.items():
        sonuc = islev(temel)
        assert sonuc.kapi == ad
        assert sonuc.bulgular == (), (ad, sonuc.bulgular)
        assert sonuc.gecti


def test_temel_girdi_sentetik_uthmani_nfc_degil_simple_nfc(temel: QaGirdisi) -> None:
    """NFC durumu kapi degil, olcumdur: NFC olmayan Uthmani metni kapilardan gecer."""
    metin = str(temel.anchor_satirlari[0].veri["text"])
    assert not unicodedata.is_normalized("NFC", metin)
    sonuc = olcumler(temel)["nfc"]
    assert sonuc == {
        KAYNAK: {"nfc_olmayan_ayet": len(CAPALAR)},
        EK_KAYNAK: {"nfc_olmayan_ayet": 0},
    }


# --- G-KAY --------------------------------------------------------------------------------


@pytest.fixture(params=["uthmani", "simple"])
def hangisi(request: pytest.FixtureRequest) -> str:
    return str(request.param)


def test_g_kay_notice_text_bir_bayt_farkliysa_kalir(temel: QaGirdisi, hangisi: str) -> None:
    notice = getattr(temel, hangisi).kayit.notice_text
    g = kayit_degistir(temel, hangisi, notice_text=notice.replace("Deneme", "Deneme2", 1))
    sonuc = g_kay(g)
    assert bulgu_var(sonuc, "notice_text dosyadaki bildirim blogundan farkli")
    assert bulgu_var(sonuc, "sha256(notice_text)")  # kilitteki bildirim_sha256'dan da ayrilir
    assert getattr(g, hangisi).kaynak in sonuc.bulgular[0]
    assert not sonuc.gecti


def test_g_kay_rstrip_yok_sondaki_lf_farki_kalir(temel: QaGirdisi, hangisi: str) -> None:
    notice = getattr(temel, hangisi).kayit.notice_text
    assert notice.endswith("\n")
    g = kayit_degistir(temel, hangisi, notice_text=notice.rstrip("\n"))
    assert bulgu_var(g_kay(g), "notice_text dosyadaki bildirim blogundan farkli")


def test_g_kay_kayitta_notice_text_yok(temel: QaGirdisi, hangisi: str) -> None:
    g = kayit_degistir(temel, hangisi, notice_text=None)
    assert bulgu_var(g_kay(g), "kayitta notice_text yok")


@pytest.mark.parametrize("atif", ["", "   ", " \t\n"])
def test_g_kay_atif_metni_bos(temel: QaGirdisi, atif: str) -> None:
    assert bulgu_var(g_kay(kayit_degistir(temel, "uthmani", atif_metni=atif)), "atif_metni bos")


def test_g_kay_kilit_bildirim_ozeti_tutmuyor(temel: QaGirdisi, hangisi: str) -> None:
    g = kilit_degistir(temel, hangisi, bildirim_sha256="0" * 64)
    sonuc = g_kay(g)
    assert bulgu_var(sonuc, "sha256(notice_text)")
    assert not bulgu_var(sonuc, "notice_text dosyadaki bildirim blogundan farkli")


def test_g_kay_staged_notice_txt_yok_ya_da_farkli(temel: QaGirdisi, hangisi: str) -> None:
    assert bulgu_var(
        g_kay(varyant_degistir(temel, hangisi, bildirim_dosyasi=None)), "notice.txt yok"
    )
    bozuk = varyant_degistir(temel, hangisi, bildirim_dosyasi=b"\n\n# baska\n")
    assert bulgu_var(g_kay(bozuk), "staged notice.txt dosyadaki bildirim blogundan farkli")


def test_g_kay_surum_ve_adres_tutarliligi(temel: QaGirdisi, hangisi: str) -> None:
    assert bulgu_var(g_kay(kayit_degistir(temel, hangisi, surum="1.2")), "kayit surumu")
    assert bulgu_var(g_kay(kilit_degistir(temel, hangisi, surum="1.2")), "kilit surumu")
    assert bulgu_var(
        g_kay(varyant_degistir(temel, hangisi, ingest_surum="1.2")), "ingest manifestindeki surum"
    )
    assert bulgu_var(
        g_kay(kayit_degistir(temel, hangisi, kaynak_url="https://example.invalid/")), "kaynak_url"
    )
    assert bulgu_var(g_kay(kayit_degistir(temel, hangisi, kaynak_url=None)), "kaynak_url")


def test_g_kay_bildirim_basligi_cozulemezse_kalir() -> None:
    basliksiz = sentetik_dosya("uthmani", TABLO, bildirim=b"\n\n# Deneme\n")
    g = qa_girdisi(TABLO, uthmani=basliksiz)
    assert bulgu_var(g_kay(g), "bildirim basligi (tur ve surum) cozulemedi")


def test_g_kay_iletisi_ascii_ve_icerik_tasimaz(temel: QaGirdisi) -> None:
    g = kayit_degistir(
        temel, "uthmani", notice_text="Deneme " + C_CEDILLA + S_CEDILLA, surum=C_CEDILLA
    )
    for bulgu in g_kay(g).bulgular:
        assert bulgu.isascii()


# --- G-BUT --------------------------------------------------------------------------------


def test_g_but_ayet_eksikse_kalir(temel: QaGirdisi) -> None:
    sonuc = g_but(satiri_cikar(temel, "q:2:5"))
    assert bulgu_var(sonuc, "anchor satirlari: ayet sayisi 11, beklenen 12")
    assert bulgu_var(sonuc, "sure 2 (4/5)")
    assert bulgu_var(sonuc, "eksik birim: 1 birim")
    assert bulgu_var(sonuc, "q:2:5")


def test_g_but_sure_eksikse_kalir(temel: QaGirdisi) -> None:
    g = temel
    for ayet in range(1, 6):  # 2. surenin butun satirlari yok
        g = satiri_cikar(g, f"q:2:{ayet}")
    sonuc = g_but(g)
    assert bulgu_var(sonuc, "anchor satirlari: sure sayisi 1, beklenen 2")
    assert bulgu_var(sonuc, "anchor satirlari: ayet sayisi 7, beklenen 12")
    assert bulgu_var(sonuc, "sure 2 (0/5)")


def test_g_but_tablo_ham_dosyayla_uyusmazsa_kalir(temel: QaGirdisi) -> None:
    sonuc = g_but(dataclasses.replace(temel, sure_tablosu=(7, 6)))
    assert bulgu_var(sonuc, "anchor satirlari: ayet sayisi 12, beklenen 13")
    assert bulgu_var(sonuc, "tanzil-uthmani ham dosya: ayet sayisi 12, beklenen 13")
    assert bulgu_var(sonuc, "tanzil-simple-clean ham dosya: ayet sayisi 12, beklenen 13")


@pytest.mark.parametrize("bos", ["", " ", " \t\n  "])
def test_g_but_bos_birim(temel: QaGirdisi, bos: str) -> None:
    sonuc = g_but(satiri_degistir(temel, "q:2:2", text=bos))
    assert bulgu_var(sonuc, "bos birim: 1 birim: metin bos: q:2:2")


@pytest.mark.parametrize("karakter", ["\x00", "\x07", "\n", "\t", "\x7f", "\x85"])
def test_g_but_kontrol_karakteri(temel: QaGirdisi, karakter: str) -> None:
    metin = str(satir_al(temel, "q:2:1").veri["text"])
    sonuc = g_but(satiri_degistir(temel, "q:2:1", text=metin + karakter))
    assert bulgu_var(sonuc, "kontrol karakteri: 1 birim")


def test_g_but_u00a0_kontrol_karakteri_degildir(temel: QaGirdisi) -> None:
    metin = str(satir_al(temel, "q:2:1").veri["text"])
    sonuc = g_but(satiri_degistir(temel, "q:2:1", text=metin + NBSP))
    assert not bulgu_var(sonuc, "kontrol karakteri")  # yalniz Cc; baytlar yine farkli
    assert bulgu_var(sonuc, "bayt esitligi")


def test_g_but_nfc_uygulanmissa_bayt_esitligi_kalir(temel: QaGirdisi) -> None:
    metin = str(temel.anchor_satirlari[0].veri["text"])
    nfc = unicodedata.normalize("NFC", metin)
    assert nfc != metin  # sentetik Uthmani sedde + hareke sirasi NFC'de degisir
    sonuc = g_but(satiri_degistir(temel, "q:1:1", text=nfc))
    assert bulgu_var(sonuc, "bayt esitligi: 1 birim: metin ham dosyanin bayt dilimiyle ayni degil")


def test_g_but_baytlar_bir_harf_farkliysa_kalir(temel: QaGirdisi) -> None:
    metin = str(temel.anchor_satirlari[1].veri["text"])
    assert bulgu_var(g_but(satiri_degistir(temel, "q:1:2", text=metin + "x")), "bayt esitligi")
    assert bulgu_var(g_but(satiri_degistir(temel, "q:1:2", text=metin[1:])), "bayt esitligi")


def test_g_but_ham_dosyada_olmayan_capa(temel: QaGirdisi) -> None:
    sonuc = g_but(satir_ekle(temel, "q:1:1", "q:2:6"))  # q:2:6 gecerli capa ama dosyada yok
    assert bulgu_var(sonuc, "ham dosyada karsiligi: 1 birim")
    assert bulgu_var(sonuc, "q:2:6")


def test_g_but_provenance_ham_dosyayla_tutmali(temel: QaGirdisi) -> None:
    kok = dict(temel.anchor_satirlari[2].veri["provenance"])
    for alan, deger in (("line", 99), ("bayt", [0, 1]), ("sha256", "0" * 64), ("file", "x.txt")):
        sonuc = g_but(satiri_degistir(temel, "q:1:3", provenance={**kok, alan: deger}))
        assert bulgu_var(sonuc, "provenance: 1 birim"), alan


def test_g_but_provenance_bool_ile_tam_sayi_ayri_sayilir(temel: QaGirdisi) -> None:
    kok = dict(temel.anchor_satirlari[0].veri["provenance"])
    assert kok["line"] == 1
    sonuc = g_but(satiri_degistir(temel, "q:1:1", provenance={**kok, "line": True}))
    assert bulgu_var(sonuc, "provenance: 1 birim")  # True == 1 ama JSON'da farkli


def test_g_but_donusum_adimi_kalir(temel: QaGirdisi) -> None:
    kok = dict(temel.anchor_satirlari[0].veri["provenance"])
    for adimlar in (["nfc"], ["bosluk", "nfc"], None, "nfc"):
        sonuc = g_but(satiri_degistir(temel, "q:1:1", provenance={**kok, "steps": adimlar}))
        assert bulgu_var(sonuc, "donusum adimi: 1 birim"), adimlar


@pytest.mark.parametrize(
    ("alan", "parca"),
    [
        ("sha256", "ham dosya kilitteki sha256 ve boyutla tutmuyor"),
        ("boyut", "ham dosya kilitteki sha256 ve boyutla tutmuyor"),
        ("metin_sha256", "ayet satirlari kilitteki metin_sha256 ile tutmuyor"),
        ("bildirim_sha256", "bildirim blogu kilitteki bildirim_sha256 ile tutmuyor"),
    ],
)
def test_g_but_ham_dosya_kilitle_tutmali(
    temel: QaGirdisi, hangisi: str, alan: str, parca: str
) -> None:
    yeni = "0" * 64 if alan != "boyut" else 1
    sonuc = g_but(kilit_degistir(temel, hangisi, **{alan: yeni}))
    assert bulgu_var(sonuc, parca)
    assert bulgu_var(sonuc, getattr(temel, hangisi).kaynak)


def test_g_but_ayet_sayilari_kopyasi_farkliysa_kalir(tmp_path: Path, temel: QaGirdisi) -> None:
    kok = sahte_kok(tmp_path)
    g = dataclasses.replace(temel, depo_kok=kok)
    assert g_but(g).gecti
    ts = kok / "packages/anchors/src/generated/ayet-sayilari.ts"
    ts.write_bytes(ts.read_bytes() + b"// elle eklenmis\n")
    sonuc = g_but(g)
    assert bulgu_var(sonuc, "packages/anchors/src/generated/ayet-sayilari.ts")
    assert bulgu_var(sonuc, "export ayet-sayilari --check")
    assert not bulgu_var(sonuc, "dizisi kodun tablosuyla")


def test_g_but_json_kodun_tablosundan_farkliysa_kalir(tmp_path: Path, temel: QaGirdisi) -> None:
    kok = sahte_kok(tmp_path)
    yol = kok / "shared/data/ayet-sayilari.json"
    belge = json.loads(yol.read_bytes())
    assert belge["sayilar"][0] == 7
    belge["sayilar"][0] = 8
    yol.write_bytes((json.dumps(belge, indent=2) + "\n").encode("utf-8"))
    sonuc = g_but(dataclasses.replace(temel, depo_kok=kok))
    assert bulgu_var(sonuc, "ayet-sayilari.json dizisi kodun tablosuyla (AYET_SAYILARI) ayni degil")
    assert bulgu_var(sonuc, "AyetSayilari.g.cs")  # uc kopya JSON'dan uretilene esit degil


def test_g_but_json_yoksa_kalir_ve_ascii(tmp_path: Path, temel: QaGirdisi) -> None:
    kok = sahte_kok(tmp_path, ())
    sonuc = g_but(dataclasses.replace(temel, depo_kok=kok))
    assert bulgu_var(sonuc, "ayet-sayilari.json okunamadi")
    assert all(b.isascii() for b in sonuc.bulgular)


def test_g_but_iletisi_icerik_tasimaz(temel: QaGirdisi) -> None:
    metin = str(temel.anchor_satirlari[0].veri["text"])
    sonuc = g_but(satiri_degistir(temel, "q:1:1", text=metin + "\x07"))
    assert all(b.isascii() for b in sonuc.bulgular)
    assert metin[:3] not in "".join(sonuc.bulgular)


# --- G-CAP --------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "capa", ["q:1:1:3", "q:1:1-2", "q:1:1@0-3", "meal:elmalili:1:1", "Q:1:1", "x"]
)
def test_g_cap_gecersiz_capa(temel: QaGirdisi, capa: str) -> None:
    sonuc = g_cap(satiri_degistir(temel, "q:1:1", anchor=capa))
    assert bulgu_var(sonuc, "gecersiz capa: 1 birim")
    assert bulgu_var(sonuc, "eksik capa: 1 birim")


def test_g_cap_yinelenen_capa(temel: QaGirdisi) -> None:
    sonuc = g_cap(satiri_degistir(temel, "q:1:2", anchor="q:1:1"))
    assert bulgu_var(sonuc, "yinelenen capa: 1 birim")
    assert bulgu_var(sonuc, "eksik capa: 1 birim")


def test_g_cap_okuma_sirasi_bozuksa_kalir(temel: QaGirdisi) -> None:
    sira = list(range(12))
    sira[1], sira[2] = sira[2], sira[1]
    sonuc = g_cap(satirlar_sirala(temel, sira))
    assert bulgu_var(sonuc, "okuma sirasi: 1 birim")


def test_g_cap_tabloda_olmayan_ayet_fazla_capa(temel: QaGirdisi) -> None:
    sonuc = g_cap(satiri_degistir(temel, "q:2:5", anchor="q:3:1"))  # (7, 5) tablosunda yok
    assert bulgu_var(sonuc, "fazla capa: 1 birim")
    assert bulgu_var(sonuc, "q:3:1")
    assert bulgu_var(sonuc, "eksik capa: 1 birim")


@pytest.mark.parametrize(
    "degisim",
    [
        {"ord": 99},
        {"ayah_lo": 99},
        {"ayah_hi": 99},
        {"ayah_hi": 3},  # bos aralik: [3, 3)
        {"ord": 2, "ayah_lo": 2, "ayah_hi": 3},  # tutarli ama kuresel sira degil
    ],
)
def test_g_cap_ord_ve_ayah_kuresel_sira_olmali(temel: QaGirdisi, degisim: dict[str, int]) -> None:
    sonuc = g_cap(satiri_degistir(temel, "q:1:3", **degisim))
    assert bulgu_var(sonuc, "ord/ayah: 1 birim")
    assert bulgu_var(sonuc, "q:1:3")


def test_g_cap_ord_ve_ayah_dogruysa_gecer(temel: QaGirdisi) -> None:
    # q:1:3 icin kuresel sira 3: ord = ayah_lo = 3, ayah_hi = 4
    assert g_cap(satiri_degistir(temel, "q:1:3", ord=3, ayah_lo=3, ayah_hi=4)).gecti


def test_g_cap_ord_tam_sayi_olmali(temel: QaGirdisi) -> None:
    with pytest.raises(GirdiHatasi, match="'ord' tam sayi degil"):
        g_cap(satiri_degistir(temel, "q:1:3", ord="3"))
    with pytest.raises(GirdiHatasi, match="'ord' tam sayi degil"):
        g_cap(satiri_degistir(temel, "q:1:3", ord=True))


def test_g_cap_content_hash(temel: QaGirdisi) -> None:
    dogru = str(temel.anchor_satirlari[2].veri["content_hash"])
    assert bulgu_var(
        g_cap(satiri_degistir(temel, "q:1:3", content_hash="0" * 64)),
        "content_hash: 1 birim: metnin SHA-256'siyla tutmuyor",
    )
    for bozuk in (dogru.upper(), dogru[:-1], "sha256:" + dogru, ""):
        sonuc = g_cap(satiri_degistir(temel, "q:1:3", content_hash=bozuk))
        assert bulgu_var(sonuc, "content_hash biciminde: 1 birim"), bozuk


def test_g_cap_metin_degisirse_ozet_tutmaz(temel: QaGirdisi) -> None:
    metin = str(temel.anchor_satirlari[2].veri["text"])
    assert bulgu_var(g_cap(satiri_degistir(temel, "q:1:3", text=metin + " ")), "content_hash:")


@pytest.mark.parametrize(
    "degisim",
    [
        {"kind": "meal"},
        {"source_id": "tanzil-simple-clean"},
        {"metin_durumu": "taslak"},
        {"data_version": "tanzil-uthmani@1.0"},
        {"data_version": "tanzil-uthmani@"},
    ],
)
def test_g_cap_sabit_alanlar(temel: QaGirdisi, degisim: dict[str, str]) -> None:
    sonuc = g_cap(satiri_degistir(temel, "q:2:2", **degisim))
    assert bulgu_var(sonuc, "sabit alan: 1 birim")


def test_g_cap_onceki_capalar_durmali(temel: QaGirdisi) -> None:
    ozetler = {str(s.veri["anchor"]): str(s.veri["content_hash"]) for s in temel.anchor_satirlari}
    ayni = dataclasses.replace(temel, onceki=Onceki("onceki-run", ozetler))
    sonuc = g_cap(ayni)
    assert sonuc.gecti
    assert sonuc.sayilar["onceki_run"] == 1
    assert sonuc.sayilar["onceki_capa"] == len(CAPALAR)

    kayip = dataclasses.replace(temel, onceki=Onceki("o", {**ozetler, "q:2:6": "a" * 64}))
    assert bulgu_var(g_cap(kayip), "onceki surumde olup kaybolan capa: 1 birim: q:2:6")

    degisen = dataclasses.replace(temel, onceki=Onceki("o", {**ozetler, "q:1:1": "a" * 64}))
    assert bulgu_var(g_cap(degisen), "onceki surumle content_hash farkli: 1 birim: q:1:1")


def test_g_cap_onceki_yoksa_sayac_sifir(temel: QaGirdisi) -> None:
    assert g_cap(temel).sayilar["onceki_run"] == 0


def test_g_cap_gercek_tabloda_tam_kume_beklenir() -> None:
    g = qa_girdisi(TABLO)
    gercek = dataclasses.replace(g, sure_tablosu=AYET_SAYILARI)
    sonuc = g_cap(gercek)  # yalniz 9 satir var: 6.236 beklenir
    assert sonuc.sayilar["beklenen_capa"] == 6236
    assert bulgu_var(sonuc, f"eksik capa: {6236 - 12} birim")


# --- G-NOR --------------------------------------------------------------------------------


def vektor_koku_kur(tmp_path: Path) -> Path:
    return sahte_kok(
        tmp_path,
        (
            "shared/test-vectors/normalize/tr.jsonl",
            "shared/test-vectors/normalize/ar.jsonl",
        ),
    )


def test_g_nor_vektor_sayisi_gercek_dosyalardan(temel: QaGirdisi) -> None:
    sonuc = g_nor(temel)
    assert sonuc.sayilar["vektor"] == vektor_sayisi()
    assert sonuc.sayilar["vektor"] >= 148  # A05: tr 86 + ar 62 (A10.7 ar-tz- satirlari ekler)
    assert sonuc.sayilar["vektor_kalan"] == 0


def test_g_nor_vektor_kalirsa_kalir(tmp_path: Path, temel: QaGirdisi) -> None:
    kok = vektor_koku_kur(tmp_path)
    yol = kok / "shared/test-vectors/normalize/ar.jsonl"
    satirlar = yol.read_bytes().decode("utf-8").split("\n")
    ilk = json.loads(satirlar[0])
    ilk["expected"] = "bozuk"
    satirlar[0] = json.dumps(ilk, ensure_ascii=True, separators=(",", ":"))
    yol.write_bytes("\n".join(satirlar).encode("utf-8"))
    sonuc = g_nor(dataclasses.replace(temel, depo_kok=kok))
    assert bulgu_var(sonuc, f"normalizasyon vektoru: 1/{vektor_sayisi()} kaldi: ar-0001")


def test_g_nor_tr_vektoru_kalirsa_kalir(tmp_path: Path, temel: QaGirdisi) -> None:
    kok = vektor_koku_kur(tmp_path)
    yol = kok / "shared/test-vectors/normalize/tr.jsonl"
    satirlar = yol.read_bytes().decode("utf-8").split("\n")
    ilk = json.loads(satirlar[0])
    ilk["expected"]["genis"] = "bozuk"
    satirlar[0] = json.dumps(ilk, ensure_ascii=True, separators=(",", ":"))
    yol.write_bytes("\n".join(satirlar).encode("utf-8"))
    sonuc = g_nor(dataclasses.replace(temel, depo_kok=kok))
    assert bulgu_var(sonuc, f"1/{vektor_sayisi()} kaldi: tr-0001")


def test_g_nor_vektor_dosyasi_yoksa_ya_bozuksa_girdi_hatasi(
    tmp_path: Path, temel: QaGirdisi
) -> None:
    bos_kok = sahte_kok(tmp_path / "bos", ())
    with pytest.raises(GirdiHatasi, match="okunamadi"):
        g_nor(dataclasses.replace(temel, depo_kok=bos_kok))
    kok = vektor_koku_kur(tmp_path / "bozuk")
    yol = kok / "shared/test-vectors/normalize/ar.jsonl"
    yol.write_bytes(yol.read_bytes() + b"{bozuk\n")
    with pytest.raises(GirdiHatasi, match="JSON gecersiz"):
        g_nor(dataclasses.replace(temel, depo_kok=kok))
    yol.write_bytes(b"\xef\xbb\xbf" + yol.read_bytes())
    with pytest.raises(GirdiHatasi, match="BOM ya da CR"):
        g_nor(dataclasses.replace(temel, depo_kok=kok))


def test_g_nor_ar_norm_ham_dosyadan_uretilenle_ayni_olmali(temel: QaGirdisi) -> None:
    eski = str(temel.anchor_satirlari[0].veri["ar_norm"])
    for yeni in (eski + " x", "x " + eski, eski.upper() + "y", ""):
        sonuc = g_nor(satiri_degistir(temel, "q:1:1", ar_norm=yeni))
        assert bulgu_var(sonuc, "ar_norm: 1 birim: ham dosyalardan AR-4 ile uretilen"), yeni
    assert bulgu_var(g_nor(satiri_degistir(temel, "q:1:1", ar_norm="")), "bos ar_norm: 1 birim")


def test_g_nor_ar4_eki_olmadan_uretilmisse_kalir(temel: QaGirdisi) -> None:
    """(sure + ayet) % 3 == 0 ayetlerinde Uthmani'ye ozgu sozcuk ar_norm sonunda olmali."""
    satir = next(s for s in temel.anchor_satirlari if s.veri["anchor"] == "q:1:2")
    ek_yok = " ".join(str(satir.veri["ar_norm"]).split(" ")[:-1])  # son sozcuk (AR-4 eki) yok
    assert bulgu_var(g_nor(satiri_degistir(temel, "q:1:2", ar_norm=ek_yok)), "ar_norm: 1 birim")


@pytest.mark.parametrize(
    ("alan", "deger"),
    [
        ("kaynak", "tanzil-uthmani"),
        ("sha256", "0" * 64),
        ("line", 99),
        ("normalizer_version", "0.9"),
        ("normalizer_version", NORMALIZER_VERSION + ".0"),
        ("ar4", False),
        ("ar4", 1),  # JSON'da true degil
        ("ek", "x"),
    ],
)
def test_g_nor_provenance_ar_norm_kaydi(temel: QaGirdisi, alan: str, deger: object) -> None:
    kok = dict(satir_al(temel, "q:2:2").veri["provenance"])
    kayit = {**kok["ar_norm"], alan: deger}
    sonuc = g_nor(satiri_degistir(temel, "q:2:2", provenance={**kok, "ar_norm": kayit}))
    assert bulgu_var(sonuc, "provenance.ar_norm: 1 birim")


def test_g_nor_provenance_ar_norm_eksikse_kalir(temel: QaGirdisi) -> None:
    kok = {k: v for k, v in satir_al(temel, "q:2:2").veri["provenance"].items() if k != "ar_norm"}
    assert bulgu_var(
        g_nor(satiri_degistir(temel, "q:2:2", provenance=kok)), "provenance.ar_norm: 1 birim"
    )


@pytest.mark.parametrize("alan", ["tr_narrow", "tr_wide", "tr_stem"])
def test_g_nor_kuran_biriminde_tr_alani_bos_olmali(temel: QaGirdisi, alan: str) -> None:
    assert bulgu_var(g_nor(satiri_degistir(temel, "q:1:1", **{alan: "x"})), "tr alani: 1 birim")
    assert g_nor(satiri_degistir(temel, "q:1:1", **{alan: None})).gecti  # bos: sorun yok


# --- olcumler -----------------------------------------------------------------------------


def test_olcumler_temel_girdi(temel: QaGirdisi) -> None:
    sonuc = olcumler(temel)
    assert set(sonuc) == {
        "nfc",
        "ar8",
        "ar8_gorulen",
        "mn_kalan",
        "mn_kalan_gorulen",
        "besmele",
        "ar4",
        "ayet_sayilari",
        "ayet_sayilari_json",
    }
    assert sonuc["ar8_gorulen"] is False
    assert sonuc["mn_kalan_gorulen"] is False
    assert sonuc["ayet_sayilari"] == {
        KAYNAK: {"sure": 2, "ayet": 12},
        EK_KAYNAK: {"sure": 2, "ayet": 12},
    }
    ar4 = sonuc["ar4"]
    assert ar4["ek_sozcuklu_ayet"] > 0
    assert ar4["ek_sozcuk"] >= ar4["ek_sozcuklu_ayet"]


def test_olcumler_json_dizisi_parca_dosyayla_ayni_degil(temel: QaGirdisi) -> None:
    """JSON 114 sureli gercek dizidir; 12 ayetlik sentetik dosyalar onunla ayni degildir."""
    assert olcumler(temel)["ayet_sayilari_json"] == {
        "okundu": True,
        "eleman": 114,
        "toplam": 6236,
        "uthmani_ile_ayni": False,
        "simple_clean_ile_ayni": False,
        "kodun_tablosuyla_ayni": True,
        "kopyalar_ayni": True,
    }


def test_olcumler_json_dizisi_tam_dosyalarla_ayni() -> None:
    tam = qa_girdisi(AYET_SAYILARI)  # 6.236 sentetik ayet, gercek tablo
    sonuc = olcumler(tam)["ayet_sayilari_json"]
    assert sonuc["uthmani_ile_ayni"] is True
    assert sonuc["simple_clean_ile_ayni"] is True
    assert (sonuc["eleman"], sonuc["toplam"]) == (114, 6236)


def test_olcumler_json_dizisi_okunamazsa_ve_kopya_farkliysa(
    tmp_path: Path, temel: QaGirdisi
) -> None:
    assert olcumler(dataclasses.replace(temel, depo_kok=sahte_kok(tmp_path / "bos", ())))[
        "ayet_sayilari_json"
    ] == {"okundu": False}
    kok = sahte_kok(tmp_path / "dolu")
    ts = kok / "packages/anchors/src/generated/ayet-sayilari.ts"
    ts.write_bytes(ts.read_bytes() + b"// elle eklenmis\n")
    sonuc = olcumler(dataclasses.replace(temel, depo_kok=kok))["ayet_sayilari_json"]
    assert sonuc["okundu"] is True
    assert sonuc["kopyalar_ayni"] is False
    assert sonuc["kodun_tablosuyla_ayni"] is True


def test_olcumler_ar8_farsca_harfler_ve_hint_rakamlar() -> None:
    ham = sentetik_dosya("uthmani", TABLO)
    ek = ARAPCA_YE + ARAPCA_KEF + HINT_BIR + DOGU_HINT_BIR
    degisik = ham.replace(b"1|1|", b"1|1|" + ek.encode("utf-8"), 1)
    sonuc = olcumler(qa_girdisi(TABLO, uthmani=degisik))
    assert sonuc["ar8_gorulen"] is True
    assert sonuc["ar8"][KAYNAK] == {
        "farsca_ye_u06cc": 1,
        "farsca_kef_u06a9": 1,
        "arapca_hint_rakam_u0660_u0669": 1,
        "dogu_arapca_hint_rakam_u06f0_u06f9": 1,
    }
    assert sum(sonuc["ar8"][EK_KAYNAK].values()) == 0


def test_olcumler_normalizasyondan_sonra_kalan_birlesen_isaret() -> None:
    isaret = chr(0x0610)  # silme araliginin disinda: normalize sonrasi kalir (Mn)
    ham = sentetik_dosya("simple-clean", TABLO)
    degisik = ham.replace(b"1|1|", b"1|1|" + isaret.encode("utf-8"), 1)
    sonuc = olcumler(qa_girdisi(TABLO, simple=degisik))
    assert sonuc["mn_kalan_gorulen"] is True
    assert sonuc["mn_kalan"][EK_KAYNAK] == {"U+0610": 1}
    assert sonuc["mn_kalan"][KAYNAK] == {}


def test_olcumler_ascii(temel: QaGirdisi) -> None:
    metin = json.dumps(olcumler(temel), ensure_ascii=False)
    assert metin.isascii()


# --- gercek parca uzerinde (dosyadan betikle kesilmis baytlar) ------------------------------


@pytest.fixture(scope="module")
def parca() -> QaGirdisi:
    return qa_girdisi((7, 33), uthmani=parca_oku("uthmani"), simple=parca_oku("simple-clean"))


def test_gercek_parca_dort_kapidan_gecer(parca: QaGirdisi) -> None:
    for ad, islev in KAPI_ISLEVLERI.items():
        assert islev(parca).bulgular == (), ad


def test_gercek_parca_varsayilan_tabloda_g_but_ve_g_cap_kalir(parca: QaGirdisi) -> None:
    """40 ayet 6.236 degildir: tam tabloyla yalniz sayi kapilari kalir."""
    tam = dataclasses.replace(parca, sure_tablosu=AYET_SAYILARI)
    assert not g_but(tam).gecti
    assert not g_cap(tam).gecti
    assert g_kay(tam).gecti
    assert g_nor(tam).gecti


def test_gercek_parca_besmele_olcumu(parca: QaGirdisi) -> None:
    besmele = olcumler(parca)["besmele"]
    for kaynak in (KAYNAK, EK_KAYNAK):
        sonuc = besmele[kaynak]
        assert sonuc["ayri_besmele_satiri"] is False  # ayri satir yok
        assert sonuc["fatiha_ilk_ayet_belirtec"] == 4  # Fatiha 1:1 dort belirtec
        assert sonuc["karsilastirilan_sure"] == 1  # parcada yalniz 2. sure var
        assert sonuc["ilk_dort_belirtec_ayni_bayt"] == 1  # 2:1 ilk dort belirteci 1:1 ile ayni
        assert sonuc["yazim_farki_sureler"] == []
        assert sonuc["farkli_sureler"] == []


def test_gercek_parca_nfc_olcumu_formulle_ayni(parca: QaGirdisi) -> None:
    sonuc = olcumler(parca)["nfc"]
    for kaynak, v in ((KAYNAK, parca.uthmani), (EK_KAYNAK, parca.simple)):
        beklenen = sum(
            1 for ay in v.ayrisma.ayetler if not unicodedata.is_normalized("NFC", ay.metin)
        )
        assert sonuc[kaynak]["nfc_olmayan_ayet"] == beklenen
    assert sonuc[KAYNAK]["nfc_olmayan_ayet"] > 0
    assert sonuc[EK_KAYNAK]["nfc_olmayan_ayet"] == 0


def test_gercek_parca_ar8_ve_mn_yok(parca: QaGirdisi) -> None:
    sonuc = olcumler(parca)
    assert sonuc["ar8_gorulen"] is False
    assert sonuc["mn_kalan_gorulen"] is False


def test_gercek_parca_g_kay_gercek_bildirimle() -> None:
    """notice_text gercek dosyadaki bildirim blogunun baytlari: bir bayt farkta kalir."""
    g = qa_girdisi((7, 33), uthmani=parca_oku("uthmani"), simple=parca_oku("simple-clean"))
    notice = g.uthmani.kayit.notice_text
    assert notice is not None
    assert notice.startswith("\n\n# ")
    assert g_kay(g).gecti
    degisik = kayit_degistir(g, "uthmani", notice_text=notice.replace("2007", "2008", 1))
    assert not g_kay(degisik).gecti


def test_varyant_kur_kilit_tablodan_uyumlu() -> None:
    ham = sentetik_dosya("uthmani", TABLO)
    v = varyant_kur("uthmani", ham, TABLO)
    assert v.kilit == kilit_tablodan("uthmani", ham, TABLO)
    assert v.ayrisma.bildirim == sentetik_bildirim("uthmani")
