"""
train.py — LE SEUL FICHIER MODIFIÉ pendant la recherche.

Contrat avec l'arbitre (evaluate.py) :
  * PARAMS      : dictionnaire des choix de l'expérience (enregistré dans results.csv) ;
  * build_model : fonction build_model(seed) -> estimateur scikit-learn NON entraîné.

Règles :
  * ne jamais charger les données ici (c'est evaluate.py qui les fournit) ;
  * toujours transmettre `seed` aux composants aléatoires (random_state=seed) ;
  * rester sous 2 minutes pour les 5 répétitions.

Version actuelle : EXP 4 — augmentation de données par décalages d'un pixel
(entraînement seulement), SVC RBF sur pixels bruts, C et gamma choisis par
validation croisée interne.
"""

import numpy as np
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.model_selection import GridSearchCV, StratifiedKFold
from sklearn.svm import SVC

PARAMS = {
    "model": "GridSearchCV(ShiftAugmentedSVC)",
    "scaler": "none",
    "kernel": "rbf",
    "augmentation": "copies décalées de 1 pixel (haut, bas, gauche, droite), entraînement seul",
    "shifts": [[1, 0], [-1, 0], [0, 1], [0, -1]],
    # Grille réduite (coût ×5 données) : couvre toutes les valeurs choisies à l'exp 3.
    "C_grid": [1, 3, 10],
    "gamma_grid": ["scale", 0.0008, 0.0016],
    "inner_cv_folds": 5,
    "inner_scoring": "accuracy",
}


def shift_images(X, dx, dy):
    """Décale des images 8×8 (aplaties en 64 colonnes) de dx pixels vers la droite
    et dy pixels vers le bas. Les pixels qui entrent par le bord valent 0 (papier blanc)."""
    imgs = np.asarray(X).reshape(-1, 8, 8)
    out = np.zeros_like(imgs)
    src_y = slice(max(0, -dy), 8 - max(0, dy))
    dst_y = slice(max(0, dy), 8 - max(0, -dy))
    src_x = slice(max(0, -dx), 8 - max(0, dx))
    dst_x = slice(max(0, dx), 8 - max(0, -dx))
    out[:, dst_y, dst_x] = imgs[:, src_y, src_x]
    return out.reshape(len(imgs), 64)


class ShiftAugmentedSVC(ClassifierMixin, BaseEstimator):
    """SVC qui, PENDANT fit uniquement, ajoute des copies décalées des images.

    predict() reçoit les images telles quelles : la validation n'est jamais augmentée.
    Les paramètres du constructeur sont stockés tels quels (règle scikit-learn),
    ce qui permet à GridSearchCV de cloner l'objet et de faire varier C et gamma.
    """

    def __init__(self, C=1.0, gamma="scale", shifts=((1, 0), (-1, 0), (0, 1), (0, -1)),
                 random_state=None):
        self.C = C
        self.gamma = gamma
        self.shifts = shifts
        self.random_state = random_state

    def fit(self, X, y):
        X, y = np.asarray(X), np.asarray(y)
        copies = [X] + [shift_images(X, dx, dy) for dx, dy in self.shifts]
        X_aug = np.vstack(copies)
        y_aug = np.tile(y, len(copies))
        self.svc_ = SVC(kernel="rbf", C=self.C, gamma=self.gamma,
                        random_state=self.random_state).fit(X_aug, y_aug)
        self.classes_ = self.svc_.classes_
        return self

    def predict(self, X):
        return self.svc_.predict(np.asarray(X))


def build_model(seed: int):
    """GridSearchCV autour du SVC augmenté : l'augmentation a lieu DANS chaque pli
    interne, donc aucune copie décalée ne fuit vers le pli qui sert à noter."""
    inner_cv = StratifiedKFold(n_splits=PARAMS["inner_cv_folds"], shuffle=True, random_state=seed)
    return GridSearchCV(
        ShiftAugmentedSVC(shifts=tuple(map(tuple, PARAMS["shifts"])), random_state=seed),
        param_grid={"C": PARAMS["C_grid"], "gamma": PARAMS["gamma_grid"]},
        cv=inner_cv,
        scoring=PARAMS["inner_scoring"],
        n_jobs=4,  # 4 cœurs (iMac 2017 : 4 cœurs) ; ne change pas les résultats, seulement la vitesse
    )


if __name__ == "__main__":
    print(build_model(seed=0))
    print("Pour lancer l'expérience : python evaluate.py run --hypothesis \"...\"")
