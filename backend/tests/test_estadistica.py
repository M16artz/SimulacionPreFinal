import numpy as np
import math
import pytest
from scipy.stats import chisquare
from restaurante.simulacion.generador_llegadas import generar_demanda
from restaurante.analisis.estadistica import resumir
from restaurante.analisis.experimentos import ejecutar_experimento
from restaurante.dominio.contratos import SolicitudExperimento, ConfiguracionRestaurante, Rango


def test_frecuencias_tamanos_y_poisson_por_franjas(configuracion):
    grupos = [g for semilla in range(200) for g in generar_demanda(configuracion, semilla)]
    frecuencias = np.bincount([g.personas for g in grupos], minlength=9)[1:]
    esperadas = np.array(configuracion.probabilidades_grupo) * len(grupos)
    # Umbral conservador y semillas fijas: detecta desviaciones sin pruebas frágiles.
    assert chisquare(frecuencias, esperadas).pvalue > 1e-6
    for franja in configuracion.llegadas:
        observados = sum(franja.inicio <= g.llegada < franja.fin for g in grupos)
        esperados = 200 * franja.tasa * (franja.fin - franja.inicio) / 60
        assert abs(observados - esperados) < 5 * np.sqrt(esperados)
    assert all(g.llegada < configuracion.cierre for g in grupos)


def test_demanda_comun_entre_recursos(configuracion):
    datos = configuracion.model_dump()
    datos.update(mesas=15, meseros=3, cocineras=4)
    assert generar_demanda(configuracion, 123) == generar_demanda(ConfiguracionRestaurante.model_validate(datos), 123)


def test_replicas_pareadas_pareto_y_reproducibilidad(breve):
    solicitud = SolicitudExperimento(configuraciones=[breve], replicas=3, semilla=42, rangos={"meseros": Rango(minimo=1, maximo=2, paso=1)})
    progreso = []
    primero = ejecutar_experimento(solicitud, informar_progreso=lambda completadas, total: progreso.append((completadas, total)))
    assert primero == ejecutar_experimento(solicitud)
    assert len(set(primero.semillas_replicas)) == 3
    assert len(primero.escenarios) == 2
    assert len(primero.diferencias_pareadas) == 1
    assert any(e["eficiente"] for e in primero.escenarios)
    assert [r["grupos_llegados"] for r in primero.escenarios[0]["replicas"]] == [r["grupos_llegados"] for r in primero.escenarios[1]["replicas"]]
    assert resumir([2])["ic95"] is None
    assert resumir([2, 2, 2])["ic95"] == [2, 2]
    assert progreso == [(completadas, 6) for completadas in range(7)]
    assert len(primero.sensibilidad) == 1


def test_intervalo_t_con_un_grado_de_libertad():
    # t con un grado de libertad es Cauchy; su cuantil tiene forma cerrada.
    critico = math.tan(math.pi * (0.975 - 0.5))
    resumen = resumir([1, 3])
    assert resumen["media"] == 2
    assert resumen["ic95"] == pytest.approx([2 - critico, 2 + critico])


@pytest.mark.parametrize("valores", [[], [float("nan")], [float("inf")], [[1, 2], [3, 4]]])
def test_estadistica_rechaza_datos_sin_definicion(valores):
    with pytest.raises(ValueError, match="valores finitos"):
        resumir(valores)
