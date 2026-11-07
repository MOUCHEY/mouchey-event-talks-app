"""Briques causales que les stratégies peuvent importer : `from lab import tools`.

Chaque fonction n'utilise, pour la date t, que des données ≤ t.
"""
from __future__ import annotations

import math

import pandas as pd


def daily_returns(prices: pd.DataFrame) -> pd.DataFrame:
    return prices / prices.shift(1) - 1


def ann_vol(prices: pd.DataFrame, lookback: int, periods_per_year: int = 252) -> pd.DataFrame:
    """Volatilité annualisée glissante (fenêtre passée uniquement)."""
    r = daily_returns(prices)
    return r.rolling(lookback, min_periods=max(2, lookback // 2)).std() * math.sqrt(periods_per_year)


def month_starts(index: pd.DatetimeIndex) -> pd.Series:
    """True le premier jour de bourse de chaque mois (connu sans regarder le futur)."""
    per = pd.Series(index.to_period("M"), index=index)
    return per.ne(per.shift(1))


def week_starts(index: pd.DatetimeIndex) -> pd.Series:
    """True le premier jour de bourse de chaque semaine."""
    per = pd.Series(index.to_period("W"), index=index)
    return per.ne(per.shift(1))


def cap_gross(weights: pd.DataFrame, max_gross: float) -> pd.DataFrame:
    """Réduit proportionnellement les lignes dont la somme des |poids| dépasse max_gross."""
    gross = weights.abs().sum(axis=1)
    scale = (max_gross / gross).clip(upper=1.0).fillna(1.0)
    return weights.mul(scale, axis=0)


def rebalance_on(targets: pd.DataFrame, prices: pd.DataFrame, when: pd.Series) -> pd.DataFrame:
    """Applique les poids cibles seulement les jours `when` ; entre deux, les poids dérivent avec les prix.

    Sans cette fonction, des poids constants signifient « rééquilibrage quotidien » (et coûts associés).
    La trésorerie (1 − somme des poids) rapporte 0.
    """
    px = prices.ffill()
    targets = targets.reindex(index=px.index, columns=px.columns).fillna(0.0)
    when = pd.Series(when, index=px.index).fillna(False).astype(bool)
    seg = when.astype(int).cumsum()
    pieces = []
    for sid, idx in seg.groupby(seg).groups.items():
        if sid == 0:
            continue  # avant le premier rééquilibrage : aucune position
        d0 = idx[0]
        base = px.loc[d0]
        w0 = targets.loc[d0].where(base.notna(), 0.0)
        rel = px.loc[idx] / base
        val = rel.mul(w0, axis=1).fillna(0.0)
        port = 1.0 + (val - w0).sum(axis=1)
        pieces.append(val.div(port, axis=0))
    if not pieces:
        return pd.DataFrame(0.0, index=px.index, columns=px.columns)
    return pd.concat(pieces).reindex(px.index).fillna(0.0)
