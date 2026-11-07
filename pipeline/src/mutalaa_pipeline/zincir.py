"""Hat adimlari arasindaki zincir: staged calistirmalarini bulma ve dogrulama (Icerik hatti §5).

`ingest -> normalize -> anchor` zincirinin her halkasi bir oncekinin `units.jsonl` ozetine bagli
yazilir: manifest `girdiler` listesinde `staged/{kaynak}/{run_id}/units.jsonl` yolu, ozeti ve
`ust_run_id` bulunur. `export pg` (export/pg.py `_zincir`) bu bicimi bekler. Bu modul zinciri
okuyan adimlar (normalize, anchor, qa) icindir; veritabanina dokunmaz.

Hata iletileri yalniz adim adi, kaynak kimligi, run_id ve dosya adi tasir.
"""

import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from mutalaa_pipeline import lineage
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.lineage import OZET_DESENI, RUN_ID_DESENI, UNITS_ADI
from mutalaa_pipeline.runctx import RAW_KLASORU, STAGED_KLASORU, RunContext
from mutalaa_pipeline.sources.kayit import SLUG_DESENI
from mutalaa_pipeline.staged import Satir, satirlari_oku

INGEST_ADIMI: Final = "ingest"
NORMALIZE_ADIMI: Final = "normalize"
ANCHOR_ADIMI: Final = "anchor"
RAW_ONEK: Final = RAW_KLASORU + "/"
# raw/{kaynak}/{tarih}/{dosya}: tarih ve dosya adi bir yol parcasidir ("." ve ".." olamaz).
YOL_PARCASI: Final = re.compile(r"(?!\.{1,2}\Z)[A-Za-z0-9._-]+")


@dataclass(frozen=True)
class Calisma:
    """Manifestli bir staged calistirmasi."""

    run_id: str
    adim: str
    source_id: str
    klasor: Path
    manifest: dict[str, object]

    def goreli(self, ad: str = UNITS_ADI) -> str:
        """Dosyanin veri kokune gore yolu: `staged/{kaynak}/{run_id}/{ad}`."""
        return f"{STAGED_KLASORU}/{self.source_id}/{self.run_id}/{ad}"

    def cikti_ozeti(self, ad: str = UNITS_ADI) -> str | None:
        """Manifestin `ciktilar` listesindeki dosya ozeti (yoksa None)."""
        ciktilar = self.manifest.get("ciktilar")
        if isinstance(ciktilar, list):
            for kayit in ciktilar:
                if isinstance(kayit, dict):
                    yol, ozet = kayit.get("yol"), kayit.get("sha256")
                    if yol == self.goreli(ad) and isinstance(ozet, str):
                        return ozet
        return None

    def ayrinti(self, ad: str) -> object | None:
        """Manifestin `ayrintilar` alanindaki bir deger."""
        ayrintilar = self.manifest.get("ayrintilar")
        if isinstance(ayrintilar, dict):
            return ayrintilar.get(ad)
        return None


def run_id_gecerli(deger: str) -> bool:
    return RUN_ID_DESENI.fullmatch(deger) is not None


def girdiler(manifest: Mapping[str, object]) -> list[tuple[str, str | None]]:
    """Manifestin `girdiler` listesi: `(yol, sha256)` ciftleri, kayit sirasinda."""
    kayitlar = manifest.get("girdiler")
    if not isinstance(kayitlar, list):
        return []
    sonuc: list[tuple[str, str | None]] = []
    for kayit in kayitlar:
        if isinstance(kayit, dict) and isinstance(kayit.get("yol"), str):
            ozet = kayit.get("sha256")
            sonuc.append((str(kayit["yol"]), ozet if isinstance(ozet, str) else None))
    return sonuc


def calismalar(ctx: RunContext, source_id: str, adim: str) -> list[Calisma]:
    """`staged/{kaynak}` altinda manifesti olan `adim` calistirmalari, run_id sirasinda."""
    return [
        Calisma(run_id, adim, source_id, klasor, manifest)
        for run_id, klasor, manifest in lineage.calismalar(ctx.staged_kaynak_dizini(source_id))
        if manifest.get("adim") == adim
    ]


def son_calisma(ctx: RunContext, source_id: str, adim: str, *, ipucu: str) -> Calisma:
    """Manifestli en son `adim` calistirmasi; yoksa `GirdiHatasi` (ipucu: once hangi komut)."""
    kayitlar = calismalar(ctx, source_id, adim)
    if not kayitlar:
        raise GirdiHatasi(f"{source_id} icin manifestli {adim} calistirmasi yok ({ipucu})")
    return kayitlar[-1]


def calisma_bul(ctx: RunContext, source_id: str, run_id: str, adim: str) -> Calisma:
    """Verilen `run_id` ile manifestli `adim` calistirmasi; yoksa `GirdiHatasi`."""
    if not run_id_gecerli(run_id):
        raise GirdiHatasi("--run bir UUID degil")
    for kayit in calismalar(ctx, source_id, adim):
        if kayit.run_id == run_id:
            return kayit
    raise GirdiHatasi(f"--run icin manifestli {adim} calistirmasi yok")


def onceki_calisma(
    ctx: RunContext,
    source_id: str,
    adim: str,
    *,
    once: str | None = None,
    kabul: Callable[[Calisma], bool] | None = None,
) -> Calisma | None:
    """`once` kimliginden kucuk (yoksa en yeni), ciktilari saglam, manifestli son calisma.

    `kabul` verilirse yalniz onu saglayan calismalar aday olur (ornegin QA'dan gecmis olanlar).
    """
    for kayit in reversed(calismalar(ctx, source_id, adim)):
        if once is not None and kayit.run_id >= once:
            continue
        if not lineage.ciktilar_saglam(ctx.veri_kok, kayit.manifest):
            continue
        if kabul is None or kabul(kayit):
            return kayit
    return None


def saglam_olmali(ctx: RunContext, calisma: Calisma) -> None:
    """Calismanin her ciktisi var ve SHA-256 degeri tutuyor olmali; aksi halde `GirdiHatasi`."""
    if not lineage.ciktilar_saglam(ctx.veri_kok, calisma.manifest):
        raise GirdiHatasi(
            f"{calisma.adim} calistirmasinin ciktilari saglam degil: {calisma.source_id}"
            f" {calisma.run_id}"
        )


def girdileri_ayni(onceki: Mapping[str, object] | None, girdiler: Sequence[lineage.Girdi]) -> bool:
    """Onceki calismanin manifest girdileri `(yol, sha256, ust_run_id)` simdikilerle ayni mi.

    Parmak izi `run_id` icermez (yalniz dosya adi ve ozet). Atlama kararinda ayrica cikti halen
    en son ust calismalara bagli olmalidir; aksi halde zincir (`export pg`) eski bir ingest'e
    bagli kalir. Ust calisma ayni ciktiyla yeniden kosulmus olabilir (ornegin `--force`).
    """
    if onceki is None:
        return False
    kayitlar = onceki.get("girdiler")
    if not isinstance(kayitlar, list):
        return False
    bulunan = {
        (k.get("yol"), k.get("sha256"), k.get("ust_run_id"))
        for k in kayitlar
        if isinstance(k, dict)
    }
    beklenen = {(g.yol, g.sha256, g.ust_run_id) for g in girdiler}
    return len(kayitlar) == len(girdiler) and bulunan == beklenen


def girdi_olarak(calisma: Calisma, ad: str = UNITS_ADI) -> lineage.Girdi:
    """Sonraki adimin manifest girdisi: calismanin ciktisi, ozeti ve `ust_run_id`'si."""
    ozet = calisma.cikti_ozeti(ad)
    if ozet is None:
        raise GirdiHatasi(f"{calisma.adim} manifestinde {ad} ozeti yok: {calisma.run_id}")
    return lineage.Girdi(yol=calisma.goreli(ad), sha256=ozet, ust_run_id=calisma.run_id)


def units_oku(calisma: Calisma, etiket: str) -> list[Satir]:
    """Calismanin `units.jsonl` dosyasini, manifestteki ozetle dogrulayarak okur."""
    try:
        veri = (calisma.klasor / UNITS_ADI).read_bytes()
    except OSError:
        raise GirdiHatasi(f"{etiket}: units.jsonl okunamadi") from None
    if lineage.sha256_bayt(veri) != calisma.cikti_ozeti():
        raise GirdiHatasi(f"{etiket}: units.jsonl ozeti manifestle tutmuyor")
    return satirlari_oku(veri, etiket)


def ust_calismalar(ctx: RunContext, calisma: Calisma) -> list[Calisma]:
    """Manifest `girdiler` icindeki `staged/{kaynak}/{run_id}/{ad}` yollarinin calistirmalari.

    Her halkada girdinin kayitli ozeti, ust calismanin o dosya icin yazdigi ozetle tutmalidir.
    `raw/...` girdileri atlanir. Sira, girdilerin manifestteki sirasidir; ayni calisma bir kez.
    """
    sonuc: list[Calisma] = []
    gorulen: set[str] = set()
    for yol, ozet in girdiler(calisma.manifest):
        parcalar = yol.split("/")
        if len(parcalar) != 4 or parcalar[0] != STAGED_KLASORU:
            continue
        _, kaynak, run_id, ad = parcalar
        if SLUG_DESENI.fullmatch(kaynak) is None or not run_id_gecerli(run_id):
            raise GirdiHatasi(f"zincirde gecersiz girdi yolu: {calisma.adim} {calisma.run_id}")
        klasor = ctx.staged_kaynak_dizini(kaynak) / run_id
        manifest = lineage.manifest_oku(klasor)
        adim = manifest.get("adim") if manifest is not None else None
        if manifest is None or manifest.get("run_id") != run_id or not isinstance(adim, str):
            raise GirdiHatasi(f"zincirde manifesti olmayan calistirma: {run_id}")
        ust = Calisma(run_id, adim, kaynak, klasor, manifest)
        if ozet is None or ust.cikti_ozeti(ad) != ozet:
            raise GirdiHatasi(
                f"zincir halkasi tutmuyor: {calisma.adim} girdisi {ad} ozeti {adim}"
                f" calistirmasinin ciktisiyla ayni degil ({run_id})"
            )
        if run_id not in gorulen:
            gorulen.add(run_id)
            sonuc.append(ust)
    return sonuc


def ham_dosya(ctx: RunContext, calisma: Calisma) -> tuple[str, str, bytes]:
    """Ingest calismasinin tek ham girdisi: `(veri kokune gore yol, sha256, baytlar)`.

    Ham dosya yerinde olmali ve ozeti manifestteki ozetle tutmalidir (`data/raw` degismez).
    """
    ham = [(yol, ozet) for yol, ozet in girdiler(calisma.manifest) if yol.startswith(RAW_ONEK)]
    if len(ham) != 1:
        raise GirdiHatasi(f"ingest manifestinde tek ham girdi bekleniyor: {calisma.run_id}")
    yol, ozet = ham[0]
    parcalar = yol.split("/")
    if (
        len(parcalar) != 4
        or SLUG_DESENI.fullmatch(parcalar[1]) is None
        or YOL_PARCASI.fullmatch(parcalar[2]) is None
        or YOL_PARCASI.fullmatch(parcalar[3]) is None
        or ozet is None
        or OZET_DESENI.fullmatch(ozet) is None
    ):
        raise GirdiHatasi(f"ham girdi yolu ya da ozeti gecersiz: {calisma.run_id}")
    dosya = ctx.veri_kok / yol
    try:
        veri = dosya.read_bytes()
    except OSError:
        raise GirdiHatasi(f"ham dosya okunamadi: {yol}") from None
    if lineage.sha256_bayt(veri) != ozet:
        raise GirdiHatasi(f"ham dosya ozeti manifestle tutmuyor: {yol}")
    return yol, ozet, veri
