"""Funciones serializables que se ejecutan en procesos separados del servidor."""
import logging
import os
from datetime import datetime, timezone
from restaurante.dominio.contratos import ConfiguracionRestaurante, SolicitudExperimento
from restaurante.infraestructura.persistencia import AlmacenArchivos


def ejecutar_trabajo(raiz: str, coleccion: str, identificador: str):
    almacen = AlmacenArchivos(raiz)
    trabajo = almacen.leer(coleccion, identificador)
    trabajo.update(estado="ejecutando", pid_proceso=os.getpid())
    almacen.guardar(coleccion, trabajo, identificador)
    def informar_progreso(completadas, total):
        trabajo["progreso"] = {"completadas": completadas, "total": total}
        almacen.guardar(coleccion, trabajo, identificador)

    try:
        if coleccion == "simulaciones":
            informar_progreso(0, 1)
            from restaurante.simulacion.motor import simular
            resultado = simular(ConfiguracionRestaurante.model_validate(trabajo["solicitud"]["configuracion"]), trabajo["solicitud"]["semilla"])
            informar_progreso(1, 1)
        else:
            from restaurante.analisis.experimentos import ejecutar_experimento
            resultado = ejecutar_experimento(SolicitudExperimento.model_validate(trabajo["solicitud"]), informar_progreso=informar_progreso)
        trabajo.update(estado="completado", resultado=resultado.model_dump(mode="json"))
    except Exception:
        logging.exception("Falló el trabajo %s", identificador)
        trabajo.update(estado="error", error="No se pudo completar la ejecución. Consulte el registro del servidor.")
    trabajo["finalizado"] = datetime.now(timezone.utc).isoformat()
    almacen.guardar(coleccion, trabajo, identificador)
