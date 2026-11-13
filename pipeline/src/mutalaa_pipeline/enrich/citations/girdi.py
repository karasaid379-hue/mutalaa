"""Atif ve iktibas motorunun veritabani girdileri (salt okuma).

Meal birimleri (`icerik.unit`, `kind = 'meal'`, taslak dahil; metin kanonik metindir ve hicbir
yere yazilmaz), onayli `surah_alias` satirlari, `tr_form` (meal benzerligi icin lemma sozlugu) ve
onayli kalip kayitlari okunur. Girdi ozeti manifeste yazilir (icerik degil, yalniz ozet).
"""

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass, field

import psycopg

from mutalaa_pipeline.enrich.citations.gramer import Alias
from mutalaa_pipeline.enrich.citations.iktibas import Birim
from mutalaa_pipeline.export.ortak import GirdiHatasi

OZET_UZUNLUGU = 16


@dataclass(frozen=True)
class DbGirdisi:
    mealler: dict[str, list[Birim]]  # source_id -> birimler (anchor baytlarina gore sirali)
    aliaslar: list[Alias]  # yalniz status = 'onayli'
    lemma_sozlugu: dict[str, frozenset[int]]  # tr_form.key_narrow -> lemma kimlikleri
    kalip_db: frozenset[str]
    sayilar: dict[str, int] = field(default_factory=dict)

    def girdi_ozeti(self) -> str:
        h = hashlib.sha256()
        for kaynak in sorted(self.mealler):
            for b in self.mealler[kaynak]:
                h.update(f"M|{kaynak}|{b.anchor}|{b.ozet}\n".encode())
        for a in sorted(self.aliaslar, key=lambda a: (a.surah_no, a.alias)):
            h.update(f"A|{a.surah_no}|{a.alias_key}|{a.kind}|{a.risky}\n".encode())
        for k, v in sorted(self.lemma_sozlugu.items()):
            h.update(f"L|{k}|{sorted(v)}\n".encode())
        for k in sorted(self.kalip_db):
            h.update(f"K|{k}\n".encode())
        return h.hexdigest()


def sirali(birimler: Sequence[Birim]) -> list[Birim]:
    return sorted(birimler, key=lambda b: b.anchor.encode("utf-8"))


def meal_oku(conn: psycopg.Connection, kaynak: str) -> list[Birim]:
    """Bir meal kaynaginin etkin birimleri (taslak dahil); bos metin atlanir."""
    satirlar = conn.execute(
        "SELECT anchor, metin, content_hash, role FROM icerik.unit WHERE source_id = %s"
        " AND kind = 'meal' AND status = 'etkin'",
        (kaynak,),
    ).fetchall()
    birimler = [
        Birim(str(a), str(m), str(h)[:OZET_UZUNLUGU], str(r))
        for a, m, h, r in satirlar
        if str(m) != ""
    ]
    if not birimler:
        raise GirdiHatasi(f"{kaynak}: veritabaninda meal birimi yok (once export pg)")
    return sirali(birimler)


def db_oku(conn: psycopg.Connection, hedefler: Sequence[str]) -> DbGirdisi:
    from mutalaa_pipeline.enrich.citations.kalip import veritabanindan_oku

    mealler = {h: meal_oku(conn, h) for h in hedefler}
    aliaslar = [
        Alias(int(no), str(alias), str(anahtar), str(tur), bool(riskli))
        for no, alias, anahtar, tur, riskli in conn.execute(
            "SELECT surah_no, alias, alias_key, kind, risky FROM icerik.surah_alias"
            " WHERE status = 'onayli'"
        ).fetchall()
    ]
    lemma: dict[str, set[int]] = {}
    for anahtar, kimlik in conn.execute(
        "SELECT f.key_narrow, f.tr_lemma_id FROM icerik.tr_form f"
        " JOIN icerik.lemma l ON l.id = f.tr_lemma_id WHERE l.status = 'onayli' AND l.lang = 'tr'"
    ).fetchall():
        lemma.setdefault(str(anahtar), set()).add(int(kimlik))
    return DbGirdisi(
        mealler,
        aliaslar,
        {k: frozenset(v) for k, v in lemma.items()},
        veritabanindan_oku(conn),
        {"alias_onayli": len(aliaslar), "tr_form_anahtar": len(lemma)},
    )
