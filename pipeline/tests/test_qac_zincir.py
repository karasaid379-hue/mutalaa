"""QAC zinciri: ingest qac -> enrich morphology -> qa run (A17.3; SENTETIK, veritabani yok).

Sentetik ust veri zinciri (`ust_veri_zinciri`, 6.236 ayet) kopyalanir; ustune sentetik bir QAC
dosyasi (kelime sayilari sentetik Tanzil bolmesiyle ayni), kilit ve kaynak kayitlari konur ve
adimlar gercek komut islevleriyle kosulur. Hicbir Kur'an metni yoktur; Arapca beklentiler
`enrich.buckwalter` donusumunden gelir.
"""

import dataclasses
import json
import re
from pathlib import Path

import pytest
from hat_yardimci import TEMIZ_GIT
from qac_yardimci import BILDIRIM, TARIH, QacZinciri, qac_hazirla
from typer.testing import CliRunner
from ust_veri_yardimci import UstVeriZinciri

from mutalaa_pipeline import cli, lineage
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.ingest import qac
from mutalaa_pipeline.lineage import DALGALAR_ADI, KELIMELER_ADI, KOKLER_ADI, LEMMALAR_ADI
from mutalaa_pipeline.qa import run_qac
from mutalaa_pipeline.qa.checks.qac import KAPI_ISLEVLERI, QacGirdisi, g_but, g_cap, g_kay, olcumler
from mutalaa_pipeline.qa.qac_capraz import KAYNAK as CAPRAZ_KAYNAGI
from mutalaa_pipeline.staged import Satir

runner = CliRunner()
KAYNAK = "qac-morfoloji"
CIKTILAR = (KELIMELER_ADI, LEMMALAR_ADI, KOKLER_ADI, DALGALAR_ADI)


@pytest.fixture
def qz(
    ust_veri_zinciri: UstVeriZinciri, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> QacZinciri:
    return qac_hazirla(ust_veri_zinciri, tmp_path / "t", monkeypatch)


def staged_klasorleri(qz: QacZinciri, kaynak: str = KAYNAK) -> list[Path]:
    kok = qz.z.veri_kok / "staged" / kaynak
    return sorted(p for p in kok.iterdir() if p.is_dir()) if kok.is_dir() else []


def son_qa_raporu(qz: QacZinciri) -> dict[str, object]:
    adaylar = [
        json.loads(r.read_bytes())
        for r in sorted((qz.z.veri_kok / "reports").glob("*.json"))
        if not r.name.endswith("-capraz.json")
    ]
    return [r for r in adaylar if r.get("komut") == "qa run" and r.get("kaynak") == KAYNAK][-1]  # type: ignore[no-any-return]


def girdi(qz: QacZinciri) -> QacGirdisi:
    ctx = qz.ctx("qa", [KAYNAK])
    kayitlar = ctx.require_sources((KAYNAK, "tanzil-ust-veri", CAPRAZ_KAYNAGI))
    return run_qac.yukle(ctx, kayitlar, run=None)[0]


# --- ingest ------------------------------------------------------------------------------


def test_ingest_ham_kopya_notice_ve_manifest(qz: QacZinciri) -> None:
    assert qz.ingest() == 0
    ham = qz.z.veri_kok / "raw" / KAYNAK / TARIH / qac.DOSYA_ADI
    assert ham.read_bytes() == qz.ham  # data/raw bayt bayt (CRLF dahil), degismez
    (klasor,) = staged_klasorleri(qz)
    manifest = lineage.manifest_oku(klasor)
    assert manifest is not None and manifest["adim"] == "ingest"
    assert (klasor / "notice.txt").read_bytes() == qac.ayristir(qz.ham).bildirim_baytlari()
    ayrinti = manifest["ayrintilar"]
    assert isinstance(ayrinti, dict) and ayrinti["sayilar"]["kelime"] == len(
        qz.staged("tanzil-uthmani", KELIMELER_ADI)
    )


def test_ingest_kilit_uyusmazligi_cikis_2_ve_raw_bos(qz: QacZinciri) -> None:
    gelen = qz.z.veri_kok / "gelen" / KAYNAK / TARIH / qac.DOSYA_ADI
    gelen.write_bytes(qz.ham + b"# fazla\r\n")
    assert qz.ingest() == 2
    assert not (qz.z.veri_kok / "raw" / KAYNAK).exists()
    assert staged_klasorleri(qz) == []


def test_ingest_kayitsiz_kaynak_cikis_2(qz: QacZinciri) -> None:
    (qz.z.kok / "pipeline" / "sources" / f"{KAYNAK}.toml").unlink()
    assert qz.ingest() == 2
    assert not (qz.z.veri_kok / "raw" / KAYNAK).exists()


def test_ingest_ham_ayni_tarihte_farkli_bayt_degismez(qz: QacZinciri) -> None:
    assert qz.ingest() == 0
    ham = qz.z.veri_kok / "raw" / KAYNAK / TARIH / qac.DOSYA_ADI
    ham.write_bytes(ham.read_bytes() + b"x")  # raw'in bozuldugunu varsay
    yeni = qz.z.veri_kok / "gelen" / KAYNAK / TARIH / qac.DOSYA_ADI
    assert yeni.read_bytes() == qz.ham
    assert qz.ingest(force=True) == 2  # ayni tarih klasoru baska baytlarla dolu: raw degismez


def test_ingest_dry_run_hicbir_sey_yazmaz(qz: QacZinciri) -> None:
    assert qz.ingest(dry_run=True) == 0
    assert not (qz.z.veri_kok / "raw" / KAYNAK).exists()
    assert staged_klasorleri(qz) == []


# --- enrich ------------------------------------------------------------------------------


def test_enrich_ingest_olmadan_cikis_2(qz: QacZinciri) -> None:
    assert qz.enrich() == 2


def test_enrich_dosyalari_ve_sayilari(qz: QacZinciri) -> None:
    assert qz.ingest() == 0
    assert qz.enrich() == 0
    kelimeler = qz.staged(KAYNAK, KELIMELER_ADI)
    tanzil = qz.staged("tanzil-uthmani", KELIMELER_ADI)
    assert len(kelimeler) == len(tanzil)
    capalar = [str(k["anchor"]) for k in kelimeler]
    assert capalar == sorted(set(capalar), key=lambda c: tuple(int(x) for x in c[2:].split(":")))
    lemmalar = qz.staged(KAYNAK, LEMMALAR_ADI)
    assert [
        lm["ilk_gecis"] for lm in sorted(lemmalar, key=lambda x: int(str(x["ilk_gecis"])))
    ] == list(range(1, len(lemmalar) + 1))
    assert not any("id" in lm for lm in lemmalar)  # kimlik tasimaz: export pg atar
    dalgalar = qz.staged(KAYNAK, DALGALAR_ADI)
    assert {d["qac_ref"] for d in dalgalar} == {lm["qac_ref"] for lm in lemmalar}
    assert {d["dalga"] for d in dalgalar} <= {0, 1, 2, 3, 4}
    toplam = sum(int(str(lm["occurrences"])) for lm in lemmalar)
    assert toplam == sum(1 for k in kelimeler if k["lemma_qac_ref"] is not None)
    ayirt = [lm for lm in lemmalar if lm["ayirt_no"] is not None]
    assert ayirt and all(str(lm["qac_ref"]).endswith("2") for lm in ayirt)
    (klasor,) = [k for k in staged_klasorleri(qz) if (k / DALGALAR_ADI).is_file()]
    manifest = lineage.manifest_oku(klasor)
    assert manifest is not None and manifest["adim"] == "anchor"  # zincir adi: anchor
    assert manifest["komut"] == "enrich morphology"
    assert {c["yol"].rsplit("/", 1)[-1] for c in manifest["ciktilar"]} == set(CIKTILAR)  # type: ignore[index,union-attr]


def test_enrich_iki_calistirma_ayni_baytlar(qz: QacZinciri) -> None:
    assert qz.ingest() == 0
    assert qz.enrich() == 0
    assert qz.enrich(force=True) == 0
    bir, iki = [k for k in staged_klasorleri(qz) if (k / DALGALAR_ADI).is_file()]
    for ad in CIKTILAR:
        assert (bir / ad).read_bytes() == (iki / ad).read_bytes(), ad
        assert b"\r" not in (bir / ad).read_bytes()
        assert (bir / ad).read_bytes().isascii()


def test_enrich_parmak_izi_ayniysa_atlanir(qz: QacZinciri, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(lineage, "git_durumu", lambda _kok: TEMIZ_GIT)
    assert qz.ingest() == 0
    assert qz.enrich() == 0
    sayi = len(staged_klasorleri(qz))
    assert qz.enrich() == 0  # ayni girdiler: atlandi, yeni klasor yok
    assert len(staged_klasorleri(qz)) == sayi
    assert qz.enrich(force=True) == 0
    assert len(staged_klasorleri(qz)) == sayi + 1


def test_enrich_dry_run_yazmaz(qz: QacZinciri) -> None:
    assert qz.ingest() == 0
    once = len(staged_klasorleri(qz))
    assert qz.enrich(dry_run=True) == 0
    assert len(staged_klasorleri(qz)) == once


def test_enrich_gecersiz_konumda_cikis_2(
    ust_veri_zinciri: UstVeriZinciri, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    baslik = BILDIRIM.replace("\n", "\r\n") + "\r\n\r\nLOCATION\tFORM\tTAG\tFEATURES\r\n"
    ham = baslik.encode()
    ham += b"(115:1:1:1)\tDeneme\tN\tSTEM|POS:N|LEM:bab\r\n"  # sure 115 yok
    qz = qac_hazirla(ust_veri_zinciri, tmp_path / "t", monkeypatch, ham=ham, mustafa0x=False)
    assert qz.ingest() == 0
    assert qz.enrich() == 2


# --- QA ----------------------------------------------------------------------------------


def _hazir(qz: QacZinciri) -> None:
    assert qz.ingest() == 0
    assert qz.enrich() == 0


def test_qa_uc_kapi_gecer_ve_rapor_yazar(qz: QacZinciri) -> None:
    qz.hepsi()
    rapor = son_qa_raporu(qz)
    assert rapor["komut"] == "qa run" and rapor["kaynak"] == KAYNAK
    assert rapor["kapilar"] == {"G-KAY": "gecti", "G-BUT": "gecti", "G-CAP": "gecti"}
    assert rapor["olcumler"]["capraz"]["durum"] == "yapildi"
    assert (
        rapor["olcumler"]["etiket_sayfada_olmayan"] == []
    )  # sentetik dosyada yalniz sayfa etiketleri
    assert rapor["olcumler"]["ayirt_rakamli_lemma"] > 0
    assert rapor["kapi_sayilari"]["G-BUT"]["ayet_kelime_farki"] == 0
    assert rapor["units_sha256"] and rapor["anchor_run_id"]


def test_qa_ikinci_kosu_ayni_ozet(qz: QacZinciri) -> None:
    qz.hepsi()
    assert qz.qa() == 0
    raporlar = [
        json.loads(r.read_bytes())
        for r in sorted((qz.z.veri_kok / "reports").glob("*.json"))
        if not r.name.endswith("-capraz.json")
    ]
    qa = [r for r in raporlar if r["komut"] == "qa run" and r.get("kaynak") == KAYNAK]
    assert len(qa) == 2
    anahtarlar = ("kapilar", "kapi_bulgulari", "kapi_sayilari", "olcumler", "anchor_run_id")
    assert all(qa[0][a] == qa[1][a] for a in anahtarlar)


def test_qa_rapor_metin_icermez(qz: QacZinciri) -> None:
    qz.hepsi()
    lemmalar = qz.staged(KAYNAK, LEMMALAR_ADI)
    arapca = {str(lm["text"]) for lm in lemmalar} | {str(lm["text_clean"]) for lm in lemmalar}
    kokler = {str(k["letters"]) for k in qz.staged(KAYNAK, KOKLER_ADI)}
    yasak = {json.dumps(m)[1:-1] for m in arapca | kokler}  # ASCII kacisli hallerinden
    for rapor in (qz.z.veri_kok / "reports").glob("*.json"):
        metin = rapor.read_bytes().decode("utf-8")
        assert metin.isascii()
        assert not re.search(r"\\u0[67][0-9a-f]{2}", metin), rapor.name  # Arapca blok yok
        assert not any(y in metin for y in yasak), rapor.name
    for gunluk in (qz.z.veri_kok / "logs").glob("*"):
        metin = gunluk.read_bytes().decode("utf-8", "replace")
        assert not any(m in metin for m in arapca), gunluk.name


def test_qa_capraz_farklar_yalniz_kimlik_ve_sayi(
    ust_veri_zinciri: UstVeriZinciri, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    qz = qac_hazirla(ust_veri_zinciri, tmp_path / "t", monkeypatch)
    kopya = qz.z.veri_kok / "gelen" / CAPRAZ_KAYNAGI / TARIH
    icerik = (kopya / "quran-morphology.txt").read_bytes().decode("utf-8")
    # ilk ROOT degerinin son harfini degistir: bir kok farki dogar (yalniz kopya degisir)
    degisik = re.sub(
        r"ROOT:(\S)(\S+?)\|", lambda m: f"ROOT:{m.group(1)}{m.group(2)}x|", icerik, count=1
    )
    assert degisik != icerik
    veri = degisik.encode("utf-8")
    (kopya / "quran-morphology.txt").write_bytes(veri)
    import hashlib

    (kopya / "SHA256SUMS").write_bytes(
        f"{hashlib.sha256(veri).hexdigest()} *quran-morphology.txt\n".encode()
    )
    qz.hepsi()  # capraz fark kapi degildir
    farklar = sorted((qz.z.veri_kok / "reports").glob("*-capraz.json"))
    assert len(farklar) == 1
    belge = json.loads(farklar[0].read_bytes())
    assert belge["sayilar"]["kok_farkli"] >= 1 and belge["kok_farkli_letters_bw"]
    assert set(belge) == {
        "run_id",
        "kaynak",
        "kopya",
        "kopya_tarih",
        "sayilar",
        "lemma_farkli_qac_ref",
        "kok_farkli_letters_bw",
        "ornek_capalar",
    }
    assert all(re.fullmatch(r"q:[0-9]+:[0-9]+:[0-9]+", c) for c in belge["ornek_capalar"])
    assert farklar[0].read_bytes().isascii()


def test_qa_capraz_kopya_yoksa_atlanir(
    ust_veri_zinciri: UstVeriZinciri, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    qz = qac_hazirla(ust_veri_zinciri, tmp_path / "t", monkeypatch, mustafa0x=False)
    qz.hepsi()
    assert not list((qz.z.veri_kok / "reports").glob("*-capraz.json"))
    rapor = son_qa_raporu(qz)
    assert rapor["olcumler"]["capraz"] == {"durum": "atlandi"}
    assert any("capraz sayim atlandi" in u for u in rapor["uyarilar"])


def test_qa_zincir_hatasi_cikis_2(qz: QacZinciri) -> None:
    _hazir(qz)
    for klasor in staged_klasorleri(qz):
        if (klasor / DALGALAR_ADI).is_file():
            (klasor / DALGALAR_ADI).write_bytes(b"{}\n")  # cikti ozeti manifestle tutmuyor
    assert qz.qa() == 2


def test_qa_enrich_olmadan_cikis_2(qz: QacZinciri) -> None:
    assert qz.ingest() == 0
    assert qz.qa() == 2


def test_qa_gate_secimi(qz: QacZinciri) -> None:
    qz.hepsi()
    assert run_qac.kapilari_sec(["G-CAP", "G-KAY"]) == ("G-KAY", "G-CAP")
    with pytest.raises(GirdiHatasi):
        run_qac.kapilari_sec(["G-NOR"])
    assert KAPI_ISLEVLERI.keys() == {"G-KAY", "G-BUT", "G-CAP"}


# --- kapi kusurlari (bellekte) -----------------------------------------------------------


def _satir(s: Satir, **alan: object) -> Satir:
    return Satir(s.etiket, s.no, {**s.veri, **alan})


def test_g_kay_kusurlari(qz: QacZinciri) -> None:
    _hazir(qz)
    g = girdi(qz)
    assert g_kay(g).gecti
    farkli_kayit = dataclasses.replace(g.kayit, notice_text=(g.kayit.notice_text or "") + "x")
    assert not g_kay(dataclasses.replace(g, kayit=farkli_kayit)).gecti
    assert not g_kay(
        dataclasses.replace(g, kayit=dataclasses.replace(g.kayit, notice_text=None))
    ).gecti
    assert not g_kay(dataclasses.replace(g, bildirim_dosyasi=b"baska")).gecti
    assert not g_kay(dataclasses.replace(g, bildirim_dosyasi=None)).gecti
    assert not g_kay(dataclasses.replace(g, kayit=dataclasses.replace(g.kayit, surum="0.5"))).gecti
    assert not g_kay(dataclasses.replace(g, ham_sha256="0" * 64)).gecti
    assert not g_kay(
        dataclasses.replace(g, kilit=dataclasses.replace(g.kilit, url="https://baska.invalid/"))
    ).gecti


def test_g_but_kusurlari(qz: QacZinciri) -> None:
    _hazir(qz)
    g = girdi(qz)
    assert g_but(g).gecti
    # Tanzil bolmesinden bir kelime eksik: ayet basina kelime farki
    eksik = dataclasses.replace(g, tanzil_kelime_satirlari=list(g.tanzil_kelime_satirlari)[:-1])
    sonuc = g_but(eksik)
    assert not sonuc.gecti and sonuc.sayilar["ayet_kelime_farki"] == 1
    # staged kelime satiri ham dosyadan yeniden uretilenden farkli
    satirlar = list(g.kelime_satirlari)
    satirlar[0] = _satir(satirlar[0], pos="XX")
    assert not g_but(dataclasses.replace(g, kelime_satirlari=satirlar)).gecti
    # satir eksik
    assert not g_but(dataclasses.replace(g, kelime_satirlari=satirlar[1:])).gecti
    # kelime satirinin kok referansi lemma envanteriyle tutarsiz
    lemmali = next(i for i, s in enumerate(g.kelime_satirlari) if s.veri["lemma_qac_ref"])
    bozuk = list(g.kelime_satirlari)
    bozuk[lemmali] = _satir(bozuk[lemmali], root_letters_bw="yok")
    sonuc2 = g_but(dataclasses.replace(g, kelime_satirlari=bozuk))
    assert not sonuc2.gecti and sonuc2.sayilar["lemma_tutarsiz"] >= 1
    # Fatiha/30. cuz lemmasi dalga 2'ye alinmis
    ozel = next(
        s.veri["lemma_qac_ref"]
        for s in g.kelime_satirlari
        if s.veri["surah"] == 1 and s.veri["lemma_qac_ref"]
    )
    dalgalar = [_satir(d, dalga=2) if d.veri["qac_ref"] == ozel else d for d in g.dalga_satirlari]
    assert not g_but(dataclasses.replace(g, dalga_satirlari=dalgalar)).gecti
    # kelime numarasi bosluklu: (sure, ayet) icinde bir numara atlanmis
    kopuk = [s for s in g.kelime_satirlari if not (s.veri["surah"] == 1 and s.veri["word"] == 2)]
    assert not g_but(dataclasses.replace(g, kelime_satirlari=kopuk)).gecti


def test_g_cap_kusurlari(qz: QacZinciri) -> None:
    _hazir(qz)
    g = girdi(qz)
    assert g_cap(g).gecti
    satirlar = list(g.kelime_satirlari)
    for kotu in ("q:2:255", "q:2:255:3-7", "Q:1:1:1", "q:115:1:1", "q:01:1:1"):
        degisik = [_satir(satirlar[0], anchor=kotu), *satirlar[1:]]
        assert not g_cap(dataclasses.replace(g, kelime_satirlari=degisik)).gecti, kotu
    ikiz = [*satirlar, satirlar[0]]
    assert not g_cap(dataclasses.replace(g, kelime_satirlari=ikiz)).gecti
    sirasiz = [satirlar[1], satirlar[0], *satirlar[2:]]
    assert not g_cap(dataclasses.replace(g, kelime_satirlari=sirasiz)).gecti
    uyumsuz = [_satir(satirlar[0], word=99), *satirlar[1:]]
    assert not g_cap(dataclasses.replace(g, kelime_satirlari=uyumsuz)).gecti
    yanlis_surum = [_satir(satirlar[0], data_version="x"), *satirlar[1:]]
    assert not g_cap(dataclasses.replace(g, kelime_satirlari=yanlis_surum)).gecti
    lemmalar = [*g.lemma_satirlari, g.lemma_satirlari[0]]
    assert not g_cap(dataclasses.replace(g, lemma_satirlari=lemmalar)).gecti
    assert not g_cap(dataclasses.replace(g, dalga_satirlari=list(g.dalga_satirlari)[1:])).gecti


def test_olcumler_metin_icermez(qz: QacZinciri) -> None:
    _hazir(qz)
    olcum = olcumler(girdi(qz))
    metin = json.dumps(olcum)
    assert metin.isascii() and "\\u06" not in metin
    assert olcum["iki_govdeli_kelime"] > 0 and olcum["lemmasiz_kelime"] > 0
    assert sum(olcum["dalga"].values()) == olcum["lemma"]  # type: ignore[union-attr]


def test_qa_kaldi_kodu_1(qz: QacZinciri) -> None:
    qz.hepsi()
    # sentetik kayitin notice_text'ini bozar: G-KAY kalir, komut 1 ile cikar
    yol = qz.z.kok / "pipeline" / "sources" / f"{KAYNAK}.toml"
    yol.write_bytes(yol.read_bytes().replace(b"DENEME", b"DEGISIK"))
    assert qz.qa() == 1


# --- komut satiri ------------------------------------------------------------------------


def test_cli_komutlari_kayitli(qz: QacZinciri) -> None:
    sonuc = runner.invoke(cli.app, ["enrich", "--help"])
    assert sonuc.exit_code == 0 and "morphology" in sonuc.output
    assert "qac" in runner.invoke(cli.app, ["ingest", "--help"]).output
    kok = str(qz.z.kok)
    oner = runner.invoke(cli.app, ["ingest", "qac", "--kilit-oner", "--kok", kok])
    assert oner.exit_code == 0
    kilit = qac.kilit_coz(oner.output.replace("\r\n", "\n").encode())
    assert kilit.sha256 == qac.kilit_onerisi(qz.ham, TARIH, kilit.url, "0.4").sha256
    assert (
        runner.invoke(cli.app, ["ingest", "qac", "--kilit-oner", "--force", "--kok", kok]).exit_code
        == 2
    )
    assert runner.invoke(cli.app, ["ingest", "qac", "--kok", kok]).exit_code == 0
    assert runner.invoke(cli.app, ["enrich", "morphology", "--kok", kok]).exit_code == 0
    assert runner.invoke(cli.app, ["qa", "run", "--source", KAYNAK, "--kok", kok]).exit_code == 0
