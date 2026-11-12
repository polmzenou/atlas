# Fixtures du simulateur — avant / après

Les pièces client (`ETUDIANTS/03_RESSOURCES/json/`) restent intactes. Ces fichiers
sont des **copies de travail** utilisées par `atlas_mock.py`. Chaque écart avec
la source est listé ci-dessous ; aucun n'est silencieux.

| Fichier | Source | Transformation |
|---|---|---|
| `sites.json`, `techniciens.json`, `identites.json` | T02 | Copie à l'identique (T03 inactif conservé, cf. T13). |
| `jetons-simules.json` | captures `http/*.http` | Ajouté : table jeton DEMO → identité, simule le résultat validé du fournisseur d'identité (P09). |
| `interventions-v2.json` | T01 `json/interventions.json` | Voir tableau suivant. |
| `evenements-v2.json` | aucune (P06 ne fournit qu'une capture de I100) | **Synthétique** : historique plausible pour rendre les révisions cohérentes. Ce n'est pas un historique migré réel. |

## Écarts sur `interventions-v2.json`

| Id | Champ | Source | Fixture | Justification / hypothèse |
|---|---|---|---|---|
| I101 | `priority` | `2` (nombre) | `"NORMAL"` | **H2** : correspondance 1=LOW, 2=NORMAL, 3=HIGH supposée (non publiée, INC-09). À confirmer par ATLAS. |
| I101 | `createdAt` | `"20/10/2026 10:00"` | `"2026-10-20T08:00:00Z"` | **H3** : heure locale serveur Europe/Paris (UTC+2 le 20/10/2026, passage à l'heure d'hiver le 25/10). À confirmer par les journaux serveur. Conséquence : I100, I101 et I102 ont le même instant → tri secondaire indispensable. |
| tous | `createdBy` | absent | U01/U02/U20 | Champ cible (R03 « auteur déterminé par le serveur ») ; auteurs choisis parmi les identités du tenant, synthétiques. |

## Anomalies conservées volontairement (constats d'audit)

- **I100** : `revision: 2` alors que `updatedAt == createdAt`. Une mutation sans
  mise à jour de date, ou une révision incrémentée à tort. Conservé ; l'événement
  `E100-2` est synthétique.
- **I103** : `DONE` en `revision: 3`. Le cycle R04 complet (NEW→ASSIGNED→IN_PROGRESS→DONE)
  exige au moins 4 révisions. Conservé : l'événement `E103-3` (ASSIGNED→DONE) reflète
  la transition non conforme permise par l'API historique (« statut reçu tel quel », P08 M4).
  Une migration réelle devrait marquer ces événements comme hérités.
