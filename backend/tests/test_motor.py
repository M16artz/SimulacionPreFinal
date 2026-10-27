import pytest
from restaurante.dominio.contratos import ConfiguracionRestaurante, GrupoCliente, ResultadoSimulacion
from restaurante.simulacion.motor import simular


def test_reproducibilidad_y_snapshot_inmutable(breve):
    primero = simular(breve, 42)
    segundo = simular(breve, 42)
    assert primero == segundo
    assert ResultadoSimulacion.model_validate_json(primero.model_dump_json()) == primero
    breve.nombre = "Otro nombre"
    assert primero.configuracion.nombre != breve.nombre
    assert simular(breve, 43).grupos != segundo.grupos


def test_invariantes_recursos_conteos_y_cierre(configuracion):
    resultado = simular(configuracion, 42)
    activos = {}
    personal = {}
    for evento in resultado.eventos:
        if evento.accion == "asignacion_mesas":
            personas = next(g["personas"] for g in resultado.grupos if g["id"] == evento.entidad)
            assert len(evento.recursos) == (2 if personas >= 5 else 1)
            assert not any(recurso in activos for recurso in evento.recursos)
            activos.update({r: evento.entidad for r in evento.recursos})
        elif evento.accion == "salida":
            for recurso in evento.recursos:
                assert activos.pop(recurso) == evento.entidad
            assert any(e.entidad == evento.entidad and e.accion == "fin_cobro" and e.secuencia < evento.secuencia for e in resultado.eventos)
        elif evento.accion.startswith("inicio_") and evento.accion != "inicio_consumo":
            for recurso in evento.recursos:
                assert recurso not in personal
                personal[recurso] = evento.entidad
        elif evento.accion.startswith("fin_") and evento.accion not in ("fin_consumo", "fin_jornada"):
            for recurso in evento.recursos:
                assert personal.pop(recurso) == evento.entidad
        assert len(evento.estado["mesas"]) <= configuracion.mesas
        assert sum(r.startswith("mesero-") for r in evento.estado["personal"]) <= configuracion.meseros
        assert sum(r.startswith("cocinera-") for r in evento.estado["personal"]) <= configuracion.cocineras
    assert not activos and not personal
    assert not resultado.eventos[-1].estado["cola"]
    assert all(configuracion.apertura <= g["llegada"] < configuracion.cierre for g in resultado.grupos)
    m = resultado.metricas
    assert m["grupos_llegados"] == m["grupos_atendidos"] + m["grupos_abandonados"]
    assert m["personas_llegadas"] == m["personas_atendidas"] + m["personas_abandonadas"]
    assert m["fin_jornada"] >= configuracion.cierre
    assert all(0 <= r["utilizacion"] <= 1 + 1e-12 for r in resultado.recursos)
    assert m["grupos_atendidos"] == resultado.eventos[-1].estado["atendidos"]


def test_abandono_no_reaparece_y_servicio_finaliza_tras_cierre(breve, monkeypatch):
    datos = breve.model_dump()
    datos.update(mesas=1, meseros=1, cocineras=1, cierre=541, llegadas=[{"inicio": 540, "fin": 541, "tasa": 1}])
    for actividad in datos["tiempos"]:
        datos["tiempos"][actividad] = {"tipo": "fija", "valor": 10}
    configuracion = ConfiguracionRestaurante.model_validate(datos)
    grupos = [GrupoCliente(id=1, personas=4, llegada=540.1, paciencia=10), GrupoCliente(id=2, personas=4, llegada=540.2, paciencia=0.5)]
    monkeypatch.setattr("restaurante.simulacion.motor.generar_demanda", lambda *_: grupos)
    resultado = simular(configuracion, 2)
    assert resultado.grupos[1]["estado"] == "abandono"
    assert not any(e.entidad == 2 and e.accion == "asignacion_mesas" for e in resultado.eventos)
    assert resultado.metricas["fin_jornada"] == pytest.approx(590.1)


def test_pedido_grupal_no_depende_de_personas(breve, monkeypatch):
    grupos = [GrupoCliente(id=1, personas=1, llegada=541, paciencia=40), GrupoCliente(id=2, personas=8, llegada=542, paciencia=40)]
    monkeypatch.setattr("restaurante.simulacion.motor.generar_demanda", lambda *_: grupos)
    datos = breve.model_dump()
    datos["tiempos"]["preparacion"] = {"tipo": "fija", "valor": 12}
    resultado = simular(ConfiguracionRestaurante.model_validate(datos), 42)
    assert [g["duracion_preparacion"] for g in resultado.grupos] == [12, 12]


def test_jornada_sin_llegadas(breve):
    datos = breve.model_dump()
    datos["llegadas"][0]["tasa"] = 0
    resultado = simular(ConfiguracionRestaurante.model_validate(datos), 42)
    assert resultado.metricas["grupos_llegados"] == 0
    assert resultado.metricas["fin_jornada"] == breve.cierre
    assert resultado.metricas["utilizacion_mesa"] == 0
