"""Archivos JSON con reemplazo atómico; sólo identificadores UUID propios."""
import json
import os
import time
from pathlib import Path
from uuid import UUID, uuid4


def reintentar_archivo(operacion):
    """Tolera bloqueos breves de Windows durante reemplazos y sincronización.

    Los permisos permanentemente inválidos se siguen informando tras un plazo
    acotado. Otros errores se propagan inmediatamente.
    """
    for intento in range(8):
        try:
            return operacion()
        except PermissionError:
            if os.name != "nt" or intento == 7:
                raise
            time.sleep(0.005 * 2 ** min(intento, 4))


class AlmacenArchivos:
    def __init__(self, raiz: str | Path):
        self.raiz = Path(raiz).resolve()
        self.raiz.mkdir(parents=True, exist_ok=True)

    def ruta(self, coleccion: str, identificador: str):
        if coleccion not in ("configuraciones", "simulaciones", "experimentos"):
            raise ValueError("Colección desconocida")
        identificador = str(UUID(identificador))
        carpeta = self.raiz / coleccion
        carpeta.mkdir(exist_ok=True)
        return carpeta / f"{identificador}.json"

    def guardar(self, coleccion, datos, identificador=None):
        identificador = identificador or str(uuid4())
        destino = self.ruta(coleccion, identificador)
        temporal = destino.with_suffix(f".{uuid4().hex}.tmp")
        temporal.write_text(json.dumps(datos, ensure_ascii=False, allow_nan=False), encoding="utf-8")
        reintentar_archivo(lambda: os.replace(temporal, destino))
        return identificador

    def leer(self, coleccion, identificador):
        return json.loads(reintentar_archivo(lambda: self.ruta(coleccion, identificador).read_text(encoding="utf-8")))

    def listar(self, coleccion):
        carpeta = self.raiz / coleccion
        return [{"id": archivo.stem, **self.leer(coleccion, archivo.stem)} for archivo in sorted(carpeta.glob("*.json"), key=lambda p: reintentar_archivo(lambda: p.stat().st_mtime), reverse=True)]
