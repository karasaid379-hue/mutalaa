"""QAC gercek veri testleri (A17.1, A17.5): veri varsa kosar, yoksa atlanir.

`data/` CI'da yoktur; `MUTALAA_DEGISMEZLIK_ZORUNLU=1` atlamayi hataya cevirir. Indirilen dosyalar
(`data/gelen/qac-morfoloji`, `qac-belge`, `mustafa0x-morfoloji`) guvenilmeyen VERIDIR: onlari
okuyan Python `-I` ile ayri surecte calisir (`test_meal_gercek.py` deseni). Test yalniz SAYI,
KUME FARKI ve kimlik dogrular; Arapca ya da Buckwalter metni ciktiya girmez. Sayilar teste
yazilmaz: dosyadan bagimsiz bir ayristirmayla yeniden hesaplanir.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from mutalaa_pipeline.anchor.ayet_sayilari import AYET_SAYILARI
from mutalaa_pipeline.config import Ayarlar
from mutalaa_pipeline.ingest import qac

BETIK = r"""
import hashlib, html, json, re, sys, unicodedata
from collections import Counter
from pathlib import Path

from mutalaa_pipeline.enrich.buckwalter import TABLO, bw_arapca, eslenemeyenler, tablo_ayristir
from mutalaa_pipeline.enrich.morphology import (
    DALGA0_ETIKETLERI, HARF_ETIKETLERI, SAYFA_ETIKETLERI, ZAMIR_ETIKETLERI,
    envanter_hesapla, kelimelere_topla, lemma_ayir, lemma_metni, kok_harfleri,
)
from mutalaa_pipeline.ingest import qac
from mutalaa_pipeline.qa.qac_capraz import karsilastir, mustafa0x_oku

kok = Path(sys.argv[1])
tarih = sys.argv[2]


def dogrula(klasor, adlar):
    sums = {}
    for satir in (klasor / "SHA256SUMS").read_bytes().decode("utf-8").split("\n"):
        if satir:
            sums[satir[66:]] = satir[:64]
    for ad in adlar:
        assert hashlib.sha256((klasor / ad).read_bytes()).hexdigest() == sums[ad], ad


sonuc = {}
qac_klasor = kok / "gelen" / "qac-morfoloji" / tarih
belge = kok / "gelen" / "qac-belge" / tarih
dogrula(qac_klasor, [qac.DOSYA_ADI])
dogrula(belge, ["buckwalter.html", "tagset.html", "morphologicalfeatures.html"])
ham = (qac_klasor / qac.DOSYA_ADI).read_bytes()
dosya = qac.ayristir(ham)

# --- bagimsiz ayristirma (paketin ayristiricisini kullanmaz) ---
satirlar = ham.decode("ascii").split("\r\n")
veri = [s.split("\t") for s in satirlar if s.startswith("(")]
bag = {
    "segment": len(veri),
    "lem": len({p[3][p[3].index("LEM:") + 4:].split("|")[0] for p in veri if "LEM:" in p[3]}),
    "root": len({p[3][p[3].index("ROOT:") + 5:].split("|")[0] for p in veri if "ROOT:" in p[3]}),
    "tag": len({p[2] for p in veri}),
    "kelime": len({p[0].rsplit(":", 1)[0] for p in veri}),
}
sonuc["bagimsiz"] = bag
sonuc["paket"] = qac.sayilar_hesapla(dosya)

# --- Buckwalter tablosu sayfadan; kume farki ---
sayfa = (belge / "buckwalter.html").read_bytes().decode("utf-8")
sonuc["tablo_sayfadan_ayni"] = tablo_ayristir(sayfa) == TABLO
kullanilan = {"FORM": set(), "LEM": set(), "ROOT": set()}
for s in dosya.segmentler:
    kullanilan["FORM"].update(s.form)
    if s.lem is not None:
        kullanilan["LEM"].update(s.lem)
    if s.kok is not None:
        kullanilan["ROOT"].update(s.kok)
sonuc["eslenemeyen"] = {
    ad: sorted(hex(ord(c)) for c in eslenemeyenler("".join(k))) for ad, k in kullanilan.items()
}
lem_rakam = {s.lem for s in dosya.segmentler if s.lem is not None and s.lem[-1:].isdigit()}
sonuc["rakamli_lem"] = len(lem_rakam)
tum_lem = {s.lem for s in dosya.segmentler if s.lem}
sonuc["rakamsiz_ikizi_olan"] = len({lemma_ayir(x)[0] for x in lem_rakam} & tum_lem)
sonuc["rakam_degerleri"] = sorted({lemma_ayir(x)[1] for x in lem_rakam})

# --- donusum: tum lemma ve kokler cevrilebilir (rakam ayirtici disinda) ---
lemmalar = sorted({s.lem for s in dosya.segmentler if s.lem is not None})
kokler = sorted({s.kok for s in dosya.segmentler if s.kok is not None})
for i, lem in enumerate(lemmalar, start=1):
    lemma_metni(lem, i)
for i, k in enumerate(kokler, start=1):
    kok_harfleri(k, i)
sonuc["donusen_lemma"] = len(lemmalar)
sonuc["donusen_kok"] = len(kokler)

# --- etiket sayfasi: gruplama ---
sayfa_t = (belge / "tagset.html").read_bytes().decode("utf-8", "replace").replace("\r\n", "\n")
gruplar = {}
mevcut = None
for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", sayfa_t, re.S):
    grup = re.search(r'<td[^>]*class="sc"[^>]*>(.*?)</td>', tr, re.S)
    if grup:
        mevcut = " ".join(re.sub(r"<[^>]+>", "", grup.group(1)).split())
    etiket = re.search(r'<td class="c1">([A-Z]+)</td>', tr)
    if etiket and mevcut is not None and 'class="hr"' not in tr:
        gruplar.setdefault(mevcut, []).append(etiket.group(1))
sonuc["gruplar"] = {ascii(g): len(t) for g, t in gruplar.items()}
def grup(parca):
    return {t for g, ts in gruplar.items() if parca in g for t in ts}
zamir = grup("Pronouns")
harf = grup("Prepositions") | grup("Prefixes") | grup("Conjunctions") | (
    {t for g, ts in gruplar.items() if g == "Particles" for t in ts}
)
sonuc["zamir_esit"] = zamir == set(ZAMIR_ETIKETLERI)
sonuc["harf_esit"] = harf == set(HARF_ETIKETLERI)
sonuc["sayfa_etiketleri_esit"] = {t for ts in gruplar.values() for t in ts} == set(SAYFA_ETIKETLERI)
dosya_etiketleri = {s.tag for s in dosya.segmentler}
sonuc["dosyada_olup_sayfada_olmayan"] = sorted(dosya_etiketleri - SAYFA_ETIKETLERI)
sonuc["sayfada_olup_dosyada_olmayan"] = sorted(SAYFA_ETIKETLERI - dosya_etiketleri)
kelimeler = kelimelere_topla(dosya.segmentler)
env = envanter_hesapla(kelimeler, (115, 1))
sonuc["govde_etiketleri_sayfada"] = {k.govde.tag for k in kelimeler} <= set(SAYFA_ETIKETLERI)
sonuc["lemma_kok_tag"] = {
    "inl_lemmasiz": all(k.govde.lem is None for k in kelimeler if k.govde.tag == "INL"),
    "det_govde": sum(1 for k in kelimeler if k.govde.tag == "DET"),
    "lemma_sayisi": len(env.lemmalar),
    "kok_sayisi": len(env.kokler),
    "kelime": env.kelime_sayisi,
    "gecis_toplami": sum(lm.occurrences for lm in env.lemmalar),
    "lemmasiz": env.lemmasiz_kelime,
}

# --- mustafa0x capraz ---
capraz = mustafa0x_oku(kok)
if capraz is None:
    sonuc["capraz"] = None
else:
    lm = {lemma: lemma_metni(lemma, 1)[0] for lemma in lemmalar}
    km = {k: kok_harfleri(k, 1) for k in kokler}
    kars = karsilastir(kelimeler, lm, km, capraz)
    sonuc["capraz"] = kars.sayilar()
    sonuc["capraz_beklenen_kelime"] = sum(
        1 for k in kelimeler if k.govde.lem is not None or k.govde.kok is not None
    )
    sonuc["capraz_lemma_kelime"] = sum(1 for k in kelimeler if k.govde.lem is not None)
    sonuc["capraz_kok_kelime"] = sum(1 for k in kelimeler if k.govde.kok is not None)
    sonuc["capraz_ornek_capa_sayisi"] = len(kars.ornek_capalar)
print(json.dumps(sonuc))
"""


def _yok(neden: str) -> None:
    if os.environ.get("MUTALAA_DEGISMEZLIK_ZORUNLU") == "1":
        pytest.fail(f"zorunlu gercek veri testi veri bulamadi: {neden}")
    pytest.skip(neden)


def _veri_kok() -> Path:
    ortam = os.environ.get("MUTALAA_VERI_KOK")
    return Ayarlar(veri_kok=Path(ortam)).veri_kok if ortam is not None else Ayarlar().veri_kok


@pytest.fixture(scope="module")
def olcum() -> dict[str, object]:
    kok = _veri_kok() / "gelen"
    tarih = qac.kilit_yukle().alinma_tarihi
    for slug in ("qac-morfoloji", "qac-belge"):
        if not (kok / slug / tarih / "SHA256SUMS").is_file():
            _yok(f"gelen dosyasi yok: gelen/{slug}/{tarih}")
    sonuc = subprocess.run(
        [sys.executable, "-I", "-c", BETIK, str(_veri_kok()), tarih],
        capture_output=True,
        check=False,
        timeout=900,
    )
    assert sonuc.returncode == 0, sonuc.stderr.decode("utf-8", "replace")[-600:]
    veri: dict[str, object] = json.loads(sonuc.stdout.decode("utf-8"))
    return veri


def test_paket_sayimlari_bagimsiz_ayristirmayla_ayni(olcum: dict[str, object]) -> None:
    bag, paket = olcum["bagimsiz"], olcum["paket"]
    assert isinstance(bag, dict) and isinstance(paket, dict)
    for ad in ("segment", "lem", "root", "tag", "kelime"):
        assert bag[ad] == paket[ad], ad
    assert paket["sure"] == len(AYET_SAYILARI)


def test_buckwalter_tablosu_sayfadan_ayni_ve_kume_farki_bilinen(olcum: dict[str, object]) -> None:
    assert olcum["tablo_sayfadan_ayni"] is True
    fark = olcum["eslenemeyen"]
    assert isinstance(fark, dict)
    assert fark["ROOT"] == []  # kokler tablodaki harflerle tamamen cevrilir
    assert fark["LEM"] == ["0x32"]  # yalniz '2': homograf ayirt eden sira numarasi (tabloda yok)
    assert fark["FORM"] == ["0x20"]  # FORM'da bosluk (iki belirtecli bir segment); cevrilmez
    assert olcum["rakam_degerleri"] == [2]
    assert (
        olcum["rakamsiz_ikizi_olan"] == olcum["rakamli_lem"]
    )  # her '2'li lemmanin rakamsiz ikizi var
    assert olcum["donusen_lemma"] == olcum["bagimsiz"]["lem"]  # type: ignore[index]
    assert olcum["donusen_kok"] == olcum["bagimsiz"]["root"]  # type: ignore[index]


def test_etiket_sayfasi_dalga0_listesiyle_tutarli(olcum: dict[str, object]) -> None:
    assert olcum["zamir_esit"] is True
    assert olcum["harf_esit"] is True
    assert olcum["sayfa_etiketleri_esit"] is True
    assert olcum["dosyada_olup_sayfada_olmayan"] == ["DET"]  # 45 etiket (dosya) - 44 (sayfa)
    assert olcum["sayfada_olup_dosyada_olmayan"] == []
    assert olcum["govde_etiketleri_sayfada"] is True  # DET yalniz onek segmentinde gecer
    sayilar = olcum["lemma_kok_tag"]
    assert isinstance(sayilar, dict)
    assert sayilar["det_govde"] == 0
    assert sayilar["inl_lemmasiz"] is True  # INL govdesinin lemmasi yok: dalga 0 sorusu onemsiz
    assert sayilar["gecis_toplami"] + sayilar["lemmasiz"] == sayilar["kelime"]


def test_capraz_karsilastirma_tutarli(olcum: dict[str, object]) -> None:
    capraz = olcum["capraz"]
    if capraz is None:
        _yok("gelen/mustafa0x-morfoloji kopyasi yok")
    assert isinstance(capraz, dict)
    assert capraz["kopyada_olmayan_kelime"] == 0
    assert capraz["karsilastirilan_kelime"] == olcum["capraz_beklenen_kelime"]
    lemma_toplam = capraz["lemma_ayni"] + capraz["lemma_iskelet_ayni"] + capraz["lemma_farkli"]
    assert lemma_toplam <= olcum["capraz_lemma_kelime"]  # type: ignore[operator]
    assert capraz["kok_ayni"] + capraz["kok_farkli"] <= olcum["capraz_kok_kelime"]  # type: ignore[operator]
    assert olcum["capraz_ornek_capa_sayisi"] <= 20  # type: ignore[operator]
