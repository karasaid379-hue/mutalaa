# ruff: noqa: RUF001
"""kaikki etimoloji cikarimi, QAC eslemesi ve lemmatizer sarmalayici (A18.2).

Satirlar ACIKCA SENTETIKTIR (uydurma sozcukler, anlamsiz Arapca harf dizileri). Gercek dokum
`tr_roots_gercek` degil; bu dosya yalniz sablon kurallarini sinar. zeyrek gerektiren test
`importorskip` ile atlanabilir.
"""

import gzip
import json
from pathlib import Path

import pytest
from tr_yardimci import (
    ETIMON_BNR,
    ETIMON_SML,
    KOK_AMN,
    KOK_AMN_ELIFLI,
    KOK_BNR,
    KOK_SML,
    QAC_KOKLER,
    QAC_LEMMALAR,
    env_kur,
    etimon_kanit,
    kok_kanit,
)

from mutalaa_pipeline.enrich.tr_roots.eslesme import (
    QacEnvanteri,
    eslestir,
    etimon_anahtari,
    kok_katla,
)
from mutalaa_pipeline.enrich.tr_roots.etimoloji import (
    DIL_OTA,
    DIL_TR,
    KaikkiIndeksi,
    Kanit,
    dokum_oku,
    madde_cikar,
    osmanlica_anahtari,
)
from mutalaa_pipeline.enrich.tr_roots.lemmatize import (
    Cozum,
    ZeyrekLemmatizer,
    _cozumleri_topla,
)
from mutalaa_pipeline.export.ortak import GirdiHatasi


def sablon(ad: str, **args: str) -> dict[str, object]:
    return {"name": ad, "args": dict(args)}


def kayit(*sablonlar: dict[str, object], metin: str = "", pos: str = "noun") -> dict[str, object]:
    return {
        "word": "deneme",
        "lang_code": "tr",
        "pos": pos,
        "etymology_templates": list(sablonlar),
        "etymology_text": metin,
    }


# --- yapisal kanit ---------------------------------------------------------------------------


def test_root_sablonu_arapca_kok_harfleri() -> None:
    m = madde_cikar(kayit(sablon("root", **{"1": "tr", "2": "ar", "3": KOK_BNR})), DIL_TR)
    assert m is not None and m.kanitlar == (kok_kanit(KOK_BNR),)


def test_root_sablonu_ayri_argumanlar_sayisal_sirayla_birlesir() -> None:
    args = {str(i): h for i, h in zip(range(3, 13), "ابتثجحخدذر", strict=True)}
    m = madde_cikar(kayit(sablon("root", **{"1": "tr", "2": "ar"}, **args)), DIL_TR)
    assert m is not None and m.kanitlar[0].deger == " ".join("ابتثجحخدذر")  # 10 harf: 3..12


def test_root_sablonu_baska_dil_kanit_degil() -> None:
    m = madde_cikar(kayit(sablon("root", **{"1": "tr", "2": "fa", "3": KOK_BNR})), DIL_TR)
    assert m is not None and m.kanitlar == ()


@pytest.mark.parametrize(
    "ad", ["bor", "bor+", "lbor", "slbor", "der", "der+", "inh", "inh+", "calque"]
)
def test_arapca_kaynakli_sablon_etimon_kanittir(ad: str) -> None:
    m = madde_cikar(kayit(sablon(ad, **{"1": "tr", "2": "ar", "3": ETIMON_SML})), DIL_TR)
    assert m is not None
    assert m.kanitlar == (Kanit("etimon", f"etymology_templates.{ad}", ETIMON_SML),)


def test_kaynak_dili_arapca_degilse_kanit_degil() -> None:
    m = madde_cikar(kayit(sablon("bor", **{"1": "tr", "2": "fa", "3": ETIMON_SML})), DIL_TR)
    assert m is not None and m.kanitlar == () and m.osmanlica == ()


def test_etimon_degerindeki_ek_bilgi_atilir_ve_arapca_olmayan_atlanir() -> None:
    m = madde_cikar(
        kayit(
            sablon("bor", **{"2": "ar", "3": f"{ETIMON_SML}<t:deneme>"}),
            sablon("bor", **{"2": "ar", "3": "latin"}),
        ),
        DIL_TR,
    )
    assert m is not None and [k.deger for k in m.kanitlar] == [ETIMON_SML]


def test_agac_sablonunda_ar_etimonu_ve_osmanlica_baglantisi() -> None:
    ham = f"ota:{KOK_BNR.replace(' ', '')}\n<ety:uder<ar:{ETIMON_SML}<t:deneme>>>"
    m = madde_cikar(kayit(sablon("ety", **{"1": "tr", "2": ":inh", "3": ham})), DIL_TR)
    assert m is not None
    assert m.kanitlar == (etimon_kanit(ETIMON_SML, "ety"),)
    assert m.osmanlica == (KOK_BNR.replace(" ", ""),)


def test_etymon_sablonu_de_agac_sayilir() -> None:
    m = madde_cikar(kayit(sablon("etymon", **{"3": f"ota:ددد <x> ar:{ETIMON_BNR}"})), DIL_TR)
    assert m is not None and m.kanitlar == (etimon_kanit(ETIMON_BNR, "etymon"),)


def test_agac_baska_dilin_ar_ile_biten_kodu_arapca_sayilmaz() -> None:
    m = madde_cikar(kayit(sablon("ety", **{"3": f"xar:{ETIMON_SML}"})), DIL_TR)
    assert m is not None and m.kanitlar == ()


def test_osmanlica_kaynakli_inh_sablonu_baglanti_uretir() -> None:
    m = madde_cikar(kayit(sablon("inh", **{"1": "tr", "2": "ota", "3": "ددد"})), DIL_TR)
    assert m is not None and m.osmanlica == ("ددد",) and m.kanitlar == ()


def test_serbest_metinde_arabic_yalniz_zayif_bayrak() -> None:
    m = madde_cikar(kayit(metin="from Arabic (deneme)"), DIL_TR)
    assert m is not None and m.zayif and m.kanitlar == () and not m.yapisal


def test_cekim_bicimi_maddesi_sozluk_maddesi_degildir() -> None:
    satir = kayit(sablon("root", **{"2": "ar", "3": KOK_BNR}))
    satir["senses"] = [{"form_of": [{"word": "baska"}]}]
    assert madde_cikar(satir, DIL_TR) is None
    satir["senses"] = [{"form_of": [{"word": "baska"}]}, {"glosses": ["x"]}]
    assert madde_cikar(satir, DIL_TR) is not None


def test_eksik_alanli_satir_atlanir() -> None:
    assert madde_cikar({"word": "x"}, DIL_TR) is None
    assert madde_cikar({"pos": "noun"}, DIL_TR) is None


def test_ayni_sablon_iki_kez_gecerse_tek_kanit() -> None:
    s = sablon("root", **{"2": "ar", "3": KOK_BNR})
    m = madde_cikar(kayit(s, s), DIL_TR)
    assert m is not None and len(m.kanitlar) == 1


def test_osmanlica_anahtari_hareke_ve_uzatma_isaretlerini_siler() -> None:
    assert osmanlica_anahtari(" صَمْل ") == "صمل"
    assert osmanlica_anahtari("ـص") == "ص"


# --- dokum okuma -----------------------------------------------------------------------------


def _dokum_yaz(yol: Path, satirlar: list[dict[str, object]]) -> None:
    veri = "".join(json.dumps(s, ensure_ascii=False) + "\n" for s in satirlar).encode("utf-8")
    yol.write_bytes(gzip.compress(veri) if yol.name.endswith(".gz") else veri)


def test_dokum_oku_gz_ve_duz_dosya_dil_suzgeci(tmp_path: Path) -> None:
    tr = tmp_path / "tr.jsonl.gz"
    ota = tmp_path / "ota.jsonl"
    _dokum_yaz(
        tr, [kayit(sablon("root", **{"2": "ar", "3": KOK_BNR})), {**kayit(), "lang_code": "az"}]
    )
    _dokum_yaz(ota, [{**kayit(), "lang_code": "ota", "word": "ددد"}])
    indeks = KaikkiIndeksi("1")
    assert dokum_oku(tr, DIL_TR, indeks) == 1
    assert dokum_oku(ota, DIL_OTA, indeks) == 1
    assert indeks.tr_maddeleri("deneme") and indeks.osmanlica_maddeleri("ددد", "noun")
    assert indeks.osmanlica_maddeleri("ددد", "verb") == []


def test_dokum_oku_bozuk_dosya_girdi_hatasi(tmp_path: Path) -> None:
    yol = tmp_path / "ota.jsonl"
    yol.write_bytes(b"{bozuk\n")
    with pytest.raises(GirdiHatasi):
        dokum_oku(yol, DIL_OTA, KaikkiIndeksi("1"))


def test_turkce_anahtar_lower_turkish_ile() -> None:
    indeks = KaikkiIndeksi("1")
    satir = kayit()
    satir["word"] = "İncir"  # noktali I
    indeks.ekle(madde_cikar(satir, DIL_TR))  # type: ignore[arg-type]
    assert indeks.tr_maddeleri("incir")


# --- QAC eslemesi ----------------------------------------------------------------------------


def test_kok_katlamasi_hemze_ve_elif_bicimleri() -> None:
    assert kok_katla(KOK_AMN_ELIFLI) == kok_katla(KOK_AMN)
    assert kok_katla("آ ب ى") == "ا ب ي"  # elif med -> elif, elif maksura -> ye
    assert kok_katla("ٱ ة إ ؤ ئ") == "ا ه ء ء ء"
    assert kok_katla("ب-ن ر،") == "ب ن ر"  # harf olmayan karakterler atilir


def test_etimon_anahtari_elifi_atar_ve_hareke_siler() -> None:
    assert etimon_anahtari(ETIMON_SML) == "صمل"
    assert etimon_anahtari(ETIMON_BNR) == "بنر"
    assert etimon_anahtari("أُمَّة") == etimon_anahtari("امة")  # hemzeli elif de elif sayilir


def test_eslestir_kok_harfleriyle() -> None:
    e = eslestir(env_kur(), [kok_kanit(KOK_SML)])
    assert {k.letters_bw for k in e.kok_kumesi} == {"Sml"}
    assert not e.lemmalar


def test_eslestir_etimonla_lemma_ve_kok() -> None:
    e = eslestir(env_kur(), [etimon_kanit(ETIMON_SML)])
    assert {k.letters_bw for k in e.kok_kumesi} == {"Sml"}
    assert {lm.qac_ref for lm in e.lemmalar} == {"samal"}


def test_koksuz_qac_lemmasi_kok_adayi_degildir() -> None:
    lemmalar = [*QAC_LEMMALAR, {"qac_ref": "ksz", "text_clean": "ددد", "root_letters_bw": None}]
    env = QacEnvanteri.kur(QAC_KOKLER, lemmalar)
    assert eslestir(env, [etimon_kanit("ددد")]).kok_kumesi == frozenset()


def test_eslestir_eslesmeyen_kanit_bos_aday() -> None:
    assert eslestir(env_kur(), [kok_kanit("ز ز ز"), etimon_kanit("ززز")]).kok_kumesi == frozenset()


# --- lemmatizer sarmalayici ------------------------------------------------------------------


class _Parse:
    def __init__(self, lemma: str, pos: str, formatted: str = "") -> None:
        self.lemma, self.pos, self.formatted = lemma, pos, formatted


def test_lemma_turu_koseli_parantez_blogundan_gelir() -> None:
    p = _Parse("Deneme", "Noun", "[deneme:Verb] oku:Verb|yan:PresPart→Noun")
    assert _cozumleri_topla([[p]]) == frozenset({Cozum("deneme", "Verb")})


def test_lemma_turu_blok_yoksa_cozum_turu_ve_unk_ayiklanir() -> None:
    cozumler = _cozumleri_topla([[_Parse("İnce", "Adj"), _Parse("Unk", "Unk"), _Parse("x", "Unk")]])
    assert cozumler == frozenset({Cozum("ince", "Adj")})  # noktali I acik eslemeyle kucultulur


def test_zeyrek_yoksa_ya_da_klasor_yoksa_girdi_hatasi(tmp_path: Path) -> None:
    with pytest.raises(GirdiHatasi):
        ZeyrekLemmatizer(tmp_path / "yok")


def test_zeyrek_gercek_kapsam_ve_susturma(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    pytest.importorskip("zeyrek")
    depo = Path(__file__).resolve().parents[2] / "data" / "gelen" / "nltk-punkt"
    adaylar = sorted(depo.glob("*/nltk_data")) if depo.is_dir() else []
    if not adaylar:
        pytest.skip("data/gelen/nltk-punkt yok")
    lem = ZeyrekLemmatizer(adaylar[-1])
    a = lem.analiz("kitaplar")
    assert "kitap" in a.lemmalar and not a.bilinmiyor
    assert lem.analiz("xqzvw").bilinmiyor
    yakalanan = capsys.readouterr()
    assert "APPENDING RESULT" not in yakalanan.out + yakalanan.err
    assert lem.analiz("kitaplar") is a  # onbellek
