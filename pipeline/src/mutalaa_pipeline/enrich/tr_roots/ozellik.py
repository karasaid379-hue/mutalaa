"""Otomatik onay kaniti ozellikleri: kucuk, onceden yazili havuz (K-51 madde 9; politika surumu 3).

Havuz `kanit` nesnesinden (`kaynaklar[].alan`, `qac.eslesme`, `qac.ar_lemma_qac_ref`) saf
islevle turetilir; veritabani, dosya ve metin yoktur. Havuz DEGERLENDIRME KAYNAGINA (QuranWBW)
bagli ozellik tasimaz: politika olcumun girdisi olan referansa dayanamaz (dongusellik).

Ozellikler (yedi; her biri kucuk kapali degerler kumesi):

* `kaikki_dilleri`: kanitin geldigi kaikki maddelerinin dili (`tr`, `ota`, `ota+tr`);
* `kok_sablonu`: `root` sablonu kanitta `var`/`yok`;
* `sablon_ailesi`: `root`, `bor` (bor, bor+, lbor, slbor), `soy` (der, der+, inh, inh+), `agac`
  (ety, etymon) kumesi, `+` ile birlesik;
* `qac_eslesme`: `kok_harfleri`, `etimon_lemma` ya da `ikisi`;
* `kaikki_pos`: kanittaki kaikki sozcuk turleri, `+` ile birlesik;
* `kaynak_sayisi`: kanit kaydi sayisi bandi (`1`, `2-3`, `4+`);
* `ar_lemma`: etimonla tek QAC lemmasi eslesti mi (`var`/`yok`).
"""

from collections.abc import Mapping
from typing import Final

OZELLIK_ADLARI: Final = (
    "kaikki_dilleri",
    "kok_sablonu",
    "sablon_ailesi",
    "qac_eslesme",
    "kaikki_pos",
    "kaynak_sayisi",
    "ar_lemma",
)

_AILE: Final[Mapping[str, str]] = {
    "root": "root",
    "bor": "bor",
    "bor+": "bor",
    "lbor": "bor",
    "slbor": "bor",
    "der": "soy",
    "der+": "soy",
    "inh": "soy",
    "inh+": "soy",
    "ety": "agac",
    "etymon": "agac",
}


def _kaynak_alanlari(kanit: Mapping[str, object]) -> list[str]:
    kaynaklar = kanit.get("kaynaklar")
    alanlar: list[str] = []
    for k in kaynaklar if isinstance(kaynaklar, list) else []:
        if isinstance(k, dict) and isinstance(k.get("alan"), str):
            alanlar.append(str(k["alan"]))
    return alanlar


def ozellikler(kanit: Mapping[str, object]) -> dict[str, str]:
    """Bir kanit nesnesinin ozellik havuzu degerleri."""
    alanlar = _kaynak_alanlari(kanit)
    parcalar = [a.split(":", 2) for a in alanlar]
    diller = sorted({p[0] for p in parcalar if len(p) == 3})
    poslar = sorted({p[1] for p in parcalar if len(p) == 3})
    sablonlar = [p[2].rsplit(".", 1)[-1] for p in parcalar if len(p) == 3]
    aileler = sorted({_AILE[s] for s in sablonlar if s in _AILE})
    qac = kanit.get("qac")
    qac = qac if isinstance(qac, dict) else {}
    n = len(alanlar)
    return {
        "kaikki_dilleri": "+".join(diller) or "yok",
        "kok_sablonu": "var" if "root" in sablonlar else "yok",
        "sablon_ailesi": "+".join(aileler) or "yok",
        "qac_eslesme": str(qac.get("eslesme") or "bilinmiyor"),
        "kaikki_pos": "+".join(poslar) or "yok",
        "kaynak_sayisi": "1" if n <= 1 else ("2-3" if n <= 3 else "4+"),
        "ar_lemma": "var" if qac.get("ar_lemma_qac_ref") else "yok",
    }
