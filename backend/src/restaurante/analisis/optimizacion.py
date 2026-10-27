"""Evaluación explícita de dominancia y sensibilidad entre escenarios."""
from itertools import product
from restaurante.dominio.contratos import ConfiguracionRestaurante, SolicitudExperimento

RECURSOS = ("mesas", "meseros", "cocineras")
OBJETIVOS = ("tasa_abandono", "espera_mesa_media")


def expandir_configuraciones(solicitud: SolicitudExperimento):
    claves = list(solicitud.rangos or {})
    configuraciones = []
    for base in solicitud.configuraciones:
        for valores in product(*[solicitud.rangos[clave].valores() for clave in claves]):
            datos = base.model_dump()
            datos.update(zip(claves, valores))
            configuraciones.append(ConfiguracionRestaurante.model_validate(datos))
    return configuraciones


def identificar_eficientes(escenarios):
    """Minimiza cada recurso, abandono y espera; no presume costes iguales."""
    def objetivos(escenario):
        return [escenario["configuracion"][clave] for clave in RECURSOS] + [escenario["resumen"][clave]["media"] for clave in OBJETIVOS]

    vectores = [objetivos(escenario) for escenario in escenarios]
    for escenario, objetivo in zip(escenarios, vectores):
        escenario["eficiente"] = not any(
            all(a <= b for a, b in zip(otro, objetivo))
            and any(a < b for a, b in zip(otro, objetivo))
            for otro in vectores
        )
    return escenarios


def calcular_sensibilidad(escenarios):
    """Diferencias por unidad de recurso; conserva iguales los otros parámetros.

    Se comparan vecinos consecutivos de cada recurso, sin mezclar escenarios
    que además cambien tiempos, demanda u otra hipótesis.
    """
    comparaciones = []
    for recurso in RECURSOS:
        familias = {}
        for escenario in escenarios:
            configuracion = escenario["configuracion"]
            import json
            firma = json.dumps({clave: valor for clave, valor in configuracion.items() if clave not in (recurso, "nombre", "notas")}, sort_keys=True)
            familias.setdefault(firma, []).append(escenario)
        for familia in familias.values():
            ordenados = sorted(familia, key=lambda e: e["configuracion"][recurso])
            # Duplicados con el mismo recurso no definen una diferencia finita.
            unicos = {e["configuracion"][recurso]: e for e in ordenados}
            vecinos = list(unicos.values())
            for anterior, posterior in zip(vecinos, vecinos[1:]):
                incremento = posterior["configuracion"][recurso] - anterior["configuracion"][recurso]
                comparaciones.append({
                    "recurso": recurso, "desde": anterior["id"], "hasta": posterior["id"],
                    "incremento": incremento,
                    "cambios_por_unidad": {
                        metrica: (posterior["resumen"][metrica]["media"] - anterior["resumen"][metrica]["media"]) / incremento
                        for metrica in (*OBJETIVOS, "personas_atendidas")
                    },
                })
    return comparaciones
