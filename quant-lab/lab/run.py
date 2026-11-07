"""Point d'entrée UNIQUE pour noter une stratégie. Chaque appel est consigné dans results.tsv.

    python -m lab.run strategies/ma_strategie.py --note "hypothèse courte"
    python -m lab.run strategies/ma_strategie.py --set lookback=126
    python -m lab.run strategies/ma_strategie.py --grid lookback=63,126,252     # 3 essais
    python -m lab.run strategies/ma_strategie.py --cost-bps 20                   # test de stress, non compté
"""
from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path

from . import checks, metrics, registry
from .config import load_config, resolve, results_path
from .data import data_source, research_prices
from .evaluate import display_path, evaluate, load_strategy, param_combinations, signal_fn


def baseline_returns(cfg, prices):
    module, _ = load_strategy(resolve(cfg["lab"]["baseline"]))
    fn = signal_fn(module, dict(getattr(module, "PARAMS", {})))
    res = evaluate(cfg, prices, fn, cfg["backtest"]["cost_bps"], check=False)
    return res["net"], res["sharpe"]


def best_so_far(df, n_trials, ppy):
    ok = df[df["status"] == registry.ACCEPTED].drop_duplicates("strategy_hash", keep="last")
    if ok.empty:
        return None
    scores = [metrics.deflate(r.sr_d, int(r.T), r.skew, r.kurt, n_trials, ppy)["score"] for r in ok.itertuples()]
    best = ok.assign(score_now=scores).sort_values("score_now", ascending=False).iloc[0]
    return best


def fmt_params(params: dict) -> str:
    return json.dumps(params, sort_keys=True, default=str, ensure_ascii=False)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m lab.run", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("strategy", type=Path)
    ap.add_argument("--set", action="append", metavar="clé=valeur", help="fixe un paramètre")
    ap.add_argument("--grid", action="append", metavar="clé=v1,v2", help="balaye un paramètre (1 essai par valeur)")
    ap.add_argument("--note", default=None, help="hypothèse en une ligne (défaut : 1re ligne de la docstring)")
    ap.add_argument("--cost-bps", type=float, default=None, help="test de stress des coûts (non compté comme essai)")
    args = ap.parse_args(argv)

    cfg = load_config()
    ppy = cfg["backtest"]["periods_per_year"]
    stress = args.cost_bps is not None
    cost_bps = args.cost_bps if stress else cfg["backtest"]["cost_bps"]

    state, msg = registry.harness_git_state()
    if state == "dirty":
        raise SystemExit(f"⛔ {msg}. Le juge doit être identique à sa version commitée par un humain.")
    if msg:
        print(f"⚠ {msg}")

    source = data_source(cfg)
    if source != "yfinance":
        print(f"⚠ Source des données : {source}. Les résultats ne valent RIEN pour la recherche, "
              "seulement pour tester le harness.")
    prices = research_prices(cfg)
    if not args.strategy.exists():
        raise SystemExit(f"Stratégie introuvable : {args.strategy}")
    problems = checks.static_guard(args.strategy.read_text())
    if problems:  # refusé AVANT d'exécuter le moindre code de la stratégie
        raise SystemExit("⛔ Code refusé : " + " ; ".join(problems) +
                         "\nUne stratégie ne reçoit que `prices` et n'utilise que pandas, numpy et lab.tools.")
    module, path = load_strategy(args.strategy)
    rel = display_path(path)

    combos = param_combinations(module, args.set, args.grid)
    base_net, base_sharpe = baseline_returns(cfg, prices)
    note = args.note or ((module.__doc__ or "").strip().splitlines() or [""])[0][:120]
    out_path = results_path(cfg)
    h_hash = registry.harness_hash()

    for params in combos:
        s_hash = registry.strategy_hash(path, params)
        res = evaluate(cfg, prices, signal_fn(module, params), cost_bps, baseline_net=base_net)
        reasons = res["reasons"]

        with registry.locked(out_path):
            df = registry.read_results(out_path)
            n_trials = registry.count_trials(df, None if stress else s_hash)
            d = metrics.deflate(res["sr_d"], res["T"], res["skew"], res["kurt"], max(n_trials, 1), ppy)
            status = registry.STRESS if stress else (registry.REJECTED if reasons else registry.ACCEPTED)
            trial = registry.next_trial_id(df)
            registry.append_result(out_path, {
                "trial": trial,
                "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "strategy": rel, "params": fmt_params(params), "strategy_hash": s_hash,
                "harness_hash": h_hash, "data_source": source, "status": status,
                "reasons": " | ".join(reasons),
                **{k: res[k] for k in ("sharpe", "ann_return", "ann_vol", "max_dd", "turnover", "max_leverage",
                                       "folds_pos", "corr_baseline", "T", "sr_d", "skew", "kurt")},
                "folds": json.dumps(res["folds"]), "n_trials": n_trials,
                "haircut": d["haircut"], "score": d["score"] if status == registry.ACCEPTED else float("nan"),
                "dsr": d["dsr"], "cost_bps": cost_bps, "note": note.replace("\t", " ").replace("\n", " "),
            })
            df = registry.read_results(out_path)
            best = best_so_far(df, n_trials, ppy)

        print(f"\n═══ Essai #{trial} · {rel} {fmt_params(params)}")
        print(f"Fenêtre notée {res['start']} → {res['end']} ({res['T']} jours) · coûts {cost_bps:g} pb · données : {source}")
        print(f"Anti-lookahead : {res.get('lookahead', '—')}")
        print(f"Sharpe {res['sharpe']:.2f} | rendement {res['ann_return']:.1%}/an | vol {res['ann_vol']:.1%} | "
              f"max DD {res['max_dd']:.1%} | turnover {res['turnover']:.1f}x/an | levier max {res['max_leverage']:.2f}")
        print(f"Sharpe par période {res['folds']} → positifs {res['folds_pos']}/{len(res['folds'])} · "
              f"corrélation à la baseline {res['corr_baseline']:.2f} (baseline : Sharpe {base_sharpe:.2f})")
        if stress:
            print(f"Statut : STRESS (non compté dans N) · Sharpe net à {cost_bps:g} pb = {res['sharpe']:.2f}")
            continue
        print(f"Essais distincts N = {n_trials} → décote {d['haircut']:.2f} → "
              f"SCORE (Sharpe déflaté) = {d['score']:.2f} · P(vrai Sharpe > décote) = {d['dsr']:.0%}")
        if reasons:
            print("Statut : REJETÉ → " + " | ".join(reasons))
        else:
            print("Statut : ACCEPTÉ")
        if best is not None:
            print(f"Meilleur score actuel (recalculé avec N = {n_trials}) : {best['score_now']:.2f} "
                  f"— essai #{int(best['trial'])} {best['strategy']} {best['params']}")
    print()


if __name__ == "__main__":
    main()
