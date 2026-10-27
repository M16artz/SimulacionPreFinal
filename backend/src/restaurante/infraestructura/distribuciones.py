"""Muestreo extensible a partir del contrato común."""
from numpy.random import Generator
from restaurante.dominio.contratos import Distribucion


def muestrear(distribucion: Distribucion, generador: Generator) -> float:
    parametros = distribucion.model_dump()
    tipo = parametros.pop("tipo")
    generadores = {
        "fija": lambda: parametros["valor"],
        "uniforme": lambda: generador.uniform(parametros["minimo"], parametros["maximo"]),
        "triangular": lambda: generador.triangular(parametros["minimo"], parametros["moda"], parametros["maximo"]),
        "exponencial": lambda: generador.exponential(parametros["media"]),
    }
    return float(generadores[tipo]())
