"""`kok` seti ve olcumu: Turkce lemma -> Arapca kok (A18.5; K-51 madde 9-11; sinif `silver`).

URETIM (olculen): `icerik.lemma` icinde `lang = 'tr'`, `status = 'onayli'`, `onay_yolu` `otomatik`
ya da `editor`, kok sahibi satirlar; kok kaikki kanitindan ve QAC eslesmesinden gelir.

REFERANS (bagimsiz kaynak): QuranWBW Turkce kelime anlamlari (`quranwbw-tr`, ham dosya
`data/gelen/quranwbw-tr/<tarih>/6.json`; A17 `cikar` okuyucusu). Arapca kelimenin Turkce anlam
metni `bolme.parcalar` ile sozcuk parcalarina bolunur, her parca zeyrek ile lemmalanir (yalniz TEK
lemmaya inen parca sayilir); o Turkce lemma, Arapca kelimenin QAC koku (`quran_word.root_id`) ile
iliskilendirilir. BU CEVIRI ESDEGERLIGIDIR, ETIMOLOJI DEGIL: "Turkce lemma bu kokten gelen Arapca
kelimenin anlam metninde geciyor" demektir; kokun Turkce sozcugun etimolojik atasi oldugunu
kanitlamaz ve "yalnizca etimolojik" etiketi icin hicbir olcum yoktur (K-51 madde 9).

Referans kumesi (SABIT, ayarlanmaz): bir lemma icin bir kok referanstir <=> `destek >= 3` kelime
VE `destek / lemmanin gectigi toplam kelime >= 0,10`. `destek`: lemmanin anlam metninde gectigi,
koku o olan Arapca kelime sayisi; toplam, koku olmayan kelimeleri de sayar (edat ve baglac gibi
koksuz sozcukler boylece referans uretmez). Esikler olcumden ONCE sabitlendi, sonuca bakilarak
degistirilmez; rapor `min_destek` ve `min_pay` alanlarini yazar.

Ornek seti: referansi olan lemmalar `siklik bandina` (QuranWBW'de gectigi kelime sayisi: `yuksek` >=
100, `orta` 10-99, `dusuk` < 10) gore tabakali, band basina esit pay (toplam 400; bir bant yetmezse
tumu), sabit tohumla (`sha256(tohum:lemma)` sirasi) secilir. Dondurulmus parca (%60) kapi olcumudur;
gelistirme parcasi (%40) bilgidir.

OLCUM: kesinlik = koku referans kumesinde olan / referansi olan tahminler; duyarlilik = referansi
olan ornekler icinde tahmini olan VE dogru olan oran. Referansi olmayan (QuranWBW'de gecmeyen ya da
destegi yetmeyen) lemmalar OLCUME KATILMAZ, sayisi ayri yazilir. KAPSAM KISITI: set yalniz
Kur'an'da gecen sozcukleri olcer; meal sozcuklerinin geri kalani bu setle olculmez. Kappa: iki
bagimsiz etiket kaynagi (kaikki tabanli eslesme / QuranWBW tabanli referansin baskin koku) arasinda
KAYNAKLAR ARASI uyumdur, insan kappasi degildir.

DONGUSELLIK: set kaniti `quranwbw-tr` (`kanit`); uretim kaniti `kaikki-tr` (`kanit`): kesisim yok.
QAC kok sozlugu iki tarafta ortaktir (`sozluk` rolu): kok kimlikleri ve Arapca kelime -> kok
esleme ayni QAC'den gelir; bu ortak sozluk raporda notlanir, dongusellik sayilmaz.
"""

import hashlib
import json
from collections import Counter
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Final

import psycopg

from mutalaa_pipeline.enrich.tr_roots.bolme import parcalar
from mutalaa_pipeline.enrich.tr_roots.lemmatize import Lemmatizer
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.qa.gold import setler
from mutalaa_pipeline.qa.gold.kapi import TurSonucu, tahmin_ozeti
from mutalaa_pipeline.qa.gold.olcum import (
    ESIKLER,
    esik_degerlendir,
    kapi_karari,
    kappa_sklearn,
    prf_sayimdan,
)
from mutalaa_pipeline.qa.uyum import wilson_alt_sinir, wilson_ust_sinir

KAYNAK_QWBW: Final = "quranwbw-tr"
KAYNAK_QAC: Final = "qac-morfoloji"
KAYNAK_KAIKKI: Final = "kaikki-tr"
MIN_DESTEK: Final = 3
MIN_PAY_PAYDA: Final = 10  # destek * 10 >= toplam  <=>  pay >= 0,10 (tam sayi aritmetigi)
BANT_YUKSEK: Final = 100
BANT_ORTA: Final = 10
BANTLAR: Final = ("yuksek", "orta", "dusuk")
ORNEK_SAYISI: Final = 400
REFERANS_ADI: Final = "referans.jsonl"
URETIM_KOMUTU: Final = "uv run --directory pipeline mutalaa qa gold --type kok --build"
DOGRULAMA_YONTEMI: Final = (
    "QuranWBW Turkce kelime anlamlari: Turkce lemma (zeyrek, tek lemmaya inen parca), Arapca"
    " kelimenin anlam metninde geciyorsa o kelimenin QAC koku ile iliskilendirilir (destek >= 3 ve"
    " pay >= 0,10). Ceviri esdegerligidir, etimoloji degildir."
)


def bant(toplam: int) -> str:
    """Siklik bandi (QuranWBW'de lemmanin gectigi kelime sayisi)."""
    if toplam >= BANT_YUKSEK:
        return "yuksek"
    return "orta" if toplam >= BANT_ORTA else "dusuk"


# --- referans kurulumu -------------------------------------------------------------------


@dataclass
class ReferansKurulum:
    toplam: Counter[str]  # lemma -> gectigi kelime sayisi (koksuz kelimeler dahil)
    destek: dict[str, Counter[int]]  # lemma -> kok kimligi -> kelime sayisi
    parca: int = 0
    belirsiz_parca: int = 0
    bilinmeyen_parca: int = 0
    kelime: int = 0
    koklu_kelime: int = 0


def referans_say(
    anlamlar: Iterable[tuple[str, str]],
    kelime_koku: Mapping[str, int | None],
    lemmatizer: Lemmatizer,
) -> ReferansKurulum:
    """Anlam satirlarindan (`q:s:a:k`, metin) lemma -> kok destek sayaclari.

    Bir kelimede ayni lemma birden cok kez gecse de bir sayilir. Cok lemmali (belirsiz) ve
    bilinmeyen parcalar sayilmaz (ayri sayac).
    """
    k = ReferansKurulum(Counter(), {})
    for capa, metin in anlamlar:
        k.kelime += 1
        kok = kelime_koku.get(capa)
        if kok is not None:
            k.koklu_kelime += 1
        lemmalar: set[str] = set()
        for p in parcalar(metin):
            k.parca += 1
            analiz = lemmatizer.analiz(p.lemmatizer_girdisi)
            if analiz.bilinmiyor:
                k.bilinmeyen_parca += 1
            elif len(analiz.lemmalar) != 1:
                k.belirsiz_parca += 1
            else:
                (lemma,) = analiz.lemmalar
                lemmalar.add(lemma)
        for lemma in lemmalar:
            k.toplam[lemma] += 1
            if kok is not None:
                k.destek.setdefault(lemma, Counter())[kok] += 1
    return k


def referans_kokleri(
    k: ReferansKurulum, min_destek: int = MIN_DESTEK, min_pay_payda: int = MIN_PAY_PAYDA
) -> dict[str, dict[int, int]]:
    """Her lemma icin referans kokleri (`destek >= min_destek` ve `destek * 10 >= toplam`)."""
    sonuc: dict[str, dict[int, int]] = {}
    for lemma, toplam in k.toplam.items():
        kokler = {
            kok: n
            for kok, n in k.destek.get(lemma, Counter()).items()
            if n >= min_destek and n * min_pay_payda >= toplam
        }
        sonuc[lemma] = dict(sorted(kokler.items()))
    return sonuc


def ornek_sec(
    referans: Mapping[str, Mapping[int, int]],
    toplam: Mapping[str, int],
    n: int = ORNEK_SAYISI,
    tohum: int = setler.VARSAYILAN_TOHUM,
) -> list[str]:
    """Referansi olan lemmalardan banda gore tabakali, tohumla deterministik ornek (lemma listesi).

    Band basina `n // 3` (artan ilk bantlara +1); band yetmezse tumu alinir, fark baska banda
    AKTARILMAZ (ayar yok).
    """
    gruplar: dict[str, list[str]] = {b: [] for b in BANTLAR}
    for lemma, kokler in referans.items():
        if kokler:
            gruplar[bant(toplam[lemma])].append(lemma)
    secilen: list[str] = []
    for i, b in enumerate(BANTLAR):
        pay = n // len(BANTLAR) + (1 if i < n % len(BANTLAR) else 0)
        sirali = sorted(
            gruplar[b], key=lambda x: hashlib.sha256(f"{tohum}:{x}".encode()).hexdigest()
        )
        secilen.extend(sirali[:pay])
    return sorted(secilen)


# --- set kurulumu ------------------------------------------------------------------------


def set_kaynaklari(qwbw_surum: str, qac_surum: str, zeyrek_surum: str) -> list[dict[str, str]]:
    return [
        {
            "source_id": KAYNAK_QWBW,
            "surum": qwbw_surum,
            "madde": "6.json kelime anlamlari (sure/ayet/kelime)",
            "rol": "kanit",
        },
        {
            "source_id": KAYNAK_QAC,
            "surum": qac_surum,
            "madde": "quran_word.root_id (Arapca kelime -> kok; iki tarafta ortak sozluk)",
            "rol": "sozluk",
        },
        {
            "source_id": "zeyrek",
            "surum": zeyrek_surum,
            "madde": "lemmatizasyon (uretimle ortak arac)",
            "rol": "arac",
        },
    ]


def ornekleri_kur(
    secilen: Sequence[str],
    referans: Mapping[str, Mapping[int, int]],
    toplam: Mapping[str, int],
    kok_harfleri: Mapping[int, str],
    qwbw_surum: str,
) -> list[dict[str, object]]:
    ornekler: list[dict[str, object]] = []
    for lemma in secilen:
        kokler = referans[lemma]
        ornekler.append(
            {
                "id": lemma,
                "sinif": "silver",
                "kaynak": {
                    "source_id": KAYNAK_QWBW,
                    "surum": qwbw_surum,
                    "madde": "6.json kelime anlamlari (sure/ayet/kelime)",
                },
                "dogrulama_yontemi": DOGRULAMA_YONTEMI,
                "uretim_komutu": URETIM_KOMUTU,
                "tr_lemma": lemma,
                "siklik_bandi": bant(toplam[lemma]),
                "toplam_kelime": toplam[lemma],
                "referans_kokler": [
                    {"letters_bw": kok_harfleri[r], "destek": n} for r, n in sorted(kokler.items())
                ],
            }
        )
    return ornekler


def referans_satirlari(
    referans: Mapping[str, Mapping[int, int]],
    toplam: Mapping[str, int],
    kok_harfleri: Mapping[int, str],
) -> list[dict[str, object]]:
    """Tum referans evreni (ornek olmayan lemmalar dahil): rapor sayimlari icin."""
    return [
        {
            "lemma": lemma,
            "toplam_kelime": toplam[lemma],
            "referans_kokler": [
                {"letters_bw": kok_harfleri[r], "destek": n}
                for r, n in sorted(referans[lemma].items())
            ],
        }
        for lemma in sorted(toplam)
    ]


def referans_baytlari(satirlar: Sequence[Mapping[str, object]]) -> bytes:
    return b"".join(
        (
            json.dumps(dict(s), ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n"
        ).encode("ascii")
        for s in satirlar
    )


def referans_yaz(klasor: Path, satirlar: Sequence[Mapping[str, object]]) -> str:
    baytlar = referans_baytlari(satirlar)
    (klasor / REFERANS_ADI).write_bytes(baytlar)
    return hashlib.sha256(baytlar).hexdigest()


def referans_oku(klasor: Path, beklenen_sha: str) -> dict[str, dict[str, object]]:
    yol = klasor / REFERANS_ADI
    try:
        baytlar = yol.read_bytes()
    except OSError:
        raise GirdiHatasi("kok seti referans.jsonl okunamadi") from None
    if hashlib.sha256(baytlar).hexdigest() != beklenen_sha:
        raise GirdiHatasi("kok seti referans.jsonl ozeti manifestle tutmuyor")
    sonuc: dict[str, dict[str, object]] = {}
    for satir in baytlar.decode("ascii").splitlines():
        o = json.loads(satir)
        sonuc[str(o["lemma"])] = o
    return sonuc


@dataclass
class KokSeti:
    manifest: dict[str, object]
    ornekler: list[dict[str, object]]
    evren: dict[str, dict[str, object]]  # lemma -> referans.jsonl satiri
    satirlar: list[dict[str, object]]
    taslak: dict[str, object] = field(default_factory=dict)


def kok_seti_kur(
    *,
    referans: Mapping[str, Mapping[int, int]],
    toplam: Mapping[str, int],
    kok_harfleri: Mapping[int, str],
    qwbw_surum: str,
    qac_surum: str,
    zeyrek_surum: str,
    ozet_sayilar: Mapping[str, object],
    tohum: int = setler.VARSAYILAN_TOHUM,
    bugun: date | None = None,
) -> KokSeti:
    """Seti bellekte kurar (dosya yazmaz); `kok_seti_yaz` diske yazar."""
    secilen = ornek_sec(referans, toplam, ORNEK_SAYISI, tohum)
    ornekler = ornekleri_kur(secilen, referans, toplam, kok_harfleri, qwbw_surum)
    satirlar = referans_satirlari(referans, toplam, kok_harfleri)
    ozet = hashlib.sha256(referans_baytlari(satirlar)).hexdigest()
    taslak: dict[str, object] = {
        "sinif": "silver",
        "olcum_turu": "dogruluk",
        "kaynak": set_kaynaklari(qwbw_surum, qac_surum, zeyrek_surum),
        "dogrulama_yontemi": DOGRULAMA_YONTEMI,
        "uretim_komutu": URETIM_KOMUTU,
        "tohum": tohum,
        "min_destek": MIN_DESTEK,
        "min_pay": 1 / MIN_PAY_PAYDA,
        "bantlar": {
            "yuksek": f">= {BANT_YUKSEK}",
            "orta": f"{BANT_ORTA}-{BANT_YUKSEK - 1}",
            "dusuk": f"< {BANT_ORTA}",
        },
        "ornek_orneklemi": "banda gore tabakali, band basina esit pay, sabit tohum",
        "referans_sha256": ozet,
        "referans_lemma_sayisi": len(satirlar),
        "referansli_lemma_sayisi": sum(1 for s in satirlar if s["referans_kokler"]),
        "ozet_sayilar": dict(ozet_sayilar),
        "kapsam_kisiti": (
            "Yalniz Kur'an'da gecen sozcukleri olcer; ceviri esdegerligidir, etimoloji degildir."
        ),
    }
    manifest, _ = setler.set_hazirla("kok", taslak, ornekler, bugun=bugun)
    return KokSeti(manifest, ornekler, {str(s["lemma"]): s for s in satirlar}, satirlar, taslak)


def kok_seti_yaz(veri_kok: Path, seti: KokSeti) -> Path:
    """Seti ve `referans.jsonl` dosyasini yazar (ayni icerik yeniden yazilmaz)."""
    manifest, klasor = setler.set_yaz(
        veri_kok,
        "kok",
        seti.taslak,
        seti.ornekler,
        bugun=date.fromisoformat(str(seti.manifest["surum"])[:10]),
    )
    if manifest["surum"] != seti.manifest["surum"]:
        raise GirdiHatasi("kok seti surumu tutarsiz")
    if (
        not (klasor / REFERANS_ADI).is_file()
        and referans_yaz(klasor, seti.satirlar) != seti.manifest["referans_sha256"]
    ):
        raise GirdiHatasi("kok referansi ozeti tutarsiz")
    return klasor


def kok_seti_oku(veri_kok: Path) -> KokSeti:
    manifest, ornekler, klasor = setler.set_oku(veri_kok, "kok")
    evren = referans_oku(klasor, str(manifest["referans_sha256"]))
    return KokSeti(manifest, ornekler, evren, list(evren.values()))


# --- olcum -------------------------------------------------------------------------------


@dataclass(frozen=True)
class Tahmin:
    lemma: str
    kok: str  # letters_bw
    onay_yolu: str
    kaynaklar: frozenset[str]  # lemma.source_id + kanit.kaynaklar[].source_id
    eslesme: str = ""  # kanit.qac.eslesme: kok_harfleri | etimon_lemma | ikisi
    alanlar: frozenset[str] = frozenset()  # kanit.kaynaklar[].alan (kaikki sablon alanlari)


SORGU_TAHMIN: Final = (
    "SELECT l.text_clean, r.letters_bw, l.onay_yolu, l.source_id,"
    " COALESCE((SELECT array_agg(DISTINCT k ->> 'source_id')"
    "           FROM jsonb_array_elements(COALESCE(l.kanit -> 'kaynaklar', '[]'::jsonb)) k),"
    "          ARRAY[]::text[]),"
    " COALESCE(l.kanit -> 'qac' ->> 'eslesme', ''),"
    " COALESCE((SELECT array_agg(DISTINCT k ->> 'alan')"
    "           FROM jsonb_array_elements(COALESCE(l.kanit -> 'kaynaklar', '[]'::jsonb)) k),"
    "          ARRAY[]::text[])"
    " FROM icerik.lemma l JOIN icerik.root r ON r.id = l.root_id"
    " WHERE l.lang = 'tr' AND l.status = 'onayli' AND l.onay_yolu IN ('otomatik', 'editor')"
    " ORDER BY l.text_clean"
)


def tahminleri_oku(conn: psycopg.Connection) -> dict[str, Tahmin]:
    sonuc: dict[str, Tahmin] = {}
    for lemma, kok, yol, kaynak, kaynaklar, eslesme, alanlar in conn.execute(
        SORGU_TAHMIN
    ).fetchall():
        sonuc[str(lemma)] = Tahmin(
            str(lemma),
            str(kok),
            str(yol),
            frozenset({str(kaynak), *(str(k) for k in kaynaklar if k)}),
            str(eslesme),
            frozenset(str(a) for a in alanlar if a),
        )
    return sonuc


def kok_kumesi(satir: Mapping[str, object]) -> set[str]:
    """Bir referans satirindaki kok harfleri (`letters_bw`) kumesi."""
    kokler = satir["referans_kokler"]
    assert isinstance(kokler, list)
    return {str(k["letters_bw"]) for k in kokler}


def _alan_ozellikleri(t: Tahmin) -> dict[str, str]:
    """Bir tahminin politika koşulu özellikleri (kanit alanlarindan; metin yok)."""
    sablonlar = sorted({a.rsplit(".", 1)[-1] for a in t.alanlar})
    diller = sorted({a.split(":", 1)[0] for a in t.alanlar})
    return {
        "qac_eslesme": t.eslesme or "bilinmiyor",
        "kaikki_sablonlari": "+".join(sablonlar) or "yok",
        "kaikki_dilleri": "+".join(diller) or "yok",
        "root_sablonu": "var" if "root" in sablonlar else "yok",
    }


def daraltma_onerisi(
    tahminler: Mapping[str, Tahmin],
    referans_evreni: Mapping[str, Mapping[str, object]],
    esik: float = ESIKLER["kok"]["kesinlik"],
) -> dict[str, object]:
    """Referansi olan TUM tahminlerde politika ozelligine gore kesinlik (kapi kalirsa: K-51 md. 11).

    K-51 madde 11: kok kapisi tutmazsa rapor, politikanin hangi kosulunun daraltilacagini onerir.
    Bu oneri ayar degil bilgidir: set, esik ve kapi sonucu degismez; karari proje sahibi verir.
    Gruplar kendi icinde kesinligi `esik`i gecenler ve en az 20 tahminli olanlardir.
    """
    gruplar: dict[str, dict[str, list[bool]]] = {}
    for lemma, t in tahminler.items():
        satir = referans_evreni.get(lemma)
        if satir is None or not satir["referans_kokler"]:
            continue
        dogru = t.kok in kok_kumesi(satir)
        for ozellik, deger in _alan_ozellikleri(t).items():
            gruplar.setdefault(ozellik, {}).setdefault(deger, []).append(dogru)
    tablo: dict[str, dict[str, dict[str, object]]] = {}
    adaylar: list[dict[str, object]] = []
    for ozellik, degerler in sorted(gruplar.items()):
        tablo[ozellik] = {}
        for deger, liste in sorted(degerler.items()):
            n, d = len(liste), sum(liste)
            kes = round(d / n, 6)
            tablo[ozellik][deger] = {"tahmin": n, "dogru": d, "kesinlik": kes}
            if n >= 20 and kes >= esik:
                adaylar.append({"ozellik": ozellik, "deger": deger, "tahmin": n, "kesinlik": kes})
    yeterli = [
        {"ozellik": o, "deger": d, **v}
        for o, degerler in tablo.items()
        for d, v in degerler.items()
        if int(str(v["tahmin"])) >= 20
    ]
    en_iyi = sorted(
        yeterli, key=lambda g: (-float(str(g["kesinlik"])), str(g["ozellik"]), str(g["deger"]))
    )
    return {
        "olcut": "referansi olan tum tahminler (ornek degil); bilgi, ayar degil",
        "en_yuksek_kesinlikli_uc_grup_en_az_20_tahmin": en_iyi[:3],
        "ozellige_gore_kesinlik": tablo,
        "esigi_gecen_gruplar_en_az_20_tahmin": adaylar,
        "oneri": (
            "Kosul (b)/(c) bu ozelliklerden biriyle daraltilabilir: "
            + ", ".join(f"{a['ozellik']}={a['deger']}" for a in adaylar)
            if adaylar
            else "Tek bir ozellikle daraltma esigi (kesinlik >= 0,95, en az 20 tahmin) tutturmuyor"
        ),
    }


def kok_olc(
    manifest: Mapping[str, object],
    ornekler: Sequence[Mapping[str, object]],
    referans_evreni: Mapping[str, Mapping[str, object]],
    tahminler: Mapping[str, Tahmin],
) -> TurSonucu:
    """Dondurulmus parcada kapi olcumu; gelistirme ve tum evren bilgi olarak yazilir."""
    setler.manifest_dongusellik_denetle(
        manifest, {k for t in tahminler.values() for k in t.kaynaklar}
    )
    uretim = sorted({k for t in tahminler.values() for k in t.kaynaklar})

    def kume(o: Mapping[str, object]) -> set[str]:
        kokler = o["referans_kokler"]
        assert isinstance(kokler, list)
        return {str(k["letters_bw"]) for k in kokler}

    def baskin(o: Mapping[str, object]) -> str:
        kokler = o["referans_kokler"]
        assert isinstance(kokler, list)
        en_iyi = max(kokler, key=lambda k: (int(k["destek"]), str(k["letters_bw"])))
        return str(en_iyi["letters_bw"])

    def parca_olc(secim: Sequence[Mapping[str, object]]) -> dict[str, object]:
        tahminli = [o for o in secim if str(o["tr_lemma"]) in tahminler]
        dogru = [o for o in tahminli if tahminler[str(o["tr_lemma"])].kok in kume(o)]
        p = prf_sayimdan(len(dogru), len(tahminli), len(dogru), len(secim))
        sonuc: dict[str, object] = {
            "ornek": len(secim),
            "tahminli": len(tahminli),
            "dogru": len(dogru),
            "kesinlik": round(p.kesinlik, 6),
            "duyarlilik": round(p.duyarlilik, 6),
            "f1": round(p.f1, 6),
        }
        if tahminli:  # kesinlik araligi = 1 - hata orani Wilson araligi
            hata = len(tahminli) - len(dogru)
            sonuc["kesinlik_wilson_alt_95"] = round(1.0 - wilson_ust_sinir(hata, len(tahminli)), 6)
            sonuc["kesinlik_wilson_ust_95"] = round(1.0 - wilson_alt_sinir(hata, len(tahminli)), 6)
        return sonuc

    donduruldu = [
        o
        for o in ornekler
        if setler.bolme("kok", str(o["id"]), int(str(manifest["tohum"]))) == setler.DONDURULMUS
    ]
    gelistirme = [o for o in ornekler if o not in donduruldu]
    kapi = parca_olc(donduruldu)
    bilgi_gelistirme = parca_olc(gelistirme)
    bilgi_tum = parca_olc(list(ornekler))

    bant_kirilimi: dict[str, object] = {}
    for b in BANTLAR:
        bant_kirilimi[b] = parca_olc([o for o in donduruldu if o["siklik_bandi"] == b])

    # kappa: kaynaklar arasi uyum (kaikki tabanli eslesme / QuranWBW tabanli baskin referans kok)
    cift = [o for o in donduruldu if str(o["tr_lemma"]) in tahminler]
    kappa: dict[str, object]
    if len(cift) >= 2:
        k = kappa_sklearn(
            [tahminler[str(o["tr_lemma"])].kok for o in cift], [baskin(o) for o in cift]
        )
        kappa = {
            "n": k.n,
            "kappa": round(k.kappa, 6),
            "kappa_uyum_py": round(k.kappa_uyum_py, 6),
            "tek_kategori": k.tek_kategori,
            "tur": (
                "kaynaklar arasi uyum (kaikki tabanli eslesme / QuranWBW tabanli baskin referans "
                "kok)"
            ),
            "not": "insan kappasi degildir; kappa esigi S-16'ya kadar uygulanmaz (K-50)",
        }
    else:
        kappa = {"n": len(cift), "atlandi": "kappa icin en az iki ortak lemma gerekir"}

    # tum evren (ornek olmayanlar dahil) bilgi sayimlari
    referansli = {m for m, o in referans_evreni.items() if o["referans_kokler"]}
    tahmin_referansli = [x for x in tahminler if x in referansli]
    tum_dogru = sum(
        1 for x in tahmin_referansli if tahminler[x].kok in kok_kumesi(referans_evreni[x])
    )
    quranwbw_gecen_yetersiz = [x for x in tahminler if x in referans_evreni and x not in referansli]
    quranwbw_gecmeyen = [x for x in tahminler if x not in referans_evreni]
    lemma_tablosunda_referansli_ornek = [o for o in donduruldu if str(o["tr_lemma"]) in tahminler]
    kapsam: dict[str, object] = {
        "tahmin_toplam": len(tahminler),
        "tahmin_referansli": len(tahmin_referansli),
        "tahmin_referanssiz_olcume_katilmadi": len(tahminler) - len(tahmin_referansli),
        "tahmin_quranwbw_de_gecen_ama_destek_yetersiz": len(quranwbw_gecen_yetersiz),
        "tahmin_quranwbw_de_gecmeyen": len(quranwbw_gecmeyen),
        "tum_evren_referansli_lemma": len(referansli),
        "tum_evren_kesinlik_tahmin": len(tahmin_referansli),
        "tum_evren_kesinlik_dogru": tum_dogru,
        "tum_evren_kesinlik": round(tum_dogru / len(tahmin_referansli), 6)
        if tahmin_referansli
        else None,
        "tahminli_ornek_dondurulmus": len(lemma_tablosunda_referansli_ornek),
        "not": (
            "Set yalniz Kur'an'da gecen sozcukleri olcer. Referans yalniz QuranWBW ceviri"
            " esdegerligidir; referansi olmayan tahminler yanlis degil, OLCULMEMISTIR."
        ),
    }
    olculer = {
        "kesinlik": float(str(kapi["kesinlik"])),
        "duyarlilik": float(str(kapi["duyarlilik"])),
        "f1": float(str(kapi["f1"])),
    }
    esikler = dict(ESIKLER["kok"])
    sonuc = kapi_karari(esikler, olculer)
    notlar = [
        "Referans QuranWBW ceviri esdegerligidir (etimoloji degil);"
        " 'yalnizca etimolojik' etiketi icin olcum yoktur.",
        "Kapsam: set yalniz Kur'an'da gecen sozcukleri olcer;"
        " referansi olmayan tahminler olcume katilmaz.",
        "QAC kok sozlugu set ve uretim icin ortak (rol sozluk):"
        " kok kimlikleri ve Arapca kelime -> kok ayni kaynaktan.",
        "Kappa kaynaklar arasi uyumdur, insan kappasi degildir;"
        " kappa esigi S-16'ya kadar uygulanmaz.",
        "Duyarlilik: referansi olan orneklerin tamami paydadir"
        " (tahmini olmayan ornek yanlis sayilir).",
    ]
    ozet = tahmin_ozeti([f"{t.lemma}|{t.kok}|{t.onay_yolu}" for _, t in sorted(tahminler.items())])
    return TurSonucu(
        cli_tur="kok",
        manifest=manifest,
        sonuc=sonuc,
        olculer=olculer,
        esikler=esikler,
        esik_sonuclari=esik_degerlendir(esikler, olculer),
        tahmin_ozeti=ozet,
        olculen_ornek=len(donduruldu),
        ayrintilar={
            "dondurulmus_kapi_olcumu": kapi,
            "gelistirme_bilgi": bilgi_gelistirme,
            "tum_ornek_bilgi": bilgi_tum,
            "bant_kirilimi_dondurulmus": bant_kirilimi,
            "kappa": kappa,
            "min_destek": MIN_DESTEK,
            "min_pay": 1 / MIN_PAY_PAYDA,
            "ornek_bant_sayilari": dict(Counter(str(o["siklik_bandi"]) for o in ornekler)),
            "tahmin_onay_yolu": dict(Counter(t.onay_yolu for t in tahminler.values())),
            "politika_daraltma_onerisi": daraltma_onerisi(tahminler, referans_evreni),
        },
        notlar=notlar,
        referans_kapsami=kapsam,
        uretim_kaynaklari=uretim,
    )


KokKur = Callable[[], Lemmatizer]
