# ruff: noqa: RUF001
"""`ingest meal --kilit-oner`: gelen dosyalardan kilit onerisi (A16.2); hicbir sey yazmaz.

Oneri, `elmalili_meal.lock.json` icindeki bir bolumun ilk degerleridir (JSON, kanonik yazim);
kilide elle (ve `/karar` ile) aktarilir. Her kaynak icin gelen dosya kati okunur ve bicimi
sinanir:

* `elmalili-meal`: API yanitlari sayfa sayfa okunur (baslik, `revid`, MediaWiki `sha1` ve
  wikitext'in hesaplanan SHA-1'i ile `size` tutmali); 114 sayfanin sure numarasi ACIK eslesme
  olarak onerilir: baslik A11 sure adi tablosundan (`staged/sure-adlari-vikipedi/*/tablo.jsonl`,
  103 baslik) ve tabloda farkli yazilan baslik icin ASCII katlanmis ad eslemesinden (`EK_ESLEME`)
  bulunur. Kilitte baslik calisma aninda ayristirilmaz; bu eslesme yalniz oneri aninda kullanilir.
  Her sayfanin ayet kumesi Tanzil sayisiyla birebir esit olmali (`sayfa_cikar`), aksi halde cikis 2.
* `elmalili-sade-meal`: dosya ozeti ve boyutu; commit kaynak kaydinin `surum` alanindan
  (`commit-<40 hane>`) okunur; JSON bicimi ve 6.236 ayet sinanir.
* `elmalili-meal-epub`: dosya ozeti, SHA-1 ve boyut; EPUB bicimi ve 114 sure basligi sinanir.

Iletiler yalniz sayi, sure no ve ozet tasir; metin asla.
"""

import hashlib
import json
import re
import unicodedata
from pathlib import Path
from typing import Final

from mutalaa_pipeline import lineage, sources
from mutalaa_pipeline.anchor.ayet_sayilari import AYET_SAYILARI
from mutalaa_pipeline.export.ortak import GirdiHatasi, kati_json
from mutalaa_pipeline.ingest import elmalili_epub, elmalili_sade, elmalili_vikikaynak, meal_kilit
from mutalaa_pipeline.ingest.elmalili_vikikaynak import sha1_hesapla, yol_al
from mutalaa_pipeline.ingest.meal_kaynaklari import (
    BOLUM_EPUB,
    BOLUM_SADE,
    BOLUM_VIKIKAYNAK,
    KAYNAK_EPUB,
    KAYNAK_ORIJINAL,
    KAYNAK_SADE,
)
from mutalaa_pipeline.ingest.meal_kilit import (
    EPUB_OGE,
    EPUB_URL,
    LISTE_DOSYASI,
    SADE_URL,
    VIKIKAYNAK_URL,
    YANIT_DESENI,
    DosyaKilidi,
    SayfaKilidi,
    VikikaynakKilidi,
)
from mutalaa_pipeline.ingest.meal_ortak import gelen_dizini, gelen_oku, gelen_tarihi_coz
from mutalaa_pipeline.normalize import lower_turkish

SURE_ADLARI_KAYNAGI: Final = "sure-adlari-vikipedi"
VIKIKAYNAK_ONEK: Final = "Kur'an/"
SURE_SUFFIX: Final = " Suresi"
EPUB_UZAK_DOSYA: Final = "Elmalili-Hamdi-Yazir-Meal-i-Serif.epub"
EPUB_YEREL_DOSYA: Final = "meal-i-serif.epub"
SADE_DOSYA: Final = "tur-elmallsadelesti.json"
COMMIT: Final = re.compile(r"commit-([0-9a-f]{40})")
KESMELER: Final = "’‘`´ʼ"
# Baslik karsilastirmasinda a/i/u uzerindeki sapka katlanir (Vikipedi ve Vikikaynak ayri yazabilir).
SAPKA_KATLAMA: Final = str.maketrans(
    {0xE2: "a", 0xEE: "i", 0xFB: "u", 0xC2: "a", 0xCE: "i", 0xDB: "u"}
)
# Vikipedi sure listesinde farkli yazilan 11 baslik: ASCII katlanmis ad -> sure no (A16.0 olcumu).
# Eslesmenin dogrulugu her sayfanin ayet kumesinin Tanzil sayisiyla birebir esitligiyle sinanir.
EK_ESLEME: Final[dict[str, int]] = {
    "cuma": 62,
    "buruc": 85,
    "maun": 107,
    "saf": 61,
    "tegabun": 64,
    "mearic": 70,
    "nebe": 78,
    "naziat": 79,
    "karia": 101,
    "suara": 26,
    "vakia": 56,
    "vaka": 56,
}


def _anahtar(ad: str) -> str:
    """Baslik anahtari: NFC, kesme bicimleri tek `'`, Turkce kucuk harf, sapkasiz, bosluksuz."""
    govde = unicodedata.normalize("NFC", ad)
    for k in KESMELER:
        govde = govde.replace(k, "'")
    return lower_turkish(govde).translate(SAPKA_KATLAMA).replace(" ", "")


def _ascii_katla(ad: str) -> str:
    ayrik = unicodedata.normalize("NFD", ad.removesuffix(SURE_SUFFIX))
    return "".join(c for c in ayrik if ord(c) < 128).lower().replace("'", "")


def sure_tablosu(veri_kok: Path) -> dict[str, int]:
    """A11 staged sure adi tablosundan `anahtar(baslik) -> sure no` (en son ingest calismasi)."""
    klasor = veri_kok / "staged" / SURE_ADLARI_KAYNAGI
    kayit = lineage.son_basarili(klasor, "ingest")
    if kayit is None:
        raise GirdiHatasi(
            f"{SURE_ADLARI_KAYNAGI} icin staged ingest yok (sure eslemesi icin gerekli)"
        )
    try:
        ham = (kayit[1] / "tablo.jsonl").read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError):
        raise GirdiHatasi("sure adi tablosu okunamadi") from None
    harita: dict[str, int] = {}
    for satir in ham.split("\n"):
        if satir == "":
            continue
        nesne = kati_json(satir)
        if not isinstance(nesne, dict):
            raise GirdiHatasi("sure adi tablosu satiri nesne degil")
        baslik, no = nesne.get("baslik"), nesne.get("no")
        if not isinstance(baslik, str) or type(no) is not int:
            raise GirdiHatasi("sure adi tablosu satiri beklenen biciminde degil")
        harita[_anahtar(baslik)] = no
    return harita


def baslik_sure(baslik: str, tablo: dict[str, int]) -> int:
    """`Kur'an/<Ad> Suresi` basliginin sure numarasi (yalniz oneri aninda)."""
    ad = baslik.removeprefix(VIKIKAYNAK_ONEK)
    no = tablo.get(_anahtar(ad))
    if no is None:
        no = EK_ESLEME.get(_ascii_katla(ad))
    if no is None:
        raise GirdiHatasi("baslik bir sure numarasina eslenemedi")
    return no


def _dosya(gelen: Path, tarih: str, slug: str, ad: str) -> tuple[DosyaKilidi, bytes]:
    veri = gelen_oku(gelen, tarih, slug, ad)
    return DosyaKilidi(ad, len(veri), lineage.sha256_bayt(veri)), veri


def _vikikaynak_onerisi(veri_kok: Path, tarih_istenen: str | None) -> dict[str, object]:
    gelen = gelen_dizini(veri_kok, KAYNAK_ORIJINAL)
    tarih = gelen_tarihi_coz(gelen, tarih_istenen, KAYNAK_ORIJINAL)
    adlar = sorted(
        p.name for p in (gelen / tarih).iterdir() if p.is_file() and YANIT_DESENI.fullmatch(p.name)
    )
    if not adlar:
        raise GirdiHatasi(f"{KAYNAK_ORIJINAL}: vikikaynak-NN.json yanitlari yok")
    dosyalar: list[DosyaKilidi] = []
    icerik: dict[str, bytes] = {}
    for ad in (LISTE_DOSYASI, *adlar):
        d, veri = _dosya(gelen, tarih, KAYNAK_ORIJINAL, ad)
        dosyalar.append(d)
        icerik[ad] = veri
    tablo = sure_tablosu(veri_kok)
    sayfalar: list[SayfaKilidi] = []
    wikitextler: dict[int, str] = {}
    for ad in adlar:
        belge = kati_json(icerik[ad].decode("utf-8"))
        liste = yol_al(belge, ad, "query", "pages")
        if not isinstance(liste, list):
            raise GirdiHatasi(f"{ad}: query.pages liste degil")
        for sayfa in liste:
            baslik = yol_al(sayfa, ad, "title")
            rev = yol_al(sayfa, ad, "revisions")
            if not isinstance(rev, list) or len(rev) != 1:
                raise GirdiHatasi(f"{ad}: tek revizyon bekleniyor")
            icerik_metni = yol_al(rev[0], ad, "slots", "main", "content")
            revid = yol_al(rev[0], ad, "revid")
            if (
                not isinstance(baslik, str)
                or not isinstance(icerik_metni, str)
                or type(revid) is not int
            ):
                raise GirdiHatasi(f"{ad}: sayfa alanlari beklenen tipte degil")
            ham = icerik_metni.encode("utf-8")
            sha1 = sha1_hesapla(ham)
            if yol_al(rev[0], ad, "sha1") != sha1 or yol_al(rev[0], ad, "size") != len(ham):
                raise GirdiHatasi(f"{ad}: revizyon ozeti ya da boyutu tutmuyor")
            sure = baslik_sure(baslik, tablo)
            sayfalar.append(SayfaKilidi(baslik, sure, revid, sha1, lineage.sha256_bayt(ham)))
            wikitextler[sure] = icerik_metni
    if sorted(wikitextler) != list(range(1, 115)) or len(sayfalar) != 114:
        raise GirdiHatasi(f"{KAYNAK_ORIJINAL}: {len(sayfalar)} sayfa eslendi; 114 sure bekleniyor")
    for sure in range(1, 115):  # her sayfanin ayet kumesi Tanzil sayisiyla esit olmali
        try:
            elmalili_vikikaynak.sayfa_cikar(
                wikitextler[sure],
                sure=sure,
                ayet_sayisi=AYET_SAYILARI[sure - 1],
                eser="elmalili",
            )
        except GirdiHatasi as hata:
            raise GirdiHatasi(f"{KAYNAK_ORIJINAL}: sure {sure}: {hata}") from None
    kilit = VikikaynakKilidi(
        url=VIKIKAYNAK_URL,
        alinma_tarihi=tarih,
        liste_sha256=next(d.sha256 for d in dosyalar if d.ad == LISTE_DOSYASI),
        dosyalar=tuple(sorted(dosyalar, key=lambda d: d.ad)),
        sayfalar=tuple(sorted(sayfalar, key=lambda s: s.sure)),
    )
    elmalili_vikikaynak.liste_denetle(icerik[LISTE_DOSYASI], kilit)
    return {BOLUM_VIKIKAYNAK: kilit.sozluk()}


def _sade_onerisi(depo_kok: Path, veri_kok: Path, tarih_istenen: str | None) -> dict[str, object]:
    gelen = gelen_dizini(veri_kok, KAYNAK_SADE)
    tarih = gelen_tarihi_coz(gelen, tarih_istenen, KAYNAK_SADE)
    dosya, veri = _dosya(gelen, tarih, KAYNAK_SADE, SADE_DOSYA)
    elmalili_sade.kayitlari_oku(veri)
    commit = _commit(depo_kok, KAYNAK_SADE)
    return {
        BOLUM_SADE: meal_kilit.SadeKilidi(
            SADE_URL.format(commit=commit), commit, tarih, dosya
        ).sozluk()
    }


def _commit(depo_kok: Path, slug: str) -> str:
    kayit = {s.dosya.removesuffix(".toml"): s for s in sources.yukle(depo_kok)}.get(slug)
    if kayit is None or kayit.kaynak is None or kayit.kaynak.surum is None:
        raise GirdiHatasi(f"kaynak kaydi: {slug}: kayitsiz, gecersiz ya da surum yok")
    e = COMMIT.fullmatch(kayit.kaynak.surum)
    if e is None:
        raise GirdiHatasi(f"kaynak kaydi: {slug}: surum 'commit <40 hane>' biciminde degil")
    return e.group(1)


def _epub_onerisi(veri_kok: Path, tarih_istenen: str | None) -> dict[str, object]:
    gelen = gelen_dizini(veri_kok, KAYNAK_EPUB)
    tarih = gelen_tarihi_coz(gelen, tarih_istenen, KAYNAK_EPUB)
    dosya, veri = _dosya(gelen, tarih, KAYNAK_EPUB, EPUB_YEREL_DOSYA)
    elmalili_epub.epub_okuma(veri)
    return {
        BOLUM_EPUB: meal_kilit.EpubKilidi(
            oge=EPUB_OGE,
            uzak_dosya=EPUB_UZAK_DOSYA,
            url=EPUB_URL.format(oge=EPUB_OGE, dosya=EPUB_UZAK_DOSYA),
            alinma_tarihi=tarih,
            sha1=hashlib.sha1(veri, usedforsecurity=False).hexdigest(),
            dosya=dosya,
        ).sozluk()
    }


def kilit_oner_metni(depo_kok: Path, veri_kok: Path, source: str, gelen_tarih: str | None) -> str:
    """`--kilit-oner`: bir kaynagin kilit bolumu (JSON); hicbir sey yazilmaz."""
    if source == KAYNAK_ORIJINAL:
        oneri = _vikikaynak_onerisi(veri_kok, gelen_tarih)
    elif source == KAYNAK_SADE:
        oneri = _sade_onerisi(depo_kok, veri_kok, gelen_tarih)
    elif source == KAYNAK_EPUB:
        oneri = _epub_onerisi(veri_kok, gelen_tarih)
    else:
        raise GirdiHatasi("--kilit-oner icin bilinmeyen meal kaynagi")
    return json.dumps(oneri, ensure_ascii=True, indent=2) + "\n"
