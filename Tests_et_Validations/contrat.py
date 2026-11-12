"""Chargement du contrat et validation JSON Schema 2020-12 de ses composants."""
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

ROOT = Path(__file__).resolve().parent.parent
CONTRACT_PATH = ROOT / "Contrat_API.yaml"
BASE_URI = "urn:atlas:contrat"


def load_contract():
    return yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))


class Contract:
    def __init__(self):
        self.doc = load_contract()
        resource = Resource.from_contents(self.doc, default_specification=DRAFT202012)
        self.registry = Registry().with_resource(BASE_URI, resource)
        self.operations = {}
        for path, item in self.doc["paths"].items():
            for method, op in item.items():
                if isinstance(op, dict) and "operationId" in op:
                    self.operations[op["operationId"]] = (method.upper(), path, op)

    def deref(self, node):
        while isinstance(node, dict) and "$ref" in node:
            cur = self.doc
            for part in node["$ref"].lstrip("#/").split("/"):
                cur = cur[part]
            node = cur
        return node

    def validator(self, schema):
        """Valide contre un sous-schéma ; les $ref internes sont résolus via BASE_URI."""
        return Draft202012Validator({"$ref": BASE_URI + "#" + schema} if isinstance(schema, str) else
                                    {"$schema": "https://json-schema.org/draft/2020-12/schema",
                                     "$id": "urn:atlas:inline", "allOf": [self._rebase(schema)]},
                                    registry=self.registry)

    def _rebase(self, node):
        if isinstance(node, dict):
            return {k: (BASE_URI + v if k == "$ref" and v.startswith("#") else self._rebase(v)) for k, v in node.items()}
        if isinstance(node, list):
            return [self._rebase(v) for v in node]
        return node

    def component(self, name):
        return self.validator(f"/components/schemas/{name}")

    def response(self, operation_id, status):
        """(media_type, validator, déclaration) de la réponse documentée, ou None."""
        _, _, op = self.operations[operation_id]
        resp = op["responses"].get(str(status))
        if resp is None:
            return None
        resp = self.deref(resp)
        content = resp.get("content", {})
        media, spec = next(iter(content.items())) if content else (None, None)
        return media, (self.validator(spec["schema"]) if spec else None), resp

    @staticmethod
    def errors(validator, instance):
        return [f"{'/'.join(map(str, e.absolute_path)) or '(racine)'}: {e.message}"
                for e in validator.iter_errors(instance)]
