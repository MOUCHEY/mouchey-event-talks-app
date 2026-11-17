"""
train.py — LE SEUL FICHIER MODIFIÉ pendant la recherche.

Contrat avec l'arbitre (evaluate.py) :
  * PARAMS      : dictionnaire des choix de l'expérience (enregistré dans results.csv) ;
  * build_model : fonction build_model(seed) -> estimateur scikit-learn NON entraîné.

Règles :
  * ne jamais charger les données ici (c'est evaluate.py qui les fournit) ;
  * toujours transmettre `seed` aux composants aléatoires (random_state=seed) ;
  * rester sous 2 minutes pour les 5 répétitions.

Version actuelle : EXP 3 — SVC RBF sur pixels bruts, C et gamma choisis par
validation croisée INTERNE (sur les seules données d'entraînement).
"""

from sklearn.model_selection import GridSearchCV, StratifiedKFold
from sklearn.svm import SVC

PARAMS = {
    "model": "GridSearchCV(SVC)",
    "scaler": "none",
    "kernel": "rbf",
    # Ordre croissant de complexité : en cas d'égalité, GridSearchCV garde le 1er (le plus simple).
    "C_grid": [0.3, 1, 3, 10, 30, 100],
    "gamma_grid": [0.0001, 0.0002, "scale", 0.0008, 0.0016, 0.0032],
    "inner_cv_folds": 5,
    "inner_scoring": "accuracy",
}


def build_model(seed: int):
    """SVC dont C et gamma sont choisis par validation croisée interne.

    Quand l'arbitre appelle fit(X_train, y_train), GridSearchCV :
      1. découpe X_train en 5 plis stratifiés ;
      2. note chacune des 36 combinaisons (entraîne sur 4 plis, mesure sur le 5e, ×5) ;
      3. réentraîne la meilleure combinaison sur tout X_train.
    La validation de l'arbitre n'est jamais vue pendant ce choix.
    """
    inner_cv = StratifiedKFold(n_splits=PARAMS["inner_cv_folds"], shuffle=True, random_state=seed)
    return GridSearchCV(
        SVC(kernel=PARAMS["kernel"], random_state=seed),
        param_grid={"C": PARAMS["C_grid"], "gamma": PARAMS["gamma_grid"]},
        cv=inner_cv,
        scoring=PARAMS["inner_scoring"],
        n_jobs=1,  # séquentiel : simple, déterministe, sans risque sur l'iMac
    )


if __name__ == "__main__":
    print(build_model(seed=0))
    print("Pour lancer l'expérience : python evaluate.py run --hypothesis \"...\"")
