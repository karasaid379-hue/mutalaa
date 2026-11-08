"""`units.jsonl` okuma ve yazma (normalize, anchor ve qa adimlari; Icerik hatti §5).

Satir bicimi `ingest/base.py::units_satiri` ile ayni kurallara uyar: anahtarlar sirali, kompakt
ayiricilar, ASCII kacisli (bir editor NFC uygulayip metni degistirmesin), satir sonu yalniz LF,
zaman damgasi yok. Okuma katidir: yinelenen anahtar, ondalik sayi, NaN, Infinity, CR ve UTF-8
olmayan bayt girdi hatasidir (cikis 2).

Hata iletileri yalniz dosya etiketi, satir numarasi ve alan adi tasir; satir icerigi asla
(Icerik hatti §7).
"""

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from mutalaa_pipeline import lineage
from mutalaa_pipeline.anchor import AnchorError, parse, sort_key
from mutalaa_pipeline.export.ortak import GirdiHatasi, kati_json
from mutalaa_pipeline.lineage import KELIMELER_ADI, UNITS_ADI

if TYPE_CHECKING:
    from mutalaa_pipeline.runctx import RunContext

CR: Final = b"\r"
LF: Final = b"\n"


@dataclass(frozen=True)
class Satir:
    """`units.jsonl` satiri. `veri` ayristirilmis nesnedir; alanlar tip denetimli okunur."""

    etiket: str
    no: int  # 1 tabanli satir numarasi
    veri: dict[str, object]

    def _hata(self, alan: str, neden: str) -> GirdiHatasi:
        return GirdiHatasi(f"{self.etiket}: satir {self.no}: '{alan}' {neden}")

    def var(self, alan: str) -> bool:
        return alan in self.veri

    def metin(self, alan: str) -> str:
        deger = self.veri.get(alan)
        if not isinstance(deger, str):
            raise self._hata(alan, "metin degil ya da yok")
        return deger

    def sayi(self, alan: str) -> int:
        deger = self.veri.get(alan)
        if not isinstance(deger, int) or isinstance(deger, bool):
            raise self._hata(alan, "tam sayi degil ya da yok")
        return deger

    def nesne(self, alan: str) -> dict[str, object]:
        deger = self.veri.get(alan)
        if not isinstance(deger, dict):
            raise self._hata(alan, "nesne degil ya da yok")
        return deger


def satir_baytlari(satir: Mapping[str, object]) -> bytes:
    """Bir satirin kanonik baytlari: sirali anahtar, kompakt, ASCII kacisli, LF ile biter."""
    metin = json.dumps(satir, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return (metin + "\n").encode("utf-8")


def satirlari_oku(veri: bytes, etiket: str) -> list[Satir]:
    """`units.jsonl` baytlarini kati bicimde okur; her satir bir JSON nesnesidir."""
    if not veri or not veri.endswith(LF):
        raise GirdiHatasi(f"{etiket}: bos ya da son satir LF ile bitmiyor")
    if CR in veri:
        raise GirdiHatasi(f"{etiket}: CR (0x0D) var")
    satirlar: list[Satir] = []
    for no, ham in enumerate(veri[:-1].split(LF), start=1):
        try:
            nesne = kati_json(ham.decode("utf-8"))
        except UnicodeDecodeError:
            raise GirdiHatasi(f"{etiket}: satir {no}: UTF-8 degil") from None
        except GirdiHatasi:
            raise GirdiHatasi(f"{etiket}: satir {no}: JSON gecersiz") from None
        if not isinstance(nesne, dict):
            raise GirdiHatasi(f"{etiket}: satir {no}: nesne degil")
        satirlar.append(Satir(etiket, no, nesne))
    return satirlar


def units_baytlari(satirlar: Iterable[Mapping[str, object]]) -> tuple[bytes, int]:
    """Satirlari capaya gore (okuma sirasi) siralar, tekilligi denetler; (bayt, satir sayisi).

    Her satirda gecerli, tekil bir `anchor` bulunmalidir; aksi halde `GirdiHatasi`.
    """
    sirali = []
    gorulen: set[str] = set()
    for sira, satir in enumerate(satirlar, start=1):
        capa = satir.get("anchor")
        if not isinstance(capa, str):
            raise GirdiHatasi(f"birim {sira}: anchor metin degil ya da yok")
        try:
            ref = parse(capa)
        except AnchorError:
            raise GirdiHatasi(f"birim {sira}: capa gecersiz") from None
        if capa in gorulen:
            raise GirdiHatasi(f"yinelenen capa: {capa}")
        gorulen.add(capa)
        sirali.append((sort_key(ref), satir))
    sirali.sort(key=lambda cift: cift[0])
    veri = b"".join(satir_baytlari(satir) for _, satir in sirali)
    return veri, len(sirali)


def units_yaz(
    ctx: "RunContext", source_id: str, satirlar: Iterable[Mapping[str, object]]
) -> lineage.Cikti:
    """`staged/{kaynak}/{run_id}/units.jsonl` dosyasini yazar (`--dry-run`'da yazmaz)."""
    return satirlari_yaz(ctx, source_id, UNITS_ADI, satirlar)


def kelimeler_yaz(
    ctx: "RunContext", source_id: str, satirlar: Iterable[Mapping[str, object]]
) -> lineage.Cikti:
    """`staged/{kaynak}/{run_id}/words.jsonl` dosyasini yazar (`--dry-run`'da yazmaz).

    Satir bicimi ve siralama `units.jsonl` ile aynidir; her satirin `anchor` degeri tekil bir
    kelime capasidir (`q:{sure}:{ayet}:{kelime}`), sira `sort_key`.
    """
    return satirlari_yaz(ctx, source_id, KELIMELER_ADI, satirlar)


def satirlari_yaz(
    ctx: "RunContext", source_id: str, ad: str, satirlar: Iterable[Mapping[str, object]]
) -> lineage.Cikti:
    """`staged/{kaynak}/{run_id}/{ad}` dosyasini kanonik satirlarla yazar."""
    veri, sayi = units_baytlari(satirlar)
    hedef = ctx.staged_dizin(source_id) / ad
    if not ctx.dry_run:
        hedef.parent.mkdir(parents=True, exist_ok=True)
        hedef.write_bytes(veri)
    return lineage.Cikti(
        yol=lineage.goreli_yol(ctx.veri_kok, hedef),
        sha256=lineage.sha256_bayt(veri),
        satir=sayi,
    )
