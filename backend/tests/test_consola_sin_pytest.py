"""Recorrido de consola real, sin servidor ni framework de pruebas externo."""
import csv
from io import StringIO
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from unittest import TestCase


class VerificacionConsola(TestCase):
    def setUp(self):
        self.raiz = Path(__file__).resolve().parents[2]
        (self.raiz / "datos").mkdir(exist_ok=True)
        self.temporal = TemporaryDirectory(dir=self.raiz / "datos")
        self.addCleanup(self.temporal.cleanup)
        self.entorno = dict(os.environ, PYTHONPATH=str(self.raiz / "backend/src"), PYTHONIOENCODING="utf-8")

    def ejecutar(self, *argumentos):
        return subprocess.run([sys.executable, "-m", "restaurante.consola", *map(str, argumentos)], cwd=self.raiz, env=self.entorno, capture_output=True, text=True, encoding="utf-8", timeout=30)

    def test_consola_exporta_json_csv_y_crea_carpetas(self):
        salida = Path(self.temporal.name) / "subcarpeta/resultado.json"
        csv_salida = Path(self.temporal.name) / "tablas/grupos.csv"
        respuesta = self.ejecutar("configuraciones/ejemplos/sintetica.yaml", "--semilla", "42", "--salida", salida, "--csv", csv_salida)
        self.assertEqual(respuesta.returncode, 0, respuesta.stderr)
        resultado = json.loads(salida.read_text(encoding="utf-8"))
        self.assertEqual(resultado["semilla"], 42)
        self.assertEqual(json.loads(respuesta.stdout), resultado["metricas"])
        filas = list(csv.DictReader(StringIO(csv_salida.read_text(encoding="utf-8-sig"))))
        self.assertEqual(len(filas), resultado["metricas"]["grupos_llegados"])
        self.assertEqual(sum(fila["estado"] == "abandono" for fila in filas), resultado["metricas"]["grupos_abandonados"])

    def test_referencia_pendiente_no_genera_resultado(self):
        salida = Path(self.temporal.name) / "resultado.json"
        respuesta = self.ejecutar("configuraciones/referencia.yaml", "--salida", salida)
        self.assertEqual(respuesta.returncode, 2)
        self.assertIn("Faltan tiempos por aprobar", respuesta.stderr)
        self.assertFalse(salida.exists())

    def test_archivo_inexistente_sin_traza_interna(self):
        respuesta = self.ejecutar(Path(self.temporal.name) / "no-existe.yaml")
        self.assertEqual(respuesta.returncode, 2)
        self.assertNotIn("Traceback", respuesta.stderr)

    def test_yaml_invalido_sin_traza_interna(self):
        archivo = Path(self.temporal.name) / "invalido.yaml"
        archivo.write_text("tiempos: [", encoding="utf-8")
        respuesta = self.ejecutar(archivo)
        self.assertEqual(respuesta.returncode, 2)
        self.assertNotIn("Traceback", respuesta.stderr)
