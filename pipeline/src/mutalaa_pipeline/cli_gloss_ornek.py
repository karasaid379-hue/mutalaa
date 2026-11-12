"""`qa gloss-sample` ve `qa gloss-score`: kelime anlami QA orneklemi ve puanlama (A17.6; K-50).

`cli.py` yalniz `kaydet(qa_app)` cagirir. Kelime anlamlari §7'ye gore uc kume secer:
- 30 maddelik KALIBRASYON seti (`{run_id}-kalibrasyon.jsonl`; inceleyenler birlikte isler;
  puanlanmaz),
- 300 lemmalik CIFT DEGERLENDIRME seti (`{run_id}-kappa.jsonl`; iki degerlendirici icin bos
  sablon, etiketler `kabul`, `duzelt`, `red`); kalibrasyon maddeleri bu kumeden cikarilir,
- ONAY SONRASI IKINCI OKUMA (`{run_id}-ikinci-okuma.jsonl`; her dalgada onayli maddelerden
  `min(N, max(300, ceil(N / 10)))`; etiketler `dogru`, `kucuk_hata`, `yanlis`),
ve `{run_id}-gloss-sample.json` ozetini yazar. Puanlama (`qa gloss-score`) doldurulmus sablonlari
okur; Cohen kappa (hedef >= 0,60) ve dalga basina Wilson %95 ust siniri (hedef <= %2)
`{run_id}-gloss-score.json` dosyasina yazilir (`qa/uyum.py`).

GIRDI: `--lemmalar` bir JSONL dosyasidir; satir basina bir nesne, yalniz su alanlar:
`{"lemma_id": 12, "dalga": 1, "tutarli": true}`; istege bagli `"onayli": true` (ikinci okuma
evreni; verilmezse yanlis) ve `"tur": "..."` (sozcuk turu; tum satirlarda ya da hicbirinde;
varsa cift degerlendirme tabakasina girer). Baska alan (ornegin anlam metni) girdi hatasidir.
`lemma_id` pozitif tam sayi ve tekil; `dalga` >= 0 tam sayi; `tutarli` mantiksal.

SECIM: A16'nin `qa/ornekleme.py` islevleriyle (`orantili_dagit`: en buyuk kalan; siralama
`sha256("{tohum}|{anahtar}")`) tabakali ve tekrarlanabilir: ayni tohum ve ayni girdi ayni
`lemma_id` listesini verir. Tabaka: kalibrasyon ve cift sette `(dalga, tutarli[, tur])`; ikinci
okumada dalga icinde `tutarli`.

CIKTI: yalniz `lemma_id`, dalga, etiket, sayi ve sonuc. Anlam METNI hicbir dosyaya yazilmaz.
CIKIS KODU (Icerik hatti §4): 0 basarili; 1 yalniz `gloss-score`da hedef tutmadiysa ya da
sablon eksikse (QA kapisi kaldi; rapor yine yazilir); 2 girdi ya da yapilandirma hatasi.
`gloss-sample` yalniz 0 ya da 2 ile cikar.
"""

import sys
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Final

import typer

from mutalaa_pipeline import cikis
from mutalaa_pipeline.export.ortak import GirdiHatasi, kati_json
from mutalaa_pipeline.komut_ortak import komutu_yurut
from mutalaa_pipeline.logs import json_baytlari
from mutalaa_pipeline.qa import uyum
from mutalaa_pipeline.qa.ornekleme import _anahtar, _yaz, json_bayt_satiri, orantili_dagit
from mutalaa_pipeline.runctx import QaKaldi, RunContext

SAMPLE_KOMUTU: Final = "qa gloss-sample"
SCORE_KOMUTU: Final = "qa gloss-score"
VARSAYILAN_TOHUM: Final = 20261112
KALIBRASYON_N: Final = 30
CIFT_N: Final = 300
RAPOR_SONEKI: Final = "-gloss-sample"
SKOR_SONEKI: Final = "-gloss-score"
KALIBRASYON_SONEKI: Final = "-kalibrasyon"
KAPPA_SONEKI: Final = "-kappa"
OKUMA_SONEKI: Final = "-ikinci-okuma"
_LEMMA_ALANLARI: Final = frozenset({"lemma_id", "dalga", "tutarli", "onayli", "tur"})
_KAPPA_ALANLARI: Final = frozenset(
    {"lemma_id", "dalga", "degerlendirici_1", "degerlendirici_2", "not"}
)
_OKUMA_ALANLARI: Final = frozenset({"lemma_id", "dalga", "evren", "karar", "not"})


# --- girdi ---------------------------------------------------------------------------------


@dataclass(frozen=True)
class Lemma:
    lemma_id: int
    dalga: int
    tutarli: bool
    onayli: bool = False
    tur: str | None = None


def _jsonl_oku(yol: Path, ad: str) -> list[tuple[int, dict[str, object]]]:
    try:
        ham = yol.read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError):
        raise GirdiHatasi(f"{ad} okunamadi (UTF-8 JSONL olmali)") from None
    satirlar: list[tuple[int, dict[str, object]]] = []
    for no, satir in enumerate(ham.split("\n"), start=1):
        if satir.strip() == "":
            continue
        nesne = kati_json(satir)
        if not isinstance(nesne, dict):
            raise GirdiHatasi(f"{ad} satir {no}: nesne olmali")
        satirlar.append((no, {str(k): v for k, v in nesne.items()}))
    return satirlar


def _tam_sayi(nesne: Mapping[str, object], alan: str, ad: str, no: int, *, en_az: int) -> int:
    deger = nesne.get(alan)
    if isinstance(deger, bool) or not isinstance(deger, int) or deger < en_az:
        raise GirdiHatasi(f"{ad} satir {no}: {alan} {en_az} ya da daha buyuk tam sayi olmali")
    return deger


def _alan_denetle(nesne: Mapping[str, object], izinli: frozenset[str], ad: str, no: int) -> None:
    if not set(nesne) <= izinli:
        raise GirdiHatasi(f"{ad} satir {no}: bilinmeyen alan (yalniz kimlik, sayi ve etiket)")


def lemmalari_oku(yol: Path) -> list[Lemma]:
    """`--lemmalar` JSONL dosyasini kati bicimde okur (modul belgesindeki bicim)."""
    ad = "--lemmalar"
    sonuc: list[Lemma] = []
    gorulen: set[int] = set()
    for no, nesne in _jsonl_oku(yol, ad):
        _alan_denetle(nesne, _LEMMA_ALANLARI, ad, no)
        lemma_id = _tam_sayi(nesne, "lemma_id", ad, no, en_az=1)
        dalga = _tam_sayi(nesne, "dalga", ad, no, en_az=0)
        tutarli = nesne.get("tutarli")
        onayli = nesne.get("onayli", False)
        tur = nesne.get("tur")
        if not isinstance(tutarli, bool) or not isinstance(onayli, bool):
            raise GirdiHatasi(f"{ad} satir {no}: tutarli ve onayli mantiksal olmali")
        if tur is not None and (not isinstance(tur, str) or tur == ""):
            raise GirdiHatasi(f"{ad} satir {no}: tur bos olmayan dize olmali")
        if lemma_id in gorulen:
            raise GirdiHatasi(f"{ad} satir {no}: yinelenen lemma_id")
        gorulen.add(lemma_id)
        sonuc.append(Lemma(lemma_id, dalga, tutarli, onayli, tur))
    if not sonuc:
        raise GirdiHatasi("--lemmalar bos: en az bir lemma gerekir")
    turlu = {x.tur is not None for x in sonuc}
    if len(turlu) > 1:
        raise GirdiHatasi("--lemmalar: tur alani tum satirlarda ya da hicbirinde olmali")
    return sonuc


# --- secim ---------------------------------------------------------------------------------

Tabaka = tuple[int, bool, str]  # (dalga, tutarli, tur); bos tur ve "tutarli" kipinde dalga 0


def _siralama_anahtari(tohum: int, lemma: Lemma) -> str:
    return _anahtar(tohum, f"lemma:{lemma.lemma_id}")  # A16 ile ayni `sha256(tohum|anahtar)`


def tabakali_sec(
    evren: Sequence[Lemma], n: int, tohum: int, tabaka_ad: str
) -> tuple[list[Lemma], list[dict[str, object]]]:
    """`n` lemmayi tabakalara orantili dagitip her tabakadan `sha256` siralamasiyla secer.

    `tabaka_ad`: `"tam"` -> `(dalga, tutarli[, tur])`; `"tutarli"` -> `(tutarli,)`. Donus:
    `lemma_id` sirali secim ve tabaka dagilimi (`evren`, `secilen`).
    """
    if n < 0 or n > len(evren):
        raise GirdiHatasi("secim boyu 0 ile evren buyuklugu arasinda olmali")
    tam = tabaka_ad == "tam"
    kovalar: dict[Tabaka, list[Lemma]] = defaultdict(list)
    for lemma in evren:
        kovalar[
            (lemma.dalga if tam else 0, lemma.tutarli, (lemma.tur or "") if tam else "")
        ].append(lemma)
    sirali = sorted(kovalar)
    dagitim = orantili_dagit([len(kovalar[t]) for t in sirali], n) if n > 0 else [0] * len(sirali)
    secilen: list[Lemma] = []
    dagilim: list[dict[str, object]] = []
    for (dalga, tutarli, tur), adet in zip(sirali, dagitim, strict=True):
        kova = sorted(kovalar[(dalga, tutarli, tur)], key=lambda x: _siralama_anahtari(tohum, x))
        secilen.extend(kova[:adet])
        kayit: dict[str, object] = {"evren": len(kova), "secilen": adet, "tutarli": tutarli}
        if tam:
            kayit["dalga"] = dalga
            if tur != "":
                kayit["tur"] = tur
        dagilim.append(kayit)
    return sorted(secilen, key=lambda x: x.lemma_id), dagilim


@dataclass(frozen=True)
class OrnekKumeleri:
    kalibrasyon: list[Lemma]
    cift: list[Lemma]
    cift_tabakalari: list[dict[str, object]]
    ikinci_okuma: list[tuple[Lemma, int]]  # (lemma, dalganin onayli evreni)
    ikinci_okuma_dalgalari: list[dict[str, object]]


def kumeleri_sec(
    lemmalar: Sequence[Lemma], tohum: int, kalibrasyon_n: int, cift_n: int
) -> OrnekKumeleri:
    if kalibrasyon_n + cift_n > len(lemmalar):
        raise GirdiHatasi("kalibrasyon ve cift degerlendirme boylarinin toplami evrenden buyuk")
    kalibrasyon, _ = tabakali_sec(lemmalar, kalibrasyon_n, tohum, "tam")
    kalan_idler = {x.lemma_id for x in kalibrasyon}
    kalan = [x for x in lemmalar if x.lemma_id not in kalan_idler]
    cift, tabakalar = tabakali_sec(kalan, cift_n, tohum, "tam")
    dalgalar: dict[int, list[Lemma]] = defaultdict(list)
    for x in lemmalar:
        if x.onayli:
            dalgalar[x.dalga].append(x)
    okuma: list[tuple[Lemma, int]] = []
    dalga_ozeti: list[dict[str, object]] = []
    for dalga in sorted(dalgalar):
        evren = dalgalar[dalga]
        boy = uyum.ikinci_okuma_boyu(len(evren))
        secilen, dagilim = tabakali_sec(evren, boy, tohum, "tutarli")
        okuma.extend((x, len(evren)) for x in secilen)
        dalga_ozeti.append(
            {"dalga": dalga, "onayli_evren": len(evren), "secilen": boy, "tabakalar": dagilim}
        )
    return OrnekKumeleri(kalibrasyon, cift, tabakalar, okuma, dalga_ozeti)


def _satirlar(nesneler: Sequence[Mapping[str, object]]) -> bytes:
    return "".join(json_bayt_satiri(n) for n in nesneler).encode("utf-8")


def kume_dosyalari(k: OrnekKumeleri) -> dict[str, bytes]:
    """Sonek -> dosya baytlari; bos kume dosya uretmez."""
    dosyalar: dict[str, bytes] = {}
    if k.kalibrasyon:
        dosyalar[KALIBRASYON_SONEKI] = _satirlar(
            [
                {"lemma_id": x.lemma_id, "dalga": x.dalga, "tutarli": x.tutarli}
                for x in k.kalibrasyon
            ]
        )
    if k.cift:
        dosyalar[KAPPA_SONEKI] = _satirlar(
            [
                {
                    "lemma_id": x.lemma_id,
                    "dalga": x.dalga,
                    "degerlendirici_1": None,
                    "degerlendirici_2": None,
                }
                for x in k.cift
            ]
        )
    if k.ikinci_okuma:
        dosyalar[OKUMA_SONEKI] = _satirlar(
            [
                {"lemma_id": x.lemma_id, "dalga": x.dalga, "evren": evren, "karar": None}
                for x, evren in k.ikinci_okuma
            ]
        )
    return dosyalar


# --- komut: gloss-sample ---------------------------------------------------------------------


def komut_gloss_sample(
    *,
    lemmalar: Path,
    tohum: int,
    kalibrasyon_n: int = KALIBRASYON_N,
    cift_n: int = CIFT_N,
    dry_run: bool,
    config: Path | None,
    kok: Path | None,
) -> int:
    """`qa gloss-sample`; cikis kodu 0 ya da 2."""

    def govde(ctx: RunContext) -> int:
        if kalibrasyon_n < 0 or cift_n < 0:
            raise GirdiHatasi("--kalibrasyon-n ve --cift-n 0 ya da daha buyuk olmali")
        girdi = lemmalari_oku(lemmalar)
        k = kumeleri_sec(girdi, tohum, kalibrasyon_n, cift_n)
        dosyalar = kume_dosyalari(k)
        rapor: dict[str, object] = {
            "tohum": tohum,
            "yontem": (
                "dalga ve tutarlilik tabakali, orantili (en buyuk kalan), sha256(tohum|lemma)"
            ),
            "evren": len(girdi),
            "onayli_evren": sum(1 for x in girdi if x.onayli),
            "kalibrasyon": {
                "n": len(k.kalibrasyon),
                "lemma_idleri": [x.lemma_id for x in k.kalibrasyon],
            },
            "cift_degerlendirme": {
                "n": len(k.cift),
                "tabakalar": k.cift_tabakalari,
                "lemma_idleri": [x.lemma_id for x in k.cift],
            },
            "ikinci_okuma": {
                "dalgalar": k.ikinci_okuma_dalgalari,
                "n": len(k.ikinci_okuma),
                "lemma_idleri": [x.lemma_id for x, _ in k.ikinci_okuma],
            },
        }
        ctx.rapor_ek.update(
            tohum=tohum,
            kalibrasyon_n=len(k.kalibrasyon),
            cift_n=len(k.cift),
            ikinci_okuma_n=len(k.ikinci_okuma),
        )
        if not dry_run:
            ctx.rapor_ek["ornek_raporu"] = _yaz(
                ctx, f"{ctx.run_id}{RAPOR_SONEKI}.json", json_baytlari(rapor)
            )
            for sonek, veri in dosyalar.items():
                ctx.rapor_ek[f"sablon{sonek.replace('-', '_')}"] = _yaz(
                    ctx, f"{ctx.run_id}{sonek}.jsonl", veri
                )
        sys.stdout.write(
            f"qa gloss-sample: kalibrasyon {len(k.kalibrasyon)}, cift degerlendirme {len(k.cift)},"
            f" ikinci okuma {len(k.ikinci_okuma)} (tohum {tohum})"
            f"{' [dry-run: dosya yazilmadi]' if dry_run else ''}\n"
        )
        return cikis.BASARILI

    return komutu_yurut(
        komut=SAMPLE_KOMUTU,
        adim="qa",
        kaynaklar=[],
        config=config,
        kok=kok,
        govde=govde,
        dry_run=dry_run,
        parametreler={"tohum": tohum, "kalibrasyon_n": kalibrasyon_n, "cift_n": cift_n},
    )


# --- komut: gloss-score ----------------------------------------------------------------------


def kappa_sablonu_oku(yol: Path) -> tuple[list[tuple[int, str, str]], int]:
    """`(lemma_id, e1, e2)` tam doldurulmus satirlar ve eksik (bos) satir sayisi."""
    ad = "--kappa-sablon"
    dolu: list[tuple[int, str, str]] = []
    eksik = 0
    gorulen: set[int] = set()
    for no, nesne in _jsonl_oku(yol, ad):
        _alan_denetle(nesne, _KAPPA_ALANLARI, ad, no)
        lemma_id = _tam_sayi(nesne, "lemma_id", ad, no, en_az=1)
        if lemma_id in gorulen:
            raise GirdiHatasi(f"{ad} satir {no}: yinelenen lemma_id")
        gorulen.add(lemma_id)
        etiketler: list[str] = []
        for alan in ("degerlendirici_1", "degerlendirici_2"):
            deger = nesne.get(alan)
            if deger is None:
                continue
            if deger not in uyum.KAPPA_ETIKETLERI:
                raise GirdiHatasi(f"{ad} satir {no}: etiket kabul, duzelt ya da red olmali")
            etiketler.append(str(deger))
        if len(etiketler) == 2:
            dolu.append((lemma_id, etiketler[0], etiketler[1]))
        else:
            eksik += 1
    return dolu, eksik


def okuma_sablonu_oku(yol: Path) -> dict[int, tuple[int, list[tuple[int, str | None]]]]:
    """Dalga -> `(evren, [(lemma_id, karar ya da None)])`."""
    ad = "--ikinci-okuma-sablon"
    dalgalar: dict[int, tuple[int, list[tuple[int, str | None]]]] = {}
    gorulen: set[int] = set()
    for no, nesne in _jsonl_oku(yol, ad):
        _alan_denetle(nesne, _OKUMA_ALANLARI, ad, no)
        lemma_id = _tam_sayi(nesne, "lemma_id", ad, no, en_az=1)
        dalga = _tam_sayi(nesne, "dalga", ad, no, en_az=0)
        evren = _tam_sayi(nesne, "evren", ad, no, en_az=1)
        if lemma_id in gorulen:
            raise GirdiHatasi(f"{ad} satir {no}: yinelenen lemma_id")
        gorulen.add(lemma_id)
        karar = nesne.get("karar")
        if karar is not None and karar not in uyum.OKUMA_ETIKETLERI:
            raise GirdiHatasi(f"{ad} satir {no}: karar dogru, kucuk_hata ya da yanlis olmali")
        onceki = dalgalar.get(dalga)
        if onceki is not None and onceki[0] != evren:
            raise GirdiHatasi(f"{ad} satir {no}: ayni dalgada evren tutarsiz")
        satirlar = onceki[1] if onceki is not None else []
        satirlar.append((lemma_id, None if karar is None else str(karar)))
        dalgalar[dalga] = (evren, satirlar)
    return dalgalar


def kappa_bolumu(dolu: Sequence[tuple[int, str, str]], eksik: int) -> dict[str, object]:
    satir = len(dolu) + eksik
    if not dolu:
        return {
            "olculdu": False,
            "neden": "doldurulmus madde yok",
            "satir": satir,
            "eksik": eksik,
            "gecti": False,
        }
    a = [x[1] for x in dolu]
    b = [x[2] for x in dolu]
    ozet = uyum.kappa_ozet(a, b).sozluk()
    capraz: dict[str, dict[str, int]] = {}
    for (e1, e2), adet in sorted(Counter(zip(a, b, strict=True)).items()):
        capraz.setdefault(e1, {})[e2] = adet
    tam = eksik == 0
    ozet.update(
        olculdu=True,
        satir=satir,
        eksik=eksik,
        tam=tam,
        capraz=capraz,
        uyusmayanlar=[
            {"lemma_id": lid, "degerlendirici_1": e1, "degerlendirici_2": e2}
            for lid, e1, e2 in dolu
            if e1 != e2
        ],
        hedef_gecti=ozet["gecti"],
        gecti=bool(ozet["gecti"]) and tam,
    )
    return ozet


def okuma_bolumu(
    dalgalar: Mapping[int, tuple[int, list[tuple[int, str | None]]]],
) -> dict[str, object]:
    liste: list[dict[str, object]] = []
    for dalga in sorted(dalgalar):
        evren, satirlar = dalgalar[dalga]
        karar = [(lid, k) for lid, k in satirlar if k is not None]
        ozet = uyum.ikinci_okuma_ozet([k for _, k in karar], evren).sozluk()
        ozet.update(
            dalga=dalga,
            satir=len(satirlar),
            eksik=len(satirlar) - len(karar),
            yanlis_lemma_idleri=[lid for lid, k in karar if k == uyum.HATA_ETIKETI],
        )
        liste.append(ozet)
    return {"dalgalar": liste, "gecti": bool(liste) and all(bool(d["gecti"]) for d in liste)}


def komut_gloss_score(
    *,
    kappa_sablon: Path | None,
    ikinci_okuma_sablon: Path | None,
    dry_run: bool,
    config: Path | None,
    kok: Path | None,
) -> int:
    """`qa gloss-score`; cikis kodu 0, 1 (hedef tutmadi ya da sablon eksik) ya da 2."""

    def govde(ctx: RunContext) -> int:
        if kappa_sablon is None and ikinci_okuma_sablon is None:
            raise GirdiHatasi("--kappa-sablon ya da --ikinci-okuma-sablon verilmeli")
        rapor: dict[str, object] = {
            "yontem": {
                "kappa": "Cohen kappa, hedef >= 0,60",
                "ikinci_okuma": "Wilson %95 ust sinir (yanlis orani), hedef <= %2",
            }
        }
        sonuclar: list[bool] = []
        if kappa_sablon is not None:
            dolu, eksik = kappa_sablonu_oku(kappa_sablon)
            bolum = kappa_bolumu(dolu, eksik)
            rapor["kappa"] = bolum
            sonuclar.append(bool(bolum["gecti"]))
            ctx.rapor_ek["kappa_gecti"] = bool(bolum["gecti"])
        if ikinci_okuma_sablon is not None:
            bolum = okuma_bolumu(okuma_sablonu_oku(ikinci_okuma_sablon))
            rapor["ikinci_okuma"] = bolum
            sonuclar.append(bool(bolum["gecti"]))
            ctx.rapor_ek["ikinci_okuma_gecti"] = bool(bolum["gecti"])
        gecti = all(sonuclar)
        rapor["sonuc"] = "gecti" if gecti else "kaldi"
        if not dry_run:
            ctx.rapor_ek["puan_raporu"] = _yaz(
                ctx, f"{ctx.run_id}{SKOR_SONEKI}.json", json_baytlari(rapor)
            )
        sys.stdout.write(
            f"qa gloss-score: {rapor['sonuc']}{' [dry-run: dosya yazilmadi]' if dry_run else ''}\n"
        )
        if not gecti:
            raise QaKaldi("kappa ya da ikinci okuma hedefi tutmadi ya da sablon eksik")
        return cikis.BASARILI

    return komutu_yurut(
        komut=SCORE_KOMUTU,
        adim="qa",
        kaynaklar=[],
        config=config,
        kok=kok,
        govde=govde,
        dry_run=dry_run,
        parametreler={},
    )


# --- Typer -------------------------------------------------------------------------------------

_KOK = Annotated[
    Path | None,
    typer.Option("--kok", help="Depo koku (testler icin); verilmezse pnpm-workspace.yaml aranir."),
]
_CONFIG = Annotated[Path | None, typer.Option("--config", help="Baska bir mutalaa.toml.")]
_DRY = Annotated[bool, typer.Option("--dry-run", help="Dosya yazmaz; ozeti yazdirir.")]


def kaydet(qa_app: typer.Typer) -> None:
    """`qa gloss-sample` ve `qa gloss-score` komutlarini `qa` grubuna ekler."""

    @qa_app.command("gloss-sample")
    def gloss_sample(
        lemmalar: Annotated[
            Path,
            typer.Option(
                "--lemmalar",
                help=(
                    "Lemma listesi (JSONL; satir basina {lemma_id, dalga, tutarli}, istege bagli "
                    "onayli ve tur; baska alan yok)."
                ),
            ),
        ],
        tohum: Annotated[
            int, typer.Option("--tohum", help="Sabit tohum; ayni tohum ayni listeyi verir.")
        ] = VARSAYILAN_TOHUM,
        kalibrasyon_n: Annotated[
            int, typer.Option("--kalibrasyon-n", help="Kalibrasyon seti boyu.")
        ] = KALIBRASYON_N,
        cift_n: Annotated[
            int, typer.Option("--cift-n", help="Cift degerlendirme seti boyu.")
        ] = CIFT_N,
        dry_run: _DRY = False,
        config: _CONFIG = None,
        kok: _KOK = None,
    ) -> None:
        """Kalibrasyon (30), cift degerlendirme (300) ve ikinci okuma sablonlari. Cikis 0 ya da 2.

        Cikti: data/reports/{run_id}-gloss-sample.json, -kalibrasyon.jsonl, -kappa.jsonl,
        -ikinci-okuma.jsonl (yalniz lemma_id, sayi ve bos etiket alanlari).
        """
        kod = komut_gloss_sample(
            lemmalar=lemmalar,
            tohum=tohum,
            kalibrasyon_n=kalibrasyon_n,
            cift_n=cift_n,
            dry_run=dry_run,
            config=config,
            kok=kok,
        )
        if kod != cikis.BASARILI:
            raise typer.Exit(code=kod)

    @qa_app.command("gloss-score")
    def gloss_score(
        kappa_sablon: Annotated[
            Path | None,
            typer.Option("--kappa-sablon", help="Doldurulmus -kappa.jsonl (kabul/duzelt/red)."),
        ] = None,
        ikinci_okuma_sablon: Annotated[
            Path | None,
            typer.Option(
                "--ikinci-okuma-sablon",
                help="Doldurulmus -ikinci-okuma.jsonl (dogru/kucuk_hata/yanlis).",
            ),
        ] = None,
        dry_run: _DRY = False,
        config: _CONFIG = None,
        kok: _KOK = None,
    ) -> None:
        """Doldurulmus sablonlari puanlar: Cohen kappa (>= 0,60), Wilson ust sinir (<= %2).

        Cikis 0 (hedefler tuttu), 1 (hedef tutmadi ya da sablon eksik; rapor yine yazilir), 2.
        """
        kod = komut_gloss_score(
            kappa_sablon=kappa_sablon,
            ikinci_okuma_sablon=ikinci_okuma_sablon,
            dry_run=dry_run,
            config=config,
            kok=kok,
        )
        if kod != cikis.BASARILI:
            raise typer.Exit(code=kod)
