"""<Hypothèse en une phrase : quel comportement du marché, et pourquoi il devrait exister.>

Mécanisme : <prime de risque ? biais comportemental ? contrainte structurelle ? — sinon, pas d'expérience>
Source    : <Auteur (année), revue — ou « idée originale »>
Prédiction : <ce qu'on doit observer si l'hypothèse est vraie, et ce qui la réfuterait>
Paramètres : <d'où viennent les valeurs de PARAMS (article, valeur ronde) — choisies AVANT de voir le score>
"""
import numpy as np
import pandas as pd

from lab import tools

PARAMS = {"lookback": 252}


def signal(prices: pd.DataFrame, lookback: int) -> pd.DataFrame:
    """Poids cibles décidés à la clôture de chaque date (une ligne par date de `prices`, une colonne par actif).

    Règle d'or : les poids de la date t n'utilisent que prices.loc[:t].
    Poids > 0 = acheteur, < 0 = vendeur, la part non investie est en trésorerie (rendement 0).
    """
    past_return = prices / prices.shift(lookback) - 1
    targets = (past_return > 0).astype(float)
    targets = targets.div(prices.notna().sum(axis=1).clip(lower=1), axis=0)
    return tools.rebalance_on(targets, prices, tools.month_starts(prices.index))
