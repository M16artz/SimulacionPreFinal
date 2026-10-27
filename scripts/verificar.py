"""Ejecuta verificaciones y guarda evidencia de éxitos, fallos y bloqueos."""
import argparse
import ast
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

RAIZ = Path(__file__).resolve().parents[1]


def principal():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    argumentos = argparse.ArgumentParser(description="Verificación por fases del restaurante")
    argumentos.add_argument("--motor", action="store_true", help="Sólo verificaciones que no requieren servidor ni frontend")
    opciones = argumentos.parse_args()
    evidencias = []
    entorno = dict(os.environ)
    entorno["PYTHONPATH"] = str(RAIZ / "backend/src")
    entorno["PYTHONIOENCODING"] = "utf-8"

    def registrar(nombre, estado, detalle):
        evidencias.append({"nombre": nombre, "estado": estado, "detalle": detalle})
        print(f"[{estado.upper()}] {nombre}: {detalle}", flush=True)

    def ejecutar(nombre, comando, carpeta=RAIZ):
        inicio = time.monotonic()
        try:
            resultado = subprocess.run(comando, cwd=carpeta, env=entorno, capture_output=True, text=True, encoding="utf-8", errors="replace")
        except OSError as error:
            registrar(nombre, "bloqueado", str(error))
            return
        detalle = resultado.stdout + resultado.stderr
        if detalle:
            print(detalle, flush=True)
        registrar(nombre, "aprobado" if resultado.returncode == 0 else "fallido", f"Código {resultado.returncode}; {time.monotonic()-inicio:.2f} s")
        evidencias[-1]["salida"] = detalle

    try:
        archivos = list((RAIZ / "backend").rglob("*.py")) + list((RAIZ / "scripts").glob("*.py"))
        for archivo in archivos:
            ast.parse(archivo.read_text(encoding="utf-8"), filename=str(archivo))
        for archivo in (RAIZ / "backend/src/restaurante/dominio").glob("*.py"):
            for nodo in ast.walk(ast.parse(archivo.read_text(encoding="utf-8"))):
                modulos = [n.name for n in nodo.names] if isinstance(nodo, ast.Import) else [nodo.module or ""] if isinstance(nodo, ast.ImportFrom) else []
                if any(modulo.split(".")[0] in ("fastapi", "simpy") for modulo in modulos):
                    raise ValueError(f"El dominio importa una dependencia prohibida: {archivo.name}")
        for archivo in (RAIZ / "frontend/package.json", RAIZ / "frontend/tsconfig.json"):
            json.loads(archivo.read_text(encoding="utf-8"))
        registrar("Sintaxis Python y límites del dominio", "aprobado", f"{len(archivos)} archivos Python y manifiestos JSON")
    except (SyntaxError, ValueError) as error:
        registrar("Sintaxis y arquitectura", "fallido", str(error))

    faltantes = [nombre for nombre in ("pydantic", "simpy", "numpy", "yaml") if importlib.util.find_spec(nombre) is None]
    if faltantes:
        registrar("Motor y servicios", "bloqueado", "Faltan dependencias: " + ", ".join(faltantes))
    else:
        ejecutar("Motor, archivos, procesos y optimización", [sys.executable, "-m", "unittest", "discover", "-s", "backend/tests", "-p", "*sin_pytest.py", "-v"])

    if not opciones.motor:
        node = shutil.which("node")
        if node:
            ejecutar("Servicios TypeScript y reproducción sin navegador", [node, "--test", "tests/logica/servicios.test.mjs"], RAIZ / "frontend")
        else:
            registrar("Servicios TypeScript y reproducción sin navegador", "bloqueado", "No se encontró Node.js 22.18 o posterior")
        faltantes = [nombre for nombre in ("pytest", "fastapi", "scipy", "httpx") if importlib.util.find_spec(nombre) is None]
        if faltantes:
            registrar("Integración Python completa", "bloqueado", "Faltan dependencias: " + ", ".join(faltantes))
        else:
            ejecutar("Pytest completo", [sys.executable, "-m", "pytest", "backend/tests", "-v"])
        npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
        if npm is None or not (RAIZ / "frontend/node_modules/.bin/vite").exists():
            registrar("Frontend y navegador", "bloqueado", "Es necesario instalar las dependencias npm")
        else:
            for nombre, script in (("Vitest", "test"), ("TypeScript y Vite", "build"), ("Playwright", "test:e2e")):
                ejecutar(nombre, [npm, "run", script], RAIZ / "frontend")

    versiones = {"python": sys.version.split()[0]}
    for paquete in ("pydantic", "simpy", "numpy", "scipy", "fastapi", "pytest"):
        try:
            versiones[paquete] = version(paquete)
        except PackageNotFoundError:
            versiones[paquete] = "no instalado"
    informe = {"fecha_utc": datetime.now(timezone.utc).isoformat(), "alcance": "motor" if opciones.motor else "completo", "entorno": versiones, "verificaciones": evidencias}
    destino = RAIZ / "documentacion/evidencia_verificacion.json"
    destino.parent.mkdir(exist_ok=True)
    destino.write_text(json.dumps(informe, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if all(e["estado"] == "aprobado" for e in evidencias) else 1


if __name__ == "__main__":
    raise SystemExit(principal())
