"""Risale kaynaklari: tek kayit modulu (A20.1, K-51 madde 2).

Kaynak kimligine bagdastiriciyi, kilit dosyasini ve kapi kumesini eslestiren TEK yerdir; `cli.py`
(ingest), `qa/run.py` (`qa run` yonlendirmesi) bu modulden turer. Modul hafiftir (yalniz standart
kitaplik): `qa` paketi onu ice aktarabilir.

    risale-asil-nusha   Diyanet "asil nusha" (GitHub zip): KARSILASTIRMA ve dogrulama verisi.
                        `data/staged` altinda kalir; `export pg` ile veritabanina YUKLENMEZ
                        (K-51 madde 2: birincil metin RNK'dir).

`risale-rnk-metin` (RNK, birincil metin) ayri bir adimdir (A20.1b) ve bu kayda eklenmez.
"""

import importlib
from dataclasses import dataclass
from typing import Final

KAYNAK_DIYANET: Final = "risale-asil-nusha"
# A20.1 kapilari: G-CAP yalniz A20.2b'de yazilir (cap yeniden numaralanmaz denetimi).
RISALE_KAPILARI: Final = ("G-KAY", "G-BUT")


@dataclass(frozen=True)
class RisaleKaynagi:
    slug: str
    modul: str  # bagdastirici modulu (tembel ice aktarilir)
    yukleme: bool  # `export pg` ile veritabanina yuklenir mi
    kapilar: tuple[str, ...]


KAYNAKLAR: Final[dict[str, RisaleKaynagi]] = {
    KAYNAK_DIYANET: RisaleKaynagi(
        slug=KAYNAK_DIYANET,
        modul="mutalaa_pipeline.ingest.risale_diyanet",
        yukleme=False,
        kapilar=RISALE_KAPILARI,
    ),
}


def risale_mi(slug: object) -> bool:
    """Bu modulun yonettigi bir Risale kaynagi mi."""
    return isinstance(slug, str) and slug in KAYNAKLAR


def kaynak(slug: str) -> RisaleKaynagi:
    return KAYNAKLAR[slug]


def bagdastirici_modulu(slug: str) -> object:
    """Kaynagin bagdastirici modulu (tembel ice aktarma: `cli` hafif kalir)."""
    return importlib.import_module(KAYNAKLAR[slug].modul)
