"""Hat testlerinin ortak yardimcilari (test degildir; SENTETIK veri)."""

import re
from collections.abc import Iterable
from pathlib import Path

from test_sources import alanlar_kur, kayit_yaz, kok_kur

from mutalaa_pipeline.config import Ayarlar
from mutalaa_pipeline.lineage import GitDurumu
from mutalaa_pipeline.runctx import RunContext, Uuid7Uretici

SAHTE_DSN = "postgresql://u:GIZLI-DENEME@127.0.0.1:1/x"
PAROLA = "GIZLI-DENEME"
# Ayni commit, farkli agac durumu: parmak izi ayni kalir, yalniz `git_dirty` degisir.
TEMIZ_GIT = GitDurumu(commit="0" * 40, kirli=False)
KIRLI_GIT = GitDurumu(commit="0" * 40, kirli=True)

_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def ansisiz(metin: str) -> str:
    """Terminal renk kacis dizilerini temizler.

    CI renkli cikti uretir: Typer `FORCE_COLOR` ve `GITHUB_ACTIONS` degiskenini iceri aktarma
    aninda okur, bu yuzden testte ortam degiskeniyle kapatilamaz. `--help` ciktisinda secenek
    adlarini kacis dizileri boler; karsilastirmadan once temizlenir.
    """
    return _ANSI.sub("", metin)


def depo_kur(tmp_path: Path, *slugs: str, **degisim: object) -> Path:
    """Sahte depo koku; her slug icin gecerli bir sentetik kayit."""
    kok = kok_kur(tmp_path)
    for slug in slugs:
        kayit_yaz(kok, alanlar_kur(slug, **degisim))
    return kok


def ayarlar_kur(tmp_path: Path, *, db_url: str | None = None, **bayrak: object) -> Ayarlar:
    """`.env` ve `mutalaa.toml` okumaz; veri koku `tmp_path/data`."""
    return Ayarlar(_env_file=None, veri_kok=tmp_path / "data", db_url=db_url, **bayrak)  # type: ignore[arg-type]


def ctx_kur(
    tmp_path: Path,
    kok: Path,
    *,
    adim: str = "ingest",
    kaynaklar: Iterable[str] = (),
    db_url: str | None = None,
    temiz_git: bool = False,
    git: GitDurumu | None = None,
    **kw: object,
) -> RunContext:
    ctx = RunContext.olustur(
        ayarlar_kur(tmp_path, db_url=db_url),
        komut=f"{adim} deneme",
        adim=adim,
        depo_kok=kok,
        kaynaklar=kaynaklar,
        uretici=Uuid7Uretici(),
        **kw,  # type: ignore[arg-type]
    )
    if git is not None:
        ctx._git = git
    elif temiz_git:
        ctx._git = TEMIZ_GIT
    return ctx
