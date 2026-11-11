"""EPUB tanigi (A16.2): `elmalili-meal-epub`, orijinal mealin ikinci tanigi (K-49; yalniz QA).

`mutalaa ingest meal --source elmalili-meal-epub`:

1. `data/gelen/elmalili-meal-epub/<tarih>/meal-i-serif.epub` (archive.org, kilitteki oge) bayt
   olarak okunur ve `elmalili_meal.lock.json` ile karsilastirilir (boyut, SHA-256 ve SHA-1);
   tutmazsa cikis 2. Ham kopya `data/raw`'a alinir. Dosya yalniz VERI olarak okunur: `zipfile`
   ile bellekte (cikarilmaz), uye sayisi ve boyutu sinirli.
2. `OEBPS/text/chapNN.xhtml` uyeleri `html.parser` ile okunur (standart kitaplik; ac-kapa
   etiketleri tabloda olmayan her sey cikis 2). Her `<h2>` bir sure baslar (sure numarasi basligin
   sirasidir; baslik metni ayristirilmaz: 114 baslik beklenir). Sureye ait `<p>` metinleri tek
   U+0020 ile birlestirilir; ayet numarasi metnin SONUNDA `(N)` (ya da `(N-M)`) biciminde gelir.
3. Cikti birimsiz, `(sure, ayet)` anahtarli `staged/elmalili-meal-epub/{run_id}/tanik.jsonl`
   dosyasidir: her satir bir isaretle biten metin parcasidir. Numara boslugu olan yerde
   (`kapsam = [onceki + 1, N]`) parca bu araligin hepsini kapsar: tanik skoru aralik duzeyinde
   hesaplanir (`adimlar/meal.py`). Isaret sirasi artmiyorsa ya da ayet sayisini asiyorsa cikis 2.

Tanik EPUB'da besmele numarasizdir (Fatiha) ve bazi surelerde numara bosluklari vardir; bunlar
tanigin bir ozelligidir, hata degil. Tanik "ozgun baskiya sadakat" degildir (K-49).
"""

import hashlib
import io
import re
import unicodedata
import zipfile
from html.parser import HTMLParser
from typing import Final

from mutalaa_pipeline import lineage
from mutalaa_pipeline.anchor import kanonik_metin
from mutalaa_pipeline.anchor.ayet_sayilari import AYET_SAYILARI
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.ingest import meal_ortak
from mutalaa_pipeline.ingest.base import RawFile
from mutalaa_pipeline.ingest.meal_kaynaklari import BOLUM_EPUB, KAYNAK_EPUB
from mutalaa_pipeline.ingest.meal_kilit import MealKilidi, kilit_ozeti, kilit_yukle
from mutalaa_pipeline.runctx import RunContext

CIKARICI_SURUMU: Final = "1"
KAYNAK: Final = KAYNAK_EPUB
BOLUM_UYE: Final = re.compile(r"OEBPS/text/chap[0-9]{2}\.xhtml")
ISARET: Final = re.compile(r"\(([0-9]{1,3})(?:-([0-9]{1,3}))?\)")
EN_COK_UYE: Final = 64
EN_BUYUK_UYE_BAYT: Final = 4 << 20
# Okunan etiketler; tabloda olmayan etiket cikis 2 verir (kati okuma).
ETIKETLER: Final = frozenset({"html", "head", "meta", "title", "link", "body", "h1", "h2", "p"})
GOVDE_ETIKETLERI: Final = frozenset({"h1", "h2", "p"})


class _Ayristirici(HTMLParser):
    """`<h2>` sure baslatir; `<p>` icindeki metin o surenin akisina eklenir."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.sureler: list[list[str]] = []  # sure basina paragraf metinleri
        self._ici: str | None = None
        self._tampon: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag not in ETIKETLER:
            raise GirdiHatasi("epub: bilinmeyen etiket (kural tablosunda yok)")
        if tag in GOVDE_ETIKETLERI:
            if self._ici is not None:
                raise GirdiHatasi("epub: ic ice govde etiketi")
            self._ici = tag
            self._tampon = []
            if tag == "h2":
                self.sureler.append([])

    def handle_endtag(self, tag: str) -> None:
        if tag not in ETIKETLER:
            raise GirdiHatasi("epub: bilinmeyen etiket (kural tablosunda yok)")
        if tag in GOVDE_ETIKETLERI and self._ici == tag:
            if tag == "p":
                if not self.sureler:
                    raise GirdiHatasi("epub: sure basligindan once paragraf var")
                self.sureler[-1].append("".join(self._tampon))
            self._ici = None
            self._tampon = []

    def handle_data(self, data: str) -> None:
        if self._ici == "p":
            self._tampon.append(data)


def epub_okuma(veri: bytes) -> list[str]:
    """EPUB baytlarindan sure basina metin akisi (sure sirasinda); 114 sure bekler."""
    try:
        arsiv = zipfile.ZipFile(io.BytesIO(veri))
    except zipfile.BadZipFile:
        raise GirdiHatasi("epub: zip degil") from None
    with arsiv:
        uyeler = [bilgi for bilgi in arsiv.infolist() if BOLUM_UYE.fullmatch(bilgi.filename)]
        if len(arsiv.infolist()) > EN_COK_UYE or not uyeler:
            raise GirdiHatasi("epub: uye sayisi beklenen disinda")
        akislar: list[str] = []
        for bilgi in sorted(uyeler, key=lambda b: b.filename):
            if bilgi.file_size > EN_BUYUK_UYE_BAYT:
                raise GirdiHatasi("epub: uye cok buyuk")
            try:
                govde = arsiv.read(bilgi).decode("utf-8")
            except UnicodeDecodeError:
                raise GirdiHatasi("epub: bolum UTF-8 degil") from None
            ayristirici = _Ayristirici()
            ayristirici.feed(govde)
            ayristirici.close()
            for paragraflar in ayristirici.sureler:
                akislar.append(" ".join(paragraflar))
    if len(akislar) != 114:
        raise GirdiHatasi(f"epub: {len(akislar)} sure basligi var; 114 bekleniyor")
    return akislar


def tanik_parcalari(akis: str, sure: int) -> tuple[list[tuple[int, int, int, str]], int, int]:
    """Bir surenin akisindan `(ayet, kapsam_ilk, kapsam_son, ham metin)` parcalari.

    Donus: parcalar, artik uzunluk ve birlestirilen yinelenen isaret sayisi.

    Ayet numarasi parcanin SONUNDAKI `(N)` isaretidir. Isaret sirasi artmali ve ayet sayisini
    asmamalidir; bir onceki isaretle AYNI numarali isaret (tanigin kendi numara yinelemesi) onceki
    parcayla tek U+0020 ile birlestirilir ve sayilir. Son isaretten sonraki artik metin
    (yalniz bosluk degilse) uzunluk olarak doner.
    """
    ayet_sayisi = AYET_SAYILARI[sure - 1]
    parcalar: list[tuple[int, int, int, str]] = []
    onceki = 0
    baslangic = 0
    yinelenen = 0
    for e in ISARET.finditer(akis):
        ilk = int(e.group(1))
        son = int(e.group(2)) if e.group(2) is not None else ilk
        parca = akis[baslangic : e.start()]
        baslangic = e.end()
        if parcalar and ilk == son == onceki:  # ayni numara iki kez: onceki parcaya eklenir
            ayet, lo, hi, metin = parcalar[-1]
            parcalar[-1] = (ayet, lo, hi, metin + " " + parca)
            yinelenen += 1
            continue
        if son < ilk or ilk <= onceki or son > ayet_sayisi:
            raise GirdiHatasi(f"epub: sure {sure}: isaret sirasi ya da araligi gecersiz")
        parcalar.append((son, onceki + 1, son, parca))
        onceki = son
    artik = len(akis[baslangic:].strip(" \t\n"))
    return parcalar, artik, yinelenen


def tanik_cikar(
    akis: str, sure: int
) -> tuple[list[dict[str, object]], list[tuple[int, int]], int, int]:
    """Bir surenin akisindan `tanik.jsonl` satirlari (metin `kanonik_metin` ile), kapsam
    araliklari, artik uzunluk ve birlestirilen yinelenen isaret sayisi (`tanik_parcalari`)."""
    parcalar, artik, yinelenen = tanik_parcalari(akis, sure)
    satirlar: list[dict[str, object]] = [
        {"sure": sure, "ayet": ayet, "kapsam": [ilk, son], "metin": kanonik_metin(ham)}
        for ayet, ilk, son, ham in parcalar
    ]
    return satirlar, [(ilk, son) for _, ilk, son, _ in parcalar], artik, yinelenen


class EpubBagdastirici:
    """Tanik bagdastiricisi: EPUB'i `data/gelen`den alir, `tanik.jsonl` satirlari uretir."""

    source_id = KAYNAK

    def __init__(self, *, gelen_tarih: str | None = None, kilit: MealKilidi | None = None) -> None:
        self._istenen_tarih = gelen_tarih
        self._kilit = (kilit if kilit is not None else kilit_yukle()).tanik_epub
        self._veri: bytes = b""
        self._tarih = ""
        self._kilit_sha = ""
        self._satir = 0
        self._bosluklu_sure = 0
        self._artik = 0
        self._yinelenen = 0

    def fetch(self, ctx: RunContext) -> list[RawFile]:
        tarih, icerik = meal_ortak.gelenleri_oku(
            ctx, KAYNAK, self._istenen_tarih, [self._kilit.dosya]
        )
        veri = icerik[self._kilit.dosya.ad]
        if hashlib.sha1(veri, usedforsecurity=False).hexdigest() != self._kilit.sha1:
            raise GirdiHatasi(f"{KAYNAK}: sha1 kilitle tutmuyor. {meal_ortak.UYARI}")
        epub_okuma(veri)  # bicim hatasi raw'a yazmadan once 2 verir
        ozet = kilit_ozeti(self._kilit.sozluk())
        yollar, yeni = meal_ortak.ham_kopyala(
            ctx,
            KAYNAK,
            tarih,
            icerik,
            meal_ortak.fetch_kaydi(KAYNAK, tarih, self._kilit.url, ozet, [self._kilit.dosya]),
        )
        self._veri, self._tarih, self._kilit_sha = veri, tarih, ozet
        ctx.sayi("ham_dosya", 1)
        ctx.sayi("ham_yeni", 1 if yeni else 0)
        return meal_ortak.raw_dosyalari(ctx, yollar, icerik)

    def tanik_satirlari(self, ctx: RunContext, files: list[RawFile]) -> list[dict[str, object]]:
        if not self._veri:
            raise GirdiHatasi("fetch cagrilmadan tanik_satirlari")
        satirlar: list[dict[str, object]] = []
        for sure, akis in enumerate(epub_okuma(self._veri), start=1):
            sure_satirlari, kapsamlar, artik, yinelenen = tanik_cikar(akis, sure)
            self._artik += artik
            self._yinelenen += yinelenen
            toplam = sum(son - ilk + 1 for ilk, son in kapsamlar)
            if toplam != len({n for ilk, son in kapsamlar for n in range(ilk, son + 1)}):
                raise GirdiHatasi(f"epub: sure {sure}: kapsamlar cakisiyor")
            if toplam != AYET_SAYILARI[sure - 1]:
                self._bosluklu_sure += 1
            satirlar.extend(sure_satirlari)
        self._satir = len(satirlar)
        return satirlar

    def manifest_ayrintilari(self) -> dict[str, object]:
        return {
            "kaynak": KAYNAK,
            "gelen_tarih": self._tarih,
            "kilit_bolumu": BOLUM_EPUB,
            "kilit_sha256": self._kilit_sha,
            "dosya_sha256": lineage.sha256_bayt(self._veri),
            "cikarici_surumu": CIKARICI_SURUMU,
            "unidata": unicodedata.unidata_version,
            "tanik_satiri": self._satir,
            "numara_bosluklu_sure": self._bosluklu_sure,
            "artik_uzunluk": self._artik,
            "yinelenen_isaret": self._yinelenen,
        }


def bagdastirici_olustur(*, gelen_tarih: str | None = None) -> EpubBagdastirici:
    return EpubBagdastirici(gelen_tarih=gelen_tarih)
