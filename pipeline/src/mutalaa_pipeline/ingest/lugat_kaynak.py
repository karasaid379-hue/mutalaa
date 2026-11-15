"""Lugat kaynaklari: RNK ve rganeyev/Sozluk (A20.6b, K-52 madde 10 ve 14): gelen -> raw -> staged.

Iki kaynak, iki biçim (guvenilmeyen veri; yalniz bayt olarak okunur, hicbir sey calistirilmaz):

* `lugat-rnk` (`lugat.txt`): satir basina `BASLIK|tanim`; 76.293 satir; maddelerin TAMAMI alinir.
* `lugat-sozluk-rganeyev` (`words.txt`): satir basina `baslik: tanim` (ayrac satirdaki ILK `:`,
  ardindan gelen tek bosluk ayracin parcasidir; 9 satirda bosluk yoktur); yalniz RNK lugatinda
  esleme anahtari (`esleme_anahtari`) bulunmayan basliklar alinir (ayni basligin birden cok
  satiri birlikte).

KURALLAR

* Satir sirasi anlam sirasidir: ayni HAM baslik (bayt bayt esit) birden cok satirda ise
  `anlam_no` 1, 2, 3... alir. Normalize baslik tekil degildir; birlestirme YAPILMAZ.
* `tanim_tr` kaynak satirindaki tanimdir, BAYT BAYT: NFC yok, hicbir karakter degismez. TEK
  istisna KIRPMA: baslik ve tanimin basindaki ve sonundaki U+0020 ve U+0009 atilir (ayrac
  bosluklari ve satir sonu artiklari; dilin `strip()` islevi KULLANILMAZ, U+00A0'i da keserdi).
  Kirpilan satir sayisi kilitte durur (`kirpilan_baslik`, `kirpilan_tanim`). Baslik kirpilinca
  yalniz bosluk farki olan iki ham baslik tek baslik olur (RNK'da 1 baslik).
* Bozuk satir (bos, NUL iceren, ayracsiz, bos baslikli, bos tanimli, harf/rakami olmayan
  baslikli) atlanir, nedenine gore sayilir, kilitte SAYI olarak durur; tahminle onarilmaz.
* Baslik ham yazimiyla saklanir (`basliksoz`). Eslemede iki anahtar vardir (olcumle secildi,
  bkz. `qa/lugat_kapsama.py`): `basliksoz_norm` (arama anahtari, sutun) ve `esleme_anahtari`
  (`sozluk_ocr.anahtar` + harf/rakam disindakilerin atilmasi). Risale baslik sozu (staged
  Kelime-Frekans) ile lugat basligi `esleme_anahtari` ile baglanir; hangisinin daha iyi oldugu
  kapsama raporunda olculur (`anahtar_olcumu`).
* Eslesen maddeye `kaynaklar.siklik` ve `kaynaklar.kitaplar` (eslesen Risale baslik sozlerinin
  toplami), `kelime_frekans_karsiligi = true` ve `risale_basliksoz` (en sik eslesen soz, ham
  yazim) yazilir; `duzey` = `duzey_hesapla(siklik)` (1-3). Eslesmeyen maddede
  `kelime_frekans_karsiligi = false`, `siklik`/`kitaplar` yok, `duzey = 4`. Kelime-Frekans
  `anlam` degeri ve staged Kelime-Frekans satirlari OKUNMAZ ve DEGISMEZ: karsilik bilgisi yalniz
  bu kaynaklarin `kaynaklar` alaninda durur.

Cikti `staged/<kaynak>/<run_id>/lugat.jsonl` (`basliksoz`, `anlam_no` sirali) ve manifest; ham
dosya `data/raw/<kaynak>/<tarih>/` altina ayni baytlarla kopyalanir (`meal_ortak.ham_kopyala`).
Kilit dosyalari `lugat_rnk.lock.json` ve `lugat_sozluk_rganeyev.lock.json` yalniz SAYI ve ozet
tasir; degisiklik `/karar` ister. Iletiler yalniz sayi ve kisaltilmis ad tasir; icerik asla.
"""

import json
import sys
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Final, NamedTuple

from mutalaa_pipeline import cikis, lineage, sources, zincir
from mutalaa_pipeline.export.ortak import GirdiHatasi, kati_json
from mutalaa_pipeline.ingest import kelime_frekans, sozluk_ocr
from mutalaa_pipeline.ingest.lugat_madde import (
    DUZEY_RISALEDE_YOK,
    LUGAT_ADI,
    MADDE_ANAHTARI_KAYNAK,
    basliksoz_norm,
    duzey_hesapla,
    madde_satiri_kaynak,
)
from mutalaa_pipeline.ingest.meal_ortak import gelen_dizini, gelen_tarihi_coz, ham_kopyala
from mutalaa_pipeline.ingest.tanzil import INGEST_ADIMI, tarih_gecerli
from mutalaa_pipeline.komut_ortak import komutu_yurut
from mutalaa_pipeline.lineage import OZET_DESENI, kisa_ozet
from mutalaa_pipeline.runctx import RunContext
from mutalaa_pipeline.staged import Satir, dosya_yaz

KAYNAK_RNK: Final = "lugat-rnk"
KAYNAK_RGANEYEV: Final = "lugat-sozluk-rganeyev"
KAYNAKLAR: Final = (KAYNAK_RNK, KAYNAK_RGANEYEV)
KILIT_SURUMU: Final = 1
EN_BUYUK_BAYT: Final = 32 << 20  # gercek dosyalar 5,2 MB ve 4,7 MB
KIRPILAN: Final = " \t"
# Editorun yazdigi ya da duzenledigi tanimin sunucudaki ust siniri (`LugatMaddeText.MaxLength`,
# kod noktasi). Kaynak tanimina ingest'te sinir uygulanmaz (bayt bayt alinir); bu esigi asan
# tanim kilitte `uzun_tanim` olarak SAYILIR: duzenlemesiz onaylanabilir, duzenlenecekse editor
# kisaltmalidir.
TANIM_ESIGI: Final = 2000
BOM: Final = b"\xef\xbb\xbf"
UYARI: Final = "Yeni lugat surumu kilit guncellenerek (/karar) alinir."


@dataclass(frozen=True)
class Bicim:
    """Bir lugat kaynaginin dosya biçimi ve kilit yolu."""

    slug: str
    dosya: str
    ayrac: str
    kilit_dosyasi: str
    cikarici: str
    rnk_bagimli: bool  # True: yalniz RNK'da olmayan basliklar alinir
    ayrac_bosluk: bool  # True: ayractan hemen sonraki TEK U+0020 ayracin parcasidir (kirpma degil)


BICIMLER: Final[Mapping[str, Bicim]] = {
    KAYNAK_RNK: Bicim(
        KAYNAK_RNK, "lugat.txt", "|", "lugat_rnk.lock.json", "lugat-rnk-cikarici-1", False, False
    ),
    KAYNAK_RGANEYEV: Bicim(
        KAYNAK_RGANEYEV,
        "words.txt",
        ":",
        "lugat_sozluk_rganeyev.lock.json",
        "lugat-rganeyev-cikarici-1",
        True,
        True,
    ),
}
# Testler `monkeypatch.setitem` ile kendi kilit yollarini verir.
KILIT_YOLLARI: Final[dict[str, Path]] = {
    slug: Path(__file__).with_name(b.kilit_dosyasi) for slug, b in BICIMLER.items()
}
BOZUK_ANAHTARLARI: Final = (
    "bos_satir",
    "nul",
    "ayracsiz",
    "bos_baslik",
    "bos_tanim",
    "normsuz",
)
SAYI_ANAHTARLARI: Final = (
    "satir",
    *(f"bozuk_{a}" for a in BOZUK_ANAHTARLARI),
    "gecerli_madde",
    "kirpilan_baslik",
    "kirpilan_tanim",
    "benzersiz_ham_baslik",
    "benzersiz_esleme_anahtari",
    "benzersiz_basliksoz_norm",
    "cok_anlamli_baslik",
    "en_cok_anlam",
    "alinan_madde",
    "alinan_ham_baslik",
    "anahtarsiz_madde",
    "uzun_tanim",
    "i_sapkali_baslik",
    "i_sapkali_sozcuk_basi",
)
KILIT_ALANLARI: Final = (
    "surum",
    "kaynak",
    "url",
    "kayit_surumu",
    "alinma_tarihi",
    "dosya",
    "boyut",
    "sha256",
    "bagimli_sha256",
    "sayilar",
)
I_SAPKALI: Final = "\N{LATIN SMALL LETTER I WITH CIRCUMFLEX}"


def veri_surumu(slug: str, sha256: str) -> str:
    """`data_version`: kaynak kimligi ve dosya ozetinin ilk 12 hanesi."""
    return f"{slug}@{kisa_ozet(sha256)}"


def _ad(deger: str) -> str:
    kesik = deger if len(deger) <= 40 else deger[:37] + "..."
    return kesik.encode("ascii", "backslashreplace").decode("ascii")


# --- anahtarlar ------------------------------------------------------------------------------


@lru_cache(maxsize=1 << 18)
def _norm(baslik: str) -> str:
    return basliksoz_norm(baslik)


@lru_cache(maxsize=1 << 18)
def esleme_anahtari(sozcuk: str) -> str:
    """Eslestirme anahtari: `sozluk_ocr.anahtar` (Turkce kucuk harf, kesme ve tire silinmis, genis
    katlama) ve harf ya da rakam OLMAYAN her karakterin (bosluk, parantez, nokta) atilmasi."""
    return "".join(h for h in sozluk_ocr.anahtar(sozcuk) if h.isalnum())


@lru_cache(maxsize=1 << 18)
def terkip_anahtari(sozcuk: str) -> str:
    """Terkip (cok sozcuklu baslik) anahtari: `anahtar` ve harf/rakam disindakiler BOSLUK olur;
    sozcuk sinirlari korunur, tekrarlayan bosluklar tek olur."""
    govde = "".join(h if h.isalnum() else " " for h in sozluk_ocr.anahtar(sozcuk))
    return " ".join(govde.split())


# --- ayristirma -------------------------------------------------------------------------------


class Madde(NamedTuple):
    """Kaynak dosyadan ayristirilmis bir madde (kirpilmis baslik ve tanim)."""

    baslik: str
    anlam_no: int
    tanim: str
    norm: str  # basliksoz_norm
    anahtar: str  # esleme_anahtari


@dataclass(frozen=True)
class Ayristirma:
    maddeler: list[Madde]
    satir: int
    bozuk: Mapping[str, int]
    kirpilan_baslik: int
    kirpilan_tanim: int


def ayristir(veri: bytes, bicim: Bicim) -> Ayristirma:
    """Dosya baytlarini ayristirir; dosya duzeyi hata `GirdiHatasi`, satir hatasi SAYILIR.

    UTF-8 BOM'suz, CR yok; son satirin LF'si olmayabilir (gercek dosyalarda yoktur). Bos dosya
    hatadir. Ayrac satirdaki ILK `bicim.ayrac` dizgesidir; rganeyev'de ayractan hemen sonraki tek
    bosluk ayracin parcasidir (`ayrac_bosluk`). Hata iletileri yalniz kaynak kimligi ve sayi tasir.
    """
    etiket, ayrac = bicim.slug, bicim.ayrac
    if len(veri) > EN_BUYUK_BAYT:
        raise GirdiHatasi(f"{_ad(etiket)}: dosya cok buyuk (sinir {EN_BUYUK_BAYT} bayt)")
    if veri.startswith(BOM) or b"\r" in veri:
        raise GirdiHatasi(f"{_ad(etiket)}: BOM ya da CR var (UTF-8 BOM'suz, LF olmali)")
    try:
        metin = veri.decode("utf-8")
    except UnicodeDecodeError:
        raise GirdiHatasi(f"{_ad(etiket)}: UTF-8 degil") from None
    satirlar = metin.split("\n")
    if satirlar[-1] == "":
        satirlar.pop()
    if not satirlar:
        raise GirdiHatasi(f"{_ad(etiket)}: dosya bos")
    bozuk = dict.fromkeys(BOZUK_ANAHTARLARI, 0)
    sayac: Counter[str] = Counter()
    maddeler: list[Madde] = []
    kirpilan_baslik = kirpilan_tanim = 0
    for satir in satirlar:
        if satir == "":
            bozuk["bos_satir"] += 1
            continue
        if "\x00" in satir:
            bozuk["nul"] += 1
            continue
        i = satir.find(ayrac)
        if i < 0:
            bozuk["ayracsiz"] += 1
            continue
        ham_baslik, ham_tanim = satir[:i], satir[i + len(ayrac) :]
        if bicim.ayrac_bosluk and ham_tanim.startswith(" "):
            ham_tanim = ham_tanim[1:]
        baslik, tanim = ham_baslik.strip(KIRPILAN), ham_tanim.strip(KIRPILAN)
        if baslik == "":
            bozuk["bos_baslik"] += 1
            continue
        if tanim == "":
            bozuk["bos_tanim"] += 1
            continue
        norm = _norm(baslik)
        if norm == "":
            bozuk["normsuz"] += 1
            continue
        sayac[baslik] += 1
        kirpilan_baslik += baslik != ham_baslik
        kirpilan_tanim += tanim != ham_tanim
        maddeler.append(Madde(baslik, sayac[baslik], tanim, norm, esleme_anahtari(baslik)))
    return Ayristirma(maddeler, len(satirlar), bozuk, kirpilan_baslik, kirpilan_tanim)


def rnk_anahtarlari(ayr: Ayristirma) -> frozenset[str]:
    """RNK lugatinin bos olmayan esleme anahtarlari."""
    return frozenset(m.anahtar for m in ayr.maddeler if m.anahtar)


def sec(bicim: Bicim, ayr: Ayristirma, rnk: frozenset[str] | None) -> list[Madde]:
    """Alinacak maddeler: RNK'da hepsi; rganeyev'de yalniz anahtari RNK'da OLMAYANLAR.

    Bos anahtarli madde RNK ile karsilastirilamaz: alinir (`anahtarsiz_madde` sayilir).
    """
    if not bicim.rnk_bagimli:
        return list(ayr.maddeler)
    if rnk is None:
        raise GirdiHatasi(f"{bicim.slug}: RNK lugati olmadan secim yapilamaz")
    return [m for m in ayr.maddeler if m.anahtar == "" or m.anahtar not in rnk]


def sayilari_hesapla(ayr: Ayristirma, secilen: Sequence[Madde]) -> dict[str, int]:
    """Kilitte durmasi gereken sayilar (`SAYI_ANAHTARLARI`; yalniz sayi)."""
    ham = Counter(m.baslik for m in ayr.maddeler)
    alinan_ham = {m.baslik for m in secilen}
    sayilar: dict[str, int] = {
        "satir": ayr.satir,
        **{f"bozuk_{a}": n for a, n in ayr.bozuk.items()},
        "gecerli_madde": len(ayr.maddeler),
        "kirpilan_baslik": ayr.kirpilan_baslik,
        "kirpilan_tanim": ayr.kirpilan_tanim,
        "benzersiz_ham_baslik": len(ham),
        "benzersiz_esleme_anahtari": len({m.anahtar for m in ayr.maddeler if m.anahtar}),
        "benzersiz_basliksoz_norm": len({m.norm for m in ayr.maddeler}),
        "cok_anlamli_baslik": sum(1 for n in ham.values() if n > 1),
        "en_cok_anlam": max(ham.values(), default=0),
        "alinan_madde": len(secilen),
        "alinan_ham_baslik": len(alinan_ham),
        "anahtarsiz_madde": sum(1 for m in secilen if m.anahtar == ""),
        "uzun_tanim": sum(1 for m in secilen if len(m.tanim) > TANIM_ESIGI),
        "i_sapkali_baslik": sum(1 for b in alinan_ham if I_SAPKALI in b),
        "i_sapkali_sozcuk_basi": sum(
            1 for b in alinan_ham if any(s.startswith(I_SAPKALI) for s in b.split())
        ),
    }
    return sayilar


# --- Risale baslik soz dizini ----------------------------------------------------------------


@dataclass
class RisaleSoz:
    """Bir esleme anahtarina dusen Risale baslik sozlerinin toplami."""

    toplam: int
    kitaplar: dict[str, int]
    soz: str  # en sik soz (esitlikte alfabetik); ham yazim
    soz_siklik: int


def risale_dizini(satirlar: Iterable[Mapping[str, object]]) -> dict[str, RisaleSoz]:
    """Staged Kelime-Frekans satirlarindan `esleme_anahtari -> RisaleSoz` (satirlara dokunmaz)."""
    dizin: dict[str, RisaleSoz] = {}
    for s in satirlar:
        baslik, kaynaklar = s.get("basliksoz"), s.get("kaynaklar")
        if not isinstance(baslik, str) or not isinstance(kaynaklar, dict):
            raise GirdiHatasi("Kelime-Frekans staged satiri: basliksoz ya da kaynaklar bozuk")
        siklik, kitaplar = kaynaklar.get("siklik"), kaynaklar.get("kitaplar")
        if (
            not isinstance(siklik, int)
            or isinstance(siklik, bool)
            or siklik < 1
            or not isinstance(kitaplar, dict)
            or not all(isinstance(n, int) and not isinstance(n, bool) for n in kitaplar.values())
        ):
            raise GirdiHatasi("Kelime-Frekans staged satiri: siklik ya da kitaplar bozuk")
        anahtar = esleme_anahtari(baslik)
        if anahtar == "":
            continue
        mevcut = dizin.get(anahtar)
        if mevcut is None:
            dizin[anahtar] = RisaleSoz(siklik, dict(kitaplar), baslik, siklik)
            continue
        mevcut.toplam += siklik
        for kitap, n in kitaplar.items():
            mevcut.kitaplar[kitap] = mevcut.kitaplar.get(kitap, 0) + n
        if (-siklik, baslik) < (-mevcut.soz_siklik, mevcut.soz):
            mevcut.soz, mevcut.soz_siklik = baslik, siklik
    return dizin


def kaynaklar_nesnesi(
    anahtar: str, dizin: Mapping[str, RisaleSoz]
) -> tuple[dict[str, object], int]:
    """Maddenin `kaynaklar` nesnesi ve duzeyi (Risale eslesmesi varsa 1-3, yoksa 4)."""
    karsilik = dizin.get(anahtar) if anahtar else None
    if karsilik is None:
        return {"kelime_frekans_karsiligi": False}, DUZEY_RISALEDE_YOK
    return (
        {
            "kelime_frekans_karsiligi": True,
            "risale_basliksoz": karsilik.soz,
            "siklik": karsilik.toplam,
            "kitaplar": dict(sorted(karsilik.kitaplar.items())),
        },
        duzey_hesapla(karsilik.toplam),
    )


def lugat_satirlari(
    slug: str, maddeler: Iterable[Madde], dizin: Mapping[str, RisaleSoz], data_version: str
) -> list[dict[str, object]]:
    """Alinan maddelerin staged satirlari (siralamayi `dosya_yaz` yapar)."""
    satirlar: list[dict[str, object]] = []
    for m in maddeler:
        kaynaklar, duzey = kaynaklar_nesnesi(m.anahtar, dizin)
        satirlar.append(
            madde_satiri_kaynak(
                source_id=slug,
                basliksoz=m.baslik,
                anlam_no=m.anlam_no,
                tanim_tr=m.tanim,
                duzey=duzey,
                kaynaklar=kaynaklar,
                data_version=data_version,
            )
        )
    return satirlar


def uret(
    bicim: Bicim,
    veri: bytes,
    sha256: str,
    rnk_veri: bytes | None,
    risale_satirlari: Iterable[Mapping[str, object]],
) -> tuple[list[dict[str, object]], Ayristirma, list[Madde]]:
    """Ham dosyalardan (ve staged Kelime-Frekans satirlarindan) staged satirlari yeniden uretir.

    Ingest ve QA (G-BUT) ayni islevi kullanir: tek tanim.
    """
    ayr = ayristir(veri, bicim)
    rnk = None
    if bicim.rnk_bagimli:
        if rnk_veri is None:
            raise GirdiHatasi(f"{bicim.slug}: RNK lugat dosyasi gerekli")
        rnk = rnk_anahtarlari(ayristir(rnk_veri, BICIMLER[KAYNAK_RNK]))
    secilen = sec(bicim, ayr, rnk)
    satirlar = lugat_satirlari(
        bicim.slug, secilen, risale_dizini(risale_satirlari), veri_surumu(bicim.slug, sha256)
    )
    return satirlar, ayr, secilen


# --- kilit -----------------------------------------------------------------------------------


@dataclass(frozen=True)
class LugatKaynakKilidi:
    """`lugat_rnk.lock.json` / `lugat_sozluk_rganeyev.lock.json`: dosya kimligi ve sayilar."""

    kaynak: str
    url: str
    kayit_surumu: str
    alinma_tarihi: str
    dosya: str
    boyut: int
    sha256: str
    bagimli_sha256: str | None  # rganeyev icin RNK dosyasinin ozeti
    sayilar: Mapping[str, int]

    def sozluk(self) -> dict[str, object]:
        return {
            "surum": KILIT_SURUMU,
            "kaynak": self.kaynak,
            "url": self.url,
            "kayit_surumu": self.kayit_surumu,
            "alinma_tarihi": self.alinma_tarihi,
            "dosya": self.dosya,
            "boyut": self.boyut,
            "sha256": self.sha256,
            "bagimli_sha256": self.bagimli_sha256,
            "sayilar": dict(self.sayilar),
        }


def _kh(slug: str, mesaj: str) -> GirdiHatasi:
    return GirdiHatasi(f"{BICIMLER[slug].kilit_dosyasi}: {mesaj}")


def _tam(slug: str, deger: object, yer: str) -> int:
    if type(deger) is not int or deger < 0:
        raise _kh(slug, f"{yer} negatif olmayan tam sayi olmali")
    return deger


def _ozet(slug: str, deger: object, yer: str) -> str:
    if not isinstance(deger, str) or OZET_DESENI.fullmatch(deger) is None:
        raise _kh(slug, f"{yer} 64 haneli kucuk harfli onaltilik olmali")
    return deger


def kilit_coz(slug: str, ham: bytes) -> LugatKaynakKilidi:
    """Kilit dosyasinin baytlarini kati bicimde cozer; bicim hatasi `GirdiHatasi`."""
    if slug not in BICIMLER:
        raise GirdiHatasi("lugat kaynagi bilinmiyor")
    bicim = BICIMLER[slug]
    if ham.startswith(BOM) or b"\r" in ham:
        raise _kh(slug, "BOM ya da CR var (UTF-8 BOM'suz, LF olmali)")
    try:
        veri = kati_json(ham.decode("utf-8"))
    except UnicodeDecodeError:
        raise _kh(slug, "UTF-8 degil") from None
    except GirdiHatasi as hata:
        raise _kh(slug, str(hata)) from None
    if not isinstance(veri, dict) or set(veri) != set(KILIT_ALANLARI):
        raise _kh(slug, f"alanlar {', '.join(KILIT_ALANLARI)} olmali")
    if veri["surum"] != KILIT_SURUMU or veri["kaynak"] != slug or veri["dosya"] != bicim.dosya:
        raise _kh(slug, "surum, kaynak ya da dosya adi desteklenmiyor")
    url, kayit_surumu, tarih = veri["url"], veri["kayit_surumu"], veri["alinma_tarihi"]
    if not isinstance(url, str) or not url.startswith("https://"):
        raise _kh(slug, "url https:// ile baslayan metin olmali")
    if not isinstance(kayit_surumu, str) or kayit_surumu == "":
        raise _kh(slug, "kayit_surumu bos olmayan metin olmali")
    if not isinstance(tarih, str) or not tarih_gecerli(tarih):
        raise _kh(slug, "alinma_tarihi YYYY-AA-GG olmali")
    bagimli = veri["bagimli_sha256"]
    if bicim.rnk_bagimli != (bagimli is not None):
        raise _kh(slug, "bagimli_sha256 yalniz RNK'ya bagimli kaynakta dolu olmali")
    sayilar_ham = veri["sayilar"]
    if not isinstance(sayilar_ham, dict) or set(sayilar_ham) != set(SAYI_ANAHTARLARI):
        raise _kh(slug, f"sayilar alanlari {', '.join(SAYI_ANAHTARLARI)} olmali")
    return LugatKaynakKilidi(
        kaynak=slug,
        url=url,
        kayit_surumu=kayit_surumu,
        alinma_tarihi=tarih,
        dosya=bicim.dosya,
        boyut=_tam(slug, veri["boyut"], "boyut"),
        sha256=_ozet(slug, veri["sha256"], "sha256"),
        bagimli_sha256=None if bagimli is None else _ozet(slug, bagimli, "bagimli_sha256"),
        sayilar={a: _tam(slug, sayilar_ham[a], f"sayilar.{a}") for a in SAYI_ANAHTARLARI},
    )


def kilit_yukle(slug: str, yol: Path | None = None) -> LugatKaynakKilidi:
    if slug not in BICIMLER:
        raise GirdiHatasi("lugat kaynagi bilinmiyor")
    try:
        ham = (yol if yol is not None else KILIT_YOLLARI[slug]).read_bytes()
    except OSError:
        raise _kh(slug, "okunamadi") from None
    return kilit_coz(slug, ham)


def kilit_metni(kilit: LugatKaynakKilidi) -> str:
    return json.dumps(kilit.sozluk(), ensure_ascii=True, indent=1, sort_keys=True) + "\n"


def kilit_denetle(kilit: LugatKaynakKilidi, veri: bytes, sayilar: Mapping[str, int]) -> None:
    """Dosya boyutu, SHA-256'si ve sayilar kilitle tutmalidir; aksi halde `GirdiHatasi`."""
    ozet = lineage.sha256_bayt(veri)
    if ozet != kilit.sha256 or len(veri) != kilit.boyut:
        raise GirdiHatasi(
            f"{kilit.kaynak}: dosya ozeti kilitle tutmuyor (beklenen {kisa_ozet(kilit.sha256)},"
            f" bulunan {kisa_ozet(ozet)}; boyut {kilit.boyut}/{len(veri)}). {UYARI}"
        )
    fark = sorted(a for a in SAYI_ANAHTARLARI if sayilar[a] != kilit.sayilar[a])
    if fark:
        raise GirdiHatasi(f"{kilit.kaynak}: sayilar kilitle tutmuyor ({', '.join(fark)}). {UYARI}")


# --- gelen klasoru ---------------------------------------------------------------------------


def gelen_oku(veri_kok: Path, slug: str, istenen: str | None) -> tuple[str, bytes]:
    """`gelen/<kaynak>/<tarih>/<dosya>` baytlari: `(tarih, bayt)`; yoksa ya da cok buyukse hata."""
    bicim = BICIMLER[slug]
    gelen = gelen_dizini(veri_kok, slug)
    tarih = gelen_tarihi_coz(gelen, istenen, slug)
    yol = gelen / tarih / bicim.dosya
    goreli = f"gelen/{slug}/{tarih}/{bicim.dosya}"
    try:
        if not yol.is_file():
            raise GirdiHatasi(f"{goreli} yok (--gelen-tarih ile baska bir klasor verilebilir)")
        if yol.stat().st_size > EN_BUYUK_BAYT:
            raise GirdiHatasi(f"{goreli} cok buyuk (sinir {EN_BUYUK_BAYT} bayt)")
        return tarih, yol.read_bytes()
    except OSError:
        raise GirdiHatasi(f"{goreli} okunamadi") from None


def risale_staged_yukle(ctx: RunContext) -> tuple[list[Satir], lineage.Girdi]:
    """En son Kelime-Frekans ingest'inin `lugat.jsonl` satirlari ve manifest girdisi.

    Dosya manifestteki ozetle dogrulanir. Satirlar YALNIZ okunur; Kelime-Frekans staged ciktisi
    ve satirlari degismez.
    """
    calisma = zincir.son_calisma(
        ctx,
        kelime_frekans.KAYNAK,
        INGEST_ADIMI,
        ipucu=f"once: ingest lugat --source {kelime_frekans.KAYNAK}",
    )
    zincir.saglam_olmali(ctx, calisma)
    satirlar = zincir.dosya_oku(calisma, LUGAT_ADI, f"{kelime_frekans.KAYNAK} {LUGAT_ADI}")
    return satirlar, zincir.girdi_olarak(calisma, LUGAT_ADI)


# --- kilit onerisi ---------------------------------------------------------------------------


def kilit_hazirla(
    slug: str, veri: bytes, rnk_veri: bytes | None, tarih: str, url: str, kayit_surumu: str
) -> LugatKaynakKilidi:
    bicim = BICIMLER[slug]
    ayr = ayristir(veri, bicim)
    rnk = None
    if bicim.rnk_bagimli:
        if rnk_veri is None:
            raise GirdiHatasi(f"{slug}: RNK lugat dosyasi gerekli")
        rnk = rnk_anahtarlari(ayristir(rnk_veri, BICIMLER[KAYNAK_RNK]))
    secilen = sec(bicim, ayr, rnk)
    return LugatKaynakKilidi(
        kaynak=slug,
        url=url,
        kayit_surumu=kayit_surumu,
        alinma_tarihi=tarih,
        dosya=bicim.dosya,
        boyut=len(veri),
        sha256=lineage.sha256_bayt(veri),
        bagimli_sha256=None
        if rnk_veri is None or not bicim.rnk_bagimli
        else lineage.sha256_bayt(rnk_veri),
        sayilar=sayilari_hesapla(ayr, secilen),
    )


def kilit_oner_metni(veri_kok: Path, depo_kok: Path, slug: str, gelen_tarih: str | None) -> str:
    """`--kilit-oner`: gelen dosyalardan hesaplanan kilit (JSON); adres ve surum kayittan."""
    if slug not in BICIMLER:
        raise GirdiHatasi("lugat kaynagi bilinmiyor")
    kayitlar = {s.dosya.removesuffix(".toml"): s for s in sources.yukle(depo_kok)}
    kayit = kayitlar.get(slug)
    if kayit is None or kayit.kaynak is None:
        raise GirdiHatasi(f"{slug}: kaynak kaydi yok ya da gecersiz")
    url, surum = kayit.kaynak.kaynak_url, kayit.kaynak.surum
    if url is None or surum is None:
        raise GirdiHatasi(f"{slug}: kaynak kaydinda kaynak_url ve surum olmali")
    tarih, veri = gelen_oku(veri_kok, slug, gelen_tarih)
    rnk_veri = (
        gelen_oku(veri_kok, KAYNAK_RNK, gelen_tarih)[1] if BICIMLER[slug].rnk_bagimli else None
    )
    return kilit_metni(kilit_hazirla(slug, veri, rnk_veri, tarih, url, surum))


# --- calistirma ------------------------------------------------------------------------------


@dataclass(frozen=True)
class LugatSonucu:
    run_id: str
    atlandi: bool
    madde_sayisi: int
    klasor: Path | None
    onceki_run_id: str | None = None


def run_lugat_kaynak(
    ctx: RunContext,
    slug: str,
    gelen_tarih: str | None = None,
    kilit: LugatKaynakKilidi | None = None,
    rnk_kilit: LugatKaynakKilidi | None = None,
) -> LugatSonucu:
    """Kayitlar, kilit, ham kopya, ayristirma, esleme, parmak izi, staged, manifest."""
    if slug not in BICIMLER:
        raise GirdiHatasi("ingest lugat: bilinmeyen lugat kaynagi")
    bicim = BICIMLER[slug]
    gerekli = (slug, KAYNAK_RNK) if bicim.rnk_bagimli else (slug,)
    kayitlar = ctx.require_sources(gerekli)
    ctx.gunluk.yaz("INFO", "lugat_kaynak_basla", source_id=slug)
    kilit = kilit if kilit is not None else kilit_yukle(slug)
    tarih, veri = gelen_oku(ctx.veri_kok, slug, gelen_tarih)
    ayr = ayristir(veri, bicim)
    hamlar: dict[str, tuple[str, bytes]] = {slug: (tarih, veri)}
    rnk: frozenset[str] | None = None
    if bicim.rnk_bagimli:
        rnk_bicim = BICIMLER[KAYNAK_RNK]
        rnk_kilit = rnk_kilit if rnk_kilit is not None else kilit_yukle(KAYNAK_RNK)
        rnk_tarih, rnk_veri = gelen_oku(ctx.veri_kok, KAYNAK_RNK, gelen_tarih)
        rnk_ayr = ayristir(rnk_veri, rnk_bicim)
        kilit_denetle(rnk_kilit, rnk_veri, sayilari_hesapla(rnk_ayr, sec(rnk_bicim, rnk_ayr, None)))
        if kilit.bagimli_sha256 != rnk_kilit.sha256:
            raise GirdiHatasi(f"{slug}: kilitteki RNK ozeti RNK kilidiyle tutmuyor. {UYARI}")
        rnk = rnk_anahtarlari(rnk_ayr)
        hamlar[KAYNAK_RNK] = (rnk_tarih, rnk_veri)
    secilen = sec(bicim, ayr, rnk)
    sayilar = sayilari_hesapla(ayr, secilen)
    kilit_denetle(kilit, veri, sayilar)  # tutmazsa raw'a hicbir sey yazilmaz

    yollar: dict[str, Path] = {}
    girdiler: list[lineage.Girdi] = []
    for ad, (ham_tarih, ham_veri) in hamlar.items():
        ham_bicim = BICIMLER[ad]
        fetch: dict[str, object] = {
            "kaynak": ad,
            "alinma_tarihi": ham_tarih,
            "url": kayitlar[ad].kaynak_url,
            "dosya": {
                "ad": ham_bicim.dosya,
                "boyut": len(ham_veri),
                "sha256": lineage.sha256_bayt(ham_veri),
            },
            "gelen_yol": f"gelen/{ad}/{ham_tarih}",
        }
        kopya, _ = ham_kopyala(ctx, ad, ham_tarih, {ham_bicim.dosya: ham_veri}, fetch)
        yollar[ad] = kopya[ham_bicim.dosya]
        girdiler.append(
            lineage.Girdi(
                yol=lineage.goreli_yol(ctx.veri_kok, yollar[ad]),
                sha256=lineage.sha256_bayt(ham_veri),
            )
        )
    risale_satirlari, risale_girdi = risale_staged_yukle(ctx)
    girdiler.append(risale_girdi)
    parmak = ctx.parmak_izi(girdiler)

    onceki = lineage.son_basarili(ctx.staged_kaynak_dizini(slug), ctx.adim)
    if lineage.atlanabilir(
        onceki=onceki[2] if onceki else None,
        parmak=parmak,
        git_kirli=ctx.git().kirli,
        force=ctx.force,
        veri_kok=ctx.veri_kok,
    ):
        ctx.gunluk.yaz("INFO", "lugat_kaynak_atlandi", source_id=slug)
        ctx.sayi("atlandi", 1)
        return LugatSonucu(ctx.run_id, True, 0, None, onceki[0] if onceki else None)

    dizin = risale_dizini(s.veri for s in risale_satirlari)
    satirlar = lugat_satirlari(slug, secilen, dizin, veri_surumu(slug, kilit.sha256))
    duzeyler = Counter(int(str(s["duzey"])) for s in satirlar)
    sonuc_sayilar = {
        "satir": sayilar["satir"],
        "madde": len(satirlar),
        "benzersiz_baslik": sayilar["alinan_ham_baslik"],
        "cok_anlamli_baslik": sayilar["cok_anlamli_baslik"],
        "bozuk": sayilar["satir"] - sayilar["gecerli_madde"],
        "eslesen_madde": sum(1 for s in satirlar if int(str(s["duzey"])) != DUZEY_RISALEDE_YOK),
        "risale_anahtari": len(dizin),
        "i_sapkali_baslik": sayilar["i_sapkali_baslik"],
        **{f"duzey_{d}": n for d, n in sorted(duzeyler.items())},
    }
    for ad, deger in sonuc_sayilar.items():
        ctx.sayi(ad, deger)
    if ctx.dry_run:
        ctx.gunluk.yaz("INFO", "lugat_kaynak_dry_run", source_id=slug, sayilar=sonuc_sayilar)
        return LugatSonucu(ctx.run_id, False, len(satirlar), None)
    klasor = ctx.staged_dizin(slug)
    klasor.mkdir(parents=True, exist_ok=True)
    cikti = dosya_yaz(ctx, slug, LUGAT_ADI, satirlar, MADDE_ANAHTARI_KAYNAK)
    ctx.manifest_yaz(
        klasor,
        girdiler=girdiler,
        ciktilar=[cikti],
        parmak=parmak,
        ayrintilar={
            "gelen_tarih": tarih,
            "kilit": {"sha256": kilit.sha256, "boyut": kilit.boyut},
            "cikarici": bicim.cikarici,
            "risale_run_id": risale_girdi.ust_run_id,
            "sayilar": sonuc_sayilar,
        },
    )
    ctx.gunluk.yaz("INFO", "lugat_kaynak_bitti", source_id=slug, sayilar=sonuc_sayilar)
    return LugatSonucu(ctx.run_id, False, len(satirlar), klasor)


def komut_ingest_lugat_kaynak(
    *,
    source: str,
    gelen_tarih: str | None,
    dry_run: bool,
    force: bool,
    config: Path | None,
    kok: Path | None,
) -> int:
    """`ingest lugat --source lugat-rnk|lugat-sozluk-rganeyev` komutu; cikis kodunu dondurur."""

    def govde(ctx: RunContext) -> int:
        sonuc = run_lugat_kaynak(ctx, source, gelen_tarih)
        if sonuc.atlandi:
            ozet = f"atlandi (parmak izi onceki calistirmayla ayni, run {sonuc.onceki_run_id})"
        elif ctx.dry_run:
            ozet = f"{sonuc.madde_sayisi} madde (dry-run, hicbir sey yazilmadi)"
        else:
            ozet = f"{sonuc.madde_sayisi} madde, run {sonuc.run_id}"
        sys.stdout.write(f"ingest {source}: {ozet}\n")
        return cikis.BASARILI

    return komutu_yurut(
        komut=f"ingest lugat --source {source}",
        adim=INGEST_ADIMI,
        kaynaklar=[source, KAYNAK_RNK] if BICIMLER[source].rnk_bagimli else [source],
        config=config,
        kok=kok,
        govde=govde,
        force=force,
        dry_run=dry_run,
        parametreler={"source": source},
    )
