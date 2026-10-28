# Mesa · Simulador de restaurante

Aplicación académica modular para configurar, simular, reproducir y comparar jornadas de restaurante. El motor Python/SimPy funciona por consola; FastAPI lo ejecuta en procesos separados y React reproduce sus eventos sin volver a simularlos.

La implementación está organizada en seis fases en [el plan de trabajo](documentacion/FASES.md). El [informe de verificación](documentacion/VERIFICACION_1.1.md) distingue las pruebas ejecutadas de las limitaciones del entorno.

La [formulación matemática](documentacion/FORMULACION_MATEMATICA.md) documenta las longitudes promedio de las cinco colas y los contrastes de Little, incorporados en la versión 1.1.0. Se consultan en Resultados y se exportan en JSON y CSV.

## Inicio en Windows (PowerShell)

Requisitos: Python 3.11 o posterior, Node.js 22.18 o posterior y acceso a los registros de paquetes durante la instalación.

La preparación automática instala las dependencias y registra las versiones realmente resueltas:

```powershell
python scripts/preparar.py --navegador
```

El script crea o reutiliza `.venv`, captura las versiones Python en `backend/requirements.lock`, conserva el `package-lock.json` producido por npm e instala Chromium si se indica `--navegador`. No genera un bloqueo ficticio si falla la instalación. Si prefieres instalar manualmente:

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -e "./backend[pruebas]"
cd frontend
npm.cmd install
cd ..
```

En una terminal, desde la raíz:

```powershell
.venv/Scripts/python.exe -m uvicorn restaurante.api.principal:app --app-dir backend/src --host 127.0.0.1 --port 8000
```

En otra terminal:

```powershell
cd frontend
npm.cmd run dev
```

Abre **http://127.0.0.1:5173**. La documentación interactiva de la API está en **http://127.0.0.1:8000/docs**. Vite redirige `/api` al backend. Se utiliza `npm.cmd` para evitar depender de la política de ejecución de scripts PowerShell.

En Linux/macOS sustituye `.venv/Scripts/python.exe` por `.venv/bin/python` y `npm.cmd` por `npm`.

## Ejecución por consola

```powershell
.venv/Scripts/python.exe -m restaurante.consola configuraciones/ejemplos/sintetica.yaml --semilla 42 --salida datos/resultado.json --csv datos/grupos.csv
```

La consola crea las carpetas de salida. También puedes usar `restaurante` al activar el entorno después de instalar el paquete. La configuración de referencia conserva cuatro tiempos `null`; intentar ejecutarla produce un error explícito.

Para comparar rangos con réplicas, sin servidor ni frontend:

```powershell
.venv/Scripts/python.exe -m restaurante.consola configuraciones/ejemplos/sintetica.yaml --replicas 5 --rango-mesas 9 13 2 --rango-meseros 1 3 1 --semilla 42 --salida datos/experimento.json --csv datos/experimento.csv
```

Cada rango contiene mínimo, máximo inclusivo y paso. También se admite `--rango-cocineras`. Para ejecutar un archivo que ya tenga el contrato `SolicitudExperimento`, utiliza `restaurante archivo.yaml --experimento --salida datos/experimento.json`. En ese modo las réplicas y rangos se toman del archivo y `--semilla` permite una sustitución explícita.

## Recorrido de la aplicación

1. **Vista general:** configuración activa, indicadores del último resultado e historial persistente.
2. **Configuración:** recursos, jornada, franjas de demanda, porcentajes de grupos y distribuciones. Permite guardar, cargar, duplicar, restaurar la última versión guardada e importar YAML/JSON. La exportación del borrador es JSON; la API también exporta YAML.
3. **Restaurante en vivo:** mesas, personal, cola y bitácora de eventos. Pausa, avanza, retrocede y cambia la velocidad. El reloj es simulado, no una conexión en tiempo real con un restaurante.
4. **Resultados:** utilización, demanda, abandono, espera y exportación completa con la configuración de ejecución.
5. **Experimentos:** selecciona escenarios guardados o utiliza el borrador; ejecuta réplicas y rangos de recursos. Consulta intervalos de confianza, diferencias pareadas, sensibilidad por recurso, alternativas de Pareto e historial.

Las simulaciones y los experimentos muestran su progreso. La última consulta queda identificada en el navegador para recuperarla al recargar o volver a una vista; una pérdida de conexión no marca como fallido un cálculo que continúa en el servidor.

Los tiempos iniciales del selector de distribuciones son valores editables propuestos para completar el formulario. Nunca sustituyen automáticamente un tiempo pendiente en el backend.

## Verificación

Para ejecutar los controles disponibles y generar evidencia que distingue aprobados, fallidos y bloqueados:

```powershell
.venv/Scripts/python.exe scripts/verificar.py
```

El informe se guarda en `documentacion/evidencia_verificacion.json`. El comando devuelve un código distinto de cero cuando alguna parte falla o está bloqueada. `--motor` limita el alcance a Python, recursos, archivos, procesos, consola y optimización. Los comandos individuales son:

```powershell
.venv/Scripts/python.exe -m pytest backend/tests -v
cd frontend
npm.cmd test
npm.cmd run build
npx.cmd playwright install chromium
npm.cmd run test:e2e
```

La prueba de extremo a extremo inicia API y Vite y requiere libres los puertos 18000 y 15173. Se pueden cambiar con `RESTAURANTE_E2E_PUERTO_API` y `RESTAURANTE_E2E_PUERTO_WEB`. Usa `datos/e2e/` para conservar aislados sus datos. Verifica ejecución, reproducción, recuperación tras recarga, vista móvil, formulación matemática, configuraciones, importación de pendientes y comparación experimental. La [integración continua](.github/workflows/verificacion.yml) instala y ejecuta estas verificaciones en Linux y adjunta evidencia, versiones y trazas de los fallos. El informe documenta una limitación del cierre automático de Playwright en este Windows.

Los servicios de API y reproducción pueden probarse directamente con Node, incluso antes de instalar React/Vite:

```powershell
cd frontend
node --test tests/logica/servicios.test.mjs
```

La suite del motor también funciona sin Pytest:

```powershell
$env:PYTHONPATH = (Resolve-Path backend/src).Path
.venv/Scripts/python.exe -m unittest discover -s backend/tests -p '*sin_pytest.py' -v
```

## Estructura

```text
backend/src/restaurante/
  dominio/          Contratos Pydantic y validaciones
  simulacion/       SimPy, llegadas, mesas, personal y eventos
  analisis/         Métricas, intervalos y experimentos
  aplicacion/       Coordinación de trabajos y admisión concurrente
  infraestructura/  Distribuciones y archivos JSON
  api/              Endpoints y errores HTTP en español
frontend/src/
  modulos/          Configuración, reproducción, resultados y experimentos
  servicios/        API, validación por esquema y reloj de reproducción
  tipos/            Contratos de consumo de la API
configuraciones/    Referencia y ejemplo sintético
documentacion/      Fases, arquitectura, métricas y evidencias
```

Los parámetros se definen en `ConfiguracionRestaurante`; los formularios consumen su JSON Schema y consultan la validación de negocio centralizada. La API valida otra vez al guardar y ejecutar. El dominio no importa FastAPI ni SimPy. No se requiere base de datos ni Docker.

## Persistencia y reproducción

`datos/` almacena configuraciones y trabajos como JSON; se puede cambiar con `RESTAURANTE_DATOS`. Cada ejecución conserva su solicitud, copia de configuración, semilla, versión del motor, versiones relevantes del entorno, eventos, grupos y métricas. Actualizar una configuración guardada no altera ejecuciones anteriores. Los archivos se escriben mediante reemplazo atómico.

En la primera apertura la API carga los dos archivos YAML. En aperturas posteriores conserva las configuraciones existentes. Al reiniciar, marca como fallidos los trabajos interrumpidos; estos pueden repetirse con los mismos datos. Utiliza **un único proceso Uvicorn**, cuyo pool interno cuenta con dos trabajadores; no uses `--workers` para esta persistencia académica.

El motor es reproducible con las mismas versiones, configuración y semilla. Conserva además las versiones instaladas mediante `python -m pip freeze` y el `package-lock.json` que crea npm tras una instalación exitosa. Las versiones resueltas están registradas en `backend/requirements.lock` y `frontend/package-lock.json`.

## Alcance académico

Los resultados de ejemplo son **sintéticos**. Los tiempos de pedido, preparación, entrega y cobro todavía requieren aprobación para la referencia. No se consideran distancias, menús individuales, turnos, averías ni clientes que abandonan después de obtener mesa. Las mesas tienen una capacidad común configurable. Los grupos incompatibles con los recursos permanecen en cola hasta agotar su paciencia.

Las alternativas eficientes pertenecen sólo al conjunto evaluado y a los objetivos declarados. No constituyen un óptimo universal ni sustituyen la calibración con datos reales. Consulta [la documentación técnica](documentacion/ARQUITECTURA_Y_MODELO.md).
