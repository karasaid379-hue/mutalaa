"""Degerlendirme seti dosyalari, manifest dogrulamasi, bolme ve dongusellik denetimi (A18.5).

Duzen (git disi): `data/gold/<set>/<surum>/manifest.json` + `ornekler.jsonl`; surum
`YYYY-AA-GG-<ornekler.jsonl SHA-256 ilk 8 hane>` (tarih-kisa ozet). Ayni icerik ayni surumu verir
(idempotent); farkli icerik yeni surum klasoru acar, eskisine dokunulmaz.

K-51 madde 10: her set ve her ornek `sinif` (`altin` | `silver` | `sentetik`), `kaynak`
(source_id, surum, madde ya da satir), `dogrulama_yontemi` ve `uretim_komutu` tasir; eksik alan
`GirdiHatasi`dir (cikis 2). Manifestte `kaynak` listesi her girdisi icin `rol` tasir:

* `kanit`: etiketin dayandigi bagimsiz kaynak. DONGUSELLIK denetimi yalniz bunlara bakar.
* `sozluk`: iki tarafin da kullandigi ortak etiket sozlugu (ornegin kok kimlikleri icin QAC).
  Dongusellik sayilmaz ama rapora "ortak sozluk" notu olarak yazilir.
* `arac`: kanit olmayan ortak arac (ornegin lemmatizer).

Bolme: `sha256("{tohum}:{set}:{ornek_id}")` ilk 8 hanesi 100'e bolumunden kalan 0..39 ise
`gelistirme` (%40, ayar), degilse `dondurulmus` (%60, olcum). Dondurulmus parca ayar icin
kullanilmaz.

Dongusellik (K-51 madde 10): set manifestindeki `kanit` kaynaklari uretimin `kanit` kaynaklariyla
kesisirse `GirdiHatasi` (cikis 2); iletide yalniz kaynak adlari yazilir. Denetim `olcum_turu =
dogruluk` setlerinde zorunludur; `tutarlilik` ve `motor_testi` muaftir.
"""

import hashlib
import json
import re
from collections.abc import Iterable, Mapping, Sequence
from datetime import date
from pathlib import Path
from typing import Final

from mutalaa_pipeline import lineage
from mutalaa_pipeline.export.ortak import GirdiHatasi

SINIFLAR: Final = ("altin", "silver", "sentetik")
ROLLER: Final = ("kanit", "sozluk", "arac")
OLCUM_TURLERI: Final = ("dogruluk", "tutarlilik", "motor_testi")
DONGUSELLIK_MUAF: Final = ("tutarlilik", "motor_testi")
GOLD_KLASORU: Final = "gold"
MANIFEST_ADI: Final = "manifest.json"
ORNEKLER_ADI: Final = "ornekler.jsonl"
SET_ADLARI: Final = ("kok", "lemma", "benzer-ayet", "atif", "iktibas")
GELISTIRME_YUZDE: Final = 40
VARSAYILAN_TOHUM: Final = 20261113
SURUM_DESENI: Final = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}-[0-9a-f]{8}")
ZORUNLU_ORNEK_ALANLARI: Final = ("id", "sinif", "kaynak", "dogrulama_yontemi", "uretim_komutu")
ZORUNLU_MANIFEST_ALANLARI: Final = (
    "set",
    "surum",
    "sinif",
    "olcum_turu",
    "kaynak",
    "dogrulama_yontemi",
    "uretim_komutu",
    "tohum",
    "ornek_sayisi",
    "ornekler_sha256",
)
GELISTIRME: Final = "gelistirme"
DONDURULMUS: Final = "dondurulmus"


def bolme(set_adi: str, ornek_id: str, tohum: int = VARSAYILAN_TOHUM) -> str:
    """`gelistirme` (~%40) ya da `dondurulmus` (%60); ornek kimligi + tohumla deterministik."""
    ozet = hashlib.sha256(f"{tohum}:{set_adi}:{ornek_id}".encode()).hexdigest()
    return GELISTIRME if int(ozet[:8], 16) % 100 < GELISTIRME_YUZDE else DONDURULMUS


def _kaynak_kaydi_dogrula(kayit: object, nerede: str, *, rol_gerekli: bool) -> None:
    if not isinstance(kayit, Mapping):
        raise GirdiHatasi(f"{nerede}: kaynak nesne olmali")
    for alan in ("source_id", "surum", "madde"):
        deger = kayit.get(alan)
        if not isinstance(deger, str) or not deger:
            raise GirdiHatasi(f"{nerede}: kaynak.{alan} dolu metin olmali")
    if rol_gerekli and kayit.get("rol") not in ROLLER:
        raise GirdiHatasi(f"{nerede}: kaynak.rol {', '.join(ROLLER)} degerlerinden biri olmali")


def ornek_dogrula(ornek: Mapping[str, object], nerede: str = "ornek") -> None:
    """Zorunlu alanlar (`sinif`, `kaynak`, `dogrulama_yontemi`, `uretim_komutu`); eksikse hata."""
    for alan in ZORUNLU_ORNEK_ALANLARI:
        if alan not in ornek or ornek[alan] in (None, "", [], {}):
            raise GirdiHatasi(f"{nerede}: zorunlu alan eksik: {alan}")
    if ornek["sinif"] not in SINIFLAR:
        raise GirdiHatasi(f"{nerede}: sinif {', '.join(SINIFLAR)} degerlerinden biri olmali")
    if not isinstance(ornek["id"], str):
        raise GirdiHatasi(f"{nerede}: id metin olmali")
    kaynak = ornek["kaynak"]
    for k in kaynak if isinstance(kaynak, list) else [kaynak]:
        _kaynak_kaydi_dogrula(k, nerede, rol_gerekli=False)
    for alan in ("dogrulama_yontemi", "uretim_komutu"):
        if not isinstance(ornek[alan], str):
            raise GirdiHatasi(f"{nerede}: {alan} metin olmali")


def manifest_dogrula(m: Mapping[str, object]) -> None:
    """Zorunlu manifest alanlari ve degerleri; eksik ya da gecersizse `GirdiHatasi`."""
    for alan in ZORUNLU_MANIFEST_ALANLARI:
        if alan not in m or m[alan] in (None, "", [], {}):
            if alan == "ornek_sayisi" and m.get(alan) == 0:
                continue
            raise GirdiHatasi(f"manifest: zorunlu alan eksik: {alan}")
    if m["sinif"] not in SINIFLAR:
        raise GirdiHatasi(f"manifest: sinif {', '.join(SINIFLAR)} degerlerinden biri olmali")
    if m["olcum_turu"] not in OLCUM_TURLERI:
        raise GirdiHatasi(
            f"manifest: olcum_turu {', '.join(OLCUM_TURLERI)} degerlerinden biri olmali"
        )
    if not isinstance(m["surum"], str) or SURUM_DESENI.fullmatch(m["surum"]) is None:
        raise GirdiHatasi("manifest: surum YYYY-AA-GG-<8 hane ozet> olmali")
    kaynaklar = m["kaynak"]
    if not isinstance(kaynaklar, list):
        raise GirdiHatasi("manifest: kaynak liste olmali")
    for k in kaynaklar:
        _kaynak_kaydi_dogrula(k, "manifest", rol_gerekli=True)
    for alan in ("dogrulama_yontemi", "uretim_komutu"):
        if not isinstance(m[alan], str):
            raise GirdiHatasi(f"manifest: {alan} metin olmali")
    if not isinstance(m["tohum"], int) or isinstance(m["tohum"], bool):
        raise GirdiHatasi("manifest: tohum tam sayi olmali")


# --- dongusellik -------------------------------------------------------------------------


def kanit_kaynaklari(kaynaklar: Iterable[Mapping[str, object]]) -> frozenset[str]:
    return frozenset(str(k["source_id"]) for k in kaynaklar if k.get("rol") == "kanit")


def dongusellik_denetle(
    set_kaynaklari: Iterable[Mapping[str, object]], uretim_kaynaklari: Iterable[str]
) -> None:
    """Set `kanit` kaynaklari ile uretim `kanit` kaynaklari kesisirse `GirdiHatasi` (cikis 2).

    Iletide yalniz kaynak adlari bulunur.
    """
    kesisim = sorted(kanit_kaynaklari(set_kaynaklari) & frozenset(uretim_kaynaklari))
    if kesisim:
        raise GirdiHatasi(
            "dongusellik: set uretimin girdisi olan kaynaktan kurulmus: " + ", ".join(kesisim)
        )


def manifest_dongusellik_denetle(
    manifest: Mapping[str, object], uretim_kaynaklari: Iterable[str]
) -> None:
    """Dongusellik denetimi `olcum_turu = dogruluk` setlerinde zorunludur.

    `tutarlilik` (QAC lemma tutarliligi) ve `motor_testi` (sentetik set: Arapca dizileri uretimle
    ayni Tanzil'den betikle alinir, kapi acmaz) turleri muaftir; manifest bunu `olcum_turu` ile
    belirtir.
    """
    if manifest.get("olcum_turu") in DONGUSELLIK_MUAF:
        return
    kaynaklar = manifest["kaynak"]
    if not isinstance(kaynaklar, list):
        raise GirdiHatasi("manifest: kaynak liste olmali")
    dongusellik_denetle(kaynaklar, uretim_kaynaklari)


# --- dosyalar ----------------------------------------------------------------------------


def _satir_baytlari(ornekler: Sequence[Mapping[str, object]]) -> bytes:
    return b"".join(
        (
            json.dumps(dict(o), ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n"
        ).encode("ascii")
        for o in ornekler
    )


def set_dizini(veri_kok: Path, set_adi: str) -> Path:
    if set_adi not in SET_ADLARI:
        raise GirdiHatasi(f"bilinmeyen set: {set_adi}")
    return veri_kok / GOLD_KLASORU / set_adi


def set_hazirla(
    set_adi: str,
    taslak: Mapping[str, object],
    ornekler: Sequence[Mapping[str, object]],
    *,
    bugun: date | None = None,
) -> tuple[dict[str, object], bytes]:
    """Manifesti (surum, sayilar, ozet) ve `ornekler.jsonl` baytlarini kurar; dosya yazmaz.

    `taslak`: `set`, `surum`, `ornek_sayisi`, `ornekler_sha256` disindaki manifest alanlari.
    """
    for i, o in enumerate(ornekler):
        ornek_dogrula(o, f"ornek {i + 1}")
    baytlar = _satir_baytlari(ornekler)
    ozet = hashlib.sha256(baytlar).hexdigest()
    surum = f"{(bugun or date.today()).isoformat()}-{ozet[:8]}"
    ids = [str(o["id"]) for o in ornekler]
    if len(set(ids)) != len(ids):
        raise GirdiHatasi("ornek kimlikleri tekil degil")
    tohum = taslak.get("tohum", VARSAYILAN_TOHUM)
    if not isinstance(tohum, int):
        raise GirdiHatasi("manifest: tohum tam sayi olmali")
    gel = sum(1 for i in ids if bolme(set_adi, i, tohum) == GELISTIRME)
    manifest: dict[str, object] = {
        **taslak,
        "set": set_adi,
        "surum": surum,
        "ornek_sayisi": len(ornekler),
        "gelistirme_sayisi": gel,
        "dondurulmus_sayisi": len(ornekler) - gel,
        "bolme": {
            "gelistirme_yuzde": GELISTIRME_YUZDE,
            "yontem": (
                "sha256(tohum:set:ornek_id) ilk 8 hane mod 100 < 40: gelistirme, aksi dondurulmus"
            ),
            "dondurulmus_ayar_icin_kullanilmaz": True,
        },
        "ornekler_sha256": ozet,
    }
    manifest_dogrula(manifest)
    return manifest, baytlar


def set_yaz(
    veri_kok: Path,
    set_adi: str,
    taslak: Mapping[str, object],
    ornekler: Sequence[Mapping[str, object]],
    *,
    bugun: date | None = None,
) -> tuple[dict[str, object], Path]:
    """Seti yazar (ayni icerik ayni surum: yeniden yazilmaz); manifesti ve klasoru dondurur."""
    manifest, baytlar = set_hazirla(set_adi, taslak, ornekler, bugun=bugun)
    klasor = set_dizini(veri_kok, set_adi) / str(manifest["surum"])
    if (klasor / ORNEKLER_ADI).is_file():
        if lineage.sha256_dosya(klasor / ORNEKLER_ADI) != manifest["ornekler_sha256"]:
            raise GirdiHatasi("set klasoru var ama icerigi farkli (surum cakismasi)")
        return manifest, klasor
    klasor.mkdir(parents=True, exist_ok=False)
    (klasor / ORNEKLER_ADI).write_bytes(baytlar)
    (klasor / MANIFEST_ADI).write_bytes(
        (json.dumps(manifest, ensure_ascii=True, sort_keys=True, indent=2) + "\n").encode("ascii")
    )
    return manifest, klasor


def son_surum(veri_kok: Path, set_adi: str) -> str | None:
    kok = set_dizini(veri_kok, set_adi)
    if not kok.is_dir():
        return None
    surumler = sorted(
        p.name for p in kok.iterdir() if p.is_dir() and SURUM_DESENI.fullmatch(p.name)
    )
    return surumler[-1] if surumler else None


def set_oku(
    veri_kok: Path, set_adi: str, surum: str | None = None
) -> tuple[dict[str, object], list[dict[str, object]], Path]:
    """Seti okur ve dogrular (manifest, her ornegin zorunlu alanlari, SHA-256); yoksa hata."""
    s = surum or son_surum(veri_kok, set_adi)
    if s is None:
        raise GirdiHatasi(f"{set_adi} seti yok: once --build ile uretin")
    klasor = set_dizini(veri_kok, set_adi) / s
    try:
        manifest = json.loads((klasor / MANIFEST_ADI).read_bytes().decode("utf-8"))
        baytlar = (klasor / ORNEKLER_ADI).read_bytes()
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        raise GirdiHatasi(f"{set_adi} seti okunamadi") from None
    if not isinstance(manifest, dict):
        raise GirdiHatasi(f"{set_adi} manifesti nesne degil")
    manifest_dogrula(manifest)
    if manifest["set"] != set_adi or manifest["surum"] != s:
        raise GirdiHatasi(f"{set_adi} manifesti klasorle tutmuyor")
    if hashlib.sha256(baytlar).hexdigest() != manifest["ornekler_sha256"]:
        raise GirdiHatasi(f"{set_adi} ornekleri manifest ozetiyle tutmuyor")
    ornekler: list[dict[str, object]] = []
    for no, satir in enumerate(baytlar.decode("ascii").splitlines(), start=1):
        try:
            o = json.loads(satir)
        except json.JSONDecodeError:
            raise GirdiHatasi(f"{set_adi} ornek {no}: gecersiz JSON") from None
        if not isinstance(o, dict):
            raise GirdiHatasi(f"{set_adi} ornek {no}: nesne degil")
        ornek_dogrula(o, f"{set_adi} ornek {no}")
        ornekler.append(o)
    if len(ornekler) != manifest["ornek_sayisi"]:
        raise GirdiHatasi(f"{set_adi}: ornek sayisi manifestle tutmuyor")
    return manifest, ornekler, klasor
