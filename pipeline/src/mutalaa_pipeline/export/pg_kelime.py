"""`export pg` yonlendirici: QAC, QuranWBW ve Turkce kok katmani kaynaklari (A17.3, A17.6, A18.2).

`export/pg.py` bu modulu ice aktarir ve iki kancada kullanir (`hazirla` ve `_yukle`); gercek is
`export/pg_qac.py` (qac-morfoloji), `export/pg_glosses.py` (quranwbw-tr) ve
`export/pg_tr_roots.py` (kaikki-tr) ve `export/pg_xref.py` (xref-baglantilar) icindedir. Bu modul
`export.pg`'yi ice aktarmaz (dairesel ice aktarma olmasin diye ilgili modul `importlib` ile,
cagri aninda yuklenir).
"""

import importlib
from collections.abc import Sequence
from typing import TYPE_CHECKING, Final, cast

import psycopg

from mutalaa_pipeline.runctx import RunContext

if TYPE_CHECKING:
    from mutalaa_pipeline.export.pg import Hazirlik

QAC_KAYNAGI: Final = "qac-morfoloji"
QURANWBW_KAYNAGI: Final = "quranwbw-tr"
TR_ROOTS_KAYNAGI: Final = "kaikki-tr"
XREF_KAYNAGI: Final = "xref-baglantilar"
XREF_ATIF_KAYNAGI: Final = "xref-atif-iktibas"
MODULLER: Final = {
    QAC_KAYNAGI: "mutalaa_pipeline.export.pg_qac",
    QURANWBW_KAYNAGI: "mutalaa_pipeline.export.pg_glosses",
    TR_ROOTS_KAYNAGI: "mutalaa_pipeline.export.pg_tr_roots",  # A18.2: Turkce lemma, tr_root_index
    XREF_KAYNAGI: "mutalaa_pipeline.export.pg_xref",  # A18.3: kok, lemma, benzer_ayet (xref)
    XREF_ATIF_KAYNAGI: "mutalaa_pipeline.export.pg_xref_atif",  # A18.4: atif, iktibas (xref)
}
KAYNAKLAR: Final = frozenset(MODULLER)


def hazirla(
    ctx: RunContext, source_id: str, run: str | None, ek_kaynaklar: Sequence[str]
) -> "Hazirlik | None":
    """Kaynak bu katmana aitse dosya onkosullarini denetler; degilse None."""
    modul = MODULLER.get(source_id)
    if modul is None:
        return None
    return cast(
        "Hazirlik", importlib.import_module(modul).hazirla(ctx, source_id, run, ek_kaynaklar)
    )


def ozel_mi(h: "Hazirlik") -> bool:
    return h.source_id in KAYNAKLAR


def yukle(conn: psycopg.Connection, ctx: RunContext, h: "Hazirlik") -> dict[str, int]:
    """Tek islemin govdesindeki kaynaga ozgu yukleme (cagiran `conn.transaction()` icindedir)."""
    modul = importlib.import_module(MODULLER[h.source_id])
    return cast("dict[str, int]", modul.yukle(conn, ctx, h))
