"""kaikki dokumlerinden yapisal etimoloji kaniti (K-51 madde 9 (b); Kok ve lemma §5 adim 4).

Girdi `data/gelen/kaikki-tr/<tarih>/` dokumleridir (Turkce `.jsonl.gz`, Osmanlica `.jsonl`; satir
basina bir madde). Dokumler guvenilmeyen veridir: yalniz `json.loads` ile okunur. Yalniz ESLEME ve
madde baglantisi saklanir; sozluk metni (tanim, `etymology_text`) saklanmaz.

YAPISAL KANIT (bir `Kanit`) yalniz sablonlardan gelir:

* `root` sablonu, `args['2'] == 'ar'`: kok harfleri `args['3']` ve sonrasi (bosluklu tek dizi ya da
  ayri argumanlar);
* `bor`, `bor+`, `lbor`, `slbor`, `der`, `der+`, `inh`, `inh+`, `calque` sablonu, `args['2'] ==
  'ar'`: etimon `args['3']`; `args['2'] == 'ota'`: Osmanlica baglanti bicimi;
* `ety` ve `etymon` agac sablonlari: `args['3']` icindeki `ar:ETIMON` (etimon) ve `ota:BICIM`
  (Osmanlica baglanti).

Serbest metindeki "Arabic" sozcugu KANIT DEGILDIR: yalniz `Madde.zayif` bayragini kaldirir
(politika bunu en fazla aday yapar). Inflection (`form_of`) maddeleri sozluk maddesi sayilmaz.
"""

import gzip
import json
import re
import unicodedata
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.normalize.turkish import lower_turkish

DIL_TR: Final = "tr"
DIL_OTA: Final = "ota"
KOK_SABLONU: Final = "root"
KAYNAK_SABLONLARI: Final = frozenset(
    {"bor", "bor+", "lbor", "slbor", "der", "der+", "inh", "inh+", "calque"}
)
AGAC_SABLONLARI: Final = frozenset({"ety", "etymon"})
TUR_KOK: Final = "kok"
TUR_ETIMON: Final = "etimon"

_ARAPCA_ETIMON: Final = re.compile(r"(?:^|[\s<])ar:([^\s<>]+)")
_OSMANLICA_BICIM: Final = re.compile(r"(?:^|[\s<])ota:([^\s<>]+)")
_ARAPCA_YAZI: Final = re.compile("[؀-ۿݐ-ݿ]")
_ARAPCA_HARF: Final = re.compile("[ء-يٱ]")
_HAREKE: Final = re.compile("[ً-ٰٟـ]")


@dataclass(frozen=True)
class Kanit:
    """Bir sablondan gelen yapisal kanit: kok harfleri ya da Arapca etimon bicimi."""

    tur: str  # TUR_KOK | TUR_ETIMON
    alan: str  # `etymology_templates.<sablon>`
    deger: str  # kok: bosluklu harf dizisi; etimon: Arapca bicim


@dataclass(frozen=True)
class Madde:
    """Bir kaikki maddesinin eslemeye yarayan ozeti (sozluk metni yok)."""

    sozcuk: str
    dil: str
    pos: str
    kanitlar: tuple[Kanit, ...] = ()
    osmanlica: tuple[str, ...] = ()  # `ota:` baglanti bicimleri (yapisal zincir)
    zayif: bool = False  # serbest metinde "Arabic" geciyor (kanit degil)

    @property
    def yapisal(self) -> bool:
        return bool(self.kanitlar)


def osmanlica_anahtari(bicim: str) -> str:
    """Osmanlica baglanti anahtari: hareke ve uzatma isaretleri silinmis, NFC."""
    return unicodedata.normalize("NFC", _HAREKE.sub("", bicim.strip()))


def _etimon_temizle(ham: str) -> str | None:
    deger = ham.split("<", 1)[0].strip()
    return deger if deger and _ARAPCA_YAZI.search(deger) else None


def _kok_harfleri(args: Mapping[str, object]) -> str | None:
    numarali = [(int(k), str(v)) for k, v in args.items() if k.isascii() and k.isdigit()]
    parcalar = [v for n, v in sorted(numarali) if n >= 3]
    harfler = _ARAPCA_HARF.findall(" ".join(parcalar))
    return " ".join(harfler) if harfler else None


def madde_cikar(kayit: Mapping[str, object], dil: str) -> Madde | None:
    """Ham kaikki satirindan `Madde`; sozluk maddesi olmayan satir (cekim bicimi) icin None."""
    sozcuk = kayit.get("word")
    pos = kayit.get("pos")
    if not isinstance(sozcuk, str) or not isinstance(pos, str):
        return None
    anlamlar = kayit.get("senses")
    if (
        isinstance(anlamlar, list)
        and anlamlar
        and all(isinstance(a, dict) and "form_of" in a for a in anlamlar)
    ):
        return None  # cekim bicimi: kendi etimolojisi yok, homograf sayilmaz
    kanitlar: list[Kanit] = []
    osmanlica: list[str] = []
    sablonlar = kayit.get("etymology_templates")
    for sablon in sablonlar if isinstance(sablonlar, list) else []:
        if not isinstance(sablon, dict):
            continue
        ad = sablon.get("name")
        args = sablon.get("args")
        if not isinstance(ad, str) or not isinstance(args, dict):
            continue
        alan = f"etymology_templates.{ad}"
        kaynak_dil = args.get("2")
        if ad == KOK_SABLONU and kaynak_dil == "ar":
            harfler = _kok_harfleri(args)
            if harfler is not None:
                kanitlar.append(Kanit(TUR_KOK, alan, harfler))
        elif ad in KAYNAK_SABLONLARI:
            ham = args.get("3")
            if not isinstance(ham, str):
                continue
            if kaynak_dil == "ar":
                etimon = _etimon_temizle(ham)
                if etimon is not None:
                    kanitlar.append(Kanit(TUR_ETIMON, alan, etimon))
            elif kaynak_dil == DIL_OTA and _ARAPCA_YAZI.search(ham):
                osmanlica.append(ham.split("<", 1)[0].strip())
        elif ad in AGAC_SABLONLARI:
            ham = args.get("3")
            if not isinstance(ham, str):
                continue
            for bulunan in _ARAPCA_ETIMON.findall(ham):
                etimon = _etimon_temizle(bulunan)
                if etimon is not None:
                    kanitlar.append(Kanit(TUR_ETIMON, alan, etimon))
            for bulunan in _OSMANLICA_BICIM.findall(ham):
                bicim = bulunan.split("<", 1)[0].strip()
                if bicim:
                    osmanlica.append(bicim)
    metin = kayit.get("etymology_text")
    zayif = isinstance(metin, str) and "Arabic" in metin
    return Madde(
        sozcuk,
        dil,
        pos,
        tuple(dict.fromkeys(kanitlar)),
        tuple(dict.fromkeys(osmanlica)),
        zayif,
    )


@dataclass
class KaikkiIndeksi:
    """Turkce maddeleri (anahtar `lower_turkish(sozcuk)`) ve Osmanlica maddeleri (anahtar
    `osmanlica_anahtari`) tutar; `surum` kaynak kaydinin surumudur."""

    surum: str
    tr: dict[str, list[Madde]] = field(default_factory=dict)
    ota: dict[str, list[Madde]] = field(default_factory=dict)

    def ekle(self, madde: Madde) -> None:
        if madde.dil == DIL_OTA:
            self.ota.setdefault(osmanlica_anahtari(madde.sozcuk), []).append(madde)
        else:
            self.tr.setdefault(lower_turkish(madde.sozcuk), []).append(madde)

    def tr_maddeleri(self, lemma: str) -> list[Madde]:
        return self.tr.get(lemma, [])

    def osmanlica_maddeleri(self, bicim: str, pos: str) -> list[Madde]:
        """`bicim` ile ayni anahtarli, ayni sozcuk turundeki Osmanlica maddeler."""
        return [m for m in self.ota.get(osmanlica_anahtari(bicim), []) if m.pos == pos]


def _satirlar(yol: Path) -> Iterator[object]:
    ac = gzip.open if yol.name.endswith(".gz") else open
    try:
        with ac(yol, "rt", encoding="utf-8") as dosya:
            for satir in dosya:
                if satir.strip():
                    yield json.loads(satir)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, EOFError):
        raise GirdiHatasi(f"kaikki dokumu okunamadi: {yol.name}") from None


def dokum_oku(yol: Path, dil: str, indeks: KaikkiIndeksi) -> int:
    """Dokumu satir satir okur, maddeleri indekse ekler; eklenen madde sayisini dondurur."""
    beklenen = {DIL_TR: "tr", DIL_OTA: "ota"}[dil]
    sayi = 0
    for kayit in _satirlar(yol):
        if not isinstance(kayit, dict) or kayit.get("lang_code") != beklenen:
            continue
        madde = madde_cikar(kayit, dil)
        if madde is not None:
            indeks.ekle(madde)
            sayi += 1
    return sayi
