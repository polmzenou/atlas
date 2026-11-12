# Catalogue REST — API Interventions ATLAS v2

Auteur : Paul Mehr (M2, mission ATLAS, environnement fictif). Version du catalogue : 1.0, alignée
sur `Contrat_API.yaml` version 2.0.0. Le contrat OpenAPI fait foi pour la syntaxe ; ce catalogue
explique les règles, les choix et les réactions attendues des interfaces. Leur concordance est
contrôlée par `Tests_et_Validations/validate_contract.py` et `run_scenarios.py`.

## 1. Conventions communes

| Sujet | Convention |
|---|---|
| Base | `https://api.atlas.invalid/v2` (domaine fictif). Les routes v1 `/api/*` restent servies pendant la transition (§9). |
| Version du **contrat** | Préfixe `/v2` et `info.version`. Un changement incompatible crée `/v3` ; un ajout de champ facultatif reste en v2. |
| Révision d'une **ressource** | Champ `revision` (entier ≥ 1, +1 par mutation effective) et en-tête `ETag: "rev-N"`. Ne jamais confondre avec la version du contrat. |
| Identité | `Authorization: Bearer <jeton>` émis par le fournisseur d'identité. Tenant, rôle, utilisateur et technicien éventuel sont lus **uniquement** dans le jeton validé. `X-Tenant` est ignoré. |
| Identifiants | Chaînes opaques `^[A-Za-z0-9_-]{1,64}$` (ex. `I100`). Jamais des entiers. Aucune déduction d'ordre, de date ou de tenant. |
| Instants | RFC 3339 en UTC suffixé `Z` (ex. `2026-10-20T08:00:00Z`). L'affichage dans le fuseau de l'utilisateur relève du Front. |
| Corps | `application/json` en entrée et en sortie de succès ; `application/problem+json` pour toute erreur. |
| Corrélation | `X-Correlation-Id` sur **toutes** les réponses, repris dans `correlationId` des erreurs. Le support le demande à la place du jeton. |
| Champs inconnus | Refusés en entrée (422 `UNKNOWN_FIELD`), y compris `tenantId`, `status`, `revision`, dates. Les consommateurs doivent **tolérer** des champs de sortie ajoutés ultérieurement. |
| Paramètres de requête inconnus | 400 `INVALID_PARAMETER` (évite qu'un `state=open` de v1 soit ignoré en silence). |

### Champ absent, `null` et valeur

| Situation | Création (POST) | Modification (PATCH) | Réponse |
|---|---|---|---|
| Champ absent | Valeur par défaut (`priority` → `NORMAL`) ou 422 `REQUIRED` | **Valeur conservée** | Jamais : tous les champs d'`Intervention` sont toujours présents |
| Champ à `null` | 422 `NULL_NOT_ALLOWED` | 422 `NULL_NOT_ALLOWED` | Seul `technicianId` peut valoir `null` (aucun technicien) |
| `technicianId` / `status` fournis | 422 `UNKNOWN_FIELD` | 422 `FIELD_NOT_MODIFIABLE` (routes dédiées) | — |

Conséquence directe sur INC-04 : un PATCH du seul titre ne peut plus effacer l'affectation.

### Format d'erreur et réaction du Front-End

```json
{
  "type": "https://api.atlas.invalid/problems/validation-failed",
  "title": "Données invalides",
  "status": 422,
  "code": "VALIDATION_FAILED",
  "correlationId": "corr-0008",
  "errors": [{ "field": "title", "code": "INVALID_LENGTH", "message": "…" }]
}
```

| HTTP | `code` | Signification | Réaction attendue du Front-End |
|---|---|---|---|
| 400 | `MALFORMED_REQUEST`, `INVALID_PARAMETER`, `INVALID_CURSOR` | Requête mal construite par l'application | Erreur d'intégration : message générique + `correlationId` ; `INVALID_CURSOR` → revenir à la 1re page |
| 401 | `UNAUTHENTICATED` | Identité absente, expirée ou invalide | Reconnexion, saisie conservée localement, puis reprise |
| 403 | `FORBIDDEN` | Ressource visible, rôle jamais autorisé pour cette action | « Action non autorisée pour votre rôle » ; masquer l'action |
| 404 | `NOT_FOUND` | Absente **ou** non visible (autre tenant, technicien non affecté) | « Introuvable ou inaccessible », sans prétendre à un manque de droit |
| 409 | `INVALID_STATE`, `INVALID_TRANSITION` | L'état courant interdit l'action ; `currentStatus` fourni | Relire le détail, retirer l'action devenue impossible |
| 412 | `PRECONDITION_FAILED` | Révision lue périmée ; `currentRevision` et `ETag` fournis | Conserver la saisie, relire, montrer l'écart, renvoyer sur confirmation |
| 415 | `UNSUPPORTED_MEDIA_TYPE` | Corps non JSON | Erreur d'intégration |
| 422 | `VALIDATION_FAILED`, `IDEMPOTENCY_KEY_REUSED` | Corps JSON correct mais contraire aux règles ; `errors[]` par champ | Garder le formulaire, afficher chaque message sous son champ |
| 428 | `PRECONDITION_REQUIRED` | Mutation sans `If-Match` | Défaut d'intégration (l'écran doit toujours envoyer l'ETag lu) |

Aucune erreur n'est renvoyée avec un statut 200 : la note « tout HTTP 200 est une réussite »
(P08 M2) est écartée. L'enveloppe `success:false` n'existe plus qu'en v1.

### Ordre d'évaluation

`401` → `400/415` → `404` → `403` → `428` → `422` → `412` → `409`.
Une ressource invisible donne toujours 404 avant toute autre information : un appelant ne peut
pas deviner l'existence d'une intervention d'un autre tenant à partir d'un 403, d'un 412 ou d'un 422.
Pour `/transitions`, le droit dépend de la cible : `403` (reporter) → `428` → `422` (cible invalide)
→ `403` (rôle non autorisé pour cette cible) → `412` → `409`.

## 2. Ressource `Intervention`

| Champ | Type | Oblig. | Nullable | Valeurs / format | Fixé par | Modifiable par |
|---|---|---|---|---|---|---|
| `id` | string | oui | non | opaque | serveur | — |
| `tenantId` | string | oui | non | tenant du jeton du créateur | serveur | — |
| `siteId` | string | oui | non | site du même tenant (R12) | client à la création | — |
| `title` | string | oui | non | 5–120 caractères après suppression des espaces aux extrémités (R02) | client | PATCH |
| `priority` | string | oui | non | `LOW` \| `NORMAL` \| `HIGH` ; défaut `NORMAL` | client / défaut | PATCH |
| `status` | string | oui | non | `NEW` \| `ASSIGNED` \| `IN_PROGRESS` \| `DONE` \| `CANCELLED` | serveur | `/assignment`, `/transitions` |
| `technicianId` | string | oui | **oui** | `null` = aucun technicien ; sinon technicien actif du tenant | serveur | `/assignment` |
| `createdAt` | string | oui | non | instant UTC | serveur | — |
| `updatedAt` | string | oui | non | instant UTC de la dernière mutation effective | serveur | — |
| `createdBy` | string | oui | non | `userId` du créateur | serveur | — |
| `revision` | integer | oui | non | ≥ 1, +1 par mutation effective | serveur | — |

## 3. Cycle de vie (R04, R05)

```
            PUT /assignment            POST /transitions {to: IN_PROGRESS}     {to: DONE}
   NEW ─────────────────────▶ ASSIGNED ─────────────────────────────▶ IN_PROGRESS ─────────▶ DONE (terminal)
    │                          │  ▲ PUT /assignment (réaffectation)
    │ {to: CANCELLED}          │  └─┘
    └──────────────┬───────────┘ {to: CANCELLED}
                   ▼
              CANCELLED (terminal)
```

| Transition | Route | Rôle | Départ admis | Sinon |
|---|---|---|---|---|
| → ASSIGNED | `PUT /interventions/{id}/assignment` | planner | NEW, ASSIGNED | 409 `INVALID_STATE` |
| → IN_PROGRESS | `POST …/transitions {to: IN_PROGRESS}` | technician affecté | ASSIGNED | 409 `INVALID_TRANSITION` |
| → DONE | `POST …/transitions {to: DONE}` | technician affecté | IN_PROGRESS | 409 `INVALID_TRANSITION` |
| → CANCELLED | `POST …/transitions {to: CANCELLED}` | requester, planner | NEW, ASSIGNED | 409 `INVALID_TRANSITION` |
| → NEW, retour arrière | aucune | — | — | 422 (`to` hors enum) |

Un rôle qui n'a jamais le droit de demander une cible reçoit 403 (ex. planner → IN_PROGRESS, U2).
L'annulation conserve `technicianId` pour l'historique ; elle reste distincte de DONE (P02, P08 M4).

## 4. Matrice des droits (R06)

| Opération | requester | planner | technician | reporter |
|---|---|---|---|---|
| Liste | tenant | tenant | ses affectations | tenant |
| Détail | tenant | tenant | ses affectations (sinon 404) | tenant |
| Création | ✅ | ✅ | 403 | 403 |
| Modification titre/priorité | en NEW | en NEW ou ASSIGNED | 403 | 403 |
| Affectation | 403 | ✅ (NEW, ASSIGNED) | 403 | 403 |
| Transitions | CANCELLED | CANCELLED | IN_PROGRESS, DONE | 403 |
| Historique | tenant | tenant | ses affectations | tenant |

« Ses affectations » = interventions dont `technicianId` égale le `technician_id` du jeton
au moment de la requête. Après réaffectation à un collègue, l'ancien technicien reçoit 404
(hypothèse H4 du rapport ; le support consulte via un compte planner ou reporter du tenant).

## 5. Les six opérations du socle

### 5.1 Liste — `GET /v2/interventions` (`listInterventions`)

- **Droits** : tous les rôles ; périmètre de visibilité du §4.
- **Paramètres** : `status` (enum exact), `siteId`, `limit` (1–100, défaut 20), `cursor`
  (opaque), `sort` (`-createdAt` par défaut, ou `createdAt`). Filtres combinés par ET (R08).
- **Ordre** : `createdAt` puis `id`, dans le sens de `sort`. L'`id` ne sert qu'à départager
  les créations simultanées (I100, I101, I102 partagent `2026-10-20T08:00:00Z` après H3).
  Cet ordre secondaire est arbitraire mais stable : il ne signifie pas qu'une intervention a été
  créée avant l'autre (identifiant opaque, P02). Le Front ne doit en tirer aucune chronologie.
- **Pagination par curseur** : `page.nextCursor` encode la clé `(createdAt, id)` de la
  dernière ligne et les filtres. **Stabilité** : une insertion ou une mutation concurrente
  ne provoque ni doublon ni saut parmi les lignes déjà ordonnées. Une ligne créée
  pendant la navigation n'apparaît que si sa clé est après le curseur. Avec le tri par
  défaut (récentes d'abord), elle n'apparaît qu'en rechargeant la première page.
  **Limite** : une ligne dont le statut change pendant la navigation peut quitter ou
  rejoindre un filtre par statut. `totalItems` est recalculé à chaque page, ce n'est pas
  une photographie. Le Front affiche « page n (environ totalItems) », n étant compté par l'écran.
- **Succès** : 200 `InterventionPage` `{items, page: {limit, hasNext, nextCursor, totalItems}}`.
  `nextCursor` est `null` si et seulement si `hasNext` vaut false.
- **Liste vide** : 200 avec `items: []`, jamais 404 (INC-05). Un `siteId` inconnu ou
  étranger donne aussi une liste vide (aucune divulgation).
- **Erreurs** : 400 `INVALID_PARAMETER` (limit hors bornes, statut inconnu, paramètre
  inconnu), 400 `INVALID_CURSOR` (curseur illisible ou réutilisé avec d'autres filtres), 401.
- **Effet UI** : chargement → tableau ; état vide dédié ; bouton « suivant » piloté par `hasNext`.
  Plus aucun filtrage local des lignes (M1).
- **Exemples** : `Exemples_JSON/liste-200-filtre.json`, `liste-200-vide.json`, `erreur-400-limit.json`.

### 5.2 Détail — `GET /v2/interventions/{interventionId}` (`getIntervention`)

- **Droits** : visibilité du §4. **Succès** : 200 `Intervention` + `ETag: "rev-N"`.
- **Erreurs** : 401 ; 404 `NOT_FOUND` pour une absence **et** pour une ressource non visible,
  avec un corps identique hormis `correlationId` (S08). Le détail d'un autre tenant ne renvoie
  plus aucun contenu (INC-06).
- **Effet UI** : mémoriser l'ETag pour les mutations ; sur 404, « Intervention introuvable ou
  inaccessible » et retour à la liste.
- **Exemple** : `detail-200.json`, `erreur-404.json`.

### 5.3 Création — `POST /v2/interventions` (`createIntervention`)

- **Droits** : requester, planner (sinon 403).
- **Corps** `InterventionCreate` : `siteId` (obligatoire), `title` (obligatoire), `priority`
  (facultative, défaut NORMAL). Tout autre champ → 422 `UNKNOWN_FIELD` (R03).
- **Validations** : titre 5–120 après suppression des espaces aux extrémités, enregistré
  normalisé (R02) ; priorité dans l'enum ; site existant **dans le tenant du jeton**, sinon
  422 `SITE_NOT_FOUND` (même réponse pour inconnu ou étranger).
- **Succès** : 201, `Location: /v2/interventions/{id}`, `ETag: "rev-1"`, corps `Intervention`
  complet (`status: NEW`, `technicianId: null`). Un événement `CREATED` en révision 1.
- **Reprise après coupure** (facultatif, U1) : en-tête `Idempotency-Key`, de portée tenant
  et utilisateur, conservé 24 h. Même clé et même corps → réponse initiale rejouée
  (`Idempotent-Replayed: true`) sans doublon ; même clé avec un autre corps → 422
  `IDEMPOTENCY_KEY_REUSED`. Il s'agit d'une déduplication de requêtes, pas d'une
  interdiction des demandes métier identiques.
- **Erreurs** : 400, 401, 403, 415, 422.
- **Effet UI** : naviguer vers `Location` ; sur 422, garder les valeurs et marquer les champs ;
  sur coupure réseau, afficher « envoi incertain » et renvoyer avec la **même** clé.
- **Exemples** : `creation-requete.json`, `creation-201.json`, `erreur-422-titre.json`.

### 5.4 Modification partielle — `PATCH /v2/interventions/{interventionId}` (`updateIntervention`)

- **Droits et états** : requester en NEW ; planner en NEW ou ASSIGNED ; technician et
  reporter → 403 ; état non admis → 409 `INVALID_STATE` (`currentStatus`).
- **En-tête obligatoire** : `If-Match: "rev-N"` (428 sinon ; 412 si périmé).
- **Corps** `InterventionPatch` : `title` et/ou `priority`, au moins un champ (sinon
  422 `EMPTY_PATCH`). Champ absent = conservé ; `null` = 422. `technicianId` et `status`
  → 422 `FIELD_NOT_MODIFIABLE` (R11, INC-04).
- **Succès** : 200 `Intervention` + nouvel `ETag`. Sans changement effectif (mêmes valeurs) :
  200, même révision, aucun événement. Sinon un événement `UPDATED`. Pour le titre, seul le
  fait du changement est tracé, pas le texte (N03).
- **Pourquoi PATCH `application/json` et non `merge-patch+json`** : en JSON Merge Patch
  (RFC 7396), `null` signifie « supprimer le champ ». Ici, aucun champ modifiable n'est
  supprimable : garder `application/json` avec une règle explicite évite toute ambiguïté (ADR-2).
- **Exemples** : `modification-requete.json`, `modification-200.json`, `erreur-412.json`, `erreur-428.json`.

### 5.5 Affectation — `PUT /v2/interventions/{interventionId}/assignment` (`assignIntervention`)

- **Droits** : planner uniquement. **En-tête** : `If-Match` obligatoire.
- **Corps** `AssignmentRequest` : `{ "technicianId": "T01" }`, obligatoire et non `null`
  (le retrait sans remplacement n'est pas une fonctionnalité, R11).
- **Règles (R05, R12)** : technicien du tenant du jeton (sinon 422 `TECHNICIAN_NOT_FOUND`, même
  réponse pour inconnu ou étranger, INC-07 T02) et actif (sinon 422 `TECHNICIAN_INACTIVE`, T03).
  Statut NEW ou ASSIGNED, sinon 409 `INVALID_STATE` (« travail commencé »).
- **Effet** : `technicianId` et `status=ASSIGNED` changent dans **une** transaction, avec **un**
  événement `ASSIGNED` (premier technicien) ou `REASSIGNED` qui décrit les deux changements
  (P02, INC-10).
- **Idempotence** : PUT idempotent. Renvoyer le même technicien donne 200 sans nouvelle révision
  ni événement (INC-03). Aucune action métier n'est accessible par GET.
- **Exemples** : `affectation-requete.json`, `affectation-200.json`, `erreur-422-technicien.json`.

### 5.6 Historique — `GET /v2/interventions/{interventionId}/events` (`listInterventionEvents`)

- **Droits** : visibilité du détail (404 sinon). Lecture seule : aucune route d'écriture (R09).
- **Paramètres** : `limit` (1–100, défaut 50), `cursor`.
- **Contenu** : `Event {eventId, interventionId, revision, type, at, actor{userId, role}, changes[]}`.
  `type` ∈ `CREATED`, `UPDATED`, `ASSIGNED`, `REASSIGNED`, `STATUS_CHANGED`. Ordre par
  `revision` croissante, unique par intervention : la chronologie est interprétable même avec
  deux événements dans la même seconde. Les tentatives rejetées n'apparaissent jamais.
- **Minimisation (N03)** : `changes` porte `from`/`to` pour `priority`, `status` et
  `technicianId`. Pour `title`, seul `{ "field": "title" }` est présent (contrôlé par le schéma).
- **Exemple** : `historique-200.json`.

### 5.7 Opération complémentaire — `POST /v2/interventions/{interventionId}/transitions`

Route admise en plus du socle. Corps `{ "to": "IN_PROGRESS" | "DONE" | "CANCELLED" }`, `If-Match`
obligatoire. Règles au §3. Succès 200 `Intervention` + événement `STATUS_CHANGED`.
Exemples : `transition-requete.json`, `transition-200.json`, `erreur-409.json`.

## 6. Isolement des tenants (R07, R12)

1. Le tenant provient du jeton, jamais d'un en-tête, d'un paramètre ou du corps.
2. Toute lecture filtre par `tenant_id` dans la requête de stockage (pas après chargement).
3. Les références (`siteId`, `technicianId`) sont vérifiées dans le tenant de l'appelant.
   En base : clés étrangères composites `(tenant_id, site_id)` et `(tenant_id, technician_id)`.
4. Ressource étrangère ou invisible → 404 indiscernable d'une absence. Liste filtrée par un site
   étranger → liste vide.

## 7. Concurrence (R10)

`ETag: "rev-N"` est renvoyé sur chaque détail et chaque mutation. Les mutations exigent
`If-Match`. Une révision périmée donne 412 avec `currentRevision`. Côté stockage :
`UPDATE … SET …, revision = revision + 1 WHERE id = ? AND tenant_id = ? AND revision = ?`
puis `INSERT` de l'événement dans la même transaction. Si 0 ligne est modifiée, la
transaction est annulée et le serveur renvoie 412. **Reprise** : le Front relit, présente
l'écart et ne renvoie qu'après confirmation de l'utilisateur (U2). Détail et alternatives : ADR-4.

## 8. Correspondance v1 → v2

| v1 (wiki P06 / captures) | v2 | Remarque |
|---|---|---|
| `GET /api/interventions?state&page&size` | `GET /v2/interventions?status&siteId&limit&cursor` | `state=open` ↔ NEW, ASSIGNED, IN_PROGRESS ; `closed` ↔ DONE, CANCELLED |
| `GET /api/intervention/{id}` | `GET /v2/interventions/{id}` | pluriel homogène |
| `POST /api/interventions` (200 `{success, intervention_id}`) | `POST /v2/interventions` (201 + `Location`) | |
| `PUT /api/intervention/{id}` (remplacement ambigu) | `PATCH /v2/interventions/{id}` | champ absent conservé |
| `GET /api/assign?id&tech` | `PUT /v2/interventions/{id}/assignment` | GET à effet de bord supprimé |
| — (statut écrit via PUT) | `POST /v2/interventions/{id}/transitions` | règles serveur |
| `GET /api/interventions/{id}/history` (tableau complet) | `GET /v2/interventions/{id}/events` (paginé) | révision ajoutée |
| `priority` chaîne ou nombre `2` | enum `LOW`/`NORMAL`/`HIGH` | H2 : 1/2/3 → LOW/NORMAL/HIGH |
| `createdAt` parfois `jj/mm/aaaa hh:mm` | instant UTC `Z` | H3 : heure locale Europe/Paris |
| `id` annoncé entier | chaîne opaque | le schéma v1 était faux, les données ont toujours été des chaînes |
| `X-Tenant` | ignoré | tenant du jeton |

**Statuts exposés en v1 (hypothèse H5)** : NEW, ASSIGNED, IN_PROGRESS et DONE restent
inchangés (valeurs déjà émises par les captures). `CANCELLED`, inconnu des consommateurs v1,
est exposé `CLOSED` (valeur documentée par le schéma v1). Le champ additionnel `statusDetail`
porte la valeur v2 exacte. **Perte** pour un consommateur v1 qui l'ignore : il ne distingue
pas une annulation d'une fin de travail. L'information détaillée reste disponible dans
`statusDetail` et dans la v2.

**Restrictions de sécurité annoncées sur v1** (autorisées par N01 et P09) : identité
obligatoire (401) ; tenant imposé par le jeton (lecture hors tenant → réponse « not_found »
v1) ; règles R02/R03 appliquées aussi aux créations v1 ; `size` plafonné à 100 ;
`GET /api/assign` et `PUT /api/intervention/{id}` fermés (410) après la migration de
Console Ops et Terrain. Les comportements v1 non dangereux sont conservés, y compris
404 `no_results` sur liste vide et `currentPage` = `page + 1`. Plan détaillé : Architecture.pdf §5 et ADR-3.

## 9. Traçabilité des exigences

| Exigence | Où dans le contrat | Preuve |
|---|---|---|
| R01 identifiant, dates | `Id`, `Instant`, `Intervention` | validate_contract [3], S01 |
| R02 titre, priorité | `InterventionCreate.title` (motif), défaut NORMAL | S05, négatifs |
| R03 champs serveur | `additionalProperties: false`, description POST | S01, S05, négatif `creation-champs-serveur` |
| R04 cycle | `/transitions`, §3 | S10, S14, S17 |
| R05 affectation | `/assignment` | S13 |
| R06 droits | §4, descriptions d'opérations | S09, S10, S14 |
| R07 isolement, 401 ≠ 403 | ordre d'évaluation, `NotFound` | S07, S08 |
| R08 filtres, ordre, bornes | `listInterventions` | S02, S03, S04 |
| R09 historique | `/events`, atomicité | S06, S11, S13, S15 |
| R10 concurrence | `If-Match`, 412/428 | S11 |
| R11 absent / null | `InterventionPatch`, §1 | S06 |
| R12 relations | `SITE_NOT_FOUND`, `TECHNICIAN_*` | S05, S13 |
| N01 continuité v1 | §8 | S12 |
| N02 contrat vérifiable | `Contrat_API.yaml`, exemples | validate_contract |
| N03 minimisation | `FieldChange` sans titre, journal | S15, S18 |
| N04 performance | pagination bornée, index (rapport §8) | revue (non mesuré) |
| N05 règles hors schéma | descriptions + scénarios | run_scenarios, verifier_detection |
