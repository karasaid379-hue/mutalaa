"""Guncel meal bagdastiricisi (A16.2): `elmalili-sade-meal`, sadelestirilmis metin (K-49 madde 1).

`mutalaa ingest meal --source elmalili-sade-meal`:

1. `data/gelen/elmalili-sade-meal/<tarih>/tur-elmallsadelesti.json` (fawazahmed0/quran-api,
   kilitteki commit) bayt olarak okunur ve `elmalili_meal.lock.json` ile karsilastirilir
   (boyut, SHA-256); tutmazsa cikis 2. Ham kopya `data/raw`'a alinir.
2. JSON kati okunur (`kati_json`: yinelenen anahtar, ondalik sayi, NaN yok). Bicim:
   `{"quran": [{"chapter", "verse", "text"} x 6236]}`; her (sure, ayet) Tanzil sayilariyla
   birebir ve tam bir kez bulunmali, aksi halde cikis 2.
3. Metin ilk kayit adimlarindan (`kanonik_metin`, NFC dahil) BIR KEZ gecer. Kesme isareti
   biciminin (U+00B4 vb.) donusturulmesi bu adimin isi DEGILDIR: oldugu gibi kalir; arama anahtari
   yedi kesme bicimini zaten katlar (K-36). Konum `provenance.konum.json_yolu` (`quran[i]`).

Cikti `meal:elmalili-sade:{sure}:{ayet}` birimleridir (6.236). Hata iletileri metin tasimaz.
"""

import unicodedata
from collections.abc import Iterator, Mapping
from typing import Final

from mutalaa_pipeline import lineage
from mutalaa_pipeline.anchor import AnchorRef, Meal, kanonik_metin
from mutalaa_pipeline.anchor import format as anchor_format
from mutalaa_pipeline.anchor.ayet_sayilari import AYET_SAYILARI
from mutalaa_pipeline.export.ortak import GirdiHatasi, kati_json
from mutalaa_pipeline.ingest import meal_ortak
from mutalaa_pipeline.ingest.base import RawFile, StagedUnit
from mutalaa_pipeline.ingest.meal_kaynaklari import BOLUM_SADE, KAYNAK_SADE, capa_eseri
from mutalaa_pipeline.ingest.meal_kilit import MealKilidi, kilit_ozeti, kilit_yukle
from mutalaa_pipeline.runctx import RunContext

CIKARICI_SURUMU: Final = "1"
KAYNAK: Final = KAYNAK_SADE
ALANLAR: Final = frozenset({"chapter", "verse", "text"})


def metin_cikar(ham: str) -> str:
    """Bir kaydin metni: ilk kayit adimlari (`kanonik_metin`, NFC dahil) bir kez. Kesme isareti
    bicimleri (U+00B4 vb.) donusturulmez; oldugu gibi kalir."""
    return kanonik_metin(ham)


def kayitlari_oku(veri: bytes) -> list[tuple[int, int, str]]:
    """JSON baytlarindan `(sure, ayet, ham metin)` listesi (dosya sirasinda); kati denetim.

    Her (sure, ayet) Tanzil sayilariyla birebir ve tam bir kez bulunmali.
    """
    try:
        belge = kati_json(veri.decode("utf-8"))
    except UnicodeDecodeError:
        raise GirdiHatasi("sade json: UTF-8 degil") from None
    except GirdiHatasi as hata:
        raise GirdiHatasi(f"sade json: {hata}") from None
    if not isinstance(belge, dict) or set(belge) != {"quran"}:
        raise GirdiHatasi("sade json: ust alan yalniz 'quran' olmali")
    liste = belge["quran"]
    if not isinstance(liste, list):
        raise GirdiHatasi("sade json: 'quran' liste degil")
    sonuc: list[tuple[int, int, str]] = []
    gorulen: set[tuple[int, int]] = set()
    for sira, kayit in enumerate(liste):
        yer = f"sade json: quran[{sira}]"
        if not isinstance(kayit, dict) or set(kayit) != ALANLAR:
            raise GirdiHatasi(f"{yer}: alanlar chapter, verse, text olmali")
        sure, ayet, metin = kayit["chapter"], kayit["verse"], kayit["text"]
        if type(sure) is not int or type(ayet) is not int or not isinstance(metin, str):
            raise GirdiHatasi(f"{yer}: chapter ve verse tam sayi, text metin olmali")
        if not 1 <= sure <= 114 or not 1 <= ayet <= AYET_SAYILARI[sure - 1]:
            raise GirdiHatasi(f"{yer}: sure/ayet Tanzil sayisinin disinda")
        if (sure, ayet) in gorulen:
            raise GirdiHatasi(f"{yer}: yinelenen sure/ayet")
        gorulen.add((sure, ayet))
        sonuc.append((sure, ayet, metin))
    if len(gorulen) != sum(AYET_SAYILARI):
        raise GirdiHatasi(f"sade json: {len(gorulen)} ayet var; Tanzil sayisi {sum(AYET_SAYILARI)}")
    return sonuc


class SadeBagdastirici:
    """`SourceAdapter`: fawazahmed0 `tur-elmallsadelesti.json` dosyasini `data/gelen`den alir."""

    source_id = KAYNAK

    def __init__(self, *, gelen_tarih: str | None = None, kilit: MealKilidi | None = None) -> None:
        self._istenen_tarih = gelen_tarih
        self._kilit = (kilit if kilit is not None else kilit_yukle()).sade
        self._veri: bytes = b""
        self._tarih = ""
        self._kilit_sha = ""
        self._birim = 0

    def fetch(self, ctx: RunContext) -> list[RawFile]:
        tarih, icerik = meal_ortak.gelenleri_oku(
            ctx, KAYNAK, self._istenen_tarih, [self._kilit.dosya]
        )
        kayitlari_oku(icerik[self._kilit.dosya.ad])  # bicim hatasi raw'a yazmadan once 2 verir
        ozet = kilit_ozeti(self._kilit.sozluk())
        yollar, yeni = meal_ortak.ham_kopyala(
            ctx,
            KAYNAK,
            tarih,
            icerik,
            meal_ortak.fetch_kaydi(KAYNAK, tarih, self._kilit.url, ozet, [self._kilit.dosya]),
        )
        self._veri = icerik[self._kilit.dosya.ad]
        self._tarih = tarih
        self._kilit_sha = ozet
        ctx.sayi("ham_dosya", 1)
        ctx.sayi("ham_yeni", 1 if yeni else 0)
        return meal_ortak.raw_dosyalari(ctx, yollar, icerik)

    def parse(self, ctx: RunContext, files: list[RawFile]) -> Iterator[StagedUnit]:
        if not self._veri:
            raise GirdiHatasi("fetch cagrilmadan parse")
        eser = capa_eseri(KAYNAK)
        dosya_sha = lineage.sha256_bayt(self._veri)
        for sira, (sure, ayet, ham) in enumerate(kayitlari_oku(self._veri)):
            self._birim += 1
            yield StagedUnit(
                anchor=anchor_format(AnchorRef(Meal(eser, sure, ayet))),
                text=metin_cikar(ham),
                attrs={},
                provenance={
                    "file": self._kilit.dosya.ad,
                    "sha256": dosya_sha,
                    "konum": {"json_yolu": f"quran[{sira}]"},
                    "cikarici": {
                        "surum": CIKARICI_SURUMU,
                        "unidata": unicodedata.unidata_version,
                    },
                },
            )

    def manifest_ayrintilari(self) -> dict[str, object]:
        return {
            "kaynak": KAYNAK,
            "gelen_tarih": self._tarih,
            "kilit_bolumu": BOLUM_SADE,
            "kilit_sha256": self._kilit_sha,
            "commit": self._kilit.commit,
            "cikarici_surumu": CIKARICI_SURUMU,
            "unidata": unicodedata.unidata_version,
            "birim": self._birim,
        }


def bagdastirici_olustur(*, gelen_tarih: str | None = None) -> SadeBagdastirici:
    return SadeBagdastirici(gelen_tarih=gelen_tarih)


def yeniden_uret(
    ham: Mapping[str, bytes], kilit: MealKilidi | None = None
) -> dict[str, tuple[str, dict[str, object]]]:
    """Ham dosya baytlarindan `capa -> (metin, attrs)`; QA G-BUT yeniden uretilebilirlik."""
    sk = (kilit if kilit is not None else kilit_yukle()).sade
    eser = capa_eseri(KAYNAK)
    return {
        anchor_format(AnchorRef(Meal(eser, sure, ayet))): (metin_cikar(metin), {})
        for sure, ayet, metin in kayitlari_oku(ham[sk.dosya.ad])
    }
