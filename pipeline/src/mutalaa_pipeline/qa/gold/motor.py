"""Atif ve iktibas motorunun bellekte kurulumu (A18.5; `enrich citations` girdileriyle ayni).

`enrich citations` ile AYNI girdilerden (`adimlar/enrich_citations.py`) `MotorGirdisi` kurar:
veritabani (ayet ozetleri, QAC kelimeleri, onayli sure adi takma adlari, meal birimleri, `tr_form`,
onayli kalip kayitlari), `tanzil-simple-clean` son `ingest` calismasi ve iskelet dosyalar.
Hicbir sey yazilmaz (veritabani salt okunur; staged ve PG'ye cikti yok).

`alias_durumlari`: varsayilan `("onayli",)` URETIM YAPILANDIRMASIdir (gercek kosuda yalniz onayli
takma adlar etkin; bugun hic onayli takma ad yok, yani ad tabanli atif bicimleri kapali). Tani
amacli ikinci kosu `("onayli", "aday")` ile ad sozlugunu bellekte acar (yazma yok).
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass

import psycopg

from mutalaa_pipeline.enrich.baglantilar import girdi as db_girdi
from mutalaa_pipeline.enrich.baglantilar.uret import simple_kelimeleri
from mutalaa_pipeline.enrich.citations import girdi as cit_girdi
from mutalaa_pipeline.enrich.citations import gramer, kalip
from mutalaa_pipeline.enrich.citations.iktibas import MotorGirdisi
from mutalaa_pipeline.enrich.citations.indeks import imlai_indeksi, uthmani_indeksi
from mutalaa_pipeline.enrich.citations.kurallar import ipuclari_oku
from mutalaa_pipeline.enrich.citations.uret import SIMPLE_KAYNAGI, UTHMANI_KAYNAGI
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.runctx import RunContext
from mutalaa_pipeline.zincir import INGEST_ADIMI, saglam_olmali, son_calisma, units_oku

HEDEFLER = ("elmalili-meal", "elmalili-sade-meal")
BEKLENEN_AYET = 6236


@dataclass
class MotorKurulum:
    motor: MotorGirdisi
    ayet_capalari: list[str]
    surumler: dict[str, str]
    alias_durumlari: tuple[str, ...]
    ad_sozlugu_etkin: bool
    simple_metni: dict[str, str]  # q:s:a -> Simple Clean ham metin (staged)


def motor_kur(
    ctx: RunContext,
    conn: psycopg.Connection,
    *,
    alias_durumlari: Sequence[str] = ("onayli",),
    hedefler: Sequence[str] = HEDEFLER,
    beklenen_ayet: int | None = BEKLENEN_AYET,
) -> MotorKurulum:
    kayitlar = ctx.require_sources((UTHMANI_KAYNAGI, SIMPLE_KAYNAGI, *hedefler))
    surumler = {s: str(k.surum) for s, k in kayitlar.items()}
    simple_calisma = son_calisma(
        ctx, SIMPLE_KAYNAGI, INGEST_ADIMI, ipucu="once: ingest tanzil --variant simple-clean"
    )
    saglam_olmali(ctx, simple_calisma)
    db = db_girdi.db_oku(conn, beklenen_ayet=beklenen_ayet)
    cit = cit_girdi.db_oku(conn, tuple(hedefler))
    simple_metni = {
        s.metin("anchor"): s.metin("text") for s in units_oku(simple_calisma, SIMPLE_KAYNAGI)
    }
    simple = simple_kelimeleri(simple_metni, db.ayetler)
    uthmani = uthmani_indeksi(db.kelimeler, len(db.ayetler))
    imlai = imlai_indeksi(simple.kelimeler, uthmani)

    aliaslar = cit.aliaslar
    if tuple(alias_durumlari) != ("onayli",):
        aliaslar = _aliaslar_oku(conn, alias_durumlari)
    meal_ayet: dict[int, str] = {}
    sira = {a.capa: a.sira for a in db.ayetler}
    for kaynak in reversed(tuple(hedefler)):
        for b in cit.mealler[kaynak]:
            _, _, s, a = b.anchor.split(":")
            ayet = sira.get(f"q:{s}:{a}")
            if ayet is not None:
                meal_ayet[ayet] = b.metin
    liste = kalip.birlestir(kalip.dosyadan_oku(), cit.kalip_db)
    sozluk = gramer.AdSozlugu(aliaslar, gramer.riskli_anahtarlar()) if aliaslar else None
    motor = MotorGirdisi(
        indeksler=[uthmani, imlai],
        ayet_capalari=[a.capa for a in db.ayetler],
        ayet_ozetleri=[a.ozet for a in db.ayetler],
        kalip=liste,
        ipuclari=ipuclari_oku(),
        sozluk=sozluk,
        adlandirilmis=gramer.adlandirilmis_oku(),
        meal_metni=meal_ayet.get,
        lemma_sozlugu=cit.lemma_sozlugu,
    )
    return MotorKurulum(
        motor,
        [a.capa for a in db.ayetler],
        surumler,
        tuple(alias_durumlari),
        sozluk is not None and not sozluk.bos,
        simple_metni,
    )


def _aliaslar_oku(conn: psycopg.Connection, durumlar: Sequence[str]) -> list[gramer.Alias]:
    if not set(durumlar) <= {"onayli", "aday"}:
        raise GirdiHatasi("alias durumu onayli ya da aday olmali")
    return [
        gramer.Alias(int(no), str(alias), str(anahtar), str(tur), bool(riskli))
        for no, alias, anahtar, tur, riskli in conn.execute(
            "SELECT surah_no, alias, alias_key, kind, risky FROM icerik.surah_alias"
            " WHERE status::text = ANY(%s)",
            (list(durumlar),),
        ).fetchall()
    ]


MotorKur = Callable[..., MotorKurulum]
