"""QA kapilari ve olcumler (Icerik hatti §9): `mutalaa qa run`.

Kapilar `qa/checks/` altindadir; `qa/run.py` zinciri okur, kapilari calistirir ve
`data/reports/{run_id}.json` raporunu yazar. `export pg` bu raporu `komut`, `kaynak`,
`anchor_run_id`, `units_sha256` ve `kapilar` alanlariyla arar (`qa/rapor.py`, export/pg.py
`_qa_denetle`); G-CAP tabani da ayni kabul kararini kullanir.
"""

from typing import Final

KAPILAR: Final = ("G-KAY", "G-BUT", "G-CAP", "G-NOR")
# Ust veri (yapi) kaynaginda normalizasyon yoktur: ar_norm/search_text uretilmez, G-NOR uygulanmaz.
UST_VERI_KAYNAGI: Final = "tanzil-ust-veri"
YAPI_KAPILARI: Final = ("G-KAY", "G-BUT", "G-CAP")
GECTI: Final = "gecti"
KALDI: Final = "kaldi"
QA_KOMUTU: Final = "qa run"


def kaynak_kapilari(source_id: object) -> tuple[str, ...]:
    """Bir kaynagin `export pg` icin gecmesi gereken kapilar (varsayilan dort kapi)."""
    return YAPI_KAPILARI if source_id == UST_VERI_KAYNAGI else KAPILAR
