# Verificación anterior · modelo 1.0

Este informe conserva el estado de la entrega anterior. El estado actual, con dependencias disponibles y pruebas de la formulación matemática, está en [VERIFICACION_1.1.md](VERIFICACION_1.1.md).

## Ejecutado en este entorno

- Motor SimPy completo con el ejemplo sintético y semilla 42.
- **31 pruebas de `unittest` aprobadas**: las 14 originales del motor y 17 nuevas de consola, archivos, CSV/JSON, expansión de rangos, Pareto, sensibilidad, admisión concurrente, recuperación de trabajos y ejecución real en otro proceso.
- **8 pruebas TypeScript aprobadas con Node**: conservación de métricas, envío de parámetros, errores HTTP, respuestas no válidas, desconexión, cancelación y reproducción de eventos. Ejecutan los módulos reales `api.ts` y `reproduccion.ts`; no comprueban React ni sustituyen el build.
- Compilación sintáctica Python de código fuente y pruebas mediante `compileall`.
- Análisis de sintaxis TypeScript/TSX con Tree-sitter. Esta comprobación no equivale a `tsc` ni a una compilación Vite.

Las dependencias del motor pudieron recuperarse de la caché local existente y copiarse al entorno virtual del proyecto. No se modificaron paquetes globales ni se descargaron paquetes por una vía alternativa.

La prueba de procesos comprueba que el PID del trabajador es distinto del PID de la prueba, conserva la configuración pese a cambios posteriores del solicitante y registra progreso completado. Las pruebas concurrentes de admisión utilizan un ejecutor controlado para comprobar el límite de solicitudes sin depender del tiempo de cómputo.

Se detectó y corrigió un `PermissionError` transitorio de Windows cuando una consulta coincidía con el reemplazo del archivo de resultados. Las operaciones de lectura y reemplazo ahora reintentan esos bloqueos durante un plazo acotado. Los errores permanentes se siguen propagando.

La consola se ejecutó además con exportaciones reales en `datos/entrega/resultado.json` y `datos/entrega/grupos.csv`. `scripts/verificar.py` guarda la evidencia más reciente en `documentacion/evidencia_verificacion.json` y devuelve un código de error si la aceptación completa está bloqueada.

## Ejecución sintética registrada

| Parámetro/indicador | Resultado |
|---|---|
| Semilla | 42 |
| Configuración | `configuraciones/ejemplos/sintetica.yaml` |
| Mesas / meseros / cocineras | 11 / 1 / 3 |
| Grupos llegados / atendidos / abandonados | 158 / 93 / 65 |
| Personas llegadas / atendidas / abandonadas | 433 / 219 / 214 |
| Espera media por mesa | 10,673077 minutos |
| Tasa de abandono | 41,139241 % |
| Utilización de mesas | 74,659556 % |
| Fin de atención | 21:12,99; minuto 1272,991626 |
| Entorno | Python 3.14.4, SimPy 4.1.2, NumPy 2.5.4, Pydantic 2.14.1 |

El resultado íntegro se encuentra localmente en `datos/verificacion-semilla-42.json`, excluido de Git por ser un archivo generado. Puede regenerarse con la consola usando esa configuración y semilla. Estos valores prueban una ejecución técnica, no una conclusión sobre un restaurante real.

## Pendiente de ejecución

- Suite completa de Pytest, incluidas integración HTTP y SciPy.
- Experimentos completos con intervalos t y comparación pareada en ejecución real. La expansión de rangos, dominancia de Pareto y sensibilidad sí se ejecutaron en pruebas independientes.
- Instalación npm, `tsc`, build Vite, Vitest y Playwright.
- Inspección visual de la interfaz en escritorio y móvil.

La instalación de Python desde PyPI falló con `WinError 10013` (conexión de red no permitida). npm también falló al acceder al registro con `EACCES`; se probó una caché dentro del espacio de trabajo para descartar el problema inicial de acceso a su caché global. FastAPI, SciPy, Pytest y las dependencias frontend no están disponibles en la caché recuperable utilizada.

Las suites y el flujo de integración continua están entregados para ejecutar la aceptación completa en un entorno con acceso a dependencias. `scripts/preparar.py` automatiza la instalación y sólo registra bloqueos de versiones después de resolver paquetes realmente. Estos bloqueos completos todavía no pudieron generarse aquí. No se afirma que las verificaciones pendientes hayan pasado.
