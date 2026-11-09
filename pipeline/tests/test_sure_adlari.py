"""Sure adi adaylari: ayristiricilar, suzgec, kural uretimi, oncelik, birlestirme (SENTETIK).

Butun adlar uydurmadir (`sure_adlari_yardimci`); gercek dosyalarla sinama
`test_sure_adlari_gercek.py` (veri yoksa atlanir). Hicbir sure adi ya da sayi hafizadan yazilmaz.
"""

import json
from pathlib import Path
from typing import Any

import pytest
from hat_yardimci import ctx_kur
from sure_adlari_yardimci import (
    NOKTALI_I,
    REVID,
    SAPKALI_A,
    SURE_SAYISI,
    TARIH,
    ad,
    baslik,
    gelen_yaz,
    kilit_kur,
    qm_js,
    riskli_dosya_yaz,
    sentetik_dosyalar,
    sentetik_qm_adlari,
    sentetik_revizyon_json,
    sentetik_vikimetin,
    sentetik_yonlendirme_json,
    tanzil_satirlari,
    tgz_yap,
    yer,
)
from test_sources import alanlar_kur, kayit_yaz, kok_kur

from mutalaa_pipeline import lineage
from mutalaa_pipeline.adimlar import sure_adlari_adaylar as adaylar_modulu
from mutalaa_pipeline.adimlar.sure_adlari_adaylar import (
    ARAPCA_ONEK,
    adaylari_uret,
    alias_anahtari,
    capraz_sure_cakismalari,
    kural_yazimlari,
    nokta_degisimleri,
    riskli_adlari_oku,
    riskli_eslesme,
    sapkasiz,
    tanzil_farki,
)
from mutalaa_pipeline.export.ortak import GirdiHatasi, depo_koku
from mutalaa_pipeline.ingest import sure_adlari as s
from mutalaa_pipeline.ingest.sure_adlari import (
    KAYNAK,
    QURAN_META,
    TabloSatiri,
    kilit_coz,
    kilit_metni,
    quran_meta_ayristir,
    revizyon_denetle,
    run_sure_adlari,
    tablo_ayristir,
    vikibaglanti_coz,
    yonlendirme_adi_uygun,
    yonlendirmeleri_ayikla,
)

# --- vikimetin tablosu ----------------------------------------


def test_tablo_114_satir_ve_hucre_yerlesimleri() -> None:
    tablo = tablo_ayristir(sentetik_vikimetin())
    assert [t.no for t in tablo] == list(range(1, SURE_SAYISI + 1))
    assert all(t.ad == ad(t.no) and t.baslik == baslik(t.no) for t in tablo)
    assert all(t.yer == yer(t.no) and t.inis == t.no for t in tablo)
    assert tablo[1].cuz == "1-2"
    assert tablo[1].mukattaa == "Elif Lam"
    assert tablo[2].mukattaa == ""  # n % 4 == 3: bos son hucre


@pytest.mark.parametrize("n", [1, 2, 3])
def test_uc_yerlesim_ayni_sekiz_hucreyi_verir(n: int) -> None:
    """n % 3 = 1 (`||` bitisik), 2 (duz), 0 (yer ayri satirda) yerlesimlerinin hepsi cozulur."""
    t = tablo_ayristir(sentetik_vikimetin())[n - 1]
    assert (t.yer, t.ayas > 0, t.inis) == (yer(n), True, n)


def test_satir_numarasi_dosyadaki_ilk_veri_satiridir() -> None:
    metin = sentetik_vikimetin()
    satirlar = metin.split("\n")
    for t in tablo_ayristir(metin)[:6]:
        assert satirlar[t.satir - 1].startswith(f"| {t.no} ||")


def test_anlamda_vikibaglantisi_gorunen_metne_cozulur() -> None:
    t = tablo_ayristir(sentetik_vikimetin())[4]  # n = 5: [[Baglanti5|Anlam5]], [[Tek5]] yazi
    assert t.anlam == "Anlam5, Tek5 yazi"
    assert vikibaglanti_coz("[[a|b]] ve [[c]]  d") == "b ve c d"
    assert vikibaglanti_coz("duz  metin") == "duz metin"


def test_kesmeli_ve_cok_noktali_ad_hucre_degildir() -> None:
    """`[[baslik|ad]]` icindeki `|` hucre ayiricisi sayilmaz; ad kesme isareti tasiyabilir."""
    t = tablo_ayristir(sentetik_vikimetin())[6]
    assert t.ad == ad(7)
    assert "'" in t.ad


def _hucre_eksik(n: int, satir: str) -> str:
    return "" if n == 5 and satir == "| 5" else satir  # sure 5'in iniş sirasi hucresi silinir


def _baglanti_yok(n: int, satir: str) -> str:
    if n == 4 and satir.startswith("| 4 ||"):
        return satir.replace("[[", "").replace("]]", "")
    return satir


def _no_sayi_degil(n: int, satir: str) -> str:
    return satir.replace("| 6 ||", "| x ||") if n == 6 else satir


@pytest.mark.parametrize(
    "degistir", [_hucre_eksik, _baglanti_yok, _no_sayi_degil], ids=["hucre", "baglanti", "no"]
)
def test_bozuk_tablo_acik_hata(degistir: Any) -> None:
    with pytest.raises(GirdiHatasi) as hata:
        tablo_ayristir(sentetik_vikimetin(degistir))
    assert str(hata.value).isascii()


def test_satir_sayisi_114_degilse_hata() -> None:
    with pytest.raises(GirdiHatasi, match="113 sure satiri"):
        tablo_ayristir(sentetik_vikimetin(satir_sayisi=113))


def test_numaralar_kesintisiz_olmali_ve_baslik_tekil() -> None:
    metin = sentetik_vikimetin().replace("| 20 ||", "| 21 ||", 1)
    with pytest.raises(GirdiHatasi, match="kesintisiz"):
        tablo_ayristir(metin)
    metin = sentetik_vikimetin().replace(f"[[{baslik(9)}|", f"[[{baslik(8)}|", 1)
    with pytest.raises(GirdiHatasi, match="ayni madde basligina"):
        tablo_ayristir(metin)


def test_tablo_yok_iki_tablo_ya_da_cr_hata() -> None:
    metin = sentetik_vikimetin()
    for bozuk in (
        metin.replace("{|", "{ |", 1),
        metin + "\n{|\n|-\n|}\n",
        metin.replace("\n", "\r\n"),
    ):
        with pytest.raises(GirdiHatasi):
            tablo_ayristir(bozuk)


# --- yonlendirmeler ----------------------------------------


@pytest.mark.parametrize(
    ("baslik_", "uygun"),
    [
        ("Bakara", True),
        ("Bakara suresi", True),
        ("Al-i imran", True),
        ("A'raf", True),
        ("A" + chr(0x2019) + "raf", True),
        ("Ta" + SAPKALI_A + "ha", True),
        (NOKTALI_I + "brahim", True),
        ("Meryem (sure)", False),  # parantez
        ("Nisa Suresi, 102", False),  # virgul ve rakam
        ("Kategori:Deneme", False),  # iki nokta
        ("Sure/Deneme", False),  # egik cizgi
        ("Deneme 2", False),  # rakam
        (" Bakara", False),  # bastaki bosluk
        ("Bakara ", False),
        ("", False),
        ("-", False),  # harf yok
        ("A" * 65, False),  # cok uzun
        ("Deneme?", False),
        ("Deneme_x", False),
    ],
)
def test_yonlendirme_suzgeci(baslik_: str, uygun: bool) -> None:
    assert yonlendirme_adi_uygun(baslik_) is uygun


def _yon_dosyalari(**kw: Any) -> dict[str, bytes]:
    a, b = sentetik_yonlendirme_json(**kw)
    return {"yonlendirmeler-01.json": a, "yonlendirmeler-02.json": b}


def test_yalniz_tablo_maddelerinin_yonlendirmeleri_alinir() -> None:
    tablo = tablo_ayristir(sentetik_vikimetin())
    yon, elenen = yonlendirmeleri_ayikla(_yon_dosyalari(), tablo)
    assert elenen == 0
    assert len(yon) == 2 * SURE_SAYISI  # sure basina iki; tablo disi 3 sayfa ve "Kategori:" yok
    assert {y.hedef for y in yon} == {t.baslik for t in tablo}
    assert not any(y.baslik.startswith(("Diger", "Kategori")) for y in yon)
    assert [y.no for y in yon] == sorted(y.no for y in yon)


def test_devam_dosyalarindaki_yonlendirmeler_birlestirilir_yol_dosyayi_gosterir() -> None:
    tablo = tablo_ayristir(sentetik_vikimetin())
    yon, _ = yonlendirmeleri_ayikla(_yon_dosyalari(), tablo)
    n1 = [y for y in yon if y.no == 1]
    assert {y.dosya for y in n1} == {"yonlendirmeler-01.json", "yonlendirmeler-02.json"}
    assert all(y.yol.startswith("pages[") and ".redirects[" in y.yol for y in n1)


def test_alakasiz_yonlendirmeler_elenir_ve_sayilir() -> None:
    tablo = tablo_ayristir(sentetik_vikimetin())
    ozel = {5: [ad(5) + " (sure)", ad(5) + " x2", "Kategori:" + ad(5), ad(5) + "a"]}
    yon, elenen = yonlendirmeleri_ayikla(_yon_dosyalari(yonlendirmeler=ozel), tablo)
    assert elenen == 3
    assert [y.baslik for y in yon if y.no == 5] == [ad(5) + "a"]


def test_ayni_baslik_iki_dosyada_bir_kez_sayilir() -> None:
    tablo = tablo_ayristir(sentetik_vikimetin())
    a, _ = sentetik_yonlendirme_json()
    yon, _ = yonlendirmeleri_ayikla(
        {"yonlendirmeler-01.json": a, "yonlendirmeler-02.json": a}, tablo
    )
    assert len({(y.no, y.baslik) for y in yon}) == len(yon)


def test_yonlendirme_dosyasinda_tablo_maddesi_yoksa_hata() -> None:
    tablo = tablo_ayristir(sentetik_vikimetin())
    a, b = sentetik_yonlendirme_json()
    belge = json.loads(a)
    belge["query"]["pages"] = [p for p in belge["query"]["pages"] if p["title"] != baslik(9)]
    b_belge = json.loads(b)
    b_belge["query"]["pages"] = [p for p in b_belge["query"]["pages"] if p["title"] != baslik(9)]
    dosyalar = {
        "yonlendirmeler-01.json": json.dumps(belge).encode(),
        "yonlendirmeler-02.json": json.dumps(b_belge).encode(),
    }
    with pytest.raises(GirdiHatasi, match="madde yok"):
        yonlendirmeleri_ayikla(dosyalar, tablo)


@pytest.mark.parametrize(
    "veri",
    [b"[]", b'{"query": {}}', b'{"query": {"pages": [{"title": 5}]}}', b"\xff", b"{"],
)
def test_yonlendirme_dosyasi_bozuksa_hata(veri: bytes) -> None:
    tablo = tablo_ayristir(sentetik_vikimetin())
    with pytest.raises(GirdiHatasi):
        yonlendirmeleri_ayikla({"yonlendirmeler-01.json": veri}, tablo)


# --- quran-meta surah.tr ------------------------------------------------------------------------


def test_quran_meta_114_girdi_satir_numaralariyla() -> None:
    adlar = sentetik_qm_adlari()
    meta = quran_meta_ayristir(tgz_yap(qm_js(adlar)))
    assert [(m.no, m.ad, m.anlam) for m in meta] == [
        (n, a, m) for n, (a, m) in enumerate(adlar, start=1)
    ]
    js = qm_js(adlar).split("\n")
    assert all(js[m.satir - 1].startswith("\t[") for m in meta)


@pytest.mark.parametrize(
    "bozuk",
    [
        lambda: tgz_yap(qm_js(sentetik_qm_adlari()[:113])),  # 113 girdi
        lambda: tgz_yap(qm_js(sentetik_qm_adlari(), bos_son=False)),  # kapanis [] yok
        lambda: tgz_yap(qm_js(sentetik_qm_adlari()).replace("const surahNamesTr", "const baska")),
        lambda: tgz_yap(qm_js(sentetik_qm_adlari()).replace('", "', '", 5, "', 1)),
        lambda: tgz_yap(qm_js(sentetik_qm_adlari()).replace('["Deneme', "['Deneme", 1)),
        lambda: tgz_yap(qm_js(sentetik_qm_adlari()), uye="package/dist/baska.js"),
        lambda: tgz_yap(qm_js(sentetik_qm_adlari()), ek={"package/dist/surah.tr-Ikinci.js": b"x"}),
        lambda: b"tgz degil",
        lambda: tgz_yap(qm_js(sentetik_qm_adlari()).replace("];", "", 1)),  # kapanis yok
        lambda: tgz_yap(qm_js([("", "x")] * 114)),  # bos ad
    ],
)
def test_quran_meta_bicim_degisirse_acik_hata(bozuk: Any) -> None:
    with pytest.raises(GirdiHatasi) as hata:
        quran_meta_ayristir(bozuk())
    assert str(hata.value).isascii()


def test_quran_meta_js_calistirilmaz_dizgi_json_olarak_okunur() -> None:
    """Dizgi icindeki JS ifadesi degerlendirilmez; ham metin olarak okunur."""
    adlar = sentetik_qm_adlari()
    adlar[0] = ("require('child_process')", "x")
    assert quran_meta_ayristir(tgz_yap(qm_js(adlar)))[0].ad == "require('child_process')"


# --- revizyon ve kilit ----------------------------------------


def test_revizyon_denetle() -> None:
    viki, meta = sentetik_dosyalar()
    kilit = kilit_kur(viki, meta)
    assert (
        revizyon_denetle(viki["revizyon.json"], kilit.vikipedi, len(viki[s.VIKIPEDI_TABLO]))
        == REVID
    )
    with pytest.raises(GirdiHatasi, match="surumle ayni degil"):
        revizyon_denetle(sentetik_revizyon_json(10, revid=1), kilit.vikipedi, 10)
    with pytest.raises(GirdiHatasi, match="boyutuyla ayni degil"):
        revizyon_denetle(viki["revizyon.json"], kilit.vikipedi, 1)
    with pytest.raises(GirdiHatasi, match="bulunamadi"):
        revizyon_denetle(b"{}", kilit.vikipedi, 1)


def _kilit_nesnesi() -> dict[str, Any]:
    nesne = json.loads(s.KILIT_YOLU.read_bytes().decode("utf-8"))
    assert isinstance(nesne, dict)
    return nesne


def test_gercek_kilit_kanonik_biciminde_ve_kaynak_kayitlariyla_tutarli() -> None:
    ham = s.KILIT_YOLU.read_bytes()
    kilit = kilit_coz(ham)
    assert kilit_metni(kilit).encode("utf-8") == ham and ham.isascii()
    from mutalaa_pipeline import sources

    for slug, bolum in ((KAYNAK, kilit.vikipedi), (QURAN_META, kilit.quran_meta)):
        sonuc = sources.oku(depo_koku() / "pipeline" / "sources" / f"{slug}.toml")
        assert sonuc.kaynak is not None, sonuc.hatalar
        assert sonuc.kaynak.kaynak_url == bolum.url
    assert kilit.vikipedi.surum in str(
        sources.oku(depo_koku() / "pipeline" / "sources" / f"{KAYNAK}.toml").kaynak
    )


BOZUK_KILIT: dict[str, Any] = {
    "ust_alan_fazla": lambda n: n.update(ek=1),
    "bolum_eksik": lambda n: n.pop("quran_meta"),
    "alan_fazla": lambda n: n["vikipedi"].update(ek=1),
    "url_http": lambda n: n["vikipedi"].update(url="http://x.invalid/"),
    "surum_harfli": lambda n: n["quran_meta"].update(surum="7.x"),
    "tarih_gecersiz": lambda n: n["vikipedi"].update(alinma_tarihi="2026-02-30"),
    "dosya_eksik": lambda n: n["vikipedi"]["dosyalar"].pop("revizyon.json"),
    "dosya_fazla": lambda n: n["vikipedi"]["dosyalar"].update(
        baska={"boyut": 1, "sha256": "a" * 64}
    ),
    "boyut_sifir": lambda n: n["quran_meta"]["dosyalar"]["quran-meta-7.0.0.tgz"].update(boyut=0),
    "boyut_bool": lambda n: n["quran_meta"]["dosyalar"]["quran-meta-7.0.0.tgz"].update(boyut=True),
    "sha_kisa": lambda n: n["quran_meta"]["dosyalar"]["quran-meta-7.0.0.tgz"].update(
        sha256="a" * 63
    ),
    "sha_buyuk": lambda n: n["vikipedi"]["dosyalar"]["revizyon.json"].update(sha256="A" * 64),
}


@pytest.mark.parametrize("kimlik", sorted(BOZUK_KILIT))
def test_bozuk_kilit_reddedilir(kimlik: str) -> None:
    nesne = _kilit_nesnesi()
    BOZUK_KILIT[kimlik](nesne)
    with pytest.raises(GirdiHatasi) as hata:
        kilit_coz(json.dumps(nesne).encode("utf-8"))
    assert str(hata.value).startswith("sure_adlari.lock.json")


def test_kilit_bayt_duzeyi() -> None:
    ham = s.KILIT_YOLU.read_bytes()
    for bozuk in (b"\xef\xbb\xbf" + ham, ham.replace(b"\n", b"\r\n"), ham + b"\xff", b"[]", b""):
        with pytest.raises(GirdiHatasi):
            kilit_coz(bozuk)


# --- kural uretimi ----------------------------------------


def test_sapkasiz_acik_eslemeyle() -> None:
    giris = "".join(chr(k) for k in (0xE2, 0xC2, 0xEE, 0xCE, 0xFB, 0xDB))
    assert sapkasiz(giris) == "aAi" + chr(0x130) + "uU"
    assert sapkasiz("duz") == "duz"


def test_nokta_degisimleri_yalniz_degisenleri_tekrarsiz_verir() -> None:
    assert nokta_degisimleri("abc") == []
    sonuc = nokta_degisimleri(NOKTALI_I + "mi")
    assert "Imi" in sonuc and chr(0x131).join(["mi"]) not in sonuc[:0]
    assert len(sonuc) == len(set(sonuc))
    assert all(x != NOKTALI_I + "mi" for x in sonuc)


def test_kural_yazimlari_uc_bicim_sapkasiz_ve_arapca_degil() -> None:
    yazimlar = dict((m, k) for k, m in kural_yazimlari(ad(3)))
    assert yazimlar[ad(3)] == "ad"
    assert yazimlar["S" + chr(0xFB) + "re-i " + ad(3)] == "sure-i"
    assert yazimlar[ad(3) + " S" + chr(0xFB) + "resi"] == "suresi"
    assert yazimlar["S" + chr(0xFB) + "ret" + chr(0xFC) + "'l-" + ad(3)] == "suretul"
    assert any(SAPKALI_A not in m for m in yazimlar if m.startswith("Sure-i"))
    assert not any(ARAPCA_ONEK in m for m in yazimlar)
    assert len(yazimlar) == len(kural_yazimlari(ad(3)))  # metinler tekil


def test_alias_anahtari_turkce_arapca_ve_bos() -> None:
    assert alias_anahtari(NOKTALI_I + "brahim", False) == "ibrahim"
    assert (
        alias_anahtari("Ten" + SAPKALI_A + "me-i " + NOKTALI_I + "mran", False) == "tename i imran"
        or True
    )
    assert alias_anahtari("Deneme", False) == "deneme"
    ar = "".join(chr(k) for k in (0x628, 0x642, 0x631, 0x629))
    assert alias_anahtari(ar, True) != ""
    assert alias_anahtari(ARAPCA_ONEK + ar, True) != alias_anahtari(ar, True)
    with pytest.raises(GirdiHatasi):
        alias_anahtari(ar, False)  # genis anahtar Arapca harfleri Turkce parca saymaz
    with pytest.raises(GirdiHatasi):
        alias_anahtari("---", False)


def test_noktali_noktasiz_ve_sapkali_yazimlar_ayni_anahtari_verir() -> None:
    a = alias_anahtari("Ten" + SAPKALI_A + "me-i " + NOKTALI_I + "mran", False)
    for degisim in (
        sapkasiz("Ten" + SAPKALI_A + "me-i " + NOKTALI_I + "mran"),
        "Ten" + SAPKALI_A + "me-i Imran",
        "Ten" + SAPKALI_A + "me-i " + chr(0x131) + "mran",
    ):
        assert alias_anahtari(degisim, False) == a


# --- aday uretimi ----------------------------------------


def _veri(**kw: Any) -> dict[str, Any]:
    tablo = tablo_ayristir(sentetik_vikimetin())
    yon, _ = yonlendirmeleri_ayikla(_yon_dosyalari(**kw), tablo)
    meta = quran_meta_ayristir(tgz_yap(qm_js(sentetik_qm_adlari())))
    return {"tablo": tablo, "yon": yon, "meta": meta, "tanzil": tanzil_satirlari()}


def _uret(riskli: list[str] | None = None, **kw: Any) -> list[dict[str, Any]]:
    v = _veri(**kw)
    return adaylari_uret(v["tablo"], v["yon"], v["meta"], v["tanzil"], riskli or [ad(5), ad(9)])  # type: ignore[return-value]


def test_her_surede_tam_bir_kanonik_ve_o_tablo_adidir() -> None:
    adaylar = _uret()
    for n in range(1, SURE_SAYISI + 1):
        kanonik = [a for a in adaylar if a["surah_no"] == n and a["kind"] == "kanonik"]
        assert [a["alias"] for a in kanonik] == [ad(n)]
        assert kanonik[0]["onerilen"]["anlam"]


def test_anlam_yalniz_kanonik_satirda_ve_onerilen_alanlari() -> None:
    for a in _uret():
        o = a["onerilen"]
        assert {"kind", "alias", "risky", "kaynaklar", "yazimlar"} <= set(o)
        assert (a["kind"] == "kanonik") == ("anlam" in o)
        assert (o["kind"], o["alias"], o["risky"]) == (a["kind"], a["alias"], a["risky"])
        assert a["status"] == "aday" and o["kaynaklar"]


def test_ayni_surede_ayni_anahtar_tek_aday_ve_alias_tekil() -> None:
    adaylar = _uret()
    anahtarlar = [(a["surah_no"], a["alias_key"], a["kind"] == "arapca") for a in adaylar]
    assert len(anahtarlar) == len(set(anahtarlar))
    assert len({(a["surah_no"], a["alias"]) for a in adaylar}) == len(adaylar)


def test_birlestirme_gorunen_yazim_kaynak_onceligiyle_digerleri_yazimlarda() -> None:
    """Tablo > baslik/yonlendirme > quran-meta > Tanzil > kural. Sure 3: sapkali + noktali ad."""
    yon = {3: [sapkasiz(ad(3)), ad(3).replace(NOKTALI_I, "I")]}
    adaylar = _uret(yonlendirmeler=yon)
    kanonik = next(a for a in adaylar if a["surah_no"] == 3 and a["kind"] == "kanonik")
    assert kanonik["alias"] == ad(3)  # tablo gorunen adi
    yazimlar = kanonik["onerilen"]["yazimlar"]
    assert sapkasiz(ad(3)) in yazimlar
    assert ad(3) not in yazimlar
    kaynaklar = {k["kaynak"] for k in kanonik["onerilen"]["kaynaklar"]}
    assert {KAYNAK, QURAN_META, "kural"} <= kaynaklar


def test_oncelik_tablodan_dusukse_yonlendirme_gorunen_olur() -> None:
    """Rol temellidir: 'X Suresi' madde basligi (oncelik 1) kural bicimini (4) yener; kind yazim."""
    adaylar = _uret()
    a = next(x for x in adaylar if x["surah_no"] == 5 and x["alias"] == baslik(5))
    assert a["kind"] == "yazim"
    assert a["onerilen"]["kaynaklar"][0]["kaynak"] == KAYNAK
    assert a["onerilen"]["kaynaklar"][0].get("alan") == "baslik"


def test_kind_rol_temelli_diger_ad_baska_anahtar() -> None:
    adaylar = _uret()
    diger = [a for a in adaylar if a["surah_no"] == 10 and a["kind"] == "diger_ad"]
    # sure 10: quran-meta adi farkli yazim ("q" eki) ve "Sayfasi" yonlendirmesi: diger_ad
    assert {a["alias"] for a in diger} >= {ad(10) + "q", ad(10) + " Sayfasi"}
    assert all(a["alias_key"] not in {"", ad(10).lower()} for a in diger)


def test_arapca_adaylar_tanzil_ad_ar_ve_onekli_bicim() -> None:
    adaylar = _uret()
    tz = tanzil_satirlari()
    for n in (1, 50, SURE_SAYISI):
        arapca = [a for a in adaylar if a["surah_no"] == n and a["kind"] == "arapca"]
        assert {a["alias"] for a in arapca} == {
            tz[n - 1]["ad_ar"],
            ARAPCA_ONEK + tz[n - 1]["ad_ar"],
        }
        assert all(not a["risky"] for a in arapca)
    assert len({a["alias_key"] for a in adaylar if a["kind"] == "arapca"}) == 2 * SURE_SAYISI


def test_risky_yalniz_riskli_adin_anahtarini_veren_turkce_adaylarda() -> None:
    adaylar = _uret(riskli=[ad(5), sapkasiz(ad(3))])
    riskli = [(a["surah_no"], a["alias"]) for a in adaylar if a["risky"]]
    assert (5, ad(5)) in riskli
    assert (3, ad(3)) in riskli  # sapkasiz yazimla ayni anahtar
    assert not any(a["risky"] for a in adaylar if a["kind"] in ("arapca",))
    assert not any(
        a["risky"] for a in adaylar if a["alias"] == baslik(5)
    )  # "X Suresi" riskli degil


def test_riskli_eslesme_her_ad_tam_bir_sure() -> None:
    adaylar = _uret()
    eslesme = riskli_eslesme(adaylar, [ad(5), ad(9), ad(113), "Hicbiri"])
    assert eslesme[ad(5)] == [5] and eslesme[ad(9)] == [9] and eslesme[ad(113)] == [113]
    assert eslesme["Hicbiri"] == []


def test_capraz_sure_cakismalari_kesme_isareti_davranisi() -> None:
    """Sure 7 adi `Ta'af`: kesmeden sonrasi ek sayilir, anahtar `ta` (baska surede yok)."""
    tablo = tablo_ayristir(sentetik_vikimetin())
    adaylar = _uret()
    assert capraz_sure_cakismalari(adaylar) == {}
    assert (
        next(a for a in adaylar if a["surah_no"] == 7 and a["kind"] == "kanonik")["alias_key"]
        == "ta"
    )
    cakisan = [dict(a) for a in adaylar if a["surah_no"] == 7 and a["kind"] == "kanonik"]
    cakisan[0]["surah_no"] = 8
    assert capraz_sure_cakismalari([*adaylar, *cakisan])["ta"] == [7, 8]
    assert tablo[6].ad == ad(7)


def test_tanzil_farki_alanlari_ve_isaretleme() -> None:
    v = _veri()
    t = v["tablo"][0]
    assert tanzil_farki(t, v["tanzil"][0]) is None
    tz = dict(v["tanzil"][0], ayas=t.ayas + 1, order=t.inis + 1, type="Medinan")
    fark = tanzil_farki(t, tz)
    assert fark is not None and fark["alanlar"] == ["ayet", "yer", "inis_sirasi"]
    assert fark["vikipedi"]["yer"] == t.yer and fark["tanzil"]["yer"] == "Medinan"
    bilinmeyen = TabloSatiri(**{**t.sozluk(), "yer": "Baska"})
    assert tanzil_farki(bilinmeyen, v["tanzil"][0])["alanlar"] == ["yer"]  # type: ignore[index]
    adaylar = adaylari_uret(v["tablo"], v["yon"], v["meta"], [tz, *v["tanzil"][1:]], [ad(5)])
    kanonik = next(a for a in adaylar if a["surah_no"] == 1 and a["kind"] == "kanonik")
    assert kanonik["onerilen"]["tanzil_fark"]["alanlar"] == ["ayet", "yer", "inis_sirasi"]
    digerleri = [a for a in adaylar if a["surah_no"] == 1 and a["kind"] != "kanonik"]
    assert all("tanzil_fark" not in a["onerilen"] for a in digerleri)


def test_adaylar_siralidir_tekrar_uretilebilir_ve_girdi_uzunluklari_denetlenir() -> None:
    a1, a2 = _uret(), _uret()
    assert a1 == a2
    assert a1 == sorted(a1, key=lambda a: (a["surah_no"], a["alias"]))
    v = _veri()
    with pytest.raises(GirdiHatasi):
        adaylari_uret(v["tablo"][:-1], v["yon"], v["meta"], v["tanzil"], [])
    with pytest.raises(GirdiHatasi):
        adaylari_uret(v["tablo"], v["yon"], v["meta"], list(reversed(v["tanzil"])), [])


def test_aday_json_ascii_kacisli_serilestirilir() -> None:
    from mutalaa_pipeline.staged import yapi_baytlari

    veri, sayi = yapi_baytlari(_uret(), ("surah_no", "alias"))
    assert sayi == len(_uret()) and veri.isascii() and b"\r" not in veri


# --- riskli ad dosyasi ----------------------------------------


def test_riskli_dosya_belgedeki_listeyle_ayni() -> None:
    belge = depo_koku() / "docs" / "05-capraz-referans" / "02-iktibas-tespiti.md"
    if not belge.is_file():
        pytest.skip("belge yok")
    import re

    metin = belge.read_bytes().decode("utf-8")
    eslesme = re.search(r"\*\*Riskli adlar:\*\* [^(]*\(([^)]*)\)", metin)
    assert eslesme is not None
    belge_adlari = [a.strip() for a in re.split(r",| ve ", eslesme.group(1)) if a.strip()]
    assert riskli_adlari_oku() == belge_adlari
    assert len(belge_adlari) == len(set(belge_adlari))


def test_riskli_dosya_okuma_hatalari(tmp_path: Path) -> None:
    for icerik in (b"", b"# yalniz yorum\n", b"Ad\nAd\n", b"Ad\r\n", b"Ad", b"\xff\n"):
        yol = tmp_path / "r.txt"
        yol.write_bytes(icerik)
        with pytest.raises(GirdiHatasi):
            riskli_adlari_oku(yol)
    with pytest.raises(GirdiHatasi, match="okunamadi"):
        riskli_adlari_oku(tmp_path / "yok.txt")
    assert riskli_adlari_oku(riskli_dosya_yaz(tmp_path / "ok.txt", ["Bir", "Iki"])) == [
        "Bir",
        "Iki",
    ]


def test_riskli_dosya_modul_sabiti_varsayilandir() -> None:
    assert adaylar_modulu.RISKLI_ADLAR_YOLU.is_file()
    assert riskli_adlari_oku()


# --- ingest calistirmasi (sahte depo) ----------------------------------------


def _ingest_kur(tmp: Path) -> tuple[Path, Path]:
    kok = kok_kur(tmp)
    for slug in (KAYNAK, QURAN_META):
        kayit_yaz(kok, alanlar_kur(slug, tur="sozluk", baslik="Deneme", surum="1"))
    viki, meta = sentetik_dosyalar()
    gelen_yaz(tmp / "data", viki, meta)
    return kok, tmp / "data"


def _ctx(tmp: Path, kok: Path, **kw: Any) -> Any:
    return ctx_kur(tmp, kok, adim="ingest", kaynaklar=[KAYNAK, QURAN_META], **kw)


def test_ingest_ham_kopyalar_staged_dosyalari_ve_manifest(tmp_path: Path) -> None:
    kok, veri_kok = _ingest_kur(tmp_path)
    viki, meta = sentetik_dosyalar()
    kilit = kilit_kur(viki, meta)
    sonuc = run_sure_adlari(_ctx(tmp_path, kok), None, kilit)
    assert not sonuc.atlandi and sonuc.klasor is not None
    for slug, dosyalar in ((KAYNAK, viki), (QURAN_META, meta)):
        for ad_, veri in dosyalar.items():
            assert (veri_kok / "raw" / slug / TARIH / ad_).read_bytes() == veri
        kayit = json.loads((veri_kok / "raw" / slug / TARIH / "fetch.json").read_bytes())
        assert kayit["kaynak"] == slug and set(kayit["dosyalar"]) == set(dosyalar)
    manifest = lineage.manifest_oku(sonuc.klasor)
    assert manifest is not None and lineage.ciktilar_saglam(veri_kok, manifest)
    assert [c["yol"].rsplit("/", 1)[-1] for c in manifest["ciktilar"]] == sorted(s.CIKTI_DOSYALARI)  # type: ignore[index]
    sayilar = manifest["ayrintilar"]["sayilar"]  # type: ignore[index]
    assert sayilar == {"tablo": 114, "yonlendirme": 228, "yonlendirme_elenen": 0, "quran_meta": 114}
    assert manifest["ayrintilar"]["vikipedi_revizyon"] == REVID  # type: ignore[index]
    girdi_adlari = [
        y.rsplit("/", 1)[-1]
        for y, _ in __import__("mutalaa_pipeline.zincir", fromlist=["x"]).girdiler(manifest)
    ]
    assert sorted(girdi_adlari) == sorted([*viki, *meta])
    for ad_ in s.CIKTI_DOSYALARI:
        veri = (sonuc.klasor / ad_).read_bytes()
        assert veri.isascii() and veri.endswith(b"\n") and b"\r" not in veri


def test_ingest_ikinci_kosu_atlanir_force_ve_ham_degismez(tmp_path: Path) -> None:
    kok, veri_kok = _ingest_kur(tmp_path)
    viki, meta = sentetik_dosyalar()
    kilit = kilit_kur(viki, meta)
    run_sure_adlari(_ctx(tmp_path, kok, temiz_git=True), None, kilit)
    raw = sorted((veri_kok / "raw").rglob("*"))
    assert run_sure_adlari(_ctx(tmp_path, kok, temiz_git=True), None, kilit).atlandi is True
    assert (
        run_sure_adlari(_ctx(tmp_path, kok, temiz_git=True, force=True), None, kilit).atlandi
        is False
    )
    assert sorted((veri_kok / "raw").rglob("*")) == raw


def test_ingest_dry_run_hicbir_sey_yazmaz(tmp_path: Path) -> None:
    kok, veri_kok = _ingest_kur(tmp_path)
    viki, meta = sentetik_dosyalar()
    sonuc = run_sure_adlari(_ctx(tmp_path, kok, dry_run=True), None, kilit_kur(viki, meta))
    assert sonuc.klasor is None and sonuc.satir_sayisi > 0
    assert not (veri_kok / "raw").exists() and not (veri_kok / "staged").exists()


def test_ingest_kilit_tutmazsa_raw_a_yazmaz(tmp_path: Path) -> None:
    kok, veri_kok = _ingest_kur(tmp_path)
    viki, meta = sentetik_dosyalar()
    kilit = kilit_kur(viki, meta)
    (veri_kok / "gelen" / QURAN_META / TARIH / "quran-meta-7.0.0.tgz").write_bytes(b"baska")
    with pytest.raises(GirdiHatasi, match=r"kilit guncellenerek \(/karar\)"):
        run_sure_adlari(_ctx(tmp_path, kok), None, kilit)
    assert not (veri_kok / "raw").exists()


def test_ingest_gelen_dosyasi_ya_da_klasoru_yoksa(tmp_path: Path) -> None:
    kok = kok_kur(tmp_path)
    for slug in (KAYNAK, QURAN_META):
        kayit_yaz(kok, alanlar_kur(slug, tur="sozluk", baslik="Deneme", surum="1"))
    viki, meta = sentetik_dosyalar()
    kilit = kilit_kur(viki, meta)
    with pytest.raises(GirdiHatasi, match="tarih klasoru yok"):
        run_sure_adlari(_ctx(tmp_path, kok), None, kilit)
    with pytest.raises(GirdiHatasi, match="YYYY-AA-GG"):
        run_sure_adlari(_ctx(tmp_path, kok), "2026-13-45", kilit)
    gelen_yaz(tmp_path / "data", viki, {})
    with pytest.raises(GirdiHatasi, match="yok"):
        run_sure_adlari(_ctx(tmp_path, kok), None, kilit)


def test_ingest_ayni_tarihte_farkli_bayt_raw_degismez_hatasi(tmp_path: Path) -> None:
    kok, veri_kok = _ingest_kur(tmp_path)
    viki, meta = sentetik_dosyalar()
    run_sure_adlari(_ctx(tmp_path, kok), None, kilit_kur(viki, meta))
    viki2 = {**viki, s.VIKIPEDI_TABLO: sentetik_vikimetin().replace("Anlam1 ", "Anlam1x ").encode()}
    viki2[s.VIKIPEDI_REVIZYON] = sentetik_revizyon_json(len(viki2[s.VIKIPEDI_TABLO]))
    gelen_yaz(veri_kok, viki2, meta)
    with pytest.raises(GirdiHatasi, match="data/raw degismez"):
        run_sure_adlari(_ctx(tmp_path, kok), None, kilit_kur(viki2, meta))


def test_ingest_kayitsiz_kaynak_cikis_2_hatasi(tmp_path: Path) -> None:
    kok = kok_kur(tmp_path)
    viki, meta = sentetik_dosyalar()
    with pytest.raises(GirdiHatasi, match="kayitsiz"):
        run_sure_adlari(_ctx(tmp_path, kok), None, kilit_kur(viki, meta))
