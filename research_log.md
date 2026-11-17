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

---

## Amendement n° 1 de l'arbitre (approuvé par l'utilisateur : option A)
- **Correctif.** Une ligne dans `evaluate.py` : le candidat est arrondi à 4 décimales,
  comme le meilleur relu dans `results.csv`, avant la comparaison appariée.
- **Preuve, sur une copie jetable.** Le modèle de l'exp 2 est comparé à lui-même.
  - Avant : « 2 gagnés / 3 perdus », alors qu'il ne devrait y avoir que des égalités.
  - Après : « 0 / 0 / **5 égalités** ».
- **Historique.** Décisions des exp 1 et 2 revérifiées en nombres d'images : inchangées.
  Aucune expérience à refaire.
- **Traçabilité.**
  - Empreinte : `492b78ce…` → `6c8d1816…`.
  - Les lignes 0 à 2 de `results.csv` portent l'ancienne empreinte ; les suivantes
    porteront la nouvelle.
  - Amendement consigné dans `program.md` § 9.
- **Leçon.** Les 12 tests de l'étape 0 ne comparaient jamais deux scores égaux : un cas
  limite oublié suffit à cacher un bug. Tester les égalités et les valeurs aux bornes
  est un réflexe à prendre.

---

## Exp 3 — Réglage automatique de C et gamma par validation croisée interne
- **Observation préalable (partie entraînement de chaque découpage).**
  `gamma="scale"` ≈ 0,00043 pour les 5 graines, très stable.
- **Hypothèse (écrite avant le lancement).** Des valeurs de `C` et `gamma` choisies par
  validation croisée **interne**, sur les seules données d'entraînement de chaque
  répétition, battront les valeurs par défaut (C=1, gamma="scale").
  - Pourquoi : les valeurs par défaut sont génériques. L'entraînement reste à 0,9976 < 1 :
    `C=1` freine peut-être un peu trop (biais).
  - Risque : la sélection interne, sur environ 860 images, est bruitée. Le gain pourrait
    rester sous le seuil.
- **Changement (une seule idée : la méthode de choix des hyperparamètres).**
  - `GridSearchCV`, 36 combinaisons : C ∈ {0,3 ; 1 ; 3 ; 10 ; 30 ; 100} ×
    gamma ∈ {0,0001 ; 0,0002 ; "scale" ; 0,0008 ; 0,0016 ; 0,0032}.
  - Validation interne : `StratifiedKFold` à 5 plis, mélangé avec la graine de la
    répétition.
  - Égalités : la première combinaison est gardée, soit la plus simple (petit C, petit gamma).
  - Pixels bruts, sans scaler (comme l'exp 2).
- **Résultat.**
  - Validation : **0,9906 ± 0,0058** (par graine : 0,9861 ; 0,9972 ; 0,9944 ; 0,9917 ; 0,9833).
    En images : [355, 359, 358, 357, 354] contre [352, 356, 355, 357, 354], soit des
    écarts de [+3, +3, +3, 0, 0]. Environ 3,4 erreurs sur 360, contre 5,2.
  - Entraînement : 0,9996, donc un écart de **0,91 point** (contre 1,20).
  - Durée : 33,3 s, contre 1,6 s.
- **Décision de l'arbitre (corrigé).** **ACCEPTE** : gain +0,0050, 3 gagnés / 0 perdu /
  2 égalités. Avec l'ancien arbitre, l'égalité de la graine 4 aurait compté comme une
  fausse victoire.
- **Inspection a posteriori (parties entraînement uniquement, validation jamais lue).**
  - Choix selon la graine :
    - graine 0 : C=10, γ=scale ;
    - graines 1 et 2 : C=3, γ=0,0008 ;
    - graine 3 : C=1, γ=0,0008 ;
    - graine 4 : C=1, γ=0,0016.
  - Gain du choix sur le défaut, en validation croisée interne : +0,2 à +0,7 point.
  - Dans chaque découpage, les 3 meilleures combinaisons ont **exactement** le même
    score : au-delà d'un certain C, augmenter C ne change plus rien.
- **Leçons.**
  1. **Le levier principal est gamma, pas C.** Il passe de 0,00043 (scale) à 0,0008
     dans 3 découpages sur 5. Le défaut était un peu trop « doux » : léger excès de biais.
  2. **Le plateau en C.** Quand le modèle classe déjà tous les exemples d'entraînement,
     augmenter C (moins de tolérance aux erreurs) ne change plus la frontière. Sur ce
     plateau, les égalités choisissent le plus simple.
  3. **On évalue une méthode, pas un réglage.** Les réglages choisis varient selon le
     découpage. L'arbitre a jugé la *procédure* « chercher C et gamma par validation
     croisée interne ». L'évaluation finale appliquera cette même procédure aux 1 437
     images de développement.
  4. **Le coût monte : 33 s** (environ ×20, pour 36 combinaisons × 5 plis × 5
     répétitions). Il reste de la marge sous 120 s, mais toute idée plus coûteuse devra
     réduire la grille.

---

## Exp 4 — Augmentation par décalages d'un pixel (entraînement seulement)
- **Analyse d'erreurs préalable (validation du modèle exp 3, hors budget).**
  - 17 erreurs sur 1 800 prédictions. Confusions entre formes à boucles :
    9→8 ×3, 8→1 ×3, 9→3 ×2, 5→9 ×2, 3→7 ×2, 9→5 ×2, 8→6, 3→5, 7→9.
  - Le centre d'encre des images ratées est normal (≈ 3,5 ; 3,5) : ce sont des
    **formes ambiguës**, pas des chiffres décentrés.
- **Hypothèse (écrite avant le lancement).** Ajouter à l'entraînement 4 copies décalées
  d'un pixel (haut, bas, gauche, droite) améliorera la validation : le modèle apprendra à
  tolérer les variations locales de position des traits.
- **Attente révisée à la baisse** après l'analyse d'erreurs : les erreurs ne viennent pas
  d'un décalage global. Gain faible probable ; un rejet est plausible.
- **Changement.**
  - Classe `ShiftAugmentedSVC` : l'augmentation a lieu dans `fit` uniquement, donc
    jamais en validation. Elle est placée **dans** `GridSearchCV`, pour éviter une fuite
    entre les plis internes.
  - Effet de bord assumé : la grille passe de 36 à 9 combinaisons
    (C ∈ {1 ; 3 ; 10} × γ ∈ {scale ; 0,0008 ; 0,0016}), à cause du coût ×5. Elle couvre
    toutes les valeurs choisies à l'exp 3.
  - `n_jobs=4` : même résultat, plus rapide.
- **Vérifications avant le lancement (entraînement seul).**
  - Test unitaire de `shift_images` : 5 cas sur 5 réussis.
  - `clone()` conserve les paramètres.
  - Coût estimé : environ 38 s.
- **Résultat.**
  - Validation : **0,9894 ± 0,0023** (par graine : 0,9889 ; 0,9917 ; 0,9889 ; 0,9917 ; 0,9861).
    En images : [356, 357, 356, 357, 355] contre [355, 359, 358, 357, 354] pour l'exp 3,
    soit des écarts de [+1, −2, −2, 0, +1].
  - Entraînement : 1,0000.
  - Durée : 33,2 s (estimation : 38 s).
- **Décision de l'arbitre.** **REJETE** : gain −0,0011, 2 gagnés / 2 perdus / 1 égalité.
  `train.py` restauré depuis l'exp 3 ; la version ratée reste dans
  `experiments/exp_04_train.py`.
- **Leçons.**
  1. **L'analyse d'erreurs avait vu juste.** Les erreurs restantes sont des formes
     ambiguës, pas des décalages ; apprendre l'invariance par translation ne les corrige
     pas. Avoir revu l'attente à la baisse *avant* le lancement rend ce rejet instructif,
     et non décevant.
  2. **Plus stable n'est pas meilleur.** L'écart-type entre découpages chute
     (0,0058 → 0,0023) : le modèle augmenté est plus régulier, mais sa moyenne est
     légèrement plus basse. Il plafonne autour de 356-357 images partout, là où l'exp 3
     atteignait 358-359 sur certains découpages.
  3. **Écarts de ±1 à 2 images = bruit de mesure.** La règle (≥ 3 découpages gagnés,
     gain ≥ 0,2 point) a correctement refusé un changement qui ne se distingue pas du
     hasard.
  4. **Limite d'interprétation.** La grille a aussi été réduite (36 → 9), ce qui empêche
     d'attribuer le résultat *uniquement* à l'augmentation. Elle couvrait toutes les
     valeurs choisies à l'exp 3 ; c'est donc probablement l'augmentation qui ne paie pas.
  5. **Compétences acquises.** Une classe compatible scikit-learn (`fit`, `predict`,
     paramètres stockés tels quels pour `clone`), l'augmentation placée à l'intérieur
     de la validation croisée, le test unitaire et l'estimation du coût avant lancement,
     le parallélisme `n_jobs`.

---

## Exp 5 — Comité de 3 modèles au vote pondéré (SVC + kNN + MLP)
- **Hypothèse (écrite avant le lancement).** Des modèles aux biais différents corrigeront
  certaines formes ambiguës. Le SVC de l'exp 3 décide, sauf si les k plus proches voisins
  ET un réseau de neurones (une couche de 128 neurones) sont d'accord contre lui.
- **Correction de conception.** Poids 1,5 / 1 / 1 au lieu des 2 / 1 / 1 annoncés.
  - Avec 2 / 1 / 1, le cas « SVC contre les deux autres » donne une égalité 2-2, tranchée
    par `argmax` au profit du plus petit chiffre, ce qui est arbitraire (vérifié sur des
    cas tests).
  - Avec 1,5 / 1 / 1, la règle annoncée est appliquée exactement.
- **Étude pilote (prédictions hors pli sur les parties entraînement, validation jamais lue).**
  - Exactitude seule : SVC 0,9887 ; kNN 0,9844 ; MLP 0,9697.
  - Le comité renverse le SVC 9 fois sur 5 385 : 4 corrections, 3 casses, soit un net
    de +1.
- **Prédiction enregistrée.** Gain nul, **rejet attendu**. Lancement maintenu (18 s) pour
  vérifier si le pilote prédit bien le verdict de la validation.
- **Coût estimé.** Environ 18 s.
- **Résultat.**
  - Validation : **0,9917 ± 0,0056** (par graine : 0,9889 ; 0,9972 ; 0,9944 ; 0,9944 ; 0,9833).
    En images : [356, 359, 358, 358, 354] contre [355, 359, 358, 357, 354], soit des
    écarts de [+1, 0, 0, +1, 0] : **+2 images sur 1 800**.
  - Entraînement : 1,0000.
  - Durée : 18,8 s (estimation : 18 s).
- **Décision de l'arbitre.** **REJETE** : gain +0,0011 (< 0,002), 2 gagnés / 0 perdu /
  3 égalités (< 3 gagnés). `train.py` restauré depuis l'exp 3.
- **Leçons.**
  1. **Le pilote a prédit le verdict.** Il annonçait un net de +1 (corrections moins
     casses) sur l'entraînement ; la validation donne +2. Un pilote hors pli sur
     l'entraînement est donc un **filtre fiable et gratuit** pour trier les idées avant
     de dépenser du budget, sans user la validation.
  2. **Un chiffre plus haut n'est pas un progrès.** 0,9917 > 0,9906 est tentant, mais
     2 images sur 1 800, c'est du bruit. Passer outre la règle « parce que la moyenne
     monte », c'est exactement ainsi qu'on se fait piéger par la malédiction du gagnant.
  3. **Rasoir d'Ockham.** Même sans perte, 3 modèles au lieu d'un (plus lent, plus
     complexe à maintenir) pour un gain invisible : le modèle simple l'emporte.
  4. **Un comité n'aide que si ses membres se trompent sur des images différentes.** Ici,
     kNN et MLP sont rarement d'accord contre le SVC (9 fois sur 5 385) : leurs erreurs
     recouvrent largement celles du SVC, ou bien ils ne s'accordent pas entre eux.

---

## Pilote — Redressement de l'écriture (deskewing), hors budget
- **Hypothèse.** Redresser chaque chiffre penché avant le SVC de l'exp 3 réduira les
  confusions entre formes (cible : « 8 étroit et penché → 1 »).
  - Méthode : inclinaison mesurée par les moments de l'encre
    (alpha = cov(ligne, colonne) / var(ligne)), puis cisaillement inverse et recentrage
    (`scipy.ndimage.affine_transform`, interpolation linéaire).
  - Prétraitement image par image, sans paramètre appris : aucune fuite possible.
- **Protocole du pilote.** Prédictions hors pli (5 plis) sur les parties entraînement des
  5 découpages, validation jamais lue. On compare A (exp 3) et B (redressement + exp 3).
- **Règle de décision fixée avant le pilote.**
  - Bilan net ≥ **+11 images** sur 5 385 → expérience officielle n° 6.
  - Sinon → arrêt de la recherche et évaluation finale.
  - Justification du seuil : l'arbitre exige environ +3,6 images sur 1 800 en
    validation, soit environ ×3 sur 5 385.
- **Code.** `pilots/deskew_pilot.py` (reproductible).
- **Résultat du pilote.**
  - Bilan net : **−23 images** sur 5 385 (par graine : −3, −7, 0, −4, −9). Seuil : +11.
  - Corrections (51) : la cible est atteinte, « 8 prédit 1 » est corrigé 5 fois, et
    « 9 prédit 5 » 5 fois.
  - Casses (74) : surtout « 6 → 4 » ×8, et « 3 → 5 ou 9 » ×9.
  - (Une première version affichait « était » au lieu de « B prédit » pour les casses ;
    étiquette corrigée, nombres identiques au second lancement.)
- **Décision (règle fixée à l'avance).** **ARRÊT de la recherche → évaluation finale.**
  Aucune expérience officielle n° 6 ; le budget s'arrête à 5/10.
- **Leçons.**
  1. **Les données sont déjà presque droites.** Inclinaison médiane +0,04 colonne par
     ligne, et 90 % des chiffres sous ±0,21, soit moins d'un pixel de décalage sur toute
     la hauteur. Pour la plupart des images, le « redressement » est un cisaillement
     sous-pixel : une simple interpolation qui **floute** (visible sur le test unitaire,
     où un trait net devient une bande de 2 colonnes). À 8×8, chaque pixel compte : le
     flou détruit plus d'information qu'il n'en corrige.
  2. **Les moments confondent forme et inclinaison.** Un 6 (boucle en bas à gauche,
     hampe en haut à droite) « paraît » penché ; le redresser le déforme vers un 4.
     Une mesure globale ne sait pas distinguer la géométrie propre d'un chiffre du style
     de l'écrivain.
  3. **Le pilote a joué son rôle.** Une idée nuisible a été écartée sans dépenser de
     budget ni user la validation. Le seuil fixé à l'avance a rendu la décision
     automatique, même si l'idée corrigeait bien sa cible (« 8 → 1 »).

---

## Évaluation finale (une seule fois)
- **Modèle retenu.** Exp 3 : SVC RBF sur pixels bruts, C et gamma choisis par validation
  croisée interne (36 combinaisons). Réentraîné sur les 1 437 images de développement.
- **Attente écrite avant le lancement.**
  - Exactitude sur le test : environ 0,98 à 1,00. Pour n = 360 et p ≈ 0,99,
    l'intervalle de confiance à 95 % fait environ ±1 point.
  - Une baisse modérée par rapport à la validation (0,9906) serait normale (malédiction
    du gagnant) et ne remettrait pas en cause la méthode.
- **Résultat (`final_result.json`, verrouillé).**
  - Exactitude sur le test : **0,9889**, soit 356/360 et **4 erreurs**.
    IC 95 % par bootstrap : [0,9778 ; 0,9972]. F1 macro : 0,9888.
  - Rappel validation : 0,9906, soit un écart de −0,17 point (environ 0,6 image). C'est
    dans le bruit et conforme à l'attente ; aucun signe de sur-ajustement à la validation.
  - Les 4 erreurs : **8 → 1 ×2**, 6 → 8 ×1, 9 → 7 ×1. La confusion « 8 → 1 », déjà
    dominante en validation, persiste.
  - Réglage choisi par le modèle final (CV interne sur le développement) : C=1, γ=0,0008.
  - Une seconde tentative d'évaluation finale a été refusée : le verrou fonctionne.

---

## Bilan de la recherche

| Étape | Idée | Validation | Décision |
|---|---|---|---|
| Exp 0 | Régression logistique + StandardScaler | 0,9633 | RÉFÉRENCE |
| Exp 1 | SVC RBF | 0,9789 | ACCEPTE |
| Exp 2 | Sans StandardScaler (pixels bruts) | 0,9856 | ACCEPTE |
| Exp 3 | C et γ par validation croisée interne | **0,9906** | ACCEPTE (retenu) |
| Exp 4 | Augmentation par décalages | 0,9894 | REJETE |
| Exp 5 | Comité SVC + kNN + MLP | 0,9917 (+2/1 800) | REJETE |
| Pilote | Redressement (deskewing) | net −23 (entraînement) | ARRÊT |
| **Test** | **Exp 3, une seule fois** | **0,9889** [0,978 ; 0,997] | — |

Budget : 5 expériences sur 10, 1 pilote, 1 amendement de l'arbitre. Erreurs divisées
par environ 3,3 par rapport à la référence (13,2 → environ 4 sur 360).

### Limites
1. **Mesure peu précise.** 360 images de test donnent environ ±1 point d'incertitude :
   on ne peut pas distinguer 98,9 % de 99,5 %. Les dernières idées étaient sous ce seuil
   de détection.
2. **Validation réutilisée.** 5 décisions ont été prises sur les mêmes 5 découpages : un
   léger optimisme est possible. Le test (−0,17 point) indique qu'il est négligeable ici.
3. **Un seul découpage de test** (graine 42) : un autre tirage pourrait varier d'environ
   1 point.
4. **Jeu jouet.** `load_digits` est en 8×8, avec des chiffres déjà centrés et droits.
   Les conclusions (pas de normalisation par pixel ; augmentation et redressement
   inutiles) ne se transposent pas à de vraies images, comme MNIST en 28×28.
5. **Pas mesuré sur l'iMac cible.** Durées et reproductibilité exacte des scores restent
   à vérifier sur macOS Intel.
6. **Exp 4 confondue.** La grille a été réduite en même temps que l'augmentation.
7. **Arbitre corrigé en cours de route** (amendement n° 1). Décisions passées
   revérifiées : inchangées.

### Prochaines hypothèses
1. **Reproduire sur l'iMac** : `check`, puis la référence dans une copie jetable ; on doit
   retrouver 0,9556 ; 0,9722 ; 0,9639 ; 0,9667 ; 0,9583.
2. **Un instrument plus fin** : nouveau protocole avec 20 à 50 découpages répétés (ou
   une validation croisée répétée), pour détecter des gains de quelques images. Leçon
   visée : la *puissance statistique*.
3. **Cibler « 8 → 1 »** par des variables de forme (nombre de boucles fermées, profils
   des lignes et colonnes), en passant d'abord par un pilote.
4. **Savoir dire « je ne sais pas »** : probabilités calibrées et abstention sur les
   formes ambiguës. Mesure : exactitude contre taux de réponse.
5. **Passer à MNIST 28×28** (téléchargement nécessaire, accord à demander) : vérifier si
   l'augmentation et le redressement, inutiles ici, deviennent utiles à plus haute
   résolution.
6. **Automatiser la boucle** (un agent propose, modifie `train.py`, lance, décide) :
   nécessiterait une API payante, donc l'accord explicite de l'utilisateur.
