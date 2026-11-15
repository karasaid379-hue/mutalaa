"""RNK baski sayfa esleme adimi (A20.3, K-52 madde 6 ve 7): `risale-baski-rnk`.

`mutalaa anchor --source risale-baski-rnk`: `risale-rnk-metin` zincirinin iki ciktisini okur ve
`page_map` satirlarini `staged/risale-baski-rnk/{run_id}/` altina yazar:

* son `anchor` calismasinin `units.jsonl` dosyasi (capalar, metin uzunlugu, okuma sirasi);
* o calismanin zincirindeki `ingest` calismasinin `sayfalar.jsonl` dosyasi (`#n` sayfa baslari:
  `dosya`, `n`, `satir`, `capa`, `ofs`, `tur`).

Cikti `page_map.jsonl` (yalniz sayi ve capa; METIN YOK) ve kitap basina `page_map_rapor.jsonl`.
Her satir `start_hash` ve `end_hash` (uc birimlerin `content_hash` degeri) tasir: `page_map`
tablosuna yazilmaz, `export pg` yukleme anindaki birim ozeti denetimi icindir.

SATIR KURALLARI (K-52 madde 6; Editoryal veritabani 9.1):

* Tek tablo: `source_id = risale-baski-rnk`, `volume` RNK dosyasinin (`{raf}/{uid}`) cilt
  numarasidir, `page` basili sayfa numarasidir (`#n`), `line` NULL'dur. Anahtar
  `(source_id, volume, page, line)` oldugu icin bir sayfa en cok bir satirdir.
* `volume` DDL'de `smallint`tir; RNK kitap kimligi (`uid`) metindir. Bu yuzden `volume`,
  `risale-kitaplar.json` `rnk.cilt` alanindaki KALICI cilt numarasidir (1'den; bir kez verilir,
  degismez, yeni RNK dosyasi sona eklenir; K-52 madde 6). Numara <-> `{raf}/{uid}` eslesmesi her
  kosuda manifestte (`ayrintilar.cilt`) yazilidir.
* Gercek sayfa satiri: `start_anchor` sayfanin ILK metin karakterinin ait oldugu birimin capasi
  (sayfa tam birim basinda ise `start_offset = 0`, birim ortasinda `ofs`); `end_anchor` bir
  sonraki sayfanin baslangicindan onceki son birimdir: sonraki sayfa birim ortasinda basliyorsa
  ayni birim ve `end_offset = ofs`, birim basinda basliyorsa onceki birim ve `end_offset` onun
  uzunlugu; son sayfada dosyanin son birimi. Ofsetler Unicode kod noktasi, aralik yari acik.
  Sunuhat/Tuluat/Isarat gibi bolunen RNK dosyasinda sayfa listesi dosya duzeyindedir; satir
  capanin kendi kitap slug'ini gosterir.
* Bos sayfa (kaynakta `#n` var, metin yok; sonraki sayfayla ayni baslangic): sifir uzunluklu
  satir, `end = start` (sayilir ve raporlanir). Hic metni olmayan sayfa (`tur = icerik-yok`) satir
  uretmez; sayilir. Kaynakta olmayan sayfa numarasi doldurulmaz.
* Bolum basi satiri (`data_version` soneki `/bolum-basi`): bolumun ilk birimi (json dugumuyle
  eslesen baslik) capasi, `start_offset = 0`; sayfa bolumun GERCEK `#n` sayfasidir (json
  `pageNo` degil; farkli olan bolum sayisi raporlanir). Ayni sayfanin gercek satiri varsa o satir
  kalir: bolum o sayfada tam basliyorsa gercek satir bolum basi satirinin yerine gecer (cift
  yazma yok); sayfa ortasinda basliyorsa ya da ayni sayfada baska bolum de basliyorsa bolum basi
  satiri yazilamaz (tekil anahtar) ve yalniz rapora sayilir. Sayfasi bilinmeyen baslik (ilk `#n`
  isaretinden once ya da sayfa isaretsiz dosya) satir uretmez, `bolum_basi_sayfasiz` sayilir.
  Gercek satiri olmayan sayfada ilk bolum yazilir; bitisi bir sonraki satir baslangicindan oncedir.

Idempotent: ayni girdi ayni baytlari uretir (zaman damgasi yok). Hata iletileri metin tasimaz.
"""

import bisect
import sys
from collections import Counter, defaultdict
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path
from typing import Final

from mutalaa_pipeline import cikis, lineage
from mutalaa_pipeline.adimlar.risale import ord_anahtari_degerleri
from mutalaa_pipeline.anchor import SortKey
from mutalaa_pipeline.anchor.risale import Kitap, kitaplar
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.ingest.risale_kaynaklari import KAYNAK_BASKI, KAYNAK_RNK
from mutalaa_pipeline.ingest.risale_rnk_kaynaklari import SAYFALAR_ADI
from mutalaa_pipeline.komut_ortak import komutu_yurut
from mutalaa_pipeline.lineage import UNITS_ADI
from mutalaa_pipeline.runctx import RunContext
from mutalaa_pipeline.staged import Satir, dosya_yaz, satirlari_akit, satirlari_oku
from mutalaa_pipeline.zincir import (
    ANCHOR_ADIMI,
    INGEST_ADIMI,
    NORMALIZE_ADIMI,
    Calisma,
    girdi_olarak,
    girdileri_ayni,
    saglam_olmali,
    son_calisma,
    ust_calismalar,
)

KAYNAK: Final = KAYNAK_BASKI
SAYFA_ESLEME_ADI: Final = "page_map.jsonl"
SAYFA_RAPOR_ADI: Final = "page_map_rapor.jsonl"
BOLUM_BASI_EKI: Final = "/bolum-basi"
SMALLINT_USTU: Final = 32767
SATIR_ALANLARI: Final = frozenset(
    {
        "source_id",
        "volume",
        "page",
        "start_anchor",
        "start_offset",
        "end_anchor",
        "end_offset",
        "data_version",
        # Yukleme anindaki on kosul icin (page_map tablosuna YAZILMAZ): baslangic ve bitis
        # birimlerinin staged `content_hash` degeri; veritabanindaki birimle karsilastirilir.
        "start_hash",
        "end_hash",
    }
)
SAYFA_ALANLARI: Final = frozenset({"dosya", "n", "satir", "capa", "ofs", "tur"})
SATIR_ANAHTARI: Final = ("volume", "page")
RAPOR_ANAHTARI: Final = ("dosya",)
TUR_BAS: Final = "bas"
TUR_ORTASI: Final = "ortasi"
TUR_ICERIK_YOK: Final = "icerik-yok"


# --- cilt numarasi ------------------------------------------------------------------------


def cilt_tablosu(tablo: tuple[Kitap, ...] | None = None) -> dict[str, int]:
    """`{raf}/{uid}` -> kalici cilt numarasi (`volume`): `risale-kitaplar.json` `rnk.cilt`.

    Numara bir kez verilir ve degismez; yeni RNK dosyasi sona eklenir (K-52 madde 6). Bolunen
    dosyada (sunuhat) uc slug ayni numarayi tasir. Tablo yukleyicisi tekilligi ve araligi da
    denetler; burada tablo disaridan verilebildigi icin yeniden sinanir.
    """
    sonuc: dict[str, int] = {}
    for k in tablo if tablo is not None else kitaplar():
        if k.rnk is None or k.rnk.cilt is None:
            raise GirdiHatasi("RNK baglantisi ya da cilt numarasi olmayan kitap")
        ad = f"{k.rnk.raf}/{k.rnk.uid}"
        if sonuc.setdefault(ad, k.rnk.cilt) != k.rnk.cilt:
            raise GirdiHatasi("ayni RNK dosyasi iki cilt numarasi tasiyor")
    aralikta = all(1 <= c <= SMALLINT_USTU for c in sonuc.values())
    if len(set(sonuc.values())) != len(sonuc) or not aralikta:
        raise GirdiHatasi("cilt numaralari tekil ve smallint araliginda olmali")
    return sonuc


def data_versiyonu(surum: str, *, bolum_basi: bool = False) -> str:
    """`risale-baski-rnk@{surum}`; bolum basi satirinda `/bolum-basi` soneki."""
    temel = f"{KAYNAK}@{surum}"
    return temel + BOLUM_BASI_EKI if bolum_basi else temel


# --- girdiler -----------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class BirimKonumu:
    """`units.jsonl` birimi: capa, metin uzunlugu (kod noktasi) ve okuma sirasi anahtari.

    `bolum_sayfasi`: json dugumuyle eslesen baslik biriminde dugumun `pageNo` degeri;
    `sayfa`: birimin kaynak satirinin sayfasi; `cumle_baslari`: yalniz sayfa baslayan birimlerde
    cumle baslangic ofsetleri (metin yok, yalniz sayi).
    """

    capa: str
    uzunluk: int
    dosya: str
    anahtar: tuple[int, int, SortKey]
    bolum_sayfasi: int | None
    sayfa: int | None
    cumle_baslari: tuple[tuple[int, int], ...] | None = None
    ozet: str = ""  # birimin `content_hash` degeri (page_map yukleme on kosulu)


def _tam(deger: object, ad: str) -> int:
    if isinstance(deger, bool) or not isinstance(deger, int):
        raise GirdiHatasi(f"{ad}: tam sayi bekleniyor")
    return deger


def birim_konumu(satir: Satir, cumle_kumesi: frozenset[str]) -> BirimKonumu:
    """Anchor ciktisinin bir satirindan konum bilgisi (metin saklanmaz)."""
    capa = satir.metin("anchor")
    saglayici = satir.nesne("provenance")
    attrs = satir.nesne("attrs")
    raf, uid = saglayici.get("raf"), saglayici.get("uid")
    if not isinstance(raf, str) or not isinstance(uid, str):
        raise GirdiHatasi(f"{satir.etiket}: satir {satir.no}: provenance.raf/uid yok")
    anahtar = ord_anahtari_degerleri(capa, saglayici)
    dugum = attrs.get("json_dugum")
    bolum = _tam(dugum["pageNo"], f"{capa} json_dugum") if isinstance(dugum, dict) else None
    sayfa = attrs.get("sayfa")
    cumleler: tuple[tuple[int, int], ...] | None = None
    if capa in cumle_kumesi:
        ham = satir.veri.get("sentences")
        if not isinstance(ham, list):
            raise GirdiHatasi(f"{satir.etiket}: satir {satir.no}: sentences liste degil")
        cumleler = tuple(
            (_tam(a[0], "sentences"), _tam(a[1], "sentences"))
            for a in ham
            if isinstance(a, list) and len(a) == 2
        )
    return BirimKonumu(
        capa=capa,
        uzunluk=len(satir.metin("text")),
        dosya=f"{raf}/{uid}",
        anahtar=(anahtar[2], anahtar[3], anahtar[4]),
        bolum_sayfasi=bolum,
        sayfa=sayfa if isinstance(sayfa, int) and not isinstance(sayfa, bool) else None,
        cumle_baslari=cumleler,
        ozet=satir.metin("content_hash"),
    )


def birimleri_grupla(
    satirlar: Iterator[Satir], cumle_kumesi: frozenset[str] = frozenset()
) -> dict[str, list[BirimKonumu]]:
    """Dosya (`raf/uid`) -> okuma sirasindaki birimler; capa dosya icinde tekil olmali."""
    gruplar: dict[str, list[BirimKonumu]] = defaultdict(list)
    for satir in satirlar:
        b = birim_konumu(satir, cumle_kumesi)
        gruplar[b.dosya].append(b)
    for dosya, liste in gruplar.items():
        liste.sort(key=lambda b: b.anahtar)
        if len({b.capa for b in liste}) != len(liste):
            raise GirdiHatasi(f"{dosya}: yinelenen capa")
    return dict(gruplar)


def sayfa_baslari_oku(satirlar: Sequence[Satir]) -> dict[str, list[dict[str, object]]]:
    """`sayfalar.jsonl` satirlari: dosya -> sayfa numarasina gore sirali kayitlar (kati bicim)."""
    sonuc: dict[str, list[dict[str, object]]] = defaultdict(list)
    for satir in satirlar:
        if set(satir.veri) != SAYFA_ALANLARI:
            raise GirdiHatasi(f"{satir.etiket}: satir {satir.no}: alan kumesi beklenen degil")
        dosya = satir.metin("dosya")
        satir.sayi("n")
        satir.sayi("satir")
        satir.sayi("ofs")
        tur = satir.metin("tur")
        if tur not in (TUR_BAS, TUR_ORTASI, TUR_ICERIK_YOK):
            raise GirdiHatasi(f"{satir.etiket}: satir {satir.no}: tur gecersiz")
        if (satir.veri["capa"] is None) != (tur == TUR_ICERIK_YOK):
            raise GirdiHatasi(f"{satir.etiket}: satir {satir.no}: capa ile tur tutarsiz")
        sonuc[dosya].append(satir.veri)
    for liste in sonuc.values():
        liste.sort(key=lambda k: _tam(k["n"], "n"))
    return dict(sonuc)


def baslangic_capalari(sayfalar: Mapping[str, Sequence[Mapping[str, object]]]) -> frozenset[str]:
    return frozenset(
        str(k["capa"]) for liste in sayfalar.values() for k in liste if k["capa"] is not None
    )


# --- satir uretimi ------------------------------------------------------------------------


@dataclass(frozen=True, order=True, slots=True)
class Konum:
    """Dosyadaki birim sirasi (`r`) ve kod noktasi ofseti (`o`)."""

    r: int
    o: int


def _bitis(birimler: Sequence[BirimKonumu], bas: Konum, sonraki: Konum | None) -> Konum:
    """Bir satirin bitisi: sonraki baslangictan onceki son konum (yari acik)."""
    if sonraki is None:
        son = len(birimler) - 1
        return Konum(son, birimler[son].uzunluk)
    if sonraki == bas:
        return bas  # bos sayfa: sifir uzunluk
    if sonraki.o > 0:
        return sonraki
    onceki = sonraki.r - 1
    return Konum(onceki, birimler[onceki].uzunluk)


def _satir(
    volume: int,
    sayfa: int,
    birimler: Sequence[BirimKonumu],
    bas: Konum,
    bit: Konum,
    surum: str,
    *,
    bolum_basi: bool,
) -> dict[str, object]:
    return {
        "source_id": KAYNAK,
        "volume": volume,
        "page": sayfa,
        "start_anchor": birimler[bas.r].capa,
        "start_offset": bas.o,
        "end_anchor": birimler[bit.r].capa,
        "end_offset": bit.o,
        "data_version": data_versiyonu(surum, bolum_basi=bolum_basi),
        "start_hash": birimler[bas.r].ozet,
        "end_hash": birimler[bit.r].ozet,
    }


@dataclass
class DosyaSonucu:
    satirlar: list[dict[str, object]]
    rapor: dict[str, object]


def _cumle_ortasi(b: BirimKonumu, ofs: int) -> bool:
    """Sayfa basi bir cumlenin icine mi dusuyor (sinirlar arasi bosluk cumle ortasi sayilmaz)."""
    return any(bas < ofs < son for bas, son in b.cumle_baslari or ())


def dosya_satirlari(
    dosya: str,
    volume: int,
    sayfalar: Sequence[Mapping[str, object]],
    birimler: Sequence[BirimKonumu],
    surum: str,
) -> DosyaSonucu:
    """Bir RNK dosyasinin gercek sayfa satirlari ve bolum basi satirlari ile kitap raporu."""
    if not birimler:
        raise GirdiHatasi(f"{dosya}: anchor ciktisinda birim yok")
    indeks = {b.capa: i for i, b in enumerate(birimler)}
    numaralar = [_tam(k["n"], f"{dosya} n") for k in sayfalar]
    if len(set(numaralar)) != len(numaralar):
        raise GirdiHatasi(f"{dosya}: yinelenen sayfa numarasi")
    baslar: list[tuple[int, Konum]] = []
    icerik_yok = 0
    for k, n in zip(sayfalar, numaralar, strict=True):
        capa = k["capa"]
        if capa is None:
            icerik_yok += 1
            continue
        i = indeks.get(str(capa))
        ofs = _tam(k["ofs"], f"{dosya}#{n} ofs")
        if i is None:
            raise GirdiHatasi(f"{dosya}#{n}: sayfa capasi anchor ciktisinda yok")
        if not 0 <= ofs < birimler[i].uzunluk:
            raise GirdiHatasi(f"{dosya}#{n}: sayfa ofseti birim metnine sigmiyor")
        if (k["tur"] == TUR_BAS) != (ofs == 0):
            raise GirdiHatasi(f"{dosya}#{n}: tur ofsetle tutmuyor")
        baslar.append((n, Konum(i, ofs)))
    for (a, ka), (c, kc) in pairwise(baslar):
        if kc < ka:
            raise GirdiHatasi(f"{dosya}: sayfa {c} sayfa {a} oncesinde basliyor")
    gercek: dict[int, Konum] = dict(baslar)
    satirlar: list[dict[str, object]] = []
    bos = 0
    birim_basi = cumle_basi = cumle_ortasi = 0
    slug_sayfa: Counter[str] = Counter()
    for sira, (n, bas) in enumerate(baslar):
        sonraki = baslar[sira + 1][1] if sira + 1 < len(baslar) else None
        bit = _bitis(birimler, bas, sonraki)
        if bit == bas:
            bos += 1
        satirlar.append(_satir(volume, n, birimler, bas, bit, surum, bolum_basi=False))
        slug_sayfa[birimler[bas.r].capa.split(":")[1]] += 1
        if bas.o == 0:
            birim_basi += 1
        elif _cumle_ortasi(birimler[bas.r], bas.o):
            cumle_ortasi += 1
        else:
            cumle_basi += 1

    # --- bolum basi ---------------------------------------------------------------------
    ilk_n = min(numaralar) if numaralar else None
    son_n = max(numaralar) if numaralar else None
    gorulen: set[int] = set()
    yerine_gecen = sayfa_ortasi = ayni_sayfada = sayfasiz = json_farkli = 0
    yazilacak: list[tuple[int, Konum]] = []
    for sira_b, b in enumerate(birimler):
        if b.bolum_sayfasi is None:
            continue  # json dugumuyle eslesen baslik degil
        p = b.sayfa  # bolumun sayfasi gercek `#n` sayfasidir (K-52 madde 6), json pageNo degil
        if p is None:
            sayfasiz += 1  # ilk `#n` isaretinden once ya da sayfa isaretsiz dosya: rapor
            continue
        if p != b.bolum_sayfasi:
            json_farkli += 1
        konum = Konum(sira_b, 0)
        if gercek.get(p) == konum:
            yerine_gecen += 1
        elif p in gorulen:
            ayni_sayfada += 1
        elif p in gercek:
            sayfa_ortasi += 1
        else:
            yazilacak.append((p, konum))
        gorulen.add(p)
    tum_baslar = sorted({k for _, k in baslar} | {k for _, k in yazilacak})
    for p, bas in yazilacak:
        yer = bisect.bisect_right(tum_baslar, bas)
        sonraki = tum_baslar[yer] if yer < len(tum_baslar) else None
        satirlar.append(
            _satir(volume, p, birimler, bas, _bitis(birimler, bas, sonraki), surum, bolum_basi=True)
        )
    satirlar.sort(key=lambda s: (_tam(s["volume"], "volume"), _tam(s["page"], "page")))
    artis = all(b - a == 1 for a, b in pairwise(sorted(numaralar)))
    rapor: dict[str, object] = {
        "dosya": dosya,
        "volume": volume,
        "sayfa": len(numaralar),
        "ilk_sayfa": ilk_n,
        "son_sayfa": son_n,
        "ardisik": artis,
        "gercek_satir": len(baslar),
        "icerik_yok": icerik_yok,
        "bos_sayfa": bos,
        "sayfa_basi_birim_basi": birim_basi,
        "sayfa_basi_cumle_basi": cumle_basi,
        "sayfa_basi_cumle_ortasi": cumle_ortasi,
        "bolum_basi_yazilan": len(yazilacak),
        "bolum_basi_yerine_gecen": yerine_gecen,
        "bolum_basi_sayfa_ortasi": sayfa_ortasi,
        "bolum_basi_ayni_sayfada_ikinci": ayni_sayfada,
        "bolum_basi_sayfasiz": sayfasiz,
        "bolum_basi_json_sayfa_farkli": json_farkli,
        "slug_sayfa": dict(sorted(slug_sayfa.items())),
    }
    return DosyaSonucu(satirlar, rapor)


def sayfa_esleme_uret(
    birimler: Mapping[str, Sequence[BirimKonumu]],
    sayfalar: Mapping[str, Sequence[Mapping[str, object]]],
    cilt: Mapping[str, int],
    surum: str,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """Butun RNK dosyalari: `(page_map satirlari, kitap raporlari)`; cilt tablosunda olmali."""
    bilinmeyen = sorted((set(birimler) | set(sayfalar)) - set(cilt))
    if bilinmeyen:
        raise GirdiHatasi(
            f"kitap tablosunda olmayan RNK dosyasi ({len(bilinmeyen)}): {bilinmeyen[:5]}"
        )
    satirlar: list[dict[str, object]] = []
    raporlar: list[dict[str, object]] = []
    for dosya, volume in cilt.items():
        sonuc = dosya_satirlari(
            dosya, volume, sayfalar.get(dosya, ()), birimler.get(dosya, ()), surum
        )
        satirlar.extend(sonuc.satirlar)
        raporlar.append(sonuc.rapor)
    satirlar.sort(key=lambda s: (_tam(s["volume"], "volume"), _tam(s["page"], "page")))
    raporlar.sort(key=lambda r: str(r["dosya"]))  # dosyadaki siralamayla ayni (`dosya_yaz`)
    return satirlar, raporlar


# --- adim ---------------------------------------------------------------------------------


@dataclass(frozen=True)
class SayfaZinciri:
    anchor: Calisma
    normalize: Calisma
    ingest: Calisma


def _ust(ctx: RunContext, calisma: Calisma, adim: str, kaynak: str) -> Calisma:
    ustler = ust_calismalar(ctx, calisma)
    if len(ustler) != 1 or ustler[0].adim != adim or ustler[0].source_id != kaynak:
        raise GirdiHatasi(
            f"zincir bozuk: {calisma.adim} calistirmasi bir {kaynak} {adim} calistirmasina"
            " bagli olmali"
        )
    saglam_olmali(ctx, ustler[0])
    return ustler[0]


def zincir_coz(ctx: RunContext, anchor: Calisma) -> SayfaZinciri:
    """`risale-rnk-metin` anchor calismasinin zinciri: normalize ve ingest (ciktilari saglam)."""
    saglam_olmali(ctx, anchor)
    normalize = _ust(ctx, anchor, NORMALIZE_ADIMI, KAYNAK_RNK)
    ingest = _ust(ctx, normalize, INGEST_ADIMI, KAYNAK_RNK)
    return SayfaZinciri(anchor, normalize, ingest)


@dataclass(frozen=True)
class AdimSonucu:
    run_id: str
    atlandi: bool
    sayfa_sayisi: int
    bolum_basi: int
    klasor: Path | None
    onceki_run_id: str | None = None


def girdileri_oku(
    zincir: SayfaZinciri,
) -> tuple[dict[str, list[dict[str, object]]], dict[str, list[BirimKonumu]]]:
    """Zincirdeki iki dosya: `(sayfa baslari, okuma sirasindaki birimler)` (dosya = `raf/uid`)."""
    ozet = zincir.ingest.cikti_ozeti(SAYFALAR_ADI)
    if ozet is None:
        raise GirdiHatasi(f"ingest manifestinde {SAYFALAR_ADI} ozeti yok: {zincir.ingest.run_id}")
    try:
        veri = (zincir.ingest.klasor / SAYFALAR_ADI).read_bytes()
    except OSError:
        raise GirdiHatasi(f"{SAYFALAR_ADI} okunamadi") from None
    if lineage.sha256_bayt(veri) != ozet:
        raise GirdiHatasi(f"{SAYFALAR_ADI} ozeti manifestle tutmuyor")
    sayfalar = sayfa_baslari_oku(satirlari_oku(veri, f"{KAYNAK_RNK} {SAYFALAR_ADI}"))
    birimler = birimleri_grupla(
        satirlari_akit(zincir.anchor.klasor / UNITS_ADI, f"anchor {KAYNAK_RNK} {UNITS_ADI}"),
        baslangic_capalari(sayfalar),
    )
    return sayfalar, birimler


def sayfa_satirlarini_hazirla(
    zincir: SayfaZinciri, cilt: Mapping[str, int], surum: str
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """Zincirdeki iki dosyadan `(page_map satirlari, kitap raporlari)`."""
    sayfalar, birimler = girdileri_oku(zincir)
    return sayfa_esleme_uret(birimler, sayfalar, cilt, surum)


def run_sayfa(ctx: RunContext) -> AdimSonucu:
    """Kaynak kaydi, zincir, parmak izi, satirlar, rapor, manifest (en son)."""
    kayit = ctx.require_sources(KAYNAK)[KAYNAK]
    if kayit.surum is None:
        raise GirdiHatasi(f"kaynak {KAYNAK}: surum cozulemedi (TOML surum alani yok)")
    ctx.gunluk.yaz("INFO", "sayfa_esleme_basla", source_id=KAYNAK)
    anchor = son_calisma(ctx, KAYNAK_RNK, ANCHOR_ADIMI, ipucu=f"once: anchor --source {KAYNAK_RNK}")
    zincir = zincir_coz(ctx, anchor)
    girdiler = [
        girdi_olarak(anchor, UNITS_ADI),
        girdi_olarak(zincir.ingest, SAYFALAR_ADI),
    ]
    parmak = ctx.parmak_izi(girdiler)
    onceki = lineage.son_basarili(ctx.staged_kaynak_dizini(KAYNAK), ctx.adim)
    onceki_manifest = onceki[2] if onceki else None
    if girdileri_ayni(onceki_manifest, girdiler) and lineage.atlanabilir(
        onceki=onceki_manifest,
        parmak=parmak,
        git_kirli=ctx.git().kirli,
        force=ctx.force,
        veri_kok=ctx.veri_kok,
    ):
        ctx.gunluk.yaz("INFO", "sayfa_esleme_atlandi", source_id=KAYNAK)
        ctx.sayi("atlandi", 1)
        return AdimSonucu(ctx.run_id, True, 0, 0, None, onceki[0] if onceki else None)

    cilt = cilt_tablosu()
    satirlar, raporlar = sayfa_satirlarini_hazirla(zincir, cilt, kayit.surum)
    sayfa_cikti = dosya_yaz(ctx, KAYNAK, SAYFA_ESLEME_ADI, satirlar, SATIR_ANAHTARI)
    rapor_cikti = dosya_yaz(ctx, KAYNAK, SAYFA_RAPOR_ADI, raporlar, RAPOR_ANAHTARI)
    bolum_basi = sum(_tam(r["bolum_basi_yazilan"], "rapor") for r in raporlar)
    ctx.sayi("sayfa", len(satirlar))
    ctx.sayi("bolum_basi", bolum_basi)
    if ctx.dry_run:
        ctx.gunluk.yaz(
            "INFO",
            "sayfa_esleme_dry_run",
            source_id=KAYNAK,
            sayilar={"sayfa": len(satirlar), "bolum_basi": bolum_basi},
        )
        return AdimSonucu(ctx.run_id, False, len(satirlar), bolum_basi, None)

    klasor = ctx.staged_dizin(KAYNAK)
    toplam: Counter[str] = Counter()
    for r in raporlar:
        for alan, deger in r.items():
            if (
                isinstance(deger, int)
                and not isinstance(deger, bool)
                and alan not in ("volume", "ilk_sayfa", "son_sayfa")
            ):
                toplam[alan] += deger
    ctx.manifest_yaz(
        klasor,
        girdiler=girdiler,
        ciktilar=[sayfa_cikti, rapor_cikti],
        parmak=parmak,
        ayrintilar={
            "kaynak": KAYNAK,
            "data_version": data_versiyonu(kayit.surum),
            "metin_kaynagi": KAYNAK_RNK,
            "anchor_run": anchor.run_id,
            "ingest_run": zincir.ingest.run_id,
            "satir": len(satirlar),
            "dosya": len(raporlar),
            "toplamlar": dict(sorted(toplam.items())),
            "cilt": cilt,
        },
    )
    ctx.gunluk.yaz("INFO", "sayfa_esleme_bitti", source_id=KAYNAK)
    return AdimSonucu(ctx.run_id, False, len(satirlar), bolum_basi, klasor)


def _ozet(sonuc: AdimSonucu, dry_run: bool) -> str:
    if sonuc.atlandi:
        return f"atlandi (parmak izi onceki calistirmayla ayni, run {sonuc.onceki_run_id})"
    if dry_run:
        return (
            f"{sonuc.sayfa_sayisi} satir, {sonuc.bolum_basi} bolum basi"
            " (dry-run, hicbir sey yazilmadi)"
        )
    return f"{sonuc.sayfa_sayisi} satir, {sonuc.bolum_basi} bolum basi, run {sonuc.run_id}"


def komut_anchor(
    *, source: str, dry_run: bool, force: bool, config: Path | None, kok: Path | None
) -> int:
    """`anchor --source risale-baski-rnk` komutu; cikis kodunu dondurur."""

    def govde(ctx: RunContext) -> int:
        if source != KAYNAK:
            raise GirdiHatasi(f"bu adim yalniz {KAYNAK} icindir")
        sonuc = run_sayfa(ctx)
        sys.stdout.write(f"anchor {source}: {_ozet(sonuc, ctx.dry_run)}\n")
        return cikis.BASARILI

    return komutu_yurut(
        komut=f"anchor --source {source}",
        adim=ANCHOR_ADIMI,
        kaynaklar=[source],
        config=config,
        kok=kok,
        govde=govde,
        force=force,
        dry_run=dry_run,
        parametreler={"source": source},
    )


__all__ = [
    "BOLUM_BASI_EKI",
    "KAYNAK",
    "SATIR_ALANLARI",
    "SAYFA_ESLEME_ADI",
    "SAYFA_RAPOR_ADI",
    "AdimSonucu",
    "BirimKonumu",
    "Konum",
    "SayfaZinciri",
    "cilt_tablosu",
    "data_versiyonu",
    "dosya_satirlari",
    "girdileri_oku",
    "komut_anchor",
    "run_sayfa",
    "sayfa_esleme_uret",
    "zincir_coz",
]
