"""API local con pool de procesos, snapshots y exportaciones."""
from contextlib import asynccontextmanager
import os
from pathlib import Path
from typing import Literal
from uuid import UUID
import yaml
from fastapi import FastAPI, HTTPException, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import Field, ValidationError
from restaurante.dominio.contratos import Contrato, ConfiguracionRestaurante, SolicitudExperimento
from restaurante.infraestructura.persistencia import AlmacenArchivos
from restaurante.aplicacion.trabajos import GestorTrabajos, ColaLlenaError, TrabajadorNoDisponibleError
from restaurante.api.errores import traducir_errores
from restaurante.infraestructura.exportaciones import serializar_csv, serializar_json, filas_experimento

RAIZ = Path(__file__).resolve().parents[4]


class SolicitudSimulacion(Contrato):
    configuracion: ConfiguracionRestaurante
    semilla: int = Field(default=42, ge=0, le=2**32 - 1)


class ArchivoConfiguracion(Contrato):
    contenido: str = Field(max_length=1_000_000)


def crear_aplicacion(raiz_datos=None):
    almacen = AlmacenArchivos(raiz_datos or os.environ.get("RESTAURANTE_DATOS", RAIZ / "datos"))

    @asynccontextmanager
    async def ciclo(aplicacion):
        if not almacen.listar("configuraciones"):
            for archivo in sorted((RAIZ / "configuraciones").rglob("*.yaml")):
                configuracion = ConfiguracionRestaurante.model_validate(yaml.safe_load(archivo.read_text(encoding="utf-8")))
                almacen.guardar("configuraciones", {"configuracion": configuracion.model_dump()})
        gestor = GestorTrabajos(almacen)
        try:
            gestor.recuperar_interrumpidos()
            aplicacion.state.trabajos = gestor
            yield
        finally:
            gestor.cerrar()

    aplicacion = FastAPI(title="Simulador de restaurante", version="1.0.0", lifespan=ciclo)

    @aplicacion.exception_handler(RequestValidationError)
    async def error_validacion(solicitud, error):
        return JSONResponse(status_code=422, content={"detail": traducir_errores(error.errors())})

    def leer(coleccion, identificador):
        try:
            return almacen.leer(coleccion, str(identificador))
        except FileNotFoundError:
            raise HTTPException(404, "Registro no encontrado")

    def resultado(coleccion, identificador):
        trabajo = leer(coleccion, identificador)
        if trabajo["estado"] != "completado":
            raise HTTPException(409, "Los resultados todavía no están disponibles")
        return trabajo["resultado"]

    def crear_trabajo(coleccion, solicitud):
        try:
            return aplicacion.state.trabajos.crear(coleccion, solicitud)
        except ColaLlenaError as error:
            raise HTTPException(429, str(error))
        except TrabajadorNoDisponibleError as error:
            raise HTTPException(503, str(error))

    def exportar(datos, formato, nombre, filas=None):
        if formato == "json":
            contenido = serializar_json(datos)
            tipo = "application/json"
        else:
            filas = filas if filas is not None else datos
            contenido = serializar_csv(filas)
            tipo = "text/csv"
        return Response(contenido, media_type=tipo, headers={"Content-Disposition": f'attachment; filename="{nombre}.{formato}"'})

    @aplicacion.get("/api/v1/salud")
    def salud():
        return {"estado": "disponible", "version_modelo": "1.0.0"}

    @aplicacion.get("/api/v1/configuraciones/esquema")
    def esquema():
        return ConfiguracionRestaurante.model_json_schema()

    @aplicacion.post("/api/v1/configuraciones/importar")
    def importar(archivo: ArchivoConfiguracion):
        try:
            configuracion = ConfiguracionRestaurante.model_validate(yaml.safe_load(archivo.contenido))
            return configuracion.model_dump()
        except ValidationError as error:
            raise HTTPException(422, traducir_errores(error.errors()))
        except (ValueError, yaml.YAMLError):
            raise HTTPException(422, "El archivo no contiene una configuración YAML o JSON válida")

    @aplicacion.post("/api/v1/configuraciones/validar")
    def validar(configuracion: ConfiguracionRestaurante):
        try:
            configuracion.comprobar_ejecutable()
            return {"valida": True, "ejecutable": True, "pendientes": []}
        except ValueError as error:
            return {"valida": True, "ejecutable": False, "pendientes": [str(error)]}

    @aplicacion.get("/api/v1/configuraciones")
    def listar_configuraciones():
        return almacen.listar("configuraciones")

    @aplicacion.post("/api/v1/configuraciones", status_code=201)
    def guardar(configuracion: ConfiguracionRestaurante):
        return {"id": almacen.guardar("configuraciones", {"configuracion": configuracion.model_dump()})}

    @aplicacion.get("/api/v1/configuraciones/{identificador}")
    def consultar_configuracion(identificador: UUID):
        return leer("configuraciones", identificador)

    @aplicacion.put("/api/v1/configuraciones/{identificador}")
    def actualizar(identificador: UUID, configuracion: ConfiguracionRestaurante):
        leer("configuraciones", identificador)
        almacen.guardar("configuraciones", {"configuracion": configuracion.model_dump()}, str(identificador))
        return {"id": str(identificador)}

    @aplicacion.post("/api/v1/configuraciones/{identificador}/duplicar", status_code=201)
    def duplicar(identificador: UUID):
        datos = leer("configuraciones", identificador)
        datos["configuracion"]["nombre"] = (datos["configuracion"]["nombre"][:92] + " (copia)")
        return {"id": almacen.guardar("configuraciones", datos)}

    @aplicacion.get("/api/v1/configuraciones/{identificador}/exportar")
    def exportar_configuracion(identificador: UUID, formato: Literal["json", "yaml"] = "yaml"):
        datos = leer("configuraciones", identificador)["configuracion"]
        if formato == "json":
            return exportar(datos, formato, "configuracion")
        return Response(yaml.safe_dump(datos, allow_unicode=True, sort_keys=False), media_type="application/yaml", headers={"Content-Disposition": 'attachment; filename="configuracion.yaml"'})

    @aplicacion.post("/api/v1/simulaciones", status_code=202)
    def simular(solicitud: SolicitudSimulacion):
        try:
            solicitud.configuracion.comprobar_ejecutable()
        except ValueError as error:
            raise HTTPException(422, str(error))
        return crear_trabajo("simulaciones", solicitud.model_dump())

    @aplicacion.get("/api/v1/simulaciones")
    def listar_simulaciones():
        return [{"id": t["id"], "estado": t["estado"], "creado": t["creado"], "nombre": t["solicitud"]["configuracion"]["nombre"], "semilla": t["solicitud"]["semilla"]} for t in almacen.listar("simulaciones")]

    @aplicacion.get("/api/v1/simulaciones/{identificador}")
    def consultar_simulacion(identificador: UUID):
        datos = leer("simulaciones", identificador)
        return {"id": str(identificador), **{k: v for k, v in datos.items() if k != "resultado"}, "metricas": datos.get("resultado", {}).get("metricas")}

    @aplicacion.get("/api/v1/simulaciones/{identificador}/eventos")
    def eventos(identificador: UUID):
        return resultado("simulaciones", identificador)["eventos"]

    @aplicacion.get("/api/v1/simulaciones/{identificador}/resultados")
    def resultados(identificador: UUID):
        return resultado("simulaciones", identificador)

    @aplicacion.get("/api/v1/simulaciones/{identificador}/exportar")
    def exportar_simulacion(identificador: UUID, formato: Literal["json", "csv"] = "json", tabla: Literal["grupos", "recursos", "eventos", "metricas"] = "grupos"):
        datos = resultado("simulaciones", identificador)
        filas = [datos[tabla]] if tabla == "metricas" else datos[tabla]
        return exportar(datos, formato, f"simulacion-{tabla}", filas)

    @aplicacion.post("/api/v1/experimentos", status_code=202)
    def experimentar(solicitud: SolicitudExperimento):
        return crear_trabajo("experimentos", solicitud.model_dump())

    @aplicacion.get("/api/v1/experimentos")
    def listar_experimentos():
        return [{k: v for k, v in t.items() if k not in ("resultado", "solicitud")} for t in almacen.listar("experimentos")]

    @aplicacion.get("/api/v1/experimentos/{identificador}")
    def consultar_experimento(identificador: UUID, incluir_resultado: bool = True):
        trabajo = leer("experimentos", identificador)
        if not incluir_resultado:
            trabajo.pop("resultado", None)
        return {"id": str(identificador), **trabajo}

    @aplicacion.get("/api/v1/experimentos/{identificador}/exportar")
    def exportar_experimento(identificador: UUID, formato: Literal["json", "csv"] = "csv"):
        datos = resultado("experimentos", identificador)
        filas = filas_experimento(datos)
        return exportar(datos, formato, "experimento", filas)

    return aplicacion


app = crear_aplicacion()
