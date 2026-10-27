"""Réplicas independientes y comparación pareada con números aleatorios comunes."""
import platform
from importlib.metadata import version
import numpy as np
from restaurante import VERSION_MODELO
from restaurante.dominio.contratos import SolicitudExperimento, ResultadoExperimento
from restaurante.analisis.estadistica import resumir
from restaurante.analisis.optimizacion import expandir_configuraciones, identificar_eficientes, calcular_sensibilidad


def ejecutar_experimento(solicitud: SolicitudExperimento, informar_progreso=None) -> ResultadoExperimento:
    from restaurante.simulacion.motor import simular
    configuraciones = expandir_configuraciones(solicitud)
    semillas = [int(s.generate_state(1)[0]) for s in np.random.SeedSequence(solicitud.semilla).spawn(solicitud.replicas)]
    escenarios = []
    total = len(configuraciones) * len(semillas)
    completadas = 0
    if informar_progreso:
        informar_progreso(completadas, total)
    for indice, configuracion in enumerate(configuraciones):
        resultados = []
        for semilla in semillas:
            resultados.append(simular(configuracion, semilla).metricas)
            completadas += 1
            if informar_progreso:
                informar_progreso(completadas, total)
        resumen = {clave: resumir([resultado[clave] for resultado in resultados]) for clave in resultados[0]}
        escenarios.append({"id": indice, "nombre": configuracion.nombre, "configuracion": configuracion.model_dump(), "resumen": resumen, "replicas": resultados})
    identificar_eficientes(escenarios)
    base = escenarios[0]
    diferencias = [{"escenario": e["id"], "base": 0, "metricas": {clave: resumir([r[clave] - b[clave] for r, b in zip(e["replicas"], base["replicas"])]) for clave in ("tasa_abandono", "espera_mesa_media", "personas_atendidas")}} for e in escenarios[1:]]
    return ResultadoExperimento(version_modelo=VERSION_MODELO, version_entorno={"python": platform.python_version(), **{nombre: version(nombre) for nombre in ("simpy", "numpy", "scipy", "pydantic")}}, semilla=solicitud.semilla, replicas=solicitud.replicas, semillas_replicas=semillas, escenarios=escenarios, diferencias_pareadas=diferencias, sensibilidad=calcular_sensibilidad(escenarios))
