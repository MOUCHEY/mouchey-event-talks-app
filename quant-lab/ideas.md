# File d'idées

Une idée = un mécanisme + une règle testable sur des clôtures quotidiennes d'ETF + des paramètres a priori.
Coche `[x]` après le test, avec le résultat en une ligne. Alimente avec `/idea-scout`.

## À tester

- [ ] **example_tsmom** — Momentum de série temporelle : chaque actif long si son rendement 12 mois > 0, court sinon, pondéré à risque égal, mensuel. *(déjà écrit dans `strategies/example_tsmom.py`)*
  - Mécanisme : sous-réaction puis sur-réaction des investisseurs ; demande de couverture persistante.
  - Source : Moskowitz, Ooi & Pedersen (2012), « Time Series Momentum », Journal of Financial Economics.
  - Paramètres a priori : 12 mois de tendance, 3 mois de volatilité (article).
  - Attendu : Sharpe positif, gains pendant les krachs longs · Risques : retournements rapides (2009, 2020).

- [ ] **sma_10m** — Détenir chaque actif (poids égaux) seulement si sa clôture dépasse sa moyenne mobile 10 mois (~210 jours), sinon trésorerie ; décision mensuelle.
  - Mécanisme : suivi de tendance simple, coupe l'exposition dans les marchés baissiers durables.
  - Source : Faber (2007), « A Quantitative Approach to Tactical Asset Allocation », Journal of Wealth Management.
  - Paramètres a priori : 10 mois (article).
  - Attendu : Sharpe proche de la baseline mais drawdown nettement plus faible · Risques : faux signaux en marché sans tendance.

- [ ] **xsmom_top3** — Classer les 10 ETF par rendement 12 mois en sautant le dernier mois, détenir les 3 meilleurs à poids égaux, mensuel.
  - Mécanisme : momentum transversal entre classes d'actifs.
  - Source : Asness, Moskowitz & Pedersen (2013), « Value and Momentum Everywhere », Journal of Finance.
  - Paramètres a priori : 12-1 mois, top 3 (≈ le tiers supérieur).
  - Attendu : bat la baseline, corrélation modérée · Risques : concentration, krachs du momentum.

- [ ] **vol_managed** — Baseline à poids égaux, exposition multipliée par (vol cible / vol réalisée sur 1 mois), plafonnée à 1,5.
  - Mécanisme : la volatilité est persistante mais les rendements ne montent pas autant qu'elle → réduire le risque quand il est élevé améliore le ratio rendement/risque.
  - Source : Moreira & Muir (2017), « Volatility-Managed Portfolios », Journal of Finance.
  - Paramètres a priori : vol réalisée 21 jours, cible = vol moyenne de la baseline (~10 %).
  - Attendu : Sharpe > baseline, drawdown réduit · Risques : turnover, rebonds en V ratés.

- [ ] **inverse_vol** — Poids ∝ 1 / volatilité 63 jours, normalisés à 100 % investis, mensuel (parité de risque naïve).
  - Mécanisme : les actifs peu risqués offrent un meilleur rendement par unité de risque (aversion au levier).
  - Source : Asness, Frazzini & Pedersen (2012), « Leverage Aversion and Risk Parity », Financial Analysts Journal.
  - Paramètres a priori : 63 jours (un trimestre), sans levier.
  - Attendu : Sharpe > baseline, forte pondération obligataire · Risques : 2022 (actions et obligations en baisse ensemble).

- [ ] **dual_momentum** — Choisir le meilleur de SPY / EFA sur 12 mois ; si son rendement 12 mois est négatif, passer sur IEF ; mensuel.
  - Mécanisme : momentum relatif plus momentum absolu (filtre de tendance).
  - Source : Antonacci (2014), *Dual Momentum Investing*, McGraw-Hill (livre, pas une revue à comité de lecture).
  - Paramètres a priori : 12 mois (livre).
  - Attendu : drawdown 2008 évité · Risques : très peu de décisions, donc forte variance de l'estimation.

- [ ] **turn_of_month** — Détenir SPY, QQQ et IWM seulement les 3 premiers jours de bourse de chaque mois, trésorerie sinon.
  - Mécanisme : flux d'investissement en début de mois (salaires, fonds de pension).
  - Source : Ariel (1987), « A Monthly Effect in Stock Returns », Journal of Financial Economics ; Lakonishok & Smidt (1988), Review of Financial Studies.
  - Paramètres a priori : 3 jours. Le dernier jour du mois n'est pas connu à l'avance de façon causale : on l'exclut.
  - Attendu : petit Sharpe positif · Risques : turnover ~24x/an, à la limite de la porte, les coûts peuvent tout manger.

## Données manquantes (pas testables en l'état)
- Carry obligataire et devises : il faut des taux et des contrats à terme.
- Value entre pays : il faut des fondamentaux (CAPE, etc.).
- Dérive avant les réunions de la Fed : Lucca & Moench (2015), Journal of Finance. Il faut le calendrier des réunions.
- Rendements de nuit contre rendements en séance : il faut les prix d'ouverture.

## Testées
*(déplace ici les idées cochées, avec le résultat en une ligne)*
