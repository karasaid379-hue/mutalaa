"""Kaynak kaydi (`pipeline/sources/{slug}.toml`): model, okuma ve denetim (A06.1, G-LIS).

Hatalar toplanir, ilki durdurmaz. Mesajlara icerik metni degil yalniz alan adi, slug ve
(enum alanlarinda) gecersiz etiket yazilir. `kapali` kaynakta lisans kopyasi aranmaz ve
dosya okunmaz: kayit yalniz ust veridir.
"""

import hashlib
import re
import tomllib
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Final

from mutalaa_pipeline.enums import LicenseStatus, SourceKind
from mutalaa_pipeline.export.ortak import GirdiHatasi

KAYNAK_DIZINI: Final = "pipeline/sources"

SLUG_DESENI: Final = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")
SHA256_DESENI: Final = re.compile(r"[0-9a-f]{64}")
KOPYA_TARIHI: Final = r"[0-9]{4}-[0-9]{2}-[0-9]{2}"
BOM: Final = b"\xef\xbb\xbf"

# Alan adi -> beklenen tip. Tip denetimi tam tiptir (bool int sayilmaz, datetime date sayilmaz).
ZORUNLU_ALANLAR: Final[dict[str, type]] = {
    "slug": str,
    "tur": str,
    "baslik": str,
    "license_name": str,
    "license_status": str,
    "atif_metni": str,
    "kurul_gerekli": bool,
    "embed_ok": bool,
    "yeniden_kontrol": date,
}
ISTEGE_BAGLI_ALANLAR: Final[dict[str, type]] = {
    "yazar": str,
    "yazar_vefat_yili": int,
    "surum": str,
    "provider": str,
    "kaynak_url": str,
    "license_url": str,
    "kisitlar": dict,
    "notice_text": str,
    "atif_url": str,
    "kamu_mali_tarihi": date,
    "baski_bilgisi": dict,
    "notlar": str,
    "lisans_kopyasi": str,
    "lisans_sha256": str,
}
BILINEN_KISITLAR: Final[dict[str, type]] = {
    "degistirme_yasak": bool,
    "hazir_vt_yasak": bool,
    "onbellek_gun": int,
    "yalniz_eslesen_ses": bool,
}
TIP_ADLARI: Final[dict[type, str]] = {
    str: "metin",
    bool: "bool",
    int: "tam sayi",
    date: "TOML tarihi",
    dict: "tablo",
}


def _g(deger: str) -> str:
    """Dosyadan gelen bir degeri konsol icin guvenli (ASCII, kontrolsuz) yazar."""
    return ascii(deger)[1:-1][:60]


@dataclass(frozen=True)
class Kaynak:
    """Gecerli bir kaynak kaydi; alan adlari `source` sutunlariyla ayni."""

    slug: str
    tur: SourceKind
    baslik: str
    license_name: str
    license_status: LicenseStatus
    atif_metni: str
    kurul_gerekli: bool
    embed_ok: bool
    yeniden_kontrol: date
    yazar: str | None = None
    yazar_vefat_yili: int | None = None
    surum: str | None = None
    provider: str | None = None
    kaynak_url: str | None = None
    license_url: str | None = None
    kisitlar: dict[str, object] = field(default_factory=dict)
    notice_text: str | None = None
    atif_url: str | None = None
    kamu_mali_tarihi: date | None = None
    baski_bilgisi: dict[str, object] | None = None
    notlar: str | None = None
    lisans_kopyasi: str | None = None
    lisans_sha256: str | None = None


@dataclass
class Sonuc:
    """Tek bir TOML dosyasinin okuma ve denetim sonucu."""

    dosya: str
    kaynak: Kaynak | None = None
    hatalar: list[str] = field(default_factory=list)
    uyarilar: list[str] = field(default_factory=list)
    kopya: str | None = None


def kaynak_dizini(kok: Path) -> Path:
    return kok / "pipeline" / "sources"


def _tip_uygun(deger: object, tip: type) -> bool:
    return type(deger) is tip


def _kopya_yolu_hatasi(yol: str, slug: str | None) -> str | None:
    """`licenses/{slug}-YYYY-AA-GG.txt` biciminde olmayan yol icin mesaj dondurur."""
    if "\\" in yol:
        return "lisans_kopyasi ters egik cizgi iceremez"
    if yol.startswith("/") or ":" in yol:
        return "lisans_kopyasi mutlak yol olamaz"
    if ".." in yol.split("/"):
        return "lisans_kopyasi '..' iceremez"
    govde = re.escape(slug) if slug is not None else SLUG_DESENI.pattern
    eslesme = re.fullmatch(f"licenses/(?P<ad>{govde})-(?P<tarih>{KOPYA_TARIHI})\\.txt", yol)
    if eslesme is None:
        return "lisans_kopyasi licenses/{slug}-YYYY-AA-GG.txt biciminde olmali"
    try:
        date.fromisoformat(eslesme.group("tarih"))
    except ValueError:
        return "lisans_kopyasi dosya adindaki tarih gecersiz"
    return None


def _lisans_kopyasi_denetle(
    veri: dict[str, object], slug: str | None, dizin: Path | None, hatalar: list[str]
) -> None:
    """`kapali` disindaki kaynakta lisans kopyasi var mi ve SHA-256 tutuyor mu (G-LIS)."""
    kopya = veri.get("lisans_kopyasi")
    ozet = veri.get("lisans_sha256")
    if "lisans_kopyasi" not in veri:
        hatalar.append("lisans_kopyasi zorunlu (license_status kapali degil)")
    if "lisans_sha256" not in veri:
        hatalar.append("lisans_sha256 zorunlu (license_status kapali degil)")
    if not isinstance(kopya, str):
        return
    hata = _kopya_yolu_hatasi(kopya, slug)
    if hata is not None:
        hatalar.append(hata)
        return
    if dizin is None:
        return
    try:
        hedef = dizin / kopya
        if not hedef.resolve().is_relative_to(dizin.resolve()):
            hatalar.append("lisans_kopyasi pipeline/sources disina cikiyor")
            return
        if not hedef.is_file():
            hatalar.append("lisans_kopyasi dosyasi yok")
            return
        ham = hedef.read_bytes()
    except (OSError, RuntimeError):
        hatalar.append("lisans_kopyasi okunamadi")
        return
    if len(ham) == 0:
        hatalar.append("lisans_kopyasi bos dosya")
        return
    hesaplanan = hashlib.sha256(ham).hexdigest()
    if isinstance(ozet, str) and SHA256_DESENI.fullmatch(ozet) and ozet != hesaplanan:
        hatalar.append(f"lisans_sha256 dosya ozetiyle ayni degil (hesaplanan: {hesaplanan})")


def _kisitlar_denetle(kisitlar: dict[str, object], hatalar: list[str], uyarilar: list[str]) -> None:
    for ad in sorted(kisitlar):
        deger = kisitlar[ad]
        beklenen = BILINEN_KISITLAR.get(ad)
        if beklenen is None:
            uyarilar.append(f"kisitlar: bilinmeyen anahtar {_g(ad)}")
        elif not _tip_uygun(deger, beklenen):
            hatalar.append(f"kisitlar.{ad}: {TIP_ADLARI[beklenen]} olmali")
        elif ad == "onbellek_gun" and isinstance(deger, int) and deger < 1:
            hatalar.append("kisitlar.onbellek_gun 1 veya daha buyuk olmali")


def dogrula(
    veri: dict[str, object], dosya: str, dizin: Path | None, sonuc: Sonuc | None = None
) -> Sonuc:
    """Ayristirilmis TOML tablosunu denetler.

    `dizin` (pipeline/sources) verilirse lisans kopyasi dosyasi da okunup ozeti sinanir;
    `None` ise yalniz kayit semasi denetlenir (`sources list`).
    """
    cikti = sonuc if sonuc is not None else Sonuc(dosya)
    hatalar, uyarilar = cikti.hatalar, cikti.uyarilar

    govde = dosya[: -len(".toml")] if dosya.endswith(".toml") else dosya
    if not dosya.endswith(".toml"):
        hatalar.append("dosya uzantisi .toml olmali")
    if SLUG_DESENI.fullmatch(govde) is None:
        hatalar.append("dosya adi ^[a-z0-9]+(-[a-z0-9]+)*$ desenine uymuyor (ASCII, kucuk harf)")

    izinli = ZORUNLU_ALANLAR.keys() | ISTEGE_BAGLI_ALANLAR.keys()
    for ad in sorted(veri):
        if ad not in izinli:
            hatalar.append(f"bilinmeyen alan: {_g(ad)}")
    for ad in ZORUNLU_ALANLAR:
        if ad not in veri:
            hatalar.append(f"zorunlu alan eksik: {ad}")

    tipli: set[str] = set()
    for ad, tip in (ZORUNLU_ALANLAR | ISTEGE_BAGLI_ALANLAR).items():
        if ad not in veri:
            continue
        if _tip_uygun(veri[ad], tip):
            tipli.add(ad)
        else:
            hatalar.append(f"{ad}: {TIP_ADLARI[tip]} olmali")

    slug: str | None = None
    ham_slug = veri.get("slug")
    if "slug" in tipli and isinstance(ham_slug, str):
        if SLUG_DESENI.fullmatch(ham_slug) is None:
            hatalar.append("slug ^[a-z0-9]+(-[a-z0-9]+)*$ desenine uymuyor")
        else:
            slug = ham_slug
            if slug != govde:
                hatalar.append(f"slug ({slug}) dosya adiyla ({_g(govde)}) ayni degil")

    if "tur" in tipli:
        try:
            SourceKind(str(veri["tur"]))
        except ValueError:
            hatalar.append(f"tur: bilinmeyen deger {_g(str(veri['tur']))}")
    durum: LicenseStatus | None = None
    if "license_status" in tipli:
        try:
            durum = LicenseStatus(str(veri["license_status"]))
        except ValueError:
            hatalar.append(f"license_status: bilinmeyen deger {_g(str(veri['license_status']))}")

    for ad in ("atif_metni", "baslik", "license_name"):
        deger = veri.get(ad)
        if ad in tipli and isinstance(deger, str) and deger.strip(" \t\n") == "":
            hatalar.append(f"{ad} bos olamaz")

    kopya_yolu = veri.get("lisans_kopyasi")
    if "lisans_kopyasi" in tipli and isinstance(kopya_yolu, str):
        cikti.kopya = kopya_yolu

    ozet = veri.get("lisans_sha256")
    if "lisans_sha256" in tipli and isinstance(ozet, str) and SHA256_DESENI.fullmatch(ozet) is None:
        hatalar.append("lisans_sha256 64 haneli kucuk harfli onaltilik olmali")

    kisitlar = veri.get("kisitlar")
    if "kisitlar" in tipli and isinstance(kisitlar, dict):
        _kisitlar_denetle(kisitlar, hatalar, uyarilar)

    embed_ok = veri.get("embed_ok")
    if embed_ok is True:
        if durum is LicenseStatus.KAPALI:
            hatalar.append("license_status kapali iken embed_ok true olamaz")
        if veri.get("provider") == "quran_foundation":
            hatalar.append("provider quran_foundation iken embed_ok true olamaz")

    if durum is not None and durum is not LicenseStatus.KAPALI:
        _lisans_kopyasi_denetle(veri, slug, dizin, hatalar)

    if not hatalar:
        cikti.kaynak = _olustur(veri)
    return cikti


def _metin(veri: dict[str, object], ad: str) -> str | None:
    deger = veri.get(ad)
    return deger if isinstance(deger, str) else None


def _tablo(veri: dict[str, object], ad: str) -> dict[str, object] | None:
    deger = veri.get(ad)
    return deger if isinstance(deger, dict) else None


def _tarih(veri: dict[str, object], ad: str) -> date | None:
    deger = veri.get(ad)
    return deger if isinstance(deger, date) else None


def _olustur(veri: dict[str, object]) -> Kaynak:
    """Hatasiz bir tablodan `Kaynak` uretir (tipler `dogrula` ile sinanmistir)."""
    yeniden = _tarih(veri, "yeniden_kontrol")
    vefat = veri.get("yazar_vefat_yili")
    kurul = veri["kurul_gerekli"]
    embed = veri["embed_ok"]
    assert yeniden is not None
    assert isinstance(kurul, bool)
    assert isinstance(embed, bool)
    return Kaynak(
        slug=str(veri["slug"]),
        tur=SourceKind(str(veri["tur"])),
        baslik=str(veri["baslik"]),
        license_name=str(veri["license_name"]),
        license_status=LicenseStatus(str(veri["license_status"])),
        atif_metni=str(veri["atif_metni"]),
        kurul_gerekli=kurul,
        embed_ok=embed,
        yeniden_kontrol=yeniden,
        yazar=_metin(veri, "yazar"),
        yazar_vefat_yili=vefat if isinstance(vefat, int) else None,
        surum=_metin(veri, "surum"),
        provider=_metin(veri, "provider"),
        kaynak_url=_metin(veri, "kaynak_url"),
        license_url=_metin(veri, "license_url"),
        kisitlar=_tablo(veri, "kisitlar") or {},
        notice_text=_metin(veri, "notice_text"),
        atif_url=_metin(veri, "atif_url"),
        kamu_mali_tarihi=_tarih(veri, "kamu_mali_tarihi"),
        baski_bilgisi=_tablo(veri, "baski_bilgisi"),
        notlar=_metin(veri, "notlar"),
        lisans_kopyasi=_metin(veri, "lisans_kopyasi"),
        lisans_sha256=_metin(veri, "lisans_sha256"),
    )


def oku(yol: Path, dizin: Path | None) -> Sonuc:
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
    sonuc = dogrula(veri, yol.name, dizin, sonuc)
    if sonuc.hatalar:
        sonuc.kaynak = None
    return sonuc


def yetim_kopyalar(kok: Path, sonuclar: list[Sonuc]) -> list[str]:
    """`licenses/` altinda hicbir kaydin gostermedigi dosyalarin adlari (`.gitkeep` haric)."""
    klasor = kaynak_dizini(kok) / "licenses"
    if not klasor.is_dir():
        return []
    gosterilen = {s.kopya for s in sonuclar if s.kopya is not None}
    yetimler: list[str] = []
    for yol in sorted(klasor.iterdir(), key=lambda p: p.name):
        if yol.name == ".gitkeep" or not yol.is_file():
            continue
        if f"licenses/{yol.name}" not in gosterilen:
            yetimler.append(_g(yol.name))
    return yetimler


def yukle(kok: Path, *, lisans_dosyalari: bool) -> list[Sonuc]:
    """`pipeline/sources/*.toml` dosyalarini dosya adi sirasinda (Ordinal) okur.

    `lisans_dosyalari` dogruysa lisans kopyasi dosyalari da sinanir (`sources check`).
    """
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
        sonuclar.append(oku(yol, dizin if lisans_dosyalari else None))
    return sonuclar
