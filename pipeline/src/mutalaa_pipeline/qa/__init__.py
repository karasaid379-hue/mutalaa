"""QA kapilari ve olcumler (Icerik hatti §9): `mutalaa qa run`.

Kapilar `qa/checks/` altindadir; `qa/run.py` zinciri okur, kapilari calistirir ve
`data/reports/{run_id}.json` raporunu yazar. `export pg` bu raporu `komut`, `kaynak`,
`anchor_run_id`, `units_sha256` ve `kapilar` alanlariyla arar (`qa/rapor.py`, export/pg.py
`_qa_denetle`); G-CAP tabani da ayni kabul kararini kullanir.
"""

from typing import Final

KAPILAR: Final = ("G-KAY", "G-BUT", "G-CAP", "G-NOR")
GECTI: Final = "gecti"
KALDI: Final = "kaldi"
QA_KOMUTU: Final = "qa run"
