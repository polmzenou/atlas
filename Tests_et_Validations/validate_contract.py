"""Contrôles statiques du contrat et des exemples.

1. Validité structurelle OpenAPI 3.1 et résolution des $ref (openapi-spec-validator).
2. Présence des six opérations du socle et des réponses d'erreur attendues.
3. Chaque exemple inline est conforme à son schéma ET identique au fichier
   Exemples_JSON référencé par `x-source` (alignement contrat / exemples, D4).
4. Chaque fichier d'Exemples_JSON est référencé (contrat ou manifeste).
5. Exemples négatifs : verdict du schéma conforme à l'attendu, puis rejeu sur le
   simulateur pour vérifier que la BONNE règle rejette (statut + code de champ).

Sortie : texte sur la console, code retour 0 si tout est conforme.
"""
import json
import sys
from importlib.metadata import version
from pathlib import Path

from openapi_spec_validator import validate
from openapi_spec_validator.readers import read_from_filename

from atlas_mock import AtlasMock
from contrat import CONTRACT_PATH, ROOT, Contract

SOCLE = {
    "listInterventions": ["200", "400", "401"],
    "getIntervention": ["200", "401", "404"],
    "createIntervention": ["201", "400", "401", "403", "422"],
    "updateIntervention": ["200", "400", "401", "403", "404", "409", "412", "422", "428"],
    "assignIntervention": ["200", "400", "401", "403", "404", "409", "412", "422", "428"],
    "listInterventionEvents": ["200", "400", "401", "404"],
}
failures = []


def check(cond, label):
    print(("  OK   " if cond else "  ÉCHEC ") + label)
    if not cond:
        failures.append(label)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    print(f"Python {sys.version.split()[0]} | openapi-spec-validator {version('openapi-spec-validator')} "
          f"| jsonschema {version('jsonschema')} | PyYAML {version('pyyaml')}")

    print("\n[1] Structure OpenAPI 3.1")
    spec, _ = read_from_filename(str(CONTRACT_PATH))
    try:
        validate(spec)
        check(spec["openapi"].startswith("3.1"), f"document {spec['openapi']} valide, références résolues")
    except Exception as exc:  # message du validateur conservé tel quel
        check(False, f"document invalide : {exc}")
        return

    contract = Contract()
    print("\n[2] Socle des six opérations")
    for op_id, codes in SOCLE.items():
        present = op_id in contract.operations
        declared = sorted(contract.operations[op_id][2]["responses"]) if present else []
        missing = [c for c in codes if c not in declared]
        check(present and not missing, f"{op_id} {contract.operations[op_id][0] if present else ''} "
              f"{contract.operations[op_id][1] if present else ''} réponses={declared}"
              + (f" manquantes={missing}" if missing else ""))
    check("bearerAuth" in contract.doc["components"]["securitySchemes"] and contract.doc.get("security"),
          "sécurité globale bearerAuth déclarée")

    print("\n[3] Exemples inline : schéma + identité avec Exemples_JSON")
    referenced = set()

    def check_media(content, where):
        for media in content.values():
            for name, ex in media.get("examples", {}).items():
                errs = contract.errors(contract.validator(media["schema"]), ex["value"])
                label = f"{where} « {name} »"
                check(not errs, label + " conforme au schéma" + (f" : {errs}" if errs else ""))
                src = ex.get("x-source")
                if src:
                    referenced.add(src)
                    f = ROOT / src
                    same = f.exists() and json.loads(f.read_text(encoding="utf-8")) == ex["value"]
                    check(same, f"{label} identique à {src}")

    for op_id, (method, path, op) in contract.operations.items():
        if "requestBody" in op:
            check_media(op["requestBody"]["content"], f"{op_id} requête")
        for status, resp in op["responses"].items():
            if "$ref" not in resp:  # les réponses partagées sont contrôlées une seule fois ci-dessous
                check_media(resp.get("content", {}), f"{op_id} {status}")
    for name, resp in contract.doc["components"]["responses"].items():
        check_media(resp.get("content", {}), f"components/responses/{name}")

    print("\n[4] Exemples négatifs : bonne règle de rejet")
    manifest = json.loads((ROOT / "Exemples_JSON" / "manifest.json").read_text(encoding="utf-8"))
    for case in manifest["negatifs"]:
        referenced.add("Exemples_JSON/" + case["file"])
        payload = json.loads((ROOT / "Exemples_JSON" / case["file"]).read_text(encoding="utf-8"))
        schema_ok = not contract.errors(contract.component(case["schema"]), payload)
        verdict = "accepté" if schema_ok else "rejeté"
        check(schema_ok == case["schemaValid"],
              f"{case['file']} : schéma {case['schema']} {verdict} (attendu {'accepté' if case['schemaValid'] else 'rejeté'})")
        r = case["replay"]
        headers = {"Authorization": "Bearer " + r["token"], "Content-Type": "application/json"}
        if "ifMatch" in r:
            headers["If-Match"] = r["ifMatch"]
        mock = AtlasMock()
        before = mock.snapshot()
        resp = mock.handle(r["method"], r["target"], headers, json.dumps(payload))
        codes = [[e["field"], e["code"]] for e in (resp.body or {}).get("errors", [])]
        check(resp.status == r["status"] and r["fieldCode"] in codes and mock.snapshot() == before,
              f"   rejeu {r['method']} {r['target']} → {resp.status} {codes} sans effet persistant ({case['rule']})")

    print("\n[5] Couverture des fichiers d'exemples")
    files = {p.relative_to(ROOT).as_posix() for p in (ROOT / "Exemples_JSON").rglob("*.json")} - {"Exemples_JSON/manifest.json"}
    orphans = sorted(files - referenced)
    check(not orphans, f"{len(files)} fichiers, tous référencés" + (f" ; orphelins : {orphans}" if orphans else ""))

    print(f"\nRÉSULTAT : {'CONFORME' if not failures else str(len(failures)) + ' échec(s)'}")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
