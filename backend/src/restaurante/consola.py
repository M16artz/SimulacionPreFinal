"""Ejecución sin API: restaurante escenario.yaml --semilla 42 --salida resultado.json."""
import argparse
import json
from pathlib import Path
import yaml
from restaurante.dominio.contratos import ConfiguracionRestaurante, SolicitudExperimento, Rango
from restaurante.infraestructura.exportaciones import serializar_csv, filas_experimento


def principal():
    argumentos = argparse.ArgumentParser(description="Simulador de restaurante")
    argumentos.add_argument("configuracion", type=Path)
    argumentos.add_argument("--semilla", type=int, help="Semilla; por defecto 42 o la del archivo experimental")
    argumentos.add_argument("--salida", type=Path, default=Path("resultado.json"))
    argumentos.add_argument("--experimento", action="store_true", help="El archivo contiene una solicitud con configuraciones, réplicas y rangos")
    argumentos.add_argument("--csv", type=Path, help="Exportar también los grupos o el resumen experimental a CSV")
    argumentos.add_argument("--replicas", type=int, help="Ejecutar réplicas de la configuración indicada")
    for recurso in ("mesas", "meseros", "cocineras"):
        argumentos.add_argument(f"--rango-{recurso}", type=int, nargs=3, metavar=("MINIMO", "MAXIMO", "PASO"), help=f"Evaluar un rango de {recurso}")
    opciones = argumentos.parse_args()
    try:
        datos = yaml.safe_load(opciones.configuracion.read_text(encoding="utf-8"))
        rangos = {recurso: Rango(minimo=valores[0], maximo=valores[1], paso=valores[2]) for recurso in ("mesas", "meseros", "cocineras") if (valores := getattr(opciones, f"rango_{recurso}")) is not None}
        if opciones.experimento or opciones.replicas is not None or rangos:
            if opciones.experimento:
                if opciones.replicas is not None or rangos:
                    raise ValueError("En modo --experimento los rangos y réplicas se definen en el archivo")
                if opciones.semilla is not None:
                    datos["semilla"] = opciones.semilla
                solicitud = SolicitudExperimento.model_validate(datos)
            else:
                solicitud = SolicitudExperimento(configuraciones=[ConfiguracionRestaurante.model_validate(datos)], replicas=opciones.replicas if opciones.replicas is not None else 5, semilla=opciones.semilla if opciones.semilla is not None else 42, rangos=rangos or None)
            from restaurante.analisis.experimentos import ejecutar_experimento
            resultado = ejecutar_experimento(solicitud)
            resumen = {"escenarios": len(resultado.escenarios), "replicas": resultado.replicas, "semillas_replicas": resultado.semillas_replicas}
            filas = filas_experimento(resultado.model_dump())
        else:
            from restaurante.simulacion.motor import simular
            resultado = simular(ConfiguracionRestaurante.model_validate(datos), opciones.semilla if opciones.semilla is not None else 42)
            resumen = resultado.metricas
            filas = resultado.grupos
        opciones.salida.parent.mkdir(parents=True, exist_ok=True)
        opciones.salida.write_text(resultado.model_dump_json(indent=2), encoding="utf-8")
        if opciones.csv:
            opciones.csv.parent.mkdir(parents=True, exist_ok=True)
            opciones.csv.write_text(serializar_csv(filas), encoding="utf-8")
        print(json.dumps(resumen, ensure_ascii=False, indent=2))
    except (ValueError, OSError, yaml.YAMLError) as error:
        argumentos.error(str(error))
    except ModuleNotFoundError as error:
        argumentos.error(f"Falta instalar la dependencia {error.name}. Instale backend con sus dependencias antes de ejecutar esta operación.")


if __name__ == "__main__":
    principal()
