"""Sure adi kaynaklari alimi (A11.3): Vikipedi tablosu, yonlendirmeler ve quran-meta `surah.tr`.

`mutalaa ingest sure-adlari`:

1. `data/gelen/sure-adlari-vikipedi/<tarih>/` (Vikipedi `Sureler listesi` vikimetni, Action API
   yonlendirme sayfalari ve `revizyon.json`) ve `data/gelen/quran-meta/<tarih>/` (npm tarball'u)
   dosyalarini bayt olarak okur ve `sure_adlari.lock.json` ile karsilastirir (boyut ve SHA-256).
   Tutmazsa cikis 2; uyari: yeni kaynak kilit guncellenerek (/karar) alinir (K-39 kalibi). Kilit
   `tanzil.lock.json`dan ayridir; orada `varyantlar` ve `ust_veri` bolumleri degismez.
2. Dosyalar `data/raw/sure-adlari-vikipedi/<tarih>/` ve `data/raw/quran-meta/<tarih>/` altina
   `fetch.json` ile kopyalanir (ayni baytlar zaten varsa yeni kopya acilmaz; `data/raw` degismez).
3. Ayristirma yalniz VERI okur, hicbir sey calistirmaz: vikimetin tablosu duzenli ifadeyle, JSON
   `kati_json` ile, `quran-meta` tarball'u `tarfile` ile bellekte (cikarmadan); `surah.tr` dizisi
   satir satir ayristirilir, bicim degisirse acik hata verir.
4. Staged cikti (`staged/sure-adlari-vikipedi/{run_id}/`):
   * `tablo.jsonl`: Vikipedi tablosunun 114 satiri (`no`, `ad` gorunen ad, `baslik` madde basligi,
     `ayas`, `cuz`, `anlam` (vikibaglanti metni cozulmus), `yer`, `inis`, `mukattaa`, `satir`);
   * `yonlendirmeler.jsonl`: yalniz tablo satirlarinin madde basliklarinin yonlendirmeleri,
     `yonlendirme_adi_uygun` suzgecinden gecenler (`no`, `baslik`, `hedef`, `dosya`, `yol`);
   * `quran-meta.jsonl`: `surah.tr` girdileri (`no`, `ad`, `anlam`, `satir`).
   Tablo disindaki yonlendirme sayfalari (bagi grafigin geri kalani) yok sayilir.

Sure adi ELLE yazilmaz: butun adlar bu dosyalardan gelir. Hata iletileri yalniz sayi, ozet ve alan
adi tasir; icerik asla.
"""

import io
import json
import re
import shutil
import sys
import tarfile
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from mutalaa_pipeline import cikis, lineage
from mutalaa_pipeline.export.ortak import GirdiHatasi, kati_json
from mutalaa_pipeline.ingest.tanzil import (
    FETCH_ADI,
    GELEN_KLASORU,
    INGEST_ADIMI,
    SURUM_DESENI,
    TARIH_DESENI,
    _klasoru_tasi,
    _yaz_esitle,
    tarih_gecerli,
)
from mutalaa_pipeline.komut_ortak import komutu_yurut
from mutalaa_pipeline.lineage import OZET_DESENI, kisa_ozet
from mutalaa_pipeline.logs import json_baytlari
from mutalaa_pipeline.runctx import RunContext
from mutalaa_pipeline.staged import dosya_yaz

KAYNAK: Final = "sure-adlari-vikipedi"
QURAN_META: Final = "quran-meta"
KILIT_YOLU: Final = Path(__file__).with_name("sure_adlari.lock.json")
SURE_SAYISI: Final = 114
EN_BUYUK_GELEN_BAYT: Final = 4 << 20
EN_BUYUK_UYE_BAYT: Final = 1 << 20
UYARI: Final = "Yeni sure adi kaynagi kilit guncellenerek (/karar) alinir."

VIKIPEDI_TABLO: Final = "sureler-listesi.wikitext"
VIKIPEDI_REVIZYON: Final = "revizyon.json"
TABLO_ADI: Final = "tablo.jsonl"
YONLENDIRME_ADI: Final = "yonlendirmeler.jsonl"
QURAN_META_ADI: Final = "quran-meta.jsonl"
CIKTI_DOSYALARI: Final = (TABLO_ADI, YONLENDIRME_ADI, QURAN_META_ADI)
QM_UYE: Final = re.compile(r"package/dist/surah\.tr-[A-Za-z0-9_-]+\.js")

HUCRE_SAYISI: Final = 8
SATIR_BASLANGICI: Final = re.compile(r"\| *[0-9]+ *\|\|")
VIKIBAGLANTI: Final = re.compile(r"\[\[([^\[\]|]+)(?:\|([^\[\]]*))?\]\]")
SURE_HUCRESI: Final = re.compile(r"\[\[([^\[\]|]+)\|([^\[\]]+)\]\]")
TAM_SAYI: Final = re.compile(r"[0-9]{1,6}")
QM_GIRDI: Final = re.compile(r'\t(?:\[\]|\[("(?:[^"\\]|\\.)*"), ("(?:[^"\\]|\\.)*")\]),?')
QM_DIZI_BASI: Final = "const surahNamesTr = ["
KESMELER: Final = frozenset({"'", chr(0x2019)})
BASLIK_EN_UZUN: Final = 64


# --- kilit ---------------------------------------------------------------------------------


@dataclass(frozen=True)
class KaynakKilidi:
    """Bir gelen klasorunun kilidi: adres, surum ve dosya boyut/ozetleri."""

    url: str
    surum: str
    alinma_tarihi: str
    dosyalar: Mapping[str, tuple[int, str]]  # ad -> (boyut, sha256)

    def sozluk(self) -> dict[str, object]:
        return {
            "url": self.url,
            "surum": self.surum,
            "alinma_tarihi": self.alinma_tarihi,
            "dosyalar": {
                ad: {"boyut": boyut, "sha256": ozet}
                for ad, (boyut, ozet) in sorted(self.dosyalar.items())
            },
        }


@dataclass(frozen=True)
class SureAdlariKilidi:
    vikipedi: KaynakKilidi
    quran_meta: KaynakKilidi

    def sozluk(self) -> dict[str, object]:
        return {"vikipedi": self.vikipedi.sozluk(), "quran_meta": self.quran_meta.sozluk()}


BEKLENEN_DOSYALAR: Final = {
    "vikipedi": (
        VIKIPEDI_TABLO,
        VIKIPEDI_REVIZYON,
        "yonlendirmeler-01.json",
        "yonlendirmeler-02.json",
    ),
    "quran_meta": ("quran-meta-7.0.0.tgz",),
}
KILIT_ALANLARI: Final = ("url", "surum", "alinma_tarihi", "dosyalar")


def _kaynak_kilidi(bolum: str, nesne: object) -> KaynakKilidi:
    yer = f"sure_adlari.lock.json {bolum}"
    if not isinstance(nesne, dict) or set(nesne) != set(KILIT_ALANLARI):
        raise GirdiHatasi(f"{yer}: alanlar {', '.join(KILIT_ALANLARI)} olmali")
    url, surum, tarih, dosyalar = (nesne[a] for a in KILIT_ALANLARI)
    if not isinstance(url, str) or not url.startswith("https://"):
        raise GirdiHatasi(f"{yer}: url https:// ile baslayan metin olmali")
    if not isinstance(surum, str) or SURUM_DESENI.fullmatch(surum) is None:
        raise GirdiHatasi(f"{yer}: surum sayilardan olusan metin olmali")
    if not isinstance(tarih, str) or not tarih_gecerli(tarih):
        raise GirdiHatasi(f"{yer}: alinma_tarihi YYYY-AA-GG olmali")
    if not isinstance(dosyalar, dict) or set(dosyalar) != set(BEKLENEN_DOSYALAR[bolum]):
        raise GirdiHatasi(f"{yer}: dosyalar {', '.join(BEKLENEN_DOSYALAR[bolum])} olmali")
    sonuc: dict[str, tuple[int, str]] = {}
    for ad, kayit in dosyalar.items():
        if not isinstance(kayit, dict) or set(kayit) != {"boyut", "sha256"}:
            raise GirdiHatasi(f"{yer}: {ad} boyut ve sha256 tasimali")
        boyut, ozet = kayit["boyut"], kayit["sha256"]
        if type(boyut) is not int or boyut <= 0:
            raise GirdiHatasi(f"{yer}: {ad} boyut pozitif tam sayi olmali")
        if not isinstance(ozet, str) or OZET_DESENI.fullmatch(ozet) is None:
            raise GirdiHatasi(f"{yer}: {ad} sha256 64 haneli kucuk harfli onaltilik olmali")
        sonuc[ad] = (boyut, ozet)
    return KaynakKilidi(url=url, surum=surum, alinma_tarihi=tarih, dosyalar=sonuc)


def kilit_coz(ham: bytes) -> SureAdlariKilidi:
    """Kilit dosyasinin baytlarini kati bicimde cozer; bicim hatasi `GirdiHatasi`."""
    if ham.startswith(b"\xef\xbb\xbf") or b"\r" in ham:
        raise GirdiHatasi("sure_adlari.lock.json: BOM ya da CR var (UTF-8 BOM'suz, LF olmali)")
    try:
        veri = kati_json(ham.decode("utf-8"))
    except UnicodeDecodeError:
        raise GirdiHatasi("sure_adlari.lock.json: UTF-8 degil") from None
    except GirdiHatasi as hata:
        raise GirdiHatasi(f"sure_adlari.lock.json: {hata}") from None
    if not isinstance(veri, dict) or set(veri) != {"vikipedi", "quran_meta"}:
        raise GirdiHatasi("sure_adlari.lock.json: ust alanlar 'vikipedi' ve 'quran_meta' olmali")
    return SureAdlariKilidi(
        vikipedi=_kaynak_kilidi("vikipedi", veri["vikipedi"]),
        quran_meta=_kaynak_kilidi("quran_meta", veri["quran_meta"]),
    )


def kilit_yukle(yol: Path | None = None) -> SureAdlariKilidi:
    hedef = yol if yol is not None else KILIT_YOLU
    try:
        ham = hedef.read_bytes()
    except OSError:
        raise GirdiHatasi("sure_adlari.lock.json okunamadi") from None
    return kilit_coz(ham)


def kilit_metni(kilit: SureAdlariKilidi) -> str:
    return json.dumps(kilit.sozluk(), ensure_ascii=True, indent=2) + "\n"


# --- vikimetin tablosu -------------------------------------------------------------------------


@dataclass(frozen=True)
class TabloSatiri:
    no: int
    ad: str
    baslik: str
    ayas: int
    cuz: str
    anlam: str
    yer: str
    inis: int
    mukattaa: str
    satir: int

    def sozluk(self) -> dict[str, object]:
        return {
            "no": self.no,
            "ad": self.ad,
            "baslik": self.baslik,
            "ayas": self.ayas,
            "cuz": self.cuz,
            "anlam": self.anlam,
            "yer": self.yer,
            "inis": self.inis,
            "mukattaa": self.mukattaa,
            "satir": self.satir,
        }


def vikibaglanti_coz(hucre: str) -> str:
    """`[[hedef|gorunen]]` -> gorunen, `[[hedef]]` -> hedef; bosluklar tek U+0020 olur."""

    def degistir(eslesme: "re.Match[str]") -> str:
        gorunen = eslesme.group(2)
        return gorunen if gorunen is not None else eslesme.group(1)

    return " ".join(VIKIBAGLANTI.sub(degistir, hucre).split())


def _hucreler(bloklar: Sequence[str]) -> list[str]:
    """Bir tablo satirinin hucreleri: satir basindaki `|` ve `||` ayirir (`[[a|b]]` bolunmez)."""
    govde = "\n".join(bloklar)
    parcalar = re.split(r"\|\||(?:^|\n)\|", govde)
    return [p.strip() for p in parcalar[1:]]


def tablo_ayristir(metin: str) -> list[TabloSatiri]:
    """Vikipedi `Sureler listesi` vikimetninin tablosundan 114 satir; sapmada `GirdiHatasi`.

    Tek `{|` ... `|}` tablosu aranir. Satirlar `|-` ile ayrilir; veri satiri `| N ||` ile baslar.
    Her satirda tam sekiz hucre (no, sure, ayet, cuz, anlam, iniş yeri, iniş sirasi, mukattaa)
    bulunmalidir. Sure hucresi `[[Madde basligi|Gorunen ad]]` olmalidir. No 1..114 kesintisizdir.
    """
    if "\r" in metin:
        raise GirdiHatasi("vikimetin: CR var (LF bekleniyor)")
    if metin.count("{|") != 1 or metin.count("\n|}") != 1:
        raise GirdiHatasi("vikimetin: tam bir tablo ({| ... |}) bekleniyor")
    satirlar = metin.split("\n")
    bas = next(i for i, s in enumerate(satirlar) if s.startswith("{|"))
    son = next(i for i, s in enumerate(satirlar) if s.startswith("|}"))
    bloklar: list[tuple[int, list[str]]] = []
    for sira in range(bas + 1, son):
        s = satirlar[sira]
        if s.startswith("|-"):
            bloklar.append((sira + 2, []))
        elif bloklar:
            bloklar[-1][1].append(s)
    sonuc: list[TabloSatiri] = []
    for baslangic, govde in bloklar:
        if not govde or SATIR_BASLANGICI.match(govde[0]) is None:
            continue  # baslik satiri
        hucreler = _hucreler(govde)
        yer = f"vikimetin satir {baslangic}"
        if len(hucreler) != HUCRE_SAYISI:
            raise GirdiHatasi(f"{yer}: {len(hucreler)} hucre; {HUCRE_SAYISI} bekleniyor")
        no, sure, ayas, cuz, anlam, yeri, inis, mukattaa = hucreler
        for ad, deger in (("no", no), ("ayet", ayas), ("inis sirasi", inis)):
            if TAM_SAYI.fullmatch(deger) is None:
                raise GirdiHatasi(f"{yer}: {ad} ondalik ASCII tam sayi degil")
        eslesme = SURE_HUCRESI.fullmatch(sure)
        if eslesme is None:
            raise GirdiHatasi(f"{yer}: sure hucresi [[baslik|ad]] biciminde degil")
        baslik, ad = " ".join(eslesme.group(1).split()), " ".join(eslesme.group(2).split())
        if not baslik or not ad:
            raise GirdiHatasi(f"{yer}: baslik ya da ad bos")
        sonuc.append(
            TabloSatiri(
                no=int(no),
                ad=ad,
                baslik=baslik,
                ayas=int(ayas),
                cuz=cuz,
                anlam=vikibaglanti_coz(anlam),
                yer=vikibaglanti_coz(yeri),
                inis=int(inis),
                mukattaa=vikibaglanti_coz(mukattaa),
                satir=baslangic,
            )
        )
    if len(sonuc) != SURE_SAYISI:
        raise GirdiHatasi(f"vikimetin: {len(sonuc)} sure satiri; {SURE_SAYISI} bekleniyor")
    if [s.no for s in sonuc] != list(range(1, SURE_SAYISI + 1)):
        raise GirdiHatasi("vikimetin: sure numaralari 1..114 kesintisiz degil")
    basliklar = [s.baslik for s in sonuc]
    if len(set(basliklar)) != len(basliklar):
        raise GirdiHatasi("vikimetin: iki sure ayni madde basligina baglaniyor")
    return sonuc


# --- yonlendirmeler -----------------------------------------------------------------------------


def yonlendirme_adi_uygun(baslik: str) -> bool:
    """Yonlendirme basligi bir sure ADI yazimi olabilir mi.

    Yalniz harfler (ve birlesen isaretler), U+0020, `-` ve kesme (`'`, U+2019) iceren, bas ve
    sonda bosluksuz, en cok `BASLIK_EN_UZUN` karakterlik basliklar uygundur. Parantez (`Meryem
    (sure)`), virgul ve rakam (`Nisa Suresi, 102`), iki nokta (`Kategori:`), egik cizgi ve her
    turlu noktalama alakasiz sayilir.
    """
    if not baslik or baslik != baslik.strip(" ") or len(baslik) > BASLIK_EN_UZUN:
        return False
    for harf in baslik:
        kategori = unicodedata.category(harf)
        if kategori[0] in ("L", "M"):
            continue
        if harf == " " or harf == "-" or harf in KESMELER:
            continue
        return False
    return any(unicodedata.category(h)[0] == "L" for h in baslik)


@dataclass(frozen=True)
class Yonlendirme:
    no: int
    baslik: str
    hedef: str
    dosya: str
    yol: str

    def sozluk(self) -> dict[str, object]:
        return {
            "no": self.no,
            "baslik": self.baslik,
            "hedef": self.hedef,
            "dosya": self.dosya,
            "yol": self.yol,
        }


def yonlendirmeleri_ayikla(
    dosyalar: Mapping[str, bytes], tablo: Sequence[TabloSatiri]
) -> tuple[list[Yonlendirme], int]:
    """`(uygun yonlendirmeler, suzgecte elenen sayisi)`; yalniz tablo madde basliklari kullanilir.

    Action API `redirects` sayfalari tum baglanti grafigini icerir (tablo disi sayfalar da);
    yalniz basligi tablo satirlarindaki `baslik` olan sayfalarin yonlendirmeleri alinir, ote
    sayfalar yok sayilir. Devam sayfalarindaki (`rdcontinue`) ayni sayfa girdileri birlestirilir;
    ayni baslik bir kez sayilir (ilk dosya kazanir). Hedef sayfa hicbir dosyada yoksa hata.
    """
    hedefler = {s.baslik: s.no for s in tablo}
    gorulen: dict[tuple[int, str], Yonlendirme] = {}
    bulunan: set[str] = set()
    elenen = 0
    for dosya in sorted(dosyalar):
        try:
            veri = kati_json(dosyalar[dosya].decode("utf-8"))
        except UnicodeDecodeError:
            raise GirdiHatasi(f"{dosya}: UTF-8 degil") from None
        sayfalar = veri.get("query", {}).get("pages") if isinstance(veri, dict) else None
        if not isinstance(veri, dict) or not isinstance(sayfalar, list):
            raise GirdiHatasi(f"{dosya}: query.pages listesi yok")
        for i, sayfa in enumerate(sayfalar):
            baslik = sayfa.get("title") if isinstance(sayfa, dict) else None
            if not isinstance(baslik, str):
                raise GirdiHatasi(f"{dosya}: pages[{i}].title metin degil")
            if baslik not in hedefler:
                continue
            bulunan.add(baslik)
            yonlendirmeler = sayfa.get("redirects", [])
            if not isinstance(yonlendirmeler, list):
                raise GirdiHatasi(f"{dosya}: pages[{i}].redirects liste degil")
            for j, kayit in enumerate(yonlendirmeler):
                ad = kayit.get("title") if isinstance(kayit, dict) else None
                if not isinstance(ad, str):
                    raise GirdiHatasi(f"{dosya}: pages[{i}].redirects[{j}].title metin degil")
                if not yonlendirme_adi_uygun(ad):
                    elenen += 1
                    continue
                anahtar = (hedefler[baslik], ad)
                gorulen.setdefault(
                    anahtar,
                    Yonlendirme(hedefler[baslik], ad, baslik, dosya, f"pages[{i}].redirects[{j}]"),
                )
    eksik = sorted(hedefler[b] for b in hedefler if b not in bulunan)
    if eksik:
        raise GirdiHatasi(
            f"yonlendirme dosyalarinda madde yok: {len(eksik)} sure (ilk: {eksik[0]})"
        )
    return sorted(gorulen.values(), key=lambda y: (y.no, y.baslik)), elenen


# --- quran-meta surah.tr -----------------------------------------------------------------------


@dataclass(frozen=True)
class MetaSatiri:
    no: int
    ad: str
    anlam: str
    satir: int

    def sozluk(self) -> dict[str, object]:
        return {"no": self.no, "ad": self.ad, "anlam": self.anlam, "satir": self.satir}


def _js_dizgi(parca: str, yer: str) -> str:
    try:
        deger = kati_json(parca)
    except GirdiHatasi:
        raise GirdiHatasi(f"{yer}: dizgi ayristirilamadi (bicim degismis)") from None
    if not isinstance(deger, str) or deger.strip() == "":
        raise GirdiHatasi(f"{yer}: dizgi bos (bicim degismis)")
    return deger


def quran_meta_ayristir(tgz: bytes) -> list[MetaSatiri]:
    """Tarball'daki `dist/surah.tr-*.js` dosyasinin `surahNamesTr` dizisini ayristirir.

    Tarball bellekte okunur (cikarilmaz, JS calistirilmaz). Dizi `[]`, 114 `["ad", "anlam"]`
    ciftleri ve kapanis `[]` olmalidir; baska bir bicim `GirdiHatasi` verir.
    """
    try:
        with tarfile.open(fileobj=io.BytesIO(tgz), mode="r:gz") as arsiv:
            uyeler = [m for m in arsiv.getmembers() if QM_UYE.fullmatch(m.name) and m.isfile()]
            if len(uyeler) != 1 or uyeler[0].size > EN_BUYUK_UYE_BAYT:
                raise GirdiHatasi("quran-meta: surah.tr uyesi bulunamadi")
            dosya = arsiv.extractfile(uyeler[0])
            if dosya is None:
                raise GirdiHatasi("quran-meta: surah.tr uyesi okunamadi")
            kaynak = dosya.read().decode("utf-8")
    except (tarfile.TarError, OSError, EOFError, UnicodeDecodeError):
        raise GirdiHatasi("quran-meta: tarball okunamadi") from None
    satirlar = kaynak.split("\n")
    bas = next((i for i, s in enumerate(satirlar) if s.strip() == QM_DIZI_BASI), None)
    if bas is None or "\r" in kaynak:
        raise GirdiHatasi("quran-meta: surahNamesTr dizisi bulunamadi (bicim degismis)")
    girdiler: list[tuple[int, str, str] | None] = []
    for sira in range(bas + 1, len(satirlar)):
        s = satirlar[sira]
        if s == "];":
            break
        eslesme = QM_GIRDI.fullmatch(s)
        if eslesme is None:
            raise GirdiHatasi(f"quran-meta: satir {sira + 1} beklenen biciminde degil")
        if eslesme.group(1) is None:
            girdiler.append(None)
        else:
            yer = f"quran-meta satir {sira + 1}"
            girdiler.append(
                (sira + 1, _js_dizgi(eslesme.group(1), yer), _js_dizgi(eslesme.group(2), yer))
            )
    else:
        raise GirdiHatasi("quran-meta: dizi kapanisi bulunamadi (bicim degismis)")
    if len(girdiler) != SURE_SAYISI + 2 or girdiler[0] is not None or girdiler[-1] is not None:
        raise GirdiHatasi(f"quran-meta: {SURE_SAYISI} sure girdisi bekleniyor (bicim degismis)")
    sonuc: list[MetaSatiri] = []
    for no, girdi in enumerate(girdiler[1:-1], start=1):
        if girdi is None:
            raise GirdiHatasi(f"quran-meta: {no}. girdi bos")
        sonuc.append(MetaSatiri(no=no, ad=girdi[1], anlam=girdi[2], satir=girdi[0]))
    return sonuc


# --- vikipedi revizyonu ------------------------------------------------------------


def revizyon_denetle(veri: bytes, kilit: KaynakKilidi, tablo_bayt: int) -> int:
    """`revizyon.json` kilitteki revizyon ve tablo boyutunu dogrulamali; revid doner."""
    try:
        belge: Any = kati_json(veri.decode("utf-8"))
    except UnicodeDecodeError:
        raise GirdiHatasi("revizyon.json: UTF-8 degil") from None
    try:
        sayfa = belge["query"]["pages"][0]["revisions"][0]
        revid, boyut = sayfa["revid"], sayfa["size"]
    except (KeyError, IndexError, TypeError):
        raise GirdiHatasi("revizyon.json: revid ve size bulunamadi") from None
    if type(revid) is not int or str(revid) != kilit.surum:
        raise GirdiHatasi("revizyon.json: revizyon numarasi kilitteki surumle ayni degil")
    if boyut != tablo_bayt:
        raise GirdiHatasi("revizyon.json: size vikimetin dosya boyutuyla ayni degil")
    return revid


# --- gelen klasoru ve ham kopya -----------------------------------------------------------------


def gelen_dizini(veri_kok: Path, slug: str) -> Path:
    return veri_kok / GELEN_KLASORU / slug


def gelen_tarihi_coz(gelen: Path, istenen: str | None) -> str:
    if istenen is not None:
        if not tarih_gecerli(istenen):
            raise GirdiHatasi("--gelen-tarih YYYY-AA-GG biciminde gecerli bir tarih olmali")
        return istenen
    tarihler = (
        sorted(p.name for p in gelen.iterdir() if p.is_dir() and tarih_gecerli(p.name))
        if gelen.is_dir()
        else []
    )
    if not tarihler:
        raise GirdiHatasi(f"{GELEN_KLASORU}/{gelen.name} altinda tarih klasoru yok")
    return tarihler[-1]


def gelen_oku(gelen: Path, tarih: str, kilit: KaynakKilidi) -> dict[str, bytes]:
    """Kilitteki dosyalari okur ve boyut/ozetlerini denetler; uyusmazlik `GirdiHatasi`."""
    sonuc: dict[str, bytes] = {}
    for ad, (boyut, ozet) in sorted(kilit.dosyalar.items()):
        goreli = f"{GELEN_KLASORU}/{gelen.name}/{tarih}/{ad}"
        yol = gelen / tarih / ad
        try:
            if not yol.is_file():
                raise GirdiHatasi(f"{goreli} yok (--gelen-tarih ile baska bir klasor verilebilir)")
            if yol.stat().st_size > EN_BUYUK_GELEN_BAYT:
                raise GirdiHatasi(f"{goreli} cok buyuk (sinir {EN_BUYUK_GELEN_BAYT} bayt)")
            veri = yol.read_bytes()
        except OSError:
            raise GirdiHatasi(f"{goreli} okunamadi") from None
        bulunan = lineage.sha256_bayt(veri)
        if bulunan != ozet or len(veri) != boyut:
            raise GirdiHatasi(
                f"{gelen.name}: {ad} ozeti kilitle tutmuyor (beklenen {kisa_ozet(ozet)},"
                f" bulunan {kisa_ozet(bulunan)}; boyut {boyut}/{len(veri)}). {UYARI}"
            )
        sonuc[ad] = veri
    return sonuc


def _mevcut_ham(kok: Path, dosyalar: Mapping[str, bytes]) -> Path | None:
    """`raw/<kaynak>/` altinda ayni dosya kumesini ayni baytlarla tasiyan klasor (en eski tarih)."""
    if not kok.is_dir():
        return None
    for klasor in sorted(kok.iterdir(), key=lambda yol: yol.name):
        if not klasor.is_dir() or TARIH_DESENI.fullmatch(klasor.name) is None:
            continue
        if all(
            (klasor / ad).is_file() and (klasor / ad).read_bytes() == veri
            for ad, veri in dosyalar.items()
        ):
            return klasor
    return None


def ham_kopyala(
    ctx: RunContext,
    slug: str,
    gelen_klasoru: Path,
    tarih: str,
    dosyalar: Mapping[str, bytes],
    fetch: Mapping[str, object],
) -> Path:
    """Dosyalari `data/raw/<slug>/<tarih>/` altina yazar; ayni baytlar varsa mevcut klasoru doner.

    `--dry-run`da yazmaz (gelen klasorunu doner). Ayni tarih klasoru baska baytlar tasiyorsa
    `data/raw degismez` hatasi. Klasor ya tam gorunur ya hic (gecici klasor + yeniden adlandirma).
    """
    kok = ctx.raw_dizin(slug)
    mevcut = _mevcut_ham(kok, dosyalar)
    if mevcut is not None:
        return mevcut
    hedef = kok / tarih
    if hedef.exists():
        raise GirdiHatasi(
            f"raw/{slug}/{tarih} zaten var ve baska bir dosya tasiyor (data/raw degismez);"
            " yeni bir gelen tarih klasoru kullanin"
        )
    if ctx.dry_run:
        return gelen_klasoru
    gecici = kok / f".{tarih}.gecici-{ctx.run_id}"
    try:
        gecici.mkdir(parents=True)
        for ad, veri in sorted(dosyalar.items()):
            _yaz_esitle(gecici / ad, veri)
        _yaz_esitle(gecici / FETCH_ADI, json_baytlari(dict(fetch)))
        _klasoru_tasi(gecici, hedef)
    except OSError:
        esdeger = _mevcut_ham(kok, dosyalar)
        if esdeger is not None:
            return esdeger
        raise GirdiHatasi(f"raw/{slug}/{tarih} yazilamadi") from None
    finally:
        if gecici.exists():
            shutil.rmtree(gecici, ignore_errors=True)
    return hedef


def _fetch_kaydi(slug: str, kilit: KaynakKilidi, tarih: str) -> dict[str, object]:
    return {
        "kaynak": slug,
        "url": kilit.url,
        "surum": kilit.surum,
        "alinma_tarihi": tarih,
        "dosyalar": {
            ad: {"boyut": boyut, "sha256": ozet}
            for ad, (boyut, ozet) in sorted(kilit.dosyalar.items())
        },
        "gelen_yol": f"{GELEN_KLASORU}/{slug}/{tarih}",
    }


# --- calistirma ----------------------------------------------------------------------------------


@dataclass(frozen=True)
class SureAdlariSonucu:
    run_id: str
    atlandi: bool
    satir_sayisi: int
    klasor: Path | None
    onceki_run_id: str | None = None


def run_sure_adlari(
    ctx: RunContext,
    gelen_tarih: str | None = None,
    kilit: SureAdlariKilidi | None = None,
) -> SureAdlariSonucu:
    """Kayitlar, kilit, ham kopya, parmak izi, ayristirma, staged, manifest (en son)."""
    ctx.require_sources((KAYNAK, QURAN_META))
    ctx.gunluk.yaz("INFO", "sure_adlari_basla", source_id=KAYNAK)
    kilit = kilit if kilit is not None else kilit_yukle()
    girdiler_: dict[str, tuple[Path, str, Mapping[str, bytes], KaynakKilidi]] = {}
    for slug, k in ((KAYNAK, kilit.vikipedi), (QURAN_META, kilit.quran_meta)):
        gelen = gelen_dizini(ctx.veri_kok, slug)
        tarih = gelen_tarihi_coz(gelen, gelen_tarih)
        girdiler_[slug] = (gelen / tarih, tarih, gelen_oku(gelen, tarih, k), k)

    viki = girdiler_[KAYNAK][2]
    tablo = tablo_ayristir(viki[VIKIPEDI_TABLO].decode("utf-8"))
    revizyon = revizyon_denetle(viki[VIKIPEDI_REVIZYON], kilit.vikipedi, len(viki[VIKIPEDI_TABLO]))
    yonlendirmeler, elenen = yonlendirmeleri_ayikla(
        {ad: v for ad, v in viki.items() if ad.startswith("yonlendirmeler-")}, tablo
    )
    meta = quran_meta_ayristir(girdiler_[QURAN_META][2]["quran-meta-7.0.0.tgz"])

    girdiler: list[lineage.Girdi] = []
    for slug, (gelen_yolu, tarih, dosyalar, k) in girdiler_.items():
        klasor_ham = ham_kopyala(
            ctx, slug, gelen_yolu, tarih, dosyalar, _fetch_kaydi(slug, k, tarih)
        )
        for ad in sorted(dosyalar):
            girdiler.append(
                lineage.Girdi(
                    yol=lineage.goreli_yol(ctx.veri_kok, klasor_ham / ad),
                    sha256=lineage.sha256_bayt(dosyalar[ad]),
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
        ctx.gunluk.yaz("INFO", "sure_adlari_atlandi", source_id=KAYNAK)
        ctx.sayi("atlandi", 1)
        return SureAdlariSonucu(ctx.run_id, True, 0, None, onceki[0] if onceki else None)

    ciktilar = [
        dosya_yaz(ctx, KAYNAK, TABLO_ADI, [s.sozluk() for s in tablo], ("no",)),
        dosya_yaz(
            ctx, KAYNAK, YONLENDIRME_ADI, [y.sozluk() for y in yonlendirmeler], ("no", "baslik")
        ),
        dosya_yaz(ctx, KAYNAK, QURAN_META_ADI, [m.sozluk() for m in meta], ("no",)),
    ]
    toplam = sum(c.satir or 0 for c in ciktilar)
    ctx.sayi("tablo", len(tablo))
    ctx.sayi("yonlendirme", len(yonlendirmeler))
    ctx.sayi("yonlendirme_elenen", elenen)
    ctx.sayi("quran_meta", len(meta))
    if ctx.dry_run:
        ctx.gunluk.yaz("INFO", "sure_adlari_dry_run", source_id=KAYNAK)
        return SureAdlariSonucu(ctx.run_id, False, toplam, None)
    klasor = ctx.staged_dizin(KAYNAK)
    ctx.manifest_yaz(
        klasor,
        girdiler=girdiler,
        ciktilar=ciktilar,
        parmak=parmak,
        ayrintilar={
            "vikipedi_revizyon": revizyon,
            "vikipedi_tarih": girdiler_[KAYNAK][1],
            "quran_meta_surum": kilit.quran_meta.surum,
            "quran_meta_tarih": girdiler_[QURAN_META][1],
            "sayilar": {
                "tablo": len(tablo),
                "yonlendirme": len(yonlendirmeler),
                "yonlendirme_elenen": elenen,
                "quran_meta": len(meta),
            },
        },
    )
    ctx.gunluk.yaz("INFO", "sure_adlari_bitti", source_id=KAYNAK)
    return SureAdlariSonucu(ctx.run_id, False, toplam, klasor)


def komut_ingest_sure_adlari(
    *,
    gelen_tarih: str | None,
    dry_run: bool,
    force: bool,
    config: Path | None,
    kok: Path | None,
) -> int:
    """`ingest sure-adlari` komutu; cikis kodunu dondurur."""

    def govde(ctx: RunContext) -> int:
        sonuc = run_sure_adlari(ctx, gelen_tarih)
        if sonuc.atlandi:
            ozet = f"atlandi (parmak izi onceki calistirmayla ayni, run {sonuc.onceki_run_id})"
        elif ctx.dry_run:
            ozet = f"{sonuc.satir_sayisi} satir (dry-run, hicbir sey yazilmadi)"
        else:
            ozet = f"{sonuc.satir_sayisi} satir, run {sonuc.run_id}"
        sys.stdout.write(f"ingest {KAYNAK}: {ozet}\n")
        return cikis.BASARILI

    return komutu_yurut(
        komut="ingest sure-adlari",
        adim=INGEST_ADIMI,
        kaynaklar=[KAYNAK, QURAN_META],
        config=config,
        kok=kok,
        govde=govde,
        force=force,
        dry_run=dry_run,
        parametreler={"source": KAYNAK},
    )
