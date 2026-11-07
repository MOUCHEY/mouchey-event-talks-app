# Labo quantitatif — instructions pour l'agent

## Mission
Trouver des stratégies d'allocation sur un univers d'ETF (actions, obligations, or, matières premières,
immobilier) dont la performance **survit à la déflation pour essais multiples** et, plus tard, à un examen
sur une période que tu ne vois jamais. Tu es payé à la vérité, pas au score : un échec bien documenté
vaut autant qu'un succès.

## Qui touche à quoi
| Chemin | Toi | Rôle |
|---|---|---|
| `strategies/*.py` | ✏️ écris | une hypothèse = un fichier |
| `journal.md`, `ideas.md`, `audits/` | ✏️ écris | mémoire du labo |
| `lab/`, `config.toml`, `scripts/` | 🔒 jamais | **le juge** |
| `results/results.tsv` | 🔒 jamais à la main | écrit uniquement par `lab.run` |
| `data/holdout/`, `lab.holdout` | ⛔ ni lire, ni lancer | examen final, réservé à l'humain |

## Le juge et le score
`python -m lab.run strategies/x.py --note "…"` : c'est la **seule** façon d'évaluer une stratégie.
1. contrôle statique (pas de lecture de fichier, pas de réseau, pas d'import du juge) ;
2. contrôle anti-lookahead : les poids de la date t ne doivent pas changer si on efface le futur ;
3. backtest net de coûts (5 pb par unité de turnover) sur 2007 → 2022, le même pour tous ;
4. portes : levier ≤ 2, drawdown ≤ 35 %, turnover ≤ 25x/an, Sharpe positif sur ≥ 3 des 4 sous-périodes ;
5. **score = Sharpe annualisé − décote(N)**, où N = nombre de couples (code, paramètres) distincts déjà
   évalués dans le labo. Chaque essai relève la barre de tous les autres : un essai doit valoir le coup.

`python -m lab.board` affiche le classement avec les scores recalculés au N actuel.

## Règles d'or
1. **Une expérience = une hypothèse avec un mécanisme** (prime de risque, biais comportemental, contrainte
   structurelle). « J'ai remarqué que ça marchait » n'est pas une hypothèse.
2. **Paramètres choisis avant de voir le score** (valeur de l'article, valeur ronde). Pour explorer, utilise
   `--grid` : chaque valeur est comptée comme un essai, et c'est voulu.
3. **Aucune évaluation de performance hors de `lab.run`** : pas de backtest maison, pas de boucle de
   paramètres dans un script, pas de « petit test rapide » de Sharpe. Des essais cachés faussent N ;
   c'est la seule vraie triche possible ici. L'analyse descriptive (volatilités, corrélations) est permise.
4. **Causalité** : la décision en t n'utilise que `prices.loc[:t]`. Pas de `shift(-k)`, de `center=True`,
   de `bfill`, de normalisation sur tout l'échantillon. Le juge vérifie, mais écris juste du premier coup.
5. **Tout se consigne**, surtout les échecs : `journal.md` après chaque essai, `ideas.md` mis à jour.
6. **Jamais de victoire annoncée** : un bon score est un candidat. Seul l'examen holdout lancé par un humain
   après un audit (`/audit`) dit si c'est réel.
7. Si le juge te semble faux ou trop sévère, **écris-le dans `journal.md`** pour l'humain ; ne le contourne pas.

## Contrat d'une stratégie
Copie `strategies/_template.py`. Le fichier définit `PARAMS = {...}` et
`signal(prices, **params) -> DataFrame` : une ligne par date de `prices`, une colonne par actif, des poids
(positifs = acheteur, négatifs = vendeur, le reste en trésorerie à 0 %). Imports permis : `numpy`, `pandas`,
`from lab import tools` (`rebalance_on`, `month_starts`, `week_starts`, `ann_vol`, `cap_gross`, `daily_returns`).

## Méthode (skills)
- `/experiment` — une itération complète (choisir → écrire → noter → consigner → commit). En boucle : `/loop /experiment`.
- `/idea-scout` — alimenter `ideas.md` depuis la littérature.
- `/audit` — revue sceptique d'un candidat avant de proposer l'examen holdout à l'humain.

## Si les données manquent
`python scripts/fetch_data.py` (période de recherche uniquement). Si le réseau bloque Yahoo Finance,
arrête-toi et dis-le : n'utilise jamais de données synthétiques pour la recherche.
