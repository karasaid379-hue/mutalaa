"""`mutalaa qa gold`: degerlendirme setleri ve kapi olcumu (A18.5; K-51 madde 5, 10-12).

`--type kok|lemma|benzer-ayet|atif|iktibas|hepsi` (hepsi sirayla). `--build` seti (yeniden) uretir
ve `data/gold/<set>/<surum>/` altina yazar; yoksa var olan son set olculur. `--dry-run` hicbir sey
yazmaz (set, rapor, `xref_gate`): olcumu yapar ve ozeti yazdirir.

Her tur icin: set (manifest dogrulamali) -> dongusellik denetimi -> olcum -> kapi karari -> gerileme
kurali -> rapor `data/reports/{data_version}-gold-{tur}.json` -> `icerik.xref_gate` upsert.

Cikis kodlari: 0 olcum tamamlandi (kapi `kaldi` olsa bile; bilgi rapor ve `xref_gate`'te), 1 yalniz
gerileme kurali kirildiysa (onceki kabul edilmis `gecti` raporuna gore bir olcu 0,02'den fazla
dustu), 2 girdi, yapilandirma ya da dongusellik hatasi. Hata iletilerinde yalniz kaynak adi, sayi
ve capa bulunur; icerik metni yazilmaz.
"""

import os
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

import psycopg

from mutalaa_pipeline import cikis
from mutalaa_pipeline.adimlar.enrich_tr_roots import _nltk_klasoru
from mutalaa_pipeline.db import baglan
from mutalaa_pipeline.enrich.baglantilar import girdi as db_girdi
from mutalaa_pipeline.enrich.baglantilar.benzer import adaylari_bul, sinirla
from mutalaa_pipeline.enrich.baglantilar.girdi import ayet_kelimeleri
from mutalaa_pipeline.enrich.baglantilar.uret import simple_kelimeleri
from mutalaa_pipeline.enrich.quran_index import KuranIndeksi
from mutalaa_pipeline.enrich.tr_roots.lemmatize import Lemmatizer, ZeyrekLemmatizer, zeyrek_surumu
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.ingest import quranwbw
from mutalaa_pipeline.ingest.meal_ortak import gelen_dizini, gelen_tarihi_coz
from mutalaa_pipeline.komut_ortak import komutu_yurut
from mutalaa_pipeline.qa.gold import araclar, benzer, kok, lemma, sentetik, setler
from mutalaa_pipeline.qa.gold import motor as motor_modulu
from mutalaa_pipeline.qa.gold.kapi import (
    CLI_TURLERI,
    TurSonucu,
    onceki_kabul_edilmis,
    onceki_olculer,
    rapor_govdesi,
    rapor_yaz,
    xref_gate_yaz,
)
from mutalaa_pipeline.qa.gold.olcum import gerilemeleri_bul
from mutalaa_pipeline.runctx import QaKaldi, RunContext
from mutalaa_pipeline.zincir import (
    ANCHOR_ADIMI,
    INGEST_ADIMI,
    kelimeler_oku,
    saglam_olmali,
    son_calisma,
    units_oku,
)

QA_ADIMI: Final = "qa"
KOMUT: Final = "qa gold"
BAGLANTI = Callable[[], psycopg.Connection]
KARAR_TUTTU: Final = (
    "ijaza hedefleri tuttu: pipeline/enrich icinde sarilir; normalizasyon, baglam ve kalip"
    " katmanlari bizde kalir"
)
KARAR_TUTMADI: Final = (
    "ijaza hedefleri tutmadi: Iktibas tespiti §5-6 eslestirici yazilir (enrich/citations)"
)


def turleri_coz(tur: str) -> tuple[str, ...]:
    """`--type` degeri; `hepsi` sirayla bes tur. Gecersiz deger `GirdiHatasi`."""
    if tur == "hepsi":
        return CLI_TURLERI
    if tur not in CLI_TURLERI:
        raise GirdiHatasi(f"--type {', '.join(CLI_TURLERI)} ya da hepsi olmali")
    return (tur,)


def _surum(kayitlar: Mapping[str, object], slug: str) -> str:
    surum = getattr(kayitlar[slug], "surum", None)
    if not isinstance(surum, str) or not surum:
        raise GirdiHatasi(f"{slug}: kaynak kaydinda surum yok")
    return surum


# --- set uretimi -------------------------------------------------------------------------


def kok_seti_uret(
    ctx: RunContext, conn: psycopg.Connection, lemmatizer: Lemmatizer | None = None
) -> kok.KokSeti:
    kayitlar = ctx.require_sources((kok.KAYNAK_QWBW, kok.KAYNAK_QAC))
    gelen = gelen_dizini(ctx.veri_kok, kok.KAYNAK_QWBW)
    tarih = gelen_tarihi_coz(gelen, None, kok.KAYNAK_QWBW)
    veri = quranwbw.gelen_oku(gelen, tarih)
    kilit = quranwbw.kilit_yukle()
    quranwbw.kilit_denetle(kilit, veri)
    satirlar = quranwbw.cikar(veri, kilit.sha256, kilit.surum)
    anlamlar = [(str(s["anchor"]), str(s["text"])) for s in satirlar]
    kelime_koku = {
        str(a): (None if r is None else int(r))
        for a, r in conn.execute("SELECT anchor, root_id FROM icerik.quran_word").fetchall()
    }
    kok_harfleri = {
        int(i): str(h) for i, h in conn.execute("SELECT id, letters_bw FROM icerik.root").fetchall()
    }
    lm = lemmatizer if lemmatizer is not None else ZeyrekLemmatizer(_nltk_klasoru(ctx))
    kurulum = kok.referans_say(anlamlar, kelime_koku, lm)
    referans = kok.referans_kokleri(kurulum)
    ozet = {
        "kelime": kurulum.kelime,
        "koklu_kelime": kurulum.koklu_kelime,
        "parca": kurulum.parca,
        "belirsiz_parca": kurulum.belirsiz_parca,
        "bilinmeyen_parca": kurulum.bilinmeyen_parca,
        "lemma": len(kurulum.toplam),
        "referansli_lemma": sum(1 for v in referans.values() if v),
        # zeyrek ciktisi PYTHONHASHSEED'e duyarlidir (rastgele tohumda kosular arasi ~%0,03 oynar);
        # ayni set icin PYTHONHASHSEED=0 ile uretin. Olcum kalici set uzerinden yapilir.
        "python_hash_seed": os.environ.get("PYTHONHASHSEED", "rastgele"),
    }
    return kok.kok_seti_kur(
        referans=referans,
        toplam=kurulum.toplam,
        kok_harfleri=kok_harfleri,
        qwbw_surum=_surum(kayitlar, kok.KAYNAK_QWBW),
        qac_surum=_surum(kayitlar, kok.KAYNAK_QAC),
        zeyrek_surum=zeyrek_surumu() or "bilinmiyor",
        ozet_sayilar=ozet,
    )


def lemma_seti_uret(ctx: RunContext) -> tuple[dict[str, object], list[dict[str, object]]]:
    """`(manifest taslagi, ornekler)`."""
    kayitlar = ctx.require_sources(lemma.KAYNAK_QAC)
    qac = son_calisma(ctx, lemma.KAYNAK_QAC, ANCHOR_ADIMI, ipucu="once: enrich morphology")
    saglam_olmali(ctx, qac)
    kelimeler = [s.veri for s in kelimeler_oku(qac, "qac words.jsonl")]
    surum = _surum(kayitlar, lemma.KAYNAK_QAC)
    ornekler = lemma.ornekleri_kur(lemma.qac_ayet_kumeleri(kelimeler), surum)
    return lemma.taslak(surum), ornekler


def benzer_seti_uret(
    ctx: RunContext, conn: psycopg.Connection
) -> tuple[dict[str, object], list[dict[str, object]]]:
    """`(manifest taslagi, ornekler)`."""
    kayitlar = ctx.require_sources((benzer.KAYNAK_QURSIM, benzer.KAYNAK_ILM))
    sirasi = benzer.ayet_sirasi_oku(conn)
    capa = {v: k for k, v in sirasi.items()}
    q_yol, _ = benzer.gelen_dosyasi(ctx.veri_kok, benzer.KAYNAK_QURSIM, benzer.QURSIM_DOSYASI)
    i_yol, _ = benzer.gelen_dosyasi(ctx.veri_kok, benzer.KAYNAK_ILM, benzer.ILM_DOSYASI)
    qursim, q_sayac = benzer.qursim_cifti_oku(q_yol, sirasi)
    ilm, i_gecersiz = benzer.ilm_oku(i_yol, sirasi)
    q_surum = _surum(kayitlar, benzer.KAYNAK_QURSIM)
    i_surum = _surum(kayitlar, benzer.KAYNAK_ILM)
    ornekler = benzer.ornekleri_kur(qursim, ilm, capa, q_surum, i_surum)
    sayilar = {
        "qursim": q_sayac,
        "ilm_cift": len(ilm),
        "ilm_gecersiz_girdi": i_gecersiz,
        "ornek": len(ornekler),
    }
    return benzer.taslak(q_surum, i_surum, sayilar), ornekler


def sentetik_seti_uret(
    ctx: RunContext, kurulum: motor_modulu.MotorKurulum, conn: psycopg.Connection
) -> list[dict[str, object]]:
    korpus = sentetik.korpus_oku(conn, kurulum.simple_metni)
    return sentetik.uret(
        korpus, kurulum.surumler[sentetik.KAYNAK_UTHMANI], kurulum.surumler[sentetik.KAYNAK_SIMPLE]
    )


def set_kaydet(
    ctx: RunContext,
    set_adi: str,
    taslak: Mapping[str, object],
    ornekler: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    """Seti kurar; `--dry-run` degilse diske de yazar. Manifesti dondurur."""
    if ctx.dry_run:
        return setler.set_hazirla(set_adi, taslak, ornekler)[0]
    return setler.set_yaz(ctx.veri_kok, set_adi, taslak, ornekler)[0]


# --- oturum ------------------------------------------------------------------------------


@dataclass
class Oturum:
    """Bir `qa gold` kosusunun ortak durumu (onbellekler, sayaclar)."""

    ctx: RunContext
    conn: psycopg.Connection
    build: bool
    lemmatizer: Lemmatizer | None = None
    motor_onbellegi: dict[tuple[str, ...], motor_modulu.MotorKurulum] = field(default_factory=dict)
    cikti_onbellegi: dict[tuple[str, str], list[sentetik.OrnekCikti]] = field(default_factory=dict)
    sentetik_ornekler: list[dict[str, object]] | None = None
    regresyonlar: list[str] = field(default_factory=list)
    hatalar: list[str] = field(default_factory=list)
    ozetler: list[str] = field(default_factory=list)

    def motor(self, alias: Sequence[str] = ("onayli",)) -> motor_modulu.MotorKurulum:
        anahtar = tuple(alias)
        if anahtar not in self.motor_onbellegi:
            self.motor_onbellegi[anahtar] = motor_modulu.motor_kur(
                self.ctx, self.conn, alias_durumlari=anahtar
            )
        return self.motor_onbellegi[anahtar]


def _sentetik_seti_al(o: Oturum, set_adi: str) -> tuple[dict[str, object], list[dict[str, object]]]:
    """Sentetik seti kurar/yazar (`--build`) ya da okur (`atif` ve `iktibas` ayni ornekler)."""
    if o.build:
        if o.sentetik_ornekler is None:
            o.sentetik_ornekler = sentetik_seti_uret(o.ctx, o.motor(), o.conn)
        kurulum = o.motor()
        taslak = sentetik.taslak(
            kurulum.surumler[sentetik.KAYNAK_UTHMANI], kurulum.surumler[sentetik.KAYNAK_SIMPLE]
        )
        manifest = set_kaydet(o.ctx, set_adi, taslak, o.sentetik_ornekler)
        return manifest, o.sentetik_ornekler
    manifest, ornekler, _ = setler.set_oku(o.ctx.veri_kok, set_adi)
    return manifest, ornekler


def _motor_ciktilari(
    o: Oturum,
    manifest: Mapping[str, object],
    ornekler: Sequence[Mapping[str, object]],
    alias: Sequence[str],
) -> list[sentetik.OrnekCikti]:
    anahtar = (str(manifest["ornekler_sha256"]), ",".join(alias))
    if anahtar not in o.cikti_onbellegi:
        o.cikti_onbellegi[anahtar] = sentetik.motoru_calistir(o.motor(alias).motor, ornekler)
    return o.cikti_onbellegi[anahtar]


# --- turler ------------------------------------------------------------------------------


def olc_kok(o: Oturum) -> TurSonucu:
    if o.build:
        seti = kok_seti_uret(o.ctx, o.conn, o.lemmatizer)
        if not o.ctx.dry_run:
            kok.kok_seti_yaz(o.ctx.veri_kok, seti)
    else:
        seti = kok.kok_seti_oku(o.ctx.veri_kok)
    tahminler = kok.tahminleri_oku(o.conn)
    return kok.kok_olc(seti.manifest, seti.ornekler, seti.evren, tahminler)


def olc_lemma(o: Oturum) -> TurSonucu:
    if o.build:
        taslak, ornekler = lemma_seti_uret(o.ctx)
        manifest = set_kaydet(o.ctx, "lemma", taslak, ornekler)
    else:
        manifest, ornekler, _ = setler.set_oku(o.ctx.veri_kok, "lemma")
    return lemma.lemma_olc(
        manifest,
        ornekler,
        lemma.db_ayet_kumeleri(o.conn),
        lemma.lemma_xref_satirlari(o.conn),
        lemma.lemma_refleri(o.conn),
        lemma.sql_ihlalleri_al(o.conn),
    )


def olc_benzer(o: Oturum) -> TurSonucu:
    if o.build:
        taslak, ornekler = benzer_seti_uret(o.ctx, o.conn)
        manifest = set_kaydet(o.ctx, "benzer-ayet", taslak, ornekler)
    else:
        manifest, ornekler, _ = setler.set_oku(o.ctx.veri_kok, "benzer-ayet")
    sirasi = benzer.ayet_sirasi_oku(o.conn)
    literal, sayaclar, _ = benzer.satirlari_oku(o.conn, sirasi)
    secilen, kaynaklar, secim_sayaclari = sozluksel_secim(o, sirasi)
    sayaclar = {**sayaclar, **secim_sayaclari}
    return benzer.benzer_olc(
        manifest,
        ornekler,
        secilen,
        sayaclar,
        kaynaklar,
        {v: k for k, v in sirasi.items()},
        literal_filtre=literal,
    )


def sozluksel_secim(
    o: Oturum, sirasi: Mapping[str, int]
) -> tuple[list[benzer.CiftAnahtari], set[str], dict[str, int]]:
    """QurSim'den bagimsiz sozluksel secim (A18.3 `adaylari_bul` + `sinirla`), 1 tabanli ayet no.

    Uretimin girdileri (veritabani `quran_word` ve `tanzil-simple-clean` staged) ayni; sonuc
    veritabanindaki `sozluksel` satirlarla karsilastirilir (`db_qursimsiz_secimde_degil` 0 olmali).
    """
    kayitlar = o.ctx.require_sources((sentetik.KAYNAK_UTHMANI, sentetik.KAYNAK_SIMPLE))
    simple_calisma = son_calisma(
        o.ctx,
        sentetik.KAYNAK_SIMPLE,
        INGEST_ADIMI,
        ipucu="once: ingest tanzil --variant simple-clean",
    )
    saglam_olmali(o.ctx, simple_calisma)
    db = db_girdi.db_oku(o.conn, beklenen_ayet=6236)
    simple = simple_kelimeleri(
        {
            s.metin("anchor"): s.metin("text")
            for s in units_oku(simple_calisma, sentetik.KAYNAK_SIMPLE)
        },
        db.ayetler,
    )
    indeksler = {
        "uthmani": KuranIndeksi(ayet_kelimeleri(db.kelimeler, len(db.ayetler))),
        "imlai": KuranIndeksi(simple.kelimeler),
    }
    adaylar = adaylari_bul(indeksler)
    secim = sinirla(adaylar)
    secilen = sorted((lo + 1, hi + 1) for lo, hi in secim)  # ayah_index 1 tabanli
    kume = set(secilen)
    db_qursimsiz = benzer.satirlari_oku(o.conn, sirasi)[0]
    sayac = {
        "sozluksel_aday_cift": len(adaylar),
        "sozluksel_secilen_cift": len(secilen),
        "db_qursimsiz_sozluksel_satir": len(db_qursimsiz),
        "db_qursimsiz_secimde_degil": sum(1 for c in db_qursimsiz if c not in kume),
    }
    kaynak = {sentetik.KAYNAK_UTHMANI, sentetik.KAYNAK_SIMPLE} & set(kayitlar)
    return secilen, kaynak, sayac


def olc_atif(o: Oturum) -> TurSonucu:
    manifest, ornekler = _sentetik_seti_al(o, "atif")
    kurulum = o.motor()
    ciktilar = {c.ornek_id: c for c in _motor_ciktilari(o, manifest, ornekler, ("onayli",))}
    s = sentetik.atif_olc(
        manifest, ornekler, ciktilar, kurulum.motor, ad_sozlugu_etkin=kurulum.ad_sozlugu_etkin
    )
    # tani: ad sozlugu bellekte acik (onayli + aday takma adlar); kapiya girmez
    tani = o.motor(("onayli", "aday"))
    tani_ciktilar = {
        c.ornek_id: c for c in _motor_ciktilari(o, manifest, ornekler, ("onayli", "aday"))
    }
    t = sentetik.atif_olc(
        manifest, ornekler, tani_ciktilar, tani.motor, ad_sozlugu_etkin=tani.ad_sozlugu_etkin
    )
    s.ayrintilar["tani_ad_sozlugu_acik_bilgi"] = {
        "olculer": {k: round(v, 6) for k, v in t.olculer.items()},
        "bicim_sinifi_kirilimi_dondurulmus": t.ayrintilar["bicim_sinifi_kirilimi_dondurulmus"],
        "bicim_duyarlilik_dondurulmus": t.ayrintilar["bicim_duyarlilik_dondurulmus"],
        "not": "Onayli ve aday takma adlar bellekte etkin; kapi sonucuna ve xref_gate'e girmez.",
    }
    return s


def olc_iktibas(o: Oturum) -> TurSonucu:
    manifest, ornekler = _sentetik_seti_al(o, "iktibas")
    kurulum = o.motor()
    ciktilar = {c.ornek_id: c for c in _motor_ciktilari(o, manifest, ornekler, ("onayli",))}
    s = sentetik.iktibas_olc(
        manifest, ornekler, ciktilar, kurulum.motor, ad_sozlugu_etkin=kurulum.ad_sozlugu_etkin
    )
    s.ayrintilar["hazir_araclar_karsilastirmasi"] = hazir_araclar(o, manifest, ornekler, ciktilar)
    return s


def hazir_araclar(
    o: Oturum,
    manifest: Mapping[str, object],
    ornekler: Sequence[Mapping[str, object]],
    ciktilar: Mapping[str, sentetik.OrnekCikti],
) -> dict[str, object]:
    """ijaza ve quran-search-in-text ile karsilastirma (§11); gelistirme ve dondurulmus parcada."""
    kurulum = o.motor()
    tohum = int(str(manifest["tohum"]))
    don, gel = sentetik.bol("iktibas", ornekler, tohum)
    capalar = kurulum.ayet_capalari
    motor_tahmin: dict[str, list[araclar.AracTahmini]] = {}
    for kimlik, c in ciktilar.items():
        satirlar = [h for h in c.satirlar if h.tur == "iktibas"]
        motor_tahmin[kimlik] = [
            araclar.AracTahmini(
                capalar[h.dst_sira],
                h.src_span[0],
                h.src_span[1],
                int(h.evidence["matched_words"]),  # type: ignore[call-overload]
            )
            for h in satirlar
        ]
    sonuc: dict[str, object] = {
        "not": (
            "Araclar etiketli veri tasimaz; yalniz karsilastirma aracidir (K-51 madde 12)."
            " Karar olcutu gelistirme parcasidir (Iktibas tespiti §11)."
        ),
        "olcut": (
            "dizi duzeyi IoU >= 0,5; uzun kesinlik >= 0,95 ve duyarlilik >= 0,85; kisa kesinlik >= "
            "0,85"
        ),
    }
    araclar_listesi: list[tuple[str, Callable[[], araclar.Arac]]] = [
        ("ijaza_2_0_0", araclar.ijaza_araci),
        ("quran_search_in_text_0_1_3", lambda: araclar.search_in_text_araci(capalar)),
    ]
    for ad, kur in araclar_listesi:
        try:
            arac = kur()
        except Exception as hata:
            sonuc[ad] = {"atlandi": f"arac kurulamadi ({type(hata).__name__})"}
            continue
        bolumler: dict[str, object] = {}
        for bolum_adi, grup in (("gelistirme", gel), ("dondurulmus", don)):
            tahminler, sayac = araclar.arac_calistir(arac, grup)
            olcum = araclar.genel_olc(grup, tahminler)
            bolumler[bolum_adi] = {
                **olcum,
                "calisma": sayac,
                "hedefler": araclar.hedefleri_tuttu_mu(olcum),
            }
        sonuc[ad] = bolumler
    kendi: dict[str, object] = {}
    for bolum_adi, grup in (("gelistirme", gel), ("dondurulmus", don)):
        olcum = araclar.genel_olc(grup, motor_tahmin)
        kendi[bolum_adi] = {**olcum, "hedefler": araclar.hedefleri_tuttu_mu(olcum)}
    sonuc["kendi_motor_ayni_olcut"] = kendi
    ijaza = sonuc.get("ijaza_2_0_0")
    karar: dict[str, object]
    if isinstance(ijaza, dict) and "gelistirme" in ijaza:
        tuttu = bool(ijaza["gelistirme"]["hedefler"]["hedefler_tuttu"])
        karar = {
            "ijaza_hedefler_tuttu_gelistirme": tuttu,
            "karar": KARAR_TUTTU if tuttu else KARAR_TUTMADI,
        }
    else:
        karar = {"karar": "ijaza calistirilamadi; karar verilemedi"}
    sonuc["karar_11"] = karar
    return sonuc


TUR_ISLEVLERI: Final[Mapping[str, Callable[[Oturum], TurSonucu]]] = {
    "kok": olc_kok,
    "lemma": olc_lemma,
    "benzer-ayet": olc_benzer,
    "atif": olc_atif,
    "iktibas": olc_iktibas,
}


# --- rapor ve kapi -----------------------------------------------------------------------


def sonuclandir(o: Oturum, s: TurSonucu) -> None:
    """Gerileme kurali, rapor ve `xref_gate` yazimi (`--dry-run`'da yalniz ozet)."""
    onceki = onceki_kabul_edilmis(o.ctx.veri_kok, s.cli_tur)
    gerileme = gerilemeleri_bul(onceki_olculer(onceki), s.olculer)
    for g in gerileme:
        o.regresyonlar.append(f"{s.cli_tur}.{g.olcu} {g.onceki:.4f} -> {g.simdiki:.4f}")
    govde = rapor_govdesi(
        s,
        o.ctx.saat(),
        [{"olcu": g.olcu, "onceki": g.onceki, "simdiki": g.simdiki} for g in gerileme],
    )
    if not o.ctx.dry_run:
        _, ozet = rapor_yaz(o.ctx.veri_kok, s, govde)
        xref_gate_yaz(
            o.conn,
            tur=s.gate_tur,
            set_sinifi=s.set_sinifi,
            set_surumu=s.set_surumu,
            sonuc=s.sonuc,
            set_kaynaklari=s.set_kaynaklari(),
            rapor_sha256=ozet,
            data_version=s.data_version,
        )
    olculer = ", ".join(f"{k} {v:.4f}" for k, v in sorted(s.olculer.items()))
    ek = " (dry-run, hicbir sey yazilmadi)" if o.ctx.dry_run else ""
    alt = (
        " [" + ", ".join(f"{k} {v}" for k, v in sorted(s.alt_sonuclar.items())) + "]"
        if s.alt_sonuclar
        else ""
    )
    o.ozetler.append(
        f"qa gold {s.cli_tur}: {s.sonuc}{alt} (set {s.set_sinifi} {s.set_surumu},"
        f" olculen {s.olculen_ornek}; {olculer}){ek}"
    )
    o.ctx.sayi(f"{s.gate_tur}_olculen", s.olculen_ornek)


def run_qa_gold(
    ctx: RunContext,
    turler: Sequence[str],
    *,
    build: bool,
    baglanti: BAGLANTI | None = None,
    lemmatizer: Lemmatizer | None = None,
) -> Oturum:
    conn = baglanti() if baglanti is not None else baglan(ctx.ayarlar, autocommit=True)
    o = Oturum(ctx, conn, build, lemmatizer)
    try:
        for tur in turler:
            try:
                s = TUR_ISLEVLERI[tur](o)
                sonuclandir(o, s)
            except GirdiHatasi as hata:
                o.hatalar.append(f"{tur}: {hata}")
    finally:
        if baglanti is None:
            conn.close()
    return o


def komut_qa_gold(
    *,
    tur: str,
    build: bool,
    dry_run: bool,
    config: Path | None,
    kok: Path | None,
    baglanti: BAGLANTI | None = None,
    lemmatizer: Lemmatizer | None = None,
) -> int:
    """`qa gold` komutu; cikis kodu 0, 1 ya da 2 (modul belgesi)."""

    def govde(ctx: RunContext) -> int:
        turler = turleri_coz(tur)
        o = run_qa_gold(ctx, turler, build=build, baglanti=baglanti, lemmatizer=lemmatizer)
        for satir in o.ozetler:
            sys.stdout.write(satir + "\n")
        if o.hatalar:
            raise GirdiHatasi("; ".join(o.hatalar))
        if o.regresyonlar:
            raise QaKaldi("gerileme: " + "; ".join(o.regresyonlar))
        return cikis.BASARILI

    return komutu_yurut(
        komut=KOMUT,
        adim=QA_ADIMI,
        kaynaklar=(),
        config=config,
        kok=kok,
        govde=govde,
        dry_run=dry_run,
        parametreler={"type": tur, "build": build},
    )
