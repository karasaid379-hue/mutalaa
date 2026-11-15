"""`mutalaa qa gold`: komut, cikis kodlari, rapor, gerileme ve `xref_gate` cagrisi (A18.5).

Tur islevleri SAHTE olculerle degistirilir (gercek olcumler `test_gold_*` dosyalarinda); burada
komutun sozlesmesi sinanir: cikis 0 (kapi kaldi olsa bile), 1 (yalniz gerileme), 2 (girdi ve
dongusellik hatasi), `--dry-run` hicbir sey yazmaz, rapor ve `xref_gate` satiri.
"""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from hat_yardimci import ansisiz, depo_kur
from typer.testing import CliRunner

from mutalaa_pipeline import cikis, cli
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.qa.gold import kapi, run
from mutalaa_pipeline.qa.gold.kapi import TurSonucu

runner = CliRunner()
ESIK = {"kesinlik": 0.95, "duyarlilik": 0.80}


class SahteBaglanti:
    """`execute` cagrilarini kaydeder (xref_gate upsert); gercek veritabani yok."""

    def __init__(self) -> None:
        self.cagrilar: list[tuple[str, tuple[object, ...]]] = []

    def execute(self, sorgu: str, parametre: tuple[object, ...] = ()) -> None:
        self.cagrilar.append((sorgu, parametre))

    def close(self) -> None:
        pass


def _sonuc(cli_tur: str, kesinlik: float, sinif: str = "silver") -> TurSonucu:
    gecti = kesinlik >= 0.95
    return TurSonucu(
        cli_tur=cli_tur,
        manifest={
            "set": cli_tur,
            "surum": "2026-11-13-0123abcd",
            "sinif": sinif,
            "olcum_turu": "dogruluk",
            "ornek_sayisi": 10,
            "kaynak": [{"source_id": "kaynak-a", "surum": "1", "madde": "m", "rol": "kanit"}],
            "dogrulama_yontemi": "sentetik",
            "uretim_komutu": "komut",
        },
        sonuc="gecti" if gecti else "kaldi",
        olculer={"kesinlik": kesinlik, "duyarlilik": 0.9},
        esikler=ESIK,
        esik_sonuclari={"kesinlik": gecti, "duyarlilik": True},
        tahmin_ozeti=f"{kesinlik:.4f}".encode().hex().ljust(64, "0"),
        olculen_ornek=6,
        uretim_kaynaklari=["kaynak-b"],
    )


@pytest.fixture
def dunya(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    kok = depo_kur(tmp_path)
    monkeypatch.setenv("MUTALAA_VERI_KOK", str(tmp_path / "data"))
    return kok


def _calistir(
    kok: Path,
    tur: str = "kok",
    *,
    dry_run: bool = False,
    build: bool = False,
    baglanti: SahteBaglanti | None = None,
) -> int:
    b = baglanti or SahteBaglanti()
    return run.komut_qa_gold(
        tur=tur,
        build=build,
        dry_run=dry_run,
        config=None,
        kok=kok,
        baglanti=lambda: b,  # type: ignore[arg-type, return-value]
    )


def _sahte(monkeypatch: pytest.MonkeyPatch, **islevler: object) -> None:
    kayit = dict(run.TUR_ISLEVLERI)
    kayit.update(islevler)  # type: ignore[arg-type]
    monkeypatch.setattr(run, "TUR_ISLEVLERI", kayit)


def _raporlar(tmp_path: Path) -> list[Path]:
    return sorted((tmp_path / "data" / "reports").glob("*-gold-*.json"))


def test_gecersiz_type_cikis_2(dunya: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert _calistir(dunya, "anlamsal") == cikis.GIRDI_HATASI
    assert "--type" in capsys.readouterr().err


def test_type_zorunlu_ve_secenekler_yardimda(dunya: Path) -> None:
    sonuc = runner.invoke(cli.app, ["qa", "gold", "--kok", str(dunya)])
    assert sonuc.exit_code == 2  # --type eksik
    yardim = ansisiz(runner.invoke(cli.app, ["qa", "gold", "--help"]).output)
    for secenek in ("--type", "--build", "--dry-run", "--config"):
        assert secenek in yardim


def test_set_yoksa_olcum_yerine_hata_cikis_2(
    dunya: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # --build yok ve data/gold/<set> yok: GirdiHatasi (cikis 2), PG'ye hicbir sey yazilmaz
    baglanti = SahteBaglanti()
    assert _calistir(dunya, "lemma", baglanti=baglanti) == cikis.GIRDI_HATASI
    assert "build" in capsys.readouterr().err
    assert baglanti.cagrilar == []


def test_kapi_kaldi_olsa_bile_cikis_0_rapor_ve_xref_gate(
    dunya: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _sahte(monkeypatch, kok=lambda o: _sonuc("kok", 0.60))
    baglanti = SahteBaglanti()
    assert _calistir(dunya, baglanti=baglanti) == cikis.BASARILI
    assert "qa gold kok: kaldi" in capsys.readouterr().out
    (rapor,) = _raporlar(tmp_path)
    r = kapi.rapor_oku(rapor)
    assert r["sonuc"] == "kaldi" and r["tur"] == "kok" and r["olculer"]["kesinlik"] == 0.6
    ((sorgu, parametre),) = baglanti.cagrilar
    assert "icerik.xref_gate" in sorgu and "ON CONFLICT (tur, set_sinifi)" in sorgu
    assert parametre[:4] == ("kok", "silver", "2026-11-13-0123abcd", "kaldi")
    assert parametre[4] == ["kaynak-a"] and parametre[5] == r["rapor_sha256"]
    assert parametre[6] == r["data_version"]


def test_iktibas_sentetik_set_sinifi_ve_tur_eslemesi(
    dunya: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    siniflar = {"benzer-ayet": "altin", "atif": "sentetik", "iktibas": "sentetik"}
    _sahte(
        monkeypatch,
        **{
            t: (lambda o, t=t: _sonuc(t, 0.99, siniflar.get(t, "silver")))  # type: ignore[misc]
            for t in kapi.CLI_TURLERI
        },
    )
    baglanti = SahteBaglanti()
    assert _calistir(dunya, "hepsi", baglanti=baglanti) == cikis.BASARILI
    turler = [(p[0], p[1]) for _, p in baglanti.cagrilar]
    assert ("benzer_ayet", "altin") in turler  # tire -> altcizgi
    assert ("iktibas", "sentetik") in turler  # sentetik sinif yazilir, kapi acmaz
    assert ("atif", "sentetik") in turler
    assert len(turler) == 5


def test_dry_run_hicbir_sey_yazmaz(
    dunya: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _sahte(monkeypatch, kok=lambda o: _sonuc("kok", 0.99))
    baglanti = SahteBaglanti()
    assert _calistir(dunya, dry_run=True, baglanti=baglanti) == cikis.BASARILI
    assert "dry-run" in capsys.readouterr().out
    assert _raporlar(tmp_path) == [] and baglanti.cagrilar == []
    assert not (tmp_path / "data" / "gold").exists()


def test_ilk_kosuda_onceki_yok_gerileme_yok(
    dunya: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _sahte(monkeypatch, kok=lambda o: _sonuc("kok", 0.50))
    assert _calistir(dunya) == cikis.BASARILI
    assert kapi.rapor_oku(_raporlar(tmp_path)[0])["gerileme"] == []


def test_gerileme_cikis_1_yalniz_onceki_gecti_raporuna_gore(
    dunya: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _sahte(monkeypatch, kok=lambda o: _sonuc("kok", 0.97))
    assert _calistir(dunya) == cikis.BASARILI  # kabul edilmis kosu: gecti
    # 0,01 dusus (0,96): esik 0,02 asilmaz -> 0
    _sahte(monkeypatch, kok=lambda o: _sonuc("kok", 0.96))
    assert _calistir(dunya) == cikis.BASARILI
    capsys.readouterr()
    # 0,97 -> 0,90: 0,02'den fazla dusus: gecmese de kirilir, cikis 1; rapor yine yazilir
    _sahte(monkeypatch, kok=lambda o: _sonuc("kok", 0.90))
    assert _calistir(dunya) == cikis.QA_KALDI
    assert "gerileme" in capsys.readouterr().err
    raporlar = [kapi.rapor_oku(p) for p in _raporlar(tmp_path)]
    son = max(raporlar, key=lambda r: str(r["olculdu_utc"]))
    assert son["olculer"]["kesinlik"] == 0.9
    assert [g["olcu"] for g in son["gerileme"]] == ["kesinlik"]
    # kaldi raporlar referans olmaz: onceki kabul edilmis hala 0,97/0,96 gecti raporlarindan biri
    onceki = kapi.onceki_kabul_edilmis(tmp_path / "data", "kok")
    assert onceki is not None and onceki["sonuc"] == "gecti"


def test_esikler_tutsa_bile_gerileme_xref_gate_kaldi_yazar_cikis_1(
    dunya: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _sahte(monkeypatch, kok=lambda o: _sonuc("kok", 0.99))
    assert _calistir(dunya) == cikis.BASARILI  # kabul edilmis kosu: gecti (0,99)
    capsys.readouterr()
    # 0,99 -> 0,95: esik (>= 0,95) tutar ama dusus 0,04 > 0,02: kaldi + cikis 1
    _sahte(monkeypatch, kok=lambda o: _sonuc("kok", 0.95))
    assert _sonuc("kok", 0.95).sonuc == "gecti"
    baglanti = SahteBaglanti()
    assert _calistir(dunya, baglanti=baglanti) == cikis.QA_KALDI
    cikti = capsys.readouterr()
    assert "gerileme" in cikti.err and "qa gold kok: kaldi" in cikti.out
    son = max((kapi.rapor_oku(p) for p in _raporlar(tmp_path)), key=lambda r: str(r["olculdu_utc"]))
    assert son["sonuc"] == "kaldi" and son["olculer"]["kesinlik"] == 0.95
    assert "gerileme: kesinlik 0.9900 -> 0.9500" in str(son["kaldi_nedeni"])
    assert [g["olcu"] for g in son["gerileme"]] == ["kesinlik"]
    ((_, parametre),) = baglanti.cagrilar
    assert parametre[3] == "kaldi" and parametre[5] == son["rapor_sha256"]
    # kaldi rapor referans olmaz; kabul edilmis kosu hala 0,99
    onceki = kapi.onceki_kabul_edilmis(tmp_path / "data", "kok")
    assert onceki is not None and onceki["olculer"]["kesinlik"] == 0.99


def test_gerilemesiz_gecen_kosuda_kaldi_nedeni_yok(
    dunya: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _sahte(monkeypatch, kok=lambda o: _sonuc("kok", 0.99))
    assert _calistir(dunya) == cikis.BASARILI
    r = kapi.rapor_oku(_raporlar(tmp_path)[0])
    assert r["sonuc"] == "gecti" and "kaldi_nedeni" not in r


def _sozluksel_secim_kur(
    monkeypatch: pytest.MonkeyPatch,
    secim: set[tuple[int, int]],
    db_satirlari: list[tuple[int, int]],
) -> run.Oturum:
    """`sozluksel_secim` bagimliliklarini sahtelerle degistirir (uretim girdisi, DB satirlari)."""
    ctx = SimpleNamespace(
        require_sources=lambda adlar: {a: SimpleNamespace(surum="1") for a in adlar},
        veri_kok=Path("."),
    )
    monkeypatch.setattr(run, "son_calisma", lambda *a, **k: object())
    monkeypatch.setattr(run, "saglam_olmali", lambda *a, **k: None)
    monkeypatch.setattr(run, "units_oku", lambda *a, **k: [])
    monkeypatch.setattr(
        run.db_girdi, "db_oku", lambda *a, **k: SimpleNamespace(ayetler=[], kelimeler=[])
    )
    monkeypatch.setattr(run, "ayet_kelimeleri", lambda *a, **k: [])
    monkeypatch.setattr(run, "simple_kelimeleri", lambda *a, **k: SimpleNamespace(kelimeler=[]))
    monkeypatch.setattr(run, "KuranIndeksi", lambda *a, **k: object())
    monkeypatch.setattr(run, "adaylari_bul", lambda *a, **k: sorted(secim))
    monkeypatch.setattr(run, "sinirla", lambda adaylar: {(lo - 1, hi - 1) for lo, hi in adaylar})
    monkeypatch.setattr(run.benzer, "satirlari_oku", lambda *a, **k: (list(db_satirlari), {}, {}))
    return SimpleNamespace(ctx=ctx, conn=object())  # type: ignore[return-value]


def test_db_qursimsiz_secimde_degilse_girdi_hatasi_cikis_2(
    dunya: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    secim = {(1, 2), (3, 4)}
    # DB'de bagimsiz secimde olmayan bir sozluksel satir var: (7, 9)
    o = _sozluksel_secim_kur(monkeypatch, secim, [(1, 2), (7, 9)])
    with pytest.raises(GirdiHatasi) as hata:
        run.sozluksel_secim(o, {})
    mesaj = str(hata.value)
    assert "1 veritabani" in mesaj and "2 QurSim'siz" in mesaj
    assert "7" not in mesaj and "9" not in mesaj  # yalniz sayac: ayet sirasi ya da metin yok
    # komut: cikis 2, benzer-ayet icin rapor ve xref_gate yazilmaz
    _sahte(monkeypatch, **{"benzer-ayet": lambda oturum: run.sozluksel_secim(o, {})})  # type: ignore[arg-type]
    baglanti = SahteBaglanti()
    assert _calistir(dunya, "benzer-ayet", baglanti=baglanti) == cikis.GIRDI_HATASI
    assert "db_qursimsiz" not in capsys.readouterr().out
    assert _raporlar(tmp_path) == [] and baglanti.cagrilar == []


def test_db_qursimsiz_tamami_secimde_ise_sayac_sifir_ve_hata_yok(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    o = _sozluksel_secim_kur(monkeypatch, {(1, 2), (3, 4)}, [(1, 2), (3, 4)])
    secilen, _, sayac = run.sozluksel_secim(o, {})
    assert secilen == [(1, 2), (3, 4)]
    assert sayac["db_qursimsiz_secimde_degil"] == 0 and sayac["db_qursimsiz_sozluksel_satir"] == 2


def test_hata_diger_turleri_durdurmaz_cikis_2_yalniz_kaynak_adi(
    dunya: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def donguselli(o: object) -> TurSonucu:
        raise GirdiHatasi("dongusellik: set uretimin girdisi olan kaynaktan kurulmus: quranwbw-tr")

    sira: list[str] = []

    def lemma_(o: object) -> TurSonucu:
        sira.append("lemma")
        return _sonuc("lemma", 0.99)

    _sahte(monkeypatch, kok=donguselli, lemma=lemma_)
    baglanti = SahteBaglanti()
    assert _calistir(dunya, "hepsi", baglanti=baglanti) == cikis.GIRDI_HATASI
    hata = capsys.readouterr().err
    assert "dongusellik" in hata and "quranwbw-tr" in hata and sira == ["lemma"]
    # kok icin olcum yerine hata: rapor ve xref_gate YOK; lemma icin var
    assert [kapi.rapor_oku(p)["tur"] for p in _raporlar(tmp_path)] == ["lemma"]
    assert [p[0] for _, p in baglanti.cagrilar] == ["lemma"]


def test_hepsi_sirayla_bes_tur(dunya: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    sira: list[str] = []

    def kur(ad: str):  # type: ignore[no-untyped-def]
        def f(o: object) -> TurSonucu:
            sira.append(ad)
            return _sonuc(ad, 0.99)

        return f

    _sahte(monkeypatch, **{t: kur(t) for t in kapi.CLI_TURLERI})
    assert _calistir(dunya, "hepsi") == cikis.BASARILI
    assert sira == ["kok", "lemma", "benzer-ayet", "atif", "iktibas"]


def test_turleri_coz() -> None:
    assert run.turleri_coz("hepsi") == kapi.CLI_TURLERI
    assert run.turleri_coz("benzer-ayet") == ("benzer-ayet",)
    with pytest.raises(GirdiHatasi):
        run.turleri_coz("benzer_ayet")


def test_run_raporu_kaynak_kimligi_tasimaz_ve_icerik_metni_yok(
    dunya: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _sahte(monkeypatch, kok=lambda o: _sonuc("kok", 0.99))
    assert _calistir(dunya) == cikis.BASARILI
    govde = json.dumps(kapi.rapor_oku(_raporlar(tmp_path)[0]))
    assert govde.isascii()  # kanonik JSON ASCII: Arapca/Turkce icerik metni sizmaz
