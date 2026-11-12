"""QAC ic capraz sayim: `mustafa0x-morfoloji` kopyasi (A17.1, A17.5; K-50).

Kopya `data/gelen/mustafa0x-morfoloji/<tarih>/quran-morphology.txt` altinda duran, guvenilmeyen
VERIDIR (QAC'den turetilmis, Arapca yazili; pakete girmez): yalniz okunur, hicbir sey
calistirilmaz. Dosya yoksa `mustafa0x_oku` `None` doner (CI'da `data/` yoktur): olcum "atlandi"
olarak raporlanir. Dosya varsa ozeti `SHA256SUMS` ile dogrulanir; uyusmazlik `GirdiHatasi`.

Dort sekme ayracli sutun (konum `sure:ayet:kelime:segment`, yazi, TAG, ozellikler); `LEM:` ve
`ROOT:` degerleri Arapca yazilidir. `PREF` ya da `SUFF` bayragi tasimayan segmentler govde
adayidir; kelimenin lemmasi ve koku ilk govde adayindan alinir.

Karsilastirma: QAC lemma ve kok metni Buckwalter'dan cevrilip `kanonik_metin` uygulanmis
(`enrich/morphology.py`) haliyle, kopyadaki metin ise BELLEKTE NFC'ye cevrilerek (ham dosya
degismez) karsilastirilir. Iki duzey: bire bir yazim ve harf iskeleti (`normalize_ar`). Sonuclar
yalniz SAYI ve KIMLIK (`qac_ref`, `letters_bw`, kelime capasi) olarak raporlanir; metin yazilmaz.
"""

import re
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from mutalaa_pipeline.enrich.morphology import Kelime, kelime_capasi
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.normalize import normalize_ar
from mutalaa_pipeline.qa.dogrulama import GELEN, _ozetleri_dogrula, _tarih_klasoru

KAYNAK: Final = "mustafa0x-morfoloji"
DOSYA_ADI: Final = "quran-morphology.txt"
EN_BUYUK_BAYT: Final = 16 << 20
KONUM: Final = re.compile(r"[0-9]{1,3}:[0-9]{1,3}:[0-9]{1,3}:[0-9]{1,3}")
AFIKS_BAYRAKLARI: Final = frozenset({"PREF", "SUFF"})
EN_COK_ORNEK: Final = 20


@dataclass(frozen=True)
class Capraz:
    """Kopyanin kelime duzeyi ozeti."""

    tarih: str
    satir_sayisi: int
    kelimeler: Mapping[tuple[int, int, int], tuple[str | None, str | None]]  # (lemma, kok), NFC
    lem_sayisi: int  # farkli LEM dizgisi (tum segmentler)
    root_sayisi: int


def mustafa0x_oku(veri_kok: Path) -> Capraz | None:
    """En yeni kopya klasorunden kelime basina govde lemmasi ve koku okur; yoksa `None`."""
    klasor = _tarih_klasoru(veri_kok / GELEN / KAYNAK, (DOSYA_ADI,))
    if klasor is None:
        return None
    yol = klasor / DOSYA_ADI
    _ozetleri_dogrula(klasor, KAYNAK, [yol])
    if yol.stat().st_size > EN_BUYUK_BAYT:
        raise GirdiHatasi(f"{KAYNAK}: dosya cok buyuk")
    try:
        metin = yol.read_bytes().decode("utf-8")
    except UnicodeDecodeError:
        raise GirdiHatasi(f"{KAYNAK}: UTF-8 degil") from None
    if "\r" in metin:
        raise GirdiHatasi(f"{KAYNAK}: CR var")
    kelimeler: dict[tuple[int, int, int], tuple[str | None, str | None]] = {}
    lemler: set[str] = set()
    kokler: set[str] = set()
    satir_sayisi = 0
    for no, satir in enumerate(metin.split("\n"), start=1):
        if satir == "":
            continue
        sutunlar = satir.split("\t")
        if len(sutunlar) != 4 or KONUM.fullmatch(sutunlar[0]) is None:
            raise GirdiHatasi(f"{KAYNAK}: satir {no}: bicim gecersiz")
        satir_sayisi += 1
        sure, ayet, kelime, _ = (int(p) for p in sutunlar[0].split(":"))
        belirtecler = sutunlar[3].split("|")
        lem = next((b[4:] for b in belirtecler if b.startswith("LEM:")), None)
        kok = next((b[5:] for b in belirtecler if b.startswith("ROOT:")), None)
        if lem is not None:
            lemler.add(lem)
        if kok is not None:
            kokler.add(kok)
        if AFIKS_BAYRAKLARI & set(belirtecler):
            continue
        anahtar = (sure, ayet, kelime)
        if anahtar not in kelimeler:  # ilk govde adayi
            nfc = unicodedata.normalize
            kelimeler[anahtar] = (
                nfc("NFC", lem) if lem is not None else None,
                nfc("NFC", kok) if kok is not None else None,
            )
    if not satir_sayisi:
        raise GirdiHatasi(f"{KAYNAK}: veri satiri yok")
    return Capraz(klasor.name, satir_sayisi, kelimeler, len(lemler), len(kokler))


@dataclass(frozen=True)
class Karsilastirma:
    """Kelime duzeyi karsilastirma sonucu (yalniz sayi ve kimlik)."""

    karsilastirilan_kelime: int
    kopyada_olmayan_kelime: int
    lemma_ayni: int
    lemma_iskelet_ayni: int  # bire bir farkli, harf iskeleti ayni
    lemma_farkli: int
    kok_ayni: int
    kok_farkli: int
    lemma_farkli_qac_ref: tuple[str, ...]  # sirali, tekil
    kok_farkli_letters_bw: tuple[str, ...]
    ornek_capalar: tuple[str, ...]  # lemma ya da kok farki olan ilk kelime capalari

    def sayilar(self) -> dict[str, int]:
        return {
            "karsilastirilan_kelime": self.karsilastirilan_kelime,
            "kopyada_olmayan_kelime": self.kopyada_olmayan_kelime,
            "lemma_ayni": self.lemma_ayni,
            "lemma_iskelet_ayni": self.lemma_iskelet_ayni,
            "lemma_farkli": self.lemma_farkli,
            "kok_ayni": self.kok_ayni,
            "kok_farkli": self.kok_farkli,
            "lemma_farkli_tekil_lemma": len(self.lemma_farkli_qac_ref),
            "kok_farkli_tekil_kok": len(self.kok_farkli_letters_bw),
        }


def karsilastir(
    kelimeler: Sequence[Kelime],
    lemma_metinleri: Mapping[str, str],
    kok_metinleri: Mapping[str, str],
    capraz: Capraz,
) -> Karsilastirma:
    """QAC kelimelerinin lemma/kok Arapcasini kopyayla karsilastirir.

    `lemma_metinleri`: `qac_ref` -> `lemmas.jsonl` `text` (kanonik); `kok_metinleri`:
    `letters_bw` -> `roots.jsonl` `letters` (aralarindaki U+0020 atilarak karsilastirilir).
    """
    sayac = dict.fromkeys(
        (
            "karsilastirilan",
            "yok",
            "lemma_ayni",
            "lemma_iskelet",
            "lemma_farkli",
            "kok_ayni",
            "kok_farkli",
        ),
        0,
    )
    lemma_farki: set[str] = set()
    kok_farki: set[str] = set()
    ornekler: list[str] = []
    for k in kelimeler:
        govde = k.govde
        if govde.lem is None and govde.kok is None:
            continue
        kopya = capraz.kelimeler.get((k.sure, k.ayet, k.kelime))
        if kopya is None:
            sayac["yok"] += 1
            continue
        sayac["karsilastirilan"] += 1
        fark = False
        if govde.lem is not None:
            beklenen = unicodedata.normalize("NFC", lemma_metinleri[govde.lem])
            if kopya[0] == beklenen:
                sayac["lemma_ayni"] += 1
            elif kopya[0] is not None and normalize_ar(kopya[0]) == normalize_ar(beklenen):
                sayac["lemma_iskelet"] += 1
                lemma_farki.add(govde.lem)
                fark = True
            else:
                sayac["lemma_farkli"] += 1
                lemma_farki.add(govde.lem)
                fark = True
        if govde.kok is not None:
            beklenen_kok = unicodedata.normalize("NFC", kok_metinleri[govde.kok].replace(" ", ""))
            if kopya[1] == beklenen_kok:
                sayac["kok_ayni"] += 1
            else:
                sayac["kok_farkli"] += 1
                kok_farki.add(govde.kok)
                fark = True
        if fark and len(ornekler) < EN_COK_ORNEK:
            ornekler.append(kelime_capasi(k.sure, k.ayet, k.kelime))
    return Karsilastirma(
        karsilastirilan_kelime=sayac["karsilastirilan"],
        kopyada_olmayan_kelime=sayac["yok"],
        lemma_ayni=sayac["lemma_ayni"],
        lemma_iskelet_ayni=sayac["lemma_iskelet"],
        lemma_farkli=sayac["lemma_farkli"],
        kok_ayni=sayac["kok_ayni"],
        kok_farkli=sayac["kok_farkli"],
        lemma_farkli_qac_ref=tuple(sorted(lemma_farki)),
        kok_farkli_letters_bw=tuple(sorted(kok_farki)),
        ornek_capalar=tuple(ornekler),
    )
