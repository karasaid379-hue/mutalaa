"""Ortak test vektoru dosyalari: bilinen dosya listesi tek yerde (A12.6).

`shared/test-vectors` altindaki her `.jsonl` dosyasi ya bir Python kosucusunun yukledigi
`KOSULAN` listesinde ya da gerekcesiyle `ATLANAN` listesinde (ya da `ATLANAN_KLASORLER`
altinda) olmali; bilinmeyen yeni dosya `test_vektor_dosyalari.py` testini kirar. Kosucu
testleri dosya yollarini buradaki sabitlerden okur (yinelenen liste yok).
"""

from pathlib import Path
from typing import Final

KOK_ISARETI: Final = "pnpm-workspace.yaml"


def depo_koku() -> Path:
    yol = Path(__file__).resolve()
    for aday in yol.parents:
        if (aday / KOK_ISARETI).is_file():
            return aday
    raise RuntimeError(f"depo koku bulunamadi ({KOK_ISARETI} yok)")


VEKTOR_KOKU: Final = depo_koku() / "shared" / "test-vectors"

# Python kosuculari (dosya yolu, VEKTOR_KOKU'ne gore).
VALID: Final = "anchors/valid.jsonl"
INVALID: Final = "anchors/invalid.jsonl"
COMPARE: Final = "anchors/compare.jsonl"
CONTAINS: Final = "anchors/contains.jsonl"
ROUTE: Final = "anchors/route.jsonl"
OFFSETS: Final = "offsets/offsets.jsonl"
HASH: Final = "content-hash/hash.jsonl"
NORMALIZE_TR: Final = "normalize/tr.jsonl"
NORMALIZE_AR: Final = "normalize/ar.jsonl"
NORMALIZE_TR_GOVDE: Final = "normalize/tr-govde.jsonl"

# Kosucu test dosyasi -> yukledigi vektor dosyalari.
KOSULAN: Final[dict[str, tuple[str, ...]]] = {
    "test_vectors.py": (VALID, INVALID, COMPARE, CONTAINS, ROUTE, OFFSETS, HASH),
    "test_normalize_vectors.py": (NORMALIZE_TR, NORMALIZE_AR, NORMALIZE_TR_GOVDE),
}

# Python'un kosmadigi dosya -> gerekce.
ATLANAN: Final[dict[str, str]] = {
    "fts-query/query.jsonl": "yalniz TypeScript kosar (packages/search buildFtsQuery)",
}
# Klasor oneki -> gerekce.
ATLANAN_KLASORLER: Final[dict[str, str]] = {
    "arama/": "olcum kumesi, vektor degil",
}

# Tarama sirasinda gezilmeyen klasorler (shared/test-vectors/scripts/check-lib.mjs DEFAULT_SKIP).
TARAMA_DISI: Final = frozenset({"node_modules", "scripts", "test", "dist"})

KOSULAN_DOSYALAR: Final = frozenset(d for dosyalar in KOSULAN.values() for d in dosyalar)
