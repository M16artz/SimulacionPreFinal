"""Figuras científicas con ReportLab Charts, exclusivamente a partir del CSV E3."""
import json
from pathlib import Path
from reportlab.graphics.shapes import Drawing, String, Rect
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics.widgets.markers import makeMarker
from reportlab.graphics import renderSVG
from reportlab.lib import colors

CARPETA = Path(__file__).resolve().parent
DATOS = json.loads((CARPETA / "analisis_verificado.json").read_text(encoding="utf-8"))["fuentes"]["E3"]["filas"]
INDICE = {tuple(int(f[k]) for k in ("mesas", "meseros", "cocineras")): f for f in DATOS}
VERDE, AZUL, NARANJA = map(colors.HexColor, ("#27665c", "#3e6b96", "#c08332"))


def lienzo(titulo, subtitulo):
    dibujo = Drawing(1050, 600)
    dibujo.add(Rect(0, 0, 1050, 600, fillColor=colors.white, strokeColor=None))
    dibujo.add(String(70, 560, titulo, fontName="Helvetica-Bold", fontSize=21, fillColor=colors.HexColor("#243a34")))
    dibujo.add(String(70, 533, subtitulo, fontName="Helvetica", fontSize=12, fillColor=colors.HexColor("#52635e")))
    dibujo.add(String(70, 24, "Fuente: experimento(2).csv. Medias de 5 réplicas con semillas comunes; datos sintéticos.", fontSize=11, fillColor=colors.HexColor("#52635e")))
    return dibujo


def barras(claves, columnas, maximo, paso, titulo, subtitulo, etiquetas, archivo):
    dibujo = lienzo(titulo, subtitulo)
    grafico = VerticalBarChart()
    grafico.x, grafico.y, grafico.width, grafico.height = 85, 110, 900, 345
    grafico.data = [[INDICE[c][columna] * escala for c in claves] for columna, escala in columnas]
    grafico.categoryAxis.categoryNames = ["/".join(map(str, c)) for c in claves]
    grafico.categoryAxis.labels.fontSize = 12
    grafico.valueAxis.labels.fontSize = 11
    grafico.valueAxis.valueMin, grafico.valueAxis.valueMax, grafico.valueAxis.valueStep = 0, maximo, paso
    grafico.valueAxis.visibleGrid = True
    grafico.valueAxis.gridStrokeColor = colors.HexColor("#e5eae7")
    grafico.bars.strokeColor = None
    for i, color in enumerate((VERDE, AZUL, NARANJA)[:len(columnas)]):
        grafico.bars[i].fillColor = color
    if len(columnas) == 1:
        grafico.barLabelFormat = lambda valor: f"{valor:.2f}".replace(".", ",")
        grafico.barLabels.fontSize = 11
        grafico.barLabels.nudge = 7
    dibujo.add(grafico)
    dibujo.add(String(365, 68, "Configuración: mesas / meseros / cocineras", fontSize=13))
    for i, (etiqueta, color) in enumerate(zip(etiquetas, (VERDE, AZUL, NARANJA))):
        x = 220 + i * 230
        dibujo.add(Rect(x, 485, 14, 12, fillColor=color, strokeColor=None))
        dibujo.add(String(x + 22, 486, etiqueta, fontSize=12))
    renderSVG.drawToFile(dibujo, str(CARPETA / archivo))


def main():
    barras([(11, 1, 3), (13, 2, 4), (13, 3, 5), (13, 3, 6), (13, 3, 7)], [("tiempo_sistema_medio_media", 1)], 80, 10,
           "Permanencia media de los grupos atendidos", "Tiempo desde llegada hasta pago y salida (minutos). Los intervalos se presentan en la tabla de resultados.", ["Permanencia (min)"], "figura_1_permanencia.svg")
    dibujo = lienzo("Efecto de ampliar la capacidad de cocina", "Permanencia media (minutos), manteniendo 13 mesas y 3 meseros. El eje vertical comienza en 40 min.")
    grafico = LinePlot()
    grafico.x, grafico.y, grafico.width, grafico.height = 85, 110, 900, 365
    valores = [(c, INDICE[(13, 3, c)]["tiempo_sistema_medio_media"]) for c in range(3, 8)]
    grafico.data = [valores]
    grafico.joinedLines = True
    grafico.xValueAxis.valueMin, grafico.xValueAxis.valueMax, grafico.xValueAxis.valueStep = 3, 7, 1
    grafico.yValueAxis.valueMin, grafico.yValueAxis.valueMax, grafico.yValueAxis.valueStep = 40, 55, 5
    grafico.xValueAxis.labels.fontSize = grafico.yValueAxis.labels.fontSize = 12
    grafico.yValueAxis.visibleGrid = True
    grafico.yValueAxis.gridStrokeColor = colors.HexColor("#e5eae7")
    grafico.lines[0].strokeColor = VERDE
    grafico.lines[0].strokeWidth = 2
    grafico.lines[0].symbol = makeMarker("FilledCircle", size=8, fillColor=VERDE, strokeColor=VERDE)
    dibujo.add(grafico)
    for c, valor in valores:
        x = 85 + (c - 3) / 4 * 900
        y = 110 + (valor - 40) / 15 * 365 + 16
        dibujo.add(String(x, y, f"{valor:.2f}".replace(".", ","), textAnchor="middle", fontSize=12))
    dibujo.add(String(435, 67, "Cantidad de cocineras", fontSize=13))
    renderSVG.drawToFile(dibujo, str(CARPETA / "figura_2_cocina.svg"))
    barras([(11, 1, 3), (13, 2, 4), (13, 3, 5), (13, 3, 6)], [("utilizacion_mesa_media", 100), ("utilizacion_mesero_media", 100), ("utilizacion_cocinera_media", 100)], 100, 20,
           "Utilización media por tipo de recurso", "Porcentaje del tiempo ocupado sobre la jornada completa, incluida la atención posterior al cierre.", ["Mesas", "Meseros", "Cocineras"], "figura_3_utilizacion.svg")
    print("Tres figuras SVG generadas con datos verificados de E3.")


if __name__ == "__main__":
    main()
