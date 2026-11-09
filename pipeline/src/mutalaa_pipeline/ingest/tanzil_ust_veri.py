"""Tanzil ust veri alimi (A11.0/A11.2): `quran-data.xml` -> `data/raw` -> `data/staged` (K-43).

`mutalaa ingest tanzil --variant ust-veri`:

1. `data/gelen/tanzil-ust-veri/<YYYY-AA-GG>/quran-data.xml` dosyasini bayt olarak okur ve
   `tanzil.lock.json` `ust_veri` bolumuyle karsilastirir (dosya ozeti ve boyut; `metin_sha256` ve
   `bildirim_sha256` yoktur). Tutmazsa cikis 2 ve "kilit guncellenerek (/karar) alinir" uyarisi
   (K-39 guncellemesi). Kilitten sonra XML A04'un sertlestirilmis ayristirmasiyla (DOCTYPE ve
   ENTITY reddi, kati UTF-8; `export/ayet_sayilari.guvenli_kok`) okunur; kok `version` degeri
   kilitteki surumle ayni olmalidir. Dosya yalniz VERI olarak okunur, hicbir sey calistirilmaz.
2. Ham kopya `data/raw/tanzil-ust-veri/<tarih>/quran-data.xml` ve `fetch.json` (metin
   varyantlariyla ayni kalip; ayni baytlar zaten varsa yeni kopya acilmaz).
3. Staged cikti tur basina bir yapi JSONL'idir (`YAPI_DOSYALARI`): sure, cuz, rub (hizb
   ceyregi), menzil, ruku, sayfa ve secde. Her satir `tur`, `no`, `sura`, `aya`; sure satirlari
   ek olarak `ad_ar` (name), `tname`, `ename`, `type`, `order`, `ayas`, `start`, `rukus`; secde
   satirlari Tanzil'in kendi etiketini `type` olarak tasir (`recommended` ya da `obligatory`).
   Degerler dosyadan okunur; hicbiri duzeltilmez. `no` tur icinde 1'den kesintisizdir ve her
   tur okuma sirasinda artar.

Hata iletileri yalniz sayi, ozet (kisaltilmis), alan adi ve goreli yol tasir; XML icerigi asla.
"""

import json
import re
import shutil
import sys
import xml.etree.ElementTree as ET
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path
from typing import Final

from mutalaa_pipeline import cikis, lineage
from mutalaa_pipeline.export import ayet_sayilari
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.ingest.tanzil import (
    EN_BUYUK_GELEN_BAYT,
    FETCH_ADI,
    GELEN_KLASORU,
    INGEST_ADIMI,
    TARIH_DESENI,
    UST_VERI,
    UstVeriKilidi,
    _klasoru_tasi,
    _yaz_esitle,
    tarih_gecerli,
    ust_veri_kilidi_yukle,
)
from mutalaa_pipeline.komut_ortak import komutu_yurut
from mutalaa_pipeline.lineage import kisa_ozet
from mutalaa_pipeline.logs import json_baytlari
from mutalaa_pipeline.runctx import RunContext
from mutalaa_pipeline.staged import dosya_yaz, satirlari_oku

KAYNAK: Final = "tanzil-ust-veri"
GELEN_KAYNAK: Final = "tanzil-ust-veri"
DOSYA_ADI: Final = "quran-data.xml"
UYARI: Final = "Yeni Tanzil ust verisi kilit guncellenerek (/karar) alinir."
SAYI: Final = re.compile(r"[0-9]{1,9}")

# XML grubu -> (grup ogesi, satir ogesi, tur, staged dosyasi). Adlar dosyadan dogrulanmistir.
YAPI_TURLERI: Final = (
    ("suras", "sura", "sure", "sure.jsonl"),
    ("juzs", "juz", "cuz", "cuz.jsonl"),
    ("hizbs", "quarter", "rub", "rub.jsonl"),
    ("manzils", "manzil", "menzil", "menzil.jsonl"),
    ("rukus", "ruku", "ruku", "ruku.jsonl"),
    ("pages", "page", "sayfa", "sayfa.jsonl"),
    ("sajdas", "sajda", "secde", "secde.jsonl"),
)
YAPI_DOSYALARI: Final = {tur: dosya for _, _, tur, dosya in YAPI_TURLERI}
SECDE_TURLERI: Final = frozenset({"recommended", "obligatory"})
SURE_METIN_ALANLARI: Final = (("name", "ad_ar"), ("tname", "tname"), ("ename", "ename"))
SURE_SAYI_ALANLARI: Final = ("ayas", "start", "order", "rukus")


def gelen_dizini(veri_kok: Path) -> Path:
    return veri_kok / GELEN_KLASORU / GELEN_KAYNAK


def _tam_sayi(oge: ET.Element, ad: str, yer: str) -> int:
    deger = oge.get(ad)
    if deger is None:
        raise GirdiHatasi(f"{yer}: '{ad}' ozniteligi yok")
    if SAYI.fullmatch(deger) is None:
        raise GirdiHatasi(f"{yer}: '{ad}' ozniteligi ondalik ASCII tam sayi degil")
    return int(deger)


def _metin(oge: ET.Element, ad: str, yer: str) -> str:
    deger = oge.get(ad)
    if deger is None or deger == "":
        raise GirdiHatasi(f"{yer}: '{ad}' ozniteligi yok ya da bos")
    return deger


def yapi_ayristir(veri: bytes, surum: str | None = None) -> dict[str, list[dict[str, object]]]:
    """XML baytlarindan `tur -> satirlar`; sertlestirilmis ayristirma, kati denetim.

    Sure tablosu `ayet_sayilari.ayristir` ile (ardisik index, `start` toplamlari, ayet toplami)
    ayrica denetlenir. Her satirin sure ve ayeti tabloda var olmali; her turun `index` degeri
    1'den kesintisiz, baslangiclari okuma sirasinda artan olmalidir. `surum` verilirse kok
    `version` degeri onunla ayni olmalidir.
    """
    ust = ayet_sayilari.ayristir(veri)  # sure sayisi, ardisiklik, start toplami, toplam ayet
    if surum is not None and ust.surum != surum:
        raise GirdiHatasi("XML surumu kilitteki surumle ayni degil")
    kok = ayet_sayilari.guvenli_kok(veri)
    sonuc: dict[str, list[dict[str, object]]] = {}
    for grup_adi, oge_adi, tur, _ in YAPI_TURLERI:
        gruplar = [g for g in kok if g.tag == grup_adi]
        if len(gruplar) != 1:
            raise GirdiHatasi(f"<{grup_adi}> grubu {len(gruplar)} kez var; 1 bekleniyor")
        satirlar: list[dict[str, object]] = []
        for sira, oge in enumerate(gruplar[0], start=1):
            yer = f"<{grup_adi}> {sira}. oge"
            if oge.tag != oge_adi:
                raise GirdiHatasi(f"{yer}: <{oge.tag}> beklenmeyen oge")
            no = _tam_sayi(oge, "index", yer)
            if no != sira:
                raise GirdiHatasi(f"{yer}: index {no}; {sira} bekleniyor (ardisik degil)")
            satirlar.append(_satir(tur, no, oge, yer, ust.sayilar))
        if not satirlar:
            raise GirdiHatasi(f"<{grup_adi}> grubu bos")
        sonuc[tur] = satirlar
    _okuma_sirasi_denetle(sonuc)
    return sonuc


def _satir(
    tur: str, no: int, oge: ET.Element, yer: str, ayet_sayilari_: Sequence[int]
) -> dict[str, object]:
    if tur == "sure":
        satir: dict[str, object] = {"tur": tur, "no": no, "sura": no, "aya": 1}
        for kaynak, hedef in SURE_METIN_ALANLARI:
            satir[hedef] = _metin(oge, kaynak, yer)
        satir["type"] = _metin(oge, "type", yer)
        for ad in SURE_SAYI_ALANLARI:
            satir[ad] = _tam_sayi(oge, ad, yer)
        return satir
    sura, aya = _tam_sayi(oge, "sura", yer), _tam_sayi(oge, "aya", yer)
    if not 1 <= sura <= len(ayet_sayilari_) or not 1 <= aya <= ayet_sayilari_[sura - 1]:
        raise GirdiHatasi(f"{yer}: sura {sura} aya {aya} sure tablosunda yok")
    satir = {"tur": tur, "no": no, "sura": sura, "aya": aya}
    if tur == "secde":
        etiket = _metin(oge, "type", yer)
        if etiket not in SECDE_TURLERI:
            raise GirdiHatasi(f"{yer}: secde 'type' degeri recommended ya da obligatory degil")
        satir["type"] = etiket
    return satir


def _okuma_sirasi_denetle(sonuc: Mapping[str, Sequence[Mapping[str, object]]]) -> None:
    for tur, satirlar in sonuc.items():
        if tur == "sure":
            continue  # sure tablosunun sirasi ayet_sayilari.ayristir ile denetlendi
        konumlar = [(int(str(s["sura"])), int(str(s["aya"]))) for s in satirlar]
        if any(sonraki <= onceki for onceki, sonraki in pairwise(konumlar)):
            raise GirdiHatasi(f"{tur}: baslangic konumlari okuma sirasinda artmiyor")


# --- kilit -------------------------------------------------------------------------------


def uyusmazlik_iletisi(kilit: UstVeriKilidi, ozet: str, boyut: int) -> str:
    return (
        f"{KAYNAK}: dosya ozeti kilitle tutmuyor (beklenen {kisa_ozet(kilit.sha256)},"
        f" bulunan {kisa_ozet(ozet)}; boyut {kilit.boyut}/{boyut}). {UYARI}"
    )


def kilit_denetle(kilit: UstVeriKilidi, veri: bytes) -> None:
    """Dosya ozeti ve boyutu kilitle tutmuyorsa `GirdiHatasi` (cikis 2)."""
    ozet = lineage.sha256_bayt(veri)
    if ozet != kilit.sha256 or len(veri) != kilit.boyut:
        raise GirdiHatasi(uyusmazlik_iletisi(kilit, ozet, len(veri)))


def kilit_onerisi(veri: bytes, tarih: str, url: str) -> UstVeriKilidi:
    """Gelen dosyanin baytlarindan ilk kilit degerleri (hicbir sey yazmaz)."""
    ust = ayet_sayilari.ayristir(veri)
    return UstVeriKilidi(
        url=url,
        surum=ust.surum,
        alinma_tarihi=tarih,
        boyut=len(veri),
        sha256=lineage.sha256_bayt(veri),
    )


# --- gelen klasoru -------------------------------------------------------------------------


def gelen_tarihi_coz(gelen: Path, istenen: str | None) -> str:
    """`--gelen-tarih` ya da (verilmediyse) en yeni gecerli tarih klasoru."""
    if istenen is not None:
        if not tarih_gecerli(istenen):
            raise GirdiHatasi("--gelen-tarih YYYY-AA-GG biciminde gecerli bir tarih olmali")
        return istenen
    tarihler = (
        sorted(p.name for p in gelen.iterdir() if p.is_dir() and tarih_gecerli(p.name))
        if gelen.is_dir()
        else []
    )
    if not tarihler:
        raise GirdiHatasi(f"{GELEN_KLASORU}/{GELEN_KAYNAK} altinda tarih klasoru yok")
    return tarihler[-1]


def gelen_oku(gelen: Path, tarih: str) -> bytes:
    goreli = f"{GELEN_KLASORU}/{GELEN_KAYNAK}/{tarih}/{DOSYA_ADI}"
    yol = gelen / tarih / DOSYA_ADI
    try:
        if not yol.is_file():
            raise GirdiHatasi(f"{goreli} yok (--gelen-tarih ile baska bir klasor verilebilir)")
        if yol.stat().st_size > EN_BUYUK_GELEN_BAYT:
            raise GirdiHatasi(f"{goreli} cok buyuk (sinir {EN_BUYUK_GELEN_BAYT} bayt)")
        return yol.read_bytes()
    except OSError:
        raise GirdiHatasi(f"{goreli} okunamadi") from None


# --- ham kopya -----------------------------------------------------------------------------


def _mevcut_ham(kok: Path, kilit: UstVeriKilidi) -> Path | None:
    """`raw/<kaynak>/` altinda ayni baytlara sahip kopya varsa (en eski tarih) yolu."""
    if not kok.is_dir():
        return None
    for klasor in sorted(kok.iterdir(), key=lambda yol: yol.name):
        if not klasor.is_dir() or TARIH_DESENI.fullmatch(klasor.name) is None:
            continue
        aday = klasor / DOSYA_ADI
        if (
            aday.is_file()
            and aday.stat().st_size == kilit.boyut
            and lineage.sha256_dosya(aday) == kilit.sha256
        ):
            return aday
    return None


def _fetch_kaydi(kilit: UstVeriKilidi, tarih: str) -> dict[str, object]:
    return {
        "kaynak": KAYNAK,
        "varyant": UST_VERI,
        "dosya": DOSYA_ADI,
        "url": kilit.url,
        "surum": kilit.surum,
        "alinma_tarihi": tarih,
        "boyut": kilit.boyut,
        "sha256": kilit.sha256,
        "gelen_yol": f"{GELEN_KLASORU}/{GELEN_KAYNAK}/{tarih}/{DOSYA_ADI}",
    }


def ham_yol(
    ctx: RunContext, gelen_yol: Path, tarih: str, veri: bytes, kilit: UstVeriKilidi
) -> Path:
    """Ham kopyanin yolu; yoksa `data/raw` altina yazar (`--dry-run`da yazmaz)."""
    kok = ctx.raw_dizin(KAYNAK)
    mevcut = _mevcut_ham(kok, kilit)
    if mevcut is not None:
        return mevcut
    hedef = kok / tarih
    if hedef.exists():
        raise GirdiHatasi(
            f"raw/{KAYNAK}/{tarih} zaten var ve baska bir dosya tasiyor"
            " (data/raw degismez); yeni bir gelen tarih klasoru kullanin"
        )
    if ctx.dry_run:
        return gelen_yol
    gecici = kok / f".{tarih}.gecici-{ctx.run_id}"
    try:
        gecici.mkdir(parents=True)
        _yaz_esitle(gecici / DOSYA_ADI, veri)
        _yaz_esitle(gecici / FETCH_ADI, json_baytlari(_fetch_kaydi(kilit, tarih)))
        _klasoru_tasi(gecici, hedef)
    except OSError:
        esdeger = _mevcut_ham(kok, kilit)
        if esdeger is not None:
            return esdeger
        raise GirdiHatasi(f"raw/{KAYNAK}/{tarih} yazilamadi") from None
    finally:
        if gecici.exists():
            shutil.rmtree(gecici, ignore_errors=True)
    return hedef / DOSYA_ADI


# --- calistirma ----------------------------------------------------------------------------


@dataclass(frozen=True)
class UstVeriSonucu:
    run_id: str
    atlandi: bool
    satir_sayisi: int
    klasor: Path | None
    onceki_run_id: str | None = None


def run_ust_veri(
    ctx: RunContext, gelen_tarih: str | None = None, kilit: UstVeriKilidi | None = None
) -> UstVeriSonucu:
    """Kaynak kaydi, kilit, ham kopya, parmak izi, yapi satirlari, manifest (en son)."""
    ctx.require_sources(KAYNAK)
    ctx.gunluk.yaz("INFO", "ust_veri_basla", source_id=KAYNAK)
    kilit = kilit if kilit is not None else ust_veri_kilidi_yukle()
    gelen = gelen_dizini(ctx.veri_kok)
    tarih = gelen_tarihi_coz(gelen, gelen_tarih)
    veri = gelen_oku(gelen, tarih)
    kilit_denetle(kilit, veri)  # tutmazsa raw'a hicbir sey yazilmaz
    yapi = yapi_ayristir(veri, kilit.surum)
    ham = ham_yol(ctx, gelen / tarih / DOSYA_ADI, tarih, veri, kilit)
    girdiler = [lineage.Girdi(yol=lineage.goreli_yol(ctx.veri_kok, ham), sha256=kilit.sha256)]
    parmak = ctx.parmak_izi(girdiler)
    sayilar = {tur: len(satirlar) for tur, satirlar in yapi.items()}

    onceki = lineage.son_basarili(ctx.staged_kaynak_dizini(KAYNAK), ctx.adim)
    if lineage.atlanabilir(
        onceki=onceki[2] if onceki else None,
        parmak=parmak,
        git_kirli=ctx.git().kirli,
        force=ctx.force,
        veri_kok=ctx.veri_kok,
    ):
        ctx.gunluk.yaz("INFO", "ust_veri_atlandi", source_id=KAYNAK)
        ctx.sayi("atlandi", 1)
        return UstVeriSonucu(ctx.run_id, True, 0, None, onceki[0] if onceki else None)

    ciktilar = [
        dosya_yaz(ctx, KAYNAK, YAPI_DOSYALARI[tur], satirlar) for tur, satirlar in yapi.items()
    ]
    toplam = sum(sayilar.values())
    for tur, adet in sayilar.items():
        ctx.sayi(tur, adet)
    ctx.sayi("ham_boyut", len(veri))
    if ctx.dry_run:
        ctx.gunluk.yaz("INFO", "ust_veri_dry_run", source_id=KAYNAK, sayilar=sayilar)
        return UstVeriSonucu(ctx.run_id, False, toplam, None)
    klasor = ctx.staged_dizin(KAYNAK)
    ctx.manifest_yaz(
        klasor,
        girdiler=girdiler,
        ciktilar=ciktilar,
        parmak=parmak,
        ayrintilar={
            "varyant": UST_VERI,
            "surum": kilit.surum,
            "gelen_tarih": tarih,
            "kilit": {"boyut": kilit.boyut, "sha256": kilit.sha256},
            "sayilar": sayilar,
        },
    )
    ctx.gunluk.yaz("INFO", "ust_veri_bitti", source_id=KAYNAK, sayilar=sayilar)
    return UstVeriSonucu(ctx.run_id, False, toplam, klasor)


def yapi_oku(klasor: Path, ad: str, etiket: str) -> list[dict[str, object]]:
    """Bir staged yapi dosyasinin satirlari (kati JSONL)."""
    try:
        veri = (klasor / ad).read_bytes()
    except OSError:
        raise GirdiHatasi(f"{etiket}: {ad} okunamadi") from None
    return [s.veri for s in satirlari_oku(veri, f"{etiket} {ad}")]


def kilit_oner_metni(veri_kok: Path, gelen_tarih: str | None, url: str) -> str:
    """`--kilit-oner`: gelen dosyadan hesaplanan `ust_veri` girdisi (JSON); hicbir sey yazmaz."""
    gelen = gelen_dizini(veri_kok)
    tarih = gelen_tarihi_coz(gelen, gelen_tarih)
    kilit = kilit_onerisi(gelen_oku(gelen, tarih), tarih, url)
    return json.dumps({"ust_veri": kilit.sozluk()}, ensure_ascii=True, indent=2) + "\n"


def komut_ingest_ust_veri(
    *,
    gelen_tarih: str | None,
    dry_run: bool,
    force: bool,
    config: Path | None,
    kok: Path | None,
) -> int:
    """`ingest tanzil --variant ust-veri` komutu; cikis kodunu dondurur."""

    def govde(ctx: RunContext) -> int:
        sonuc = run_ust_veri(ctx, gelen_tarih)
        if sonuc.atlandi:
            ozet = f"atlandi (parmak izi onceki calistirmayla ayni, run {sonuc.onceki_run_id})"
        elif ctx.dry_run:
            ozet = f"{sonuc.satir_sayisi} satir (dry-run, hicbir sey yazilmadi)"
        else:
            ozet = f"{sonuc.satir_sayisi} satir, run {sonuc.run_id}"
        sys.stdout.write(f"ingest {KAYNAK}: {ozet}\n")
        return cikis.BASARILI

    return komutu_yurut(
        komut=f"ingest tanzil --variant {UST_VERI}",
        adim=INGEST_ADIMI,
        kaynaklar=[KAYNAK],
        config=config,
        kok=kok,
        govde=govde,
        force=force,
        dry_run=dry_run,
        parametreler={"variant": UST_VERI},
    )
