"""Lugat kapsama raporu (A20.6b): "projenin tum kelimelerinin karsiligi" hedefinin olcusu.

`mutalaa qa risale-rapor --rapor lugat` -> `data/reports/a20/lugat-kapsama.json` (YALNIZ sayi ve
oran; metin yok) ve `data/reports/a20/lugat-karsiliksiz.txt` (yerel liste: karsiliksiz en sik
sozcukler; `data/` git disidir, rapora ve commit'e girmez). Veritabani YOKTUR: girdi yalniz
staged calismalari ve gelen zip'tir.

Girdiler

* Lugat: en son `ingest lugat` calismasi (`lugat-rnk`, `lugat-sozluk-rganeyev`; manifestli ve
  ciktilari saglam).
* Risale baslik sozleri: en son `risale-kelime-frekans` ingest'i (`lugat.jsonl`, 21.486 soz).
* Risale metni: `risale-rnk-metin` en son `anchor` calismasinin `units.jsonl` dosyasi (veritabani
  DEGIL); yalniz Turkce (`dil = tr`) kitaplar. Sozcuk = `tr_narrow` sozcugu, govdesi `tr_stem`
  ayni konumdaki sozcuk. Derleme kitaplardaki tekrarlar gecis sikligina dahildir.
* Terkipler: Kelime-Frekans zip'inin `terkipli/<kitap>_frekans.txt` listeleri (bellekte; yalniz
  kitap dosyalari) ve RNK'nin cok sozcuklu basliklari.

Olcumler

* (a) `baslik_soz`: 21.486 Risale baslik sozunun lugat kaynaklarina gore karsiligi (RNK, yalniz
  rganeyev, hicbiri; sayi ve siklik agirlikli). `anahtar_olcumu`: uc aday eslestirme anahtarinin
  (`basliksoz_norm`, `sozluk_ocr.anahtar`, `esleme_anahtari`) RNK kapsama olcusu; `esleme_anahtari`
  secilidir.
* (b) `metin_sozcukleri`: Turkce Risale birimlerinin benzersiz sozcukleri; lugat basligiyla (yalin)
  ya da govde anahtariyla karsilanma orani (sozcuk ve gecis sikligi agirlikli).
* (c) `terkipler`: Risale terkipleri <-> RNK cok sozcuklu basliklari.
* (d) karsiliksiz en sik 200 sozcuk ayri yerel dosyada.
"""

from collections import Counter
from collections.abc import Callable, Iterable, Mapping, Sequence
from pathlib import Path
from typing import Final

from mutalaa_pipeline import lineage, zincir
from mutalaa_pipeline.anchor import risale
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.ingest import kelime_frekans, lugat_kaynak, sozluk_ocr
from mutalaa_pipeline.ingest.lugat_madde import LUGAT_ADI
from mutalaa_pipeline.ingest.meal_ortak import gelen_dizini, gelen_tarihi_coz
from mutalaa_pipeline.ingest.risale_karsilastirma import rnk_kitap_slugu
from mutalaa_pipeline.ingest.tanzil import INGEST_ADIMI
from mutalaa_pipeline.logs import json_baytlari
from mutalaa_pipeline.runctx import RunContext
from mutalaa_pipeline.staged import satirlari_akit

RAPOR_SURUMU: Final = 1
RAPOR_ADI: Final = "lugat-kapsama.json"
KARSILIKSIZ_ADI: Final = "lugat-karsiliksiz.txt"
RAPOR_KLASORU: Final = ("reports", "a20")
RNK_METIN: Final = "risale-rnk-metin"
ANCHOR_ADIMI: Final = "anchor"
EN_SIK_KARSILIKSIZ: Final = 200
SIKLIK_DILIMLERI: Final = (
    (1, 1),
    (2, 4),
    (5, 19),
    (20, 99),
    (100, 0),
)  # (alt, ust); ust 0 = sinirsiz
TERKIP_BASLIGI: Final = "kelime,frekans"


def _yuzde(pay: int, payda: int) -> float:
    return round(100 * pay / payda, 2) if payda else 0.0


def _oran(pay: int, payda: int) -> dict[str, object]:
    return {"sayi": pay, "yuzde": _yuzde(pay, payda)}


def _calisma(ctx: RunContext, kaynak: str, adim: str, ipucu: str) -> zincir.Calisma:
    calisma = zincir.son_calisma(ctx, kaynak, adim, ipucu=ipucu)
    zincir.saglam_olmali(ctx, calisma)
    return calisma


def _lugat_basliklari(ctx: RunContext, slug: str) -> tuple[list[tuple[str, str]], str]:
    """Lugat kaynaginin `(basliksoz, basliksoz_norm)` ciftleri ve run_id'si."""
    calisma = _calisma(ctx, slug, INGEST_ADIMI, f"once: ingest lugat --source {slug}")
    satirlar = zincir.dosya_oku(calisma, LUGAT_ADI, f"{slug} {LUGAT_ADI}")
    return [(s.metin("basliksoz"), s.metin("basliksoz_norm")) for s in satirlar], calisma.run_id


def _risale_sozleri(ctx: RunContext) -> tuple[list[tuple[str, str, int]], str]:
    """Kelime-Frekans baslik sozleri: `(basliksoz, basliksoz_norm, siklik)` ve run_id."""
    calisma = _calisma(
        ctx,
        kelime_frekans.KAYNAK,
        INGEST_ADIMI,
        f"once: ingest lugat --source {kelime_frekans.KAYNAK}",
    )
    satirlar = zincir.dosya_oku(calisma, LUGAT_ADI, f"{kelime_frekans.KAYNAK} {LUGAT_ADI}")
    sonuc: list[tuple[str, str, int]] = []
    for s in satirlar:
        siklik = s.nesne("kaynaklar").get("siklik")
        if not isinstance(siklik, int) or isinstance(siklik, bool) or siklik < 1:
            raise GirdiHatasi(f"{kelime_frekans.KAYNAK} {LUGAT_ADI}: satir {s.no}: siklik gecersiz")
        sonuc.append((s.metin("basliksoz"), s.metin("basliksoz_norm"), siklik))
    return sonuc, calisma.run_id


# --- (a) baslik sozler ------------------------------------------------------------------------


def _kapsama(
    sozler: Sequence[tuple[str, str, int]],
    anahtar: Callable[[str, str], str],
    kume: set[str],
) -> dict[str, object]:
    """Bir anahtarla `kume`ye giren baslik soz sayisi ve siklik agirligi."""
    toplam_siklik = sum(s for _, _, s in sozler)
    bulunan = [s for b, n, s in sozler if (k := anahtar(b, n)) and k in kume]
    return {
        "kume_boyutu": len(kume),
        "soz": _oran(len(bulunan), len(sozler)),
        "siklikli": _oran(sum(bulunan), toplam_siklik),
    }


def baslik_soz_raporu(
    sozler: Sequence[tuple[str, str, int]],
    rnk: Sequence[tuple[str, str]],
    rganeyev: Sequence[tuple[str, str]],
) -> dict[str, object]:
    """(a): Risale baslik sozlerinin lugat karsiligi ve eslestirme anahtari olcusu."""
    esleme = lugat_kaynak.esleme_anahtari
    rnk_k = {esleme(b) for b, _ in rnk} - {""}
    rg_k = {esleme(b) for b, _ in rganeyev} - {""}
    sinif: Counter[str] = Counter()
    siklik: Counter[str] = Counter()
    for b, _, s in sozler:
        k = esleme(b)
        ad = "rnk" if k in rnk_k else "yalniz_rganeyev" if k in rg_k else "hicbiri"
        sinif[ad] += 1
        siklik[ad] += s
    toplam, toplam_s = len(sozler), sum(s for _, _, s in sozler)
    karsilikli = sinif["rnk"] + sinif["yalniz_rganeyev"]
    karsilikli_s = siklik["rnk"] + siklik["yalniz_rganeyev"]
    adaylar: dict[str, Callable[[str, str], str]] = {
        "basliksoz_norm": lambda _b, n: n,
        "sozluk_ocr_anahtar": lambda b, _n: sozluk_ocr.anahtar(b),
        "esleme_anahtari": lambda b, _n: esleme(b),
    }
    anahtar_olcumu: dict[str, object] = {
        ad: _kapsama(sozler, f, {f(b, n) for b, n in rnk} - {""}) for ad, f in adaylar.items()
    }
    return {
        "baslik_soz": toplam,
        "toplam_siklik": toplam_s,
        "rnk": {"soz": _oran(sinif["rnk"], toplam), "siklikli": _oran(siklik["rnk"], toplam_s)},
        "yalniz_rganeyev": {
            "soz": _oran(sinif["yalniz_rganeyev"], toplam),
            "siklikli": _oran(siklik["yalniz_rganeyev"], toplam_s),
        },
        "rnk_ve_rganeyev": {
            "soz": _oran(karsilikli, toplam),
            "siklikli": _oran(karsilikli_s, toplam_s),
        },
        "hicbiri": {
            "soz": _oran(sinif["hicbiri"], toplam),
            "siklikli": _oran(siklik["hicbiri"], toplam_s),
        },
        "anahtar_olcumu": anahtar_olcumu,
        "secilen_anahtar": "esleme_anahtari",
    }


# --- (b) metin sozcukleri ---------------------------------------------------------------------


def turkce_kitaplar() -> frozenset[str]:
    """`shared/data/risale-kitaplar.json` tablosunda `dil = tr` olan kitap slug'lari."""
    return frozenset(k.slug for k in risale.kitaplar() if k.dil == "tr")


def sozcuk_say(
    birimler: Iterable[Mapping[str, object]], turkce: frozenset[str]
) -> tuple[Counter[str], dict[str, str], dict[str, int]]:
    """Turkce birimlerden `(gecis sikligi, sozcuk -> govde, birim sayilari)`.

    Sozcuk: `tr_narrow` sozcugu (rakamsiz, en az bir harf); govde: `tr_stem` ayni konumdaki sozcuk
    (konum sayilari ayni degilse sozcugun kendisi). Turkce olmayan kitap ve metni olmayan birim
    sayilir, okunmaz.
    """
    gecis: Counter[str] = Counter()
    govde: dict[str, str] = {}
    sayilar = {"birim": 0, "turkce_birim": 0, "metinsiz_birim": 0}
    for u in birimler:
        sayilar["birim"] += 1
        capa = u.get("anchor")
        if not isinstance(capa, str):
            raise GirdiHatasi("staged RNK birimi: anchor metin degil")
        slug = rnk_kitap_slugu(capa)
        if slug not in turkce:
            continue
        sayilar["turkce_birim"] += 1
        dar, kok = u.get("tr_narrow"), u.get("tr_stem")
        if not isinstance(dar, str) or dar == "":
            sayilar["metinsiz_birim"] += 1
            continue
        sozcukler = dar.split(" ")
        kokler = kok.split(" ") if isinstance(kok, str) else []
        if len(kokler) != len(sozcukler):
            kokler = sozcukler
        for s, k in zip(sozcukler, kokler, strict=True):
            if not any(h.isalpha() for h in s):
                continue
            gecis[s] += 1
            govde.setdefault(s, k)
    return gecis, govde, sayilar


def metin_sozcukleri_raporu(
    gecis: Mapping[str, int],
    govde: Mapping[str, str],
    rnk: Sequence[tuple[str, str]],
    rganeyev: Sequence[tuple[str, str]],
) -> tuple[dict[str, object], list[tuple[str, int]]]:
    """(b): benzersiz sozcuklerin lugat basligi (yalin) ya da govdesiyle karsilanma orani.

    Doner: `(rapor, karsiliksiz sozcuk listesi)`; liste gecis sikligina gore azalan, esitlikte
    alfabetik (rapora girmez).
    """
    esleme = lugat_kaynak.esleme_anahtari
    rnk_k = {esleme(b) for b, _ in rnk} - {""}
    hepsi = rnk_k | ({esleme(b) for b, _ in rganeyev} - {""})
    toplam_s, toplam_g = len(gecis), sum(gecis.values())

    def olc(kume: set[str]) -> dict[str, object]:
        yalin = yalniz_govde = 0
        yalin_g = govde_g = 0
        for s, n in gecis.items():
            if esleme(s) in kume:
                yalin += 1
                yalin_g += n
            elif esleme(govde[s]) in kume:
                yalniz_govde += 1
                govde_g += n
        karsilikli, karsilikli_g = yalin + yalniz_govde, yalin_g + govde_g
        return {
            "yalin": {"sozcuk": _oran(yalin, toplam_s), "gecis": _oran(yalin_g, toplam_g)},
            "yalniz_govde": {
                "sozcuk": _oran(yalniz_govde, toplam_s),
                "gecis": _oran(govde_g, toplam_g),
            },
            "toplam": {
                "sozcuk": _oran(karsilikli, toplam_s),
                "gecis": _oran(karsilikli_g, toplam_g),
            },
            "karsiliksiz": {
                "sozcuk": _oran(toplam_s - karsilikli, toplam_s),
                "gecis": _oran(toplam_g - karsilikli_g, toplam_g),
            },
        }

    karsiliksiz = sorted(
        (
            (s, n)
            for s, n in gecis.items()
            if esleme(s) not in hepsi and esleme(govde[s]) not in hepsi
        ),
        key=lambda c: (-c[1], c[0]),
    )
    dilimler: dict[str, dict[str, int]] = {}
    for alt, ust in SIKLIK_DILIMLERI:
        ad = f"{alt}+" if ust == 0 else str(alt) if alt == ust else f"{alt}-{ust}"
        secili = [n for _, n in karsiliksiz if n >= alt and (ust == 0 or n <= ust)]
        dilimler[ad] = {"sozcuk": len(secili), "gecis": sum(secili)}
    rapor: dict[str, object] = {
        "benzersiz_sozcuk": toplam_s,
        "toplam_gecis": toplam_g,
        "rnk_ve_rganeyev": olc(hepsi),
        "yalniz_rnk": olc(rnk_k),
        "karsiliksiz_siklik_dilimleri": dilimler,
        "karsiliksiz_en_sik_listesi": {
            "dosya": KARSILIKSIZ_ADI,
            "satir": min(EN_SIK_KARSILIKSIZ, len(karsiliksiz)),
        },
    }
    return rapor, karsiliksiz


# --- (c) terkipler ----------------------------------------------------------------------------


def terkipli_oku(veri: bytes) -> tuple[Counter[str], int]:
    """`kelime,frekans` terkip listesi: `(terkip -> siklik, bozuk satir)` (terkipte bosluk olur)."""
    try:
        metin = veri.decode("utf-8")
    except UnicodeDecodeError:
        raise GirdiHatasi("terkipli liste UTF-8 degil") from None
    satirlar = metin.split("\n")
    if satirlar and satirlar[-1] == "":
        satirlar.pop()
    if not satirlar or satirlar[0] != TERKIP_BASLIGI:
        raise GirdiHatasi("terkipli liste baslik satiri 'kelime,frekans' degil")
    sayac: Counter[str] = Counter()
    bozuk = 0
    for satir in satirlar[1:]:
        terkip, ayrac, sayi = satir.rpartition(",")
        if ayrac == "" or terkip.strip() == "" or not sayi.isascii() or not sayi.isdigit():
            bozuk += 1
            continue
        sayac[terkip] += int(sayi)
    return sayac, bozuk


def _terkipler(ctx: RunContext) -> tuple[Counter[str], dict[str, int]]:
    """Kelime-Frekans zip'indeki KITAP dosyalarinin `terkipli/` listeleri (bellekte)."""
    kilit = kelime_frekans.kilit_yukle()
    gelen = gelen_dizini(ctx.veri_kok, kelime_frekans.KAYNAK)
    tarih = gelen_tarihi_coz(gelen, None, kelime_frekans.KAYNAK)
    z = kelime_frekans.zip_denetle(kilit, kelime_frekans.gelen_zip_oku(gelen, tarih, kilit.zip_ad))
    on = f"{kilit.kok}/data/eRisale/analysis/terkipli/"
    toplam: Counter[str] = Counter()
    sayilar = {"kitap": len(kilit.kitaplar), "dosya_yok": 0, "bozuk_satir": 0}
    for kitap in kilit.kitaplar:
        uye = f"{on}{kitap}{kelime_frekans.FREKANS_SONEKI}"
        if not z.var_mi(uye):
            sayilar["dosya_yok"] += 1
            continue
        sayac, bozuk = terkipli_oku(z.oku(uye))
        toplam.update(sayac)
        sayilar["bozuk_satir"] += bozuk
    return toplam, sayilar


def terkip_raporu(
    risale_terkipleri: Mapping[str, int],
    rnk: Sequence[tuple[str, str]],
    rganeyev: Sequence[tuple[str, str]],
) -> dict[str, object]:
    """(c): Risale terkipleri <-> RNK ve rganeyev cok sozcuklu basliklari.

    Terkip anahtari `terkip_anahtari` (sozcuk sinirlari korunur). Cok sozcuklu baslik: kirpilmis
    ham baslikta bosluk ya da sekme olan baslik.
    """
    anahtar = lugat_kaynak.terkip_anahtari

    def cok_sozcuklu(basliklar: Iterable[tuple[str, str]]) -> set[str]:
        return {b for b, _ in basliklar if " " in b or "\t" in b}

    rnk_ham = cok_sozcuklu(rnk)
    rg_ham = cok_sozcuklu(rganeyev)
    rnk_k = {anahtar(b) for b in rnk_ham} - {""}
    rg_k = {anahtar(b) for b in rg_ham} - {""}
    risale_k: Counter[str] = Counter()
    for t, n in risale_terkipleri.items():
        k = anahtar(t)
        if k:
            risale_k[k] += n
    sinif: Counter[str] = Counter()
    siklik: Counter[str] = Counter()
    for k, n in risale_k.items():
        ad = "rnk" if k in rnk_k else "yalniz_rganeyev" if k in rg_k else "hicbiri"
        sinif[ad] += 1
        siklik[ad] += n
    toplam, toplam_s = len(risale_k), sum(risale_k.values())
    karsilikli, karsilikli_s = (
        sinif["rnk"] + sinif["yalniz_rganeyev"],
        siklik["rnk"] + siklik["yalniz_rganeyev"],
    )
    return {
        "risale_terkip": toplam,
        "risale_terkip_toplam_siklik": toplam_s,
        "rnk_cok_sozcuklu_baslik": len(rnk_ham),
        "rnk_cok_sozcuklu_anahtar": len(rnk_k),
        "rnk": {"terkip": _oran(sinif["rnk"], toplam), "siklikli": _oran(siklik["rnk"], toplam_s)},
        "yalniz_rganeyev": {
            "terkip": _oran(sinif["yalniz_rganeyev"], toplam),
            "siklikli": _oran(siklik["yalniz_rganeyev"], toplam_s),
        },
        "rnk_ve_rganeyev": {
            "terkip": _oran(karsilikli, toplam),
            "siklikli": _oran(karsilikli_s, toplam_s),
        },
        "hicbiri": {
            "terkip": _oran(sinif["hicbiri"], toplam),
            "siklikli": _oran(siklik["hicbiri"], toplam_s),
        },
        "rnk_terkibinin_risalede_gecen": _oran(len(rnk_k & set(risale_k)), len(rnk_k)),
    }


# --- ust duzey --------------------------------------------------------------------------------


def rapor_uret(ctx: RunContext) -> tuple[dict[str, object], list[tuple[str, int]]]:
    """Kapsama raporu (yalniz sayi) ve karsiliksiz sozcuk listesi (yerel dosya icin)."""
    rnk, rnk_run = _lugat_basliklari(ctx, lugat_kaynak.KAYNAK_RNK)
    rg, rg_run = _lugat_basliklari(ctx, lugat_kaynak.KAYNAK_RGANEYEV)
    sozler, kf_run = _risale_sozleri(ctx)
    metin = _calisma(ctx, RNK_METIN, ANCHOR_ADIMI, "once: ingest risale, normalize, anchor")
    gecis, govde, birim_sayilari = sozcuk_say(
        (s.veri for s in satirlari_akit(metin.klasor / lineage.UNITS_ADI, f"{RNK_METIN} units")),
        turkce_kitaplar(),
    )
    terkipler, terkip_sayilari = _terkipler(ctx)
    metin_raporu, karsiliksiz = metin_sozcukleri_raporu(gecis, govde, rnk, rg)
    rapor: dict[str, object] = {
        "tur": "lugat-kapsama",
        "surum": RAPOR_SURUMU,
        "kaynaklar": {
            "lugat_rnk": f"{lugat_kaynak.KAYNAK_RNK}/{rnk_run}",
            "lugat_rganeyev": f"{lugat_kaynak.KAYNAK_RGANEYEV}/{rg_run}",
            "kelime_frekans": f"{kelime_frekans.KAYNAK}/{kf_run}",
            "staged_rnk_metin": f"{RNK_METIN}/{metin.run_id}",
        },
        "lugat": {"rnk_madde": len(rnk), "rganeyev_alinan_madde": len(rg)},
        "baslik_soz": baslik_soz_raporu(sozler, rnk, rg),
        "metin_sozcukleri": {**metin_raporu, "birim": birim_sayilari},
        "terkipler": {**terkip_raporu(terkipler, rnk, rg), "girdi": terkip_sayilari},
        "not": (
            "Karsilik: lugat basligi ya da (metin sozcuklerinde) govdesi esleme anahtariyla ayni."
            " Gecis sikligi derleme kitaplardaki tekrarlari icerir. Yapay zeka ile tanim uretilmez."
        ),
    }
    return rapor, karsiliksiz


def _yaz(ctx: RunContext, ad: str, veri: bytes) -> str:
    klasor = ctx.veri_kok.joinpath(*RAPOR_KLASORU)
    klasor.mkdir(parents=True, exist_ok=True)
    hedef = klasor / ad
    gecici = klasor / (ad + ".tmp")
    gecici.write_bytes(veri)
    lineage.atomik_degistir(gecici, hedef)
    return lineage.goreli_yol(ctx.veri_kok, hedef)


def raporu_yaz(
    ctx: RunContext, rapor: Mapping[str, object], karsiliksiz: Sequence[tuple[str, int]]
) -> tuple[str, str]:
    """`lugat-kapsama.json` ve yerel `lugat-karsiliksiz.txt` (`sozcuk<TAB>gecis`, UTF-8, LF)."""
    liste = "".join(f"{s}\t{n}\n" for s, n in karsiliksiz[:EN_SIK_KARSILIKSIZ])
    return (
        _yaz(ctx, RAPOR_ADI, json_baytlari(dict(rapor))),
        _yaz(ctx, KARSILIKSIZ_ADI, liste.encode("utf-8")),
    )


def ozet_satiri(rapor: Mapping[str, object]) -> str:
    """Konsol icin tek satir ozet (yalniz yuzdeler)."""

    def al(*yol: str) -> object:
        deger: object = rapor
        for anahtar in yol:
            deger = deger[anahtar] if isinstance(deger, dict) else None
        return deger

    baslik = ("baslik_soz", "rnk_ve_rganeyev")
    metin = ("metin_sozcukleri", "rnk_ve_rganeyev", "toplam")
    return (
        f"baslik soz karsiligi %{al(*baslik, 'soz', 'yuzde')}"
        f" (siklikli %{al(*baslik, 'siklikli', 'yuzde')});"
        f" metin sozcugu karsiligi %{al(*metin, 'sozcuk', 'yuzde')}"
        f" (gecis %{al(*metin, 'gecis', 'yuzde')});"
        f" terkip karsiligi %{al('terkipler', 'rnk_ve_rganeyev', 'terkip', 'yuzde')}"
    )


def rapor_dosyasi(veri_kok: Path) -> Path:
    return veri_kok.joinpath(*RAPOR_KLASORU) / RAPOR_ADI
