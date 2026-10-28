"""Veritabani baglantisi (config'ten). Hata iletilerine baglanti dizesi girmez."""

from collections.abc import Iterable

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


def lisans_durumlari(conn: psycopg.Connection, slugs: Iterable[str]) -> dict[str, str]:
    """`icerik.source` tablosunda satiri olan kaynaklarin `license_status` degerleri."""
    liste = sorted(set(slugs))
    try:
        satirlar = conn.execute(
            "SELECT slug, license_status::text FROM icerik.source WHERE slug = ANY(%s)",
            (liste,),
        ).fetchall()
    except psycopg.Error as hata:
        raise VeritabaniHatasi(f"lisans durumu okunamadi ({type(hata).__name__})") from None
    return {str(slug): str(durum) for slug, durum in satirlar}
