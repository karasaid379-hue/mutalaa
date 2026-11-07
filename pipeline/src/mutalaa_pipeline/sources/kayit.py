"""Kaynak kaydi (`pipeline/sources/{slug}.toml`): model, okuma ve denetim (A06.1, G-KAY).

Kayit adi, adresi, surumu, atif satirini ve kaynagin kendi bildirimini tasir (K-42 madde 4).
Zorunlu alanlar `slug`, `tur`, `baslik`, `atif_metni`; oteki alanlar istege baglidir ve burada
sayilmayan her alan hatadir. Hatalar toplanir, ilki durdurmaz. Mesajlara icerik metni degil
yalniz alan adi, slug ve (enum alaninda) gecersiz etiket yazilir.
"""

import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

from mutalaa_pipeline.enums import SourceKind
from mutalaa_pipeline.export.ortak import GirdiHatasi

KAYNAK_DIZINI: Final = "pipeline/sources"

SLUG_DESENI: Final = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")
BOM: Final = b"\xef\xbb\xbf"

# Alan adi -> beklenen tip. Tip denetimi tam tiptir (bool int sayilmaz).
ZORUNLU_ALANLAR: Final[dict[str, type]] = {
    "slug": str,
    "tur": str,
    "baslik": str,
    "atif_metni": str,
}
ISTEGE_BAGLI_ALANLAR: Final[dict[str, type]] = {
    "yazar": str,
    "surum": str,
    "provider": str,
    "kaynak_url": str,
    "atif_url": str,
    "notice_text": str,
    "baski_bilgisi": dict,
    "notlar": str,
}
# Bos (yalniz U+0020, U+0009, U+000A) olamayan metin alanlari.
DOLU_ALANLAR: Final = ("baslik", "atif_metni")
TIP_ADLARI: Final[dict[type, str]] = {str: "metin", dict: "tablo"}


def _g(deger: str) -> str:
    """Dosyadan gelen bir degeri konsol icin guvenli (ASCII, kontrolsuz) yazar."""
    return ascii(deger)[1:-1][:60]


@dataclass(frozen=True)
class Kaynak:
    """Gecerli bir kaynak kaydi; alan adlari `icerik.source` sutunlariyla ayni."""

    slug: str
    tur: SourceKind
    baslik: str
    atif_metni: str
    yazar: str | None = None
    surum: str | None = None
    provider: str | None = None
    kaynak_url: str | None = None
    atif_url: str | None = None
    notice_text: str | None = None
    baski_bilgisi: dict[str, object] | None = None
    notlar: str | None = None


@dataclass
class Sonuc:
    """Tek bir TOML dosyasinin okuma ve denetim sonucu."""

    dosya: str
    kaynak: Kaynak | None = None
    hatalar: list[str] = field(default_factory=list)
    uyarilar: list[str] = field(default_factory=list)


def kaynak_dizini(kok: Path) -> Path:
    return kok / "pipeline" / "sources"


def _tip_uygun(deger: object, tip: type) -> bool:
    return type(deger) is tip


def dogrula(veri: dict[str, object], dosya: str, sonuc: Sonuc | None = None) -> Sonuc:
    """Ayristirilmis TOML tablosunu kayit semasina gore denetler."""
    cikti = sonuc if sonuc is not None else Sonuc(dosya)
    hatalar = cikti.hatalar

    govde = dosya[: -len(".toml")] if dosya.endswith(".toml") else dosya
    if not dosya.endswith(".toml"):
        hatalar.append("dosya uzantisi .toml olmali")
    if SLUG_DESENI.fullmatch(govde) is None:
        hatalar.append("dosya adi ^[a-z0-9]+(-[a-z0-9]+)*$ desenine uymuyor (ASCII, kucuk harf)")

    alanlar = ZORUNLU_ALANLAR | ISTEGE_BAGLI_ALANLAR
    for ad in sorted(veri):
        if ad not in alanlar:
            hatalar.append(f"bilinmeyen alan: {_g(ad)}")
    for ad in ZORUNLU_ALANLAR:
        if ad not in veri:
            hatalar.append(f"zorunlu alan eksik: {ad}")

    tipli: set[str] = set()
    for ad, tip in alanlar.items():
        if ad not in veri:
            continue
        if _tip_uygun(veri[ad], tip):
            tipli.add(ad)
        else:
            hatalar.append(f"{ad}: {TIP_ADLARI[tip]} olmali")

    ham_slug = veri.get("slug")
    if "slug" in tipli and isinstance(ham_slug, str):
        if SLUG_DESENI.fullmatch(ham_slug) is None:
            hatalar.append("slug ^[a-z0-9]+(-[a-z0-9]+)*$ desenine uymuyor")
        elif ham_slug != govde:
            hatalar.append(f"slug ({ham_slug}) dosya adiyla ({_g(govde)}) ayni degil")

    if "tur" in tipli:
        try:
            SourceKind(str(veri["tur"]))
        except ValueError:
            hatalar.append(f"tur: bilinmeyen deger {_g(str(veri['tur']))}")

    for ad in DOLU_ALANLAR:
        deger = veri.get(ad)
        if ad in tipli and isinstance(deger, str) and deger.strip(" \t\n") == "":
            hatalar.append(f"{ad} bos olamaz")

    if not hatalar:
        cikti.kaynak = _olustur(veri)
    return cikti


def _metin(veri: dict[str, object], ad: str) -> str | None:
    deger = veri.get(ad)
    return deger if isinstance(deger, str) else None


def _tablo(veri: dict[str, object], ad: str) -> dict[str, object] | None:
    deger = veri.get(ad)
    return deger if isinstance(deger, dict) else None


def _olustur(veri: dict[str, object]) -> Kaynak:
    """Hatasiz bir tablodan `Kaynak` uretir (tipler `dogrula` ile sinanmistir)."""
    return Kaynak(
        slug=str(veri["slug"]),
        tur=SourceKind(str(veri["tur"])),
        baslik=str(veri["baslik"]),
        atif_metni=str(veri["atif_metni"]),
        yazar=_metin(veri, "yazar"),
        surum=_metin(veri, "surum"),
        provider=_metin(veri, "provider"),
        kaynak_url=_metin(veri, "kaynak_url"),
        atif_url=_metin(veri, "atif_url"),
        notice_text=_metin(veri, "notice_text"),
        baski_bilgisi=_tablo(veri, "baski_bilgisi"),
        notlar=_metin(veri, "notlar"),
    )


def oku(yol: Path) -> Sonuc:
    """Tek bir TOML dosyasini baytlardan okur, ayristirir ve denetler."""
    sonuc = Sonuc(_g(yol.name))
    try:
        ham = yol.read_bytes()
    except OSError:
        sonuc.hatalar.append("dosya okunamadi")
        return sonuc
    if ham.startswith(BOM):
        sonuc.hatalar.append("BOM var (UTF-8 BOM'suz olmali)")
        return sonuc
    try:
        metin = ham.decode("utf-8")
    except UnicodeDecodeError as hata:
        sonuc.hatalar.append(f"UTF-8 degil (bayt {hata.start})")
        return sonuc
    if "\r" in metin:
        sonuc.hatalar.append("CR/CRLF satir sonu var (LF olmali)")
    try:
        veri: dict[str, object] = tomllib.loads(metin)
    except tomllib.TOMLDecodeError as hata:
        sonuc.hatalar.append(f"TOML ayristirilamadi: {_g(str(hata))}")
        return sonuc
    sonuc = dogrula(veri, yol.name, sonuc)
    if sonuc.hatalar:
        sonuc.kaynak = None
    return sonuc


def yukle(kok: Path) -> list[Sonuc]:
    """`pipeline/sources/*.toml` dosyalarini dosya adi sirasinda (Ordinal) okur ve denetler."""
    dizin = kaynak_dizini(kok)
    if not dizin.is_dir():
        raise GirdiHatasi(f"{KAYNAK_DIZINI} klasoru yok")
    sonuclar: list[Sonuc] = []
    for yol in sorted(dizin.glob("*.toml"), key=lambda p: p.name):
        if not yol.is_file():
            sonuc = Sonuc(_g(yol.name))
            sonuc.hatalar.append("dosya degil")
            sonuclar.append(sonuc)
            continue
        sonuclar.append(oku(yol))
    return sonuclar
