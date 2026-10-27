"""Definiciones explícitas de los indicadores (tiempos en minutos)."""
import numpy as np


def calcular_metricas(grupos, ocupacion, apertura, fin):
    atendidos = [g for g in grupos if g["estado"] == "atendido"]
    abandonos = [g for g in grupos if g["estado"] == "abandono"]
    promedio = lambda valores: float(np.mean(valores)) if valores else 0.0
    duracion = fin - apertura
    recursos = [{"recurso": nombre, "ocupado_minutos": tiempo, "utilizacion": tiempo / duracion if duracion else 0.0} for nombre, tiempo in ocupacion.items()]
    metricas = {
        "grupos_llegados": len(grupos), "grupos_atendidos": len(atendidos), "grupos_abandonados": len(abandonos),
        "personas_llegadas": sum(g["personas"] for g in grupos), "personas_atendidas": sum(g["personas"] for g in atendidos),
        "personas_abandonadas": sum(g["personas"] for g in abandonos),
        "tasa_abandono": len(abandonos) / len(grupos) if grupos else 0.0,
        "espera_mesa_media": promedio([g["espera_mesa"] for g in grupos]),
        "espera_mesa_atendidos": promedio([g["espera_mesa"] for g in atendidos]),
        "espera_mesa_p95": float(np.percentile([g["espera_mesa"] for g in grupos], 95)) if grupos else 0.0,
        "tiempo_sistema_medio": promedio([g["tiempo_sistema"] for g in atendidos]),
        "fin_jornada": fin, "duracion_jornada": duracion,
    }
    for tipo in ("mesa", "mesero", "cocinera"):
        metricas[f"utilizacion_{tipo}"] = promedio([r["utilizacion"] for r in recursos if r["recurso"].startswith(tipo + "-")])
    for actividad in ("pedido", "preparacion", "entrega", "cobro"):
        metricas[f"espera_{actividad}_media"] = promedio([g[f"espera_{actividad}"] for g in atendidos])
    return metricas, recursos
