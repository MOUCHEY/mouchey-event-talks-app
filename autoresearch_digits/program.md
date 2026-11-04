# program.md — Protocole du mini système AutoResearch

Ce document est le **contrat de recherche**. Il est écrit *avant* la première
expérience, pour qu'aucune règle ne soit ajustée après coup en fonction des résultats.

## 1. Objectif

Maximiser l'**exactitude de validation** (part d'images bien classées) d'un
classifieur scikit-learn sur `load_digits` (1 797 images de chiffres manuscrits,
8×8 pixels, 10 classes), puis mesurer **une seule fois** la performance réelle
sur un test final réservé.

Matériel cible : iMac Intel 2017, 32 Go de RAM, 4 cœurs, sans GPU.
Logiciel : Python 3 + scikit-learn uniquement (voir `requirements.txt`).

## 2. Rôle de chaque fichier

| Fichier | Rôle | Modifiable pendant la recherche ? |
|---|---|---|
| `program.md` | ce protocole | non |
| `evaluate.py` | l'arbitre : données, découpages, métriques, chrono, budget, décision | **jamais** (empreinte dans `evaluate.sha256`) |
| `train.py` | le modèle candidat : `PARAMS` + `build_model(seed)` | **oui, c'est le seul** |
| `results.csv` | journal machine : une ligne par expérience, échecs compris | écrit uniquement par `evaluate.py` |
| `research_log.md` | journal humain : hypothèse, raisonnement, leçon | oui (rédaction) |
| `experiments/` | copie exacte de `train.py` pour chaque expérience | écrit par `evaluate.py` |
| `final_result.json` | résultat unique sur le test, verrouillé | écrit une fois par `evaluate.py final` |

## 3. Découpage des données

```
1 797 images
├── TEST FINAL réservé : 360 images (20 %, stratifié, graine 42) → utilisé UNE fois
└── DÉVELOPPEMENT : 1 437 images
      └── ×5 répétitions (graines 0,1,2,3,4) :
            ├── entraînement : 1 077 images (75 %)
            └── validation   :   360 images (25 %)
```

* Le test n'est **jamais** utilisé pour choisir un modèle ou un réglage.
* Les 5 découpages sont **identiques pour toutes les expériences**, ce qui
  permet une comparaison *appariée* (même découpage, deux modèles).
* La graine `g` sert à la fois au découpage n° `g` et au `random_state` du modèle.

## 4. Boucle de recherche (une expérience)

1. **Hypothèse** écrite dans `research_log.md` : *« Je pense que X améliorera
   la validation parce que Y. »*
2. **Modification** de `train.py` uniquement (un seul changement d'idée à la fois).
3. **Lancement** : `python evaluate.py run --hypothesis "…"`
4. **Enregistrement automatique** dans `results.csv` : paramètres, métriques,
   durée, graines, avertissements, erreur éventuelle, empreintes SHA-256.
5. **Décision automatique** (règle § 5), puis :
   * `ACCEPTE` → ce `train.py` devient le nouveau meilleur ;
   * `REJETE` ou `ECHEC` → `python evaluate.py restore` (retour au meilleur),
     et l'échec reste tracé.
6. **Leçon** notée dans `research_log.md`.

## 5. Règle de décision (fixée à l'avance)

Un candidat est **accepté** seulement si, par rapport au meilleur courant,
sur les 5 découpages appariés :

* gain moyen d'exactitude **≥ +0,002** (0,2 point), **et**
* il gagne sur **au moins 3** découpages, **et**
* il perd sur **au plus 1** découpage.

Sinon il est rejeté, même s'il « a l'air » meilleur. On préfère rater une
petite amélioration plutôt que de garder un faux progrès dû au hasard.

## 6. Budgets et limites

* **1 référence + 10 expériences maximum.** Les échecs et dépassements comptent.
* **2 minutes** de calcul par expérience (5 répétitions incluses) : au-delà,
  le processus est tué et l'expérience notée `timeout`.
* Budget épuisé → arrêt de la recherche, puis évaluation finale.
* Aucune nouvelle dépendance, aucun service payant sans accord explicite.
* Pour l'iMac (4 cœurs) : `n_jobs` ≤ 4.

## 7. Évaluation finale (une seule fois)

`python evaluate.py final` :
1. vérifie que `train.py` est bien le modèle retenu (empreinte SHA-256) ;
2. l'entraîne sur les 1 437 images de développement ;
3. le mesure **une seule fois** sur les 360 images de test
   (exactitude, intervalle de confiance à 95 % par bootstrap, F1 macro,
   matrice de confusion) ;
4. verrouille le résultat dans `final_result.json`. Toute nouvelle tentative est refusée.

## 8. Commandes

```bash
source .venv/bin/activate              # activer l'environnement isolé
python evaluate.py check               # prérequis + contrôles d'intégrité
python evaluate.py run --hypothesis "…" # une expérience
python evaluate.py status              # tableau + budget
python evaluate.py restore             # revenir au meilleur train.py
python evaluate.py final               # évaluation finale unique
```
