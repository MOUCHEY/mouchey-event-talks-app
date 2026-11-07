"""
train.py — LE SEUL FICHIER MODIFIÉ pendant la recherche.

Contrat avec l'arbitre (evaluate.py) :
  * PARAMS      : dictionnaire des choix de l'expérience (enregistré dans results.csv) ;
  * build_model : fonction build_model(seed) -> estimateur scikit-learn NON entraîné.

Règles :
  * ne jamais charger les données ici (c'est evaluate.py qui les fournit) ;
  * toujours transmettre `seed` aux composants aléatoires (random_state=seed) ;
  * rester sous 2 minutes pour les 5 répétitions.

Version actuelle : EXP 2 — SVC à noyau RBF sur pixels bruts (sans StandardScaler).
"""

from sklearn.pipeline import make_pipeline
from sklearn.svm import SVC

PARAMS = {
    "model": "SVC",
    "scaler": "none",
    "kernel": "rbf",
    "C": 1.0,
    "gamma": "scale",
}


def build_model(seed: int):
    """Pipeline = SVM à noyau RBF directement sur les pixels bruts (0 à 16)."""
    return make_pipeline(
        SVC(kernel=PARAMS["kernel"], C=PARAMS["C"], gamma=PARAMS["gamma"], random_state=seed),
    )


if __name__ == "__main__":
    print(build_model(seed=0))
    print("Pour lancer l'expérience : python evaluate.py run --hypothesis \"...\"")
