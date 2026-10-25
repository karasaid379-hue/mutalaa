"""Arama normalizasyonu (A05, K-36): Turkce dar/genis/govde ve Arapca anahtarlar.

Normalizasyon yalniz arama sutunlari ve sorgu icindir; kanonik metin degismez (K-26).
Kural ya da ic kesme listesi degisirse `NORMALIZER_VERSION` artar.
"""

from typing import Final, NamedTuple

from mutalaa_pipeline.normalize.arabic import ar_anahtari, normalize_ar
from mutalaa_pipeline.normalize.turkish import (
    dar_sozcukler,
    fold_wide,
    ic_kesme_listesi,
    lower_turkish,
    normalize_tr,
    tr_stem,
    tr_stem_sozcukler,
)
from mutalaa_pipeline.normalize.unicode import BOSLUK, split_scripts

NORMALIZER_VERSION: Final = "1.0"


class SearchKeys(NamedTuple):
    """Bir metnin arama anahtarlari."""

    tr_narrow: str
    tr_wide: str
    tr_stem: str
    ar_norm: str


def search_keys(metin: str) -> SearchKeys:
    """Tum anahtarlar; on adim ve bolme bir kez yapilir."""
    parcalar = split_scripts(metin)
    sozcukler = dar_sozcukler(parcalar.tr, ic_kesme_listesi())
    return SearchKeys(
        tr_narrow=BOSLUK.join(sozcukler),
        tr_wide=BOSLUK.join(fold_wide(s) for s in sozcukler),
        tr_stem=tr_stem_sozcukler(sozcukler),
        ar_norm=ar_anahtari(parcalar.ar),
    )


__all__ = [
    "NORMALIZER_VERSION",
    "SearchKeys",
    "lower_turkish",
    "normalize_ar",
    "normalize_tr",
    "search_keys",
    "split_scripts",
    "tr_stem",
]
