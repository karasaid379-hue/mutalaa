"""Sure adi testlerinin ortak yardimcilari (test degildir; SENTETIK veri).

Butun sure adlari uydurmadir: harflerden uretilen "Deneme..." adlari ve `chr()` ile kurulmus
sapkali/noktali harfli birkac sentetik ad. Gercek sure adi ya da Kur'an metni yoktur. Vikimetin,
yonlendirme JSON'u ve `quran-meta` tarball'u gercek dosyalarin BICIMINI taklit eder (hucre
bolunmeleri, `||` bitisik yazimi, son hucrenin satir sonuna yapismasi dahil).
"""

import gzip
import hashlib
import io
import json
import tarfile
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path

import pytest
from test_sources import alanlar_kur, kayit_yaz
from ust_veri_yardimci import UstVeriZinciri, ar_ad
from zincir_yardimci import ortam_kur

from mutalaa_pipeline.adimlar import sure_adlari_adaylar as adaylar_modulu
from mutalaa_pipeline.adimlar.anchor_sure_adlari import komut_anchor_sure_adlari
from mutalaa_pipeline.anchor.ayet_sayilari import AYET_SAYILARI
from mutalaa_pipeline.ingest import sure_adlari as sure_adlari_modulu
from mutalaa_pipeline.ingest.sure_adlari import (
    BEKLENEN_DOSYALAR,
    QURAN_META,
    VIKIPEDI_REVIZYON,
    VIKIPEDI_TABLO,
    KaynakKilidi,
    SureAdlariKilidi,
    kilit_metni,
    komut_ingest_sure_adlari,
)
from mutalaa_pipeline.qa.run_sure_adlari import komut_qa_run_sure_adlari

TARIH = "2026-11-08"
REVID = 424242
SURE_SAYISI = len(AYET_SAYILARI)
HARFLER = "abcdefghijklmnopqrstuvwxyz"
SAPKALI_A = chr(0xE2)
NOKTALI_I = chr(0x130)
QM_UYE = "package/dist/surah.tr-Sentetik1.js"


def ad(n: int) -> str:
    """Sure icin SENTETIK gorunen ad (harflerden uretilir; 3, 7 ve 14 ozel harf tasir)."""
    taban = "Deneme" + HARFLER[(n // 26) % 26] + HARFLER[n % 26]
    if n == 3:
        return "Ten" + SAPKALI_A + "me-i " + NOKTALI_I + "mran"  # sapkali + noktali harf
    if n == 7:
        return "Ta'" + HARFLER[0] + "f"  # kesme isaretli
    if n == 14:
        return NOKTALI_I + "brahimx"
    return taban


def baslik(n: int) -> str:
    return ad(n) + " Suresi"


def yer(n: int) -> str:
    """Tanzil sentetik XML'iyle ayni: tek numaralar Meccan (Mekke), cift numaralar Medinan."""
    return "Mekke" if n % 2 else "Medine"


def anlam(n: int) -> str:
    return f"[[Baglanti{n}|Anlam{n}]], [[Tek{n}]] yazi" if n % 5 == 0 else f"Anlam{n} yazi"


def sentetik_vikimetin(
    degistir: Callable[[int, str], str] | None = None, satir_sayisi: int = SURE_SAYISI
) -> str:
    """Vikimetin: gercek tablonun bicimi (uc satir/hucre yerlesimi) ve sentetik degerler."""
    satirlar = [
        "{{Kaynak|sablon}}",
        "== Mushaftaki sirasina gore ==",
        '{| class="wikitable sortable"',
        "|-",
        "! No !! Sure ",
        "! Ayet !! Cuz !! {{Kayma|Adinin anlami}}!! {{Kayma|Indigi yer}}",
        "! {{Kayma|Inis sirasi}}",
        "! Basindaki [[mukattaa harfler]]",
    ]
    for n in range(1, satir_sayisi + 1):
        sure = f"[[{baslik(n)}|{ad(n)}]]"
        ayas = AYET_SAYILARI[(n - 1) % SURE_SAYISI]
        cuz = "1-2" if n == 2 else str((n // 4) + 1)
        mukattaa = "Elif Lam" if n % 4 == 2 else ""
        if n % 3 == 0:  # yer ayri satirda (gercek tabloda Meryem satiri gibi)
            govde = [
                f"| {n} || {sure}",
                f"| {ayas} || {cuz} || {anlam(n)}",
                f"| {yer(n)}",
                f"| {n}",
                f"| {mukattaa}",
            ]
        elif n % 3 == 1:  # `||` bitisik yazim ve bos son hucrenin `|` olarak yapismasi
            govde = [
                f"| {n} || {sure} ",
                f"| {ayas} || {cuz} || {anlam(n)}||{yer(n)}",
                f"| {n}",
                "|" if not mukattaa else f"| {mukattaa}",
            ]
        else:
            govde = [
                f"| {n} || {sure} ",
                f"| {ayas} || {cuz} || {anlam(n)} || {yer(n)}",
                f"| {n}",
                f"| {mukattaa}",
            ]
        satirlar += ["|-"] + [degistir(n, s) if degistir else s for s in govde]
    satirlar += ["|}", "", "== Ayrica bakiniz ==", "* [[Baska madde]]", ""]
    return "\n".join(satirlar)


def sentetik_yonlendirme_json(
    yonlendirmeler: Mapping[int, Sequence[str]] | None = None, ek_sayfalar: int = 3
) -> tuple[bytes, bytes]:
    """Action API biciminde iki dosya: her sure maddesi iki dosyada da, yonlendirmeler bolunmus.

    `yonlendirmeler`: sure no -> yonlendirme basliklari (varsayilan: sure basina `ad` ve
    `ad + " Sayfasi"`). Tablo disi sayfalar (`Diger madde N`) yok sayilmalidir.
    """
    sayfalar: list[tuple[str, list[str]]] = []
    for n in range(1, SURE_SAYISI + 1):
        varsayilan = [ad(n), ad(n) + " Sayfasi"]
        sayfalar.append(
            (baslik(n), list(yonlendirmeler.get(n, varsayilan)) if yonlendirmeler else varsayilan)
        )
    for i in range(ek_sayfalar):
        sayfalar.append((f"Diger madde {i}", [f"Diger yonlendirme {i}", "Kategori:Deneme"]))
    birinci: list[dict[str, object]] = []
    ikinci: list[dict[str, object]] = []
    for sira, (baslik_, adlar) in enumerate(sayfalar, start=1):
        yarim = (len(adlar) + 1) // 2
        for hedef, parca in ((birinci, adlar[:yarim]), (ikinci, adlar[yarim:])):
            sayfa: dict[str, object] = {"pageid": sira, "ns": 0, "title": baslik_}
            if parca:
                sayfa["redirects"] = [
                    {"pageid": sira * 1000 + i, "ns": 0, "title": a} for i, a in enumerate(parca)
                ]
            hedef.append(sayfa)

    def paketle(sayfalar_: list[dict[str, object]], devam: bool) -> bytes:
        belge: dict[str, object] = {"limits": {"redirects": 500}, "query": {"pages": sayfalar_}}
        belge["continue" if devam else "batchcomplete"] = {"rdcontinue": "x"} if devam else True
        return json.dumps(belge, ensure_ascii=False, separators=(",", ":")).encode("utf-8")

    return paketle(birinci, True), paketle(ikinci, False)


def sentetik_revizyon_json(tablo_bayt: int, revid: int = REVID) -> bytes:
    belge = {
        "batchcomplete": True,
        "query": {
            "pages": [
                {
                    "pageid": 1,
                    "title": "Sureler listesi",
                    "revisions": [{"revid": revid, "size": tablo_bayt}],
                }
            ]
        },
    }
    return json.dumps(belge, separators=(",", ":")).encode("utf-8")


def qm_js(adlar: Sequence[tuple[str, str]], bos_son: bool = True) -> str:
    """`surah.tr` dosyasinin bicimi: `[]`, 114 cift, `[]`."""
    satirlar = [
        'import { t as __exportAll } from "./rolldown-runtime-D7D4PA-g.js";',
        "//#region src/i18n/surah.tr.ts",
        "const surahNamesTr = [",
        "\t[],",
    ]
    for i, (a, m) in enumerate(adlar):
        son = "," if (i < len(adlar) - 1 or bos_son) else ""
        satirlar.append(
            "\t["
            + json.dumps(a, ensure_ascii=False)
            + ", "
            + json.dumps(m, ensure_ascii=False)
            + "]"
            + son
        )
    if bos_son:
        satirlar.append("\t[]")
    satirlar += ["];", "//#endregion", "export { surahNamesTr as t };", ""]
    return "\n".join(satirlar)


def sentetik_qm_adlari() -> list[tuple[str, str]]:
    """quran-meta adi: tablo adiyla ayni, ancak her 10. surede farkli bir yazim (diger_ad)."""
    return [(ad(n) + ("q" if n % 10 == 0 else ""), f"Anlam{n}") for n in range(1, SURE_SAYISI + 1)]


def tgz_yap(js: str, uye: str = QM_UYE, ek: Mapping[str, bytes] | None = None) -> bytes:
    """Deterministik tarball (gzip ve tar zaman damgasi 0): ayni girdi ayni baytlari verir."""
    govde = js.encode("utf-8")
    tampon = io.BytesIO()
    with (
        gzip.GzipFile(fileobj=tampon, mode="wb", mtime=0) as gz,
        tarfile.open(fileobj=gz, mode="w") as arsiv,
    ):
        for ad_, veri in {uye: govde, **(ek or {})}.items():
            bilgi = tarfile.TarInfo(ad_)
            bilgi.size = len(veri)
            bilgi.mtime = 0
            arsiv.addfile(bilgi, io.BytesIO(veri))
    return tampon.getvalue()


def tanzil_satirlari() -> list[dict[str, object]]:
    """Ust veri `sure.jsonl` satirlarinin sentetik karsiligi (`ust_veri_yardimci.sentetik_xml`)."""
    return [
        {
            "tur": "sure",
            "no": n,
            "sura": n,
            "aya": 1,
            "ad_ar": ar_ad(n),
            "tname": f"Deneme-{n}",
            "ename": f"Deneme {n}",
            "type": "Meccan" if n % 2 else "Medinan",
            "order": n,
            "ayas": AYET_SAYILARI[n - 1],
            "start": sum(AYET_SAYILARI[: n - 1]),
            "rukus": 1,
        }
        for n in range(1, SURE_SAYISI + 1)
    ]


def sentetik_dosyalar() -> tuple[dict[str, bytes], dict[str, bytes]]:
    """`(vikipedi dosyalari, quran-meta dosyalari)`; adlar `BEKLENEN_DOSYALAR` ile ayni."""
    metin = sentetik_vikimetin().encode("utf-8")
    yon1, yon2 = sentetik_yonlendirme_json()
    viki = {
        VIKIPEDI_TABLO: metin,
        VIKIPEDI_REVIZYON: sentetik_revizyon_json(len(metin)),
        "yonlendirmeler-01.json": yon1,
        "yonlendirmeler-02.json": yon2,
    }
    meta = {"quran-meta-7.0.0.tgz": tgz_yap(qm_js(sentetik_qm_adlari()))}
    return viki, meta


def kilit_kur(viki: Mapping[str, bytes], meta: Mapping[str, bytes]) -> SureAdlariKilidi:
    def kaynak(url: str, surum: str, dosyalar: Mapping[str, bytes]) -> KaynakKilidi:
        return KaynakKilidi(
            url=url,
            surum=surum,
            alinma_tarihi=TARIH,
            dosyalar={a: (len(v), hashlib.sha256(v).hexdigest()) for a, v in dosyalar.items()},
        )

    assert set(viki) == set(BEKLENEN_DOSYALAR["vikipedi"])
    return SureAdlariKilidi(
        vikipedi=kaynak("https://deneme.invalid/sureler", str(REVID), viki),
        quran_meta=kaynak("https://deneme.invalid/quran-meta.tgz", "7.0.0", meta),
    )


def gelen_yaz(veri_kok: Path, viki: Mapping[str, bytes], meta: Mapping[str, bytes]) -> None:
    for slug, dosyalar in (("sure-adlari-vikipedi", viki), (QURAN_META, meta)):
        klasor = veri_kok / "gelen" / slug / TARIH
        klasor.mkdir(parents=True, exist_ok=True)
        for ad_, veri in dosyalar.items():
            (klasor / ad_).write_bytes(veri)


def riskli_dosya_yaz(yol: Path, adlar: Sequence[str]) -> Path:
    yol.write_bytes(("# Sentetik riskli adlar\n" + "\n".join(adlar) + "\n").encode("utf-8"))
    return yol


def lock_yaz(yol: Path, kilit: SureAdlariKilidi) -> None:
    yol.write_bytes(kilit_metni(kilit).encode("utf-8"))


# --- zincir (ust_veri_zinciri uzerine) -------------------------------------------------------


class SureAdlariZinciri:
    """`ust_veri_zinciri` kokune sentetik sure adi girdileri, kilit ve riskli ad listesi ekler."""

    def __init__(self, uz: UstVeriZinciri) -> None:
        self.uz = uz
        self.viki, self.meta = sentetik_dosyalar()
        self.kilit = kilit_kur(self.viki, self.meta)
        self.kilit_yolu = uz.z.tmp / "sure_adlari.lock.json"
        self.riskli_adlar = [ad(5), ad(9)]
        self.riskli_yolu = riskli_dosya_yaz(uz.z.tmp / "riskli.txt", self.riskli_adlar)
        lock_yaz(self.kilit_yolu, self.kilit)
        kok = uz.z.kok
        kayit_yaz(
            kok,
            alanlar_kur(
                "sure-adlari-vikipedi",
                tur="sozluk",
                baslik="Deneme Vikipedi",
                surum=f"revizyon {REVID} (deneme)",
                provider="vikipedi",
                kaynak_url=self.kilit.vikipedi.url,
            ),
        )
        kayit_yaz(
            kok,
            alanlar_kur(
                QURAN_META,
                tur="mushaf_duzeni",
                baslik="Deneme quran-meta",
                surum="7.0.0",
                kaynak_url=self.kilit.quran_meta.url,
            ),
        )
        gelen_yaz(uz.z.veri_kok, self.viki, self.meta)

    def ortam(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Ortam degiskenlerini ve kilit/riskli dosya yollarini bu zincire yonlendirir."""
        ortam_kur(self.uz.z, monkeypatch)
        monkeypatch.setattr(sure_adlari_modulu, "KILIT_YOLU", self.kilit_yolu)
        monkeypatch.setattr(adaylar_modulu, "RISKLI_ADLAR_YOLU", self.riskli_yolu)

    def ingest(self, **kw: object) -> int:
        return komut_ingest_sure_adlari(
            gelen_tarih=None,
            dry_run=bool(kw.get("dry_run", False)),
            force=bool(kw.get("force", False)),
            config=None,
            kok=self.uz.z.kok,
        )

    def anchor(self, **kw: object) -> int:
        return komut_anchor_sure_adlari(
            dry_run=bool(kw.get("dry_run", False)),
            force=bool(kw.get("force", False)),
            config=None,
            kok=self.uz.z.kok,
        )

    def qa(self) -> int:
        return komut_qa_run_sure_adlari(run=None, gate=None, config=None, kok=self.uz.z.kok)

    def hepsi(self) -> None:
        assert self.ingest() == 0
        assert self.anchor() == 0
        assert self.qa() == 0
