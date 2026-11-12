# Tests et validations

## Exécuter

```bash
cd Tests_et_Validations
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt   # Linux/macOS : .venv/bin/python
.venv/Scripts/python tout_verifier.py
```

Prérequis : Python ≥ 3.10 (sorties produites avec 3.13.2), Node.js facultatif
(sorties produites avec v22.14.0, utilisé uniquement pour `node --check`).
Aucun réseau ni base de données. `tout_verifier.py` réécrit `resultats/` et
`SCENARIOS.md` ; les sorties livrées sont celles de la dernière exécution.

| Script | Ce qu'il vérifie | Sortie |
|---|---|---|
| `audit_preuves.py` | Les pièces client (copie dans `pieces_client_originales/`) : OpenAPI initial, données contre schéma v1, dates, référentiels, configuration publique, motifs dans le code, statuts des captures, total de la liste capturée confronté aux données par tenant | `resultats/01-audit-preuves.txt` |
| `validate_contract.py` | OpenAPI 3.1 structurellement valide (références résolues) ; les six opérations et leurs erreurs ; chaque exemple inline conforme à son schéma **et** identique au fichier `Exemples_JSON/` ; 15 exemples négatifs rejetés par la bonne règle (schéma ou règle métier) sans effet persistant | `resultats/02-contrat-et-exemples.txt` |
| `run_scenarios.py` | 18 scénarios, 82 requêtes rejouées sur `atlas_mock.py` ; chaque réponse v2 (succès **et** erreurs) est confrontée au schéma, au type de contenu et aux en-têtes déclarés dans le contrat ; effets persistants comparés avant/après | `SCENARIOS.md`, `resultats/03-scenarios.txt`, `resultats/scenarios-resultats.json` |
| `verifier_detection.py` | Contre-épreuve : 9 défauts historiques (INC-03 à INC-08, R02, R03, N03) réinjectés un par un dans le simulateur ; chacun doit faire échouer au moins un scénario | `resultats/04-detection-defauts.txt` |

## Correspondance avec les 12 scénarios exigés

| Exigence de la mission | Scénario(s) |
|---|---|
| Chemin nominal | S01 (+ S13, S14, S17) |
| Liste vide | S02 |
| Filtre combiné | S03 |
| Borne de pagination | S04, S15 |
| Saisie invalide | S05 (+ négatifs du manifeste) |
| Champ absent / null | S06 |
| Session invalide | S07 |
| Accès hors tenant | S08, S01 étape 4, S02 étape 2 |
| Permission insuffisante | S09 |
| Transition interdite | S10, S14, S17 |
| Concurrence | S11 |
| Continuité v1 | S12 |
| Compléments | S13 affectation, S15 historique, S16 idempotence, S18 journaux |

Chaque scénario de `SCENARIOS.md` indique les préconditions, la requête HTTP,
la réponse obtenue (statut, en-têtes, corps), les vérifications, l'effet persistant
et la réaction attendue du Front-End, ainsi que les exigences et décisions liées.

## Ce que ces contrôles prouvent, et ce qu'ils ne prouvent pas

- **Simulation.** `atlas_mock.py` est une implémentation en mémoire écrite pour ce
  dossier. Les scénarios prouvent que le contrat est **cohérent et réalisable**,
  que ses exemples concordent et que les règles non exprimables en schéma sont
  testables. Ils **ne prouvent pas** le comportement du futur serveur ATLAS. Les
  mêmes scénarios devront être rejoués contre la vraie implémentation (voir ADR-3).
- **Concurrence.** Le simulateur est séquentiel : S11 prouve la logique de
  révision (`If-Match` → 412), pas l'absence de course entre deux transactions.
  En base, la garantie repose sur `UPDATE … WHERE id = ? AND tenant_id = ? AND revision = ?`
  (0 ligne → 412) dans la transaction qui écrit aussi l'événement. **Vérifié par revue
  seulement** : à couvrir par un test d'intégration PostgreSQL.
- **Identité.** Le fournisseur d'identité est simulé (`fixtures/jetons-simules.json`) :
  la validation de signature et d'expiration d'un JWT n'est pas testée.
- **Routes v1.** Elles ne figurent pas dans le contrat v2 : leurs réponses sont
  vérifiées par les assertions explicites de S12, pas par un schéma. Le format de
  sortie de l'adaptateur vers Portail 1.8 (champs français) n'est pas fourni par
  le dossier (hypothèse H1) : non testable ici.
- **Expressions régulières.** Le motif du titre (`\s`, `\S`) est évalué par le moteur
  Python de `jsonschema` ; un validateur ECMA-262 peut différer sur des espaces Unicode
  rares. Le serveur reste juge (`strip()` puis longueur 5–120).
- **N04 (500 ms p95)** : non mesuré, aucune infrastructure fournie. Méthode de mesure
  proposée dans le rapport (§8). **N03 (rétention 12 mois / 30 jours)** : vérifié par
  revue de conception uniquement ; S18 ne contrôle que l'absence de jeton et de texte
  libre dans le journal simulé.
- **Fixtures.** Les écarts avec les pièces client sont listés dans `fixtures/README.md`
  (hypothèses H2, H3 et historique synthétique).

## Erreurs détectées et corrigées pendant la construction des tests

1. Un exemple négatif « titre trop court après suppression des espaces » valait
   `"  Porte  "`, soit 5 caractères utiles : il était **valide**. Corrigé en `"  Port  "`.
2. Le simulateur n'identifiait l'opération qu'après l'avoir exécutée. Les réponses
   d'erreur étaient donc journalisées comme `unknown` et **n'étaient pas confrontées
   au contrat**. Corrigé : routage avant exécution ; 74 réponses v2 désormais
   contrôlées, au lieu des seules réponses de succès.
3. `verifier_detection.py` a montré qu'aucun scénario ne détectait un tenant lu dans
   `X-Tenant` à la création (8/9 défauts détectés). Ajout à S01 d'un `X-Tenant: C02`
   falsifié et d'une lecture par Zoé (C02) : 9/9.
