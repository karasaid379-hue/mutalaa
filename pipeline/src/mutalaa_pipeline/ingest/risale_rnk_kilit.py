"""RNK kilidi (`risale_rnk.lock.json`): bicim, uretim ve okuma (A20.1b, K-51 madde 5 ve 7).

Kilit kitap basina dosyalarin sabit kimligini ve yalnizca SAYILARI tutar (metin yok):

* MD5 (RNK katalogunun `hash_txt` ve `hash_json` degerleriyle eslesir), SHA-256, bayt boyutu;
* satir sayisi, BOM, CR'li satir sayisi, son satirda CR, dosyanin LF ile bitmesi;
* `#n` sayisi, ilk ve son sayfa, baslik satiri (`<&€∑` ile baslayip `>` ile biten) sayisi;
* her isaret karakterinin sayisi (`isaretler`; virgul icin satir basi sayisi);
* denetlenen karakterlerin sayisi (`karakterler`: S12 kumesi ve kontrol, bicim, bosluk, ozel
  kullanim siniflari; K-51 madde 5) ve ozel kullanim karakterlerinin tek tek yeri;
* NFC olmayan satir sayisi (bilgi; NFC uygulanmaz).

Kilit yalniz `/karar` ile degisir: gelen dosya kilitle tutmazsa `ingest` 2 ile durur. `kilit_uret`
gelen klasorunden onerilen kilidi hesaplar (dosya yazmaz); MD5 katalogla dogrulanir.
"""

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from mutalaa_pipeline import lineage
from mutalaa_pipeline.export.ortak import GirdiHatasi, kati_json
from mutalaa_pipeline.ingest.risale_rnk import (
    BASLIK_ACILISLARI,
    ISARET_SIRASI,
    SAYFA_DESENI,
    dosya_coz,
    isaret_sayilari,
    karakter_sayilari,
    kod_adi,
    nfc_olmayan_satir,
)
from mutalaa_pipeline.ingest.tanzil import tarih_gecerli

KILIT_YOLU: Final = Path(__file__).with_name("risale_rnk.lock.json")
KILIT_SURUMU: Final = 1
KAYNAK: Final = "risale-rnk-metin"
GELEN_KAYNAK: Final = "risale-baski-rnk"
KATALOG_ADI: Final = "shelves.json"
OZEL_KULLANIM: Final = range(0xE000, 0xF900)
UYARI: Final = "Yeni RNK dosyasi kilit guncellenerek (/karar) alinir."

SAYISAL_ALANLAR: Final = (
    "boyut_txt",
    "boyut_json",
    "satir_sayisi",
    "cr_satir",
    "nfc_olmayan_satir",
    "sayfa_sayisi",
    "ilk_sayfa",
    "son_sayfa",
    "baslik_satiri",
)
MANTIKSAL_ALANLAR: Final = ("bom", "cr_son", "son_lf")
OZET_ALANLARI: Final = ("md5_txt", "md5_json", "sha256_txt", "sha256_json")


@dataclass(frozen=True)
class KitapKilidi:
    ad: str  # "raf/uid"
    veri: dict[str, object]

    @property
    def raf(self) -> str:
        return self.ad.split("/")[0]

    @property
    def uid(self) -> str:
        return self.ad.split("/")[1]

    def sayi(self, alan: str) -> int:
        deger = self.veri.get(alan)
        if isinstance(deger, bool) or not isinstance(deger, int):
            raise GirdiHatasi(f"kilit {self.ad}: {alan} tam sayi degil")
        return deger

    def metin(self, alan: str) -> str:
        deger = self.veri.get(alan)
        if not isinstance(deger, str):
            raise GirdiHatasi(f"kilit {self.ad}: {alan} metin degil")
        return deger

    def mantiksal(self, alan: str) -> bool:
        deger = self.veri.get(alan)
        if not isinstance(deger, bool):
            raise GirdiHatasi(f"kilit {self.ad}: {alan} mantiksal degil")
        return deger

    def sayilar(self, alan: str) -> dict[str, int]:
        deger = self.veri.get(alan)
        if not isinstance(deger, dict):
            raise GirdiHatasi(f"kilit {self.ad}: {alan} nesne degil")
        sonuc: dict[str, int] = {}
        for anahtar, sayi in deger.items():
            if isinstance(sayi, bool) or not isinstance(sayi, int):
                raise GirdiHatasi(f"kilit {self.ad}: {alan} sayisi tam sayi degil")
            sonuc[anahtar] = sayi
        return sonuc

    def ozel_kullanim(self) -> list[tuple[int, str]]:
        deger = self.veri.get("ozel_kullanim")
        if not isinstance(deger, list):
            raise GirdiHatasi(f"kilit {self.ad}: ozel_kullanim liste degil")
        sonuc: list[tuple[int, str]] = []
        for oge in deger:
            if not isinstance(oge, dict):
                raise GirdiHatasi(f"kilit {self.ad}: ozel_kullanim ogesi nesne degil")
            satir, kod = oge.get("satir"), oge.get("kod")
            if not isinstance(satir, int) or not isinstance(kod, str):
                raise GirdiHatasi(f"kilit {self.ad}: ozel_kullanim ogesi gecersiz")
            sonuc.append((satir, kod))
        return sonuc


@dataclass(frozen=True)
class RnkKilidi:
    gelen_tarih: str
    katalog_boyut: int
    katalog_sha256: str
    kitaplar: dict[str, KitapKilidi]

    def sozluk(self) -> dict[str, object]:
        return {
            "surum": KILIT_SURUMU,
            "kaynak": KAYNAK,
            "gelen_kaynak": GELEN_KAYNAK,
            "gelen_tarih": self.gelen_tarih,
            "katalog": {
                "ad": KATALOG_ADI,
                "boyut": self.katalog_boyut,
                "sha256": self.katalog_sha256,
            },
            "kitaplar": {ad: k.veri for ad, k in sorted(self.kitaplar.items())},
        }


def kilit_metni(kilit: RnkKilidi) -> str:
    """Kilit dosyasinin kanonik metni (alan sirasi sabit, ASCII, LF)."""
    return json.dumps(kilit.sozluk(), ensure_ascii=True, indent=2) + "\n"


def kilit_ozeti(kilit: RnkKilidi) -> str:
    """Kilidin kanonik JSON'unun SHA-256'si (ingest manifestine yazilir)."""
    govde = json.dumps(kilit.sozluk(), ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return lineage.sha256_bayt(govde.encode("utf-8"))


def kilit_coz(ham: bytes) -> RnkKilidi:
    try:
        belge = kati_json(ham.decode("utf-8"))
    except UnicodeDecodeError:
        raise GirdiHatasi("risale_rnk.lock.json: UTF-8 degil") from None
    if not isinstance(belge, dict) or belge.get("surum") != KILIT_SURUMU:
        raise GirdiHatasi("risale_rnk.lock.json: surum gecersiz")
    katalog = belge.get("katalog")
    kitaplar = belge.get("kitaplar")
    tarih = belge.get("gelen_tarih")
    if (
        not isinstance(katalog, dict)
        or not isinstance(kitaplar, dict)
        or not isinstance(tarih, str)
    ):
        raise GirdiHatasi("risale_rnk.lock.json: katalog, kitaplar ve gelen_tarih bekleniyor")
    if not tarih_gecerli(tarih):  # tarih `data/gelen` ve `data/raw` yoluna eklenir
        raise GirdiHatasi("risale_rnk.lock.json: gelen_tarih YYYY-AA-GG biciminde gecerli degil")
    boyut, sha = katalog.get("boyut"), katalog.get("sha256")
    if not isinstance(boyut, int) or not isinstance(sha, str):
        raise GirdiHatasi("risale_rnk.lock.json: katalog boyut ve sha256 bekleniyor")
    sonuc: dict[str, KitapKilidi] = {}
    for ad, veri in kitaplar.items():
        if not isinstance(veri, dict) or ad.count("/") != 1:
            raise GirdiHatasi("risale_rnk.lock.json: kitap kaydi gecersiz")
        k = KitapKilidi(ad, veri)
        for alan in SAYISAL_ALANLAR:
            k.sayi(alan)
        for alan in MANTIKSAL_ALANLAR:
            k.mantiksal(alan)
        for alan in OZET_ALANLARI:
            k.metin(alan)
        k.sayilar("isaretler")
        k.sayilar("karakterler")
        k.ozel_kullanim()
        sonuc[ad] = k
    return RnkKilidi(tarih, boyut, sha, sonuc)


def kilit_yukle(yol: Path | None = None) -> RnkKilidi:
    hedef = yol if yol is not None else KILIT_YOLU
    try:
        ham = hedef.read_bytes()
    except OSError:
        raise GirdiHatasi("risale_rnk.lock.json okunamadi") from None
    return kilit_coz(ham)


# ---------------------------------------------------------------------------
# Uretim


def baslik_satiri_sayisi(satirlar: list[str]) -> int:
    return sum(1 for s in satirlar if s[:1] in BASLIK_ACILISLARI and s.endswith(">"))


def kitap_istatistigi(txt: bytes, json_veri: bytes) -> dict[str, object]:
    """Bir RNK dosyasinin kilit alanlari (MD5 hariç: katalogla ayrica dogrulanir)."""
    satirlar, bom, cr, son_lf = dosya_coz(txt)
    govde = "\n".join(satirlar)
    sayfalar = [int(s[1:]) for s in satirlar if SAYFA_DESENI.fullmatch(s)]
    ozel: list[dict[str, object]] = []
    for no, satir in enumerate(satirlar, start=1):
        for ch in satir:
            if ord(ch) in OZEL_KULLANIM:
                ozel.append({"satir": no, "kod": kod_adi(ord(ch))})
    return {
        "md5_txt": hashlib.md5(txt, usedforsecurity=False).hexdigest(),
        "md5_json": hashlib.md5(json_veri, usedforsecurity=False).hexdigest(),
        "sha256_txt": lineage.sha256_bayt(txt),
        "sha256_json": lineage.sha256_bayt(json_veri),
        "boyut_txt": len(txt),
        "boyut_json": len(json_veri),
        "satir_sayisi": len(satirlar),
        "bom": bom,
        "cr_satir": sum(cr),
        "cr_son": bool(cr) and cr[-1],
        "son_lf": son_lf,
        "nfc_olmayan_satir": nfc_olmayan_satir(satirlar),
        "sayfa_sayisi": len(sayfalar),
        "ilk_sayfa": sayfalar[0] if sayfalar else 0,
        "son_sayfa": sayfalar[-1] if sayfalar else 0,
        "baslik_satiri": baslik_satiri_sayisi(satirlar),
        "isaretler": isaret_sayilari(govde),
        "karakterler": karakter_sayilari(govde),
        "ozel_kullanim": ozel,
    }


def katalog_hashleri(veri: bytes) -> dict[tuple[str, str], tuple[str, str]]:
    """`shelves.json` -> `(raf, uid) -> (hash_txt, hash_json)`."""
    try:
        belge = kati_json(veri.decode("utf-8"))
    except UnicodeDecodeError:
        raise GirdiHatasi("shelves.json: UTF-8 degil") from None
    if not isinstance(belge, dict) or not isinstance(belge.get("shelves"), list):
        raise GirdiHatasi("shelves.json: shelves listesi yok")
    sonuc: dict[tuple[str, str], tuple[str, str]] = {}
    for raf in belge["shelves"]:
        if not isinstance(raf, dict) or not isinstance(raf.get("books"), list):
            continue
        for kitap in raf["books"]:
            if (
                isinstance(kitap, dict)
                and isinstance(raf.get("id"), str)
                and isinstance(kitap.get("uid"), str)
                and isinstance(kitap.get("hash_txt"), str)
                and isinstance(kitap.get("hash_json"), str)
            ):
                sonuc[(raf["id"], kitap["uid"])] = (kitap["hash_txt"], kitap["hash_json"])
    return sonuc


def kilit_uret(
    *,
    gelen: Path,
    tarih: str,
    dosyalar: list[tuple[str, str]],
) -> RnkKilidi:
    """`gelen` klasorunden (`<tarih>` altinda) onerilen kilit; MD5 katalogla dogrulanir.

    `dosyalar`: `(raf, uid)` listesi. Katalog `shelves.json` ayni klasordedir. Dosya
    okunamazsa ya da MD5 katalogla tutmazsa `GirdiHatasi`.
    """
    kok = gelen / tarih
    try:
        katalog = (kok / KATALOG_ADI).read_bytes()
    except OSError:
        raise GirdiHatasi(f"{KATALOG_ADI} okunamadi") from None
    hashler = katalog_hashleri(katalog)
    kitaplar: dict[str, KitapKilidi] = {}
    for raf, uid in sorted(dosyalar):
        try:
            txt = (kok / raf / f"{uid}.txt").read_bytes()
            json_veri = (kok / raf / f"{uid}.json").read_bytes()
        except OSError:
            raise GirdiHatasi(f"{raf}/{uid}: dosya okunamadi") from None
        veri = kitap_istatistigi(txt, json_veri)
        beklenen = hashler.get((raf, uid))
        if beklenen is None:
            raise GirdiHatasi(f"{raf}/{uid}: katalogda yok")
        if beklenen != (veri["md5_txt"], veri["md5_json"]):
            raise GirdiHatasi(f"{raf}/{uid}: MD5 katalogla tutmuyor")
        kitaplar[f"{raf}/{uid}"] = KitapKilidi(f"{raf}/{uid}", veri)
    return RnkKilidi(tarih, len(katalog), lineage.sha256_bayt(katalog), kitaplar)


__all__ = [
    "ISARET_SIRASI",
    "KILIT_YOLU",
    "KitapKilidi",
    "RnkKilidi",
    "kilit_coz",
    "kilit_metni",
    "kilit_ozeti",
    "kilit_uret",
    "kilit_yukle",
]
