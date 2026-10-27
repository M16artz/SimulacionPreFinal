"""Serialización reutilizable para consola y HTTP, sin dependencias web."""
import csv
from io import StringIO
import json


def serializar_json(datos):
    return json.dumps(datos, ensure_ascii=False, allow_nan=False, indent=2)


def serializar_csv(filas):
    salida = StringIO(newline="")
    if filas:
        columnas = list(dict.fromkeys(clave for fila in filas for clave in fila))
        escritor = csv.DictWriter(salida, fieldnames=columnas)
        escritor.writeheader()
        for fila in filas:
            escritor.writerow({clave: json.dumps(valor, ensure_ascii=False) if isinstance(valor, (dict, list)) else valor for clave, valor in fila.items()})
    return "\ufeff" + salida.getvalue()


def filas_experimento(resultado):
    return [
        {"escenario": escenario["id"], "nombre": escenario["nombre"], "eficiente": escenario["eficiente"],
         **{clave: escenario["configuracion"][clave] for clave in ("mesas", "meseros", "cocineras")},
         **{f"{clave}_{estadistico}": (valor["media"] if estadistico == "media" else (valor["ic95"][0 if estadistico == "inferior" else 1] if valor["ic95"] is not None else None))
            for clave, valor in escenario["resumen"].items() for estadistico in ("media", "inferior", "superior")}}
        for escenario in resultado["escenarios"]
    ]
