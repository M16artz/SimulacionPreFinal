"""Cola local acotada y protegida frente a solicitudes HTTP concurrentes."""
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
from threading import Lock
from restaurante.aplicacion.servicios import ejecutar_trabajo


class ColaLlenaError(RuntimeError):
    """La cola alcanzó su límite de trabajos simultáneos."""


class TrabajadorNoDisponibleError(RuntimeError):
    """No se pudo enviar el trabajo al ejecutor."""


class GestorTrabajos:
    def __init__(self, almacen, limite=12, ejecutor=None):
        if limite < 1:
            raise ValueError("El límite de trabajos debe ser positivo")
        self.almacen = almacen
        self.limite = limite
        self.ejecutor = ejecutor if ejecutor is not None else ProcessPoolExecutor(max_workers=2)
        self.futuros = []
        self.cerrojo = Lock()

    def recuperar_interrumpidos(self):
        for coleccion in ("simulaciones", "experimentos"):
            for trabajo in self.almacen.listar(coleccion):
                if trabajo["estado"] in ("pendiente", "ejecutando"):
                    identificador = trabajo.pop("id")
                    trabajo.update(estado="error", finalizado=datetime.now(timezone.utc).isoformat(), error="El servidor se reinició. Repita la ejecución con los mismos parámetros y semilla.")
                    self.almacen.guardar(coleccion, trabajo, identificador)

    def crear(self, coleccion, solicitud):
        if coleccion not in ("simulaciones", "experimentos"):
            raise ValueError("Tipo de trabajo desconocido")
        with self.cerrojo:
            self.futuros = [futuro for futuro in self.futuros if not futuro.done()]
            if len(self.futuros) >= self.limite:
                raise ColaLlenaError("Hay demasiadas ejecuciones pendientes; espere antes de reintentar")
            trabajo = {"estado": "pendiente", "creado": datetime.now(timezone.utc).isoformat(), "solicitud": solicitud, "progreso": {"completadas": 0, "total": None}}
            identificador = self.almacen.guardar(coleccion, trabajo)
            try:
                futuro = self.ejecutor.submit(ejecutar_trabajo, str(self.almacen.raiz), coleccion, identificador)
                self.futuros.append(futuro)
                futuro.add_done_callback(lambda terminado: self._revisar(terminado, coleccion, identificador))
            except (RuntimeError, OSError) as error:
                self._marcar_error(coleccion, identificador, "No hay trabajadores disponibles. Reinicie el servidor antes de reintentar.")
                raise TrabajadorNoDisponibleError("No hay trabajadores disponibles") from error
        return {"id": identificador, "estado": "pendiente"}

    def _marcar_error(self, coleccion, identificador, mensaje):
        trabajo = self.almacen.leer(coleccion, identificador)
        if trabajo["estado"] not in ("completado", "error"):
            trabajo.update(estado="error", error=mensaje, finalizado=datetime.now(timezone.utc).isoformat())
            self.almacen.guardar(coleccion, trabajo, identificador)

    def _revisar(self, futuro, coleccion, identificador):
        if futuro.cancelled() or futuro.exception() is not None:
            self._marcar_error(coleccion, identificador, "El trabajador terminó inesperadamente. Repita la ejecución.")

    def cerrar(self):
        self.ejecutor.shutdown(wait=True)
