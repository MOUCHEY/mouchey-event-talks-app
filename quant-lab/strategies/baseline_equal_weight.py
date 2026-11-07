"""Référence : poids égaux sur tous les actifs cotés, rééquilibrage le premier jour de chaque mois.

Ce n'est pas une hypothèse de recherche : c'est l'étalon. Une stratégie qui ne fait pas mieux,
ou qui lui est corrélée à 0,95, n'apporte rien.
"""
import pandas as pd

from lab import tools

PARAMS = {}


def signal(prices: pd.DataFrame) -> pd.DataFrame:
    listed = prices.notna().astype(float)
    targets = listed.div(listed.sum(axis=1).clip(lower=1), axis=0)
    return tools.rebalance_on(targets, prices, tools.month_starts(prices.index))
