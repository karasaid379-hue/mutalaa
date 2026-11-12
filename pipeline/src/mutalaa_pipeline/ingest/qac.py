"""QAC morfoloji alimi (A17.3, K-50): `data/gelen` -> `data/raw` -> `data/staged`.

`mutalaa ingest qac`:

1. `data/gelen/qac-morfoloji/<YYYY-AA-GG>/quranic-corpus-morphology-0.4.txt` dosyasini BAYT olarak
   okur (en cok 16 MB) ve `qac.lock.json` ile karsilastirir (boyut ve SHA-256). Tutmazsa cikis 2 ve
   "kilit guncellenerek (/karar) alinir" uyarisi; `data/raw`'a hicbir sey yazilmaz. Kilit yalniz
   `/karar` ile degisir; ilk degerleri `--kilit-oner` yazdirir. Dosya yalniz VERI olarak okunur.
2. Dosya ASCII olmali, satirlar yalniz CR LF ile bitmeli (CRLF bellekte ayrilir; metin kipi ve
   yerel kod sayfasi kullanilmaz). Bildirim blogu (`LOCATION` baslik satirindan onceki `#`
   satirlari) LF'ye cevrilip sondaki satir sonlari atilarak `notice_text` ile karsilastirilir;
   ozeti kilitte durur. Veri satirlari dort sekme ayracli sutundur: LOCATION `(sure:ayet:kelime:
   segment)`, FORM, TAG, FEATURES (`|` ile ayrili; `STEM` govde bayragi, `LEM:` ve `ROOT:`).
3. Ham kopya `data/raw/qac-morfoloji/<tarih>/` altina `fetch.json` ile yazilir (ayni baytlar zaten
   varsa yeni kopya acilmaz; `data/raw` degismez). Staged cikti yalniz `notice.txt`'tir: segmentler
   ham dosyadan `enrich morphology` adiminda yeniden ayristirilir (ham dosya manifestteki ozetle
   dogrulanir).

FORM, LEM ve ROOT extended Buckwalter ASCII dizgisidir; bu modul onlari CEVIRMEZ (`enrich/
buckwalter.py`). Hata iletileri yalniz satir numarasi, sayi ve kisaltilmis ozet tasir; icerik asla.
"""

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from mutalaa_pipeline import cikis, lineage, sources
from mutalaa_pipeline.export.ortak import GirdiHatasi, kati_json
from mutalaa_pipeline.ingest.meal_ortak import gelen_dizini, gelen_tarihi_coz, ham_kopyala
from mutalaa_pipeline.ingest.tanzil import INGEST_ADIMI, tarih_gecerli
from mutalaa_pipeline.komut_ortak import komutu_yurut
from mutalaa_pipeline.lineage import NOTICE_ADI, OZET_DESENI, kisa_ozet
from mutalaa_pipeline.runctx import RunContext

KAYNAK: Final = "qac-morfoloji"
DOSYA_ADI: Final = "quranic-corpus-morphology-0.4.txt"
KILIT_YOLU: Final = Path(__file__).with_name("qac.lock.json")
EN_BUYUK_BAYT: Final = 16 << 20
UYARI: Final = "Yeni QAC surumu kilit guncellenerek (/karar) alinir."
BASLIK_SATIRI: Final = "LOCATION\tFORM\tTAG\tFEATURES"
SATIR_SONU: Final = b"\r\n"
KONUM_DESENI: Final = re.compile(
    r"\((?P<sure>[0-9]{1,3}):(?P<ayet>[0-9]{1,3}):(?P<kelime>[0-9]{1,3}):(?P<segment>[0-9]{1,3})\)"
)
BILDIRIM_SURUMU: Final = re.compile(
    r"Quranic Arabic Corpus \(morphology, version (?P<surum>[0-9]+(?:\.[0-9]+)*)\)"
)
SURUM_DESENI: Final = re.compile(r"[0-9]+(?:\.[0-9]+)*")
GOVDE_BAYRAGI: Final = "STEM"
LEM_ONEKI: Final = "LEM:"
KOK_ONEKI: Final = "ROOT:"
KILIT_ALANLARI: Final = (
    "url",
    "surum",
    "alinma_tarihi",
    "dosya",
    "boyut",
    "sha256",
    "bildirim_bayt",
    "bildirim_sha256",
    "bildirim_satir",
)


# --- ayristirma --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Segment:
    """Bir morfolojik segment (dosyanin bir veri satiri). Degerler Buckwalter ASCII dizgisidir."""

    sure: int
    ayet: int
    kelime: int
    segment: int
    form: str
    tag: str
    ozellikler: tuple[str, ...]  # FEATURES, `|` ile bolunmus, dosya sirasinda
    govde: bool  # `STEM` bayragi
    lem: str | None
    kok: str | None


@dataclass(frozen=True)
class BildirimOzeti:
    bayt: int
    sha256: str
    satir: int


@dataclass(frozen=True)
class QacDosyasi:
    bildirim: str  # LF'ye cevrilmis, sondaki satir sonlari atilmis
    segmentler: tuple[Segment, ...]

    def bildirim_baytlari(self) -> bytes:
        return self.bildirim.encode("utf-8")

    def bildirim_ozeti(self) -> BildirimOzeti:
        veri = self.bildirim_baytlari()
        return BildirimOzeti(len(veri), lineage.sha256_bayt(veri), self.bildirim.count("\n") + 1)


def _alan(ozellikler: tuple[str, ...], onek: str, no: int) -> str | None:
    degerler = [o[len(onek) :] for o in ozellikler if o.startswith(onek)]
    if len(degerler) > 1:
        raise GirdiHatasi(f"qac: satir {no}: {onek} birden fazla")
    if degerler and degerler[0] == "":
        raise GirdiHatasi(f"qac: satir {no}: {onek} bos")
    return degerler[0] if degerler else None


def _satir_coz(satir: str, no: int) -> Segment:
    sutunlar = satir.split("\t")
    if len(sutunlar) != 4:
        raise GirdiHatasi(f"qac: satir {no}: {len(sutunlar)} sutun; 4 bekleniyor")
    konum, form, tag, ozellik = sutunlar
    eslesme = KONUM_DESENI.fullmatch(konum)
    if eslesme is None:
        raise GirdiHatasi(f"qac: satir {no}: LOCATION bicimi gecersiz")
    if tag == "" or ozellik == "":  # FORM bos olabilir (kaynakta 208 sonek segmenti)
        raise GirdiHatasi(f"qac: satir {no}: TAG ya da FEATURES bos")
    sayilar = {ad: int(deger) for ad, deger in eslesme.groupdict().items()}
    if min(sayilar.values()) < 1:
        raise GirdiHatasi(f"qac: satir {no}: konum numarasi 1'den kucuk")
    ozellikler = tuple(ozellik.split("|"))
    return Segment(
        sure=sayilar["sure"],
        ayet=sayilar["ayet"],
        kelime=sayilar["kelime"],
        segment=sayilar["segment"],
        form=form,
        tag=tag,
        ozellikler=ozellikler,
        govde=GOVDE_BAYRAGI in ozellikler,
        lem=_alan(ozellikler, LEM_ONEKI, no),
        kok=_alan(ozellikler, KOK_ONEKI, no),
    )


def ayristir(veri: bytes) -> QacDosyasi:
    """QAC dosyasini bayt olarak kati bicimde okur; bicim sapmasi `GirdiHatasi` (cikis 2).

    ASCII, yalniz CR LF satir sonu (son satir dahil), `#` bildirim satirlari, tek baslik satiri,
    sonra yalniz veri satirlari; konum tekildir. Hata iletileri yalniz satir numarasi tasir.
    """
    if not veri.isascii():
        raise GirdiHatasi("qac: ASCII olmayan bayt var")
    if not veri.endswith(SATIR_SONU):
        raise GirdiHatasi("qac: son satir CR LF ile bitmiyor")
    govde = veri[: -len(SATIR_SONU)].split(SATIR_SONU)
    if any(b"\r" in s or b"\n" in s for s in govde):
        raise GirdiHatasi("qac: CR LF disinda satir sonu var")
    satirlar = [s.decode("ascii") for s in govde]
    if BASLIK_SATIRI not in satirlar:
        raise GirdiHatasi("qac: LOCATION baslik satiri yok")
    baslik = satirlar.index(BASLIK_SATIRI)
    for no, satir in enumerate(satirlar[:baslik], start=1):
        if satir != "" and not satir.startswith("#"):
            raise GirdiHatasi(f"qac: satir {no}: bildirim blogunda yorum olmayan satir")
    bildirim = "\n".join(satirlar[:baslik]).rstrip("\n")
    if bildirim == "":
        raise GirdiHatasi("qac: bildirim blogu yok")
    segmentler: list[Segment] = []
    gorulen: set[tuple[int, int, int, int]] = set()
    for sira, satir in enumerate(satirlar[baslik + 1 :], start=baslik + 2):
        segment = _satir_coz(satir, sira)
        anahtar = (segment.sure, segment.ayet, segment.kelime, segment.segment)
        if anahtar in gorulen:
            raise GirdiHatasi(f"qac: satir {sira}: konum yinelendi")
        gorulen.add(anahtar)
        segmentler.append(segment)
    if not segmentler:
        raise GirdiHatasi("qac: veri satiri yok")
    return QacDosyasi(bildirim=bildirim, segmentler=tuple(segmentler))


def bildirim_surumu(bildirim: str) -> str | None:
    """Bildirim blogundaki "Quranic Arabic Corpus (morphology, version X)" surumu."""
    eslesme = BILDIRIM_SURUMU.search(bildirim)
    return eslesme.group("surum") if eslesme is not None else None


# --- kilit -------------------------------------------------------------------------------


@dataclass(frozen=True)
class QacKilidi:
    """`qac.lock.json`: dosya ve bildirim blogunun sabit kimligi (yalniz `/karar` ile degisir)."""

    url: str
    surum: str
    alinma_tarihi: str
    dosya: str
    boyut: int
    sha256: str
    bildirim_bayt: int
    bildirim_sha256: str
    bildirim_satir: int

    def sozluk(self) -> dict[str, object]:
        return {
            "url": self.url,
            "surum": self.surum,
            "alinma_tarihi": self.alinma_tarihi,
            "dosya": self.dosya,
            "boyut": self.boyut,
            "sha256": self.sha256,
            "bildirim_bayt": self.bildirim_bayt,
            "bildirim_sha256": self.bildirim_sha256,
            "bildirim_satir": self.bildirim_satir,
        }


def kilit_coz(ham: bytes) -> QacKilidi:
    """Kilit dosyasinin baytlarini kati bicimde cozer; bicim hatasi `GirdiHatasi`."""
    if ham.startswith(b"\xef\xbb\xbf") or b"\r" in ham:
        raise GirdiHatasi("qac.lock.json: BOM ya da CR var (UTF-8 BOM'suz, LF olmali)")
    try:
        veri = kati_json(ham.decode("utf-8"))
    except UnicodeDecodeError:
        raise GirdiHatasi("qac.lock.json: UTF-8 degil") from None
    except GirdiHatasi as hata:
        raise GirdiHatasi(f"qac.lock.json: {hata}") from None
    if not isinstance(veri, dict) or set(veri) != set(KILIT_ALANLARI):
        raise GirdiHatasi(f"qac.lock.json: alanlar {', '.join(KILIT_ALANLARI)} olmali")
    url, surum, tarih, dosya = (veri[a] for a in KILIT_ALANLARI[:4])
    if not isinstance(url, str) or not url.startswith("https://"):
        raise GirdiHatasi("qac.lock.json: url https:// ile baslayan metin olmali")
    if not isinstance(surum, str) or SURUM_DESENI.fullmatch(surum) is None:
        raise GirdiHatasi("qac.lock.json: surum sayilardan olusan metin olmali")
    if not isinstance(tarih, str) or not tarih_gecerli(tarih):
        raise GirdiHatasi("qac.lock.json: alinma_tarihi YYYY-AA-GG olmali")
    if dosya != DOSYA_ADI:
        raise GirdiHatasi(f"qac.lock.json: dosya {DOSYA_ADI} olmali")
    sayilar = {a: veri[a] for a in ("boyut", "bildirim_bayt", "bildirim_satir")}
    for ad, deger in sayilar.items():
        if type(deger) is not int or deger <= 0:
            raise GirdiHatasi(f"qac.lock.json: {ad} pozitif tam sayi olmali")
    for ad in ("sha256", "bildirim_sha256"):
        deger = veri[ad]
        if not isinstance(deger, str) or OZET_DESENI.fullmatch(deger) is None:
            raise GirdiHatasi(f"qac.lock.json: {ad} 64 haneli kucuk harfli onaltilik olmali")
    return QacKilidi(
        url=url,
        surum=surum,
        alinma_tarihi=tarih,
        dosya=dosya,
        boyut=sayilar["boyut"],
        sha256=str(veri["sha256"]),
        bildirim_bayt=sayilar["bildirim_bayt"],
        bildirim_sha256=str(veri["bildirim_sha256"]),
        bildirim_satir=sayilar["bildirim_satir"],
    )


def kilit_yukle(yol: Path | None = None) -> QacKilidi:
    try:
        ham = (yol if yol is not None else KILIT_YOLU).read_bytes()
    except OSError:
        raise GirdiHatasi("qac.lock.json okunamadi") from None
    return kilit_coz(ham)


def kilit_metni(kilit: QacKilidi) -> str:
    return json.dumps(kilit.sozluk(), ensure_ascii=True, indent=2) + "\n"


def kilit_denetle(kilit: QacKilidi, veri: bytes) -> None:
    """Dosya boyutu ve SHA-256'si kilitle tutmuyorsa `GirdiHatasi` (cikis 2)."""
    ozet = lineage.sha256_bayt(veri)
    if ozet != kilit.sha256 or len(veri) != kilit.boyut:
        raise GirdiHatasi(
            f"{KAYNAK}: dosya ozeti kilitle tutmuyor (beklenen {kisa_ozet(kilit.sha256)},"
            f" bulunan {kisa_ozet(ozet)}; boyut {kilit.boyut}/{len(veri)}). {UYARI}"
        )


def bildirim_denetle(kilit: QacKilidi, dosya: QacDosyasi) -> None:
    """Bildirim blogunun ozeti kilitle tutmuyorsa `GirdiHatasi`."""
    ozet = dosya.bildirim_ozeti()
    if (ozet.bayt, ozet.sha256, ozet.satir) != (
        kilit.bildirim_bayt,
        kilit.bildirim_sha256,
        kilit.bildirim_satir,
    ):
        raise GirdiHatasi(
            f"{KAYNAK}: bildirim blogu kilitle tutmuyor"
            f" (beklenen {kisa_ozet(kilit.bildirim_sha256)}, bulunan {kisa_ozet(ozet.sha256)})."
            f" {UYARI}"
        )


def kilit_onerisi(veri: bytes, tarih: str, url: str, surum: str) -> QacKilidi:
    """Gelen dosyanin baytlarindan ilk kilit degerleri (hicbir sey yazmaz)."""
    dosya = ayristir(veri)
    ozet = dosya.bildirim_ozeti()
    return QacKilidi(
        url=url,
        surum=surum,
        alinma_tarihi=tarih,
        dosya=DOSYA_ADI,
        boyut=len(veri),
        sha256=lineage.sha256_bayt(veri),
        bildirim_bayt=ozet.bayt,
        bildirim_sha256=ozet.sha256,
        bildirim_satir=ozet.satir,
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


def _fetch_kaydi(kilit: QacKilidi, tarih: str) -> dict[str, object]:
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
class QacSonucu:
    run_id: str
    atlandi: bool
    segment_sayisi: int
    klasor: Path | None
    onceki_run_id: str | None = None


def sayilar_hesapla(dosya: QacDosyasi) -> dict[str, int]:
    """Sayim ozeti (icerik yok): segment, kelime, ayet, sure, farkli TAG/LEM/ROOT."""
    kelimeler = {(s.sure, s.ayet, s.kelime) for s in dosya.segmentler}
    return {
        "segment": len(dosya.segmentler),
        "kelime": len(kelimeler),
        "ayet": len({(s.sure, s.ayet) for s in dosya.segmentler}),
        "sure": len({s.sure for s in dosya.segmentler}),
        "tag": len({s.tag for s in dosya.segmentler}),
        "lem": len({s.lem for s in dosya.segmentler if s.lem is not None}),
        "root": len({s.kok for s in dosya.segmentler if s.kok is not None}),
    }


def run_qac(
    ctx: RunContext, gelen_tarih: str | None = None, kilit: QacKilidi | None = None
) -> QacSonucu:
    """Kaynak kaydi, kilit, ham kopya, parmak izi, notice.txt, manifest (en son)."""
    ctx.require_sources(KAYNAK)
    ctx.gunluk.yaz("INFO", "qac_basla", source_id=KAYNAK)
    kilit = kilit if kilit is not None else kilit_yukle()
    gelen = gelen_dizini(ctx.veri_kok, KAYNAK)
    tarih = gelen_tarihi_coz(gelen, gelen_tarih, KAYNAK)
    veri = gelen_oku(gelen, tarih)
    kilit_denetle(kilit, veri)  # tutmazsa raw'a hicbir sey yazilmaz
    dosya = ayristir(veri)
    bildirim_denetle(kilit, dosya)
    yollar, _ = ham_kopyala(ctx, KAYNAK, tarih, {DOSYA_ADI: veri}, _fetch_kaydi(kilit, tarih))
    ham = yollar[DOSYA_ADI]
    girdiler = [lineage.Girdi(yol=lineage.goreli_yol(ctx.veri_kok, ham), sha256=kilit.sha256)]
    parmak = ctx.parmak_izi(girdiler)
    sayilar = sayilar_hesapla(dosya)

    onceki = lineage.son_basarili(ctx.staged_kaynak_dizini(KAYNAK), ctx.adim)
    if lineage.atlanabilir(
        onceki=onceki[2] if onceki else None,
        parmak=parmak,
        git_kirli=ctx.git().kirli,
        force=ctx.force,
        veri_kok=ctx.veri_kok,
    ):
        ctx.gunluk.yaz("INFO", "qac_atlandi", source_id=KAYNAK)
        ctx.sayi("atlandi", 1)
        return QacSonucu(ctx.run_id, True, 0, None, onceki[0] if onceki else None)

    for ad, deger in sayilar.items():
        ctx.sayi(ad, deger)
    if ctx.dry_run:
        ctx.gunluk.yaz("INFO", "qac_dry_run", source_id=KAYNAK, sayilar=sayilar)
        return QacSonucu(ctx.run_id, False, sayilar["segment"], None)
    klasor = ctx.staged_dizin(KAYNAK)
    klasor.mkdir(parents=True, exist_ok=True)
    bildirim = dosya.bildirim_baytlari()
    (klasor / NOTICE_ADI).write_bytes(bildirim)  # LF'ye cevrilmis bildirim blogu (notice_text)
    cikti = lineage.Cikti(
        yol=lineage.goreli_yol(ctx.veri_kok, klasor / NOTICE_ADI),
        sha256=lineage.sha256_bayt(bildirim),
    )
    ctx.manifest_yaz(
        klasor,
        girdiler=girdiler,
        ciktilar=[cikti],
        parmak=parmak,
        ayrintilar={
            "surum": kilit.surum,
            "gelen_tarih": tarih,
            "kilit": {"boyut": kilit.boyut, "sha256": kilit.sha256},
            "sayilar": sayilar,
        },
    )
    ctx.gunluk.yaz("INFO", "qac_bitti", source_id=KAYNAK, sayilar=sayilar)
    return QacSonucu(ctx.run_id, False, sayilar["segment"], klasor)


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


def komut_ingest_qac(
    *,
    gelen_tarih: str | None,
    dry_run: bool,
    force: bool,
    config: Path | None,
    kok: Path | None,
) -> int:
    """`ingest qac` komutu; cikis kodunu dondurur."""

    def govde(ctx: RunContext) -> int:
        sonuc = run_qac(ctx, gelen_tarih)
        if sonuc.atlandi:
            ozet = f"atlandi (parmak izi onceki calistirmayla ayni, run {sonuc.onceki_run_id})"
        elif ctx.dry_run:
            ozet = f"{sonuc.segment_sayisi} segment (dry-run, hicbir sey yazilmadi)"
        else:
            ozet = f"{sonuc.segment_sayisi} segment, run {sonuc.run_id}"
        sys.stdout.write(f"ingest {KAYNAK}: {ozet}\n")
        return cikis.BASARILI

    return komutu_yurut(
        komut="ingest qac",
        adim=INGEST_ADIMI,
        kaynaklar=[KAYNAK],
        config=config,
        kok=kok,
        govde=govde,
        force=force,
        dry_run=dry_run,
        parametreler={"source": KAYNAK},
    )
