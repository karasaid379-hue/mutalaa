"""Meal kilidi (`elmalili_meal.lock.json`): bicim, okuma ve ozet (A16.2, K-49 madde 11).

Kilit uc kaynak icin alinan dosyalarin sabit kimligini tutar; `tanzil.lock.json` ve
`sure_adlari.lock.json` ile ayni kalip: kati okuma (BOM, CR, yinelenen anahtar, ondalik sayi yok),
ASCII kacisli yazim, alan sirasi sabit. Kilit yalniz `/karar` ile degisir: gelen dosya kilitle
tutmazsa komut 2 ile durur, kilit kendiliginden guncellenmez.

* `vikikaynak`: API yanitlari (`dosyalar`: 3 JSON yaniti ve `basliklar.tsv`; boyut ve SHA-256) ve
  114 sayfanin her biri icin `baslik`, `sure` (ACIK eslesme: baslik calisma aninda ayristirilmaz),
  `revid`, `sha1` (MediaWiki'nin verdigi revizyon ozeti) ve `wikitext_sha256` (wikitext'in UTF-8
  baytlarinin ozeti).
* `sade`: fawazahmed0 dosyasi (`url`, `commit`, `dosya`).
* `tanik_epub`: archive.org EPUB'i (`oge`, `uzak_dosya`, `url`, `sha1`, `dosya`).

`kilit_ozeti` bir bolumun kanonik JSON'unun SHA-256'sidir; ingest manifestine yazilir ve G-CAP
`content_hash` degisimini "kilit degisti" diye aciklayabilsin diye kullanilir.
"""

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from mutalaa_pipeline.export.ortak import GirdiHatasi, kati_json
from mutalaa_pipeline.ingest.meal_kaynaklari import BOLUM_EPUB, BOLUM_SADE, BOLUM_VIKIKAYNAK
from mutalaa_pipeline.ingest.tanzil import TARIH_DESENI, tarih_gecerli
from mutalaa_pipeline.lineage import OZET_DESENI

KILIT_YOLU: Final = Path(__file__).with_name("elmalili_meal.lock.json")
UYARI: Final = "Yeni meal kaynagi kilit guncellenerek (/karar) alinir."
SURE_SAYISI: Final = 114
SHA1_DESENI: Final = re.compile(r"[0-9a-f]{40}")
COMMIT_DESENI: Final = SHA1_DESENI
DOSYA_ADI_DESENI: Final = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")
OGE_DESENI: Final = re.compile(r"[a-z0-9][a-z0-9._-]{0,127}")
VIKIKAYNAK_URL: Final = "https://tr.wikisource.org/w/api.php"
SADE_URL: Final = (
    "https://raw.githubusercontent.com/fawazahmed0/quran-api/{commit}/editions/"
    "tur-elmallsadelesti.json"
)
EPUB_OGE: Final = "elmalili-hamdi-yazir-meal-i-serif"
EPUB_URL: Final = "https://archive.org/download/{oge}/{dosya}"
LISTE_DOSYASI: Final = "basliklar.tsv"
YANIT_DESENI: Final = re.compile(r"vikikaynak-[0-9]{2}\.json")


@dataclass(frozen=True)
class DosyaKilidi:
    ad: str
    boyut: int
    sha256: str

    def sozluk(self) -> dict[str, object]:
        return {"ad": self.ad, "boyut": self.boyut, "sha256": self.sha256}


@dataclass(frozen=True)
class SayfaKilidi:
    baslik: str
    sure: int
    revid: int
    sha1: str
    wikitext_sha256: str

    def sozluk(self) -> dict[str, object]:
        return {
            "baslik": self.baslik,
            "sure": self.sure,
            "revid": self.revid,
            "sha1": self.sha1,
            "wikitext_sha256": self.wikitext_sha256,
        }


@dataclass(frozen=True)
class VikikaynakKilidi:
    url: str
    alinma_tarihi: str
    liste_sha256: str
    dosyalar: tuple[DosyaKilidi, ...]
    sayfalar: tuple[SayfaKilidi, ...]

    def sozluk(self) -> dict[str, object]:
        return {
            "url": self.url,
            "alinma_tarihi": self.alinma_tarihi,
            "liste_sha256": self.liste_sha256,
            "dosyalar": [d.sozluk() for d in self.dosyalar],
            "sayfalar": [s.sozluk() for s in self.sayfalar],
        }

    def dosya(self, ad: str) -> DosyaKilidi:
        for d in self.dosyalar:
            if d.ad == ad:
                return d
        raise GirdiHatasi("kilitte beklenen dosya yok")

    @property
    def yanit_dosyalari(self) -> tuple[DosyaKilidi, ...]:
        return tuple(d for d in self.dosyalar if YANIT_DESENI.fullmatch(d.ad))


@dataclass(frozen=True)
class SadeKilidi:
    url: str
    commit: str
    alinma_tarihi: str
    dosya: DosyaKilidi

    def sozluk(self) -> dict[str, object]:
        return {
            "url": self.url,
            "commit": self.commit,
            "alinma_tarihi": self.alinma_tarihi,
            "dosya": self.dosya.sozluk(),
        }


@dataclass(frozen=True)
class EpubKilidi:
    oge: str
    uzak_dosya: str
    url: str
    alinma_tarihi: str
    sha1: str
    dosya: DosyaKilidi

    def sozluk(self) -> dict[str, object]:
        return {
            "oge": self.oge,
            "uzak_dosya": self.uzak_dosya,
            "url": self.url,
            "alinma_tarihi": self.alinma_tarihi,
            "sha1": self.sha1,
            "dosya": self.dosya.sozluk(),
        }


@dataclass(frozen=True)
class MealKilidi:
    vikikaynak: VikikaynakKilidi
    sade: SadeKilidi
    tanik_epub: EpubKilidi

    def sozluk(self) -> dict[str, object]:
        return {
            BOLUM_VIKIKAYNAK: self.vikikaynak.sozluk(),
            BOLUM_SADE: self.sade.sozluk(),
            BOLUM_EPUB: self.tanik_epub.sozluk(),
        }

    def bolum_sozlugu(self, bolum: str) -> dict[str, object]:
        govde = self.sozluk()
        deger = govde.get(bolum)
        if not isinstance(deger, dict):
            raise GirdiHatasi("kilit bolumu yok")
        return deger


def kilit_ozeti(bolum: dict[str, object]) -> str:
    """Bir kilit bolumunun kanonik JSON'unun SHA-256'si."""
    veri = json.dumps(bolum, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(veri.encode("utf-8")).hexdigest()


# --- okuma ---------------------------------------------------------------------------------


def _alanlar(nesne: object, ad: str, alanlar: tuple[str, ...]) -> dict[str, object]:
    yer = f"elmalili_meal.lock.json {ad}"
    if not isinstance(nesne, dict) or set(nesne) != set(alanlar):
        raise GirdiHatasi(f"{yer}: alanlar {', '.join(alanlar)} olmali")
    return nesne


def _https(deger: object, yer: str) -> str:
    if not isinstance(deger, str) or not deger.startswith("https://"):
        raise GirdiHatasi(f"{yer}: url https:// ile baslayan metin olmali")
    return deger


def _tarih(deger: object, yer: str) -> str:
    if not isinstance(deger, str) or not tarih_gecerli(deger) or not TARIH_DESENI.fullmatch(deger):
        raise GirdiHatasi(f"{yer}: alinma_tarihi YYYY-AA-GG olmali")
    return deger


def _ozet(deger: object, desen: re.Pattern[str], yer: str, alan: str) -> str:
    if not isinstance(deger, str) or desen.fullmatch(deger) is None:
        raise GirdiHatasi(f"{yer}: {alan} kucuk harfli onaltilik olmali")
    return deger


def _tam_sayi(deger: object, yer: str, alan: str) -> int:
    if type(deger) is not int or deger <= 0:
        raise GirdiHatasi(f"{yer}: {alan} pozitif tam sayi olmali")
    return deger


def _dosya(nesne: object, yer: str) -> DosyaKilidi:
    alanlar = _alanlar(nesne, f"{yer} dosya", ("ad", "boyut", "sha256"))
    ad = alanlar["ad"]
    if not isinstance(ad, str) or DOSYA_ADI_DESENI.fullmatch(ad) is None:
        raise GirdiHatasi(f"{yer}: dosya adi ASCII ve guvenli olmali")
    return DosyaKilidi(
        ad,
        _tam_sayi(alanlar["boyut"], yer, "boyut"),
        _ozet(alanlar["sha256"], OZET_DESENI, yer, "sha256"),
    )


def _vikikaynak(nesne: object) -> VikikaynakKilidi:
    yer = "elmalili_meal.lock.json vikikaynak"
    alanlar = _alanlar(
        nesne, "vikikaynak", ("url", "alinma_tarihi", "liste_sha256", "dosyalar", "sayfalar")
    )
    dosyalar_ham, sayfalar_ham = alanlar["dosyalar"], alanlar["sayfalar"]
    if not isinstance(dosyalar_ham, list) or not isinstance(sayfalar_ham, list):
        raise GirdiHatasi(f"{yer}: dosyalar ve sayfalar liste olmali")
    dosyalar = tuple(_dosya(d, yer) for d in dosyalar_ham)
    adlar = [d.ad for d in dosyalar]
    if len(set(adlar)) != len(adlar) or LISTE_DOSYASI not in adlar:
        raise GirdiHatasi(f"{yer}: dosya adlari tekil olmali ve {LISTE_DOSYASI} bulunmali")
    if not any(YANIT_DESENI.fullmatch(a) for a in adlar) or any(
        a != LISTE_DOSYASI and YANIT_DESENI.fullmatch(a) is None for a in adlar
    ):
        raise GirdiHatasi(f"{yer}: dosya adlari vikikaynak-NN.json ve {LISTE_DOSYASI} olmali")
    sayfalar: list[SayfaKilidi] = []
    for sira, ham in enumerate(sayfalar_ham, start=1):
        sayfa_yeri = f"{yer} sayfa {sira}"
        s = _alanlar(ham, f"sayfa {sira}", ("baslik", "sure", "revid", "sha1", "wikitext_sha256"))
        baslik = s["baslik"]
        if not isinstance(baslik, str) or baslik == "" or len(baslik) > 128:
            raise GirdiHatasi(f"{sayfa_yeri}: baslik bos ya da cok uzun")
        sure = s["sure"]
        if type(sure) is not int or not 1 <= sure <= SURE_SAYISI:
            raise GirdiHatasi(f"{sayfa_yeri}: sure 1..114 olmali")
        sayfalar.append(
            SayfaKilidi(
                baslik,
                sure,
                _tam_sayi(s["revid"], sayfa_yeri, "revid"),
                _ozet(s["sha1"], SHA1_DESENI, sayfa_yeri, "sha1"),
                _ozet(s["wikitext_sha256"], OZET_DESENI, sayfa_yeri, "wikitext_sha256"),
            )
        )
    if (
        len(sayfalar) != SURE_SAYISI
        or sorted(s.sure for s in sayfalar) != list(range(1, SURE_SAYISI + 1))
        or len({s.baslik for s in sayfalar}) != SURE_SAYISI
        or len({s.revid for s in sayfalar}) != SURE_SAYISI
    ):
        raise GirdiHatasi(f"{yer}: 114 sayfa, her sure bir kez, baslik ve revid tekil olmali")
    return VikikaynakKilidi(
        _https(alanlar["url"], yer),
        _tarih(alanlar["alinma_tarihi"], yer),
        _ozet(alanlar["liste_sha256"], OZET_DESENI, yer, "liste_sha256"),
        tuple(sorted(dosyalar, key=lambda d: d.ad)),
        tuple(sorted(sayfalar, key=lambda s: s.sure)),
    )


def _sade(nesne: object) -> SadeKilidi:
    yer = "elmalili_meal.lock.json sade"
    a = _alanlar(nesne, "sade", ("url", "commit", "alinma_tarihi", "dosya"))
    return SadeKilidi(
        _https(a["url"], yer),
        _ozet(a["commit"], COMMIT_DESENI, yer, "commit"),
        _tarih(a["alinma_tarihi"], yer),
        _dosya(a["dosya"], yer),
    )


def _epub(nesne: object) -> EpubKilidi:
    yer = "elmalili_meal.lock.json tanik_epub"
    a = _alanlar(
        nesne, "tanik_epub", ("oge", "uzak_dosya", "url", "alinma_tarihi", "sha1", "dosya")
    )
    oge, uzak = a["oge"], a["uzak_dosya"]
    if not isinstance(oge, str) or OGE_DESENI.fullmatch(oge) is None:
        raise GirdiHatasi(f"{yer}: oge kimligi gecersiz")
    if not isinstance(uzak, str) or DOSYA_ADI_DESENI.fullmatch(uzak) is None:
        raise GirdiHatasi(f"{yer}: uzak_dosya gecersiz")
    return EpubKilidi(
        oge,
        uzak,
        _https(a["url"], yer),
        _tarih(a["alinma_tarihi"], yer),
        _ozet(a["sha1"], SHA1_DESENI, yer, "sha1"),
        _dosya(a["dosya"], yer),
    )


def kilit_coz(ham: bytes) -> MealKilidi:
    """Kilit dosyasinin baytlarini kati bicimde cozer; bicim hatasi `GirdiHatasi`."""
    if ham.startswith(b"\xef\xbb\xbf") or b"\r" in ham:
        raise GirdiHatasi("elmalili_meal.lock.json: BOM ya da CR var (UTF-8 BOM'suz, LF olmali)")
    try:
        metin = ham.decode("utf-8")
    except UnicodeDecodeError:
        raise GirdiHatasi("elmalili_meal.lock.json: UTF-8 degil") from None
    try:
        veri = kati_json(metin)
    except GirdiHatasi as hata:
        raise GirdiHatasi(f"elmalili_meal.lock.json: {hata}") from None
    if not isinstance(veri, dict) or set(veri) != {BOLUM_VIKIKAYNAK, BOLUM_SADE, BOLUM_EPUB}:
        raise GirdiHatasi(
            f"elmalili_meal.lock.json: ust alanlar {BOLUM_VIKIKAYNAK}, {BOLUM_SADE},"
            f" {BOLUM_EPUB} olmali"
        )
    return MealKilidi(
        _vikikaynak(veri[BOLUM_VIKIKAYNAK]), _sade(veri[BOLUM_SADE]), _epub(veri[BOLUM_EPUB])
    )


def kilit_yukle(yol: Path | None = None) -> MealKilidi:
    """Paketteki kilit dosyasini okur (testler kendi yolunu verir)."""
    hedef = yol if yol is not None else KILIT_YOLU
    try:
        ham = hedef.read_bytes()
    except OSError:
        raise GirdiHatasi("elmalili_meal.lock.json okunamadi") from None
    return kilit_coz(ham)


def kilit_metni(kilit: MealKilidi) -> str:
    """Kilit dosyasinin kanonik metni (alan sirasi sabit, ASCII, LF)."""
    return json.dumps(kilit.sozluk(), ensure_ascii=True, indent=2) + "\n"
