"""zeyrek lemmatizasyonu (Kok ve lemma §5 adim 3): enjekte edilebilir arayuz.

`Lemmatizer` bir protokoldur; testler sahte bir lemmatizer verir, gercek kosu `ZeyrekLemmatizer`
kullanir (`--extra turkce`). Cikti, bicimin butun cozumlerinin `(lemma, sozcuk turu)` kumesidir;
lemma Turkce kucuk harfe (acik eslemeyle) cevrilir. `bilinmiyor`: hicbir cozum yok ya da yalniz
`Unk` var.

Sozcuk turu, cozumun SON turu degil LEMMANIN turudur (zeyrek biciminin koseli parantez blogu:
`[okumak:Verb] ...`): `okuyan` icin son tur `Noun` olsa da lemma `okumak` bir fiildir ve kaikki
maddesi de fiildir. Blok okunamazsa cozumun `pos` alani kullanilir.

PYTHONHASHSEED DUYARLILIGI (A18 inceleme bulgusu 1): zeyrek'in
`calculate_phonetic_attributes` islevi `functools.lru_cache` ile ayni DEGISTIRILEBILIR kumeyi
dondurur; cagiranlar (`morphotactics` govde uretimi, `rulebasedanalyzer.advance`) kumeyi yerinde
degistirir (`add`, `discard`). Ayni telaffuzlu maddeler (ad ve fiil) birbirinin ozelligini kirletir
ve sonuc sozluk maddelerinin KURULUM SIRASINA baglanir. Kurulum sirasi `RootLexicon.items =
list(set)` oldugundan karma tohumuna (`PYTHONHASHSEED`) baglidir: ayni sozcuk listesinde tohuma gore
11-43 bicim farkli cozumlenir, kimi yaygin sozcukler `Unk` doner. `ZeyrekLemmatizer` bu yuzden (1)
o islevi her cagrida KOPYA dondurecek sekilde sarar (kirlenme biter) ve (2) sozluk maddelerini `id_`
ile, madde ozelliklerini adla SIRALI yineletir (kalan sira bagimliliklari kapanir). Kalan tohum
duyarliligi (varsa) manifestte `python_hash_seed` ile ve bir UYARI ile gorunur
(`hash_tohumu_uyarisi`); kesin cozum `PYTHONHASHSEED=0` ile kosmaktir.

zeyrek `logging` ile her cozumde bir `APPENDING RESULT` iletisi yazar; sarmalayici o kaydediciyi
susturur ve her cagrida stdout'u da yakalar. `NLTK_DATA` zeyrek'ten ONCE ayarlanir (proje ici
`data/gelen/nltk-punkt/<tarih>/nltk_data`).
"""

import contextlib
import functools
import importlib
import io
import logging
import os
import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final, Protocol

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


class _SiraliOzellikler(set):  # type: ignore[type-arg]
    """Sozluk maddesi kok ozellikleri: kume ama yineleme ozellik ADIYLA sirali (karmadan bagimsiz).

    zeyrek `for attr in madde.attributes` ile govde degisimlerini (ornegin `Doubling` ve `Voicing`)
    sirayla uygular; sira degisince ayni maddeden farkli govdeler cikar.
    """

    def __iter__(self) -> Iterator[object]:
        return iter(sorted(super().__iter__(), key=lambda a: str(getattr(a, "name", a))))


def _ozellik_hesabini_kopyalat() -> None:
    """`calculate_phonetic_attributes` sonucunu her cagrida yeni kume yapar (kirlenmeyi onler)."""
    ozellikler: Any = importlib.import_module("zeyrek.attributes")
    islev = ozellikler.calculate_phonetic_attributes
    if getattr(islev, "_mutalaa_kopyalar", False):
        return

    @functools.wraps(islev)
    def kopyalayan(*args: object, **kwargs: object) -> set[object]:
        return set(islev(*args, **kwargs))

    kopyalayan._mutalaa_kopyalar = True  # type: ignore[attr-defined]
    for ad in ("zeyrek.attributes", "zeyrek.morphotactics", "zeyrek.rulebasedanalyzer"):
        modul: Any = importlib.import_module(ad)
        if getattr(modul, "calculate_phonetic_attributes", None) is not None:
            modul.calculate_phonetic_attributes = kopyalayan


def _sirali_sozluk(zeyrek: object) -> object:
    """zeyrek varsayilan sozlugu; madde ve ozellik dizilimi karmadan bagimsiz (sirali) olur."""
    lexicon = importlib.import_module("zeyrek.lexicon")

    class SiraliSozluk(lexicon.RootLexicon):  # type: ignore[name-defined, misc]
        @property
        def items(self) -> list[object]:
            return sorted(self.item_set, key=lambda madde: str(madde.id_))

    sozluk = lexicon.RootLexicon.default_text_dictionaries()
    sozluk.__class__ = SiraliSozluk
    for madde in sozluk.item_set:
        madde.attributes = _SiraliOzellikler(madde.attributes)
    return sozluk


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
        _ozellik_hesabini_kopyalat()
        cozucu_sinifi: Any = zeyrek.MorphAnalyzer
        self._cozucu = cozucu_sinifi(lexicon=_sirali_sozluk(zeyrek))
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


HASH_TOHUMU_ORTAM: Final = "PYTHONHASHSEED"
HASH_TOHUMU_BEKLENEN: Final = "0"


def hash_tohumu() -> str:
    """Kosunun `PYTHONHASHSEED` degeri (ayarsizsa `rastgele`); manifest ve rapor icin."""
    return os.environ.get(HASH_TOHUMU_ORTAM, "rastgele")


def hash_tohumu_uyarisi(tohum: str | None = None) -> str | None:
    """`PYTHONHASHSEED=0` degilse uyari metni (cikis kodunu etkilemez); `0` ise `None`."""
    deger = hash_tohumu() if tohum is None else tohum
    if deger == HASH_TOHUMU_BEKLENEN:
        return None
    return (
        f"UYARI: {HASH_TOHUMU_ORTAM}={deger}; zeyrek ciktisi karma tohumuna duyarlidir ve kosular"
        f" arasi degisebilir. Tekrarlanabilir uretim icin"
        f" {HASH_TOHUMU_ORTAM}={HASH_TOHUMU_BEKLENEN}"
        " ile calistirin."
    )


def zeyrek_surumu() -> str | None:
    """Kurulu zeyrek surumu (yoksa None); manifest ayrintilari icin."""
    from importlib import metadata

    try:
        return metadata.version("zeyrek")
    except metadata.PackageNotFoundError:
        return None
