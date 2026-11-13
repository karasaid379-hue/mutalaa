"""Kur'an ici baglanti adimi (A18.3, K-51): `mutalaa enrich links --type <tur>`.

`<tur>`: `kok`, `lemma`, `benzer-ayet` ya da `hepsi`.

Uc tur tek adimdadir ve ayni staged dosyasina yazar: `staged/xref-baglantilar/{run_id}/
xref_links.jsonl` (ASCII kacisli, sirali, LF; zaman damgasi yok). `xref-baglantilar` bir icerik
kaynagi degil, bu uretimin staged ve `export pg` adidir; `evidence.source_id` degerleri gercek
kaynak kayitlaridir (`qac-morfoloji`, `tanzil-uthmani`, `qursim`).

Girdiler (hepsi salt okunur):

* veritabani: `icerik.quran_word` (kelime, kok, lemma, normalize kelime), `icerik.unit`
  (Tanzil Uthmani ayet ozetleri) ve `icerik.root` (`ayah_count`); girdi ozeti manifestte;
* `benzer-ayet` icin: `tanzil-simple-clean` son `ingest` calismasi (imlai indeks; Simple
  Clean'in anchor adimi yoktur) ve `data/gelen/qursim/<tarih>/QurSim_filtered.csv` (SHA256SUMS
  ile dogrulanir; yalniz `SS`, `SV`, `TS`, `TV` ve `Label` alinir, K-51 madde 12).

Adim adi `enrich`tir; `export pg --source xref-baglantilar` ve `qa run --source
xref-baglantilar` son `enrich` calismasini arar. Her kosuda yeniden uretilir (parmak izi
atlamasi yoktur: girdinin bir kismi veritabanidir). Dil modeli ve ag cagrisi yoktur (K-50).
Hata iletileri yalniz sayi, capa ve ozet tasir; Arapca metin hicbir yere yazilmaz.
"""

import sys
from collections.abc import Callable
from pathlib import Path
from typing import Final

import psycopg

from mutalaa_pipeline import cikis, lineage
from mutalaa_pipeline.adimlar.enrich_tr_roots import _tarih_klasoru, ozetler_oku
from mutalaa_pipeline.db import baglan
from mutalaa_pipeline.enrich.baglantilar import girdi as db_girdi
from mutalaa_pipeline.enrich.baglantilar.qursim import qursim_oku
from mutalaa_pipeline.enrich.baglantilar.uret import (
    BENZER,
    KOK,
    LEMMA,
    LINKS_SURUMU,
    QAC_KAYNAGI,
    QURSIM_KAYNAGI,
    TURLER,
    UTHMANI_KAYNAGI,
    Girdi,
    Uretim,
    simple_kelimeleri,
    uret,
)
from mutalaa_pipeline.enrich.rapor import yan_rapor_yaz
from mutalaa_pipeline.export.ortak import GirdiHatasi
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

KAYNAK: Final = "xref-baglantilar"
LINKS_ADIMI: Final = "enrich"
LINKS_DOSYASI: Final = "xref_links.jsonl"
SIMPLE_KAYNAGI: Final = "tanzil-simple-clean"
QURSIM_DOSYASI: Final = "QurSim_filtered.csv"
SIRA_ANAHTARI: Final = ("tur_no", "src_no", "dst_no")
BEKLENEN_AYET: Final = 6236
TUR_SECENEKLERI: Final = {
    "kok": (KOK,),
    "lemma": (LEMMA,),
    "benzer-ayet": (BENZER,),
    "hepsi": TURLER,
}
KAYNAK_GEREKSINIMI: Final = {
    KOK: (QAC_KAYNAGI,),
    LEMMA: (QAC_KAYNAGI,),
    BENZER: (UTHMANI_KAYNAGI, SIMPLE_KAYNAGI, QURSIM_KAYNAGI),
}
BAGLANTI = Callable[[], psycopg.Connection]


def turleri_coz(secim: str) -> tuple[str, ...]:
    """`--type` degeri -> xref turleri (kok, lemma, benzer_ayet); bilinmeyen deger `GirdiHatasi`."""
    turler = TUR_SECENEKLERI.get(secim)
    if turler is None:
        raise GirdiHatasi(f"--type {', '.join(TUR_SECENEKLERI)} degerlerinden biri olmali")
    return turler


def veri_surumu(tur: str, surumler: dict[str, str | None]) -> str:
    """`xref.data_version`: yalniz o turun girdi surumlerine baglidir."""
    if tur == BENZER:
        return (
            f"links-benzer@{LINKS_SURUMU}/{UTHMANI_KAYNAGI}@{surumler[UTHMANI_KAYNAGI]}"
            f"/{QURSIM_KAYNAGI}@{surumler[QURSIM_KAYNAGI]}"
        )
    return f"links-{tur}@{LINKS_SURUMU}/{QAC_KAYNAGI}@{surumler[QAC_KAYNAGI]}"


def _qursim_dosyasi(ctx: RunContext, tarih: str | None) -> tuple[Path, str]:
    klasor = _tarih_klasoru(ctx.veri_kok, tarih, QURSIM_KAYNAGI)
    yol = klasor / QURSIM_DOSYASI
    if not yol.is_file():
        raise GirdiHatasi(f"QurSim dosyasi yok: {QURSIM_DOSYASI}")
    ozet = lineage.sha256_dosya(yol)
    if ozetler_oku(klasor).get(QURSIM_DOSYASI) != ozet:
        raise GirdiHatasi("QurSim dosyasi SHA256SUMS ile tutmuyor")
    return yol, ozet


def run_enrich_links(
    ctx: RunContext,
    turler: tuple[str, ...],
    *,
    gelen_tarih: str | None = None,
    baglanti: BAGLANTI | None = None,
    beklenen_ayet: int | None = BEKLENEN_AYET,
) -> tuple[Uretim, Path | None]:
    """Kaynak kayitlari, girdiler, uretim, dosya ve manifest (en son); `beklenen_ayet`: testler."""
    gerekli = tuple(dict.fromkeys(s for t in turler for s in KAYNAK_GEREKSINIMI[t]))
    kayitlar = ctx.require_sources(gerekli)
    ctx.gunluk.yaz("INFO", "enrich_links_basla", source_id=KAYNAK)
    surumler: dict[str, str | None] = {slug: k.surum for slug, k in kayitlar.items()}
    if any(v is None for v in surumler.values()):
        raise GirdiHatasi("kaynak kaydinda surum yok")
    girdiler: list[lineage.Girdi] = []
    simple_calisma = None
    qursim_yolu: Path | None = None
    if BENZER in turler:
        simple_calisma = son_calisma(
            ctx, SIMPLE_KAYNAGI, INGEST_ADIMI, ipucu="once: ingest tanzil --variant simple-clean"
        )
        saglam_olmali(ctx, simple_calisma)
        girdiler.append(girdi_olarak(simple_calisma))
        qursim_yolu, qursim_ozeti = _qursim_dosyasi(ctx, gelen_tarih)
        girdiler.append(lineage.Girdi(lineage.goreli_yol(ctx.veri_kok, qursim_yolu), qursim_ozeti))

    kapat = baglanti is None
    conn = baglanti() if baglanti is not None else baglan(ctx.ayarlar, autocommit=True)
    try:
        db = db_girdi.db_oku(conn, beklenen_ayet=beklenen_ayet)
    finally:
        if kapat:
            conn.close()
    simple = None
    qursim = None
    if simple_calisma is not None and qursim_yolu is not None:
        satirlar = units_oku(simple_calisma, f"{SIMPLE_KAYNAGI} units.jsonl")
        simple = simple_kelimeleri(
            {s.metin("anchor"): s.metin("text") for s in satirlar}, db.ayetler
        )
        qursim = qursim_oku(qursim_yolu, db.ayet_sirasi())
    surum_tablosu = {t: veri_surumu(t, surumler) for t in turler}
    uretim = uret(Girdi(db, simple, qursim), turler, surum_tablosu)
    for ad, deger in uretim.istatistik.items():
        if isinstance(deger, dict):
            ctx.sayi(f"{ad}_satir", int(str(deger["satir"])))
    ctx.sayi("satir", int(str(uretim.istatistik["satir_toplam"])))
    if ctx.dry_run:
        ctx.gunluk.yaz("INFO", "enrich_links_dry_run", source_id=KAYNAK)
        return uretim, None

    cikti = dosya_yaz(ctx, KAYNAK, LINKS_DOSYASI, uretim.satirlar, SIRA_ANAHTARI)
    klasor = ctx.staged_dizin(KAYNAK)
    parmak = ctx.parmak_izi(girdiler)
    ayrintilar: dict[str, object] = {
        "kaynak": KAYNAK,
        "turler": list(turler),
        "data_version": surum_tablosu,
        "yontem_surumu": LINKS_SURUMU,
        "kaynak_surumleri": {s: str(v) for s, v in sorted(surumler.items())},
        "db_girdi_ozeti": db.girdi_ozeti(),
        "ayet_sayisi": len(db.ayetler),
        "istatistik": uretim.istatistik,
    }
    if simple_calisma is not None:
        ayrintilar["simple_clean_run"] = simple_calisma.run_id
    ctx.manifest_yaz(
        klasor, girdiler=girdiler, ciktilar=[cikti], parmak=parmak, ayrintilar=ayrintilar
    )
    yan_rapor_yaz(
        ctx,
        "links",
        {
            "run_id": ctx.run_id,
            "kaynak": KAYNAK,
            "turler": list(turler),
            "data_version": surum_tablosu,
            "db_girdi_ozeti": db.girdi_ozeti(),
            "istatistik": uretim.istatistik,
        },
    )
    ctx.gunluk.yaz("INFO", "enrich_links_bitti", source_id=KAYNAK)
    return uretim, klasor


def _ozet_yaz(uretim: Uretim, klasor: Path | None, run_id: str, dry_run: bool) -> None:
    parcalar = []
    for tur in TURLER:
        ist = uretim.istatistik.get(tur)
        if isinstance(ist, dict):
            parcalar.append(f"{tur} {ist['satir']}")
    ek = " (dry-run, hicbir sey yazilmadi)" if dry_run or klasor is None else f", run {run_id}"
    sys.stdout.write(
        f"enrich links: {uretim.istatistik['satir_toplam']} satir ({', '.join(parcalar)}){ek}\n"
    )


def komut_enrich_links(
    *,
    tur: str,
    gelen_tarih: str | None,
    dry_run: bool,
    force: bool,
    config: Path | None,
    kok: Path | None,
    baglanti: BAGLANTI | None = None,
    beklenen_ayet: int | None = BEKLENEN_AYET,
) -> int:
    """`enrich links` komutu; cikis kodunu dondurur (0 ya da 2)."""

    def govde(ctx: RunContext) -> int:
        turler = turleri_coz(tur)
        uretim, klasor = run_enrich_links(
            ctx, turler, gelen_tarih=gelen_tarih, baglanti=baglanti, beklenen_ayet=beklenen_ayet
        )
        _ozet_yaz(uretim, klasor, ctx.run_id, ctx.dry_run)
        return cikis.BASARILI

    parametreler: dict[str, object] = {"type": tur}
    if gelen_tarih is not None:
        parametreler["gelen_tarih"] = gelen_tarih
    secilen = TUR_SECENEKLERI.get(tur, TURLER)
    return komutu_yurut(
        komut="enrich links",
        adim=LINKS_ADIMI,
        kaynaklar=sorted({s for t in secilen for s in KAYNAK_GEREKSINIMI[t]}),
        config=config,
        kok=kok,
        govde=govde,
        force=force,
        dry_run=dry_run,
        parametreler=parametreler,
    )
