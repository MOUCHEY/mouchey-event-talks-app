"""Lecture de config.toml et résolution des chemins."""
from __future__ import annotations

import os
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_config() -> dict:
    with open(ROOT / "config.toml", "rb") as f:
        return tomllib.load(f)


def resolve(path_str: str) -> Path:
    p = Path(os.path.expanduser(path_str))
    return p if p.is_absolute() else ROOT / p


def results_path(cfg: dict) -> Path:
    return resolve(os.environ.get("QUANT_LAB_RESULTS", cfg["lab"]["results_file"]))


def holdout_log_path(cfg: dict) -> Path:
    return resolve(cfg["lab"]["holdout_log"])
