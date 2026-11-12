# Décisions techniques (ADR)

Auteur : Paul Mehr. Statut de toutes les décisions : **proposée à ATLAS**, à confirmer par la
direction des opérations (P01). Chaque décision renvoie aux preuves (pièces P0x, T0x, incidents)
et aux scénarios qui la vérifient (`Tests_et_Validations/SCENARIOS.md`).

| ADR | Sujet | Exigences | Scénarios |
|---|---|---|---|
| ADR-1 | Frontière de confiance, identité et isolement | R03, R06, R07, R12, N03, N05 | S01, S07, S08, S09, S18 |
| ADR-2 | Conventions REST, sémantique des mutations et format d'erreur | R02, R04, R05, R09, R11, N02 | S05, S06, S10, S13, S14, S16 |
| ADR-3 | Compatibilité v1 et migration par consommateur | N01, P09 | S12 |
| ADR-4 | Concurrence optimiste par révision (ETag / If-Match) | R10, R09 | S11, S13 |
| ADR-5 | Pagination par curseur et ordre déterministe | R08, N04 | S02, S03, S04, S15 |

---

## ADR-1 — Frontière de confiance : le serveur décide, à partir de l'identité validée

**Contexte.** L'API lit le tenant dans `X-Tenant` (P05 ; `back.mjs create`). Le détail charge
par identifiant sans filtre (`back.mjs detail`), d'où INC-06 : Lina (C01) lit I200 (C02) en
changeant l'URL et `X-Tenant` (`http/isolement.http`). La configuration **publique** de la
console contient le tenant et une chaîne de connexion à une vue SQL (`config-demo.json` ;
`front.mjs fastList`). Les règles de titre et de transition sont confiées aux écrans (P05,
P08 M2). Les journaux recopient `Authorization` et les titres (P09, `back.mjs` ligne `log.info`).

**Options.**
1. Garder `X-Tenant`, mais vérifier qu'il correspond au jeton.
2. Masquer les boutons et les données côté Front (proposition de M3).
3. **Lire tenant, rôle et technicien uniquement dans le jeton validé. Faire appliquer
   par le serveur toutes les règles, la visibilité et les références. Fermer tout accès
   direct au stockage depuis le navigateur.**

**Choix.** Option 3. En complément : 404 indiscernable pour une ressource invisible,
clés étrangères composites `(tenant_id, site_id)` et `(tenant_id, technician_id)`, révocation
des identifiants de la vue SQL et retrait de `sqlView`, `tenantHeader` et `logAuthorization`
de la configuration publique. Journal technique réduit à `correlationId`, opération, statut
et durée.

**Justification vérifiable.**
- P09 : « un en-tête saisi par l'appelant n'est pas une preuve ». Option 1 garde une source
  falsifiable qui n'apporte rien quand le jeton porte déjà le tenant.
- Option 2 : un client HTTP contourne l'écran (DEMARRER.md ; M2 Élodie) et le contenu déjà
  divulgué n'est pas traité (M3 Salomé).
- Vérifications : S08 (404 identiques pour I200 et I999, PATCH et historique de I200 en 404),
  S01 (création avec `X-Tenant: C02` falsifié → rattachée à C01, invisible pour Zoé), S07,
  S09, S18. `verifier_detection.py` montre que les scénarios échouent si la visibilité ignore
  le tenant ou si la création lit `X-Tenant`.

**Conséquences.** Les écrans ne gardent que la prévalidation ergonomique (N05). Console Ops
perd sa liste rapide par SQL : elle est remplacée par la liste v2 paginée et indexée (ADR-5).
Le support identifie un échec par `correlationId`, sans jeton.

**Risques.** Un consommateur non identifié qui dépend de la lecture inter-tenant cesse de
fonctionner. C'est un **usage non autorisé** (P09 « une correction de sécurité peut rendre
indisponible un ancien usage non autorisé »), à annoncer à la direction. Autre risque : un
oubli de filtre `tenant_id` dans une nouvelle requête. Mesures : prédicat de tenant
centralisé dans la couche d'accès aux données, test S08 en non-régression, et
éventuellement une politique de sécurité de lignes PostgreSQL (RLS) en défense en profondeur.

**Critères de réexamen.** Création d'un rôle transversal légitime (support multi-tenant).
Il faudrait alors un claim et une journalisation d'accès dédiés, pas un en-tête.

---

## ADR-2 — Conventions REST : méthodes sûres, routes d'action explicites, erreurs RFC 9457

**Contexte.** L'affectation est un `GET` avec effet (P05, INC-03 : un robot de préchargement
réaffecte). `PUT /api/intervention/{id}` remplace `technicianId` absent par `null` et recopie le
statut reçu (INC-04, `back.mjs update`). Les erreurs sont tantôt du texte, tantôt
`200 {success:false}`, tantôt un 404 pour une liste vide (P06, `http/detail.http`,
`http/vide.http`). La création répond 200 + `intervention_id` alors que le wiki annonce
201 + `Location` (INC-02).

**Options pour les mutations.**
1. Un seul `PUT` de remplacement complet de la ressource.
2. Un `PATCH` générique incluant `status` et `technicianId`, contrôlé par une machine à états.
3. **Un `PATCH` limité aux champs libres (`title`, `priority`), un `PUT …/assignment` et un
   `POST …/transitions`.**

**Options pour les erreurs.** (a) Enveloppe `success:false` avec HTTP 200 ; (b) codes HTTP seuls ;
(c) **codes HTTP + `application/problem+json` (RFC 9457) + `code` stable + `errors[]` par champ
+ `correlationId`**.

**Choix.** Option 3 et option (c). En complément : 201 + `Location` + `ETag` pour la création,
200 avec la ressource à jour pour chaque mutation, 200 avec `items: []` pour une liste vide,
`Idempotency-Key` facultative pour la création.

**Justification vérifiable.**
- RFC 9110 §9.2.1 : GET est une méthode sûre, un préchargeur peut la suivre. Une action
  métier ne doit donc pas y être exposée.
- PUT est idempotent (RFC 9110 §9.2.2) : `PUT /assignment` avec le même technicien ne crée
  ni révision ni événement (S13 étape 4), ce qui règle les doubles événements d'INC-03/INC-10.
- Option 1 exige de renvoyer tous les champs : c'est exactement le mécanisme d'INC-04.
- Option 2 mélange dans une même requête des changements qui relèvent de rôles différents
  (le planner corrige la priorité, seul le technicien démarre). R11 demande de distinguer
  « conserver » et « changer » l'affectation : une route dédiée rend la distinction
  structurelle. Avec l'option 3, `technicianId` absent d'un PATCH ne peut **pas** être
  interprété comme un retrait (S06).
- Erreurs : avec l'option (a), les outils HTTP (cache, supervision, retry) voient un succès,
  et P04 demande d'expliquer comment ils décident encore correctement. L'option (b) ne dit
  pas au formulaire quel champ corriger. Avec (c), le Front choisit sa réaction sur
  `status` + `code` et marque les champs via `errors[]` (table du Catalogue §1).
- JSON mal formé (400) et règle métier (422) sont distincts : S05 étapes 4 et 1. Le manifeste
  d'exemples négatifs montre que `creation-site-autre-tenant.json` et
  `affectation-technicien-*.json` passent le schéma et sont rejetés par la règle de référentiel.

**Conséquences.** Trois routes de mutation au lieu d'une. Chaque transition a un propriétaire
clair (matrice R06). Le Front construit ses états d'écran à partir des seuls codes du contrat (N02).

**Risques.** Multiplication de routes si de nouveaux états arrivent (WAITING_PARTS, atelier 3).
Mesure : `to` est un enum extensible en v3, et la table des transitions est documentée en un
seul endroit. Risque d'incompréhension de 404 contre 403 par les équipes Front : la table de
réaction du Catalogue est normative.

**Critères de réexamen.** Si les transitions deviennent paramétrables par tenant, réexaminer
une ressource `workflow` explicite.

---

## ADR-3 — Compatibilité : v2 séparée, adaptateur v1 conservé, migration par consommateur

**Contexte.** Portail Client 1.8 (douze tenants) et Export BI 0.6 consomment v1 via
l'adaptateur, jusqu'au 31/01/2027 (N01, P09). Console Ops et Terrain peuvent migrer en
premier (P09, M5). La liste a changé de forme sans annonce (M1, INC-01). Les routes
d'écriture dangereuses peuvent être fermées (P09). Aucune fuite entre tenants ne peut être
maintenue au nom de la compatibilité (P01).

**Options.**
1. Corriger v1 en place, sans nouvelle version.
2. Big-bang : tous les consommateurs passent en v2 à la même date.
3. Conversion v1 ↔ v2 dans chaque écran.
4. **Cœur unique exposant `/v2`. L'adaptateur v1 conservé est rebranché sur v2 et reste le
   seul point de conversion. Migration consommateur par consommateur.**

**Choix.** Option 4, en quatre phases avec critères d'entrée, d'arrêt et de retour
(Architecture.pdf §5) :
- **Phase 0, correctif de sécurité immédiat sur v1** : tenant tiré du jeton, filtres de
  visibilité, R02/R03 appliqués, contrôle tenant et actif du technicien, transaction unique
  pour l'affectation, révocation de la vue SQL, arrêt de la journalisation des jetons.
- **Phase 1** : publication de v2 ; Console Ops puis Terrain migrent.
- **Phase 2** : fermeture de `GET /api/assign` et `PUT /api/intervention` (410), une fois le
  trafic de ces routes nul pendant 7 jours.
- **Phase 3** : Portail et BI restent en v1 via l'adaptateur jusqu'au retrait (date
  proposée 31/01/2027, à confirmer par ATLAS).

**Justification vérifiable.**
- L'option 1 ne peut pas changer la forme de la liste ni les statuts sans casser
  quelqu'un (INC-01 l'a montré).
- L'option 2 est impossible : « les douze anciens portails ne seront pas mis à jour cette
  semaine » (M5).
- L'option 3 multiplie les conversions divergentes (P02 : les développeurs Back veulent
  « des validations et transitions communes »).
- L'option 4 n'a qu'une conversion maintenue (raisonnement de DECISION_EXEMPLE).
- S12 vérifie : enveloppe v1 conservée pour BI, lecture hors tenant en « not_found » v1,
  ancienne route d'affectation en 410 sans mutation, R02 appliquée à une création v1,
  `CANCELLED` exposé `CLOSED` + `statusDetail`.

**Conséquences.** Deux contrats à tester pendant la transition. Les comportements v1 non
dangereux sont **gelés tels qu'observés** : enveloppe `{data, currentPage, total}`, 404
`no_results` pour liste vide, `currentPage = page + 1`. Ils sont documentés au lieu d'être
corrigés en silence, et la v2 les corrige.

**Risques et hypothèses.**
- **H1** : le format exact que l'adaptateur sert au Portail (« champs français », P05) n'est
  pas fourni. Mesure : avant de rebrancher l'adaptateur, capturer des réponses de référence
  (« golden files ») par route et par tenant pilote, puis rejouer après rebranchement.
  Critère d'entrée de la phase 3.
- **H5** : un consommateur v1 à enum fermé peut ne pas connaître IN_PROGRESS ou les nouveaux
  `kind` d'historique (`REASSIGNED`, `STATUS_CHANGED`, `UPDATED`). Mesure : test de contrat
  par consommateur ; si nécessaire, une table `kind` v1 dans l'adaptateur.
- Oubli du retrait de v1. Mesure : métrique de trafic par route v1, date de retrait inscrite
  au registre des risques.

**Critères d'arrêt et de retour.** Taux d'erreurs 5xx ou de conflits (412) au-dessus de la
référence v1 de plus de 2 points pendant 24 h, ou ticket de fuite de données : on arrête la
migration du consommateur concerné et on le remet sur sa route précédente. **Un retour
arrière ne réactive jamais la vue SQL, `X-Tenant` ni la lecture hors tenant** (P09) : les
correctifs de phase 0 ne sont pas réversibles.

**Critère de réexamen.** Trafic v1 nul pendant 30 jours et confirmation écrite des
propriétaires de Portail et BI : retrait de l'adaptateur.

---

## ADR-4 — Concurrence optimiste par révision (`ETag` / `If-Match`)

**Contexte.** Deux planificateurs lisent I100 en révision 2. Le second envoi efface la
priorité du premier sans avertissement (INC-08, `http/concurrence.http`, U2). Le champ
`revision` existe déjà en base (P05) mais n'est pas utilisé. R10 exige d'éviter l'écrasement
silencieux et de dire au consommateur comment reprendre.

**Options.**
1. Dernier écrit gagne (situation actuelle).
2. Verrou pessimiste (verrouillage à l'ouverture d'un écran).
3. Révision dans le corps de la requête (`"revision": 2`).
4. **`ETag: "rev-N"` en réponse, `If-Match` obligatoire sur toutes les mutations ; 428 s'il
   manque, 412 + `currentRevision` s'il est périmé.**

**Choix.** Option 4, appliquée en base par un `UPDATE … WHERE revision = ?` conditionnel
dans la même transaction que l'écriture de l'événement.

**Justification vérifiable.**
- L'option 1 viole R10.
- L'option 2 : des verrous sur des écrans web ouverts longtemps, ou sur mobile
  déconnecté (U3), restent bloqués sans libération fiable.
- L'option 3 fonctionne, mais mélange la précondition avec les données et ne profite pas
  de la sémantique HTTP standard (RFC 9110 §13.1.1 `If-Match`, §15.5.13 412 ; RFC 6585 §3
  428 Precondition Required).
- Rendre `If-Match` **obligatoire** empêche un client oublieux de retomber dans le mode
  « dernier écrit gagne ».
- S11 rejoue U2 : écran ancien → 412, I100 inchangée, aucun événement ; relecture
  (priorité HIGH visible) ; renvoi conscient → 200 révision 4.
- `verifier_detection.py` montre que S11 échoue si la révision est ignorée.

**Conséquences.** Chaque écran conserve l'ETag de sa dernière lecture. Un 412 n'est pas une
erreur utilisateur : l'écran garde la saisie, relit, affiche l'écart et propose de renvoyer.
Le contrôle s'applique à toute mutation : deux modifications indépendantes (priorité, puis
affectation) entrent aussi en conflit. Ce choix prudent est accepté, la relecture suffisant
à reprendre.

**Risques.** Conflits plus fréquents sur les files très actives. Mesure : suivre le taux de
412 pendant la période d'observation (P09). S'il dépasse environ 5 % des mutations,
envisager une fusion automatique des champs disjoints. Autre risque : Terrain hors ligne
renvoie une intention ancienne. Le 412 la signale au lieu de l'appliquer à l'aveugle (U3).

**Critères de réexamen.** Taux de 412 durablement élevé, ou besoin d'édition collaborative.

---

## ADR-5 — Pagination par curseur (keyset) et ordre total déterministe

**Contexte.** La liste n'a aucun ordre spécifié (P06). `page=0` est converti en 1 sans
annonce, si bien que page 0 et page 1 renvoient les mêmes lignes (M1, INC-05). Le filtre site
est appliqué dans le navigateur sur une page tronquée (M1, `front.mjs load`). Plusieurs
créations partagent un `createdAt` : I100 et I102, plus I101 après conversion H3
(`audit_preuves.py`). La taille est « libre » (P06). Objectif N04 : 500 ms p95 pour 20 lignes
sur 1 600 demandes par semaine.

**Options.**
1. `page`/`size` avec décalage (`OFFSET`).
2. **Curseur opaque sur la clé `(createdAt, id)`, `limit` borné 1–100, `totalItems` informatif.**

**Choix.** Option 2. Tri par `createdAt` puis `id` (sens `-createdAt` par défaut, `createdAt`
pour une file d'attente). Le curseur est lié aux filtres et au tri (400 `INVALID_CURSOR`
sinon). Hors bornes, la requête est rejetée (400), sans écrêtage silencieux. Index
proposé : `(tenant_id, status, site_id, created_at DESC, id DESC)` et `(tenant_id, created_at DESC, id DESC)`.

**Justification vérifiable.**
- Avec un décalage, une insertion en tête pendant la navigation décale toutes les pages :
  doublons ou sauts, le symptôme d'INC-05. Le coût d'`OFFSET` croît aussi avec la
  profondeur.
- Le keyset reprend strictement après la dernière clé vue. S04 insère une intervention
  entre la page 1 et la page 2 : page 2 = I100, I103, sans doublon ni saut. Le second
  critère `id` départage les trois créations simultanées. Il fournit un ordre total stable, pas
  une chronologie : un identifiant opaque ne dit rien de l'antériorité (P02).
- La position demandée en U4 reste servie par `hasNext` et par `totalItems`, recalculé à
  chaque page. Le numéro de page est compté par l'écran.

**Conséquences.** Pas d'accès direct à « la page 7 » : acceptable pour une file de travail
qui se parcourt séquentiellement et se filtre. Le Front ne filtre plus localement. Une
lecture vide est un 200 normal.

**Limites acceptées.** Le curseur n'est pas une photographie : une ligne dont le statut
change pendant la navigation peut quitter un filtre par statut. Une ligne créée après la
première page n'apparaît, en tri décroissant, qu'au rechargement. `totalItems` coûte un
`COUNT` filtré par tenant : acceptable aux volumes annoncés, à surveiller dans la mesure N04.

**Critères de réexamen.** Besoin d'export complet cohérent (BI) : un instantané dédié, pas la
liste paginée. Ou un `COUNT` qui devient le poste dominant de la latence : rendre
`totalItems` facultatif.
