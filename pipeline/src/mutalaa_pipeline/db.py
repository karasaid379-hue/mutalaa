"""Veritabani baglantisi (config'ten). Hata iletilerine baglanti dizesi girmez."""

import psycopg

from mutalaa_pipeline.config import Ayarlar
from mutalaa_pipeline.export.ortak import GirdiHatasi


class VeritabaniHatasi(GirdiHatasi):
    """Baglanti ya da sorgu hatasi; komut 2 ile cikar. Ileti yalniz hata turunu tasir."""


def baglan(
    ayarlar: Ayarlar, *, test: bool = False, autocommit: bool = False, zaman_asimi: int = 10
) -> psycopg.Connection:
    """Ana (ya da turetilmis test) veritabanina baglanir."""
    adres = ayarlar.test_db_adresi().get_secret_value() if test else ayarlar.db_adresi()
    try:
        return psycopg.connect(adres, autocommit=autocommit, connect_timeout=zaman_asimi)
    except psycopg.Error as hata:
        # psycopg iletisi host, kullanici ve baglanti parcalari icerebilir: yalniz tur yazilir.
        raise VeritabaniHatasi(f"veritabanina baglanilamadi ({type(hata).__name__})") from None
