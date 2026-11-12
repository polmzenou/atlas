"""Exécute tous les contrôles et archive leurs sorties réelles dans resultats/.

Usage : python tout_verifier.py   (depuis Tests_et_Validations/, après pip install -r requirements.txt)
Code retour 0 si tous les contrôles réussissent.
"""
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).parent
STEPS = [
    ("01-audit-preuves.txt", ["audit_preuves.py"]),
    ("02-contrat-et-exemples.txt", ["validate_contract.py"]),
    ("03-scenarios.txt", ["run_scenarios.py"]),
    ("04-detection-defauts.txt", ["verifier_detection.py"]),
]


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    (HERE / "resultats").mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    node = subprocess.run(["node", "--version"], capture_output=True, text=True).stdout.strip() or "absent"
    worst = 0
    for name, args in STEPS:
        cmd = [sys.executable, *args]
        res = subprocess.run(cmd, cwd=HERE, capture_output=True, text=True, encoding="utf-8",
                             env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8"})
        header = f"$ python {' '.join(args)}\n# {stamp} | Python {sys.version.split()[0]} | node {node} | code retour {res.returncode}\n\n"
        (HERE / "resultats" / name).write_text(header + res.stdout + res.stderr, encoding="utf-8")
        last = (res.stdout.strip().splitlines() or ["(aucune sortie)"])[-1]
        print(f"{'OK ' if res.returncode == 0 else 'ÉCHEC'} {name:32} {last}")
        worst = max(worst, res.returncode)
    return worst


if __name__ == "__main__":
    sys.exit(main())
