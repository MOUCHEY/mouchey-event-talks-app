"""
evaluate.py — L'ARBITRE du mini système AutoResearch.

  ⚠️  CE FICHIER EST GELÉ. On ne le modifie JAMAIS pendant l'optimisation.
      Son empreinte SHA-256 est stockée dans evaluate.sha256 et vérifiée
      à chaque lancement. Seul train.py change d'une expérience à l'autre.

Rôle :
  * charger load_digits et réserver un TEST FINAL (20 %) jamais vu pendant la recherche ;
  * évaluer le modèle de train.py sur 5 découpages train/validation répétés ;
  * chronométrer, appliquer la limite de 2 minutes et le budget de 10 expériences ;
  * décider, avec une règle fixée à l'avance, si un changement est une amélioration robuste ;
  * tout enregistrer dans results.csv (y compris les échecs) ;
  * exécuter UNE SEULE fois l'évaluation finale sur le test réservé.

Commandes :
  python evaluate.py check                         # vérifie prérequis + intégrité des découpages
  python evaluate.py run --hypothesis "..."        # lance une expérience (train.py actuel)
  python evaluate.py status                        # tableau des expériences + budget
  python evaluate.py restore                       # remet dans train.py la meilleure version
  python evaluate.py final                         # évaluation finale unique sur le test
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import traceback
import warnings
from datetime import datetime
from pathlib import Path

import numpy as np

# ---------------------------------------------------------------------------
# 1. Constantes du protocole (fixées AVANT de voir le moindre résultat)
# ---------------------------------------------------------------------------
PROJECT_DIR = Path(__file__).resolve().parent
TRAIN_PATH = PROJECT_DIR / "train.py"
RESULTS_PATH = PROJECT_DIR / "results.csv"
HASH_PATH = PROJECT_DIR / "evaluate.sha256"
SNAPSHOT_DIR = PROJECT_DIR / "experiments"
FINAL_PATH = PROJECT_DIR / "final_result.json"

TEST_SPLIT_SEED = 42        # graine du découpage développement / test (ne change jamais)
TEST_SIZE = 0.20            # 20 % des images réservées au test final
VAL_SIZE = 0.25             # 25 % du jeu de développement servent de validation
REPEAT_SEEDS = (0, 1, 2, 3, 4)  # 5 répétitions : découpage train/val + graine du modèle
TIME_LIMIT_S = 120          # 2 minutes de calcul maximum par expérience
MAX_EXPERIMENTS = 10        # budget (la référence, expérience 0, n'est pas comptée)
MIN_GAIN = 0.002            # gain moyen minimal en exactitude (0,2 point) pour accepter
MIN_WINS = 3                # le candidat doit battre le meilleur sur >= 3 découpages sur 5…
MAX_LOSSES = 1              # … et perdre sur au plus 1 découpage

COLUMNS = [
    "exp_id", "role", "timestamp", "hypothesis", "status", "decision", "reason",
    "val_acc_mean", "val_acc_std", "val_acc_min", "val_f1_mean", "train_acc_mean",
    "overfit_gap", "val_acc_per_seed", "seeds", "duration_s", "fit_time_mean_s",
    "params", "model", "warnings", "error", "train_sha256", "evaluate_sha256", "snapshot",
]


# ---------------------------------------------------------------------------
# 2. Outils d'intégrité
# ---------------------------------------------------------------------------
def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_frozen_evaluator() -> str:
    """Refuse de travailler si evaluate.py a été modifié depuis son gel."""
    current = sha256_of(Path(__file__).resolve())
    if not HASH_PATH.exists():
        sys.exit("ERREUR : evaluate.sha256 absent — l'arbitre n'a pas été gelé.")
    frozen = HASH_PATH.read_text().split()[0]
    if current != frozen:
        sys.exit(
            "ERREUR : evaluate.py a été modifié depuis son gel "
            f"(attendu {frozen[:12]}…, obtenu {current[:12]}…). Expérience refusée."
        )
    return current


# ---------------------------------------------------------------------------
# 3. Données : développement (train+val) et test réservé
# ---------------------------------------------------------------------------
def _split_indices():
    """Indices du découpage développement/test. Déterministe grâce à TEST_SPLIT_SEED."""
    from sklearn.datasets import load_digits
    from sklearn.model_selection import train_test_split

    X, y = load_digits(return_X_y=True)
    idx = np.arange(len(y))
    dev_idx, test_idx = train_test_split(
        idx, test_size=TEST_SIZE, stratify=y, random_state=TEST_SPLIT_SEED
    )
    return X, y, dev_idx, test_idx


def load_dev():
    """Données de DÉVELOPPEMENT uniquement. Le test n'est jamais renvoyé ici."""
    X, y, dev_idx, _ = _split_indices()
    return X[dev_idx], y[dev_idx]


def split_train_val(X_dev, y_dev, seed: int):
    from sklearn.model_selection import train_test_split

    return train_test_split(X_dev, y_dev, test_size=VAL_SIZE, stratify=y_dev, random_state=seed)


# ---------------------------------------------------------------------------
# 4. Le « travailleur » : exécuté dans un processus séparé, chronométré
# ---------------------------------------------------------------------------
def _worker(out_path: str) -> None:
    """Importe train.py, entraîne/évalue sur les 5 découpages, écrit un JSON."""
    result: dict = {"status": "error"}
    try:
        from sklearn.metrics import accuracy_score, f1_score

        sys.path.insert(0, str(PROJECT_DIR))
        import train  # le seul fichier modifié pendant la recherche

        X_dev, y_dev = load_dev()
        val_acc, val_f1, train_acc, fit_times = [], [], [], []
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            for seed in REPEAT_SEEDS:
                X_tr, X_val, y_tr, y_val = split_train_val(X_dev, y_dev, seed)
                model = train.build_model(seed)
                t0 = time.perf_counter()
                model.fit(X_tr, y_tr)
                fit_times.append(time.perf_counter() - t0)
                pred_val = model.predict(X_val)
                val_acc.append(accuracy_score(y_val, pred_val))
                val_f1.append(f1_score(y_val, pred_val, average="macro"))
                train_acc.append(accuracy_score(y_tr, model.predict(X_tr)))
        msgs = sorted({f"{w.category.__name__}: {str(w.message)[:120]}" for w in caught})
        result = {
            "status": "ok",
            "val_acc": val_acc,
            "val_f1": val_f1,
            "train_acc": train_acc,
            "fit_times": fit_times,
            "params": getattr(train, "PARAMS", {}),
            "model": " ".join(repr(train.build_model(REPEAT_SEEDS[0])).split())[:400],
            "warnings": msgs[:3],
        }
    except Exception as exc:  # l'erreur est enregistrée, pas cachée
        result = {
            "status": "error",
            "error": f"{type(exc).__name__}: {exc}"[:300],
            "traceback": traceback.format_exc()[-2000:],
        }
    Path(out_path).write_text(json.dumps(result, default=str))


def _run_worker_with_timeout() -> tuple[dict, float]:
    """Lance le travailleur dans un sous-processus ; le tue s'il dépasse TIME_LIMIT_S."""
    fd, out_path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    env = dict(os.environ, PYTHONHASHSEED="0")
    t0 = time.perf_counter()
    proc = subprocess.Popen(
        [sys.executable, str(Path(__file__).resolve()), "_worker", out_path],
        cwd=PROJECT_DIR, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, start_new_session=True,  # groupe de processus à part → on peut tout tuer
    )
    try:
        _, stderr = proc.communicate(timeout=TIME_LIMIT_S)
        duration = time.perf_counter() - t0
        try:
            result = json.loads(Path(out_path).read_text())
        except (json.JSONDecodeError, FileNotFoundError):
            result = {"status": "error",
                      "error": f"processus terminé (code {proc.returncode}) sans résultat : "
                               f"{stderr.strip()[-250:]}"}
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)  # tue aussi les éventuels sous-processus (n_jobs)
        except (ProcessLookupError, AttributeError):
            proc.kill()
        proc.communicate()
        duration = time.perf_counter() - t0
        result = {"status": "timeout",
                  "error": f"limite de {TIME_LIMIT_S} s dépassée — expérience interrompue"}
    finally:
        Path(out_path).unlink(missing_ok=True)
    return result, duration


# ---------------------------------------------------------------------------
# 5. Journal results.csv et règle de décision
# ---------------------------------------------------------------------------
def read_results() -> list[dict]:
    if not RESULTS_PATH.exists():
        return []
    with RESULTS_PATH.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def append_result(row: dict) -> None:
    new_file = not RESULTS_PATH.exists() or RESULTS_PATH.stat().st_size == 0
    with RESULTS_PATH.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        if new_file:
            writer.writeheader()
        writer.writerow({k: row.get(k, "") for k in COLUMNS})


def current_best(rows: list[dict]) -> dict | None:
    """Le meilleur courant = dernière ligne acceptée (ou la référence)."""
    kept = [r for r in rows if r["decision"] in ("REFERENCE", "ACCEPTE")]
    return kept[-1] if kept else None


def decide(candidate: list[float], best: list[float]) -> tuple[str, str]:
    """Comparaison APPARIÉE : mêmes découpages pour le candidat et le meilleur."""
    diffs = np.array(candidate) - np.array(best)
    wins = int((diffs > 1e-12).sum())
    losses = int((diffs < -1e-12).sum())
    ties = len(diffs) - wins - losses
    mean_gain = float(diffs.mean())
    ok = mean_gain >= MIN_GAIN and wins >= MIN_WINS and losses <= MAX_LOSSES
    reason = (f"gain moyen {mean_gain:+.4f} (seuil {MIN_GAIN}); "
              f"{wins} gagnés / {losses} perdus / {ties} égalités")
    return ("ACCEPTE" if ok else "REJETE"), reason


def _fmt(x: float) -> str:
    return f"{x:.4f}"


# ---------------------------------------------------------------------------
# 6. Commandes
# ---------------------------------------------------------------------------
def cmd_run(hypothesis: str) -> None:
    eval_hash = verify_frozen_evaluator()
    if FINAL_PATH.exists():
        sys.exit("ERREUR : l'évaluation finale a déjà eu lieu. La recherche est close.")
    rows = read_results()
    has_reference = current_best(rows) is not None
    role = "experiment" if has_reference else "baseline"
    n_exp = sum(r["role"] == "experiment" for r in rows)
    if role == "experiment" and n_exp >= MAX_EXPERIMENTS:
        sys.exit(f"BUDGET ÉPUISÉ : {n_exp}/{MAX_EXPERIMENTS} expériences. "
                 "Passez à l'évaluation finale.")
    if role == "experiment" and not hypothesis.strip():
        sys.exit("ERREUR : une hypothèse écrite est obligatoire avant chaque expérience.")

    exp_id = len(rows)
    SNAPSHOT_DIR.mkdir(exist_ok=True)
    snapshot = SNAPSHOT_DIR / f"exp_{exp_id:02d}_train.py"
    shutil.copy2(TRAIN_PATH, snapshot)  # copie exacte du code qui va tourner

    print(f"▶ Expérience {exp_id} ({role}) — hypothèse : {hypothesis or 'modèle de référence'}")
    print(f"  {len(REPEAT_SEEDS)} répétitions, limite {TIME_LIMIT_S} s…")
    res, duration = _run_worker_with_timeout()

    row = {
        "exp_id": exp_id, "role": role, "timestamp": datetime.now().isoformat(timespec="seconds"),
        "hypothesis": hypothesis or "Modèle de référence", "status": res["status"],
        "seeds": ";".join(map(str, REPEAT_SEEDS)), "duration_s": f"{duration:.2f}",
        "error": res.get("error", ""), "train_sha256": sha256_of(snapshot),
        "evaluate_sha256": eval_hash, "snapshot": snapshot.name,
    }
    if res["status"] == "ok":
        va, tr = np.array(res["val_acc"]), np.array(res["train_acc"])
        row.update({
            "val_acc_mean": _fmt(va.mean()), "val_acc_std": _fmt(va.std(ddof=1)),
            "val_acc_min": _fmt(va.min()), "val_f1_mean": _fmt(np.mean(res["val_f1"])),
            "train_acc_mean": _fmt(tr.mean()), "overfit_gap": _fmt(tr.mean() - va.mean()),
            "val_acc_per_seed": ";".join(_fmt(v) for v in va),
            "fit_time_mean_s": f"{np.mean(res['fit_times']):.3f}",
            "params": json.dumps(res["params"], default=str, ensure_ascii=False),
            "model": res["model"], "warnings": " | ".join(res["warnings"]),
        })
        if role == "baseline":
            row["decision"], row["reason"] = "REFERENCE", "premier modèle valide"
        else:
            best = current_best(rows)
            best_scores = [float(v) for v in best["val_acc_per_seed"].split(";")]
            row["decision"], row["reason"] = decide(list(va), best_scores)
            row["reason"] += f" vs exp {best['exp_id']}"
    else:
        row["decision"], row["reason"] = "ECHEC", res["status"]

    append_result(row)
    print(f"  statut   : {row['status']}  ({row['duration_s']} s)")
    if res["status"] == "ok":
        print(f"  val acc  : {row['val_acc_mean']} ± {row['val_acc_std']}  "
              f"(par graine : {row['val_acc_per_seed']})")
        print(f"  train acc: {row['train_acc_mean']}  → écart de sur-apprentissage "
              f"{row['overfit_gap']}")
        if row["warnings"]:
            print(f"  avertissements : {row['warnings']}")
    else:
        print(f"  erreur   : {row['error']}")
    print(f"  DÉCISION : {row['decision']} — {row['reason']}")
    if role == "experiment":
        print(f"  budget   : {n_exp + 1}/{MAX_EXPERIMENTS} expériences utilisées")
    if row["decision"] in ("REJETE", "ECHEC"):
        print("  → pensez à `python evaluate.py restore` pour revenir au meilleur train.py")


def cmd_status() -> None:
    rows = read_results()
    if not rows:
        print("Aucune expérience enregistrée.")
        return
    print(f"{'id':>3} {'rôle':<10} {'statut':<8} {'décision':<10} {'val_acc':>8} "
          f"{'±std':>7} {'durée':>7}  hypothèse")
    for r in rows:
        print(f"{r['exp_id']:>3} {r['role']:<10} {r['status']:<8} {r['decision']:<10} "
              f"{r['val_acc_mean'] or '-':>8} {r['val_acc_std'] or '-':>7} "
              f"{r['duration_s']:>6}s  {r['hypothesis'][:60]}")
    n_exp = sum(r["role"] == "experiment" for r in rows)
    best = current_best(rows)
    print(f"\nBudget : {n_exp}/{MAX_EXPERIMENTS} expériences.")
    if best:
        print(f"Meilleur courant : exp {best['exp_id']} — val acc {best['val_acc_mean']} "
              f"({best['snapshot']})")


def cmd_restore() -> None:
    best = current_best(read_results())
    if not best:
        sys.exit("Aucun modèle de référence à restaurer.")
    shutil.copy2(SNAPSHOT_DIR / best["snapshot"], TRAIN_PATH)
    print(f"train.py restauré depuis {best['snapshot']} (exp {best['exp_id']}).")


def cmd_final() -> None:
    """ÉVALUATION FINALE UNIQUE : entraîne le modèle retenu sur tout le développement,
    puis le mesure UNE fois sur le test réservé. Un verrou empêche toute répétition."""
    eval_hash = verify_frozen_evaluator()
    if FINAL_PATH.exists():
        print(FINAL_PATH.read_text())
        sys.exit("REFUS : l'évaluation finale a déjà été faite (résultat ci-dessus).")
    best = current_best(read_results())
    if not best:
        sys.exit("ERREUR : aucun modèle retenu.")
    if sha256_of(TRAIN_PATH) != best["train_sha256"]:
        sys.exit(f"ERREUR : train.py ne correspond pas au modèle retenu (exp {best['exp_id']}). "
                 "Lancez `python evaluate.py restore` d'abord.")

    from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score

    sys.path.insert(0, str(PROJECT_DIR))
    import train

    X, y, dev_idx, test_idx = _split_indices()
    t0 = time.perf_counter()
    model = train.build_model(REPEAT_SEEDS[0])
    model.fit(X[dev_idx], y[dev_idx])
    pred = model.predict(X[test_idx])
    duration = time.perf_counter() - t0
    y_test = y[test_idx]
    correct = (pred == y_test).astype(float)

    # Intervalle de confiance à 95 % par bootstrap (rééchantillonnage du test)
    rng = np.random.default_rng(0)
    boots = [correct[rng.integers(0, len(correct), len(correct))].mean() for _ in range(2000)]
    lo, hi = np.percentile(boots, [2.5, 97.5])

    final = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "selected_exp_id": int(best["exp_id"]),
        "hypothesis": best["hypothesis"],
        "params": json.loads(best["params"]) if best["params"] else {},
        "validation_acc_mean": float(best["val_acc_mean"]),
        "test_accuracy": float(accuracy_score(y_test, pred)),
        "test_accuracy_ci95": [float(lo), float(hi)],
        "test_f1_macro": float(f1_score(y_test, pred, average="macro")),
        "n_dev": int(len(dev_idx)), "n_test": int(len(test_idx)),
        "n_errors": int((pred != y_test).sum()),
        "confusion_matrix": confusion_matrix(y_test, pred).tolist(),
        "classification_report": classification_report(y_test, pred, output_dict=True),
        "duration_s": round(duration, 3), "seed": REPEAT_SEEDS[0],
        "test_split_seed": TEST_SPLIT_SEED,
        "train_sha256": best["train_sha256"], "evaluate_sha256": eval_hash,
    }
    FINAL_PATH.write_text(json.dumps(final, indent=2, ensure_ascii=False))
    print(f"ÉVALUATION FINALE (exp {best['exp_id']}) — entraînée sur {len(dev_idx)} images, "
          f"testée sur {len(test_idx)}")
    print(f"  exactitude test : {final['test_accuracy']:.4f}  "
          f"(IC 95 % : [{lo:.4f}, {hi:.4f}])  — {final['n_errors']} erreurs")
    print(f"  F1 macro test   : {final['test_f1_macro']:.4f}")
    print(f"  (rappel validation : {best['val_acc_mean']})")
    print("  Matrice de confusion (lignes = vrai chiffre, colonnes = prédiction) :")
    for i, line in enumerate(final["confusion_matrix"]):
        print(f"   {i}: " + " ".join(f"{v:3d}" for v in line))
    print(f"Résultat verrouillé dans {FINAL_PATH.name}.")


def cmd_check() -> None:
    """Prérequis matériels/logiciels + contrôles d'intégrité des découpages."""
    import scipy
    import sklearn

    ok = True

    def report(label: str, good: bool, detail: str = "") -> None:
        nonlocal ok
        ok &= good
        print(f"  [{'OK' if good else 'ÉCHEC'}] {label}{' — ' + detail if detail else ''}")

    print("Logiciel :")
    report("Python >= 3.9", sys.version_info >= (3, 9), platform.python_version())
    in_venv = sys.prefix != sys.base_prefix
    report("Environnement virtuel actif", in_venv, sys.prefix)
    print(f"  [INFO] numpy {np.__version__}, scipy {scipy.__version__}, "
          f"scikit-learn {sklearn.__version__}")
    print("Matériel :")
    try:
        ram_gb = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 1e9
    except (ValueError, OSError, AttributeError):
        ram_gb = float("nan")
    print(f"  [INFO] {platform.system()} {platform.machine()}, {os.cpu_count()} CPU logiques, "
          f"{ram_gb:.1f} Go RAM")
    print("Intégrité :")
    try:
        verify_frozen_evaluator()
        report("evaluate.py identique à son empreinte gelée", True)
    except SystemExit as e:
        report("evaluate.py identique à son empreinte gelée", False, str(e))

    print("Données :")
    X, y, dev_idx, test_idx = _split_indices()
    report("load_digits chargé", X.shape == (1797, 64), f"X {X.shape}, {len(set(y))} classes")
    report("aucune image commune développement/test",
           len(set(dev_idx) & set(test_idx)) == 0,
           f"dev {len(dev_idx)} / test {len(test_idx)}")
    _, _, dev2, test2 = _split_indices()
    report("découpage déterministe (2 appels identiques)",
           np.array_equal(dev_idx, dev2) and np.array_equal(test_idx, test2))
    counts = np.bincount(y[test_idx], minlength=10)
    report("test stratifié (chaque chiffre présent)", counts.min() > 0, f"effectifs {counts.tolist()}")
    X_dev, y_dev = load_dev()
    for seed in REPEAT_SEEDS[:1]:
        X_tr, X_val, _, _ = split_train_val(X_dev, y_dev, seed)
        report(f"découpage train/val (graine {seed})", len(X_tr) + len(X_val) == len(X_dev),
               f"train {len(X_tr)} / val {len(X_val)}")
    print("Modèle :")
    try:
        sys.path.insert(0, str(PROJECT_DIR))
        import train
        m = train.build_model(0)
        report("train.build_model(seed) renvoie un estimateur",
               hasattr(m, "fit") and hasattr(m, "predict"), type(m).__name__)
    except Exception as exc:
        report("train.py importable", False, f"{type(exc).__name__}: {exc}")
    print("\nTOUS LES PRÉREQUIS SONT SATISFAITS." if ok else "\nCERTAINS CONTRÔLES ONT ÉCHOUÉ.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Arbitre AutoResearch (load_digits)")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check")
    run_p = sub.add_parser("run")
    run_p.add_argument("--hypothesis", default="")
    sub.add_parser("status")
    sub.add_parser("restore")
    sub.add_parser("final")
    worker_p = sub.add_parser("_worker")
    worker_p.add_argument("out_path")
    args = parser.parse_args()

    if args.cmd == "_worker":
        _worker(args.out_path)
    elif args.cmd == "check":
        cmd_check()
    elif args.cmd == "run":
        cmd_run(args.hypothesis)
    elif args.cmd == "status":
        cmd_status()
    elif args.cmd == "restore":
        cmd_restore()
    elif args.cmd == "final":
        cmd_final()


if __name__ == "__main__":
    main()
