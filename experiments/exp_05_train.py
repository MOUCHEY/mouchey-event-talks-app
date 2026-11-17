"""
train.py — LE SEUL FICHIER MODIFIÉ pendant la recherche.

Contrat avec l'arbitre (evaluate.py) :
  * PARAMS      : dictionnaire des choix de l'expérience (enregistré dans results.csv) ;
  * build_model : fonction build_model(seed) -> estimateur scikit-learn NON entraîné.

Règles :
  * ne jamais charger les données ici (c'est evaluate.py qui les fournit) ;
  * toujours transmettre `seed` aux composants aléatoires (random_state=seed) ;
  * rester sous 2 minutes pour les 5 répétitions.

Version actuelle : EXP 5 — comité de 3 modèles au vote pondéré :
le SVC (exp 3) décide, sauf si les k plus proches voisins ET le réseau de
neurones sont d'accord contre lui.
"""

from sklearn.ensemble import VotingClassifier
from sklearn.model_selection import GridSearchCV, StratifiedKFold
from sklearn.neighbors import KNeighborsClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import FunctionTransformer
from sklearn.svm import SVC

PARAMS = {
    "model": "VotingClassifier(hard)",
    "members": ["svc (exp 3)", "knn", "mlp"],
    # 1.5 / 1 / 1 : les deux autres ensemble (2) battent le SVC (1.5), jamais un seul (1).
    # (2 / 1 / 1 créerait des égalités 2-2 tranchées arbitrairement par le plus petit chiffre.)
    "weights": [1.5, 1, 1],
    "svc_C_grid": [0.3, 1, 3, 10, 30, 100],
    "svc_gamma_grid": [0.0001, 0.0002, "scale", 0.0008, 0.0016, 0.0032],
    "knn_k_grid": [1, 3, 5, 7],
    "mlp_hidden": [128],
    "mlp_max_iter": 1000,
    "inner_cv_folds": 5,
}


def divide_by_16(X):
    """Pixels 0–16 → 0–1, même échelle pour tous (évite d'amplifier les pixels rares)."""
    return X / 16.0


def _inner_cv(seed):
    return StratifiedKFold(n_splits=PARAMS["inner_cv_folds"], shuffle=True, random_state=seed)


def build_model(seed: int):
    # Membre 1 — le meilleur modèle actuel (exp 3), inchangé.
    svc = GridSearchCV(
        SVC(kernel="rbf", random_state=seed),
        param_grid={"C": PARAMS["svc_C_grid"], "gamma": PARAMS["svc_gamma_grid"]},
        cv=_inner_cv(seed), scoring="accuracy",
        n_jobs=4,  # même résultat qu'avec 1, plus rapide
    )
    # Membre 2 — k plus proches voisins : « ressemble le plus à ces quelques exemples ».
    knn = GridSearchCV(
        KNeighborsClassifier(),
        param_grid={"n_neighbors": PARAMS["knn_k_grid"]},
        cv=_inner_cv(seed), scoring="accuracy",
    )
    # Membre 3 — petit réseau de neurones : une couche cachée de 128 neurones.
    mlp = make_pipeline(
        FunctionTransformer(divide_by_16),
        MLPClassifier(hidden_layer_sizes=tuple(PARAMS["mlp_hidden"]),
                      max_iter=PARAMS["mlp_max_iter"], random_state=seed),
    )
    return VotingClassifier(
        estimators=[("svc", svc), ("knn", knn), ("mlp", mlp)],
        voting="hard",
        weights=PARAMS["weights"],
    )


if __name__ == "__main__":
    print(build_model(seed=0))
    print("Pour lancer l'expérience : python evaluate.py run --hypothesis \"...\"")
