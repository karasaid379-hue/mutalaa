"""Veritabani baglantisi (config'ten). Hata iletilerine baglanti dizesi girmez."""

import psycopg
from psycopg import conninfo

from mutalaa_pipeline.config import Ayarlar
from mutalaa_pipeline.export.ortak import GirdiHatasi


class VeritabaniHatasi(GirdiHatasi):
    """Baglanti ya da sorgu hatasi; komut 2 ile cikar. Ileti yalniz hata turunu tasir."""


def ipv4_tercih(adres: str) -> str:
    """`host=localhost` ise ve `hostaddr` yoksa 127.0.0.1'e baglanir (adresi degistirmez).

    Windows'ta `localhost` once `::1`e cozulur; Docker yalniz 127.0.0.1'i yayinlar, bu yuzden ilk
    deneme `connect_timeout` suresince bekler (her baglanti 10 sn). Docker ayni makinede yalniz
    IPv4 dinledigi icin sonuc ayni sunucudur; yalniz bekleme kalkar.
    """
    try:
        parcalar = conninfo.conninfo_to_dict(adres)
    except psycopg.Error:
        return adres
    host = parcalar.get("host")
    if isinstance(host, str) and host.lower() == "localhost" and not parcalar.get("hostaddr"):
        return conninfo.make_conninfo(adres, hostaddr="127.0.0.1")
    return adres


def baglan(
    ayarlar: Ayarlar, *, test: bool = False, autocommit: bool = False, zaman_asimi: int = 10
) -> psycopg.Connection:
    """Ana (ya da turetilmis test) veritabanina baglanir."""
    adres = ayarlar.test_db_adresi().get_secret_value() if test else ayarlar.db_adresi()
    try:
        return psycopg.connect(
            ipv4_tercih(adres), autocommit=autocommit, connect_timeout=zaman_asimi
        )
    except psycopg.Error as hata:
        # psycopg iletisi host, kullanici ve baglanti parcalari icerebilir: yalniz tur yazilir.
        raise VeritabaniHatasi(f"veritabanina baglanilamadi ({type(hata).__name__})") from None
