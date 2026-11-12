"""`qa gloss-sample` ve `qa gloss-score` (A17.6; veritabanisiz, SENTETIK lemma kimlikleri).

Girdide yalniz sayi ve mantiksal degerler vardir; anlam metni yoktur ve girdiye giremez.
Raporlar `tmp_path/data/reports/` altina yazilir (`MUTALAA_VERI_KOK` ortam degiskeniyle).
"""

import json
from collections import Counter
from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

from mutalaa_pipeline import cikis
from mutalaa_pipeline import cli_gloss_ornek as g
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.qa.ornekleme import orantili_dagit


def _lemmalar(adet: int = 1000, *, onayli_dalga: dict[int, int] | None = None) -> list[g.Lemma]:
    """Dalga 0..3, tutarli her 3 lemmadan biri degil; `onayli_dalga`: dalga -> onayli sayisi."""
    kalan = dict(onayli_dalga or {})
    sonuc: list[g.Lemma] = []
    for i in range(1, adet + 1):
        dalga = i % 4
        onayli = kalan.get(dalga, 0) > 0
        if onayli:
            kalan[dalga] -= 1
        sonuc.append(g.Lemma(i, dalga, i % 3 != 0, onayli))
    return sonuc


def _jsonl_yaz(yol: Path, lemmalar: list[g.Lemma], *, tur: bool = False) -> Path:
    satirlar = []
    for x in lemmalar:
        nesne: dict[str, object] = {"lemma_id": x.lemma_id, "dalga": x.dalga, "tutarli": x.tutarli}
        if x.onayli:
            nesne["onayli"] = True
        if tur:
            nesne["tur"] = "isim" if x.lemma_id % 2 else "fiil"
        satirlar.append(json.dumps(nesne))
    yol.write_bytes(("\n".join(satirlar) + "\n").encode("utf-8"))
    return yol


@pytest.fixture
def ortam(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    veri = tmp_path / "data"
    monkeypatch.setenv("MUTALAA_VERI_KOK", str(veri))
    return tmp_path


def _rapor_klasoru(tmp_path: Path) -> Path:
    return tmp_path / "data" / "reports"


def _sample(tmp_path: Path, girdi: Path, **kw: object) -> int:
    return g.komut_gloss_sample(
        lemmalar=girdi,
        tohum=int(kw.pop("tohum", 7)),  # type: ignore[call-overload]
        dry_run=bool(kw.pop("dry_run", False)),
        config=None,
        kok=tmp_path,
        **kw,  # type: ignore[arg-type]
    )


def _tek(klasor: Path, desen: str) -> Path:
    bulunan = sorted(klasor.glob(desen))
    assert len(bulunan) == 1, desen
    return bulunan[0]


def _satirlar(yol: Path) -> list[dict[str, object]]:
    return [json.loads(s) for s in yol.read_bytes().decode("utf-8").splitlines()]


# --- girdi -------------------------------------------------------------------------------------


def test_girdi_gecerli(tmp_path: Path) -> None:
    yol = _jsonl_yaz(tmp_path / "l.jsonl", _lemmalar(10, onayli_dalga={1: 1}), tur=True)
    sonuc = g.lemmalari_oku(yol)
    assert len(sonuc) == 10 and sum(x.onayli for x in sonuc) == 1
    assert all(x.tur in {"isim", "fiil"} for x in sonuc)


@pytest.mark.parametrize(
    "satirlar",
    [
        ['{"lemma_id":1,"dalga":0,"tutarli":true,"anlam":"Deneme anlam"}'],  # anlam metni girmez
        ['{"lemma_id":1,"dalga":0,"tutarli":true}', '{"lemma_id":1,"dalga":1,"tutarli":false}'],
        ['{"lemma_id":true,"dalga":0,"tutarli":true}'],
        ['{"lemma_id":0,"dalga":0,"tutarli":true}'],
        ['{"lemma_id":1,"dalga":-1,"tutarli":true}'],
        ['{"lemma_id":1.0,"dalga":0,"tutarli":true}'],
        ['{"lemma_id":1,"dalga":0,"tutarli":"evet"}'],
        ['{"lemma_id":1,"dalga":0,"tutarli":true,"onayli":1}'],
        [
            '{"lemma_id":1,"dalga":0,"tutarli":true,"tur":"isim"}',
            '{"lemma_id":2,"dalga":0,"tutarli":true}',
        ],
        ['{"lemma_id":1,"dalga":0,"tutarli":true,"lemma_id":2}'],  # yinelenen anahtar
        ["[1,2]"],
        ["{bozuk"],
        [],
    ],
)
def test_girdi_hatalari(tmp_path: Path, satirlar: list[str]) -> None:
    yol = tmp_path / "l.jsonl"
    yol.write_bytes(("\n".join(satirlar) + "\n").encode("utf-8"))
    with pytest.raises(GirdiHatasi):
        g.lemmalari_oku(yol)


def test_girdi_bom_ve_gecersiz_utf8_ve_olmayan_dosya(tmp_path: Path) -> None:
    yol = tmp_path / "l.jsonl"
    yol.write_bytes(b"\xef\xbb\xbf" + b'{"lemma_id":1,"dalga":0,"tutarli":true}\n')
    with pytest.raises(GirdiHatasi):
        g.lemmalari_oku(yol)
    yol.write_bytes(b'{"lemma_id":1,"dalga":0,"tutarli":true}\n\xff')
    with pytest.raises(GirdiHatasi):
        g.lemmalari_oku(yol)
    with pytest.raises(GirdiHatasi):
        g.lemmalari_oku(tmp_path / "yok.jsonl")


# --- secim -------------------------------------------------------------------------------------


def test_tabakali_secim_tekrarlanabilir_ve_orantili() -> None:
    evren = _lemmalar(1000)
    s1, d1 = g.tabakali_sec(evren, 300, 20261112, "tam")
    s2, d2 = g.tabakali_sec(evren, 300, 20261112, "tam")
    assert (s1, d1) == (s2, d2)  # ayni tohum, ayni liste
    assert len(s1) == len({x.lemma_id for x in s1}) == 300
    assert s1 != g.tabakali_sec(evren, 300, 1, "tam")[0]  # baska tohum, baska liste
    assert [x.lemma_id for x in s1] == sorted(x.lemma_id for x in s1)
    # tabaka dagilimi A16'nin `orantili_dagit` islevinin ciktisidir
    assert [int(str(t["secilen"])) for t in d1] == orantili_dagit(
        [int(str(t["evren"])) for t in d1], 300
    )
    secilen = Counter((x.dalga, x.tutarli) for x in s1)
    for t in d1:
        assert secilen[(int(str(t["dalga"])), bool(t["tutarli"]))] == t["secilen"]
    assert sum(int(str(t["evren"])) for t in d1) == 1000


def test_tabakali_secim_tur_tabakaya_girer() -> None:
    evren = [g.Lemma(i, i % 2, True, False, "isim" if i % 3 else "fiil") for i in range(1, 241)]
    secilen, dagilim = g.tabakali_sec(evren, 24, 3, "tam")
    assert len(secilen) == 24
    assert all("tur" in t for t in dagilim) and {t["tur"] for t in dagilim} == {"isim", "fiil"}


def test_tabakali_secim_sinirlari() -> None:
    evren = _lemmalar(10)
    assert g.tabakali_sec(evren, 0, 1, "tam")[0] == []
    assert len(g.tabakali_sec(evren, 10, 1, "tam")[0]) == 10  # evrenin tamami
    with pytest.raises(GirdiHatasi):
        g.tabakali_sec(evren, 11, 1, "tam")
    with pytest.raises(GirdiHatasi):
        g.tabakali_sec(evren, -1, 1, "tam")
    tek_tabaka = [g.Lemma(i, 0, True) for i in range(1, 51)]
    assert len(g.tabakali_sec(tek_tabaka, 7, 1, "tam")[0]) == 7  # tek tabaka


def test_kumeler_ayrik_ve_ikinci_okuma_boyu_kurali() -> None:
    # dalga 0: 100 onayli (tamami), dalga 1: 2000 onayli (300), dalga 2: 4000 onayli (400)
    adet = 20_000
    evren = _lemmalar(adet, onayli_dalga={0: 100, 1: 2000, 2: 4000})
    k = g.kumeleri_sec(evren, 11, 30, 300)
    assert len(k.kalibrasyon) == 30 and len(k.cift) == 300
    assert not {x.lemma_id for x in k.kalibrasyon} & {x.lemma_id for x in k.cift}
    boylar = {int(str(d["dalga"])): int(str(d["secilen"])) for d in k.ikinci_okuma_dalgalari}
    assert boylar == {0: 100, 1: 300, 2: 400}
    sayac = Counter(x.dalga for x, _ in k.ikinci_okuma)
    assert dict(sayac) == boylar
    assert all(x.onayli for x, _ in k.ikinci_okuma)
    assert {(x.dalga, e) for x, e in k.ikinci_okuma} == {(0, 100), (1, 2000), (2, 4000)}
    with pytest.raises(GirdiHatasi):
        g.kumeleri_sec(_lemmalar(100), 1, 30, 300)  # 330 > 100


# --- gloss-sample komutu -----------------------------------------------------------------------


def test_sample_dosyalari_ve_icerigi(ortam: Path) -> None:
    girdi = _jsonl_yaz(ortam / "l.jsonl", _lemmalar(1000, onayli_dalga={1: 400, 2: 50}))
    assert _sample(ortam, girdi) == cikis.BASARILI
    r = _rapor_klasoru(ortam)
    kalibrasyon = _satirlar(_tek(r, "*-kalibrasyon.jsonl"))
    kappa = _satirlar(_tek(r, "*-kappa.jsonl"))
    okuma = _satirlar(_tek(r, "*-ikinci-okuma.jsonl"))
    ozet = json.loads(_tek(r, "*-gloss-sample.json").read_bytes())
    assert len(kalibrasyon) == 30 and len(kappa) == 300
    assert {tuple(sorted(x)) for x in kappa} == {
        ("dalga", "degerlendirici_1", "degerlendirici_2", "lemma_id")
    }
    assert all(x["degerlendirici_1"] is None and x["degerlendirici_2"] is None for x in kappa)
    assert not {x["lemma_id"] for x in kalibrasyon} & {x["lemma_id"] for x in kappa}
    # dalga 1'de yalniz 250 lemma var (onayli 250), dalga 2'de 50: ikisi de evrenin tamami
    assert Counter(x["dalga"] for x in okuma) == {1: 250, 2: 50}
    assert all(x["karar"] is None for x in okuma)
    assert ozet["cift_degerlendirme"]["n"] == 300
    assert ozet["ikinci_okuma"]["n"] == len(okuma)


def test_sample_ikinci_okuma_dalga_boylari(ortam: Path) -> None:
    # dalga 1: 250 lemmadan 120 onayli -> tamami (120); dalga 2: 250 lemmadan 250 onayli
    evren = _lemmalar(1000, onayli_dalga={1: 120, 2: 250})
    girdi = _jsonl_yaz(ortam / "l.jsonl", evren)
    _sample(ortam, girdi)
    okuma = _satirlar(_tek(_rapor_klasoru(ortam), "*-ikinci-okuma.jsonl"))
    assert Counter(x["dalga"] for x in okuma) == {1: 120, 2: 250}
    assert {(x["dalga"], x["evren"]) for x in okuma} == {(1, 120), (2, 250)}


def test_sample_ayni_tohum_ayni_sablon_baska_tohum_baska(ortam: Path, tmp_path: Path) -> None:
    girdi = _jsonl_yaz(ortam / "l.jsonl", _lemmalar(1000))
    _sample(ortam, girdi, tohum=5)
    _sample(ortam, girdi, tohum=5)
    _sample(ortam, girdi, tohum=6)
    dosyalar = sorted(_rapor_klasoru(ortam).glob("*-kappa.jsonl"))
    assert len(dosyalar) == 3
    icerik = [d.read_bytes() for d in dosyalar]
    assert len({*icerik}) == 2  # iki calistirma ayni, biri farkli (run_id sirasi bagimsiz)
    assert Counter(icerik).most_common(1)[0][1] == 2


def test_sample_dry_run_dosya_yazmaz(ortam: Path) -> None:
    girdi = _jsonl_yaz(ortam / "l.jsonl", _lemmalar(1000, onayli_dalga={1: 300}))
    assert _sample(ortam, girdi, dry_run=True) == cikis.BASARILI
    r = _rapor_klasoru(ortam)
    for desen in ("*-kappa.jsonl", "*-kalibrasyon.jsonl", "*-ikinci-okuma.jsonl", "*-gloss-*.json"):
        assert list(r.glob(desen)) == []


def test_sample_onaylisiz_girdide_ikinci_okuma_dosyasi_yok(ortam: Path) -> None:
    girdi = _jsonl_yaz(ortam / "l.jsonl", _lemmalar(400))
    assert _sample(ortam, girdi) == cikis.BASARILI
    assert list(_rapor_klasoru(ortam).glob("*-ikinci-okuma.jsonl")) == []


def test_sample_hata_kodlari(ortam: Path, capsys: pytest.CaptureFixture[str]) -> None:
    kucuk = _jsonl_yaz(ortam / "k.jsonl", _lemmalar(100))
    assert _sample(ortam, kucuk) == cikis.GIRDI_HATASI  # 30 + 300 > 100
    assert _sample(ortam, ortam / "yok.jsonl") == cikis.GIRDI_HATASI
    assert _sample(ortam, kucuk, kalibrasyon_n=-1) == cikis.GIRDI_HATASI
    assert "hata:" in capsys.readouterr().err


def test_sample_ciktisi_yalniz_kimlik_ve_sayi(ortam: Path) -> None:
    girdi = _jsonl_yaz(ortam / "l.jsonl", _lemmalar(1000, onayli_dalga={1: 300}))
    _sample(ortam, girdi)
    for yol in _rapor_klasoru(ortam).glob("*-gloss-sample.json"):
        veri = json.loads(yol.read_bytes())
        assert set(veri) == {
            "tohum",
            "yontem",
            "evren",
            "onayli_evren",
            "kalibrasyon",
            "cift_degerlendirme",
            "ikinci_okuma",
        }


# --- gloss-score komutu ------------------------------------------------------------------------


def _kappa_sablonu(yol: Path, ciftler: list[tuple[str | None, str | None]], **ek: str) -> Path:
    satirlar = []
    for i, (e1, e2) in enumerate(ciftler, start=1):
        satir: dict[str, object] = {
            "lemma_id": i,
            "dalga": 1,
            "degerlendirici_1": e1,
            "degerlendirici_2": e2,
        }
        satir.update(ek)
        satirlar.append(json.dumps(satir))
    yol.write_bytes(("\n".join(satirlar) + "\n").encode("utf-8"))
    return yol


def _okuma_sablonu(yol: Path, dalga: int, evren: int, kararlar: list[str | None]) -> Path:
    satirlar = [
        json.dumps({"lemma_id": 1000 * dalga + i, "dalga": dalga, "evren": evren, "karar": k})
        for i, k in enumerate(kararlar, start=1)
    ]
    yol.write_bytes(("\n".join(satirlar) + "\n").encode("utf-8"))
    return yol


def _skor(tmp_path: Path, **kw: object) -> int:
    return g.komut_gloss_score(
        kappa_sablon=kw.get("kappa_sablon"),  # type: ignore[arg-type]
        ikinci_okuma_sablon=kw.get("ikinci_okuma_sablon"),  # type: ignore[arg-type]
        dry_run=bool(kw.get("dry_run", False)),
        config=None,
        kok=tmp_path,
    )


def _skor_raporu(tmp_path: Path) -> dict[str, object]:
    return json.loads(_tek(_rapor_klasoru(tmp_path), "*-gloss-score.json").read_bytes())


def test_score_kappa_gecer(ortam: Path) -> None:
    # 10 madde, 5 kabul + 5 red; 9 uyum -> p_o = 0,9; p_e = 0,5 -> kappa = 0,8
    ciftler: list[tuple[str | None, str | None]] = [("kabul", "kabul")] * 5 + [("red", "red")] * 4
    ciftler.append(("red", "kabul"))
    kod = _skor(ortam, kappa_sablon=_kappa_sablonu(ortam / "k.jsonl", ciftler))
    assert kod == cikis.BASARILI
    rapor = _skor_raporu(ortam)
    kappa = rapor["kappa"]
    assert isinstance(kappa, dict)
    assert kappa["kappa"] == pytest.approx(0.8) and kappa["gecti"] is True and kappa["tam"] is True
    assert kappa["uyusmayanlar"] == [
        {"lemma_id": 10, "degerlendirici_1": "red", "degerlendirici_2": "kabul"}
    ]
    assert kappa["capraz"] == {"kabul": {"kabul": 5}, "red": {"kabul": 1, "red": 4}}
    assert rapor["sonuc"] == "gecti"


def test_score_kappa_hedef_tutmaz_cikis_1_rapor_yazilir(ortam: Path) -> None:
    ciftler: list[tuple[str | None, str | None]] = [("kabul", "red"), ("red", "kabul")] * 5
    kod = _skor(ortam, kappa_sablon=_kappa_sablonu(ortam / "k.jsonl", ciftler))
    assert kod == cikis.QA_KALDI
    assert _skor_raporu(ortam)["sonuc"] == "kaldi"


def test_score_eksik_sablon_cikis_1(ortam: Path) -> None:
    ciftler: list[tuple[str | None, str | None]] = [("kabul", "kabul")] * 5 + [("red", "red")] * 4
    ciftler.append(("red", None))
    assert _skor(ortam, kappa_sablon=_kappa_sablonu(ortam / "k.jsonl", ciftler)) == cikis.QA_KALDI
    kappa = _skor_raporu(ortam)["kappa"]
    assert isinstance(kappa, dict)
    assert kappa["eksik"] == 1 and kappa["tam"] is False and kappa["hedef_gecti"] is True
    assert kappa["gecti"] is False


def test_score_bos_sablon_olculmez_cikis_1(ortam: Path) -> None:
    sablon = _kappa_sablonu(ortam / "k.jsonl", [(None, None)] * 3)
    assert _skor(ortam, kappa_sablon=sablon) == cikis.QA_KALDI
    kappa = _skor_raporu(ortam)["kappa"]
    assert isinstance(kappa, dict) and kappa["olculdu"] is False


def test_score_tek_kategori_gecmez(ortam: Path) -> None:
    sablon = _kappa_sablonu(ortam / "k.jsonl", [("kabul", "kabul")] * 6)
    assert _skor(ortam, kappa_sablon=sablon) == cikis.QA_KALDI
    kappa = _skor_raporu(ortam)["kappa"]
    assert isinstance(kappa, dict) and kappa["tek_kategori"] is True


def test_score_ikinci_okuma_dalga_dalga(ortam: Path) -> None:
    # dalga 1: evren 1000 -> 300 gerekir; 300 okundu, 0 yanlis -> gecer
    # dalga 2: evren 1000; 300 okundu, 3 yanlis -> Wilson ust sinir > %2 -> kalir
    d1 = ["dogru"] * 290 + ["kucuk_hata"] * 10
    d2 = ["dogru"] * 297 + ["yanlis"] * 3
    yol = ortam / "o.jsonl"
    satirlar = []
    for dalga, kararlar in ((1, d1), (2, d2)):
        for i, k in enumerate(kararlar, start=1):
            satirlar.append(
                json.dumps(
                    {"lemma_id": 1000 * dalga + i, "dalga": dalga, "evren": 1000, "karar": k}
                )
            )
    yol.write_bytes(("\n".join(satirlar) + "\n").encode("utf-8"))
    assert _skor(ortam, ikinci_okuma_sablon=yol) == cikis.QA_KALDI
    okuma = _skor_raporu(ortam)["ikinci_okuma"]
    assert isinstance(okuma, dict) and okuma["gecti"] is False
    d = {x["dalga"]: x for x in okuma["dalgalar"]}
    assert d[1]["gecti"] is True and d[1]["kucuk_hata"] == 10 and d[1]["yanlis"] == 0
    assert d[2]["gecti"] is False and d[2]["yanlis"] == 3
    assert d[2]["yanlis_lemma_idleri"] == [2298, 2299, 2300]
    assert d[2]["wilson_ust_95"] == pytest.approx(0.02898, abs=1e-5)


def test_score_ikinci_okuma_gecer_cikis_0(ortam: Path) -> None:
    yol = _okuma_sablonu(ortam / "o.jsonl", 1, 1000, ["dogru"] * 300)
    assert _skor(ortam, ikinci_okuma_sablon=yol) == cikis.BASARILI
    assert _skor_raporu(ortam)["sonuc"] == "gecti"


def test_score_okunmamis_satir_yetersiz_orneklem(ortam: Path) -> None:
    yol = _okuma_sablonu(ortam / "o.jsonl", 1, 1000, ["dogru"] * 299 + [None])
    assert _skor(ortam, ikinci_okuma_sablon=yol) == cikis.QA_KALDI
    okuma = _skor_raporu(ortam)["ikinci_okuma"]
    assert isinstance(okuma, dict)
    assert okuma["dalgalar"][0]["eksik"] == 1 and okuma["dalgalar"][0]["yeterli_orneklem"] is False


def test_score_iki_sablon_birlikte(ortam: Path) -> None:
    ciftler: list[tuple[str | None, str | None]] = [("kabul", "kabul")] * 5 + [("red", "red")] * 5
    k = _kappa_sablonu(ortam / "k.jsonl", ciftler)
    o = _okuma_sablonu(ortam / "o.jsonl", 1, 1000, ["dogru"] * 300)
    assert _skor(ortam, kappa_sablon=k, ikinci_okuma_sablon=o) == cikis.BASARILI
    rapor = _skor_raporu(ortam)
    assert "kappa" in rapor and "ikinci_okuma" in rapor


@pytest.mark.parametrize(
    "satir",
    [
        {"lemma_id": 1, "dalga": 1, "degerlendirici_1": "evet", "degerlendirici_2": "red"},
        {"lemma_id": 1, "dalga": 1, "degerlendirici_1": "KABUL", "degerlendirici_2": "red"},
        {"lemma_id": 1, "dalga": 1, "degerlendirici_1": "red", "anlam": "Deneme"},
        {"dalga": 1, "degerlendirici_1": "red"},
    ],
)
def test_score_kappa_sablon_hatalari(ortam: Path, satir: dict[str, object]) -> None:
    yol = ortam / "k.jsonl"
    yol.write_bytes((json.dumps(satir) + "\n").encode("utf-8"))
    assert _skor(ortam, kappa_sablon=yol) == cikis.GIRDI_HATASI


def test_score_okuma_sablon_hatalari(ortam: Path) -> None:
    yol = ortam / "o.jsonl"
    # tanimsiz karar
    yol.write_bytes(b'{"lemma_id":1,"dalga":1,"evren":10,"karar":"hata"}\n')
    assert _skor(ortam, ikinci_okuma_sablon=yol) == cikis.GIRDI_HATASI
    # ayni dalgada tutarsiz evren
    yol.write_bytes(
        b'{"lemma_id":1,"dalga":1,"evren":10,"karar":null}\n'
        b'{"lemma_id":2,"dalga":1,"evren":11,"karar":null}\n'
    )
    assert _skor(ortam, ikinci_okuma_sablon=yol) == cikis.GIRDI_HATASI
    # yinelenen lemma_id
    yol.write_bytes(
        b'{"lemma_id":1,"dalga":1,"evren":10,"karar":null}\n'
        b'{"lemma_id":1,"dalga":1,"evren":10,"karar":null}\n'
    )
    assert _skor(ortam, ikinci_okuma_sablon=yol) == cikis.GIRDI_HATASI
    # evrenden fazla okunan
    yol.write_bytes(
        b'{"lemma_id":1,"dalga":1,"evren":1,"karar":"dogru"}\n'
        b'{"lemma_id":2,"dalga":1,"evren":1,"karar":"dogru"}\n'
    )
    assert _skor(ortam, ikinci_okuma_sablon=yol) == cikis.GIRDI_HATASI


def test_score_sablonsuz_cagri_girdi_hatasi(ortam: Path) -> None:
    assert _skor(ortam) == cikis.GIRDI_HATASI


def test_score_dry_run_rapor_dosyasi_yazmaz(ortam: Path) -> None:
    sablon = _kappa_sablonu(ortam / "k.jsonl", [("kabul", "kabul"), ("red", "red")] * 3)
    assert _skor(ortam, kappa_sablon=sablon, dry_run=True) == cikis.BASARILI
    assert list(_rapor_klasoru(ortam).glob("*-gloss-score.json")) == []


def test_score_raporu_anlam_metni_ve_not_icermez(ortam: Path) -> None:
    # Sablona elle yazilmis serbest not alani raporlara KOPYALANMAZ.
    ciftler: list[tuple[str | None, str | None]] = [("kabul", "kabul"), ("red", "red")] * 3
    k = _kappa_sablonu(ortam / "k.jsonl", ciftler, **{"not": "Deneme anlam notu"})
    o = ortam / "o.jsonl"
    o.write_bytes(
        b'{"lemma_id":1,"dalga":1,"evren":1,"karar":"yanlis","not":"Deneme anlam notu"}\n'
    )
    _skor(ortam, kappa_sablon=k, ikinci_okuma_sablon=o)
    for yol in _rapor_klasoru(ortam).iterdir():
        assert b"Deneme" not in yol.read_bytes(), yol.name
    rapor = _skor_raporu(ortam)
    assert set(rapor) == {"yontem", "kappa", "ikinci_okuma", "sonuc"}
    assert "not" not in json.dumps(rapor)


# --- Typer kaydi -------------------------------------------------------------------------------


def _uygulama() -> typer.Typer:
    app = typer.Typer()
    qa = typer.Typer()
    g.kaydet(qa)
    app.add_typer(qa, name="qa")
    return app


def test_typer_yardim_bicimi_belgeler() -> None:
    sonuc = CliRunner().invoke(_uygulama(), ["qa", "gloss-sample", "--help"])
    assert sonuc.exit_code == 0
    for parca in ("--lemmalar", "lemma_id", "dalga", "tutarli", "--tohum", "--dry-run"):
        assert parca in sonuc.output
    puan = CliRunner().invoke(_uygulama(), ["qa", "gloss-score", "--help"])
    assert puan.exit_code == 0 and "--kappa-sablon" in puan.output


def test_typer_uctan_uca_ve_cikis_kodlari(ortam: Path) -> None:
    girdi = _jsonl_yaz(ortam / "l.jsonl", _lemmalar(1000))
    sonuc = CliRunner().invoke(
        _uygulama(), ["qa", "gloss-sample", "--lemmalar", str(girdi), "--kok", str(ortam)]
    )
    assert sonuc.exit_code == 0, sonuc.output
    hata = CliRunner().invoke(
        _uygulama(), ["qa", "gloss-sample", "--lemmalar", str(ortam / "yok"), "--kok", str(ortam)]
    )
    assert hata.exit_code == cikis.GIRDI_HATASI
    kaldi = _kappa_sablonu(ortam / "k.jsonl", [("kabul", "red"), ("red", "kabul")])
    puan = CliRunner().invoke(
        _uygulama(), ["qa", "gloss-score", "--kappa-sablon", str(kaldi), "--kok", str(ortam)]
    )
    assert puan.exit_code == cikis.QA_KALDI
