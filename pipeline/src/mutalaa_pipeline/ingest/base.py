"""Kaynak bagdastirici tabani (Icerik hatti §8): RawFile, StagedUnit, SourceAdapter, run_ingest.

Bagdastirici `fetch` ile ham dosyayi `data/raw` altina alir, `parse` ile kanonik metni
birimlere boler. Kanonik metin normalize edilmez (K-26). `staged` yalniz capaya gore sirali ve
zaman damgasiz yazilir; manifest en son yazilir.
"""

import json
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Final, Protocol

from mutalaa_pipeline import lineage
from mutalaa_pipeline.anchor import AnchorError, AnchorRef, parse, sort_key
from mutalaa_pipeline.export.ortak import GirdiHatasi

if TYPE_CHECKING:
    from mutalaa_pipeline.runctx import RunContext

UNITS_ADI: Final = "units.jsonl"


@dataclass(frozen=True)
class RawFile:
    path: Path
    sha256: str
    url: str | None = None


@dataclass(frozen=True)
class StagedUnit:
    anchor: str
    text: str  # kanonik metin, normalize edilmemis
    attrs: dict[str, object] = field(default_factory=dict)
    provenance: dict[str, object] = field(default_factory=dict)


class SourceAdapter(Protocol):
    source_id: str

    def fetch(self, ctx: "RunContext") -> list[RawFile]: ...

    def parse(self, ctx: "RunContext", files: list[RawFile]) -> Iterator[StagedUnit]: ...


@dataclass(frozen=True)
class IngestSonucu:
    run_id: str
    atlandi: bool
    birim_sayisi: int
    klasor: Path | None
    onceki_run_id: str | None = None


def units_satiri(source_id: str, birim: StagedUnit) -> str:
    """Bir birimin JSONL satiri: kanonik, ASCII kacisli (editor NFC'sine karsi), zaman damgasiz."""
    return (
        json.dumps(
            {
                "anchor": birim.anchor,
                "source_id": source_id,
                "text": birim.text,
                "attrs": birim.attrs,
                "provenance": birim.provenance,
            },
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    )


def staged_yaz(ctx: "RunContext", source_id: str, birimler: Iterable[StagedUnit]) -> lineage.Cikti:
    """`staged/{kaynak}/{run_id}/units.jsonl` dosyasini yazar (`--dry-run`'da yazmaz)."""
    sirali: list[tuple[AnchorRef, StagedUnit]] = []
    gorulen: set[str] = set()
    for sira, birim in enumerate(birimler, start=1):
        try:
            ref = parse(birim.anchor)
        except AnchorError:
            raise GirdiHatasi(f"birim {sira}: capa gecersiz") from None
        if birim.anchor in gorulen:
            raise GirdiHatasi(f"yinelenen capa: {birim.anchor}")
        gorulen.add(birim.anchor)
        sirali.append((ref, birim))
    sirali.sort(key=lambda cift: sort_key(cift[0]))
    veri = "".join(units_satiri(source_id, b) for _, b in sirali).encode("utf-8")
    hedef = ctx.staged_dizin(source_id) / UNITS_ADI
    if not ctx.dry_run:
        hedef.parent.mkdir(parents=True, exist_ok=True)
        hedef.write_bytes(veri)
    return lineage.Cikti(
        yol=lineage.goreli_yol(ctx.veri_kok, hedef),
        sha256=lineage.sha256_bayt(veri),
        satir=len(sirali),
    )


def _klasor_ciktilari(ctx: "RunContext", klasor: Path) -> list[lineage.Cikti]:
    """Klasordeki butun dosyalar (manifest haric), bagdastiricinin yazdiklari dahil."""
    ciktilar: list[lineage.Cikti] = []
    for yol in sorted(klasor.iterdir(), key=lambda p: p.name):
        if not yol.is_file() or yol.name in {lineage.MANIFEST_ADI, lineage.MANIFEST_ADI + ".tmp"}:
            continue
        veri = yol.read_bytes()
        satir = veri.count(b"\n") if yol.suffix == ".jsonl" else None
        ciktilar.append(
            lineage.Cikti(
                yol=lineage.goreli_yol(ctx.veri_kok, yol),
                sha256=lineage.sha256_bayt(veri),
                satir=satir,
            )
        )
    return ciktilar


def run_ingest(adapter: SourceAdapter, ctx: "RunContext") -> IngestSonucu:
    """Kaynak kaydi, `fetch`, parmak izi, `parse`, `staged`, manifest (en son)."""
    kaynak = adapter.source_id
    ctx.require_sources(kaynak)  # kayitsiz ya da gecersiz kayitta buraya gelinmez (cikis 2)
    ctx.gunluk.yaz("INFO", "ingest_basla", source_id=kaynak)

    dosyalar = adapter.fetch(ctx)
    girdiler: list[lineage.Girdi] = []
    for dosya in dosyalar:
        if lineage.sha256_dosya(dosya.path) != dosya.sha256:
            raise GirdiHatasi(f"ham dosya ozeti tutmuyor: sha256 {dosya.sha256}")
        girdiler.append(
            lineage.Girdi(yol=lineage.goreli_yol(ctx.veri_kok, dosya.path), sha256=dosya.sha256)
        )
    parmak = ctx.parmak_izi(girdiler)

    onceki = lineage.son_basarili(ctx.staged_kaynak_dizini(kaynak), ctx.adim)
    if lineage.atlanabilir(
        onceki=onceki[2] if onceki else None,
        parmak=parmak,
        git_kirli=ctx.git().kirli,
        force=ctx.force,
        veri_kok=ctx.veri_kok,
    ):
        ctx.gunluk.yaz("INFO", "ingest_atlandi", source_id=kaynak)
        ctx.sayi("atlandi", 1)
        return IngestSonucu(
            run_id=ctx.run_id,
            atlandi=True,
            birim_sayisi=0,
            klasor=None,
            onceki_run_id=onceki[0] if onceki else None,
        )

    klasor = ctx.staged_dizin(kaynak)
    units = ctx.write_staged(kaynak, adapter.parse(ctx, dosyalar))
    ctx.sayi("birim", units.satir or 0)
    if ctx.dry_run:
        ctx.gunluk.yaz("INFO", "ingest_dry_run", source_id=kaynak, sayilar={"birim": units.satir})
        return IngestSonucu(
            run_id=ctx.run_id, atlandi=False, birim_sayisi=units.satir or 0, klasor=None
        )

    ciktilar = _klasor_ciktilari(ctx, klasor)
    # Istege bagli kanca: bagdastirici manifeste eklenecek ayrintilari (ornegin satir duzeni)
    # `manifest_ayrintilari()` ile verir; parse() sonrasinda cagrilir.
    kanca = getattr(adapter, "manifest_ayrintilari", None)
    ctx.manifest_yaz(
        klasor,
        girdiler=girdiler,
        ciktilar=ciktilar,
        parmak=parmak,
        ayrintilar=kanca() if callable(kanca) else None,
    )
    ctx.gunluk.yaz("INFO", "ingest_bitti", source_id=kaynak, sayilar={"birim": units.satir})
    return IngestSonucu(
        run_id=ctx.run_id, atlandi=False, birim_sayisi=units.satir or 0, klasor=klasor
    )
