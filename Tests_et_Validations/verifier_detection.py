"""Contre-épreuve : les scénarios détectent-ils les défauts historiques ?

Chaque mutation réintroduit dans le simulateur un défaut observé dans
03_RESSOURCES/code/back.mjs ou dans les incidents, puis rejoue les scénarios.
Une mutation doit faire échouer au moins un scénario ; sinon les tests seraient
complaisants. Le simulateur d'origine n'est pas modifié (remplacement temporaire).
"""
import contextlib
import io
import sys

import atlas_mock
import run_scenarios
from atlas_mock import AtlasMock, ApiError


def _patch_keeps_null(self, iid, query, headers, body):
    """INC-04 : technicianId absent remplacé par null, statut reçu tel quel."""
    resp = ORIGINAL["_patch"](self, iid, query, headers, body)
    if resp.status == 200:
        self.interventions[iid]["technicianId"] = None
        resp.body["technicianId"] = None
    return resp


def _visible_ignores_tenant(ident, itv):
    """INC-06 : le contrôleur détail charge par id sans filtre de tenant."""
    return True


def _check_revision_noop(expected, itv):
    """INC-08 : aucune vérification de la révision lue."""
    return None


def _assign_exists_only(self, iid, query, headers, body):
    """INC-07 : seule l'existence du technicien est vérifiée."""
    saved = {k: dict(v) for k, v in self.technicians.items()}
    for t in self.technicians.values():
        t["tenantId"], t["active"] = "C01", True
    try:
        return ORIGINAL["_assign"](self, iid, query, headers, body)
    finally:
        self.technicians = saved


def _assign_always_event(self, iid, query, headers, body):
    """INC-03/INC-10 : chaque appel réécrit l'historique, même sans changement."""
    resp = ORIGINAL["_assign"](self, iid, query, headers, body)
    if resp.status == 200 and self.events[iid][-1]["revision"] != resp.body["revision"] + 1:
        last = dict(self.events[iid][-1], revision=resp.body["revision"] + 1)
        self.events[iid].append(last)
    return resp


def _list_without_order(self, query, headers):
    """INC-05 : aucun ordre garanti (ordre d'insertion inversé)."""
    resp = ORIGINAL["_list"](self, query, headers)
    if resp.status == 200:
        resp.body["items"].reverse()
    return resp


def _title_not_validated(data, errors, required):
    """P05/P08 M2 : la longueur du titre n'est vérifiée que par le navigateur."""
    title = data.get("title")
    if title is None and required:
        errors.append({"field": "title", "code": "REQUIRED", "message": "Titre obligatoire."})
    return title


def _create_uses_header_tenant(self, query, headers, body):
    """INC-06/R03 : le tenant est lu dans X-Tenant."""
    resp = ORIGINAL["_create"](self, query, headers, body)
    if resp.status == 201 and "x-tenant" in headers:
        self.interventions[resp.body["id"]]["tenantId"] = headers["x-tenant"]
    return resp


def _log_secrets(self, method, target, headers=None, body=None):
    """P09/N03 : le jeton et le titre sont journalisés."""
    resp = ORIGINAL["handle"](self, method, target, headers, body)
    self.log[-1]["authorization"] = (headers or {}).get("Authorization")
    self.log[-1]["title"] = body
    return resp


ORIGINAL = {name: getattr(AtlasMock, name) for name in ("_patch", "_assign", "_list", "_create", "handle")}
MUTATIONS = [
    ("INC-04 PATCH remet technicianId à null", "_patch", _patch_keeps_null, False),
    ("INC-06 visibilité sans contrôle de tenant", "_visible", staticmethod(_visible_ignores_tenant), True),
    ("INC-08 révision If-Match ignorée", "_check_revision", staticmethod(_check_revision_noop), True),
    ("INC-07 technicien : existence seule", "_assign", _assign_exists_only, False),
    ("INC-03/10 événement à chaque répétition", "_assign", _assign_always_event, False),
    ("INC-05 liste sans ordre déterministe", "_list", _list_without_order, False),
    ("R02 titre non validé côté serveur", "_check_title", staticmethod(_title_not_validated), True),
    ("R03 tenant pris dans X-Tenant à la création", "_create", _create_uses_header_tenant, False),
    ("N03 jeton et texte libre journalisés", "handle", _log_secrets, False),
]


def run_quiet():
    failed = []
    for sc in run_scenarios.SCENARIOS:
        mock = AtlasMock()
        before, ctx, prev, ok = mock.snapshot(), {}, None, True
        for st in sc["steps"]:
            resp, _, checks, _ = run_scenarios.run_step(run_scenarios.Contract(), mock, dict(st), ctx, prev)
            prev = resp
            ok &= all(c[1] for c in checks)
        label, fn = sc["effect"]
        ok &= (mock.snapshot() == before) if fn is None else bool(fn(mock))
        if not ok:
            failed.append(sc["id"])
    return failed


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    undetected = 0
    print("Référence (simulateur non modifié) :", run_quiet() or "aucun échec")
    for label, attr, replacement, is_static in MUTATIONS:
        saved = AtlasMock.__dict__[attr]
        setattr(AtlasMock, attr, replacement)
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                failed = run_quiet()
        finally:
            setattr(AtlasMock, attr, saved)
        undetected += 0 if failed else 1
        print(f"{'✅ détecté ' if failed else '❌ NON détecté'} — {label} → scénarios en échec : {', '.join(failed) or 'aucun'}")
    print(f"\nBILAN : {len(MUTATIONS) - undetected}/{len(MUTATIONS)} défauts historiques détectés par les scénarios.")
    return 0 if undetected == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
