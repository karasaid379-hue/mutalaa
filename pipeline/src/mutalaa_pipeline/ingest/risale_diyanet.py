"""Diyanet Risale metni alimi (A20.1, K-51 madde 2 ve 5): zip -> staged (karsilastirma verisi).

`mutalaa ingest risale --source risale-asil-nusha`:

1. `data/gelen/risale-asil-nusha/<YYYY-AA-GG>/` altindaki zip BAYT olarak okunur (diske ACILMAZ;
   `risale_zip.GuvenliZip`) ve `risale.lock.json` ile karsilastirilir: zip boyutu ve SHA-256, uye
   sayisi, kullanilan butun `txt` ve markdown uyelerinin SHA-256'si. Tutmazsa cikis 2 ve "kilit
   guncellenerek (/karar) alinir" uyarisi; `data/raw`'a hicbir sey yazilmaz.
2. Kitap ve bolum kimligi `risale_diyanet_kimlik.json` tablosundadir; dosya adindan slug
   TURETILMEZ. Bolum numarasi kaynakta yoksa doldurulmaz (rapora yazilir).
3. Birim metni `txt` satirlarindan BAYT BAYT gelir: NFC yok; U+00AD, U+200C/D, bosluk turu
   karakterler korunur; dosya basindaki BOM ve satir sonu CR metne girmez (dosya duzeyi sayi olarak
   kilitte). Yapi (baslik duzeyi) ve Arapca isareti markdown'dan gelir (`risale_md`); satirlar
   anahtar esitligiyle hizalanir, hizalanamayan satir tahmin edilmez (`hizalama: "yok"`).
   `***` ayiraclari birim uretmez. Dosya sonundaki `[N] ...` dipnot tanimlari `txt`'den alinir;
   `txt`'de karsiligi olmayan markdown tanimi `provenance.kaynak = "md"` ile alinir.
4. Capalar: `rn:{kitap}[:{bolum}]:p{n}` (`n` dosyadaki birim sirasi, 1'den) ve dipnot icin
   `rn:{kitap}[:{bolum}]:hasiye-{n}:p{m}`. Bu capalar KARSILASTIRMA verisinin adresidir; son
   yapi A20.2b ve RNK metni (K-51 madde 2) ile belirlenir.
5. Ham kopya `data/raw/risale-asil-nusha/<tarih>/` (zip islenmeden, degismez), staged
   `units.jsonl` ve manifest. Hicbir sey veritabanina yazilmaz.

Hata iletileri yalniz sayi, goreli yol ve kisaltilmis ozet tasir; metin asla.
"""

import difflib
import json
import re
import sys
import unicodedata
from collections import Counter
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Final

from mutalaa_pipeline import cikis, lineage, sources
from mutalaa_pipeline.anchor import risale
from mutalaa_pipeline.export.ortak import GirdiHatasi, kati_json
from mutalaa_pipeline.ingest import meal_ortak
from mutalaa_pipeline.ingest.base import RawFile, StagedUnit, run_ingest
from mutalaa_pipeline.ingest.risale_md import MdBelge, MdSatir, anahtar_uret, md_coz
from mutalaa_pipeline.ingest.risale_zip import GuvenliZip
from mutalaa_pipeline.ingest.tanzil import INGEST_ADIMI, tarih_gecerli
from mutalaa_pipeline.komut_ortak import komutu_yurut
from mutalaa_pipeline.lineage import OZET_DESENI, kisa_ozet
from mutalaa_pipeline.runctx import RunContext

KAYNAK: Final = "risale-asil-nusha"
CIKARICI_SURUMU: Final = "risale-diyanet-cikarici-1"
KILIT_YOLU: Final = Path(__file__).with_name("risale.lock.json")
KIMLIK_YOLU: Final = Path(__file__).with_name("risale_diyanet_kimlik.json")
KILIT_SURUMU: Final = 1
KIMLIK_SURUMU: Final = 1
EN_BUYUK_ZIP_BAYT: Final = 256 << 20
UYARI: Final = "Yeni Diyanet surumu kilit guncellenerek (/karar) alinir."
DEPO_ONEKI: Final = "https://github.com/alitekdemir/Risale-i-Nur-Diyanet"
COMMIT_DESENI: Final = re.compile(r"[0-9a-f]{40}")

KELIME: Final = re.compile(r"\w+")
DIPNOT_TXT: Final = re.compile(r"\[(?P<e>[^\]\s]+)\] (?P<m>.*)", re.DOTALL)
DIPNOT_ATFI_TXT: Final = re.compile(r"\([^()\[\]\n]{0,20}\[[^\[\]\s]+\]\)")
SIRALI_BOLUM: Final = re.compile(r"(?P<tur>[a-z]+)-(?P<n>[0-9]+)")

# Kitap basina kilitli sayilar (anahtar kumesi sabittir).
SAYI_ANAHTARLARI: Final = (
    "arapca_isareti_md",
    "baslik",
    "baslik_hizalanamayan",
    "birim",
    "bom_dosya",
    "bos_olmayan_satir",
    "crlf_dosya",
    "dipnot_atfi_md",
    "dipnot_atfi_txt",
    "dipnot_birimi_md",
    "dipnot_birimi_txt",
    "dipnot_tanimi_md",
    "dipnot_tanimi_md_kaynakli",
    "dipnot_tanimi_txt",
    "dipnot_tanimi_txt_eslesmeyen",
    "dosya",
    "isaret",
    "isaret_cozulemeyen",
    "kelime_w",
    "md_dosya",
    "md_karsiligi_yok_dosya",
    "nfc_degil_birim",
    "paragraf",
    "yalniz_bosluk_satir",
    "ayirici_satir",
)
# Metinde olduklari gibi kalan, kitap basina SAYISI kilitli karakter siniflari (K-51 madde 5).
KILITLI_KATEGORILER: Final = frozenset({"Cf", "Cc", "Cs", "Co", "Cn", "Zs", "Zl", "Zp"})


# --- kimlik tablosu ------------------------------------------------------------------------


@dataclass(frozen=True)
class KimlikDosya:
    txt: str
    md: str | None
    bolum: str | None


@dataclass(frozen=True)
class KimlikKitap:
    slug: str
    txt_klasor: str
    md_klasor: str | None
    dosyalar: tuple[KimlikDosya, ...]

    def bolum_yolu(self, dosya: KimlikDosya) -> tuple[str, ...]:
        return (self.slug,) if dosya.bolum is None else (self.slug, dosya.bolum)

    def txt_uyesi(self, dosya: KimlikDosya) -> str:
        return f"txt/{self.txt_klasor}/{dosya.txt}"

    def md_uyesi(self, dosya: KimlikDosya) -> str | None:
        if dosya.md is None or self.md_klasor is None:
            return None
        return f"obsidian-markdown/{self.md_klasor}/{dosya.md}"


@dataclass(frozen=True)
class Kimlik:
    kitaplar: tuple[KimlikKitap, ...]
    md_yalniz: Mapping[str, tuple[str, ...]]


def _hata(mesaj: str) -> GirdiHatasi:
    return GirdiHatasi(f"risale_diyanet_kimlik.json: {mesaj}")


def _nesne(deger: object, alanlar: set[str], yer: str) -> dict[str, object]:
    if not isinstance(deger, dict) or set(deger) != alanlar:
        raise _hata(f"{yer}: alanlar {', '.join(sorted(alanlar))} olmali")
    return deger


def _guvenli_ad(deger: object, yer: str, sonek: str | None = None) -> str:
    if not isinstance(deger, str) or not risale.dosya_adi_guvenli_mi(deger):
        raise _hata(f"{yer}: guvenli bir klasor ya da dosya adi olmali")
    if sonek is not None and not deger.endswith(sonek):
        raise _hata(f"{yer}: {sonek} ile bitmeli")
    return deger


def kimlik_coz(ham: bytes) -> Kimlik:
    """Kimlik tablosunu kati bicimde cozer ve dogrular; hata `GirdiHatasi`."""
    if ham.startswith(b"\xef\xbb\xbf") or b"\r" in ham:
        raise _hata("BOM ya da CR var (UTF-8 BOM'suz, LF olmali)")
    try:
        veri = kati_json(ham.decode("utf-8"))
    except UnicodeDecodeError:
        raise _hata("UTF-8 degil") from None
    govde = _nesne(veri, {"surum", "kitaplar", "md_yalniz"}, "tablo")
    if govde["surum"] != KIMLIK_SURUMU:
        raise _hata(f"surum {KIMLIK_SURUMU} olmali")
    liste = govde["kitaplar"]
    if not isinstance(liste, list) or not liste:
        raise _hata("kitaplar bos olmayan liste olmali")
    kitaplar: list[KimlikKitap] = []
    slug_gorulen: set[str] = set()
    txt_gorulen: set[tuple[str, str]] = set()
    for sira, oge in enumerate(liste):
        yer = f"kitaplar[{sira}]"
        k = _nesne(oge, {"slug", "txt_klasor", "md_klasor", "dosyalar"}, yer)
        try:
            slug = risale.kitap_slug_denetle(str(k["slug"]))
        except risale.RisaleHatasi:
            raise _hata(f"{yer}.slug gecersiz") from None
        if slug in slug_gorulen:
            raise _hata(f"{yer}.slug yinelenen")
        slug_gorulen.add(slug)
        txt_klasor = _guvenli_ad(k["txt_klasor"], f"{yer}.txt_klasor")
        md_klasor = None if k["md_klasor"] is None else _guvenli_ad(k["md_klasor"], yer)
        dosyalar_ham = k["dosyalar"]
        if not isinstance(dosyalar_ham, list) or not dosyalar_ham:
            raise _hata(f"{yer}.dosyalar bos olmayan liste olmali")
        dosyalar: list[KimlikDosya] = []
        bolumler: set[str] = set()
        for j, d_ham in enumerate(dosyalar_ham):
            d = _nesne(d_ham, {"txt", "md", "bolum"}, f"{yer}.dosyalar[{j}]")
            txt = _guvenli_ad(d["txt"], f"{yer}.dosyalar[{j}].txt", ".txt")
            md = None if d["md"] is None else _guvenli_ad(d["md"], f"{yer}.md", ".md")
            bolum = d["bolum"]
            if md is not None and md_klasor is None:
                raise _hata(f"{yer}.dosyalar[{j}]: md_klasor olmadan md dosyasi")
            if bolum is None:
                if len(dosyalar_ham) != 1:
                    raise _hata(f"{yer}.dosyalar[{j}]: birden cok dosyali kitapta bolum olmali")
            else:
                try:
                    bolum = risale.bolum_denetle(str(bolum))
                except risale.RisaleHatasi:
                    raise _hata(f"{yer}.dosyalar[{j}].bolum gecersiz") from None
                if bolum in bolumler:
                    raise _hata(f"{yer}.dosyalar[{j}].bolum yinelenen")
                bolumler.add(bolum)
            if (txt_klasor, txt) in txt_gorulen:
                raise _hata(f"{yer}.dosyalar[{j}].txt yinelenen")
            txt_gorulen.add((txt_klasor, txt))
            dosyalar.append(KimlikDosya(txt, md, None if bolum is None else str(bolum)))
        kitaplar.append(KimlikKitap(slug, txt_klasor, md_klasor, tuple(dosyalar)))
    yalniz = govde["md_yalniz"]
    if not isinstance(yalniz, dict):
        raise _hata("md_yalniz nesne olmali")
    md_yalniz: dict[str, tuple[str, ...]] = {}
    for klasor, adlar in yalniz.items():
        if not isinstance(adlar, list) or not all(isinstance(a, str) for a in adlar):
            raise _hata("md_yalniz degerleri metin listesi olmali")
        md_yalniz[klasor] = tuple(adlar)
    return Kimlik(tuple(kitaplar), md_yalniz)


def kimlik_yukle(yol: Path | None = None) -> Kimlik:
    try:
        ham = (yol if yol is not None else KIMLIK_YOLU).read_bytes()
    except OSError:
        raise GirdiHatasi("risale_diyanet_kimlik.json okunamadi") from None
    return kimlik_coz(ham)


# --- kilit ---------------------------------------------------------------------------------


@dataclass(frozen=True)
class KitapKilidi:
    sayilar: Mapping[str, int]
    karakterler: Mapping[str, int]
    uyeler: Mapping[str, str]  # zip kokune gore uye adi -> SHA-256
    dipnot_uyusmazliklari: tuple[tuple[str, int, int], ...]  # (dosya, tanim, atif)


@dataclass(frozen=True)
class RisaleKilidi:
    depo_url: str
    url: str
    commit: str
    alinma_tarihi: str
    kok: str
    zip_ad: str
    zip_boyut: int
    zip_sha256: str
    uye_sayisi: int
    kitaplar: Mapping[str, KitapKilidi]

    def sozluk(self) -> dict[str, object]:
        return {
            "surum": KILIT_SURUMU,
            "kaynak": KAYNAK,
            "depo_url": self.depo_url,
            "url": self.url,
            "commit": self.commit,
            "alinma_tarihi": self.alinma_tarihi,
            "kok": self.kok,
            "zip": {
                "ad": self.zip_ad,
                "boyut": self.zip_boyut,
                "sha256": self.zip_sha256,
                "uye_sayisi": self.uye_sayisi,
            },
            "kitaplar": {
                slug: {
                    "sayilar": dict(k.sayilar),
                    "karakterler": dict(k.karakterler),
                    "uyeler": dict(k.uyeler),
                    "dipnot_uyusmazliklari": [
                        {"dosya": d, "tanim": t, "atif": a} for d, t, a in k.dipnot_uyusmazliklari
                    ],
                }
                for slug, k in self.kitaplar.items()
            },
        }


def _kh(mesaj: str) -> GirdiHatasi:
    return GirdiHatasi(f"risale.lock.json: {mesaj}")


def _sayi_tablosu(deger: object, anahtarlar: tuple[str, ...] | None, yer: str) -> dict[str, int]:
    if not isinstance(deger, dict):
        raise _kh(f"{yer}: nesne olmali")
    if anahtarlar is not None and set(deger) != set(anahtarlar):
        raise _kh(f"{yer}: anahtarlar sabit kumeye uymali")
    for anahtar, sayi in deger.items():
        if type(sayi) is not int or sayi < 0:
            raise _kh(f"{yer}.{anahtar}: sifir ya da pozitif tam sayi olmali")
    return {str(k): int(v) for k, v in deger.items()}


def kilit_coz(ham: bytes) -> RisaleKilidi:
    """Kilit dosyasinin baytlarini kati bicimde cozer; bicim hatasi `GirdiHatasi`."""
    if ham.startswith(b"\xef\xbb\xbf") or b"\r" in ham:
        raise _kh("BOM ya da CR var (UTF-8 BOM'suz, LF olmali)")
    try:
        veri = kati_json(ham.decode("utf-8"))
    except UnicodeDecodeError:
        raise _kh("UTF-8 degil") from None
    except GirdiHatasi as hata:
        raise _kh(str(hata)) from None
    if not isinstance(veri, dict) or set(veri) != {
        "surum",
        "kaynak",
        "depo_url",
        "url",
        "commit",
        "alinma_tarihi",
        "kok",
        "zip",
        "kitaplar",
    }:
        raise _kh("ust alanlar sabit kumeye uymali")
    if veri["surum"] != KILIT_SURUMU or veri["kaynak"] != KAYNAK:
        raise _kh("surum ya da kaynak uymuyor")
    depo, url, commit, tarih, kok = (
        veri[a] for a in ("depo_url", "url", "commit", "alinma_tarihi", "kok")
    )
    if not isinstance(depo, str) or not depo.startswith(DEPO_ONEKI):
        raise _kh("depo_url alitekdemir deposunu gostermeli")
    if not isinstance(url, str) or not url.startswith("https://"):
        raise _kh("url https:// ile baslamali")
    if not isinstance(commit, str) or COMMIT_DESENI.fullmatch(commit) is None:
        raise _kh("commit 40 haneli kucuk harfli onaltilik olmali")
    if not isinstance(tarih, str) or not tarih_gecerli(tarih):
        raise _kh("alinma_tarihi YYYY-AA-GG olmali")
    if kok != f"Risale-i-Nur-Diyanet-{commit}":
        raise _kh("kok Risale-i-Nur-Diyanet-<commit> olmali")
    z = veri["zip"]
    if not isinstance(z, dict) or set(z) != {"ad", "boyut", "sha256", "uye_sayisi"}:
        raise _kh("zip alanlari ad, boyut, sha256, uye_sayisi olmali")
    zip_ad, boyut, ozet, uye = z["ad"], z["boyut"], z["sha256"], z["uye_sayisi"]
    if not isinstance(zip_ad, str) or not risale.dosya_adi_guvenli_mi(zip_ad):
        raise _kh("zip.ad guvenli bir dosya adi olmali")
    if type(boyut) is not int or boyut <= 0 or type(uye) is not int or uye <= 0:
        raise _kh("zip.boyut ve zip.uye_sayisi pozitif tam sayi olmali")
    if not isinstance(ozet, str) or OZET_DESENI.fullmatch(ozet) is None:
        raise _kh("zip.sha256 64 haneli kucuk harfli onaltilik olmali")
    kitaplar_ham = veri["kitaplar"]
    if not isinstance(kitaplar_ham, dict) or not kitaplar_ham:
        raise _kh("kitaplar bos olmayan nesne olmali")
    kitaplar: dict[str, KitapKilidi] = {}
    for slug, k in kitaplar_ham.items():
        if not isinstance(k, dict) or set(k) != {
            "sayilar",
            "karakterler",
            "uyeler",
            "dipnot_uyusmazliklari",
        }:
            raise _kh(f"{slug}: alanlar sabit kumeye uymali")
        uyeler = k["uyeler"]
        if not isinstance(uyeler, dict) or not uyeler:
            raise _kh(f"{slug}.uyeler bos olmayan nesne olmali")
        for ad, o in uyeler.items():
            if not isinstance(o, str) or OZET_DESENI.fullmatch(o) is None:
                raise _kh(f"{slug}.uyeler ozeti gecersiz")
            if not risale.dosya_adi_guvenli_mi(ad.replace("/", "_")):
                raise _kh(f"{slug}.uyeler: guvensiz uye adi")
        uyusmazlik = k["dipnot_uyusmazliklari"]
        if not isinstance(uyusmazlik, list):
            raise _kh(f"{slug}.dipnot_uyusmazliklari liste olmali")
        liste: list[tuple[str, int, int]] = []
        for u in uyusmazlik:
            if not isinstance(u, dict) or set(u) != {"dosya", "tanim", "atif"}:
                raise _kh(f"{slug}.dipnot_uyusmazliklari alanlari dosya, tanim, atif olmali")
            if not isinstance(u["dosya"], str) or type(u["tanim"]) is not int:
                raise _kh(f"{slug}.dipnot_uyusmazliklari tipleri gecersiz")
            if type(u["atif"]) is not int:
                raise _kh(f"{slug}.dipnot_uyusmazliklari tipleri gecersiz")
            liste.append((u["dosya"], u["tanim"], u["atif"]))
        kitaplar[slug] = KitapKilidi(
            sayilar=_sayi_tablosu(k["sayilar"], SAYI_ANAHTARLARI, f"{slug}.sayilar"),
            karakterler=_sayi_tablosu(k["karakterler"], None, f"{slug}.karakterler"),
            uyeler={str(a): str(o) for a, o in uyeler.items()},
            dipnot_uyusmazliklari=tuple(liste),
        )
    return RisaleKilidi(
        depo_url=depo,
        url=url,
        commit=commit,
        alinma_tarihi=tarih,
        kok=kok,
        zip_ad=zip_ad,
        zip_boyut=boyut,
        zip_sha256=ozet,
        uye_sayisi=uye,
        kitaplar=kitaplar,
    )


def kilit_yukle(yol: Path | None = None) -> RisaleKilidi:
    try:
        ham = (yol if yol is not None else KILIT_YOLU).read_bytes()
    except OSError:
        raise GirdiHatasi("risale.lock.json okunamadi") from None
    return kilit_coz(ham)


def kilit_metni(kilit: RisaleKilidi) -> str:
    return json.dumps(kilit.sozluk(), ensure_ascii=True, indent=1, sort_keys=True) + "\n"


# --- txt ayristirma ------------------------------------------------------------------------


@dataclass
class TxtDipnot:
    etiket: str
    satirlar: list[tuple[int, str]]  # (1 tabanli satir no, birim metni); ilki tanim satiri


@dataclass
class TxtBelge:
    govde: list[tuple[int, str]] = field(default_factory=list)  # (satir no, metin)
    dipnotlar: list[TxtDipnot] = field(default_factory=list)
    ayirici: int = 0
    yalniz_bosluk: int = 0
    bos_olmayan: int = 0
    kelime: int = 0
    crlf: int = 0
    bom: bool = False
    atif: int = 0


def txt_coz(metin: str) -> TxtBelge:
    """`txt` dosyasini satirlara ayirir; metin DEGISTIRILMEZ (yalniz BOM ve satir sonu CR atilir).

    `***` satiri ayiractir (birim degil). Ilk `[N] ...` satirindan sonrasi dipnot bolumudur:
    `[N] ` ile baslayan satir yeni tanim, ote satirlar onceki tanimin devamidir.
    """
    belge = TxtBelge(bom=metin.startswith("﻿"))
    if belge.bom:
        metin = metin[1:]
    kuyruk = False
    for no, ham in enumerate(metin.split("\n"), start=1):
        satir = ham
        if satir.endswith("\r"):
            satir = satir[:-1]
            belge.crlf += 1
        belge.kelime += len(KELIME.findall(satir))
        kesik = satir.strip()
        if kesik == "":
            if satir != "":
                belge.yalniz_bosluk += 1
            continue
        belge.bos_olmayan += 1
        if kesik == "***":
            belge.ayirici += 1
            continue
        tanim = DIPNOT_TXT.fullmatch(satir)
        if tanim is not None:
            kuyruk = True
            belge.dipnotlar.append(TxtDipnot(tanim.group("e"), [(no, tanim.group("m"))]))
        elif kuyruk:
            belge.dipnotlar[-1].satirlar.append((no, satir))
        else:
            belge.govde.append((no, satir))
            belge.atif += len(DIPNOT_ATFI_TXT.findall(satir))
    return belge


# --- hizalama ve isaretler -----------------------------------------------------------------


def hizala(
    txt_govde: list[tuple[int, str]], md_govde: tuple[MdSatir, ...]
) -> tuple[dict[int, MdSatir], set[int]]:
    """txt gövde indeksi -> eslesen md satiri, ve eslesen md indeksleri.

    1. Gecis: anahtar esitligiyle sirali hizalama (`difflib`). 2. Gecis: `<br/>` ile bolunmus,
    parcalari eslesmemis bir markdown satiri, txt'de TEK satir olarak durabilir (kaynak tutarsiz):
    parca anahtarlarinin birlesimi eslesmemis bir txt satirinin anahtariysa o satir eslesir.
    """
    # txt'deki "(Hasiye[1])" atfi markdown'da `[^etiket]`tir ve duz metinden atilir: anahtardan da.
    tk = [(i, anahtar_uret(DIPNOT_ATFI_TXT.sub("", m))) for i, (_, m) in enumerate(txt_govde)]
    tk = [(i, k) for i, k in tk if k]
    mk = [(i, s.anahtar) for i, s in enumerate(md_govde) if s.anahtar]
    eslesme = difflib.SequenceMatcher(None, [k for _, k in mk], [k for _, k in tk], autojunk=False)
    sonuc: dict[int, MdSatir] = {}
    eslesen_md: set[int] = set()
    for blok in eslesme.get_matching_blocks():
        for d in range(blok.size):
            sonuc[tk[blok.b + d][0]] = md_govde[mk[blok.a + d][0]]
            eslesen_md.add(mk[blok.a + d][0])
    bos_txt: dict[str, list[int]] = {}
    for i, k in tk:
        if i not in sonuc:
            bos_txt.setdefault(k, []).append(i)
    gruplar: dict[int, list[int]] = {}
    for i, s in enumerate(md_govde):
        if s.grup:
            gruplar.setdefault(s.grup, []).append(i)
    for indeksler in gruplar.values():
        if len(indeksler) < 2 or any(i in eslesen_md for i in indeksler):
            continue
        parcalar = [md_govde[i] for i in indeksler]
        birlesik = "".join(p.anahtar for p in parcalar)
        adaylar = bos_txt.get(birlesik)
        if birlesik == "" or not adaylar:
            continue
        duz = " ".join(p.duz for p in parcalar)
        tam = all(p.tam_arapca for p in parcalar)
        araplar = ((0, len(duz)),) if tam else ()
        sonuc[adaylar.pop(0)] = MdSatir(
            "paragraf", None, duz, birlesik, araplar, (duz,) if tam else (), tam, parcalar[0].grup
        )
        eslesen_md.update(indeksler)
    return sonuc, eslesen_md


def arapca_isaretleri(metin: str, md: MdSatir) -> tuple[list[dict[str, object]], int]:
    """txt satirindaki Arapca araliklari (kod noktasi, yari acik) ve cozulemeyen isaret sayisi."""
    if not md.araplar:
        return [], 0
    if md.tam_arapca:  # hizalama anahtari esit: satirin tamami Arapca
        bas = len(metin) - len(metin.lstrip(" \t"))
        son = len(metin.rstrip(" \t"))
        return ([{"s": bas, "e": son, "t": "ar"}] if son > bas else []), 0
    isaretler: list[dict[str, object]] = []
    imlec = 0
    cozulemeyen = 0
    for parca in md.arapca_metinleri:
        i = metin.find(parca, imlec)
        if i < 0:
            cozulemeyen += 1
            continue
        isaretler.append({"s": i, "e": i + len(parca), "t": "ar"})
        imlec = i + len(parca)
    return isaretler, cozulemeyen


# --- cikarma -------------------------------------------------------------------------------


@dataclass
class Cikarim:
    birimler: list[StagedUnit] = field(default_factory=list)
    sayilar: dict[str, dict[str, int]] = field(default_factory=dict)
    karakterler: dict[str, dict[str, int]] = field(default_factory=dict)
    uyusmazliklar: dict[str, list[tuple[str, int, int]]] = field(default_factory=dict)
    eksik_numaralar: dict[str, list[str]] = field(default_factory=dict)
    md_karsiligi_yok: list[str] = field(default_factory=list)
    kullanilan_uyeler: dict[str, list[str]] = field(default_factory=dict)  # kitap -> uye adlari


def kilitli_karakter_sayilari(sayac: Counter[str]) -> dict[str, int]:
    """Kilitli siniflardaki (Cf, Cc, Cs, Co, Cn, Zl, Zp ve bosluk disi Zs) karakter sayilari."""
    sonuc: dict[str, int] = {}
    for harf, adet in sayac.items():
        if harf != " " and unicodedata.category(harf) in KILITLI_KATEGORILER:
            sonuc[f"U+{ord(harf):04X}"] = adet
    return dict(sorted(sonuc.items()))


def _metin_coz(veri: bytes, ad: str) -> str:
    try:
        return veri.decode("utf-8")
    except UnicodeDecodeError:
        raise GirdiHatasi(f"zip: {ad} UTF-8 degil") from None


def _birim(
    yol: tuple[str, ...],
    p: int,
    metin: str,
    attrs: dict[str, object],
    provenance: dict[str, object],
) -> StagedUnit:
    return StagedUnit(anchor=risale.rn_capa(yol, p), text=metin, attrs=attrs, provenance=provenance)


def _eksik_numaralar(bolumler: list[str]) -> list[str]:
    """Siralamali bolum adlarinda (`soz-10` gibi) atlanan numaralar: `soz-10` yok gibi."""
    tur_sayilari: dict[str, set[int]] = {}
    for ad in bolumler:
        eslesme = SIRALI_BOLUM.fullmatch(ad)
        if eslesme is not None and risale.bolum_kalibi(ad) is not None:
            tur_sayilari.setdefault(eslesme.group("tur"), set()).add(int(eslesme.group("n")))
    eksik: list[str] = []
    for tur, sayilar in sorted(tur_sayilari.items()):
        eksik.extend(f"{tur}-{n}" for n in range(1, max(sayilar) + 1) if n not in sayilar)
    return eksik


def _dipnot_birimleri(
    kok_yol: tuple[str, ...],
    txt_dipnotlar: list[TxtDipnot],
    md: MdBelge | None,
    txt_uyesi: str,
    md_uyesi: str | None,
    commit: str,
    sayac: Counter[str],
) -> list[StagedUnit]:
    """Dipnot birimleri: markdown sirasi esas; `txt`'de karsiligi olmayan tanim `md`'den gelir."""
    sira: list[tuple[str, TxtDipnot | tuple[str, tuple[MdSatir, ...]]]] = []
    kullanilan: set[int] = set()
    if md is not None:
        txt_anahtarlari = [
            anahtar_uret(DIPNOT_ATFI_TXT.sub("", t.satirlar[0][1])) for t in txt_dipnotlar
        ]
        imlec = 0
        for tanim in md.dipnotlar:
            # `txt` tanimi, markdown metninin onune etiket sozcugu ekler ("Hasiye: ..."): son ek.
            anahtar = next((s.anahtar for s in tanim.satirlar if s.anahtar), "")
            adaylar = [*range(imlec, len(txt_dipnotlar)), *range(0, imlec)]
            es = (
                None
                if anahtar == ""
                else next(
                    (
                        i
                        for i in adaylar
                        if i not in kullanilan and txt_anahtarlari[i].endswith(anahtar)
                    ),
                    None,
                )
            )
            if es is not None:
                imlec = es + 1
            if es is None:
                # markdown tanimi bos satirlar icerebilir (metin sonraki satirlarda); bos
                # satir birim olmaz, hic metni olmayan tanim atlanir.
                dolu = tuple(s for s in tanim.satirlar if s.duz.strip() != "")
                if dolu:
                    sira.append(("md", (tanim.etiket, dolu)))
            else:
                kullanilan.add(es)
                sira.append(("txt", txt_dipnotlar[es]))
    artik = [t for i, t in enumerate(txt_dipnotlar) if i not in kullanilan]
    if md is not None:
        sayac["dipnot_tanimi_txt_eslesmeyen"] += len(artik)
    sira.extend(("txt", t) for t in artik)
    birimler: list[StagedUnit] = []
    for n, (kaynak, oge) in enumerate(sira, start=1):
        yol = risale.hasiye_yolu(kok_yol, n)
        if kaynak == "txt" and isinstance(oge, TxtDipnot):
            for m, (no, metin) in enumerate(oge.satirlar, start=1):
                attrs: dict[str, object] = {"rol": "dipnot", "etiket": oge.etiket}
                if m > 1:
                    attrs["devam"] = True
                birimler.append(
                    _birim(
                        yol,
                        m,
                        metin,
                        attrs,
                        {"kaynak": "txt", "dosya": txt_uyesi, "satir": no, "commit": commit},
                    )
                )
            sayac["dipnot_birimi_txt"] += len(oge.satirlar)
        elif not isinstance(oge, TxtDipnot):
            etiket, satirlar = oge
            for m, md_satiri in enumerate(satirlar, start=1):
                attrs = {"rol": "dipnot", "etiket": etiket}
                if m > 1:
                    attrs["devam"] = True
                if md_satiri.araplar:
                    attrs["marks"] = [{"s": s, "e": e, "t": "ar"} for s, e in md_satiri.araplar]
                birimler.append(
                    _birim(
                        yol,
                        m,
                        md_satiri.duz,
                        attrs,
                        {
                            "kaynak": "md",
                            "dosya": md_uyesi or "",
                            "etiket": etiket,
                            "commit": commit,
                        },
                    )
                )
            sayac["dipnot_birimi_md"] += len(satirlar)
            sayac["dipnot_tanimi_md_kaynakli"] += 1
    return birimler


def cikar(z: GuvenliZip, kimlik: Kimlik, kilit: RisaleKilidi) -> Cikarim:
    """Zip'ten (yalniz bellekte) butun kitaplarin birimlerini ve sayilarini cikarir."""
    cikarim = Cikarim()
    kok, commit = kilit.kok, kilit.commit
    for kitap in kimlik.kitaplar:
        sayac: Counter[str] = Counter()
        harfler: Counter[str] = Counter()
        uyusmazlik: list[tuple[str, int, int]] = []
        bolumler: list[str] = []
        uyeler: list[str] = []
        baslangic = len(cikarim.birimler)
        for dosya in kitap.dosyalar:
            txt_uyesi = kitap.txt_uyesi(dosya)
            md_uyesi = kitap.md_uyesi(dosya)
            txt = txt_coz(_metin_coz(z.oku(f"{kok}/{txt_uyesi}"), txt_uyesi))
            uyeler.append(txt_uyesi)
            md: MdBelge | None = None
            if md_uyesi is not None:
                md_metin = _metin_coz(z.oku(f"{kok}/{md_uyesi}"), md_uyesi)
                md = md_coz(md_metin.removeprefix("﻿"))
                uyeler.append(md_uyesi)
                sayac["md_dosya"] += 1
                sayac["dipnot_tanimi_md"] += md.sayilar["dipnot_tanimi"]
                sayac["dipnot_atfi_md"] += md.sayilar["dipnot_atfi"]
                sayac["arapca_isareti_md"] += md.sayilar["arapca_isareti"]
                if md.sayilar["dipnot_tanimi"] != md.sayilar["dipnot_atfi"]:
                    uyusmazlik.append(
                        (txt_uyesi, md.sayilar["dipnot_tanimi"], md.sayilar["dipnot_atfi"])
                    )
            else:
                sayac["md_karsiligi_yok_dosya"] += 1
                cikarim.md_karsiligi_yok.append(f"{kitap.slug}: {txt_uyesi}")
            sayac["dosya"] += 1
            sayac["bom_dosya"] += int(txt.bom)
            sayac["crlf_dosya"] += int(txt.crlf > 0)
            sayac["bos_olmayan_satir"] += txt.bos_olmayan
            sayac["yalniz_bosluk_satir"] += txt.yalniz_bosluk
            sayac["ayirici_satir"] += txt.ayirici
            sayac["kelime_w"] += txt.kelime
            sayac["dipnot_tanimi_txt"] += len(txt.dipnotlar)
            sayac["dipnot_atfi_txt"] += txt.atif
            yol = kitap.bolum_yolu(dosya)
            if dosya.bolum is not None:
                bolumler.append(dosya.bolum)
            eslesme, eslesen = hizala(txt.govde, md.govde) if md is not None else ({}, set())
            if md is not None:
                sayac["baslik_hizalanamayan"] += sum(
                    1 for i, s in enumerate(md.govde) if s.tur == "baslik" and i not in eslesen
                )
            for sira, (no, metin) in enumerate(txt.govde, start=1):
                attrs: dict[str, object] = {"rol": "paragraf", "hizalama": "md-yok"}
                if md is not None:
                    attrs["hizalama"] = "yok"
                    md_satiri = eslesme.get(sira - 1)
                    if md_satiri is not None:
                        attrs["hizalama"] = "md"
                        if md_satiri.tur == "baslik":
                            attrs["rol"] = "baslik"
                            attrs["baslik_duzeyi"] = md_satiri.duzey or 0
                        isaretler, cozulemeyen = arapca_isaretleri(metin, md_satiri)
                        sayac["isaret_cozulemeyen"] += cozulemeyen
                        if isaretler:
                            attrs["marks"] = isaretler
                            sayac["isaret"] += len(isaretler)
                sayac["baslik" if attrs["rol"] == "baslik" else "paragraf"] += 1
                cikarim.birimler.append(
                    _birim(
                        yol,
                        sira,
                        metin,
                        attrs,
                        {"kaynak": "txt", "dosya": txt_uyesi, "satir": no, "commit": commit},
                    )
                )
            cikarim.birimler.extend(
                _dipnot_birimleri(yol, txt.dipnotlar, md, txt_uyesi, md_uyesi, commit, sayac)
            )
        # Kitabin birim metinlerinden karakter ve NFC sayilari (staged'e giren metin)
        kitap_birimleri = cikarim.birimler[baslangic:]
        for b in kitap_birimleri:
            harfler.update(b.text)
            sayac["nfc_degil_birim"] += int(not unicodedata.is_normalized("NFC", b.text))
        sayac["birim"] = len(kitap_birimleri)
        for anahtar in SAYI_ANAHTARLARI:
            sayac.setdefault(anahtar, 0)
        cikarim.sayilar[kitap.slug] = {a: sayac[a] for a in SAYI_ANAHTARLARI}
        cikarim.karakterler[kitap.slug] = kilitli_karakter_sayilari(harfler)
        cikarim.uyusmazliklar[kitap.slug] = uyusmazlik
        cikarim.eksik_numaralar[kitap.slug] = _eksik_numaralar(bolumler)
        cikarim.kullanilan_uyeler[kitap.slug] = uyeler
    return cikarim


# --- gelen klasoru ve kilit denetimi -------------------------------------------------------


def gelen_zip_oku(gelen: Path, tarih: str, ad: str) -> bytes:
    """Gelen zip'in baytlari; yoksa, okunamiyorsa ya da cok buyukse `GirdiHatasi`."""
    goreli = f"gelen/{KAYNAK}/{tarih}/{ad}"
    yol = gelen / tarih / ad
    try:
        if not yol.is_file():
            raise GirdiHatasi(f"{goreli} yok (--gelen-tarih ile baska bir klasor verilebilir)")
        if yol.stat().st_size > EN_BUYUK_ZIP_BAYT:
            raise GirdiHatasi(f"{goreli} cok buyuk (sinir {EN_BUYUK_ZIP_BAYT} bayt)")
        return yol.read_bytes()
    except OSError:
        raise GirdiHatasi(f"{goreli} okunamadi") from None


def zip_denetle(kilit: RisaleKilidi, veri: bytes) -> GuvenliZip:
    """Zip boyutu, SHA-256'si, uye sayisi ve kullanilan uyelerin ozetleri kilitle tutmali."""
    ozet = lineage.sha256_bayt(veri)
    if ozet != kilit.zip_sha256 or len(veri) != kilit.zip_boyut:
        raise GirdiHatasi(
            f"{KAYNAK}: zip ozeti kilitle tutmuyor (beklenen {kisa_ozet(kilit.zip_sha256)},"
            f" bulunan {kisa_ozet(ozet)}; boyut {kilit.zip_boyut}/{len(veri)}). {UYARI}"
        )
    z = GuvenliZip(veri)
    if len(z) != kilit.uye_sayisi:
        raise GirdiHatasi(
            f"{KAYNAK}: zip uye sayisi kilitle tutmuyor ({kilit.uye_sayisi}/{len(z)})"
        )
    for slug, kitap in kilit.kitaplar.items():
        for ad, beklenen in kitap.uyeler.items():
            bulunan = lineage.sha256_bayt(z.oku(f"{kilit.kok}/{ad}"))
            if bulunan != beklenen:
                raise GirdiHatasi(f"{KAYNAK}: {slug}: uye ozeti kilitle tutmuyor ({ad}). {UYARI}")
    return z


def kilit_kimlik_denetle(kilit: RisaleKilidi, kimlik: Kimlik) -> None:
    """Kilitteki kitaplar kimlik tablosuyla ayni kitaplar olmali."""
    if set(kilit.kitaplar) != {k.slug for k in kimlik.kitaplar}:
        raise GirdiHatasi(f"{KAYNAK}: kilit kitaplari kimlik tablosuyla ayni degil")


def kilit_onerisi(
    veri: bytes, tarih: str, depo_url: str, url: str, commit: str, kimlik: Kimlik
) -> RisaleKilidi:
    """Gelen zip'ten ilk kilit degerleri (hicbir sey yazmaz)."""
    kok = f"Risale-i-Nur-Diyanet-{commit}"
    z = GuvenliZip(veri)
    taslak = RisaleKilidi(
        depo_url=depo_url,
        url=url,
        commit=commit,
        alinma_tarihi=tarih,
        kok=kok,
        zip_ad=f"{kok}.zip",
        zip_boyut=len(veri),
        zip_sha256=lineage.sha256_bayt(veri),
        uye_sayisi=len(z),
        kitaplar={},
    )
    cikarim = cikar(z, kimlik, taslak)
    kitaplar: dict[str, KitapKilidi] = {}
    for slug, uyeler in cikarim.kullanilan_uyeler.items():
        kitaplar[slug] = KitapKilidi(
            sayilar=cikarim.sayilar[slug],
            karakterler=cikarim.karakterler[slug],
            uyeler={u: lineage.sha256_bayt(z.oku(f"{kok}/{u}")) for u in sorted(set(uyeler))},
            dipnot_uyusmazliklari=tuple(cikarim.uyusmazliklar[slug]),
        )
    return replace(taslak, kitaplar=kitaplar)


# --- bagdastirici --------------------------------------------------------------------------


class DiyanetBagdastirici:
    """`SourceAdapter`: Diyanet zip'ini `data/gelen`den alir, bellekte okur."""

    source_id = KAYNAK

    def __init__(
        self,
        *,
        gelen_tarih: str | None = None,
        kilit: RisaleKilidi | None = None,
        kimlik: Kimlik | None = None,
    ) -> None:
        self._istenen_tarih = gelen_tarih
        self._kilit = kilit if kilit is not None else kilit_yukle()
        self._kimlik = kimlik if kimlik is not None else kimlik_yukle()
        kilit_kimlik_denetle(self._kilit, self._kimlik)
        self._cikarim: Cikarim | None = None
        self._tarih = ""

    def fetch(self, ctx: RunContext) -> list[RawFile]:
        gelen = meal_ortak.gelen_dizini(ctx.veri_kok, KAYNAK)
        tarih = meal_ortak.gelen_tarihi_coz(gelen, self._istenen_tarih, KAYNAK)
        veri = gelen_zip_oku(gelen, tarih, self._kilit.zip_ad)
        z = zip_denetle(self._kilit, veri)
        self._cikarim = cikar(z, self._kimlik, self._kilit)  # hata raw'a yazmadan once 2 verir
        self._tarih = tarih
        fetch_kaydi: dict[str, object] = {
            "kaynak": KAYNAK,
            "alinma_tarihi": tarih,
            "url": self._kilit.url,
            "commit": self._kilit.commit,
            "zip": {"ad": self._kilit.zip_ad, "boyut": len(veri), "sha256": self._kilit.zip_sha256},
            "gelen_yol": f"gelen/{KAYNAK}/{tarih}",
        }
        yollar, yeni = meal_ortak.ham_kopyala(
            ctx, KAYNAK, tarih, {self._kilit.zip_ad: veri}, fetch_kaydi
        )
        ctx.sayi("ham_dosya", 1)
        ctx.sayi("ham_yeni", 1 if yeni else 0)
        return meal_ortak.raw_dosyalari(ctx, yollar, {self._kilit.zip_ad: veri})

    def parse(self, ctx: RunContext, files: list[RawFile]) -> Iterator[StagedUnit]:
        if self._cikarim is None:
            raise GirdiHatasi("fetch cagrilmadan parse")
        yield from self._cikarim.birimler

    def manifest_ayrintilari(self) -> dict[str, object]:
        c = self._cikarim
        if c is None:
            raise GirdiHatasi("fetch cagrilmadan manifest")
        return {
            "kaynak": KAYNAK,
            "gelen_tarih": self._tarih,
            "commit": self._kilit.commit,
            "kilit_zip_sha256": self._kilit.zip_sha256,
            "cikarici_surumu": CIKARICI_SURUMU,
            "unidata": unicodedata.unidata_version,
            "birim": sum(k["birim"] for k in c.sayilar.values()),
            "kitaplar": c.sayilar,
            "eksik_bolum_numaralari": {k: v for k, v in c.eksik_numaralar.items() if v},
            "md_karsiligi_yok": c.md_karsiligi_yok,
        }


def bagdastirici_olustur(
    *, gelen_tarih: str | None = None, kilit: RisaleKilidi | None = None
) -> DiyanetBagdastirici:
    return DiyanetBagdastirici(gelen_tarih=gelen_tarih, kilit=kilit)


def yeniden_uret(ham_zip: bytes, kilit: RisaleKilidi, kimlik: Kimlik | None = None) -> Cikarim:
    """Ham zip baytlarindan cikarimi yeniden uretir; QA G-BUT yeniden uretilebilirlik."""
    return cikar(GuvenliZip(ham_zip), kimlik if kimlik is not None else kimlik_yukle(), kilit)


# --- komutlar ------------------------------------------------------------------------------


def kilit_oner_metni(veri_kok: Path, depo_kok: Path, gelen_tarih: str | None) -> str:
    """`--kilit-oner`: gelen zip'ten hesaplanan kilit (JSON); adres ve surum kaynak kaydindan."""
    kayit = {s.dosya.removesuffix(".toml"): s for s in sources.yukle(depo_kok)}.get(KAYNAK)
    if kayit is None or kayit.kaynak is None:
        raise GirdiHatasi(f"{KAYNAK}: kaynak kaydi yok ya da gecersiz")
    depo_url, commit = kayit.kaynak.kaynak_url, kayit.kaynak.surum
    if depo_url is None or commit is None or COMMIT_DESENI.fullmatch(commit) is None:
        raise GirdiHatasi(f"{KAYNAK}: kaynak kaydinda kaynak_url ve 40 haneli commit surumu olmali")
    url = f"{depo_url}/archive/{commit}.zip"
    gelen = meal_ortak.gelen_dizini(veri_kok, KAYNAK)
    tarih = meal_ortak.gelen_tarihi_coz(gelen, gelen_tarih, KAYNAK)
    veri = gelen_zip_oku(gelen, tarih, f"Risale-i-Nur-Diyanet-{commit}.zip")
    return kilit_metni(kilit_onerisi(veri, tarih, depo_url, url, commit, kimlik_yukle()))


def komut_ingest_risale(
    *,
    gelen_tarih: str | None,
    dry_run: bool,
    force: bool,
    config: Path | None,
    kok: Path | None,
) -> int:
    """`ingest risale --source risale-asil-nusha` komutu; cikis kodunu dondurur."""

    def govde(ctx: RunContext) -> int:
        sonuc = run_ingest(bagdastirici_olustur(gelen_tarih=gelen_tarih), ctx)
        if sonuc.atlandi:
            ozet = f"atlandi (parmak izi onceki calistirmayla ayni, run {sonuc.onceki_run_id})"
        elif ctx.dry_run:
            ozet = f"{sonuc.birim_sayisi} birim (dry-run, hicbir sey yazilmadi)"
        else:
            ozet = f"{sonuc.birim_sayisi} birim, run {sonuc.run_id}"
        sys.stdout.write(f"ingest {KAYNAK}: {ozet}\n")
        return cikis.BASARILI

    return komutu_yurut(
        komut=f"ingest risale --source {KAYNAK}",
        adim=INGEST_ADIMI,
        kaynaklar=[KAYNAK],
        config=config,
        kok=kok,
        govde=govde,
        force=force,
        dry_run=dry_run,
        parametreler={"source": KAYNAK},
    )
