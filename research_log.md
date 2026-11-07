# research_log.md — Journal de recherche

Journal *humain* : on y écrit le raisonnement (hypothèse → résultat → leçon).
Les chiffres bruts, eux, sont dans `results.csv`, écrit automatiquement par l'arbitre.

Modèle d'entrée :

```
## Exp N — titre court
- Hypothèse : je pense que … parce que …
- Changement dans train.py : …
- Résultat : val acc … ± … (vs meilleur …), durée …
- Décision de l'arbitre : ACCEPTE / REJETE / ECHEC — raison
- Leçon : …
```

---

## Étape 0 — Installation et prérequis (2026-11-04)

**Où ça tourne.** Session cloud Linux (4 vCPU Intel Xeon 2,1 GHz, ~17 Go RAM) et non
l'iMac Intel 2017 visé (4 cœurs, 32 Go). Le code est portable vers macOS. Les durées
mesurées ici donnent un ordre de grandeur pour l'iMac.

**Environnement.**
- Python 3.13.18, environnement virtuel `.venv/`.
- Seule installation : `scikit-learn`. Ses dépendances obligatoires sont venues avec
  (numpy, scipy, joblib, threadpoolctl, cloudpickle, narwhals). Versions figées dans
  `requirements.txt`.
- `load_digits` est inclus dans scikit-learn : aucun téléchargement, aucun service externe.

**Arbitre.** `evaluate.py` a été testé *avant* son gel, sur une copie jetable
(limite de temps réduite à 5 s, budget réduit à 3). 12 scénarios ont été vérifiés :
- arbitre non gelé refusé ;
- `check` ;
- référence ;
- hypothèse manquante refusée ;
- erreur enregistrée ;
- dépassement de temps : processus tué, aucun orphelin ;
- acceptation ;
- budget épuisé ;
- `restore` ;
- règle de décision (5 cas) ;
- verrou de l'évaluation finale ;
- `evaluate.py` modifié détecté.

Lors du test de l'évaluation finale, la sortie a été masquée : **aucun score du test
réservé n'a été lu**. La copie a ensuite été supprimée.
Remarque de transparence : la répétition générale a déjà calculé une fois le score de
*validation* de la référence. C'est sans conséquence pour le test. Cela servira même de
contrôle de reproductibilité : l'exécution officielle devra redonner exactement le même chiffre.

**Dépôt.** Le projet vit sur la branche orpheline `auto-research`, fichiers à la racine.
Cette branche n'a aucun historique commun avec l'application de `main`. Le `.venv` a été
recréé uniquement depuis `requirements.txt` : versions identiques, ce qui valide la
reproductibilité de l'installation.

**Gel.** Empreinte SHA-256 de `evaluate.py` : `492b78ce…6771117` (dans `evaluate.sha256`).

**`python evaluate.py check` : tous les prérequis sont satisfaits.**
- 1 797 images, 10 classes.
- Développement 1 437 / test 360, aucune image commune.
- Découpage déterministe.
- Chaque chiffre présent 35 à 37 fois dans le test.
- Pour chaque graine : entraînement 1 077 / validation 360.

**Prochaine étape :** exécution officielle du modèle de référence
(StandardScaler + LogisticRegression, C=1).

---

## Exp 0 — Référence : StandardScaler + LogisticRegression(C=1)
- **Hypothèse.** Un modèle linéaire simple, sur des pixels normalisés, donne un point de
  départ solide et rapide.
- **Code.** `train.py` initial (copie : `experiments/exp_00_train.py`).
- **Résultat.**
  - Validation : **0,9633 ± 0,0066** (par graine : 0,9556 ; 0,9722 ; 0,9639 ; 0,9667 ; 0,9583),
    soit environ 13 erreurs sur 360 images.
  - Entraînement : 0,9998, donc un écart de **3,65 points**.
  - Durée : 1,8 s.
- **Décision de l'arbitre.** REFERENCE.
- **Reproductibilité.** Scores identiques à la répétition générale : déterminisme vérifié.
- **Leçons.**
  1. Le score varie de 1,7 point selon le découpage (95,6 % à 97,2 %). Une mesure unique
     aurait été trompeuse ; les 5 répétitions sont justifiées.
  2. Le modèle est presque parfait sur l'entraînement mais perd 3,65 points en validation.
     Il mémorise une partie du bruit, et sa frontière linéaire ne capte sans doute pas
     toutes les formes des chiffres.
  3. 1,8 s sur 120 s autorisées : le budget de temps laisse de la marge pour des modèles
     plus coûteux.
- **Transparence.** Lors des tests de l'arbitre (étape 0), le scénario « acceptation »
  utilisait `StandardScaler + SVC` par défaut. Je connais donc déjà son score de
  validation : 0,9789. C'est sans conséquence pour le test réservé, mais c'est une
  information obtenue hors budget. Si on choisit cette piste, elle sera rejouée
  officiellement et comptée dans le budget.

---

## Plan de recherche provisoire (révisé après chaque résultat)

Mode de travail choisi : **une expérience à la fois**. Après chacune : pause, leçon,
puis attente du « go ».

| # | Hypothèse | Concept |
|---|---|---|
| 1 | Un SVC à noyau RBF battra la régression : la frontière entre chiffres n'est pas linéaire. (Score de validation déjà connu : 0,9789, voir « Transparence » ci-dessus.) | astuce du noyau |
| 2 | Diviser les pixels par 16 vaudra mieux que `StandardScaler`, qui amplifie les pixels de bord presque toujours éteints. | choix de la normalisation |
| 3 | Ajuster `C` et `gamma` du meilleur SVC. | hyperparamètres, biais/variance |
| 4 | Les k plus proches voisins, comme autre famille de modèles. | modèles fondés sur la distance |
| 5–10 | Selon les résultats : ACP avant le SVC, ensembles de modèles, etc. | |

**Changement de machine.** Si la recherche se poursuit sur une autre machine (par exemple
l'iMac), refaire d'abord la référence dans une copie jetable et comparer les 5 scores
à l'Exp 0. S'ils sont identiques, on garde ce `results.csv`. Sinon, on repart d'une
nouvelle référence mesurée sur cette machine.

---

## Exp 1 — SVC à noyau RBF (C=1, gamma="scale")
- **Hypothèse (écrite avant le lancement).** Un SVM à noyau RBF dépassera la régression
  logistique : la frontière entre certains chiffres n'est pas linéaire (1 penché / 7,
  3 / 8…). Je change une seule idée, la famille de modèle ; `StandardScaler` est conservé.
- **Biais connu.** Score de validation déjà vu lors des tests de l'arbitre (0,9789).
  Cette exécution l'officialise et compte dans le budget.
- **Résultat.**
  - Validation : **0,9789 ± 0,0070** (par graine : 0,9694 ; 0,9889 ; 0,9778 ; 0,9778 ; 0,9806),
    contre 0,9633 pour la référence. Les erreurs passent d'environ 13,2 à 7,6 sur 360 (−42 %).
  - Entraînement : 0,9980, donc un écart de **1,91 point** (contre 3,65).
  - Durée totale : 8,52 s, dont seulement 0,022 s d'entraînement par graine.
- **Décision de l'arbitre.** **ACCEPTE** : gain moyen +0,0155, 5 découpages gagnés,
  0 perdu. C'est le nouveau meilleur modèle.
- **Leçons.**
  1. L'hypothèse est confirmée, et de façon robuste : le SVC gagne sur les 5 découpages,
     pas seulement en moyenne.
  2. Le score d'entraînement baisse (0,9998 → 0,9980) pendant que la validation monte :
     le modèle **généralise mieux** au lieu de mémoriser. Raisonner par ressemblance
     entre images convient mieux à ce problème qu'une frontière droite.
  3. Durée totale et temps d'entraînement sont deux choses différentes. Les 8,5 s sont
     presque entièrement dues au démarrage de Python et au chargement de scikit-learn
     sur un disque « froid » (machine redémarrée). La limite de 2 min porte sur la durée
     totale ; elle est donc prudente.
  4. Cette confirmation était attendue (score déjà vu). Les expériences suivantes
     portent sur des résultats réellement inconnus.

---

## Exp 2 — SVC RBF sans StandardScaler (pixels bruts 0–16)
- **Observation préalable (développement uniquement, aucun modèle entraîné).**
  - 16 pixels sur 64 ont un écart-type < 1, tous sur les colonnes 0 et 7 ; 3 sont constants.
  - Le pixel n° 56 n'est allumé que sur 1 image sur 1 437. Après `StandardScaler`, il
    atteint 37,9, contre environ 1 à 1,5 pour un pixel central.
  - Dans le noyau RBF (écarts au carré), cette tache isolée pèse environ 1 400 fois plus
    qu'un pixel central.
- **Hypothèse (écrite avant le lancement).** Supprimer `StandardScaler` améliorera la
  validation. Chaque pixel gardera un poids proportionnel à son encre, et les traits
  parasites en bordure ne domineront plus la ressemblance entre images.
- **Note.** Avec `gamma="scale"`, diviser par 16 équivaut exactement à ne rien faire
  (invariance d'échelle) : on retire donc simplement le scaler. Une seule idée change ;
  `C=1` et `gamma="scale"` sont conservés.
- **Résultat.**
  - Validation : **0,9856 ± 0,0053** (par graine : 0,9778 ; 0,9889 ; 0,9861 ; 0,9917 ; 0,9833).
    En images bien classées : [352, 356, 355, 357, 354] contre [349, 356, 352, 352, 353].
    Les erreurs passent d'environ 7,6 à 5,2 sur 360.
  - Entraînement : 0,9976, donc un écart de **1,20 point** (contre 1,91).
  - Durée : 1,6 s.
- **Décision de l'arbitre.** **ACCEPTE** : gain +0,0067, annoncé « 4 gagnés / 1 perdu / 0 égalité ».
- **⚠️ Anomalie découverte dans l'arbitre.** Sur la graine 1, les deux modèles ont
  356/360, pourtant l'arbitre compte une défaite.
  - Cause : `results.csv` stocke les scores arrondis à 4 décimales. Le meilleur est relu
    arrondi (0,9889), alors que le candidat est comparé en pleine précision
    (0,98888…). Une égalité devient donc une défaite si le meilleur a été arrondi
    vers le haut, et une **fausse victoire** s'il a été arrondi vers le bas.
  - Audit exact, en nombres d'images (k = score × 360, sans ambiguïté) :
    - exp 1 : 5/0/0 ;
    - exp 2 : **4 gagnés / 0 perdu / 1 égalité**.
    Les deux décisions sont **inchangées** ; le passé est sain.
  - Risque pour la suite : le meilleur actuel (exp 2) est arrondi vers le bas sur les
    graines 2 et 4. Une égalité y serait comptée comme victoire, ce qui pourrait faire
    accepter à tort un faux progrès.
  - Conformément au protocole, `evaluate.py` n'a pas été modifié : décision soumise à
    l'utilisateur avant l'Exp 3.
- **Leçons.**
  1. L'hypothèse est confirmée : la normalisation par pixel amplifiait le bruit des bords.
     Supprimer une étape a amélioré le modèle. Une étape de prétraitement « standard »
     n'est pas automatiquement bonne.
  2. Le sur-apprentissage diminue encore (1,91 → 1,20 point) : le modèle n'apprend plus
     des taches parasites.
  3. Même un arbitre testé peut avoir un bug. Relire les résultats bruts avec un œil
     critique fait partie du métier.
