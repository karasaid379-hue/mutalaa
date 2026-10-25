"""Tanzil ust verisinden sure basina ayet sayilari ve uc dilde uretilmis kopyalari (A04.1).

Indirilen XML guvenilmeyen veridir: yalniz ayristirilir. Kok ogenin `type`, `version`,
`copyright`, `license` oznitelikleri ile `<sura>` ogelerinin `index`, `ayas`, `start`
oznitelikleri okunur. Sure adlari okunmaz, yazilmaz, gunluge basilmaz. Sayilar asla
"duzeltilmez": ihlalde komut 2 ile cikar.
"""

import contextlib
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Final
from xml.parsers import expat

from mutalaa_pipeline.export.ortak import GirdiHatasi, ayni_mi, kati_json, utf8_oku, yaz

SURE_SAYISI: Final = 114
TOPLAM_AYET: Final = 6236  # Capa semasi bolum 2 madde 1
IKINCI_SURE_AYET: Final = 286  # Capa semasi bolum 4 (q:2:287 AYET_ARALIGI)

JSON_YOLU: Final = "shared/data/ayet-sayilari.json"
TS_YOLU: Final = "packages/anchors/src/generated/ayet-sayilari.ts"
PY_YOLU: Final = "pipeline/src/mutalaa_pipeline/anchor/ayet_sayilari.py"
CS_YOLU: Final = "server/Mutalaa.Domain/Anchors/AyetSayilari.g.cs"

UYARI: Final = "Bu dosya `uv run mutalaa export ayet-sayilari` ile üretilir; elle düzenlenmez."
# Uretilmis Python kopyasinda belge dizgisi olur; ruff RUF001-RUF003 dotless i'yi belirsiz sayar.
ACIKLAMA: Final = "Her sure için âyet adedi (114 eleman); indis 0 birinci suredir."

_JSON_ANAHTARLARI: Final = (
    "kaynak_url",
    "alinma_tarihi",
    "sha256",
    "lisans",
    "telif",
    "surum",
    "sayilar",
)
_SAYI: Final = re.compile(r"0|[1-9][0-9]{0,8}")
_TARIH: Final = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
_URL: Final = re.compile(r"https://[!-~]+")
_SHA256: Final = re.compile(r"[0-9a-f]{64}")
_YASAK_BILDIRIMLER: Final = (b"<!DOCTYPE", b"<!ENTITY")


@dataclass(frozen=True)
class UstVeri:
    """XML'den okunan alanlar."""

    surum: str
    telif: str
    lisans: str
    sayilar: tuple[int, ...]


@dataclass(frozen=True)
class AyetSayilariBelgesi:
    """`shared/data/ayet-sayilari.json` icerigi."""

    kaynak_url: str
    alinma_tarihi: str
    sha256: str
    lisans: str
    telif: str
    surum: str
    sayilar: tuple[int, ...]


def _oznitelik(oge: ET.Element, ad: str, baglam: str) -> str:
    deger = oge.get(ad)
    if deger is None:
        raise GirdiHatasi(f"{baglam}: '{ad}' ozniteligi yok")
    return deger


def _tam_sayi(oge: ET.Element, ad: str, baglam: str) -> int:
    deger = _oznitelik(oge, ad, baglam)
    if _SAYI.fullmatch(deger) is None:
        raise GirdiHatasi(f"{baglam}: '{ad}' ozniteligi ondalik ASCII tam sayi degil")
    return int(deger)


def _bildirim_reddet(*_bagimsiz: object) -> None:
    raise GirdiHatasi("XML DOCTYPE ya da ENTITY bildirimi iceriyor; reddedildi")


def _bildirim_yedek_denetimi(veri: bytes) -> None:
    """Yedek: expat DOCTYPE ya da varlik bildirimi gorurse reddeder (bayt aramasindan bagimsiz)."""
    ayristirici = expat.ParserCreate()
    ayristirici.StartDoctypeDeclHandler = _bildirim_reddet
    ayristirici.EntityDeclHandler = _bildirim_reddet
    with contextlib.suppress(expat.ExpatError):  # bozuk XML'i asil ayristirma bildirir
        ayristirici.Parse(veri, True)


def ayristir(veri: bytes) -> UstVeri:
    """Tanzil `quran-data.xml` baytlarini denetleyerek ayristirir."""
    # Yalniz UTF-8 XML kabul edilir: BOM'suz UTF-16 bayt alt dizgisi aramasini atlatir.
    try:
        veri.decode("utf-8")
    except UnicodeDecodeError as hata:
        raise GirdiHatasi(f"XML UTF-8 degil (bayt {hata.start})") from hata
    if b"\x00" in veri:
        raise GirdiHatasi("XML UTF-8 degil (NUL bayt)")
    for bildirim in _YASAK_BILDIRIMLER:
        if bildirim in veri:
            raise GirdiHatasi("XML DOCTYPE ya da ENTITY bildirimi iceriyor; reddedildi")
    _bildirim_yedek_denetimi(veri)
    try:
        kok = ET.fromstring(veri)
    except ET.ParseError as hata:
        satir, sutun = hata.position
        raise GirdiHatasi(f"XML ayristirilamadi (satir {satir}, sutun {sutun})") from hata

    if kok.get("type") != "metadata":
        raise GirdiHatasi("kok ogenin 'type' ozniteligi 'metadata' degil")
    surum = _oznitelik(kok, "version", "kok oge")
    telif = _oznitelik(kok, "copyright", "kok oge")
    lisans = _oznitelik(kok, "license", "kok oge")

    sureler = list(kok.iter("sura"))
    if len(sureler) != SURE_SAYISI:
        raise GirdiHatasi(f"{len(sureler)} <sura> ogesi var; {SURE_SAYISI} bekleniyor")
    sayilar: list[int] = []
    toplam = 0
    for sira, oge in enumerate(sureler, start=1):
        baglam = f"{sira}. <sura>"
        index = _tam_sayi(oge, "index", baglam)
        if index != sira:
            raise GirdiHatasi(f"{baglam}: index {index}; {sira} bekleniyor (ardisik degil)")
        ayas = _tam_sayi(oge, "ayas", baglam)
        if ayas < 1:
            raise GirdiHatasi(f"{baglam}: ayas 1'den kucuk")
        start = _tam_sayi(oge, "start", baglam)
        if start != toplam:
            raise GirdiHatasi(f"{baglam}: start {start}; onceki ayas toplami {toplam}")
        sayilar.append(ayas)
        toplam += ayas
    # Sabitler Capa semasinda yazilidir; uyusmazlikta sayilar "duzeltilmez", komut durur.
    if sayilar[1] != IKINCI_SURE_AYET:
        raise GirdiHatasi(f"2. sure {sayilar[1]} ayet; {IKINCI_SURE_AYET} bekleniyor")
    if toplam != TOPLAM_AYET:
        raise GirdiHatasi(f"ayet toplami {toplam}; {TOPLAM_AYET} bekleniyor")
    return UstVeri(surum=surum, telif=telif, lisans=lisans, sayilar=tuple(sayilar))


def _url_denetle(url: str) -> str:
    if _URL.fullmatch(url) is None:
        raise GirdiHatasi("kaynak adresi https:// ile baslayan, bosluksuz ASCII olmali")
    return url


def _tarih_denetle(tarih: str) -> str:
    if _TARIH.fullmatch(tarih) is None:
        raise GirdiHatasi("tarih YYYY-AA-GG biciminde olmali")
    try:
        date.fromisoformat(tarih)
    except ValueError as hata:
        raise GirdiHatasi("tarih gecerli bir gun degil") from hata
    return tarih


def belge_kur(veri: bytes, url: str, tarih: str) -> AyetSayilariBelgesi:
    """XML baytlarindan JSON belgesini kurar."""
    url = _url_denetle(url)
    tarih = _tarih_denetle(tarih)
    ust = ayristir(veri)
    return AyetSayilariBelgesi(
        kaynak_url=url,
        alinma_tarihi=tarih,
        sha256=hashlib.sha256(veri).hexdigest(),
        lisans=ust.lisans,
        telif=ust.telif,
        surum=ust.surum,
        sayilar=ust.sayilar,
    )


def json_metni(belge: AyetSayilariBelgesi) -> str:
    """JSON dosyasinin metni: 2 bosluk girinti, sonda satir sonu."""
    icerik = {
        "kaynak_url": belge.kaynak_url,
        "alinma_tarihi": belge.alinma_tarihi,
        "sha256": belge.sha256,
        "lisans": belge.lisans,
        "telif": belge.telif,
        "surum": belge.surum,
        "sayilar": list(belge.sayilar),
    }
    return json.dumps(icerik, ensure_ascii=True, indent=2) + "\n"


def _dizgi_alani(icerik: dict[str, object], ad: str) -> str:
    deger = icerik[ad]
    if not isinstance(deger, str):
        raise GirdiHatasi(f"{JSON_YOLU}: '{ad}' dizgi degil")
    return deger


def json_coz(metin: str) -> AyetSayilariBelgesi:
    """JSON metnini denetleyerek belgeye cevirir."""
    icerik = kati_json(metin)
    if not isinstance(icerik, dict):
        raise GirdiHatasi(f"{JSON_YOLU}: kok nesne degil")
    if set(icerik) != set(_JSON_ANAHTARLARI):
        raise GirdiHatasi(f"{JSON_YOLU}: anahtarlar {', '.join(_JSON_ANAHTARLARI)} olmali")
    sayilar = icerik["sayilar"]
    if not isinstance(sayilar, list) or len(sayilar) != SURE_SAYISI:
        raise GirdiHatasi(f"{JSON_YOLU}: 'sayilar' {SURE_SAYISI} elemanli dizi olmali")
    dogrulanmis: list[int] = []
    for sira, sayi in enumerate(sayilar, start=1):
        if type(sayi) is not int or sayi < 1:
            raise GirdiHatasi(f"{JSON_YOLU}: sayilar[{sira - 1}] pozitif tam sayi degil")
        dogrulanmis.append(sayi)
    sha256 = _dizgi_alani(icerik, "sha256")
    if _SHA256.fullmatch(sha256) is None:
        raise GirdiHatasi(f"{JSON_YOLU}: 'sha256' 64 kucuk harf onaltilik olmali")
    return AyetSayilariBelgesi(
        kaynak_url=_url_denetle(_dizgi_alani(icerik, "kaynak_url")),
        alinma_tarihi=_tarih_denetle(_dizgi_alani(icerik, "alinma_tarihi")),
        sha256=sha256,
        lisans=_dizgi_alani(icerik, "lisans"),
        telif=_dizgi_alani(icerik, "telif"),
        surum=_dizgi_alani(icerik, "surum"),
        sayilar=tuple(dogrulanmis),
    )


def json_oku(kok: Path) -> AyetSayilariBelgesi:
    """Depodaki `shared/data/ayet-sayilari.json` dosyasini okur."""
    yol = kok / JSON_YOLU
    if not yol.is_file():
        raise GirdiHatasi(f"{JSON_YOLU} yok; once `export ayet-sayilari --kaynak` calistirin")
    return json_coz(utf8_oku(yol, JSON_YOLU))


def _baslik(yorum: str, belge: AyetSayilariBelgesi) -> list[str]:
    return [
        f"{yorum} {UYARI}",
        f"{yorum} Kaynak: {belge.kaynak_url}",
        f"{yorum} SHA-256: {belge.sha256}",
    ]


def ts_metni(belge: AyetSayilariBelgesi) -> str:
    """`packages/anchors` icin TypeScript kopyasi."""
    satirlar = [
        *_baslik("//", belge),
        "",
        f"/** {ACIKLAMA} */",
        "export const AYET_SAYILARI: readonly number[] = Object.freeze([",
        *(f"  {sayi}," for sayi in belge.sayilar),
        "]);",
    ]
    return "\n".join(satirlar) + "\n"


def py_metni(belge: AyetSayilariBelgesi) -> str:
    """`mutalaa_pipeline.anchor` icin Python kopyasi."""
    satirlar = [
        *_baslik("#", belge),
        f'"""{ACIKLAMA}"""',
        "",
        "from typing import Final",
        "",
        "AYET_SAYILARI: Final[tuple[int, ...]] = (",
        *(f"    {sayi}," for sayi in belge.sayilar),
        ")",
    ]
    return "\n".join(satirlar) + "\n"


def cs_metni(belge: AyetSayilariBelgesi) -> str:
    """`Mutalaa.Domain/Anchors` icin C# kopyasi."""
    satirlar = [
        "// <auto-generated/>",
        *_baslik("//", belge),
        "",
        "using System.Collections.Immutable;",
        "",
        "namespace Mutalaa.Domain.Anchors;",
        "",
        "/// <summary>",
        f"/// {ACIKLAMA}",
        "/// </summary>",
        "public static class AyetSayilari",
        "{",
        "    public static ImmutableArray<int> Sayilar { get; } =",
        "    [",
        *(f"        {sayi}," for sayi in belge.sayilar),
        "    ];",
        "}",
    ]
    return "\n".join(satirlar) + "\n"


def tum_metinler(belge: AyetSayilariBelgesi) -> dict[str, str]:
    """Goreli yol -> beklenen metin; JSON ve uc kopya."""
    return {
        JSON_YOLU: json_metni(belge),
        TS_YOLU: ts_metni(belge),
        PY_YOLU: py_metni(belge),
        CS_YOLU: cs_metni(belge),
    }


def uret(kok: Path, kaynak: Path, url: str, tarih: str) -> list[str]:
    """XML'den JSON ve uc kopyayi yazar; degisen dosyalarin goreli yollarini dondurur."""
    if not kaynak.is_file():
        raise GirdiHatasi("--kaynak dosyasi bulunamadi")
    belge = belge_kur(kaynak.read_bytes(), url, tarih)
    return [yol for yol, metin in tum_metinler(belge).items() if yaz(kok, yol, metin)]


def denetle(kok: Path) -> list[str]:
    """JSON'dan beklenen metinleri bellekte uretir; diskten farkli dosyalari dondurur."""
    belge = json_oku(kok)
    return [yol for yol, metin in tum_metinler(belge).items() if not ayni_mi(kok, yol, metin)]
