import json
import os
import time
from fastapi.testclient import TestClient
from restaurante.api.principal import crear_aplicacion


def esperar(cliente, ruta):
    limite = time.monotonic() + 60
    while time.monotonic() < limite:
        respuesta = cliente.get(ruta)
        assert respuesta.status_code == 200
        datos = respuesta.json()
        if datos["estado"] in ("completado", "error"):
            assert datos["estado"] == "completado", datos
            return datos
        time.sleep(0.05)
    raise AssertionError("El trabajador no terminó en 60 segundos")


def test_crud_importacion_y_validacion(tmp_path, configuracion):
    with TestClient(crear_aplicacion(tmp_path)) as cliente:
        assert cliente.get("/api/v1/salud").status_code == 200
        datos = configuracion.model_dump()
        identificador = cliente.post("/api/v1/configuraciones", json=datos).json()["id"]
        assert cliente.get(f"/api/v1/configuraciones/{identificador}").json()["configuracion"] == datos
        datos["nombre"] = "Actualizada"
        assert cliente.put(f"/api/v1/configuraciones/{identificador}", json=datos).status_code == 200
        copia = cliente.post(f"/api/v1/configuraciones/{identificador}/duplicar").json()["id"]
        assert copia != identificador
        assert cliente.post("/api/v1/configuraciones/importar", json={"contenido": json.dumps(datos)}).json() == datos
        datos["tiempos"]["pedido"] = None
        assert not cliente.post("/api/v1/configuraciones/validar", json=datos).json()["ejecutable"]
        assert cliente.post("/api/v1/simulaciones", json={"configuracion": datos, "semilla": 42}).status_code == 422
        datos["mesas"] = 0
        assert cliente.post("/api/v1/configuraciones", json=datos).status_code == 422
        assert cliente.get("/api/v1/configuraciones/no-es-uuid").status_code == 422


def test_trabajador_resultados_exportacion_y_snapshot(tmp_path, breve):
    with TestClient(crear_aplicacion(tmp_path)) as cliente:
        solicitud = {"configuracion": breve.model_dump(), "semilla": 42}
        respuesta = cliente.post("/api/v1/simulaciones", json=solicitud)
        assert respuesta.status_code == 202
        identificador = respuesta.json()["id"]
        ruta = f"/api/v1/simulaciones/{identificador}"
        estado = esperar(cliente, ruta)
        assert estado["pid_proceso"] != os.getpid()
        assert estado["progreso"] == {"completadas": 1, "total": 1}
        resultado = cliente.get(ruta + "/resultados").json()
        assert resultado["configuracion"] == solicitud["configuracion"]
        assert resultado["semilla"] == 42
        assert resultado["eventos"] == cliente.get(ruta + "/eventos").json()
        assert cliente.get(ruta).json()["metricas"] == resultado["metricas"]
        assert all(c["coincide"] for c in resultado["formulacion_matematica"]["little"])
        for tabla in ("grupos", "recursos", "eventos", "metricas", "colas", "little"):
            exportado = cliente.get(ruta + f"/exportar?formato=csv&tabla={tabla}")
            assert exportado.status_code == 200 and "text/csv" in exportado.headers["content-type"]
        assert cliente.get(ruta + "/exportar").json() == resultado
        solicitud["configuracion"]["mesas"] = 80
        assert cliente.get(ruta + "/resultados").json()["configuracion"]["mesas"] == breve.mesas


def test_experimento_en_proceso_separado(tmp_path, breve):
    with TestClient(crear_aplicacion(tmp_path)) as cliente:
        respuesta = cliente.post("/api/v1/experimentos", json={"configuraciones": [breve.model_dump()], "replicas": 2, "semilla": 9})
        assert respuesta.status_code == 202
        ruta = "/api/v1/experimentos/" + respuesta.json()["id"]
        terminado = esperar(cliente, ruta)
        assert len(terminado["resultado"]["semillas_replicas"]) == 2
        ligero = cliente.get(ruta + "?incluir_resultado=false").json()
        assert "resultado" not in ligero
        assert ligero["progreso"] == {"completadas": 2, "total": 2}
        assert cliente.get(ruta + "/exportar?formato=json").json() == terminado["resultado"]
        assert "espera_mesa_media_inferior" in cliente.get(ruta + "/exportar").text
