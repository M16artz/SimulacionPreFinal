# Implementación por fases

**Actualización 1.1.0:** quedaron implementadas la integración temporal de cinco colas y siete contrastes de Little, con presentación y exportación. La verificación actual alcanza **82 pruebas Pytest, 14 Vitest, 8 de servicios Node y build aprobados**. Los cuatro casos de navegador completaron sus aserciones; el cierre de servidores de Playwright quedó limitado por el entorno Windows. Las referencias a dependencias pendientes de las filas históricas siguientes quedan reemplazadas por [el informe actual](VERIFICACION_1.1.md).

Se desarrolló en orden, con límites entre responsabilidades. «Implementado» describe el código entregado; la aceptación completa requiere ejecutar las suites señaladas. No se consideran aprobados los tiempos operativos pendientes.

En la continuación se añadieron gestión concurrente de trabajos, progreso y recuperación de consultas, experimentos por consola, sensibilidad por unidad de recurso, presentación de diferencias pareadas y scripts de preparación/verificación. La evidencia actual incluye **31 pruebas Python y 8 pruebas de servicios TypeScript aprobadas**. Entre ellas se ejecutaron un trabajador real en otro proceso, exportaciones por consola, Pareto y sensibilidad. Las filas siguientes conservan el alcance de cada fase; HTTP, SciPy, React y navegador todavía necesitan sus dependencias para cerrar la aceptación.

| Fase | Entrega implementada | Criterio de aceptación | Evidencia actual |
|---|---|---|---|
| 1. Contratos y dominio | Configuración versionada, distribuciones, grupos, eventos, resultados, rangos y errores | Contratos válidos, rechazo de probabilidades incorrectas, franjas discontinuas, valores no finitos y pendientes | Contratos y validación ejecutados dentro de 14 pruebas del motor; pruebas parametrizadas Pytest añadidas |
| 2. Motor SimPy | Poisson por tramos, grupos, asignación atómica y compatible, paciencia, meseros compartidos, cocina, consumo y pago | Exclusión de recursos, dos mesas simultáneas, cancelación, atención tras el cierre y ejecución por consola | Motor ejecutado; 14 pruebas automatizadas aprobadas |
| 3. Análisis | Métricas, trazabilidad, semillas independientes, demanda común, intervalos t y diferencias pareadas | Conteos coherentes, reproducción exacta, demanda idéntica y estadística por réplicas | Métricas y demanda común verificadas; suite SciPy/Pytest pendiente |
| 4. API y configuración | FastAPI, CRUD y duplicación, YAML/JSON, pool de procesos, historial y CSV/JSON | HTTP 202, estados consultables, snapshot conservado y exportaciones correctas | Código compilado; integración HTTP pendiente de dependencias |
| 5. Frontend | React/TypeScript/Vite, cinco vistas, editor, animación por eventos, Recharts y comparación | Validación, reproducción reversible e indicadores iguales a la API | Sintaxis TS/TSX verificada; Vitest, compilación de tipos y navegador pendientes |
| 6. Optimización y cierre | Producto cartesiano de rangos, Pareto, sensibilidad, suites y documentación | Combinaciones limitadas, objetivos explícitos, pruebas integradas y recorrido completo | Implementación y pruebas entregadas; aceptación integral pendiente de red |

## Contratos de coordinación

- Andrés: dominio y validaciones en `backend/src/restaurante/dominio`.
- Yandri: procesos y recursos en `backend/src/restaurante/simulacion`.
- Miguel: indicadores, réplicas y Pareto en `backend/src/restaurante/analisis`.
- Melissa/Katheryn: archivos, casos de uso, API e interfaz.

La distribución sirve para mantener el proyecto posteriormente. No se contactó a integrantes ni se ejecutó trabajo en su nombre.

## Trazabilidad de requisitos

| Requisitos | Implementación y pruebas |
|---|---|
| RF-B01–B02, RF-C01–C07 | `dominio/contratos.py`, `api/principal.py`, `test_dominio.py`, `test_api.py` |
| RF-B03–B13 | `simulacion/`, `test_mesas.py`, `test_motor.py`, `test_estadistica.py`, `test_motor_sin_pytest.py` |
| RF-B14–B15 | Eventos con snapshot, `analisis/metricas.py`, pruebas de invariantes y conteos |
| RF-B16–B18, RF-C08 | `analisis/experimentos.py`, `estadistica.py`, rangos y límites del contrato |
| RF-B19–B20, RF-C04 | Exportaciones, consola y almacenamiento de solicitud/configuración/semilla/entorno |
| RF-F01–F08, F14 | Editor en español, JSON Schema, validación API, guardado/importación/exportación |
| RF-F09–F11 | `Sala.tsx`, reloj e índice de reproducción, `reproduccion.test.ts` |
| RF-F12–F13 | `Experimentos.tsx`, tablas, IC, sensibilidad, rangos y Pareto |
| RF-F15 | CSS adaptable con reglas para escritorio, tableta y móvil; inspección visual pendiente |
| RF-C09–C10 | Muestreo por contrato y configuración sintética diferenciada |
| RNF-01–RNF-12 | Separación modular, español, versiones, procesos, pruebas y documentación; aceptación integral pendiente |

## Orden para cerrar la aceptación

1. Instalar dependencias con acceso a PyPI/npm y generar los archivos de bloqueo.
2. Ejecutar Pytest, Vitest y compilación TypeScript/Vite.
3. Ejecutar Playwright y revisar las vistas en escritorio y móvil.
4. Revisar y aprobar las distribuciones pendientes con el equipo del proyecto.
5. Ejecutar nuevos experimentos con esos parámetros; archivar configuración, semillas y exportaciones.

Los cuatro primeros módulos no dependen de terminar la interfaz. La referencia sin tiempos completos se puede editar y guardar, pero nunca ejecutar silenciosamente.
