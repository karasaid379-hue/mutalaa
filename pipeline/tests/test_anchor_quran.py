"""`anchor/quran.py`: ayet metnini kelimelere bolme (A11.2, K-43 madde 1; SENTETIK metin).

Butun metinler "Deneme ..." biciminde sentetiktir; durak isaretleri ve ozel karakterler `chr()`
ile kurulur. Gercek Kur'an metni hafizadan yazilmaz; gercek metinle sinama
`test_kelime_gercek.py` (veri yoksa atlanir) ve `test_anchor_tanzil.py` parcalaridadir.
"""

import unicodedata
from itertools import pairwise

import pytest

from mutalaa_pipeline.anchor import quran
from mutalaa_pipeline.anchor.quran import (
    BESMELE_BELIRTEC,
    BESMELESIZ_SURELER,
    BIRLESTIRME,
    SURE_SAYISI,
    Kelime,
    KelimeBolmeHatasi,
    besmele_onekli_mi,
    durak_belirteci_mi,
    kelimelere_bol,
)

DURAK_ILK, DURAK_SON = chr(0x06D6), chr(0x06ED)
DURAK_ONCESI, DURAK_SONRASI = chr(0x06D5), chr(0x06EE)


def belirtecler(adet: int, onek: str = "Deneme") -> list[str]:
    return [f"{onek}{i}" for i in range(1, adet + 1)]


def metin_kur(*parcalar: str) -> str:
    return " ".join(parcalar)


def dilimler(metin: str, kelimeler: list[Kelime]) -> list[str]:
    return [metin[k.char_start : k.char_end] for k in kelimeler]


# --- bosluk bolme ve ofsetler ------------------------------------------------------------------


def test_bosluk_bolme_numara_ve_yari_acik_aralik() -> None:
    metin = "a bb ccc"
    sonuc = kelimelere_bol(metin, 3, 5)
    assert sonuc == [Kelime(1, 0, 1), Kelime(2, 2, 4), Kelime(3, 5, 8)]
    assert dilimler(metin, sonuc) == ["a", "bb", "ccc"]
    assert [k.char_end - k.char_start for k in sonuc] == [1, 2, 3]


def test_sonuc_bir_demettir_word_start_end_siraliydi() -> None:
    assert tuple(kelimelere_bol("a b", 3, 5)[0]) == (1, 0, 1)


def test_tek_kelimeli_ayet() -> None:
    assert kelimelere_bol("Deneme", 3, 5) == [Kelime(1, 0, 6)]


def test_ofsetler_kod_noktasidir_utf16_birimi_degil() -> None:
    """BMP disi bir karakter (U+1D400) 2 UTF-16 birimi ama 1 kod noktasidir."""
    buyuk_a = chr(0x1D400)
    metin = f"{buyuk_a}{buyuk_a} kelime"
    sonuc = kelimelere_bol(metin, 3, 5)
    assert sonuc == [Kelime(1, 0, 2), Kelime(2, 3, 9)]
    assert len(metin.encode("utf-16-le")) // 2 > len(metin)  # UTF-16 birimi daha cok
    assert dilimler(metin, sonuc) == [f"{buyuk_a}{buyuk_a}", "kelime"]


def test_metin_donusturulmez_nfc_olmayan_dizi_aynen_dilimlenir() -> None:
    """Kaynak NFC degilse dilim de NFC degildir: bolme yalniz aralik hesaplar (K-26)."""
    nfc_degil = "e" + chr(0x0301) + "x"  # NFC'de tek karakter olurdu
    metin = f"{nfc_degil} {nfc_degil}"
    assert unicodedata.normalize("NFC", metin) != metin
    sonuc = kelimelere_bol(metin, 3, 5)
    assert dilimler(metin, sonuc) == [nfc_degil, nfc_degil]
    assert sonuc[1].char_start == len(nfc_degil) + 1


def test_numaralar_1den_kesintisiz_araliklar_ortusmez() -> None:
    metin = " ".join(belirtecler(25))
    sonuc = kelimelere_bol(metin, 5, 7)
    assert [k.word for k in sonuc] == list(range(1, 26))
    for onceki, sonraki in pairwise(sonuc):
        assert onceki.char_end + 1 == sonraki.char_start  # tek bosluk aradadir
    assert all(k.char_start < k.char_end for k in sonuc)
    assert dilimler(metin, sonuc) == metin.split(" ")


# --- durak isareti belirteci --------------------------------------------------------------------


def test_durak_belirteci_kelime_sayilmaz_numara_kaymaz() -> None:
    metin = metin_kur("aa", DURAK_ILK, "bb", DURAK_SON + DURAK_ILK, "cc")
    sonuc = kelimelere_bol(metin, 3, 5)
    assert dilimler(metin, sonuc) == ["aa", "bb", "cc"]
    assert [k.word for k in sonuc] == [1, 2, 3]


@pytest.mark.parametrize(
    ("belirtec", "durak"),
    [
        (DURAK_ILK, True),
        (DURAK_SON, True),
        (DURAK_ILK + DURAK_SON, True),
        (chr(0x06DE), True),  # aralik icinde
        (DURAK_ONCESI, False),  # aralik disi
        (DURAK_SONRASI, False),
        ("a" + DURAK_ILK, False),  # harf + isaret kelimedir
        (DURAK_ILK + "a", False),
        ("", False),
    ],
)
def test_durak_belirteci_siniri(belirtec: str, durak: bool) -> None:
    assert durak_belirteci_mi(belirtec) is durak


def test_aralik_siniri_disindaki_tek_karakter_kelimedir() -> None:
    metin = metin_kur("aa", DURAK_ONCESI, DURAK_SONRASI)
    assert len(kelimelere_bol(metin, 3, 5)) == 3


def test_ayet_sonundaki_durak_belirteci_de_atilir() -> None:
    metin = metin_kur("aa", "bb", DURAK_ILK)
    assert dilimler(metin, kelimelere_bol(metin, 3, 5)) == ["aa", "bb"]


# --- besmele oneki -------------------------------------------------------------------------------


def test_besmele_onekli_sureler_1_ve_9_haric_2_den_114e() -> None:
    onekliler = [s for s in range(1, SURE_SAYISI + 1) if besmele_onekli_mi(s, 1)]
    assert onekliler == [s for s in range(2, SURE_SAYISI + 1) if s not in BESMELESIZ_SURELER]
    assert {1, 9} == BESMELESIZ_SURELER
    assert len(onekliler) == SURE_SAYISI - len(BESMELESIZ_SURELER)
    assert not any(besmele_onekli_mi(s, 2) for s in range(1, SURE_SAYISI + 1))  # yalniz 1. ayet


def test_besmele_dort_belirteci_numara_almaz() -> None:
    besmele = belirtecler(BESMELE_BELIRTEC, "Besmele")
    govde = belirtecler(3)
    metin = metin_kur(*besmele, *govde)
    sonuc = kelimelere_bol(metin, 2, 1)
    assert dilimler(metin, sonuc) == govde
    assert [k.word for k in sonuc] == [1, 2, 3]
    assert sonuc[0].char_start == len(metin_kur(*besmele)) + 1  # ofset ayet metnine goredir


@pytest.mark.parametrize("sure", [1, 9])
def test_sure_1_ve_9_un_ilk_ayetinde_ilk_dort_belirtec_de_sayilir(sure: int) -> None:
    metin = " ".join(belirtecler(BESMELE_BELIRTEC + 3))
    assert len(kelimelere_bol(metin, sure, 1)) == BESMELE_BELIRTEC + 3


def test_besmele_yalniz_ilk_ayette_uygulanir() -> None:
    metin = " ".join(belirtecler(BESMELE_BELIRTEC + 3))
    assert len(kelimelere_bol(metin, 2, 2)) == BESMELE_BELIRTEC + 3
    assert len(kelimelere_bol(metin, 2, 1)) == 3


def test_besmele_onceki_belirteci_durak_olsa_da_ilk_dort_belirtec_atilir() -> None:
    """Kural belirtec sayar: ilk dort belirtec (durak dahil) atilir, sonra durak suzulur."""
    metin = metin_kur("b1", DURAK_ILK, "b3", "b4", "k1", DURAK_ILK, "k2")
    assert dilimler(metin, kelimelere_bol(metin, 2, 1)) == ["k1", "k2"]


def test_besmele_ayetinde_kelime_kalmazsa_hata() -> None:
    for adet in range(BESMELE_BELIRTEC + 1):
        with pytest.raises(KelimeBolmeHatasi):
            kelimelere_bol(" ".join(belirtecler(adet)) if adet else "a", 2, 1)
    with pytest.raises(KelimeBolmeHatasi):  # besmeleden sonra yalniz durak isareti kalir
        kelimelere_bol(metin_kur(*belirtecler(BESMELE_BELIRTEC), DURAK_ILK), 2, 1)


# --- birlestirme listesi ------------------------------------------------------------------------


def test_birlestirme_listesi_tam_dort_ayet_ve_gecerli_siralar() -> None:
    assert len(BIRLESTIRME) == 4
    assert all(sira >= 1 for sira in BIRLESTIRME.values())
    assert all(1 <= s <= SURE_SAYISI and a >= 1 for s, a in BIRLESTIRME)


@pytest.mark.parametrize(("ayet", "sira"), sorted(BIRLESTIRME.items()))
def test_birlestirme_iki_belirteci_tek_kelime_yapar(ayet: tuple[int, int], sira: int) -> None:
    sure, no = ayet
    onek = belirtecler(BESMELE_BELIRTEC, "Besmele") if besmele_onekli_mi(sure, no) else []
    govde = belirtecler(sira + 3)
    metin = metin_kur(*onek, *govde)
    sonuc = kelimelere_bol(metin, sure, no)
    assert len(sonuc) == len(govde) - 1
    assert [k.word for k in sonuc] == list(range(1, len(govde)))
    birlesen = sonuc[sira - 1]
    assert metin[birlesen.char_start : birlesen.char_end] == f"{govde[sira - 1]} {govde[sira]}"
    assert dilimler(metin, sonuc[: sira - 1]) == govde[: sira - 1]
    assert dilimler(metin, sonuc[sira:]) == govde[sira + 1 :]


def test_birlestirme_listede_olmayan_ayeti_birlestirmez() -> None:
    metin = " ".join(belirtecler(12))
    kural_disi = next(
        (s, a) for s in range(3, SURE_SAYISI + 1) for a in (2, 3) if (s, a) not in BIRLESTIRME
    )
    assert len(kelimelere_bol(metin, *kural_disi)) == 12


def test_birlestirme_sirasi_besmele_ve_durak_atildiktan_sonraki_kelime_belirteclerindedir(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Sira 2: durak belirteci sayilmaz, 2. ve 3. KELIME belirteci birlesir (aralarindaki durak da
    araliga girer: aralik iki belirteci ve arasini kapsar)."""
    monkeypatch.setitem(BIRLESTIRME, (3, 5), 2)
    metin = metin_kur("k1", DURAK_ILK, "k2", DURAK_SON, "k3", "k4")
    sonuc = kelimelere_bol(metin, 3, 5)
    assert [k.word for k in sonuc] == [1, 2, 3]
    assert dilimler(metin, sonuc)[0] == "k1"
    assert dilimler(metin, sonuc)[1] == metin_kur("k2", DURAK_SON, "k3")
    assert dilimler(metin, sonuc)[2] == "k4"


def test_birlestirme_icin_yeterli_belirtec_yoksa_hata(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(BIRLESTIRME, (3, 5), 3)
    with pytest.raises(KelimeBolmeHatasi):
        kelimelere_bol("k1 k2 k3", 3, 5)  # 3. ve 4. belirtec yok
    assert len(kelimelere_bol("k1 k2 k3 k4", 3, 5)) == 3


def test_birlestirme_listesi_modul_sabitidir_ve_bolmeye_bagli(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(quran, "BIRLESTIRME", {})
    sure, ayet = next(iter(BIRLESTIRME))
    metin = " ".join(belirtecler(12))
    assert len(kelimelere_bol(metin, sure, ayet)) == 12


# --- kaynak bozuklugu ve gecersiz girdi ---------------------------------------------------------


def test_bos_belirtecler_atlanir_ofsetler_ayet_metnine_gore_kalir() -> None:
    metin = " a  bb "
    sonuc = kelimelere_bol(metin, 3, 5)
    assert sonuc == [Kelime(1, 1, 2), Kelime(2, 4, 6)]
    assert dilimler(metin, sonuc) == ["a", "bb"]


def test_besmele_bos_belirtecleri_saymaz() -> None:
    metin = "  b1 b2  b3 b4 k1 "
    assert dilimler(metin, kelimelere_bol(metin, 2, 1)) == ["k1"]


@pytest.mark.parametrize("metin", ["", " ", "   "])
def test_belirtecsiz_metin_hata(metin: str) -> None:
    with pytest.raises(KelimeBolmeHatasi):
        kelimelere_bol(metin, 3, 5)


@pytest.mark.parametrize(("sure", "ayet"), [(0, 1), (SURE_SAYISI + 1, 1), (3, 0), (3, -1)])
def test_gecersiz_sure_ya_da_ayet_hata(sure: int, ayet: int) -> None:
    with pytest.raises(KelimeBolmeHatasi):
        kelimelere_bol("a b", sure, ayet)


def test_yalniz_durak_belirtecinden_olusan_ayet_hata() -> None:
    with pytest.raises(KelimeBolmeHatasi):
        kelimelere_bol(metin_kur(DURAK_ILK, DURAK_SON), 3, 5)


def test_hata_iletisi_metin_tasimaz() -> None:
    gizli = "GIZLI-DENEME-METNI"
    with pytest.raises(KelimeBolmeHatasi) as hata:
        kelimelere_bol(gizli, 0, 5)
    assert gizli not in str(hata.value)
    assert str(hata.value).isascii()


def test_kelime_bolme_hatasi_value_error_alt_sinifidir() -> None:
    assert issubclass(KelimeBolmeHatasi, ValueError)
