"""`qa/gold/benzer.py` ve `qa/gold/lemma.py` (A18.5): SENTETIK ayet kumeleri, elle hesap.

Ayet capalari `q:1:1` ... `q:1:30` (anlamsiz kume), QurSim ve ilm dosyalari tmp altinda sentetik.
Hicbir Kur'an metni yoktur.
"""

import hashlib
import json
from pathlib import Path

import pytest

from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.qa.gold import benzer, lemma, setler

SIRA = {f"q:1:{i}": i for i in range(1, 31)}  # capa -> 1 tabanli kuresel ayet no
CAPA = {v: k for k, v in SIRA.items()}


def _cift(a: int, b: int) -> tuple[int, int]:
    return (a, b) if a < b else (b, a)


# --- ilm okuyucusu -------------------------------------------------------------------------------


def _ilm_yaz(tmp_path: Path, veri: object) -> Path:
    yol = tmp_path / "matching-ayah.json"
    yol.write_bytes(json.dumps(veri).encode("utf-8"))
    return yol


def test_ilm_oku_ciftler_ve_gecersiz_girdiler(tmp_path: Path) -> None:
    yol = _ilm_yaz(
        tmp_path,
        {
            "1:1": [
                {"matched_ayah_key": "1:5", "matched_words_count": 4},
                {"matched_ayah_key": "1:5", "matched_words_count": 7},  # ayni cift: en buyuk
                {"matched_ayah_key": "1:1", "matched_words_count": 2},  # kendisi: gecersiz
                {"matched_ayah_key": "9:9", "matched_words_count": 2},  # kumede olmayan ayet
            ],
            "1:7": [{"matched_ayah_key": "1:2", "matched_words_count": 3}],
            "9:9": [{"matched_ayah_key": "1:1", "matched_words_count": 3}],  # gecersiz anahtar
        },
    )
    ciftler, gecersiz = benzer.ilm_oku(yol, SIRA)
    assert ciftler == {(1, 5): 7, (2, 7): 3}  # lo < hi, ters sirali girdi de ayni cift
    assert gecersiz == 3


def test_ilm_oku_bozuk_dosya_hata(tmp_path: Path) -> None:
    yol = tmp_path / "x.json"
    yol.write_bytes(b"{bozuk")
    with pytest.raises(GirdiHatasi):
        benzer.ilm_oku(yol, SIRA)
    with pytest.raises(GirdiHatasi, match="nesne"):
        benzer.ilm_oku(_ilm_yaz(tmp_path, [1, 2]), SIRA)


def test_gelen_dosyasi_sha256sums_denetimi(tmp_path: Path) -> None:
    klasor = tmp_path / "gelen" / "ilm-matching-ayah" / "2026-11-13"
    klasor.mkdir(parents=True)
    (klasor / "matching-ayah.json").write_bytes(b"{}")
    ozet = hashlib.sha256(b"{}").hexdigest()
    (klasor / "SHA256SUMS").write_text(f"{ozet} *matching-ayah.json\n", encoding="utf-8")
    yol, tarih = benzer.gelen_dosyasi(tmp_path, "ilm-matching-ayah", "matching-ayah.json")
    assert yol.name == "matching-ayah.json" and tarih == "2026-11-13"
    (klasor / "matching-ayah.json").write_bytes(b"{ }")  # degisti
    with pytest.raises(GirdiHatasi, match="SHA256SUMS"):
        benzer.gelen_dosyasi(tmp_path, "ilm-matching-ayah", "matching-ayah.json")
    with pytest.raises(GirdiHatasi, match="klasoru yok"):
        benzer.gelen_dosyasi(tmp_path, "olmayan", "x")


# --- olcum ---------------------------------------------------------------------------------------


def _dunya() -> tuple[
    dict[str, object],
    list[dict[str, object]],
    list[tuple[int, int]],
    dict[tuple[int, int], int],
    set[tuple[int, int]],
]:
    qursim = {_cift(i, i + 1): i % 3 for i in range(1, 25, 2)}  # 12 cift, Label 0/1/2
    ilm = {_cift(i, i + 2) for i in range(1, 25, 3)} | {_cift(1, 2), _cift(3, 4)}
    ornekler = benzer.ornekleri_kur(qursim, dict.fromkeys(ilm, 3), CAPA, "q-test", "i-test")
    manifest, _ = setler.set_hazirla("benzer-ayet", benzer.taslak("q-test", "i-test", {}), ornekler)
    olculen = [_cift(i, j) for i in range(1, 30) for j in range(i + 2, 30, 7)]  # sozluksel secim
    return manifest, ornekler, sorted(set(olculen)), qursim, ilm


def _beklenen(
    olculen: list[tuple[int, int]], ref: set[tuple[int, int]], parca: str
) -> tuple[int, int]:
    sec = [c for c in olculen if setler.bolme("benzer-ayet", f"{CAPA[c[0]]}|{CAPA[c[1]]}") == parca]
    return sum(1 for c in sec if c in ref), len(sec)


def test_benzer_olc_kesinlik_dondurulmus_parcada_elle_hesap() -> None:
    manifest, ornekler, olculen, qursim, ilm = _dunya()
    s = benzer.benzer_olc(
        manifest, ornekler, olculen, {"olculen": len(olculen)}, {"tanzil-uthmani"}, CAPA
    )
    dogru, n = _beklenen(olculen, set(qursim), "dondurulmus")
    assert n > 0
    assert s.olculer == {"kesinlik": pytest.approx(dogru / n, abs=1e-6)}
    assert s.olculen_ornek == n
    kapi = s.ayrintilar["kapi_qursim_dondurulmus"]
    assert kapi["referansta"] == dogru and kapi["referansta_yok"] == n - dogru  # type: ignore[index]
    # ilm ve birlesim bilgidir
    i_dogru, _ = _beklenen(olculen, ilm, "dondurulmus")
    assert s.ayrintilar["ilm_silver_dondurulmus_bilgi"]["referansta"] == i_dogru  # type: ignore[index]
    b_dogru, _ = _beklenen(olculen, ilm | set(qursim), "dondurulmus")
    assert s.ayrintilar["birlesim_dondurulmus_bilgi"]["referansta"] == b_dogru  # type: ignore[index]
    assert s.cli_tur == "benzer-ayet" and s.gate_tur == "benzer_ayet" and s.set_sinifi == "altin"
    assert s.sonuc == ("gecti" if dogru / n >= 0.90 else "kaldi")


def test_benzer_olc_esik_090_ve_kapsam_notu() -> None:
    manifest, ornekler, _, qursim, _ = _dunya()
    # olculen = yalniz QurSim ciftleri: kesinlik 1,0 -> gecti
    s = benzer.benzer_olc(manifest, ornekler, sorted(qursim), {}, {"tanzil-uthmani"}, CAPA)
    assert s.olculer["kesinlik"] == 1.0 and s.sonuc == "gecti"
    # hicbiri referansta degil: kesinlik 0 -> kaldi; "yanlis" ilan edilmez, kapsam notu var
    disarda = [_cift(1, 30), _cift(2, 29), _cift(3, 28), _cift(5, 26)]
    k = benzer.benzer_olc(manifest, ornekler, disarda, {}, {"tanzil-uthmani"}, CAPA)
    assert k.olculer["kesinlik"] == 0.0 and k.sonuc == "kaldi"
    assert "tam kapsamli degildir" in " ".join(k.notlar)
    assert "referansta_yok" in str(k.ayrintilar["kapi_qursim_dondurulmus"])
    assert "dondurulmus_referansta_olmayan" in k.referans_kapsami


def test_benzer_label_kirilimi_bilgi_ve_label_esik_yok() -> None:
    manifest, ornekler, olculen, qursim, _ = _dunya()
    s = benzer.benzer_olc(manifest, ornekler, olculen, {}, {"tanzil-uthmani"}, CAPA)
    kirilim = s.ayrintilar["qursim_label_kirilimi_bilgi_dondurulmus"]
    assert set(kirilim) == {"label_0", "label_1", "label_2", "label_1_2"}  # type: ignore[arg-type]
    assert s.ayrintilar["qursim_label_dagilimi"] == {"0": 4, "1": 4, "2": 4}
    # kapi tum etiketleri pozitif sayar: referans kume = butun QurSim ciftleri
    dogru, _ = _beklenen(olculen, set(qursim), "dondurulmus")
    assert s.ayrintilar["kapi_qursim_dondurulmus"]["referansta"] == dogru  # type: ignore[index]
    assert "Label" in " ".join(s.notlar)


def test_benzer_literal_filtre_bilgi_olarak_yazilir() -> None:
    manifest, ornekler, olculen, qursim, _ = _dunya()
    # veritabani filtresi (qursim isaretsiz sozluksel) tanim geregi QurSim ciftlerinden ayrik
    ayrik = [c for c in olculen if c not in qursim]
    s = benzer.benzer_olc(
        manifest, ornekler, olculen, {}, {"tanzil-uthmani"}, CAPA, literal_filtre=ayrik
    )
    lit = s.ayrintilar["literal_veritabani_filtresi_bilgi"]
    assert lit["referansta"] == 0 and "yapisal" in lit["not"]  # type: ignore[index, operator]


def test_benzer_dongusellik_qursim_kaynakli_satir_qursim_ile_olculmez() -> None:
    manifest, ornekler, olculen, _, _ = _dunya()
    with pytest.raises(GirdiHatasi) as hata:
        benzer.benzer_olc(manifest, ornekler, olculen, {}, {"tanzil-uthmani", "qursim"}, CAPA)
    assert "qursim" in str(hata.value) and "dongusellik" in str(hata.value)
    with pytest.raises(GirdiHatasi, match="ilm-matching-ayah"):  # ilm de kanit: ayni kural
        benzer.benzer_olc(manifest, ornekler, olculen, {}, {"ilm-matching-ayah"}, CAPA)


def test_benzer_set_manifesti_siniflar() -> None:
    manifest, ornekler, _, qursim, ilm = _dunya()
    assert manifest["sinif"] == "altin" and manifest["olcum_turu"] == "dogruluk"
    assert manifest["referans_siniflari"] == {"qursim": "altin", "ilm-matching-ayah": "silver"}
    siniflar = {o["id"]: o["sinif"] for o in ornekler}
    for c in qursim:
        assert siniflar[f"{CAPA[c[0]]}|{CAPA[c[1]]}"] == "altin"
    for c in ilm - set(qursim):
        assert siniflar[f"{CAPA[c[0]]}|{CAPA[c[1]]}"] == "silver"
    for o in ornekler:
        setler.ornek_dogrula(o)


# --- lemma ---------------------------------------------------------------------------------------


def _lemma_dunyasi() -> tuple[
    dict[str, object],
    list[dict[str, object]],
    dict[str, tuple[list[str], list[str]]],
    dict[int, str],
]:
    kelimeler = [
        {"surah": 1, "ayah": 1, "lemma_qac_ref": "ra", "root_letters_bw": "k1"},
        {"surah": 1, "ayah": 1, "lemma_qac_ref": "rb", "root_letters_bw": "k2"},
        {"surah": 1, "ayah": 2, "lemma_qac_ref": "ra", "root_letters_bw": "k1"},
        {"surah": 1, "ayah": 3, "lemma_qac_ref": "rc", "root_letters_bw": None},
        {"surah": 1, "ayah": 4, "lemma_qac_ref": None, "root_letters_bw": None},
    ]
    kumeler = lemma.qac_ayet_kumeleri(kelimeler)
    ornekler = lemma.ornekleri_kur(kumeler, "q-test")
    manifest, _ = setler.set_hazirla("lemma", lemma.taslak("q-test"), ornekler)
    refler = {10: "ra", 11: "rb", 12: "rc"}
    return manifest, ornekler, kumeler, refler


def test_lemma_qac_kumeleri_ve_set_alanlari() -> None:
    manifest, ornekler, kumeler, _ = _lemma_dunyasi()
    assert kumeler["q:1:1"] == (["ra", "rb"], ["k1", "k2"])
    assert kumeler["q:1:4"] == ([], [])  # bos kumeli ayet de ornek
    assert manifest["sinif"] == "altin" and manifest["olcum_turu"] == "tutarlilik"
    for o in ornekler:
        setler.ornek_dogrula(o)
        assert o["sinif"] == "altin" and o["kaynak"]["source_id"] == "qac-morfoloji"  # type: ignore[index]


def test_lemma_olc_tam_tutarli_gecer() -> None:
    manifest, ornekler, kumeler, refler = _lemma_dunyasi()
    xref = [("q:1:1", "q:1:2", [10])]  # ra: iki ayetin kesisiminde
    s = lemma.lemma_olc(manifest, ornekler, dict(kumeler), xref, refler)
    assert s.olculer["tutarlilik"] == 1.0 and s.sonuc == "gecti"
    assert s.cli_tur == "lemma" and s.set_sinifi == "altin"
    assert s.olculen_ornek == 4  # dort ayet


def test_lemma_olc_ayet_kumesi_farki_yuzde_yuzu_bozar() -> None:
    manifest, ornekler, kumeler, refler = _lemma_dunyasi()
    db = dict(kumeler)
    db["q:1:2"] = (["ra", "rb"], ["k1"])  # veritabaninda fazladan lemma
    s = lemma.lemma_olc(manifest, ornekler, db, [("q:1:1", "q:1:2", [10])], refler)
    assert s.olculer["tutarlilik_ayet"] == 3 / 4
    assert s.olculer["tutarlilik"] == pytest.approx(4 / 5)  # (3 ayet + 1 xref) / (4 + 1)
    assert s.sonuc == "kaldi"
    assert s.ayrintilar["ayet"]["farkli_ayet_ornekleri"] == ["q:1:2"]  # type: ignore[index]


def test_lemma_olc_xref_paylasilan_lemma_kesisimde_degilse_tutarsiz() -> None:
    manifest, ornekler, kumeler, refler = _lemma_dunyasi()
    # rb (11) yalniz q:1:1'de var; q:1:2 ile paylasilamaz
    xref = [("q:1:1", "q:1:2", [11]), ("q:1:1", "q:1:2", [10]), ("q:1:1", "q:1:3", [])]
    s = lemma.lemma_olc(manifest, ornekler, dict(kumeler), xref, refler)
    assert s.olculer["tutarlilik_xref"] == pytest.approx(1 / 3)  # bos paylasim da tutarsiz
    assert s.sonuc == "kaldi"
    assert s.ayrintilar["xref"]["tutarsiz_ornekleri"] == ["q:1:1|q:1:2", "q:1:1|q:1:3"]  # type: ignore[index]


def test_lemma_olc_xref_yoksa_ayet_tutarliligi_belirler() -> None:
    manifest, ornekler, kumeler, refler = _lemma_dunyasi()
    s = lemma.lemma_olc(manifest, ornekler, dict(kumeler), [], refler)
    assert s.olculer["tutarlilik_xref"] == 1.0 and s.sonuc == "gecti"
    eksik = {k: v for k, v in kumeler.items() if k != "q:1:3"}
    k = lemma.lemma_olc(manifest, ornekler, eksik, [], refler)
    assert k.sonuc == "kaldi" and k.ayrintilar["ayet"]["veritabaninda_olmayan_ayet"] == 1  # type: ignore[index]


def test_lemma_dongusellik_muaf_olcum_turu() -> None:
    manifest, _, _, _ = _lemma_dunyasi()
    # uretim de qac-morfoloji: tutarlilik testinde dongusellik hatasi YOK (K-51 madde 12)
    setler.manifest_dongusellik_denetle(manifest, {"qac-morfoloji"})
