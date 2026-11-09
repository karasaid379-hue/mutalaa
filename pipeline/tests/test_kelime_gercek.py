"""Kelime bolmesi gercek veriyle (A11.2, K-43): Tanzil Uthmani <-> QPC1 duzeni.

Veri yoksa atlanir (CI'da `data/` yoktur; `MUTALAA_DEGISMEZLIK_ZORUNLU=1` atlamayi hataya cevirir).
QPC1 duzeni (`data/gelen/medine-604-duzen/<tarih>/mushaf/QPC1/page-NNN.json`) yalniz kelime SAYISI
ve KONUM dogrulayicisidir; Kur'an metni olarak alinmaz. Dosyalar yalniz JSON olarak okunur
(hicbir sey calistirilmaz) ve `SHA256SUMS` ile dogrulanir. Sayilar teste yazilmaz: kaynak
dosyadan ve yapisal kurallardan turetilir. Hata iletileri yalniz capa ve sayi tasir.
"""

import hashlib
import json
import os
import re
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import pytest

from mutalaa_pipeline.anchor import quran
from mutalaa_pipeline.anchor.quran import (
    BESMELE_BELIRTEC,
    BIRLESTIRME,
    Kelime,
    besmele_onekli_mi,
    kelimelere_bol,
)
from mutalaa_pipeline.config import Ayarlar
from mutalaa_pipeline.ingest import tanzil, tanzil_bicim
from mutalaa_pipeline.normalize import normalize_ar

KLASOR_DESENI = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
HINT_ILK, HINT_SON = 0x0660, 0x0669  # Arapca-Hint rakamlar (QPC1'de ayet numarasi)
# QPC1 ile Tanzil'in harf iskeleti ayri yazimlar: konum ve sayi ayni, yazim farkli. Olculen
# fark (8 Kasim 2026, QPC1 v2 ucu): tek kelime. Yeni bir fark karar ister (iskelet testi kirmizi).
ISKELET_ISTISNALARI = frozenset({(11, 13, 3)})
_ORTAM_VERI_KOK = os.environ.get("MUTALAA_VERI_KOK")

Konum = tuple[int, int]


def _yok(neden: str) -> None:
    if os.environ.get("MUTALAA_DEGISMEZLIK_ZORUNLU") == "1":
        pytest.fail(f"zorunlu gercek veri testi veri bulamadi: {neden}")
    pytest.skip(neden)


def _veri_kok() -> Path:
    if _ORTAM_VERI_KOK is not None:
        return Ayarlar(veri_kok=Path(_ORTAM_VERI_KOK)).veri_kok
    return Ayarlar().veri_kok


def _iskelet(metin: str) -> str:
    """Harf iskeleti: harekesiz, isaretsiz, bosluksuz (A05 `normalize_ar`)."""
    return "".join(normalize_ar(metin).split())


def _hint_mi(harf: str) -> bool:
    return HINT_ILK <= ord(harf) <= HINT_SON


def _yalniz_hint(metin: str) -> bool:
    return metin != "" and all(_hint_mi(h) for h in metin)


@dataclass(frozen=True)
class Gercek:
    ayetler: Mapping[Konum, str]  # Tanzil Uthmani ayet metinleri
    qpc1: Mapping[Konum, Mapping[int, str]]  # (sure, ayet) -> kelime no -> QPC1 kelimesi
    qpc1_ayet_sonu: int  # yalniz rakamdan olusan "ayet sonu" girdisi sayisi


def _tanzil_ayetleri(veri_kok: Path) -> dict[Konum, str]:
    tarih = tanzil.kilit_yukle()["uthmani"].alinma_tarihi
    yol = veri_kok / "gelen" / "tanzil" / tarih / tanzil.dosya_adi("uthmani")
    if not yol.is_file():
        _yok(f"gelen dosyasi yok: gelen/tanzil/{tarih}/{tanzil.dosya_adi('uthmani')}")
    ayrisma = tanzil_bicim.ayristir(yol.read_bytes())
    return {(ay.sure, ay.ayet): ay.metin for ay in ayrisma.ayetler}


def _qpc1_klasoru(veri_kok: Path) -> Path:
    """`medine-604-duzen/` altindaki en yeni gecerli tarih klasorunun `mushaf/QPC1` dizini."""
    kok = veri_kok / "gelen" / "medine-604-duzen"
    adaylar = (
        sorted(p for p in kok.iterdir() if p.is_dir() and KLASOR_DESENI.fullmatch(p.name))
        if kok.is_dir()
        else []
    )
    for tarih_klasoru in reversed(adaylar):
        if (tarih_klasoru / "mushaf" / "QPC1").is_dir() and (
            tarih_klasoru / "SHA256SUMS"
        ).is_file():
            return tarih_klasoru
    _yok("data/gelen/medine-604-duzen/<tarih>/mushaf/QPC1 yok (QPC1 duzeni indirilmemis)")
    raise AssertionError  # _yok her zaman cikar


def _sha256sums_dogrula(tarih_klasoru: Path) -> None:
    """`sha256sum` bicimi: '<ozet> *<yol>' (yol klasore gore)."""
    sayi = 0
    for satir in (tarih_klasoru / "SHA256SUMS").read_text(encoding="utf-8").split("\n"):
        if not satir:
            continue
        ozet, yol = satir[:64], satir[66:]
        dosya = tarih_klasoru / yol
        assert dosya.is_file(), f"SHA256SUMS dosyasi yok: {yol}"
        assert hashlib.sha256(dosya.read_bytes()).hexdigest() == ozet, f"ozet tutmuyor: {yol}"
        sayi += 1
    assert sayi > 0


def _qpc1_oku(tarih_klasoru: Path) -> tuple[dict[Konum, dict[int, str]], int]:
    """QPC1 sayfalarindan kelimeler; yalniz rakamdan olusan 'ayet sonu' girdileri ayri sayilir."""
    kelimeler: dict[Konum, dict[int, str]] = {}
    ayet_sonu = 0
    for yol in sorted((tarih_klasoru / "mushaf" / "QPC1").glob("page-*.json")):
        sayfa = json.loads(yol.read_bytes().decode("utf-8"))
        for satir in sayfa["lines"]:
            for kelime in satir.get("words", []):
                metin = kelime["word"]
                if _yalniz_hint(metin):
                    ayet_sonu += 1
                    continue
                sure, ayet, no = (int(x) for x in kelime["location"].split(":"))
                ayetin = kelimeler.setdefault((sure, ayet), {})
                assert no not in ayetin, f"QPC1'de yinelenen konum: {sure}:{ayet}:{no}"
                ayetin[no] = "".join(h for h in metin if not _hint_mi(h))  # yapisik ayet numarasi
    return kelimeler, ayet_sonu


@pytest.fixture(scope="module")
def gercek() -> Gercek:
    veri_kok = _veri_kok()
    ayetler = _tanzil_ayetleri(veri_kok)
    klasor = _qpc1_klasoru(veri_kok)
    _sha256sums_dogrula(klasor)
    qpc1, ayet_sonu = _qpc1_oku(klasor)
    return Gercek(ayetler, qpc1, ayet_sonu)


def _bol(g: Gercek, sure: int, ayet: int) -> list[Kelime]:
    return kelimelere_bol(g.ayetler[(sure, ayet)], sure, ayet)


# --- sayilar ve konumlar -----------------------------------------------------------------------


def test_qpc1_yapisi_tutarli(gercek: Gercek) -> None:
    """QPC1 kaynagi: ayet kumesi Tanzil'inkiyle ayni, kelime numaralari 1'den kesintisiz."""
    assert set(gercek.qpc1) == set(gercek.ayetler)
    for (sure, ayet), kelimeler in gercek.qpc1.items():
        assert sorted(kelimeler) == list(range(1, len(kelimeler) + 1)), f"{sure}:{ayet}"
    assert gercek.qpc1_ayet_sonu > 0


def test_her_ayetin_kelime_sayisi_qpc1_ile_ayni(gercek: Gercek) -> None:
    farkli = [
        f"q:{s}:{a}"
        for (s, a) in gercek.ayetler
        if len(_bol(gercek, s, a)) != len(gercek.qpc1[(s, a)])
    ]
    assert farkli == []


def test_toplam_kelime_sayisi_qpc1_ile_ayni(gercek: Gercek) -> None:
    toplam = sum(len(_bol(gercek, s, a)) for s, a in gercek.ayetler)
    assert toplam == sum(len(k) for k in gercek.qpc1.values())
    assert toplam > len(gercek.ayetler)


def test_birlestirme_listesi_tam_olarak_qpc1_ile_farkli_cikan_ayetlerdir(
    gercek: Gercek, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Birlestirme kapaliyken sayisi QPC1'den farkli olan ayetler == liste (ne eksik ne fazla)."""
    monkeypatch.setattr(quran, "BIRLESTIRME", {})
    farkli = {
        (s, a): len(_bol(gercek, s, a)) - len(gercek.qpc1[(s, a)])
        for (s, a) in gercek.ayetler
        if len(_bol(gercek, s, a)) != len(gercek.qpc1[(s, a)])
    }
    assert set(farkli) == set(BIRLESTIRME)
    assert set(farkli.values()) == {
        1
    }  # her birinde Tanzil bir belirtec fazla: iki belirtec = 1 kelime


# --- harf iskeleti -------------------------------------------------------------------------------


def test_kelime_kelime_harf_iskeleti_qpc1_ile_ayni(gercek: Gercek) -> None:
    """Tanzil kelimesinin iskeleti QPC1 kelimesinin iskeletiyle ayni (yazim istisnalari haric).

    Bu sinama birlestirme listesindeki SIRA tanimini da dogrular: yanlis siradaki bir birlestirme
    sonraki kelimeleri kaydirir ve iskeletler tutmaz.
    """
    farkli: set[tuple[int, int, int]] = set()
    for (sure, ayet), metin in gercek.ayetler.items():
        for kelime in kelimelere_bol(metin, sure, ayet):
            tanzil_iskelet = _iskelet(metin[kelime.char_start : kelime.char_end])
            qpc1_iskelet = _iskelet(gercek.qpc1[(sure, ayet)][kelime.word])
            assert tanzil_iskelet != "", f"q:{sure}:{ayet}:{kelime.word}"
            if tanzil_iskelet != qpc1_iskelet:
                farkli.add((sure, ayet, kelime.word))
    assert farkli == ISKELET_ISTISNALARI


@pytest.mark.parametrize(("ayet", "sira"), sorted(BIRLESTIRME.items()))
def test_birlesen_kelime_iki_belirtecin_iskeletidir(
    gercek: Gercek, ayet: tuple[int, int], sira: int
) -> None:
    """Birlesen kelime QPC1'deki tek kelimeyle ayni iskelete sahiptir; ayrik belirtecler degil."""
    sure, no = ayet
    metin = gercek.ayetler[ayet]
    birlesen = _bol(gercek, sure, no)[sira - 1]
    parca = metin[birlesen.char_start : birlesen.char_end]
    belirtecler = parca.split(" ")
    assert len(belirtecler) == 2
    qpc1_iskelet = _iskelet(gercek.qpc1[ayet][sira])
    assert _iskelet(parca) == qpc1_iskelet
    assert all(_iskelet(b) != qpc1_iskelet for b in belirtecler)


def test_besmele_onekleri_1_1in_kelimeleriyle_iskelet_olarak_ayni(gercek: Gercek) -> None:
    """Sure 2-114 (9 haric) 1. ayetlerinde ilk dort belirtec 1:1'in kelimeleridir (iskelet).

    Iskelet esitligine bakilir, bayt esitligine degil: A10 gozlemi, 95. ve 97. surelerde Uthmani'de
    besmele oneki baytca farklidir (yazim) ama iskeleti aynidir.
    """
    ilk = gercek.ayetler[(1, 1)]
    referans = [_iskelet(ilk[k.char_start : k.char_end]) for k in _bol(gercek, 1, 1)]
    assert len(referans) == BESMELE_BELIRTEC
    kontrol = [s for (s, a) in gercek.ayetler if a == 1 and besmele_onekli_mi(s, a)]
    assert kontrol, "besmele onekli sure bulunamadi"
    assert {95, 97} <= set(kontrol)
    for sure in kontrol:
        onek = gercek.ayetler[(sure, 1)].split(" ")[:BESMELE_BELIRTEC]
        assert [_iskelet(b) for b in onek] == referans, f"q:{sure}:1"


def test_besmele_onekli_ayetlerde_ilk_kelime_besmeleden_sonraki_belirectir(gercek: Gercek) -> None:
    for (sure, ayet), metin in gercek.ayetler.items():
        if not besmele_onekli_mi(sure, ayet):
            continue
        belirtecler = metin.split(" ")
        ilk_kelime = _bol(gercek, sure, ayet)[0]
        assert ilk_kelime.char_start == len(" ".join(belirtecler[:BESMELE_BELIRTEC])) + 1


# --- ofsetler ------------------------------------------------------------------------------------


def test_dilim_ortusme_numara_ve_kelime_kapsami(gercek: Gercek) -> None:
    for (sure, ayet), metin in gercek.ayetler.items():
        kelimeler = kelimelere_bol(metin, sure, ayet)
        assert kelimeler, f"q:{sure}:{ayet}: kelime yok"
        assert [k.word for k in kelimeler] == list(range(1, len(kelimeler) + 1))
        onceki_son = 0
        for k in kelimeler:
            assert onceki_son <= k.char_start < k.char_end <= len(metin), (
                f"q:{sure}:{ayet}:{k.word}"
            )
            onceki_son = k.char_end
        # Birlesen kelime disinda hicbir kelimede bosluk yoktur; birlesende tam bir bosluk vardir.
        bosluklu = [k.word for k in kelimeler if " " in metin[k.char_start : k.char_end]]
        assert len(bosluklu) == (1 if (sure, ayet) in BIRLESTIRME else 0), f"q:{sure}:{ayet}"


def test_bolme_metni_degistirmez_nfc_olmayan_dilim_kalir(gercek: Gercek) -> None:
    """Dilim ayet metninin birebir parcasidir: NFC uygulanmaz (NFC olmayan kelime kalir)."""
    nfc_degil = [
        (sure, ayet, k.word)
        for (sure, ayet), metin in gercek.ayetler.items()
        for k in kelimelere_bol(metin, sure, ayet)
        if not unicodedata.is_normalized("NFC", metin[k.char_start : k.char_end])
    ]
    assert nfc_degil
