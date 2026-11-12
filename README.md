# ATLAS — Audit et contrat d'intégration des interventions

**Paul Mehr** — Mastère 2 Informatique, Ynov Strasbourg — travail individuel.
Mission lancée le 27/10/2026, remise le 17/11/2026. Environnement entièrement fictif : aucune
donnée réelle, aucun secret, domaine `.invalid`.

## Ordre de lecture conseillé

| # | Livrable | Contenu |
|---|---|---|
| 1 | [Rapport_Audit.pdf](Rapport_Audit.pdf) | Les 10 parties exigées ; annexe A : tableau d'audit (11 problèmes, preuves, criticité, corrections) ; annexe B : registre des risques |
| 2 | [Architecture.pdf](Architecture.pdf) | Existant reconstitué (dont les flux non déclarés), cible et frontières de confiance, séquence HTTP, matrice Front / Back / stockage / identité, accès aux données, migration v1 |
| 3 | [Decisions_Techniques.md](Decisions_Techniques.md) | 5 ADR : frontière de confiance, conventions REST et erreurs, compatibilité, concurrence, pagination |
| 4 | [Catalogue_REST.md](Catalogue_REST.md) | Les six opérations (+ transitions) : routes, paramètres, droits, validations, statuts, champ absent/`null`, effets sur l'interface, correspondance v1 → v2, traçabilité R01–N05 |
| 5 | [Contrat_API.yaml](Contrat_API.yaml) | OpenAPI 3.1.0 : six opérations du socle + `transitionIntervention`, schémas, erreurs RFC 9457, `bearerAuth` |
| 6 | [Exemples_JSON/](Exemples_JSON/) | 21 exemples (succès de chaque opération, requêtes, erreurs), identiques aux exemples du contrat ; 15 exemples négatifs et leur [manifeste](Exemples_JSON/manifest.json) |
| 7 | [Tests_et_Validations/](Tests_et_Validations/README.md) | 18 scénarios ([SCENARIOS.md](Tests_et_Validations/SCENARIOS.md)), validateurs, simulateur, contre-épreuve, sorties réelles dans [resultats/](Tests_et_Validations/resultats/) |
| 8 | [Sources_et_IA.md](Sources_et_IA.md) | Sources datées, outils et versions, usage de l'IA, erreurs trouvées et corrigées |
| 9 | [Presentation.pdf](Presentation.pdf) | Support de l'oral (9 diapositives, 5 à 10 minutes) |

Fichiers sources ajoutés : [sources_pdf/](sources_pdf/) contient le HTML des trois PDF et leur script de
génération. [Tests_et_Validations/pieces_client_originales/](Tests_et_Validations/pieces_client_originales/LISEZ-MOI.md)
est une copie **non modifiée** des pièces auditées : ce n'est ni un livrable ni le contrat corrigé.

## Prérequis

- Python ≥ 3.10 (sorties produites avec 3.13.2) et les paquets libres de
  [requirements.txt](Tests_et_Validations/requirements.txt) : openapi-spec-validator 0.9.0, jsonschema 4.26.0, PyYAML 6.0.3.
- Facultatif : Node.js (v22.14.0 utilisé) pour `node --check` sur les extraits historiques ; Chrome, Edge ou Chromium
  pour régénérer les PDF.
- Aucun réseau, aucune base de données, aucun service ATLAS réel.

## Commandes réellement exécutées

```bash
cd Tests_et_Validations
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt     # Linux/macOS : .venv/bin/python
.venv/Scripts/python tout_verifier.py                       # lance les 4 contrôles et archive leurs sorties
cd ..
python sources_pdf/build_pdfs.py                            # régénère les 3 PDF (Chrome/Edge headless)
```

Résultat de la dernière exécution (sorties complètes dans `Tests_et_Validations/resultats/`) :

| Contrôle | Résultat |
|---|---|
| `audit_preuves.py` | 17 écarts entre données et schéma v1 ; 17/17 motifs fautifs localisés dans le code ; `node --check` OK ; `total` de liste non filtré par tenant (5 pour 4) |
| `validate_contract.py` | OpenAPI 3.1.0 valide ; 6/6 opérations ; 21 exemples conformes et identiques aux fichiers ; 15/15 négatifs rejetés par la bonne règle — CONFORME |
| `run_scenarios.py` | 18/18 scénarios, 82 requêtes, 74 réponses v2 confrontées au contrat |
| `verifier_detection.py` | 9/9 défauts historiques réinjectés détectés |

**Nature des preuves** : les scénarios sont exécutés sur un **simulateur** en mémoire. Ils prouvent la cohérence
et la faisabilité du contrat, pas le comportement du futur serveur. Les limites sont détaillées dans
[Tests_et_Validations/README.md](Tests_et_Validations/README.md).

## Points clés de la proposition

- **Le serveur décide** à partir de l'identité validée : le tenant vient du jeton, jamais de `X-Tenant`. Une ressource
  hors périmètre donne un 404 indiscernable d'une absence. La vue SQL exposée au navigateur est supprimée.
- **Mutations explicites** : `PATCH` (titre, priorité ; champ absent = conservé, `null` refusé),
  `PUT …/assignment` (idempotent), `POST …/transitions`. Plus aucune action par `GET`.
- **Concurrence** : `ETag: "rev-N"` et `If-Match` obligatoire → 412 avec relecture ; mutation, révision et événement
  écrits dans une seule transaction.
- **Erreurs** : `application/problem+json` avec `code` stable, `errors[]` par champ et `correlationId` (plus de jeton
  dans les journaux).
- **Liste** : filtres serveur combinés par ET, ordre `createdAt` puis `id`, pagination par curseur, `limit` 1–100,
  liste vide = 200.
- **Continuité** : v2 séparée ; adaptateur v1 conservé, sécurisé puis rebranché ; migration par consommateur en
  4 phases avec critères d'arrêt et de retour. Les correctifs de sécurité ne sont jamais annulés.
