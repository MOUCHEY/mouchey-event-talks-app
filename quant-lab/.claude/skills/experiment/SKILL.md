---
name: experiment
description: Mène UNE expérience complète dans le labo quant — choisir une hypothèse, l'écrire comme stratégie, la faire noter par le juge (lab.run), consigner le résultat et commiter. À utiliser pour chaque itération de recherche, seule ou en boucle avec /loop /experiment.
---

# Une expérience = une hypothèse = une trace

## 0. Se remettre en contexte
- `python -m lab.board` : classement, N actuel, décote actuelle.
- Lis les 10 dernières entrées de `journal.md` et la liste `ideas.md`.
- Rappel : chaque essai augmente N, donc la décote de **tous** les scores. Moins d'essais, mieux pensés.

## 1. Choisir l'hypothèse
- Prends la première idée `[ ]` de `ideas.md` la plus prometteuse, ou une piste ouverte par le journal.
- Ne retente pas une idée marquée échouée, sauf avec un argument **nouveau** (écris-le).
- Exige un mécanisme : pourquoi quelqu'un perdrait-il de l'argent en face de cette stratégie ?
- `ideas.md` est vide ? Lance d'abord `/idea-scout`.

## 2. L'écrire
- Copie `strategies/_template.py` → `strategies/<nom_court>.py`.
- Remplis la docstring : hypothèse, mécanisme, source, prédiction, origine des paramètres.
- `PARAMS` : valeurs choisies **maintenant**, avant tout résultat (article, valeur ronde, convention).
- Utilise `tools.rebalance_on(..., tools.month_starts(prices.index))` pour un rééquilibrage mensuel.
- Relis la causalité ligne par ligne : rien ne doit dépendre de données postérieures à t.

## 3. Le faire noter
```bash
python -m lab.run strategies/<nom_court>.py --note "<hypothèse en une ligne>"
```
- Erreur Python ? Corrige et relance (une exécution qui plante n'est pas comptée).
- REJETÉ pour lookahead : c'est un bug, corrige-le ; pour une porte de risque : c'est un résultat, consigne-le.
- Robustesse, une fois par idée qui dépasse la baseline : `--grid param=v_bas,v_apriori,v_haut`.
  Un plateau (les voisins marchent aussi) est bon signe ; un pic isolé signe le sur-ajustement.

## 4. Consigner (obligatoire, échec compris)
Ajoute à la fin de `journal.md` :
```markdown
## Essai #<n> — <nom_court> (<date>)
- **Hypothèse** : …
- **Résultat** : score <x> · Sharpe <y> · DD <z> · plis <a/b> · corr. baseline <c> · <ACCEPTÉ/REJETÉ : raison>
- **Lecture** : ce que ça confirme ou réfute, et pourquoi (une ou deux phrases honnêtes)
- **Suite** : idée(s) dérivée(s) ou « piste close »
```
Dans `ideas.md` : coche `[x]` l'idée testée avec un résumé en une ligne, ajoute les idées nouvelles.

## 5. Commiter
```bash
git add strategies/<nom_court>.py journal.md ideas.md results/results.tsv
git commit -m "exp #<n> <nom_court> : score <x> (<statut>)"
```

## 6. Candidat ?
Si le score dépasse le Sharpe de la baseline avec une corrélation à la baseline < 0,8, note-le comme
**candidat** dans le journal et suggère `/audit`. N'annonce jamais de découverte.

## Interdits
- Modifier `lab/`, `config.toml`, `scripts/`, `results/` ; lire `data/holdout/` ; lancer `lab.holdout`.
- Mesurer une performance hors de `lab.run` (backtest maison, boucle de paramètres dans un script).
- Ajuster les paramètres après avoir vu un score sans passer par `--grid`.
- Données synthétiques pour la recherche.
