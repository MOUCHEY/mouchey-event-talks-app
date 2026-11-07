---
name: audit
description: Revue sceptique d'une stratégie candidate du labo quant avant l'examen holdout — chasse au lookahead subtil, robustesse des paramètres, stress des coûts, dépendance à une période, essais cachés. Produit audits/<nom>.md avec un verdict. À utiliser quand un candidat sort du lot dans lab.board.
---

# Audit : essayer de tuer le candidat

Ton rôle change : tu n'es plus l'auteur, tu es l'avocat du diable. Le but est de trouver la raison pour
laquelle ce résultat est faux. Si tu n'en trouves pas après un vrai effort, le candidat mérite l'examen.

## 1. Identifier
`python -m lab.board` → note le n° d'essai, le fichier et les paramètres exacts du candidat.

## 2. Lire le code ligne par ligne
Pièges que le contrôle automatique peut rater :
- statistiques sur tout l'échantillon cachées dans une fonction utilitaire, ou calculées une seule fois ;
- `resample(...).last()` étiqueté en fin de période puis ré-aligné sur des dates antérieures ;
- poids sélectionnés selon un classement qui inclut la date du jour **et** le rendement du jour ;
- paramètres « magiques » non justifiés dans la docstring (ex. 137 jours) → réglés sur les résultats ?
- choix de l'univers ou des dates qui exploite la connaissance a posteriori (ex. exclure un actif qui a chuté).

## 3. Stress des coûts (non compté dans N)
```bash
python -m lab.run strategies/<x>.py --set ... --cost-bps 15
python -m lab.run strategies/<x>.py --set ... --cost-bps 30
```
Une stratégie qui meurt à 15 pb est fragile ; à 30 pb, ça peut être acceptable pour un turnover élevé.

## 4. Robustesse des paramètres
Si aucun `--grid` n'a été fait autour des paramètres, fais-en un (valeurs à ±50 %). Ces essais comptent
dans N et c'est voulu. Cherche un plateau ; un pic isolé = rejet.

## 5. Dépendance à une période ou à un actif
- Plis : un seul pli porte-t-il tout le résultat ?
- Corrélation à la baseline : > 0,8 → c'est surtout du bêta déguisé.
- Variante sans l'actif le plus pondéré, via un paramètre `exclude` si la stratégie s'y prête (compte dans N).

## 6. Essais cachés
Relis `journal.md` : combien de variantes de la même famille d'idées ont été testées ? Le N global
compte tout ; ici, juge si la famille a été « torturée » (beaucoup de variantes proches → méfiance accrue).

## 7. Verdict → `audits/<nom_court>.md`
```markdown
# Audit — <nom_court> (essai #<n>, <date>)
Verdict : PRÊT POUR L'EXAMEN | PAS PRÊT
## Constats
- Code : …
- Coûts : Sharpe à 5 / 15 / 30 pb = … / … / …
- Paramètres : plateau ou pic ? …
- Périodes / actifs : …
- Famille d'essais : … variantes
## Commande d'examen pour l'humain
python -m lab.holdout strategies/<x>.py --set clé=valeur ...
```
**Ne lance jamais `lab.holdout` toi-même.** Termine en donnant la commande à l'humain.
