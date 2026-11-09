"""`lineage`: manifest, parmak izi, atomik yazim, son basarili calistirma (SENTETIK)."""

import hashlib
import inspect
import json
import os
from pathlib import Path

import pytest
from hat_yardimci import SAHTE_DSN, ayarlar_kur, ctx_kur, depo_kur

from mutalaa_pipeline import lineage
from mutalaa_pipeline.config import Ayarlar
from mutalaa_pipeline.lineage import Cikti, Girdi, GitDurumu
from mutalaa_pipeline.runctx import Uuid7Uretici

GIRDI = Girdi("raw/test-kaynak/2026-10-28/dosya.txt", "a" * 64, "ust-run")
CIKTI = Cikti("staged/test-kaynak/RUN/units.jsonl", "b" * 64, 2)
ARACLAR = {"normalizer_version": "1.0", "psycopg": "3.3.6", "snowballstemmer": "3.1.1"}


def manifest_kur(run_id: str = "00000000-0000-7000-8000-000000000001") -> dict[str, object]:
    return lineage.manifest_kur(
        run_id=run_id,
        adim="ingest",
        komut="ingest deneme",
        git=GitDurumu("c" * 40, False),
        uv_lock="d" * 64,
        config_sha="e" * 64,
        girdiler=[GIRDI],
        araclar=ARACLAR,
        ciktilar=[CIKTI],
        parmak="1" * 64,
    )


def parmak(**degisim: object) -> str:
    alanlar: dict[str, object] = {
        "adim": "ingest",
        "parametreler": {"variant": "deneme"},
        "girdiler": [GIRDI],
        "config_sha": "e" * 64,
        "git_commit": "c" * 40,
        "araclar": ARACLAR,
    }
    alanlar.update(degisim)
    return lineage.parmak_izi(**alanlar)  # type: ignore[arg-type]


# --- manifest ----------------------------------------------------------------------------


def test_manifest_alanlari_ve_sirasi() -> None:
    m = manifest_kur()
    assert list(m) == [
        "run_id",
        "adim",
        "komut",
        "git_commit",
        "git_dirty",
        "python",
        "uv_lock_sha256",
        "config_sha256",
        "girdiler",
        "araclar",
        "llm",
        "ciktilar",
        "parmak_izi",
    ]
    assert m["llm"] is None
    assert not any("lisans" in anahtar for anahtar in m)  # K-42: manifest lisans kopyasi tasimaz
    assert m["girdiler"] == [{"yol": GIRDI.yol, "sha256": GIRDI.sha256, "ust_run_id": "ust-run"}]
    assert set(m["araclar"]) == {"normalizer_version", "psycopg", "snowballstemmer"}  # type: ignore[call-overload]


def test_parmak_izi_ve_manifest_lisans_kopyasi_almaz() -> None:
    """K-42: parmak izi ve manifest lisans kopyasi parametresi tasimaz."""
    for islev in (lineage.parmak_izi, lineage.manifest_kur):
        assert "lisans_kopyalari" not in inspect.signature(islev).parameters
    assert isinstance(parmak(), str)


def test_manifest_deterministik_zaman_damgasiz() -> None:
    a = lineage.manifest_baytlari(manifest_kur())
    b = lineage.manifest_baytlari(manifest_kur())
    assert a == b
    assert a.endswith(b"\n")
    metin = a.decode("utf-8")
    for anahtar in ("ts", "zaman", "tarih", "baslangic", "bitis"):
        assert f'"{anahtar}"' not in metin
    # run_id disinda ayni
    iki = lineage.manifest_baytlari(manifest_kur("00000000-0000-7000-8000-000000000002"))
    assert iki.replace(b"000000000002", b"000000000001") == a


def test_manifest_listeleri_sirali() -> None:
    g2 = Girdi("raw/b.txt", "1" * 64)
    g1 = Girdi("raw/a.txt", "2" * 64)
    c2 = Cikti("staged/z.jsonl", "3" * 64)
    c1 = Cikti("staged/a.jsonl", "4" * 64, 1)
    ters = lineage.manifest_kur(
        run_id="r",
        adim="ingest",
        komut="k",
        git=GitDurumu(None, True),
        uv_lock=None,
        config_sha=None,
        girdiler=[g2, g1],
        araclar=ARACLAR,
        ciktilar=[c2, c1],
        parmak="p",
    )
    duz = lineage.manifest_kur(
        run_id="r",
        adim="ingest",
        komut="k",
        git=GitDurumu(None, True),
        uv_lock=None,
        config_sha=None,
        girdiler=[g1, g2],
        araclar=ARACLAR,
        ciktilar=[c1, c2],
        parmak="p",
    )
    assert lineage.manifest_baytlari(ters) == lineage.manifest_baytlari(duz)


def test_manifest_atomik_yazim_gecici_dosya_kalmaz(tmp_path: Path) -> None:
    klasor = tmp_path / "run"
    yol = lineage.manifest_yaz(klasor, manifest_kur())
    assert yol == klasor / "manifest.json"
    assert json.loads(yol.read_bytes())["adim"] == "ingest"
    assert [p.name for p in klasor.iterdir()] == ["manifest.json"]


def test_manifest_yazimi_yarida_kalirsa_manifest_olusmaz(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    klasor = tmp_path / "run"

    def patla(*_: object, **__: object) -> None:
        raise OSError("yeniden adlandirma basarisiz")

    monkeypatch.setattr(os, "replace", patla)
    with pytest.raises(OSError):
        lineage.manifest_yaz(klasor, manifest_kur())
    assert not (klasor / "manifest.json").exists()
    assert lineage.manifest_oku(klasor) is None


def test_manifest_yazimi_eski_manifesti_yarim_birakmaz(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    klasor = tmp_path / "run"
    lineage.manifest_yaz(klasor, manifest_kur())
    eski = (klasor / "manifest.json").read_bytes()
    monkeypatch.setattr(os, "replace", lambda *a, **k: (_ for _ in ()).throw(OSError("x")))
    with pytest.raises(OSError):
        lineage.manifest_yaz(klasor, manifest_kur("00000000-0000-7000-8000-000000000009"))
    assert (klasor / "manifest.json").read_bytes() == eski


# --- calistirma bulma -----------------------------------------------------------------------


def calisma_yaz(kaynak: Path, uretici: Uuid7Uretici, adim: str = "ingest") -> str:
    run_id = str(uretici.uret())
    m = manifest_kur(run_id)
    m["adim"] = adim
    lineage.manifest_yaz(kaynak / run_id, m)
    return run_id


def test_manifestsiz_klasor_yok_sayilir(tmp_path: Path) -> None:
    kaynak = tmp_path / "staged" / "test-kaynak"
    uretici = Uuid7Uretici()
    r1 = calisma_yaz(kaynak, uretici)
    yarim = kaynak / str(uretici.uret())
    yarim.mkdir()
    (yarim / "units.jsonl").write_bytes(b"{}\n")
    gecici = kaynak / str(uretici.uret())
    gecici.mkdir()
    (gecici / "manifest.json.tmp").write_bytes(b"{}")
    bozuk = kaynak / str(uretici.uret())
    bozuk.mkdir()
    (bozuk / "manifest.json").write_bytes(b"{bozuk")
    (kaynak / "serbest-dosya.txt").write_bytes(b"x")
    assert [r for r, _, _ in lineage.calismalar(kaynak)] == [r1]
    bulunan = lineage.son_basarili(kaynak)
    assert bulunan is not None
    assert bulunan[0] == r1


def test_son_basarili_uuid7_sirasi_ve_adim_suzgeci(tmp_path: Path) -> None:
    kaynak = tmp_path / "staged" / "test-kaynak"
    uretici = Uuid7Uretici()
    r1 = calisma_yaz(kaynak, uretici, "ingest")
    r2 = calisma_yaz(kaynak, uretici, "normalize")
    r3 = calisma_yaz(kaynak, uretici, "ingest")
    assert lineage.son_basarili(kaynak) is not None
    assert lineage.son_basarili(kaynak)[0] == r3  # type: ignore[index]
    assert lineage.son_basarili(kaynak, "normalize")[0] == r2  # type: ignore[index]
    assert lineage.son_basarili(kaynak, "anchor") is None
    assert [r for r, _, _ in lineage.calismalar(kaynak)] == [r1, r2, r3]
    assert lineage.son_basarili(tmp_path / "yok") is None


# --- parmak izi ----------------------------------------------------------------------------


def test_parmak_izi_deterministik_ve_hassas() -> None:
    assert parmak() == parmak()
    assert len(parmak()) == 64
    for degisim in (
        {"adim": "normalize"},
        {"parametreler": {"variant": "baska"}},
        {"girdiler": [Girdi("raw/x/dosya.txt", "9" * 64)]},
        {"config_sha": "9" * 64},
        {"git_commit": "9" * 40},
        {"araclar": {**ARACLAR, "normalizer_version": "2.0"}},
    ):
        assert parmak(**degisim) != parmak()


def test_parmak_izi_girdi_yolu_tarihine_ve_run_id_ye_bagli_degil() -> None:
    a = [Girdi("raw/test-kaynak/2026-10-28/dosya.txt", "a" * 64, "run-1")]
    b = [Girdi("raw/test-kaynak/2026-11-02/dosya.txt", "a" * 64, "run-2")]
    assert parmak(girdiler=a) == parmak(girdiler=b)


def test_iki_farkli_db_url_ayni_parmak_izi(tmp_path: Path) -> None:
    kok = depo_kur(tmp_path, "test-kaynak")
    girdiler = [GIRDI]
    izler = []
    for dsn in (None, SAHTE_DSN, "postgresql://baska:BASKA-PAROLA@10.0.0.9:5432/baska"):
        ctx = ctx_kur(tmp_path, kok, db_url=dsn, parametreler={"variant": "deneme"})
        izi = ctx.parmak_izi(girdiler)
        assert isinstance(izi, str)
        izler.append(izi)
    assert len(set(izler)) == 1


def test_ortam_degiskenleri_parmak_izine_girmez(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    kok = depo_kur(tmp_path, "test-kaynak")
    onceki = ctx_kur(tmp_path, kok).parmak_izi([GIRDI])
    monkeypatch.setenv("MUTALAA_DB_URL", SAHTE_DSN)
    monkeypatch.setenv("MUTALAA_LOG_DUZEYI", "ERROR")
    sonraki = ctx_kur(tmp_path, kok).parmak_izi([GIRDI])
    assert onceki == sonraki


def test_config_sha256_yalniz_toml_baytlarindan(tmp_path: Path) -> None:
    toml = tmp_path / "ozel.toml"
    toml.write_bytes(b'[genel]\nlog_duzeyi = "INFO"\n')
    ozet = hashlib.sha256(toml.read_bytes()).hexdigest()
    assert lineage.config_sha256(toml) == ozet
    assert lineage.config_sha256(tmp_path / "yok.toml") is None
    kok = depo_kur(tmp_path, "test-kaynak")
    for dsn in (None, SAHTE_DSN):
        ctx = ctx_kur(tmp_path, kok, db_url=dsn)
        ctx.ayarlar = Ayarlar(
            _env_file=None, db_url=dsn, veri_kok=tmp_path / "data", config_dosyasi=toml
        )
        yol = ctx.manifest_yaz(
            tmp_path / "m",
            girdiler=[GIRDI],
            ciktilar=[CIKTI],
            parmak="p",
        )
        assert json.loads(yol.read_bytes())["config_sha256"] == ozet
    # toml degisirse ozet degisir
    toml.write_bytes(b'[genel]\nlog_duzeyi = "DEBUG"\n')
    assert lineage.config_sha256(toml) != ozet


def test_ayarlar_kur_yardimcisi_env_okumaz(tmp_path: Path) -> None:
    assert ayarlar_kur(tmp_path).db_url is None


# --- atlama ----------------------------------------------------------------------------------


def atlama_kur(tmp_path: Path) -> tuple[Path, dict[str, object]]:
    veri_kok = tmp_path / "data"
    cikti = veri_kok / "staged" / "test-kaynak" / "RUN" / "units.jsonl"
    cikti.parent.mkdir(parents=True)
    cikti.write_bytes(b"{}\n")
    m = manifest_kur()
    m["ciktilar"] = [
        {
            "yol": "staged/test-kaynak/RUN/units.jsonl",
            "sha256": hashlib.sha256(b"{}\n").hexdigest(),
            "satir": 1,
        }
    ]
    m["parmak_izi"] = "p1"
    return veri_kok, m


def test_atlama_kosullari(tmp_path: Path) -> None:
    veri_kok, m = atlama_kur(tmp_path)

    def karar(**degisim: object) -> bool:
        alanlar: dict[str, object] = {
            "onceki": m,
            "parmak": "p1",
            "git_kirli": False,
            "force": False,
            "veri_kok": veri_kok,
        }
        alanlar.update(degisim)
        return lineage.atlanabilir(**alanlar)  # type: ignore[arg-type]

    assert karar() is True
    assert karar(force=True) is False  # --force her zaman calistirir
    assert karar(git_kirli=True) is False  # kirli agacta atlama kapali
    assert karar(parmak="p2") is False
    assert karar(onceki=None) is False


def test_atlama_onceki_kirli_agacta_uretildiyse_kapali(tmp_path: Path) -> None:
    """Onceki manifest kirli agacta yazildiysa, parmak izi ayni olsa da atlanmaz (K-39 madde 8)."""
    veri_kok, m = atlama_kur(tmp_path)
    assert m["git_dirty"] is False  # atlama_kur manifesti temiz agactan

    def karar(onceki: dict[str, object]) -> bool:
        return lineage.atlanabilir(
            onceki=onceki, parmak="p1", git_kirli=False, force=False, veri_kok=veri_kok
        )

    assert karar(m) is True
    assert karar({**m, "git_dirty": True}) is False
    # Yalniz acikca `False` olan onceki temiz sayilir: alan yoksa ya da bool degilse atlanmaz.
    assert karar({k: v for k, v in m.items() if k != "git_dirty"}) is False
    for bool_olmayan in (None, 0, "false"):
        assert karar({**m, "git_dirty": bool_olmayan}) is False


def test_atlama_cikti_bozuksa_kapali(tmp_path: Path) -> None:
    veri_kok, m = atlama_kur(tmp_path)
    cikti = veri_kok / "staged" / "test-kaynak" / "RUN" / "units.jsonl"
    cikti.write_bytes(b"{}\n{}\n")
    assert not lineage.atlanabilir(
        onceki=m, parmak="p1", git_kirli=False, force=False, veri_kok=veri_kok
    )
    cikti.unlink()
    assert not lineage.atlanabilir(
        onceki=m, parmak="p1", git_kirli=False, force=False, veri_kok=veri_kok
    )


def test_goreli_yol_veri_kokunun_disinda_hata(tmp_path: Path) -> None:
    from mutalaa_pipeline.export.ortak import GirdiHatasi

    assert lineage.goreli_yol(tmp_path, tmp_path / "a" / "b.txt") == "a/b.txt"
    with pytest.raises(GirdiHatasi):
        lineage.goreli_yol(tmp_path / "x", tmp_path / "y.txt")


def test_git_durumu_depo_degilse_kirli_sayilir(tmp_path: Path) -> None:
    durum = lineage.git_durumu(tmp_path)
    assert durum.kirli is True
    assert durum.commit is None


def test_arac_surumleri() -> None:
    araclar = lineage.arac_surumleri()
    assert set(araclar) == {"normalizer_version", "psycopg", "snowballstemmer"}
    assert araclar["normalizer_version"] == "1.0"
    assert araclar["snowballstemmer"] == "3.1.1"
    assert araclar["psycopg"] is not None


# --- atomik_degistir: OneDrive/antivirus kaynakli gecici PermissionError (A13.6) ---------


class GeciciIzinHatasi:
    """Ilk `n` cagriyi `PermissionError` ile bitiren, sonra gercek `os.replace` yapan sahte."""

    def __init__(self, n: int) -> None:
        self.kalan = n
        self.cagri = 0

    def __call__(self, gecici: Path, hedef: Path) -> None:
        self.cagri += 1
        if self.kalan > 0:
            self.kalan -= 1
            raise PermissionError(13, "erisim engellendi (WinError 5)")
        os.replace(gecici, hedef)


def _gecici_dosya(tmp_path: Path) -> tuple[Path, Path]:
    gecici, hedef = tmp_path / "a.tmp", tmp_path / "a"
    gecici.write_bytes(b"yeni")
    return gecici, hedef


def test_atomik_degistir_gecici_izin_hatasinda_yeniden_dener(tmp_path: Path) -> None:
    gecici, hedef = _gecici_dosya(tmp_path)
    sahte, beklemeler = GeciciIzinHatasi(2), []
    lineage.atomik_degistir(gecici, hedef, degistir=sahte, uyku=beklemeler.append)
    assert sahte.cagri == 3
    assert beklemeler == [0.2, 0.4]  # kisa, artan bekleme
    assert hedef.read_bytes() == b"yeni"
    assert not gecici.exists()


def test_atomik_degistir_uc_denemeden_sonra_hatayi_firlatir(tmp_path: Path) -> None:
    gecici, hedef = _gecici_dosya(tmp_path)
    sahte, beklemeler = GeciciIzinHatasi(99), []
    with pytest.raises(PermissionError):
        lineage.atomik_degistir(gecici, hedef, degistir=sahte, uyku=beklemeler.append)
    assert sahte.cagri == lineage.YENIDEN_DEGISTIRME_DENEMESI == 3
    assert len(beklemeler) == 2  # son denemeden sonra beklenmez
    assert gecici.exists()
    assert not hedef.exists()


def test_atomik_degistir_baska_hatayi_yeniden_denemez(tmp_path: Path) -> None:
    gecici, hedef = _gecici_dosya(tmp_path)
    cagri = []

    def bozuk(_a: Path, _b: Path) -> None:
        cagri.append(1)
        raise OSError("baska hata")

    with pytest.raises(OSError, match="baska hata"):
        lineage.atomik_degistir(gecici, hedef, degistir=bozuk, uyku=lambda _s: None)
    assert len(cagri) == 1


def test_manifest_yazimi_gecici_izin_hatasindan_kurtulur(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gercek, cagri = os.replace, []

    def replace(a: object, b: object) -> None:
        cagri.append(1)
        if len(cagri) < 3:
            raise PermissionError(13, "erisim engellendi")
        gercek(a, b)  # type: ignore[arg-type]

    monkeypatch.setattr(os, "replace", replace)
    monkeypatch.setattr(lineage.time, "sleep", lambda _s: None)
    klasor = tmp_path / "run"
    lineage.manifest_yaz(klasor, manifest_kur())
    assert len(cagri) == 3
    assert lineage.manifest_oku(klasor) is not None
    assert not (klasor / "manifest.json.tmp").exists()
