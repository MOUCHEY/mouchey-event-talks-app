"""
train.py — LE SEUL FICHIER MODIFIÉ pendant la recherche.

Contrat avec l'arbitre (evaluate.py) :
  * PARAMS      : dictionnaire des choix de l'expérience (enregistré dans results.csv) ;
  * build_model : fonction build_model(seed) -> estimateur scikit-learn NON entraîné.

Règles :
  * ne jamais charger les données ici (c'est evaluate.py qui les fournit) ;
  * toujours transmettre `seed` aux composants aléatoires (random_state=seed) ;
  * rester sous 2 minutes pour les 5 répétitions.

Version actuelle : EXP 1 — SVC à noyau RBF (frontière non linéaire).
"""

from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

PARAMS = {
    "model": "SVC",
    "scaler": "StandardScaler",
    "kernel": "rbf",
    "C": 1.0,
    "gamma": "scale",
}


def build_model(seed: int):
    """Pipeline = mise à l'échelle des pixels, puis SVM à noyau RBF."""
    return make_pipeline(
        StandardScaler(),
        SVC(kernel=PARAMS["kernel"], C=PARAMS["C"], gamma=PARAMS["gamma"], random_state=seed),
    )


if __name__ == "__main__":
    print(build_model(seed=0))
    print("Pour lancer l'expérience : python evaluate.py run --hypothesis \"...\"")
