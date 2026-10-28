"""Flujo completo: mesa → pedido → cocina → entrega → consumo → cobro."""
import platform
from importlib.metadata import version
import numpy as np
import simpy
from restaurante import VERSION_MODELO
from restaurante.dominio.contratos import ConfiguracionRestaurante, EventoSimulacion, ResultadoSimulacion
from restaurante.infraestructura.distribuciones import muestrear
from restaurante.simulacion.generador_llegadas import generar_demanda
from restaurante.simulacion.gestor_mesas import GestorMesas
from restaurante.simulacion.gestor_personal import GestorPersonal
from restaurante.analisis.metricas import calcular_metricas
from restaurante.analisis.colas import calcular_colas_y_little, ESTACIONES


def simular(configuracion: ConfiguracionRestaurante, semilla: int) -> ResultadoSimulacion:
    configuracion = ConfiguracionRestaurante.model_validate(configuracion.model_dump())
    configuracion.comprobar_ejecutable()
    if not 0 <= semilla <= 2**32 - 1:
        raise ValueError("La semilla debe estar entre 0 y 4294967295")
    entorno = simpy.Environment(initial_time=configuracion.apertura)
    mesas = GestorMesas(entorno, [configuracion.capacidad_mesa] * configuracion.mesas)
    meseros = GestorPersonal(entorno, configuracion.meseros, "mesero")
    cocina = GestorPersonal(entorno, configuracion.cocineras, "cocinera")
    eventos, registros = [], []
    estado = {"mesas": {}, "personal": {}, "cola": [], "atendidos": 0, "abandonos": 0, "personas_atendidas": 0}
    estado["colas"] = {estacion: [] for estacion in ESTACIONES}
    estado["colas"]["mesa"] = estado["cola"]
    estado["en_sistema"] = []
    ocupacion = {**{f"mesa-{i+1}": 0.0 for i in range(configuracion.mesas)}, **{f"mesero-{i+1}": 0.0 for i in range(configuracion.meseros)}, **{f"cocinera-{i+1}": 0.0 for i in range(configuracion.cocineras)}}

    def registrar(accion, grupo=None, recursos=None):
        import copy
        eventos.append(EventoSimulacion(secuencia=len(eventos), tiempo=float(entorno.now), entidad=grupo, accion=accion, recursos=recursos or [], estado=copy.deepcopy(estado)))

    def duracion(grupo, actividad):
        indice = ("pedido", "preparacion", "entrega", "consumo", "cobro").index(actividad)
        generador = np.random.default_rng(np.random.SeedSequence([semilla, grupo.id, indice, 9182]))
        return muestrear(getattr(configuracion.tiempos, actividad), generador)

    def actividad(grupo, nombre, gestor, registro):
        inicio_cola = entorno.now
        estado["colas"][nombre].append(grupo.id)
        registrar(f"entrada_cola_{nombre}", grupo.id)
        recurso = yield gestor.solicitar()
        estado["colas"][nombre].remove(grupo.id)
        registro[f"espera_{nombre}"] = entorno.now - inicio_cola
        estado["personal"][recurso] = {"grupo": grupo.id, "actividad": nombre}
        registrar(f"inicio_{nombre}", grupo.id, [recurso])
        tiempo = duracion(grupo, nombre)
        yield entorno.timeout(tiempo)
        ocupacion[recurso] += tiempo
        registro[f"duracion_{nombre}"] = tiempo
        del estado["personal"][recurso]
        registrar(f"fin_{nombre}", grupo.id, [recurso])
        yield gestor.liberar(recurso)

    def atender(grupo):
        registro = grupo.model_dump() | {"estado": "esperando"}
        registros.append(registro)
        estado["en_sistema"].append(grupo.id)
        estado["cola"].append(grupo.id)
        registrar("llegada", grupo.id)
        solicitud = mesas.solicitar(grupo.personas)
        yield solicitud | entorno.timeout(grupo.paciencia)
        estado["cola"].remove(grupo.id)
        # En un empate exacto se favorece la asignación ya confirmada.
        if not solicitud.triggered:
            mesas.cancelar(solicitud)
            registro.update(estado="abandono", espera_mesa=float(entorno.now - grupo.llegada), salida=float(entorno.now))
            estado["abandonos"] += 1
            estado["en_sistema"].remove(grupo.id)
            registrar("abandono", grupo.id)
            return
        asignadas = solicitud.value
        nombres = [f"mesa-{i+1}" for i in asignadas]
        inicio = entorno.now
        registro.update(estado="atendido", espera_mesa=float(inicio - grupo.llegada), mesas=nombres, sentado=float(inicio))
        for mesa in nombres:
            estado["mesas"][mesa] = {"grupo": grupo.id, "personas": grupo.personas}
        registrar("asignacion_mesas", grupo.id, nombres)
        yield entorno.process(actividad(grupo, "pedido", meseros, registro))
        yield entorno.process(actividad(grupo, "preparacion", cocina, registro))
        yield entorno.process(actividad(grupo, "entrega", meseros, registro))
        registrar("inicio_consumo", grupo.id, nombres)
        consumo = duracion(grupo, "consumo")
        yield entorno.timeout(consumo)
        registro["duracion_consumo"] = consumo
        registrar("fin_consumo", grupo.id, nombres)
        yield entorno.process(actividad(grupo, "cobro", meseros, registro))
        registro.update(salida=float(entorno.now), tiempo_sistema=float(entorno.now - grupo.llegada))
        for mesa in nombres:
            ocupacion[mesa] += entorno.now - inicio
            del estado["mesas"][mesa]
        estado["atendidos"] += 1
        estado["personas_atendidas"] += grupo.personas
        estado["en_sistema"].remove(grupo.id)
        registrar("salida", grupo.id, nombres)
        mesas.liberar(asignadas)

    def jornada():
        procesos = []
        registrar("apertura")
        for grupo in generar_demanda(configuracion, semilla):
            yield entorno.timeout(grupo.llegada - entorno.now)
            procesos.append(entorno.process(atender(grupo)))
        yield entorno.timeout(configuracion.cierre - entorno.now)
        registrar("cierre_llegadas")
        yield entorno.all_of(procesos)
        registrar("fin_jornada")

    entorno.run(until=entorno.process(jornada()))
    metricas, recursos = calcular_metricas(registros, ocupacion, configuracion.apertura, float(entorno.now))
    analisis, indicadores = calcular_colas_y_little(eventos, registros, configuracion.apertura, float(entorno.now))
    metricas.update(indicadores)
    return ResultadoSimulacion(version_modelo=VERSION_MODELO, version_entorno={"python": platform.python_version(), **{nombre: version(nombre) for nombre in ("simpy", "numpy", "pydantic")}}, semilla=semilla, configuracion=configuracion, metricas=metricas, recursos=recursos, grupos=registros, eventos=eventos, formulacion_matematica=analisis)
