"""Pruebas del flujo real de archivos, procesos, exportaciones y optimización."""
from concurrent.futures import Future, ThreadPoolExecutor
import csv
from io import StringIO
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Barrier
import time
from unittest import TestCase
import yaml
from restaurante.analisis.optimizacion import expandir_configuraciones, identificar_eficientes, calcular_sensibilidad
from restaurante.aplicacion.trabajos import GestorTrabajos, ColaLlenaError, TrabajadorNoDisponibleError
from restaurante.dominio.contratos import ConfiguracionRestaurante, SolicitudExperimento, Rango
from restaurante.infraestructura.exportaciones import serializar_csv, serializar_json, filas_experimento
from restaurante.infraestructura.persistencia import AlmacenArchivos


def escenario(identificador, mesas=11, meseros=1, cocineras=3, espera=10, abandono=0.2, personas=100, **otros):
    return {"id": identificador, "nombre": f"Escenario {identificador}", "configuracion": {"mesas": mesas, "meseros": meseros, "cocineras": cocineras, **otros}, "resumen": {clave: {"media": valor, "ic95": None, "replicas": 1} for clave, valor in {"espera_mesa_media": espera, "tasa_abandono": abandono, "personas_atendidas": personas}.items()}}


class VerificacionOptimizacion(TestCase):
    def test_dominancia_en_todos_los_objetivos(self):
        escenarios = [escenario(0), escenario(1, mesas=12), escenario(2, espera=8, meseros=2), escenario(3, espera=9, abandono=0.1)]
        identificar_eficientes(escenarios)
        self.assertEqual([e["eficiente"] for e in escenarios], [False, False, True, True])

    def test_duplicados_no_se_dominan_entre_si(self):
        escenarios = identificar_eficientes([escenario(0), escenario(1)])
        self.assertTrue(all(e["eficiente"] for e in escenarios))

    def test_sensibilidad_respeta_las_otras_hipotesis(self):
        escenarios = [escenario(0, tiempos={"pedido": 2}), escenario(1, mesas=13, espera=6, abandono=0.1, personas=120, tiempos={"pedido": 2}), escenario(2, mesas=15, espera=4, tiempos={"pedido": 3})]
        sensibilidad = calcular_sensibilidad(escenarios)
        self.assertEqual(len(sensibilidad), 1)
        diferencia = sensibilidad[0]
        self.assertEqual((diferencia["recurso"], diferencia["desde"], diferencia["hasta"]), ("mesas", 0, 1))
        self.assertEqual(diferencia["cambios_por_unidad"]["espera_mesa_media"], -2)
        self.assertEqual(diferencia["cambios_por_unidad"]["personas_atendidas"], 10)

    def test_sensibilidad_utiliza_vecinos_y_no_duplica(self):
        sensibilidad = calcular_sensibilidad([escenario(0, mesas=9), escenario(1, mesas=11), escenario(2, mesas=13), escenario(3, mesas=11)])
        self.assertEqual(len(sensibilidad), 2)
        self.assertEqual([s["incremento"] for s in sensibilidad], [2, 2])

    def test_expansion_de_rangos_es_un_producto_cartesiano(self):
        raiz = Path(__file__).resolve().parents[2]
        configuracion = ConfiguracionRestaurante.model_validate(yaml.safe_load((raiz / "configuraciones/ejemplos/sintetica.yaml").read_text(encoding="utf-8")))
        solicitud = SolicitudExperimento(configuraciones=[configuracion], rangos={"mesas": Rango(minimo=9, maximo=13, paso=2), "meseros": Rango(minimo=1, maximo=2, paso=1)})
        combinaciones = expandir_configuraciones(solicitud)
        self.assertEqual({(c.mesas, c.meseros) for c in combinaciones}, {(9, 1), (9, 2), (11, 1), (11, 2), (13, 1), (13, 2)})
        self.assertEqual(configuracion.mesas, 11)
        self.assertIsNot(combinaciones[0], configuracion)


class AlmacenTemporal:
    def setUp(self):
        carpeta = Path(__file__).resolve().parents[2] / "datos"
        carpeta.mkdir(exist_ok=True)
        self.temporal = TemporaryDirectory(dir=carpeta)
        self.addCleanup(self.temporal.cleanup)
        self.almacen = AlmacenArchivos(self.temporal.name)


class VerificacionArchivos(AlmacenTemporal, TestCase):
    def test_snapshot_y_reemplazo_atomico(self):
        original = {"configuracion": {"nombre": "Versión inicial"}}
        identificador = self.almacen.guardar("configuraciones", original)
        original["configuracion"]["nombre"] = "Cambio externo"
        self.assertEqual(self.almacen.leer("configuraciones", identificador)["configuracion"]["nombre"], "Versión inicial")
        self.almacen.guardar("configuraciones", original, identificador)
        self.assertEqual(self.almacen.listar("configuraciones")[0]["id"], identificador)
        self.assertFalse(list(Path(self.temporal.name).rglob("*.tmp")))

    def test_rechaza_rutas_y_valores_no_finitos(self):
        with self.assertRaises(ValueError):
            self.almacen.leer("configuraciones", "../archivo")
        with self.assertRaises(ValueError):
            self.almacen.guardar("../otra-carpeta", {})
        with self.assertRaises(ValueError):
            self.almacen.guardar("simulaciones", {"invalido": float("nan")})

    def test_csv_con_campos_heterogeneos_y_unicode(self):
        filas = [{"id": 1, "mesas": ["mesa-1", "mesa-2"], "nombre": "Atención"}, {"id": 2, "abandono": True}]
        texto = serializar_csv(filas)
        self.assertTrue(texto.startswith("\ufeff"))
        leidas = list(csv.DictReader(StringIO(texto.removeprefix("\ufeff"))))
        self.assertEqual(json.loads(leidas[0]["mesas"]), ["mesa-1", "mesa-2"])
        self.assertEqual(leidas[0]["nombre"], "Atención")
        self.assertEqual(leidas[1]["mesas"], "")

    def test_csv_experimento_con_intervalos_y_sin_intervalos(self):
        uno = escenario(0)
        uno["eficiente"] = True
        dos = escenario(1)
        dos["eficiente"] = False
        dos["resumen"]["espera_mesa_media"]["ic95"] = [8, 12]
        filas = filas_experimento({"escenarios": [uno, dos]})
        self.assertIsNone(filas[0]["espera_mesa_media_inferior"])
        self.assertEqual(filas[1]["espera_mesa_media_superior"], 12)
        self.assertEqual(json.loads(serializar_json({"nombre": "Réplicas"}))["nombre"], "Réplicas")


class EjecutorControlado:
    """Doble de la frontera del ejecutor para probar admisión concurrente."""
    def __init__(self, fallar=False):
        self.futuros = []
        self.fallar = fallar

    def submit(self, *argumentos):
        if self.fallar:
            raise RuntimeError("Ejecutor cerrado")
        futuro = Future()
        self.futuros.append(futuro)
        return futuro

    def shutdown(self, wait=True):
        pass


class VerificacionTrabajos(AlmacenTemporal, TestCase):
    def configuracion(self):
        raiz = Path(__file__).resolve().parents[2]
        return yaml.safe_load((raiz / "configuraciones/ejemplos/sintetica.yaml").read_text(encoding="utf-8"))

    def test_admision_concurrente_no_supera_limite(self):
        ejecutor = EjecutorControlado()
        gestor = GestorTrabajos(self.almacen, limite=3, ejecutor=ejecutor)
        barrera = Barrier(12)
        def crear(_):
            barrera.wait(timeout=10)
            try:
                gestor.crear("simulaciones", {"configuracion": {}, "semilla": 1})
                return True
            except ColaLlenaError:
                return False
        with ThreadPoolExecutor(max_workers=12) as clientes:
            admitidos = list(clientes.map(crear, range(12)))
        self.assertEqual(sum(admitidos), 3)
        self.assertEqual(len(self.almacen.listar("simulaciones")), 3)

    def test_fallo_de_envio_y_fallo_del_trabajador(self):
        gestor = GestorTrabajos(self.almacen, ejecutor=EjecutorControlado(fallar=True))
        with self.assertRaises(TrabajadorNoDisponibleError):
            gestor.crear("simulaciones", {})
        self.assertEqual(self.almacen.listar("simulaciones")[0]["estado"], "error")
        ejecutor = EjecutorControlado()
        gestor = GestorTrabajos(self.almacen, ejecutor=ejecutor)
        trabajo = gestor.crear("simulaciones", {})
        ejecutor.futuros[0].set_exception(RuntimeError("Terminación inesperada"))
        self.assertEqual(self.almacen.leer("simulaciones", trabajo["id"])["estado"], "error")

    def test_recuperar_interrumpidos_conserva_completados(self):
        pendiente = self.almacen.guardar("simulaciones", {"estado": "ejecutando", "solicitud": {"semilla": 42}})
        completado = self.almacen.guardar("simulaciones", {"estado": "completado", "resultado": {"prueba": True}})
        gestor = GestorTrabajos(self.almacen, ejecutor=EjecutorControlado())
        gestor.recuperar_interrumpidos()
        self.assertEqual(self.almacen.leer("simulaciones", pendiente)["estado"], "error")
        self.assertEqual(self.almacen.leer("simulaciones", completado)["resultado"], {"prueba": True})

    def test_simulacion_en_proceso_separado_y_snapshot(self):
        gestor = GestorTrabajos(self.almacen)
        self.addCleanup(gestor.cerrar)
        configuracion = self.configuracion()
        trabajo = gestor.crear("simulaciones", {"configuracion": configuracion, "semilla": 42})
        configuracion["mesas"] = 80
        limite = time.monotonic() + 30
        while time.monotonic() < limite:
            guardado = self.almacen.leer("simulaciones", trabajo["id"])
            if guardado["estado"] in ("completado", "error"):
                break
            time.sleep(0.02)
        self.assertEqual(guardado["estado"], "completado", guardado)
        self.assertNotEqual(guardado["pid_proceso"], os.getpid())
        self.assertEqual(guardado["resultado"]["configuracion"]["mesas"], 11)
        self.assertEqual(guardado["progreso"], {"completadas": 1, "total": 1})
        self.assertEqual(guardado["resultado"]["metricas"]["grupos_llegados"], 158)
