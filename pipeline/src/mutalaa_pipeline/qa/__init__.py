"""QA kapilari ve olcumler (Icerik hatti §9): `mutalaa qa run`.

Kapilar `qa/checks/` altindadir; `qa/run.py` zinciri okur, kapilari calistirir ve
`data/reports/{run_id}.json` raporunu yazar. `export pg` bu raporu `komut`, `kaynak`,
`anchor_run_id`, `units_sha256` ve `kapilar` alanlariyla arar (`qa/rapor.py`, export/pg.py
`_qa_denetle`); G-CAP tabani da ayni kabul kararini kullanir.
"""

from typing import Final

from mutalaa_pipeline.ingest.meal_kaynaklari import MEAL_KAPILARI, meal_mi
from mutalaa_pipeline.ingest.risale_kaynaklari import (
    BASKI_KAPILARI,
    KAYNAK_BASKI,
    KAYNAK_RNK,
    RNK_KAPILARI,
)

KAPILAR: Final = ("G-KAY", "G-BUT", "G-CAP", "G-NOR")
# Ust veri (yapi) kaynaginda normalizasyon yoktur: ar_norm/search_text uretilmez, G-NOR uygulanmaz.
UST_VERI_KAYNAGI: Final = "tanzil-ust-veri"
YAPI_KAPILARI: Final = ("G-KAY", "G-BUT", "G-CAP")
# Sure adi adaylari (A11.3): capa uretilmez (G-CAP yok), arama metni uretilmez (G-NOR yok).
SURE_ADI_KAYNAGI: Final = "sure-adlari-vikipedi"
SURE_ADI_KAPILARI: Final = ("G-KAY", "G-BUT")
# QAC morfolojisi (A17.3): kelime/lemma/kok satirlari; arama metni yok (G-NOR yok).
QAC_KAYNAGI: Final = "qac-morfoloji"
# QuranWBW Turkce kelime anlami (A17.6): ayni uc kapi; G-NOR yok.
QURANWBW_KAYNAGI: Final = "quranwbw-tr"
# Risale lugat adaylari (A20.6; Kelime-Frekans baslik soz listesi): dort kapi. G-CAP "uygulanmaz"
# olarak gecer (lugat maddesinin capasi yoktur), ama kaynak kapisi sayilir.
LUGAT_KAYNAGI: Final = "risale-kelime-frekans"
LUGAT_KAPILARI: Final = ("G-KAY", "G-BUT", "G-CAP", "G-NOR")
# Lugat kaynaklari (A20.6b): RNK lugati ve rganeyev/Sozluk; ayni dort kapi (G-CAP uygulanmaz).
LUGAT_KAYNAK_KIMLIKLERI: Final = ("lugat-rnk", "lugat-sozluk-rganeyev")
# Risale ayet atif dizini (A20.7b; K-51 madde 13): `enrich citations` ciktisi, dort kapi.
# G-NOR "uygulanmaz" olarak gecer (satirlar metin tasimaz), ama kaynak kapisi sayilir.
ATIF_KAYNAGI: Final = "risale-atif-dizini"
ATIF_KAPILARI: Final = ("G-KAY", "G-BUT", "G-CAP", "G-NOR")
GECTI: Final = "gecti"
KALDI: Final = "kaldi"
QA_KOMUTU: Final = "qa run"


def kaynak_kapilari(source_id: object) -> tuple[str, ...]:
    """Bir kaynagin `export pg` icin gecmesi gereken kapilar (varsayilan dort kapi).

    Meal kaynaklarinda bes kapi: G-HIZ sert kapidir (K-49 madde 12); G-MET uygulanmaz.
    RNK Risale metninde (`risale-rnk-metin`) dort kapi: G-KAY, G-BUT, G-CAP, G-NOR. Diyanet
    karsilastirma verisi (`risale-asil-nusha`) `export pg` ile yuklenmez; varsayilan dort kapi ona
    uygulanmaz.
    """
    if meal_mi(source_id):
        return MEAL_KAPILARI
    if source_id in (UST_VERI_KAYNAGI, QAC_KAYNAGI, QURANWBW_KAYNAGI):
        return YAPI_KAPILARI
    if source_id == SURE_ADI_KAYNAGI:
        return SURE_ADI_KAPILARI
    if source_id == KAYNAK_RNK:  # A20.2b: G-CAP dahil dort kapi
        return RNK_KAPILARI
    if source_id == LUGAT_KAYNAGI or source_id in LUGAT_KAYNAK_KIMLIKLERI:  # A20.6, A20.6b
        return LUGAT_KAPILARI
    if source_id == ATIF_KAYNAGI:  # A20.7b: ayet atif dizini, dort kapi
        return ATIF_KAPILARI
    if source_id == KAYNAK_BASKI:  # A20.3: baski sayfa esleme, G-NOR "uygulanmaz" olarak gecer
        return BASKI_KAPILARI
    return KAPILAR
