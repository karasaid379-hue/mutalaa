"""Paylasilan enum degerleri (A06.2): `enums.json` dosyasindaki 10 tur.

Degerler `packages/content-schema/enums.json` dosyasindaki etiketlerdir ve bildirim sirasi
JSON sirasidir. Sira anlamlidir (`taslak` < `incelemede` < `onayli`). Deger eklemek ya da
sirayi degistirmek once JSON'a, sonra dort dile ayni degisiklikte girer; `tests/test_enums.py`
bu siniflari JSON'a karsi sinar.
"""

from enum import StrEnum


class DerlemeTuru(StrEnum):
    DEV = "dev"
    INTERNAL = "internal"
    PUBLIC = "public"


class SourceKind(StrEnum):
    KURAN_METNI = "kuran_metni"
    MEAL = "meal"
    TEFSIR = "tefsir"
    HADIS = "hadis"
    HADIS_CEVIRI = "hadis_ceviri"
    RISALE = "risale"
    KITAP = "kitap"
    MORFOLOJI = "morfoloji"
    KELIME_ANLAMI = "kelime_anlami"
    SOZLUK = "sozluk"
    MUSHAF_DUZENI = "mushaf_duzeni"
    MUSHAF_GORSELI = "mushaf_gorseli"
    FONT = "font"
    BASKI = "baski"
    SES = "ses"
    ZAMANLAMA = "zamanlama"
    BAGLANTI_VERISI = "baglanti_verisi"


class XrefType(StrEnum):
    ATIF = "atif"
    IKTIBAS = "iktibas"
    IMA = "ima"
    KOK = "kok"
    LEMMA = "lemma"
    KONU = "konu"
    BENZER_AYET = "benzer_ayet"
    ANLAMSAL = "anlamsal"


class XrefStatus(StrEnum):
    ADAY = "aday"
    ONAYLI = "onayli"
    RED = "red"


class XrefOrigin(StrEnum):
    HAT = "hat"
    EDITOR = "editor"
    KULLANICI_OYU = "kullanici_oyu"


class UnitKind(StrEnum):
    AYET = "ayet"
    MEAL = "meal"
    TEFSIR = "tefsir"
    RISALE = "risale"
    HADIS = "hadis"
    HADIS_CEVIRI = "hadis_ceviri"
    KITAP = "kitap"


class UnitStatus(StrEnum):
    ETKIN = "etkin"
    KULLANIM_DISI = "kullanim_disi"


class MetinDurumu(StrEnum):
    TASLAK = "taslak"
    INCELEMEDE = "incelemede"
    ONAYLI = "onayli"


class IncelemeDurumu(StrEnum):
    ACIK = "acik"
    ONAYLANDI = "onaylandi"
    REDDEDILDI = "reddedildi"
    GERI_ALINDI = "geri_alindi"


class SurumDurumu(StrEnum):
    HAZIRLANIYOR = "hazirlaniyor"
    DOGRULANDI = "dogrulandi"
    YAYINLANDI = "yayinlandi"
    BASARISIZ = "basarisiz"
    GERI_CEKILDI = "geri_cekildi"
