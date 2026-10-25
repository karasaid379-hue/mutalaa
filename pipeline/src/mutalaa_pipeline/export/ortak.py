"""Disa aktarim komutlarinin ortak yardimcilari: depo koku, kati JSON okuma, dosya yazimi."""

import json
from pathlib import Path
from typing import Final

KOK_ISARETI: Final = "pnpm-workspace.yaml"


class GirdiHatasi(Exception):
    """Girdi ya da yapilandirma hatasi; komut 2 ile cikar."""


def depo_koku(baslangic: Path | None = None) -> Path:
    """`pnpm-workspace.yaml` dosyasini tasiyan ilk ust klasoru dondurur."""
    yol = (baslangic if baslangic is not None else Path(__file__)).resolve()
    for aday in (yol, *yol.parents):
        if (aday / KOK_ISARETI).is_file():
            return aday
    raise GirdiHatasi(f"depo koku bulunamadi ({KOK_ISARETI} yok)")


def kok_coz(kok: Path | None) -> Path:
    """`--kok` verildiyse onu, verilmediyse depo kokunu dondurur."""
    if kok is None:
        return depo_koku()
    if not kok.is_dir():
        raise GirdiHatasi("--kok bir klasor degil")
    return kok.resolve()


def _ciftler(ciftler: list[tuple[str, object]]) -> dict[str, object]:
    sonuc: dict[str, object] = {}
    for anahtar, deger in ciftler:
        if anahtar in sonuc:
            raise GirdiHatasi(f"yinelenen anahtar: {anahtar}")
        sonuc[anahtar] = deger
    return sonuc


def _ondalik(_metin: str) -> object:
    raise GirdiHatasi("ondalik sayi desteklenmez")


def _sabit(_metin: str) -> object:
    raise GirdiHatasi("NaN ve Infinity desteklenmez")


def kati_json(metin: str) -> object:
    """JSON ayristirir; yinelenen anahtar, ondalik sayi, NaN ve Infinity girdi hatasidir."""
    try:
        sonuc: object = json.loads(
            metin,
            object_pairs_hook=_ciftler,
            parse_float=_ondalik,
            parse_constant=_sabit,
        )
    except json.JSONDecodeError as hata:
        raise GirdiHatasi(f"JSON hatasi: {hata.msg} (sutun {hata.colno})") from hata
    except ValueError as hata:
        # Python'un tam sayi basamak siniri (4300) json.loads'ta ValueError verir.
        raise GirdiHatasi("JSON hatasi: sayi cok uzun") from hata
    except RecursionError as hata:
        raise GirdiHatasi("JSON cok derin") from hata
    return sonuc


def utf8_oku(yol: Path, goreli: str) -> str:
    """Dosyayi bayt olarak okuyup kati UTF-8 ile cozer."""
    try:
        return yol.read_bytes().decode("utf-8")
    except UnicodeDecodeError as hata:
        raise GirdiHatasi(f"{goreli}: UTF-8 degil (bayt {hata.start})") from hata


def ayni_mi(kok: Path, goreli: str, metin: str) -> bool:
    """Diskteki dosya `metin`in UTF-8 baytlarina bayt bayt esitse True."""
    hedef = kok / goreli
    return hedef.is_file() and hedef.read_bytes() == metin.encode("utf-8")


def yaz(kok: Path, goreli: str, metin: str) -> bool:
    """Icerik farkliysa dosyayi yazar (UTF-8, BOM yok, LF); yazildiysa True."""
    if ayni_mi(kok, goreli, metin):
        return False
    hedef = kok / goreli
    hedef.parent.mkdir(parents=True, exist_ok=True)
    hedef.write_text(metin, encoding="utf-8", newline="\n")
    return True
