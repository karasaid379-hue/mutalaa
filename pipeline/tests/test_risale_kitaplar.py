"""Risale kitap tablosu `shared/data/risale-kitaplar.json` (A20.2a, K-51 madde 1 ve 4).

Bu testler `data/` klasorune BAGLI DEGILDIR (CI'da yok): RNK katalogunun 85 kitap kimligi ve
Diyanet deposunun dosya sayilari asagida sabit olarak tutulur (kimlikler ve sayilar; metin yok);
olcum ve ilk uretim `data/gelen` altindaki dosyalarla betikle yapilmistir.
"""

import json
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any

import pytest

import mutalaa_pipeline.anchor.risale as risale
from mutalaa_pipeline.anchor.risale import (
    KITAPLAR_YOLU,
    Kitap,
    RisaleHatasi,
    dosya_adi_guvenli_mi,
    kitap_haritasi,
    kitap_slug_denetle,
    kitaplar,
    paket_kimligi,
)

# RNK katalogu (shelves.json, 12 Kasim 2026): raf -> kitap kimlikleri (K-51 madde 1: bes raf).
RNK_KATALOG: dict[str, tuple[str, ...]] = {
    "tr": (
        "asamusa", "barla", "emirdag1", "emirdag2", "imankufur", "isarat", "kastamonu",
        "lemalar", "mektubat", "mesnevi", "muhakemat", "sikke", "sozler", "sualar",
        "tarihce", "abed", "ilkeserler",
    ),
    "tr_k": (
        "ayetkubra", "bcevab", "dvan", "elhuccet", "enezerre", "gencreh", "haknurlari",
        "hanimreh", "hasir", "hastalar", "hizmetreh", "hutbe", "ihlas", "ihtiyarlar",
        "ikincisua", "imanhak", "konferans", "ksozler", "latifnukte", "meyve", "miftah",
        "mirackamer", "mirkatsunnet", "muahmed", "mukuran", "munacat", "munazarat",
        "nuralemi", "nurcesme", "nurilkka", "onucsua", "otuzlema", "otuzuc",
        "rahmetsefkat", "ramazan", "sunuhat", "tabiat", "uhuvvet", "vesvese",
        "yirmidortmek", "yirmiuc", "zuhretunnur",
    ),
    "osm": (
        "osm_asamusa", "osm_barla", "osm_emirdag1", "osm_emirdag2", "osm_isarat",
        "osm_kastamonu", "osm_lemalar", "osm_mektubat", "osm_mesnevi", "osm_sozler",
        "osm_sualar", "osm_tarihce",
    ),
    "ar": (
        "ar_asamusa", "ar_imankufur", "ar_isarat", "ar_lemalar", "ar_mektubat",
        "ar_melahik", "ar_mesnevi", "ar_saykal", "ar_sozler", "ar_sualar",
    ),
    "ar_k": ("ar_hasir", "ar_hastalar", "ar_ksozler", "ar_yirmiuc"),
}  # fmt: skip

# Diyanet deposu (a5abc3f3...): txt/ altindaki klasor -> dosya sayisi (15 klasor, 298 dosya).
DIYANET_BUYUK: dict[str, int] = {
    "sozler": 36,
    "mektubat": 39,
    "lemalar": 36,
    "sualar": 18,
    "tarihce-i-hayat": 14,
    "mesnevi-i-nuriye": 16,
    "isaratul-icaz": 27,
    "sikke-i-tasdik-i-gaybi": 8,
    "barla-lahikasi": 20,
    "kastamonu-lahikasi": 13,
    "emirdag-lahikasi-1": 15,
    "emirdag-lahikasi-2": 13,
    "asa-yi-musa": 26,
    "muhakemat": 6,
}
DIYANET_KUCUK: tuple[str, ...] = (
    "divan-i-harb-i-orfi",
    "genclik-rehberi",
    "hanimlar-rehberi",
    "hutbe-i-samiye",
    "isarat",
    "konferans",
    "munazarat",
    "nur-cesmesi",
    "nurun-ilk-kapisi",
    "sunuhat",
    "tuluat",
)
# Ozellikle RNK ile Diyanet arasinda eslesme tuzagi olan kitaplar.
BOLUNEN_RNK = ("tr_k", "sunuhat")
RNK_ONCELIKLI = ("asar-i-bediiyye", "latif-nukteler")  # Diyanet'te bulunma orani < %80

TUM = kitaplar()
HARITA = kitap_haritasi()


def _rnk(k: Kitap) -> tuple[str, str]:
    assert k.rnk is not None
    return (k.rnk.raf, k.rnk.uid)


# ---------------------------------------------------------------------------
# genel yapi


def test_tablo_yolu_depo_icinde_sabit() -> None:
    assert KITAPLAR_YOLU.is_file()
    assert (
        KITAPLAR_YOLU.relative_to(risale.DEPO_KOKU).as_posix() == "shared/data/risale-kitaplar.json"
    )


def test_dosya_bicimi_ve_kanonik_yazim() -> None:
    bayt = KITAPLAR_YOLU.read_bytes()
    assert not bayt.startswith(b"\xef\xbb\xbf"), "BOM var"
    assert b"\r" not in bayt, "CR var"
    assert bayt.endswith(b"\n") and not bayt.endswith(b"\n\n")
    ham = json.loads(bayt.decode("utf-8"))
    # kanonik yazim: girinti 2, ASCII disi karakterler oldugu gibi (U+0307 dahil), son satir sonu
    assert json.dumps(ham, ensure_ascii=False, indent=2) + "\n" == bayt.decode("utf-8")


def test_87_kitap_ve_dagilim() -> None:
    assert len(TUM) == 87
    assert Counter(k.metin_kaynagi for k in TUM) == {"diyanet": 25, "derleme": 34, "rnk": 28}
    assert Counter(k.dil for k in TUM) == {"tr": 61, "ota": 12, "ar": 14}
    assert Counter(k.yon for k in TUM) == {"ltr": 61, "rtl": 26}


def test_hepsi_dogrulanmamis_baslar() -> None:
    assert all(k.dogrulandi is False for k in TUM)


def test_slug_tekil_ve_gecerli() -> None:
    slug_listesi = [k.slug for k in TUM]
    assert len(set(slug_listesi)) == len(slug_listesi)
    paketler = [paket_kimligi(s) for s in slug_listesi]
    assert len(set(paketler)) == len(paketler)
    for slug in slug_listesi:
        assert kitap_slug_denetle(slug) == slug
        assert len(slug) <= 64
        assert slug != "dizin"
        assert slug.isascii() and slug == slug.strip("-")


def test_basliklar_dolu_ve_nfc_ya_da_ayrik_dosya_adi_disinda() -> None:
    for k in TUM:
        assert k.baslik.strip() == k.baslik and k.baslik
        assert unicodedata.normalize("NFC", k.baslik) == k.baslik  # gorunen ad NFC


# ---------------------------------------------------------------------------
# RNK baglantisi: her kitap tam bir satira bagli, yetim yok


def test_rnk_katalogu_85_kitap_bes_raf() -> None:
    assert {raf: len(uidler) for raf, uidler in RNK_KATALOG.items()} == {
        "tr": 17,
        "tr_k": 42,
        "osm": 12,
        "ar": 10,
        "ar_k": 4,
    }
    assert sum(len(u) for u in RNK_KATALOG.values()) == 85


def test_her_rnk_kitabi_baglidir_yetim_yok() -> None:
    beklenen = {(raf, uid) for raf, uidler in RNK_KATALOG.items() for uid in uidler}
    baglanan = {_rnk(k) for k in TUM}
    assert baglanan == beklenen
    assert all(k.rnk is not None for k in TUM)  # her kitabin RNK karsiligi var (K-51 madde 1)


def test_bir_rnk_kitabi_yalniz_bolunen_icin_birden_cok_satira_baglanir() -> None:
    sayac = Counter(_rnk(k) for k in TUM)
    coklu = {anahtar: n for anahtar, n in sayac.items() if n > 1}
    assert coklu == {BOLUNEN_RNK: 3}


def test_sunuhat_tuluat_isarat_uc_slug_tek_rnk_kitabi() -> None:
    uc = [k for k in TUM if _rnk(k) == BOLUNEN_RNK]
    assert sorted(k.slug for k in uc) == ["isarat", "sunuhat", "tuluat"]
    bolunmeler = {k.rnk.bolunme for k in uc if k.rnk is not None}
    assert len(bolunmeler) == 1  # uc satirda ayni bolunme kaydi
    (bolunme,) = bolunmeler
    assert bolunme is not None
    assert [p.slug for p in bolunme.parcalar] == ["sunuhat", "tuluat", "isarat"]
    assert [p.baslangic_sayfasi for p in bolunme.parcalar] == [5, 71, 95]
    assert bolunme.son_sayfa == 111
    assert all(k.dil == "tr" and k.metin_kaynagi == "diyanet" for k in uc)


def test_isarat_tuzagi_rnk_isarat_isaratul_icaz_dir() -> None:
    """RNK `tr/isarat` Isaratul-Icaz'dir; Diyanet'in kucuk eseri `isarat` `tr_k/sunuhat`'tadir."""
    assert _rnk(HARITA["isaratul-icaz"]) == ("tr", "isarat")
    assert _rnk(HARITA["isarat"]) == ("tr_k", "sunuhat")
    assert _rnk(HARITA["isaratul-icaz-osmanlica"]) == ("osm", "osm_isarat")
    assert _rnk(HARITA["isaratul-icaz-arapca"]) == ("ar", "ar_isarat")


def test_ilkeserler_ve_abed_rnk_katalogundadir() -> None:
    assert HARITA["ilk-eserler"].metin_kaynagi == "derleme"
    assert HARITA["asar-i-bediiyye"].metin_kaynagi == "rnk"
    assert HARITA["latif-nukteler"].metin_kaynagi == "rnk"
    assert _rnk(HARITA["ilk-eserler"]) == ("tr", "ilkeserler")
    assert _rnk(HARITA["asar-i-bediiyye"]) == ("tr", "abed")


def test_emirdag_iki_kitap_belge_tablosuna_gore() -> None:
    assert _rnk(HARITA["emirdag-lahikasi-1"]) == ("tr", "emirdag1")
    assert _rnk(HARITA["emirdag-lahikasi-2"]) == ("tr", "emirdag2")
    assert "emirdag-lahikasi" not in HARITA


# ---------------------------------------------------------------------------
# metin kaynagi kurali


def test_diyanet_kitaplari_14_buyuk_ve_11_kucuk() -> None:
    diyanet = [k for k in TUM if k.metin_kaynagi == "diyanet"]
    assert {k.slug for k in diyanet} == set(DIYANET_BUYUK) | set(DIYANET_KUCUK)
    assert all(k.diyanet is not None for k in diyanet)
    assert all(k.dil == "tr" for k in diyanet)


def test_derleme_ve_rnk_kitaplarinin_diyanet_alani_bos() -> None:
    for k in TUM:
        assert (k.diyanet is not None) == (k.metin_kaynagi == "diyanet")


def test_rnk_metin_kaynagi_osmanlica_arapca_ve_iki_turkce() -> None:
    rnk = {k.slug for k in TUM if k.metin_kaynagi == "rnk"}
    assert set(RNK_ONCELIKLI) <= rnk
    assert {k.slug for k in TUM if k.dil != "tr"} == rnk - set(RNK_ONCELIKLI)
    derleme = [k for k in TUM if k.metin_kaynagi == "derleme"]
    assert len(derleme) == 34
    assert all(k.dil == "tr" for k in derleme)


# ---------------------------------------------------------------------------
# Diyanet klasor ve dosya adlari


def test_diyanet_15_klasor_298_dosya() -> None:
    klasorler: dict[str, list[str]] = {}
    for k in TUM:
        if k.diyanet is not None:
            klasorler.setdefault(k.diyanet.klasor, []).extend(k.diyanet.dosyalar)
    assert len(klasorler) == 15
    assert sum(len(v) for v in klasorler.values()) == 298
    assert len({a for v in klasorler.values() for a in v}) == 298  # dosya adlari tekil


def test_diyanet_buyuk_kitap_dosya_sayilari() -> None:
    for slug, adet in DIYANET_BUYUK.items():
        k = HARITA[slug]
        assert k.diyanet is not None
        assert len(k.diyanet.dosyalar) == adet, slug
        assert k.diyanet.klasor[:2].isdigit() and k.diyanet.klasor[2] == " "
        assert all(a.endswith(".txt") for a in k.diyanet.dosyalar)
        # dosya adlari sirali (NN-onekli); zip sirasi korunur
        assert list(k.diyanet.dosyalar) == sorted(k.diyanet.dosyalar)


def test_diyanet_kucuk_kitaplar_tek_klasor_tek_dosya() -> None:
    klasorler = set()
    for slug in DIYANET_KUCUK:
        k = HARITA[slug]
        assert k.diyanet is not None
        assert len(k.diyanet.dosyalar) == 1
        klasorler.add(k.diyanet.klasor)
    assert len(klasorler) == 1
    (klasor,) = klasorler
    assert klasor.startswith("14 ")


def test_diyanet_dosya_adlari_bayt_bayt_ayrik_nokta_korunur() -> None:
    """Dosya adlari NFC'ye cevrilmez: birlesik nokta U+0307 tabloda aynen durur."""
    adlar = [a for k in TUM if k.diyanet is not None for a in k.diyanet.dosyalar]
    ayrik = [a for a in adlar if "̇" in a]
    assert len(ayrik) >= 7
    # en az bir ad NFC'de degisir (I + U+0307 -> U+0130): tabloda NFC'ye cevrilmemis hali durur
    assert any(unicodedata.normalize("NFC", a) != a for a in ayrik)
    ham = KITAPLAR_YOLU.read_bytes().decode("utf-8")
    assert "̇" in ham  # JSON'da kacissiz yazili
    assert "\\u0307" not in ham


def test_dosya_adi_guvenligi() -> None:
    assert dosya_adi_guvenli_mi("01 Sözler")
    for kotu in ("", "..", "../x", "a/b", "/etc", "C:x", "a\\b", "a\x00b"):
        assert not dosya_adi_guvenli_mi(kotu), kotu
    for k in TUM:
        if k.diyanet is not None:
            assert dosya_adi_guvenli_mi(k.diyanet.klasor)
            assert all(dosya_adi_guvenli_mi(a) for a in k.diyanet.dosyalar)


# ---------------------------------------------------------------------------
# dil, yon ve slug ekleri (K-51 madde 4)


def test_dil_yon_slug_eki_ve_raf() -> None:
    for k in TUM:
        assert k.rnk is not None
        if k.dil == "tr":
            assert k.yon == "ltr" and k.rnk.raf in {"tr", "tr_k"}
            assert not k.slug.endswith(("-osmanlica", "-arapca"))
        elif k.dil == "ota":
            assert k.yon == "rtl" and k.rnk.raf == "osm"
            assert k.slug.endswith("-osmanlica")
        else:
            assert k.yon == "rtl" and k.rnk.raf in {"ar", "ar_k"}
            assert k.slug.endswith("-arapca")


def test_osmanlica_ve_arapca_slug_turkce_slug_artı_ek() -> None:
    ozel = {"melahik-arapca", "saykalul-islam-arapca"}  # Turkce karsiligi olmayan (slug onerisi)
    for k in TUM:
        if k.dil == "tr" or k.slug in ozel:
            continue
        ek = "-osmanlica" if k.dil == "ota" else "-arapca"
        taban = k.slug[: -len(ek)]
        assert taban in HARITA and HARITA[taban].dil == "tr", k.slug
        assert HARITA[taban].rnk is not None
        assert k.rnk is not None
        # RNK uid'si taban kitabin uid'sinin onekli hali (osm_ / ar_)
        onek = "osm_" if k.dil == "ota" else "ar_"
        assert k.rnk.uid == onek + HARITA[taban].rnk.uid or taban == "isaratul-icaz"
    assert ozel <= {k.slug for k in TUM}


# ---------------------------------------------------------------------------
# belgedeki adlar (Risale hazirligi kitap tablosu ve kucuk kitaplar)


def test_belge_tablosundaki_slug_listesi_tabloda() -> None:
    belge = [
        "sozler", "mektubat", "lemalar", "sualar", "mesnevi-i-nuriye", "isaratul-icaz",
        "muhakemat", "asa-yi-musa", "barla-lahikasi", "kastamonu-lahikasi",
        "emirdag-lahikasi-1", "emirdag-lahikasi-2", "tarihce-i-hayat", "sikke-i-tasdik-i-gaybi",
        "divan-i-harb-i-orfi", "genclik-rehberi", "hanimlar-rehberi", "hutbe-i-samiye",
        "isarat", "konferans", "munazarat", "nur-cesmesi", "nurun-ilk-kapisi", "sunuhat",
        "tuluat",
        "sozler-arapca", "mesnevi-i-nuriye-arapca", "saykalul-islam-arapca",
        "sozler-osmanlica",
    ]  # fmt: skip
    assert [s for s in belge if s not in HARITA] == []


def test_uretilen_slug_ornekleri() -> None:
    assert HARITA["iman-ve-kufur-muvazeneleri"].dil == "tr"
    assert HARITA["hasir-risalesi"].metin_kaynagi == "derleme"
    assert HARITA["hasir-risalesi-arapca"].rnk is not None


# ---------------------------------------------------------------------------
# yukleyici sertligi (veriden bagimsiz sentetik tablolar)


def _satir(**degisen: Any) -> dict[str, Any]:
    satir: dict[str, Any] = {
        "slug": "test-kitap",
        "baslik": "Deneme Kitap",
        "dil": "tr",
        "yon": "ltr",
        "metin_kaynagi": "derleme",
        "diyanet": None,
        "rnk": {"raf": "tr_k", "uid": "deneme", "ad": "Deneme Kitap"},
        "dogrulandi": False,
    }
    satir.update(degisen)
    return satir


def _yukle(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, tablo: Any) -> tuple[Kitap, ...]:
    monkeypatch.setattr(risale, "DEPO_KOKU", tmp_path)
    yol = tmp_path / "tablo.json"
    yol.write_text(json.dumps(tablo), encoding="utf-8", newline="\n")
    return kitaplar(yol)


def _hata(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, tablo: Any) -> RisaleHatasi:
    with pytest.raises(RisaleHatasi) as hata:
        _yukle(tmp_path, monkeypatch, tablo)
    return hata.value


def test_yukleyici_gecerli_sentetik_tablo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    sonuc = _yukle(tmp_path, monkeypatch, {"surum": 1, "kitaplar": [_satir()]})
    assert [k.slug for k in sonuc] == ["test-kitap"]
    assert sonuc[0].paket_kimligi == "risale-test-kitap"


def test_yukleyici_depo_disi_yolu_reddeder(tmp_path: Path) -> None:
    yol = tmp_path / "tablo.json"
    yol.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="depo kokunun disinda"):
        kitaplar(yol)


@pytest.mark.parametrize(
    ("ad", "degisim"),
    [
        ("dizin", {"slug": "dizin"}),
        ("buyuk-harf", {"slug": "Kitap"}),
        ("p-adi", {"slug": "p4"}),
        ("uzun", {"slug": "a" * 65}),
        ("yon", {"yon": "rtl"}),
        ("dil", {"dil": "fr"}),
        ("kaynak", {"metin_kaynagi": "baska"}),
        ("ek-eksik", {"dil": "ota", "yon": "rtl", "metin_kaynagi": "rnk"}),
        ("ota-diyanet-kaynakli", {"slug": "x-osmanlica", "dil": "ota", "yon": "rtl"}),
        ("diyanet-alani-yok", {"metin_kaynagi": "diyanet"}),
        ("diyanet-alani-fazla", {"diyanet": {"klasor": "01 K", "dosyalar": ["a.txt"]}}),
        ("rnk-yok", {"rnk": None}),
        ("raf-bilinmiyor", {"rnk": {"raf": "evr", "uid": "kuran", "ad": "x"}}),
        ("raf-dille-uyumsuz", {"rnk": {"raf": "osm", "uid": "osm_x", "ad": "x"}}),
        ("rnk-fazla-alan", {"rnk": {"raf": "tr", "uid": "x", "ad": "x", "asd": 1}}),
        ("dogrulandi-sayi", {"dogrulandi": 0}),
        ("baslik-bos", {"baslik": ""}),
        ("fazla-alan", {"not": "x"}),
    ],
)
def test_yukleyici_gecersiz_satiri_reddeder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, ad: str, degisim: dict[str, Any]
) -> None:
    assert ad  # parametre kimligi
    _hata(tmp_path, monkeypatch, {"surum": 1, "kitaplar": [_satir(**degisim)]})


def test_yukleyici_guvensiz_diyanet_adini_reddeder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for kotu in ("../x.txt", "a/b.txt", "C:x.txt", "/mutlak.txt"):
        satir = _satir(metin_kaynagi="diyanet", diyanet={"klasor": "01 K", "dosyalar": [kotu]})
        assert "guvensiz" in str(_hata(tmp_path, monkeypatch, {"surum": 1, "kitaplar": [satir]}))


def test_yukleyici_yinelenen_slug_ve_anahtar(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ayni = {"surum": 1, "kitaplar": [_satir(), _satir()]}
    assert "yinelenen slug" in str(_hata(tmp_path, monkeypatch, ayni))
    monkeypatch.setattr(risale, "DEPO_KOKU", tmp_path)
    yol = tmp_path / "t.json"
    yol.write_text('{"surum": 1, "surum": 1, "kitaplar": []}', encoding="utf-8")
    with pytest.raises(RisaleHatasi, match="yinelenen anahtar"):
        kitaplar(yol)


def test_yukleyici_surum_ve_bos_liste(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _hata(tmp_path, monkeypatch, {"surum": 2, "kitaplar": [_satir()]})
    _hata(tmp_path, monkeypatch, {"surum": 1, "kitaplar": []})
    _hata(tmp_path, monkeypatch, {"surum": 1})
    _hata(tmp_path, monkeypatch, [])


def test_yukleyici_bolunme_kendi_slugini_icermeli(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bolunme = {
        "son_sayfa": 10,
        "parcalar": [
            {"slug": "a-kitap", "baslangic_sayfasi": 1},
            {"slug": "b-kitap", "baslangic_sayfasi": 5},
        ],
    }
    satir = _satir(rnk={"raf": "tr_k", "uid": "deneme", "ad": "x", "bolunme": bolunme})
    assert "kendi slug" in str(_hata(tmp_path, monkeypatch, {"surum": 1, "kitaplar": [satir]}))
    iyi = _satir(
        slug="a-kitap", rnk={"raf": "tr_k", "uid": "deneme", "ad": "x", "bolunme": bolunme}
    )
    sonuc = _yukle(tmp_path, monkeypatch, {"surum": 1, "kitaplar": [iyi]})
    assert sonuc[0].rnk is not None and sonuc[0].rnk.bolunme is not None
    # sayfalar artan olmali
    bolunme["parcalar"][1]["baslangic_sayfasi"] = 1  # type: ignore[index]
    _hata(tmp_path, monkeypatch, {"surum": 1, "kitaplar": [iyi]})
