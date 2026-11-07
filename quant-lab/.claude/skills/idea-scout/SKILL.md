---
name: idea-scout
description: Alimente ideas.md du labo quant avec des hypothèses tirées de la littérature (articles évalués par les pairs, études de réplication), chacune traduite en règle testable sur des clôtures quotidiennes d'ETF. À utiliser quand la file d'idées est vide ou pour explorer un thème.
---

# De la littérature aux hypothèses testables

## Contraintes du labo (filtre n° 1)
On ne dispose que de **clôtures quotidiennes ajustées** de 10 ETF (voir `config.toml`).
Pas d'intraday, de fondamentaux, de carnet d'ordres, d'options, de sentiment. Une idée qui en a besoin va
dans la section « Données manquantes » d'`ideas.md`, pas dans la file.

## Étapes
1. Choisis un thème (celui demandé, ou le moins exploré d'après `journal.md`).
2. Recherche (WebSearch) en privilégiant : revues à comité de lecture, working papers très cités, et
   surtout les **études de réplication** et de décroissance post-publication.
3. Pour chaque effet retenu, demande-toi :
   - **Mécanisme** : qui perd en face, et pourquoi il continuerait à perdre ?
   - **Robustesse rapportée** : sur combien de marchés et de décennies ? répliqué par d'autres ?
   - **Décroissance** : l'effet a-t-il faibli après publication ? (McLean & Pontiff, 2016)
   - **Traduction** : quelle règle simple sur nos 10 ETF teste l'idée, avec quels paramètres a priori ?
4. Ajoute **au plus 5 idées** par passage, au format :
```markdown
- [ ] **<nom_court>** — <règle testable en une phrase>
  - Mécanisme : …
  - Source : Auteur(s) (année), « Titre », Revue — ou « référence à vérifier »
  - Paramètres a priori : … (d'où ils viennent)
  - Attendu : … · Risques : … (sur-ajustement, coûts, régime)
```

## Honnêteté des sources
N'invente jamais une référence. Si tu n'es pas sûr de l'auteur, de l'année ou de la revue, écris
« référence à vérifier ». Une fausse citation pollue le labo plus qu'une idée manquante.
