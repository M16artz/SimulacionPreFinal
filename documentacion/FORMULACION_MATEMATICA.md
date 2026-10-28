# Etapa 5 · Formulación matemática implementada

La versión 1.1.0 del modelo añade integración de colas por estación y contraste de la ley de Little. Todos los tiempos se expresan en minutos y las poblaciones en **grupos**, no en personas, mesas ni pedidos individuales. Los eventos contienen el estado posterior a cada cambio.

## Correspondencia con el código

| Expresión | Implementación |
|---|---|
| λ(t), Poisson por franjas | `configuraciones/referencia.yaml` y `simulacion/generador_llegadas.py`: intervalos exponenciales con media 60/λ |
| Utilización U | `simulacion/motor.py` acumula minutos ocupados; `analisis/metricas.py` divide por T y promedia servidores |
| Espera Wq | `motor.py` registra tiempo desde solicitud hasta adquisición; `metricas.py` promedia los registros |
| Longitud Lq | `analisis/colas.py`, `integrar_escalones` y `calcular_colas_y_little` |
| Permanencia W | `motor.py`: salida menos llegada; `metricas.py`: promedio entre atendidos |
| Abandono | `metricas.py`: grupos abandonados / grupos llegados; el frontend convierte a porcentaje |
| Ley de Little | `analisis/colas.py`, `contrastar_little` |

## Longitudes de cola

El motor registra las listas `estado.colas.mesa`, `pedido`, `preparacion`, `entrega` y `cobro`. Se añaden eventos `entrada_cola_<actividad>` al solicitar personal o cocina; el grupo sale de esa cola al comenzar el servicio. `estado.cola` conserva el formato anterior y equivale a la cola de mesas. Las cinco estaciones pueden compartir personal sin compartir el significado de sus esperas.

Para cada estación se calcula exactamente:

`área_i = Σ Q_i(t_j) × (t_{j+1} − t_j)`

`Lq_i = área_i / T`

No hay muestreo periódico, interpolación lineal ni promedio simple de las longitudes observadas. Los eventos simultáneos aportan duración cero. El tiempo inicial y final sin cola también forma parte del denominador. El área tiene unidad grupo·minuto y su división entre minutos produce grupos.

En la cola de mesas, N y Wq incluyen tanto a los que obtienen mesa como a los que abandonan. Para las demás estaciones se cuentan todos los grupos que pasan por ellas, incluidos aquellos con espera cero.

## Periodo y poblaciones para Little

Se observa desde la apertura hasta finalizar la atención de todos los grupos admitidos, incluidos los abandonos de la cola de mesas. Se conserva el periodo completo después del cierre. Para esa misma ventana se registra `estado.en_sistema` en cada evento y se calcula la ocupación temporal del sistema.

Se publican siete contrastes:

1. Las cinco colas: `Lq_i` frente a `(N_i/T) × Wq_i`.
2. Sistema completo: L y W incluyen grupos atendidos y abandonados, con tasa efectiva `N_llegados/T`.
3. Sistema de atendidos: W incluye sólo grupos que completan el servicio, la tasa es `N_atendidos/T` y L se obtiene filtrando los estados por los identificadores de esa misma cohorte.

La tasa efectiva se expresa en **grupos/minuto**. No se sustituye por 8 o 25 grupos/hora ni por la tasa calculada sólo durante el horario de admisión.

`L = integral de la población observada / T`

`λ_ef = N / T`

`W = suma de permanencias de esa población / N`

El contraste utiliza el error absoluto `|L − λ_ef W|` y una comparación numérica con tolerancias absoluta y relativa de 10⁻⁹. Los lados se calculan por vías diferentes: L desde los eventos y W desde los registros de los grupos. Una discrepancia se conserva como `coincide=false`; no se fuerza la igualdad.

## Condiciones de aplicación y límites

Se utiliza una identidad de balance para una cohorte completa que empieza y termina con el sistema vacío. La coincidencia es una comprobación contable del registro; **no demuestra estado estacionario**, estabilidad a largo plazo, distribución exponencial de servicios ni condiciones M/M/s. No se implementan fórmulas M/M/s porque este restaurante no satisface esas hipótesis de forma general.

Si faltan salidas o los extremos no están vacíos, el contraste se marca `aplicable=false`. Con N=0, W, el producto y el error son `null`, y `coincide` también es `null`. No se interpreta ausencia de observaciones como evidencia de cumplimiento. Una ventana truncada al cierre requeriría un tratamiento explícito de las entidades que quedan dentro; esta versión no aplica Little a esa ventana.

## Resultado y exportación

Cada nueva ejecución contiene `formulacion_matematica` con periodo, áreas, longitudes, esperas y los siete contrastes con sus poblaciones y unidades. Las longitudes y poblaciones medias también aparecen como indicadores numéricos en `metricas`, por lo que participan en los resúmenes de experimentos sin cambiar sus objetivos de Pareto.

La vista **Resultados → Colas y ley de Little** muestra estos datos. El JSON completo los incluye. La API permite CSV mediante:

- `/api/v1/simulaciones/{id}/exportar?formato=csv&tabla=colas`
- `/api/v1/simulaciones/{id}/exportar?formato=csv&tabla=little`

Las ejecuciones de la versión 1.0 conservan sus archivos y resultados. No se inventan poblaciones faltantes a partir de ellos: la interfaz indica que hace falta repetir su configuración y semilla para obtener el nuevo análisis.

## Verificación

`backend/tests/test_formulacion_sin_pytest.py` contiene casos con integrales conocidas, eventos simultáneos, dos grupos calculables a mano, colas de pedido y cocina, abandono, jornada vacía, cohortes incompletas y discrepancias intencionales. En una ejecución sintética completa se contrasta además el área de cada cola contra la suma independiente de esperas individuales.

Ejemplo manual: con una mesa y actividades fijas de un minuto, G1 llega en 0 y sale en 5; G2 llega en 1, obtiene mesa en 5 y sale en 10. El área de la cola de mesas es 4, Lq=0,4, Wq=2 y λ=0,2. Para el sistema, el área es 5+9=14, L=1,4 y W=7; por tanto λW=1,4.
