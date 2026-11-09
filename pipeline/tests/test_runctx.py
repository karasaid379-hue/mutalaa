"""`runctx`: UUIDv7, kaynak kaydi denetimi (cikis 2), komut sarmalayici ve sizinti kurali."""

import itertools
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from hat_yardimci import PAROLA, SAHTE_DSN, ctx_kur, depo_kur
from test_sources import alanlar_kur, kayit_yaz

from mutalaa_pipeline import cikis, runctx
from mutalaa_pipeline.db import VeritabaniHatasi, baglan
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.lineage import Cikti, Girdi
from mutalaa_pipeline.runctx import (
    QaKaldi,
    RunContext,
    Uuid7Uretici,
    cikis_kodu,
    komut_calistir,
    uuid7,
)

# --- UUIDv7 ------------------------------------------------------------------------------


class SahteSaat:
    def __init__(self, ms: int) -> None:
        self.ms = ms

    def __call__(self) -> int:
        return self.ms


def test_uuid7_surum_ve_varyant_bitleri() -> None:
    u = Uuid7Uretici(SahteSaat(1_700_000_000_123)).uret()
    assert u.version == 7
    assert u.variant == uuid.RFC_4122
    assert (u.int >> 76) & 0xF == 0x7
    assert (u.int >> 62) & 0b11 == 0b10
    assert u.int >> 80 == 1_700_000_000_123
    assert str(u)[14] == "7"
    assert str(u)[19] in "89ab"


def test_uuid7_zaman_sirasi() -> None:
    saat = SahteSaat(1_000)
    uretici = Uuid7Uretici(saat)
    liste = []
    for ms in (1_000, 1_001, 5_000, 70_000_000_000):
        saat.ms = ms
        liste.append(str(uretici.uret()))
    assert liste == sorted(liste)
    assert len(set(liste)) == 4


def test_uuid7_ayni_milisaniyede_monoton() -> None:
    uretici = Uuid7Uretici(SahteSaat(1_000))
    liste = [str(uretici.uret()) for _ in range(5000)]  # sayac tasmasini da asar
    assert liste == sorted(liste)
    assert len(set(liste)) == len(liste)


def test_uuid7_saat_geri_gidince_monoton() -> None:
    saat = SahteSaat(10_000)
    uretici = Uuid7Uretici(saat)
    ilk = uretici.uret()
    saat.ms = 9_000
    ikinci = uretici.uret()
    assert str(ikinci) > str(ilk)
    assert ikinci.version == 7


def test_uuid7_sayac_tasarsa_zaman_ilerler() -> None:
    uretici = Uuid7Uretici(SahteSaat(1_000), rastgele=lambda bit: (1 << bit) - 1)
    ilk = uretici.uret()
    liste = [uretici.uret() for _ in range(3000)]
    tum = [ilk, *liste]
    assert all(str(b) > str(a) for a, b in itertools.pairwise(tum))
    assert liste[-1].int >> 80 > ilk.int >> 80


def test_uuid7_modul_islevi() -> None:
    a, b = uuid7(), uuid7()
    assert a.version == 7
    assert str(b) > str(a)


def test_run_id_uuid7_metni(tmp_path: Path) -> None:
    kok = depo_kur(tmp_path)
    ctx = ctx_kur(tmp_path, kok)
    parsed = uuid.UUID(ctx.run_id)
    assert parsed.version == 7
    assert ctx.run_id == str(parsed)


# --- require_sources -----------------------------------------------------------------------


def test_require_sources_gecerli_kaynak(tmp_path: Path) -> None:
    kok = depo_kur(tmp_path, "test-bir", "test-iki")
    ctx = ctx_kur(tmp_path, kok)
    sonuc = ctx.require_sources(["test-bir", "test-iki"])
    assert set(sonuc) == {"test-bir", "test-iki"}
    assert sonuc["test-bir"].atif_metni
    assert set(ctx.require_sources("test-bir")) == {"test-bir"}
    assert list(ctx.require_sources(["test-iki", "test-bir", "test-iki"])) == [
        "test-iki",
        "test-bir",
    ]


def test_require_sources_kayitsiz_girdi_hatasi(tmp_path: Path) -> None:
    kok = depo_kur(tmp_path, "test-acik")
    ctx = ctx_kur(tmp_path, kok)
    with pytest.raises(GirdiHatasi) as hata:
        ctx.require_sources("test-yok")
    assert "kayitsiz" in str(hata.value)
    assert cikis_kodu(hata.value) == cikis.GIRDI_HATASI
    # bir kaynak bile kayitsizsa hepsi durur
    with pytest.raises(GirdiHatasi):
        ctx.require_sources(["test-acik", "test-yok"])


def test_require_sources_sema_hatali_kayit(tmp_path: Path) -> None:
    kok = depo_kur(tmp_path)
    kayit_yaz(kok, alanlar_kur("test-bozuk", atif_metni=None))
    with pytest.raises(GirdiHatasi) as hata:
        ctx_kur(tmp_path, kok).require_sources("test-bozuk")
    assert "gecersiz" in str(hata.value)
    assert cikis_kodu(hata.value) == cikis.GIRDI_HATASI


def test_require_sources_bos_atif_metni_gecersiz(tmp_path: Path) -> None:
    kok = depo_kur(tmp_path)
    kayit_yaz(kok, alanlar_kur("test-bos", atif_metni="  "))
    with pytest.raises(GirdiHatasi):
        ctx_kur(tmp_path, kok).require_sources("test-bos")


def test_require_sources_eski_lisans_alani_gecersiz(tmp_path: Path) -> None:
    kok = depo_kur(tmp_path)
    kayit_yaz(kok, alanlar_kur("test-eski", license_status="serbest"))
    with pytest.raises(GirdiHatasi) as hata:
        ctx_kur(tmp_path, kok).require_sources("test-eski")
    assert "gecersiz" in str(hata.value)


def test_require_sources_bos_liste_girdi_hatasi(tmp_path: Path) -> None:
    ctx = ctx_kur(tmp_path, depo_kur(tmp_path))
    with pytest.raises(GirdiHatasi):
        ctx.require_sources([])


def test_require_sources_iletide_ascii_disi_slug_kacirilir(tmp_path: Path) -> None:
    ctx = ctx_kur(tmp_path, depo_kur(tmp_path))
    with pytest.raises(GirdiHatasi) as hata:
        ctx.require_sources("test-çok")
    assert str(hata.value).isascii()


def test_cikis_kodlari() -> None:
    assert cikis_kodu(QaKaldi("x")) == cikis.QA_KALDI == 1
    assert cikis_kodu(GirdiHatasi("x")) == cikis.GIRDI_HATASI == 2
    assert cikis_kodu(RuntimeError("x")) == cikis.GIRDI_HATASI


def test_cikis_kodu_kumesi_sifir_bir_iki() -> None:
    kodlar = {deger for ad, deger in vars(cikis).items() if ad.isupper() and isinstance(deger, int)}
    assert kodlar == {0, 1, 2}
    assert (cikis.BASARILI, cikis.QA_KALDI, cikis.GIRDI_HATASI) == (0, 1, 2)


def test_lisans_kapisi_kalmadi() -> None:
    """K-42: lisans kapisi, `require_status` ve cikis kodu 3 kalkti."""
    assert not hasattr(runctx, "LisansKapisi")
    assert not hasattr(runctx, "IZINLI_DURUMLAR")
    assert not hasattr(RunContext, "require_status")
    assert not hasattr(RunContext, "lisans_kopyalari")
    assert not hasattr(cikis, "LISANS_KAPISI")


def gec(c: RunContext, kaynak: str) -> None:
    c.require_sources(kaynak)


def test_komut_calistir_kayitsiz_kaynak_cikis_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    ctx = ctx_kur(tmp_path, depo_kur(tmp_path), kaynaklar=["test-yok"])
    assert komut_calistir(ctx, lambda c: gec(c, "test-yok")) == 2
    assert "kayitsiz" in capsys.readouterr().err
    rapor = (tmp_path / "data" / "reports" / f"{ctx.run_id}.json").read_text(encoding="utf-8")
    assert '"cikis_kodu": 2' in rapor
    assert '"durum": "basarisiz"' in rapor


def test_komut_calistir_gecersiz_kayit_cikis_2(tmp_path: Path) -> None:
    kok = depo_kur(tmp_path)
    kayit_yaz(kok, alanlar_kur("test-bozuk", atif_metni=None))
    ctx = ctx_kur(tmp_path, kok, kaynaklar=["test-bozuk"])
    assert komut_calistir(ctx, lambda c: gec(c, "test-bozuk")) == 2


def test_komut_calistir_basarili_ve_qa(tmp_path: Path) -> None:
    kok = depo_kur(tmp_path)
    assert komut_calistir(ctx_kur(tmp_path, kok), lambda c: None) == 0

    def qa(c: RunContext) -> None:
        raise QaKaldi("G-BUT kaldi")

    assert komut_calistir(ctx_kur(tmp_path, kok), qa) == 1

    def girdi(c: RunContext) -> None:
        raise GirdiHatasi("kotu girdi")

    assert komut_calistir(ctx_kur(tmp_path, kok), girdi) == 2


def test_komut_calistir_donus_kodu_korunur(tmp_path: Path) -> None:
    assert komut_calistir(ctx_kur(tmp_path, depo_kur(tmp_path)), lambda c: 1) == 1


# --- Sizinti kurali -------------------------------------------------------------------------


def dosyalarda_ara(klasor: Path, ifade: str) -> list[str]:
    bulunan = []
    for yol in klasor.rglob("*"):
        if yol.is_file() and ifade.encode() in yol.read_bytes():
            bulunan.append(yol.name)
    return bulunan


def test_dsn_stderr_gunluk_rapor_manifest_parmak_izinde_gorunmez(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    kok = depo_kur(tmp_path, "test-kaynak")
    ctx = ctx_kur(tmp_path, kok, kaynaklar=["test-kaynak"], db_url=SAHTE_DSN)

    def govde(c: RunContext) -> None:
        c.gunluk.yaz("INFO", f"baglanti {SAHTE_DSN}", sayilar={"n": 1})
        c.gunluk.yaz("INFO", "parola " + PAROLA)
        c.uyar(f"uyari {SAHTE_DSN}")
        c.parametreler["adres"] = SAHTE_DSN
        izi = c.parmak_izi([Girdi("raw/x/a.txt", "a" * 64)])
        assert isinstance(izi, str)
        c.manifest_yaz(
            tmp_path / "data" / "staged" / "test-kaynak" / c.run_id,
            girdiler=[Girdi("raw/x/a.txt", "a" * 64)],
            ciktilar=[Cikti("staged/x/units.jsonl", "b" * 64, 1)],
            parmak=izi,
        )
        raise GirdiHatasi(f"baglanti kurulamadi: {SAHTE_DSN} / password={PAROLA}")

    assert komut_calistir(ctx, govde) == 2
    yakalanan = capsys.readouterr()
    assert PAROLA not in yakalanan.err + yakalanan.out
    assert "hata:" in yakalanan.err
    assert dosyalarda_ara(tmp_path / "data", PAROLA) == []
    assert dosyalarda_ara(tmp_path / "data", "@127.0.0.1") == []
    assert (tmp_path / "data" / "logs" / f"{ctx.run_id}.jsonl").is_file()
    assert (tmp_path / "data" / "reports" / f"{ctx.run_id}.json").is_file()
    manifest = tmp_path / "data" / "staged" / "test-kaynak" / ctx.run_id / "manifest.json"
    assert manifest.is_file()
    assert b"lisans" not in manifest.read_bytes()  # K-42: manifest lisans kopyasi tasimaz


def test_beklenmeyen_hata_yalniz_tur_adi_yazar(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    ctx = ctx_kur(tmp_path, depo_kur(tmp_path), db_url=SAHTE_DSN)

    def govde(c: RunContext) -> None:
        raise RuntimeError(SAHTE_DSN)

    assert komut_calistir(ctx, govde) == 2
    err = capsys.readouterr().err
    assert "RuntimeError" in err
    assert PAROLA not in err


def test_ascii_disi_hata_iletisi_gizlenir(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    ctx = ctx_kur(tmp_path, depo_kur(tmp_path))

    def govde(c: RunContext) -> None:
        raise GirdiHatasi("satir 3: Deneme çş metni")

    assert komut_calistir(ctx, govde) == 2
    err = capsys.readouterr().err
    assert "ç" not in err
    assert "ileti gizlendi" in err


def test_baglan_hatasi_iletide_dsn_yok(tmp_path: Path) -> None:
    ayarlar = ctx_kur(tmp_path, depo_kur(tmp_path), db_url=SAHTE_DSN).ayarlar
    with pytest.raises(VeritabaniHatasi) as hata:
        baglan(ayarlar, zaman_asimi=1)  # 127.0.0.1:1 dinlemez
    assert PAROLA not in str(hata.value)
    assert "127.0.0.1" not in str(hata.value)
    assert hata.value.__cause__ is None
    with pytest.raises(VeritabaniHatasi) as hata_test:
        baglan(ayarlar, test=True, zaman_asimi=1)
    assert PAROLA not in str(hata_test.value)


def test_baglan_db_url_yoksa_girdi_hatasi(tmp_path: Path) -> None:
    ayarlar = ctx_kur(tmp_path, depo_kur(tmp_path)).ayarlar
    with pytest.raises(GirdiHatasi):
        baglan(ayarlar)


def test_rapor_alanlari(tmp_path: Path) -> None:
    sabit = datetime(2026, 10, 28, 12, 0, 0, tzinfo=UTC)
    saatler = iter([sabit + timedelta(seconds=n) for n in range(100)])
    ctx = ctx_kur(tmp_path, depo_kur(tmp_path), saat=lambda: next(saatler))
    ctx.sayi("birim", 3)
    ctx.uyar("deneme uyarisi")
    yol = ctx.rapor_yaz("tamam", 0)
    assert yol == tmp_path / "data" / "reports" / f"{ctx.run_id}.json"
    veri = yol.read_text(encoding="utf-8")
    assert '"sayilar": {\n    "birim": 3\n  }' in veri
    assert "deneme uyarisi" in veri
    assert "sure_sn" in veri
    assert not list((tmp_path / "data" / "reports").glob("*.tmp"))


def test_rapor_yeniden_adlandirmadan_once_diske_esitlenir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Guc kesilirse sifir uzunluklu en yeni rapor kalmasin: fsync, os.replace'ten once."""
    olaylar: list[str] = []
    gercek_fsync = runctx.os.fsync
    gercek_replace = runctx.os.replace

    def fsync(fd: int) -> None:
        olaylar.append("fsync")
        gercek_fsync(fd)

    def replace(kaynak: object, hedef: object) -> None:
        olaylar.append("replace")
        gercek_replace(kaynak, hedef)  # type: ignore[arg-type]

    monkeypatch.setattr(runctx.os, "fsync", fsync)
    monkeypatch.setattr(runctx.os, "replace", replace)
    ctx = ctx_kur(tmp_path, depo_kur(tmp_path))
    ctx.rapor_yaz("tamam", 0)
    assert olaylar == ["fsync", "replace"]


def test_rapor_gecici_izin_hatasinda_yeniden_denenir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """OneDrive hedefi kisa sure tutarsa `os.replace` PermissionError verir: rapor yine yazilir."""
    gercek, cagri = runctx.os.replace, []

    def replace(kaynak: object, hedef: object) -> None:
        cagri.append(1)
        if len(cagri) < 3:
            raise PermissionError(13, "erisim engellendi")
        gercek(kaynak, hedef)  # type: ignore[arg-type]

    monkeypatch.setattr(runctx.os, "replace", replace)
    monkeypatch.setattr(runctx.lineage.time, "sleep", lambda _s: None)
    ctx = ctx_kur(tmp_path, depo_kur(tmp_path))
    yol = ctx.rapor_yaz("tamam", 0)
    assert len(cagri) == 3
    assert yol.is_file()
    assert not yol.with_name(yol.name + ".tmp").exists()
