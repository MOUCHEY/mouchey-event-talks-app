"""Évaluation d'une stratégie : chargement, contrôles, backtest, mesures, portes."""
from __future__ import annotations

import ast
import functools
import importlib.util
import itertools
import math
from pathlib import Path

import pandas as pd

from . import checks, metrics
from .backtest import run_backtest
from .config import ROOT


def load_strategy(path: Path):
    path = path if path.is_absolute() else (Path.cwd() / path)
    if not path.exists():
        raise SystemExit(f"Stratégie introuvable : {path}")
    spec = importlib.util.spec_from_file_location(f"strategy_{path.stem}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not callable(getattr(module, "signal", None)):
        raise SystemExit(f"{path.name} doit définir une fonction signal(prices, **params)")
    return module, path


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def parse_assignments(items: list[str] | None) -> dict:
    out = {}
    for item in items or []:
        key, _, raw = item.partition("=")
        if not key or not raw:
            raise SystemExit(f"Format attendu clé=valeur, reçu : {item!r}")
        try:
            out[key.strip()] = ast.literal_eval(raw)
        except (ValueError, SyntaxError):
            out[key.strip()] = raw
    return out


def param_combinations(module, sets: list[str] | None, grids: list[str] | None, max_combos: int = 50) -> list[dict]:
    defaults = dict(getattr(module, "PARAMS", {}))
    fixed = parse_assignments(sets)
    grid = {}
    for item in grids or []:
        key, _, raw = item.partition("=")
        grid[key.strip()] = [parse_assignments([f"v={v}"])["v"] for v in raw.split(",") if v.strip()]
    for key in list(fixed) + list(grid):
        if key not in defaults:
            raise SystemExit(f"Paramètre inconnu {key!r} : déclare-le dans PARAMS ({sorted(defaults)})")
    combos = [dict(zip(grid, vals)) for vals in itertools.product(*grid.values())] or [{}]
    if len(combos) > max_combos:
        raise SystemExit(f"{len(combos)} combinaisons : maximum {max_combos} par appel (chacune compte comme un essai)")
    return [{**defaults, **fixed, **c} for c in combos]


def signal_fn(module, params: dict):
    return functools.partial(module.signal, **params)


def evaluate(cfg: dict, prices: pd.DataFrame, fn, cost_bps: float, check: bool = True,
             start: str | None = None, end: str | None = None, baseline_net: pd.Series | None = None) -> dict:
    """Renvoie un dict de mesures + 'net' (rendements nets sur la fenêtre notée) + 'reasons' (portes échouées)."""
    g, ppy = cfg["gates"], cfg["backtest"]["periods_per_year"]
    reasons, info = [], {}

    if check:
        ok, msg, weights = checks.lookahead_check(fn, prices, g["lookahead_checks"], g["min_history"])
        info["lookahead"] = msg
        if not ok:
            reasons.append(msg)
    else:
        weights = checks.call_signal(fn, prices)

    bt = run_backtest(prices, weights, cost_bps)
    lo = pd.Timestamp(start or cfg["data"]["eval_start"])
    window = bt[bt.index >= lo]
    if end is not None:
        window = window[window.index < pd.Timestamp(end)]
    if len(window) < 60:
        raise SystemExit(f"Fenêtre notée trop courte ({len(window)} jours) : vérifie les dates et les données.")

    net = window["net"]
    stats = metrics.summarize(net, ppy)
    years = len(window) / ppy
    stats["turnover"] = float(window["turnover"].sum() / years)
    stats["max_leverage"] = float(window["leverage"].max())
    folds = metrics.fold_sharpes(net, g["n_folds"], ppy)
    stats["folds"] = [round(f, 2) for f in folds]
    stats["folds_pos"] = sum(1 for f in folds if f > 0)
    stats["corr_baseline"] = float(net.corr(baseline_net.reindex(net.index))) if baseline_net is not None else float("nan")
    stats["start"], stats["end"] = window.index[0].date(), window.index[-1].date()

    if math.isnan(stats["sharpe"]):
        reasons.append("aucune position (rendements constants)")
    if stats["max_leverage"] > g["max_gross_leverage"] + 1e-9:
        reasons.append(f"levier {stats['max_leverage']:.2f} > {g['max_gross_leverage']}")
    if stats["max_dd"] > g["max_drawdown"]:
        reasons.append(f"drawdown {stats['max_dd']:.0%} > {g['max_drawdown']:.0%}")
    if stats["turnover"] > g["max_annual_turnover"]:
        reasons.append(f"turnover {stats['turnover']:.1f}x/an > {g['max_annual_turnover']}x")
    if stats["folds_pos"] < g["min_positive_folds"]:
        reasons.append(f"Sharpe positif sur {stats['folds_pos']}/{g['n_folds']} périodes seulement (min {g['min_positive_folds']})")

    return {**stats, **info, "net": net, "reasons": reasons}
