# ruff: noqa: RUF001
"""Sentetik fiksturler (A13.6): `test-kucuk` ve `test-tefsir-ornek` icin belirlenimci uretec.

`mutalaa ingest fikstur --source <slug>`: disaridan dosya almaz (`data/gelen` ve `data/raw` bu
komutta kullanilmaz); birimleri kodla uretir ve `staged/{slug}/{run_id}/units.jsonl` olarak yazar.
Ayni surumde ayni baytlar cikar (zaman, rastgelelik, ortam yok). Metin acikca sentetiktir
("Deneme paragrafi N ..."); hicbir Kur'an, meal, tefsir, hadis ya da Risale metnine benzetilmez.

Ham dosya olmadigi icin manifestin `girdiler` listesi bos kalir; parmak izine uretilen
`units.jsonl` baytlarinin ozeti `parametreler.icerik_sha256` olarak girer (uretec degisince
parmak izi de degisir). Kendi urettigimiz metin oldugu icin her metne uretimde bir kez
`kanonik_metin` (K-35 madde 7: NFC dahil) uygulanir; sonraki adimlar metne dokunmaz.

`test-ses` birim uretmez (icerigi A27.2'de gelir): bu komut onu GirdiHatasi ile reddeder; kaynak
satiri `export pg --source test-ses` ile yuklenir.

Birim alanlari (ingest `attrs`): `kind` (`kitap` ya da `tefsir`), kitapta `parent_path` (bolum yolu,
ornegin `k:test-kucuk:bolum-1`; capa degildir, icindekiler yoludur). `ayah_lo`/`ayah_hi` capadan
anchor adiminda turetilir.
"""

import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from mutalaa_pipeline import cikis, lineage
from mutalaa_pipeline.anchor import kanonik_metin, parse, sort_key
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.ingest.base import RawFile, StagedUnit, run_ingest, units_satiri
from mutalaa_pipeline.komut_ortak import komutu_yurut
from mutalaa_pipeline.runctx import RunContext

KITAP: Final = "test-kucuk"
TEFSIR: Final = "test-tefsir-ornek"
SES: Final = "test-ses"
# Birim ureten fiksturler ve birim turleri (`icerik.unit_kind`).
KAYNAKLAR: Final = (KITAP, TEFSIR)
KIND: Final = {KITAP: "kitap", TEFSIR: "tefsir"}
# Yalniz `source` satiri yuklenen fiksturler: zincir, QA ve birim yok (export pg).
YALNIZ_KAYNAK: Final = (SES,)
URETEC_SURUMU: Final = "1"
INGEST_ADIMI: Final = "ingest"

KITAP_ONEK: Final = "k:test-kucuk"
# Her bolumde 6 paragraf. "Isik" yalniz bolum-1 p3'te vardir (Maestro arama akisi `isik` arar);
# bolum-1 p5 Turkce I/i ayrimini sinayan cumleyi tasir ("Isik" sozcugu gecmez).
KITAP_BOLUMLERI: Final = {
    "bolum-1": (
        "yalnızca sistem denemesi içindir.",
        "okuma ekranının satır kaydırmasını sınamak için biraz daha uzun yazılmıştır;"
        " bu cümle yalnızca doldurma amacı taşır.",
        "Işık sözcüğünü içerir ve arama denemesi için yazılmıştır.",
        "Bu paragraf kısa tutuldu.",
        "İlk ılık sabah için İ ve ı harfleri bir arada kullanıldı.",
        "Birinci bölümün son paragrafı, sentetik veridir.",
    ),
    "bolum-2": (
        "ikinci bölümün ilk paragrafıdır ve yalnızca deneme içindir.",
        "Sayfa geçişini sınamak için eklenmiş sentetik bir paragraftır.",
        "Bu paragrafta özel bir sözcük yoktur.",
        "Kısa paragraf.",
        "Liste ve başlık denemesi için ayrılmıştır, başka bir amacı yoktur.",
        "İkinci bölümün son paragrafı, sentetik veridir.",
    ),
}
# (sure, ilk, son, paragraf sayisi): yalniz capa ve ayet araligi denemesi icin.
TEFSIR_ARALIKLARI: Final = ((1, 1, 7, 2), (2, 255, 257, 3), (2, 256, 256, 1), (114, 1, 6, 1))
TEFSIR_ESER: Final = "test-ornek"
TEFSIR_EKLERI: Final = (
    "sentetik bir tefsir örneğidir; kapsadığı aralık yalnızca çapa denemesi içindir.",
    "ikinci paragraf, aynı aralığın başka bir sentetik parçasıdır.",
    "üçüncü paragraf, paragraf numarasını sınamak için eklenmiştir.",
)


@dataclass(frozen=True)
class FiksturBirimi:
    anchor: str
    text: str
    kind: str
    parent_path: str | None


def kitap_birimleri() -> list[FiksturBirimi]:
    birimler: list[FiksturBirimi] = []
    for bolum, ekler in KITAP_BOLUMLERI.items():
        yol = f"{KITAP_ONEK}:{bolum}"
        for n, ek in enumerate(ekler, start=1):
            birimler.append(
                FiksturBirimi(
                    anchor=f"{yol}:p{n}",
                    text=kanonik_metin(f"Deneme paragrafı {n} {ek}"),
                    kind=KIND[KITAP],
                    parent_path=yol,
                )
            )
    return birimler


def tefsir_birimleri() -> list[FiksturBirimi]:
    birimler: list[FiksturBirimi] = []
    for sure, ilk, son, sayi in TEFSIR_ARALIKLARI:
        for n in range(1, sayi + 1):
            birimler.append(
                FiksturBirimi(
                    anchor=f"tf:{TEFSIR_ESER}:{sure}-{ilk}-{son}:p{n}",
                    text=kanonik_metin(f"Deneme paragrafı {n} {TEFSIR_EKLERI[n - 1]}"),
                    kind=KIND[TEFSIR],
                    parent_path=None,
                )
            )
    return birimler


def birimler(slug: str) -> list[FiksturBirimi]:
    """Fikstur birimleri (uretim sirasi sabit). Birim uretmeyen ya da bilinmeyen kaynak: hata."""
    if slug == KITAP:
        return kitap_birimleri()
    if slug == TEFSIR:
        return tefsir_birimleri()
    if slug in YALNIZ_KAYNAK:
        raise GirdiHatasi(f"{slug} birim uretmez (yalniz kaynak satiri: export pg --source {slug})")
    raise GirdiHatasi("ingest fikstur: bilinmeyen fikstur kaynagi (test-kucuk, test-tefsir-ornek)")


def staged_birimleri(slug: str) -> list[StagedUnit]:
    """Ingest `units.jsonl` birimleri: `attrs` icinde `kind` (ve kitapta `parent_path`)."""
    sonuc: list[StagedUnit] = []
    for satir, birim in enumerate(birimler(slug), start=1):
        attrs: dict[str, object] = {"kind": birim.kind}
        if birim.parent_path is not None:
            attrs["parent_path"] = birim.parent_path
        sonuc.append(
            StagedUnit(
                anchor=birim.anchor,
                text=birim.text,
                attrs=attrs,
                provenance={"uretec": "fikstur", "uretec_surumu": URETEC_SURUMU, "line": satir},
            )
        )
    return sonuc


def icerik_baytlari(slug: str) -> bytes:
    """Uretecin `units.jsonl` baytlari (staged_yaz ile ayni satir bicimi, capa sirasiyla)."""
    sirali = sorted(staged_birimleri(slug), key=lambda b: sort_key(parse(b.anchor)))
    return "".join(units_satiri(slug, b) for b in sirali).encode("utf-8")


class FiksturBagdastirici:
    """`SourceAdapter`: `fetch` dosya almaz, `parse` birimleri uretir."""

    def __init__(self, source_id: str) -> None:
        self.source_id = source_id

    def fetch(self, ctx: RunContext) -> list[RawFile]:
        return []

    def parse(self, ctx: RunContext, files: list[RawFile]) -> Iterator[StagedUnit]:
        yield from staged_birimleri(self.source_id)

    def manifest_ayrintilari(self) -> dict[str, object]:
        return {
            "kaynak": self.source_id,
            "uretec_surumu": URETEC_SURUMU,
            "kind": KIND[self.source_id],
            "birim": len(birimler(self.source_id)),
        }


def komut_ingest_fikstur(
    *, source: str, dry_run: bool, force: bool, config: Path | None, kok: Path | None
) -> int:
    """`ingest fikstur` komutu; cikis kodunu dondurur (rapor `data/reports/{run_id}.json`)."""

    def govde(ctx: RunContext) -> int:
        sonuc = run_ingest(FiksturBagdastirici(source), ctx)
        if sonuc.atlandi:
            ozet = f"atlandi (parmak izi onceki calistirmayla ayni, run {sonuc.onceki_run_id})"
        elif ctx.dry_run:
            ozet = f"{sonuc.birim_sayisi} birim (dry-run, hicbir sey yazilmadi)"
        else:
            ozet = f"{sonuc.birim_sayisi} birim, run {sonuc.run_id}"
        sys.stdout.write(f"ingest fikstur {source}: {ozet}\n")
        return cikis.BASARILI

    # Uretilen baytlarin ozeti parmak izine girer: uretec degisirse atlama olmaz.
    try:
        parametreler: dict[str, object] = {
            "source": source,
            "uretec_surumu": URETEC_SURUMU,
            "icerik_sha256": lineage.sha256_bayt(icerik_baytlari(source)),
        }
    except GirdiHatasi as hata:
        sys.stderr.write(f"hata: {hata}\n")
        return cikis.GIRDI_HATASI
    return komutu_yurut(
        komut=f"ingest fikstur --source {source}",
        adim=INGEST_ADIMI,
        kaynaklar=[source],
        config=config,
        kok=kok,
        govde=govde,
        force=force,
        dry_run=dry_run,
        parametreler=parametreler,
    )
