# Scénarios de validation — résultats d'exécution

> **Document généré** par `python run_scenarios.py` ; ne pas éditer à la main.
> Environnement : Python 3.13.2, jsonschema 4.26.0, PyYAML 6.0.3 — exécuté le 2026-11-12 14:11 UTC.
> **Nature de la preuve : simulation.** Les réponses proviennent de `atlas_mock.py` (implémentation
> en mémoire, sans réseau ni base). Elles prouvent que le contrat est cohérent, réalisable et
> que ses exemples concordent ; elles ne prouvent pas le comportement du futur serveur ATLAS.

| Id | Catégorie imposée | Titre | Exigences | Verdict |
|---|---|---|---|---|
| [S01](#s01) | Chemin nominal | Chemin nominal : Lina crée puis retrouve sa demande (U1) | R01, R02 (priorité par défaut), R03, R09 ; INC-02 | ✅ |
| [S02](#s02) | Liste vide | Liste vide : site S03 sans demande (INC-05) | R08, R07 ; INC-05 | ✅ |
| [S03](#s03) | Filtre combiné | Filtre combiné statut ET site appliqué par le serveur (U4) | R08 ; INC-05, P08 M1 | ✅ |
| [S04](#s04) | Borne de pagination | Bornes de pagination et stabilité sous insertion (U4) | R08 ; INC-05, N04 | ✅ |
| [S05](#s05) | Saisie invalide | Saisie invalide : règle métier ≠ JSON mal formé (U1) | R02, R03, N05 ; INC-02, P08 M2 | ✅ |
| [S06](#s06) | Champ absent/null | Champ absent / null en modification partielle (INC-04) | R11, R09 ; INC-04, P08 M4 | ✅ |
| [S07](#s07) | Session invalide | Session invalide | R07 (401 distinct de 403/404), P09 | ✅ |
| [S08](#s08) | Accès hors tenant | Accès hors tenant : aucune divulgation (INC-06, U3) | R07, R06, P09 ; INC-06, M3 | ✅ |
| [S09](#s09) | Permission insuffisante | Permission insuffisante sur une ressource visible | R06, R07, P09 (reporting jamais en écriture) | ✅ |
| [S10](#s10) | Transition interdite | Transitions interdites et états terminaux | R04, R05, R06 ; INC-04 (I103 rouvert), U2 | ✅ |
| [S11](#s11) | Concurrence | Concurrence : deux planificateurs à la même révision (U2, INC-08) | R10, R09 ; INC-08 | ✅ |
| [S12](#s12) | Continuité v1 | Continuité v1 : Portail et Export BI sécurisés (N01) | N01, P09, R07 ; INC-03, INC-06 | ✅ |
| [S13](#s13) | Complément — affectation | Affectation : référentiel, atomicité, idempotence (INC-03, INC-07, INC-10) | R05, R09, R12 ; INC-03, INC-07, INC-10, U2 | ✅ |
| [S14](#s14) | Complément — transitions | Terrain : cycle du technicien (U3) | R04, R06 ; U3, INC-04 | ✅ |
| [S15](#s15) | Complément — historique | Historique : lecture, pagination et droits (U4) | R09, R06, N03 ; U4 | ✅ |
| [S16](#s16) | Complément — idempotence | Reprise après coupure réseau : clé d'idempotence (U1, approfondissement 1) | U1 (coupure avant réponse) | ✅ |
| [S17](#s17) | Complément — annulation | Annulation par la demandeuse puis tentative d'affectation | R04, R06 ; P08 M4 (« l'annulation n'est pas une fin de travail ») | ✅ |
| [S18](#s18) | Complément — observabilité | Journaux techniques sans secret ni texte libre (N03, P09) | N03, P09 Observabilité ; INC-10 | ✅ |

**Bilan : 18/18 scénarios conformes, 82 requêtes rejouées.**

## S01 — Chemin nominal : Lina crée puis retrouve sa demande (U1)

- **Catégorie** : Chemin nominal
- **Opération(s)** : createIntervention, getIntervention, listInterventions
- **Exigences / incidents** : R01, R02 (priorité par défaut), R03, R09 ; INC-02
- **Décision(s)** : ADR-2, ADR-3 (voir Decisions_Techniques.md)
- **Préconditions** : Lina (U01, requester, C01). S01 appartient à C01. Aucune intervention I104. Son navigateur envoie encore X-Tenant (configuration historique), ici falsifié en C02.

### Étape 1 — Création sans priorité (X-Tenant falsifié ignoré) : ✅ conforme

Requête :

```http
POST /v2/interventions HTTP/1.1
Host: api.atlas.invalid
Authorization: Bearer DEMO-U01-C01
Content-Type: application/json
X-Tenant: C02

{"siteId": "S01", "title": "  Climatisation salle réunion "}
```

Réponse obtenue :

```http
HTTP/1.1 201
Content-Type: application/json
Location: /v2/interventions/I104
ETag: "rev-1"
X-Correlation-Id: corr-0001

{
  "id": "I104",
  "tenantId": "C01",
  "siteId": "S01",
  "title": "Climatisation salle réunion",
  "priority": "NORMAL",
  "status": "NEW",
  "technicianId": null,
  "createdAt": "2026-10-27T09:00:01Z",
  "updatedAt": "2026-10-27T09:00:01Z",
  "createdBy": "U01",
  "revision": 1
}
```

Vérifications :

- ✅ statut 201
- ✅ statut 201 documenté pour createIntervention
- ✅ Content-Type application/json
- ✅ corps conforme au schéma du contrat
- ✅ en-tête Location déclaré, présent et conforme
- ✅ en-tête ETag déclaré, présent et conforme
- ✅ en-tête X-Correlation-Id déclaré, présent et conforme
- ✅ corps identique à Exemples_JSON/creation-201.json
- ✅ Location = /v2/interventions/I104
- ✅ ETag = "rev-1"
- ✅ titre normalisé (espaces retirés), priorité NORMAL, tenant C01 imposé

### Étape 2 — Lecture du lien Location : ✅ conforme

Requête :

```http
GET /v2/interventions/I104 HTTP/1.1
Host: api.atlas.invalid
Authorization: Bearer DEMO-U01-C01
```

Réponse obtenue :

```http
HTTP/1.1 200
Content-Type: application/json
ETag: "rev-1"
X-Correlation-Id: corr-0002

{
  "id": "I104",
  "tenantId": "C01",
  "siteId": "S01",
  "title": "Climatisation salle réunion",
  "priority": "NORMAL",
  "status": "NEW",
  "technicianId": null,
  "createdAt": "2026-10-27T09:00:01Z",
  "updatedAt": "2026-10-27T09:00:01Z",
  "createdBy": "U01",
  "revision": 1
}
```

Vérifications :

- ✅ statut 200
- ✅ statut 200 documenté pour getIntervention
- ✅ Content-Type application/json
- ✅ corps conforme au schéma du contrat
- ✅ en-tête ETag déclaré, présent et conforme
- ✅ en-tête X-Correlation-Id déclaré, présent et conforme
- ✅ même identifiant et même contenu que la réponse de création

### Étape 3 — Présence dans la liste filtrée : ✅ conforme

Requête :

```http
GET /v2/interventions?status=NEW&siteId=S01 HTTP/1.1
Host: api.atlas.invalid
Authorization: Bearer DEMO-U01-C01
```

Réponse obtenue :

```http
HTTP/1.1 200
Content-Type: application/json
X-Correlation-Id: corr-0003

{
  "items": [
    {
      "id": "I104",
      "tenantId": "C01",
      "siteId": "S01",
      "title": "Climatisation salle réunion",
      "priority": "NORMAL",
      "status": "NEW",
      "technicianId": null,
      "createdAt": "2026-10-27T09:00:01Z",
      "updatedAt": "2026-10-27T09:00:01Z",
      "createdBy": "U01",
      "revision": 1
    },
    {
      "id": "I100",
      "tenantId": "C01",
      "siteId": "S01",
      "title": "Porte bloquée accueil",
      "priority": "NORMAL",
      "status": "NEW",
      "technicianId": null,
      "createdAt": "2026-10-20T08:00:00Z",
      "updatedAt": "2026-10-20T08:00:00Z",
      "createdBy": "U02",
      "revision": 2
    }
  ],
  "page": {
    "limit": 20,
    "hasNext": false,
    "nextCursor": null,
    "totalItems": 2
  }
}
```

Vérifications :

- ✅ statut 200
- ✅ statut 200 documenté pour listInterventions
- ✅ Content-Type application/json
- ✅ corps conforme au schéma du contrat
- ✅ en-tête X-Correlation-Id déclaré, présent et conforme
- ✅ I104 présent, I100 présent

### Étape 4 — Zoé (C02) tente de lire I104 (T13) : ✅ conforme

Requête :

```http
GET /v2/interventions/I104 HTTP/1.1
Host: api.atlas.invalid
Authorization: Bearer DEMO-U20-C02
```

Réponse obtenue :

```http
HTTP/1.1 404
Content-Type: application/problem+json
X-Correlation-Id: corr-0004

{
  "type": "https://api.atlas.invalid/problems/not-found",
  "title": "Intervention introuvable",
  "status": 404,
  "code": "NOT_FOUND",
  "correlationId": "corr-0004"
}
```

Vérifications :

- ✅ statut 404
- ✅ code NOT_FOUND
- ✅ statut 404 documenté pour getIntervention
- ✅ Content-Type application/problem+json
- ✅ corps conforme au schéma du contrat
- ✅ en-tête X-Correlation-Id déclaré, présent et conforme
- ✅ I104 persistée dans C01

**Effet persistant attendu** : +1 intervention, +1 événement CREATED en révision 1 — ✅ vérifié

**Réaction attendue du Front-End** : Formulaire désactivé pendant l'envoi ; sur 201, navigation vers Location ; le détail et la liste affichent I104.

## S02 — Liste vide : site S03 sans demande (INC-05)

- **Catégorie** : Liste vide
- **Opération(s)** : listInterventions
- **Exigences / incidents** : R08, R07 ; INC-05
- **Décision(s)** : ADR-2, ADR-5 (voir Decisions_Techniques.md)
- **Préconditions** : Nora (planner C01). S03 appartient à C01 et n'a aucune intervention. Zoé (C02).

### Étape 1 — Site du tenant sans résultat : ✅ conforme

Requête :

```http
GET /v2/interventions?siteId=S03 HTTP/1.1
Host: api.atlas.invalid
Authorization: Bearer DEMO-U02-C01
```

Réponse obtenue :

```http
HTTP/1.1 200
Content-Type: application/json
X-Correlation-Id: corr-0001

{
  "items": [],
  "page": {
    "limit": 20,
    "hasNext": false,
    "nextCursor": null,
    "totalItems": 0
  }
}
```

Vérifications :

- ✅ statut 200
- ✅ statut 200 documenté pour listInterventions
- ✅ Content-Type application/json
- ✅ corps conforme au schéma du contrat
- ✅ en-tête X-Correlation-Id déclaré, présent et conforme
- ✅ corps identique à Exemples_JSON/liste-200-vide.json

### Étape 2 — Site d'un autre tenant : même réponse vide (aucune divulgation) : ✅ conforme

Requête :

```http
GET /v2/interventions?siteId=S01 HTTP/1.1
Host: api.atlas.invalid
Authorization: Bearer DEMO-U20-C02
```

Réponse obtenue :

```http
HTTP/1.1 200
Content-Type: application/json
X-Correlation-Id: corr-0002

{
  "items": [],
  "page": {
    "limit": 20,
    "hasNext": false,
    "nextCursor": null,
    "totalItems": 0
  }
}
```

Vérifications :

- ✅ statut 200
- ✅ statut 200 documenté pour listInterventions
- ✅ Content-Type application/json
- ✅ corps conforme au schéma du contrat
- ✅ en-tête X-Correlation-Id déclaré, présent et conforme
- ✅ items vide, totalItems 0

**Effet persistant attendu** : aucun — ✅ vérifié (état comparé avant/après)

**Réaction attendue du Front-End** : État « Aucune intervention pour ces critères » (pas d'alerte « ressource disparue »), filtres conservés.

## S03 — Filtre combiné statut ET site appliqué par le serveur (U4)

- **Catégorie** : Filtre combiné
- **Opération(s)** : listInterventions
- **Exigences / incidents** : R08 ; INC-05, P08 M1
- **Décision(s)** : ADR-5 (voir Decisions_Techniques.md)
- **Préconditions** : C01 : I100 NEW/S01, I101 ASSIGNED/S01, I102 NEW/S02, I103 DONE/S01.

### Étape 1 — status=NEW seul : ✅ conforme

Requête :

```http
GET /v2/interventions?status=NEW HTTP/1.1
Host: api.atlas.invalid
Authorization: Bearer DEMO-U02-C01
```

Réponse obtenue :

```http
HTTP/1.1 200
Content-Type: application/json
X-Correlation-Id: corr-0001

{
  "items": [
    {
      "id": "I102",
      "tenantId": "C01",
      "siteId": "S02",
      "title": "Éclairage couloir étage",
      "priority": "LOW",
      "status": "NEW",
      "technicianId": null,
      "createdAt": "2026-10-20T08:00:00Z",
      "updatedAt": "2026-10-20T08:00:00Z",
      "createdBy": "U02",
      "revision": 1
    },
    {
      "id": "I100",
      "tenantId": "C01",
      "siteId": "S01",
      "title": "Porte bloquée accueil",
      "priority": "NORMAL",
      "status": "NEW",
      "technicianId": null,
      "createdAt": "2026-10-20T08:00:00Z",
      "updatedAt": "2026-10-20T08:00:00Z",
      "createdBy": "U02",
      "revision": 2
    }
  ],
  "page": {
    "limit": 20,
    "hasNext": false,
    "nextCursor": null,
    "totalItems": 2
  }
}
```

Vérifications :

- ✅ statut 200
- ✅ statut 200 documenté pour listInterventions
- ✅ Content-Type application/json
- ✅ corps conforme au schéma du contrat
- ✅ en-tête X-Correlation-Id déclaré, présent et conforme
- ✅ I102 puis I100 (tri createdAt desc, id desc)

### Étape 2 — siteId=S01 seul : ✅ conforme

Requête :

```http
GET /v2/interventions?siteId=S01 HTTP/1.1
Host: api.atlas.invalid
Authorization: Bearer DEMO-U02-C01
```

Réponse obtenue :

```http
HTTP/1.1 200
Content-Type: application/json
X-Correlation-Id: corr-0002

{
  "items": [
    {
      "id": "I101",
      "tenantId": "C01",
      "siteId": "S01",
      "title": "Climatisation salle réunion",
      "priority": "NORMAL",
      "status": "ASSIGNED",
      "technicianId": "T01",
      "createdAt": "2026-10-20T08:00:00Z",
      "updatedAt": "2026-10-21T09:00:00Z",
      "createdBy": "U01",
      "revision": 2
    },
    {
      "id": "I100",
      "tenantId": "C01",
      "siteId": "S01",
      "title": "Porte bloquée accueil",
      "priority": "NORMAL",
      "status": "NEW",
      "technicianId": null,
      "createdAt": "2026-10-20T08:00:00Z",
      "updatedAt": "2026-10-20T08:00:00Z",
      "createdBy": "U02",
      "revision": 2
    },
    {
      "id": "I103",
      "tenantId": "C01",
      "siteId": "S01",
      "title": "Serrure salle serveur",
      "priority": "HIGH",
      "status": "DONE",
      "technicianId": "T01",
      "createdAt": "2026-10-19T08:00:00Z",
      "updatedAt": "2026-10-21T11:00:00Z",
      "createdBy": "U01",
      "revision": 3
    }
  ],
  "page": {
    "limit": 20,
    "hasNext": false,
    "nextCursor": null,
    "totalItems": 3
  }
}
```

Vérifications :

- ✅ statut 200
- ✅ statut 200 documenté pour listInterventions
- ✅ Content-Type application/json
- ✅ corps conforme au schéma du contrat
- ✅ en-tête X-Correlation-Id déclaré, présent et conforme
- ✅ I101, I100, I103

### Étape 3 — status=NEW ET siteId=S01 : ✅ conforme

Requête :

```http
GET /v2/interventions?status=NEW&siteId=S01 HTTP/1.1
Host: api.atlas.invalid
Authorization: Bearer DEMO-U02-C01
```

Réponse obtenue :

```http
HTTP/1.1 200
Content-Type: application/json
X-Correlation-Id: corr-0003

{
  "items": [
    {
      "id": "I100",
      "tenantId": "C01",
      "siteId": "S01",
      "title": "Porte bloquée accueil",
      "priority": "NORMAL",
      "status": "NEW",
      "technicianId": null,
      "createdAt": "2026-10-20T08:00:00Z",
      "updatedAt": "2026-10-20T08:00:00Z",
      "createdBy": "U02",
      "revision": 2
    }
  ],
  "page": {
    "limit": 20,
    "hasNext": false,
    "nextCursor": null,
    "totalItems": 1
  }
}
```

Vérifications :

- ✅ statut 200
- ✅ statut 200 documenté pour listInterventions
- ✅ Content-Type application/json
- ✅ corps conforme au schéma du contrat
- ✅ en-tête X-Correlation-Id déclaré, présent et conforme
- ✅ corps identique à Exemples_JSON/liste-200-filtre.json
- ✅ intersection exacte : I100 seul

### Étape 4 — Statut inconnu : ✅ conforme

Requête :

```http
GET /v2/interventions?status=OPEN HTTP/1.1
Host: api.atlas.invalid
Authorization: Bearer DEMO-U02-C01
```

Réponse obtenue :

```http
HTTP/1.1 400
Content-Type: application/problem+json
X-Correlation-Id: corr-0004

{
  "type": "https://api.atlas.invalid/problems/invalid-parameter",
  "title": "Paramètre invalide",
  "status": 400,
  "code": "INVALID_PARAMETER",
  "correlationId": "corr-0004",
  "errors": [
    {
      "field": "status",
      "code": "INVALID_VALUE",
      "message": "Valeurs : NEW, ASSIGNED, IN_PROGRESS, DONE, CANCELLED"
    }
  ]
}
```

Vérifications :

- ✅ statut 400
- ✅ code INVALID_PARAMETER
- ✅ erreur de champ status=INVALID_VALUE
- ✅ statut 400 documenté pour listInterventions
- ✅ Content-Type application/problem+json
- ✅ corps conforme au schéma du contrat
- ✅ en-tête X-Correlation-Id déclaré, présent et conforme

### Étape 5 — Paramètre v1 sur la route v2 : ✅ conforme

Requête :

```http
GET /v2/interventions?state=open HTTP/1.1
Host: api.atlas.invalid
Authorization: Bearer DEMO-U02-C01
```

Réponse obtenue :

```http
HTTP/1.1 400
Content-Type: application/problem+json
X-Correlation-Id: corr-0005

{
  "type": "https://api.atlas.invalid/problems/invalid-parameter",
  "title": "Paramètre invalide",
  "status": 400,
  "code": "INVALID_PARAMETER",
  "correlationId": "corr-0005",
  "errors": [
    {
      "field": "state",
      "code": "UNKNOWN_FIELD",
      "message": "Paramètre inconnu."
    }
  ]
}
```

Vérifications :

- ✅ statut 400
- ✅ code INVALID_PARAMETER
- ✅ erreur de champ state=UNKNOWN_FIELD
- ✅ statut 400 documenté pour listInterventions
- ✅ Content-Type application/problem+json
- ✅ corps conforme au schéma du contrat
- ✅ en-tête X-Correlation-Id déclaré, présent et conforme

**Effet persistant attendu** : aucun — ✅ vérifié (état comparé avant/après)

**Réaction attendue du Front-End** : Le tableau affiche exactement la page reçue ; plus aucun filtrage local des lignes.

## S04 — Bornes de pagination et stabilité sous insertion (U4)

- **Catégorie** : Borne de pagination
- **Opération(s)** : listInterventions
- **Exigences / incidents** : R08 ; INC-05, N04
- **Décision(s)** : ADR-5 (voir Decisions_Techniques.md)
- **Préconditions** : C01 contient 4 interventions dont 3 au même createdAt (I100, I101, I102).

### Étape 1 — limit=0 : ✅ conforme

Requête :

```http
GET /v2/interventions?limit=0 HTTP/1.1
Host: api.atlas.invalid
Authorization: Bearer DEMO-U02-C01
```

Réponse obtenue :

```http
HTTP/1.1 400
Content-Type: application/problem+json
X-Correlation-Id: corr-0001

{
  "type": "https://api.atlas.invalid/problems/invalid-parameter",
  "title": "Paramètre invalide",
  "status": 400,
  "code": "INVALID_PARAMETER",
  "correlationId": "corr-0001",
  "detail": "limit doit être compris entre 1 et 100.",
  "errors": [
    {
      "field": "limit",
      "code": "OUT_OF_RANGE",
      "message": "Valeur entre 1 et 100."
    }
  ]
}
```

Vérifications :

- ✅ statut 400
- ✅ code INVALID_PARAMETER
- ✅ erreur de champ limit=OUT_OF_RANGE
- ✅ statut 400 documenté pour listInterventions
- ✅ Content-Type application/problem+json
- ✅ corps conforme au schéma du contrat
- ✅ en-tête X-Correlation-Id déclaré, présent et conforme

### Étape 2 — limit=101 (taille déraisonnable) : ✅ conforme

Requête :

```http
GET /v2/interventions?limit=101 HTTP/1.1
Host: api.atlas.invalid
Authorization: Bearer DEMO-U02-C01
```

Réponse obtenue :

```http
HTTP/1.1 400
Content-Type: application/problem+json
X-Correlation-Id: corr-0002

{
  "type": "https://api.atlas.invalid/problems/invalid-parameter",
  "title": "Paramètre invalide",
  "status": 400,
  "code": "INVALID_PARAMETER",
  "correlationId": "corr-0002",
  "detail": "limit doit être compris entre 1 et 100.",
  "errors": [
    {
      "field": "limit",
      "code": "OUT_OF_RANGE",
      "message": "Valeur entre 1 et 100."
    }
  ]
}
```

Vérifications :

- ✅ statut 400
- ✅ code INVALID_PARAMETER
- ✅ erreur de champ limit=OUT_OF_RANGE
- ✅ statut 400 documenté pour listInterventions
- ✅ Content-Type application/problem+json
- ✅ corps conforme au schéma du contrat
- ✅ en-tête X-Correlation-Id déclaré, présent et conforme

### Étape 3 — limit=100 (borne haute admise) : ✅ conforme

Requête :

```http
GET /v2/interventions?limit=100 HTTP/1.1
Host: api.atlas.invalid
Authorization: Bearer DEMO-U02-C01
```

Réponse obtenue :

```http
HTTP/1.1 200
Content-Type: application/json
X-Correlation-Id: corr-0003

{
  "items": [
    {
      "id": "I102",
      "tenantId": "C01",
      "siteId": "S02",
      "title": "Éclairage couloir étage",
      "priority": "LOW",
      "status": "NEW",
      "technicianId": null,
      "createdAt": "2026-10-20T08:00:00Z",
      "updatedAt": "2026-10-20T08:00:00Z",
      "createdBy": "U02",
      "revision": 1
    },
    {
      "id": "I101",
      "tenantId": "C01",
      "siteId": "S01",
      "title": "Climatisation salle réunion",
      "priority": "NORMAL",
      "status": "ASSIGNED",
      "technicianId": "T01",
      "createdAt": "2026-10-20T08:00:00Z",
      "updatedAt": "2026-10-21T09:00:00Z",
      "createdBy": "U01",
      "revision": 2
    },
    {
      "id": "I100",
      "tenantId": "C01",
      "siteId": "S01",
      "title": "Porte bloquée accueil",
      "priority": "NORMAL",
      "status": "NEW",
      "technicianId": null,
      "createdAt": "2026-10-20T08:00:00Z",
      "updatedAt": "2026-10-20T08:00:00Z",
      "createdBy": "U02",
      "revision": 2
    },
    {
      "id": "I103",
      "tenantId": "C01",
      "siteId": "S01",
      "title": "Serrure salle serveur",
      "priority": "HIGH",
      "status": "DONE",
      "technicianId": "T01",
      "createdAt": "2026-10-19T08:00:00Z",
      "updatedAt": "2026-10-21T11:00:00Z",
      "createdBy": "U01",
      "revision": 3
    }
  ],
  "page": {
    "limit": 100,
    "hasNext": false,
    "nextCursor": null,
    "totalItems": 4
  }
}
```

Vérifications :

- ✅ statut 200
- ✅ statut 200 documenté pour listInterventions
- ✅ Content-Type application/json
- ✅ corps conforme au schéma du contrat
- ✅ en-tête X-Correlation-Id déclaré, présent et conforme
- ✅ 4 éléments, pas de page suivante

### Étape 4 — Page 1, limit=2 : ✅ conforme

Requête :

```http
GET /v2/interventions?limit=2 HTTP/1.1
Host: api.atlas.invalid
Authorization: Bearer DEMO-U02-C01
```

Réponse obtenue :

```http
HTTP/1.1 200
Content-Type: application/json
X-Correlation-Id: corr-0004

{
  "items": [
    {
      "id": "I102",
      "tenantId": "C01",
      "siteId": "S02",
      "title": "Éclairage couloir étage",
      "priority": "LOW",
      "status": "NEW",
      "technicianId": null,
      "createdAt": "2026-10-20T08:00:00Z",
      "updatedAt": "2026-10-20T08:00:00Z",
      "createdBy": "U02",
      "revision": 1
    },
    {
      "id": "I101",
      "tenantId": "C01",
      "siteId": "S01",
      "title": "Climatisation salle réunion",
      "priority": "NORMAL",
      "status": "ASSIGNED",
      "technicianId": "T01",
      "createdAt": "2026-10-20T08:00:00Z",
      "updatedAt": "2026-10-21T09:00:00Z",
      "createdBy": "U01",
      "revision": 2
    }
  ],
  "page": {
    "limit": 2,
    "hasNext": true,
    "nextCursor": "eyJrIjpbIjIwMjYtMTAtMjBUMDg6MDA6MDBaIiwiSTEwMSJdLCJmIjp7InN0YXR1cyI6bnVsbCwic2l0ZUlkIjpudWxsLCJzb3J0IjoiLWNyZWF0ZWRBdCJ9fQ",
    "totalItems": 4
  }
}
```

Vérifications :

- ✅ statut 200
- ✅ statut 200 documenté pour listInterventions
- ✅ Content-Type application/json
- ✅ corps conforme au schéma du contrat
- ✅ en-tête X-Correlation-Id déclaré, présent et conforme
- ✅ I102, I101 ; hasNext ; totalItems 4

### Étape 5 — Insertion concurrente entre deux pages : ✅ conforme

Requête :

```http
POST /v2/interventions HTTP/1.1
Host: api.atlas.invalid
Authorization: Bearer DEMO-U01-C01
Content-Type: application/json

{"siteId": "S02", "title": "Fuite lavabo étage 2"}
```

Réponse obtenue :

```http
HTTP/1.1 201
Content-Type: application/json
Location: /v2/interventions/I104
ETag: "rev-1"
X-Correlation-Id: corr-0005

{
  "id": "I104",
  "tenantId": "C01",
  "siteId": "S02",
  "title": "Fuite lavabo étage 2",
  "priority": "NORMAL",
  "status": "NEW",
  "technicianId": null,
  "createdAt": "2026-10-27T09:00:01Z",
  "updatedAt": "2026-10-27T09:00:01Z",
  "createdBy": "U01",
  "revision": 1
}
```

Vérifications :

- ✅ statut 201
- ✅ statut 201 documenté pour createIntervention
- ✅ Content-Type application/json
- ✅ corps conforme au schéma du contrat
- ✅ en-tête Location déclaré, présent et conforme
- ✅ en-tête ETag déclaré, présent et conforme
- ✅ en-tête X-Correlation-Id déclaré, présent et conforme

### Étape 6 — Page 2 avec le curseur reçu : ✅ conforme

Requête :

```http
GET /v2/interventions?limit=2&cursor=eyJrIjpbIjIwMjYtMTAtMjBUMDg6MDA6MDBaIiwiSTEwMSJdLCJmIjp7InN0YXR1cyI6bnVsbCwic2l0ZUlkIjpudWxsLCJzb3J0IjoiLWNyZWF0ZWRBdCJ9fQ HTTP/1.1
Host: api.atlas.invalid
Authorization: Bearer DEMO-U02-C01
```

Réponse obtenue :

```http
HTTP/1.1 200
Content-Type: application/json
X-Correlation-Id: corr-0006

{
  "items": [
    {
      "id": "I100",
      "tenantId": "C01",
      "siteId": "S01",
      "title": "Porte bloquée accueil",
      "priority": "NORMAL",
      "status": "NEW",
      "technicianId": null,
      "createdAt": "2026-10-20T08:00:00Z",
      "updatedAt": "2026-10-20T08:00:00Z",
      "createdBy": "U02",
      "revision": 2
    },
    {
      "id": "I103",
      "tenantId": "C01",
      "siteId": "S01",
      "title": "Serrure salle serveur",
      "priority": "HIGH",
      "status": "DONE",
      "technicianId": "T01",
      "createdAt": "2026-10-19T08:00:00Z",
      "updatedAt": "2026-10-21T11:00:00Z",
      "createdBy": "U01",
      "revision": 3
    }
  ],
  "page": {
    "limit": 2,
    "hasNext": false,
    "nextCursor": null,
    "totalItems": 5
  }
}
```

Vérifications :

- ✅ statut 200
- ✅ statut 200 documenté pour listInterventions
- ✅ Content-Type application/json
- ✅ corps conforme au schéma du contrat
- ✅ en-tête X-Correlation-Id déclaré, présent et conforme
- ✅ I100, I103 : ni doublon ni saut ; la nouvelle ligne (plus récente) n'apparaît pas
- ✅ totalItems recalculé = 5 (décompte non figé)

### Étape 7 — Curseur réutilisé avec un autre filtre : ✅ conforme

Requête :

```http
GET /v2/interventions?limit=2&status=NEW&cursor=eyJrIjpbIjIwMjYtMTAtMjBUMDg6MDA6MDBaIiwiSTEwMSJdLCJmIjp7InN0YXR1cyI6bnVsbCwic2l0ZUlkIjpudWxsLCJzb3J0IjoiLWNyZWF0ZWRBdCJ9fQ HTTP/1.1
Host: api.atlas.invalid
Authorization: Bearer DEMO-U02-C01
```

Réponse obtenue :

```http
HTTP/1.1 400
Content-Type: application/problem+json
X-Correlation-Id: corr-0007

{
  "type": "https://api.atlas.invalid/problems/invalid-cursor",
  "title": "Curseur invalide",
  "status": 400,
  "code": "INVALID_CURSOR",
  "correlationId": "corr-0007",
  "detail": "Curseur illisible ou utilisé avec d'autres filtres ; repartir de la première page."
}
```

Vérifications :

- ✅ statut 400
- ✅ code INVALID_CURSOR
- ✅ statut 400 documenté pour listInterventions
- ✅ Content-Type application/problem+json
- ✅ corps conforme au schéma du contrat
- ✅ en-tête X-Correlation-Id déclaré, présent et conforme

**Effet persistant attendu** : seule la création de l'étape 5 (I104) — ✅ vérifié

**Réaction attendue du Front-End** : Bouton « Suivant » piloté par hasNext ; position affichée « page n (environ totalItems) » calculée par l'écran ; sur INVALID_CURSOR, retour à la première page.

## S05 — Saisie invalide : règle métier ≠ JSON mal formé (U1)

- **Catégorie** : Saisie invalide
- **Opération(s)** : createIntervention
- **Exigences / incidents** : R02, R03, N05 ; INC-02, P08 M2
- **Décision(s)** : ADR-1, ADR-2 (voir Decisions_Techniques.md)
- **Préconditions** : Lina (requester C01). Le navigateur est contourné : requêtes envoyées directement.

### Étape 1 — Titre composé d'espaces : ✅ conforme

Requête :

```http
POST /v2/interventions HTTP/1.1
Host: api.atlas.invalid
Authorization: Bearer DEMO-U01-C01
Content-Type: application/json

{"siteId": "S01", "title": "     "}
```

Réponse obtenue :

```http
HTTP/1.1 422
Content-Type: application/problem+json
X-Correlation-Id: corr-0001

{
  "type": "https://api.atlas.invalid/problems/validation-failed",
  "title": "Données invalides",
  "status": 422,
  "code": "VALIDATION_FAILED",
  "correlationId": "corr-0001",
  "errors": [
    {
      "field": "title",
      "code": "INVALID_LENGTH",
      "message": "Le titre doit contenir 5 à 120 caractères hors espaces aux extrémités."
    }
  ]
}
```

Vérifications :

- ✅ statut 422
- ✅ code VALIDATION_FAILED
- ✅ erreur de champ title=INVALID_LENGTH
- ✅ statut 422 documenté pour createIntervention
- ✅ Content-Type application/problem+json
- ✅ corps conforme au schéma du contrat
- ✅ en-tête X-Correlation-Id déclaré, présent et conforme

### Étape 2 — Titre de 121 caractères : ✅ conforme

Requête :

```http
POST /v2/interventions HTTP/1.1
Host: api.atlas.invalid
Authorization: Bearer DEMO-U01-C01
Content-Type: application/json

{"siteId": "S01", "title": "Remplacement complet de la centrale de traitement d'air du bâtiment B, contrôle des filtres et des gaines, essais de bonX"}
```

Réponse obtenue :

```http
HTTP/1.1 422
Content-Type: application/problem+json
X-Correlation-Id: corr-0002

{
  "type": "https://api.atlas.invalid/problems/validation-failed",
  "title": "Données invalides",
  "status": 422,
  "code": "VALIDATION_FAILED",
  "correlationId": "corr-0002",
  "errors": [
    {
      "field": "title",
      "code": "INVALID_LENGTH",
      "message": "Le titre doit contenir 5 à 120 caractères hors espaces aux extrémités."
    }
  ]
}
```

Vérifications :

- ✅ statut 422
- ✅ code VALIDATION_FAILED
- ✅ erreur de champ title=INVALID_LENGTH
- ✅ statut 422 documenté pour createIntervention
- ✅ Content-Type application/problem+json
- ✅ corps conforme au schéma du contrat
- ✅ en-tête X-Correlation-Id déclaré, présent et conforme

### Étape 3 — Plusieurs erreurs rendues ensemble : ✅ conforme

Requête :

```http
POST /v2/interventions HTTP/1.1
Host: api.atlas.invalid
Authorization: Bearer DEMO-U01-C01
Content-Type: application/json

{"siteId": "S20", "title": "abc", "priority": "urgent", "tenantId": "C02"}
```

Réponse obtenue :

```http
HTTP/1.1 422
Content-Type: application/problem+json
X-Correlation-Id: corr-0003

{
  "type": "https://api.atlas.invalid/problems/validation-failed",
  "title": "Données invalides",
  "status": 422,
  "code": "VALIDATION_FAILED",
  "correlationId": "corr-0003",
  "errors": [
    {
      "field": "tenantId",
      "code": "UNKNOWN_FIELD",
      "message": "Champ non accepté : valeur déterminée par le serveur ou inconnue."
    },
    {
      "field": "title",
      "code": "INVALID_LENGTH",
      "message": "Le titre doit contenir 5 à 120 caractères hors espaces aux extrémités."
    },
    {
      "field": "siteId",
      "code": "SITE_NOT_FOUND",
      "message": "Site inconnu dans votre organisation."
    },
    {
      "field": "priority",
      "code": "INVALID_VALUE",
      "message": "Valeurs : LOW, NORMAL, HIGH."
    }
  ]
}
```

Vérifications :

- ✅ statut 422
- ✅ code VALIDATION_FAILED
- ✅ statut 422 documenté pour createIntervention
- ✅ Content-Type application/problem+json
- ✅ corps conforme au schéma du contrat
- ✅ en-tête X-Correlation-Id déclaré, présent et conforme
- ✅ 4 champs signalés : tenantId, title, siteId, priority

### Étape 4 — JSON mal formé : ✅ conforme

Requête :

```http
POST /v2/interventions HTTP/1.1
Host: api.atlas.invalid
Authorization: Bearer DEMO-U01-C01
Content-Type: application/json

{"siteId": "S01", "title": 
```

Réponse obtenue :

```http
HTTP/1.1 400
Content-Type: application/problem+json
X-Correlation-Id: corr-0004

{
  "type": "https://api.atlas.invalid/problems/malformed-request",
  "title": "Corps JSON illisible",
  "status": 400,
  "code": "MALFORMED_REQUEST",
  "correlationId": "corr-0004"
}
```

Vérifications :

- ✅ statut 400
- ✅ code MALFORMED_REQUEST
- ✅ statut 400 documenté pour createIntervention
- ✅ Content-Type application/problem+json
- ✅ corps conforme au schéma du contrat
- ✅ en-tête X-Correlation-Id déclaré, présent et conforme

### Étape 5 — Mauvais type de contenu : ✅ conforme

Requête :

```http
POST /v2/interventions HTTP/1.1
Host: api.atlas.invalid
Authorization: Bearer DEMO-U01-C01
Content-Type: application/x-www-form-urlencoded

title=Porte
```

Réponse obtenue :

```http
HTTP/1.1 415
Content-Type: application/problem+json
X-Correlation-Id: corr-0005

{
  "type": "https://api.atlas.invalid/problems/unsupported-media-type",
  "title": "Type de contenu non supporté",
  "status": 415,
  "code": "UNSUPPORTED_MEDIA_TYPE",
  "correlationId": "corr-0005",
  "detail": "Content-Type attendu : application/json."
}
```

Vérifications :

- ✅ statut 415
- ✅ code UNSUPPORTED_MEDIA_TYPE
- ✅ statut 415 documenté pour createIntervention
- ✅ Content-Type application/problem+json
- ✅ corps conforme au schéma du contrat
- ✅ en-tête X-Correlation-Id déclaré, présent et conforme

### Étape 6 — Borne basse acceptée : 5 caractères utiles : ✅ conforme

Requête :

```http
POST /v2/interventions HTTP/1.1
Host: api.atlas.invalid
Authorization: Bearer DEMO-U01-C01
Content-Type: application/json

{"siteId": "S01", "title": " Porte "}
```

Réponse obtenue :

```http
HTTP/1.1 201
Content-Type: application/json
Location: /v2/interventions/I104
ETag: "rev-1"
X-Correlation-Id: corr-0006

{
  "id": "I104",
  "tenantId": "C01",
  "siteId": "S01",
  "title": "Porte",
  "priority": "NORMAL",
  "status": "NEW",
  "technicianId": null,
  "createdAt": "2026-10-27T09:00:01Z",
  "updatedAt": "2026-10-27T09:00:01Z",
  "createdBy": "U01",
  "revision": 1
}
```

Vérifications :

- ✅ statut 201
- ✅ statut 201 documenté pour createIntervention
- ✅ Content-Type application/json
- ✅ corps conforme au schéma du contrat
- ✅ en-tête Location déclaré, présent et conforme
- ✅ en-tête ETag déclaré, présent et conforme
- ✅ en-tête X-Correlation-Id déclaré, présent et conforme
- ✅ titre « Porte »

### Étape 7 — Borne haute acceptée : 120 caractères : ✅ conforme

Requête :

```http
POST /v2/interventions HTTP/1.1
Host: api.atlas.invalid
Authorization: Bearer DEMO-U01-C01
Content-Type: application/json

{"siteId": "S01", "title": "Remplacement complet de la centrale de traitement d'air du bâtiment B, contrôle des filtres et des gaines, essais de bon"}
```

Réponse obtenue :

```http
HTTP/1.1 201
Content-Type: application/json
Location: /v2/interventions/I105
ETag: "rev-1"
X-Correlation-Id: corr-0007

{
  "id": "I105",
  "tenantId": "C01",
  "siteId": "S01",
  "title": "Remplacement complet de la centrale de traitement d'air du bâtiment B, contrôle des filtres et des gaines, essais de bon",
  "priority": "NORMAL",
  "status": "NEW",
  "technicianId": null,
  "createdAt": "2026-10-27T09:00:02Z",
  "updatedAt": "2026-10-27T09:00:02Z",
  "createdBy": "U01",
  "revision": 1
}
```

Vérifications :

- ✅ statut 201
- ✅ statut 201 documenté pour createIntervention
- ✅ Content-Type application/json
- ✅ corps conforme au schéma du contrat
- ✅ en-tête Location déclaré, présent et conforme
- ✅ en-tête ETag déclaré, présent et conforme
- ✅ en-tête X-Correlation-Id déclaré, présent et conforme
- ✅ titre de 120 caractères

**Effet persistant attendu** : seules les 2 créations valides (I104, I105) ; aucune trace des rejets — ✅ vérifié

**Réaction attendue du Front-End** : 422 : formulaire conservé, message sous chaque champ cité dans errors[] ; 400/415 : erreur d'intégration (message générique + correlationId), jamais présentée comme une faute de saisie.

## S06 — Champ absent / null en modification partielle (INC-04)

- **Catégorie** : Champ absent/null
- **Opération(s)** : updateIntervention
- **Exigences / incidents** : R11, R09 ; INC-04, P08 M4
- **Décision(s)** : ADR-2 (voir Decisions_Techniques.md)
- **Préconditions** : I101 ASSIGNED à T01, révision 2. Nora (planner C01).

### Étape 1 — PATCH du seul titre (technicianId absent) : ✅ conforme

Requête :

```http
PATCH /v2/interventions/I101 HTTP/1.1
Host: api.atlas.invalid
Authorization: Bearer DEMO-U02-C01
Content-Type: application/json
If-Match: "rev-2"

{"title": "Climatisation salle réunion étage"}
```

Réponse obtenue :

```http
HTTP/1.1 200
Content-Type: application/json
ETag: "rev-3"
X-Correlation-Id: corr-0001

{
  "id": "I101",
  "tenantId": "C01",
  "siteId": "S01",
  "title": "Climatisation salle réunion étage",
  "priority": "NORMAL",
  "status": "ASSIGNED",
  "technicianId": "T01",
  "createdAt": "2026-10-20T08:00:00Z",
  "updatedAt": "2026-10-27T09:00:01Z",
  "createdBy": "U01",
  "revision": 3
}
```

Vérifications :

- ✅ statut 200
- ✅ statut 200 documenté pour updateIntervention
- ✅ Content-Type application/json
- ✅ corps conforme au schéma du contrat
- ✅ en-tête ETag déclaré, présent et conforme
- ✅ en-tête X-Correlation-Id déclaré, présent et conforme
- ✅ technicianId T01 et statut ASSIGNED conservés ; révision 3
- ✅ événement UPDATED sans recopie du titre

### Étape 2 — priority: null : ✅ conforme

Requête :

```http
PATCH /v2/interventions/I101 HTTP/1.1
Host: api.atlas.invalid
Authorization: Bearer DEMO-U02-C01
Content-Type: application/json
If-Match: "rev-3"

{"priority": null}
```

Réponse obtenue :

```http
HTTP/1.1 422
Content-Type: application/problem+json
X-Correlation-Id: corr-0002

{
  "type": "https://api.atlas.invalid/problems/validation-failed",
  "title": "Données invalides",
  "status": 422,
  "code": "VALIDATION_FAILED",
  "correlationId": "corr-0002",
  "errors": [
    {
      "field": "priority",
      "code": "NULL_NOT_ALLOWED",
      "message": "Priorité obligatoire si fournie."
    }
  ]
}
```

Vérifications :

- ✅ statut 422
- ✅ code VALIDATION_FAILED
- ✅ erreur de champ priority=NULL_NOT_ALLOWED
- ✅ statut 422 documenté pour updateIntervention
- ✅ Content-Type application/problem+json
- ✅ corps conforme au schéma du contrat
- ✅ en-tête X-Correlation-Id déclaré, présent et conforme

### Étape 3 — technicianId: null (retrait déguisé) : ✅ conforme

Requête :

```http
PATCH /v2/interventions/I101 HTTP/1.1
Host: api.atlas.invalid
Authorization: Bearer DEMO-U02-C01
Content-Type: application/json
If-Match: "rev-3"

{"technicianId": null}
```

Réponse obtenue :

```http
HTTP/1.1 422
Content-Type: application/problem+json
X-Correlation-Id: corr-0003

{
  "type": "https://api.atlas.invalid/problems/validation-failed",
  "title": "Données invalides",
  "status": 422,
  "code": "VALIDATION_FAILED",
  "correlationId": "corr-0003",
  "errors": [
    {
      "field": "technicianId",
      "code": "FIELD_NOT_MODIFIABLE",
      "message": "Non modifiable ici : utiliser /assignment."
    }
  ]
}
```

Vérifications :

- ✅ statut 422
- ✅ code VALIDATION_FAILED
- ✅ erreur de champ technicianId=FIELD_NOT_MODIFIABLE
- ✅ statut 422 documenté pour updateIntervention
- ✅ Content-Type application/problem+json
- ✅ corps conforme au schéma du contrat
- ✅ en-tête X-Correlation-Id déclaré, présent et conforme

### Étape 4 — Même titre renvoyé : aucun changement effectif : ✅ conforme

Requête :

```http
PATCH /v2/interventions/I101 HTTP/1.1
Host: api.atlas.invalid
Authorization: Bearer DEMO-U02-C01
Content-Type: application/json
If-Match: "rev-3"

{"title": "Climatisation salle réunion étage"}
```

Réponse obtenue :

```http
HTTP/1.1 200
Content-Type: application/json
ETag: "rev-3"
X-Correlation-Id: corr-0004

{
  "id": "I101",
  "tenantId": "C01",
  "siteId": "S01",
  "title": "Climatisation salle réunion étage",
  "priority": "NORMAL",
  "status": "ASSIGNED",
  "technicianId": "T01",
  "createdAt": "2026-10-20T08:00:00Z",
  "updatedAt": "2026-10-27T09:00:01Z",
  "createdBy": "U01",
  "revision": 3
}
```

Vérifications :

- ✅ statut 200
- ✅ statut 200 documenté pour updateIntervention
- ✅ Content-Type application/json
- ✅ corps conforme au schéma du contrat
- ✅ en-tête ETag déclaré, présent et conforme
- ✅ en-tête X-Correlation-Id déclaré, présent et conforme
- ✅ révision toujours 3

**Effet persistant attendu** : une seule révision et un seul événement UPDATED — ✅ vérifié

**Réaction attendue du Front-End** : L'écran n'envoie que les champs modifiés ; il remplace son état par la réponse 200 et mémorise le nouvel ETag.

## S07 — Session invalide

- **Catégorie** : Session invalide
- **Opération(s)** : listInterventions, getIntervention, createIntervention
- **Exigences / incidents** : R07 (401 distinct de 403/404), P09
- **Décision(s)** : ADR-1 (voir Decisions_Techniques.md)
- **Préconditions** : Aucun jeton, jeton inconnu, ou seulement l'en-tête X-Tenant.

### Étape 1 — Sans Authorization : ✅ conforme

Requête :

```http
GET /v2/interventions HTTP/1.1
Host: api.atlas.invalid
```

Réponse obtenue :

```http
HTTP/1.1 401
Content-Type: application/problem+json
WWW-Authenticate: Bearer realm="atlas"
X-Correlation-Id: corr-0001

{
  "type": "https://api.atlas.invalid/problems/unauthenticated",
  "title": "Authentification requise",
  "status": 401,
  "code": "UNAUTHENTICATED",
  "correlationId": "corr-0001"
}
```

Vérifications :

- ✅ statut 401
- ✅ code UNAUTHENTICATED
- ✅ statut 401 documenté pour listInterventions
- ✅ Content-Type application/problem+json
- ✅ corps conforme au schéma du contrat
- ✅ en-tête WWW-Authenticate déclaré, présent et conforme
- ✅ en-tête X-Correlation-Id déclaré, présent et conforme
- ✅ WWW-Authenticate présent

### Étape 2 — Jeton non reconnu : ✅ conforme

Requête :

```http
GET /v2/interventions/I100 HTTP/1.1
Host: api.atlas.invalid
Authorization: Bearer FAUX-JETON
```

Réponse obtenue :

```http
HTTP/1.1 401
Content-Type: application/problem+json
WWW-Authenticate: Bearer realm="atlas"
X-Correlation-Id: corr-0002

{
  "type": "https://api.atlas.invalid/problems/unauthenticated",
  "title": "Authentification requise",
  "status": 401,
  "code": "UNAUTHENTICATED",
  "correlationId": "corr-0002"
}
```

Vérifications :

- ✅ statut 401
- ✅ code UNAUTHENTICATED
- ✅ statut 401 documenté pour getIntervention
- ✅ Content-Type application/problem+json
- ✅ corps conforme au schéma du contrat
- ✅ en-tête WWW-Authenticate déclaré, présent et conforme
- ✅ en-tête X-Correlation-Id déclaré, présent et conforme

### Étape 3 — X-Tenant seul ne vaut pas identité : ✅ conforme

Requête :

```http
POST /v2/interventions HTTP/1.1
Host: api.atlas.invalid
Content-Type: application/json
X-Tenant: C01

{"siteId": "S01", "title": "Porte bloquée"}
```

Réponse obtenue :

```http
HTTP/1.1 401
Content-Type: application/problem+json
WWW-Authenticate: Bearer realm="atlas"
X-Correlation-Id: corr-0003

{
  "type": "https://api.atlas.invalid/problems/unauthenticated",
  "title": "Authentification requise",
  "status": 401,
  "code": "UNAUTHENTICATED",
  "correlationId": "corr-0003"
}
```

Vérifications :

- ✅ statut 401
- ✅ code UNAUTHENTICATED
- ✅ statut 401 documenté pour createIntervention
- ✅ Content-Type application/problem+json
- ✅ corps conforme au schéma du contrat
- ✅ en-tête WWW-Authenticate déclaré, présent et conforme
- ✅ en-tête X-Correlation-Id déclaré, présent et conforme

**Effet persistant attendu** : aucun — ✅ vérifié (état comparé avant/après)

**Réaction attendue du Front-End** : Redirection vers la connexion en conservant la saisie locale ; reprise de la requête après reconnexion.

## S08 — Accès hors tenant : aucune divulgation (INC-06, U3)

- **Catégorie** : Accès hors tenant
- **Opération(s)** : getIntervention, updateIntervention, listInterventionEvents
- **Exigences / incidents** : R07, R06, P09 ; INC-06, M3
- **Décision(s)** : ADR-1 (voir Decisions_Techniques.md)
- **Préconditions** : Lina (C01). I200 appartient à C02. I999 n'existe pas. Samir (T01) n'est pas affecté à I100.

### Étape 1 — Lina lit I200 en forçant X-Tenant: C02 : ✅ conforme

Requête :

```http
GET /v2/interventions/I200 HTTP/1.1
Host: api.atlas.invalid
Authorization: Bearer DEMO-U01-C01
X-Tenant: C02
```

Réponse obtenue :

```http
HTTP/1.1 404
Content-Type: application/problem+json
X-Correlation-Id: corr-0001

{
  "type": "https://api.atlas.invalid/problems/not-found",
  "title": "Intervention introuvable",
  "status": 404,
  "code": "NOT_FOUND",
  "correlationId": "corr-0001"
}
```

Vérifications :

- ✅ statut 404
- ✅ code NOT_FOUND
- ✅ statut 404 documenté pour getIntervention
- ✅ Content-Type application/problem+json
- ✅ corps conforme au schéma du contrat
- ✅ en-tête X-Correlation-Id déclaré, présent et conforme
- ✅ aucun champ de I200 dans la réponse

### Étape 2 — Lina lit I999 inexistant : ✅ conforme

Requête :

```http
GET /v2/interventions/I999 HTTP/1.1
Host: api.atlas.invalid
Authorization: Bearer DEMO-U01-C01
```

Réponse obtenue :

```http
HTTP/1.1 404
Content-Type: application/problem+json
X-Correlation-Id: corr-0002

{
  "type": "https://api.atlas.invalid/problems/not-found",
  "title": "Intervention introuvable",
  "status": 404,
  "code": "NOT_FOUND",
  "correlationId": "corr-0002"
}
```

Vérifications :

- ✅ statut 404
- ✅ code NOT_FOUND
- ✅ statut 404 documenté pour getIntervention
- ✅ Content-Type application/problem+json
- ✅ corps conforme au schéma du contrat
- ✅ en-tête X-Correlation-Id déclaré, présent et conforme
- ✅ réponse identique à l'étape précédente (hors correlationId)

### Étape 3 — Lina tente un PATCH sur I200 : ✅ conforme

Requête :

```http
PATCH /v2/interventions/I200 HTTP/1.1
Host: api.atlas.invalid
Authorization: Bearer DEMO-U01-C01
Content-Type: application/json
If-Match: "rev-1"

{"title": "Prise de contrôle"}
```

Réponse obtenue :

```http
HTTP/1.1 404
Content-Type: application/problem+json
X-Correlation-Id: corr-0003

{
  "type": "https://api.atlas.invalid/problems/not-found",
  "title": "Intervention introuvable",
  "status": 404,
  "code": "NOT_FOUND",
  "correlationId": "corr-0003"
}
```

Vérifications :

- ✅ statut 404
- ✅ code NOT_FOUND
- ✅ statut 404 documenté pour updateIntervention
- ✅ Content-Type application/problem+json
- ✅ corps conforme au schéma du contrat
- ✅ en-tête X-Correlation-Id déclaré, présent et conforme

### Étape 4 — Lina lit l'historique de I200 : ✅ conforme

Requête :

```http
GET /v2/interventions/I200/events HTTP/1.1
Host: api.atlas.invalid
Authorization: Bearer DEMO-U01-C01
```

Réponse obtenue :

```http
HTTP/1.1 404
Content-Type: application/problem+json
X-Correlation-Id: corr-0004

{
  "type": "https://api.atlas.invalid/problems/not-found",
  "title": "Intervention introuvable",
  "status": 404,
  "code": "NOT_FOUND",
  "correlationId": "corr-0004"
}
```

Vérifications :

- ✅ statut 404
- ✅ code NOT_FOUND
- ✅ statut 404 documenté pour listInterventionEvents
- ✅ Content-Type application/problem+json
- ✅ corps conforme au schéma du contrat
- ✅ en-tête X-Correlation-Id déclaré, présent et conforme

### Étape 5 — Samir lit I100 (même tenant, non affectée) : ✅ conforme

Requête :

```http
GET /v2/interventions/I100 HTTP/1.1
Host: api.atlas.invalid
Authorization: Bearer DEMO-U03-C01
```

Réponse obtenue :

```http
HTTP/1.1 404
Content-Type: application/problem+json
X-Correlation-Id: corr-0005

{
  "type": "https://api.atlas.invalid/problems/not-found",
  "title": "Intervention introuvable",
  "status": 404,
  "code": "NOT_FOUND",
  "correlationId": "corr-0005"
}
```

Vérifications :

- ✅ statut 404
- ✅ code NOT_FOUND
- ✅ statut 404 documenté pour getIntervention
- ✅ Content-Type application/problem+json
- ✅ corps conforme au schéma du contrat
- ✅ en-tête X-Correlation-Id déclaré, présent et conforme

**Effet persistant attendu** : aucun — ✅ vérifié (état comparé avant/après)

**Réaction attendue du Front-End** : « Intervention introuvable ou inaccessible » + lien vers la liste ; le Front n'affirme jamais un manque de droit qu'il ne peut distinguer.

## S09 — Permission insuffisante sur une ressource visible

- **Catégorie** : Permission insuffisante
- **Opération(s)** : updateIntervention, createIntervention, assignIntervention
- **Exigences / incidents** : R06, R07, P09 (reporting jamais en écriture)
- **Décision(s)** : ADR-1 (voir Decisions_Techniques.md)
- **Préconditions** : bi-c01 (reporter C01), Lina (requester), Samir (technician de I101).

### Étape 1 — Reporter lit la liste (autorisé) : ✅ conforme

Requête :

```http
GET /v2/interventions HTTP/1.1
Host: api.atlas.invalid
Authorization: Bearer DEMO-BI01-C01
```

Réponse obtenue :

```http
HTTP/1.1 200
Content-Type: application/json
X-Correlation-Id: corr-0001

{
  "items": [
    {
      "id": "I102",
      "tenantId": "C01",
      "siteId": "S02",
      "title": "Éclairage couloir étage",
      "priority": "LOW",
      "status": "NEW",
      "technicianId": null,
      "createdAt": "2026-10-20T08:00:00Z",
      "updatedAt": "2026-10-20T08:00:00Z",
      "createdBy": "U02",
      "revision": 1
    },
    {
      "id": "I101",
      "tenantId": "C01",
      "siteId": "S01",
      "title": "Climatisation salle réunion",
      "priority": "NORMAL",
      "status": "ASSIGNED",
      "technicianId": "T01",
      "createdAt": "2026-10-20T08:00:00Z",
      "updatedAt": "2026-10-21T09:00:00Z",
      "createdBy": "U01",
      "revision": 2
    },
    {
      "id": "I100",
      "tenantId": "C01",
      "siteId": "S01",
      "title": "Porte bloquée accueil",
      "priority": "NORMAL",
      "status": "NEW",
      "technicianId": null,
      "createdAt": "2026-10-20T08:00:00Z",
      "updatedAt": "2026-10-20T08:00:00Z",
      "createdBy": "U02",
      "revision": 2
    },
    {
      "id": "I103",
      "tenantId": "C01",
      "siteId": "S01",
      "title": "Serrure salle serveur",
      "priority": "HIGH",
      "status": "DONE",
      "technicianId": "T01",
      "createdAt": "2026-10-19T08:00:00Z",
      "updatedAt": "2026-10-21T11:00:00Z",
      "createdBy": "U01",
      "revision": 3
    }
  ],
  "page": {
    "limit": 20,
    "hasNext": false,
    "nextCursor": null,
    "totalItems": 4
  }
}
```

Vérifications :

- ✅ statut 200
- ✅ statut 200 documenté pour listInterventions
- ✅ Content-Type application/json
- ✅ corps conforme au schéma du contrat
- ✅ en-tête X-Correlation-Id déclaré, présent et conforme
- ✅ 4 interventions C01

### Étape 2 — Reporter modifie I100 : ✅ conforme

Requête :

```http
PATCH /v2/interventions/I100 HTTP/1.1
Host: api.atlas.invalid
Authorization: Bearer DEMO-BI01-C01
Content-Type: application/json
If-Match: "rev-2"

{"priority": "HIGH"}
```

Réponse obtenue :

```http
HTTP/1.1 403
Content-Type: application/problem+json
X-Correlation-Id: corr-0002

{
  "type": "https://api.atlas.invalid/problems/forbidden",
  "title": "Action non autorisée",
  "status": 403,
  "code": "FORBIDDEN",
  "correlationId": "corr-0002",
  "detail": "Le rôle reporter ne peut pas modifier une intervention."
}
```

Vérifications :

- ✅ statut 403
- ✅ code FORBIDDEN
- ✅ statut 403 documenté pour updateIntervention
- ✅ Content-Type application/problem+json
- ✅ corps conforme au schéma du contrat
- ✅ en-tête X-Correlation-Id déclaré, présent et conforme

### Étape 3 — Reporter crée : ✅ conforme

Requête :

```http
POST /v2/interventions HTTP/1.1
Host: api.atlas.invalid
Authorization: Bearer DEMO-BI01-C01
Content-Type: application/json

{"siteId": "S01", "title": "Porte bloquée"}
```

Réponse obtenue :

```http
HTTP/1.1 403
Content-Type: application/problem+json
X-Correlation-Id: corr-0003

{
  "type": "https://api.atlas.invalid/problems/forbidden",
  "title": "Action non autorisée",
  "status": 403,
  "code": "FORBIDDEN",
  "correlationId": "corr-0003",
  "detail": "Le rôle reporter ne peut pas créer d'intervention."
}
```

Vérifications :

- ✅ statut 403
- ✅ code FORBIDDEN
- ✅ statut 403 documenté pour createIntervention
- ✅ Content-Type application/problem+json
- ✅ corps conforme au schéma du contrat
- ✅ en-tête X-Correlation-Id déclaré, présent et conforme

### Étape 4 — Demandeuse affecte un technicien : ✅ conforme

Requête :

```http
PUT /v2/interventions/I100/assignment HTTP/1.1
Host: api.atlas.invalid
Authorization: Bearer DEMO-U01-C01
Content-Type: application/json
If-Match: "rev-2"

{"technicianId": "T01"}
```

Réponse obtenue :

```http
HTTP/1.1 403
Content-Type: application/problem+json
X-Correlation-Id: corr-0004

{
  "type": "https://api.atlas.invalid/problems/forbidden",
  "title": "Action non autorisée",
  "status": 403,
  "code": "FORBIDDEN",
  "correlationId": "corr-0004",
  "detail": "Le rôle requester ne peut pas affecter un technicien."
}
```

Vérifications :

- ✅ statut 403
- ✅ code FORBIDDEN
- ✅ statut 403 documenté pour assignIntervention
- ✅ Content-Type application/problem+json
- ✅ corps conforme au schéma du contrat
- ✅ en-tête X-Correlation-Id déclaré, présent et conforme

### Étape 5 — Technicien modifie le titre de son intervention : ✅ conforme

Requête :

```http
PATCH /v2/interventions/I101 HTTP/1.1
Host: api.atlas.invalid
Authorization: Bearer DEMO-U03-C01
Content-Type: application/json
If-Match: "rev-2"

{"title": "Titre modifié par Samir"}
```

Réponse obtenue :

```http
HTTP/1.1 403
Content-Type: application/problem+json
X-Correlation-Id: corr-0005

{
  "type": "https://api.atlas.invalid/problems/forbidden",
  "title": "Action non autorisée",
  "status": 403,
  "code": "FORBIDDEN",
  "correlationId": "corr-0005",
  "detail": "Le rôle technician ne peut pas modifier une intervention."
}
```

Vérifications :

- ✅ statut 403
- ✅ code FORBIDDEN
- ✅ statut 403 documenté pour updateIntervention
- ✅ Content-Type application/problem+json
- ✅ corps conforme au schéma du contrat
- ✅ en-tête X-Correlation-Id déclaré, présent et conforme

**Effet persistant attendu** : aucun — ✅ vérifié (état comparé avant/après)

**Réaction attendue du Front-End** : L'action n'est pas proposée pour ce rôle ; si l'appel survient quand même : « Action non autorisée pour votre rôle », données inchangées.

## S10 — Transitions interdites et états terminaux

- **Catégorie** : Transition interdite
- **Opération(s)** : transitionIntervention, assignIntervention, updateIntervention
- **Exigences / incidents** : R04, R05, R06 ; INC-04 (I103 rouvert), U2
- **Décision(s)** : ADR-2 (voir Decisions_Techniques.md)
- **Préconditions** : I103 DONE (rév. 3), I100 NEW (rév. 2), I101 ASSIGNED (rév. 2).

### Étape 1 — Annuler I103 terminée : ✅ conforme

Requête :

```http
POST /v2/interventions/I103/transitions HTTP/1.1
Host: api.atlas.invalid
Authorization: Bearer DEMO-U02-C01
Content-Type: application/json
If-Match: "rev-3"

{"to": "CANCELLED"}
```

Réponse obtenue :

```http
HTTP/1.1 409
Content-Type: application/problem+json
X-Correlation-Id: corr-0001

{
  "type": "https://api.atlas.invalid/problems/invalid-transition",
  "title": "Transition interdite",
  "status": 409,
  "code": "INVALID_TRANSITION",
  "correlationId": "corr-0001",
  "detail": "DONE → CANCELLED n'est pas autorisé.",
  "currentStatus": "DONE"
}
```

Vérifications :

- ✅ statut 409
- ✅ code INVALID_TRANSITION
- ✅ statut 409 documenté pour transitionIntervention
- ✅ Content-Type application/problem+json
- ✅ corps conforme au schéma du contrat
- ✅ en-tête X-Correlation-Id déclaré, présent et conforme
- ✅ currentStatus DONE

### Étape 2 — Affecter I103 terminée : ✅ conforme

Requête :

```http
PUT /v2/interventions/I103/assignment HTTP/1.1
Host: api.atlas.invalid
Authorization: Bearer DEMO-U02-C01
Content-Type: application/json
If-Match: "rev-3"

{"technicianId": "T01"}
```

Réponse obtenue :

```http
HTTP/1.1 409
Content-Type: application/problem+json
X-Correlation-Id: corr-0002

{
  "type": "https://api.atlas.invalid/problems/invalid-state",
  "title": "Affectation impossible dans cet état",
  "status": 409,
  "code": "INVALID_STATE",
  "correlationId": "corr-0002",
  "detail": "Une intervention DONE ne peut plus être affectée.",
  "currentStatus": "DONE"
}
```

Vérifications :

- ✅ statut 409
- ✅ code INVALID_STATE
- ✅ statut 409 documenté pour assignIntervention
- ✅ Content-Type application/problem+json
- ✅ corps conforme au schéma du contrat
- ✅ en-tête X-Correlation-Id déclaré, présent et conforme

### Étape 3 — Planificateur force IN_PROGRESS : ✅ conforme

Requête :

```http
POST /v2/interventions/I101/transitions HTTP/1.1
Host: api.atlas.invalid
Authorization: Bearer DEMO-U02-C01
Content-Type: application/json
If-Match: "rev-2"

{"to": "IN_PROGRESS"}
```

Réponse obtenue :

```http
HTTP/1.1 403
Content-Type: application/problem+json
X-Correlation-Id: corr-0003

{
  "type": "https://api.atlas.invalid/problems/forbidden",
  "title": "Action non autorisée",
  "status": 403,
  "code": "FORBIDDEN",
  "correlationId": "corr-0003",
  "detail": "Le rôle planner ne peut pas demander IN_PROGRESS."
}
```

Vérifications :

- ✅ statut 403
- ✅ code FORBIDDEN
- ✅ statut 403 documenté pour transitionIntervention
- ✅ Content-Type application/problem+json
- ✅ corps conforme au schéma du contrat
- ✅ en-tête X-Correlation-Id déclaré, présent et conforme

### Étape 4 — Demandeuse corrige une demande ASSIGNED : ✅ conforme

Requête :

```http
PATCH /v2/interventions/I101 HTTP/1.1
Host: api.atlas.invalid
Authorization: Bearer DEMO-U01-C01
Content-Type: application/json
If-Match: "rev-2"

{"priority": "HIGH"}
```

Réponse obtenue :

```http
HTTP/1.1 409
Content-Type: application/problem+json
X-Correlation-Id: corr-0004

{
  "type": "https://api.atlas.invalid/problems/invalid-state",
  "title": "Modification impossible dans cet état",
  "status": 409,
  "code": "INVALID_STATE",
  "correlationId": "corr-0004",
  "detail": "Le rôle requester ne peut modifier une intervention ASSIGNED.",
  "currentStatus": "ASSIGNED"
}
```

Vérifications :

- ✅ statut 409
- ✅ code INVALID_STATE
- ✅ statut 409 documenté pour updateIntervention
- ✅ Content-Type application/problem+json
- ✅ corps conforme au schéma du contrat
- ✅ en-tête X-Correlation-Id déclaré, présent et conforme

### Étape 5 — Retour vers NEW demandé : ✅ conforme

Requête :

```http
POST /v2/interventions/I103/transitions HTTP/1.1
Host: api.atlas.invalid
Authorization: Bearer DEMO-U02-C01
Content-Type: application/json
If-Match: "rev-3"

{"to": "NEW"}
```

Réponse obtenue :

```http
HTTP/1.1 422
Content-Type: application/problem+json
X-Correlation-Id: corr-0005

{
  "type": "https://api.atlas.invalid/problems/validation-failed",
  "title": "Données invalides",
  "status": 422,
  "code": "VALIDATION_FAILED",
  "correlationId": "corr-0005",
  "errors": [
    {
      "field": "to",
      "code": "INVALID_VALUE",
      "message": "Valeurs : IN_PROGRESS, DONE, CANCELLED (ASSIGNED via /assignment)."
    }
  ]
}
```

Vérifications :

- ✅ statut 422
- ✅ code VALIDATION_FAILED
- ✅ erreur de champ to=INVALID_VALUE
- ✅ statut 422 documenté pour transitionIntervention
- ✅ Content-Type application/problem+json
- ✅ corps conforme au schéma du contrat
- ✅ en-tête X-Correlation-Id déclaré, présent et conforme

**Effet persistant attendu** : aucun — ✅ vérifié (état comparé avant/après)

**Réaction attendue du Front-End** : Sur 409, relire le détail et retirer l'action devenue impossible ; afficher le statut courant renvoyé.

## S11 — Concurrence : deux planificateurs à la même révision (U2, INC-08)

- **Catégorie** : Concurrence
- **Opération(s)** : getIntervention, updateIntervention, assignIntervention
- **Exigences / incidents** : R10, R09 ; INC-08
- **Décision(s)** : ADR-4 (voir Decisions_Techniques.md)
- **Préconditions** : Nora et un collègue (même identité planner simulée) ont lu I100 en révision 2.

### Étape 1 — Lecture : ETag rev-2 : ✅ conforme

Requête :

```http
GET /v2/interventions/I100 HTTP/1.1
Host: api.atlas.invalid
Authorization: Bearer DEMO-U02-C01
```

Réponse obtenue :

```http
HTTP/1.1 200
Content-Type: application/json
ETag: "rev-2"
X-Correlation-Id: corr-0001

{
  "id": "I100",
  "tenantId": "C01",
  "siteId": "S01",
  "title": "Porte bloquée accueil",
  "priority": "NORMAL",
  "status": "NEW",
  "technicianId": null,
  "createdAt": "2026-10-20T08:00:00Z",
  "updatedAt": "2026-10-20T08:00:00Z",
  "createdBy": "U02",
  "revision": 2
}
```

Vérifications :

- ✅ statut 200
- ✅ statut 200 documenté pour getIntervention
- ✅ Content-Type application/json
- ✅ corps conforme au schéma du contrat
- ✅ en-tête ETag déclaré, présent et conforme
- ✅ en-tête X-Correlation-Id déclaré, présent et conforme
- ✅ ETag "rev-2"

### Étape 2 — Mutation sans If-Match : ✅ conforme

Requête :

```http
PATCH /v2/interventions/I100 HTTP/1.1
Host: api.atlas.invalid
Authorization: Bearer DEMO-U02-C01
Content-Type: application/json

{"priority": "HIGH"}
```

Réponse obtenue :

```http
HTTP/1.1 428
Content-Type: application/problem+json
X-Correlation-Id: corr-0002

{
  "type": "https://api.atlas.invalid/problems/precondition-required",
  "title": "En-tête If-Match obligatoire",
  "status": 428,
  "code": "PRECONDITION_REQUIRED",
  "correlationId": "corr-0002"
}
```

Vérifications :

- ✅ statut 428
- ✅ code PRECONDITION_REQUIRED
- ✅ statut 428 documenté pour updateIntervention
- ✅ Content-Type application/problem+json
- ✅ corps conforme au schéma du contrat
- ✅ en-tête X-Correlation-Id déclaré, présent et conforme

### Étape 3 — Nora relève la priorité (If-Match rev-2) : ✅ conforme

Requête :

```http
PATCH /v2/interventions/I100 HTTP/1.1
Host: api.atlas.invalid
Authorization: Bearer DEMO-U02-C01
Content-Type: application/json
If-Match: "rev-2"

{"priority": "HIGH"}
```

Réponse obtenue :

```http
HTTP/1.1 200
Content-Type: application/json
ETag: "rev-3"
X-Correlation-Id: corr-0003

{
  "id": "I100",
  "tenantId": "C01",
  "siteId": "S01",
  "title": "Porte bloquée accueil",
  "priority": "HIGH",
  "status": "NEW",
  "technicianId": null,
  "createdAt": "2026-10-20T08:00:00Z",
  "updatedAt": "2026-10-27T09:00:01Z",
  "createdBy": "U02",
  "revision": 3
}
```

Vérifications :

- ✅ statut 200
- ✅ statut 200 documenté pour updateIntervention
- ✅ Content-Type application/json
- ✅ corps conforme au schéma du contrat
- ✅ en-tête ETag déclaré, présent et conforme
- ✅ en-tête X-Correlation-Id déclaré, présent et conforme
- ✅ corps identique à Exemples_JSON/modification-200.json

### Étape 4 — Collègue affecte T01 depuis l'écran ancien (If-Match rev-2) : ✅ conforme

Requête :

```http
PUT /v2/interventions/I100/assignment HTTP/1.1
Host: api.atlas.invalid
Authorization: Bearer DEMO-U02-C01
Content-Type: application/json
If-Match: "rev-2"

{"technicianId": "T01"}
```

Réponse obtenue :

```http
HTTP/1.1 412
Content-Type: application/problem+json
ETag: "rev-3"
X-Correlation-Id: corr-0004

{
  "type": "https://api.atlas.invalid/problems/precondition-failed",
  "title": "Intervention modifiée entre-temps",
  "status": 412,
  "code": "PRECONDITION_FAILED",
  "correlationId": "corr-0004",
  "detail": "If-Match \"rev-2\" ne correspond plus à la révision 3.",
  "currentRevision": 3
}
```

Vérifications :

- ✅ statut 412
- ✅ code PRECONDITION_FAILED
- ✅ statut 412 documenté pour assignIntervention
- ✅ Content-Type application/problem+json
- ✅ corps conforme au schéma du contrat
- ✅ en-tête ETag déclaré, présent et conforme
- ✅ en-tête X-Correlation-Id déclaré, présent et conforme
- ✅ currentRevision 3 et ETag rev-3
- ✅ I100 inchangée : NEW, sans technicien

### Étape 5 — Relecture par le collègue : ✅ conforme

Requête :

```http
GET /v2/interventions/I100 HTTP/1.1
Host: api.atlas.invalid
Authorization: Bearer DEMO-U02-C01
```

Réponse obtenue :

```http
HTTP/1.1 200
Content-Type: application/json
ETag: "rev-3"
X-Correlation-Id: corr-0005

{
  "id": "I100",
  "tenantId": "C01",
  "siteId": "S01",
  "title": "Porte bloquée accueil",
  "priority": "HIGH",
  "status": "NEW",
  "technicianId": null,
  "createdAt": "2026-10-20T08:00:00Z",
  "updatedAt": "2026-10-27T09:00:01Z",
  "createdBy": "U02",
  "revision": 3
}
```

Vérifications :

- ✅ statut 200
- ✅ statut 200 documenté pour getIntervention
- ✅ Content-Type application/json
- ✅ corps conforme au schéma du contrat
- ✅ en-tête ETag déclaré, présent et conforme
- ✅ en-tête X-Correlation-Id déclaré, présent et conforme
- ✅ priorité HIGH visible (décision de Nora conservée)

### Étape 6 — Nouvel envoi conscient avec rev-3 : ✅ conforme

Requête :

```http
PUT /v2/interventions/I100/assignment HTTP/1.1
Host: api.atlas.invalid
Authorization: Bearer DEMO-U02-C01
Content-Type: application/json
If-Match: "rev-3"

{"technicianId": "T01"}
```

Réponse obtenue :

```http
HTTP/1.1 200
Content-Type: application/json
ETag: "rev-4"
X-Correlation-Id: corr-0006

{
  "id": "I100",
  "tenantId": "C01",
  "siteId": "S01",
  "title": "Porte bloquée accueil",
  "priority": "HIGH",
  "status": "ASSIGNED",
  "technicianId": "T01",
  "createdAt": "2026-10-20T08:00:00Z",
  "updatedAt": "2026-10-27T09:00:02Z",
  "createdBy": "U02",
  "revision": 4
}
```

Vérifications :

- ✅ statut 200
- ✅ statut 200 documenté pour assignIntervention
- ✅ Content-Type application/json
- ✅ corps conforme au schéma du contrat
- ✅ en-tête ETag déclaré, présent et conforme
- ✅ en-tête X-Correlation-Id déclaré, présent et conforme
- ✅ ASSIGNED, T01, priorité HIGH, révision 4

**Effet persistant attendu** : événements r3 UPDATED et r4 ASSIGNED, aucun pour les tentatives rejetées — ✅ vérifié

**Réaction attendue du Front-End** : Sur 412 : bandeau « modifiée entre-temps », saisie conservée, relecture affichée côte à côte, renvoi uniquement après confirmation (pas de répétition aveugle).

## S12 — Continuité v1 : Portail et Export BI sécurisés (N01)

- **Catégorie** : Continuité v1
- **Opération(s)** : routes v1 /api/* (adaptateur)
- **Exigences / incidents** : N01, P09, R07 ; INC-03, INC-06
- **Décision(s)** : ADR-3 (voir Decisions_Techniques.md)
- **Préconditions** : Phase 2 du plan de migration : Console Ops et Terrain sont passés en v2.

### Étape 1 — BI lit la liste v1 ouverte : ✅ conforme

Requête :

```http
GET /api/interventions?state=open&page=0&size=20 HTTP/1.1
Host: api.atlas.invalid
Authorization: Bearer DEMO-BI01-C01
```

Réponse obtenue :

```http
HTTP/1.1 200
Content-Type: application/json
X-Correlation-Id: corr-0001

{
  "data": [
    {
      "id": "I102",
      "title": "Éclairage couloir étage",
      "status": "NEW",
      "statusDetail": "NEW"
    },
    {
      "id": "I101",
      "title": "Climatisation salle réunion",
      "status": "ASSIGNED",
      "statusDetail": "ASSIGNED"
    },
    {
      "id": "I100",
      "title": "Porte bloquée accueil",
      "status": "NEW",
      "statusDetail": "NEW"
    }
  ],
  "currentPage": 1,
  "total": 3
}
```

Vérifications :

- ✅ statut 200
- ✅ enveloppe v1 {data, currentPage, total}, 3 lignes C01 ouvertes
- ✅ aucune ligne C02

### Étape 2 — Lina lit I200 via v1 avec X-Tenant: C02 : ✅ conforme

Requête :

```http
GET /api/intervention/I200 HTTP/1.1
Host: api.atlas.invalid
Authorization: Bearer DEMO-U01-C01
X-Tenant: C02
```

Réponse obtenue :

```http
HTTP/1.1 200
Content-Type: application/json
X-Correlation-Id: corr-0002

{
  "success": false,
  "error": "not_found"
}
```

Vérifications :

- ✅ statut 200
- ✅ format v1 « not_found », identique à une absence

### Étape 3 — BI lit l'historique v1 : ✅ conforme

Requête :

```http
GET /api/interventions/I101/history HTTP/1.1
Host: api.atlas.invalid
Authorization: Bearer DEMO-BI01-C01
```

Réponse obtenue :

```http
HTTP/1.1 200
Content-Type: application/json
X-Correlation-Id: corr-0003

[
  {
    "actorId": "U01",
    "kind": "CREATED",
    "at": "2026-10-20T08:00:00Z"
  },
  {
    "actorId": "U02",
    "kind": "ASSIGNED",
    "at": "2026-10-21T09:00:00Z"
  }
]
```

Vérifications :

- ✅ statut 200
- ✅ tableau [{actorId, kind, at}] ordonné

### Étape 4 — Liste v1 vide : comportement v1 conservé : ✅ conforme

Requête :

```http
GET /api/interventions?state=open&site=S03 HTTP/1.1
Host: api.atlas.invalid
Authorization: Bearer DEMO-U02-C01
```

Réponse obtenue :

```http
HTTP/1.1 404
Content-Type: application/json
X-Correlation-Id: corr-0004

{
  "success": false,
  "error": "no_results"
}
```

Vérifications :

- ✅ statut 404
- ✅ {success:false, error:no_results}

### Étape 5 — Ancien lien d'affectation GET : ✅ conforme

Requête :

```http
GET /api/assign?id=I100&tech=T01 HTTP/1.1
Host: api.atlas.invalid
Authorization: Bearer DEMO-U02-C01
```

Réponse obtenue :

```http
HTTP/1.1 410
Content-Type: application/json
X-Correlation-Id: corr-0005

{
  "success": false,
  "error": "gone",
  "see": "/v2/interventions/{id}/assignment"
}
```

Vérifications :

- ✅ statut 410
- ✅ aucune mutation

### Étape 6 — Annulation v2 de I102 puis lecture v1 : ✅ conforme

Requête :

```http
POST /v2/interventions/I102/transitions HTTP/1.1
Host: api.atlas.invalid
Authorization: Bearer DEMO-U02-C01
Content-Type: application/json
If-Match: "rev-1"

{"to": "CANCELLED"}
```

Réponse obtenue :

```http
HTTP/1.1 200
Content-Type: application/json
ETag: "rev-2"
X-Correlation-Id: corr-0006

{
  "id": "I102",
  "tenantId": "C01",
  "siteId": "S02",
  "title": "Éclairage couloir étage",
  "priority": "LOW",
  "status": "CANCELLED",
  "technicianId": null,
  "createdAt": "2026-10-20T08:00:00Z",
  "updatedAt": "2026-10-27T09:00:01Z",
  "createdBy": "U02",
  "revision": 2
}
```

Vérifications :

- ✅ statut 200
- ✅ statut 200 documenté pour transitionIntervention
- ✅ Content-Type application/json
- ✅ corps conforme au schéma du contrat
- ✅ en-tête ETag déclaré, présent et conforme
- ✅ en-tête X-Correlation-Id déclaré, présent et conforme

### Étape 7 — Lecture v1 de I102 annulée : ✅ conforme

Requête :

```http
GET /api/intervention/I102 HTTP/1.1
Host: api.atlas.invalid
Authorization: Bearer DEMO-BI01-C01
```

Réponse obtenue :

```http
HTTP/1.1 200
Content-Type: application/json
X-Correlation-Id: corr-0007

{
  "id": "I102",
  "title": "Éclairage couloir étage",
  "status": "CLOSED",
  "statusDetail": "CANCELLED",
  "tenantId": "C01",
  "siteId": "S02",
  "priority": "LOW",
  "technicianId": null,
  "createdAt": "2026-10-20T08:00:00Z",
  "updatedAt": "2026-10-27T09:00:01Z",
  "revision": 2
}
```

Vérifications :

- ✅ statut 200
- ✅ status v1 CLOSED, détail CANCELLED conservé

### Étape 8 — Création v1 par le Portail : ✅ conforme

Requête :

```http
POST /api/interventions HTTP/1.1
Host: api.atlas.invalid
Authorization: Bearer DEMO-U01-C01
Content-Type: application/json

{"title": "Porte bloquée", "siteId": "S01", "priority": "HIGH"}
```

Réponse obtenue :

```http
HTTP/1.1 200
Content-Type: application/json
X-Correlation-Id: corr-0008

{
  "success": true,
  "intervention_id": "I104",
  "id": "I104"
}
```

Vérifications :

- ✅ statut 200
- ✅ format v1 conservé + id additionnel

### Étape 9 — Création v1 invalide : règle R02 appliquée aussi en v1 : ✅ conforme

Requête :

```http
POST /api/interventions HTTP/1.1
Host: api.atlas.invalid
Authorization: Bearer DEMO-U01-C01
Content-Type: application/json

{"title": "abc", "siteId": "S01"}
```

Réponse obtenue :

```http
HTTP/1.1 200
Content-Type: application/json
X-Correlation-Id: corr-0009

{
  "success": false,
  "error": "validation_failed"
}
```

Vérifications :

- ✅ statut 200
- ✅ format d'erreur v1

**Effet persistant attendu** : I102 CANCELLED et I104 créée ; aucune mutation par l'ancien lien GET — ✅ vérifié

**Réaction attendue du Front-End** : Portail 1.8 et Export BI inchangés (formats observés) ; seules les lectures hors tenant et l'ancien lien d'affectation cessent, annoncés en amont.

## S13 — Affectation : référentiel, atomicité, idempotence (INC-03, INC-07, INC-10)

- **Catégorie** : Complément — affectation
- **Opération(s)** : assignIntervention, listInterventionEvents
- **Exigences / incidents** : R05, R09, R12 ; INC-03, INC-07, INC-10, U2
- **Décision(s)** : ADR-2, ADR-4 (voir Decisions_Techniques.md)
- **Préconditions** : I100 NEW rév. 2. T01 actif C01, T02 actif C02, T03 inactif C01.

### Étape 1 — T02 d'un autre tenant : ✅ conforme

Requête :

```http
PUT /v2/interventions/I100/assignment HTTP/1.1
Host: api.atlas.invalid
Authorization: Bearer DEMO-U02-C01
Content-Type: application/json
If-Match: "rev-2"

{"technicianId": "T02"}
```

Réponse obtenue :

```http
HTTP/1.1 422
Content-Type: application/problem+json
X-Correlation-Id: corr-0001

{
  "type": "https://api.atlas.invalid/problems/validation-failed",
  "title": "Données invalides",
  "status": 422,
  "code": "VALIDATION_FAILED",
  "correlationId": "corr-0001",
  "errors": [
    {
      "field": "technicianId",
      "code": "TECHNICIAN_NOT_FOUND",
      "message": "Technicien inconnu dans votre organisation."
    }
  ]
}
```

Vérifications :

- ✅ statut 422
- ✅ code VALIDATION_FAILED
- ✅ erreur de champ technicianId=TECHNICIAN_NOT_FOUND
- ✅ statut 422 documenté pour assignIntervention
- ✅ Content-Type application/problem+json
- ✅ corps conforme au schéma du contrat
- ✅ en-tête X-Correlation-Id déclaré, présent et conforme

### Étape 2 — T03 inactif : ✅ conforme

Requête :

```http
PUT /v2/interventions/I100/assignment HTTP/1.1
Host: api.atlas.invalid
Authorization: Bearer DEMO-U02-C01
Content-Type: application/json
If-Match: "rev-2"

{"technicianId": "T03"}
```

Réponse obtenue :

```http
HTTP/1.1 422
Content-Type: application/problem+json
X-Correlation-Id: corr-0002

{
  "type": "https://api.atlas.invalid/problems/validation-failed",
  "title": "Données invalides",
  "status": 422,
  "code": "VALIDATION_FAILED",
  "correlationId": "corr-0002",
  "errors": [
    {
      "field": "technicianId",
      "code": "TECHNICIAN_INACTIVE",
      "message": "Technicien inactif : affectation impossible."
    }
  ]
}
```

Vérifications :

- ✅ statut 422
- ✅ code VALIDATION_FAILED
- ✅ erreur de champ technicianId=TECHNICIAN_INACTIVE
- ✅ statut 422 documenté pour assignIntervention
- ✅ Content-Type application/problem+json
- ✅ corps conforme au schéma du contrat
- ✅ en-tête X-Correlation-Id déclaré, présent et conforme

### Étape 3 — T01 actif : ✅ conforme

Requête :

```http
PUT /v2/interventions/I100/assignment HTTP/1.1
Host: api.atlas.invalid
Authorization: Bearer DEMO-U02-C01
Content-Type: application/json
If-Match: "rev-2"

{"technicianId": "T01"}
```

Réponse obtenue :

```http
HTTP/1.1 200
Content-Type: application/json
ETag: "rev-3"
X-Correlation-Id: corr-0003

{
  "id": "I100",
  "tenantId": "C01",
  "siteId": "S01",
  "title": "Porte bloquée accueil",
  "priority": "NORMAL",
  "status": "ASSIGNED",
  "technicianId": "T01",
  "createdAt": "2026-10-20T08:00:00Z",
  "updatedAt": "2026-10-27T09:00:01Z",
  "createdBy": "U02",
  "revision": 3
}
```

Vérifications :

- ✅ statut 200
- ✅ statut 200 documenté pour assignIntervention
- ✅ Content-Type application/json
- ✅ corps conforme au schéma du contrat
- ✅ en-tête ETag déclaré, présent et conforme
- ✅ en-tête X-Correlation-Id déclaré, présent et conforme
- ✅ corps identique à Exemples_JSON/affectation-200.json

### Étape 4 — Répétition (rafraîchissement, robot) : ✅ conforme

Requête :

```http
PUT /v2/interventions/I100/assignment HTTP/1.1
Host: api.atlas.invalid
Authorization: Bearer DEMO-U02-C01
Content-Type: application/json
If-Match: "rev-3"

{"technicianId": "T01"}
```

Réponse obtenue :

```http
HTTP/1.1 200
Content-Type: application/json
ETag: "rev-3"
X-Correlation-Id: corr-0004

{
  "id": "I100",
  "tenantId": "C01",
  "siteId": "S01",
  "title": "Porte bloquée accueil",
  "priority": "NORMAL",
  "status": "ASSIGNED",
  "technicianId": "T01",
  "createdAt": "2026-10-20T08:00:00Z",
  "updatedAt": "2026-10-27T09:00:01Z",
  "createdBy": "U02",
  "revision": 3
}
```

Vérifications :

- ✅ statut 200
- ✅ statut 200 documenté pour assignIntervention
- ✅ Content-Type application/json
- ✅ corps conforme au schéma du contrat
- ✅ en-tête ETag déclaré, présent et conforme
- ✅ en-tête X-Correlation-Id déclaré, présent et conforme
- ✅ révision toujours 3

### Étape 5 — Historique : ✅ conforme

Requête :

```http
GET /v2/interventions/I100/events HTTP/1.1
Host: api.atlas.invalid
Authorization: Bearer DEMO-U02-C01
```

Réponse obtenue :

```http
HTTP/1.1 200
Content-Type: application/json
X-Correlation-Id: corr-0005

{
  "items": [
    {
      "eventId": "E100-1",
      "interventionId": "I100",
      "revision": 1,
      "type": "CREATED",
      "at": "2026-10-20T08:00:00Z",
      "actor": {
        "userId": "U02",
        "role": "planner"
      },
      "changes": [
        {
          "field": "status",
          "from": null,
          "to": "NEW"
        },
        {
          "field": "priority",
          "from": null,
          "to": "NORMAL"
        },
        {
          "field": "title"
        }
      ]
    },
    {
      "eventId": "E100-2",
      "interventionId": "I100",
      "revision": 2,
      "type": "UPDATED",
      "at": "2026-10-20T08:00:00Z",
      "actor": {
        "userId": "U02",
        "role": "planner"
      },
      "changes": [
        {
          "field": "title"
        }
      ]
    },
    {
      "eventId": "E100-3",
      "interventionId": "I100",
      "revision": 3,
      "type": "ASSIGNED",
      "at": "2026-10-27T09:00:01Z",
      "actor": {
        "userId": "U02",
        "role": "planner"
      },
      "changes": [
        {
          "field": "technicianId",
          "from": null,
          "to": "T01"
        },
        {
          "field": "status",
          "from": "NEW",
          "to": "ASSIGNED"
        }
      ]
    }
  ],
  "page": {
    "limit": 50,
    "hasNext": false,
    "nextCursor": null,
    "totalItems": 3
  }
}
```

Vérifications :

- ✅ statut 200
- ✅ statut 200 documenté pour listInterventionEvents
- ✅ Content-Type application/json
- ✅ corps conforme au schéma du contrat
- ✅ en-tête X-Correlation-Id déclaré, présent et conforme
- ✅ corps identique à Exemples_JSON/historique-200.json
- ✅ un seul événement ASSIGNED décrivant technicien ET statut

**Effet persistant attendu** : une affectation, un événement ; rien pour T02, T03 et la répétition — ✅ vérifié

**Réaction attendue du Front-End** : Liste de techniciens issue du référentiel du tenant ; sur 422 TECHNICIAN_*, message sous le sélecteur ; sur 200, état ASSIGNED affiché depuis la réponse.

## S14 — Terrain : cycle du technicien (U3)

- **Catégorie** : Complément — transitions
- **Opération(s)** : listInterventions, transitionIntervention
- **Exigences / incidents** : R04, R06 ; U3, INC-04
- **Décision(s)** : ADR-2 (voir Decisions_Techniques.md)
- **Préconditions** : Samir (U03, T01). I101 ASSIGNED à T01 (rév. 2), I103 DONE à T01.

### Étape 1 — Samir liste ses interventions : ✅ conforme

Requête :

```http
GET /v2/interventions HTTP/1.1
Host: api.atlas.invalid
Authorization: Bearer DEMO-U03-C01
```

Réponse obtenue :

```http
HTTP/1.1 200
Content-Type: application/json
X-Correlation-Id: corr-0001

{
  "items": [
    {
      "id": "I101",
      "tenantId": "C01",
      "siteId": "S01",
      "title": "Climatisation salle réunion",
      "priority": "NORMAL",
      "status": "ASSIGNED",
      "technicianId": "T01",
      "createdAt": "2026-10-20T08:00:00Z",
      "updatedAt": "2026-10-21T09:00:00Z",
      "createdBy": "U01",
      "revision": 2
    },
    {
      "id": "I103",
      "tenantId": "C01",
      "siteId": "S01",
      "title": "Serrure salle serveur",
      "priority": "HIGH",
      "status": "DONE",
      "technicianId": "T01",
      "createdAt": "2026-10-19T08:00:00Z",
      "updatedAt": "2026-10-21T11:00:00Z",
      "createdBy": "U01",
      "revision": 3
    }
  ],
  "page": {
    "limit": 20,
    "hasNext": false,
    "nextCursor": null,
    "totalItems": 2
  }
}
```

Vérifications :

- ✅ statut 200
- ✅ statut 200 documenté pour listInterventions
- ✅ Content-Type application/json
- ✅ corps conforme au schéma du contrat
- ✅ en-tête X-Correlation-Id déclaré, présent et conforme
- ✅ uniquement I101 et I103 (ses affectations)

### Étape 2 — Démarrer I101 : ✅ conforme

Requête :

```http
POST /v2/interventions/I101/transitions HTTP/1.1
Host: api.atlas.invalid
Authorization: Bearer DEMO-U03-C01
Content-Type: application/json
If-Match: "rev-2"

{"to": "IN_PROGRESS"}
```

Réponse obtenue :

```http
HTTP/1.1 200
Content-Type: application/json
ETag: "rev-3"
X-Correlation-Id: corr-0002

{
  "id": "I101",
  "tenantId": "C01",
  "siteId": "S01",
  "title": "Climatisation salle réunion",
  "priority": "NORMAL",
  "status": "IN_PROGRESS",
  "technicianId": "T01",
  "createdAt": "2026-10-20T08:00:00Z",
  "updatedAt": "2026-10-27T09:00:01Z",
  "createdBy": "U01",
  "revision": 3
}
```

Vérifications :

- ✅ statut 200
- ✅ statut 200 documenté pour transitionIntervention
- ✅ Content-Type application/json
- ✅ corps conforme au schéma du contrat
- ✅ en-tête ETag déclaré, présent et conforme
- ✅ en-tête X-Correlation-Id déclaré, présent et conforme
- ✅ corps identique à Exemples_JSON/transition-200.json

### Étape 3 — Terminer I101 : ✅ conforme

Requête :

```http
POST /v2/interventions/I101/transitions HTTP/1.1
Host: api.atlas.invalid
Authorization: Bearer DEMO-U03-C01
Content-Type: application/json
If-Match: "rev-3"

{"to": "DONE"}
```

Réponse obtenue :

```http
HTTP/1.1 200
Content-Type: application/json
ETag: "rev-4"
X-Correlation-Id: corr-0003

{
  "id": "I101",
  "tenantId": "C01",
  "siteId": "S01",
  "title": "Climatisation salle réunion",
  "priority": "NORMAL",
  "status": "DONE",
  "technicianId": "T01",
  "createdAt": "2026-10-20T08:00:00Z",
  "updatedAt": "2026-10-27T09:00:02Z",
  "createdBy": "U01",
  "revision": 4
}
```

Vérifications :

- ✅ statut 200
- ✅ statut 200 documenté pour transitionIntervention
- ✅ Content-Type application/json
- ✅ corps conforme au schéma du contrat
- ✅ en-tête ETag déclaré, présent et conforme
- ✅ en-tête X-Correlation-Id déclaré, présent et conforme
- ✅ DONE rév. 4

### Étape 4 — Terminer à nouveau : ✅ conforme

Requête :

```http
POST /v2/interventions/I101/transitions HTTP/1.1
Host: api.atlas.invalid
Authorization: Bearer DEMO-U03-C01
Content-Type: application/json
If-Match: "rev-4"

{"to": "DONE"}
```

Réponse obtenue :

```http
HTTP/1.1 409
Content-Type: application/problem+json
X-Correlation-Id: corr-0004

{
  "type": "https://api.atlas.invalid/problems/invalid-transition",
  "title": "Transition interdite",
  "status": 409,
  "code": "INVALID_TRANSITION",
  "correlationId": "corr-0004",
  "detail": "DONE → DONE n'est pas autorisé.",
  "currentStatus": "DONE"
}
```

Vérifications :

- ✅ statut 409
- ✅ code INVALID_TRANSITION
- ✅ statut 409 documenté pour transitionIntervention
- ✅ Content-Type application/problem+json
- ✅ corps conforme au schéma du contrat
- ✅ en-tête X-Correlation-Id déclaré, présent et conforme

### Étape 5 — Le technicien annule : ✅ conforme

Requête :

```http
POST /v2/interventions/I101/transitions HTTP/1.1
Host: api.atlas.invalid
Authorization: Bearer DEMO-U03-C01
Content-Type: application/json
If-Match: "rev-4"

{"to": "CANCELLED"}
```

Réponse obtenue :

```http
HTTP/1.1 403
Content-Type: application/problem+json
X-Correlation-Id: corr-0005

{
  "type": "https://api.atlas.invalid/problems/forbidden",
  "title": "Action non autorisée",
  "status": 403,
  "code": "FORBIDDEN",
  "correlationId": "corr-0005",
  "detail": "Le rôle technician ne peut pas demander CANCELLED."
}
```

Vérifications :

- ✅ statut 403
- ✅ code FORBIDDEN
- ✅ statut 403 documenté pour transitionIntervention
- ✅ Content-Type application/problem+json
- ✅ corps conforme au schéma du contrat
- ✅ en-tête X-Correlation-Id déclaré, présent et conforme

**Effet persistant attendu** : deux événements STATUS_CHANGED — ✅ vérifié

**Réaction attendue du Front-End** : Boutons proposés d'après le statut reçu ; hors ligne, l'intention est mise en file locale et affichée « en attente » jusqu'au 200 du serveur.

## S15 — Historique : lecture, pagination et droits (U4)

- **Catégorie** : Complément — historique
- **Opération(s)** : listInterventionEvents
- **Exigences / incidents** : R09, R06, N03 ; U4
- **Décision(s)** : ADR-5 (voir Decisions_Techniques.md)
- **Préconditions** : I103 : 3 événements. bi-c01 reporter. Samir affecté à I103.

### Étape 1 — Reporter, limit=2 : ✅ conforme

Requête :

```http
GET /v2/interventions/I103/events?limit=2 HTTP/1.1
Host: api.atlas.invalid
Authorization: Bearer DEMO-BI01-C01
```

Réponse obtenue :

```http
HTTP/1.1 200
Content-Type: application/json
X-Correlation-Id: corr-0001

{
  "items": [
    {
      "eventId": "E103-1",
      "interventionId": "I103",
      "revision": 1,
      "type": "CREATED",
      "at": "2026-10-19T08:00:00Z",
      "actor": {
        "userId": "U01",
        "role": "requester"
      },
      "changes": [
        {
          "field": "status",
          "from": null,
          "to": "NEW"
        },
        {
          "field": "priority",
          "from": null,
          "to": "HIGH"
        },
        {
          "field": "title"
        }
      ]
    },
    {
      "eventId": "E103-2",
      "interventionId": "I103",
      "revision": 2,
      "type": "ASSIGNED",
      "at": "2026-10-20T10:00:00Z",
      "actor": {
        "userId": "U02",
        "role": "planner"
      },
      "changes": [
        {
          "field": "technicianId",
          "from": null,
          "to": "T01"
        },
        {
          "field": "status",
          "from": "NEW",
          "to": "ASSIGNED"
        }
      ]
    }
  ],
  "page": {
    "limit": 2,
    "hasNext": true,
    "nextCursor": "eyJrIjpbMiwiIl0sImYiOnsiaW50ZXJ2ZW50aW9uSWQiOiJJMTAzIn19",
    "totalItems": 3
  }
}
```

Vérifications :

- ✅ statut 200
- ✅ statut 200 documenté pour listInterventionEvents
- ✅ Content-Type application/json
- ✅ corps conforme au schéma du contrat
- ✅ en-tête X-Correlation-Id déclaré, présent et conforme
- ✅ révisions 1 et 2, hasNext

### Étape 2 — Page suivante : ✅ conforme

Requête :

```http
GET /v2/interventions/I103/events?limit=2&cursor=eyJrIjpbMiwiIl0sImYiOnsiaW50ZXJ2ZW50aW9uSWQiOiJJMTAzIn19 HTTP/1.1
Host: api.atlas.invalid
Authorization: Bearer DEMO-BI01-C01
```

Réponse obtenue :

```http
HTTP/1.1 200
Content-Type: application/json
X-Correlation-Id: corr-0002

{
  "items": [
    {
      "eventId": "E103-3",
      "interventionId": "I103",
      "revision": 3,
      "type": "STATUS_CHANGED",
      "at": "2026-10-21T11:00:00Z",
      "actor": {
        "userId": "U03",
        "role": "technician"
      },
      "changes": [
        {
          "field": "status",
          "from": "ASSIGNED",
          "to": "DONE"
        }
      ]
    }
  ],
  "page": {
    "limit": 2,
    "hasNext": false,
    "nextCursor": null,
    "totalItems": 3
  }
}
```

Vérifications :

- ✅ statut 200
- ✅ statut 200 documenté pour listInterventionEvents
- ✅ Content-Type application/json
- ✅ corps conforme au schéma du contrat
- ✅ en-tête X-Correlation-Id déclaré, présent et conforme
- ✅ révision 3 seule, fin

### Étape 3 — Technicien affecté : ✅ conforme

Requête :

```http
GET /v2/interventions/I103/events HTTP/1.1
Host: api.atlas.invalid
Authorization: Bearer DEMO-U03-C01
```

Réponse obtenue :

```http
HTTP/1.1 200
Content-Type: application/json
X-Correlation-Id: corr-0003

{
  "items": [
    {
      "eventId": "E103-1",
      "interventionId": "I103",
      "revision": 1,
      "type": "CREATED",
      "at": "2026-10-19T08:00:00Z",
      "actor": {
        "userId": "U01",
        "role": "requester"
      },
      "changes": [
        {
          "field": "status",
          "from": null,
          "to": "NEW"
        },
        {
          "field": "priority",
          "from": null,
          "to": "HIGH"
        },
        {
          "field": "title"
        }
      ]
    },
    {
      "eventId": "E103-2",
      "interventionId": "I103",
      "revision": 2,
      "type": "ASSIGNED",
      "at": "2026-10-20T10:00:00Z",
      "actor": {
        "userId": "U02",
        "role": "planner"
      },
      "changes": [
        {
          "field": "technicianId",
          "from": null,
          "to": "T01"
        },
        {
          "field": "status",
          "from": "NEW",
          "to": "ASSIGNED"
        }
      ]
    },
    {
      "eventId": "E103-3",
      "interventionId": "I103",
      "revision": 3,
      "type": "STATUS_CHANGED",
      "at": "2026-10-21T11:00:00Z",
      "actor": {
        "userId": "U03",
        "role": "technician"
      },
      "changes": [
        {
          "field": "status",
          "from": "ASSIGNED",
          "to": "DONE"
        }
      ]
    }
  ],
  "page": {
    "limit": 50,
    "hasNext": false,
    "nextCursor": null,
    "totalItems": 3
  }
}
```

Vérifications :

- ✅ statut 200
- ✅ statut 200 documenté pour listInterventionEvents
- ✅ Content-Type application/json
- ✅ corps conforme au schéma du contrat
- ✅ en-tête X-Correlation-Id déclaré, présent et conforme
- ✅ titre jamais recopié

### Étape 4 — limit=500 : ✅ conforme

Requête :

```http
GET /v2/interventions/I103/events?limit=500 HTTP/1.1
Host: api.atlas.invalid
Authorization: Bearer DEMO-BI01-C01
```

Réponse obtenue :

```http
HTTP/1.1 400
Content-Type: application/problem+json
X-Correlation-Id: corr-0004

{
  "type": "https://api.atlas.invalid/problems/invalid-parameter",
  "title": "Paramètre invalide",
  "status": 400,
  "code": "INVALID_PARAMETER",
  "correlationId": "corr-0004",
  "detail": "limit doit être compris entre 1 et 100.",
  "errors": [
    {
      "field": "limit",
      "code": "OUT_OF_RANGE",
      "message": "Valeur entre 1 et 100."
    }
  ]
}
```

Vérifications :

- ✅ statut 400
- ✅ code INVALID_PARAMETER
- ✅ statut 400 documenté pour listInterventionEvents
- ✅ Content-Type application/problem+json
- ✅ corps conforme au schéma du contrat
- ✅ en-tête X-Correlation-Id déclaré, présent et conforme

**Effet persistant attendu** : aucun — ✅ vérifié (état comparé avant/après)

**Réaction attendue du Front-End** : Chronologie triée par révision, heures converties dans le fuseau de l'utilisateur à partir des instants UTC.

## S16 — Reprise après coupure réseau : clé d'idempotence (U1, approfondissement 1)

- **Catégorie** : Complément — idempotence
- **Opération(s)** : createIntervention
- **Exigences / incidents** : U1 (coupure avant réponse)
- **Décision(s)** : ADR-2 (voir Decisions_Techniques.md)
- **Préconditions** : Lina a envoyé une création dont la réponse a été perdue.

### Étape 1 — Premier envoi : ✅ conforme

Requête :

```http
POST /v2/interventions HTTP/1.1
Host: api.atlas.invalid
Authorization: Bearer DEMO-U01-C01
Content-Type: application/json
Idempotency-Key: lina-7f3c2a91

{"siteId": "S01", "title": "Porte bloquée"}
```

Réponse obtenue :

```http
HTTP/1.1 201
Content-Type: application/json
Location: /v2/interventions/I104
ETag: "rev-1"
X-Correlation-Id: corr-0001

{
  "id": "I104",
  "tenantId": "C01",
  "siteId": "S01",
  "title": "Porte bloquée",
  "priority": "NORMAL",
  "status": "NEW",
  "technicianId": null,
  "createdAt": "2026-10-27T09:00:01Z",
  "updatedAt": "2026-10-27T09:00:01Z",
  "createdBy": "U01",
  "revision": 1
}
```

Vérifications :

- ✅ statut 201
- ✅ statut 201 documenté pour createIntervention
- ✅ Content-Type application/json
- ✅ corps conforme au schéma du contrat
- ✅ en-tête Location déclaré, présent et conforme
- ✅ en-tête ETag déclaré, présent et conforme
- ✅ en-tête X-Correlation-Id déclaré, présent et conforme

### Étape 2 — Renvoi identique après coupure : ✅ conforme

Requête :

```http
POST /v2/interventions HTTP/1.1
Host: api.atlas.invalid
Authorization: Bearer DEMO-U01-C01
Content-Type: application/json
Idempotency-Key: lina-7f3c2a91

{"siteId": "S01", "title": "Porte bloquée"}
```

Réponse obtenue :

```http
HTTP/1.1 201
Content-Type: application/json
Location: /v2/interventions/I104
ETag: "rev-1"
Idempotent-Replayed: true
X-Correlation-Id: corr-0002

{
  "id": "I104",
  "tenantId": "C01",
  "siteId": "S01",
  "title": "Porte bloquée",
  "priority": "NORMAL",
  "status": "NEW",
  "technicianId": null,
  "createdAt": "2026-10-27T09:00:01Z",
  "updatedAt": "2026-10-27T09:00:01Z",
  "createdBy": "U01",
  "revision": 1
}
```

Vérifications :

- ✅ statut 201
- ✅ statut 201 documenté pour createIntervention
- ✅ Content-Type application/json
- ✅ corps conforme au schéma du contrat
- ✅ en-tête Location déclaré, présent et conforme
- ✅ en-tête ETag déclaré, présent et conforme
- ✅ en-tête X-Correlation-Id déclaré, présent et conforme
- ✅ en-tête Idempotent-Replayed déclaré, présent et conforme
- ✅ même id I104 et Idempotent-Replayed: true

### Étape 3 — Même clé, autre contenu : ✅ conforme

Requête :

```http
POST /v2/interventions HTTP/1.1
Host: api.atlas.invalid
Authorization: Bearer DEMO-U01-C01
Content-Type: application/json
Idempotency-Key: lina-7f3c2a91

{"siteId": "S02", "title": "Autre demande"}
```

Réponse obtenue :

```http
HTTP/1.1 422
Content-Type: application/problem+json
X-Correlation-Id: corr-0003

{
  "type": "https://api.atlas.invalid/problems/idempotency-key-reused",
  "title": "Clé d'idempotence déjà utilisée",
  "status": 422,
  "code": "IDEMPOTENCY_KEY_REUSED",
  "correlationId": "corr-0003",
  "detail": "Cette clé a servi pour un autre contenu."
}
```

Vérifications :

- ✅ statut 422
- ✅ code IDEMPOTENCY_KEY_REUSED
- ✅ statut 422 documenté pour createIntervention
- ✅ Content-Type application/problem+json
- ✅ corps conforme au schéma du contrat
- ✅ en-tête X-Correlation-Id déclaré, présent et conforme

**Effet persistant attendu** : une seule création — ✅ vérifié

**Réaction attendue du Front-End** : Sur coupure : « Envoi incertain — vérification » ; renvoi automatique avec la même clé, jamais une nouvelle clé pour la même saisie.

## S17 — Annulation par la demandeuse puis tentative d'affectation

- **Catégorie** : Complément — annulation
- **Opération(s)** : transitionIntervention, assignIntervention
- **Exigences / incidents** : R04, R06 ; P08 M4 (« l'annulation n'est pas une fin de travail »)
- **Décision(s)** : ADR-2, ADR-3 (voir Decisions_Techniques.md)
- **Préconditions** : I100 NEW rév. 2.

### Étape 1 — Lina annule I100 : ✅ conforme

Requête :

```http
POST /v2/interventions/I100/transitions HTTP/1.1
Host: api.atlas.invalid
Authorization: Bearer DEMO-U01-C01
Content-Type: application/json
If-Match: "rev-2"

{"to": "CANCELLED"}
```

Réponse obtenue :

```http
HTTP/1.1 200
Content-Type: application/json
ETag: "rev-3"
X-Correlation-Id: corr-0001

{
  "id": "I100",
  "tenantId": "C01",
  "siteId": "S01",
  "title": "Porte bloquée accueil",
  "priority": "NORMAL",
  "status": "CANCELLED",
  "technicianId": null,
  "createdAt": "2026-10-20T08:00:00Z",
  "updatedAt": "2026-10-27T09:00:01Z",
  "createdBy": "U02",
  "revision": 3
}
```

Vérifications :

- ✅ statut 200
- ✅ statut 200 documenté pour transitionIntervention
- ✅ Content-Type application/json
- ✅ corps conforme au schéma du contrat
- ✅ en-tête ETag déclaré, présent et conforme
- ✅ en-tête X-Correlation-Id déclaré, présent et conforme
- ✅ CANCELLED, distinct de DONE

### Étape 2 — Nora affecte ensuite : ✅ conforme

Requête :

```http
PUT /v2/interventions/I100/assignment HTTP/1.1
Host: api.atlas.invalid
Authorization: Bearer DEMO-U02-C01
Content-Type: application/json
If-Match: "rev-3"

{"technicianId": "T01"}
```

Réponse obtenue :

```http
HTTP/1.1 409
Content-Type: application/problem+json
X-Correlation-Id: corr-0002

{
  "type": "https://api.atlas.invalid/problems/invalid-state",
  "title": "Affectation impossible dans cet état",
  "status": 409,
  "code": "INVALID_STATE",
  "correlationId": "corr-0002",
  "detail": "Une intervention CANCELLED ne peut plus être affectée.",
  "currentStatus": "CANCELLED"
}
```

Vérifications :

- ✅ statut 409
- ✅ code INVALID_STATE
- ✅ statut 409 documenté pour assignIntervention
- ✅ Content-Type application/problem+json
- ✅ corps conforme au schéma du contrat
- ✅ en-tête X-Correlation-Id déclaré, présent et conforme

**Effet persistant attendu** : un événement STATUS_CHANGED — ✅ vérifié

**Réaction attendue du Front-End** : Intervention affichée « Annulée » (libellé distinct de « Terminée ») ; actions de planification retirées.

## S18 — Journaux techniques sans secret ni texte libre (N03, P09)

- **Catégorie** : Complément — observabilité
- **Opération(s)** : createIntervention
- **Exigences / incidents** : N03, P09 Observabilité ; INC-10
- **Décision(s)** : ADR-1 (voir Decisions_Techniques.md)
- **Préconditions** : Journal technique simulé vide.

### Étape 1 — Création : ✅ conforme

Requête :

```http
POST /v2/interventions HTTP/1.1
Host: api.atlas.invalid
Authorization: Bearer DEMO-U01-C01
Content-Type: application/json

{"siteId": "S01", "title": "Serrure bureau direction"}
```

Réponse obtenue :

```http
HTTP/1.1 201
Content-Type: application/json
Location: /v2/interventions/I104
ETag: "rev-1"
X-Correlation-Id: corr-0001

{
  "id": "I104",
  "tenantId": "C01",
  "siteId": "S01",
  "title": "Serrure bureau direction",
  "priority": "NORMAL",
  "status": "NEW",
  "technicianId": null,
  "createdAt": "2026-10-27T09:00:01Z",
  "updatedAt": "2026-10-27T09:00:01Z",
  "createdBy": "U01",
  "revision": 1
}
```

Vérifications :

- ✅ statut 201
- ✅ statut 201 documenté pour createIntervention
- ✅ Content-Type application/json
- ✅ corps conforme au schéma du contrat
- ✅ en-tête Location déclaré, présent et conforme
- ✅ en-tête ETag déclaré, présent et conforme
- ✅ en-tête X-Correlation-Id déclaré, présent et conforme
- ✅ journal : correlationId, opération, statut ; ni jeton ni titre

**Effet persistant attendu** : +1 intervention — ✅ vérifié

**Réaction attendue du Front-End** : En cas d'erreur, l'écran affiche le correlationId à transmettre au support ; jamais le jeton.
