"""Kalip listesi (Iktibas tespiti §7): editor onayli normalize anahtarlar.

Kaynaklar: `kalip_listesi.toml` (iskelet, bos) ve veritabanindaki onayli `review` kayitlari
(`eylem = 'kalip_ekle'`, `durum = 'onaylandi'`, `onerilen ->> 'anahtar'`). Ikisi birlestirilir.
Anahtarlar yeniden normalize edilir (`normalizasyon.anahtar_dizisi`; idempotent). Dosyaya ve
koda Kur'an dizisi hafizadan yazilmaz. Kalip listesindeki dizi icin otomatik satir uretilmez.
"""

import tomllib
from collections.abc import Iterable
from pathlib import Path
from typing import Final

import psycopg

from mutalaa_pipeline.enrich.citations.normalizasyon import anahtar_dizisi

KALIP_YOLU: Final = Path(__file__).resolve().parent / "kalip_listesi.toml"
DB_SORGUSU: Final = (
    "SELECT DISTINCT onerilen ->> 'anahtar' FROM icerik.review WHERE eylem = 'kalip_ekle'"
    " AND durum = 'onaylandi' AND onerilen ->> 'anahtar' IS NOT NULL"
)


def anahtar_normallestir(anahtar: str) -> str:
    return " ".join(anahtar_dizisi(anahtar))


def dosyadan_oku(yol: Path | None = None) -> frozenset[str]:
    veri = tomllib.loads((yol or KALIP_YOLU).read_text(encoding="utf-8"))
    ham = veri.get("anahtarlar", [])
    if not isinstance(ham, list) or not all(isinstance(a, str) for a in ham):
        raise ValueError("kalip listesi: `anahtarlar` metin dizisi olmali")
    return frozenset(a for a in map(anahtar_normallestir, ham) if a)


def veritabanindan_oku(conn: psycopg.Connection) -> frozenset[str]:
    return frozenset(
        a
        for (ham,) in conn.execute(DB_SORGUSU).fetchall()
        for a in (anahtar_normallestir(str(ham)),)
        if a
    )


def birlestir(*kaynaklar: Iterable[str]) -> frozenset[str]:
    return frozenset(a for k in kaynaklar for a in k)


def kalip_mi(anahtar: str, liste: frozenset[str]) -> bool:
    """`anahtar` ya da onu kapsayan bir kalip listede mi (kalip anahtarinin alt dizisi sayilir)."""
    return anahtar in liste or any(f" {anahtar} " in f" {k} " for k in liste)
