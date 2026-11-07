"""Contrôles automatiques : causalité (anti-lookahead), déterminisme, pas d'accès aux données en douce."""
from __future__ import annotations

import io
import re
import tokenize
from typing import Callable

import numpy as np
import pandas as pd

# Une stratégie reçoit ses données en argument et n'a pas à en lire d'autres.
# Vérifié sur les identifiants du code (les commentaires sont ignorés).
_FORBIDDEN_NAMES = {
    "lecture de fichier": r"^(read_\w+|open|loadtxt|genfromtxt|fromfile|Path|os|shutil|glob|pickle)$",
    "accès réseau / système": r"^(yfinance|requests|urllib|httpx|socket|subprocess|sys)$",
    "accès direct aux données du juge": r"^(full_prices|research_prices|holdout)$",
    "import ou exécution dynamique": r"^(__import__|importlib|eval|exec|globals|getattr)$",
}
_FORBIDDEN_STRINGS = r"\.(csv|parquet|pkl|json|feather|h5|xlsx?)\b|/"
# Seul `from lab import tools` (ou `import lab.tools`) est permis parmi les modules du juge.
_LAB_IMPORT = (
    r"\bfrom lab import (?!tools$)"
    r"|\bfrom lab \. (?!tools\b)"
    r"|\bimport lab$"
    r"|\blab \. (?!tools\b)\w"
)


def static_guard(source: str) -> list[str]:
    names, strings, code_lines, line = set(), [], [], []
    for tok in tokenize.generate_tokens(io.StringIO(source).readline):
        if tok.type == tokenize.NAME:
            names.add(tok.string)
            line.append(tok.string)
        elif tok.type == tokenize.OP:
            line.append(tok.string)
        elif tok.type == tokenize.STRING:
            strings.append(tok.string)
        elif tok.type in (tokenize.NEWLINE, tokenize.NL) and line:
            code_lines.append(" ".join(line))
            line = []
    problems = [
        f"{why} ({', '.join(sorted(n for n in names if re.match(pat, n)))})"
        for why, pat in _FORBIDDEN_NAMES.items()
        if any(re.match(pat, n) for n in names)
    ]
    # Les docstrings peuvent citer des sources (URL…) : on ne contrôle que les autres chaînes.
    if any(re.search(_FORBIDDEN_STRINGS, s) for s in strings if not s.startswith(('"""', "'''"))):
        problems.append("chemin de fichier ou URL dans une chaîne")
    if any(re.search(_LAB_IMPORT, l) for l in code_lines):
        problems.append("import d'un module du juge (seul `from lab import tools` est permis)")
    return problems


def call_signal(fn: Callable, prices: pd.DataFrame) -> pd.DataFrame:
    w = fn(prices.copy())
    if not isinstance(w, pd.DataFrame):
        raise TypeError(f"signal() doit renvoyer un DataFrame de poids, pas {type(w).__name__}")
    if not isinstance(w.index, pd.DatetimeIndex):
        raise TypeError("les poids doivent être indexés par date (DatetimeIndex)")
    coverage = w.index.isin(prices.index).sum() / len(prices.index)
    if coverage < 0.99:
        raise ValueError(
            f"signal() ne renvoie des poids que pour {coverage:.0%} des dates : "
            "il faut une ligne par date de `prices` (utilise tools.rebalance_on pour un rééquilibrage périodique)"
        )
    return w


def _compare(a: pd.DataFrame, b: pd.DataFrame, dates: pd.DatetimeIndex, labels=("historique complet", "historique tronqué"),
             tol: float = 1e-9) -> tuple[bool, str]:
    cols = a.columns.union(b.columns)
    x = a.reindex(index=dates, columns=cols).fillna(0.0).to_numpy(float)
    y = b.reindex(index=dates, columns=cols).fillna(0.0).to_numpy(float)
    bad = np.abs(x - y) > tol * (1 + np.abs(x))
    if not bad.any():
        return True, ""
    i, j = np.argwhere(bad)[0]
    return False, f"{cols[j]} le {dates[i].date()} : {x[i, j]:.6g} ({labels[0]}) ≠ {y[i, j]:.6g} ({labels[1]})"


def lookahead_check(fn: Callable, prices: pd.DataFrame, n_checks: int, min_history: int):
    """Le poids décidé en t ne doit pas changer quand on supprime les données postérieures à t.

    Renvoie (ok, message, poids_sur_historique_complet).
    """
    full = call_signal(fn, prices)
    again = call_signal(fn, prices)
    ok, msg = _compare(full, again, prices.index, ("1er appel", "2e appel"))
    if not ok:
        return False, f"non déterministe (fixe la graine aléatoire) — {msg}", full

    n = len(prices)
    candidates = np.arange(min(min_history, n - 2), n - 1)
    rng = np.random.default_rng()
    cuts = np.sort(rng.choice(candidates, size=min(n_checks, len(candidates)), replace=False))
    for c in cuts:
        part = call_signal(fn, prices.iloc[: c + 1])
        ok, msg = _compare(full, part, prices.index[: c + 1])
        if not ok:
            return False, f"lookahead détecté (coupure au {prices.index[c].date()}) — {msg}", full
    dates = ", ".join(str(prices.index[c].date()) for c in cuts)
    return True, f"OK ({len(cuts)} coupures : {dates})", full
