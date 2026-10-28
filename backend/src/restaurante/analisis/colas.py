"""Integración temporal de colas y contraste de Little sobre cohortes completas.

La igualdad se usa como balance de una jornada que comienza y termina vacía.
No demuestra estacionariedad ni convierte el restaurante en un modelo M/M/s.
"""
from math import fsum, isclose, isfinite
from restaurante.dominio.contratos import AnalisisMatematico, ContrasteLittle, IndicadorCola

ESTACIONES = ("mesa", "pedido", "preparacion", "entrega", "cobro")


def integrar_escalones(muestras, inicio: float, fin: float) -> float:
    """Área exacta Σ Q(t_j)·(t_{j+1}−t_j) de un estado posterior al evento.

    Los eventos simultáneos tienen duración cero. Antes de la primera muestra
    se considera una población vacía; no se interpola entre observaciones.
    """
    if not isfinite(inicio) or not isfinite(fin) or fin <= inicio:
        raise ValueError("El periodo de observación debe ser finito y positivo")
    anterior, cantidad = inicio, 0.0
    areas = []
    for tiempo, nueva_cantidad in muestras:
        if not isfinite(tiempo) or not anterior <= tiempo <= fin:
            raise ValueError("Las observaciones deben estar ordenadas y dentro del periodo")
        if not isfinite(nueva_cantidad) or nueva_cantidad < 0:
            raise ValueError("La cantidad observada debe ser finita y no negativa")
        areas.append(cantidad * (tiempo - anterior))
        anterior, cantidad = tiempo, nueva_cantidad
    areas.append(cantidad * (fin - anterior))
    return fsum(areas)


def contrastar_little(ambito, poblacion, longitud_media, tiempos, inicio, fin, poblacion_cerrada=True):
    """λ=N/T en grupos/minuto; W en minutos; L en grupos.

    W y N deben pertenecer exactamente a la población integrada para obtener L.
    Una población vacía no permite estimar W ni contrastar la relación.
    """
    if not isfinite(inicio) or not isfinite(fin) or fin <= inicio:
        raise ValueError("El periodo de observación debe ser finito y positivo")
    if not isfinite(longitud_media) or longitud_media < 0 or any(not isfinite(t) or t < 0 for t in tiempos):
        raise ValueError("Los tiempos y la longitud media deben ser finitos y no negativos")
    numero = len(tiempos)
    tasa = numero / (fin - inicio)
    promedio = fsum(tiempos) / numero if numero else None
    aplicable = poblacion_cerrada and numero > 0
    producto = tasa * promedio if aplicable else None
    error = abs(longitud_media - producto) if aplicable else None
    return ContrasteLittle(
        ambito=ambito, poblacion=poblacion, numero_entidades=numero,
        inicio=inicio, fin=fin, longitud_media=longitud_media,
        tasa_efectiva=tasa, tiempo_medio=promedio, producto_lambda_w=producto,
        error_absoluto=error, aplicable=aplicable,
        coincide=isclose(longitud_media, producto, rel_tol=1e-9, abs_tol=1e-9) if aplicable else None,
        observacion=("Balance finito de una cohorte completa con sistema inicialmente y finalmente vacío. No prueba estado estacionario."
                     if aplicable else "Sin entidades observadas; W no es estimable."
                     if numero == 0 else "La ventana no contiene una cohorte completa con extremos vacíos; no se contrasta Little sin corregir los bordes."),
    )


def calcular_colas_y_little(eventos, grupos, apertura, fin):
    if not eventos or eventos[0].tiempo != apertura or eventos[-1].tiempo != fin:
        raise ValueError("El registro debe cubrir desde la apertura hasta el fin de observación")
    for evento in eventos:
        if "en_sistema" not in evento.estado or any(estacion not in evento.estado.get("colas", {}) for estacion in ESTACIONES):
            raise ValueError("El registro no contiene las poblaciones y colas de todas las estaciones")
    duracion = fin - apertura
    atendidos = [grupo for grupo in grupos if grupo["estado"] == "atendido"]
    ids_atendidos = {grupo["id"] for grupo in atendidos}
    extremos_vacios = not eventos[0].estado["en_sistema"] and not eventos[-1].estado["en_sistema"]
    cohorte_completa = extremos_vacios and all("salida" in grupo and apertura <= grupo["llegada"] <= grupo["salida"] <= fin for grupo in grupos)
    colas, contrastes, metricas = [], [], {}
    for estacion in ESTACIONES:
        area = integrar_escalones(((evento.tiempo, len(evento.estado["colas"][estacion])) for evento in eventos), apertura, fin)
        visitantes = grupos if estacion == "mesa" else atendidos
        clave_espera = "espera_mesa" if estacion == "mesa" else f"espera_{estacion}"
        tiempos = [grupo[clave_espera] for grupo in visitantes if clave_espera in grupo]
        longitud = area / duracion
        colas.append(IndicadorCola(estacion=estacion, area_grupo_minutos=area, longitud_media=longitud, numero_entidades=len(tiempos), espera_media=fsum(tiempos) / len(tiempos) if tiempos else None))
        metricas[f"longitud_cola_{estacion}_media"] = longitud
        contrastes.append(contrastar_little(
            f"cola_{estacion}", "Todos los grupos llegados, incluidos abandonos" if estacion == "mesa" else "Grupos atendidos que visitan esta estación",
            longitud, tiempos, apertura, fin,
            cohorte_completa and len(tiempos) == len(visitantes) and not eventos[0].estado["colas"][estacion] and not eventos[-1].estado["colas"][estacion],
        ))
    for nombre, seleccionados, descripcion in (
        ("sistema", grupos, "Todos los grupos llegados, incluidos abandonos"),
        ("sistema_atendidos", atendidos, "Sólo grupos que completaron el servicio; L se filtra por esa misma cohorte"),
    ):
        area = integrar_escalones(((evento.tiempo, len(evento.estado["en_sistema"]) if nombre == "sistema" else sum(identificador in ids_atendidos for identificador in evento.estado["en_sistema"])) for evento in eventos), apertura, fin)
        tiempos = [grupo["salida"] - grupo["llegada"] for grupo in seleccionados if "salida" in grupo]
        longitud = area / duracion
        metricas[f"grupos_{nombre}_media"] = longitud
        metricas[f"tasa_efectiva_{nombre}"] = len(tiempos) / duracion
        if nombre == "sistema":
            metricas["tiempo_sistema_todos_medio"] = fsum(tiempos) / len(tiempos) if tiempos else 0.0
        contrastes.append(contrastar_little(nombre, descripcion, longitud, tiempos, apertura, fin, cohorte_completa and len(tiempos) == len(seleccionados)))
    return AnalisisMatematico(inicio=apertura, fin=fin, duracion=duracion, colas=colas, little=contrastes), metricas
