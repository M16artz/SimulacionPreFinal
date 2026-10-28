"""Casos calculables a mano y balances independientes del registro de eventos."""
from math import fsum
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch
import yaml
from restaurante.analisis.colas import integrar_escalones, contrastar_little, calcular_colas_y_little, ESTACIONES
from restaurante.dominio.contratos import ConfiguracionRestaurante, GrupoCliente
from restaurante.simulacion.motor import simular


class VerificacionFormulacion(TestCase):
    @classmethod
    def setUpClass(cls):
        raiz = Path(__file__).resolve().parents[2]
        cls.datos = yaml.safe_load((raiz / "configuraciones/ejemplos/sintetica.yaml").read_text(encoding="utf-8"))

    def escenario_controlado(self, mesas=1, preparacion=1, paciencia_segundo=40, simultaneos=False):
        import copy
        datos = copy.deepcopy(self.datos)
        datos.update(mesas=mesas, meseros=1, cocineras=1, apertura=0, cierre=2, llegadas=[{"inicio": 0, "fin": 2, "tasa": 0}])
        for actividad in datos["tiempos"]:
            datos["tiempos"][actividad] = {"tipo": "fija", "valor": 1}
        datos["tiempos"]["preparacion"] = {"tipo": "fija", "valor": preparacion}
        grupos = [GrupoCliente(id=1, personas=1, llegada=0, paciencia=40), GrupoCliente(id=2, personas=1, llegada=0 if simultaneos else 1, paciencia=paciencia_segundo)]
        with patch("restaurante.simulacion.motor.generar_demanda", return_value=grupos):
            return simular(ConfiguracionRestaurante.model_validate(datos), 42)

    def test_integral_exacta_con_intervalos_desiguales(self):
        self.assertEqual(integrar_escalones([(540, 0), (542, 2), (545, 1), (548, 0)], 540, 550), 9)
        self.assertEqual(integrar_escalones([(542, 3)], 540, 550), 24)

    def test_eventos_simultaneos_no_crean_area(self):
        self.assertEqual(integrar_escalones([(0, 0), (1, 7), (1, 2), (3, 0)], 0, 5), 4)

    def test_integral_rechaza_registros_invalidos(self):
        for muestras, inicio, fin in [([(2, 1), (1, 0)], 0, 3), ([(4, 1)], 0, 3), ([(1, -1)], 0, 3), ([(1, float("nan"))], 0, 3), ([], 3, 3)]:
            with self.subTest(muestras=muestras):
                with self.assertRaises(ValueError):
                    integrar_escalones(muestras, inicio, fin)

    def test_cola_de_mesas_y_sistema_calculados_a_mano(self):
        resultado = self.escenario_controlado()
        analisis = resultado.formulacion_matematica
        mesa = next(c for c in analisis.colas if c.estacion == "mesa")
        # G1 permanece [0,5]; G2 espera mesa [1,5] y permanece [1,10].
        self.assertEqual(analisis.fin, 10)
        self.assertEqual(mesa.area_grupo_minutos, 4)
        self.assertEqual(mesa.longitud_media, 0.4)
        self.assertEqual(mesa.espera_media, 2)
        sistema = next(c for c in analisis.little if c.ambito == "sistema")
        self.assertEqual(sistema.longitud_media, 1.4)
        self.assertEqual(sistema.tasa_efectiva, 0.2)
        self.assertEqual(sistema.tiempo_medio, 7)
        self.assertTrue(sistema.coincide)

    def test_esperas_de_pedido_y_cocina_conocidas(self):
        resultado = self.escenario_controlado(mesas=2, preparacion=3, simultaneos=True)
        colas = {c.estacion: c for c in resultado.formulacion_matematica.colas}
        self.assertEqual(colas["pedido"].area_grupo_minutos, 1)
        self.assertEqual(colas["preparacion"].area_grupo_minutos, 2)
        self.assertEqual(colas["mesa"].area_grupo_minutos, 0)
        self.assertTrue(all(c.coincide for c in resultado.formulacion_matematica.little))

    def test_abandonos_no_mezclan_la_cohorte_de_atendidos(self):
        resultado = self.escenario_controlado(paciencia_segundo=1)
        analisis = resultado.formulacion_matematica
        contrastes = {c.ambito: c for c in analisis.little}
        total, atendidos = contrastes["sistema"], contrastes["sistema_atendidos"]
        self.assertEqual(total.longitud_media, 1.2)
        self.assertEqual(total.tasa_efectiva, 0.4)
        self.assertEqual(total.tiempo_medio, 3)
        self.assertEqual(atendidos.longitud_media, 1)
        self.assertEqual(atendidos.tasa_efectiva, 0.2)
        self.assertEqual(atendidos.tiempo_medio, 5)
        self.assertEqual(contrastes["cola_mesa"].numero_entidades, 2)
        self.assertTrue(all(c.coincide for c in contrastes.values()))

    def test_jornada_real_areas_y_permanencias_independientes(self):
        resultado = simular(ConfiguracionRestaurante.model_validate(self.datos), 42)
        atendidos = [g for g in resultado.grupos if g["estado"] == "atendido"]
        for cola in resultado.formulacion_matematica.colas:
            visitantes = resultado.grupos if cola.estacion == "mesa" else atendidos
            clave = "espera_mesa" if cola.estacion == "mesa" else f"espera_{cola.estacion}"
            self.assertAlmostEqual(cola.area_grupo_minutos, fsum(g[clave] for g in visitantes), places=8)
            self.assertAlmostEqual(cola.longitud_media, resultado.metricas[f"longitud_cola_{cola.estacion}_media"])
        for contraste in resultado.formulacion_matematica.little:
            self.assertTrue(contraste.aplicable)
            self.assertTrue(contraste.coincide)
            self.assertLess(contraste.error_absoluto, 1e-8)
        self.assertTrue(all(not resultado.eventos[-1].estado["colas"][e] for e in ESTACIONES))
        self.assertEqual(resultado.eventos[-1].estado["en_sistema"], [])

    def test_jornada_sin_llegadas_no_inventa_W_ni_contraste(self):
        import copy
        datos = copy.deepcopy(self.datos)
        for franja in datos["llegadas"]:
            franja["tasa"] = 0
        resultado = simular(ConfiguracionRestaurante.model_validate(datos), 42)
        for cola in resultado.formulacion_matematica.colas:
            self.assertEqual(cola.longitud_media, 0)
            self.assertIsNone(cola.espera_media)
        for contraste in resultado.formulacion_matematica.little:
            self.assertFalse(contraste.aplicable)
            self.assertIsNone(contraste.tiempo_medio)
            self.assertIsNone(contraste.coincide)
            self.assertIsNone(contraste.producto_lambda_w)

    def test_no_afirma_little_con_cohorte_incompleta(self):
        contraste = contrastar_little("sistema", "Prueba incompleta", 0.6, [2, 4], 0, 10, poblacion_cerrada=False)
        self.assertFalse(contraste.aplicable)
        self.assertIsNone(contraste.coincide)
        self.assertIsNone(contraste.error_absoluto)

    def test_detecta_desacuerdo_en_vez_de_forzar_igualdad(self):
        contraste = contrastar_little("sistema", "Prueba", 100, [2, 4], 0, 10)
        self.assertTrue(contraste.aplicable)
        self.assertFalse(contraste.coincide)
        self.assertAlmostEqual(contraste.producto_lambda_w, 0.6)

    def test_no_reconstruye_silenciosamente_eventos_antiguos(self):
        resultado = self.escenario_controlado()
        resultado.eventos[0].estado.pop("colas")
        with self.assertRaisesRegex(ValueError, "todas las estaciones"):
            calcular_colas_y_little(resultado.eventos, resultado.grupos, 0, 10)
