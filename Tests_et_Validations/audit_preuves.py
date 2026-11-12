"""Preuves outillées de l'audit sur les pièces client (copie dans pieces_client_originales/).

Chaque contrôle affiche une observation reproductible référencée par la ligne
d'audit (A-xx) qu'elle étaye. Les contrôles de forme ne prouvent pas un comportement
serveur : ils objectivent des divergences entre pièces.
"""
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from jsonschema import Draft202012Validator
from openapi_spec_validator import validate
from openapi_spec_validator.readers import read_from_filename

SRC = Path(__file__).parent / "pieces_client_originales"


def load(rel):
    return json.loads((SRC / rel).read_text(encoding="utf-8"))


def section(title):
    print(f"\n== {title}")


def main():
    sys.stdout.reconfigure(encoding="utf-8")

    section("A-07 / D1 — openapi-initial.yaml (T12) : syntaxe valide, contenu non contractuel")
    spec, _ = read_from_filename(str(SRC / "openapi-initial.yaml"))
    validate(spec)
    ops = [(m.upper(), p) for p, item in spec["paths"].items() for m in item]
    print(f"structure OpenAPI {spec['openapi']} valide ; {len(ops)} opérations : {ops}")
    no_body = [f"{m} {p}" for m, p in ops if "content" not in spec["paths"][p][m.lower()]["responses"]["200"]]
    print(f"réponses 200 sans schéma de contenu : {len(no_body)}/{len(ops)} ; aucune réponse d'erreur ; aucun securityScheme : "
          f"{'securitySchemes' not in spec.get('components', {})}")
    print(f"GET /api/assign déclaré comme lecture (méthode sûre) : {('GET', '/api/assign') in ops}")

    section("A-06 — Données et réponses capturées confrontées au schéma v1 annoncé (T11)")
    schema = load("schemas/intervention-v1.schema.json")
    validator = Draft202012Validator(schema)
    for rel in ("json/interventions.json", "json/detail-reponse.json"):
        data = load(rel)
        for item in data if isinstance(data, list) else [data]:
            errs = sorted({f"{'/'.join(map(str, e.path)) or 'racine'}: {e.message}" for e in validator.iter_errors(item)})
            print(f"{rel} {item['id']} : {len(errs)} écart(s) — " + " | ".join(errs))

    section("A-06 / A-08 — Dates, priorités et ordre (T01, T04)")
    rows = load("json/interventions.json")
    iso = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
    for r in rows:
        if not iso.match(r["createdAt"]):
            print(f"{r['id']} createdAt non ISO 8601 UTC : {r['createdAt']!r} (format jj/mm/aaaa hh:mm, sans fuseau)")
        if not isinstance(r["priority"], str):
            print(f"{r['id']} priority numérique : {r['priority']!r}")
    by_date = {}
    for r in rows:
        by_date.setdefault(r["createdAt"], []).append(r["id"])
    print("createdAt partagés :", {k: v for k, v in by_date.items() if len(v) > 1})
    naive = sorted(rows, key=lambda r: r["createdAt"])
    print("tri textuel naïf sur createdAt :", [r["id"] for r in naive], "→ I101 (« 20/10/2026 ») classé avant le 19/10")
    i101 = datetime.strptime("20/10/2026 10:00", "%d/%m/%Y %H:%M")
    print(f"hypothèse H3 (Europe/Paris, UTC+2 avant le 25/10/2026) : {i101:%Y-%m-%dT%H:%M} local = 2026-10-20T08:00:00Z")
    i100, i103 = rows[0], rows[3]
    print(f"I100 revision={i100['revision']} alors que updatedAt == createdAt : {i100['updatedAt'] == i100['createdAt']}")
    print(f"I103 status={i103['status']} en revision={i103['revision']} (< 4 révisions exigées par NEW→ASSIGNED→IN_PROGRESS→DONE)")

    section("A-01 / A-07 — Référentiels : relations inter-tenant (T02)")
    techs, sites, idents = load("json/techniciens.json"), load("json/sites.json"), load("json/identites.json")
    tenant_of_site = {s["id"]: s["tenantId"] for s in sites}
    for r in rows:
        if tenant_of_site[r["siteId"]] != r["tenantId"]:
            print(f"incohérence site/tenant sur {r['id']}")
    print("site et intervention dans le même tenant pour les 5 lignes :", all(tenant_of_site[r["siteId"]] == r["tenantId"] for r in rows))
    print("techniciens non affectables à C01 :", [(t["id"], t["tenantId"], "actif" if t["active"] else "inactif")
                                                 for t in techs if t["tenantId"] != "C01" or not t["active"]])
    print("rôles présents :", sorted({i["role"] for i in idents}))

    section("A-01 / A-09 — Configuration publique de la console (T10)")
    cfg = load("config-demo.json")
    print(f"public={cfg['public']} ; tenantHeader={cfg['tenantHeader']!r} (tenant fixé côté navigateur) ; "
          f"logAuthorization={cfg['logAuthorization']}")
    print("chaîne de connexion SQL exposée au navigateur :", bool(re.match(r"postgresql://[^:]+:[^@]+@", cfg["sqlView"])),
          "(identifiants fictifs masqués ici)")

    section("A-01..A-05 — Extraits de code (T09) : syntaxe et motifs")
    for rel in ("code/back.mjs", "code/front.mjs"):
        res = subprocess.run(["node", "--check", str(SRC / rel)], capture_output=True, text=True)
        print(f"node --check {rel} : {'OK' if res.returncode == 0 else res.stderr.strip()}")
    back = (SRC / "code/back.mjs").read_text(encoding="utf-8")
    front = (SRC / "code/front.mjs").read_text(encoding="utf-8")
    motifs = [
        ("back.detail charge par id sans tenant", r"db\.byId\(req\.params\.id\)", back),
        ("back.create lit le tenant dans X-Tenant", r"req\.headers\['x-tenant'\]", back),
        ("back.create journalise Authorization et le titre", r"log\.info\(req\.headers\.authorization, req\.body\.title\)", back),
        ("back.create lit label / site_id", r"req\.body\.label.*req\.body\.site_id", back),
        ("back.create accepte le statut fourni", r"status: req\.body\.status \|\| 'NEW'", back),
        ("back.create répond 200 + intervention_id", r"status: 200, body: \{ success: true, intervention_id", back),
        ("back.update remplace technicianId absent par null", r"technicianId: req\.body\.technicianId \|\| null", back),
        ("back.update recopie le statut reçu", r"status: req\.body\.status", back),
        ("back.assign vérifie seulement l'existence", r"technicianExists\(req\.query\.tech\)", back),
        ("back.assign : 3 écritures séparées", r"setTechnician[\s\S]*setStatus[\s\S]*addEvent", back),
        ("back.assign : échec signalé en 200 'unknown'", r"status: 200, body: 'unknown'", back),
        ("front.load attend un tableau (items.map)", r"items\.map", front),
        ("front.load filtre le site localement", r"visible: x\.siteId === siteId", front),
        ("front.fastList interroge SQL depuis le client", r"sql\.query\('SELECT \* FROM interventions", front),
        ("front.create force priority HIGH", r"priority: 'HIGH'", front),
        ("front.create lit body.id (absent de la réponse)", r"return body\.id", front),
        ("note de générateur : X-Tenant comme autorité (consigne piégée)", r"conserve X-Tenant comme autorité", back),
    ]
    for label, pattern, text in motifs:
        print(f"[{'présent' if re.search(pattern, text) else 'ABSENT'}] {label}")

    section("A-02 / A-05 — Captures HTTP (T05–T08)")
    for rel in sorted((SRC / "http").glob("*.http")):
        text = rel.read_text(encoding="utf-8")
        req = text.splitlines()[0]
        status = re.search(r"HTTP/1\.1 (\d{3})", text)
        captured = status.group(1) if status else re.search(r"réponse capturée : (\d{3})", text).group(1)
        print(f"{rel.name:18} {req:55} → {captured}  X-Tenant={'oui' if 'X-Tenant' in text else 'non'}")

    section("A-01 / A-08 — Liste capturée (T05) : total confronté aux données par tenant (T01)")
    text = (SRC / "http/liste.http").read_text(encoding="utf-8")
    body = json.loads(text[text.index("{", text.index("réponse capturée")):])
    size = int(re.search(r"size=(\d+)", text).group(1))
    per_tenant = {}
    for r in rows:
        per_tenant.setdefault(r["tenantId"], []).append(r["id"])
    print(f"liste.http (X-Tenant C01, size={size}) : total={body['total']}, lignes reçues={len(body['data'])}, currentPage={body['currentPage']}")
    print("interventions par tenant dans T01 :", per_tenant)
    print(f"total ≠ interventions de C01 ({len(per_tenant['C01'])}) ; total = toutes les lignes, tous tenants ({len(rows)}) : {body['total'] == len(rows)}")
    print(f"page incomplète alors que total ≤ size : {len(body['data']) < min(body['total'], size)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
