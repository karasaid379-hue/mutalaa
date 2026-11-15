"""Baglanti uretiminin girdi tipleri ve veritabani okuyucusu (salt okuma).

`db_oku` `icerik.unit` (Tanzil Uthmani ayet ozetleri), `icerik.quran_word` (kelime, kok, lemma,
normalize kelime) ve `icerik.root` (`ayah_count`) tablolarini okur; hicbir sey yazmaz. Ayet
numarasi (`ayah_index`) kuresel ve 1 tabanlidir; bu modul 0 tabanli sira (`sira`) kullanir.
"""

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final

import psycopg

from mutalaa_pipeline.export.ortak import GirdiHatasi

UTHMANI_KAYNAGI: Final = "tanzil-uthmani"
OZET_UZUNLUGU: Final = 16  # evidence.src_hash / dst_hash: content_hash ilk 16 hane


@dataclass(frozen=True)
class Ayet:
    sira: int  # 0 tabanli kuresel ayet sirasi (ayah_index - 1)
    capa: str  # q:s:a
    ozet: str  # content_hash ilk 16 hane


@dataclass(frozen=True)
class Kelime:
    sira: int  # ayet sirasi
    no: int  # ayet icindeki kelime numarasi (QAC konumu, 1 tabanli)
    capa: str  # q:s:a:k
    norm: str
    root_id: int | None
    lemma_id: int | None


@dataclass(frozen=True)
class DbGirdisi:
    ayetler: list[Ayet]
    kelimeler: list[Kelime]
    kok_ayah_count: dict[int, int]  # root.id -> root.ayah_count

    def girdi_ozeti(self) -> str:
        """Girdinin SHA-256 ozeti (manifest; icerik metni degil, yalniz ozet saklanir)."""
        h = hashlib.sha256()
        for a in self.ayetler:
            h.update(f"A|{a.sira}|{a.capa}|{a.ozet}\n".encode())
        for k in self.kelimeler:
            h.update(f"K|{k.capa}|{k.root_id}|{k.lemma_id}|".encode())
            h.update(k.norm.encode("utf-8"))
            h.update(b"\n")
        for kimlik, sayi in sorted(self.kok_ayah_count.items()):
            h.update(f"R|{kimlik}|{sayi}\n".encode())
        return h.hexdigest()

    def ayet_sirasi(self) -> dict[str, int]:
        return {a.capa: a.sira for a in self.ayetler}


def ayet_capasi(capa: str) -> str:
    """`q:s:a:k` kelime capasindan `q:s:a` ayet capasi."""
    return capa.rsplit(":", 1)[0]


def db_oku(conn: psycopg.Connection, *, beklenen_ayet: int | None = None) -> DbGirdisi:
    """Ayet ozetleri, kelimeler ve kok sayaclari; tutarsizlikta `GirdiHatasi` (cikis 2)."""
    kelime_satirlari = conn.execute(
        "SELECT anchor, surah, ayah, word, ayah_index, norm, root_id, lemma_id"
        " FROM icerik.quran_word ORDER BY ayah_index, word"
    ).fetchall()
    ozetler = {
        str(capa): str(ozet)[:OZET_UZUNLUGU]
        for capa, ozet in conn.execute(
            "SELECT anchor, content_hash FROM icerik.unit WHERE kind = 'ayet'"
            " AND source_id = %s AND status = 'etkin'",
            (UTHMANI_KAYNAGI,),
        ).fetchall()
    }
    ayetler: list[Ayet] = []
    kelimeler: list[Kelime] = []
    onceki = 0
    for capa, sure, ayet, no, indeks, norm, kok, lemma in kelime_satirlari:
        ayet_capa = f"q:{int(sure)}:{int(ayet)}"
        if int(indeks) != onceki:
            if int(indeks) != onceki + 1:
                raise GirdiHatasi("quran_word.ayah_index kesintisiz degil")
            onceki = int(indeks)
            ozet = ozetler.get(ayet_capa)
            if ozet is None:
                raise GirdiHatasi(f"ayet birimi yok ya da etkin degil: {ayet_capa}")
            ayetler.append(Ayet(onceki - 1, ayet_capa, ozet))
        kelimeler.append(
            Kelime(
                onceki - 1,
                int(no),
                str(capa),
                str(norm),
                None if kok is None else int(kok),
                None if lemma is None else int(lemma),
            )
        )
    if beklenen_ayet is not None and len(ayetler) != beklenen_ayet:
        raise GirdiHatasi(f"{len(ayetler)} ayet okundu; {beklenen_ayet} bekleniyor")
    if not ayetler:
        raise GirdiHatasi("quran_word bos: once export pg --source tanzil-uthmani ve qac-morfoloji")
    kok_sayilari = {
        int(k): int(n) for k, n in conn.execute("SELECT id, ayah_count FROM icerik.root").fetchall()
    }
    return DbGirdisi(ayetler, kelimeler, kok_sayilari)


def ayet_kelimeleri(kelimeler: Sequence[Kelime], ayet_sayisi: int) -> list[list[str]]:
    """Ayet basina normalize jetonlar (QAC konum sirasinda; bosluklu `norm` birden cok jeton)."""
    sonuc: list[list[str]] = [[] for _ in range(ayet_sayisi)]
    for k in kelimeler:
        sonuc[k.sira].extend(k.norm.split())
    return sonuc
