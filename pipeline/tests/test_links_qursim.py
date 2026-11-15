"""QurSim CSV okuyucusu (A18.3, K-51 madde 12): SENTETIK dosya (`Verse` sutunlari yer tutucu)."""

from pathlib import Path

import pytest

from mutalaa_pipeline.enrich.baglantilar.qursim import qursim_oku
from mutalaa_pipeline.export.ortak import GirdiHatasi

AYETLER = {f"q:2:{i}": i - 1 for i in range(1, 11)}  # 10 sentetik ayet
BASLIK = ",ID,SS,SV,Verse1,TS,TV,Verse2,Label"
YER_TUTUCU = "SENTINEL-METIN-1"


def yaz(tmp_path: Path, *satirlar: str, baslik: str = BASLIK) -> Path:
    yol = tmp_path / "QurSim_filtered.csv"
    yol.write_bytes(("\n".join([baslik, *satirlar]) + "\n").encode("utf-8"))
    return yol


def satir(i: int, ss: object, sv: object, ts: object, tv: object, label: object) -> str:
    return f'{i},{i},{ss},{sv},"{YER_TUTUCU}, deneme",{ts},{tv},"Deneme metni 2",{label}'


def test_gecerli_ciftler_siralanir_ve_ham_label_saklanir(tmp_path: Path) -> None:
    yol = yaz(
        tmp_path,
        satir(0, 2, 5, 2, 3, 2),  # ters sirali cift: (lo, hi) = (2, 4)
        satir(1, 2, 1, 2, 2, 0),
        satir(2, 2, 7, 2, 9, 1),
    )
    s = qursim_oku(yol, AYETLER)
    assert s.ciftler == {(2, 4): 2, (0, 1): 0, (6, 8): 1}
    assert (s.satir, s.gecerli, s.gecersiz_toplam, s.yinelenen) == (3, 3, 0, 0)
    assert dict(s.label_dagilimi) == {0: 1, 1: 1, 2: 1}


def test_gecersiz_satirlar_sayaca_yazilir_ve_atlanir(tmp_path: Path) -> None:
    yol = yaz(
        tmp_path,
        satir(0, 2, 1, 2, 2, 1),  # gecerli
        satir(1, 2, 1, 2, 1, 1),  # kendi ayeti
        satir(2, 2, 1, 2, 11, 1),  # 11. ayet kumede yok
        satir(3, 3, 1, 2, 2, 1),  # 3. sure kumede yok
        satir(4, "x", 1, 2, 2, 1),  # sayi degil
        satir(5, 2, "01", 2, 2, 1),  # bastaki sifir
        satir(6, 2, 1, 2, 2, "uc"),  # Label sayi degil
        satir(7, 2, 2, 2, 1, 1),  # (1,2) ciftinin yinelemesi
        "1,2,3",  # sutun sayisi tutmuyor
    )
    s = qursim_oku(yol, AYETLER)
    assert s.ciftler == {(0, 1): 1}
    assert dict(s.gecersiz) == {
        "kendi_ayeti": 1,
        "capa_gecersiz": 2,
        "sayi_gecersiz": 2,
        "label_gecersiz": 1,
        "sutun_sayisi": 1,
    }
    assert s.yinelenen == 1 and s.gecerli == 1 and s.satir == 9


def test_verse_sutunlari_sonuca_girmez(tmp_path: Path) -> None:
    s = qursim_oku(yaz(tmp_path, satir(0, 2, 1, 2, 2, 1)), AYETLER)
    assert YER_TUTUCU not in repr(s) and "Deneme metni" not in repr(s)


def test_baslik_eksikse_ya_da_dosya_utf8_degilse_girdi_hatasi(tmp_path: Path) -> None:
    with pytest.raises(GirdiHatasi, match="baslik"):
        qursim_oku(yaz(tmp_path, baslik=",ID,SS,SV,Verse1,TS,TV,Verse2"), AYETLER)
    with pytest.raises(GirdiHatasi, match="yinelenen"):
        qursim_oku(yaz(tmp_path, baslik=",ID,SS,SV,SV,TS,TV,Label"), AYETLER)
    kotu = tmp_path / "kotu.csv"
    kotu.write_bytes(BASLIK.encode() + b"\n0,0,2,1,\xff\xfe,2,2,x,1\n")
    with pytest.raises(GirdiHatasi, match="UTF-8"):
        qursim_oku(kotu, AYETLER)
    with pytest.raises(GirdiHatasi, match="okunamadi"):
        qursim_oku(tmp_path / "yok.csv", AYETLER)
