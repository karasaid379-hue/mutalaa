"""Risale zip'inin bellekte guvenli okunmasi (A20.1; SENTETIK, diske hicbir sey acilmaz)."""

import io
import stat
import zipfile
from pathlib import Path

import pytest

from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.ingest.risale_zip import GuvenliZip, ZipSiniri, uye_adi_guvenli_mi


def _zip(uyeler: dict[str, bytes], sikistir: int = zipfile.ZIP_DEFLATED) -> bytes:
    tampon = io.BytesIO()
    with zipfile.ZipFile(tampon, "w", sikistir) as z:
        for ad, veri in uyeler.items():
            z.writestr(ad, veri)
    return tampon.getvalue()


def test_gecerli_zip_bellekte_okunur() -> None:
    z = GuvenliZip(_zip({"kok/a.txt": b"Deneme paragrafi 1", "kok/alt/b.txt": b"x"}))
    assert len(z) == 2
    assert z.adlar() == ["kok/a.txt", "kok/alt/b.txt"]
    assert z.oku("kok/a.txt") == b"Deneme paragrafi 1"
    assert z.var_mi("kok/a.txt") and not z.var_mi("kok/yok.txt")
    assert z.boyut("kok/alt/b.txt") == 1


@pytest.mark.parametrize(
    "ad",
    [
        "../disari.txt",
        "kok/../../disari.txt",
        "kok/..",
        "/mutlak.txt",
        "C:/surucu.txt",
        "C:\\surucu.txt",
        "kok\\ters.txt",
        "kok/a:b.txt",
        "kok/nul\x00.txt",
        "",
    ],
)
def test_guvensiz_uye_adi_islevi_reddeder(ad: str) -> None:
    assert not uye_adi_guvenli_mi(ad)


@pytest.mark.parametrize("ad", ["../disari.txt", "kok/../../disari.txt", "/mutlak.txt", "C:/s.txt"])
def test_guvensiz_ad_tasiyan_zip_acilmaz(ad: str) -> None:
    # `zipfile` bu adlari yazarken korur; Windows'ta bile `/` ayiricilidir.
    with pytest.raises(GirdiHatasi, match="guvensiz uye adi"):
        GuvenliZip(_zip({ad: b"x"}))


def test_guvenli_adlar_kabul_edilir() -> None:
    assert uye_adi_guvenli_mi("Risale-i-Nur-Diyanet-0123/txt/01 Deneme/Deneme-01-Birinci.txt")
    assert uye_adi_guvenli_mi("kok/.github/FUNDING.yml")
    assert uye_adi_guvenli_mi("kok/")  # dizin girdisi


def test_sembolik_baglanti_reddedilir() -> None:
    tampon = io.BytesIO()
    bilgi = zipfile.ZipInfo("kok/baglanti")
    bilgi.external_attr = (stat.S_IFLNK | 0o777) << 16
    with zipfile.ZipFile(tampon, "w") as z:
        z.writestr(bilgi, b"hedef.txt")
    with pytest.raises(GirdiHatasi, match="sembolik baglanti"):
        GuvenliZip(tampon.getvalue())


def test_yinelenen_uye_adi_reddedilir() -> None:
    tampon = io.BytesIO()
    with zipfile.ZipFile(tampon, "w") as z:
        z.writestr("kok/a.txt", b"1")
        with pytest.warns(UserWarning):  # zipfile yinelenen adi uyarir
            z.writestr("kok/a.txt", b"2")
    with pytest.raises(GirdiHatasi, match="yinelenen uye adi"):
        GuvenliZip(tampon.getvalue())


def test_sifreli_uye_reddedilir() -> None:
    veri = bytearray(_zip({"kok/a.txt": b"x"}, zipfile.ZIP_STORED))
    dizin = veri.rfind(b"PK\x01\x02")  # merkezi dizin: genel amacli bit bayragi ofset 8
    veri[dizin + 8] |= 0x1
    with pytest.raises(GirdiHatasi, match="sifreli uye"):
        GuvenliZip(bytes(veri))


def test_desteklenmeyen_sikistirma_reddedilir() -> None:
    tampon = io.BytesIO()
    with zipfile.ZipFile(tampon, "w", zipfile.ZIP_BZIP2) as z:
        z.writestr("kok/a.txt", b"Deneme paragrafi 1")
    with pytest.raises(GirdiHatasi, match="desteklenmeyen sikistirma"):
        GuvenliZip(tampon.getvalue())


def test_uye_sayisi_siniri() -> None:
    veri = _zip({f"kok/{i}.txt": b"x" for i in range(5)})
    GuvenliZip(veri, ZipSiniri(en_cok_uye=5))
    with pytest.raises(GirdiHatasi, match="uye sayisi"):
        GuvenliZip(veri, ZipSiniri(en_cok_uye=4))


def test_uye_boyut_ve_toplam_siniri() -> None:
    veri = _zip({"kok/a.txt": b"x" * 100, "kok/b.txt": b"y" * 100})
    with pytest.raises(GirdiHatasi, match="uye cok buyuk"):
        GuvenliZip(veri, ZipSiniri(en_cok_uye_bayt=99))
    with pytest.raises(GirdiHatasi, match="toplam acik boyut"):
        GuvenliZip(veri, ZipSiniri(en_cok_toplam_bayt=199))
    with pytest.raises(GirdiHatasi, match="zip: cok buyuk"):
        GuvenliZip(veri, ZipSiniri(en_cok_zip_bayt=10))


def test_sikistirma_orani_siniri_zip_bombasini_reddeder() -> None:
    veri = _zip({"kok/bomba.txt": b"\x00" * 1_000_000})
    with pytest.raises(GirdiHatasi, match="sikistirma orani"):
        GuvenliZip(veri, ZipSiniri(en_cok_oran=100))
    GuvenliZip(veri, ZipSiniri(en_cok_oran=100_000))  # sinir gevsekse acilir


def test_gecerli_zip_degil_cikis_hatasi() -> None:
    with pytest.raises(GirdiHatasi, match="gecerli bir zip degil"):
        GuvenliZip(b"zip hic degil")


def test_bozuk_veri_okumada_hata_verir() -> None:
    veri = bytearray(_zip({"kok/a.txt": b"Deneme paragrafi 1"}, zipfile.ZIP_STORED))
    konum = veri.find(b"Deneme paragrafi 1")
    veri[konum] ^= 0xFF  # veri bozulur, CRC ayni kalir
    z = GuvenliZip(bytes(veri))
    with pytest.raises(GirdiHatasi, match="uye okunamadi"):
        z.oku("kok/a.txt")


def test_olmayan_uye_hata_verir() -> None:
    z = GuvenliZip(_zip({"kok/a.txt": b"x"}))
    with pytest.raises(GirdiHatasi, match="uye yok"):
        z.oku("kok/b.txt")


def test_zip_diske_acilmaz(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    z = GuvenliZip(_zip({"kok/a.txt": b"x"}))
    z.oku("kok/a.txt")
    assert list(tmp_path.iterdir()) == []
