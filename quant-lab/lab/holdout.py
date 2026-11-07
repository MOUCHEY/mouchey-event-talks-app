"""EXAMEN FINAL sur la période réservée. Lancé par un HUMAIN, jamais par l'agent.

    python -m lab.holdout strategies/ma_strategie.py [--set clé=valeur]

Chaque examen « use » le holdout : si tu ajustes une stratégie après l'avoir vue échouer ici puis la
re-présentes, le holdout devient une période de recherche comme les autres. Garde-le pour les finalistes.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from . import checks, metrics, registry
from .config import holdout_log_path, load_config, resolve, results_path
from .data import full_prices
from .evaluate import display_path, evaluate, load_strategy, param_combinations, signal_fn


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m lab.holdout", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("strategy", type=Path)
    ap.add_argument("--set", action="append", metavar="clé=valeur")
    args = ap.parse_args(argv)

    cfg = load_config()
    ppy = cfg["backtest"]["periods_per_year"]
    if checks.static_guard(args.strategy.read_text()):
        raise SystemExit("⛔ Code refusé par le contrôle statique : passe d'abord par lab.run.")
    module, path = load_strategy(args.strategy)
    params = param_combinations(module, args.set, None)[0]
    s_hash = registry.strategy_hash(path, params)

    df = registry.read_results(results_path(cfg))
    match = df[(df["strategy_hash"] == s_hash) & (df["status"] == registry.ACCEPTED)]
    if match.empty:
        raise SystemExit("⛔ Ce code + ces paramètres n'ont pas été ACCEPTÉS par lab.run : rien à examiner.")
    research = match.iloc[-1]

    log_path = holdout_log_path(cfg)
    past = pd.read_csv(log_path, sep="\t") if log_path.exists() else pd.DataFrame()
    if len(past) >= 3:
        print(f"⚠ {len(past)} examens déjà passés sur ce holdout : il s'use. Pense à le renouveler (nouvelles données).")

    prices = full_prices(cfg)
    hold_start = cfg["data"]["holdout_start"]
    base_mod, _ = load_strategy(resolve(cfg["lab"]["baseline"]))
    base = evaluate(cfg, prices, signal_fn(base_mod, dict(getattr(base_mod, "PARAMS", {}))),
                    cfg["backtest"]["cost_bps"], check=False, start=hold_start)
    res = evaluate(cfg, prices, signal_fn(module, params), cfg["backtest"]["cost_bps"],
                   start=hold_start, baseline_net=base["net"])
    p_pos = metrics.psr(res["sr_d"], 0.0, res["T"], res["skew"], res["kurt"])

    print(f"\n═══ EXAMEN HOLDOUT · {display_path(path)} {json.dumps(params, sort_keys=True)}")
    print(f"Période {res['start']} → {res['end']} ({res['T']} jours) · anti-lookahead : {res.get('lookahead')}")
    print(f"Recherche : Sharpe {research['sharpe']:.2f} (score déflaté {research['score']:.2f}, N = {int(research['n_trials'])})")
    print(f"Holdout   : Sharpe {res['sharpe']:.2f} | rendement {res['ann_return']:.1%}/an | max DD {res['max_dd']:.1%} "
          f"| P(Sharpe > 0) = {p_pos:.0%}")
    print(f"Baseline sur la même période : Sharpe {base['sharpe']:.2f} · corrélation {res['corr_baseline']:.2f}")
    ratio = res["sharpe"] / research["sharpe"] if research["sharpe"] else float("nan")
    print(f"Sharpe holdout / recherche = {ratio:.0%}. Une perte de moitié est courante ; un signe inversé = échec.")

    row = pd.DataFrame([{
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "strategy": display_path(path), "params": json.dumps(params, sort_keys=True), "strategy_hash": s_hash,
        "research_trial": int(research["trial"]), "research_sharpe": research["sharpe"],
        "holdout_sharpe": res["sharpe"], "holdout_p_pos": p_pos, "holdout_max_dd": res["max_dd"],
        "baseline_sharpe": base["sharpe"], "start": res["start"], "end": res["end"],
    }])
    log_path.parent.mkdir(parents=True, exist_ok=True)
    row.to_csv(log_path, sep="\t", index=False, header=not log_path.exists(), mode="a", float_format="%.6g")
    print(f"Consigné dans {log_path}\n")


if __name__ == "__main__":
    main()
