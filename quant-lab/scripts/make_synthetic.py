"""Génère des prix SYNTHÉTIQUES pour tester le harness sans connexion.

Ne JAMAIS faire de recherche dessus : le juge affiche un avertissement tant que la source est « synthetic ».

    python scripts/make_synthetic.py [--seed 7]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from lab.config import load_config, resolve  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()
    cfg = load_config()
    d = cfg["data"]
    rng = np.random.default_rng(args.seed)

    dates = pd.bdate_range(d["start"], pd.Timestamp.today().normalize())
    n, k = len(dates), len(d["universe"])
    # 3 facteurs (actions, taux, matières premières) avec dérive lente persistante → tendances
    drift = np.zeros((n, 3))
    for t in range(1, n):
        drift[t] = 0.998 * drift[t - 1] + rng.normal(0, 0.00002, 3)
    crisis = np.zeros(n, bool)
    for t in range(1, n):
        crisis[t] = rng.random() < (0.985 if crisis[t - 1] else 0.002)
    vol = np.where(crisis, 2.5, 1.0)[:, None] * np.array([0.011, 0.005, 0.009])
    factors = drift + np.array([0.0003, 0.0001, 0.0001]) + rng.normal(0, 1, (n, 3)) * vol
    loadings = np.abs(rng.normal(0.8, 0.3, (k, 3))) * rng.choice([1, 0.2], (k, 3), p=[0.4, 0.6])
    idio = rng.normal(0, 0.006, (n, k))
    rets = factors @ loadings.T + idio
    prices = pd.DataFrame(100 * np.exp(np.cumsum(rets, axis=0)), index=dates, columns=d["universe"])
    prices.iloc[:280, -2] = np.nan  # un actif coté plus tard, comme dans la réalité
    prices.index.name = "date"

    cutoff = pd.Timestamp(d["holdout_start"])
    for key, frame in (("research_file", prices[prices.index < cutoff]), ("holdout_file", prices)):
        out = resolve(d[key])
        out.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(out, float_format="%.6f")
        print(f"{key}: {out} ({len(frame)} jours)")
    resolve(d["source_file"]).write_text(json.dumps({"source": "synthetic", "seed": args.seed}, indent=2))
    print("⚠ Données synthétiques : pour tester le harness uniquement.")


if __name__ == "__main__":
    main()
