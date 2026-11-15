"""Kelime-Frekans lugat baslik soz listesi (A20.6, K-52 madde 9 ve 10): gelen -> raw -> staged.

`alitekdemir/Risale-i-Nur-Kelime-Frekans` deposunun sabit commit zip'i (`data/gelen/
risale-kelime-frekans/<tarih>/`) DISKE ACILMAZ; uyeler `ingest/risale_zip.py` ile bellekte okunur
(yol ve boyut denetimi, hicbir uye calistirilmaz). Kullanilan uyeler:

* `data/eRisale/analysis/terkipsiz/<ad>_frekans.txt` (`kelime,frekans`): baslik soz ve siklik.
  20 dosya vardir; hangilerinin KITAP, hangilerinin ALT KUME oldugu OLCUYLE belirlenir
  (`siniflandir`): sozleri baska bir dosyanin sozlerinin alt kumesi ve her sozun sikligi o
  dosyadakinden kucuk ya da esit olan dosya alt kumedir (cift sayilmaz). Gercek zipte 15 kitap
  ve 5 Soz alt kumesi cikar.
* `data/eRisale/raw/<ad>.csv` (`"kelime","anlam"`): YALNIZ `anlam` sutunu editor basvurusudur
  (K-52 madde 10): `onerilen_basvuru`ya gider; madde sutunlarina, `kaynaklar`a ve pakete YAZILMAZ.
  `terkipli/` klasorune ve `SorularlaRisale/` agacina dokunulmaz (karar bekler).

Cikti `staged/risale-kelime-frekans/<run_id>/lugat.jsonl` (alanlar `ingest/lugat_madde.py`'de;
`basliksoz`a gore sirali) ve manifest. Baslik soz kaynaktaki yazimiyla bayt bayt saklanir (NFC
YOK). Harf ya da rakami olmayan jetonlar (noktalama) baslik soz sayilmaz ve elenir (sayisi
kilitte). Sozluk OCR isabeti (`ingest/sozluk_ocr.py`) `kaynaklar.sozluk_isabet`e yazilir.

Kilit `kelime_frekans.lock.json` yalniz SAYI ve ozet tasir (metin yok); degisiklik `/karar` ister.
Hata iletileri yalniz sayi ve kisaltilmis dosya adi tasir; dosya icerigi asla.
"""

import csv
import io
import json
import re
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Final

from mutalaa_pipeline import cikis, lineage, sources
from mutalaa_pipeline.export.ortak import GirdiHatasi, kati_json
from mutalaa_pipeline.ingest import sozluk_ocr
from mutalaa_pipeline.ingest.lugat_madde import (
    LUGAT_ADI,
    MADDE_ANAHTARI,
    basliksoz_norm,
    basvuru_nesnesi,
    duzey_hesapla,
    madde_satiri,
)
from mutalaa_pipeline.ingest.meal_ortak import gelen_dizini, gelen_tarihi_coz, ham_kopyala
from mutalaa_pipeline.ingest.risale_zip import GuvenliZip
from mutalaa_pipeline.ingest.tanzil import INGEST_ADIMI, tarih_gecerli
from mutalaa_pipeline.komut_ortak import komutu_yurut
from mutalaa_pipeline.lineage import OZET_DESENI, kisa_ozet
from mutalaa_pipeline.runctx import RAPOR_KLASORU, RunContext
from mutalaa_pipeline.staged import dosya_yaz

KAYNAK: Final = "risale-kelime-frekans"
CIKARICI_SURUMU: Final = "kelime-frekans-cikarici-1"
KILIT_YOLU: Final = Path(__file__).with_name("kelime_frekans.lock.json")
KILIT_SURUMU: Final = 1
EN_BUYUK_ZIP_BAYT: Final = 64 << 20
OCR_HAM_ADI: Final = "ocr_djvu.txt"
RAPOR_ADI: Final = "lugat-sozluk-isabet.json"
UYARI: Final = "Yeni Kelime-Frekans surumu kilit guncellenerek (/karar) alinir."
COMMIT_DESENI: Final = re.compile(r"[0-9a-f]{40}")
SIKLIK_DESENI: Final = re.compile(r"[0-9]+")
FREKANS_SONEKI: Final = "_frekans.txt"
CSV_SONEKI: Final = ".csv"
FREKANS_BASLIGI: Final = "kelime,frekans"
CSV_BASLIGI: Final = ["kelime", "anlam"]
SAYI_ANAHTARLARI: Final = (
    "frekans_satir",
    "benzersiz_kelime",
    "toplam_frekans",
    "csv_kayit",
    "csv_bozuk",
    "csv_benzersiz_kelime",
)
BIRLESIK_ANAHTARLARI: Final = (
    "benzersiz_kelime",
    "toplam_frekans",
    "elenen_noktalama_soz",
    "elenen_noktalama_siklik",
)
KILIT_ALANLARI: Final = (
    "surum",
    "kaynak",
    "depo_url",
    "url",
    "commit",
    "alinma_tarihi",
    "zip_ad",
    "zip_boyut",
    "zip_sha256",
    "uye_sayisi",
    "dosyalar",
    "birlesik",
    "sozlukler",
)


def veri_surumu(commit: str) -> str:
    return f"{KAYNAK}@{commit}"


def _ad(deger: str) -> str:
    """Iletide kullanilacak kisaltilmis, ASCII dosya adi."""
    kesik = deger if len(deger) <= 40 else deger[:37] + "..."
    return kesik.encode("ascii", "backslashreplace").decode("ascii")


@lru_cache(maxsize=1 << 17)
def _norm(sozcuk: str) -> str:
    return basliksoz_norm(sozcuk)


# --- dosya ayristirma ----------------------------------------------------------------------


def _metin(veri: bytes, etiket: str) -> str:
    if veri.startswith(b"\xef\xbb\xbf") or b"\r" in veri:
        raise GirdiHatasi(f"{_ad(etiket)}: BOM ya da CR var (UTF-8 BOM'suz, LF olmali)")
    try:
        return veri.decode("utf-8")
    except UnicodeDecodeError:
        raise GirdiHatasi(f"{_ad(etiket)}: UTF-8 degil") from None


def frekans_coz(veri: bytes, etiket: str) -> tuple[dict[str, int], int]:
    """`kelime,frekans` dosyasi: (kelime -> toplam siklik, veri satiri sayisi).

    Baslik satiri `kelime,frekans`, LF ile biten satirlar, her satir `kelime,siklik` (siklik
    `[0-9]+`, en az 1), kelimede bosluk ve kontrol karakteri yok. Ayni kelime birden cok satirda
    olursa siklik toplanir (satir sayisi benzersiz sayidan buyuk kalir).
    """
    metin = _metin(veri, etiket)
    if not metin.endswith("\n"):
        raise GirdiHatasi(f"{_ad(etiket)}: son satir LF ile bitmiyor")
    satirlar = metin[:-1].split("\n")
    if satirlar[0] != FREKANS_BASLIGI:
        raise GirdiHatasi(f"{_ad(etiket)}: baslik satiri '{FREKANS_BASLIGI}' degil")
    sonuc: dict[str, int] = {}
    for no, satir in enumerate(satirlar[1:], start=2):
        kelime, ayrac, sayi = satir.rpartition(",")
        if (
            ayrac == ""
            or kelime == ""
            or SIKLIK_DESENI.fullmatch(sayi) is None
            or int(sayi) < 1
            or any(h.isspace() or ord(h) < 0x20 or 0x7F <= ord(h) <= 0x9F for h in kelime)
        ):
            raise GirdiHatasi(f"{_ad(etiket)}: satir {no}: gecersiz kelime,frekans satiri")
        sonuc[kelime] = sonuc.get(kelime, 0) + int(sayi)
    return sonuc, len(satirlar) - 1


def csv_coz(veri: bytes, etiket: str) -> tuple[Counter[tuple[str, str]], int]:
    """`"kelime","anlam"` CSV: ((kelime, anlam) -> sayi, bozuk satir sayisi).

    Bozuk: iki sutunlu olmayan, kelimesi ya da anlami bos satir (atlanir ve sayilir). Bos satir
    bozuk sayilmaz. Dosya metni (anlam dahil) dondurulur ama HICBIR yere yazilmaz, yalniz
    `onerilen_basvuru` icin toplanir.
    """
    metin = _metin(veri, etiket)
    try:
        satirlar = list(csv.reader(io.StringIO(metin, newline="")))
    except csv.Error:
        raise GirdiHatasi(f"{_ad(etiket)}: CSV ayristirilamadi") from None
    if not satirlar or satirlar[0] != CSV_BASLIGI:
        raise GirdiHatasi(f"{_ad(etiket)}: baslik satiri 'kelime,anlam' degil")
    sayac: Counter[tuple[str, str]] = Counter()
    bozuk = 0
    for satir in satirlar[1:]:
        if not satir:
            continue
        if len(satir) != 2 or satir[0] == "" or satir[1] == "":
            bozuk += 1
            continue
        sayac[(satir[0], satir[1])] += 1
    return sayac, bozuk


# --- kitap ve alt kume ayrimi ----------------------------------------------------------------


def siniflandir(frekans: Mapping[str, Mapping[str, int]]) -> dict[str, str | None]:
    """Dosya -> ust kitap (alt kume) ya da None (kitap); OLCUYLE.

    A dosyasi, B'nin ALT KUMESIDIR: B'de A'dan fazla soz var, A'nin her sozu B'de var ve A'daki
    siklik B'dekinden buyuk degil. Birden cok ust varsa en cok sozlusu ust kitaptir (altkumeler
    gecis iliskisiyle zincirlenir; en buyuk ust daima kitaptir).
    """
    sonuc: dict[str, str | None] = {}
    for ad, a in frekans.items():
        ustler = [
            b_ad
            for b_ad, b in frekans.items()
            if b_ad != ad and len(b) > len(a) and all(k in b and v <= b[k] for k, v in a.items())
        ]
        sonuc[ad] = max(ustler, key=lambda u: (len(frekans[u]), u)) if ustler else None
    return sonuc


# --- kilit -----------------------------------------------------------------------------------


@dataclass(frozen=True)
class DosyaKilidi:
    """Bir frekans dosyasi (ve ayni adli CSV): ozetler ve sayilar; `ust` None ise kitaptir."""

    ust: str | None
    frekans_sha256: str
    csv_sha256: str
    sayilar: Mapping[str, int]

    def sozluk(self) -> dict[str, object]:
        return {
            "ust": self.ust,
            "frekans_sha256": self.frekans_sha256,
            "csv_sha256": self.csv_sha256,
            "sayilar": dict(self.sayilar),
        }


@dataclass(frozen=True)
class OcrKilidi:
    boyut: int
    sha256: str
    satir: int

    def sozluk(self) -> dict[str, object]:
        return {"boyut": self.boyut, "sha256": self.sha256, "satir": self.satir}


@dataclass(frozen=True)
class KelimeFrekansKilidi:
    """`kelime_frekans.lock.json`: zip ve kullanilan uyelerin sabit kimligi (sayi ve ozet)."""

    depo_url: str
    url: str
    commit: str
    alinma_tarihi: str
    zip_ad: str
    zip_boyut: int
    zip_sha256: str
    uye_sayisi: int
    dosyalar: Mapping[str, DosyaKilidi]
    birlesik: Mapping[str, int]
    sozlukler: Mapping[str, OcrKilidi]

    @property
    def kok(self) -> str:
        return f"Risale-i-Nur-Kelime-Frekans-{self.commit}"

    @property
    def kitaplar(self) -> list[str]:
        return sorted(ad for ad, d in self.dosyalar.items() if d.ust is None)

    def sozluk(self) -> dict[str, object]:
        return {
            "surum": KILIT_SURUMU,
            "kaynak": KAYNAK,
            "depo_url": self.depo_url,
            "url": self.url,
            "commit": self.commit,
            "alinma_tarihi": self.alinma_tarihi,
            "zip_ad": self.zip_ad,
            "zip_boyut": self.zip_boyut,
            "zip_sha256": self.zip_sha256,
            "uye_sayisi": self.uye_sayisi,
            "dosyalar": {ad: d.sozluk() for ad, d in sorted(self.dosyalar.items())},
            "birlesik": dict(self.birlesik),
            "sozlukler": {ad: o.sozluk() for ad, o in sorted(self.sozlukler.items())},
        }


def _kh(mesaj: str) -> GirdiHatasi:
    return GirdiHatasi(f"kelime_frekans.lock.json: {mesaj}")


def _tam(deger: object, yer: str) -> int:
    if type(deger) is not int or deger < 0:
        raise _kh(f"{yer} negatif olmayan tam sayi olmali")
    return deger


def _ozet(deger: object, yer: str) -> str:
    if not isinstance(deger, str) or OZET_DESENI.fullmatch(deger) is None:
        raise _kh(f"{yer} 64 haneli kucuk harfli onaltilik olmali")
    return deger


def _sayilar(deger: object, anahtarlar: tuple[str, ...], yer: str) -> dict[str, int]:
    if not isinstance(deger, dict) or set(deger) != set(anahtarlar):
        raise _kh(f"{yer} alanlari {', '.join(anahtarlar)} olmali")
    return {a: _tam(deger[a], f"{yer}.{a}") for a in anahtarlar}


def kilit_coz(ham: bytes) -> KelimeFrekansKilidi:
    """Kilit dosyasinin baytlarini kati bicimde cozer; bicim hatasi `GirdiHatasi`."""
    if ham.startswith(b"\xef\xbb\xbf") or b"\r" in ham:
        raise _kh("BOM ya da CR var (UTF-8 BOM'suz, LF olmali)")
    try:
        veri = kati_json(ham.decode("utf-8"))
    except UnicodeDecodeError:
        raise _kh("UTF-8 degil") from None
    except GirdiHatasi as hata:
        raise _kh(str(hata)) from None
    if not isinstance(veri, dict) or set(veri) != set(KILIT_ALANLARI):
        raise _kh(f"alanlar {', '.join(KILIT_ALANLARI)} olmali")
    if veri["surum"] != KILIT_SURUMU or veri["kaynak"] != KAYNAK:
        raise _kh("surum ya da kaynak desteklenmiyor")
    depo_url, url, commit, tarih, zip_ad = (
        veri[a] for a in ("depo_url", "url", "commit", "alinma_tarihi", "zip_ad")
    )
    if not isinstance(depo_url, str) or not depo_url.startswith("https://"):
        raise _kh("depo_url https:// ile baslayan metin olmali")
    if not isinstance(url, str) or not url.startswith("https://"):
        raise _kh("url https:// ile baslayan metin olmali")
    if not isinstance(commit, str) or COMMIT_DESENI.fullmatch(commit) is None:
        raise _kh("commit 40 haneli kucuk harfli onaltilik olmali")
    if not isinstance(tarih, str) or not tarih_gecerli(tarih):
        raise _kh("alinma_tarihi YYYY-AA-GG olmali")
    if zip_ad != f"Risale-i-Nur-Kelime-Frekans-{commit}.zip":
        raise _kh("zip_ad commit ile tutarsiz")
    dosyalar_ham = veri["dosyalar"]
    if not isinstance(dosyalar_ham, dict) or not dosyalar_ham:
        raise _kh("dosyalar bos olmayan nesne olmali")
    dosyalar: dict[str, DosyaKilidi] = {}
    for ad, d in dosyalar_ham.items():
        if not isinstance(d, dict) or set(d) != {"ust", "frekans_sha256", "csv_sha256", "sayilar"}:
            raise _kh("dosyalar ogesi alanlari yanlis")
        ust = d["ust"]
        if ust is not None and (not isinstance(ust, str) or ust not in dosyalar_ham):
            raise _kh("dosyalar.ust bilinen bir kitap adi ya da null olmali")
        dosyalar[ad] = DosyaKilidi(
            ust,
            _ozet(d["frekans_sha256"], "frekans_sha256"),
            _ozet(d["csv_sha256"], "csv_sha256"),
            _sayilar(d["sayilar"], SAYI_ANAHTARLARI, "dosyalar.sayilar"),
        )
    if any(d.ust is not None and dosyalar[d.ust].ust is not None for d in dosyalar.values()):
        raise _kh("alt kumenin ustu kitap olmali")
    sozlukler_ham = veri["sozlukler"]
    if not isinstance(sozlukler_ham, dict) or set(sozlukler_ham) != set(sozluk_ocr.SOZLUKLER):
        raise _kh("sozlukler uc sozluk kimligini tasimali")
    sozlukler: dict[str, OcrKilidi] = {}
    for ad, o in sozlukler_ham.items():
        if not isinstance(o, dict) or set(o) != {"boyut", "sha256", "satir"}:
            raise _kh("sozlukler ogesi alanlari yanlis")
        sozlukler[ad] = OcrKilidi(
            _tam(o["boyut"], "sozluk.boyut"),
            _ozet(o["sha256"], "sozluk.sha256"),
            _tam(o["satir"], "sozluk.satir"),
        )
    return KelimeFrekansKilidi(
        depo_url=depo_url,
        url=url,
        commit=commit,
        alinma_tarihi=tarih,
        zip_ad=zip_ad,
        zip_boyut=_tam(veri["zip_boyut"], "zip_boyut"),
        zip_sha256=_ozet(veri["zip_sha256"], "zip_sha256"),
        uye_sayisi=_tam(veri["uye_sayisi"], "uye_sayisi"),
        dosyalar=dosyalar,
        birlesik=_sayilar(veri["birlesik"], BIRLESIK_ANAHTARLARI, "birlesik"),
        sozlukler=sozlukler,
    )


def kilit_yukle(yol: Path | None = None) -> KelimeFrekansKilidi:
    try:
        ham = (yol if yol is not None else KILIT_YOLU).read_bytes()
    except OSError:
        raise GirdiHatasi("kelime_frekans.lock.json okunamadi") from None
    return kilit_coz(ham)


def kilit_metni(kilit: KelimeFrekansKilidi) -> str:
    return json.dumps(kilit.sozluk(), ensure_ascii=True, indent=1, sort_keys=True) + "\n"


# --- zip okuma -------------------------------------------------------------------------------


@dataclass
class Okuma:
    """Zipten okunan veri: dosya kimlikleri, birlesik siklik ve anlam basvurusu (bellekte)."""

    dosyalar: dict[str, DosyaKilidi]
    toplam: dict[str, int]  # baslik soz (ham yazim) -> toplam siklik (yalniz kitaplar)
    kitap_siklik: dict[str, dict[str, int]]  # baslik soz -> {kitap: siklik}
    basvuru: dict[str, Counter[str]]  # basliksoz_norm -> {anlam dizesi: sayi}
    elenen_soz: int
    elenen_siklik: int

    def birlesik(self) -> dict[str, int]:
        return {
            "benzersiz_kelime": len(self.toplam),
            "toplam_frekans": sum(self.toplam.values()),
            "elenen_noktalama_soz": self.elenen_soz,
            "elenen_noktalama_siklik": self.elenen_siklik,
        }


def _uye_adlari(z: GuvenliZip, kok: str) -> tuple[dict[str, str], dict[str, str]]:
    """`(frekans, csv)`: dosya adi koku -> zip uye adi; iki kume ayni adlari tasimali."""
    frekans_on = f"{kok}/data/eRisale/analysis/terkipsiz/"
    csv_on = f"{kok}/data/eRisale/raw/"
    frekans: dict[str, str] = {}
    csvler: dict[str, str] = {}
    for ad in z.adlar():
        if ad.startswith(frekans_on) and ad.endswith(FREKANS_SONEKI):
            govde = ad[len(frekans_on) : -len(FREKANS_SONEKI)]
            if govde and "/" not in govde:
                frekans[govde] = ad
        elif ad.startswith(csv_on) and ad.endswith(CSV_SONEKI):
            govde = ad[len(csv_on) : -len(CSV_SONEKI)]
            if govde and "/" not in govde:
                csvler[govde] = ad
    if not frekans:
        raise GirdiHatasi(f"{KAYNAK}: zipte terkipsiz frekans dosyasi yok")
    if set(frekans) != set(csvler):
        raise GirdiHatasi(f"{KAYNAK}: frekans ve CSV dosya adlari ayni degil")
    return frekans, csvler


def oku_zip(z: GuvenliZip, commit: str) -> Okuma:
    """Zipten frekans ve CSV dosyalarini okur; kitap/alt kume ayrimini olcer."""
    kok = f"Risale-i-Nur-Kelime-Frekans-{commit}"
    frekans_uyeleri, csv_uyeleri = _uye_adlari(z, kok)
    frekanslar: dict[str, dict[str, int]] = {}
    satir_sayilari: dict[str, int] = {}
    frekans_ozetleri: dict[str, str] = {}
    csv_verileri: dict[str, tuple[Counter[tuple[str, str]], int]] = {}
    csv_ozetleri: dict[str, str] = {}
    for ad in sorted(frekans_uyeleri):
        ham = z.oku(frekans_uyeleri[ad])
        frekanslar[ad], satir_sayilari[ad] = frekans_coz(ham, ad + FREKANS_SONEKI)
        frekans_ozetleri[ad] = lineage.sha256_bayt(ham)
        ham = z.oku(csv_uyeleri[ad])
        csv_verileri[ad] = csv_coz(ham, ad + CSV_SONEKI)
        csv_ozetleri[ad] = lineage.sha256_bayt(ham)
    ustler = siniflandir(frekanslar)
    dosyalar: dict[str, DosyaKilidi] = {}
    for ad in sorted(frekanslar):
        sayac, bozuk = csv_verileri[ad]
        sayilar = {
            "frekans_satir": satir_sayilari[ad],
            "benzersiz_kelime": len(frekanslar[ad]),
            "toplam_frekans": sum(frekanslar[ad].values()),
            "csv_kayit": sum(sayac.values()),
            "csv_bozuk": bozuk,
            "csv_benzersiz_kelime": len({k for k, _ in sayac}),
        }
        dosyalar[ad] = DosyaKilidi(ustler[ad], frekans_ozetleri[ad], csv_ozetleri[ad], sayilar)
    toplam: dict[str, int] = {}
    kitap_siklik: dict[str, dict[str, int]] = {}
    basvuru: dict[str, Counter[str]] = {}
    for ad in sorted(a for a, u in ustler.items() if u is None):
        for kelime, sayi in frekanslar[ad].items():
            toplam[kelime] = toplam.get(kelime, 0) + sayi
            kitap_siklik.setdefault(kelime, {})[ad] = sayi
        for (kelime, anlam), sayi in csv_verileri[ad][0].items():
            norm = _norm(kelime)
            if norm:
                basvuru.setdefault(norm, Counter())[anlam] += sayi
    elenen = [k for k in toplam if _norm(k) == ""]
    return Okuma(
        dosyalar=dosyalar,
        toplam=toplam,
        kitap_siklik=kitap_siklik,
        basvuru=basvuru,
        elenen_soz=len(elenen),
        elenen_siklik=sum(toplam[k] for k in elenen),
    )


def kilit_denetle(kilit: KelimeFrekansKilidi, okuma: Okuma) -> None:
    """Zipten okunan kimlik, ayrim ve sayilar kilitle tutmalidir; aksi halde `GirdiHatasi`."""
    if set(okuma.dosyalar) != set(kilit.dosyalar):
        raise GirdiHatasi(f"{KAYNAK}: dosya adlari kilitle tutmuyor. {UYARI}")
    for ad, bulunan in okuma.dosyalar.items():
        beklenen = kilit.dosyalar[ad]
        if bulunan.ust != beklenen.ust:
            raise GirdiHatasi(f"{KAYNAK}: kitap/alt kume ayrimi kilitle tutmuyor ({_ad(ad)})")
        if (bulunan.frekans_sha256, bulunan.csv_sha256) != (
            beklenen.frekans_sha256,
            beklenen.csv_sha256,
        ):
            raise GirdiHatasi(f"{KAYNAK}: uye ozeti kilitle tutmuyor ({_ad(ad)}). {UYARI}")
        if dict(bulunan.sayilar) != dict(beklenen.sayilar):
            raise GirdiHatasi(f"{KAYNAK}: sayilar kilitle tutmuyor ({_ad(ad)})")
    if okuma.birlesik() != dict(kilit.birlesik):
        raise GirdiHatasi(f"{KAYNAK}: birlesik sayilar kilitle tutmuyor")


def zip_denetle(kilit: KelimeFrekansKilidi, veri: bytes) -> GuvenliZip:
    """Zip boyutu, SHA-256'si ve uye sayisi kilitle tutmalidir."""
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
    return z


def ocr_denetle(kilit: KelimeFrekansKilidi, sozluk: str, veri: bytes) -> None:
    """OCR dosyasinin boyutu, SHA-256'si ve satir sayisi kilitle tutmalidir."""
    beklenen = kilit.sozlukler[sozluk]
    ozet = lineage.sha256_bayt(veri)
    if (ozet, len(veri), sozluk_ocr.satir_sayisi(veri)) != (
        beklenen.sha256,
        beklenen.boyut,
        beklenen.satir,
    ):
        raise GirdiHatasi(f"{sozluk}: OCR dosyasi kilitle tutmuyor. {UYARI}")


def kilit_onerisi(
    zip_verisi: bytes,
    ocr_verileri: Mapping[str, bytes],
    tarih: str,
    depo_url: str,
    url: str,
    commit: str,
) -> KelimeFrekansKilidi:
    """Gelen dosyalardan ilk kilit degerleri (hicbir sey yazmaz)."""
    z = GuvenliZip(zip_verisi)
    okuma = oku_zip(z, commit)
    return KelimeFrekansKilidi(
        depo_url=depo_url,
        url=url,
        commit=commit,
        alinma_tarihi=tarih,
        zip_ad=f"Risale-i-Nur-Kelime-Frekans-{commit}.zip",
        zip_boyut=len(zip_verisi),
        zip_sha256=lineage.sha256_bayt(zip_verisi),
        uye_sayisi=len(z),
        dosyalar=okuma.dosyalar,
        birlesik=okuma.birlesik(),
        sozlukler={
            ad: OcrKilidi(len(v), lineage.sha256_bayt(v), sozluk_ocr.satir_sayisi(v))
            for ad, v in sorted(ocr_verileri.items())
        },
    )


# --- madde satirlari ---------------------------------------------------------------------------


def lugat_satirlari(
    okuma: Okuma,
    indeksler: Sequence[sozluk_ocr.SozlukIndeksi],
    guvenilmez: Sequence[str],
    commit: str,
) -> list[dict[str, object]]:
    """Baslik soz basina bir lugat maddesi (siralamayi `dosya_yaz` yapar)."""
    surum = veri_surumu(commit)
    satirlar: list[dict[str, object]] = []
    for soz, toplam in okuma.toplam.items():
        norm = _norm(soz)
        if norm == "":
            continue
        kitaplar = okuma.kitap_siklik[soz]
        # Ust duzey `siklik` kuyruk siralamasi icindir (sunucu `LugatMaddeText.SiklikKey`).
        kaynaklar: dict[str, object] = {
            "siklik": toplam,
            "kitaplar": dict(sorted(kitaplar.items())),
            "sozluk_isabet": [sozluk_ocr.ara(ix, soz) for ix in indeksler],
            "sozluk_guvenilmez": list(guvenilmez),
        }
        anlamlar = okuma.basvuru.get(norm)
        satirlar.append(
            madde_satiri(
                source_id=KAYNAK,
                basliksoz=soz,
                duzey=duzey_hesapla(toplam),
                kaynaklar=kaynaklar,
                onerilen_basvuru=basvuru_nesnesi(
                    list(anlamlar.items()) if anlamlar else [], toplam, len(kitaplar)
                ),
                data_version=surum,
            )
        )
    return satirlar


# --- gelen klasoru -----------------------------------------------------------------------------


def gelen_zip_oku(gelen: Path, tarih: str, ad: str) -> bytes:
    """Gelen zip'in baytlari; yoksa, okunamiyorsa ya da cok buyukse `GirdiHatasi`."""
    goreli = f"gelen/{KAYNAK}/{tarih}/{_ad(ad)}"
    yol = gelen / tarih / ad
    try:
        if not yol.is_file():
            raise GirdiHatasi(f"{goreli} yok (--gelen-tarih ile baska bir klasor verilebilir)")
        if yol.stat().st_size > EN_BUYUK_ZIP_BAYT:
            raise GirdiHatasi(f"{goreli} cok buyuk (sinir {EN_BUYUK_ZIP_BAYT} bayt)")
        return yol.read_bytes()
    except OSError:
        raise GirdiHatasi(f"{goreli} okunamadi") from None


def gelen_ocr_oku(veri_kok: Path, sozluk: str, istenen: str | None) -> tuple[str, bytes]:
    """Sozlugun `gelen/<sozluk>/<tarih>/` klasorundeki tek `_djvu.txt` dosyasi: (tarih, bayt)."""
    gelen = gelen_dizini(veri_kok, sozluk)
    tarih = gelen_tarihi_coz(gelen, istenen, sozluk)
    klasor = gelen / tarih
    try:
        adaylar = (
            sorted(p for p in klasor.iterdir() if p.is_file() and p.name.endswith("_djvu.txt"))
            if klasor.is_dir()
            else []
        )
        if len(adaylar) != 1:
            raise GirdiHatasi(f"gelen/{sozluk}/{tarih}: tam bir _djvu.txt dosyasi olmali")
        if adaylar[0].stat().st_size > sozluk_ocr.EN_BUYUK_BAYT:
            raise GirdiHatasi(f"gelen/{sozluk}/{tarih}: OCR dosyasi cok buyuk")
        return tarih, adaylar[0].read_bytes()
    except OSError:
        raise GirdiHatasi(f"gelen/{sozluk}/{tarih}: OCR dosyasi okunamadi") from None


# --- calistirma ------------------------------------------------------------------------------


@dataclass(frozen=True)
class LugatSonucu:
    run_id: str
    atlandi: bool
    madde_sayisi: int
    klasor: Path | None
    onceki_run_id: str | None = None


def _siralama(okuma: Okuma) -> list[str]:
    """Olcum icin baslik sozler: siklik azalan, esitlikte alfabetik; noktalama elenmis."""
    soz = [k for k in okuma.toplam if _norm(k)]
    return sorted(soz, key=lambda k: (-okuma.toplam[k], k))


def olcum_raporu_yaz(veri_kok: Path, rapor: Mapping[str, object]) -> Path:
    """`data/reports/a20/lugat-sozluk-isabet.json` (yalniz sayi; zaman damgasi yok)."""
    klasor = veri_kok / RAPOR_KLASORU / "a20"
    klasor.mkdir(parents=True, exist_ok=True)
    hedef = klasor / RAPOR_ADI
    gecici = klasor / (RAPOR_ADI + ".tmp")
    gecici.write_bytes((json.dumps(dict(rapor), indent=1, sort_keys=True) + "\n").encode("utf-8"))
    lineage.atomik_degistir(gecici, hedef)
    return hedef


def run_lugat(
    ctx: RunContext, gelen_tarih: str | None = None, kilit: KelimeFrekansKilidi | None = None
) -> LugatSonucu:
    """Kayitlar, kilit, ham kopya, ayristirma, sozluk aramasi, parmak izi, staged, manifest."""
    kayitlar = ctx.require_sources((KAYNAK, *sozluk_ocr.SOZLUKLER))
    ctx.gunluk.yaz("INFO", "lugat_basla", source_id=KAYNAK)
    kilit = kilit if kilit is not None else kilit_yukle()
    gelen = gelen_dizini(ctx.veri_kok, KAYNAK)
    tarih = gelen_tarihi_coz(gelen, gelen_tarih, KAYNAK)
    zip_verisi = gelen_zip_oku(gelen, tarih, kilit.zip_ad)
    z = zip_denetle(kilit, zip_verisi)
    okuma = oku_zip(z, kilit.commit)
    kilit_denetle(kilit, okuma)  # tutmazsa raw'a hicbir sey yazilmaz
    ocr_tarihleri: dict[str, str] = {}
    ocr_verileri: dict[str, bytes] = {}
    for sozluk in sozluk_ocr.SOZLUKLER:
        ocr_tarihleri[sozluk], ocr_verileri[sozluk] = gelen_ocr_oku(
            ctx.veri_kok, sozluk, gelen_tarih
        )
        ocr_denetle(kilit, sozluk, ocr_verileri[sozluk])

    zip_fetch: dict[str, object] = {
        "kaynak": KAYNAK,
        "alinma_tarihi": tarih,
        "url": kilit.url,
        "commit": kilit.commit,
        "zip": {"ad": kilit.zip_ad, "boyut": len(zip_verisi), "sha256": kilit.zip_sha256},
        "gelen_yol": f"gelen/{KAYNAK}/{tarih}",
    }
    yollar, _ = ham_kopyala(ctx, KAYNAK, tarih, {kilit.zip_ad: zip_verisi}, zip_fetch)
    girdiler = [
        lineage.Girdi(
            yol=lineage.goreli_yol(ctx.veri_kok, yollar[kilit.zip_ad]), sha256=kilit.zip_sha256
        )
    ]
    for sozluk in sozluk_ocr.SOZLUKLER:
        veri = ocr_verileri[sozluk]
        kayit = kayitlar[sozluk]
        ocr_fetch: dict[str, object] = {
            "kaynak": sozluk,
            "alinma_tarihi": ocr_tarihleri[sozluk],
            "url": kayit.kaynak_url,
            "dosya": kilit.sozlukler[sozluk].sozluk(),
            "gelen_yol": f"gelen/{sozluk}/{ocr_tarihleri[sozluk]}",
        }
        ocr_yollari, _ = ham_kopyala(
            ctx, sozluk, ocr_tarihleri[sozluk], {OCR_HAM_ADI: veri}, ocr_fetch
        )
        girdiler.append(
            lineage.Girdi(
                yol=lineage.goreli_yol(ctx.veri_kok, ocr_yollari[OCR_HAM_ADI]),
                sha256=lineage.sha256_bayt(veri),
            )
        )
    parmak = ctx.parmak_izi(girdiler)

    onceki = lineage.son_basarili(ctx.staged_kaynak_dizini(KAYNAK), ctx.adim)
    if lineage.atlanabilir(
        onceki=onceki[2] if onceki else None,
        parmak=parmak,
        git_kirli=ctx.git().kirli,
        force=ctx.force,
        veri_kok=ctx.veri_kok,
    ):
        ctx.gunluk.yaz("INFO", "lugat_atlandi", source_id=KAYNAK)
        ctx.sayi("atlandi", 1)
        return LugatSonucu(ctx.run_id, True, 0, None, onceki[0] if onceki else None)

    indeksler = [sozluk_ocr.indeks_kur(s, ocr_verileri[s]) for s in sozluk_ocr.SOZLUKLER]
    olcumu = sozluk_ocr.olcum(indeksler, _siralama(okuma))
    guvenilmez = sozluk_ocr.guvenilmezler(olcumu)
    satirlar = lugat_satirlari(okuma, indeksler, guvenilmez, kilit.commit)
    tum: dict[str, object] = {
        ix.sozluk: {
            "madde": len(satirlar),
            "bulundu": sum(
                1 for s in satirlar if sozluk_ocr.ara(ix, str(s["basliksoz"]))["bulundu"]
            ),
        }
        for ix in indeksler
    }
    rapor = {**olcumu, "kaynak": KAYNAK, "commit": kilit.commit, "tum_maddeler": tum}
    duzeyler = Counter(int(str(s["duzey"])) for s in satirlar)
    sayilar = {
        "madde": len(satirlar),
        "kitap": len(kilit.kitaplar),
        "alt_kume": len(kilit.dosyalar) - len(kilit.kitaplar),
        "elenen_noktalama_soz": okuma.elenen_soz,
        **{f"duzey_{d}": n for d, n in sorted(duzeyler.items())},
        "basvurulu_madde": sum(1 for s in satirlar if str(s["basliksoz_norm"]) in okuma.basvuru),
    }
    for ad, deger in sayilar.items():
        ctx.sayi(ad, deger)
    ctx.rapor_ek["sozluk_isabet"] = olcumu
    if ctx.dry_run:
        ctx.gunluk.yaz("INFO", "lugat_dry_run", source_id=KAYNAK, sayilar=sayilar)
        return LugatSonucu(ctx.run_id, False, len(satirlar), None)
    klasor = ctx.staged_dizin(KAYNAK)
    klasor.mkdir(parents=True, exist_ok=True)
    cikti = dosya_yaz(ctx, KAYNAK, LUGAT_ADI, satirlar, MADDE_ANAHTARI)
    olcum_raporu_yaz(ctx.veri_kok, rapor)
    ctx.manifest_yaz(
        klasor,
        girdiler=girdiler,
        ciktilar=[cikti],
        parmak=parmak,
        ayrintilar={
            "commit": kilit.commit,
            "gelen_tarih": tarih,
            "kilit": {"zip_sha256": kilit.zip_sha256, "zip_boyut": kilit.zip_boyut},
            "cikarici": CIKARICI_SURUMU,
            "sozluk_yontemi": sozluk_ocr.YONTEM,
            "sozluk_guvenilmez": guvenilmez,
            "sayilar": sayilar,
        },
    )
    ctx.gunluk.yaz("INFO", "lugat_bitti", source_id=KAYNAK, sayilar=sayilar)
    return LugatSonucu(ctx.run_id, False, len(satirlar), klasor)


def kilit_oner_metni(veri_kok: Path, depo_kok: Path, gelen_tarih: str | None) -> str:
    """`--kilit-oner`: gelen dosyalardan hesaplanan kilit (JSON); adres ve surum kayittan."""
    kayit = {s.dosya.removesuffix(".toml"): s for s in sources.yukle(depo_kok)}.get(KAYNAK)
    if kayit is None or kayit.kaynak is None:
        raise GirdiHatasi(f"{KAYNAK}: kaynak kaydi yok ya da gecersiz")
    depo_url, commit = kayit.kaynak.kaynak_url, kayit.kaynak.surum
    if depo_url is None or commit is None or COMMIT_DESENI.fullmatch(commit) is None:
        raise GirdiHatasi(f"{KAYNAK}: kaynak kaydinda kaynak_url ve 40 haneli commit surumu olmali")
    gelen = gelen_dizini(veri_kok, KAYNAK)
    tarih = gelen_tarihi_coz(gelen, gelen_tarih, KAYNAK)
    zip_verisi = gelen_zip_oku(gelen, tarih, f"Risale-i-Nur-Kelime-Frekans-{commit}.zip")
    ocr = {s: gelen_ocr_oku(veri_kok, s, gelen_tarih)[1] for s in sozluk_ocr.SOZLUKLER}
    url = f"{depo_url}/archive/{commit}.zip"
    return kilit_metni(kilit_onerisi(zip_verisi, ocr, tarih, depo_url, url, commit))


def komut_ingest_lugat(
    *,
    gelen_tarih: str | None,
    dry_run: bool,
    force: bool,
    config: Path | None,
    kok: Path | None,
) -> int:
    """`ingest lugat --source risale-kelime-frekans` komutu; cikis kodunu dondurur."""

    def govde(ctx: RunContext) -> int:
        sonuc = run_lugat(ctx, gelen_tarih)
        if sonuc.atlandi:
            ozet = f"atlandi (parmak izi onceki calistirmayla ayni, run {sonuc.onceki_run_id})"
        elif ctx.dry_run:
            ozet = f"{sonuc.madde_sayisi} madde (dry-run, hicbir sey yazilmadi)"
        else:
            ozet = f"{sonuc.madde_sayisi} madde, run {sonuc.run_id}"
        sys.stdout.write(f"ingest {KAYNAK}: {ozet}\n")
        return cikis.BASARILI

    return komutu_yurut(
        komut=f"ingest lugat --source {KAYNAK}",
        adim=INGEST_ADIMI,
        kaynaklar=[KAYNAK, *sozluk_ocr.SOZLUKLER],
        config=config,
        kok=kok,
        govde=govde,
        force=force,
        dry_run=dry_run,
        parametreler={"source": KAYNAK},
    )
