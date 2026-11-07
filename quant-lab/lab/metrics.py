"""Mesures de performance et Sharpe déflaté.

Décote pour essais multiples : si N stratégies sans aucun pouvoir prédictif (Sharpe réel = 0) sont
testées sur T jours, la meilleure affiche quand même en moyenne un Sharpe de
    E[max] ≈ ((1−γ)·Φ⁻¹(1−1/N) + γ·Φ⁻¹(1−1/(N·e))) / √(T−1)   (par jour)
(Bailey & López de Prado, 2014, « The Deflated Sharpe Ratio »). On retire ce montant au Sharpe observé.
Hypothèse d'essais indépendants : c'est volontairement sévère.
"""
from __future__ import annotations

import math
from statistics import NormalDist

import numpy as np
import pandas as pd

EULER_GAMMA = 0.5772156649015329
_NORMAL = NormalDist()


def sharpe_per_period(r: pd.Series) -> float:
    sd = r.std(ddof=1)
    return float(r.mean() / sd) if sd > 0 else float("nan")


def summarize(r: pd.Series, periods_per_year: int) -> dict:
    T = len(r)
    sr = sharpe_per_period(r)
    equity = (1 + r).cumprod()
    drawdown = 1 - equity / equity.cummax()
    years = T / periods_per_year
    final = float(equity.iloc[-1])
    return {
        "T": T,
        "sr_d": sr,
        "sharpe": sr * math.sqrt(periods_per_year),
        "ann_return": final ** (1 / years) - 1 if final > 0 else -1.0,
        "ann_vol": float(r.std(ddof=1) * math.sqrt(periods_per_year)),
        "max_dd": float(drawdown.max()),
        "skew": float(r.skew()),
        "kurt": float(r.kurt() + 3),  # kurtosis non centrée (3 pour une loi normale)
    }


def fold_sharpes(r: pd.Series, n_folds: int, periods_per_year: int) -> list[float]:
    chunks = np.array_split(np.arange(len(r)), n_folds)
    return [sharpe_per_period(r.iloc[c]) * math.sqrt(periods_per_year) for c in chunks]


def expected_max_z(n_trials: int) -> float:
    if n_trials <= 1:
        return 0.0
    n = float(n_trials)
    return (1 - EULER_GAMMA) * _NORMAL.inv_cdf(1 - 1 / n) + EULER_GAMMA * _NORMAL.inv_cdf(1 - 1 / (n * math.e))


def haircut_per_period(n_trials: int, T: int) -> float:
    return expected_max_z(n_trials) / math.sqrt(T - 1)


def psr(sr: float, sr_star: float, T: int, skew: float, kurt: float) -> float:
    """Probabilistic Sharpe Ratio : P(Sharpe réel > sr_star), Sharpe par période."""
    var = 1 - skew * sr + (kurt - 1) / 4 * sr * sr
    if T < 3 or not var > 0 or math.isnan(sr):
        return float("nan")
    return _NORMAL.cdf((sr - sr_star) * math.sqrt(T - 1) / math.sqrt(var))


def deflate(sr_d: float, T: int, skew: float, kurt: float, n_trials: int, periods_per_year: int) -> dict:
    h = haircut_per_period(n_trials, T)
    return {
        "haircut": h * math.sqrt(periods_per_year),
        "score": (sr_d - h) * math.sqrt(periods_per_year),
        "dsr": psr(sr_d, h, T, skew, kurt),
    }
