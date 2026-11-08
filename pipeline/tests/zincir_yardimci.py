"""Zincir testlerinin ortak yardimcilari (test degildir): ingest -> normalize -> anchor -> qa.

SENTETIK Arapca yazili metin: harfler ve harekeler `\\u` kacisiyla, deterministik bir formulle
kurulur. Hicbir ayet, besmele ya da baska bir metinden alinti degildir (Kur'an metni hafizadan
yazilmaz). Gercek bayt gereken yerlerde `tests/fixtures/tanzil/` parcalari (dosyadan betikle
kesilmis) kullanilir. Uthmani sentetik metni bilerek NFC olmayan sira (sedde, sonra hareke)
ve elif vasla (U+0671) icerir; boylece "NFC uygulanmaz" ve "yazim farki normalize sonrasi esit"
durumlari sinanir. `(sure + ayet) % 3 == 0` ayetlerinde Uthmani'nin ikinci kelimesine bir elif
eklenir: normalize hali farkli olur ve AR-4 o sozcugu ar_norm sonuna ekler.
"""

import copy
import dataclasses
import hashlib
import shutil
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from hat_yardimci import ctx_kur
from tanzil_yardimci import TARIH, gelen_yaz, sentetik_bildirim
from test_sources import alanlar_kur, kayit_yaz, kok_kur

from mutalaa_pipeline.adimlar.anchor_tanzil import (
    anchor_satirlari,
    kelime_satirlari,
    komut_anchor,
    run_anchor,
)
from mutalaa_pipeline.adimlar.normalize_tanzil import (
    EK_KAYNAK,
    KAYNAK,
    komut_normalize,
    normalize_satirlari,
    run_normalize,
)
from mutalaa_pipeline.anchor.ayet_sayilari import AYET_SAYILARI
from mutalaa_pipeline.anchor.quran import BESMELE_BELIRTEC, BIRLESTIRME, besmele_onekli_mi
from mutalaa_pipeline.enums import SourceKind
from mutalaa_pipeline.export.ortak import GirdiHatasi, depo_koku
from mutalaa_pipeline.ingest import tanzil, tanzil_bicim
from mutalaa_pipeline.ingest.base import run_ingest
from mutalaa_pipeline.ingest.tanzil import KilitGirdisi, dosya_adi
from mutalaa_pipeline.qa.checks.tanzil import QaGirdisi, Varyant
from mutalaa_pipeline.runctx import RunContext
from mutalaa_pipeline.sources.kayit import Kaynak
from mutalaa_pipeline.staged import Satir, kelimeler_yaz, units_yaz
from mutalaa_pipeline.zincir import (
    NORMALIZE_ADIMI,
    calismalar,
    girdi_olarak,
    units_oku,
)

# Sentetik harf ve hareke dizileri chr() ile kurulur (kaynak dosya ASCII kalir).
HARF = "".join(chr(kod) for kod in range(0x0628, 0x0628 + 10))
FETHA, KESRA, DAMME = chr(0x064E), chr(0x0650), chr(0x064F)
SEDDE, SUKUN = chr(0x0651), chr(0x0652)
HANCER_ELIF, ELIF_VASLA, ELIF = chr(0x0670), chr(0x0671), chr(0x0627)
KUCUK_YUKSEK_SUKUN = chr(0x06E1)
HAREKELER = (FETHA, KESRA, DAMME)
VARYANT_KAYNAK = {"uthmani": KAYNAK, "simple-clean": EK_KAYNAK}
# Sahte depo kokune kopyalanan degismez veri dosyalari (depo kokune gore yol).
PAYLASILAN_DOSYALAR = (
    "shared/data/ayet-sayilari.json",
    "packages/anchors/src/generated/ayet-sayilari.ts",
    "pipeline/src/mutalaa_pipeline/anchor/ayet_sayilari.py",
    "server/Mutalaa.Domain/Anchors/AyetSayilari.g.cs",
    "shared/test-vectors/normalize/tr.jsonl",
    "shared/test-vectors/normalize/ar.jsonl",
)


def vektor_sayisi() -> int:
    """Gercek `normalize/tr.jsonl` ve `ar.jsonl` dosyalarindaki vektor (dolu satir) sayisi.

    G-NOR'un raporladigi sayiyla karsilastirilir; A10.7 `ar-tz-` satirlari ekleyince de gecer.
    """
    toplam = 0
    for ad in ("tr.jsonl", "ar.jsonl"):
        veri = (depo_koku() / "shared" / "test-vectors" / "normalize" / ad).read_bytes()
        toplam += sum(1 for satir in veri.split(b"\n") if satir)
    return toplam


def sentetik_kelime(n: int, uthmani: bool, *, ek_elif: bool = False, ilk: bool = False) -> str:
    """Uc harfli sentetik kelime. Uthmani ve Simple Clean yazimi normalize sonrasi aynidir
    (`ek_elif` verilince Uthmani'ye bir elif eklenir: normalize hali de farkli olur)."""
    h1, h2, h3 = HARF[n % 10], HARF[(n // 10 + 3) % 10], HARF[(n * 7 + 1) % 10]
    hareke = HAREKELER[n % 3]
    bas = (ELIF_VASLA if uthmani else ELIF) if ilk else ""
    if uthmani:
        orta = h2 + (ELIF if ek_elif else "")
        return bas + h1 + SEDDE + hareke + orta + HANCER_ELIF + h3 + KUCUK_YUKSEK_SUKUN
    return bas + h1 + hareke + SEDDE + h2 + h3 + SUKUN


def sentetik_ayet(sure: int, ayet: int, varyant: str) -> str:
    """`(sure, ayet)` icin deterministik sentetik ayet metni (3-5 kelime).

    Besmele onekli ayetlerde (sure 2-114, 9 haric, 1. ayet; K-43) metnin basina SENTETIK besmele
    eklenir: 1:1'in dort sentetik kelimesi. Boylece `anchor/quran.py` kuralinin dort belirteci
    atmasi kelime birakir; gercek besmele yazilmaz.
    """
    uthmani = varyant == "uthmani"
    kelimeler = []
    # Birlestirme listesindeki ayetlerde (K-43) birlesecek iki belirtec bulunmalidir.
    adet = max(3 + ayet % 3, BIRLESTIRME.get((sure, ayet), 0) + 1)
    for k in range(adet):
        n = sure * 31 + ayet * 7 + k
        ek = uthmani and k == 1 and (sure + ayet) % 3 == 0
        kelimeler.append(sentetik_kelime(n, uthmani, ek_elif=ek, ilk=k == 0))
    if besmele_onekli_mi(sure, ayet):
        kelimeler = sentetik_ayet(1, 1, varyant).split(" ")[:BESMELE_BELIRTEC] + kelimeler
    return " ".join(kelimeler)


def sentetik_dosya(
    varyant: str, tablo: Sequence[int] = AYET_SAYILARI, bildirim: bytes | None = None
) -> bytes:
    """`tablo`daki her ayet icin `sure|ayet|metin` satiri + sentetik bildirim blogu."""
    satirlar = [
        f"{sure}|{ayet}|{sentetik_ayet(sure, ayet, varyant)}\n"
        for sure, adet in enumerate(tablo, start=1)
        for ayet in range(1, adet + 1)
    ]
    govde = "".join(satirlar).encode("utf-8")
    return govde + (bildirim if bildirim is not None else sentetik_bildirim(varyant))


def kilit_tablodan(
    varyant: str, veri: bytes, tablo: Sequence[int] = AYET_SAYILARI, tarih: str = TARIH
) -> KilitGirdisi:
    """`veri` icin kilit girdisi; ayristirma `tablo` ile yapilir (parca ya da tam dosya)."""
    ayrisma = tanzil_bicim.ayristir(veri, tablo)
    return KilitGirdisi(
        varyant=varyant,
        url=tanzil.FORM_ADRESI,
        secenekler=dict(tanzil.SECENEKLER),
        surum="1.1",
        alinma_tarihi=tarih,
        boyut=len(veri),
        sha256=hashlib.sha256(veri).hexdigest(),
        metin_sha256=ayrisma.metin_sha256,
        bildirim_sha256=ayrisma.bildirim_sha256,
    )


def kaynak_kaydi(varyant: str, bildirim: bytes, **degisim: object) -> Kaynak:
    """QA kapilarinin okudugu bellekteki kaynak kaydi (TOML dosyasi degil)."""
    alanlar: dict[str, object] = {
        "slug": VARYANT_KAYNAK[varyant],
        "tur": SourceKind.KURAN_METNI,
        "baslik": "Deneme Tanzil kaydi",
        "atif_metni": "Deneme atif metni.",
        "surum": "1.1",
        "kaynak_url": tanzil.FORM_ADRESI,
        "notice_text": bildirim.decode("utf-8"),
    }
    alanlar.update(degisim)
    return Kaynak(**alanlar)  # type: ignore[arg-type]


# --- diskte zincir -----------------------------------------------------------------------


@dataclass
class Zincir:
    """Sahte depo kokunde (kayitlar + paylasilan veri) ve `tmp/data` altinda bir zincir."""

    tmp: Path
    kok: Path
    veri_kok: Path
    tablo: Sequence[int]
    veriler: dict[str, bytes]

    def ctx(self, adim: str, kaynaklar: Sequence[str], **kw: object) -> RunContext:
        return ctx_kur(
            self.tmp,
            self.kok,
            adim=adim,
            kaynaklar=kaynaklar,
            parametreler={"source": KAYNAK},
            **kw,  # type: ignore[arg-type]
        )

    def kilit_dosyasi(self) -> Path:
        """Gecici kilit dosyasi (iki varyantin bu zincirdeki dosyalarindan hesaplanir)."""
        yol = self.tmp / "kilit.json"
        kilitler = {
            v: kilit_tablodan(v, self.veriler[v], self.tablo) for v in ("uthmani", "simple-clean")
        }
        yol.write_bytes(tanzil.kilit_metni(kilitler).encode("utf-8"))
        return yol

    def ingest(
        self,
        varyant: str,
        *,
        tarih: str | None = None,
        veri: bytes | None = None,
        temiz_git: bool = True,
        **kw: object,
    ) -> RunContext:
        """`tarih` verilirse `gelen/tanzil/<tarih>/` altina veri (yoksa mevcut baytlar) yazilir."""
        ctx = self.ctx("ingest", [VARYANT_KAYNAK[varyant]], temiz_git=temiz_git, **kw)
        ctx.parametreler = {"variant": varyant}
        if veri is not None:
            self.veriler[varyant] = veri
        if tarih is not None:
            gelen_yaz(self.veri_kok, varyant, self.veriler[varyant], tarih)
        kilit = kilit_tablodan(varyant, self.veriler[varyant], self.tablo, tarih or TARIH)
        bagdastirici = tanzil.TanzilBagdastirici(varyant, gelen_tarih=tarih, kilit=kilit, tam=False)
        run_ingest(bagdastirici, ctx)
        return ctx

    def normalize(self, *, temiz_git: bool = True, **kw: object) -> RunContext:
        ctx = self.ctx("normalize", [KAYNAK, EK_KAYNAK], temiz_git=temiz_git, **kw)
        run_normalize(ctx)
        return ctx

    def anchor(self, *, temiz_git: bool = True, **kw: object) -> RunContext:
        ctx = self.ctx("anchor", [KAYNAK], temiz_git=temiz_git, **kw)
        run_anchor(ctx)
        return ctx

    def hepsi(self, *, temiz_git: bool = False) -> None:
        """ingest x2, normalize ve anchor (qa ayri cagrilir)."""
        self.ingest("uthmani", temiz_git=temiz_git)
        self.ingest("simple-clean", temiz_git=temiz_git)
        self.normalize(temiz_git=temiz_git)
        self.anchor(temiz_git=temiz_git)


def sahte_kok_kur(tmp: Path, bildirimler: dict[str, bytes]) -> Path:
    """Sahte depo koku: iki Tanzil kaynak kaydi + degismez veri dosyalarinin kopyalari."""
    kok = kok_kur(tmp)
    for varyant, kaynak in VARYANT_KAYNAK.items():
        kayit_yaz(
            kok,
            alanlar_kur(
                kaynak,
                baslik=f"Deneme {varyant}",
                surum="1.1",
                provider="tanzil",
                kaynak_url=tanzil.FORM_ADRESI,
                notice_text=bildirimler[varyant].decode("utf-8"),
            ),
        )
    gercek = depo_koku()
    for goreli in PAYLASILAN_DOSYALAR:
        hedef = kok / goreli
        hedef.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(gercek / goreli, hedef)
    return kok


def zincir_hazirla(
    tmp: Path,
    veriler: dict[str, bytes],
    tablo: Sequence[int] = AYET_SAYILARI,
    bildirimler: dict[str, bytes] | None = None,
) -> Zincir:
    """Kayitlar, paylasilan dosyalar ve `gelen` dosyalari hazir bir `Zincir` (adimlar kosulmadi)."""
    bildirimler = bildirimler or {
        v: tanzil_bicim.ayristir(veriler[v], tablo, tam=False).bildirim for v in veriler
    }
    kok = sahte_kok_kur(tmp, bildirimler)
    veri_kok = tmp / "data"
    for varyant, veri in veriler.items():
        gelen_yaz(veri_kok, varyant, veri)
    return Zincir(tmp, kok, veri_kok, tablo, veriler)


# --- bellekte QA girdisi -------------------------------------------------------------------


def _ingest_satirlari(
    kaynak: str, dosya: str, ham_sha: str, ayrisma: tanzil_bicim.Ayrisma
) -> dict[str, Satir]:
    """Ingest adiminin yazacagi satirlar (`capa -> Satir`)."""
    return {
        ay.capa: Satir(
            f"ingest {kaynak}",
            ay.satir,
            {
                "anchor": ay.capa,
                "attrs": {},
                "provenance": {
                    "file": dosya,
                    "sha256": ham_sha,
                    "line": ay.satir,
                    "bayt": [ay.bayt_bas, ay.bayt_son],
                    "steps": [],
                },
                "source_id": kaynak,
                "text": ay.metin,
            },
        )
        for ay in ayrisma.ayetler
    }


def varyant_kur(varyant: str, ham: bytes, tablo: Sequence[int], **degisim: object) -> Varyant:
    """Bellekte bir `Varyant`: ham dosya, kayit, kilit (hepsi `ham`dan tutarli)."""
    ayrisma = tanzil_bicim.ayristir(ham, tablo)
    alanlar: dict[str, Any] = {
        "kaynak": VARYANT_KAYNAK[varyant],
        "kayit": kaynak_kaydi(varyant, ayrisma.bildirim),
        "kilit": kilit_tablodan(varyant, ham, tablo),
        "ham": ham,
        "ham_sha256": hashlib.sha256(ham).hexdigest(),
        "ayrisma": ayrisma,
        "bildirim_dosyasi": ayrisma.bildirim,
        "ingest_surum": "1.1",
    }
    alanlar.update(degisim)
    return Varyant(**alanlar)


def qa_girdisi(
    tablo: Sequence[int] = (3, 4, 2),
    *,
    uthmani: bytes | None = None,
    simple: bytes | None = None,
    depo_kok: Path | None = None,
) -> QaGirdisi:
    """Bellekte `QaGirdisi`: ham dosyalar -> ingest satirlari -> normalize -> anchor.

    Satirlar adimlarin kendi islevleriyle uretilir; kapilar bu girdiyi okur. Varsayilan tablo
    `(3, 4, 2)` (9 sentetik ayet) kucuktur: kapi testleri hizli kalir.
    """
    u_ham = uthmani if uthmani is not None else sentetik_dosya("uthmani", tablo)
    s_ham = simple if simple is not None else sentetik_dosya("simple-clean", tablo)
    u = varyant_kur("uthmani", u_ham, tablo)
    s = varyant_kur("simple-clean", s_ham, tablo)
    normalize = normalize_satirlari(
        _ingest_satirlari(KAYNAK, dosya_adi("uthmani"), u.ham_sha256, u.ayrisma),
        _ingest_satirlari(EK_KAYNAK, dosya_adi("simple-clean"), s.ham_sha256, s.ayrisma),
    )[0]
    anchor = anchor_satirlari([Satir("normalize", i, r) for i, r in enumerate(normalize, 1)], "1.1")
    kelimeler = kelime_satirlari(anchor, "1.1")
    return QaGirdisi(
        anchor_satirlari=[Satir("anchor", i, r) for i, r in enumerate(anchor, 1)],
        kelime_satirlari=[Satir("words", i, r) for i, r in enumerate(kelimeler, 1)],
        uthmani=u,
        simple=s,
        depo_kok=depo_kok if depo_kok is not None else depo_koku(),
        sure_tablosu=tablo,
    )


def satiri_degistir(g: QaGirdisi, capa: str, **alanlar: object) -> QaGirdisi:
    """Bir anchor satirinin alanlarini degistirilmis kopya (`None` verilen alan silinir)."""
    yeni = []
    for satir in g.anchor_satirlari:
        if satir.veri.get("anchor") == capa:
            veri = {**satir.veri, **alanlar}
            veri = {k: v for k, v in veri.items() if v is not None}
            satir = Satir(satir.etiket, satir.no, veri)
        yeni.append(satir)
    return dataclasses.replace(g, anchor_satirlari=yeni)


def satiri_cikar(g: QaGirdisi, capa: str) -> QaGirdisi:
    return dataclasses.replace(
        g, anchor_satirlari=[s for s in g.anchor_satirlari if s.veri.get("anchor") != capa]
    )


# --- tam (6.236 ayetlik) sentetik sablon ----------------------------------------------------


def tam_zincir_kur(tmp: Path) -> Path:
    """6.236 ayetlik SENTETIK zincir: ingest x2, normalize ve anchor gercek komutlarla kosulur.

    Dondurulen klasor bir sablondur; testler `sablon_kopyala` ile kendi kopyalarini alir.
    """
    veriler = {v: sentetik_dosya(v) for v in ("uthmani", "simple-clean")}
    z = zincir_hazirla(tmp, veriler)
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(tanzil, "KILIT_YOLU", z.kilit_dosyasi())
        mp.setenv("MUTALAA_VERI_KOK", str(z.veri_kok))
        for varyant in ("uthmani", "simple-clean"):
            kod = tanzil.komut_ingest_tanzil(
                varyant=varyant,
                gelen_tarih=None,
                dry_run=False,
                force=False,
                config=None,
                kok=z.kok,
            )
            assert kod == 0, varyant
        assert (
            komut_normalize(source=KAYNAK, dry_run=False, force=False, config=None, kok=z.kok) == 0
        )
        assert komut_anchor(source=KAYNAK, dry_run=False, force=False, config=None, kok=z.kok) == 0
    return tmp


def sablon_kopyala(sablon: Path, hedef: Path) -> Zincir:
    """Sablonun bagimsiz bir kopyasi: sahte depo koku, `data/` ve gecici kilit dosyasi."""
    shutil.copytree(sablon, hedef)
    gelen = hedef / "data" / "gelen" / "tanzil" / TARIH
    veriler = {v: (gelen / tanzil.dosya_adi(v)).read_bytes() for v in ("uthmani", "simple-clean")}
    return Zincir(hedef, hedef / "kok", hedef / "data", AYET_SAYILARI, veriler)


def ortam_kur(z: Zincir, monkeypatch: pytest.MonkeyPatch) -> None:
    """CLI cagrilari icin: veri koku ve gecici kilit dosyasi bu zincire yonlendirilir."""
    monkeypatch.setenv("MUTALAA_VERI_KOK", str(z.veri_kok))
    monkeypatch.setattr(tanzil, "KILIT_YOLU", z.tmp / "kilit.json")


def anchor_bozdur(
    z: Zincir, degistir: Callable[[list[dict[str, Any]]], list[dict[str, Any]] | None]
) -> RunContext:
    """Yeni bir anchor calistirmasi yazar: gercek adimin satirlari `degistir` ile bozulmustur.

    Manifest ve zincir gecerlidir (hatali bir anchor adimini taklit eder); boylece QA kapilari
    kalir ama zincir bozuk sayilmaz. `degistir` listeyi yerinde degistirir ya da yenisini dondurur.
    """
    ctx = z.ctx("anchor", [KAYNAK], temiz_git=False)
    normalize = calismalar(ctx, KAYNAK, NORMALIZE_ADIMI)[-1]
    satirlar = anchor_satirlari(units_oku(normalize, "normalize units.jsonl"), "1.1")
    saglam = copy.deepcopy(satirlar)
    sonuc = degistir(satirlar)
    bozuk = sonuc if sonuc is not None else satirlar
    try:
        kelimeler = kelime_satirlari(bozuk, "1.1")
    except GirdiHatasi:  # bozulmus satirlardan kelime uretilemiyorsa bozulmamis halinden uretilir
        kelimeler = kelime_satirlari(saglam, "1.1")
    cikti = units_yaz(ctx, KAYNAK, bozuk)
    kelime_cikti = kelimeler_yaz(ctx, KAYNAK, kelimeler)
    ctx.manifest_yaz(
        ctx.staged_dizin(KAYNAK),
        girdiler=[girdi_olarak(normalize)],
        ciktilar=[cikti, kelime_cikti],
        parmak="0" * 64,
    )
    return ctx
