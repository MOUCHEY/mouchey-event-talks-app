"""
pilots/deskew_pilot.py — ÉTUDE PILOTE (hors budget, validation jamais lue).

Question : redresser l'écriture penchée (deskewing) avant le SVC de l'exp 3
améliore-t-il les prédictions ?

Méthode : sur la partie ENTRAÎNEMENT de chacun des 5 découpages, prédictions
hors pli (cross_val_predict, 5 plis) de deux variantes :
  A = méthode exp 3 (GridSearchCV(SVC) sur pixels bruts) ;
  B = redressement de chaque image, puis la même méthode.
Bilan net = (images bien classées par B) − (images bien classées par A).

Règle de décision fixée AVANT le pilote (research_log.md) :
  bilan net >= +11 sur 5 385 prédictions → expérience officielle n° 6 ;
  sinon → arrêt de la recherche et évaluation finale.

Lancement : .venv/bin/python pilots/deskew_pilot.py
"""

import sys
import time
import warnings
from pathlib import Path

import numpy as np
from scipy.ndimage import affine_transform

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # accès à evaluate.py et train.py
from evaluate import REPEAT_SEEDS, load_dev, split_train_val  # noqa: E402

warnings.filterwarnings("ignore")
NET_THRESHOLD = 11


def skew(img):
    """Inclinaison alpha = cov(ligne, colonne) / var(ligne), pondérées par l'encre."""
    r, c = np.indices(img.shape)
    m = img.sum()
    if m == 0:
        return 0.0, (3.5, 3.5)
    mr, mc = (r * img).sum() / m, (c * img).sum() / m
    var_r = (((r - mr) ** 2) * img).sum() / m
    cov = ((r - mr) * (c - mc) * img).sum() / m
    return (cov / var_r if var_r > 0 else 0.0), (mr, mc)


def deskew_image(img):
    """Cisaillement qui annule l'inclinaison ; le centre de gravité est ramené au centre."""
    alpha, (mr, mc) = skew(img)
    matrix = np.array([[1.0, 0.0], [alpha, 1.0]])   # sortie (r, c) ← entrée (r, c + alpha·r')
    centre = np.array([3.5, 3.5])
    offset = np.array([mr, mc]) - matrix @ centre
    out = affine_transform(img, matrix, offset=offset, order=1, mode="constant", cval=0.0)
    return np.clip(out, 0, 16)


def deskew_images(X):
    X = np.asarray(X, dtype=float)
    return np.array([deskew_image(x.reshape(8, 8)).ravel() for x in X])


def ascii(img):
    chars = " .:-=+*#%@"
    return ["".join(chars[min(int(v) * 10 // 17, 9)] * 2 for v in row) for row in img.reshape(8, 8)]


def unit_tests():
    print("1) Tests unitaires")
    slanted = np.zeros((8, 8))
    for r in range(1, 7):
        slanted[r, 2 + r // 2] = 16          # trait penché vers la droite en descendant
    a0, _ = skew(slanted)
    a1, _ = skew(deskew_image(slanted))
    print(f"   trait penché : alpha {a0:+.2f} → {a1:+.2f} après redressement "
          f"({'OK' if abs(a1) < abs(a0) / 3 else 'ÉCHEC'})")
    upright = np.zeros((8, 8))
    upright[1:7, 3] = 16
    a2, _ = skew(upright)
    print(f"   trait vertical : alpha {a2:+.2f} (déjà droit) → encre conservée "
          f"{deskew_image(upright).sum() / upright.sum():.0%} "
          f"({'OK' if abs(a2) < 1e-9 else 'ÉCHEC'})")
    return slanted


def main():
    from sklearn.model_selection import StratifiedKFold, cross_val_predict
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import FunctionTransformer
    import train  # méthode de l'exp 3 (meilleur modèle courant)

    slanted = unit_tests()
    print("\n2) Exemple visuel (trait penché, avant | après)")
    for left, right in zip(ascii(slanted), ascii(deskew_image(slanted))):
        print(f"   {left} | {right}")

    X_dev, y_dev = load_dev()
    alphas = np.array([skew(x.reshape(8, 8))[0] for x in X_dev])
    print(f"\n3) Inclinaison des chiffres (développement) : médiane {np.median(alphas):+.2f}, "
          f"10 % les plus penchés au-delà de ±{np.percentile(np.abs(alphas), 90):.2f} colonne/ligne")

    print("\n4) Pilote : prédictions hors pli sur les parties ENTRAÎNEMENT")
    t0 = time.perf_counter()
    net_total, n_total, gained, lost = 0, 0, {}, {}
    for s in REPEAT_SEEDS:
        X_tr, _, y_tr, _ = split_train_val(X_dev, y_dev, s)      # la validation est ignorée
        model_a = train.build_model(s).set_params(n_jobs=4)       # même résultat, plus rapide
        model_b = make_pipeline(FunctionTransformer(deskew_images),
                                train.build_model(s).set_params(n_jobs=4))
        cv = StratifiedKFold(5, shuffle=True, random_state=100 + s)
        pa = cross_val_predict(model_a, X_tr, y_tr, cv=cv)
        pb = cross_val_predict(model_b, X_tr, y_tr, cv=cv)
        ok_a, ok_b = pa == y_tr, pb == y_tr
        net = int(ok_b.sum() - ok_a.sum())
        for i in np.where(ok_b & ~ok_a)[0]:
            gained[(int(y_tr[i]), int(pa[i]))] = gained.get((int(y_tr[i]), int(pa[i])), 0) + 1
        for i in np.where(ok_a & ~ok_b)[0]:
            lost[(int(y_tr[i]), int(pb[i]))] = lost.get((int(y_tr[i]), int(pb[i])), 0) + 1
        net_total += net
        n_total += len(y_tr)
        print(f"   graine {s} : A {ok_a.mean():.4f} | B (redressé) {ok_b.mean():.4f} | "
              f"corrigées {int((ok_b & ~ok_a).sum())}, cassées {int((ok_a & ~ok_b).sum())}, net {net:+d}")
    def fmt(d, word):
        items = sorted(d.items(), key=lambda kv: -kv[1])
        return ", ".join(f"{t} ({word} {p})×{n}" for (t, p), n in items) or "aucune"
    print(f"   corrections — vrai chiffre (A prédisait …) : {fmt(gained, 'A prédisait')}")
    print(f"   casses      — vrai chiffre (B prédit …)    : {fmt(lost, 'B prédit')}")
    print(f"\nBILAN NET : {net_total:+d} images sur {n_total} prédictions "
          f"(seuil fixé à l'avance : +{NET_THRESHOLD})  [{time.perf_counter() - t0:.0f} s]")
    verdict = "EXPÉRIENCE OFFICIELLE n° 6" if net_total >= NET_THRESHOLD else "ARRÊT → évaluation finale"
    print(f"DÉCISION DU PILOTE : {verdict}")


if __name__ == "__main__":
    main()
