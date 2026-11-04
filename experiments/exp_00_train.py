"""
train.py — LE SEUL FICHIER MODIFIÉ pendant la recherche.

Contrat avec l'arbitre (evaluate.py) :
  * PARAMS      : dictionnaire des choix de l'expérience (enregistré dans results.csv) ;
  * build_model : fonction build_model(seed) -> estimateur scikit-learn NON entraîné.

Règles :
  * ne jamais charger les données ici (c'est evaluate.py qui les fournit) ;
  * toujours transmettre `seed` aux composants aléatoires (random_state=seed) ;
  * rester sous 2 minutes pour les 5 répétitions.

Version actuelle : MODÈLE DE RÉFÉRENCE (expérience 0).
"""

from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

PARAMS = {
    "model": "LogisticRegression",
    "scaler": "StandardScaler",
    "C": 1.0,
    "max_iter": 5000,
}


def build_model(seed: int):
    """Pipeline = mise à l'échelle des pixels, puis régression logistique."""
    return make_pipeline(
        StandardScaler(),
        LogisticRegression(C=PARAMS["C"], max_iter=PARAMS["max_iter"], random_state=seed),
    )


if __name__ == "__main__":
    print(build_model(seed=0))
    print("Pour lancer l'expérience : python evaluate.py run --hypothesis \"...\"")
