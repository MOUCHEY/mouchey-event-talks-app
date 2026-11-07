"""Chargement des prix. La période de recherche s'arrête TOUJOURS avant holdout_start."""
from __future__ import annotations

import json

import pandas as pd

from .config import resolve


def _load_csv(path) -> pd.DataFrame:
    if not path.exists():
        raise SystemExit(
            f"Données introuvables : {path}\n"
            "→ lance `python scripts/fetch_data.py` (vraies données) "
            "ou `python scripts/make_synthetic.py` (test du harness uniquement)."
        )
    df = pd.read_csv(path, index_col=0, parse_dates=True).sort_index().astype(float)
    df.index.name = "date"
    return df


def data_source(cfg: dict) -> str:
    path = resolve(cfg["data"]["source_file"])
    if not path.exists():
        return "inconnue"
    try:
        return json.loads(path.read_text()).get("source", "inconnue")
    except (OSError, ValueError):
        return "inconnue"


def research_prices(cfg: dict) -> pd.DataFrame:
    df = _load_csv(resolve(cfg["data"]["research_file"]))
    cutoff = pd.Timestamp(cfg["data"]["holdout_start"])
    if (df.index >= cutoff).any():
        print(f"⚠ research.csv contient des dates ≥ {cutoff.date()} : elles sont ignorées.")
        df = df[df.index < cutoff]
    return df


def full_prices(cfg: dict) -> pd.DataFrame:
    """Historique complet, holdout inclus. Réservé à lab.holdout."""
    return _load_csv(resolve(cfg["data"]["holdout_file"]))
