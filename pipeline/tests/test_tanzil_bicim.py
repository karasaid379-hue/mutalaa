"""`ingest.tanzil_bicim`: Tanzil dosya bicimi, kati ayristirma ve yeniden kurma (K-39 madde 7).

Fiksturler gercek Uthmani ve Simple Clean dosyalarindan betikle kesilmis parcalardir
(`tests/fixtures/tanzil/KAYNAK.txt`): okuma sirasinin 1|1'den baslayan 40 ayet satiri + dosyanin
tam bildirim blogu. Bozuk kopyalar parcadan bayt duzeyinde kodla uretilir; eklenen satirlar
SENTETIK "Deneme ..." metnidir. Kur'an metni testlerde hafizadan yazilmaz.
"""

import hashlib
import json
import random
import re
import unicodedata
from pathlib import Path

import pytest
from tanzil_yardimci import (
    BASLIK_TURU,
    FIKSTUR,
    PARCA_AYET,
    PARCA_BILDIRIM_SATIR,
    PARCA_CAPALAR,
    VARYANTLAR,
    ayet_bitisi,
    parca_oku,
)

from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.ingest import tanzil_bicim as bicim

degismezlik = pytest.mark.degismezlik

BASLIK_SATIRI = b"# PLEASE DO NOT REMOVE OR CHANGE THIS COPYRIGHT BLOCK"


def satirlar_al(veri: bytes) -> list[bytes]:
    """LF ile boler; son LF'den sonraki bos parca atilir."""
    return veri.split(b"\n")[:-1]


def birlestir(satirlar: list[bytes]) -> bytes:
    return b"".join(s + b"\n" for s in satirlar)


@pytest.fixture(params=VARYANTLAR)
def varyant(request: pytest.FixtureRequest) -> str:
    return str(request.param)


# --- iyi bicimli parca ---------------------------------------------------------------------


def test_parca_dosyalari_kaynak_kaydiyla_ayni(varyant: str) -> None:
    """KAYNAK.txt'deki ozet, git/editor donusumu olmadigini gosterir (bayt butunlugu)."""
    kaynak = (FIKSTUR / "KAYNAK.txt").read_text(encoding="utf-8")
    kayitlar = dict(re.findall(r"([a-z-]+-parca\.txt) +[0-9]+ bayt +sha256 ([0-9a-f]{64})", kaynak))
    assert set(kayitlar) == {f"{v}-parca.txt" for v in VARYANTLAR}
    veri = parca_oku(varyant)
    assert hashlib.sha256(veri).hexdigest() == kayitlar[f"{varyant}-parca.txt"]


def test_parca_ayet_sayisi_sirasi_ve_duzeni(varyant: str) -> None:
    veri = parca_oku(varyant)
    ayrisma = bicim.ayristir(veri, tam=False)
    assert len(ayrisma.ayetler) == PARCA_AYET
    assert [a.capa for a in ayrisma.ayetler] == PARCA_CAPALAR
    assert [a.satir for a in ayrisma.ayetler] == list(range(1, PARCA_AYET + 1))
    bitis = ayet_bitisi(veri)
    duzen = ayrisma.duzen
    assert duzen.konum == "son"
    assert duzen.son_lf is True
    assert duzen.toplam_bayt == len(veri)
    assert duzen.ayet_satir == (1, PARCA_AYET)
    assert duzen.ayet_bayt == (0, bitis)
    assert duzen.bildirim_satir == (PARCA_AYET + 1, PARCA_AYET + PARCA_BILDIRIM_SATIR)
    assert duzen.bildirim_bayt == (bitis, len(veri))
    assert duzen.bildirim_bos_satir == 2


@degismezlik
def test_metin_dilimi_bayt_esitligi(varyant: str) -> None:
    veri = parca_oku(varyant)
    ayrisma = bicim.ayristir(veri, tam=False)
    onceki_son = 0
    for ay in ayrisma.ayetler:
        assert veri[ay.bayt_bas : ay.bayt_son].decode("utf-8") == ay.metin
        assert veri[ay.satir_bas : ay.bayt_bas] == f"{ay.sure}|{ay.ayet}|".encode("ascii")
        assert veri[ay.bayt_son : ay.satir_son] == b"\n"
        assert ay.satir_bas == onceki_son  # satirlar bitisik, aralik yok
        assert "\n" not in ay.metin
        assert "\r" not in ay.metin
        onceki_son = ay.satir_son
    assert onceki_son == ayet_bitisi(veri)
    assert ayrisma.metin_baytlari == veri[:onceki_son]
    assert bicim.metin_baytlari(veri, tam=False) == ayrisma.metin_baytlari
    assert ayrisma.metin_sha256 == hashlib.sha256(veri[:onceki_son]).hexdigest()


@degismezlik
def test_metin_donusturulmez_nfc_uygulanmaz() -> None:
    """Uthmani parcasinda NFC olmayan ayetler var; metin yine de dosyanin aynen dilimidir."""
    veri = parca_oku("uthmani")
    ayrisma = bicim.ayristir(veri, tam=False)
    nfc_olmayan = [a for a in ayrisma.ayetler if unicodedata.normalize("NFC", a.metin) != a.metin]
    assert nfc_olmayan, "parca NFC olmayan ayet icermeli (NFC uygulanmadigini kanitlar)"
    for ay in nfc_olmayan:
        assert ay.metin.encode("utf-8") == veri[ay.bayt_bas : ay.bayt_son]


def test_bildirim_baytlari_ve_baslik(varyant: str) -> None:
    veri = parca_oku(varyant)
    ayrisma = bicim.ayristir(veri, tam=False)
    bildirim = ayrisma.bildirim
    assert bildirim == veri[ayet_bitisi(veri) :]
    assert bildirim.endswith(b"\n")
    satirlar = bildirim.split(b"\n")
    assert len(satirlar) == PARCA_BILDIRIM_SATIR + 1  # 30 satir + son LF'den sonraki bos parca
    assert satirlar[0] == satirlar[1] == b""
    assert satirlar[-1] == b""
    diyezli = satirlar[2:-1]
    assert len(diyezli) == 28
    assert all(s.startswith(b"#") for s in diyezli)
    assert diyezli[0] == BASLIK_SATIRI
    assert bicim.bildirim_basligi(bildirim) == (BASLIK_TURU[varyant], "1.1")
    assert ayrisma.bildirim_sha256 == hashlib.sha256(bildirim).hexdigest()


# --- yeniden kurma -------------------------------------------------------------------------


@degismezlik
def test_yeniden_kur_bayt_bayt_gidis_donus(varyant: str) -> None:
    veri = parca_oku(varyant)
    ayrisma = bicim.ayristir(veri, tam=False)
    birimler = [(a.capa, a.metin) for a in ayrisma.ayetler]
    assert bicim.yeniden_kur(birimler, ayrisma.bildirim, ayrisma.duzen) == veri
    # duzen manifest sozlugunden (JSON gidis-donusu) geri kurulsa da sonuc ayni
    duzen = bicim.Duzen.sozlukten(json.loads(json.dumps(ayrisma.duzen.sozluk())))
    assert duzen == ayrisma.duzen
    assert bicim.yeniden_kur(birimler, ayrisma.bildirim, duzen) == veri


def test_yeniden_kur_capa_hatalari() -> None:
    duzen = bicim.Duzen("son", True, 0, (1, 1), (0, 0), (2, 2), (0, 0), 0)
    with pytest.raises(GirdiHatasi, match="capa gecersiz"):
        bicim.yeniden_kur([("Q:1:1", "Deneme")], b"", duzen)
    for capa in ("q:1:1:2", "q:1:1:2-3", "q:1:1-2", "meal:elmalili:1:1"):
        with pytest.raises(GirdiHatasi, match="ayet capasi degil"):
            bicim.yeniden_kur([(capa, "Deneme")], b"", duzen)


def test_yeniden_kur_duzen_uyumsuzsa_durur() -> None:
    uyumsuz = bicim.Duzen("bas", True, 0, (1, 1), (0, 0), (2, 2), (0, 0), 0)
    with pytest.raises(GirdiHatasi, match="satir duzeni"):
        bicim.yeniden_kur([], b"", uyumsuz)
    sonsuz_lf_yok = bicim.Duzen("son", False, 0, (1, 1), (0, 0), (2, 2), (0, 0), 0)
    with pytest.raises(GirdiHatasi, match="satir duzeni"):
        bicim.yeniden_kur([], b"", sonsuz_lf_yok)


# --- bozuk kopyalar ------------------------------------------------------------------------


def vakalar(veri: bytes) -> dict[str, tuple[bytes, str]]:
    """Bayt duzeyinde bozulmus kopyalar: kimlik -> (bozuk veri, iletide beklenen parca)."""
    s = satirlar_al(veri)
    bitis = ayet_bitisi(veri)
    sentetik = b"Deneme tanimsiz satir"
    return {
        "cr": (veri.replace(b"\n", b"\r\n", 1), "CR (0x0D) var: ilk bayt"),
        "bom": (bicim.BOM + veri, "BOM var (bayt 0)"),
        "bos_dosya": (b"", "dosya bos"),
        "sonda_lf_yok": (veri[:-1], "dosya LF ile bitmiyor"),
        "tanimsiz_satir_ayetlerin_arasinda": (
            birlestir([*s[:5], sentetik, *s[5:]]),
            "satir 6: tanimsiz satir",
        ),
        "tanimsiz_satir_son_ayetten_sonra": (
            birlestir([*s[:40], sentetik, *s[40:]]),
            "satir 41: tanimsiz satir",
        ),
        "ayet_bolgesinde_bos_satir": (
            birlestir([*s[:5], b"", *s[5:]]),
            "satir 7: ayet bolgesi kesildi (ilk ayet olmayan satir 6)",
        ),
        "numara_atlamasi": (birlestir(s[:2] + s[3:]), "satir 3: sira disi numara"),
        "tekrar": (birlestir([*s[:5], s[4], *s[5:]]), "satir 6: sira disi numara"),
        "sure_atlamasi": (veri.replace(b"\n2|1|", b"\n3|1|", 1), "satir 8: sira disi numara"),
        "sure_geri_donusu": (veri.replace(b"\n2|1|", b"\n1|1|", 1), "satir 8: sira disi numara"),
        "bastaki_sifir_ortada": (
            veri.replace(b"\n1|3|", b"\n1|03|", 1),
            "satir 3: tanimsiz satir (ayet numarasi gecersiz",
        ),
        "bastaki_sifir_son_ayet": (
            veri.replace(b"\n2|33|", b"\n2|033|", 1),
            "satir 40: tanimsiz satir (ayet numarasi gecersiz",
        ),
        "bastaki_sifir_ilk_satir": (b"0" + veri, "ayet satiri yok"),
        "uc_haneden_uzun_numara": (
            veri.replace(b"\n1|3|", b"\n1|1000|", 1),
            "satir 3: tanimsiz satir (ayet numarasi gecersiz",
        ),
        "bos_metin": (birlestir([*s[:1], b"1|2|", *s[2:]]), "satir 2: bos metin"),
        "bildirimsiz": (veri[:bitis], "bildirim blogu yok"),
        "yalniz_bos_bildirim": (veri[:bitis] + b"\n\n", "bildirim blogu yok"),
        "bildirim_basta": (veri[bitis:] + veri[:bitis], "ayet satiri yok"),
        "yalniz_bildirim": (veri[bitis:], "ayet satiri yok"),
        "bildirimde_ayet_benzeri_satir": (
            veri + b"1|1|Deneme\n",
            "satir 71: ayet bolgesi kesildi (ilk ayet olmayan satir 41)",
        ),
        "bildirimde_tanimsiz_satir": (veri + sentetik + b"\n", "satir 71: tanimsiz satir"),
        "gecersiz_utf8_ayet": (
            veri.replace(b"\n1|2|", b"\n1|2|\xff", 1),
            "satir 2: gecersiz UTF-8 (bayt",
        ),
        "gecersiz_utf8_bildirim": (veri[:-1] + b"\xff\n", "bildirim blogu gecersiz UTF-8 (bayt"),
    }


VAKA_KIMLIKLERI = sorted(vakalar(parca_oku("uthmani")))


@pytest.mark.parametrize("kimlik", VAKA_KIMLIKLERI)
def test_bozuk_kopya_girdi_hatasi_verir_ve_icerik_sizdirmaz(varyant: str, kimlik: str) -> None:
    veri = parca_oku(varyant)
    bozuk, beklenen = vakalar(veri)[kimlik]
    assert bozuk != veri
    with pytest.raises(GirdiHatasi) as hata:
        bicim.ayristir(bozuk, tam=False)
    mesaj = str(hata.value)
    assert beklenen in mesaj
    assert mesaj.isascii()  # ayet ve bildirim icerigi ASCII disi; iletide yer almaz
    assert "Deneme" not in mesaj  # eklenen sentetik satir icerigi de sizmaz
    assert "PLEASE" not in mesaj
    for ay in bicim.ayristir(veri, tam=False).ayetler:
        assert ay.metin[:6] not in mesaj


def test_vaka_tablosu_her_bozulma_turunu_kapsar() -> None:
    """Gorevin sayacagi turler: 0x0D, BOM, tanimsiz satir, bos satir, atlama, tekrar, sifir, LF."""
    gerekli = {
        "cr",
        "bom",
        "tanimsiz_satir_ayetlerin_arasinda",
        "ayet_bolgesinde_bos_satir",
        "numara_atlamasi",
        "tekrar",
        "bastaki_sifir_ortada",
        "sonda_lf_yok",
        "bildirimsiz",
    }
    assert gerekli <= set(VAKA_KIMLIKLERI)


def test_tam_istenirse_parca_eksik_sayilir(varyant: str) -> None:
    with pytest.raises(GirdiHatasi) as hata:
        bicim.ayristir(parca_oku(varyant))
    assert str(hata.value) == "ayet sayisi eksik: beklenen 6236, bulunan 40"


def test_ayristir_rastgele_bozmada_ya_girdi_hatasi_ya_kayipsiz_gidis_donus(varyant: str) -> None:
    """Hicbir bozulma sessizce baytlari kaybedemez ya da baska turde istisna firlatamaz."""
    veri = parca_oku(varyant)
    rastgele = random.Random(20261102)
    gecenler = 0
    for _ in range(400):
        bozuk = bytearray(veri)
        konum = rastgele.randrange(len(bozuk))
        tur = rastgele.choice(("degistir", "ekle", "sil"))
        if tur == "degistir":
            bozuk[konum] = rastgele.randrange(256)
        elif tur == "ekle":
            bozuk.insert(konum, rastgele.randrange(256))
        else:
            del bozuk[konum]
        bozuk_bayt = bytes(bozuk)
        try:
            ayrisma = bicim.ayristir(bozuk_bayt, tam=False)
        except GirdiHatasi as hata:
            assert str(hata).isascii()
            continue
        gecenler += 1
        birimler = [(a.capa, a.metin) for a in ayrisma.ayetler]
        assert bicim.yeniden_kur(birimler, ayrisma.bildirim, ayrisma.duzen) == bozuk_bayt
    assert gecenler > 0  # metin icindeki gecerli degisiklikler ayristirilabilir kalir


# --- sentetik girdiler (gercek metin yok) --------------------------------------------------

SENTETIK = b"1|1|Deneme 1 1\n1|2|Deneme 1 2\n2|1|Deneme 2 1\n\n\n#  Deneme (C) 2007-2026\n#  son\n"


def test_sentetik_tam_ayristirma_ozel_sure_tablosuyla() -> None:
    ayrisma = bicim.ayristir(SENTETIK, (2, 1))
    assert [a.capa for a in ayrisma.ayetler] == ["q:1:1", "q:1:2", "q:2:1"]
    assert [a.metin for a in ayrisma.ayetler] == ["Deneme 1 1", "Deneme 1 2", "Deneme 2 1"]
    assert ayrisma.bildirim == b"\n\n#  Deneme (C) 2007-2026\n#  son\n"
    assert ayrisma.duzen.ayet_satir == (1, 3)
    assert ayrisma.duzen.bildirim_satir == (4, 7)
    assert ayrisma.duzen.bildirim_bos_satir == 2
    assert ayrisma.metin_baytlari == b"1|1|Deneme 1 1\n1|2|Deneme 1 2\n2|1|Deneme 2 1\n"


def test_sentetik_eksik_ve_fazla_ayet() -> None:
    eksik = SENTETIK.replace(b"2|1|Deneme 2 1\n", b"")
    with pytest.raises(GirdiHatasi, match="ayet sayisi eksik: beklenen 3, bulunan 2"):
        bicim.ayristir(eksik, (2, 1))
    fazla = SENTETIK.replace(b"\n\n\n", b"\n2|2|Deneme 2 2\n\n\n", 1)
    with pytest.raises(GirdiHatasi, match="satir 4: sira disi numara"):
        bicim.ayristir(fazla, (2, 1))
    assert bicim.ayristir(eksik, (2, 1), tam=False).duzen.ayet_satir == (1, 2)


def test_sonraki_okuma_sirasi() -> None:
    assert bicim.sonraki(1, 1, (2, 1)) == (1, 2)
    assert bicim.sonraki(1, 2, (2, 1)) == (2, 1)
    assert bicim.sonraki(2, 1, (2, 1)) is None
    assert bicim.sure_basina_toplam((2, 1)) == 3


def test_bildirim_bul_ilk_ayet_olmayan_satiri_verir() -> None:
    assert bicim.bildirim_bul([True, True, False, False]) == 2
    assert bicim.bildirim_bul([True, True]) == 2  # bildirim yok
    assert bicim.bildirim_bul([False, True]) == 0
    assert bicim.bildirim_bul([]) == 0


def test_bildirim_basligi_yalniz_bir_baslik_kabul_eder() -> None:
    assert bicim.bildirim_basligi(b"\n#  Tanzil Quran Text (Deneme Tur, Version 2.10)\n") == (
        "Deneme Tur",
        "2.10",
    )
    with pytest.raises(GirdiHatasi, match="eslesme sayisi 0"):
        bicim.bildirim_basligi(b"\n#  Baska baslik\n")
    iki = b"#  Tanzil Quran Text (A, Version 1)\n#  Tanzil Quran Text (B, Version 2)\n"
    with pytest.raises(GirdiHatasi, match="eslesme sayisi 2"):
        bicim.bildirim_basligi(iki)


def test_duzen_sozlukten_gecersiz_kayitlari_reddeder(varyant: str) -> None:
    gecerli = bicim.ayristir(parca_oku(varyant), tam=False).duzen.sozluk()

    def kopya(**degisim: object) -> dict[str, object]:
        return {**json.loads(json.dumps(gecerli)), **degisim}

    assert bicim.Duzen.sozlukten(kopya()).toplam_bayt == len(parca_oku(varyant))
    kisa_satir = kopya()
    siniflar = kisa_satir["siniflar"]
    assert isinstance(siniflar, list)
    siniflar[1]["satir"] = [1]
    bozuklar: list[dict[str, object]] = [
        kisa_satir,
        kopya(konum="bas"),
        kopya(son_lf=False),
        kopya(toplam_bayt="1"),
        kopya(toplam_bayt=True),
        kopya(siniflar="x"),
        kopya(siniflar=[1]),
        kopya(siniflar=[]),
        kopya(siniflar=[{"sinif": "ayet", "satir": [1, 2], "bayt": [0, 1]}]),
        {k: v for k, v in kopya().items() if k != "konum"},
    ]
    for bozuk in bozuklar:
        with pytest.raises(GirdiHatasi, match="satir duzeni kaydi gecersiz"):
            bicim.Duzen.sozlukten(bozuk)


def test_modulde_varsayim_isareti_kalmadi() -> None:
    kaynak = Path(bicim.__file__).read_text(encoding="utf-8")
    assert "VARSAYIM" not in kaynak
    assert "olculecek" not in kaynak
