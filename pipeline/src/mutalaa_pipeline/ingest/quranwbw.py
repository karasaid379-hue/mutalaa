"""QuranWBW Turkce kelime anlami alimi (A17.6, K-19, K-50): `data/gelen` -> `data/raw` -> staged.

`mutalaa ingest quranwbw-tr`:

1. `data/gelen/quranwbw-tr/<YYYY-AA-GG>/6.json` dosyasini BAYT olarak okur (en cok 16 MB) ve
   `quranwbw.lock.json` ile karsilastirir (boyut ve SHA-256). Tutmazsa cikis 2 ve "kilit
   guncellenerek (/karar) alinir" uyarisi; `data/raw`'a hicbir sey yazilmaz. Kilit yalniz
   `/karar` ile degisir; ilk degerleri `--kilit-oner` yazdirir (hicbir sey yazmaz). Dosya yalniz
   VERI olarak okunur.
2. Dosya kati UTF-8 JSON'dur (yinelenen anahtar, ondalik sayi ve NaN hatadir): sure -> ayet ->
   `[[kelime anlamlari]]` (her ayet tek elemanli bir liste, o eleman kelime basina bir metin).
   Kelime numarasi listedeki konumdur (1 tabanli; QAC konumu, K-43 madde 1). Sure, ayet ve kelime
   capalari `mutalaa_pipeline.anchor` ile bicimlenir ve dogrulanir (`q:{s}:{a}:{k}`).
3. Her anlam girdisine `anchor.metin.kanonik_metin` BIR KEZ uygulanir (kendi urettigimiz
   cikarilmis metin: ilk kayit adimlari ve NFC yalniz burada; K-26, metin-butunlugu becerisi) ve
   `provenance` yazilir: ham dosya ozeti, dosya ici konum (JSON isaretcisi `/sure/ayet/0/indeks`) ve
   cikarici surumu. Bos girdi (kanonik hal dahil) hatadir (cikis 2).
4. Ham kopya `data/raw/quranwbw-tr/<tarih>/` altina `fetch.json` ile yazilir (`data/raw`
   degismez); staged cikti `meanings.jsonl`'dir (capaya gore sirali, ASCII kacisli).

Hata iletileri yalniz sure/ayet/kelime numarasi, sayi ve kisaltilmis ozet tasir; anlam metni asla.
"""

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from mutalaa_pipeline import cikis, lineage, sources
from mutalaa_pipeline.anchor import AnchorError, AnchorRef, Q, parse
from mutalaa_pipeline.anchor import format as anchor_format
from mutalaa_pipeline.anchor.metin import kanonik_metin
from mutalaa_pipeline.export.ortak import GirdiHatasi, kati_json
from mutalaa_pipeline.ingest.meal_ortak import gelen_dizini, gelen_tarihi_coz, ham_kopyala
from mutalaa_pipeline.ingest.tanzil import INGEST_ADIMI, tarih_gecerli
from mutalaa_pipeline.komut_ortak import komutu_yurut
from mutalaa_pipeline.lineage import OZET_DESENI, kisa_ozet
from mutalaa_pipeline.runctx import RunContext
from mutalaa_pipeline.staged import satirlari_yaz

KAYNAK: Final = "quranwbw-tr"
DOSYA_ADI: Final = "6.json"
ANLAMLAR_ADI: Final = "meanings.jsonl"
KILIT_YOLU: Final = Path(__file__).with_name("quranwbw.lock.json")
EN_BUYUK_BAYT: Final = 16 << 20
CIKARICI_SURUMU: Final = "quranwbw-tr-cikarici-1"
UYARI: Final = "Yeni QuranWBW surumu kilit guncellenerek (/karar) alinir."
SAYI_ANAHTARI: Final = re.compile(r"[1-9][0-9]{0,2}")
KILIT_ALANLARI: Final = ("url", "surum", "alinma_tarihi", "dosya", "boyut", "sha256")


def veri_surumu(surum: str) -> str:
    return f"{KAYNAK}@{surum}"


# --- cikarma -----------------------------------------------------------------------------


def kelime_capasi(sure: int, ayet: int, kelime: int) -> str:
    """`q:{sure}:{ayet}:{kelime}`; bicimleme ve dogrulama yalniz `mutalaa_pipeline.anchor` ile."""
    try:
        dizge = anchor_format(AnchorRef(Q(sure, ayet, kelime)))
        parse(dizge)
    except (AnchorError, ValueError):
        raise GirdiHatasi(
            f"quranwbw: gecersiz kelime konumu (sure {sure}, ayet {ayet}, kelime {kelime})"
        ) from None
    return dizge


def _numara(anahtar: str, ne: str) -> int:
    if SAYI_ANAHTARI.fullmatch(anahtar) is None:
        raise GirdiHatasi(f"quranwbw: {ne} anahtari kanonik sayi degil")
    return int(anahtar)


def cikar(veri: bytes, ham_sha256: str, surum: str) -> list[dict[str, object]]:
    """Ham dosyadan anlam satirlari (capaya gore SIRALANMAMIS, dosya sirasinda).

    Satir: `anchor`, `surah`, `ayah`, `word`, `text` (kanonik), `provenance` (`ham_sha256`,
    `yol`, `cikarici`), `source_id`, `data_version`. Bicim sapmasi ve bos girdi `GirdiHatasi`.
    """
    try:
        govde = kati_json(veri.decode("utf-8"))
    except UnicodeDecodeError:
        raise GirdiHatasi("quranwbw: dosya UTF-8 degil") from None
    if not isinstance(govde, dict) or not govde:
        raise GirdiHatasi("quranwbw: kok nesne degil ya da bos")
    satirlar: list[dict[str, object]] = []
    for sure_anahtari, ayetler in govde.items():
        sure = _numara(sure_anahtari, "sure")
        if not isinstance(ayetler, dict):
            raise GirdiHatasi(f"quranwbw: sure {sure} nesne degil")
        for ayet_anahtari, icerik in ayetler.items():
            ayet = _numara(ayet_anahtari, "ayet")
            if (
                not isinstance(icerik, list)
                or len(icerik) != 1
                or not isinstance(icerik[0], list)
                or not icerik[0]
            ):
                raise GirdiHatasi(f"quranwbw: sure {sure} ayet {ayet}: [[anlamlar]] bicimi degil")
            for indeks, ham in enumerate(icerik[0]):
                kelime = indeks + 1
                if not isinstance(ham, str):
                    raise GirdiHatasi(
                        f"quranwbw: sure {sure} ayet {ayet} kelime {kelime}: anlam metin degil"
                    )
                try:
                    metin = kanonik_metin(ham)
                except UnicodeEncodeError:
                    raise GirdiHatasi(
                        f"quranwbw: sure {sure} ayet {ayet} kelime {kelime}: gecersiz Unicode"
                    ) from None
                if metin == "":
                    raise GirdiHatasi(
                        f"quranwbw: sure {sure} ayet {ayet} kelime {kelime}: bos anlam girdisi"
                    )
                satirlar.append(
                    {
                        "anchor": kelime_capasi(sure, ayet, kelime),
                        "surah": sure,
                        "ayah": ayet,
                        "word": kelime,
                        "text": metin,
                        "provenance": {
                            "ham_sha256": ham_sha256,
                            "yol": f"/{sure_anahtari}/{ayet_anahtari}/0/{indeks}",
                            "cikarici": CIKARICI_SURUMU,
                        },
                        "source_id": KAYNAK,
                        "data_version": veri_surumu(surum),
                    }
                )
    return satirlar


# --- kilit -------------------------------------------------------------------------------


@dataclass(frozen=True)
class QuranwbwKilidi:
    """`quranwbw.lock.json`: dosyanin sabit kimligi (yalniz `/karar` ile degisir)."""

    url: str
    surum: str
    alinma_tarihi: str
    dosya: str
    boyut: int
    sha256: str

    def sozluk(self) -> dict[str, object]:
        return {
            "url": self.url,
            "surum": self.surum,
            "alinma_tarihi": self.alinma_tarihi,
            "dosya": self.dosya,
            "boyut": self.boyut,
            "sha256": self.sha256,
        }


def kilit_coz(ham: bytes) -> QuranwbwKilidi:
    """Kilit dosyasinin baytlarini kati bicimde cozer; bicim hatasi `GirdiHatasi`."""
    if ham.startswith(b"\xef\xbb\xbf") or b"\r" in ham:
        raise GirdiHatasi("quranwbw.lock.json: BOM ya da CR var (UTF-8 BOM'suz, LF olmali)")
    try:
        veri = kati_json(ham.decode("utf-8"))
    except UnicodeDecodeError:
        raise GirdiHatasi("quranwbw.lock.json: UTF-8 degil") from None
    except GirdiHatasi as hata:
        raise GirdiHatasi(f"quranwbw.lock.json: {hata}") from None
    if not isinstance(veri, dict) or set(veri) != set(KILIT_ALANLARI):
        raise GirdiHatasi(f"quranwbw.lock.json: alanlar {', '.join(KILIT_ALANLARI)} olmali")
    url, surum, tarih, dosya, boyut, ozet = (veri[a] for a in KILIT_ALANLARI)
    if not isinstance(url, str) or not url.startswith("https://"):
        raise GirdiHatasi("quranwbw.lock.json: url https:// ile baslayan metin olmali")
    if not isinstance(surum, str) or surum == "":
        raise GirdiHatasi("quranwbw.lock.json: surum bos olmayan metin olmali")
    if not isinstance(tarih, str) or not tarih_gecerli(tarih):
        raise GirdiHatasi("quranwbw.lock.json: alinma_tarihi YYYY-AA-GG olmali")
    if dosya != DOSYA_ADI:
        raise GirdiHatasi(f"quranwbw.lock.json: dosya {DOSYA_ADI} olmali")
    if type(boyut) is not int or boyut <= 0:
        raise GirdiHatasi("quranwbw.lock.json: boyut pozitif tam sayi olmali")
    if not isinstance(ozet, str) or OZET_DESENI.fullmatch(ozet) is None:
        raise GirdiHatasi("quranwbw.lock.json: sha256 64 haneli kucuk harfli onaltilik olmali")
    return QuranwbwKilidi(url, surum, tarih, dosya, boyut, ozet)


def kilit_yukle(yol: Path | None = None) -> QuranwbwKilidi:
    try:
        ham = (yol if yol is not None else KILIT_YOLU).read_bytes()
    except OSError:
        raise GirdiHatasi("quranwbw.lock.json okunamadi") from None
    return kilit_coz(ham)


def kilit_metni(kilit: QuranwbwKilidi) -> str:
    return json.dumps(kilit.sozluk(), ensure_ascii=True, indent=2) + "\n"


def kilit_denetle(kilit: QuranwbwKilidi, veri: bytes) -> None:
    """Dosya boyutu ve SHA-256'si kilitle tutmuyorsa `GirdiHatasi` (cikis 2)."""
    ozet = lineage.sha256_bayt(veri)
    if ozet != kilit.sha256 or len(veri) != kilit.boyut:
        raise GirdiHatasi(
            f"{KAYNAK}: dosya ozeti kilitle tutmuyor (beklenen {kisa_ozet(kilit.sha256)},"
            f" bulunan {kisa_ozet(ozet)}; boyut {kilit.boyut}/{len(veri)}). {UYARI}"
        )


def kilit_onerisi(veri: bytes, tarih: str, url: str, surum: str) -> QuranwbwKilidi:
    """Gelen dosyanin baytlarindan ilk kilit degerleri (hicbir sey yazmaz)."""
    return QuranwbwKilidi(
        url=url,
        surum=surum,
        alinma_tarihi=tarih,
        dosya=DOSYA_ADI,
        boyut=len(veri),
        sha256=lineage.sha256_bayt(veri),
    )


# --- gelen klasoru -----------------------------------------------------------------------


def gelen_oku(gelen: Path, tarih: str) -> bytes:
    """Gelen dosyanin baytlari; yoksa, okunamiyorsa ya da cok buyukse `GirdiHatasi`."""
    goreli = f"gelen/{KAYNAK}/{tarih}/{DOSYA_ADI}"
    yol = gelen / tarih / DOSYA_ADI
    try:
        if not yol.is_file():
            raise GirdiHatasi(f"{goreli} yok (--gelen-tarih ile baska bir klasor verilebilir)")
        if yol.stat().st_size > EN_BUYUK_BAYT:
            raise GirdiHatasi(f"{goreli} cok buyuk (sinir {EN_BUYUK_BAYT} bayt)")
        return yol.read_bytes()
    except OSError:
        raise GirdiHatasi(f"{goreli} okunamadi") from None


def _fetch_kaydi(kilit: QuranwbwKilidi, tarih: str) -> dict[str, object]:
    return {
        "kaynak": KAYNAK,
        "dosya": DOSYA_ADI,
        "url": kilit.url,
        "surum": kilit.surum,
        "alinma_tarihi": tarih,
        "boyut": kilit.boyut,
        "sha256": kilit.sha256,
        "gelen_yol": f"gelen/{KAYNAK}/{tarih}",
    }


# --- calistirma --------------------------------------------------------------------------


@dataclass(frozen=True)
class QuranwbwSonucu:
    run_id: str
    atlandi: bool
    girdi_sayisi: int
    klasor: Path | None
    onceki_run_id: str | None = None


def sayilar_hesapla(satirlar: list[dict[str, object]]) -> dict[str, int]:
    """Sayim ozeti (icerik yok): girdi, sure, ayet, farkli anlam."""
    return {
        "girdi": len(satirlar),
        "sure": len({s["surah"] for s in satirlar}),
        "ayet": len({(s["surah"], s["ayah"]) for s in satirlar}),
        "farkli_anlam": len({str(s["text"]) for s in satirlar}),
    }


def run_quranwbw(
    ctx: RunContext, gelen_tarih: str | None = None, kilit: QuranwbwKilidi | None = None
) -> QuranwbwSonucu:
    """Kaynak kaydi, kilit, ham kopya, cikarma, parmak izi, `meanings.jsonl`, manifest (en son)."""
    ctx.require_sources(KAYNAK)
    ctx.gunluk.yaz("INFO", "quranwbw_basla", source_id=KAYNAK)
    kilit = kilit if kilit is not None else kilit_yukle()
    gelen = gelen_dizini(ctx.veri_kok, KAYNAK)
    tarih = gelen_tarihi_coz(gelen, gelen_tarih, KAYNAK)
    veri = gelen_oku(gelen, tarih)
    kilit_denetle(kilit, veri)  # tutmazsa raw'a hicbir sey yazilmaz
    satirlar = cikar(veri, kilit.sha256, kilit.surum)
    yollar, _ = ham_kopyala(ctx, KAYNAK, tarih, {DOSYA_ADI: veri}, _fetch_kaydi(kilit, tarih))
    ham = yollar[DOSYA_ADI]
    girdiler = [lineage.Girdi(yol=lineage.goreli_yol(ctx.veri_kok, ham), sha256=kilit.sha256)]
    parmak = ctx.parmak_izi(girdiler)
    sayilar = sayilar_hesapla(satirlar)

    onceki = lineage.son_basarili(ctx.staged_kaynak_dizini(KAYNAK), ctx.adim)
    if lineage.atlanabilir(
        onceki=onceki[2] if onceki else None,
        parmak=parmak,
        git_kirli=ctx.git().kirli,
        force=ctx.force,
        veri_kok=ctx.veri_kok,
    ):
        ctx.gunluk.yaz("INFO", "quranwbw_atlandi", source_id=KAYNAK)
        ctx.sayi("atlandi", 1)
        return QuranwbwSonucu(ctx.run_id, True, 0, None, onceki[0] if onceki else None)

    for ad, deger in sayilar.items():
        ctx.sayi(ad, deger)
    if ctx.dry_run:
        ctx.gunluk.yaz("INFO", "quranwbw_dry_run", source_id=KAYNAK, sayilar=sayilar)
        return QuranwbwSonucu(ctx.run_id, False, sayilar["girdi"], None)
    klasor = ctx.staged_dizin(KAYNAK)
    klasor.mkdir(parents=True, exist_ok=True)
    cikti = satirlari_yaz(ctx, KAYNAK, ANLAMLAR_ADI, satirlar)
    ctx.manifest_yaz(
        klasor,
        girdiler=girdiler,
        ciktilar=[cikti],
        parmak=parmak,
        ayrintilar={
            "surum": kilit.surum,
            "gelen_tarih": tarih,
            "kilit": {"boyut": kilit.boyut, "sha256": kilit.sha256},
            "cikarici": CIKARICI_SURUMU,
            "sayilar": sayilar,
        },
    )
    ctx.gunluk.yaz("INFO", "quranwbw_bitti", source_id=KAYNAK, sayilar=sayilar)
    return QuranwbwSonucu(ctx.run_id, False, sayilar["girdi"], klasor)


def kilit_oner_metni(veri_kok: Path, depo_kok: Path, gelen_tarih: str | None) -> str:
    """`--kilit-oner`: gelen dosyadan hesaplanan kilit (JSON); adres ve surum kaynak kaydindan."""
    sonuclar = {s.dosya.removesuffix(".toml"): s for s in sources.yukle(depo_kok)}
    kayit = sonuclar.get(KAYNAK)
    if kayit is None or kayit.kaynak is None:
        raise GirdiHatasi(f"{KAYNAK}: kaynak kaydi yok ya da gecersiz")
    url, surum = kayit.kaynak.kaynak_url, kayit.kaynak.surum
    if url is None or surum is None:
        raise GirdiHatasi(f"{KAYNAK}: kaynak kaydinda kaynak_url ve surum olmali")
    gelen = gelen_dizini(veri_kok, KAYNAK)
    tarih = gelen_tarihi_coz(gelen, gelen_tarih, KAYNAK)
    return kilit_metni(kilit_onerisi(gelen_oku(gelen, tarih), tarih, url, surum))


def komut_ingest_quranwbw(
    *,
    gelen_tarih: str | None,
    dry_run: bool,
    force: bool,
    config: Path | None,
    kok: Path | None,
) -> int:
    """`ingest quranwbw-tr` komutu; cikis kodunu dondurur."""

    def govde(ctx: RunContext) -> int:
        sonuc = run_quranwbw(ctx, gelen_tarih)
        if sonuc.atlandi:
            ozet = f"atlandi (parmak izi onceki calistirmayla ayni, run {sonuc.onceki_run_id})"
        elif ctx.dry_run:
            ozet = f"{sonuc.girdi_sayisi} girdi (dry-run, hicbir sey yazilmadi)"
        else:
            ozet = f"{sonuc.girdi_sayisi} girdi, run {sonuc.run_id}"
        sys.stdout.write(f"ingest {KAYNAK}: {ozet}\n")
        return cikis.BASARILI

    return komutu_yurut(
        komut="ingest quranwbw-tr",
        adim=INGEST_ADIMI,
        kaynaklar=[KAYNAK],
        config=config,
        kok=kok,
        govde=govde,
        force=force,
        dry_run=dry_run,
        parametreler={"source": KAYNAK},
    )
