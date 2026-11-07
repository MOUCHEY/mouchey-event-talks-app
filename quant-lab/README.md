# Labo quantitatif : auto-research sur les marchés

Un harness pour que Claude Code cherche des stratégies d'allocation **en boucle, seul**, sans pouvoir se
mentir. Le principe : un juge automatique que l'agent ne peut pas modifier, un score qui **pénalise le
nombre d'essais**, et une période d'examen final que seul toi peux lancer.

```
 ideas.md ──► /experiment ──► strategies/x.py ──► python -m lab.run ──► results.tsv
    ▲                                                  │  (juge verrouillé)
    └──────────── journal.md ◄─────────────────────────┘
                                   candidat ──► /audit ──► TOI : python -m lab.holdout
```

## Pourquoi c'est construit comme ça
Le danger n° 1 en recherche quantitative automatisée, c'est le **sur-ajustement par volume**. Testez
1 000 règles au hasard et la meilleure affichera un beau Sharpe par pure chance. Un agent qui tourne des
heures en produit énormément. D'où :

| Garde-fou | Contre quoi |
|---|---|
| Score = Sharpe − décote(N), N = essais distincts | la chance de « la meilleure de N » (Bailey & López de Prado, 2014) |
| Contrôle anti-lookahead (on efface le futur, les poids passés ne doivent pas bouger) | utiliser sans le vouloir des données de demain |
| Contrôle statique (pas de fichier, de réseau, d'import du juge) | lire les données en douce |
| Portes : levier, drawdown, turnover, stabilité sur 4 sous-périodes | les stratégies « un seul coup de chance » |
| Coûts de transaction sur le turnover réel (poids qui dérivent) | les stratégies qui n'existent qu'à coût nul |
| Holdout 2023 → aujourd'hui, jamais vu par l'agent | le sur-ajustement résiduel sur 2007-2022 |
| Hash du juge dans chaque ligne + refus si `lab/` est modifié hors commit | un juge trafiqué |

## Installation
```bash
cd quant-lab
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python scripts/fetch_data.py --with-holdout     # toi seul : écrit aussi data/holdout/
git add -A && git commit -m "Labo quant : juge v1"   # verrouille le juge
python -m lab.run strategies/baseline_equal_weight.py   # 1er essai : l'étalon
```
Pour une séparation stricte, mets `holdout_file = "~/quant-holdout/prices.csv"` dans `config.toml` :
le holdout vit alors hors du projet et l'agent ne peut pas tomber dessus.

## Lancer la recherche
Ouvre Claude Code **dans le dossier `quant-lab/`**, pour qu'il lise `CLAUDE.md` et les skills :
```
/idea-scout momentum et suivi de tendance        → remplit ideas.md
/experiment                                      → une itération complète
/loop /experiment                                → en boucle, à son rythme
/audit                                           → revue sceptique d'un candidat
```
**Agents en parallèle** (worktrees git) : fais pointer tous les agents vers **un seul** registre, sinon
chacun compte son propre N et la décote est sous-estimée :
`export QUANT_LAB_RESULTS=/chemin/absolu/partage/results.tsv`

## L'examen final (toi uniquement)
Quand `/audit` rend « PRÊT POUR L'EXAMEN » :
```bash
python -m lab.holdout strategies/x.py --set clé=valeur
```
- Un Sharpe holdout de l'ordre de la moitié du Sharpe de recherche est **normal**.
- Un signe inversé = échec ; consigne-le et ne « répare » pas la stratégie pour la représenter.
- Chaque examen use le holdout. Au-delà de quelques examens, renouvelle-le (période plus récente).

## Lire le score
- **Sharpe** : rendement annuel net / volatilité (trésorerie à 0 %, donc légèrement flatteur).
- **Décote** : le Sharpe qu'aurait en moyenne la meilleure de N stratégies sans aucun pouvoir prédictif.
  Sur 16 ans de données : ≈ 0,34 pour N = 7, ≈ 0,56 pour N = 50, ≈ 0,62 pour N = 100. C'est sévère, et c'est voulu.
- **Score** = Sharpe − décote ; il baisse pour toutes les stratégies à chaque nouvel essai. `lab.board` le recalcule.
- **P(…)** : probabilité que le vrai Sharpe dépasse la décote (Probabilistic Sharpe Ratio).
- **corr. baseline** : au-delà de 0,8, la stratégie est surtout un portefeuille à poids égaux déguisé.

## Verrouillage des permissions (recommandé, à installer toi-même)
Les règles du labo sont dans `CLAUDE.md` ; le contrôle git attrape une modification du juge. Pour que Claude
Code **bloque** aussi les actions interdites, crée `quant-lab/.claude/settings.json` avec ce contenu,
relis-le, puis commite-le :
```json
{
  "permissions": {
    "deny": [
      "Edit(/lab/**)", "Edit(/config.toml)", "Edit(/scripts/**)", "Edit(/results/**)",
      "Edit(/data/**)", "Edit(/CLAUDE.md)", "Edit(/.claude/**)",
      "Read(/data/holdout/**)",
      "Bash(*holdout*)", "Bash(*make_synthetic*)", "Bash(*results.tsv*)",
      "Bash(git push --force*)", "Bash(git reset --hard*)"
    ],
    "allow": [
      "Bash(python -m lab.run *)", "Bash(python -m lab.board *)",
      "Edit(/strategies/**)", "Edit(/journal.md)", "Edit(/ideas.md)", "Edit(/audits/**)"
    ]
  }
}
```
La liste `deny` ne fait que restreindre. La liste `allow` évite les demandes de confirmation pendant `/loop` :
retire-la si tu préfères valider chaque commande.

**Limite honnête** : un agent qui écrit un script Python peut en théorie tout lire. Ces protections
rendent la triche difficile et visible, pas impossible. Le holdout hors du projet et ta relecture des audits
restent le vrai rempart.

## Personnaliser
Univers, dates, coûts et portes se règlent dans `config.toml`. Changer le juge change les règles :
archive `results/results.tsv`, repars d'un registre vide et commite la nouvelle version du juge.

## Limites du backtest
- Univers d'ETF qui existent encore aujourd'hui (biais du survivant, faible ici mais réel).
- Exécution à la clôture, sans glissement au-delà des 5 pb ; ni impôts ni frais de garde.
- Prix ajustés Yahoo Finance : dividendes réinvestis, qualité non garantie.
- Un backtest réussi n'est pas de l'argent : passe par une période de paper trading avant tout capital réel.

## Références
- Bailey & López de Prado (2014), « The Deflated Sharpe Ratio », Journal of Portfolio Management.
- Bailey, Borwein, López de Prado & Zhu (2014), « Pseudo-Mathematics and Financial Charlatanism », Notices of the AMS.
- Harvey, Liu & Zhu (2016), « … and the Cross-Section of Expected Returns », Review of Financial Studies.
- McLean & Pontiff (2016), « Does Academic Research Destroy Stock Return Predictability? », Journal of Finance.
