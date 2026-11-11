# ruff: noqa: RUF001
"""Meal kaynaklari: tek kayit modulu (A16.2, K-49).

Kaynak kimligine bagdastiriciyi, capa eserini, kilit bolumunu, tanik baglantisini ve kapi kumesini
eslestiren TEK yerdir; `cli.py` (ingest, normalize, anchor), `qa/` (kapi kumesi ve `qa run`
yonlendirmesi) ve `export/pg.py` (yukleme yonlendirmesi) bu modulden turer. Modul hafiftir
(yalniz standart kitaplik): `qa` ve `export` paketleri onu ice aktarabilir.

Iki meal birim uretir; ucuncu kaynak yalniz tanikdir (QA; yuklenmez):

    elmalili-meal       Vikikaynak, capa `meal:elmalili:{s}:{a}` (O ailesi, orijinal meal)
    elmalili-sade-meal  fawazahmed0 `tur-elmallsadelesti`, capa `meal:elmalili-sade:{s}:{a}` (S)
    elmalili-meal-epub  archive.org EPUB; birimsiz `tanik.jsonl` (O ailesi, ayri derleme)

Capa adlari baska bir metne verilmez (K-26). "Yeni Elmalili" ailesi (T) alinmaz (K-49 madde 1).
"""

import importlib
from dataclasses import dataclass
from typing import Final

ROL_MEAL: Final = "meal"
ROL_TANIK: Final = "tanik"
KIND: Final = "meal"
ROL_METIN: Final = "govde"  # unit.role
METIN_DURUMU: Final = "taslak"  # K-49 madde 4: hazir metin taslak girer

KAYNAK_ORIJINAL: Final = "elmalili-meal"
KAYNAK_SADE: Final = "elmalili-sade-meal"
KAYNAK_EPUB: Final = "elmalili-meal-epub"

# Kilit bolumleri (`elmalili_meal.lock.json` ust anahtarlari).
BOLUM_VIKIKAYNAK: Final = "vikikaynak"
BOLUM_SADE: Final = "sade"
BOLUM_EPUB: Final = "tanik_epub"

# Meal kaynaklarinin `export pg` icin gecmesi gereken bes kapi (K-49 madde 12; G-MET uygulanmaz).
MEAL_KAPILARI: Final = ("G-KAY", "G-BUT", "G-CAP", "G-NOR", "G-HIZ")

# G-KAY: kaynak kaydinin `atif_metni` bu metinle baslar (K-49 madde 14). G-INC gecince sona
# " Mütâlaa editörlerince denetlenmiştir." eklenir; bu yuzden tam esitlik degil onek denetlenir.
ATIF_ORIJINAL: Final = (
    "Meal: Elmalılı Muhammed Hamdi Yazır, Hak Dini Kur'an Dili, İstanbul 1935–1939."
    " Metin Vikikaynak 'Kur'an' sayfalarından alınmıştır."
)
ATIF_SADE: Final = (
    "Meal: Elmalılı Muhammed Hamdi Yazır, sadeleştirilmiş metin (sadeleştiren belirtilmemiş)."
    " fawazahmed0/quran-api üzerinden alınmıştır."
)
DENETLENDI_EKI: Final = " Mütâlaa editörlerince denetlenmiştir."


@dataclass(frozen=True)
class MealKaynagi:
    slug: str
    rol: str  # ROL_MEAL ya da ROL_TANIK
    eser: str | None  # capa eseri (`meal:{eser}:{s}:{a}`); tanikta yok
    kilit_bolumu: str
    modul: str  # bagdastirici modulu (tembel ice aktarilir)
    tanik: str | None  # bu kaynagin QA tanigi (slug); yoksa None
    atif: str | None  # beklenen atif metni (G-KAY onek denetimi); tanikta yok

    @property
    def kapilar(self) -> tuple[str, ...]:
        return MEAL_KAPILARI if self.rol == ROL_MEAL else ()


KAYNAKLAR: Final[dict[str, MealKaynagi]] = {
    KAYNAK_ORIJINAL: MealKaynagi(
        slug=KAYNAK_ORIJINAL,
        rol=ROL_MEAL,
        eser="elmalili",
        kilit_bolumu=BOLUM_VIKIKAYNAK,
        modul="mutalaa_pipeline.ingest.elmalili_vikikaynak",
        tanik=KAYNAK_EPUB,
        atif=ATIF_ORIJINAL,
    ),
    KAYNAK_SADE: MealKaynagi(
        slug=KAYNAK_SADE,
        rol=ROL_MEAL,
        eser="elmalili-sade",
        kilit_bolumu=BOLUM_SADE,
        modul="mutalaa_pipeline.ingest.elmalili_sade",
        tanik=None,
        atif=ATIF_SADE,
    ),
    KAYNAK_EPUB: MealKaynagi(
        slug=KAYNAK_EPUB,
        rol=ROL_TANIK,
        eser=None,
        kilit_bolumu=BOLUM_EPUB,
        modul="mutalaa_pipeline.ingest.elmalili_epub",
        tanik=None,
        atif=None,
    ),
}

MEAL_KAYNAKLARI: Final = tuple(s for s, k in KAYNAKLAR.items() if k.rol == ROL_MEAL)
TANIK_KAYNAKLARI: Final = tuple(s for s, k in KAYNAKLAR.items() if k.rol == ROL_TANIK)


def meal_mi(slug: object) -> bool:
    """Birim ureten ve `export pg` ile yuklenen meal kaynagi mi (tanik degil)."""
    return isinstance(slug, str) and slug in MEAL_KAYNAKLARI


def tanik_mi(slug: object) -> bool:
    return isinstance(slug, str) and slug in TANIK_KAYNAKLARI


def kayitli_mi(slug: object) -> bool:
    return isinstance(slug, str) and slug in KAYNAKLAR


def kaynak(slug: str) -> MealKaynagi:
    return KAYNAKLAR[slug]


def capa_eseri(slug: str) -> str:
    """Meal kaynaginin capa eseri (`elmalili`, `elmalili-sade`); tanikta hata."""
    eser = KAYNAKLAR[slug].eser
    if eser is None:
        raise KeyError(slug)
    return eser


def capa_onegi(slug: str) -> str:
    """`meal:{eser}:` oneki."""
    return f"meal:{capa_eseri(slug)}:"


def bagdastirici_modulu(slug: str) -> object:
    """Kaynagin bagdastirici modulu (tembel ice aktarma: `ingest` ve `cli` hafif kalir)."""
    return importlib.import_module(KAYNAKLAR[slug].modul)
