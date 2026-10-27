"""Instala dependencias y captura versiones reales; nunca inventa un bloqueo.

Ejecutar con Python desde la raíz: python scripts/preparar.py
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

RAIZ = Path(__file__).resolve().parents[1]


def ejecutar(argumentos, carpeta=RAIZ):
    print("Ejecutando:", " ".join(map(str, argumentos)), flush=True)
    subprocess.run(list(map(str, argumentos)), cwd=carpeta, check=True)


def principal():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    argumentos = argparse.ArgumentParser(description="Preparar el simulador y registrar versiones resueltas")
    argumentos.add_argument("--navegador", action="store_true", help="Instalar también Chromium para las pruebas")
    opciones = argumentos.parse_args()
    if sys.version_info < (3, 11):
        argumentos.error("Se necesita Python 3.11 o posterior")
    python = RAIZ / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    try:
        if not python.exists():
            ejecutar([sys.executable, "-m", "venv", RAIZ / ".venv"])
        bloqueo = RAIZ / "backend/requirements.lock"
        if bloqueo.exists():
            ejecutar([python, "-m", "pip", "install", "-r", bloqueo])
        ejecutar([python, "-m", "pip", "install", "-e", ".[pruebas]"], RAIZ / "backend")
        congelado = subprocess.check_output([str(python), "-m", "pip", "freeze", "--exclude-editable"], cwd=RAIZ, text=True, encoding="utf-8")
        bloqueo.write_text("# Versiones instaladas por scripts/preparar.py\n" + congelado, encoding="utf-8")
        npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
        if npm is None:
            argumentos.error("No se encontró npm. Instale Node.js 22 o posterior")
        ejecutar([npm, "ci" if (RAIZ / "frontend/package-lock.json").exists() else "install", "--cache", str(RAIZ / "frontend/.npm-cache")], RAIZ / "frontend")
        if opciones.navegador:
            npx = shutil.which("npx.cmd" if os.name == "nt" else "npx")
            if npx is None:
                argumentos.error("No se encontró npx")
            ejecutar([npx, "playwright", "install", "chromium"], RAIZ / "frontend")
        entorno = subprocess.check_output([str(python), "-c", "import sys,json;print(json.dumps({'python':sys.version}))"], text=True)
        (RAIZ / "documentacion/entorno_instalado.json").write_text(json.dumps(json.loads(entorno), indent=2), encoding="utf-8")
        print("Dependencias instaladas; versiones registradas en requirements.lock y package-lock.json.")
    except (subprocess.CalledProcessError, OSError) as error:
        print(f"No se pudo completar la preparación: {error}", file=sys.stderr)
        print("Los bloqueos sólo se escriben después de una resolución o instalación exitosa.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(principal())
