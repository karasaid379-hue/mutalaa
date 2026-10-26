"""Paylasilan enum degerleri (A06.2).

Degerler `packages/content-schema/enums.json` dosyasindaki etiketlerdir ve bildirim sirasi
JSON sirasidir. Sira anlamlidir (`serbest` < `bekliyor` < `ic_kullanim` < `kapali`). Deger
eklemek ya da sirayi degistirmek once JSON'a, sonra dort dile ayni degisiklikte girer;
`tests/test_enums.py` bu siniflari JSON'a karsi sinar.
"""

from enum import StrEnum


class LicenseStatus(StrEnum):
    """Kaynagin lisans durumu; sira kisitliligi artar (kapi en kisitlayiciyi secer)."""

    SERBEST = "serbest"
    BEKLIYOR = "bekliyor"
    IC_KULLANIM = "ic_kullanim"
    KAPALI = "kapali"

    def kisitlilik_sirasi(self) -> int:
        """Bildirim sirasindaki konum: 0 (`serbest`) en az, 3 (`kapali`) en cok kisitlidir."""
        return tuple(type(self)).index(self)


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
