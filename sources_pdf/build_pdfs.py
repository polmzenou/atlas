"""Génère les PDF du dossier à partir des sources HTML, avec Chrome ou Edge en mode headless.

Usage : python sources_pdf/build_pdfs.py   (depuis la racine du dossier ou depuis sources_pdf/)
"""
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DOCS = ["Rapport_Audit", "Architecture", "Presentation"]
CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "google-chrome", "chromium", "chromium-browser", "msedge",
]


def find_browser():
    for c in CANDIDATES:
        if Path(c).exists() or shutil.which(c):
            return c
    sys.exit("Aucun navigateur Chromium trouvé (Chrome, Edge ou Chromium).")


def main():
    browser = find_browser()
    for name in DOCS:
        src, out = HERE / f"{name}.html", ROOT / f"{name}.pdf"
        cmd = [browser, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
               f"--print-to-pdf={out}", src.as_uri()]
        subprocess.run(cmd, check=True, capture_output=True, timeout=120)
        print(f"{out.name} : {out.stat().st_size // 1024} Ko")


if __name__ == "__main__":
    main()
