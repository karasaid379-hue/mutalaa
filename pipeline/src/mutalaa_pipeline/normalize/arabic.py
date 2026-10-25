"""Arapca arama anahtari `ar_norm` (K-36 madde 4, Arama 1.3).

Sira: silme, birlestirme, sozcuklere bolme. Silme araligi disindaki isaretler
(U+0610-U+061A, U+08D3-U+08FF), Farsca harfler, Arapca-Hint rakamlar, sunum bicimleri
(NFKC yok) ve U+06C0 1.0'da degismez; yalin hemze (U+0621) korunur.
"""

from typing import Final

from mutalaa_pipeline.normalize.unicode import (
    BOSLUK,
    harf_ya_da_rakam_var_mi,
    sozcuklere_bol,
    split_scripts,
)

_SILINENLER: Final = frozenset(
    {
        *range(0x064B, 0x0660),
        0x0670,
        *range(0x06D6, 0x06EE),
        0x0640,
    }
)
_BIRLESTIRME: Final = {
    0x0623: 0x0627,  # elif uzerinde hemze
    0x0625: 0x0627,  # elif altinda hemze
    0x0622: 0x0627,  # elif uzerinde med
    0x0671: 0x0627,  # elif vasla
    0x0649: 0x064A,  # elif maksura
    0x0629: 0x0647,  # te marbuta
    0x0624: 0x0648,  # vav uzerinde hemze
    0x0626: 0x064A,  # ye uzerinde hemze
}
_CEVIRI: Final[dict[int, int | None]] = {**dict.fromkeys(_SILINENLER), **_BIRLESTIRME}


def ar_anahtari(ar_parca: str) -> str:
    sozcukler = sozcuklere_bol(ar_parca.translate(_CEVIRI), kesme_dahil=False)
    return BOSLUK.join(s for s in sozcukler if harf_ya_da_rakam_var_mi(s))


def normalize_ar(metin: str) -> str:
    """Arapca anahtar `ar_norm`; Turkce konumlar ayirici olur."""
    return ar_anahtari(split_scripts(metin).ar)
