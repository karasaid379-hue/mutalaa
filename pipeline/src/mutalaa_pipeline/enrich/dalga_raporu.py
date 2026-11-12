"""Dalga tablosu raporu (A17.5, K-50 madde 7): dalga basina lemma sayisi ve kumulatif kapsama.

Saf islev: `Envanter` ve `DalgaKaydi` listesinden bir sozluk uretir; yalniz sayi, dalga numarasi
ve `qac_ref` tipi tanimlayicilar tasir (lemma ya da kok METNI yok). `enrich morphology` bunu
`data/reports/{run_id}-dalga.json` olarak yazar.

Kapsama kelime duzeyindedir ve govde lemmasini sayar: `kumulatif_kelime_orani`, o dalgaya kadar
(dalga 0 dahil) olan lemmalarin kelime gecislerinin lemmali toplam kelimeye orani; `dalga_0_haric_
kumulatif_oran` ayni sayinin dalga 0 cikarilarak (yuzdelerin dayandigi payda) hesabi.
"""

from collections.abc import Sequence
from typing import Final

from mutalaa_pipeline.enrich.morphology import SON_DALGA, DalgaKaydi, Envanter

ORAN_BASAMAK: Final = 6


def dalga_raporu(
    envanter: Envanter,
    dalgalar: Sequence[DalgaKaydi],
    cuz_basi: tuple[int, int],
    kaynak: str,
    surum: str,
) -> dict[str, object]:
    gecis = {lm.qac_ref: lm.occurrences for lm in envanter.lemmalar}
    toplam = sum(gecis.values())
    dalga0 = sum(gecis[d.qac_ref] for d in dalgalar if d.dalga == 0)
    kalan_toplam = toplam - dalga0
    satirlar: list[dict[str, object]] = []
    kum_lemma = kum_kelime = 0
    for no in range(SON_DALGA + 1):
        grup = [d for d in dalgalar if d.dalga == no]
        kelime = sum(gecis[d.qac_ref] for d in grup)
        kum_lemma += len(grup)
        kum_kelime += kelime
        satir: dict[str, object] = {
            "dalga": no,
            "lemma": len(grup),
            "kelime": kelime,
            "kumulatif_lemma": kum_lemma,
            "kumulatif_kelime": kum_kelime,
            "kumulatif_kelime_orani": round(kum_kelime / toplam, ORAN_BASAMAK) if toplam else 0,
            "zorla_dalga_1": sum(1 for d in grup if d.zorla),
        }
        if no >= 1 and kalan_toplam:
            satir["dalga_0_haric_kumulatif_oran"] = round(
                (kum_kelime - dalga0) / kalan_toplam, ORAN_BASAMAK
            )
        satirlar.append(satir)
    fatiha = [d for d in dalgalar if d.fatiha]
    cuz30 = [d for d in dalgalar if d.cuz30]
    return {
        "tur": "dalga-tablosu",
        "kaynak": kaynak,
        "data_version": f"{kaynak}@{surum}",
        "lemma": len(dalgalar),
        "lemmali_kelime": toplam,
        "cuz30_baslangic": [cuz_basi[0], cuz_basi[1]],
        "dalgalar": satirlar,
        "fatiha_lemma": len(fatiha),
        "cuz30_lemma": len(cuz30),
        "fatiha_cuz30_dalga_0_1_disinda": len(
            {d.qac_ref for d in (*fatiha, *cuz30) if d.dalga > 1}
        ),
    }
