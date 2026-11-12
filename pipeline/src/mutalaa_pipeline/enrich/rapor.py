"""`data/reports/` altina yalniz sayi iceren yan raporlar (dalga tablosu, kapsama; A17.5, A17.6).

Raporlar `qa run` raporu degildir (`komut` alani yoktur; `qa/rapor.py` onlari kabul karari icin
okumaz). Icerik metni yazilmaz: yalniz sayi, etiket adi, dalga numarasi ve `qac_ref` /
`lemma_id` tipi tanimlayicilar.
"""

import os
from collections.abc import Mapping
from pathlib import Path

from mutalaa_pipeline import lineage
from mutalaa_pipeline.logs import json_baytlari
from mutalaa_pipeline.runctx import RAPOR_KLASORU, RunContext


def yan_rapor_yaz(ctx: RunContext, onek: str, govde: Mapping[str, object]) -> Path:
    """`data/reports/{run_id}-{onek}.json` dosyasini atomik yazar (`--dry-run`'da cagrilmaz)."""
    klasor = ctx.veri_kok / RAPOR_KLASORU
    klasor.mkdir(parents=True, exist_ok=True)
    hedef = klasor / f"{ctx.run_id}-{onek}.json"
    gecici = klasor / f"{ctx.run_id}-{onek}.json.tmp"
    with gecici.open("wb") as dosya:
        dosya.write(json_baytlari(dict(govde)))
        dosya.flush()
        os.fsync(dosya.fileno())
    lineage.atomik_degistir(gecici, hedef)
    return hedef
