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
# Sure adi adaylari (A11.3): capa uretilmez (G-CAP yok), arama metni uretilmez (G-NOR yok).
SURE_ADI_KAYNAGI: Final = "sure-adlari-vikipedi"
SURE_ADI_KAPILARI: Final = ("G-KAY", "G-BUT")
GECTI: Final = "gecti"
KALDI: Final = "kaldi"
QA_KOMUTU: Final = "qa run"


def kaynak_kapilari(source_id: object) -> tuple[str, ...]:
    """Bir kaynagin `export pg` icin gecmesi gereken kapilar (varsayilan dort kapi)."""
    if source_id == UST_VERI_KAYNAGI:
        return YAPI_KAPILARI
    if source_id == SURE_ADI_KAYNAGI:
        return SURE_ADI_KAPILARI
    return KAPILAR
