"""`mutalaa` komut satiri girisi (cikis kodlari: `cikis.py`)."""

from enum import StrEnum
from pathlib import Path
from typing import Annotated

import typer

from mutalaa_pipeline import cikis, cli_gloss_ornek, cli_gold, cli_qac, sources
from mutalaa_pipeline.export import ayet_sayilari, ic_kesme, test_vectors
from mutalaa_pipeline.export.ortak import GirdiHatasi, kok_coz
from mutalaa_pipeline.ingest import meal_kaynaklari

app = typer.Typer(
    name="mutalaa",
    help=(
        "Mutalaa icerik hatti. Cikis kodlari: 0 basarili, 1 QA kapisi kaldi,"
        " 2 girdi ya da yapilandirma hatasi (kayitsiz ya da gecersiz kaynak kaydi dahil)."
    ),
    no_args_is_help=True,
    add_completion=False,
    # Iz (traceback) yerel degiskenleri gosterirse baglanti dizesi sizabilir.
    pretty_exceptions_show_locals=False,
)

export_app = typer.Typer(no_args_is_help=True, help="Disa aktarim: veri dosyalari ve vektorler.")
app.add_typer(export_app, name="export")

sources_app = typer.Typer(
    no_args_is_help=True, help="Kaynak kayitlari (pipeline/sources/*.toml): liste ve denetim."
)
app.add_typer(sources_app, name="sources")

ingest_app = typer.Typer(
    no_args_is_help=True, help="Kaynak alimi: data/gelen -> data/raw -> data/staged."
)
app.add_typer(ingest_app, name="ingest")

qa_app = typer.Typer(
    no_args_is_help=True,
    help="QA kapilari (G-KAY..G-NOR; meal: + G-HIZ), `sample` ornekleme ve G-INC olcumu.",
)
app.add_typer(qa_app, name="qa")

KokSecenegi = Annotated[
    Path | None,
    typer.Option("--kok", help="Depo koku (testler icin); verilmezse pnpm-workspace.yaml aranir."),
]


@app.callback()
def main() -> None:
    """Mutalaa icerik hatti komutlari."""


class Bicim(StrEnum):
    JSON = "json"
    TABLO = "tablo"


class TanzilVaryanti(StrEnum):
    UTHMANI = "uthmani"
    SIMPLE_CLEAN = "simple-clean"
    UST_VERI = "ust-veri"


def _hata(hata: GirdiHatasi) -> typer.Exit:
    typer.echo(f"hata: {hata}", err=True)
    return typer.Exit(code=cikis.GIRDI_HATASI)


@export_app.command("ayet-sayilari")
def export_ayet_sayilari(
    kaynak: Annotated[
        Path | None, typer.Option("--kaynak", help="Tanzil quran-data.xml dosyasi.")
    ] = None,
    url: Annotated[str | None, typer.Option("--url", help="Dosyanin indirildigi adres.")] = None,
    tarih: Annotated[str | None, typer.Option("--tarih", help="Alinma tarihi, YYYY-AA-GG.")] = None,
    check: Annotated[
        bool, typer.Option("--check", help="Yazmadan diskle karsilastirir; fark varsa 1.")
    ] = False,
    kok: KokSecenegi = None,
) -> None:
    """Sure basina ayet sayilarini (JSON) ve uc dildeki kopyalarini uretir."""
    try:
        depo = kok_coz(kok)
        if check:
            if kaynak is not None or url is not None or tarih is not None:
                raise GirdiHatasi("--check ile --kaynak, --url ve --tarih verilmez")
            farklar = ayet_sayilari.denetle(depo)
            if farklar:
                for yol in farklar:
                    typer.echo(f"fark: {yol}")
                raise typer.Exit(code=1)
            typer.echo("ayet-sayilari: fark yok")
            return
        if kaynak is None or url is None or tarih is None:
            raise GirdiHatasi("--kaynak, --url ve --tarih birlikte verilmeli (ya da --check)")
        yazilanlar = ayet_sayilari.uret(depo, kaynak, url, tarih)
    except GirdiHatasi as hata:
        raise _hata(hata) from hata
    for yol in yazilanlar:
        typer.echo(f"yazildi: {yol}")
    if not yazilanlar:
        typer.echo("ayet-sayilari: degisiklik yok")


@export_app.command("test-vectors")
def export_test_vectors(
    check: Annotated[
        bool, typer.Option("--check", help="Yazmadan diskle karsilastirir; fark varsa 1.")
    ] = False,
    tanzil_ornekleri: Annotated[
        bool,
        typer.Option(
            "--tanzil-ornekleri",
            help=(
                "Arama belgesi 1.5 Arapca tablosunun Tanzil Uthmani satirlarini (ar-tz-)"
                " belgeden ve data/gelen dosyasindan bastan uretir (A10.7); bulunamazsa ya"
                " da tablodaki degeri vermezse 2 ile durur."
            ),
        ),
    ] = False,
    fts_ornekleri: Annotated[
        bool,
        typer.Option(
            "--fts-ornekleri",
            help=(
                "Arama belgesi bolum 3 sorgu tablosunun iki Arapca sorgusunu (fq-ar-0001,"
                " fq-ar-0002) belgeden alip fts-query/query.jsonl dosyasina yazar (A12.4)."
            ),
        ),
    ] = False,
    config: Annotated[
        Path | None,
        typer.Option("--config", help="Baska bir mutalaa.toml (yalniz --tanzil-ornekleri ile)."),
    ] = None,
    kok: KokSecenegi = None,
) -> None:
    """`shared/test-vectors` dosyalarinin hesaplanan alanlarini ve sinir satirlarini uretir."""
    try:
        depo = kok_coz(kok)
        ek: list[test_vectors.Satir] | None = None
        if config is not None and not tanzil_ornekleri:
            raise GirdiHatasi("--config yalniz --tanzil-ornekleri ile verilir")
        if tanzil_ornekleri:
            # Ice aktarma: yapilandirma, normallestirici ve ingest yalniz bu secenekte yuklenir.
            from mutalaa_pipeline.config import ayarlar_yukle
            from mutalaa_pipeline.export import tanzil_ornekleri as tz

            uretim = tz.uret(depo, ayarlar_yukle(config).veri_kok)
            ek = uretim.satirlar
            for eslesme in uretim.eslesmeler:
                typer.echo(f"tanzil: {eslesme.ozet()}")
        if check:
            farklar = test_vectors.denetle(depo, ek)
            if fts_ornekleri:
                from mutalaa_pipeline.export import fts_ornekleri as fts

                farklar += fts.denetle(depo)
            if farklar:
                for fark in farklar:
                    typer.echo(f"fark: {fark}")
                raise typer.Exit(code=1)
            typer.echo("test-vectors: fark yok")
            return
        yazilanlar = test_vectors.uret(depo, ek)
        if fts_ornekleri:
            from mutalaa_pipeline.export import fts_ornekleri as fts

            if fts.uret(depo):
                yazilanlar.append(fts.VEKTOR_YOLU)
    except GirdiHatasi as hata:
        raise _hata(hata) from hata
    for yol in yazilanlar:
        typer.echo(f"yazildi: {yol}")
    if not yazilanlar:
        typer.echo("test-vectors: degisiklik yok")


@export_app.command("ic-kesme")
def export_ic_kesme(
    check: Annotated[
        bool, typer.Option("--check", help="Yazmadan diskle karsilastirir; fark varsa 1.")
    ] = False,
    kok: KokSecenegi = None,
) -> None:
    """`shared/data/ic-kesme.txt` listesinden TypeScript ve C# kopyalarini uretir."""
    try:
        depo = kok_coz(kok)
        if check:
            farklar = ic_kesme.denetle(depo)
            if farklar:
                for yol in farklar:
                    typer.echo(f"fark: {yol}")
                raise typer.Exit(code=1)
            typer.echo("ic-kesme: fark yok")
            return
        yazilanlar = ic_kesme.uret(depo)
    except GirdiHatasi as hata:
        raise _hata(hata) from hata
    for yol in yazilanlar:
        typer.echo(f"yazildi: {yol}")
    if not yazilanlar:
        typer.echo("ic-kesme: degisiklik yok")


@export_app.command("pg")
def export_pg_komutu(
    source: Annotated[str, typer.Option("--source", help="Kaynak kimligi, or. tanzil-uthmani.")],
    run: Annotated[
        str | None,
        typer.Option("--run", help="anchor run_id; verilmezse manifestli en son anchor."),
    ] = None,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Islemi geri alir; hicbir satir yazmaz.")
    ] = False,
    force: Annotated[
        bool, typer.Option("--force", help="Kabul edilir; export pg parmak izi atlamaz (K-39).")
    ] = False,
    config: Annotated[Path | None, typer.Option("--config", help="Baska bir mutalaa.toml.")] = None,
    kok: KokSecenegi = None,
) -> None:
    """Staged birimleri PostgreSQL'e yukler (tek islem, idempotent; K-39). Cikis 0, 1 ya da 2."""
    # Ice aktarma: psycopg ve yapilandirma yalniz bu komutta yuklenir.
    from mutalaa_pipeline.config import ayarlar_yukle
    from mutalaa_pipeline.export import pg

    try:
        depo = kok_coz(kok)
        ayarlar = ayarlar_yukle(config)
    except GirdiHatasi as hata:
        raise _hata(hata) from hata
    kod = pg.komut_export_pg(
        ayarlar, depo_kok=depo, source=source, run=run, dry_run=dry_run, force=force
    )
    if kod != cikis.BASARILI:
        raise typer.Exit(code=kod)


@ingest_app.command("tanzil")
def ingest_tanzil(
    variant: Annotated[
        TanzilVaryanti,
        typer.Option(
            "--variant", help="Tanzil varyanti: uthmani, simple-clean ya da ust-veri (XML)."
        ),
    ],
    gelen_tarih: Annotated[
        str | None,
        typer.Option(
            "--gelen-tarih",
            help=(
                "data/gelen/tanzil (ust-veri icin data/gelen/tanzil-ust-veri) altindaki tarih"
                " klasoru, YYYY-AA-GG; verilmezse en yenisi."
            ),
        ),
    ] = None,
    kilit_oner: Annotated[
        bool,
        typer.Option(
            "--kilit-oner",
            help="Kilidin ilk degerlerini gelen dosyadan hesaplayip yazdirir; hicbir sey yazmaz.",
        ),
    ] = False,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="raw ve staged'e yazmaz; kilit yine denetlenir.")
    ] = False,
    force: Annotated[
        bool, typer.Option("--force", help="Parmak izi ayni olsa da calistirir.")
    ] = False,
    limit: Annotated[
        int | None,
        typer.Option("--limit", help="Tanzil'de reddedilir (kismi alim kilidi ve G-BUT'u bozar)."),
    ] = None,
    config: Annotated[Path | None, typer.Option("--config", help="Baska bir mutalaa.toml.")] = None,
    kok: KokSecenegi = None,
) -> None:
    """Gelen Tanzil dosyasini kilitle karsilastirir, raw'a alir, staged uretir. Cikis 0 ya da 2."""
    # Ice aktarma: psycopg ve yapilandirma yalniz bu komutta yuklenir.
    from mutalaa_pipeline.config import ayarlar_yukle
    from mutalaa_pipeline.ingest import tanzil, tanzil_ust_veri

    try:
        if limit is not None:
            raise GirdiHatasi("--limit Tanzil alimi icin desteklenmez (kismi alim kilidi bozulur)")
        if kilit_oner:
            if dry_run or force:
                raise GirdiHatasi("--kilit-oner ile --dry-run ve --force verilmez")
            depo = kok_coz(kok)
            ayarlar = ayarlar_yukle(config)
            if variant is TanzilVaryanti.UST_VERI:
                url = tanzil.ust_veri_kilidi_yukle().url
                metin = tanzil_ust_veri.kilit_oner_metni(ayarlar.veri_kok, gelen_tarih, url)
            else:
                metin = tanzil.kilit_oner_metni(depo, ayarlar.veri_kok, variant.value, gelen_tarih)
            typer.echo(metin, nl=False)
            return
    except GirdiHatasi as hata:
        raise _hata(hata) from hata
    if variant is TanzilVaryanti.UST_VERI:
        kod = tanzil_ust_veri.komut_ingest_ust_veri(
            gelen_tarih=gelen_tarih, dry_run=dry_run, force=force, config=config, kok=kok
        )
    else:
        kod = tanzil.komut_ingest_tanzil(
            varyant=variant.value,
            gelen_tarih=gelen_tarih,
            dry_run=dry_run,
            force=force,
            config=config,
            kok=kok,
        )
    if kod != cikis.BASARILI:
        raise typer.Exit(code=kod)


@ingest_app.command("sure-adlari")
def ingest_sure_adlari(
    gelen_tarih: Annotated[
        str | None,
        typer.Option(
            "--gelen-tarih",
            help=(
                "data/gelen/sure-adlari-vikipedi ve data/gelen/quran-meta altindaki tarih"
                " klasoru, YYYY-AA-GG; verilmezse her kaynagin en yenisi."
            ),
        ),
    ] = None,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="raw ve staged'e yazmaz; kilit yine denetlenir.")
    ] = False,
    force: Annotated[
        bool, typer.Option("--force", help="Parmak izi ayni olsa da calistirir.")
    ] = False,
    limit: Annotated[
        int | None, typer.Option("--limit", help="Sure adi alimi icin reddedilir.")
    ] = None,
    config: Annotated[Path | None, typer.Option("--config", help="Baska bir mutalaa.toml.")] = None,
    kok: KokSecenegi = None,
) -> None:
    """Vikipedi sure listesi, yonlendirmeler ve quran-meta adlarini alir. Cikis 0 ya da 2."""
    from mutalaa_pipeline.ingest import sure_adlari

    try:
        if limit is not None:
            raise GirdiHatasi("--limit sure adi alimi icin desteklenmez")
    except GirdiHatasi as hata:
        raise _hata(hata) from hata
    kod = sure_adlari.komut_ingest_sure_adlari(
        gelen_tarih=gelen_tarih, dry_run=dry_run, force=force, config=config, kok=kok
    )
    if kod != cikis.BASARILI:
        raise typer.Exit(code=kod)


@ingest_app.command("meal")
def ingest_meal(
    source: Annotated[
        str,
        typer.Option(
            "--source",
            help="Meal kaynagi: elmalili-meal, elmalili-sade-meal ya da tanik elmalili-meal-epub.",
        ),
    ],
    gelen_tarih: Annotated[
        str | None,
        typer.Option(
            "--gelen-tarih",
            help=("data/gelen/<kaynak> altindaki tarih klasoru, YYYY-AA-GG; verilmezse en yenisi."),
        ),
    ] = None,
    kilit_oner: Annotated[
        bool,
        typer.Option(
            "--kilit-oner",
            help="Kilit bolumunun ilk degerlerini gelen dosyadan hesaplayip yazdirir; yazmaz.",
        ),
    ] = False,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="raw ve staged'e yazmaz; kilit yine denetlenir.")
    ] = False,
    force: Annotated[
        bool, typer.Option("--force", help="Parmak izi ayni olsa da calistirir.")
    ] = False,
    limit: Annotated[
        int | None,
        typer.Option(
            "--limit", help="Meal alimi icin reddedilir (kismi alim kilidi ve G-HIZ'i bozar)."
        ),
    ] = None,
    config: Annotated[Path | None, typer.Option("--config", help="Baska bir mutalaa.toml.")] = None,
    kok: KokSecenegi = None,
) -> None:
    """Gelen meal dosyasini kilitle karsilastirir, raw'a alir, staged uretir. Cikis 0 ya da 2."""
    # Ice aktarma: yapilandirma ve ayristiricilar yalniz bu komutta yuklenir.
    from mutalaa_pipeline.config import ayarlar_yukle
    from mutalaa_pipeline.ingest import meal_kilit_oner, meal_ortak

    try:
        if limit is not None:
            raise GirdiHatasi("--limit meal alimi icin desteklenmez (kismi alim G-HIZ'i bozar)")
        if kilit_oner:
            if dry_run or force:
                raise GirdiHatasi("--kilit-oner ile --dry-run ve --force verilmez")
            depo = kok_coz(kok)
            ayarlar = ayarlar_yukle(config)
            typer.echo(
                meal_kilit_oner.kilit_oner_metni(depo, ayarlar.veri_kok, source, gelen_tarih),
                nl=False,
            )
            return
    except GirdiHatasi as hata:
        raise _hata(hata) from hata
    kod = meal_ortak.komut_ingest_meal(
        source=source,
        gelen_tarih=gelen_tarih,
        dry_run=dry_run,
        force=force,
        config=config,
        kok=kok,
    )
    if kod != cikis.BASARILI:
        raise typer.Exit(code=kod)


@ingest_app.command("fikstur")
def ingest_fikstur(
    source: Annotated[
        str,
        typer.Option(
            "--source",
            help="Fikstur kaynagi: test-kucuk ya da test-tefsir-ornek (test-ses birim uretmez).",
        ),
    ],
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="staged ve manifest yazmaz; her sey yine denetlenir.")
    ] = False,
    force: Annotated[
        bool, typer.Option("--force", help="Parmak izi ayni olsa da calistirir.")
    ] = False,
    limit: Annotated[
        int | None, typer.Option("--limit", help="Fikstur uretimi icin reddedilir.")
    ] = None,
    config: Annotated[Path | None, typer.Option("--config", help="Baska bir mutalaa.toml.")] = None,
    kok: KokSecenegi = None,
) -> None:
    """Belirlenimci sentetik fikstur birimlerini uretir (data/gelen ve data/raw kullanilmaz)."""
    from mutalaa_pipeline.ingest import fikstur

    try:
        if limit is not None:
            raise GirdiHatasi("--limit fikstur uretimi icin desteklenmez")
    except GirdiHatasi as hata:
        raise _hata(hata) from hata
    kod = fikstur.komut_ingest_fikstur(
        source=source, dry_run=dry_run, force=force, config=config, kok=kok
    )
    if kod != cikis.BASARILI:
        raise typer.Exit(code=kod)


def _fikstur_mu(source: str) -> bool:
    """Sentetik fikstur kaynagi mi (A13.6); ice aktarma: komut modulleri tembel yuklenir."""
    from mutalaa_pipeline.ingest.fikstur import KAYNAKLAR

    return source in KAYNAKLAR


def _limit_reddet(limit: int | None) -> None:
    """Tanzil adimlarinda kismi calisma kabul edilmez (G-BUT ve capa kumesi bozulur)."""
    if limit is not None:
        raise GirdiHatasi("--limit Tanzil adimlari icin desteklenmez (kismi cikti G-BUT'u bozar)")


@app.command("normalize")
def normalize_komutu(
    source: Annotated[str, typer.Option("--source", help="Kaynak kimligi, or. tanzil-uthmani.")],
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="staged ve manifest yazmaz; her sey yine denetlenir.")
    ] = False,
    force: Annotated[
        bool, typer.Option("--force", help="Parmak izi ayni olsa da calistirir.")
    ] = False,
    limit: Annotated[
        int | None,
        typer.Option("--limit", help="Tanzil'de reddedilir (kismi cikti capa kumesini bozar)."),
    ] = None,
    config: Annotated[Path | None, typer.Option("--config", help="Baska bir mutalaa.toml.")] = None,
    kok: KokSecenegi = None,
) -> None:
    """Arama metnini uretir: ar_norm (Simple Clean + AR-4, K-39). Cikis 0 ya da 2."""
    # Ice aktarma: normallestirici (regex, snowballstemmer) yalniz bu komutta yuklenir.
    from mutalaa_pipeline.adimlar import normalize_tanzil

    try:
        _limit_reddet(limit)
    except GirdiHatasi as hata:
        raise _hata(hata) from hata
    if _fikstur_mu(source):  # sentetik fikstur: Turkce arama anahtarlari (A13.6)
        from mutalaa_pipeline.adimlar import fikstur as fikstur_adimlari

        kod = fikstur_adimlari.komut_normalize(
            source=source, dry_run=dry_run, force=force, config=config, kok=kok
        )
    elif meal_kaynaklari.kayitli_mi(source):  # iki meal: Turkce arama anahtarlari (A16.3)
        from mutalaa_pipeline.adimlar import meal as meal_adimlari

        kod = meal_adimlari.komut_normalize(
            source=source, dry_run=dry_run, force=force, config=config, kok=kok
        )
    else:
        kod = normalize_tanzil.komut_normalize(
            source=source, dry_run=dry_run, force=force, config=config, kok=kok
        )
    if kod != cikis.BASARILI:
        raise typer.Exit(code=kod)


@app.command("anchor")
def anchor_komutu(
    source: Annotated[str, typer.Option("--source", help="Kaynak kimligi, or. tanzil-uthmani.")],
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="staged ve manifest yazmaz; her sey yine denetlenir.")
    ] = False,
    force: Annotated[
        bool, typer.Option("--force", help="Parmak izi ayni olsa da calistirir.")
    ] = False,
    limit: Annotated[
        int | None,
        typer.Option("--limit", help="Tanzil'de reddedilir (kismi cikti capa kumesini bozar)."),
    ] = None,
    config: Annotated[Path | None, typer.Option("--config", help="Baska bir mutalaa.toml.")] = None,
    kok: KokSecenegi = None,
) -> None:
    """Capa, content_hash ve kuresel ayet sirasini uretir (q:{sure}:{ayet}). Cikis 0 ya da 2."""
    from mutalaa_pipeline.adimlar import anchor_sure_adlari, anchor_tanzil, anchor_ust_veri
    from mutalaa_pipeline.ingest.sure_adlari import KAYNAK as SURE_ADLARI_KAYNAGI
    from mutalaa_pipeline.ingest.tanzil_ust_veri import KAYNAK as UST_VERI_KAYNAGI

    try:
        _limit_reddet(limit)
    except GirdiHatasi as hata:
        raise _hata(hata) from hata
    if source == UST_VERI_KAYNAGI:  # isaret ve sayfa satirlari (A11.4, A11.5)
        kod = anchor_ust_veri.komut_anchor_ust_veri(
            dry_run=dry_run, force=force, config=config, kok=kok
        )
    elif source == SURE_ADLARI_KAYNAGI:  # sure adi adaylari (A11.3)
        kod = anchor_sure_adlari.komut_anchor_sure_adlari(
            dry_run=dry_run, force=force, config=config, kok=kok
        )
    elif _fikstur_mu(source):  # sentetik fikstur capalari (A13.6)
        from mutalaa_pipeline.adimlar import fikstur as fikstur_adimlari

        kod = fikstur_adimlari.komut_anchor(
            source=source, dry_run=dry_run, force=force, config=config, kok=kok
        )
    elif meal_kaynaklari.kayitli_mi(source):  # iki meal: capa, ord, tanik skoru (A16.3)
        from mutalaa_pipeline.adimlar import meal as meal_adimlari

        kod = meal_adimlari.komut_anchor(
            source=source, dry_run=dry_run, force=force, config=config, kok=kok
        )
    else:
        kod = anchor_tanzil.komut_anchor(
            source=source, dry_run=dry_run, force=force, config=config, kok=kok
        )
    if kod != cikis.BASARILI:
        raise typer.Exit(code=kod)


@qa_app.command("run")
def qa_run(
    source: Annotated[str, typer.Option("--source", help="Kaynak kimligi, or. tanzil-uthmani.")],
    run: Annotated[
        str | None,
        typer.Option("--run", help="anchor run_id; verilmezse manifestli en son anchor."),
    ] = None,
    gate: Annotated[
        list[str] | None,
        typer.Option(
            "--gate",
            help=(
                "Yalniz bu kapi(lar)i kosar (G-KAY, G-BUT, G-CAP, G-NOR; meal kaynaklarinda"
                " ayrica G-HIZ); eksik rapor export pg'ye yetmez."
            ),
        ),
    ] = None,
    config: Annotated[Path | None, typer.Option("--config", help="Baska bir mutalaa.toml.")] = None,
    kok: KokSecenegi = None,
    db: Annotated[
        bool,
        typer.Option(
            "--db",
            help=(
                "Yalniz kaikki-tr, xref-baglantilar ve xref-atif-iktibas: G-CAP'a veritabani"
                " uzantisini ekler (tr_root_index; staged baglantilarin ayet/meal ozeti,"
                " aralik ve kok/lemma tutarliligi)."
            ),
        ),
    ] = False,
) -> None:
    """QA kapilarini kosar ve data/reports/{run_id}.json raporunu yazar. Cikis 0, 1 ya da 2."""
    from mutalaa_pipeline.qa import run as qa_calistir

    kod = qa_calistir.komut_qa_run(source=source, run=run, gate=gate, config=config, kok=kok, db=db)
    if kod != cikis.BASARILI:
        raise typer.Exit(code=kod)


@qa_app.command("sample")
def qa_sample(
    source: Annotated[
        str, typer.Option("--source", help="Meal kaynagi: elmalili-meal ya da elmalili-sade-meal.")
    ],
    n: Annotated[int, typer.Option("--n", help="Ornek buyuklugu (tur 2: en az 600).")] = 600,
    seed: Annotated[
        int, typer.Option("--seed", help="Sabit tohum; ayni tohum ayni capa listesini verir.")
    ] = 20261111,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Ornek raporu ve sablonu yazmaz; ozeti yazdirir.")
    ] = False,
    onayli: Annotated[
        bool, typer.Option("--onayli", help="Evreni yalniz onayli birimlerle sinirlar.")
    ] = False,
    okunan: Annotated[
        int | None, typer.Option("--okunan", help="Tur 2: ikinci okuyucunun okudugu ayet sayisi.")
    ] = None,
    hatali: Annotated[
        int | None, typer.Option("--hatali", help="Tur 2: okunanlar arasinda hatali ayet sayisi.")
    ] = None,
    sablon: Annotated[
        Path | None,
        typer.Option(
            "--sablon", help="Doldurulmus ikinci okuma sablonu (okunan ve hatali sayilir)."
        ),
    ] = None,
    config: Annotated[Path | None, typer.Option("--config", help="Baska bir mutalaa.toml.")] = None,
    kok: KokSecenegi = None,
) -> None:
    """Ikinci okuma orneklemi (sure grubuna gore tabakali) ve G-INC olcum raporu. Cikis 0 ya da 2.

    Veritabanindan yalniz okur; G-INC `qa run` kapisi degildir, sonuc yalniz rapora yazilir.
    """
    from mutalaa_pipeline.qa import ornekleme

    kod = ornekleme.komut_qa_sample(
        source=source,
        n=n,
        seed=seed,
        dry_run=dry_run,
        yalniz_onayli=onayli,
        okunan=okunan,
        hatali=hatali,
        sablon=sablon,
        config=config,
        kok=kok,
    )
    if kod != cikis.BASARILI:
        raise typer.Exit(code=kod)


@sources_app.command("list")
def sources_list(
    bicim: Annotated[
        Bicim, typer.Option("--format", help="Cikti bicimi: tablo ya da json.")
    ] = Bicim.TABLO,
    kok: KokSecenegi = None,
) -> None:
    """`pipeline/sources/*.toml` kayitlarini listeler: slug, tur, surum, kaynak_url."""
    try:
        sonuclar = sources.yukle(kok_coz(kok))
    except GirdiHatasi as hata:
        raise _hata(hata) from hata
    bozuk = False
    for sonuc in sonuclar:
        for mesaj in sonuc.hatalar:
            typer.echo(f"hata: {sonuc.dosya}: {mesaj}", err=True)
            bozuk = True
    if bozuk:
        raise typer.Exit(code=cikis.GIRDI_HATASI)
    kayitlar = [s.kaynak for s in sonuclar if s.kaynak is not None]
    satirlar = sources.satirlar(kayitlar)
    if bicim is Bicim.JSON:
        typer.echo(sources.json_metni(satirlar))
    elif satirlar:
        typer.echo(sources.tablo_metni(satirlar))
    else:
        typer.echo("kayit yok")


@sources_app.command("check")
def sources_check(kok: KokSecenegi = None) -> None:
    """Kaynak kayitlarinin bicimini ve zorunlu alanlarini denetler (G-KAY); cikis 0 ya da 2."""
    try:
        sonuclar = sources.yukle(kok_coz(kok))
    except GirdiHatasi as hata:
        raise _hata(hata) from hata
    hata_sayisi = 0
    uyari_sayisi = 0
    for sonuc in sonuclar:
        for mesaj in sonuc.hatalar:
            typer.echo(f"hata: {sonuc.dosya}: {mesaj}", err=True)
            hata_sayisi += 1
        for mesaj in sonuc.uyarilar:
            typer.echo(f"uyari: {sonuc.dosya}: {mesaj}", err=True)
            uyari_sayisi += 1
    if not sonuclar:
        typer.echo("kayit yok")
    else:
        typer.echo(
            f"sources check: {len(sonuclar)} kayit, {hata_sayisi} hata, {uyari_sayisi} uyari"
        )
    if hata_sayisi:
        raise typer.Exit(code=cikis.GIRDI_HATASI)


cli_qac.kaydet(app, ingest_app)  # A17: ingest qac, enrich morphology
cli_gloss_ornek.kaydet(qa_app)  # A17.6: qa gloss-sample, qa gloss-score
cli_gold.kaydet(qa_app)  # A18.5: qa gold
