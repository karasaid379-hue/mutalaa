"""Lugat maddesi staged satiri (A20.6, K-51 madde 9 ve 10): ortak kurucu ve sabitler.

`lugat.jsonl` satiri (kayit turu: lugat maddesi; `units.jsonl` DEGIL; capa yoktur). Kelime-Frekans
kaynagi (`ingest/kelime_frekans.py`) ve sentetik fikstur (`ingest/risale_ornek_lugat.py`) ayni
kurucuyu kullanir; QA (`qa/checks/risale_lugat.py`) alan kumesini ve degismezleri bu modulden
okur. Staged JSON ondalik sayi tasimaz (`kati_json`): butun degerler tam sayi, metin, mantiksal
ya da null'dur.

Alanlar (sunucu gocu `lugat_madde` sutunlariyla bire bir; `id` veritabaninda uretilir):

* `source_id`, `basliksoz` (kaynaktaki yazim, bayt bayt; NFC UYGULANMAZ), `basliksoz_norm`
  (`tr_narrow` arama anahtari; bos ise `ar_norm`), `osmanlica_yazim`, `koken_dil`, `ar_kok_id`
  (hepsi `null`: editor doldurur), `tanim_tr` (Kelime-Frekans maddesinde HER ZAMAN `null`; K-51
  madde 10: tanimi editor yazar, yapay zeka taslagi yok, K-50 madde 1), `kaynaklar` (jsonb),
  `duzey`, `status = "aday"`, `origin = "hat"`, `version = 1`, `content_hash`, `data_version`.
* `onerilen_basvuru`: `review.onerilen`e gidecek nesne; madde sutunlarina YAZILMAZ. Kelime-Frekans
  `anlam` sutunu yalniz burada (editor basvurusu) bulunur.

`content_hash = sha256(utf-8(basliksoz + "\\n" + (tanim_tr or "")))`: editor tanim yazip onaylayinca
ozet yenilenir (K-50 madde 6 emsali); tanimi bos maddede ozet yine baslik sozune baglidir.
`duzey` siklik dilimidir (1 en sik); esikler ONERIDIR (karar bekler) ve tek yerde, burada durur.
"""

from collections.abc import Mapping, Sequence
from typing import Final

from mutalaa_pipeline.anchor import content_hash
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.normalize import search_keys

LUGAT_ADI: Final = "lugat.jsonl"
MADDE_ANAHTARI: Final = ("basliksoz",)
DURUM_ADAY: Final = "aday"
KOKEN_HAT: Final = "hat"
SURUM_1: Final = 1
# (en az toplam siklik, duzey): ilk saglanan esik gecerlidir; hicbiri saglanmazsa EN_SEYREK_DUZEY.
# Olcum (15 kitap, 21.494 benzersiz soz): >= 100 icin 1.064 soz (jeton payi %64), >= 20 icin
# 3.613 soz (%87). Esikler ONERIDIR: Lugat yogunlugu (Az/Orta/Cok) ile iliskisi karar bekler.
DUZEY_ESIKLERI: Final = ((100, 1), (20, 2))
EN_SEYREK_DUZEY: Final = 3
MADDE_ALANLARI: Final = (
    "source_id",
    "basliksoz",
    "basliksoz_norm",
    "osmanlica_yazim",
    "koken_dil",
    "tanim_tr",
    "ar_kok_id",
    "kaynaklar",
    "duzey",
    "status",
    "origin",
    "version",
    "content_hash",
    "data_version",
    "onerilen_basvuru",
)


# Lugat kaynagindan gelen madde (A20.6b, K-51 madde 10 ve 14): `lugat-rnk` ve
# `lugat-sozluk-rganeyev`. Alan kumesi Kelime-Frekans maddesinden `anlam_no` (yeni) ve
# `onerilen_basvuru` (yok) ile ayrilir; `tanim_tr` kaynak satirindan bayt bayt gelir (NFC yok;
# yalniz bas ve sondaki U+0020/U+0009 kirpilir, bkz. `ingest/lugat_kaynak.py`).
KOKEN_KAYNAK: Final = "kaynak"
DUZEY_RISALEDE_YOK: Final = 4  # Risale baslik soz listesinde yok (K-51 madde 14)
MADDE_ALANLARI_KAYNAK: Final = (
    "source_id",
    "basliksoz",
    "anlam_no",
    "basliksoz_norm",
    "osmanlica_yazim",
    "koken_dil",
    "tanim_tr",
    "ar_kok_id",
    "kaynaklar",
    "duzey",
    "status",
    "origin",
    "version",
    "content_hash",
    "data_version",
)
MADDE_ANAHTARI_KAYNAK: Final = ("basliksoz", "anlam_no")
EN_COK_ANLAM_NO: Final = 32767  # smallint


def basliksoz_norm(basliksoz: str) -> str:
    """Arama anahtari: `tr_narrow`; Turkce harf yoksa `ar_norm`. Harfsiz sozde bos kalir."""
    anahtarlar = search_keys(basliksoz)
    return anahtarlar.tr_narrow or anahtarlar.ar_norm


def duzey_hesapla(toplam_siklik: int) -> int:
    """Toplam sikliga gore duzey (1 en sik); esikler `DUZEY_ESIKLERI`."""
    for esik, duzey in DUZEY_ESIKLERI:
        if toplam_siklik >= esik:
            return duzey
    return EN_SEYREK_DUZEY


def madde_hash(basliksoz: str, tanim_tr: str | None) -> str:
    """`content_hash` (bkz. modul belgesi)."""
    return content_hash(basliksoz + "\n" + (tanim_tr or ""))


def madde_satiri(
    *,
    source_id: str,
    basliksoz: str,
    duzey: int,
    kaynaklar: Mapping[str, object],
    onerilen_basvuru: Mapping[str, object],
    data_version: str,
    tanim_tr: str | None = None,
) -> dict[str, object]:
    """Bir lugat maddesinin staged satiri (alan kumesi `MADDE_ALANLARI`)."""
    if basliksoz == "":
        raise GirdiHatasi("lugat: bos baslik soz")
    norm = basliksoz_norm(basliksoz)
    if norm == "":
        raise GirdiHatasi("lugat: baslik soz normalize edilemedi (harf ya da rakam yok)")
    return {
        "source_id": source_id,
        "basliksoz": basliksoz,
        "basliksoz_norm": norm,
        "osmanlica_yazim": None,
        "koken_dil": None,
        "tanim_tr": tanim_tr,
        "ar_kok_id": None,
        "kaynaklar": dict(kaynaklar),
        "duzey": duzey,
        "status": DURUM_ADAY,
        "origin": KOKEN_HAT,
        "version": SURUM_1,
        "content_hash": madde_hash(basliksoz, tanim_tr),
        "data_version": data_version,
        "onerilen_basvuru": dict(onerilen_basvuru),
    }


def madde_satiri_kaynak(
    *,
    source_id: str,
    basliksoz: str,
    anlam_no: int,
    tanim_tr: str,
    duzey: int,
    kaynaklar: Mapping[str, object],
    data_version: str,
) -> dict[str, object]:
    """Lugat kaynagindan gelen bir maddenin staged satiri (alan kumesi `MADDE_ALANLARI_KAYNAK`).

    `status = aday`, `origin = kaynak`, `version = 1`; tanim dolu olmali. Kelime-Frekans
    `anlam` degeri bu satira hicbir yoldan girmez (`kaynaklar` anlam dizesi tasimaz).
    """
    if basliksoz == "":
        raise GirdiHatasi("lugat: bos baslik soz")
    if tanim_tr == "":
        raise GirdiHatasi("lugat: bos tanim")
    if not 1 <= anlam_no <= EN_COK_ANLAM_NO:
        raise GirdiHatasi("lugat: anlam_no aralik disi")
    norm = basliksoz_norm(basliksoz)
    if norm == "":
        raise GirdiHatasi("lugat: baslik soz normalize edilemedi (harf ya da rakam yok)")
    return {
        "source_id": source_id,
        "basliksoz": basliksoz,
        "anlam_no": anlam_no,
        "basliksoz_norm": norm,
        "osmanlica_yazim": None,
        "koken_dil": None,
        "tanim_tr": tanim_tr,
        "ar_kok_id": None,
        "kaynaklar": dict(kaynaklar),
        "duzey": duzey,
        "status": DURUM_ADAY,
        "origin": KOKEN_KAYNAK,
        "version": SURUM_1,
        "content_hash": madde_hash(basliksoz, tanim_tr),
        "data_version": data_version,
    }


def basvuru_nesnesi(
    anlamlar: Sequence[tuple[str, int]], siklik: int, kitap_sayisi: int
) -> dict[str, object]:
    """`onerilen_basvuru`: `{anlam_basvuru: [{anlam, sayi}], siklik, kitaplar}` (sayi azalan)."""
    sirali = sorted(anlamlar, key=lambda a: (-a[1], a[0]))
    return {
        "anlam_basvuru": [{"anlam": a, "sayi": n} for a, n in sirali],
        "siklik": siklik,
        "kitaplar": kitap_sayisi,
    }
