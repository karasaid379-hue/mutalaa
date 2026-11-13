# ruff: noqa: RUF001
"""Sentetik lugat maddeleri (A20.6, A20.5a'dan kalan): `test-risale-ornek` fiksturu.

15 ACIKCA SENTETIK madde ("Deneme sozu N"): hicbir gercek Risale-i Nur sozu, lugat tanimi ya da
kelime anlami degildir. Uc yogunluk duzeyi (`duzey` 1, 2, 3: besere madde) ve tanimsiz maddeler
(`tanim_tr` null) icerir, boylece lugat karti ve yogunluk ayari (A31) uctan uca denenir. Maddeler
`status = "aday"` ve `origin = "hat"` girer; kaynak `test-` onekli oldugu icin `public` derlemeye
HICBIR durumda girmez (P-12). Kendi urettigimiz metin oldugu icin her metne uretimde BIR KEZ
`kanonik_metin` uygulanir. Disaridan dosya almaz; ayni surumde ayni baytlar cikar.

Satirlar gercek yolla (`ingest/lugat_madde.py`) ayni alanlari tasir; `kaynaklar` Kelime-Frekans
yerine `{siklik, kitaplar, fikstur}` icerir (sozluk OCR yok). Fikstur ingest'ine baglama
(`ingest/risale_ornek.py` `dosya_yaz(ctx, KAYNAK, LUGAT_ADI, ornek_lugat_satirlari(),
MADDE_ANAHTARI)`) birlestirmede yapilir; bu modul ortak dosyaya dokunmaz.
"""

from typing import Final

from mutalaa_pipeline.anchor import kanonik_metin
from mutalaa_pipeline.ingest.lugat_madde import (
    MADDE_ANAHTARI,
    basvuru_nesnesi,
    duzey_hesapla,
    madde_satiri,
)
from mutalaa_pipeline.staged import yapi_baytlari

KAYNAK: Final = "test-risale-ornek"
KITAP: Final = "test-ornek"
URETEC_SURUMU: Final = "1"
# Uc duzey: ilk bes >= 100 (duzey 1), sonraki bes 20-99 (duzey 2), son bes < 20 (duzey 3).
SIKLIKLAR: Final = (200, 180, 160, 140, 120, 80, 70, 60, 50, 40, 15, 12, 9, 6, 3)
ADET: Final = len(SIKLIKLAR)


def ornek_lugat_satirlari() -> list[dict[str, object]]:
    """15 sentetik madde (basliksoz sirasina gore SIRALANMAMIS, uretim sirasinda)."""
    satirlar: list[dict[str, object]] = []
    for no, siklik in enumerate(SIKLIKLAR, start=1):
        baslik = kanonik_metin(f"Deneme sözü {no}")
        # Her ucuncu madde tanimsiz kalir (editor henuz yazmadi).
        tanim = None if no % 3 == 0 else kanonik_metin(f"Deneme tanımı {no}")
        satirlar.append(
            madde_satiri(
                source_id=KAYNAK,
                basliksoz=baslik,
                duzey=duzey_hesapla(siklik),
                kaynaklar={"siklik": siklik, "kitaplar": {KITAP: siklik}, "fikstur": True},
                onerilen_basvuru=basvuru_nesnesi(
                    [(kanonik_metin(f"Deneme başvurusu {no}"), 1)], siklik, 1
                ),
                data_version=f"{KAYNAK}@{URETEC_SURUMU}",
                tanim_tr=tanim,
            )
        )
    return satirlar


def ornek_lugat_baytlari() -> bytes:
    """`lugat.jsonl` baytlari (kanonik, `basliksoz`a gore sirali)."""
    return yapi_baytlari(ornek_lugat_satirlari(), MADDE_ANAHTARI)[0]
