# Estado de verificación · modelo 1.1.0

## Ejecutado

- **82 pruebas Pytest aprobadas**, incluidas API HTTP, trabajadores en procesos separados, experimentos SciPy, reproducibilidad y formulación matemática. La suite incluye las 42 pruebas compatibles con `unittest`; no son adicionales a las 82.
- **14 pruebas Vitest aprobadas**: indicadores, API, seguimiento de trabajos, reproducción y presentación de colas/Little.
- **8 pruebas de servicios TypeScript con Node aprobadas**.
- **Compilación TypeScript y build Vite aprobados**, mediante `npm run build`. Vite informa del tamaño de un paquete JavaScript superior a 500 kB; la compilación finaliza correctamente.
- Los **cuatro recorridos Playwright completaron sus aserciones**: simulación/reproducción/recarga/vista móvil, configuraciones, importación de pendientes y comparación experimental. El primero también comprueba el panel de formulación matemática y su enlace CSV.

Las dependencias que anteriormente faltaban ya estaban disponibles al verificar esta entrega. Se utilizaron las versiones resueltas en `backend/requirements.lock` y `frontend/package-lock.json`.

## Límite del cierre de Playwright en Windows

Aunque los cuatro casos mostraron éxito, la orden Playwright quedó esperando el cierre automático de sus servidores de prueba. Se detuvieron los dos servidores creados por esa ejecución y se interrumpió la orden pendiente. Por eso la evidencia marca **bloqueado el cierre de Playwright**, sin afirmar que la orden completa terminó con código cero. No se detuvieron los servidores que ya estaban abiertos en los puertos habituales.

Las pruebas utilizan ahora puertos separados: API 18000 y frontend 15173, configurables mediante `RESTAURANTE_E2E_PUERTO_API` y `RESTAURANTE_E2E_PUERTO_WEB`. Vite carga su configuración mediante el cargador nativo, compatible con Node 22.18+, para evitar el error de lectura de directorios padre durante el empaquetado de esa configuración.

## Formulación matemática comprobada

`backend/tests/test_formulacion_sin_pytest.py` aporta 11 casos incluidos en las suites anteriores: integrales conocidas, eventos simultáneos, colas calculables a mano, abandono, separación de cohortes, jornada sin llegadas, cohortes incompletas, discrepancias deliberadas y registros antiguos. Las áreas integradas también se contrastan con las sumas independientes de esperas individuales.

## Resultado sintético reproducido

Configuración: `configuraciones/ejemplos/sintetica.yaml`, semilla 42, 11 mesas, 1 mesero y 3 cocineras. Llegaron 158 grupos: 93 atendidos y 65 abandonados. La jornada terminó en el minuto 1272,991626 (21:12,99), incluida la atención posterior al cierre.

| Estación | Longitud media de cola (grupos) |
|---|---|
| Mesa | 2,300635 |
| Pedido | 0,711634 |
| Preparación | 0,030874 |
| Entrega | 0,769270 |
| Cobro | 0,769880 |

Los siete contrastes de Little resultaron compatibles. El error absoluto máximo fue 4,440892098500626 × 10⁻¹⁶ grupos. Para el sistema completo: L=10,075415, λ efectiva=0,215555 grupos/min y W=46,741742 min. Para atendidos: L=8,689466, λ efectiva=0,126877 grupos/min y W=68,487157 min. Cada relación utiliza su propia cohorte.

Los archivos generados están en `datos/entrega/resultado-v1.1.json` y `datos/entrega/grupos-v1.1.csv`. La definición y limitaciones científicas están en [FORMULACION_MATEMATICA.md](FORMULACION_MATEMATICA.md). Estos datos son sintéticos y no constituyen una calibración de un restaurante real.

## Evidencia y repetición

`documentacion/evidencia_verificacion.json` conserva las verificaciones ejecutadas y sus repeticiones después de corregir la configuración de herramientas. Para repetir todos los controles utiliza `.venv/Scripts/python.exe scripts/verificar.py`. El comando conserva un estado distinto de aprobado si una herramienta falla o no puede finalizar.
