"""Momentum de série temporelle : un actif en hausse sur 12 mois a tendance à continuer le mois suivant.

Mécanisme : sous-réaction initiale aux informations puis sur-réaction tardive (comportemental),
            et demande de couverture persistante (structurel).
Source    : Moskowitz, Ooi & Pedersen (2012), « Time Series Momentum », Journal of Financial Economics ;
            Hurst, Ooi & Pedersen (2017), « A Century of Evidence on Trend-Following Investing ».
Prédiction : Sharpe positif sur la plupart des périodes, et surtout pendant les krachs prolongés
             (corrélation faible ou négative à la baseline en 2008).
Paramètres : 12 mois et volatilité sur 3 mois, valeurs standard de l'article — non optimisées.
"""
import numpy as np
import pandas as pd

from lab import tools

PARAMS = {"lookback": 252, "vol_lookback": 63, "target_vol": 0.20, "long_only": False, "max_gross": 1.5}


def signal(prices: pd.DataFrame, lookback: int, vol_lookback: int, target_vol: float,
           long_only: bool, max_gross: float) -> pd.DataFrame:
    past_return = prices / prices.shift(lookback) - 1
    direction = np.sign(past_return)
    if long_only:
        direction = direction.clip(lower=0)
    vol = tools.ann_vol(prices, vol_lookback)
    n_assets = prices.notna().sum(axis=1).clip(lower=1)
    targets = (direction * target_vol / vol).div(n_assets, axis=0)  # chaque actif pèse à risque égal
    targets = tools.cap_gross(targets.replace([np.inf, -np.inf], np.nan).fillna(0.0), max_gross)
    return tools.rebalance_on(targets, prices, tools.month_starts(prices.index))
