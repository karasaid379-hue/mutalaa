"""`mutalaa qa run --source tanzil-uthmani`: komut, cikis kodlari ve rapor (A10.5; SENTETIK veri).

6.236 ayetlik sentetik zincir (`tam_sablon`: ingest x2, normalize, anchor; gercek komutlarla) bir
kez kurulur, her test kendi kopyasini bozar. Kapi kalan senaryolarda zincir gecerli kalir
(`anchor_bozdur` hatali bir anchor adimini taklit eder); zinciri bozan senaryolar cikis 2 verir.
`export pg` sozlesmesi `pg._qa_denetle` ve `pg.hazirla` ile veritabanisiz sinanir.
"""

import hashlib
import json
import shutil
import unicodedata
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner, Result
from zincir_yardimci import Zincir, anchor_bozdur, ortam_kur, sablon_kopyala, vektor_sayisi

from mutalaa_pipeline import cli, lineage
from mutalaa_pipeline.adimlar.normalize_tanzil import EK_KAYNAK, KAYNAK
from mutalaa_pipeline.export import pg
from mutalaa_pipeline.qa import KAPILAR
from mutalaa_pipeline.runctx import QaKaldi
from mutalaa_pipeline.zincir import calismalar

runner = CliRunner()


@pytest.fixture
def z(tam_sablon: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Zincir:
    zincir = sablon_kopyala(tam_sablon, tmp_path / "t")
    ortam_kur(zincir, monkeypatch)
    return zincir


def qa(z: Zincir, *argumanlar: str) -> Result:
    return runner.invoke(
        cli.app, ["qa", "run", "--source", KAYNAK, *argumanlar, "--kok", str(z.kok)]
    )


def son_qa_raporu(z: Zincir) -> dict[str, Any]:
    raporlar = [json.loads(p.read_bytes()) for p in sorted((z.veri_kok / "reports").glob("*.json"))]
    qa_raporlari = [r for r in raporlar if r.get("komut") == "qa run"]
    assert qa_raporlari
    return qa_raporlari[-1]


def son_anchor(z: Zincir) -> Any:
    return calismalar(z.ctx("export", [KAYNAK]), KAYNAK, "anchor")[-1]


def pg_denetimi(z: Zincir) -> str:
    """`export pg`nin QA raporu aramasi (veritabani gerekmez): rapor kimligi ya da QaKaldi."""
    anchor = son_anchor(z)
    ctx = z.ctx("export", [KAYNAK, EK_KAYNAK])
    return pg._qa_denetle(ctx, KAYNAK, anchor.run_id, str(anchor.cikti_ozeti()))


# --- gecen senaryo -------------------------------------------------------------------------


def test_dort_kapi_gecer_cikis_0(z: Zincir) -> None:
    sonuc = qa(z)
    assert sonuc.exit_code == 0, sonuc.stderr + sonuc.stdout
    anchor = son_anchor(z)
    assert sonuc.stdout == (
        f"qa run {KAYNAK}: G-KAY gecti, G-BUT gecti, G-CAP gecti, G-NOR gecti"
        f" (anchor run {anchor.run_id})\n"
    )


def test_rapor_alanlari(z: Zincir) -> None:
    assert qa(z).exit_code == 0
    rapor = son_qa_raporu(z)
    anchor = son_anchor(z)
    assert rapor["komut"] == "qa run"
    assert rapor["adim"] == "qa"
    assert rapor["kaynak"] == KAYNAK
    assert rapor["kaynaklar"] == [KAYNAK, EK_KAYNAK]
    assert rapor["anchor_run_id"] == anchor.run_id
    assert rapor["units_sha256"] == anchor.cikti_ozeti()
    assert rapor["cikis_kodu"] == 0
    assert rapor["durum"] == "tamam"
    assert rapor["kapilar"] == dict.fromkeys(KAPILAR, "gecti")
    assert rapor["kapi_bulgulari"] == {k: [] for k in KAPILAR}
    assert rapor["parametreler"] == {"source": KAYNAK}
    assert rapor["sayilar"]["birim"] == 6236
    assert rapor["uyarilar"] == []
    zincir = rapor["zincir"]
    assert zincir["anchor"] == anchor.run_id
    assert set(zincir["ingest"]) == {KAYNAK, EK_KAYNAK}
    sayilar = rapor["kapi_sayilari"]
    assert sayilar["G-BUT"]["birim"] == 6236
    assert sayilar["G-BUT"]["sure"] == 114
    assert sayilar["G-CAP"]["capa"] == sayilar["G-CAP"]["beklenen_capa"] == 6236
    assert sayilar["G-NOR"]["vektor"] == vektor_sayisi()
    olcum = rapor["olcumler"]
    assert olcum["ayet_sayilari"][KAYNAK] == {"sure": 114, "ayet": 6236}
    assert olcum["ayet_sayilari_json"] == {
        "okundu": True,
        "eleman": 114,
        "toplam": 6236,
        "uthmani_ile_ayni": True,
        "simple_clean_ile_ayni": True,
        "kodun_tablosuyla_ayni": True,
        "kopyalar_ayni": True,
    }
    assert olcum["ar8_gorulen"] is False
    assert olcum["mn_kalan_gorulen"] is False
    assert olcum["nfc"][KAYNAK]["nfc_olmayan_ayet"] == 6236  # sentetik Uthmani NFC degil
    assert olcum["nfc"][EK_KAYNAK]["nfc_olmayan_ayet"] == 0
    assert olcum["ar4"]["ek_sozcuklu_ayet"] > 0
    assert set(olcum["besmele"]) == {KAYNAK, EK_KAYNAK}


def test_rapor_ve_gunluk_icerik_tasimaz(z: Zincir) -> None:
    assert qa(z).exit_code == 0
    rapor_baytlari = b"".join(p.read_bytes() for p in (z.veri_kok / "reports").glob("*.json"))
    gunluk_baytlari = b"".join(p.read_bytes() for p in (z.veri_kok / "logs").glob("*.jsonl"))
    for veri in (rapor_baytlari, gunluk_baytlari):
        assert veri.isascii()
        assert b"\\u06" not in veri  # Arapca metin kacisli bile rapora ve gunluge girmez
    assert b"Deneme bildirim" not in rapor_baytlari  # bildirim metni de girmez


def test_rapor_export_pg_sozlesmesine_uyar(z: Zincir) -> None:
    """`export pg` ayni anchor calistirmasi ve ayni units ozeti icin dort kapida gecti arar."""
    with pytest.raises(QaKaldi, match="QA raporu yok"):
        pg_denetimi(z)  # QA henuz kosulmadi
    assert qa(z).exit_code == 0
    assert pg_denetimi(z) == son_qa_raporu(z)["run_id"]


def test_export_pg_dosya_onkosullari_qa_sonrasi_gecer(z: Zincir) -> None:
    """zincir, QA raporu, satirlar, bildirim: `export pg`nin veritabani oncesi butun denetimleri."""
    assert qa(z).exit_code == 0
    ctx = z.ctx("export", [KAYNAK, EK_KAYNAK])
    h = pg.hazirla(ctx, KAYNAK, None, ("tanzil-simple-clean",))
    assert len(h.satirlar) == 6236
    assert h.qa_rapor_id == son_qa_raporu(z)["run_id"]
    assert sorted(h.ingest) == [EK_KAYNAK, KAYNAK]
    assert [r.adim for r in h.zincir].count("normalize") == 1
    for slug in (KAYNAK, EK_KAYNAK):
        assert h.bildirimler[slug] == h.kaynaklar[slug].notice_text  # bayt bayt
    assert [s.ord for s in h.satirlar] == list(range(1, 6237))
    assert all(s.ayah_hi == s.ayah_lo + 1 for s in h.satirlar)


def test_qa_tekrar_kosusu_ayni_sonucu_verir(z: Zincir) -> None:
    assert qa(z).exit_code == 0
    assert qa(z).exit_code == 0
    ilk, ikinci = sorted((z.veri_kok / "reports").glob("*.json"))[-2:]
    a, b = (json.loads(p.read_bytes()) for p in (ilk, ikinci))
    for alan in ("kapilar", "kapi_sayilari", "olcumler", "anchor_run_id", "units_sha256"):
        assert a[alan] == b[alan]
    assert pg_denetimi(z) == b["run_id"]  # en yeni rapor secilir


# --- kapi kalirsa cikis 1 ------------------------------------------------------------------


def kapilari_oku(z: Zincir) -> dict[str, str]:
    return dict(son_qa_raporu(z)["kapilar"])


def test_g_kay_kalirsa_cikis_1(z: Zincir) -> None:
    yol = z.kok / "pipeline" / "sources" / f"{KAYNAK}.toml"
    metin = yol.read_text(encoding="utf-8")
    assert "Deneme bildirim blogu" in metin
    yol.write_text(
        metin.replace("Deneme bildirim blogu", "Deneme bildirim bloku"),
        encoding="utf-8",
        newline="\n",
    )
    sonuc = qa(z)
    assert sonuc.exit_code == 1
    assert (
        "G-KAY kaldi: tanzil-uthmani: notice_text dosyadaki bildirim blogundan farkli"
        in sonuc.stdout
    )
    assert "QA kapisi kaldi: G-KAY" in sonuc.stderr
    assert kapilari_oku(z) == {
        "G-KAY": "kaldi",
        "G-BUT": "gecti",
        "G-CAP": "gecti",
        "G-NOR": "gecti",
    }
    rapor = son_qa_raporu(z)
    assert (rapor["cikis_kodu"], rapor["durum"]) == (1, "basarisiz")
    with pytest.raises(QaKaldi, match="QA kapisi gecmedi: G-KAY"):
        pg_denetimi(z)  # export pg de durur


def hata_enjekte(degistir: Any) -> Any:
    """Bir satirin alanlarini degistiren `anchor_bozdur` islevi (q:2:255 satiri)."""

    def islev(satirlar: list[dict[str, Any]]) -> None:
        satir = next(s for s in satirlar if s["anchor"] == "q:2:255")
        degistir(satir)

    return islev


def nfc_uygula(satir: dict[str, Any]) -> None:
    """K-26 ihlali: Tanzil metnine NFC uygulanmis; `content_hash` yeni metinle tutarlidir."""
    nfc = unicodedata.normalize("NFC", satir["text"])
    assert nfc != satir["text"]
    satir["text"] = nfc
    satir["content_hash"] = hashlib.sha256(nfc.encode("utf-8")).hexdigest()


BAYT_ESITLIGI = (
    "G-BUT kaldi: bayt esitligi: 1 birim: metin ham dosyanin bayt dilimiyle ayni degil: q:2:255"
)


def test_g_but_kalirsa_cikis_1(z: Zincir) -> None:
    """Onceki anchor calismasi yokken NFC ihlalini yalniz G-BUT (bayt esitligi) yakalar."""
    eski = son_anchor(z)
    anchor_bozdur(z, hata_enjekte(nfc_uygula))
    shutil.rmtree(eski.klasor)  # onceki calisma yok: G-CAP'in onceki-ozet denetimi devreye girmez
    sonuc = qa(z)
    assert sonuc.exit_code == 1
    assert BAYT_ESITLIGI in sonuc.stdout
    assert kapilari_oku(z) == {
        "G-KAY": "gecti",
        "G-BUT": "kaldi",
        "G-CAP": "gecti",
        "G-NOR": "gecti",
    }
    assert "QA kapisi kaldi: G-BUT" in sonuc.stderr
    assert "QA kapisi kaldi: G-BUT," not in sonuc.stderr


def test_nfc_ihlalini_onceki_calismanin_ozeti_de_yakalar(z: Zincir) -> None:
    """QA'dan gecmis onceki anchor calismasi duruyorsa metin ozeti degistigi icin G-CAP da kalir."""
    assert qa(z).exit_code == 0  # tam sablonun anchor calismasi onaylanir: G-CAP tabani olur
    anchor_bozdur(z, hata_enjekte(nfc_uygula))
    sonuc = qa(z)
    assert sonuc.exit_code == 1
    assert BAYT_ESITLIGI in sonuc.stdout
    assert "G-CAP kaldi: onceki surumle content_hash farkli: 1 birim: q:2:255" in sonuc.stdout
    assert kapilari_oku(z) == {
        "G-KAY": "gecti",
        "G-BUT": "kaldi",
        "G-CAP": "kaldi",
        "G-NOR": "gecti",
    }
    assert "QA kapisi kaldi: G-BUT, G-CAP" in sonuc.stderr


def test_g_cap_kalirsa_cikis_1(z: Zincir) -> None:
    anchor_bozdur(z, hata_enjekte(lambda s: s.update(ord=s["ord"] + 1)))
    sonuc = qa(z)
    assert sonuc.exit_code == 1
    assert "G-CAP kaldi: ord/ayah: 1 birim" in sonuc.stdout
    assert "q:2:255" in sonuc.stdout
    assert kapilari_oku(z) == {
        "G-KAY": "gecti",
        "G-BUT": "gecti",
        "G-CAP": "kaldi",
        "G-NOR": "gecti",
    }


def test_g_cap_content_hash_kalirsa_cikis_1(z: Zincir) -> None:
    anchor_bozdur(z, hata_enjekte(lambda s: s.update(content_hash="0" * 64)))
    sonuc = qa(z)
    assert sonuc.exit_code == 1
    assert (
        "G-CAP kaldi: content_hash: 1 birim: metnin SHA-256'siyla tutmuyor: q:2:255" in sonuc.stdout
    )


def test_g_nor_kalirsa_cikis_1(z: Zincir) -> None:
    anchor_bozdur(z, hata_enjekte(lambda s: s.update(ar_norm=s["ar_norm"] + " x")))
    sonuc = qa(z)
    assert sonuc.exit_code == 1
    assert "G-NOR kaldi: ar_norm: 1 birim" in sonuc.stdout
    assert kapilari_oku(z) == {
        "G-KAY": "gecti",
        "G-BUT": "gecti",
        "G-CAP": "gecti",
        "G-NOR": "kaldi",
    }


def test_birden_cok_kapi_kalirsa_hepsi_listelenir(z: Zincir) -> None:
    def bozdur(satir: dict[str, Any]) -> None:
        satir.update(ord=satir["ord"] + 1, ar_norm="")

    anchor_bozdur(z, hata_enjekte(bozdur))
    sonuc = qa(z)
    assert sonuc.exit_code == 1
    assert "QA kapisi kaldi: G-CAP, G-NOR" in sonuc.stderr
    assert "G-CAP kaldi:" in sonuc.stdout
    assert "G-NOR kaldi:" in sonuc.stdout
    assert kapilari_oku(z) == {
        "G-KAY": "gecti",
        "G-BUT": "gecti",
        "G-CAP": "kaldi",
        "G-NOR": "kaldi",
    }


def test_ayet_eksikse_g_but_ve_g_cap_kalir(z: Zincir) -> None:
    anchor_bozdur(z, lambda satirlar: [s for s in satirlar if s["anchor"] != "q:114:6"])
    sonuc = qa(z)
    assert sonuc.exit_code == 1
    assert "anchor satirlari: ayet sayisi 6235, beklenen 6236" in sonuc.stdout
    assert "eksik capa: 1 birim" in sonuc.stdout
    assert kapilari_oku(z)["G-BUT"] == kapilari_oku(z)["G-CAP"] == "kaldi"


def test_onceki_calismadan_kaybolan_capa_g_cap_kalir(z: Zincir) -> None:
    """Onceki anchor calismasinda olup yenisinde olmayan capa G-CAP'i kaldirir (onceki capalar)."""
    assert qa(z).exit_code == 0  # temiz ilk kosu: onceki yok
    assert son_qa_raporu(z)["kapi_sayilari"]["G-CAP"]["onceki_run"] == 0
    # ikinci, ayni icerikli anchor calistirmasi: onceki var ve hicbir sey kaybolmamis
    anchor_bozdur(z, lambda satirlar: None)
    assert qa(z).exit_code == 0
    sayilar = son_qa_raporu(z)["kapi_sayilari"]["G-CAP"]
    assert (sayilar["onceki_run"], sayilar["onceki_capa"]) == (1, 6236)
    # ucuncu calistirma bir capayi yitirir
    anchor_bozdur(z, lambda satirlar: [s for s in satirlar if s["anchor"] != "q:1:1"])
    sonuc = qa(z)
    assert sonuc.exit_code == 1
    assert "onceki surumde olup kaybolan capa: 1 birim: q:1:1" in sonuc.stdout


def metni_degistir(satir: dict[str, Any]) -> None:
    """Metne bosluk ekler ve `content_hash` yeni metinle tutarli kalir (G-BUT ve G-CAP kalir)."""
    satir["text"] = satir["text"] + " "
    satir["content_hash"] = hashlib.sha256(satir["text"].encode("utf-8")).hexdigest()


def test_onceki_calismayla_content_hash_farki_g_cap_kalir(z: Zincir) -> None:
    anchor_bozdur(z, lambda satirlar: None)  # onceki: dogru ozetler
    assert qa(z).exit_code == 0  # ... ve QA'dan gecti: G-CAP tabani
    anchor_bozdur(z, hata_enjekte(metni_degistir))
    sonuc = qa(z)
    assert sonuc.exit_code == 1
    assert "onceki surumle content_hash farkli: 1 birim: q:2:255" in sonuc.stdout


# --- G-CAP tabani: QA'dan gecmis son anchor calismasi ----------------------------------------


def test_g_cap_tabani_hemen_onceki_degil_qa_dan_gecen_son_calismadir(z: Zincir) -> None:
    """Bozuk ara calisma tabani degistirmez: duzgun yeniden uretim QA'dan gecer."""
    ilk = son_anchor(z)
    assert qa(z).exit_code == 0  # anchor#1 onaylandi
    anchor_bozdur(z, hata_enjekte(metni_degistir))  # anchor#2 bozuk
    assert qa(z).exit_code == 1
    duzgun = anchor_bozdur(z, lambda satirlar: None)  # anchor#3: duzgun yeniden uretim
    sonuc = qa(z)
    assert sonuc.exit_code == 0, sonuc.stdout + sonuc.stderr
    rapor = son_qa_raporu(z)
    assert rapor["anchor_run_id"] == duzgun.run_id
    assert rapor["onceki_anchor_run_id"] == ilk.run_id  # anchor#2 degil
    assert (rapor["kapi_sayilari"]["G-CAP"]["onceki_run"], rapor["kapilar"]["G-CAP"]) == (
        1,
        "gecti",
    )


def test_ayni_bozuk_girdiden_yeniden_uretim_g_cap_i_kaldirmaz(z: Zincir) -> None:
    """Fark yalniz `anchor` yeniden kosularak ortadan kalkmaz: taban onayli son calismadir."""
    ilk = son_anchor(z)
    assert qa(z).exit_code == 0  # anchor#1 onaylandi
    anchor_bozdur(z, hata_enjekte(metni_degistir))
    assert qa(z).exit_code == 1
    anchor_bozdur(z, hata_enjekte(metni_degistir))  # anchor#3: ayni bozuk icerik yeniden uretildi
    sonuc = qa(z)
    assert sonuc.exit_code == 1
    assert "G-CAP kaldi: onceki surumle content_hash farkli: 1 birim: q:2:255" in sonuc.stdout
    assert son_qa_raporu(z)["onceki_anchor_run_id"] == ilk.run_id


def test_qa_dan_gecmemis_onceki_calisma_taban_olmaz_ve_uyari_verir(z: Zincir) -> None:
    anchor_bozdur(z, lambda satirlar: None)  # anchor#2; anchor#1 icin QA hic kosulmadi
    assert qa(z).exit_code == 0
    rapor = son_qa_raporu(z)
    assert rapor["onceki_anchor_run_id"] is None
    assert rapor["kapi_sayilari"]["G-CAP"]["onceki_run"] == 0
    assert any("dort kapisini da gecmis olan yok" in u for u in rapor["uyarilar"])
    assert all(u.isascii() for u in rapor["uyarilar"])


def test_ilk_kosuda_onceki_calisma_yoksa_uyari_yok(z: Zincir) -> None:
    assert qa(z).exit_code == 0
    rapor = son_qa_raporu(z)
    assert rapor["onceki_anchor_run_id"] is None
    assert rapor["uyarilar"] == []


# --- --gate ve --run -----------------------------------------------------------------------


def test_gate_yalniz_secilen_kapiyi_kosar_eksik_rapor_export_pg_yetmez(z: Zincir) -> None:
    sonuc = qa(z, "--gate", "G-CAP")
    assert sonuc.exit_code == 0
    assert sonuc.stdout.startswith(f"qa run {KAYNAK}: G-CAP gecti (anchor run ")
    rapor = son_qa_raporu(z)
    assert rapor["kapilar"] == {"G-CAP": "gecti"}
    assert rapor["parametreler"] == {"source": KAYNAK, "gate": ["G-CAP"]}
    with pytest.raises(QaKaldi, match="dort kapiyi da icermiyor"):
        pg_denetimi(z)


# --- export pg: ayni calisma icin EN YENI QA kosusu karar verir -------------------------------


def pg_komutu(z: Zincir) -> int:
    """`export pg` komutu; veritabani baglantisi acilirsa test kirilir (`Cagrilmaz`)."""
    from hat_yardimci import ayarlar_kur
    from test_export_pg import Cagrilmaz

    bag = Cagrilmaz()
    kod = pg.komut_export_pg(ayarlar_kur(z.tmp), depo_kok=z.kok, source=KAYNAK, baglanti=bag)
    assert bag.sayi == 0
    return kod


@pytest.mark.parametrize("bozma", ["sil", "bom"])
def test_sonraki_tamamlanamayan_qa_kosusu_eski_gecen_raporu_gecersiz_kilar(
    z: Zincir, capsys: pytest.CaptureFixture[str], bozma: str
) -> None:
    """Vektor dosyasi bozulunca `qa run` 2 ile biter; eski `gecti` raporu export pg'ye yetmez."""
    assert qa(z).exit_code == 0
    gecen = son_qa_raporu(z)["run_id"]
    assert pg_denetimi(z) == gecen
    vektor = z.kok / "shared" / "test-vectors" / "normalize" / "ar.jsonl"
    icerik = vektor.read_bytes()
    if bozma == "sil":
        vektor.unlink()
    else:
        vektor.write_bytes(b"\xef\xbb\xbf" + icerik)  # BOM
    cikis_2(z, "ar.jsonl")
    rapor = son_qa_raporu(z)
    assert rapor["anchor_run_id"] == son_anchor(z).run_id  # rapor veriye bagli, kapi iddia etmez
    assert "kapilar" not in rapor
    with pytest.raises(QaKaldi, match=r"son QA kosusu tamamlanmadi \(cikis 2\)"):
        pg_denetimi(z)
    capsys.readouterr()
    assert pg_komutu(z) == 1  # veritabanina baglanilmadan
    assert "son QA kosusu tamamlanmadi" in capsys.readouterr().err
    vektor.write_bytes(icerik)  # sorun giderilir, QA yeniden kosulur
    assert qa(z).exit_code == 0
    assert pg_denetimi(z) == son_qa_raporu(z)["run_id"] != gecen


@pytest.mark.parametrize("bozma", ["kilit", "halka"])
def test_zincir_ya_da_kilit_hatasiyla_biten_kosu_eski_gecen_raporu_gecersiz_kilar(
    z: Zincir, capsys: pytest.CaptureFixture[str], bozma: str
) -> None:
    """Hata `anchor_run_id` yazilmadan once cikarsa rapor veriye baglanamaz, eski raporu ezemez."""
    assert qa(z).exit_code == 0
    gecen = son_qa_raporu(z)["run_id"]
    assert pg_denetimi(z) == gecen
    if bozma == "kilit":
        kilit = z.tmp / "kilit.json"
        icerik = kilit.read_bytes()
        kilit.write_bytes(b"{")
        cikis_2(z, "tanzil.lock.json")
    else:
        klasor = son_anchor(z).klasor
        manifest = json.loads((klasor / "manifest.json").read_bytes())
        manifest["girdiler"][0]["sha256"] = "0" * 64
        lineage.manifest_yaz(klasor, manifest)
        cikis_2(z, "zincir halkasi tutmuyor")
    rapor = son_qa_raporu(z)
    assert rapor["run_id"] != gecen
    assert rapor["anchor_run_id"] == son_anchor(z).run_id  # hata erken olsa da veriye baglidir
    assert rapor["units_sha256"] == son_anchor(z).cikti_ozeti()
    with pytest.raises(QaKaldi, match=r"son QA kosusu tamamlanmadi \(cikis 2\)"):
        pg_denetimi(z)
    capsys.readouterr()
    assert pg_komutu(z) == 1  # veritabanina baglanilmadan
    assert "son QA kosusu tamamlanmadi" in capsys.readouterr().err
    if bozma == "kilit":
        kilit.write_bytes(icerik)  # sorun giderilir, QA yeniden kosulur
        assert qa(z).exit_code == 0
        assert pg_denetimi(z) == son_qa_raporu(z)["run_id"] != gecen


def test_sonraki_kalan_kismi_kosu_eski_gecen_raporu_gecersiz_kilar(z: Zincir) -> None:
    assert qa(z).exit_code == 0
    yol = z.kok / "pipeline" / "sources" / f"{KAYNAK}.toml"
    metin = yol.read_text(encoding="utf-8")
    yol.write_text(
        metin.replace("Deneme bildirim blogu", "Deneme bildirim bloku"),
        encoding="utf-8",
        newline="\n",
    )
    assert qa(z, "--gate", "G-KAY").exit_code == 1
    assert son_qa_raporu(z)["kapilar"] == {"G-KAY": "kaldi"}
    with pytest.raises(QaKaldi, match="QA kapisi gecmedi: G-KAY"):
        pg_denetimi(z)


def test_sonraki_basarili_kismi_kosu_export_pg_kararini_degistirmez(z: Zincir) -> None:
    assert qa(z).exit_code == 0
    tam = son_qa_raporu(z)["run_id"]
    assert qa(z, "--gate", "G-CAP").exit_code == 0
    assert son_qa_raporu(z)["run_id"] != tam
    assert pg_denetimi(z) == tam  # en yeni rapor kismi; karar tam rapordan okunur


def test_gate_birden_cok_kez_ve_sirasi(z: Zincir) -> None:
    sonuc = qa(z, "--gate", "G-NOR", "--gate", "G-KAY")
    assert sonuc.exit_code == 0
    assert son_qa_raporu(z)["kapilar"] == {"G-KAY": "gecti", "G-NOR": "gecti"}


def test_gate_kalan_kapi_cikis_1(z: Zincir) -> None:
    anchor_bozdur(z, hata_enjekte(lambda s: s.update(ord=0)))
    assert qa(z, "--gate", "G-NOR").exit_code == 0  # G-NOR bu hatayi gormez
    assert qa(z, "--gate", "G-CAP").exit_code == 1


def test_run_belirli_anchor_calistirmasini_denetler(z: Zincir) -> None:
    eski = son_anchor(z)
    anchor_bozdur(z, hata_enjekte(lambda s: s.update(ord=0)))  # yeni ama bozuk
    assert qa(z).exit_code == 1  # varsayilan: en yeni
    sonuc = qa(z, "--run", eski.run_id)
    assert sonuc.exit_code == 0, sonuc.stderr + sonuc.stdout
    rapor = son_qa_raporu(z)
    assert rapor["anchor_run_id"] == eski.run_id
    assert rapor["parametreler"] == {"source": KAYNAK, "run": eski.run_id}
    assert rapor["kapi_sayilari"]["G-CAP"]["onceki_run"] == 0  # eskiden onceki yok


# --- zincir bozuksa cikis 2 -----------------------------------------------------------------


def cikis_2(z: Zincir, parca: str, *argumanlar: str) -> Result:
    sonuc = qa(z, *argumanlar)
    assert sonuc.exit_code == 2, sonuc.stdout + sonuc.stderr
    assert parca in sonuc.stderr
    assert sonuc.stderr.isascii()
    rapor = son_qa_raporu(z)
    assert (rapor["cikis_kodu"], rapor["durum"]) == (2, "basarisiz")
    assert "kapilar" not in rapor  # kapilar degerlendirilemedi: rapor kapi iddia etmez
    return sonuc


def test_anchor_calistirmasi_yoksa_cikis_2(z: Zincir) -> None:
    for klasor in (z.veri_kok / "staged" / KAYNAK).iterdir():
        manifest = json.loads((klasor / "manifest.json").read_bytes())
        if manifest["adim"] == "anchor":
            shutil.rmtree(klasor)
    cikis_2(z, "anchor calistirmasi yok")


def test_anchor_ciktisi_bozulmussa_cikis_2(z: Zincir) -> None:
    units = son_anchor(z).klasor / "units.jsonl"
    units.write_bytes(units.read_bytes().replace(b"q:1:1", b"q:1:2", 1))
    cikis_2(z, "ciktilari saglam degil")


def test_normalize_ciktisi_bozulmussa_cikis_2(z: Zincir) -> None:
    normalize = calismalar(z.ctx("qa", [KAYNAK]), KAYNAK, "normalize")[-1]
    units = normalize.klasor / "units.jsonl"
    units.write_bytes(units.read_bytes() + b"\n")
    cikis_2(z, "ciktilari saglam degil")


def test_zincir_halkasi_ozeti_tutmuyorsa_cikis_2(z: Zincir) -> None:
    """Anchor manifestindeki girdi ozeti, normalize calistirmasinin ciktisiyla ayni degil."""
    klasor = son_anchor(z).klasor
    manifest = json.loads((klasor / "manifest.json").read_bytes())
    manifest["girdiler"][0]["sha256"] = "0" * 64
    lineage.manifest_yaz(klasor, manifest)
    cikis_2(z, "zincir halkasi tutmuyor")


def test_ust_calisma_manifesti_yoksa_cikis_2(z: Zincir) -> None:
    simple = calismalar(z.ctx("qa", [KAYNAK]), EK_KAYNAK, "ingest")[-1]
    (simple.klasor / "manifest.json").unlink()
    cikis_2(z, "zincirde manifesti olmayan calistirma")


def test_ham_dosya_degismisse_cikis_2(z: Zincir) -> None:
    (ham,) = (z.veri_kok / "raw" / KAYNAK).rglob("quran-uthmani.txt")
    veri = ham.read_bytes()
    ham.write_bytes(veri.replace(b"1|1|", b"1|1|X", 1))
    cikis_2(z, "ham dosya ozeti manifestle tutmuyor")


def test_ham_dosya_yoksa_cikis_2(z: Zincir) -> None:
    (ham,) = (z.veri_kok / "raw" / EK_KAYNAK).rglob("quran-simple-clean.txt")
    ham.unlink()
    cikis_2(z, "ham dosya okunamadi")


def test_kilit_dosyasi_yoksa_ya_bozuksa_cikis_2(z: Zincir) -> None:
    kilit = z.tmp / "kilit.json"
    icerik = kilit.read_bytes()
    kilit.write_bytes(b"{")
    cikis_2(z, "tanzil.lock.json")
    kilit.unlink()
    cikis_2(z, "tanzil.lock.json okunamadi")
    kilit.write_bytes(icerik)
    assert qa(z).exit_code == 0


def test_kayitsiz_ya_da_gecersiz_kaynak_kaydi_cikis_2(z: Zincir) -> None:
    yol = z.kok / "pipeline" / "sources" / f"{EK_KAYNAK}.toml"
    icerik = yol.read_bytes()
    yol.unlink()
    cikis_2(z, "kayitsiz")
    yol.write_bytes(icerik.replace(b"atif_metni", b"atif_metni_x", 1))  # bilinmeyen alan
    cikis_2(z, "kayit gecersiz")


def test_ayet_sayilari_json_yoksa_g_but_kalir_cikis_1(z: Zincir) -> None:
    """Sabit veri dosyasi okunamazsa kapi degerlendirilir ve kalir (zincir saglam)."""
    (z.kok / "shared" / "data" / "ayet-sayilari.json").unlink()
    sonuc = qa(z)
    assert sonuc.exit_code == 1
    assert "G-BUT kaldi: ayet-sayilari.json okunamadi" in sonuc.stdout


def test_vektor_dosyasi_yoksa_cikis_2(z: Zincir) -> None:
    (z.kok / "shared" / "test-vectors" / "normalize" / "ar.jsonl").unlink()
    cikis_2(z, "ar.jsonl okunamadi")


@pytest.mark.parametrize(
    ("argumanlar", "parca"),
    [
        (["--gate", "G-XYZ"], "--gate"),
        (["--gate", "g-kay"], "--gate"),
        (["--run", "uuid-degil"], "--run bir UUID degil"),
        (["--run", "01a19f8e-853e-714c-9f42-93b8ea1aa126"], "--run icin manifestli anchor"),
    ],
)
def test_hatali_bayraklar_cikis_2(z: Zincir, argumanlar: list[str], parca: str) -> None:
    cikis_2(z, parca, *argumanlar)


@pytest.mark.parametrize("kaynak", [EK_KAYNAK, "baska-kaynak"])
def test_desteklenmeyen_kaynak_cikis_2(z: Zincir, kaynak: str) -> None:
    sonuc = runner.invoke(cli.app, ["qa", "run", "--source", kaynak, "--kok", str(z.kok)])
    assert sonuc.exit_code == 2
    assert "tanimli degil" in sonuc.stderr


@pytest.mark.parametrize("bayrak", ["--dry-run", "--force", "--limit"])
def test_qa_icin_tanimsiz_bayraklar_reddedilir(z: Zincir, bayrak: str) -> None:
    sonuc = qa(z, bayrak, *(["5"] if bayrak == "--limit" else []))
    assert sonuc.exit_code == 2


def test_run_gecerli_uuid_baska_kaynagin_adimi_degil(z: Zincir) -> None:
    normalize = calismalar(z.ctx("qa", [KAYNAK]), KAYNAK, "normalize")[-1]
    cikis_2(z, "--run icin manifestli anchor", "--run", normalize.run_id)  # normalize != anchor


def test_hata_iletisi_gizli_icerik_tasimaz(z: Zincir) -> None:
    units = son_anchor(z).klasor / "units.jsonl"
    units.write_bytes(units.read_bytes() + b"Deneme gizli metin\n")
    sonuc = cikis_2(z, "ciktilari saglam degil")
    assert "gizli" not in sonuc.stderr + sonuc.stdout


def test_pg_komut_qa_kalinca_veritabanina_baglanmadan_cikis_1(z: Zincir) -> None:
    """`export pg`: QA kapisi kalmissa baglanti acilmaz, cikis 1."""
    from hat_yardimci import ayarlar_kur
    from test_export_pg import Cagrilmaz

    anchor_bozdur(z, hata_enjekte(lambda s: s.update(ord=0)))
    assert qa(z).exit_code == 1
    bag = Cagrilmaz()
    kod = pg.komut_export_pg(ayarlar_kur(z.tmp), depo_kok=z.kok, source=KAYNAK, baglanti=bag)
    assert kod == 1
    assert bag.sayi == 0


def test_qa_kapi_olaylari_kapi_adini_tasir(z: Zincir) -> None:
    assert qa(z).exit_code == 0
    rapor = son_qa_raporu(z)
    gunluk = (z.veri_kok / "logs" / f"{rapor['run_id']}.jsonl").read_bytes().decode("utf-8")
    olaylar = [json.loads(s) for s in gunluk.splitlines()]
    kapilar = [o for o in olaylar if o["olay"] == "qa_kapi"]
    assert [o["kapi"] for o in kapilar] == list(KAPILAR)
    assert all(o["source_id"] == KAYNAK and o["sayilar"] == {"bulgu": 0} for o in kapilar)
