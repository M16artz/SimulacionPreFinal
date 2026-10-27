"""Verificación ejecutable también con unittest y las dependencias del motor.

Desde la raíz: python -m unittest discover -s backend/tests -p test_motor_sin_pytest.py -v
El paquete restaurante debe estar instalado o presente en PYTHONPATH.
"""
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch
import math
import numpy as np
import simpy
import yaml
from pydantic import ValidationError
from restaurante.dominio.contratos import ConfiguracionRestaurante, GrupoCliente, ResultadoSimulacion
from restaurante.simulacion.motor import simular
from restaurante.simulacion.generador_llegadas import generar_demanda
from restaurante.simulacion.gestor_mesas import GestorMesas


class VerificacionMotor(TestCase):
    @classmethod
    def setUpClass(cls):
        raiz = Path(__file__).resolve().parents[2]
        cls.configuracion = ConfiguracionRestaurante.model_validate(yaml.safe_load((raiz / "configuraciones/ejemplos/sintetica.yaml").read_text(encoding="utf-8")))
        cls.resultado = simular(cls.configuracion, 42)

    def test_reproduccion_exacta(self):
        self.assertEqual(self.resultado, simular(self.configuracion, 42))

    def test_semillas_diferentes(self):
        self.assertNotEqual(self.resultado.grupos, simular(self.configuracion, 43).grupos)

    def test_serializacion_completa(self):
        self.assertEqual(ResultadoSimulacion.model_validate_json(self.resultado.model_dump_json()), self.resultado)

    def test_contabilidad_personas_y_grupos(self):
        m = self.resultado.metricas
        self.assertEqual(m["personas_llegadas"], m["personas_atendidas"] + m["personas_abandonadas"])
        self.assertEqual(m["grupos_llegados"], m["grupos_atendidos"] + m["grupos_abandonados"])
        self.assertEqual(m["grupos_atendidos"], self.resultado.eventos[-1].estado["atendidos"])

    def test_mesas_exclusivas_y_grandes_atomicos(self):
        activas = {}
        por_id = {g["id"]: g for g in self.resultado.grupos}
        for evento in self.resultado.eventos:
            if evento.accion == "asignacion_mesas":
                self.assertEqual(len(evento.recursos), 2 if por_id[evento.entidad]["personas"] >= 5 else 1)
                for recurso in evento.recursos:
                    self.assertNotIn(recurso, activas)
                    activas[recurso] = evento.entidad
            elif evento.accion == "salida":
                for recurso in evento.recursos:
                    self.assertEqual(activas.pop(recurso), evento.entidad)
        self.assertFalse(activas)

    def test_personal_exclusivo_y_capacidades(self):
        activos = {}
        for evento in self.resultado.eventos:
            for recurso in evento.recursos:
                if recurso.startswith("mesa-"):
                    continue
                if evento.accion.startswith("inicio_"):
                    self.assertNotIn(recurso, activos)
                    activos[recurso] = evento.entidad
                elif evento.accion.startswith("fin_"):
                    self.assertEqual(activos.pop(recurso), evento.entidad)
            self.assertLessEqual(sum(r.startswith("mesero-") for r in activos), self.configuracion.meseros)
            self.assertLessEqual(sum(r.startswith("cocinera-") for r in activos), self.configuracion.cocineras)
        self.assertFalse(activos)

    def test_mesas_se_liberan_tras_pago(self):
        pagos = set()
        for evento in self.resultado.eventos:
            if evento.accion == "fin_cobro":
                pagos.add(evento.entidad)
            elif evento.accion == "salida":
                self.assertIn(evento.entidad, pagos)

    def test_abandonos_no_se_asignan(self):
        abandonos = {g["id"] for g in self.resultado.grupos if g["estado"] == "abandono"}
        sentados = {e.entidad for e in self.resultado.eventos if e.accion == "asignacion_mesas"}
        self.assertFalse(abandonos & sentados)
        self.assertFalse(self.resultado.eventos[-1].estado["cola"])

    def test_cierre_y_utilizacion(self):
        self.assertTrue(all(self.configuracion.apertura <= g["llegada"] < self.configuracion.cierre for g in self.resultado.grupos))
        self.assertGreaterEqual(self.resultado.metricas["fin_jornada"], self.configuracion.cierre)
        self.assertTrue(all(0 <= r["utilizacion"] <= 1 + 1e-12 for r in self.resultado.recursos))

    def test_compatibilidad_sin_fifo_y_cancelacion(self):
        gestor = GestorMesas(simpy.Environment(), [4, 4])
        primera = gestor.solicitar(4)
        grande = gestor.solicitar(8)
        pequeno = gestor.solicitar(2)
        self.assertTrue(pequeno.triggered)
        self.assertFalse(grande.triggered)
        gestor.liberar(primera.value)
        self.assertFalse(grande.triggered)
        gestor.cancelar(grande)
        otra = gestor.solicitar(8)
        gestor.liberar(pequeno.value)
        self.assertTrue(otra.triggered)
        self.assertEqual(len(otra.value), 2)
        self.assertFalse(gestor.pendientes)

    def test_demanda_compartida_y_frecuencias(self):
        datos = self.configuracion.model_dump()
        datos["mesas"] = 20
        otra = ConfiguracionRestaurante.model_validate(datos)
        self.assertEqual(generar_demanda(self.configuracion, 42), generar_demanda(otra, 42))
        grupos = [g for semilla in range(100) for g in generar_demanda(self.configuracion, semilla)]
        observadas = np.bincount([g.personas for g in grupos], minlength=9)[1:]
        for n, p in zip(observadas, self.configuracion.probabilidades_grupo):
            self.assertLess(abs(n - p * len(grupos)), 5 * math.sqrt(len(grupos) * p * (1 - p)))

    def test_poisson_por_franjas_y_sin_llegadas_al_cierre(self):
        grupos = [g for semilla in range(100) for g in generar_demanda(self.configuracion, semilla)]
        for franja in self.configuracion.llegadas:
            observados = sum(franja.inicio <= g.llegada < franja.fin for g in grupos)
            esperados = 100 * franja.tasa * (franja.fin - franja.inicio) / 60
            self.assertLess(abs(observados - esperados), 5 * math.sqrt(esperados))
        self.assertTrue(all(g.llegada < self.configuracion.cierre for g in grupos))

    def test_pendientes_y_validacion_central(self):
        datos = self.configuracion.model_dump()
        datos["tiempos"]["pedido"] = None
        pendiente = ConfiguracionRestaurante.model_validate(datos)
        with self.assertRaisesRegex(ValueError, "pedido"):
            simular(pendiente, 42)
        datos["probabilidades_grupo"] = [0.2] * 8
        with self.assertRaises(ValidationError):
            ConfiguracionRestaurante.model_validate(datos)

    def test_pago_despues_del_cierre_y_pedido_grupal(self):
        datos = self.configuracion.model_dump()
        datos.update(mesas=3, cierre=541, llegadas=[{"inicio": 540, "fin": 541, "tasa": 1}])
        for actividad in datos["tiempos"]:
            datos["tiempos"][actividad] = {"tipo": "fija", "valor": 10}
        grupos = [GrupoCliente(id=1, personas=1, llegada=540.1, paciencia=40), GrupoCliente(id=2, personas=8, llegada=540.2, paciencia=40)]
        with patch("restaurante.simulacion.motor.generar_demanda", return_value=grupos):
            resultado = simular(ConfiguracionRestaurante.model_validate(datos), 42)
        self.assertEqual([g["duracion_preparacion"] for g in resultado.grupos], [10, 10])
        self.assertGreater(resultado.metricas["fin_jornada"], 541)
