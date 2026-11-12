"""zeyrek lemmatizasyonu (Kok ve lemma §5 adim 3): enjekte edilebilir arayuz.

`Lemmatizer` bir protokoldur; testler sahte bir lemmatizer verir, gercek kosu `ZeyrekLemmatizer`
kullanir (`--extra turkce`). Cikti, bicimin butun cozumlerinin `(lemma, sozcuk turu)` kumesidir;
lemma Turkce kucuk harfe (acik eslemeyle) cevrilir. `bilinmiyor`: hicbir cozum yok ya da yalniz
`Unk` var.

Sozcuk turu, cozumun SON turu degil LEMMANIN turudur (zeyrek biciminin koseli parantez blogu:
`[okumak:Verb] ...`): `okuyan` icin son tur `Noun` olsa da lemma `okumak` bir fiildir ve kaikki
maddesi de fiildir. Blok okunamazsa cozumun `pos` alani kullanilir.

zeyrek `logging` ile her cozumde bir `APPENDING RESULT` iletisi yazar; sarmalayici o kaydediciyi
susturur ve her cagrida stdout'u da yakalar. `NLTK_DATA` zeyrek'ten ONCE ayarlanir (proje ici
`data/gelen/nltk-punkt/<tarih>/nltk_data`).
"""

import contextlib
import importlib
import io
import logging
import os
import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Protocol

from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.normalize.turkish import lower_turkish

BILINMEYEN: Final = "Unk"
_LEMMA_BLOGU: Final = re.compile(r"\[(?P<lemma>[^:\]]+):(?P<tur>[A-Za-z]+)(?:,[A-Za-z]+)*\]")
_DUZELTME_KATLAMA: Final = str.maketrans({"â": "a", "î": "i", "û": "u"})


@dataclass(frozen=True, order=True)
class Cozum:
    lemma: str
    pos: str


@dataclass(frozen=True)
class Analiz:
    """Bir bicimin butun cozumleri (`Unk` ayiklanmis)."""

    cozumler: frozenset[Cozum]

    @property
    def bilinmiyor(self) -> bool:
        return not self.cozumler

    @property
    def lemmalar(self) -> frozenset[str]:
        return frozenset(c.lemma for c in self.cozumler)

    def poslar(self, lemma: str) -> frozenset[str]:
        return frozenset(c.pos for c in self.cozumler if c.lemma == lemma)


class Lemmatizer(Protocol):
    def analiz(self, bicim: str) -> Analiz:
        """`bicim` kesmesiz Turkce kucuk harf bicimdir (`Parca.lemmatizer_girdisi`)."""
        ...


def _cozumleri_topla(gruplar: Iterable[Iterable[object]]) -> frozenset[Cozum]:
    sonuc: set[Cozum] = set()
    for grup in gruplar:
        for parse in grup:
            lemma = str(getattr(parse, "lemma", BILINMEYEN))
            pos = str(getattr(parse, "pos", BILINMEYEN))
            blok = _LEMMA_BLOGU.search(str(getattr(parse, "formatted", "")))
            if blok is not None:
                pos = blok.group("tur")
            if lemma == BILINMEYEN or pos == BILINMEYEN:
                continue
            sonuc.add(Cozum(lower_turkish(lemma), pos))
    return frozenset(sonuc)


class ZeyrekLemmatizer:
    """zeyrek `MorphAnalyzer` sarmalayicisi (onbellekli; `NLTK_DATA` proje ici klasor).

    Cozumsuz bicimde duzeltme isaretli (`a`, `i`, `u` uzerindeki sapka) harfler katlanmis bicim de
    denenir. zeyrek yalniz bu sinifin ilk ornegi kurulurken ice aktarilir.
    """

    def __init__(self, nltk_data: Path | None = None) -> None:
        if nltk_data is not None:
            if not nltk_data.is_dir():
                raise GirdiHatasi("NLTK_DATA klasoru yok (data/gelen/nltk-punkt/<tarih>/nltk_data)")
            os.environ["NLTK_DATA"] = str(nltk_data)
        try:
            import zeyrek
        except ImportError:
            raise GirdiHatasi("zeyrek yok: uv run --extra turkce ile calistirin") from None
        if (
            nltk_data is not None
        ):  # zeyrek (ve nltk) daha once ice aktarildiysa ortam degiskeni yetmez
            nltk = importlib.import_module("nltk")
            nltk.data.path.insert(0, str(nltk_data))
        logging.getLogger("zeyrek").setLevel(logging.ERROR)
        logging.getLogger("zeyrek.rulebasedanalyzer").setLevel(logging.ERROR)
        self._cozucu = zeyrek.MorphAnalyzer()
        self._onbellek: dict[str, Analiz] = {}

    def _coz(self, bicim: str) -> frozenset[Cozum]:
        with contextlib.redirect_stdout(io.StringIO()):
            return _cozumleri_topla(self._cozucu.analyze(bicim))

    def analiz(self, bicim: str) -> Analiz:
        onbellekte = self._onbellek.get(bicim)
        if onbellekte is not None:
            return onbellekte
        cozumler = self._coz(bicim)
        katlanmis = bicim.translate(_DUZELTME_KATLAMA)
        if not cozumler and katlanmis != bicim:
            cozumler = self._coz(katlanmis)
        sonuc = Analiz(cozumler)
        self._onbellek[bicim] = sonuc
        return sonuc


def zeyrek_surumu() -> str | None:
    """Kurulu zeyrek surumu (yoksa None); manifest ayrintilari icin."""
    from importlib import metadata

    try:
        return metadata.version("zeyrek")
    except metadata.PackageNotFoundError:
        return None
