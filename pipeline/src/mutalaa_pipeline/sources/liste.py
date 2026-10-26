"""`sources list` ciktisi: tablo ve JSON bicimleri."""

import json
from datetime import date

from mutalaa_pipeline.sources.kayit import Kaynak

SUTUNLAR = ("slug", "tur", "license_status", "kurul_gerekli", "embed_ok", "yeniden_kontrol")


def gecmis_mi(kaynak: Kaynak, bugun: date) -> bool:
    """Yeniden kontrol tarihi bugunden eskiyse dogru."""
    return kaynak.yeniden_kontrol < bugun


def satirlar(kaynaklar: list[Kaynak], bugun: date) -> list[dict[str, object]]:
    """Slug sirasinda (Ordinal) liste satirlari."""
    return [
        {
            "slug": k.slug,
            "tur": k.tur.value,
            "license_status": k.license_status.value,
            "kurul_gerekli": k.kurul_gerekli,
            "embed_ok": k.embed_ok,
            "yeniden_kontrol": k.yeniden_kontrol.isoformat(),
            "yeniden_kontrol_gecmis": gecmis_mi(k, bugun),
        }
        for k in sorted(kaynaklar, key=lambda k: k.slug)
    ]


def json_metni(satir_listesi: list[dict[str, object]]) -> str:
    return json.dumps(satir_listesi, indent=2, ensure_ascii=True)


def _evet_hayir(deger: object) -> str:
    return "evet" if deger is True else "hayir"


def tablo_metni(satir_listesi: list[dict[str, object]]) -> str:
    """Sabit genislikli tablo; gecmis yeniden_kontrol tarihinin sonuna `!` eklenir."""
    hucreler: list[tuple[str, ...]] = [SUTUNLAR]
    for satir in satir_listesi:
        tarih = str(satir["yeniden_kontrol"]) + (" !" if satir["yeniden_kontrol_gecmis"] else "")
        hucreler.append(
            (
                str(satir["slug"]),
                str(satir["tur"]),
                str(satir["license_status"]),
                _evet_hayir(satir["kurul_gerekli"]),
                _evet_hayir(satir["embed_ok"]),
                tarih,
            )
        )
    genislik = [max(len(satir[i]) for satir in hucreler) for i in range(len(SUTUNLAR))]
    return "\n".join(
        "  ".join(hucre.ljust(genislik[i]) for i, hucre in enumerate(satir)).rstrip()
        for satir in hucreler
    )
