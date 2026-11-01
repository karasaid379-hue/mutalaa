"""`sources list` ciktisi: tablo ve JSON bicimleri (ikisi de ASCII)."""

import json

from mutalaa_pipeline.sources.kayit import Kaynak

SUTUNLAR = ("slug", "tur", "surum", "kaynak_url")
BOS_HUCRE = "-"


def satirlar(kaynaklar: list[Kaynak]) -> list[dict[str, object]]:
    """Slug sirasinda (Ordinal) liste satirlari; olmayan alan `None`."""
    return [
        {"slug": k.slug, "tur": k.tur.value, "surum": k.surum, "kaynak_url": k.kaynak_url}
        for k in sorted(kaynaklar, key=lambda k: k.slug)
    ]


def json_metni(satir_listesi: list[dict[str, object]]) -> str:
    return json.dumps(satir_listesi, indent=2, ensure_ascii=True)


def _hucre(deger: object) -> str:
    """Tablo hucresi: olmayan deger `-`; ASCII disi ve kontrol karakterleri kacislidir."""
    if deger is None:
        return BOS_HUCRE
    return ascii(str(deger))[1:-1]


def tablo_metni(satir_listesi: list[dict[str, object]]) -> str:
    """Sabit genislikli tablo; ilk satir sutun adlaridir."""
    hucreler: list[tuple[str, ...]] = [SUTUNLAR]
    for satir in satir_listesi:
        hucreler.append(tuple(_hucre(satir[ad]) for ad in SUTUNLAR))
    genislik = [max(len(satir[i]) for satir in hucreler) for i in range(len(SUTUNLAR))]
    return "\n".join(
        "  ".join(hucre.ljust(genislik[i]) for i, hucre in enumerate(satir)).rstrip()
        for satir in hucreler
    )
