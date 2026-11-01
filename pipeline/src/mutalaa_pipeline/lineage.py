"""Veri soyu: manifest, parmak izi, atomik yazim, son basarili calistirma (§5, §6, §12).

Parmak izi yalniz acik girdilerden hesaplanir (adim, parametreler, girdi ozetleri, `mutalaa.toml`
ozeti, git commit, arac surumleri). Ortam degiskenleri ve `.env` degerleri hicbir ozete girmez.
Icerik dosyalarina zaman damgasi yazilmaz.
"""

import hashlib
import json
import os
import platform
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path
from typing import Final

from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.logs import json_baytlari

MANIFEST_ADI: Final = "manifest.json"
UV_LOCK_YOLU: Final = "pipeline/uv.lock"
UUID_UZUNLUGU: Final = 36


def sha256_bayt(veri: bytes) -> str:
    return hashlib.sha256(veri).hexdigest()


def sha256_dosya(yol: Path) -> str:
    ozet = hashlib.sha256()
    with yol.open("rb") as dosya:
        for parca in iter(lambda: dosya.read(1 << 20), b""):
            ozet.update(parca)
    return ozet.hexdigest()


@dataclass(frozen=True)
class GitDurumu:
    commit: str | None
    kirli: bool


def git_durumu(depo_kok: Path) -> GitDurumu:
    """HEAD commit ve calisma agacinin kirli olup olmadigi; git yoksa kirli sayilir."""

    def calistir(*arglar: str) -> str | None:
        try:
            sonuc = subprocess.run(
                ["git", "-C", str(depo_kok), *arglar],
                capture_output=True,
                check=False,
                timeout=60,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        if sonuc.returncode != 0:
            return None
        return sonuc.stdout.decode("utf-8", "replace")

    commit = calistir("rev-parse", "HEAD")
    durum = calistir("status", "--porcelain")
    return GitDurumu(
        commit=commit.strip() if commit is not None else None,
        kirli=durum is None or durum.strip() != "",
    )


def uv_lock_sha256(depo_kok: Path) -> str | None:
    yol = depo_kok / UV_LOCK_YOLU
    return sha256_dosya(yol) if yol.is_file() else None


def config_sha256(yol: Path) -> str | None:
    """Yalniz `mutalaa.toml` baytlarindan; dosya yoksa None."""
    return sha256_dosya(yol) if yol.is_file() else None


def arac_surumleri() -> dict[str, str | None]:
    # Ice aktarma burada: normalize paketi regex ve snowballstemmer yukler.
    from mutalaa_pipeline.normalize import NORMALIZER_VERSION

    def surum(ad: str) -> str | None:
        try:
            return metadata.version(ad)
        except metadata.PackageNotFoundError:
            return None

    return {
        "normalizer_version": NORMALIZER_VERSION,
        "psycopg": surum("psycopg"),
        "snowballstemmer": surum("snowballstemmer"),
    }


def goreli_yol(kok: Path, yol: Path) -> str:
    """`kok` altindaki yolu `/` ayiracli goreli yol yapar; disindaysa girdi hatasi."""
    try:
        return yol.resolve().relative_to(kok.resolve()).as_posix()
    except ValueError:
        raise GirdiHatasi("yol veri kokunun disinda") from None


@dataclass(frozen=True)
class Girdi:
    yol: str
    sha256: str
    ust_run_id: str | None = None

    def sozluk(self) -> dict[str, object]:
        return {"yol": self.yol, "sha256": self.sha256, "ust_run_id": self.ust_run_id}


@dataclass(frozen=True)
class Cikti:
    yol: str
    sha256: str
    satir: int | None = None

    def sozluk(self) -> dict[str, object]:
        kayit: dict[str, object] = {"yol": self.yol, "sha256": self.sha256}
        if self.satir is not None:
            kayit["satir"] = self.satir
        return kayit


def parmak_izi(
    *,
    adim: str,
    parametreler: Mapping[str, object],
    girdiler: Sequence[Girdi],
    config_sha: str | None,
    git_commit: str | None,
    araclar: Mapping[str, str | None],
) -> str:
    """`SHA-256(girdi ozetleri + yapilandirma + git commit + arac surumleri)`.

    Girdi yollari (tarihli klasor, run_id) ozete girmez; yalniz dosya adi ve SHA-256.
    """
    govde = {
        "adim": adim,
        "parametreler": dict(parametreler),
        "girdiler": sorted([Path(g.yol).name, g.sha256] for g in girdiler),
        "config_sha256": config_sha,
        "git_commit": git_commit,
        "araclar": dict(araclar),
    }
    return sha256_bayt(json_baytlari(govde))


def manifest_kur(
    *,
    run_id: str,
    adim: str,
    komut: str,
    git: GitDurumu,
    uv_lock: str | None,
    config_sha: str | None,
    girdiler: Sequence[Girdi],
    araclar: Mapping[str, str | None],
    ciktilar: Sequence[Cikti],
    parmak: str,
    ayrintilar: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Manifest sozlugu (alan sirasi Icerik hatti §12). Zaman damgasi icermez."""
    manifest: dict[str, object] = {
        "run_id": run_id,
        "adim": adim,
        "komut": komut,
        "git_commit": git.commit,
        "git_dirty": git.kirli,
        "python": platform.python_version(),
        "uv_lock_sha256": uv_lock,
        "config_sha256": config_sha,
        "girdiler": [g.sozluk() for g in sorted(girdiler, key=lambda g: g.yol)],
        "araclar": dict(araclar),
        "llm": None,
        "ciktilar": [c.sozluk() for c in sorted(ciktilar, key=lambda c: c.yol)],
        "parmak_izi": parmak,
    }
    if ayrintilar:
        manifest["ayrintilar"] = dict(ayrintilar)
    return manifest


def manifest_baytlari(manifest: Mapping[str, object]) -> bytes:
    """Alan sirasini koruyan, deterministik JSON (sort_keys yok; sira kurulustan gelir)."""
    return (json.dumps(manifest, ensure_ascii=True, indent=2) + "\n").encode("utf-8")


def manifest_yaz(klasor: Path, manifest: Mapping[str, object]) -> Path:
    """Manifesti en son ve atomik yazar: gecici dosya, fsync, yeniden adlandirma."""
    klasor.mkdir(parents=True, exist_ok=True)
    hedef = klasor / MANIFEST_ADI
    gecici = klasor / (MANIFEST_ADI + ".tmp")
    with gecici.open("wb") as dosya:
        dosya.write(manifest_baytlari(manifest))
        dosya.flush()
        os.fsync(dosya.fileno())
    os.replace(gecici, hedef)
    return hedef


def manifest_oku(klasor: Path) -> dict[str, object] | None:
    """Manifest yoksa ya da okunamiyorsa None (klasor yok sayilir)."""
    yol = klasor / MANIFEST_ADI
    try:
        veri = json.loads(yol.read_bytes().decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return veri if isinstance(veri, dict) else None


def calismalar(kaynak_klasoru: Path) -> list[tuple[str, Path, dict[str, object]]]:
    """`staged/{kaynak}` altinda manifesti olan calistirmalar, run_id (UUIDv7) sirasinda."""
    if not kaynak_klasoru.is_dir():
        return []
    sonuc: list[tuple[str, Path, dict[str, object]]] = []
    for yol in sorted(kaynak_klasoru.iterdir(), key=lambda p: p.name):
        if not yol.is_dir() or len(yol.name) != UUID_UZUNLUGU:
            continue
        manifest = manifest_oku(yol)
        if manifest is not None and manifest.get("run_id") == yol.name:
            sonuc.append((yol.name, yol, manifest))
    return sonuc


def son_basarili(
    kaynak_klasoru: Path, adim: str | None = None
) -> tuple[str, Path, dict[str, object]] | None:
    """Manifesti olan en son calistirma (istenirse belirli bir adim)."""
    for kayit in reversed(calismalar(kaynak_klasoru)):
        if adim is None or kayit[2].get("adim") == adim:
            return kayit
    return None


def ciktilar_saglam(veri_kok: Path, manifest: Mapping[str, object]) -> bool:
    """Manifestteki her cikti dosyasi var ve SHA-256 degeri tutuyor mu."""
    ciktilar = manifest.get("ciktilar")
    if not isinstance(ciktilar, list) or not ciktilar:
        return False
    for kayit in ciktilar:
        if not isinstance(kayit, dict):
            return False
        yol, ozet = kayit.get("yol"), kayit.get("sha256")
        if not isinstance(yol, str) or not isinstance(ozet, str):
            return False
        dosya = veri_kok / yol
        if not dosya.is_file() or sha256_dosya(dosya) != ozet:
            return False
    return True


def atlanabilir(
    *,
    onceki: Mapping[str, object] | None,
    parmak: str,
    git_kirli: bool,
    force: bool,
    veri_kok: Path,
) -> bool:
    """Parmak izi onceki basarili calistirmayla ayniysa ve ciktilar saglamsa atlanir.

    `--force` ve kirli calisma agaci atlamayi her zaman kapatir.
    """
    if force or git_kirli or onceki is None:
        return False
    if onceki.get("git_dirty") is not False:
        # Kirli agacta uretilen cikti, bir commit'e baglanamaz: onceki sayilmaz.
        return False
    return onceki.get("parmak_izi") == parmak and ciktilar_saglam(veri_kok, onceki)
