"""Turkce kelime -> Arapca kok adimi (A18.2, K-51 madde 9): `mutalaa enrich tr-roots`.

Zincirlenen ust calismalar (hepsi manifestli ve ciktilari saglam):

* her `--source` meali icin son `anchor` calismasinin `units.jsonl` dosyasi (metin);
* `qac-morfoloji` son `anchor` (`enrich morphology`) calismasinin `roots.jsonl` ve `lemmas.jsonl`
  dosyalari (kok ve lemma envanteri);
* `data/gelen/kaikki-tr/<tarih>/` dokumleri (SHA256SUMS ile dogrulanir, `data/raw`'a alinmaz).

`staged/kaikki-tr/{run_id}/` altina iki dosya yazar (ASCII kacisli, sirali, LF; zaman damgasi yok):
`tr_lemmas.jsonl` ve `tr_forms.jsonl` (`enrich/tr_roots/uret.py`) ve her kosuda yeniden uretilir.
Adim adi `enrich`tir (`TR_ROOTS_ADIMI`); `export pg --source kaikki-tr` ve `qa run --source
kaikki-tr` son `enrich` calismasini arar. Istatistik raporu `data/reports/{run_id}-tr-roots.json`.

Dil modeli ve ag cagrisi yoktur (K-50). Hata iletileri yalniz sayi, sira ve ozet tasir.
"""

import re
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final, cast

from mutalaa_pipeline import cikis, lineage
from mutalaa_pipeline.enrich.rapor import yan_rapor_yaz
from mutalaa_pipeline.enrich.tr_roots.eslesme import QacEnvanteri
from mutalaa_pipeline.enrich.tr_roots.etimoloji import DIL_OTA, DIL_TR, KaikkiIndeksi, dokum_oku
from mutalaa_pipeline.enrich.tr_roots.lemmatize import Lemmatizer, ZeyrekLemmatizer, zeyrek_surumu
from mutalaa_pipeline.enrich.tr_roots.politika import (
    POLITIKA_ADI,
    POLITIKA_SURUMU,
    YONTEM_ADI,
    YONTEM_SURUMU,
)
from mutalaa_pipeline.enrich.tr_roots.uret import (
    FORMLAR_ADI,
    LEMMALAR_ADI,
    VARSAYILAN_MIN_SIKLIK,
    KaynakMetni,
    Uretim,
    uret,
)
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.komut_ortak import komutu_yurut
from mutalaa_pipeline.lineage import KOKLER_ADI
from mutalaa_pipeline.lineage import LEMMALAR_ADI as QAC_LEMMALAR_ADI
from mutalaa_pipeline.runctx import RunContext
from mutalaa_pipeline.staged import dosya_yaz
from mutalaa_pipeline.zincir import (
    ANCHOR_ADIMI,
    dosya_oku,
    girdi_olarak,
    girdileri_ayni,
    saglam_olmali,
    son_calisma,
    units_oku,
)

KAYNAK: Final = "kaikki-tr"
QAC_KAYNAGI: Final = "qac-morfoloji"
MEAL_KAYNAKLARI: Final = ("elmalili-meal", "elmalili-sade-meal")
TR_ROOTS_ADIMI: Final = "enrich"
TR_DOSYASI: Final = "kaikki.org-dictionary-Turkish.jsonl.gz"
OTA_DOSYASI: Final = "kaikki.org-dictionary-OttomanTurkish.jsonl"
GELEN_KLASORU: Final = "gelen"
NLTK_KAYNAGI: Final = "nltk-punkt"
TARIH_DESENI: Final = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
OZET_SATIRI: Final = re.compile(r"(?P<ozet>[0-9a-f]{64}) [ *](?P<ad>[A-Za-z0-9._-]+)")


@dataclass(frozen=True)
class AdimSonucu:
    run_id: str
    atlandi: bool
    uretim: Uretim | None
    klasor: Path | None
    onceki_run_id: str | None = None


def _tarih_klasoru(kok: Path, tarih: str | None, ad: str) -> Path:
    """`data/gelen/<ad>/<tarih>` (verilmezse en yenisi)."""
    taban = kok / GELEN_KLASORU / ad
    if tarih is not None:
        if TARIH_DESENI.fullmatch(tarih) is None:
            raise GirdiHatasi("--gelen-tarih YYYY-AA-GG olmali")
        yol = taban / tarih
        if not yol.is_dir():
            raise GirdiHatasi(f"data/gelen/{ad}/<tarih> klasoru yok")
        return yol
    adaylar = (
        sorted(p for p in taban.iterdir() if p.is_dir() and TARIH_DESENI.fullmatch(p.name))
        if taban.is_dir()
        else []
    )
    if not adaylar:
        raise GirdiHatasi(f"data/gelen/{ad}/<tarih> klasoru yok")
    return adaylar[-1]


def ozetler_oku(klasor: Path) -> dict[str, str]:
    """`SHA256SUMS` dosyasi: dosya adi -> SHA-256 (sha256sum bicimi)."""
    yol = klasor / "SHA256SUMS"
    try:
        metin = yol.read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError):
        raise GirdiHatasi("SHA256SUMS okunamadi") from None
    sonuc: dict[str, str] = {}
    for satir in metin.splitlines():
        if not satir.strip():
            continue
        e = OZET_SATIRI.fullmatch(satir.strip())
        if e is None:
            raise GirdiHatasi("SHA256SUMS satiri gecersiz")
        sonuc[e.group("ad")] = e.group("ozet")
    return sonuc


def kaikki_dosyalari(ctx: RunContext, tarih: str | None) -> tuple[Path, Path, list[lineage.Girdi]]:
    """Iki dokumun yolu ve girdileri; SHA-256 degerleri `SHA256SUMS` ile tutmalidir."""
    klasor = _tarih_klasoru(ctx.veri_kok, tarih, KAYNAK)
    ozetler = ozetler_oku(klasor)
    girdiler: list[lineage.Girdi] = []
    for ad in (TR_DOSYASI, OTA_DOSYASI):
        yol = klasor / ad
        if not yol.is_file():
            raise GirdiHatasi(f"kaikki dokumu yok: {ad}")
        ozet = lineage.sha256_dosya(yol)
        if ozetler.get(ad) != ozet:
            raise GirdiHatasi(f"kaikki dokumu SHA256SUMS ile tutmuyor: {ad}")
        girdiler.append(lineage.Girdi(lineage.goreli_yol(ctx.veri_kok, yol), ozet))
    return klasor / TR_DOSYASI, klasor / OTA_DOSYASI, girdiler


def _nltk_klasoru(ctx: RunContext) -> Path:
    """`data/gelen/nltk-punkt/<en yeni tarih>/nltk_data` (proje ici)."""
    klasor = _tarih_klasoru(ctx.veri_kok, None, NLTK_KAYNAGI) / "nltk_data"
    if not klasor.is_dir():
        raise GirdiHatasi("NLTK_DATA klasoru yok (data/gelen/nltk-punkt/<tarih>/nltk_data)")
    return klasor


def run_enrich_tr_roots(
    ctx: RunContext,
    meal_kaynaklari: Sequence[str],
    *,
    min_sik: int = VARSAYILAN_MIN_SIKLIK,
    gelen_tarih: str | None = None,
    lemmatizer_kur: Callable[[], Lemmatizer] | None = None,
) -> AdimSonucu:
    """Kaynak kayitlari, ust calismalar, parmak izi, uretim, dosyalar, manifest (en son)."""
    mealler = sorted(dict.fromkeys(meal_kaynaklari))
    if not mealler or any(m not in MEAL_KAYNAKLARI for m in mealler):
        raise GirdiHatasi(f"--source {', '.join(MEAL_KAYNAKLARI)} degerlerinden olmali")
    if min_sik < 1:
        raise GirdiHatasi("--min-freq 1 ya da daha buyuk olmali")
    kayitlar = ctx.require_sources((KAYNAK, QAC_KAYNAGI, *mealler))
    surum = kayitlar[KAYNAK].surum
    if surum is None:
        raise GirdiHatasi(f"{KAYNAK}: kaynak kaydinda surum yok")
    ctx.gunluk.yaz("INFO", "enrich_tr_roots_basla", source_id=KAYNAK)

    meal_calismalari = {
        m: son_calisma(ctx, m, ANCHOR_ADIMI, ipucu=f"once: anchor --source {m}") for m in mealler
    }
    qac = son_calisma(ctx, QAC_KAYNAGI, ANCHOR_ADIMI, ipucu="once: enrich morphology")
    for calisma in (*meal_calismalari.values(), qac):
        saglam_olmali(ctx, calisma)
    tr_yolu, ota_yolu, kaikki_girdileri = kaikki_dosyalari(ctx, gelen_tarih)
    girdiler = [
        *(girdi_olarak(c) for c in meal_calismalari.values()),
        girdi_olarak(qac, KOKLER_ADI),
        girdi_olarak(qac, QAC_LEMMALAR_ADI),
        *kaikki_girdileri,
    ]
    parmak = ctx.parmak_izi(girdiler)
    onceki = lineage.son_basarili(ctx.staged_kaynak_dizini(KAYNAK), ctx.adim)
    onceki_manifest = onceki[2] if onceki else None
    if girdileri_ayni(onceki_manifest, girdiler) and lineage.atlanabilir(
        onceki=onceki_manifest,
        parmak=parmak,
        git_kirli=ctx.git().kirli,
        force=ctx.force,
        veri_kok=ctx.veri_kok,
    ):
        ctx.gunluk.yaz("INFO", "enrich_tr_roots_atlandi", source_id=KAYNAK)
        ctx.sayi("atlandi", 1)
        return AdimSonucu(ctx.run_id, True, None, None, onceki[0] if onceki else None)

    metinler: list[KaynakMetni] = []
    for m, calisma in meal_calismalari.items():
        satirlar = units_oku(calisma, f"{m} units.jsonl")
        metinler.append(
            KaynakMetni(
                m,
                [(s.metin("anchor"), s.metin("text")) for s in satirlar if s.metin("text") != ""],
            )
        )
    env = QacEnvanteri.kur(
        (s.veri for s in dosya_oku(qac, KOKLER_ADI, "qac roots.jsonl")),
        (s.veri for s in dosya_oku(qac, QAC_LEMMALAR_ADI, "qac lemmas.jsonl")),
    )
    indeks = KaikkiIndeksi(surum)
    tr_madde = dokum_oku(tr_yolu, DIL_TR, indeks)
    ota_madde = dokum_oku(ota_yolu, DIL_OTA, indeks)
    lemmatizer = (
        lemmatizer_kur() if lemmatizer_kur is not None else ZeyrekLemmatizer(_nltk_klasoru(ctx))
    )
    data_version = f"{KAYNAK}@{surum}/politika@{POLITIKA_SURUMU}"
    uretim = uret(metinler, lemmatizer, indeks, env, min_sik=min_sik, data_version=data_version)
    ist = uretim.istatistik
    siniflar = cast("dict[str, dict[str, int | float]]", ist["siniflar"])
    for ad, deger in siniflar.items():
        ctx.sayi(f"tur_{ad}", int(deger["tur"]))
        ctx.sayi(f"token_{ad}", int(deger["token"]))
    ctx.sayi("tur", int(str(ist["tur"])))
    ctx.sayi("token", int(str(ist["token"])))
    ctx.sayi("tr_lemma", len(uretim.lemma_satirlari))
    if ctx.dry_run:
        ctx.gunluk.yaz("INFO", "enrich_tr_roots_dry_run", source_id=KAYNAK)
        return AdimSonucu(ctx.run_id, False, uretim, None)

    ciktilar = [
        dosya_yaz(ctx, KAYNAK, LEMMALAR_ADI, uretim.lemma_satirlari, ("lemma",)),
        dosya_yaz(ctx, KAYNAK, FORMLAR_ADI, uretim.form_satirlari, ("form",)),
    ]
    klasor = ctx.staged_dizin(KAYNAK)
    ctx.manifest_yaz(
        klasor,
        girdiler=girdiler,
        ciktilar=ciktilar,
        parmak=parmak,
        ayrintilar={
            "kaynak": KAYNAK,
            "surum": surum,
            "data_version": data_version,
            "politika": POLITIKA_ADI,
            "politika_surumu": POLITIKA_SURUMU,
            "yontem": YONTEM_ADI,
            "yontem_surumu": YONTEM_SURUMU,
            "min_siklik": min_sik,
            "mealler": mealler,
            "meal_run": {m: c.run_id for m, c in meal_calismalari.items()},
            "qac_run": qac.run_id,
            "zeyrek_surumu": zeyrek_surumu(),
            "kaikki_madde": {"tr": tr_madde, "ota": ota_madde},
            "sayilar": {
                "tur": ist["tur"],
                "token": ist["token"],
                "tr_lemma": len(uretim.lemma_satirlari),
                "tur_siniflari": {a: d["tur"] for a, d in siniflar.items()},
                "token_siniflari": {a: d["token"] for a, d in siniflar.items()},
                "lemma": ist["lemma"],
            },
        },
    )
    yan_rapor_yaz(
        ctx,
        "tr-roots",
        {
            "run_id": ctx.run_id,
            "kaynak": KAYNAK,
            "surum": surum,
            "politika": POLITIKA_ADI,
            "politika_surumu": POLITIKA_SURUMU,
            "min_siklik": min_sik,
            "mealler": mealler,
            "zeyrek_surumu": zeyrek_surumu(),
            "istatistik": ist,
        },
    )
    ctx.gunluk.yaz("INFO", "enrich_tr_roots_bitti", source_id=KAYNAK)
    return AdimSonucu(ctx.run_id, False, uretim, klasor)


def _ozet_yaz(sonuc: AdimSonucu, dry_run: bool) -> None:
    if sonuc.atlandi:
        onceki = sonuc.onceki_run_id
        sys.stdout.write(f"enrich tr-roots: atlandi (parmak izi onceki ile ayni, run {onceki})\n")
        return
    assert sonuc.uretim is not None
    ist = sonuc.uretim.istatistik
    siniflar = cast("dict[str, dict[str, int | float]]", ist["siniflar"])
    parcalar = ", ".join(
        f"{ad} {d['tur']} tur / {d['token']} token ({d['token_yuzde']}%)"
        for ad, d in siniflar.items()
    )
    ek = " (dry-run, hicbir sey yazilmadi)" if dry_run else f", run {sonuc.run_id}"
    sys.stdout.write(
        f"enrich tr-roots: {ist['tur']} tur, {ist['token']} token; {parcalar}; "
        f"{len(sonuc.uretim.lemma_satirlari)} lemma satiri{ek}\n"
    )


def komut_enrich_tr_roots(
    *,
    kaynaklar: Sequence[str],
    min_sik: int,
    gelen_tarih: str | None,
    dry_run: bool,
    force: bool,
    config: Path | None,
    kok: Path | None,
    lemmatizer_kur: Callable[[], Lemmatizer] | None = None,
) -> int:
    """`enrich tr-roots` komutu; cikis kodunu dondurur."""

    def govde(ctx: RunContext) -> int:
        sonuc = run_enrich_tr_roots(
            ctx,
            kaynaklar,
            min_sik=min_sik,
            gelen_tarih=gelen_tarih,
            lemmatizer_kur=lemmatizer_kur,
        )
        _ozet_yaz(sonuc, ctx.dry_run)
        return cikis.BASARILI

    parametreler: dict[str, object] = {
        "source": sorted(dict.fromkeys(kaynaklar)),
        "min_freq": min_sik,
    }
    if gelen_tarih is not None:
        parametreler["gelen_tarih"] = gelen_tarih
    return komutu_yurut(
        komut="enrich tr-roots",
        adim=TR_ROOTS_ADIMI,
        kaynaklar=[KAYNAK, QAC_KAYNAGI, *sorted(dict.fromkeys(kaynaklar))],
        config=config,
        kok=kok,
        govde=govde,
        force=force,
        dry_run=dry_run,
        parametreler=parametreler,
    )
