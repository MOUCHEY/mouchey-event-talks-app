"""Télécharge les clôtures ajustées (dividendes et splits) depuis Yahoo Finance via yfinance.

    python scripts/fetch_data.py                 # période de recherche seulement (ce que l'agent peut lancer)
    python scripts/fetch_data.py --with-holdout  # + historique complet pour l'examen final (humain)
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402

from lab.config import load_config, resolve  # noqa: E402


def download(tickers: list[str], start: str) -> pd.DataFrame:
    try:
        import yfinance as yf
    except ImportError:
        raise SystemExit("yfinance manquant : pip install -r requirements.txt")
    raw = yf.download(tickers, start=start, auto_adjust=True, progress=False, group_by="column", threads=True)
    if raw is None or raw.empty:
        raise SystemExit("Téléchargement vide : vérifie ta connexion (Yahoo Finance est-il accessible ?)")
    close = raw["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw[["Close"]].set_axis(tickers, axis=1)
    if isinstance(close, pd.Series):
        close = close.to_frame(tickers[0])
    close.index = pd.to_datetime(close.index)
    if close.index.tz is not None:
        close.index = close.index.tz_localize(None)
    close = close.reindex(columns=tickers).sort_index().dropna(how="all")
    close.index.name = "date"
    return close


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--with-holdout", action="store_true", help="écrit aussi l'historique complet (examen final)")
    args = ap.parse_args()

    cfg = load_config()
    d = cfg["data"]
    close = download(d["universe"], d["start"])
    missing = [t for t in d["universe"] if close[t].isna().all()]
    if missing:
        print(f"⚠ Aucune donnée pour : {', '.join(missing)}")

    cutoff = pd.Timestamp(d["holdout_start"])
    research = close[close.index < cutoff]
    out = resolve(d["research_file"])
    out.parent.mkdir(parents=True, exist_ok=True)
    research.to_csv(out, float_format="%.6f")
    print(f"Recherche : {out} ({research.index[0].date()} → {research.index[-1].date()}, {len(research)} jours)")

    if args.with_holdout:
        hold = resolve(d["holdout_file"])
        hold.parent.mkdir(parents=True, exist_ok=True)
        close.to_csv(hold, float_format="%.6f")
        print(f"Holdout   : {hold} (jusqu'au {close.index[-1].date()}) — ne pas le montrer à l'agent")

    resolve(d["source_file"]).write_text(json.dumps({
        "source": "yfinance",
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "tickers": d["universe"],
        "first": str(close.index[0].date()),
        "last_research": str(research.index[-1].date()),
    }, indent=2))


if __name__ == "__main__":
    main()
