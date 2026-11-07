"""Registre des essais (results.tsv). Écrit uniquement par le juge, jamais à la main."""
from __future__ import annotations

import contextlib
import hashlib
import json
import subprocess
from pathlib import Path

import pandas as pd

from .config import ROOT

COLUMNS = [
    "trial", "timestamp", "strategy", "params", "strategy_hash", "harness_hash", "data_source",
    "status", "reasons", "sharpe", "ann_return", "ann_vol", "max_dd", "turnover", "max_leverage",
    "folds_pos", "folds", "corr_baseline", "T", "sr_d", "skew", "kurt", "n_trials", "haircut",
    "score", "dsr", "cost_bps", "note",
]
ACCEPTED, REJECTED, STRESS = "ACCEPTE", "REJETE", "STRESS"


def harness_hash() -> str:
    h = hashlib.sha256()
    for p in sorted((ROOT / "lab").glob("*.py")) + [ROOT / "config.toml"]:
        h.update(p.name.encode())
        h.update(p.read_bytes())
    return h.hexdigest()[:12]


def strategy_hash(path: Path, params: dict) -> str:
    h = hashlib.sha256(path.read_bytes())
    h.update(json.dumps(params, sort_keys=True, default=str).encode())
    return h.hexdigest()[:12]


def harness_git_state() -> tuple[str, str]:
    """'ok' | 'dirty' | 'untracked' | 'nogit'."""
    try:
        diff = subprocess.run(
            ["git", "-C", str(ROOT), "status", "--porcelain", "--", "lab/*.py", "config.toml"],
            capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "nogit", "git indisponible : impossible de vérifier que le juge est intact"
    if diff.returncode != 0:
        return "nogit", "pas un dépôt git : impossible de vérifier que le juge est intact"
    lines = [l for l in diff.stdout.splitlines() if l.strip()]
    if any(not l.startswith("??") for l in lines):
        return "dirty", "le juge (lab/ ou config.toml) a des modifications non commitées"
    if lines:
        return "untracked", "le juge n'est pas encore commité : commite-le pour le verrouiller"
    return "ok", ""


@contextlib.contextmanager
def locked(path: Path):
    """Verrou exclusif pour que plusieurs agents puissent écrire dans le même registre."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = open(path.with_suffix(path.suffix + ".lock"), "w")
    try:
        try:
            import fcntl
            fcntl.flock(lock, fcntl.LOCK_EX)
        except ImportError:  # Windows : pas de verrou, éviter les écritures simultanées
            pass
        yield
    finally:
        lock.close()


def read_results(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame(columns=COLUMNS)
    return pd.read_csv(path, sep="\t", dtype={"strategy_hash": str, "harness_hash": str})


def count_trials(df: pd.DataFrame, extra_hash: str | None = None) -> int:
    """N = nombre de couples (code, paramètres) distincts évalués, rejetés compris, stress exclus."""
    hashes = set(df.loc[df["status"] != STRESS, "strategy_hash"].astype(str))
    if extra_hash:
        hashes.add(extra_hash)
    return len(hashes)


def next_trial_id(df: pd.DataFrame) -> int:
    return int(df["trial"].max()) + 1 if len(df) else 1


def append_result(path: Path, row: dict) -> None:
    new = not path.exists() or path.stat().st_size == 0
    line = pd.DataFrame([{c: row.get(c, "") for c in COLUMNS}])
    line.to_csv(path, sep="\t", index=False, header=new, mode="a", float_format="%.6g")
