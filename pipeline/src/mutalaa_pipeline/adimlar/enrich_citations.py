"""Acik atif ve iktibas adimi (A18.4, K-51): `mutalaa enrich citations --target <meal> ...`.

`--target`: `elmalili-meal` ve/veya `elmalili-sade-meal` (tekrarlanir; K-51 madde 7: iki meal
birlikte). Meal birimleri veritabanindan (`icerik.unit`, taslak dahil) okunur; metin hicbir yere
yazilmaz. Staged cikti `staged/xref-atif-iktibas/{run_id}/xref_citations.jsonl` (ASCII kacisli,
sirali, LF; zaman damgasi yok). `xref-atif-iktibas` bir icerik kaynagi degil, bu uretimin staged
ve `export pg` / `qa run` adidir (A18.3 `xref-baglantilar` deseni); `evidence.source_id`
degerleri gercek kaynak kayitlaridir (`tanzil-uthmani`, `tanzil-simple-clean`).

Girdiler (hepsi salt okunur): veritabani (`quran_word`, ayet ozetleri, meal birimleri, onayli
`surah_alias`, `tr_form`, onayli kalip kayitlari), `tanzil-simple-clean` son `ingest` calismasi
(imlai indeks) ve depodaki iskelet dosyalar (`kalip_listesi.toml`, `adlandirilmis_ayetler.toml`,
`ipuclari.toml`). Her kosuda yeniden uretilir (girdinin bir kismi veritabanidir). Dil modeli ve ag
cagrisi yoktur (K-50). Hata iletileri yalniz sayi, capa ve ozet tasir; metin hicbir yere yazilmaz.
"""

import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Final

import psycopg

from mutalaa_pipeline import cikis
from mutalaa_pipeline.db import baglan
from mutalaa_pipeline.enrich.baglantilar import girdi as db_girdi
from mutalaa_pipeline.enrich.baglantilar.uret import simple_kelimeleri
from mutalaa_pipeline.enrich.citations import girdi as cit_girdi
from mutalaa_pipeline.enrich.citations import gramer, kalip
from mutalaa_pipeline.enrich.citations.iktibas import MotorGirdisi
from mutalaa_pipeline.enrich.citations.indeks import imlai_indeksi, uthmani_indeksi
from mutalaa_pipeline.enrich.citations.kurallar import ipuclari_oku
from mutalaa_pipeline.enrich.citations.uret import (
    CITATIONS_SURUMU,
    SIMPLE_KAYNAGI,
    UTHMANI_KAYNAGI,
    Uretim,
    uret,
)
from mutalaa_pipeline.enrich.rapor import yan_rapor_yaz
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.ingest.meal_kaynaklari import MEAL_KAYNAKLARI
from mutalaa_pipeline.komut_ortak import komutu_yurut
from mutalaa_pipeline.runctx import RunContext
from mutalaa_pipeline.staged import dosya_yaz
from mutalaa_pipeline.zincir import (
    INGEST_ADIMI,
    girdi_olarak,
    saglam_olmali,
    son_calisma,
    units_oku,
)

KAYNAK: Final = "xref-atif-iktibas"
CITATIONS_ADIMI: Final = "enrich"
CITATIONS_DOSYASI: Final = "xref_citations.jsonl"
SIRA_ANAHTARI: Final = ("tur_no", "src_no", "src_bas", "dst_no", "dst_bas")
BEKLENEN_AYET: Final = 6236
BAGLANTI = Callable[[], psycopg.Connection]


def hedefleri_coz(hedefler: Sequence[str]) -> tuple[str, ...]:
    """`--target` degerleri (sirali, tekil); bos ya da bilinmeyen deger `GirdiHatasi`."""
    sirali = tuple(sorted(dict.fromkeys(hedefler)))
    if not sirali or any(h not in MEAL_KAYNAKLARI for h in sirali):
        raise GirdiHatasi(f"--target {', '.join(MEAL_KAYNAKLARI)} degerlerinden olmali")
    return sirali


def veri_surumu(surumler: dict[str, str | None]) -> str:
    return (
        f"citations@{CITATIONS_SURUMU}/{UTHMANI_KAYNAGI}@{surumler[UTHMANI_KAYNAGI]}"
        f"/{SIMPLE_KAYNAGI}@{surumler[SIMPLE_KAYNAGI]}"
    )


def run_enrich_citations(
    ctx: RunContext,
    hedefler: tuple[str, ...],
    *,
    baglanti: BAGLANTI | None = None,
    beklenen_ayet: int | None = BEKLENEN_AYET,
) -> tuple[Uretim, Path | None]:
    """Kaynak kayitlari, girdiler, uretim, dosya ve manifest (en son)."""
    kayitlar = ctx.require_sources((UTHMANI_KAYNAGI, SIMPLE_KAYNAGI, *hedefler))
    ctx.gunluk.yaz("INFO", "enrich_citations_basla", source_id=KAYNAK)
    surumler: dict[str, str | None] = {slug: k.surum for slug, k in kayitlar.items()}
    if surumler[UTHMANI_KAYNAGI] is None or surumler[SIMPLE_KAYNAGI] is None:
        raise GirdiHatasi("kaynak kaydinda surum yok")
    simple_calisma = son_calisma(
        ctx, SIMPLE_KAYNAGI, INGEST_ADIMI, ipucu="once: ingest tanzil --variant simple-clean"
    )
    saglam_olmali(ctx, simple_calisma)
    girdiler = [girdi_olarak(simple_calisma)]

    kapat = baglanti is None
    conn = baglanti() if baglanti is not None else baglan(ctx.ayarlar, autocommit=True)
    try:
        db = db_girdi.db_oku(conn, beklenen_ayet=beklenen_ayet)
        cit = cit_girdi.db_oku(conn, hedefler)
    finally:
        if kapat:
            conn.close()

    simple = simple_kelimeleri(
        {s.metin("anchor"): s.metin("text") for s in units_oku(simple_calisma, SIMPLE_KAYNAGI)},
        db.ayetler,
    )
    uthmani = uthmani_indeksi(db.kelimeler, len(db.ayetler))
    imlai = imlai_indeksi(simple.kelimeler, uthmani)
    meal_ayet: dict[int, str] = {}
    sira = {a.capa: a.sira for a in db.ayetler}
    for kaynak in reversed(hedefler):  # `elmalili-meal` (alfabetik ilk) onceliklidir
        for b in cit.mealler[kaynak]:
            _, _, s, a = b.anchor.split(":")
            ayet = sira.get(f"q:{s}:{a}")
            if ayet is not None:
                meal_ayet[ayet] = b.metin
    liste = kalip.birlestir(kalip.dosyadan_oku(), cit.kalip_db)
    sozluk = gramer.AdSozlugu(cit.aliaslar, gramer.riskli_anahtarlar()) if cit.aliaslar else None
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
    birimler = cit_girdi.sirali([b for h in hedefler for b in cit.mealler[h]])
    surum = veri_surumu(surumler)
    uretim = uret(motor, birimler, surum)
    uretim.istatistik["hedefler"] = list(hedefler)
    uretim.istatistik["meal_birim"] = {h: len(cit.mealler[h]) for h in hedefler}
    uretim.istatistik["imlai_uthmani_kelime_farkli_ayet"] = sum(
        1
        for i in range(uthmani.ayet_sayisi)
        if len(imlai.ayet_belirtec[i]) != len(uthmani.ayet_belirtec[i])
    )
    uretim.istatistik.update(cit.sayilar)
    ctx.sayi("satir", int(str(uretim.istatistik["satir_toplam"])))
    for tur, n in dict(uretim.istatistik["tur"]).items():  # type: ignore[call-overload]
        ctx.sayi(f"{tur}_satir", int(n))
    if ctx.dry_run:
        ctx.gunluk.yaz("INFO", "enrich_citations_dry_run", source_id=KAYNAK)
        return uretim, None

    cikti = dosya_yaz(ctx, KAYNAK, CITATIONS_DOSYASI, uretim.satirlar, SIRA_ANAHTARI)
    klasor = ctx.staged_dizin(KAYNAK)
    parmak = ctx.parmak_izi(girdiler)
    girdi_ozeti = f"{db.girdi_ozeti()}/{cit.girdi_ozeti()}"
    ayrintilar: dict[str, object] = {
        "kaynak": KAYNAK,
        "hedefler": list(hedefler),
        "turler": ["atif", "iktibas"],
        "data_version": surum,
        "yontem_surumu": CITATIONS_SURUMU,
        "kaynak_surumleri": {s: str(v) for s, v in sorted(surumler.items()) if v},
        "db_girdi_ozeti": girdi_ozeti,
        "ayet_sayisi": len(db.ayetler),
        "simple_clean_run": simple_calisma.run_id,
        "istatistik": uretim.istatistik,
    }
    ctx.manifest_yaz(
        klasor, girdiler=girdiler, ciktilar=[cikti], parmak=parmak, ayrintilar=ayrintilar
    )
    yan_rapor_yaz(
        ctx,
        "citations",
        {
            "run_id": ctx.run_id,
            "kaynak": KAYNAK,
            "hedefler": list(hedefler),
            "data_version": surum,
            "db_girdi_ozeti": girdi_ozeti,
            "istatistik": uretim.istatistik,
        },
    )
    ctx.gunluk.yaz("INFO", "enrich_citations_bitti", source_id=KAYNAK)
    return uretim, klasor


def _ozet_yaz(uretim: Uretim, klasor: Path | None, run_id: str, dry_run: bool) -> None:
    tur = uretim.istatistik["tur"]
    parcalar = ", ".join(f"{t} {n}" for t, n in dict(tur).items())  # type: ignore[call-overload]
    ek = " (dry-run, hicbir sey yazilmadi)" if dry_run or klasor is None else f", run {run_id}"
    sys.stdout.write(
        f"enrich citations: {uretim.istatistik['satir_toplam']} satir ({parcalar}){ek}\n"
    )


def komut_enrich_citations(
    *,
    hedefler: Sequence[str],
    dry_run: bool,
    force: bool,
    config: Path | None,
    kok: Path | None,
    baglanti: BAGLANTI | None = None,
    beklenen_ayet: int | None = BEKLENEN_AYET,
) -> int:
    """`enrich citations` komutu; cikis kodunu dondurur (0 ya da 2)."""

    def govde(ctx: RunContext) -> int:
        cozulen = hedefleri_coz(hedefler)
        uretim, klasor = run_enrich_citations(
            ctx, cozulen, baglanti=baglanti, beklenen_ayet=beklenen_ayet
        )
        _ozet_yaz(uretim, klasor, ctx.run_id, ctx.dry_run)
        return cikis.BASARILI

    secilen = tuple(h for h in hedefler if h in MEAL_KAYNAKLARI)
    return komutu_yurut(
        komut="enrich citations",
        adim=CITATIONS_ADIMI,
        kaynaklar=sorted({UTHMANI_KAYNAGI, SIMPLE_KAYNAGI, *secilen}),
        config=config,
        kok=kok,
        govde=govde,
        force=force,
        dry_run=dry_run,
        parametreler={"target": list(hedefler)},
    )
