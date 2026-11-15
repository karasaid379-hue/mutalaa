"""Risale kaynaklari: tek kayit modulu (A20.1, K-52 madde 2).

Kaynak kimligine bagdastiriciyi, kilit dosyasini ve kapi kumesini eslestiren TEK yerdir; `cli.py`
(ingest), `qa/run.py` (`qa run` yonlendirmesi) bu modulden turer. Modul hafiftir (yalniz standart
kitaplik): `qa` paketi onu ice aktarabilir.

    risale-asil-nusha   Diyanet "asil nusha" (GitHub zip): KARSILASTIRMA ve dogrulama verisi.
                        `data/staged` altinda kalir; `export pg` ile veritabanina YUKLENMEZ
                        (K-52 madde 2: birincil metin RNK'dir).

    risale-rnk-metin    RNK Neşriyat `txt` + `json` (A20.1b): BIRINCIL metin; bagdastirici
                        `risale_rnk_kaynaklari`. `data/staged` birimleri `export pg` ile
                        yuklenir (G-KAY, G-BUT, G-CAP, G-NOR).

    test-risale-ornek   Sentetik Risale fiksturu (A20.5a): `export pg` ile yuklenir; ingest,
                        normalize, anchor ve qa `ingest/risale_ornek.py`, `adimlar/risale_ornek.py`
                        ve `qa/run_risale_ornek.py` modullerindedir (`yukleme = True`).

    risale-baski-rnk    RNK baski sayfa esleme (A20.3, K-52 madde 6 ve 7): `tur = "baski"`. Bir
                        INGEST kaynagi degildir (`KAYNAKLAR`da yoktur): `risale-rnk-metin`
                        zincirinden `anchor --source risale-baski-rnk` adimiyla `page_map`
                        satirlari uretir; `export pg` onlari yukler (`export/pg_risale_sayfa.py`).
"""

import importlib
from dataclasses import dataclass
from typing import Final

KAYNAK_DIYANET: Final = "risale-asil-nusha"
KAYNAK_RNK: Final = "risale-rnk-metin"
KAYNAK_BASKI: Final = "risale-baski-rnk"
# Sentetik fikstur (A20.5a): `test-` onekli; ingest/normalize/anchor/qa kendi modullerindedir.
KAYNAK_ORNEK: Final = "test-risale-ornek"
# Diyanet karsilastirma verisi: birim yuklenmez, G-CAP ve G-NOR uygulanmaz (A20.1).
RISALE_KAPILARI: Final = ("G-KAY", "G-BUT")
# RNK metni: dort kapi (A20.2b); G-KAY ve G-BUT ingest, G-CAP ve G-NOR anchor ciktisinda kosar.
RNK_KAPILARI: Final = ("G-KAY", "G-BUT", "G-CAP", "G-NOR")
# Baski sayfa esleme: dort kapi; G-NOR arama metni uretilmedigi icin "uygulanmaz" olarak gecer.
BASKI_KAPILARI: Final = RNK_KAPILARI


@dataclass(frozen=True)
class RisaleKaynagi:
    slug: str
    modul: str  # bagdastirici modulu (tembel ice aktarilir)
    yukleme: bool  # `export pg` ile veritabanina yuklenir mi
    kapilar: tuple[str, ...]


KAYNAKLAR: Final[dict[str, RisaleKaynagi]] = {
    KAYNAK_DIYANET: RisaleKaynagi(
        slug=KAYNAK_DIYANET,
        modul="mutalaa_pipeline.ingest.risale_diyanet",
        yukleme=False,
        kapilar=RISALE_KAPILARI,
    ),
    KAYNAK_RNK: RisaleKaynagi(
        slug=KAYNAK_RNK,
        modul="mutalaa_pipeline.ingest.risale_rnk_kaynaklari",
        yukleme=True,
        kapilar=RNK_KAPILARI,
    ),
    KAYNAK_ORNEK: RisaleKaynagi(
        slug=KAYNAK_ORNEK,
        modul="mutalaa_pipeline.ingest.risale_ornek",
        yukleme=True,
        kapilar=RNK_KAPILARI,
    ),
}


def risale_mi(slug: object) -> bool:
    """Bu modulun yonettigi bir Risale kaynagi mi."""
    return isinstance(slug, str) and slug in KAYNAKLAR


def baski_mi(slug: object) -> bool:
    """RNK baski sayfa esleme kaynagi mi (ingest kaynagi degil, bir adim ciktisi)."""
    return slug == KAYNAK_BASKI


def kaynak(slug: str) -> RisaleKaynagi:
    return KAYNAKLAR[slug]


def bagdastirici_modulu(slug: str) -> object:
    """Kaynagin bagdastirici modulu (tembel ice aktarma: `cli` hafif kalir)."""
    return importlib.import_module(KAYNAKLAR[slug].modul)
