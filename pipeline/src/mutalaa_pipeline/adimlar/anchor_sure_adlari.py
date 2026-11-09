"""Sure adi aday adimi (A11.3): `aliases.jsonl` (K-43 madde 4-5).

`mutalaa anchor --source sure-adlari-vikipedi`: iki ust calismayi zincirler:

* `ingest sure-adlari` calismasinin `tablo.jsonl`, `yonlendirmeler.jsonl`, `quran-meta.jsonl`
  dosyalari (Vikipedi tablosu, tablo maddelerinin suzulmus yonlendirmeleri, `surah.tr`);
* `ingest tanzil --variant ust-veri` calismasinin `sure.jsonl` dosyasi (Tanzil `tname`, `ad_ar`,
  `type`, `order`, `ayas`).

ve `staged/sure-adlari-vikipedi/{run_id}/aliases.jsonl` dosyasini yazar: her satir bir
`surah_alias` adayidir (`surah_no`, `alias`, `alias_key`, `kind`, `risky`, `status = "aday"`,
`onerilen`); `(surah_no, alias)` sirasinda, ASCII kacisli, tekrar uretilebilir. `onerilen` ayni
zamanda `review` satirinin `onerilen` jsonb alanidir (K-43 madde 4). Uretim kurallari
`adimlar/sure_adlari_adaylar.py` modulunun basinda. Onay (`status = 'onayli'`) bu adimin isi
degildir: onay editorun karar uclaridir (A14, I-23).
"""

import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from mutalaa_pipeline import cikis, lineage
from mutalaa_pipeline.adimlar.sure_adlari_adaylar import (
    adaylari_uret,
    capraz_sure_cakismalari,
    riskli_adlari_oku,
    riskli_eslesme,
)
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.ingest import tanzil_ust_veri
from mutalaa_pipeline.ingest.sure_adlari import (
    CIKTI_DOSYALARI,
    KAYNAK,
    QURAN_META_ADI,
    TABLO_ADI,
    YONLENDIRME_ADI,
    MetaSatiri,
    TabloSatiri,
    Yonlendirme,
)
from mutalaa_pipeline.komut_ortak import komutu_yurut
from mutalaa_pipeline.lineage import ALIASLAR_ADI
from mutalaa_pipeline.runctx import RunContext
from mutalaa_pipeline.staged import dosya_yaz
from mutalaa_pipeline.zincir import (
    ANCHOR_ADIMI,
    INGEST_ADIMI,
    Calisma,
    dosya_oku,
    girdi_olarak,
    girdileri_ayni,
    saglam_olmali,
    son_calisma,
)

UST_VERI: Final = tanzil_ust_veri.KAYNAK
SURE_DOSYASI: Final = tanzil_ust_veri.YAPI_DOSYALARI["sure"]
ALIAS_ANAHTARI: Final = ("surah_no", "alias")


@dataclass(frozen=True)
class AnchorSureAdlariSonucu:
    run_id: str
    atlandi: bool
    aday_sayisi: int
    klasor: Path | None
    onceki_run_id: str | None = None


def satirlari_coz[T](calisma: Calisma, ad: str, tur: type[T]) -> list[T]:
    """Staged dosyasini (manifest ozetine karsi) okuyup veri sinifina cevirir."""
    sonuc: list[T] = []
    for satir in dosya_oku(calisma, ad, f"{calisma.adim} {ad}"):
        try:
            sonuc.append(tur(**satir.veri))
        except TypeError:
            raise GirdiHatasi(f"{ad} satir {satir.no}: alan kumesi beklenen degil") from None
    return sonuc


def tanzil_sureleri(ust_veri: Calisma) -> list[Mapping[str, Any]]:
    return [s.veri for s in dosya_oku(ust_veri, SURE_DOSYASI, f"ust veri {SURE_DOSYASI}")]


def ozet_sayilari(adaylar: Sequence[Mapping[str, object]]) -> dict[str, object]:
    """Manifest ve rapor icin sayilar (icerik yok)."""
    return {
        "aday": len(adaylar),
        "kind": dict(sorted(Counter(str(a["kind"]) for a in adaylar).items())),
        "riskli": sum(1 for a in adaylar if a["risky"]),
        "tanzil_fark_sure": sorted(
            int(str(a["surah_no"]))
            for a in adaylar
            if isinstance(a["onerilen"], dict) and "tanzil_fark" in a["onerilen"]
        ),
    }


def run_anchor_sure_adlari(ctx: RunContext) -> AnchorSureAdlariSonucu:
    """Kaynak kaydi, iki ust calisma, parmak izi, adaylar, manifest (en son)."""
    ctx.require_sources((KAYNAK, UST_VERI))
    ctx.gunluk.yaz("INFO", "anchor_sure_adlari_basla", source_id=KAYNAK)
    ingest = son_calisma(ctx, KAYNAK, INGEST_ADIMI, ipucu="once: ingest sure-adlari")
    ust_veri = son_calisma(
        ctx, UST_VERI, INGEST_ADIMI, ipucu="once: ingest tanzil --variant ust-veri"
    )
    saglam_olmali(ctx, ingest)
    saglam_olmali(ctx, ust_veri)
    girdiler = [girdi_olarak(ingest, ad) for ad in CIKTI_DOSYALARI]
    girdiler.append(girdi_olarak(ust_veri, SURE_DOSYASI))
    parmak = ctx.parmak_izi(girdiler)

    onceki = lineage.son_basarili(ctx.staged_kaynak_dizini(KAYNAK), ctx.adim)
    if girdileri_ayni(onceki[2] if onceki else None, girdiler) and lineage.atlanabilir(
        onceki=onceki[2] if onceki else None,
        parmak=parmak,
        git_kirli=ctx.git().kirli,
        force=ctx.force,
        veri_kok=ctx.veri_kok,
    ):
        ctx.gunluk.yaz("INFO", "anchor_sure_adlari_atlandi", source_id=KAYNAK)
        ctx.sayi("atlandi", 1)
        return AnchorSureAdlariSonucu(ctx.run_id, True, 0, None, onceki[0] if onceki else None)

    riskli = riskli_adlari_oku()
    adaylar = adaylari_uret(
        satirlari_coz(ingest, TABLO_ADI, TabloSatiri),
        satirlari_coz(ingest, YONLENDIRME_ADI, Yonlendirme),
        satirlari_coz(ingest, QURAN_META_ADI, MetaSatiri),
        tanzil_sureleri(ust_veri),
        riskli,
    )
    cikti = dosya_yaz(ctx, KAYNAK, ALIASLAR_ADI, adaylar, ALIAS_ANAHTARI)
    sayilar = ozet_sayilari(adaylar)
    eslesme = riskli_eslesme(adaylar, riskli)
    capraz = capraz_sure_cakismalari(adaylar)
    ctx.sayi("aday", len(adaylar))
    ctx.sayi("riskli", int(str(sayilar["riskli"])))
    ctx.sayi("tanzil_fark_sure", len(list(sayilar["tanzil_fark_sure"])))  # type: ignore[call-overload]
    ctx.sayi("capraz_sure_anahtar", len(capraz))
    if capraz:
        ctx.uyar(
            f"{len(capraz)} alias_key birden fazla surede ayni (A05 geniş anahtari kesme"
            " isaretinden sonrasini ek sayar); ayrinti qa olcumlerinde"
        )
    if ctx.dry_run:
        ctx.gunluk.yaz("INFO", "anchor_sure_adlari_dry_run", source_id=KAYNAK)
        return AnchorSureAdlariSonucu(ctx.run_id, False, len(adaylar), None)
    klasor = ctx.staged_dizin(KAYNAK)
    ctx.manifest_yaz(
        klasor,
        girdiler=girdiler,
        ciktilar=[cikti],
        parmak=parmak,
        ayrintilar={
            "kaynak": KAYNAK,
            "ingest_run": ingest.run_id,
            "ust_veri_run": ust_veri.run_id,
            **sayilar,
            # ad metni yazilmaz: anahtar riskli_adlar.txt icindeki ad sirasidir (1 tabanli)
            "riskli_eslesme": {str(i): v for i, v in enumerate(eslesme.values(), 1)},
            "capraz_sure_anahtar": len(capraz),
        },
    )
    ctx.gunluk.yaz("INFO", "anchor_sure_adlari_bitti", source_id=KAYNAK)
    return AnchorSureAdlariSonucu(ctx.run_id, False, len(adaylar), klasor)


def komut_anchor_sure_adlari(
    *, dry_run: bool, force: bool, config: Path | None, kok: Path | None
) -> int:
    """`anchor --source sure-adlari-vikipedi` komutu; cikis kodunu dondurur."""

    def govde(ctx: RunContext) -> int:
        sonuc = run_anchor_sure_adlari(ctx)
        if sonuc.atlandi:
            ozet = f"atlandi (parmak izi onceki calistirmayla ayni, run {sonuc.onceki_run_id})"
        elif ctx.dry_run:
            ozet = f"{sonuc.aday_sayisi} aday (dry-run, hicbir sey yazilmadi)"
        else:
            ozet = f"{sonuc.aday_sayisi} aday, run {sonuc.run_id}"
        sys.stdout.write(f"anchor {KAYNAK}: {ozet}\n")
        return cikis.BASARILI

    return komutu_yurut(
        komut=f"anchor --source {KAYNAK}",
        adim=ANCHOR_ADIMI,
        kaynaklar=[KAYNAK, UST_VERI],
        config=config,
        kok=kok,
        govde=govde,
        force=force,
        dry_run=dry_run,
        parametreler={"source": KAYNAK},
    )
