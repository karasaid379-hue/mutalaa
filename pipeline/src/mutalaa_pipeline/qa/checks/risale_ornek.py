"""Sentetik Risale fiksturu QA kapilari (A20.5a): G-KAY, G-BUT, G-CAP, G-NOR.

Kapi islevleri bellekteki `OrnekGirdisi` uzerinde calisir; zinciri `qa/run_risale_ornek.py`
yukler. Gercek RNK kapilarinin (`qa/checks/risale_rnk.py`) kontrollerini fiksturun anchor
ciktisina uygular; RNK kapilari ham dosya, kilit ve `risale-kitaplar.json` tablosuna bagli oldugu
icin fiksturde ayri kapi islevleri vardir. Bulgular ASCII ve kisadir: yalniz capa, sayi ve alan
adi tasir, metin asla.

* G-KAY: kaynak kaydi gecerli, `slug` `test-risale-ornek` (`test-` onekli), `tur = risale`,
  `atif_metni` sabit sentetik atif satiri, `surum` var, `notice_text` yok.
* G-BUT: birimler uretecin cikisiyla bayt bayt ayni (metin, `marks`, `bolum_yolu`, rol); bos birim
  yok; kontrol karakteri yok; kendi metnimiz oldugu icin kanonik (NFC dahil); `dizin` kitap ya da
  bolum adi degil; `ar` ve `hasiye` isaretleri var ve hasiye isareti var olan dipnota gider;
  `sayfalar.jsonl` ofsetleri birim metnine sigar, bir sayfa birimin ICINDE (cumle ortasi)
  baslar.
* G-CAP: capa kanonik, `rn:test-ornek:` ailesinden, `rn_yolu` dogrulayicisindan gecer, tekil;
  `ord` okuma sirasi 1..N; `parent_path`, `role`, `kind`, `source_id`, `metin_durumu`,
  `data_version`; `content_hash`; `marks` ve `sentences` araliklari yari acik, cumleler
  ayiriciyla yeniden uretilir ve `ar` isaretinde bolunmez; onceki (kapilari gecmis) anchor
  calismasinin her capasi durur ve `content_hash` degismez. `page_map` ve `xref` araliklari
  (K-46 fikstur kurallari): `page_map` `source_id` ve cilt, capalar var, ofsetler sigar;
  `xref` `aday`, `origin = 'hat'`, `evidence.fikstur = true`, dogal anahtar tekil, `src_span`
  kaynak metne sigar, hedef ucu bir ayet capasidir (`q:`) ve `dst_span` `to_unit_span` ile ayni.
* G-NOR: normalizasyon vektorleri Python'da gecer; `tr_narrow`, `tr_wide`, `tr_stem` ve `ar_norm`
  metinden `search_keys` ile yeniden uretilince ayni; Arapca bloklu birimde `ar_norm` dolu;
  `provenance.arama` surumu.
"""

import unicodedata
from collections import defaultdict
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path
from typing import Final

from mutalaa_pipeline.adimlar.risale import (
    ANCHOR_ALANLARI,
    KIND,
    METIN_DURUMU,
    ROLLER,
    cumle_araliklari,
    hasiye_bolumu_mu,
    ord_anahtari_degerleri,
    parent_yolu,
    rn_yolu,
)
from mutalaa_pipeline.adimlar.risale_sayfa import SATIR_ALANLARI
from mutalaa_pipeline.anchor import (
    SortKey,
    content_hash,
    kanonik_metin,
    parse,
    sort_key,
    to_unit_span,
)
from mutalaa_pipeline.anchor import format as anchor_format
from mutalaa_pipeline.anchor.cumle import CUMLE_SURUMU
from mutalaa_pipeline.enums import SourceKind
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.ingest import risale_ornek
from mutalaa_pipeline.ingest.risale_ornek import (
    ANCHOR_ONEKI,
    CILT,
    DIL,
    DOSYA,
    KAYNAK,
    KITAP,
    OrnekBirimi,
)
from mutalaa_pipeline.lineage import OZET_DESENI
from mutalaa_pipeline.normalize import NORMALIZER_VERSION, search_keys
from mutalaa_pipeline.qa.checks.fikstur import ATIF_METNI, _bulgu, _capalar, _kontrol_karakteri
from mutalaa_pipeline.qa.checks.risale_rnk import (
    _ar_icinde_boler,
    _araliklar_gecerli,
    _isaretler_gecerli,
)
from mutalaa_pipeline.qa.checks.tanzil import KapiSonucu, Onceki
from mutalaa_pipeline.qa.vektorler import vektorleri_calistir
from mutalaa_pipeline.sources.kayit import Kaynak
from mutalaa_pipeline.staged import Satir

TR_ALANLARI: Final = ("tr_narrow", "tr_wide", "tr_stem")
SAYFA_VERSIYONU_ONEKI: Final = f"{KAYNAK}@"
XREF_ALANLARI: Final = frozenset(
    {
        "type",
        "src_anchor",
        "src_span",
        "dst_anchor",
        "dst_span",
        "score",
        "confidence",
        "evidence",
        "origin",
        "status",
        "data_version",
    }
)


@dataclass
class OrnekGirdisi:
    kayit: Kaynak
    anchor_satirlari: Sequence[Satir]  # anchor units.jsonl (capa sirasinda)
    sayfalar: Sequence[Satir]  # ingest sayfalar.jsonl
    page_map: Sequence[Satir]  # anchor page_map.jsonl
    xref: Sequence[Satir]  # anchor xref.jsonl
    beklenen: Sequence[OrnekBirimi]  # uretecin ayni surumdeki cikisi
    depo_kok: Path
    onceki: Onceki | None = None


def _tam(deger: object) -> int | None:
    return deger if isinstance(deger, int) and not isinstance(deger, bool) else None


def _aralik(deger: object, uzunluk: int) -> tuple[int, int] | None:
    """`[bas, son]` listesi: `0 <= bas < son <= uzunluk` (yari acik); degilse None."""
    if not isinstance(deger, list) or len(deger) != 2:
        return None
    bas, son = _tam(deger[0]), _tam(deger[1])
    if bas is None or son is None or not 0 <= bas < son <= uzunluk:
        return None
    return bas, son


# --- G-KAY -------------------------------------------------------------------------------


def g_kay(g: OrnekGirdisi) -> KapiSonucu:
    bulgular: list[str] = []
    k = g.kayit
    if k.slug != KAYNAK or not k.slug.startswith("test-"):
        bulgular.append("kaynak kaydi: slug test-risale-ornek degil ya da test- onekli degil")
    if k.tur is not SourceKind.RISALE:
        bulgular.append("kaynak kaydi: tur risale olmali")
    if k.atif_metni != ATIF_METNI:
        bulgular.append("kaynak kaydi: atif_metni sabit sentetik atif satiri degil")
    if k.surum is None:
        bulgular.append("kaynak kaydi: surum yok")
    if k.notice_text is not None:
        bulgular.append("kaynak kaydi: sentetik fiksturde notice_text olmaz")
    return KapiSonucu("G-KAY", tuple(bulgular), {"kayit": 1})


# --- G-BUT -------------------------------------------------------------------------------


def _but_birimleri(g: OrnekGirdisi, bulgular: list[str]) -> dict[str, int]:
    beklenen = {b.anchor: b for b in g.beklenen}
    var = {s.metin("anchor"): s for s in g.anchor_satirlari}
    if len(g.anchor_satirlari) != len(beklenen):
        bulgular.append(f"birim sayisi {len(g.anchor_satirlari)}, uretec {len(beklenen)} bekliyor")
    _bulgu(bulgular, "eksik birim", sorted(set(beklenen) - set(var)), "uretecin capasi yok")
    _bulgu(bulgular, "fazla birim", sorted(set(var) - set(beklenen)), "uretecte olmayan capa")
    liste: dict[str, list[str]] = defaultdict(list)
    ar_isareti = hasiye_isareti = 0
    for capa, satir in var.items():
        metin = satir.metin("text")
        if metin == "" or all(h in " \t\n" for h in metin):
            liste["bos metin"].append(capa)
        if _kontrol_karakteri(metin):
            liste["kontrol karakteri"].append(capa)
        if kanonik_metin(metin) != metin or not unicodedata.is_normalized("NFC", metin):
            liste["kanonik olmayan metin"].append(capa)
        if "dizin" in capa.split(":"):
            liste["dizin adi"].append(capa)
        marks = satir.veri.get("marks")
        if isinstance(marks, list):
            for m in marks:
                if not isinstance(m, dict):
                    continue
                if m.get("t") == "ar":
                    ar_isareti += 1
                if m.get("t") == "hasiye":
                    hasiye_isareti += 1
                    hedef = var.get(str(m.get("a")))
                    if hedef is None or hedef.metin("role") != ROLLER["hasiye"]:
                        liste["hasiye isareti"].append(capa)
        b = beklenen.get(capa)
        if b is None:
            continue
        if b.text.encode("utf-8") != metin.encode("utf-8"):
            liste["metin"].append(capa)
        if marks != [dict(m) for m in b.marks]:
            liste["marks"].append(capa)
        attrs = satir.nesne("attrs")
        if (
            attrs.get("dil") != DIL
            or attrs.get("p") != b.p
            or attrs.get("sayfa") != b.sayfa
            or attrs.get("baslik_yolu") != list(b.baslik_yolu)
            or satir.metin("role") != ROLLER[b.tur]
        ):
            liste["attrs ya da role"].append(capa)
    for ad, neden in (
        ("metin", "uretecin cikisiyla bayt bayt ayni degil"),
        ("marks", "uretecin isaretleriyle ayni degil"),
        ("attrs ya da role", "dil, p, sayfa, baslik_yolu ya da role uretecle ayni degil"),
        ("bos metin", "metin bos"),
        ("kontrol karakteri", "metinde kontrol ya da bicim karakteri var"),
        ("kanonik olmayan metin", "kanonik_metin (NFC dahil) metni degistiriyor"),
        ("dizin adi", "capada dizin adi var (risale-dizin paketine ayrilmis)"),
        ("hasiye isareti", "hasiye isareti dipnot birimine gitmiyor"),
    ):
        _bulgu(bulgular, ad, liste.get(ad, []), neden)
    if ar_isareti < 1:
        bulgular.append("ar isareti yok (Arapca alfabe bloku bekleniyor)")
    if hasiye_isareti < 1:
        bulgular.append("hasiye isareti yok")
    return {"birim": len(var), "beklenen_birim": len(beklenen), "ar_isareti": ar_isareti}


def _but_sayfalar(g: OrnekGirdisi, bulgular: list[str]) -> dict[str, int]:
    uzunluk = {s.metin("anchor"): len(s.metin("text")) for s in g.anchor_satirlari}
    hatali: list[str] = []
    ortasi = icerik_yok = 0
    numaralar: list[int] = []
    for s in g.sayfalar:
        n = s.sayi("n")
        numaralar.append(n)
        capa, ofs, tur = s.veri.get("capa"), s.sayi("ofs"), s.metin("tur")
        if s.metin("dosya") != DOSYA:
            hatali.append(f"sayfa {n}")
        elif tur == "icerik-yok":
            icerik_yok += 1
            if capa is not None or ofs != 0:
                hatali.append(f"sayfa {n}")
        elif (
            not isinstance(capa, str)
            or not 0 <= ofs < uzunluk.get(capa, 0)
            or (tur == "bas") != (ofs == 0)
        ):
            hatali.append(f"sayfa {n}")
        elif tur == "ortasi":
            ortasi += 1
    _bulgu(bulgular, "sayfa", hatali, "ofset birim metnine sigmiyor ya da tur tutarsiz")
    if numaralar != list(range(1, len(numaralar) + 1)):
        bulgular.append("sayfa numaralari 1..N ardisik degil")
    if ortasi < 1:
        bulgular.append("birim ortasinda baslayan sayfa yok (cumle ortasi sinamasi)")
    return {"sayfa": len(numaralar), "sayfa_ortasi": ortasi, "sayfa_icerik_yok": icerik_yok}


def g_but(g: OrnekGirdisi) -> KapiSonucu:
    bulgular: list[str] = []
    sayilar = _but_birimleri(g, bulgular)
    sayilar.update(_but_sayfalar(g, bulgular))
    return KapiSonucu("G-BUT", tuple(bulgular), sayilar)


# --- G-CAP -------------------------------------------------------------------------------


def _capa_birimleri(g: OrnekGirdisi, bulgular: list[str]) -> tuple[dict[str, str], int]:
    """Birim kurallari; `{capa: content_hash}` ve satir sayisi."""
    listeler: dict[str, list[str]] = defaultdict(list)
    gorulen: set[str] = set()
    anahtarlar: list[tuple[SortKey, str]] = []
    siralar: list[tuple[object, int]] = []
    simdiki: dict[str, str] = {}
    data_version = f"{KAYNAK}@{g.kayit.surum}"
    for satir in g.anchor_satirlari:
        capa = satir.metin("anchor")
        if capa in gorulen:
            listeler["yinelenen capa"].append(capa)
        gorulen.add(capa)
        if set(satir.veri) != ANCHOR_ALANLARI:
            listeler["alan kumesi"].append(capa)
            continue
        try:
            yol = rn_yolu(capa)
            kanonik = anchor_format(parse(capa)) == capa
        except GirdiHatasi:
            listeler["gecersiz capa"].append(capa)
            continue
        if not kanonik or not capa.startswith(ANCHOR_ONEKI) or yol[0] != KITAP:
            listeler["capa ailesi"].append(capa)
        hasiye = hasiye_bolumu_mu(yol)
        rol = satir.veri.get("role")
        if rol not in ROLLER.values() or (rol == ROLLER["hasiye"]) != hasiye:
            listeler["role"].append(capa)
        if (
            satir.veri.get("kind") != KIND
            or satir.veri.get("metin_durumu") != METIN_DURUMU
            or satir.veri.get("source_id") != KAYNAK
            or satir.veri.get("data_version") != data_version
            or satir.veri.get("ayah_lo") is not None
            or satir.veri.get("ayah_hi") is not None
        ):
            listeler["sabit alan"].append(capa)
        if satir.veri.get("parent_path") != parent_yolu(yol):
            listeler["parent_path"].append(capa)
        ozet, metin = satir.metin("content_hash"), satir.metin("text")
        if OZET_DESENI.fullmatch(ozet) is None:
            listeler["content_hash biciminde"].append(capa)
        elif ozet != content_hash(metin):
            listeler["content_hash"].append(capa)
        marks = satir.veri.get("marks")
        sentences = satir.veri.get("sentences")
        marks_liste = marks if isinstance(marks, list) else []
        if not isinstance(marks, list) or not _isaretler_gecerli(marks_liste, len(metin)):
            listeler["marks araligi"].append(capa)
        elif not _araliklar_gecerli(sentences, len(metin)) or not isinstance(sentences, list):
            listeler["sentences araligi"].append(capa)
        elif rol == ROLLER["baslik"]:
            if sentences:
                listeler["baslik biriminde cumle"].append(capa)
        else:
            try:
                yeniden = cumle_araliklari(
                    capa, metin, [m for m in marks_liste if isinstance(m, dict)]
                )
            except GirdiHatasi:
                yeniden = []
            if yeniden != sentences:
                listeler["sentences ayiriciyla yeniden uretilemedi"].append(capa)
            if _ar_icinde_boler(sentences, marks_liste):
                listeler["ar isaretinde cumle siniri"].append(capa)
        saglayici = satir.nesne("provenance")
        cumle = saglayici.get("cumle")
        if not isinstance(cumle, dict) or cumle.get("surum") != CUMLE_SURUMU:
            listeler["provenance.cumle.surum"].append(capa)
        try:
            siralar.append((ord_anahtari_degerleri(capa, saglayici), _tam(satir.veri["ord"]) or 0))
        except GirdiHatasi:
            listeler["provenance.konum"].append(capa)
        anahtarlar.append((sort_key(parse(capa)), capa))
        simdiki[capa] = ozet
    siralama = [c for (a, _), (b, c) in pairwise(anahtarlar) if not a < b]
    siralar.sort(key=lambda cift: cift[0])  # type: ignore[arg-type, return-value]
    if [o for _, o in siralar] != list(range(1, len(siralar) + 1)):
        listeler["ord"].append(KITAP)
    for ad, neden in (
        ("alan kumesi", "anchor cikisinin alan kumesi degil"),
        ("yinelenen capa", "capa birden fazla satirda"),
        ("gecersiz capa", "gramere ya da rn: dogrulayicisina uymuyor"),
        ("capa ailesi", f"kanonik degil ya da {ANCHOR_ONEKI} ailesinden degil"),
        ("role", "role baslik/dipnot/govde kuralina uymuyor"),
        ("sabit alan", "kind, metin_durumu, source_id, data_version ya da ayah_lo/hi"),
        ("parent_path", "capanin bolum yoluyla ayni degil"),
        ("content_hash biciminde", "64 haneli kucuk harfli onaltilik degil"),
        ("content_hash", "metnin SHA-256'siyla tutmuyor"),
        ("marks araligi", "yari acik aralik metne sigmiyor"),
        ("sentences araligi", "yari acik, artan, ayrik aralik metne sigmiyor"),
        ("baslik biriminde cumle", "baslik birimi cumle tasimaz"),
        ("sentences ayiriciyla yeniden uretilemedi", "cumle ayirici surumuyle farkli"),
        ("ar isaretinde cumle siniri", "ar isaretli aralik icinde bolunmus"),
        ("provenance.cumle.surum", "cumle ayirici surumu yok ya da farkli"),
        ("provenance.konum", "okuma sirasi icin satir konumu yok"),
        ("ord", "ord 1..N okuma sirasi degil"),
    ):
        _bulgu(bulgular, ad, listeler.get(ad, []), neden)
    _bulgu(bulgular, "okuma sirasi", siralama, "satir onceki capadan sonra gelmiyor")
    return simdiki, len(g.anchor_satirlari)


def _capa_sayfa_esleme(g: OrnekGirdisi, bulgular: list[str]) -> int:
    """`page_map` satirlari: kaynak, cilt, capalar ve ofsetler (yari acik, kod noktasi)."""
    uzunluk = {s.metin("anchor"): len(s.metin("text")) for s in g.anchor_satirlari}
    sira = {s.metin("anchor"): s.sayi("ord") for s in g.anchor_satirlari if s.var("ord")}
    liste: dict[str, list[str]] = defaultdict(list)
    gorulen: set[tuple[int, int]] = set()
    for s in g.page_map:
        yer = f"sayfa {s.veri.get('volume')}/{s.veri.get('page')}"
        if set(s.veri) != SATIR_ALANLARI:
            liste["alan kumesi"].append(yer)
            continue
        anahtar = (s.sayi("volume"), s.sayi("page"))
        if anahtar in gorulen:
            liste["yinelenen sayfa"].append(yer)
        gorulen.add(anahtar)
        if s.metin("source_id") != KAYNAK or s.sayi("volume") != CILT:
            liste["kaynak ya da cilt"].append(yer)
        surum = s.metin("data_version")
        if not surum.startswith(SAYFA_VERSIYONU_ONEKI):
            liste["data_version"].append(yer)
        bas, bit = s.metin("start_anchor"), s.metin("end_anchor")
        bo, eo = s.sayi("start_offset"), s.sayi("end_offset")
        if bas not in uzunluk or bit not in uzunluk:
            liste["capa"].append(yer)
        elif not (
            0 <= bo < uzunluk[bas]
            and 0 <= eo <= uzunluk[bit]
            and (sira[bas], bo) <= (sira[bit], eo)
        ):
            liste["ofset"].append(yer)
    for ad, neden in (
        ("alan kumesi", "page_map alan kumesi degil"),
        ("yinelenen sayfa", "(volume, page) tekil degil"),
        ("kaynak ya da cilt", f"source_id {KAYNAK} ve volume {CILT} olmali"),
        ("data_version", f"{SAYFA_VERSIYONU_ONEKI}{{surum}} ile baslamiyor"),
        ("capa", "baslangic ya da bitis capasi birimlerde yok"),
        ("ofset", "ofset birim metnine sigmiyor ya da bitis baslangictan once"),
    ):
        _bulgu(bulgular, ad, liste.get(ad, []), neden)
    if not g.page_map:
        bulgular.append("page_map bos")
    return len(g.page_map)


def _capa_xref(g: OrnekGirdisi, bulgular: list[str]) -> int:
    """K-46 fikstur kurallari: aday, origin hat, evidence.fikstur, dogal anahtar, araliklar."""
    metinler = {s.metin("anchor"): s.metin("text") for s in g.anchor_satirlari}
    liste: dict[str, list[str]] = defaultdict(list)
    anahtarlar: set[tuple[object, ...]] = set()
    for s in g.xref:
        yer = f"{s.veri.get('type')} {s.veri.get('src_anchor')}"
        if set(s.veri) != XREF_ALANLARI:
            liste["alan kumesi"].append(yer)
            continue
        if s.metin("type") not in risale_ornek.XREF_TURLERI:
            liste["tur"].append(yer)
        if s.metin("status") != "aday" or s.metin("origin") != "hat":
            liste["status ya da origin"].append(yer)
        kanit = s.nesne("evidence")
        if kanit.get("fikstur") is not True or kanit.get("source_id") != KAYNAK:
            liste["evidence.fikstur"].append(yer)
        if s.metin("data_version") != f"{KAYNAK}@{g.kayit.surum}":
            liste["data_version"].append(yer)
        for alan in ("score", "confidence"):
            deger = _tam(s.veri[alan])
            if deger is None or not 0 <= deger <= 1:
                liste["score ya da confidence"].append(yer)
        kaynak = s.metin("src_anchor")
        metin = metinler.get(kaynak)
        aralik = _aralik(s.veri["src_span"], len(metin) if metin is not None else 0)
        if metin is None or not kaynak.startswith(ANCHOR_ONEKI) or aralik is None:
            liste["kaynak ucu"].append(yer)
        else:
            try:
                cozulen = to_unit_span(parse(f"{kaynak}@{aralik[0]}-{aralik[1]}"))
            except (ValueError, GirdiHatasi):
                liste["kaynak ucu"].append(yer)
            else:
                if cozulen.unit != kaynak or cozulen.span != aralik:
                    liste["kaynak ucu"].append(yer)
        hedef = s.metin("dst_anchor")
        try:
            hedef_ref = parse(hedef)
            hedef_birim = to_unit_span(hedef_ref).unit
        except (ValueError, GirdiHatasi):
            liste["hedef ucu"].append(yer)
        else:
            if not hedef.startswith("q:") or hedef_birim != hedef or hedef_ref.span is not None:
                liste["hedef ucu"].append(yer)
        try:
            anahtar = risale_ornek.dogal_anahtar(s.veri)
        except GirdiHatasi:
            liste["dogal anahtar"].append(yer)
        else:
            if anahtar in anahtarlar:
                liste["dogal anahtar"].append(yer)
            anahtarlar.add(anahtar)
    for ad, neden in (
        ("alan kumesi", "xref alan kumesi degil"),
        ("tur", "fikstur xref turu atif ya da iktibas degil"),
        ("status ya da origin", "status aday ve origin hat olmali"),
        ("evidence.fikstur", "evidence.fikstur true ve evidence.source_id kaynak olmali"),
        ("data_version", f"{KAYNAK}@{{surum}} degil"),
        ("score ya da confidence", "0..1 tam sayi degil (staged JSON ondalik tasimaz)"),
        ("kaynak ucu", "src_anchor birimi/araligi kod noktasi olarak metne sigmiyor"),
        ("hedef ucu", "dst_anchor birim duzeyinde bir q: ayet capasi degil"),
        ("dogal anahtar", "xref_natural_key (type, src, src_span, dst, dst_span) tekil degil"),
    ):
        _bulgu(bulgular, ad, liste.get(ad, []), neden)
    if not g.xref:
        bulgular.append("xref bos")
    return len(g.xref)


def g_cap(g: OrnekGirdisi) -> KapiSonucu:
    bulgular: list[str] = []
    simdiki, adet = _capa_birimleri(g, bulgular)
    sayilar = {
        "capa": adet,
        "sayfa_satiri": _capa_sayfa_esleme(g, bulgular),
        "xref": _capa_xref(g, bulgular),
        "onceki_run": 0,
    }
    if g.onceki is not None:
        sayilar["onceki_run"] = 1
        sayilar["onceki_capa"] = len(g.onceki.ozetler)
        kayip = sorted(c for c in g.onceki.ozetler if c not in simdiki)
        degisen = sorted(
            c for c, ozet in g.onceki.ozetler.items() if c in simdiki and simdiki[c] != ozet
        )
        _bulgu(bulgular, "onceki surumde olup kaybolan capa", kayip, "capa kullanim disi olamaz")
        _bulgu(bulgular, "onceki surumle content_hash farkli", degisen, "metin degismis")
    return KapiSonucu("G-CAP", tuple(bulgular), sayilar)


# --- G-NOR -------------------------------------------------------------------------------


def g_nor(g: OrnekGirdisi) -> KapiSonucu:
    bulgular: list[str] = []
    vektor = vektorleri_calistir(g.depo_kok)
    if vektor.kalan:
        bulgular.append(
            f"normalizasyon vektoru: {len(vektor.kalan)}/{vektor.toplam} kaldi:"
            f" {_capalar(vektor.kalan)}"
        )
    if vektor.hizasiz:
        bulgular.append(
            f"tr_wide/tr_stem sozcuk hizasi: {len(vektor.hizasiz)} vektor:"
            f" {_capalar(vektor.hizasiz)}"
        )
    farkli: list[str] = []
    ar_hatasi: list[str] = []
    surum: list[str] = []
    ar_dolu = 0
    for satir in g.anchor_satirlari:
        capa = satir.metin("anchor")
        k = search_keys(satir.metin("text"))
        beklenen = {"tr_narrow": k.tr_narrow, "tr_wide": k.tr_wide, "tr_stem": k.tr_stem}
        if any(satir.veri.get(alan) != beklenen[alan] for alan in TR_ALANLARI):
            farkli.append(capa)
        if satir.veri.get("ar_norm") != (k.ar_norm or None):
            ar_hatasi.append(capa)
        if satir.veri.get("ar_norm") is not None:
            ar_dolu += 1
        arama = satir.nesne("provenance").get("arama")
        if not isinstance(arama, dict) or arama.get("normalizer_version") != NORMALIZER_VERSION:
            surum.append(capa)
    for ad, liste, neden in (
        ("arama anahtari", farkli, "metinden search_keys ile uretilen degerle ayni degil"),
        ("ar_norm", ar_hatasi, "metinden search_keys ile uretilen ar_norm ile ayni degil"),
        ("provenance.arama", surum, "normalizer_version yok ya da bu surumle ayni degil"),
    ):
        _bulgu(bulgular, ad, liste, neden)
    if ar_dolu < 1:
        bulgular.append("Arapca bloklu birimde ar_norm dolu degil")
    sayilar = {
        "vektor": vektor.toplam,
        "vektor_kalan": len(vektor.kalan),
        "vektor_hizasiz": len(vektor.hizasiz),
        "anahtar_farki": len(farkli),
        "ar_norm_dolu": ar_dolu,
    }
    return KapiSonucu("G-NOR", tuple(bulgular), sayilar)


KAPI_ISLEVLERI: Final[dict[str, Callable[[OrnekGirdisi], KapiSonucu]]] = {
    "G-KAY": g_kay,
    "G-BUT": g_but,
    "G-CAP": g_cap,
    "G-NOR": g_nor,
}

__all__ = ["KAPI_ISLEVLERI", "OrnekGirdisi"]
