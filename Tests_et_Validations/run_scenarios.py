"""Rejoue les scénarios sur le simulateur et produit les preuves.

Sorties :
  - SCENARIOS.md                      rapport lisible (requêtes, réponses obtenues, verdicts)
  - resultats/scenarios-resultats.json  données brutes
Code retour 0 si toutes les vérifications passent.

Contrôles automatiques pour chaque réponse v2 : statut documenté pour l'opération,
type de contenu, conformité au schéma du contrat, en-têtes déclarés présents et
conformes. Les routes v1 ne sont pas décrites par le contrat v2 : leurs réponses
sont vérifiées par les assertions explicites des scénarios uniquement.
"""
import json
import sys
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

from atlas_mock import AtlasMock
from contrat import ROOT, Contract
from scenarios import SCENARIOS

HERE = Path(__file__).parent
OPTIONAL_HEADERS = {"Idempotent-Replayed"}
SHOWN_HEADERS = ("Content-Type", "Location", "ETag", "WWW-Authenticate", "Idempotent-Replayed", "X-Correlation-Id")


def http_request(st, headers, payload):
    lines = [f"{st['method']} {st['target_resolved']} HTTP/1.1", "Host: api.atlas.invalid"]
    lines += [f"{k}: {v}" for k, v in headers.items()]
    if payload is not None:
        lines += ["", payload]
    return "\n".join(lines)


def http_response(resp):
    lines = [f"HTTP/1.1 {resp.status}"] + [f"{h}: {resp.headers[h]}" for h in SHOWN_HEADERS if h in resp.headers]
    if resp.body is not None:
        lines += ["", json.dumps(resp.body, ensure_ascii=False, indent=2)]
    return "\n".join(lines)


def without_corr(body):
    return {k: v for k, v in body.items() if k != "correlationId"} if isinstance(body, dict) else body


def run_step(contract, mock, st, ctx, previous):
    headers = {}
    if st["token"]:
        headers["Authorization"] = f"Bearer {st['token']}"
    payload = st["raw_body"] if st["raw_body"] is not None else (json.dumps(st["body"], ensure_ascii=False) if st["body"] is not None else None)
    if payload is not None:
        headers["Content-Type"] = st["content_type"]
    headers.update({k: v for k, v in st["headers"].items() if not k.startswith("_")})
    st["target_resolved"] = st["target"].format(**ctx)
    resp = mock.handle(st["method"], st["target_resolved"], headers, payload)
    operation = mock.log[-1]["operation"]
    checks = [(f"statut {st['status']}", resp.status == st["status"])]
    if st["code"]:
        checks.append((f"code {st['code']}", isinstance(resp.body, dict) and resp.body.get("code") == st["code"]))
    if st["field"]:
        got = [[e["field"], e["code"]] for e in (resp.body or {}).get("errors", [])]
        checks.append((f"erreur de champ {st['field'][0]}={st['field'][1]}", st["field"] in got))
    if not operation.startswith("v1.") and operation != "unknown":
        declared = contract.response(operation, resp.status)
        checks.append((f"statut {resp.status} documenté pour {operation}", declared is not None))
        if declared:
            media, validator, decl = declared
            checks.append((f"Content-Type {media}", resp.headers.get("Content-Type") == media))
            errs = contract.errors(validator, resp.body) if validator else []
            checks.append(("corps conforme au schéma du contrat" + (f" — {errs}" if errs else ""), not errs))
            for name, hdr in decl.get("headers", {}).items():
                if name in OPTIONAL_HEADERS and name not in resp.headers:
                    continue
                hdr = contract.deref(hdr)
                present = name in resp.headers
                ok = present and not contract.errors(contract.validator(hdr["schema"]), resp.headers[name])
                checks.append((f"en-tête {name} déclaré, présent et conforme", ok))
    if st["example"]:
        expected = json.loads((ROOT / "Exemples_JSON" / st["example"]).read_text(encoding="utf-8"))
        checks.append((f"corps identique à Exemples_JSON/{st['example']}", resp.body == expected))
    if st["headers"].get("_compare_previous") and previous is not None:
        checks.append(("réponse identique à l'étape précédente (hors correlationId)",
                       without_corr(resp.body) == without_corr(previous.body) and resp.status == previous.status))
    for label, fn in st["checks"]:
        try:
            ok = bool(fn(resp, mock))
        except Exception as exc:  # une assertion qui lève est un échec, pas un crash du lanceur
            ok, label = False, f"{label} (exception : {exc!r})"
        checks.append((label, ok))
    if st["headers"].get("_save_cursor") and isinstance(resp.body, dict):
        ctx["cursor"] = resp.body["page"]["nextCursor"]
    return resp, operation, checks, http_request(st, headers, payload)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    contract = Contract()
    env = (f"Python {sys.version.split()[0]}, jsonschema {version('jsonschema')}, PyYAML {version('pyyaml')} — "
           f"exécuté le {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    md = ["# Scénarios de validation — résultats d'exécution", "",
          "> **Document généré** par `python run_scenarios.py` ; ne pas éditer à la main.",
          f"> Environnement : {env}.",
          "> **Nature de la preuve : simulation.** Les réponses proviennent de `atlas_mock.py` (implémentation",
          "> en mémoire, sans réseau ni base). Elles prouvent que le contrat est cohérent, réalisable et",
          "> que ses exemples concordent ; elles ne prouvent pas le comportement du futur serveur ATLAS.", "",
          "| Id | Catégorie imposée | Titre | Exigences | Verdict |", "|---|---|---|---|---|"]
    detail, raw, total_fail = [], [], 0
    for sc in SCENARIOS:
        mock = AtlasMock()
        before = mock.snapshot()
        ctx, previous, steps_out, sc_ok = {}, None, [], True
        detail += ["", f"## {sc['id']} — {sc['title']}", "",
                   f"- **Catégorie** : {sc['category']}",
                   f"- **Opération(s)** : {sc['operation']}",
                   f"- **Exigences / incidents** : {sc['requirements']}",
                   f"- **Décision(s)** : {sc['decision']} (voir Decisions_Techniques.md)",
                   f"- **Préconditions** : {sc['preconditions']}"]
        for i, st in enumerate(sc["steps"], 1):
            resp, op, checks, req_text = run_step(contract, mock, st, ctx, previous)
            previous = resp
            ok = all(c[1] for c in checks)
            sc_ok &= ok
            detail += ["", f"### Étape {i} — {st['label']} : {'✅ conforme' if ok else '❌ ÉCHEC'}", "",
                       "Requête :", "", "```http", req_text, "```", "",
                       "Réponse obtenue :", "", "```http", http_response(resp), "```", "",
                       "Vérifications :", ""] + [f"- {'✅' if c[1] else '❌'} {c[0]}" for c in checks]
            steps_out.append({"label": st["label"], "operation": op, "request": req_text,
                              "response": resp.to_dict(), "checks": [{"label": c[0], "ok": c[1]} for c in checks]})
            for label, good in checks:
                if not good:
                    print(f"  ❌ {sc['id']} étape {i} : {label}")
        effect_label, effect_fn = sc["effect"]
        effect_ok = (mock.snapshot() == before) if effect_fn is None else bool(effect_fn(mock))
        sc_ok &= effect_ok
        if not effect_ok:
            print(f"  ❌ {sc['id']} effet persistant : {effect_label}")
        detail += ["", f"**Effet persistant attendu** : {effect_label} — {'✅ vérifié' if effect_ok else '❌ non vérifié'}"
                   + (" (état comparé avant/après)" if effect_fn is None else ""),
                   "", f"**Réaction attendue du Front-End** : {sc['front']}"]
        total_fail += 0 if sc_ok else 1
        md.append(f"| [{sc['id']}](#{sc['id'].lower()}) | {sc['category']} | {sc['title']} | {sc['requirements']} | {'✅' if sc_ok else '❌'} |")
        raw.append({"id": sc["id"], "ok": sc_ok, "effect": {"label": effect_label, "ok": effect_ok}, "steps": steps_out})
        print(f"{'✅' if sc_ok else '❌'} {sc['id']} {sc['title']}")
    nb_steps = sum(len(s["steps"]) for s in SCENARIOS)
    md += ["", f"**Bilan : {len(SCENARIOS) - total_fail}/{len(SCENARIOS)} scénarios conformes, {nb_steps} requêtes rejouées.**"]
    (HERE / "SCENARIOS.md").write_text("\n".join(md + detail) + "\n", encoding="utf-8")
    (HERE / "resultats").mkdir(exist_ok=True)
    (HERE / "resultats" / "scenarios-resultats.json").write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nBILAN : {len(SCENARIOS) - total_fail}/{len(SCENARIOS)} scénarios conformes ({nb_steps} requêtes).")
    return 0 if total_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
