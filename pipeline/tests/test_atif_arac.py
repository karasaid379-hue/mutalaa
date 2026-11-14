"""Atif araci: guven hesabi, Kur'an metni (bellekte) ve `quran-toolkit` sarmalayicisi (A20.7b).

SENTETIK veri: "ayet"ler Arap alfabesi harflerinden uydurulmus kelimelerdir; gercek bir ayet
degildir. Arac gercek `quran-toolkit` paketidir ama yalniz bu uydurma jeton listesiyle kosar.
"""

import re
from pathlib import Path

import pytest

from mutalaa_pipeline.enrich import arac_sarmalayicilari, atif_guven, citations, kuran_metni
from mutalaa_pipeline.enrich.arac_sarmalayicilari import ToolkitSarmalayici
from mutalaa_pipeline.enrich.kuran_metni import KuranMetni, ayetleri_kur, basit_kelimeler
from mutalaa_pipeline.export.ortak import GirdiHatasi

HARFLER = "بتثجحخدذرزسشصضطظعغفقلمنه"


def kelime(i: int) -> str:
    """Her `i` icin ayri, normalize sonrasi da ayri uc harfli sentetik kelime."""
    return HARFLER[i % 24] + HARFLER[(i // 24) % 24] + HARFLER[(i * 7 + 3) % 24]


def cumle(*sira: int) -> str:
    return " ".join(kelime(i) for i in sira)


def sentetik_kuran() -> KuranMetni:
    """Sure 1: uc ayet; sure 9: iki ayet (ikincisi Simple Clean'de bir kelime fazla: hizasiz)."""
    uthmani = [
        (1, 1, cumle(0, 1, 2, 3, 4, 5)),
        (1, 2, cumle(6, 7, 8, 9, 10)),
        (1, 3, cumle(11, 12, 13, 14, 15, 16)),
        (9, 1, cumle(0, 1, 2, 3, 20, 21)),
        (9, 2, cumle(30, 31, 32, 33, 34)),
    ]
    basit = list(uthmani)
    basit[4] = (9, 2, cumle(30, 31, 32, 33, 34, 35))
    return KuranMetni(ayetleri_kur(uthmani, basit), (), {})


@pytest.fixture(scope="module")
def arac() -> ToolkitSarmalayici:
    return ToolkitSarmalayici(sentetik_kuran().ayetler)


# --- guven hesabi --------------------------------------------------------------------------


def test_puan_degerleri_tam_sayi() -> None:
    p = atif_guven.iktibas_puani(4, 4)
    assert (p.skor, p.guven, p.kapsama) == (571, 600, 1000)
    p = atif_guven.iktibas_puani(7, 7)
    assert (p.skor, p.guven, p.kapsama) == (1000, 900, 1000)
    p = atif_guven.iktibas_puani(4, 21)
    assert (p.skor, p.guven, p.kapsama) == (340, 357, 190)
    for deger in (p.skor, p.guven, p.kapsama):
        assert type(deger) is int


def test_puan_tekrar_kelime_ve_kapsama_etkisi() -> None:
    temel = atif_guven.iktibas_puani(5, 10)
    assert atif_guven.iktibas_puani(5, 10, 2).guven < temel.guven
    assert atif_guven.iktibas_puani(5, 10, 2).skor < temel.skor
    assert atif_guven.iktibas_puani(8, 10).guven > temel.guven  # daha uzun dizi
    assert atif_guven.iktibas_puani(5, 20).guven < temel.guven  # daha dusuk kapsama
    # kelime sayisi 7'de doyar; kapsama sabitken guven artmaz
    assert atif_guven.iktibas_puani(14, 14).guven == atif_guven.iktibas_puani(7, 7).guven
    # n > toplam: kapsama 1000'e kirpilir
    assert atif_guven.iktibas_puani(9, 5).kapsama == 1000
    for n in range(1, 40):
        for toplam in (1, 4, 17, 286):
            for f in (1, 3, 18):
                p = atif_guven.iktibas_puani(n, toplam, f)
                assert 0 <= p.skor <= 1000 and 0 <= p.guven <= 1000


def test_puan_gecersiz_girdi() -> None:
    for kotu in ((0, 4, 1), (4, 0, 1), (4, 4, 0)):
        with pytest.raises(ValueError):
            atif_guven.iktibas_puani(*kotu)
    assert atif_guven.binde(0.95) == 950
    assert atif_guven.binde(0.85) == 850


# --- Kur'an metni (bellekte) ---------------------------------------------------------------


def test_basit_kelimeler_besmele_ve_durak_isareti() -> None:
    durak = "ۖ"
    # sure 2 ayet 1: ilk dort belirtec besmele oneki (K-43); sure 1 ayet 1'de yok
    assert basit_kelimeler(2, 1, f"{cumle(0, 1, 2, 3)} {kelime(9)} {durak}") == (kelime(9),)
    assert len(basit_kelimeler(1, 1, f"{cumle(0, 1, 2, 3)} {durak}")) == 4
    assert basit_kelimeler(9, 1, f"{kelime(1)}  {kelime(2)}") == (kelime(1), kelime(2))


def test_ayetleri_kur_hizali_ve_hizasiz() -> None:
    kuran = sentetik_kuran()
    assert kuran.kelime_sayisi(1, 1) == 6
    assert kuran.ayet(1, 1).hizali  # type: ignore[union-attr]
    assert kuran.ayet(9, 2).hizali is False  # type: ignore[union-attr]
    assert kuran.ayet(9, 2).kelime == 5  # type: ignore[union-attr]
    assert kuran.hizasiz == 1
    assert kuran.ayet(2, 1) is None


def test_ayet_dosyalari_uyumsuzsa_hata() -> None:
    with pytest.raises(GirdiHatasi):
        ayetleri_kur([(1, 1, cumle(0, 1))], [(1, 2, cumle(0, 1))])
    with pytest.raises(GirdiHatasi):
        ayetleri_kur([(1, 1, cumle(0, 1))], [])


def test_yukle_sentetik_dizinde_tarih_klasoru_yok_hatasi(tmp_path: Path) -> None:
    with pytest.raises(GirdiHatasi):
        kuran_metni.yukle(tmp_path)


# --- sarmalayici ---------------------------------------------------------------------------


def test_cok_ayetli_eslesme_konumlar_ve_ofsetler(arac: ToolkitSarmalayici) -> None:
    onek = cumle(100, 101, 102) + " "
    dizi = onek + cumle(3, 4, 5, 6, 7) + " " + cumle(103)
    sonuc = arac.tespit_et(dizi)
    assert len(sonuc) == 1
    e = sonuc[0]
    assert dizi[e.bas : e.son] == cumle(3, 4, 5, 6, 7)  # kod noktasi, yari acik
    assert e.kelime_sayisi == 5
    assert e.ayetler == ((1, 1), (1, 2))
    assert [(p.sure, p.ayet, p.ilk, p.son, p.sayi) for p in e.parcalar] == [
        (1, 1, 4, 6, 3),  # kelime 4-6 (1 tabanli)
        (1, 2, 1, 2, 2),
    ]
    assert e.tekrar == 1
    assert e.skor is None  # arac skor vermez


def test_tekrar_kalip_dizi(arac: ToolkitSarmalayici) -> None:
    sonuc = arac.tespit_et(cumle(0, 1, 2, 3))  # hem 1:1 hem 9:1 basinda
    assert len(sonuc) == 1
    assert sonuc[0].tekrar == 2
    assert sonuc[0].ayetler == ((1, 1),)  # arac ayni uzunlukta en erken yeri secer


def test_en_az_dort_kelime(arac: ToolkitSarmalayici) -> None:
    assert arac.tespit_et(cumle(11, 12, 13)) == []
    assert len(arac.tespit_et(cumle(11, 12, 13, 14))) == 1


def test_tam_ayet_ve_hizasiz_ayet(arac: ToolkitSarmalayici) -> None:
    tam = arac.tespit_et(cumle(11, 12, 13, 14, 15, 16))[0]
    assert (tam.parcalar[0].ilk, tam.parcalar[0].son) == (1, 6)
    hizasiz = arac.tespit_et(cumle(30, 31, 32, 33))[0]
    assert hizasiz.ayetler == ((9, 2),)
    assert (hizasiz.parcalar[0].ilk, hizasiz.parcalar[0].son) == (0, 0)  # konum bilinmiyor


def test_bos_ve_eslesmeyen_dizi(arac: ToolkitSarmalayici) -> None:
    assert arac.tespit_et("") == []
    assert arac.tespit_et(cumle(200, 201, 202, 203, 204)) == []


def test_arac_kimligi_ve_surumu() -> None:
    assert arac_sarmalayicilari.ARAC_ADI == "quran-toolkit"
    assert arac_sarmalayicilari.ARAC_SURUMU == "0.1.0"
    assert arac_sarmalayicilari.paket_surumu() == "0.1.0"


# --- kaybeden sarmalayicilar silindi -------------------------------------------------------

KAYNAK_KLASORU = Path(__file__).resolve().parents[1] / "src" / "mutalaa_pipeline"
YASAK = re.compile(
    r"^\s*(?:import|from)\s+(?:ijaza|quran_detector)\b|import_module\(\s*['\"](?:ijaza|quran_detector)"
    r"|IjazaSarmalayici|DetectorSarmalayici",
    re.MULTILINE,
)


def test_kaybeden_sarmalayicilar_silindi() -> None:
    assert not hasattr(arac_sarmalayicilari, "IjazaSarmalayici")
    assert not hasattr(arac_sarmalayicilari, "DetectorSarmalayici")
    bulunan = [
        str(yol.relative_to(KAYNAK_KLASORU))
        for yol in KAYNAK_KLASORU.rglob("*.py")
        if YASAK.search(yol.read_text(encoding="utf-8"))
    ]
    assert bulunan == []
    pyproject = (KAYNAK_KLASORU.parents[1] / "pyproject.toml").read_text(encoding="utf-8")
    assert "quran-toolkit==0.1.0" in pyproject
    assert "ijaza" not in pyproject
    assert "quran-detector" not in pyproject


def test_sarmalayici_citations_arayuzune_uyar(arac: ToolkitSarmalayici) -> None:
    tespitler = citations.birimden_tespitler(
        "rn:deneme-kitap:p1",
        f"Deneme paragrafi 1 {cumle(3, 4, 5, 6, 7)} sonu.",
        [{"t": "ar", "s": 19, "e": 19 + len(cumle(3, 4, 5, 6, 7)), "tur": "blok"}],
        tespitci=arac,
        ayet_kelime=lambda s, a: sentetik_kuran().kelime_sayisi(s, a),
    )
    assert [(t.sure, t.ayet, t.dst_bas, t.dst_son) for t in tespitler] == [
        (1, 1, 4, 7),
        (1, 2, 1, 3),
    ]
    assert all(t.ayrintilar["skor_yok"] is True for t in tespitler)
    assert tespitler[0].ayrintilar["kapsama"] == 454  # 5 / (6 + 5)
