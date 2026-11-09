"""Ust veri capa adimi (A11.4, A11.5): `quran_marker` ve `page_map` satirlari (K-43).

`mutalaa anchor --source tanzil-ust-veri`: iki ust calismayi zincirler:

* `ingest tanzil --variant ust-veri` calismasinin yapi dosyalari (cuz, rub, sayfa, secde ...);
* `anchor --source tanzil-uthmani` calismasinin `words.jsonl` dosyasi (ayet basina kelime sayisi
  ve ayetin kuresel sirasi; birlestirme listesinin etkisi dahil).

ve `staged/tanzil-ust-veri/{run_id}/` altina iki dosya yazar:

`markers.jsonl` (K-43 madde 2): `kind` (cuz, hizb, rub, secde), `no` (tur icinde 1'den
kesintisiz), `anchor` (`q:{sure}:{ayet}`: baslangic ayeti, secdede secde ayeti), `secde_turu`
(yalniz secde satirinda, Tanzil'in kendi etiketi; digerlerinde null), `source_id`, `data_version`.
Hizb her dorduncu ceyrektir: hizb i = ceyrek 4(i-1)+1; 240 ceyrek `rub` olarak da saklanir.
Menzil ve ruku v1'de yuklenmez, ingest ciktisinda kalir.

`pages.jsonl` (A11.5): `page` (1..sayfa sayisi), `start_anchor` (sayfa baslangic ayetinin 1.
kelimesi), `end_anchor` (sonraki sayfanin baslangic ayetinden onceki ayetin SON kelimesi; son
sayfada kitabin son ayetinin son kelimesi), `source_id`, `data_version`. Sayfa kaynagi Tanzil
`pages` grubudur; QPC1 duzeni yalniz dogrulayicidir (QA). `volume`, `line` ... yuklemede NULL'dir.

Degerler kaynak dosyadan okunur; hicbiri hafizadan yazilmaz. Hata iletileri yalniz sayi ve capa
tasir.
"""

import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from mutalaa_pipeline import cikis, lineage
from mutalaa_pipeline.anchor import AnchorRef, Q
from mutalaa_pipeline.anchor import format as anchor_format
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.ingest.tanzil_ust_veri import KAYNAK, YAPI_DOSYALARI, yapi_oku
from mutalaa_pipeline.komut_ortak import komutu_yurut
from mutalaa_pipeline.lineage import ISARETLER_ADI, KELIMELER_ADI, SAYFALAR_ADI
from mutalaa_pipeline.runctx import RunContext
from mutalaa_pipeline.staged import dosya_yaz
from mutalaa_pipeline.zincir import (
    ANCHOR_ADIMI,
    INGEST_ADIMI,
    Calisma,
    girdi_olarak,
    girdileri_ayni,
    kelimeler_oku,
    saglam_olmali,
    son_calisma,
)

KELIME_KAYNAGI: Final = "tanzil-uthmani"
CEYREK_BASINA_HIZB: Final = 4  # hizb her dorduncu ceyrektir (K-43 madde 2)
ISARET_ANAHTARI: Final = ("kind", "no")
SAYFA_ANAHTARI: Final = ("page",)


@dataclass(frozen=True)
class AyetBilgisi:
    """Kelime dosyasindan ayet basina: kuresel sira ve kelime sayisi."""

    sira: dict[tuple[int, int], int]  # (sure, ayet) -> kuresel sira
    konum: dict[int, tuple[int, int]]  # kuresel sira -> (sure, ayet)
    kelime_sayisi: dict[tuple[int, int], int]

    @property
    def son_ayet(self) -> tuple[int, int]:
        return self.konum[max(self.konum)]


@dataclass(frozen=True)
class AnchorUstVeriSonucu:
    run_id: str
    atlandi: bool
    isaret_sayisi: int
    sayfa_sayisi: int
    klasor: Path | None
    onceki_run_id: str | None = None


def ayet_bilgisi(kelimeler: Sequence[Mapping[str, object]]) -> AyetBilgisi:
    """`words.jsonl` satirlarindan ayet basina kuresel sira ve kelime sayisi."""
    sira: dict[tuple[int, int], int] = {}
    sayi: dict[tuple[int, int], int] = {}
    for k in kelimeler:
        sure, ayet, no, idx = k.get("surah"), k.get("ayah"), k.get("word"), k.get("ayah_index")
        if not all(isinstance(d, int) and not isinstance(d, bool) for d in (sure, ayet, no, idx)):
            raise GirdiHatasi("words.jsonl: surah, ayah, word ya da ayah_index tam sayi degil")
        konum = (int(str(sure)), int(str(ayet)))
        if sira.setdefault(konum, int(str(idx))) != int(str(idx)):
            raise GirdiHatasi(f"words.jsonl: q:{konum[0]}:{konum[1]} icin ayah_index tutarsiz")
        sayi[konum] = max(sayi.get(konum, 0), int(str(no)))
    if not sira:
        raise GirdiHatasi("words.jsonl bos")
    konum_sira = {idx: konum for konum, idx in sira.items()}
    if len(konum_sira) != len(sira):
        raise GirdiHatasi("words.jsonl: iki ayet ayni ayah_index degerini tasiyor")
    return AyetBilgisi(sira=sira, konum=konum_sira, kelime_sayisi=sayi)


def _ayet_capasi(sure: int, ayet: int) -> str:
    return anchor_format(AnchorRef(Q(sure, ayet)))


def _kelime_capasi(sure: int, ayet: int, kelime: int) -> str:
    return anchor_format(AnchorRef(Q(sure, ayet, kelime)))


def _konum(satir: Mapping[str, object]) -> tuple[int, int]:
    return int(str(satir["sura"])), int(str(satir["aya"]))


def isaret_satirlari(
    yapi: Mapping[str, Sequence[Mapping[str, object]]], ayetler: AyetBilgisi, surum: str
) -> list[dict[str, object]]:
    """Yapi satirlarindan `quran_marker` satirlari (cuz, hizb, rub, secde).

    Cuz ve ceyrek sayisi kaynak dosyadan gelir; ceyrek sayisi 4'un kati olmalidir. Her baslangic
    ayeti kelime dosyasindaki ayetlerden biri olmalidir.
    """
    data_version = f"{KAYNAK}@{surum}"
    satirlar: list[dict[str, object]] = []

    def ekle(kind: str, no: int, sure: int, ayet: int, secde_turu: str | None) -> None:
        if (sure, ayet) not in ayetler.sira:
            raise GirdiHatasi(f"{kind} {no}: q:{sure}:{ayet} kelime dosyasinda yok")
        satirlar.append(
            {
                "kind": kind,
                "no": no,
                "anchor": _ayet_capasi(sure, ayet),
                "secde_turu": secde_turu,
                "source_id": KAYNAK,
                "data_version": data_version,
            }
        )

    for satir in yapi["cuz"]:
        ekle("cuz", int(str(satir["no"])), *_konum(satir), None)
    ceyrekler = yapi["rub"]
    if len(ceyrekler) % CEYREK_BASINA_HIZB != 0:
        raise GirdiHatasi(f"ceyrek sayisi {len(ceyrekler)} {CEYREK_BASINA_HIZB}'un kati degil")
    for sira, satir in enumerate(ceyrekler[::CEYREK_BASINA_HIZB], start=1):
        ekle("hizb", sira, *_konum(satir), None)
    for satir in ceyrekler:
        ekle("rub", int(str(satir["no"])), *_konum(satir), None)
    for satir in yapi["secde"]:
        tur = satir.get("type")
        if not isinstance(tur, str):
            raise GirdiHatasi(f"secde {satir['no']}: type yok")
        ekle("secde", int(str(satir["no"])), *_konum(satir), tur)
    return satirlar


def sayfa_satirlari(
    yapi: Mapping[str, Sequence[Mapping[str, object]]], ayetler: AyetBilgisi, surum: str
) -> list[dict[str, object]]:
    """Tanzil `pages` satirlarindan `page_map` satirlari (sayfa basina tek satir)."""
    data_version = f"{KAYNAK}@{surum}"
    sayfalar = yapi["sayfa"]
    satirlar: list[dict[str, object]] = []
    for i, satir in enumerate(sayfalar):
        sayfa = int(str(satir["no"]))
        bas = _konum(satir)
        if bas not in ayetler.sira:
            raise GirdiHatasi(f"sayfa {sayfa}: baslangic ayeti kelime dosyasinda yok")
        if i + 1 < len(sayfalar):
            sonraki = _konum(sayfalar[i + 1])
            if sonraki not in ayetler.sira:
                raise GirdiHatasi(f"sayfa {sayfa + 1}: baslangic ayeti kelime dosyasinda yok")
            onceki_sira = ayetler.sira[sonraki] - 1
            if onceki_sira not in ayetler.konum:
                raise GirdiHatasi(f"sayfa {sayfa}: sonraki sayfadan onceki ayet yok")
            son = ayetler.konum[onceki_sira]
        else:
            son = ayetler.son_ayet
        if ayetler.sira[son] < ayetler.sira[bas]:
            raise GirdiHatasi(f"sayfa {sayfa}: bitis ayeti baslangic ayetinden once")
        satirlar.append(
            {
                "page": sayfa,
                "start_anchor": _kelime_capasi(*bas, 1),
                "end_anchor": _kelime_capasi(*son, ayetler.kelime_sayisi[son]),
                "source_id": KAYNAK,
                "data_version": data_version,
            }
        )
    return satirlar


def yapi_satirlari(ingest: Calisma) -> dict[str, list[dict[str, object]]]:
    """Ust veri ingest calismasinin yapi dosyalari (kati JSONL, manifest ozetine karsi)."""
    sonuc: dict[str, list[dict[str, object]]] = {}
    for tur, ad in YAPI_DOSYALARI.items():
        ozet = ingest.cikti_ozeti(ad)
        if ozet is None:
            raise GirdiHatasi(f"ust veri manifestinde {ad} ozeti yok: {ingest.run_id}")
        satirlar = yapi_oku(ingest.klasor, ad, "ust veri")
        veri = (ingest.klasor / ad).read_bytes()
        if lineage.sha256_bayt(veri) != ozet:
            raise GirdiHatasi(f"ust veri {ad} ozeti manifestle tutmuyor")
        sonuc[tur] = satirlar
    return sonuc


def run_anchor_ust_veri(ctx: RunContext) -> AnchorUstVeriSonucu:
    """Kaynak kaydi, iki ust calisma, parmak izi, satirlar, manifest (en son)."""
    kayit = ctx.require_sources(KAYNAK)[KAYNAK]
    if kayit.surum is None:
        raise GirdiHatasi(f"kaynak {KAYNAK}: surum cozulemedi (TOML surum alani yok)")
    ctx.gunluk.yaz("INFO", "anchor_ust_veri_basla", source_id=KAYNAK)
    ingest = son_calisma(ctx, KAYNAK, INGEST_ADIMI, ipucu="once: ingest tanzil --variant ust-veri")
    kelime_calismasi = son_calisma(
        ctx, KELIME_KAYNAGI, ANCHOR_ADIMI, ipucu="once: anchor --source tanzil-uthmani"
    )
    saglam_olmali(ctx, ingest)
    saglam_olmali(ctx, kelime_calismasi)
    girdiler = [girdi_olarak(ingest, ad) for ad in YAPI_DOSYALARI.values()]
    girdiler.append(girdi_olarak(kelime_calismasi, KELIMELER_ADI))
    parmak = ctx.parmak_izi(girdiler)

    onceki = lineage.son_basarili(ctx.staged_kaynak_dizini(KAYNAK), ctx.adim)
    if girdileri_ayni(onceki[2] if onceki else None, girdiler) and lineage.atlanabilir(
        onceki=onceki[2] if onceki else None,
        parmak=parmak,
        git_kirli=ctx.git().kirli,
        force=ctx.force,
        veri_kok=ctx.veri_kok,
    ):
        ctx.gunluk.yaz("INFO", "anchor_ust_veri_atlandi", source_id=KAYNAK)
        ctx.sayi("atlandi", 1)
        return AnchorUstVeriSonucu(ctx.run_id, True, 0, 0, None, onceki[0] if onceki else None)

    yapi = yapi_satirlari(ingest)
    ayetler = ayet_bilgisi([k.veri for k in kelimeler_oku(kelime_calismasi, "anchor words.jsonl")])
    isaretler = isaret_satirlari(yapi, ayetler, kayit.surum)
    sayfalar = sayfa_satirlari(yapi, ayetler, kayit.surum)
    isaret_cikti = dosya_yaz(ctx, KAYNAK, ISARETLER_ADI, isaretler, ISARET_ANAHTARI)
    sayfa_cikti = dosya_yaz(ctx, KAYNAK, SAYFALAR_ADI, sayfalar, SAYFA_ANAHTARI)
    ctx.sayi("isaret", len(isaretler))
    ctx.sayi("sayfa", len(sayfalar))
    if ctx.dry_run:
        ctx.gunluk.yaz(
            "INFO",
            "anchor_ust_veri_dry_run",
            source_id=KAYNAK,
            sayilar={"isaret": len(isaretler), "sayfa": len(sayfalar)},
        )
        return AnchorUstVeriSonucu(ctx.run_id, False, len(isaretler), len(sayfalar), None)

    klasor = ctx.staged_dizin(KAYNAK)
    sayim: dict[str, int] = {}
    for satir in isaretler:
        sayim[str(satir["kind"])] = sayim.get(str(satir["kind"]), 0) + 1
    ctx.manifest_yaz(
        klasor,
        girdiler=girdiler,
        ciktilar=[isaret_cikti, sayfa_cikti],
        parmak=parmak,
        ayrintilar={
            "kaynak": KAYNAK,
            "data_version": f"{KAYNAK}@{kayit.surum}",
            "ust_veri_run": ingest.run_id,
            "kelime_run": kelime_calismasi.run_id,
            "isaret": sayim,
            "sayfa": len(sayfalar),
        },
    )
    ctx.gunluk.yaz("INFO", "anchor_ust_veri_bitti", source_id=KAYNAK)
    return AnchorUstVeriSonucu(ctx.run_id, False, len(isaretler), len(sayfalar), klasor)


def komut_anchor_ust_veri(
    *, dry_run: bool, force: bool, config: Path | None, kok: Path | None
) -> int:
    """`anchor --source tanzil-ust-veri` komutu; cikis kodunu dondurur."""

    def govde(ctx: RunContext) -> int:
        sonuc = run_anchor_ust_veri(ctx)
        if sonuc.atlandi:
            ozet = f"atlandi (parmak izi onceki calistirmayla ayni, run {sonuc.onceki_run_id})"
        elif ctx.dry_run:
            ozet = (
                f"{sonuc.isaret_sayisi} isaret, {sonuc.sayfa_sayisi} sayfa"
                " (dry-run, hicbir sey yazilmadi)"
            )
        else:
            ozet = f"{sonuc.isaret_sayisi} isaret, {sonuc.sayfa_sayisi} sayfa, run {sonuc.run_id}"
        sys.stdout.write(f"anchor {KAYNAK}: {ozet}\n")
        return cikis.BASARILI

    return komutu_yurut(
        komut=f"anchor --source {KAYNAK}",
        adim=ANCHOR_ADIMI,
        kaynaklar=[KAYNAK],
        config=config,
        kok=kok,
        govde=govde,
        force=force,
        dry_run=dry_run,
        parametreler={"source": KAYNAK},
    )
