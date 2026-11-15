# ruff: noqa: RUF001
"""`qa/gold/sentetik.py`: sentetik atif ve iktibas seti ile motor olcumu (A18.5).

Dunya ACIKCA sentetiktir: 3 sure x 20 ayet, kelimeler Arapca harflerden kurala bagli uretilen
anlamsiz uc harfli dizilerdir (`kelime(i)`); Kur'an metni yoktur. Motor sahte cikti ile
beslenir (gercek motor `test_citations_*` testlerinde); burada set kurulumu ve olcum sinanir.
"""

from types import SimpleNamespace
from typing import cast

import pytest

from mutalaa_pipeline.enrich.citations.diziler import arapca_diziler
from mutalaa_pipeline.enrich.citations.iktibas import AdayHat, MotorGirdisi
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.qa.gold import sentetik, setler
from mutalaa_pipeline.qa.gold.sentetik import Korpus, OrnekCikti

_HARFLER = [chr(c) for c in (0x0628, *range(0x062A, 0x0639), 0x0639, 0x063A)]
TEKRAR_AYETLERI = (5, 12, 19, 27, 33, 41)  # ayni 4 kelimeyi tasiyan ayetler (kalip)


def kelime(i: int) -> str:
    n = len(_HARFLER)
    return _HARFLER[i % n] + _HARFLER[(i // n) % n] + _HARFLER[(i // (n * n)) % n]


def korpus_kur() -> Korpus:
    capalar: list[str] = []
    kelimeler: list[list[str]] = []
    for j in range(60):
        sure, ayet = j // 20 + 1, j % 20 + 1
        capalar.append(f"q:{sure}:{ayet}")
        kel = [kelime(j * 30 + t) for t in range(6 + (j * 5) % 7)]  # 6..12 kelime
        if j in TEKRAR_AYETLERI:
            kel[2:6] = [kelime(3000 + t) for t in range(4)]
        kelimeler.append(kel)
    metin = [" ".join(k) for k in kelimeler]
    ofsetler: list[list[tuple[int, int]]] = []
    for k in kelimeler:
        o: list[tuple[int, int]] = []
        konum = 0
        for w in k:
            o.append((konum, konum + len(w)))
            konum += len(w) + 1
        ofsetler.append(o)
    return Korpus(
        capalar,
        kelimeler,
        metin,
        ofsetler,
        list(metin),
        {1: 20, 2: 20, 3: 20},
        {1: "Sure-bir", 2: "Sure-iki", 3: "Sure-uc"},
    )


ADETLER_KUCUK = {**dict.fromkeys(sentetik.ADETLER, 14), "tekrarli_kalip": 1}  # toyda tek kalip var


def _uret(tohum: int = 5) -> list[dict[str, object]]:
    return sentetik.uret(korpus_kur(), "t1", "t2", tohum, ADETLER_KUCUK, 3)


# --- korpus ve gecerli hedefler ------------------------------------------------------------------


def test_gecerli_hedefler_tekrarli_dizi_butun_ayetleri_verir() -> None:
    k = korpus_kur()
    dizi = k.norm[5][2:6]
    hedefler = sentetik.gecerli_hedefler(k, dizi, 5)
    assert hedefler == [k.capalar[a] for a in TEKRAR_AYETLERI]  # sirali, kaynak dahil
    tek = sentetik.gecerli_hedefler(k, k.norm[7][1:5], 7)
    assert tek == [k.capalar[7]]  # tekil dizi: yalniz kaynak ayet


def test_gecerli_hedefler_kaynak_ayet_her_zaman_dahil() -> None:
    k = korpus_kur()
    assert sentetik.gecerli_hedefler(k, ["eslesmeyen"], 9) == [k.capalar[9]]


def test_hareke_sil_yalniz_birlesen_isaretleri_siler() -> None:
    assert sentetik.hareke_sil("بَبّ ت") == "بب ت"
    assert sentetik.hareke_sil("deneme 12") == "deneme 12"


# --- atif bicimleri ------------------------------------------------------------------------------


def test_atif_dizgesi_bicimleri_ve_hedefler() -> None:
    k = korpus_kur()
    assert sentetik.atif_dizgesi(k, "parantez_sayi", 2, 7, None) == ("(2:7)", [7])
    assert sentetik.atif_dizgesi(k, "koseli_sayi", 2, 7, None) == ("[2/7]", [7])
    assert sentetik.atif_dizgesi(k, "aralik_sayi", 2, 7, 9) == ("(2:7-9)", [7, 8, 9])
    assert sentetik.atif_dizgesi(k, "parantez_ad", 2, 7, None) == ("(Sure-iki Sûresi, 7)", [7])
    assert sentetik.atif_dizgesi(k, "ad_iki_nokta", 3, 4, None) == ("Sure-uc: 4", [4])
    assert sentetik.atif_dizgesi(k, "sure_i_ad", 1, 4, None) == ("Sûre-i Sure-bir, 4", [4])
    assert sentetik.atif_dizgesi(k, "ad_sayi_bolu", 3, 4, None) == ("Sure-uc 3/4", [4])
    assert sentetik.atif_dizgesi(k, "sira_sayisi", 3, 4, None) == (
        "Sure-uc Sûresinin 4. âyeti",
        [4],
    )
    assert sentetik.atif_dizgesi(k, "liste_ad", 3, 4, 6) == ("Sure-uc, 4, 6", [4, 6])
    k.sure_adi.pop(2)
    assert sentetik.atif_dizgesi(k, "parantez_ad", 2, 7, None) is None  # adi olmayan sure
    assert sentetik.atif_dizgesi(k, "parantez_sayi", 2, 7, None) == ("(2:7)", [7])


# --- set uretimi ---------------------------------------------------------------------------------


def test_uretim_ayni_tohumla_ayni_cikti_tohum_degisince_degisir() -> None:
    assert _uret(5) == _uret(5)
    assert _uret(5) != _uret(6)


def test_tum_kategoriler_zorunlu_alanlar_ve_sinif() -> None:
    ornekler = _uret()
    kategoriler = {str(o["kategori"]) for o in ornekler}
    assert kategoriler == set(sentetik.ADETLER)  # bozulma kategorilerinin hepsi var
    ids = [str(o["id"]) for o in ornekler]
    assert len(ids) == len(set(ids))
    for o in ornekler:
        setler.ornek_dogrula(o)
        assert o["sinif"] == "sentetik"
        assert str(o["paragraf"]).startswith("Deneme paragrafı ")  # sentetik cerceve
    manifest, _ = setler.set_hazirla("atif", sentetik.taslak("t1", "t2"), ornekler)
    assert manifest["sinif"] == "sentetik" and manifest["olcum_turu"] == "motor_testi"
    gelistirme, dondurulmus = manifest["gelistirme_sayisi"], manifest["dondurulmus_sayisi"]
    assert int(str(gelistirme)) + int(str(dondurulmus)) == len(ornekler)
    assert 0.25 < int(str(gelistirme)) / len(ornekler) < 0.55  # ~%40


def test_iktibas_etiketleri_paragraf_ofsetleriyle_tutarli() -> None:
    k = korpus_kur()
    for o in _uret():
        p = str(o["paragraf"])
        for g in o["iktibas"]:  # type: ignore[attr-defined]
            parca = p[g["bas"] : g["son"]]
            assert 0 <= g["bas"] < g["son"] <= len(p)
            assert len(parca.split()) == g["kelime"]
            assert g["birincil"] in g["hedefler"]
            i, j = g["birincil_aralik"]
            assert j - i == g["kelime"]
            if o["kategori"] in ("tam_uthmani", "kismi", "ardisik", "tekrarli_kalip") or str(
                o["kategori"]
            ).startswith("kisa"):
                a = k.capalar.index(g["birincil"])
                assert parca == " ".join(k.kelimeler[a][i - 1 : j - 1])  # kaynak metnin dilimi
        diziler = arapca_diziler(p)
        if o["iktibas"]:
            assert diziler  # cerceve Arapca harf icermez; dizi gold ofsetiyle ortusur
            assert diziler[0].bas <= o["iktibas"][0]["bas"]  # type: ignore[index]


def test_kategori_ozellikleri() -> None:
    ornekler = {k: [o for o in _uret() if o["kategori"] == k] for k in sentetik.ADETLER}
    for o in ornekler["arapcasiz"]:
        assert o["iktibas"] == [] and o["atif"] == [] and not arapca_diziler(str(o["paragraf"]))
    for o in ornekler["ardisik"]:
        assert len(o["iktibas"]) == 2  # type: ignore[arg-type]
    for o in ornekler["kismi"]:
        assert 4 <= o["iktibas"][0]["kelime"] <= 8  # type: ignore[index]
    for o in ornekler["tekrarli_kalip"]:
        assert len(o["iktibas"][0]["hedefler"]) >= 5  # type: ignore[index]
    for kat in ("kisa_baglamsiz", "kisa_ipucu", "kisa_atifli"):
        for o in ornekler[kat]:
            assert o["iktibas"][0]["kelime"] == 3  # type: ignore[index]
    for o in ornekler["kisa_atifli"]:
        assert len(o["atif"]) == 1  # type: ignore[arg-type]
    for o in ornekler["kisa_ipucu"]:
        assert "âyet-i kerîme" in str(o["paragraf"])
    for o in ornekler["yanlis_atif"]:
        atif = o["atif"][0]  # type: ignore[index]
        assert atif["tutarsiz"] is True
        assert atif["hedef"] not in o["iktibas"][0]["hedefler"]  # type: ignore[index]
    for o in ornekler["atif_ile_alinti"]:
        assert o["atif"][0]["hedef"] == o["iktibas"][0]["birincil"]  # type: ignore[index]
        assert o["atif"][0]["tutarsiz"] is False  # type: ignore[index]
    bicimler = {a["bicim"] for o in ornekler["atif_bicimleri"] for a in o["atif"]}  # type: ignore[attr-defined]
    assert bicimler == {b for b, _ in sentetik.BICIMLER}
    for o in ornekler["atif_bicimleri"]:
        assert o["iktibas"] == []
        for a in o["atif"]:  # type: ignore[attr-defined]
            assert str(o["paragraf"])[a["bas"] : a["son"]].strip() != ""


def test_imlai_havuzu_kelime_sayisi_ayni_ayetlerle_sinirli() -> None:
    k = korpus_kur()
    k.simple[10] = k.simple[10] + " fazla"  # kelime sayisi farkli: imlai havuzundan cikar
    ornekler = sentetik.uret(k, "t1", "t2", 5, {**ADETLER_KUCUK, "imlai": 10}, 3)
    for o in (o for o in ornekler if o["kategori"] == "imlai"):
        assert o["iktibas"][0]["birincil"] != "q:1:11"  # type: ignore[index]


def test_uretim_ilk_ayetleri_ve_kaynak_alani() -> None:
    for o in _uret():
        if o["kategori"] in ("tam_uthmani", "imlai", "hareke_yok"):
            assert not str(o["iktibas"][0]["birincil"]).endswith(":1")  # type: ignore[index]
        kaynaklar = o["kaynak"]
        assert isinstance(kaynaklar, list) and kaynaklar[0]["source_id"]
    imlai = next(o for o in _uret() if o["kategori"] == "imlai")
    assert {x["source_id"] for x in imlai["kaynak"]} == {  # type: ignore[attr-defined]
        "tanzil-uthmani",
        "tanzil-simple-clean",
    }


# --- olcum: sahte motor cikti ile ----------------------------------------------------------------


def _motor() -> MotorGirdisi:
    return cast(MotorGirdisi, SimpleNamespace(ayet_capalari=korpus_kur().capalar))


def _hat(
    tur: str,
    hedef: str,
    bas: int,
    son: int,
    n: int = 0,
    aralik: tuple[int, int] | None = None,
    tutarli: bool | None = None,
) -> AdayHat:
    sira = korpus_kur().capalar.index(hedef)
    kanit: dict[str, object] = {"matched_words": n}
    if tutarli is not None:
        kanit["consistent_quote"] = tutarli
    return AdayHat(tur, "meal:sentetik:1:1", (bas, son), sira, aralik, 1.0, 1.0, kanit)


def _kusursuz(ornekler: list[dict[str, object]]) -> dict[str, OrnekCikti]:
    sonuc: dict[str, OrnekCikti] = {}
    for o in ornekler:
        satirlar: list[AdayHat] = []
        for g in o["iktibas"]:  # type: ignore[attr-defined]
            satirlar.append(
                _hat(
                    "iktibas",
                    g["birincil"],
                    g["bas"],
                    g["son"],
                    g["kelime"],
                    tuple(g["birincil_aralik"]),
                )
            )
        for a in o["atif"]:  # type: ignore[attr-defined]
            satirlar.append(_hat("atif", a["hedef"], a["bas"], a["son"], tutarli=not a["tutarsiz"]))
        sonuc[str(o["id"])] = OrnekCikti(str(o["id"]), satirlar)
    return sonuc


def _manifest(ornekler: list[dict[str, object]]) -> dict[str, object]:
    return setler.set_hazirla("atif", sentetik.taslak("t1", "t2"), ornekler)[0]


def test_kusursuz_motor_iktibas_ve_atif_gecer() -> None:
    ornekler = _uret()
    ciktilar = _kusursuz(ornekler)
    m = _manifest(ornekler)
    i = sentetik.iktibas_olc(m, ornekler, ciktilar, _motor(), ad_sozlugu_etkin=False)
    assert i.olculer == {"uzun_kesinlik": 1.0, "uzun_duyarlilik": 1.0, "kisa_kesinlik": 1.0}
    assert i.sonuc == "gecti" and i.alt_sonuclar == {"kisa": "gecti", "uzun": "gecti"}
    assert i.set_sinifi == "sentetik" and i.gate_tur == "iktibas"
    a = sentetik.atif_olc(m, ornekler, ciktilar, _motor(), ad_sozlugu_etkin=False)
    assert a.olculer["kesinlik"] == 1.0 and a.olculer["duyarlilik"] == 1.0 and a.sonuc == "gecti"
    assert a.ayrintilar["tutarsiz_numara_isaretleme"]["tutarsiz_gold"] > 0  # type: ignore[index]
    assert (
        a.ayrintilar["tutarsiz_numara_isaretleme"]["tutarsiz_gold"]  # type: ignore[index]
        == a.ayrintilar["tutarsiz_numara_isaretleme"]["tutarsiz_isaretlendi"]  # type: ignore[index]
    )
    # hedef kelime araligi: kusursuz motorda hepsi dogru
    aralik = i.ayrintilar["hedef_kelime_araligi_dogru_bilgi"]
    assert aralik["dogru"] == aralik["karsilastirilan"] > 0  # type: ignore[index]


def test_olcum_yalniz_dondurulmus_parcada() -> None:
    ornekler = _uret()
    ciktilar = _kusursuz(ornekler)
    m = _manifest(ornekler)
    don, gel = sentetik.bol("iktibas", ornekler, int(str(m["tohum"])))
    assert len(don) + len(gel) == len(ornekler) and don and gel
    i = sentetik.iktibas_olc(m, ornekler, ciktilar, _motor(), ad_sozlugu_etkin=False)
    assert i.olculen_ornek == len(don)
    # gelistirme parcasini bozmak kapi olcumunu etkilemez (dondurulmus parca ayar icin degil)
    bozuk = dict(ciktilar)
    for o in gel:
        bozuk[str(o["id"])] = OrnekCikti(str(o["id"]), [])
    j = sentetik.iktibas_olc(m, ornekler, bozuk, _motor(), ad_sozlugu_etkin=False)
    assert j.olculer == i.olculer


def test_yanlis_pozitif_arapcasiz_paragrafta_kesinligi_dusurur() -> None:
    ornekler = _uret()
    m = _manifest(ornekler)
    don, _ = sentetik.bol("iktibas", ornekler, int(str(m["tohum"])))
    ciktilar = _kusursuz(ornekler)
    hedef = next(o for o in don if o["kategori"] == "arapcasiz")
    uzun_n = sum(
        1
        for o in don
        for g in o["iktibas"]  # type: ignore[attr-defined]
        if g["kelime"] >= 4
    )
    ciktilar[str(hedef["id"])] = OrnekCikti(
        str(hedef["id"]),
        [_hat("iktibas", "q:1:2", 10, 40, 6)],  # uzun yanlis pozitif
    )
    i = sentetik.iktibas_olc(m, ornekler, ciktilar, _motor(), ad_sozlugu_etkin=False)
    assert i.olculer["uzun_kesinlik"] == pytest.approx(uzun_n / (uzun_n + 1), abs=1e-6)
    assert i.alt_sonuclar["uzun"] == ("gecti" if uzun_n / (uzun_n + 1) >= 0.95 else "kaldi")
    assert i.olculer["uzun_duyarlilik"] == 1.0


def test_kisa_ve_uzun_ayri_degerlendirilir() -> None:
    ornekler = _uret()
    m = _manifest(ornekler)
    don, _ = sentetik.bol("iktibas", ornekler, int(str(m["tohum"])))
    ciktilar = _kusursuz(ornekler)
    kisa = [o for o in don if str(o["kategori"]).startswith("kisa")]
    assert kisa
    # kisa (n < 4) bir yanlis tahmin kisa kesinligi bozar, uzun olcumlere dokunmaz
    ciktilar[str(kisa[0]["id"])].satirlar.append(_hat("iktibas", "q:1:2", 3, 20, 3))
    i = sentetik.iktibas_olc(m, ornekler, ciktilar, _motor(), ad_sozlugu_etkin=False)
    kisa_golds = sum(1 for o in don for g in o["iktibas"] if g["kelime"] < 4)  # type: ignore[attr-defined]
    assert i.olculer["kisa_kesinlik"] == pytest.approx(kisa_golds / (kisa_golds + 1), abs=1e-6)
    assert i.olculer["uzun_kesinlik"] == 1.0 and i.alt_sonuclar["uzun"] == "gecti"
    # kisa kesinlik < 0,85 ise tur kaldi (iktibas gecti yalniz uzun VE kisa gecerse)
    for o in kisa[1:]:
        ciktilar[str(o["id"])].satirlar.append(_hat("iktibas", "q:1:3", 3, 20, 3))
    j = sentetik.iktibas_olc(m, ornekler, ciktilar, _motor(), ad_sozlugu_etkin=False)
    assert j.alt_sonuclar == {"kisa": "kaldi", "uzun": "gecti"} and j.sonuc == "kaldi"


def test_uzun_duyarlilik_dususu_kaldi() -> None:
    ornekler = _uret()
    m = _manifest(ornekler)
    don, _ = sentetik.bol("iktibas", ornekler, int(str(m["tohum"])))
    ciktilar = _kusursuz(ornekler)
    uzunlar = [o for o in don if o["kategori"] in ("tam_uthmani", "imlai", "hareke_yok")]
    for o in uzunlar:  # butun tam alintilari kacir
        ciktilar[str(o["id"])] = OrnekCikti(str(o["id"]), [])
    i = sentetik.iktibas_olc(m, ornekler, ciktilar, _motor(), ad_sozlugu_etkin=False)
    assert i.olculer["uzun_duyarlilik"] < 0.85 and i.alt_sonuclar["uzun"] == "kaldi"
    assert i.sonuc == "kaldi" and i.olculer["uzun_kesinlik"] == 1.0


def test_atif_eksik_ve_fazla_tahmin() -> None:
    ornekler = _uret()
    m = _manifest(ornekler)
    don, _ = sentetik.bol("atif", ornekler, int(str(m["tohum"])))
    ciktilar = _kusursuz(ornekler)
    atifli = [o for o in don if o["atif"]]
    # bir atif kacirilir, bir fazla atif eklenir
    ciktilar[str(atifli[0]["id"])] = OrnekCikti(
        str(atifli[0]["id"]),
        [h for h in ciktilar[str(atifli[0]["id"])].satirlar if h.tur != "atif"],
    )
    ar = next(o for o in don if o["kategori"] == "arapcasiz")
    ciktilar[str(ar["id"])] = OrnekCikti(str(ar["id"]), [_hat("atif", "q:1:2", 40, 46)])
    a = sentetik.atif_olc(m, ornekler, ciktilar, _motor(), ad_sozlugu_etkin=False)
    toplam = sum(len(o["atif"]) for o in don)  # type: ignore[arg-type]
    kacan = len(atifli[0]["atif"])  # type: ignore[arg-type]
    assert a.olculer["duyarlilik"] == pytest.approx((toplam - kacan) / toplam, abs=1e-6)
    assert a.olculer["kesinlik"] == pytest.approx((toplam - kacan) / (toplam - kacan + 1), abs=1e-6)
    assert a.sonuc == "kaldi"  # kesinlik < 0,98


def test_atif_ad_bicimleri_kapaliysa_siniflar_ayri_raporlanir() -> None:
    ornekler = _uret()
    ciktilar = _kusursuz(ornekler)
    for o in ornekler:  # ad tabanli atif tahminleri kacirilir (uretimde onayli takma ad yok)
        ciktilar[str(o["id"])].satirlar = [
            h
            for h in ciktilar[str(o["id"])].satirlar
            if not (h.tur == "atif" and _ad_bicimi(o, h.src_span))
        ]
    a = sentetik.atif_olc(_manifest(ornekler), ornekler, ciktilar, _motor(), ad_sozlugu_etkin=False)
    kirilim = a.ayrintilar["bicim_sinifi_kirilimi_dondurulmus"]
    assert kirilim["sayi"]["duyarlilik"] == 1.0  # type: ignore[index]
    assert kirilim["ad"]["duyarlilik"] == 0.0  # type: ignore[index]
    assert a.olculer["kesinlik"] == 1.0 and a.sonuc == "kaldi"
    assert "kapali" in " ".join(a.notlar)


def _ad_bicimi(o: dict[str, object], span: tuple[int, int]) -> bool:
    return any(
        g["bicim_sinifi"] == "ad" and (g["bas"], g["son"]) == span
        for g in o["atif"]  # type: ignore[attr-defined]
    )


def test_motoru_calistir_birim_basina_cikti_yazmaz() -> None:
    # gercek motor girdisi yok: bos atif/iktibas dunyasi (arapcasiz paragraf, ad sozlugu yok)
    from mutalaa_pipeline.enrich.citations.indeks import EslestirmeIndeksi

    arapcasiz = [o for o in _uret() if o["kategori"] == "arapcasiz"][:3]
    motor = cast(
        MotorGirdisi,
        SimpleNamespace(
            indeksler=cast(list[EslestirmeIndeksi], []),
            ayet_capalari=[],
            ayet_yeri={},
            sozluk=None,
            adlandirilmis=(),
        ),
    )
    ciktilar = sentetik.motoru_calistir(motor, arapcasiz)
    assert [c.ornek_id for c in ciktilar] == [str(o["id"]) for o in arapcasiz]
    assert all(c.satirlar == [] for c in ciktilar)


def test_set_olmadan_olcum_istenirse_hata(tmp_path) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(GirdiHatasi, match="build"):
        setler.set_oku(tmp_path, "atif")


def test_kisa_tahmin_yoksa_kisa_kesinlik_bos_kume_uyarisi() -> None:
    ornekler = _uret()
    ciktilar = _kusursuz(ornekler)
    for c in ciktilar.values():
        c.satirlar = [
            h for h in c.satirlar if not (h.tur == "iktibas" and h.evidence["matched_words"] < 4)
        ]  # type: ignore[operator]
    i = sentetik.iktibas_olc(
        _manifest(ornekler), ornekler, ciktilar, _motor(), ad_sozlugu_etkin=False
    )
    assert i.ayrintilar["kisa_tahmin_sayisi"] == 0
    assert i.olculer["kisa_kesinlik"] == 1.0  # bos kume kurali
    assert any("bos kume" in n and "kanit degildir" in n for n in i.notlar)
    tam = sentetik.iktibas_olc(
        _manifest(ornekler), ornekler, _kusursuz(ornekler), _motor(), ad_sozlugu_etkin=False
    )
    assert tam.ayrintilar["kisa_tahmin_sayisi"] > 0
    assert not any("bos kume" in n for n in tam.notlar)
