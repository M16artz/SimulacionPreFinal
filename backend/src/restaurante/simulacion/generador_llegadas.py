"""Poisson no homogéneo, exacto por tramos de tasa constante."""
import numpy as np
from restaurante.dominio.contratos import ConfiguracionRestaurante, GrupoCliente
from restaurante.infraestructura.distribuciones import muestrear


def generar_demanda(configuracion: ConfiguracionRestaurante, semilla: int) -> list[GrupoCliente]:
    flujo_llegadas, flujo_tamanos, flujo_paciencia = [np.random.default_rng(s) for s in np.random.SeedSequence(semilla).spawn(3)]
    grupos = []
    for franja in configuracion.llegadas:
        instante = float(franja.inicio)
        if franja.tasa == 0:
            continue
        while True:
            instante += float(flujo_llegadas.exponential(60 / franja.tasa))
            if instante >= franja.fin:
                break
            grupos.append(GrupoCliente(id=len(grupos) + 1, personas=int(flujo_tamanos.choice(np.arange(1, 9), p=configuracion.probabilidades_grupo)), llegada=instante, paciencia=muestrear(configuracion.tiempos.paciencia, flujo_paciencia)))
    return grupos
