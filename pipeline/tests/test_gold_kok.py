"""`qa/gold/kok.py`: referans kurulumu, ornekleme, set ve olcum (A18.5; SENTETIK kucuk dunya).

Turkce sozcukler ve kokler ACIKCA sentetiktir ("alfa", "beta" ...); lemmatizer sahtedir; Kur'an,
meal ya da sozluk metni kullanilmaz. Beklenen degerler elle hesaplanmistir.
"""

from pathlib import Path

import pytest

from mutalaa_pipeline.enrich.tr_roots.lemmatize import Analiz, Cozum
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.qa import uyum
from mutalaa_pipeline.qa.gold import kok, setler
from mutalaa_pipeline.qa.gold.kok import Tahmin, kok_olc, kok_seti_kur

KOK_HARFLERI = {1: "k1x", 2: "k2x", 3: "k3x"}


class SahteLemmatizer:
    """`analiz(bicim)`: sozluk disi bicim bilinmiyor; `belirsiz` iki lemmaya iner."""

    def __init__(self) -> None:
        self.sozluk: dict[str, set[str]] = {
            "alfa": {"alfa"},
            "alfalar": {"alfa"},
            "beta": {"beta"},
            "gama": {"gama"},
            "belirsiz": {"alfa", "beta"},
        }

    def analiz(self, bicim: str) -> Analiz:
        return Analiz(frozenset(Cozum(lm, "Noun") for lm in self.sozluk.get(bicim, ())))


def _anlamlar(
    satirlar: list[tuple[str, int | None]],
) -> tuple[list[tuple[str, str]], dict[str, int | None]]:
    anlamlar: list[tuple[str, str]] = []
    koku: dict[str, int | None] = {}
    for i, (metin, root) in enumerate(satirlar):
        capa = f"q:1:{i // 50 + 1}:{i % 50 + 1}"
        anlamlar.append((capa, metin))
        koku[capa] = root
    return anlamlar, koku


def _dunya() -> tuple[list[tuple[str, str]], dict[str, int | None]]:
    s: list[tuple[str, int | None]] = []
    # alfa: 10 kelime = 6 kok1 + 3 kok2 + 1 koksuz -> kok1 (6), kok2 (3): ikisi referans
    s += [("alfa", 1)] * 6 + [("alfalar", 2)] * 3 + [("alfa", None)]
    # beta: 40 kelime: kok1 = 4 (pay tam 0,10: dahil), kok2 = 3 (pay 0,075 < 0,10),
    # kok3 = 2 (destek < 3)
    s += [("beta", 1)] * 4 + [("beta", 2)] * 3 + [("beta", 3)] * 2 + [("beta", None)] * 31
    # gama: 12 kelime, kok1 = 2 (destek < 3): referans yok
    s += [("gama", 1)] * 2 + [("gama", None)] * 10
    # belirsiz parca (iki lemma) ve bilinmeyen parca sayilmaz
    s += [("belirsiz", 1)] * 5 + [("bilinmeyen", 1)] * 5
    return _anlamlar(s)


def test_referans_say_ve_esikler_elle_hesap() -> None:
    anlamlar, koku = _dunya()
    k = kok.referans_say(anlamlar, koku, SahteLemmatizer())
    assert k.toplam["alfa"] == 10 and k.toplam["beta"] == 40 and k.toplam["gama"] == 12
    assert dict(k.destek["alfa"]) == {1: 6, 2: 3}
    assert dict(k.destek["beta"]) == {1: 4, 2: 3, 3: 2}
    assert (k.belirsiz_parca, k.bilinmeyen_parca) == (5, 5)  # sayilmayan parcalar ayri sayilir
    assert k.kelime == len(anlamlar)
    referans = kok.referans_kokleri(k)
    assert referans["alfa"] == {1: 6, 2: 3}
    assert referans["beta"] == {1: 4}  # 4 * 10 >= 40: tam sinirda dahil; kok2 pay < 0,10
    assert referans["gama"] == {}  # destek 2 < 3
    assert "belirsiz" not in referans


def test_referans_esikleri_sabit() -> None:
    assert kok.MIN_DESTEK == 3 and kok.MIN_PAY_PAYDA == 10  # olcumden once sabitlendi
    assert (kok.BANT_YUKSEK, kok.BANT_ORTA, kok.ORNEK_SAYISI) == (100, 10, 400)


def test_bant_sinirlari() -> None:
    assert [kok.bant(n) for n in (3, 9, 10, 99, 100, 5000)] == [
        "dusuk",
        "dusuk",
        "orta",
        "orta",
        "yuksek",
        "yuksek",
    ]


def _evren() -> tuple[dict[str, dict[int, int]], dict[str, int]]:
    referans: dict[str, dict[int, int]] = {}
    toplam: dict[str, int] = {}
    for i in range(50):
        for b, n in (("y", 100 + i), ("o", 10 + i), ("d", 3 + i % 7)):
            ad = f"{b}{i:02d}"
            referans[ad] = {1: n}
            toplam[ad] = n
    return referans, toplam


def test_ornek_sec_tabakali_ve_deterministik() -> None:
    referans, toplam = _evren()
    a = kok.ornek_sec(referans, toplam, 30, 5)
    assert a == kok.ornek_sec(referans, toplam, 30, 5)
    assert a != kok.ornek_sec(referans, toplam, 30, 6)  # tohum degisince secim degisir
    bantlar = [kok.bant(toplam[x]) for x in a]
    assert [bantlar.count(b) for b in kok.BANTLAR] == [10, 10, 10]  # band basina esit pay
    assert len(set(a)) == 30


def test_ornek_sec_band_yetmezse_aktarma_yok_ve_referanssiz_alinmaz() -> None:
    referans = {"y0": {1: 100}, "y1": {1: 101}, "d0": {1: 4}, "d1": {}, "o0": {1: 10}}
    toplam = {"y0": 100, "y1": 101, "d0": 4, "d1": 9, "o0": 10}
    secim = kok.ornek_sec(referans, toplam, 9, 1)  # band basina 3; her bant yetersiz
    assert secim == ["d0", "o0", "y0", "y1"]  # d1 referanssiz; eksik pay baska banda aktarilmaz


def _set_dunyasi(tmp_path: Path) -> kok.KokSeti:
    referans, toplam = _evren()
    return kok_seti_kur(
        referans=referans,
        toplam=toplam,
        kok_harfleri=KOK_HARFLERI,
        qwbw_surum="v-test",
        qac_surum="q-test",
        zeyrek_surum="z-test",
        ozet_sayilar={"kelime": 1},
        tohum=11,
    )


def test_set_manifesti_siniflar_roller_ve_zorunlu_alanlar(tmp_path: Path) -> None:
    seti = _set_dunyasi(tmp_path)
    m = seti.manifest
    assert m["sinif"] == "silver" and m["olcum_turu"] == "dogruluk" and m["set"] == "kok"
    roller = {k["source_id"]: k["rol"] for k in m["kaynak"]}  # type: ignore[attr-defined]
    assert roller == {"quranwbw-tr": "kanit", "qac-morfoloji": "sozluk", "zeyrek": "arac"}
    assert "etimoloji degildir" in str(m["dogrulama_yontemi"])  # ceviri esdegerligi acik yazili
    assert m["min_destek"] == 3 and m["min_pay"] == 0.1
    for o in seti.ornekler:
        setler.ornek_dogrula(o)
        assert o["sinif"] == "silver"
        assert o["kaynak"]["source_id"] == "quranwbw-tr"  # type: ignore[index]
        assert set(o) >= {"tr_lemma", "siklik_bandi", "referans_kokler", "toplam_kelime"}


def test_set_uretimi_ayni_tohumla_ayni_cikti(tmp_path: Path) -> None:
    a, b = _set_dunyasi(tmp_path), _set_dunyasi(tmp_path)
    assert a.manifest == b.manifest and a.ornekler == b.ornekler


def test_set_yaz_oku_gidis_donus(tmp_path: Path) -> None:
    seti = _set_dunyasi(tmp_path)
    klasor = kok.kok_seti_yaz(tmp_path, seti)
    assert (klasor / "referans.jsonl").is_file()
    kok.kok_seti_yaz(tmp_path, seti)  # idempotent
    okunan = kok.kok_seti_oku(tmp_path)
    assert okunan.manifest == seti.manifest
    assert okunan.ornekler == seti.ornekler
    assert set(okunan.evren) == set(seti.evren)
    (klasor / "referans.jsonl").write_bytes(b"{}\n")
    with pytest.raises(GirdiHatasi, match="referans"):
        kok.kok_seti_oku(tmp_path)


# --- olcum ---------------------------------------------------------------------------------------


def _olcum_dunyasi() -> tuple[
    dict[str, object], list[dict[str, object]], dict[str, dict[str, object]]
]:
    """6 ornek: 4 dondurulmus + 2 gelistirme (bolme gercek sha256 ile bulunur)."""
    don = [f"l{i}" for i in range(400) if setler.bolme("kok", f"l{i}", 3) == "dondurulmus"][:4]
    gel = [f"l{i}" for i in range(400) if setler.bolme("kok", f"l{i}", 3) == "gelistirme"][:2]
    kokler = {
        don[0]: ["k1x"],
        don[1]: ["k1x", "k2x"],
        don[2]: ["k2x"],
        don[3]: ["k3x"],
        gel[0]: ["k1x"],
        gel[1]: ["k2x"],
    }
    ornekler: list[dict[str, object]] = []
    for ad, ks in kokler.items():
        ornekler.append(
            {
                "id": ad,
                "sinif": "silver",
                "kaynak": {"source_id": "quranwbw-tr", "surum": "v", "madde": "m"},
                "dogrulama_yontemi": "d",
                "uretim_komutu": "u",
                "tr_lemma": ad,
                "siklik_bandi": "orta",
                "toplam_kelime": 20,
                "referans_kokler": [{"letters_bw": k, "destek": 10 - i} for i, k in enumerate(ks)],
            }
        )
    manifest, _ = setler.set_hazirla(
        "kok",
        {
            "sinif": "silver",
            "olcum_turu": "dogruluk",
            "kaynak": kok.set_kaynaklari("v", "q", "z"),
            "dogrulama_yontemi": "d",
            "uretim_komutu": "u",
            "tohum": 3,
        },
        ornekler,
    )
    evren = {
        str(o["tr_lemma"]): {
            "lemma": o["tr_lemma"],
            "toplam_kelime": 20,
            "referans_kokler": o["referans_kokler"],
        }
        for o in ornekler
    }
    evren["referanssiz1"] = {"lemma": "referanssiz1", "toplam_kelime": 5, "referans_kokler": []}
    return manifest, ornekler, evren


def _tahmin(lemma: str, kok_: str, kaynak: str = "kaikki-tr") -> Tahmin:
    return Tahmin(lemma, kok_, "otomatik", frozenset({kaynak}))


def test_kok_olc_kesinlik_duyarlilik_elle_hesap() -> None:
    manifest, ornekler, evren = _olcum_dunyasi()
    don = [str(o["id"]) for o in ornekler[:4]]
    tahminler = {
        don[0]: _tahmin(don[0], "k1x"),  # dogru
        don[1]: _tahmin(don[1], "k2x"),  # dogru (referans kumesinde)
        don[2]: _tahmin(don[2], "k1x"),  # yanlis
        # don[3]: tahmin yok
        "referanssiz1": _tahmin("referanssiz1", "k1x"),  # referansi yok: olcume katilmaz
        "quranwbw-de-yok": _tahmin("quranwbw-de-yok", "k1x"),
    }
    s = kok_olc(manifest, ornekler, evren, tahminler)
    # dondurulmus: 4 ornek, 3 tahminli, 2 dogru -> kesinlik 2/3; duyarlilik 2/4
    kapi = s.ayrintilar["dondurulmus_kapi_olcumu"]
    assert kapi["ornek"] == 4 and kapi["tahminli"] == 3 and kapi["dogru"] == 2  # type: ignore[index]
    assert s.olculer == {"kesinlik": pytest.approx(2 / 3, abs=1e-6)}  # gerileme yalniz kesinlikte
    bilgi = s.ayrintilar["kapsam_bilgisi"]
    assert bilgi["duyarlilik"] == pytest.approx(0.5, abs=1e-6)  # type: ignore[index]
    assert bilgi["kapi_sarti"] is False and bilgi["bilgi_esigi"] == 0.80  # type: ignore[index]
    assert s.sonuc == "kaldi" and s.esik_sonuclari == {"kesinlik": False}
    assert s.cli_tur == "kok" and s.gate_tur == "kok" and s.set_sinifi == "silver"
    assert s.olculen_ornek == 4
    # referanssiz tahminler ayri sayilir, olcume katilmaz
    kapsam = s.referans_kapsami
    assert kapsam["tahmin_toplam"] == 5
    assert kapsam["tahmin_referansli"] == 3
    assert kapsam["tahmin_referanssiz_olcume_katilmadi"] == 2
    assert kapsam["tahmin_quranwbw_de_gecen_ama_destek_yetersiz"] == 1  # referanssiz1
    assert kapsam["tahmin_quranwbw_de_gecmeyen"] == 1
    assert "etimoloji" in " ".join(s.notlar)  # ceviri esdegerligi notu
    assert "Kur'an'da gecen" in str(kapsam["not"])


def _buyuk_dunya(
    n_ornek: int, n_tahmin: int, n_dogru: int
) -> tuple[
    dict[str, object], list[dict[str, object]], dict[str, dict[str, object]], dict[str, Tahmin]
]:
    """`n_ornek` dondurulmus ornek (hepsinin referansi `k1x`); ilk `n_tahmin` ornek tahminli,
    bunlarin ilk `n_dogru` tanesi dogru (`k1x`), kalani yanlis (`k2x`)."""
    adlar = [f"l{i}" for i in range(4000) if setler.bolme("kok", f"l{i}", 3) == "dondurulmus"]
    adlar = adlar[:n_ornek]
    assert len(adlar) == n_ornek
    ornekler: list[dict[str, object]] = [
        {
            "id": ad,
            "sinif": "silver",
            "kaynak": {"source_id": "quranwbw-tr", "surum": "v", "madde": "m"},
            "dogrulama_yontemi": "d",
            "uretim_komutu": "u",
            "tr_lemma": ad,
            "siklik_bandi": "orta",
            "toplam_kelime": 20,
            "referans_kokler": [{"letters_bw": "k1x", "destek": 10}],
        }
        for ad in adlar
    ]
    manifest, _ = setler.set_hazirla(
        "kok",
        {
            "sinif": "silver",
            "olcum_turu": "dogruluk",
            "kaynak": kok.set_kaynaklari("v", "q", "z"),
            "dogrulama_yontemi": "d",
            "uretim_komutu": "u",
            "tohum": 3,
        },
        ornekler,
    )
    evren = {
        ad: {"lemma": ad, "toplam_kelime": 20, "referans_kokler": ornekler[i]["referans_kokler"]}
        for i, ad in enumerate(adlar)
    }
    tahminler = {
        ad: _tahmin(ad, "k1x" if i < n_dogru else "k2x") for i, ad in enumerate(adlar[:n_tahmin])
    }
    return manifest, ornekler, evren, tahminler


def test_kok_olc_kapi_gecer_orneklem_yeterliyse() -> None:
    manifest, ornekler, evren, tahminler = _buyuk_dunya(40, 40, 40)
    s = kok_olc(manifest, ornekler, evren, tahminler)
    assert s.olculer == {"kesinlik": 1.0}
    assert s.ayrintilar["kapsam_bilgisi"]["duyarlilik"] == 1.0  # type: ignore[index]
    assert s.sonuc == "gecti" and s.kaldi_nedeni is None
    assert s.min_ornek == 30
    assert s.ayrintilar["olculemedi_bilgi"] is None
    assert s.ayrintilar["orneklem_sarti"] == {  # type: ignore[comparison-overlap]
        "min_referansli_tahmin": 30,
        "referansli_tahmin": 40,
        "saglandi": True,
    }


def test_kok_orneklem_sarti_30_alti_kesinlik_1_olsa_bile_kaldi() -> None:
    """Proje sahibi karari (15 Kasim 2026): en az 30 referansli tahmin. 29 tahminin 29'u dogru
    (kesinlik 1,0, esik 0,95) olsa da kapi `kaldi`: kanit yetersiz (Wilson alt siniri ~0,88)."""
    manifest, ornekler, evren, tahminler = _buyuk_dunya(40, 29, 29)
    s = kok_olc(manifest, ornekler, evren, tahminler)
    assert s.olculer == {"kesinlik": 1.0}  # kesinlik yine hesaplanir ve yazilir
    assert s.esik_sonuclari == {"kesinlik": True}  # esik tutar; sart ayrica uygulanir
    assert s.sonuc == "kaldi" and s.kaldi_nedeni == "orneklem_yetersiz"
    bilgi = s.ayrintilar["olculemedi_bilgi"]
    assert bilgi["referansli_tahmin"] == 29 and bilgi["esik"] == 30  # type: ignore[index]
    assert bilgi["kesinlik_bilgi"] == 1.0  # type: ignore[index]
    assert s.ayrintilar["orneklem_sarti"]["saglandi"] is False  # type: ignore[index]


def test_kok_orneklem_siniri_tam_30_yeterli() -> None:
    manifest, ornekler, evren, tahminler = _buyuk_dunya(40, 30, 30)
    s = kok_olc(manifest, ornekler, evren, tahminler)
    assert s.sonuc == "gecti" and s.kaldi_nedeni is None
    assert s.ayrintilar["orneklem_sarti"]["referansli_tahmin"] == 30  # type: ignore[index]


def test_kok_orneklem_yeterli_ama_kesinlik_095_altinda_kaldi() -> None:
    # 30 tahmin, 28 dogru: 0,9333 < 0,95; neden kesinlik (orneklem_yetersiz DEGIL)
    manifest, ornekler, evren, tahminler = _buyuk_dunya(40, 30, 28)
    s = kok_olc(manifest, ornekler, evren, tahminler)
    assert s.sonuc == "kaldi" and s.kaldi_nedeni is None
    assert s.olculer["kesinlik"] == pytest.approx(28 / 30, abs=1e-6)
    assert s.esik_sonuclari == {"kesinlik": False}
    assert s.ayrintilar["olculemedi_bilgi"] is None


def test_kok_orneklem_yeterli_kesinlik_tam_095_gecer() -> None:
    # 40 tahmin, 38 dogru: 0,95 (sinir, esit gecer)
    manifest, ornekler, evren, tahminler = _buyuk_dunya(40, 40, 38)
    s = kok_olc(manifest, ornekler, evren, tahminler)
    assert s.olculer["kesinlik"] == pytest.approx(0.95) and s.sonuc == "gecti"


def test_kok_kapisi_yalniz_kesinlige_baglidir_duyarlilik_sonucu_etkilemez() -> None:
    """Orneklem yeterli (30 referansli tahmin), kesinlik 1,0 ama duyarlilik 0,15 (bilgi esigi
    0,80'in cok altinda): kapi gecer; duyarlilik `kapsam_bilgisi` alaninda bilgi olarak durur.
    Kesinlik esigin altindaysa duyarlilik yuksek olsa da kaldi."""
    manifest, ornekler, evren, tahminler = _buyuk_dunya(200, 30, 30)
    s = kok_olc(manifest, ornekler, evren, tahminler)
    assert s.olculer == {"kesinlik": 1.0}
    assert s.ayrintilar["kapsam_bilgisi"]["duyarlilik"] == pytest.approx(0.15)  # type: ignore[index]
    assert s.ayrintilar["kapsam_bilgisi"]["bilgi_esigi_tuttu"] is False  # type: ignore[index]
    assert s.sonuc == "gecti" and s.esik_sonuclari == {"kesinlik": True}
    # kesinlik 0,5 (duyarlilik 0,15 ayni): kesinlik esigin altinda -> kaldi
    manifest, ornekler, evren, yanlis = _buyuk_dunya(40, 40, 20)
    t = kok_olc(manifest, ornekler, evren, yanlis)
    assert t.sonuc == "kaldi" and t.olculer["kesinlik"] < 0.95


def test_kok_olc_kapi_yalniz_otomatik_onayli_tahminleri_olcer() -> None:
    """K-51 madde 11: editor onayli tahminler kapiya girmez, ayri bilgi alaninda raporlanir."""
    manifest, ornekler, evren = _olcum_dunyasi()
    don = [str(o["id"]) for o in ornekler[:4]]
    otomatik = {
        don[0]: _tahmin(don[0], "k1x"),  # dogru
        don[1]: _tahmin(don[1], "k3x"),  # yanlis
    }
    editor = {
        don[2]: Tahmin(don[2], "k2x", "editor", frozenset({"kaikki-tr"})),  # dogru (editor)
        don[3]: Tahmin(don[3], "k9x", "editor", frozenset({"kaikki-tr"})),  # yanlis (editor)
    }
    sadece = kok_olc(manifest, ornekler, evren, otomatik)
    karisik = kok_olc(manifest, ornekler, evren, {**otomatik, **editor})
    # kapi olculeri ve data_version editor satirlarindan etkilenmez
    assert karisik.olculer == sadece.olculer
    assert karisik.sonuc == sadece.sonuc
    assert karisik.tahmin_ozeti == sadece.tahmin_ozeti
    assert (
        karisik.ayrintilar["dondurulmus_kapi_olcumu"]
        == sadece.ayrintilar["dondurulmus_kapi_olcumu"]
    )
    assert karisik.referans_kapsami["tahmin_toplam"] == 2
    # yalniz otomatik: 2 tahmin, 1 dogru -> kesinlik 0,5 (editor dogrusu kesinligi yukseltmez)
    kapi = karisik.ayrintilar["dondurulmus_kapi_olcumu"]
    assert kapi["tahminli"] == 2 and kapi["dogru"] == 1  # type: ignore[index]
    assert karisik.ayrintilar["kapi_tahmin_onay_yolu"] == "otomatik"
    assert karisik.ayrintilar["tahmin_onay_yolu"] == {"otomatik": 2, "editor": 2}
    bilgi = karisik.ayrintilar["editor_onayli_bilgi"]
    assert bilgi["tahmin"] == 2 and bilgi["referansli"] == 2  # type: ignore[index]
    assert bilgi["referansli_dogru"] == 1 and bilgi["referansli_kesinlik"] == 0.5  # type: ignore[index]
    assert sadece.ayrintilar["editor_onayli_bilgi"]["tahmin"] == 0  # type: ignore[index]
    assert sadece.ayrintilar["editor_onayli_bilgi"]["referansli_kesinlik"] is None  # type: ignore[index]


def test_kok_dongusellik_denetimi_editor_kaynaklarini_kapsamaz() -> None:
    manifest, ornekler, evren = _olcum_dunyasi()
    editor = {"x": Tahmin("x", "k1x", "editor", frozenset({"quranwbw-tr"}))}
    s = kok_olc(manifest, ornekler, evren, editor)  # kapiya girmeyen satir dongusellik sayilmaz
    assert s.uretim_kaynaklari == []


def test_kok_olc_kappa_kaynaklar_arasi_uyum() -> None:
    manifest, ornekler, evren = _olcum_dunyasi()
    don = [str(o["id"]) for o in ornekler[:4]]
    tahminler = {
        don[0]: _tahmin(don[0], "k1x"),  # baskin ref k1x (destek 10): uyum
        don[1]: _tahmin(don[1], "k2x"),  # baskin ref k1x, tahmin k2x: uyumsuz
        don[2]: _tahmin(don[2], "k2x"),  # uyum
        don[3]: _tahmin(don[3], "k3x"),  # uyum
    }
    k = kok_olc(manifest, ornekler, evren, tahminler).ayrintilar["kappa"]
    assert k["n"] == 4  # type: ignore[index]
    beklenen = uyum.cohen_kappa(["k1x", "k2x", "k2x", "k3x"], ["k1x", "k1x", "k2x", "k3x"])
    assert k["kappa"] == pytest.approx(beklenen, abs=1e-6)  # type: ignore[index]
    assert k["kappa"] == k["kappa_uyum_py"]  # type: ignore[index]
    assert "kaynaklar arasi" in k["tur"]  # type: ignore[index]
    assert "insan kappasi degildir" in k["not"]  # type: ignore[index]


def test_kok_olc_kappa_az_ornekte_atlanir() -> None:
    manifest, ornekler, evren = _olcum_dunyasi()
    k = kok_olc(manifest, ornekler, evren, {}).ayrintilar["kappa"]
    assert "atlandi" in k  # type: ignore[operator]


def test_kok_dongusellik_kaikki_ile_olculen_set_hata_yalniz_ad() -> None:
    manifest, ornekler, evren = _olcum_dunyasi()
    # uretim kaniti set kaniti ile ayni kaynaktan ("quranwbw-tr") gelirse olcum yerine hata
    tahminler = {"x": _tahmin("x", "k1x", kaynak="quranwbw-tr")}
    with pytest.raises(GirdiHatasi) as hata:
        kok_olc(manifest, ornekler, evren, tahminler)
    assert "dongusellik" in str(hata.value) and "quranwbw-tr" in str(hata.value)
    # QAC iki tarafta ortak sozluktur (rol sozluk): dongusellik sayilmaz
    kok_olc(manifest, ornekler, evren, {"x": _tahmin("x", "k1x", kaynak="qac-morfoloji")})
    kok_olc(manifest, ornekler, evren, {"x": _tahmin("x", "k1x", kaynak="kaikki-tr")})


def test_daraltma_onerisi_yalniz_gelistirme_parcasi_ve_ozellige_gore_kesinlik() -> None:
    # 300 lemma: ilk 150 "ikisi" (hepsi dogru), son 150 "kok_harfleri" (yarisi dogru). Dondurulmus
    # parca (bolme) hesaba GIRMEZ: sayilar yalniz gelistirme lemmalarindan gelir.
    evren: dict[str, dict[str, object]] = {}
    tahminler: dict[str, Tahmin] = {}
    for i in range(300):
        ad = f"t{i}"
        evren[ad] = {
            "lemma": ad,
            "toplam_kelime": 20,
            "referans_kokler": [{"letters_bw": "k1x", "destek": 5}],
        }
        ikisi = i < 150
        dogru = ikisi or i % 2 == 0
        tahminler[ad] = Tahmin(
            ad,
            "k1x" if dogru else "k2x",
            "otomatik",
            frozenset({"kaikki-tr"}),
            "ikisi" if ikisi else "kok_harfleri",
            frozenset({"tr:noun:etymology_templates.root"}),
        )
    tahminler["referanssiz"] = Tahmin("referanssiz", "k1x", "otomatik", frozenset({"kaikki-tr"}))
    gel = [i for i in range(300) if setler.bolme("kok", f"t{i}") == setler.GELISTIRME]
    gel_ikisi = [i for i in gel if i < 150]
    gel_harf = [i for i in gel if i >= 150]
    assert 0 < len(gel) < 300  # bolme gercekten ikiye ayirir
    sonuc = kok.daraltma_onerisi(tahminler, evren)
    tablo = sonuc["ozellige_gore_kesinlik"]
    assert tablo["qac_eslesme"]["ikisi"] == {  # type: ignore[index]
        "tahmin": len(gel_ikisi),
        "dogru": len(gel_ikisi),
        "kesinlik": 1.0,
    }
    assert tablo["qac_eslesme"]["kok_harfleri"]["tahmin"] == len(gel_harf)  # type: ignore[index]
    assert tablo["qac_eslesme"]["kok_harfleri"]["dogru"] == sum(1 for i in gel_harf if i % 2 == 0)  # type: ignore[index]
    # dondurulmus lemma hicbir grupta sayilmaz
    assert sum(v["tahmin"] for v in tablo["qac_eslesme"].values()) == len(gel)  # type: ignore[union-attr]
    assert tablo["root_sablonu"]["var"]["tahmin"] == len(gel)  # type: ignore[index]  # referanssiz yok
    adaylar = sonuc["esigi_gecen_gruplar_en_az_20_tahmin"]
    assert adaylar == [
        {"ozellik": "qac_eslesme", "deger": "ikisi", "tahmin": len(gel_ikisi), "kesinlik": 1.0}
    ]
    assert "qac_eslesme=ikisi" in str(sonuc["oneri"])
    assert "dondurulmus" in str(sonuc["olcut"])
