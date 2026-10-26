# ruff: noqa: RUF001
"""Lisans kopyasi dosyasi uretir (A06.3): `pipeline/sources/licenses/{kimlik}-{tarih}.txt`.

Girdi dosyalari guvenilmez veridir: bu betik onlari yalniz METIN olarak okur, calistirmaz.
Python `-I` ile, proje kokunden calistirilir:

    uv run --project pipeline python -I scripts/lisans_kopyasi_olustur.py <komut> ...

Komutlar:
  cikar     HTML ya da ham dosyadan govde metni cikarir (kesme, paragraf secme).
  font-ttx  `ttx -t name -t OS/2` ciktisindan telif/lisans metinleri ve fsType degerini cikarir.
  yaz       Baslik (5 satir) + bos satir + govde(ler) ile lisans kopyasini yazar.

Dosya UTF-8 (BOM'suz), LF satir sonludur. Ucuncu taraf lisans metninin sozcuklerine dokunulmaz;
yalnizca satir sonlari LF'ye cevrilir ve dosya sonuna (yoksa) bir LF eklenir.
Betik yerel ayar kullanmaz; buyuk-kucuk harf donusumu yapmaz.
"""

import argparse
import datetime
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from mutalaa_pipeline.sources.html_metin import KesmeHatasi, html_metni, paragraf_sec

KIMLIK_DESENI = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")
TARIH_DESENI = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
KOK = Path(__file__).resolve().parent.parent
KOPYA_DIZINI = KOK / "pipeline" / "sources" / "licenses"
BOM = chr(0xFEFF)
# Dosya basligindaki Not satiri.
NOT_SATIRI_TR = (
    "Not: Hukuki görüş değildir. Bu dosya lisans/şart metninin "
    "kopyasıdır; kaynağın kendi metni değildir."
)
FSTYPE_BIT_SAYISI = 16


class YolHatasi(Exception):
    """Verilen yol proje kokunun disina cikiyor."""


def yol_coz(metin: str) -> Path:
    """Yolu proje kokune gore cozer; kokun disina cikarsa `YolHatasi` verir."""
    yol = Path(metin)
    if not yol.is_absolute():
        yol = KOK / yol
    cozulmus = yol.resolve()
    if not cozulmus.is_relative_to(KOK.resolve()):
        raise YolHatasi
    return cozulmus


def metin_oku(yol: Path) -> str:
    """Dosyayi UTF-8 olarak okur; BOM atilir, satir sonlari LF olur."""
    metin = yol.read_bytes().decode("utf-8")
    if metin.startswith(BOM):
        metin = metin[len(BOM) :]
    return metin.replace("\r\n", "\n").replace("\r", "\n")


def metin_yaz(yol: Path, metin: str) -> None:
    if not metin.endswith("\n"):
        metin += "\n"
    yol.parent.mkdir(parents=True, exist_ok=True)
    yol.write_bytes(metin.encode("utf-8"))


# --- cikar ----------------------------------------------------------------------------------


def komut_cikar(args: argparse.Namespace) -> int:
    ham = metin_oku(yol_coz(args.girdi))
    if args.tur == "html":
        sonuc = html_metni(
            ham, baslangic=args.baslangic, bitis=args.bitis, bitis_son=args.bitis_son
        )
        govde = sonuc.govde
        print(f"baslik: {sonuc.baslik!r}", file=sys.stderr)
    else:
        govde = ham
    if args.paragraf is not None:
        govde = paragraf_sec(govde, args.paragraf)
    metin_yaz(yol_coz(args.cikti), govde)
    print(f"yazildi: {args.cikti} ({len(govde)} karakter)", file=sys.stderr)
    return 0


# --- font-ttx -------------------------------------------------------------------------------


def _fstype_bitleri(deger: int) -> str:
    bitler = format(deger, f"0{FSTYPE_BIT_SAYISI}b")
    return " ".join(bitler[i : i + 8] for i in range(0, FSTYPE_BIT_SAYISI, 8))


def komut_font_ttx(args: argparse.Namespace) -> int:
    kok = ET.fromstring(yol_coz(args.ttx).read_bytes())
    kayitlar: dict[int, list[tuple[str, str]]] = {0: [], 13: [], 14: []}
    for kayit in kok.iter("namerecord"):
        kimlik = int(kayit.attrib["nameID"])
        if kimlik not in kayitlar:
            continue
        etiket = (
            f"platformID={kayit.attrib['platformID']}, platEncID={kayit.attrib['platEncID']}, "
            f"langID={kayit.attrib['langID']}"
        )
        metin = (kayit.text or "").strip(" \n").replace("\r\n", "\n").replace("\r", "\n")
        kayitlar[kimlik].append((etiket, metin))
    fs = kok.find("OS_2/fsType")
    if fs is None:
        print("hata: OS_2/fsType yok", file=sys.stderr)
        return 2
    bitler_metni = fs.attrib["value"]
    deger = int(bitler_metni.replace(" ", ""), 2)
    satirlar: list[str] = []
    for kimlik in (0, 13, 14):
        satirlar.append(f"== name tablosu, nameID {kimlik} ==")
        if not kayitlar[kimlik]:
            satirlar.extend(["(kayit yok)", ""])
            continue
        for etiket, metin in kayitlar[kimlik]:
            satirlar.extend([f"[{etiket}]", metin, ""])
    satirlar.append("== OS/2 tablosu ==")
    satirlar.append(f"OS/2 fsType = {deger}")
    satirlar.append(f"fsType bitleri (bit 15 ... bit 0, ttx cikisi): {_fstype_bitleri(deger)}")
    satirlar.append("Bit anlamlari icin OpenType belirtimi: ")
    satirlar[-1] += "https://learn.microsoft.com/en-us/typography/opentype/spec/os2"
    metin_yaz(yol_coz(args.cikti), "\n".join(satirlar))
    print(f"yazildi: {args.cikti}; fsType={deger}", file=sys.stderr)
    return 0


# --- yaz ------------------------------------------------------------------------------------


def baslik_satirlari(kimlik: str, kaynak_url: str, tarih: str, yontem: str) -> list[str]:
    return [
        f"Kaynak kimliği: {kimlik}",
        f"Kaynak adresi: {kaynak_url}",
        f"Okuma tarihi: {tarih}",
        f"Yöntem: {yontem}",
        NOT_SATIRI_TR,
    ]


def komut_yaz(args: argparse.Namespace) -> int:
    kimlik: str = args.kimlik
    tarih: str = args.tarih
    if KIMLIK_DESENI.fullmatch(kimlik) is None:
        print("hata: gecersiz kimlik", file=sys.stderr)
        return 2
    if TARIH_DESENI.fullmatch(tarih) is None:
        print("hata: tarih YYYY-AA-GG olmali", file=sys.stderr)
        return 2
    try:
        datetime.date.fromisoformat(tarih)
    except ValueError:
        print("hata: tarih gercek bir takvim tarihi olmali", file=sys.stderr)
        return 2
    if "\n" in args.yontem or "\n" in args.kaynak_url:
        print("hata: yontem ve kaynak adresi tek satir olmali", file=sys.stderr)
        return 2
    if (args.govde is None) == (not args.bolum):
        print("hata: --govde ya da --bolum (biri ve yalniz biri) verilmeli", file=sys.stderr)
        return 2
    hedef = KOPYA_DIZINI / f"{kimlik}-{tarih}.txt"
    parcalar: list[str] = []
    if args.govde is not None:
        parcalar.append(metin_oku(yol_coz(args.govde)))
    else:
        for url, dosya in args.bolum:
            govde = metin_oku(yol_coz(dosya))
            parcalar.append(f"### Bölüm kaynağı: {url}\n\n{govde.rstrip(chr(10))}\n")
    metin = "\n".join(baslik_satirlari(kimlik, args.kaynak_url, tarih, args.yontem))
    metin += "\n\n" + "\n".join(parcalar)
    metin_yaz(hedef, metin)
    print(f"yazildi: {hedef}", file=sys.stderr)
    return 0


def kur() -> argparse.ArgumentParser:
    ana = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    alt = ana.add_subparsers(dest="komut", required=True)

    c = alt.add_parser("cikar", help="govde metni cikar")
    c.add_argument("--girdi", required=True)
    c.add_argument("--tur", choices=["html", "ham"], required=True)
    c.add_argument("--baslangic")
    c.add_argument("--bitis")
    c.add_argument("--bitis-son", action="store_true", help="bitis: SON eslesen satir")
    c.add_argument("--paragraf", help="bu ifadeyi iceren paragraf(lar)i sec")
    c.add_argument("--cikti", required=True)
    c.set_defaults(isle=komut_cikar)

    f = alt.add_parser("font-ttx", help="ttx ciktisindan name/OS2 bulgulari")
    f.add_argument("--ttx", required=True)
    f.add_argument("--cikti", required=True)
    f.set_defaults(isle=komut_font_ttx)

    y = alt.add_parser("yaz", help="lisans kopyasini yaz")
    y.add_argument("--kimlik", required=True)
    y.add_argument("--kaynak-url", required=True)
    y.add_argument("--yontem", required=True)
    y.add_argument("--tarih", default="2026-10-26")
    y.add_argument("--govde", help="tek govde dosyasi")
    y.add_argument(
        "--bolum", nargs=2, action="append", metavar=("URL", "DOSYA"), help="adresli bolum"
    )
    y.set_defaults(isle=komut_yaz)
    return ana


def main() -> int:
    args = kur().parse_args()
    try:
        return int(args.isle(args))
    except YolHatasi:
        print("hata: yol proje kokunun disina cikiyor", file=sys.stderr)
        return 2
    except KesmeHatasi as hata:
        print(f"hata: {hata}", file=sys.stderr)
        return 2
    except (OSError, UnicodeDecodeError, ET.ParseError) as hata:
        print(f"hata: {type(hata).__name__}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
