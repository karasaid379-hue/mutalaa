"""QAC testlerinin ortak yardimcilari (test degildir; SENTETIK veri).

`sentetik_qac` gercek QAC dosyasinin BICIMINI taklit eder (ASCII, CR LF, bildirim blogu, `LOCATION`
baslik satiri, dort sekme ayracli sutun, `STEM` bayragi, `LEM:` ve `ROOT:`) ama icerigi uydurmadir:
lemma ve kok dizgileri Buckwalter tablosundaki ASCII harflerden kurala bagli uretilir ("Deneme"
niteliginde, Kur'an kelimesi degil); FORM sutunu "Deneme" metnidir. Kelime sayilari sentetik Tanzil
zincirinin kelime bolmesinden gelir (G-BUT ayet basina esitlik sinar). Arapca metin yoktur;
Arapca beklentiler `enrich.buckwalter` donusumunden hesaplanir.
"""

import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import pytest
from hat_yardimci import ctx_kur
from test_sources import alanlar_kur, kayit_yaz
from ust_veri_yardimci import UstVeriZinciri
from zincir_yardimci import Zincir, ortam_kur, sablon_kopyala

from mutalaa_pipeline.adimlar.enrich_morphology import komut_enrich_morphology
from mutalaa_pipeline.enrich.buckwalter import TABLO
from mutalaa_pipeline.ingest import qac
from mutalaa_pipeline.ingest.qac import DOSYA_ADI, kilit_metni, kilit_onerisi
from mutalaa_pipeline.qa import qac_capraz as capraz_modulu
from mutalaa_pipeline.qa import run_qac
from mutalaa_pipeline.runctx import RunContext
from mutalaa_pipeline.staged import satirlari_oku

TARIH = "2026-11-12"
URL = "https://deneme.invalid/qac/quranic-corpus-morphology-0.4.txt"
HARFLER = "btjHxdrzsSDTEgfqklmnhwy"  # hepsi Buckwalter tablosunda
BILDIRIM = (
    "# DENEME BILDIRIM BLOGU (sentetik)\n"
    "#  Quranic Arabic Corpus (morphology, version 0.4)\n"
    "#  Bu metin testler icin uydurulmustur.\n"
    "#"
)
assert all(h in TABLO for h in HARFLER + "ai")


def lemma_bw(i: int) -> str:
    """`i`. sentetik lemma (tekil dizgi; `i` % 11 == 0 olanlar '2' ayirt rakami tasir)."""
    govde = HARFLER[i % 23] + "a" + HARFLER[(i // 23) % 23] + "i" + HARFLER[(i * 3 + 1) % 23]
    return govde + "2" if i % 11 == 0 and i > 0 else govde


def kok_bw(i: int) -> str | None:
    """`i`. lemmanin koku (iki lemma bir kokte; `i` % 17 == 0 koksuz)."""
    if i % 17 == 0:
        return None
    k = i // 2
    return HARFLER[k % 23] + HARFLER[(k // 23) % 23] + "w"


def sentetik_qac(
    kelimeler: Sequence[Mapping[str, object]],
    *,
    bildirim: str = BILDIRIM,
    lemma_sayisi: int = 60,
) -> bytes:
    """Sentetik kelime satirlarindan (`surah`, `ayah`, `word`) sentetik QAC dosyasi (CR LF)."""
    satirlar = [*bildirim.split("\n"), "", "LOCATION\tFORM\tTAG\tFEATURES"]
    for n, k in enumerate(kelimeler):
        konum = f"{k['surah']}:{k['ayah']}:{k['word']}"
        i = (n % 7) if n % 4 == 0 else (n % lemma_sayisi)
        segment = 1
        if n % 5 == 0:
            satirlar.append(f"({konum}:{segment})\tDeneme\tP\tPREFIX|bi+")
            segment += 1
        if n % 29 == 0:  # lemmasiz bagimsiz zamir govdesi
            satirlar.append(f"({konum}:{segment})\tDeneme\tPRON\tSTEM|POS:PRON|3MS|NOM")
            continue
        tag = "P" if i % 5 == 0 else ("V" if i % 3 == 0 else "N")
        kok = kok_bw(i)
        ozellik = f"STEM|POS:{tag}|LEM:{lemma_bw(i)}" + (f"|ROOT:{kok}" if kok else "") + "|MS"
        satirlar.append(f"({konum}:{segment})\tDeneme\t{tag}\t{ozellik}")
        if n % 97 == 0 and n > 0:  # ikinci govdeli (kaynasik) kelime
            satirlar.append(f"({konum}:{segment + 1})\tDeneme\tREL\tSTEM|POS:REL|LEM:{lemma_bw(3)}")
    return ("\r\n".join(satirlar) + "\r\n").encode("ascii")


def mustafa0x_satirlari(qac_ham: bytes) -> bytes:
    """Sentetik `mustafa0x` kopyasi: ayni kelimeler, lemma/kok Arapca (donusumden), LF."""
    from mutalaa_pipeline.enrich.buckwalter import bw_arapca
    from mutalaa_pipeline.enrich.morphology import lemma_ayir

    cikti = []
    for s in qac.ayristir(qac_ham).segmentler:
        konum = f"{s.sure}:{s.ayet}:{s.kelime}:{s.segment}"
        ozellik = ["PREF"] if not s.govde else []
        if s.kok is not None:
            ozellik.append("ROOT:" + "".join(bw_arapca(c) for c in s.kok))
        if s.lem is not None:
            ozellik.append("LEM:" + bw_arapca(lemma_ayir(s.lem)[0]))
        cikti.append(f"{konum}\tDeneme\tN\t{'|'.join(ozellik) or 'N'}")
    return ("\n".join(cikti) + "\n").encode("utf-8")


@dataclass
class QacZinciri:
    """Sahte kokte: sentetik ust veri zinciri + sentetik QAC dosyasi, kilit ve kayitlar."""

    z: Zincir
    ham: bytes
    kilit_yolu: Path

    def ctx(self, adim: str, kaynaklar: list[str], **kw: object) -> RunContext:
        return ctx_kur(self.z.tmp, self.z.kok, adim=adim, kaynaklar=kaynaklar, **kw)  # type: ignore[arg-type]

    def ingest(self, **kw: object) -> int:
        return qac.komut_ingest_qac(
            gelen_tarih=None,
            dry_run=bool(kw.get("dry_run", False)),
            force=bool(kw.get("force", False)),
            config=None,
            kok=self.z.kok,
        )

    def enrich(self, **kw: object) -> int:
        return komut_enrich_morphology(
            dry_run=bool(kw.get("dry_run", False)),
            force=bool(kw.get("force", False)),
            config=None,
            kok=self.z.kok,
        )

    def qa(self, **kw: object) -> int:
        return run_qac.komut_qa_run_qac(run=None, gate=None, config=None, kok=self.z.kok)

    def hepsi(self) -> None:
        assert self.ingest() == 0
        assert self.enrich() == 0
        assert self.qa() == 0

    def staged(self, kaynak: str, ad: str) -> list[dict[str, object]]:
        klasorler = sorted((self.z.veri_kok / "staged" / kaynak).iterdir(), key=lambda p: p.name)
        for klasor in reversed(klasorler):
            if (klasor / ad).is_file():
                return [s.veri for s in satirlari_oku((klasor / ad).read_bytes(), ad)]
        raise AssertionError(f"{kaynak}/{ad} yok")


def tanzil_kelimeleri(ust_veri: UstVeriZinciri) -> list[dict[str, object]]:
    """Sentetik zincirdeki `tanzil-uthmani` anchor `words.jsonl` satirlari."""
    kok = ust_veri.z.veri_kok / "staged" / "tanzil-uthmani"
    for klasor in sorted(kok.iterdir(), key=lambda p: p.name, reverse=True):
        yol = klasor / "words.jsonl"
        if yol.is_file():
            return [s.veri for s in satirlari_oku(yol.read_bytes(), "words")]
    raise AssertionError("sentetik Tanzil words.jsonl yok")


def qac_hazirla(
    ust_veri: UstVeriZinciri,
    hedef: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    ham: bytes | None = None,
    mustafa0x: bool = True,
) -> QacZinciri:
    """Ust veri zincirinin kopyasina sentetik QAC girdilerini koyar (hicbir adim kosulmaz)."""
    z = sablon_kopyala(ust_veri.z.tmp, hedef)
    ortam_kur(z, monkeypatch)
    veri = ham if ham is not None else sentetik_qac(tanzil_kelimeleri(ust_veri))
    gelen = z.veri_kok / "gelen" / "qac-morfoloji" / TARIH
    gelen.mkdir(parents=True)
    (gelen / DOSYA_ADI).write_bytes(veri)
    kilit = kilit_onerisi(veri, TARIH, URL, "0.4")
    kilit_yolu = z.tmp / "qac.lock.json"
    kilit_yolu.write_bytes(kilit_metni(kilit).encode("utf-8"))
    monkeypatch.setattr(qac, "KILIT_YOLU", kilit_yolu)
    bildirim = qac.ayristir(veri).bildirim
    kayit_yaz(
        z.kok,
        alanlar_kur(
            "qac-morfoloji",
            tur="morfoloji",
            baslik="Deneme QAC",
            surum="0.4",
            provider="qac",
            kaynak_url=URL,
            notice_text=bildirim,
        ),
    )
    kayit_yaz(
        z.kok, alanlar_kur("mustafa0x-morfoloji", tur="morfoloji", baslik="Deneme kopya", surum="1")
    )
    if mustafa0x:
        kopya = z.veri_kok / "gelen" / capraz_modulu.KAYNAK / TARIH
        kopya.mkdir(parents=True)
        icerik = mustafa0x_satirlari(veri)
        (kopya / capraz_modulu.DOSYA_ADI).write_bytes(icerik)
        ozet = hashlib.sha256(icerik).hexdigest()
        (kopya / "SHA256SUMS").write_bytes(f"{ozet} *{capraz_modulu.DOSYA_ADI}\n".encode())
    return QacZinciri(z, veri, kilit_yolu)
