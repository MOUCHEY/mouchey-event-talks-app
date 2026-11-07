"""Backtest vectorisé : poids décidés à la clôture de t, détenus de t à t+1, coûts sur le turnover réel."""
from __future__ import annotations

import numpy as np
import pandas as pd


def run_backtest(prices: pd.DataFrame, weights: pd.DataFrame, cost_bps: float) -> pd.DataFrame:
    px = prices.ffill()
    tradable = px.notna()
    rets = (px / px.shift(1) - 1).fillna(0.0)

    w = weights.reindex(index=px.index, columns=px.columns).astype(float)
    if np.isinf(w.to_numpy()).any():
        raise ValueError("la stratégie renvoie des poids infinis")
    w = w.where(tradable, 0.0).fillna(0.0)  # pas de position sur un actif pas encore coté

    held = w.shift(1).fillna(0.0)                       # ce qu'on détient pendant la journée t
    gross = (held * rets).sum(axis=1)
    drifted = (held * (1 + rets)).div(1 + gross, axis=0)  # poids juste avant de rééquilibrer en t
    turnover = (w - drifted).abs().sum(axis=1)
    cost = turnover * cost_bps / 1e4

    return pd.DataFrame(
        {
            "gross": gross,
            "cost": cost,
            "net": gross - cost,
            "turnover": turnover,
            "leverage": w.abs().sum(axis=1),
        }
    )
