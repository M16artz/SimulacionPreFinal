# Arquitectura y modelo científico

## Límites entre módulos

`dominio` define los datos y reglas matemáticas sin importar SimPy o FastAPI. `infraestructura` interpreta distribuciones y almacena archivos. `simulacion` implementa procesos discretos. `analisis` calcula indicadores y coordina experimentos. `aplicacion` ejecuta trabajos serializables. `api` expone operaciones HTTP. React presenta configuraciones y resultados.

El mismo modelo Pydantic valida YAML importado, JSON enviado desde la interfaz y datos recibidos por la consola. Su JSON Schema permite validar estructura, tipos y rangos en el navegador. Las restricciones cruzadas se validan centralmente por `/configuraciones/validar` y de nuevo al guardar o ejecutar. Los tipos TypeScript describen el consumo de la API y no reemplazan al esquema de validación.

Distribuciones soportadas: fija (valor ≥ 0), uniforme (0 ≤ mínimo < máximo), triangular (0 ≤ mínimo ≤ moda ≤ máximo y mínimo < máximo) y exponencial (media > 0). Los tiempos están expresados en minutos. La paciencia debe estar acotada por 40 minutos; por eso no admite exponencial. Los límites máximos de campos y experimentos protegen el uso local del laboratorio.

## Proceso de llegadas

La unidad temporal interna es el minuto desde medianoche. En cada franja constante, los incrementos entre llegadas se muestrean de una exponencial con media `60/tasa`. Una llegada que cruza el final de una franja se descarta y la siguiente franja inicia un nuevo proceso independiente. Esto genera exactamente un Poisson por tramos de tasa constante, incluso si la tasa cambia a las 12:00, 14:00 o 18:00. Una tasa cero no genera llegadas. El intervalo de admisión es `[apertura, cierre)`.

Se utiliza `SeedSequence` para separar los flujos de llegadas, tamaños y paciencia. Los tiempos de servicio se derivan de semilla, identificador de grupo y actividad. Cambiar la cantidad de recursos no cambia la demanda ni los tiempos sorteados para una misma actividad del mismo grupo. Esto permite comparaciones con números aleatorios comunes.

## Recursos y reglas de atención

El gestor de mesas conserva una lista de solicitudes. Cada liberación recorre la lista en orden de llegada y atiende las solicitudes que sean compatibles con los recursos libres. Un grupo pequeño puede adelantar a un grupo grande si sólo queda una mesa; no se aplica FIFO estricto. Para grupos de 1 a 4 se necesita una mesa compatible; para grupos de 5 a 8 se adquieren exactamente dos mesas en una operación indivisible. No se juntan mesas para grupos pequeños.

La solicitud compite con un evento de paciencia. Si la paciencia vence, se elimina de pendientes. En un empate exacto se favorece una asignación que ya haya sido confirmada. Las mesas permanecen ocupadas durante todas las esperas y actividades hasta completar el cobro.

Los meseros se conservan en un `Store` FIFO identificado. Pedido, entrega y cobro adquieren una persona del mismo conjunto y la liberan al terminar. Las cocineras utilizan otro conjunto FIFO: se asigna la primera disponible y se procesa un pedido grupal sin multiplicar su duración por el tamaño del grupo. El consumo no adquiere personal.

Al cierre se detienen las llegadas. La jornada espera a que cada grupo que llegó antes del cierre complete su flujo o abandone la cola. Por tanto, un grupo que todavía espera mesa puede sentarse después del cierre. Se documenta esta interpretación de «grupos admitidos»; si se acuerda atender únicamente a los ya sentados, esa política requerirá un cambio explícito del contrato/modelo.

## Eventos y reproducción

Cada evento incluye secuencia, minuto simulado, grupo, acción, recursos afectados y snapshot de mesas, personal, cola y contadores. La secuencia desambigua eventos simultáneos. Los eventos no alteran el generador aleatorio.

El navegador sólo selecciona snapshots. El avance temporal utiliza búsqueda binaria; los botones permiten examinar la secuencia exacta. Retroceder restaura un snapshot anterior. Los indicadores instantáneos se leen del snapshot y los finales del resultado del backend.

## Definiciones de indicadores

| Indicador | Cálculo |
|---|---|
| Grupos/personas llegados | Suma de todos los grupos generados antes del cierre |
| Grupos/personas atendidos | Grupos que completan el pago y personas integrantes |
| Grupos/personas abandonados | Grupos que agotan paciencia sin mesa y personas integrantes |
| Tasa de abandono | Grupos abandonados / grupos llegados; cero si no hay llegadas |
| Espera media por mesa | Promedio de espera hasta asignación o abandono sobre todos los grupos |
| Espera de atendidos | Promedio hasta asignación entre quienes completan la atención |
| Percentil 95 de espera | Percentil empírico NumPy sobre todos los grupos |
| Esperas de personal/cocina | Tiempo desde solicitud hasta adquisición, por actividad, entre atendidos |
| Tiempo medio en el sistema | Salida menos llegada, entre los atendidos |
| Utilización de un recurso | Minutos ocupado / (fin de jornada − apertura) |
| Utilización de un tipo | Media de la utilización de sus recursos individuales |

La jornada completa incluye la atención posterior al cierre. Los grupos abandonados no aportan duración de servicio. En los CSV de grupos las columnas de servicio de los abandonados quedan vacías. Los indicadores sin observaciones se publican como cero, según esta convención explícita; no son parámetros pendientes. Los porcentajes se conservan como fracciones de 0 a 1 en API y archivos.

## Réplicas, comparación y sensibilidad

Cada réplica obtiene una semilla hija de `SeedSequence`. La misma lista se utiliza en todos los escenarios del experimento; sus semillas se exportan. La API exige las mismas franjas, probabilidades y jornada entre escenarios. Se pueden cambiar tiempos o recursos explícitamente y estudiar su efecto.

Para cada indicador se informa la media y un intervalo t de Student bilateral del 95 %: `media ± t(0.975, n−1) × s/√n`. Con una sola réplica el intervalo es `null`. Los intervalos no se recortan al rango físico, para no alterar su definición. Se calculan también diferencias pareadas respecto al primer escenario. Son aproximaciones; pocas réplicas o distribuciones asimétricas limitan su interpretación.

La búsqueda evalúa el producto cartesiano de los rangos, respetando mínimo, máximo inclusivo y paso. Se admiten hasta 200 escenarios y 1000 ejecuciones por experimento, con hasta 100 réplicas. Se minimizan simultáneamente cinco objetivos: mesas, meseros, cocineras, tasa media de abandono y espera media por mesa. Un escenario es dominado si otro no empeora ningún objetivo y mejora al menos uno. La frontera se calcula con medias observadas, no mediante pruebas de significación. No existe una función de coste monetario implícita.

La gráfica espera–abandono y los rangos permiten explorar sensibilidad. El JSON conserva los parámetros exactos, réplicas, semillas, entornos, intervalos y diferencias. No se almacenan eventos de todas las réplicas del experimento para limitar el volumen; cada réplica puede regenerarse como simulación individual con su configuración y semilla exportadas.

La sensibilidad también se calcula como diferencia finita entre escenarios vecinos de un recurso, manteniendo idénticos todos los demás parámetros salvo nombre y notas. Se informa el cambio por unidad de recurso en espera, abandono y personas atendidas. Las comparaciones que cambian simultáneamente otra hipótesis se excluyen. Las diferencias pareadas, sensibilidad y versiones se presentan en la interfaz además de exportarse.

## Persistencia y ejecución HTTP

Los identificadores son UUID. La API devuelve 202 con un identificador y envía el trabajo a `ProcessPoolExecutor`, con dos procesos y un límite de doce trabajos pendientes/en ejecución por servidor. Los trabajadores guardan estados y resultados por reemplazo atómico. Los fallos del trabajador se registran y se exponen con mensajes comprensibles. Los reinicios marcan trabajos interrumpidos como error; no existe una cola distribuida ni reanudación automática.

El gestor de trabajos protege la comprobación de capacidad y el envío mediante un cerrojo, para que solicitudes HTTP simultáneas respeten el límite. Los trabajadores registran su PID y el avance de las réplicas. En Windows se reintentan brevemente los bloqueos de archivos durante lectura o reemplazo. El navegador conserva el identificador de la última consulta; puede volver a consultarla tras una recarga o desconexión sin reiniciar el cómputo.

El servicio está destinado a uso académico local. No incluye autenticación ni acceso multiusuario. Para despliegue futuro deben configurarse un servidor para el frontend, un proxy `/api`, control de acceso y una cola/persistencia adecuadas al alcance real. La implementación actual no depende de esos componentes.

## Referencias de implementación

- [Eventos y condiciones de SimPy](https://simpy.readthedocs.io/en/latest/topical_guides/events.html): eventos de espera y resolución de condiciones.
- [Trabajos en segundo plano en FastAPI](https://fastapi.tiangolo.com/tutorial/background-tasks/): separación del cómputo pesado respecto de las solicitudes HTTP.
- [JSON Schema en Pydantic](https://docs.pydantic.dev/latest/concepts/json_schema/): generación del esquema compartido con la interfaz.
