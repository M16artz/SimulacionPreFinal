"""Auditoría de los CSV originales y análisis posterior de réplicas archivadas.

No ejecuta nuevas simulaciones ni modifica las fuentes. Los intervalos pareados
son exploratorios y no incluyen ajuste por selección entre muchos escenarios.
"""
import csv
import hashlib
from itertools import product
import json
import math
from pathlib import Path
import statistics
from scipy.stats import t

RAIZ = Path(__file__).resolve().parents[2]
SALIDA = Path(__file__).resolve().parent
ARCHIVOS = {"E1": "experimento.csv", "E2": "experimento(1).csv", "E3": "experimento(2).csv"}


def clave(fila):
    return tuple(int(fila[k]) for k in ("mesas", "meseros", "cocineras"))


def intervalo(valores):
    media = statistics.mean(valores)
    margen = float(t.ppf(0.975, len(valores) - 1)) * statistics.stdev(valores) / math.sqrt(len(valores))
    return {"media": media, "inferior": media - margen, "superior": media + margen, "n": len(valores)}


def main():
    fuentes = {}
    metadatos = [(p, json.loads(p.read_text(encoding="utf-8"))) for p in (RAIZ / "datos/experimentos").glob("*.json")]
    for etiqueta, nombre in ARCHIVOS.items():
        archivo = RAIZ / nombre
        crudas = list(csv.DictReader(archivo.open(encoding="utf-8-sig", newline="")))
        filas = [{k: v if k == "nombre" else v == "True" if k == "eficiente" else float(v) for k, v in fila.items()} for fila in crudas]
        indice = {clave(fila): fila for fila in filas}
        assert len(indice) == len(filas), "Combinaciones duplicadas dentro de un CSV"
        coincidencias = []
        for ruta, trabajo in metadatos:
            escenarios = trabajo.get("resultado", {}).get("escenarios", [])
            if len(escenarios) != len(filas):
                continue
            por_recurso = {clave(e["configuracion"]): e for e in escenarios}
            if set(por_recurso) != set(indice):
                continue
            if all(math.isclose(fila["tiempo_sistema_medio_media"], por_recurso[c]["resumen"]["tiempo_sistema_medio"]["media"], abs_tol=1e-10) for c, fila in indice.items()):
                coincidencias.append((ruta, trabajo, por_recurso))
        assert len(coincidencias) == 1, f"No se identificó inequívocamente el respaldo de {nombre}"
        ruta, trabajo, por_recurso = coincidencias[0]
        resultado = trabajo["resultado"]
        for c, fila in indice.items():
            escenario = por_recurso[c]
            assert int(fila["escenario"]) == escenario["id"]
            assert fila["nombre"] == escenario["nombre"]
            assert fila["eficiente"] == escenario["eficiente"]
            for metrica, resumen in escenario["resumen"].items():
                for sufijo, valor in (("media", resumen["media"]), ("inferior", resumen["ic95"][0]), ("superior", resumen["ic95"][1])):
                    assert math.isclose(fila[f"{metrica}_{sufijo}"], valor, rel_tol=1e-12, abs_tol=1e-12)
                replicadas = [r[metrica] for r in escenario["replicas"]]
                propio = intervalo(replicadas)
                assert math.isclose(propio["inferior"], resumen["ic95"][0], abs_tol=1e-8)
                assert math.isclose(propio["superior"], resumen["ic95"][1], abs_tol=1e-8)
            for replica in escenario["replicas"]:
                assert replica["grupos_llegados"] == replica["grupos_atendidos"] + replica["grupos_abandonados"]
                assert replica["personas_llegadas"] == replica["personas_atendidas"] + replica["personas_abandonadas"]
        rangos = trabajo["solicitud"]["rangos"]
        esperadas = set(product(*(range(rangos[k]["minimo"], rangos[k]["maximo"] + 1, rangos[k]["paso"]) for k in ("mesas", "meseros", "cocineras"))))
        assert set(indice) == esperadas
        # Revisión independiente del criterio de Pareto realmente utilizado.
        def objetivos(fila):
            return (*clave(fila), fila["tasa_abandono_media"], fila["espera_mesa_media_media"])
        for fila in filas:
            valor = objetivos(fila)
            eficiente = not any(all(a <= b for a, b in zip(objetivos(otra), valor)) and any(a < b for a, b in zip(objetivos(otra), valor)) for otra in filas)
            assert eficiente == fila["eficiente"]
        fuentes[etiqueta] = {"archivo": nombre, "respaldo": str(ruta.relative_to(RAIZ)), "sha256": hashlib.sha256(archivo.read_bytes()).hexdigest(), "replicas": trabajo["solicitud"]["replicas"], "semilla": trabajo["solicitud"]["semilla"], "semillas_replicas": resultado["semillas_replicas"], "version_modelo": resultado["version_modelo"], "rangos": rangos, "configuracion": trabajo["solicitud"]["configuraciones"][0], "filas": filas, "replicas_por_configuracion": {"/".join(map(str, c)): e["replicas"] for c, e in por_recurso.items()}, "eficientes": sum(fila["eficiente"] for fila in filas)}
    por = {e: {clave(f): f for f in d["filas"]} for e, d in fuentes.items()}
    assert set(por["E2"]) <= set(por["E3"])
    cambios_etiqueta = 0
    for c, fila in por["E2"].items():
        otra = por["E3"][c]
        assert all(math.isclose(v, otra[k], abs_tol=1e-12) for k, v in fila.items() if k not in ("nombre", "eficiente", "escenario"))
        cambios_etiqueta += fila["eficiente"] != otra["eficiente"]
    comunes = set(por["E1"]) & set(por["E3"])
    for c in comunes:
        primero = fuentes["E1"]["replicas_por_configuracion"]["/".join(map(str, c))]
        tercero = fuentes["E3"]["replicas_por_configuracion"]["/".join(map(str, c))]
        assert primero == tercero[:4]
    comparaciones = []
    for nombre, anterior, posterior in (
        ("Aumentar sólo mesas", (11, 1, 3), (13, 1, 3)),
        ("Añadir segundo mesero", (11, 1, 3), (11, 2, 3)),
        ("Base frente a menor permanencia E3", (11, 1, 3), (13, 3, 6)),
        ("Sexta cocinera", (13, 3, 5), (13, 3, 6)),
        ("Séptima cocinera", (13, 3, 6), (13, 3, 7)),
    ):
        a = fuentes["E3"]["replicas_por_configuracion"]["/".join(map(str, anterior))]
        b = fuentes["E3"]["replicas_por_configuracion"]["/".join(map(str, posterior))]
        comparaciones.append({"nombre": nombre, "anterior": anterior, "posterior": posterior, "diferencias_pareadas": {metrica: intervalo([y[metrica] - x[metrica] for x, y in zip(a, b)]) for metrica in ("tiempo_sistema_medio", "tasa_abandono", "personas_atendidas", "espera_mesa_media")}})
    union = set().union(*(set(indice) for indice in por.values()))
    informe = {"fuentes": fuentes, "auditoria": {"filas_totales": sum(len(d["filas"]) for d in fuentes.values()), "configuraciones_distintas": len(union), "corridas_contabilizadas": sum(len(d["filas"]) * d["replicas"] for d in fuentes.values()), "comunes_E1_E3": len(comunes), "E2_es_subconjunto_E3": True, "etiquetas_pareto_cambiadas_E2_E3": cambios_etiqueta, "primeras_cuatro_replicas_comunes_identicas": True, "csv_y_json_coinciden": True}, "comparaciones_exploratorias": comparaciones}
    SALIDA.mkdir(exist_ok=True, parents=True)
    (SALIDA / "analisis_verificado.json").write_text(json.dumps(informe, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(informe["auditoria"], ensure_ascii=True))
    for comparacion in comparaciones:
        print(comparacion["nombre"], json.dumps(comparacion["diferencias_pareadas"], ensure_ascii=True))


if __name__ == "__main__":
    main()
