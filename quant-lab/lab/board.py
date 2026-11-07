"""Classement des stratégies, scores recalculés avec le N actuel.

    python -m lab.board            # top 10
    python -m lab.board --top 25
"""
from __future__ import annotations

import argparse

from . import metrics, registry
from .config import load_config, results_path


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m lab.board")
    ap.add_argument("--top", type=int, default=10)
    args = ap.parse_args(argv)

    cfg = load_config()
    ppy = cfg["backtest"]["periods_per_year"]
    df = registry.read_results(results_path(cfg))
    if df.empty:
        print("Aucun essai pour l'instant. Commence par : python -m lab.run strategies/baseline_equal_weight.py")
        return

    counted = df[df["status"] != registry.STRESS]
    n = registry.count_trials(df)
    rejected = counted.drop_duplicates("strategy_hash", keep="last")
    n_rej = int((rejected["status"] == registry.REJECTED).sum())
    print(f"Essais distincts N = {n} (dont {n_rej} rejetés) · décote actuelle ≈ "
          f"{metrics.haircut_per_period(n, int(counted['T'].median())) * ppy ** 0.5:.2f} de Sharpe")

    if df["harness_hash"].nunique() > 1:
        print(f"⚠ {df['harness_hash'].nunique()} versions du juge dans le registre : les scores ne sont pas comparables.")
    sources = set(df["data_source"].astype(str))
    if sources != {"yfinance"}:
        print(f"⚠ Sources de données dans le registre : {', '.join(sorted(sources))}")

    ok = df[df["status"] == registry.ACCEPTED].drop_duplicates("strategy_hash", keep="last").copy()
    if ok.empty:
        print("Aucune stratégie acceptée.")
        return
    ok["score_now"] = [metrics.deflate(r.sr_d, int(r.T), r.skew, r.kurt, n, ppy)["score"] for r in ok.itertuples()]
    ok["dsr_now"] = [metrics.deflate(r.sr_d, int(r.T), r.skew, r.kurt, n, ppy)["dsr"] for r in ok.itertuples()]
    ok = ok.sort_values("score_now", ascending=False).head(args.top)

    print(f"\n{'#':>4} {'score':>6} {'P>0':>5} {'Sharpe':>6} {'maxDD':>6} {'turn':>5} {'corrB':>5}  stratégie / paramètres / note")
    for r in ok.itertuples():
        print(f"{int(r.trial):>4} {r.score_now:>6.2f} {r.dsr_now:>5.0%} {r.sharpe:>6.2f} {r.max_dd:>6.0%} "
              f"{r.turnover:>5.1f} {r.corr_baseline:>5.2f}  {r.strategy} {r.params}")
        if isinstance(r.note, str) and r.note:
            print(f"{'':>40}↳ {r.note}")


if __name__ == "__main__":
    main()
