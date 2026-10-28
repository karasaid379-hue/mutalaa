"""JSON satirli gunluk (`data/logs/{run_id}.jsonl`) ve sizinti korumasi (Icerik hatti §7).

SIZINTI KURALI: gunluk, rapor ve hata iletileri yalniz capa, satir no, bayt araligi, sha256 ve
U+XXXX tasir; satir icerigi ve baglanti dizesi asla. Bu modul son savunmadir: ASCII disi ya da
baglanti dizesine benzeyen metin degerleri yazilmadan once maskelenir.
"""

import hashlib
import json
import re
import threading
from collections.abc import Callable, Iterable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

SEVIYELER: Final = {"DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40}
MASKE: Final = "[gizli]"
EN_UZUN_DEGER: Final = 200

# scheme://...@ biciminde kullanici bilgisi tasiyan baglanti dizesi
BAGLANTI_DESENI: Final = re.compile(r"[A-Za-z][A-Za-z0-9+.-]*://[^\s\"']*@[^\s\"']*")
# anahtar=deger bicimindeki libpq baglanti dizesinde parola
PAROLA_DESENI: Final = re.compile(r"(?i)\bpassword\s*=\s*[^\s\"']+")

Saat = Callable[[], datetime]
Deger = int | float | bool | None | str


def simdi() -> datetime:
    return datetime.now(UTC)


def zaman_metni(an: datetime) -> str:
    return an.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.") + f"{an.microsecond // 1000:03d}Z"


def maskele(metin: str, gizliler: Iterable[str] = ()) -> str:
    """Bilinen gizli degerleri ve baglanti dizesi desenlerini maskeler."""
    sonuc = metin
    for gizli in gizliler:
        if gizli:
            sonuc = sonuc.replace(gizli, MASKE)
    sonuc = BAGLANTI_DESENI.sub(MASKE, sonuc)
    return PAROLA_DESENI.sub(MASKE, sonuc)


def guvenli_deger(deger: object, gizliler: Iterable[str] = ()) -> object:
    """Sayilar ve bool oldugu gibi; metin yalniz yazdirilabilir ASCII ve kisa ise.

    Aksi hâlde metnin yerine uzunlugu ve SHA-256 on eki yazilir (icerik sizmasin).
    """
    if deger is None or isinstance(deger, bool | int | float):
        return deger
    if isinstance(deger, str):
        temiz = maskele(deger, gizliler)
        if len(temiz) <= EN_UZUN_DEGER and all(" " <= c <= "~" for c in temiz):
            return temiz
        ozet = hashlib.sha256(deger.encode("utf-8", "surrogatepass")).hexdigest()[:12]
        return f"[metin:{len(deger)}:{ozet}]"
    if isinstance(deger, Path):
        return guvenli_deger(deger.as_posix(), gizliler)
    if isinstance(deger, Mapping):
        return {
            str(guvenli_deger(str(k), gizliler)): guvenli_deger(v, gizliler)
            for k, v in deger.items()
        }
    if isinstance(deger, list | tuple):
        return [guvenli_deger(v, gizliler) for v in deger]
    return f"[{type(deger).__name__}]"


def ileti_temizle(metin: str, gizliler: Iterable[str] = (), *, en_uzun: int = 300) -> str:
    """Hata iletisini konsola yazmadan once temizler.

    Gizli degerler maskelenir; ASCII disi karakter varsa (icerik olabilir) ileti yerine uzunlugu
    ve SHA-256 on eki yazilir.
    """
    temiz = maskele(metin, gizliler)[:en_uzun]
    if all(" " <= c <= "~" for c in temiz):
        return temiz
    ozet = hashlib.sha256(metin.encode("utf-8", "surrogatepass")).hexdigest()[:12]
    return f"[ileti gizlendi:{len(metin)}:{ozet}]"


def json_baytlari(veri: object) -> bytes:
    """Kanonik JSON: anahtarlar sirali, ASCII, LF ile biter."""
    return (json.dumps(veri, ensure_ascii=True, sort_keys=True, indent=2) + "\n").encode("utf-8")


class Gunluk:
    """`{klasor}/{run_id}.jsonl` dosyasina JSON satirlari ekler."""

    def __init__(
        self,
        klasor: Path,
        run_id: str,
        adim: str,
        *,
        duzey: str = "INFO",
        saat: Saat = simdi,
        gizliler: Iterable[str] = (),
    ) -> None:
        self.yol = klasor / f"{run_id}.jsonl"
        self._run_id = run_id
        self._adim = adim
        self._esik = SEVIYELER[duzey]
        self._saat = saat
        self._gizliler = tuple(gizliler)
        self._kilit = threading.Lock()

    def yaz(
        self,
        duzey: str,
        olay: str,
        *,
        source_id: str | None = None,
        sayilar: Mapping[str, Deger] | None = None,
    ) -> None:
        if duzey not in SEVIYELER:
            raise ValueError("bilinmeyen gunluk duzeyi")
        if SEVIYELER[duzey] < self._esik:
            return
        kayit = {
            "ts": zaman_metni(self._saat()),
            "level": duzey,
            "run_id": self._run_id,
            "source_id": guvenli_deger(source_id, self._gizliler),
            "adim": self._adim,
            "olay": guvenli_deger(olay, self._gizliler),
            "sayilar": guvenli_deger(dict(sayilar or {}), self._gizliler),
        }
        satir = json.dumps(kayit, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n"
        with self._kilit:
            self.yol.parent.mkdir(parents=True, exist_ok=True)
            with self.yol.open("a", encoding="utf-8", newline="\n") as dosya:
                dosya.write(satir)

    def bilgi(self, olay: str, **sayilar: Deger) -> None:
        self.yaz("INFO", olay, sayilar=sayilar)

    def uyari(self, olay: str, **sayilar: Deger) -> None:
        self.yaz("WARNING", olay, sayilar=sayilar)

    def hata(self, olay: str, **sayilar: Deger) -> None:
        self.yaz("ERROR", olay, sayilar=sayilar)
