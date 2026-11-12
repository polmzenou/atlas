"""Simulateur local du contrat ATLAS v2 et de l'API v1 sécurisée.

SIMULATION en mémoire, sans réseau ni base : il sert à rejouer les scénarios et à
vérifier que des réponses conformes au contrat sont produisibles. Il ne prouve pas
le comportement du futur serveur réel (voir Tests_et_Validations/README.md).

Les règles métier sont codées ici à la main, indépendamment des schémas JSON, afin
que la confrontation réponse / schéma (run_scenarios.py) soit un vrai contrôle.
"""
import base64
import copy
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

FIXTURES = Path(__file__).parent / "fixtures"
PROBLEM_BASE = "https://api.atlas.invalid/problems/"
PRIORITIES = ("LOW", "NORMAL", "HIGH")
STATUSES = ("NEW", "ASSIGNED", "IN_PROGRESS", "DONE", "CANCELLED")
ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
ETAG_RE = re.compile(r'^"rev-([1-9][0-9]*)"$')
IDEM_RE = re.compile(r"^[A-Za-z0-9_-]{8,64}$")
# Table de correspondance v2 -> v1 (hypothèse H5) : seules les valeurs déjà émises
# ou documentées en v1 sont publiées ; le détail exact reste dans statusDetail.
V1_STATUS = {"NEW": "NEW", "ASSIGNED": "ASSIGNED", "IN_PROGRESS": "IN_PROGRESS",
             "DONE": "DONE", "CANCELLED": "CLOSED"}
V1_OPEN = {"NEW", "ASSIGNED", "IN_PROGRESS"}
# Cible -> (rôles autorisés, statuts de départ admis) — R04/R06.
TRANSITIONS = {
    "IN_PROGRESS": ({"technician"}, {"ASSIGNED"}),
    "DONE": ({"technician"}, {"IN_PROGRESS"}),
    "CANCELLED": ({"requester", "planner"}, {"NEW", "ASSIGNED"}),
}


class Response:
    def __init__(self, status, body=None, headers=None):
        self.status = status
        self.body = body
        self.headers = headers or {}

    def to_dict(self):
        return {"status": self.status, "headers": self.headers, "body": self.body}


class ApiError(Exception):
    def __init__(self, status, code, title, detail=None, errors=None, **extra):
        super().__init__(code)
        self.status, self.code, self.title = status, code, title
        self.detail, self.errors, self.extra = detail, errors, extra


def _load(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _b64(obj):
    return base64.urlsafe_b64encode(json.dumps(obj, separators=(",", ":")).encode()).decode().rstrip("=")


def _unb64(text):
    return json.loads(base64.urlsafe_b64decode(text + "=" * (-len(text) % 4)))


def _fe(field, code, message):
    return {"field": field, "code": code, "message": message}


class AtlasMock:
    def __init__(self, start="2026-10-27T09:00:00Z"):
        self.interventions = {i["id"]: i for i in _load("interventions-v2.json")}
        self.events = {}
        for e in _load("evenements-v2.json"):
            self.events.setdefault(e["interventionId"], []).append(e)
        self.sites = {s["id"]: s for s in _load("sites.json")}
        self.technicians = {t["id"]: t for t in _load("techniciens.json")}
        users = {u["userId"]: u for u in _load("identites.json")}
        self.tokens = {k: users[v] for k, v in _load("jetons-simules.json").items() if not k.startswith("_")}
        self.clock = datetime.strptime(start, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        self.next_id = 104
        self.corr = 0
        self.idempotency = {}
        self.log = []  # journal technique simulé : jamais de jeton ni de texte libre (N03)

    # ------------------------------------------------------------------ outils
    def _now(self):
        self.clock += timedelta(seconds=1)
        return self.clock.strftime("%Y-%m-%dT%H:%M:%SZ")

    def _new_id(self):
        while f"I{self.next_id}" in self.interventions:
            self.next_id += 1
        self.next_id += 1
        return f"I{self.next_id - 1}"

    def snapshot(self):
        """État persistant comparable avant/après (preuve d'absence d'effet)."""
        return copy.deepcopy({"interventions": self.interventions, "events": self.events})

    # ------------------------------------------------------------- point d'entrée
    def handle(self, method, target, headers=None, body=None):
        headers = {k.lower(): v for k, v in (headers or {}).items()}
        self.corr += 1
        corr = f"corr-{self.corr:04d}"
        url = urlsplit(target)
        query = parse_qs(url.query, keep_blank_values=True)
        path = url.path.rstrip("/")
        # L'opération est identifiée AVANT exécution : une erreur reste attribuée à
        # son opération (journal et contrôle de conformité des réponses d'erreur).
        if path.startswith("/v2/"):
            operation, action = self._route_v2(method, path[3:])
        elif path.startswith("/api/"):
            operation, action = self._route_v1(method, path)
        else:
            operation, action = "unknown", None
        try:
            if action is None:
                raise ApiError(404, "NOT_FOUND", "Ressource introuvable")
            resp = action(query, headers, body)
        except ApiError as err:
            if path.startswith("/api/") and err.status != 401:
                resp = Response(200, {"success": False, "error": err.code.lower()})
            else:
                problem = {"type": PROBLEM_BASE + err.code.lower().replace("_", "-"),
                           "title": err.title, "status": err.status, "code": err.code,
                           "correlationId": corr}
                if err.detail:
                    problem["detail"] = err.detail
                if err.errors:
                    problem["errors"] = err.errors
                problem.update(err.extra)
                resp = Response(err.status, problem, {"Content-Type": "application/problem+json"})
                if err.status == 401:
                    resp.headers["WWW-Authenticate"] = 'Bearer realm="atlas"'
                if err.status == 412 and "currentRevision" in err.extra:
                    resp.headers["ETag"] = f'"rev-{err.extra["currentRevision"]}"'
        resp.headers.setdefault("Content-Type", "application/json")
        resp.headers["X-Correlation-Id"] = corr
        self.log.append({"correlationId": corr, "operation": operation, "status": resp.status})
        return resp

    # ------------------------------------------------------------- sécurité commune
    def _identity(self, headers):
        auth = headers.get("authorization", "")
        if not auth.startswith("Bearer ") or auth[7:] not in self.tokens:
            raise ApiError(401, "UNAUTHENTICATED", "Authentification requise")
        return self.tokens[auth[7:]]  # X-Tenant éventuel ignoré volontairement

    @staticmethod
    def _visible(ident, itv):
        if itv["tenantId"] != ident["tenantId"]:
            return False
        if ident["role"] == "technician":
            return itv["technicianId"] == ident.get("technicianId")
        return True

    def _get_visible(self, ident, iid):
        itv = self.interventions.get(iid)
        if itv is None or not self._visible(ident, itv):
            raise ApiError(404, "NOT_FOUND", "Intervention introuvable")
        return itv

    @staticmethod
    def _json_body(headers, body):
        ctype = headers.get("content-type", "")
        if not ctype.split(";")[0].strip() == "application/json":
            raise ApiError(415, "UNSUPPORTED_MEDIA_TYPE", "Type de contenu non supporté",
                           "Content-Type attendu : application/json.")
        try:
            data = json.loads(body) if isinstance(body, (str, bytes)) else body
        except json.JSONDecodeError:
            raise ApiError(400, "MALFORMED_REQUEST", "Corps JSON illisible")
        if not isinstance(data, dict):
            raise ApiError(400, "MALFORMED_REQUEST", "Le corps doit être un objet JSON")
        return data

    @staticmethod
    def _check_query(query, allowed):
        unknown = sorted(set(query) - set(allowed))
        if unknown:
            raise ApiError(400, "INVALID_PARAMETER", "Paramètre invalide",
                           errors=[_fe(u, "UNKNOWN_FIELD", "Paramètre inconnu.") for u in unknown])
        for name, values in query.items():
            if len(values) > 1:
                raise ApiError(400, "INVALID_PARAMETER", "Paramètre invalide",
                               errors=[_fe(name, "INVALID_VALUE", "Paramètre répété.")])
        return {k: v[0] for k, v in query.items()}

    @staticmethod
    def _limit(q, default):
        raw = q.get("limit")
        if raw is None:
            return default
        if not re.fullmatch(r"[1-9][0-9]{0,2}", raw) or int(raw) > 100:
            raise ApiError(400, "INVALID_PARAMETER", "Paramètre invalide",
                           "limit doit être compris entre 1 et 100.",
                           errors=[_fe("limit", "OUT_OF_RANGE", "Valeur entre 1 et 100.")])
        return int(raw)

    @staticmethod
    def _if_match(headers, itv):
        raw = headers.get("if-match")
        if raw is None:
            raise ApiError(428, "PRECONDITION_REQUIRED", "En-tête If-Match obligatoire")
        m = ETAG_RE.match(raw)
        if not m:
            raise ApiError(400, "INVALID_PARAMETER", "Paramètre invalide",
                           errors=[_fe("If-Match", "INVALID_VALUE", 'Format attendu : "rev-N".')])
        return int(m.group(1))

    @staticmethod
    def _check_revision(expected, itv):
        if expected != itv["revision"]:
            raise ApiError(412, "PRECONDITION_FAILED", "Intervention modifiée entre-temps",
                           f'If-Match "rev-{expected}" ne correspond plus à la révision {itv["revision"]}.',
                           currentRevision=itv["revision"])

    def _commit(self, ident, itv, new_values, ev_type, changes):
        """Transaction : intervention + révision + événement, tout ou rien."""
        updated = dict(itv, **new_values)
        updated["revision"] = itv["revision"] + 1
        updated["updatedAt"] = self._now()
        event = {"eventId": f"E{itv['id'][1:]}-{updated['revision']}", "interventionId": itv["id"],
                 "revision": updated["revision"], "type": ev_type, "at": updated["updatedAt"],
                 "actor": {"userId": ident["userId"], "role": ident["role"]}, "changes": changes}
        self.interventions[itv["id"]] = updated
        self.events.setdefault(itv["id"], []).append(event)
        return updated

    @staticmethod
    def _one(itv, status=200, extra=None):
        h = {"ETag": f'"rev-{itv["revision"]}"'}
        h.update(extra or {})
        return Response(status, copy.deepcopy(itv), h)

    # ------------------------------------------------------------------- v2
    def _route_v2(self, method, path):
        parts = path.strip("/").split("/")
        if parts[0] != "interventions" or len(parts) > 3:
            return "unknown", None
        if len(parts) == 1:
            return {"GET": ("listInterventions", lambda q, h, b: self._list(q, h)),
                    "POST": ("createIntervention", self._create)}.get(method, ("unknown", None))
        iid = parts[1]
        sub = parts[2] if len(parts) == 3 else None
        routes = {
            (None, "GET"): ("getIntervention", lambda q, h, b: self._detail(iid, q, h)),
            (None, "PATCH"): ("updateIntervention", lambda q, h, b: self._patch(iid, q, h, b)),
            ("assignment", "PUT"): ("assignIntervention", lambda q, h, b: self._assign(iid, q, h, b)),
            ("transitions", "POST"): ("transitionIntervention", lambda q, h, b: self._transition(iid, q, h, b)),
            ("events", "GET"): ("listInterventionEvents", lambda q, h, b: self._events(iid, q, h)),
        }
        return routes.get((sub, method), ("unknown", None))

    def _list(self, query, headers):
        ident = self._identity(headers)
        q = self._check_query(query, {"status", "siteId", "limit", "cursor", "sort"})
        errors = []
        if "status" in q and q["status"] not in STATUSES:
            errors.append(_fe("status", "INVALID_VALUE", "Valeurs : " + ", ".join(STATUSES)))
        if "siteId" in q and not ID_RE.match(q["siteId"]):
            errors.append(_fe("siteId", "INVALID_VALUE", "Identifiant invalide."))
        sort = q.get("sort", "-createdAt")
        if sort not in ("-createdAt", "createdAt"):
            errors.append(_fe("sort", "INVALID_VALUE", "Valeurs : -createdAt, createdAt"))
        if errors:
            raise ApiError(400, "INVALID_PARAMETER", "Paramètre invalide", errors=errors)
        limit = self._limit(q, 20)
        filters = {"status": q.get("status"), "siteId": q.get("siteId"), "sort": sort}
        rows = [i for i in self.interventions.values() if self._visible(ident, i)
                and (filters["status"] is None or i["status"] == filters["status"])
                and (filters["siteId"] is None or i["siteId"] == filters["siteId"])]
        desc = sort.startswith("-")
        rows.sort(key=lambda i: (i["createdAt"], i["id"]), reverse=desc)
        total = len(rows)
        if "cursor" in q:
            key = self._decode_cursor(q["cursor"], filters)
            rows = [i for i in rows if ((i["createdAt"], i["id"]) < key if desc else (i["createdAt"], i["id"]) > key)]
        page, has_next = rows[:limit], len(rows) > limit
        cursor = _b64({"k": [page[-1]["createdAt"], page[-1]["id"]], "f": filters}) if has_next else None
        return Response(200, {"items": copy.deepcopy(page),
                              "page": {"limit": limit, "hasNext": has_next, "nextCursor": cursor, "totalItems": total}})

    @staticmethod
    def _decode_cursor(raw, filters):
        try:
            data = _unb64(raw)
            key = tuple(data["k"])
            assert data["f"] == filters and len(key) == 2
            return key
        except Exception:
            raise ApiError(400, "INVALID_CURSOR", "Curseur invalide",
                           "Curseur illisible ou utilisé avec d'autres filtres ; repartir de la première page.")

    def _create(self, query, headers, body):
        ident = self._identity(headers)
        self._check_query(query, set())
        data = self._json_body(headers, body)
        if ident["role"] not in ("requester", "planner"):
            raise ApiError(403, "FORBIDDEN", "Action non autorisée",
                           f"Le rôle {ident['role']} ne peut pas créer d'intervention.")
        key = headers.get("idempotency-key")
        fingerprint = hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
        if key is not None:
            if not IDEM_RE.match(key):
                raise ApiError(400, "INVALID_PARAMETER", "Paramètre invalide",
                               errors=[_fe("Idempotency-Key", "INVALID_VALUE", "8 à 64 caractères [A-Za-z0-9_-].")])
            stored = self.idempotency.get((ident["tenantId"], ident["userId"], key))
            if stored:
                if stored[0] != fingerprint:
                    raise ApiError(422, "IDEMPOTENCY_KEY_REUSED", "Clé d'idempotence déjà utilisée",
                                   "Cette clé a servi pour un autre contenu.")
                replay = copy.deepcopy(stored[1])
                replay.headers["Idempotent-Replayed"] = "true"
                return replay
        errors = []
        for k in sorted(set(data) - {"siteId", "title", "priority"}):
            errors.append(_fe(k, "UNKNOWN_FIELD", "Champ non accepté : valeur déterminée par le serveur ou inconnue."))
        title = self._check_title(data, errors, required=True)
        site = data.get("siteId", ...)
        if site is ...:
            errors.append(_fe("siteId", "REQUIRED", "Site obligatoire."))
        elif site is None:
            errors.append(_fe("siteId", "NULL_NOT_ALLOWED", "Site obligatoire."))
        elif not isinstance(site, str) or not ID_RE.match(site):
            errors.append(_fe("siteId", "INVALID_TYPE", "Identifiant de site attendu."))
        elif site not in self.sites or self.sites[site]["tenantId"] != ident["tenantId"]:
            errors.append(_fe("siteId", "SITE_NOT_FOUND", "Site inconnu dans votre organisation."))
        priority = self._check_priority(data, errors, default="NORMAL")
        if errors:
            raise ApiError(422, "VALIDATION_FAILED", "Données invalides", errors=errors)
        now = self._now()
        itv = {"id": self._new_id(), "tenantId": ident["tenantId"], "siteId": site, "title": title,
               "priority": priority, "status": "NEW", "technicianId": None, "createdAt": now,
               "updatedAt": now, "createdBy": ident["userId"], "revision": 1}
        event = {"eventId": f"E{itv['id'][1:]}-1", "interventionId": itv["id"], "revision": 1,
                 "type": "CREATED", "at": now, "actor": {"userId": ident["userId"], "role": ident["role"]},
                 "changes": [{"field": "status", "from": None, "to": "NEW"},
                             {"field": "priority", "from": None, "to": priority}, {"field": "title"}]}
        self.interventions[itv["id"]] = itv
        self.events[itv["id"]] = [event]
        resp = self._one(itv, 201, {"Location": f"/v2/interventions/{itv['id']}"})
        if key is not None:
            self.idempotency[(ident["tenantId"], ident["userId"], key)] = (fingerprint, copy.deepcopy(resp))
        return resp

    @staticmethod
    def _check_title(data, errors, required):
        if "title" not in data:
            if required:
                errors.append(_fe("title", "REQUIRED", "Titre obligatoire."))
            return None
        title = data["title"]
        if title is None:
            errors.append(_fe("title", "NULL_NOT_ALLOWED", "Titre obligatoire."))
        elif not isinstance(title, str):
            errors.append(_fe("title", "INVALID_TYPE", "Texte attendu."))
        elif not 5 <= len(title.strip()) <= 120:
            errors.append(_fe("title", "INVALID_LENGTH",
                              "Le titre doit contenir 5 à 120 caractères hors espaces aux extrémités."))
        else:
            return title.strip()
        return None

    @staticmethod
    def _check_priority(data, errors, default=None):
        if "priority" not in data:
            return default
        p = data["priority"]
        if p is None:
            errors.append(_fe("priority", "NULL_NOT_ALLOWED", "Priorité obligatoire si fournie."))
        elif p not in PRIORITIES:
            errors.append(_fe("priority", "INVALID_VALUE", "Valeurs : LOW, NORMAL, HIGH."))
        else:
            return p
        return None

    def _detail(self, iid, query, headers):
        ident = self._identity(headers)
        self._check_query(query, set())
        return self._one(self._get_visible(ident, iid))

    def _patch(self, iid, query, headers, body):
        ident = self._identity(headers)
        self._check_query(query, set())
        data = self._json_body(headers, body)
        itv = self._get_visible(ident, iid)
        if ident["role"] not in ("requester", "planner"):
            raise ApiError(403, "FORBIDDEN", "Action non autorisée",
                           f"Le rôle {ident['role']} ne peut pas modifier une intervention.")
        expected = self._if_match(headers, itv)
        errors = []
        if not data:
            errors.append(_fe("body", "EMPTY_PATCH", "Au moins un champ attendu : title, priority."))
        for k in sorted(set(data) - {"title", "priority"}):
            if k in ("technicianId", "status"):
                route = "/assignment" if k == "technicianId" else "/transitions"
                errors.append(_fe(k, "FIELD_NOT_MODIFIABLE", f"Non modifiable ici : utiliser {route}."))
            else:
                errors.append(_fe(k, "UNKNOWN_FIELD", "Champ non modifiable ou inconnu."))
        title = self._check_title(data, errors, required=False)
        priority = self._check_priority(data, errors)
        if errors:
            raise ApiError(422, "VALIDATION_FAILED", "Données invalides", errors=errors)
        self._check_revision(expected, itv)
        allowed = {"requester": {"NEW"}, "planner": {"NEW", "ASSIGNED"}}[ident["role"]]
        if itv["status"] not in allowed:
            raise ApiError(409, "INVALID_STATE", "Modification impossible dans cet état",
                           f"Le rôle {ident['role']} ne peut modifier une intervention {itv['status']}.",
                           currentStatus=itv["status"])
        new, changes = {}, []
        if title is not None and title != itv["title"]:
            new["title"] = title
            changes.append({"field": "title"})
        if priority is not None and priority != itv["priority"]:
            new["priority"] = priority
            changes.append({"field": "priority", "from": itv["priority"], "to": priority})
        if not changes:
            return self._one(itv)
        return self._one(self._commit(ident, itv, new, "UPDATED", changes))

    def _assign(self, iid, query, headers, body):
        ident = self._identity(headers)
        self._check_query(query, set())
        data = self._json_body(headers, body)
        itv = self._get_visible(ident, iid)
        if ident["role"] != "planner":
            raise ApiError(403, "FORBIDDEN", "Action non autorisée",
                           f"Le rôle {ident['role']} ne peut pas affecter un technicien.")
        expected = self._if_match(headers, itv)
        errors = [_fe(k, "UNKNOWN_FIELD", "Champ inconnu.") for k in sorted(set(data) - {"technicianId"})]
        tid = data.get("technicianId", ...)
        if tid is ...:
            errors.append(_fe("technicianId", "REQUIRED", "Technicien obligatoire."))
        elif tid is None:
            errors.append(_fe("technicianId", "NULL_NOT_ALLOWED", "Le retrait sans remplacement n'existe pas."))
        elif not isinstance(tid, str) or not ID_RE.match(tid):
            errors.append(_fe("technicianId", "INVALID_TYPE", "Identifiant de technicien attendu."))
        else:
            tech = self.technicians.get(tid)
            if tech is None or tech["tenantId"] != ident["tenantId"]:
                errors.append(_fe("technicianId", "TECHNICIAN_NOT_FOUND", "Technicien inconnu dans votre organisation."))
            elif not tech["active"]:
                errors.append(_fe("technicianId", "TECHNICIAN_INACTIVE", "Technicien inactif : affectation impossible."))
        if errors:
            raise ApiError(422, "VALIDATION_FAILED", "Données invalides", errors=errors)
        self._check_revision(expected, itv)
        if itv["status"] not in ("NEW", "ASSIGNED"):
            raise ApiError(409, "INVALID_STATE", "Affectation impossible dans cet état",
                           f"Une intervention {itv['status']} ne peut plus être affectée.",
                           currentStatus=itv["status"])
        if itv["technicianId"] == tid and itv["status"] == "ASSIGNED":
            return self._one(itv)  # PUT idempotent : aucune révision, aucun événement
        changes = [{"field": "technicianId", "from": itv["technicianId"], "to": tid}]
        if itv["status"] != "ASSIGNED":
            changes.append({"field": "status", "from": itv["status"], "to": "ASSIGNED"})
        ev_type = "ASSIGNED" if itv["technicianId"] is None else "REASSIGNED"
        return self._one(self._commit(ident, itv, {"technicianId": tid, "status": "ASSIGNED"}, ev_type, changes))

    def _transition(self, iid, query, headers, body):
        ident = self._identity(headers)
        self._check_query(query, set())
        data = self._json_body(headers, body)
        itv = self._get_visible(ident, iid)
        if ident["role"] == "reporter":
            raise ApiError(403, "FORBIDDEN", "Action non autorisée", "Le rôle reporter est en lecture seule.")
        expected = self._if_match(headers, itv)
        errors = [_fe(k, "UNKNOWN_FIELD", "Champ inconnu.") for k in sorted(set(data) - {"to"})]
        target = data.get("to", ...)
        if target is ...:
            errors.append(_fe("to", "REQUIRED", "Statut cible obligatoire."))
        elif target not in TRANSITIONS:
            errors.append(_fe("to", "INVALID_VALUE", "Valeurs : IN_PROGRESS, DONE, CANCELLED (ASSIGNED via /assignment)."))
        if errors:
            raise ApiError(422, "VALIDATION_FAILED", "Données invalides", errors=errors)
        roles, sources = TRANSITIONS[target]
        if ident["role"] not in roles:
            raise ApiError(403, "FORBIDDEN", "Action non autorisée",
                           f"Le rôle {ident['role']} ne peut pas demander {target}.")
        self._check_revision(expected, itv)
        if itv["status"] not in sources:
            raise ApiError(409, "INVALID_TRANSITION", "Transition interdite",
                           f"{itv['status']} → {target} n'est pas autorisé.", currentStatus=itv["status"])
        changes = [{"field": "status", "from": itv["status"], "to": target}]
        return self._one(self._commit(ident, itv, {"status": target}, "STATUS_CHANGED", changes))

    def _events(self, iid, query, headers):
        ident = self._identity(headers)
        q = self._check_query(query, {"limit", "cursor"})
        limit = self._limit(q, 50)
        self._get_visible(ident, iid)
        rows = sorted(self.events.get(iid, []), key=lambda e: e["revision"])
        total = len(rows)
        if "cursor" in q:
            after = self._decode_cursor(q["cursor"], {"interventionId": iid})[0]
            rows = [e for e in rows if e["revision"] > after]
        page, has_next = rows[:limit], len(rows) > limit
        cursor = _b64({"k": [page[-1]["revision"], ""], "f": {"interventionId": iid}}) if has_next else None
        return Response(200, {"items": copy.deepcopy(page),
                              "page": {"limit": limit, "hasNext": has_next, "nextCursor": cursor, "totalItems": total}})

    # ------------------------------------------------------------------- v1
    # Routes historiques maintenues jusqu'au 31/01/2027 (N01), phase 2 du plan de
    # migration : identité imposée par le jeton, formats observés conservés,
    # routes d'écriture dangereuses fermées (410).
    def _v1_item(self, itv, full):
        out = {"id": itv["id"], "title": itv["title"], "status": V1_STATUS[itv["status"]],
               "statusDetail": itv["status"]}
        if full:
            out.update({"tenantId": itv["tenantId"], "siteId": itv["siteId"], "priority": itv["priority"],
                        "technicianId": itv["technicianId"], "createdAt": itv["createdAt"],
                        "updatedAt": itv["updatedAt"], "revision": itv["revision"]})
        return out

    def _route_v1(self, method, path):
        detail = re.fullmatch(r"/api/intervention/([^/]+)", path)
        history = re.fullmatch(r"/api/interventions/([^/]+)/history", path)
        if path == "/api/assign" and method == "GET":
            return "v1.assign", lambda q, h, b: self._v1_gone(h, "/v2/interventions/{id}/assignment")
        if detail and method == "PUT":
            return "v1.update", lambda q, h, b: self._v1_gone(h, "/v2/interventions/{id}")
        if path == "/api/interventions" and method == "GET":
            return "v1.list", self._v1_list
        if path == "/api/interventions" and method == "POST":
            return "v1.create", self._v1_create
        if detail and method == "GET":
            return "v1.detail", lambda q, h, b: self._v1_detail(detail.group(1), h)
        if history and method == "GET":
            return "v1.history", lambda q, h, b: self._v1_history(history.group(1), h)
        return "unknown", None

    def _v1_gone(self, headers, see):
        self._identity(headers)
        return Response(410, {"success": False, "error": "gone", "see": see})

    def _v1_list(self, query, headers, body):
        ident = self._identity(headers)
        q = {k: v[0] for k, v in query.items()}
        rows = [i for i in self.interventions.values() if self._visible(ident, i)]
        if q.get("state") in ("open", "closed"):
            rows = [i for i in rows if (i["status"] in V1_OPEN) == (q["state"] == "open")]
        if q.get("site"):
            rows = [i for i in rows if i["siteId"] == q["site"]]
        rows.sort(key=lambda i: (i["createdAt"], i["id"]), reverse=True)
        page = int(q["page"]) if q.get("page", "").isdigit() else 0
        size = min(int(q["size"]), 100) if q.get("size", "").isdigit() and int(q["size"]) > 0 else 20
        if not rows:
            return Response(404, {"success": False, "error": "no_results"})
        return Response(200, {"data": [self._v1_item(i, False) for i in rows[page * size:(page + 1) * size]],
                              "currentPage": page + 1, "total": len(rows)})

    def _v1_detail(self, iid, headers):
        ident = self._identity(headers)
        itv = self.interventions.get(iid)
        if itv is None or not self._visible(ident, itv):
            return Response(200, {"success": False, "error": "not_found"})
        return Response(200, self._v1_item(itv, True))

    def _v1_history(self, iid, headers):
        ident = self._identity(headers)
        itv = self.interventions.get(iid)
        if itv is None or not self._visible(ident, itv):
            return Response(200, {"success": False, "error": "not_found"})
        evs = sorted(self.events.get(iid, []), key=lambda e: e["revision"])
        return Response(200, [{"actorId": e["actor"]["userId"], "kind": e["type"], "at": e["at"]} for e in evs])

    def _v1_create(self, query, headers, body):
        data = self._json_body(headers, body)
        v2 = {k: data[k] for k in ("title", "siteId", "priority") if k in data}
        resp = self._create({}, headers | {"content-type": "application/json"}, json.dumps(v2))
        return Response(200, {"success": True, "intervention_id": resp.body["id"], "id": resp.body["id"]})
