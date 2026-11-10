# Verificación ejecutada

Fechas: 9 y 10 de noviembre de 2026, America/Santiago. Proyecto: backend_eva3. Esta evidencia corresponde a ejecución local; no acredita despliegue público en AWS.

## Automatizada
Comando: `.venv/Scripts/python.exe manage.py test tests --noinput`.

Resultado final observado: **52 pruebas, 33.332 segundos, OK**. Motor: PostgreSQL real. Se creó y eliminó la base separada test_buildcorp. Incluye concurrencia con conexiones independientes: dos contratistas compiten por un activo y solo uno obtiene el préstamo.

Cobertura de comportamientos: roles y sesiones/CSRF; permisos API e imágenes de firmas; CRUD y protección de relaciones históricas; transferencias y bajas; entrega duplicada y firmas inválidas; devoluciones parciales/repetidas; horas decimales y valores no finitos; morosidad sin cron; mantenimiento por fecha/horas, inicio y cierre; tarifas históricas y redondeo diario; pagos aprobados/rechazados/cancelados/expirados, identidad/monto inconsistentes, timeout, retorno sin sesión, repetición, intento pendiente recuperable; bloqueo de configuración Webpay de producción; registros inexistentes sin errores 500; modelos registrados en Admin y documentos transaccionales de solo lectura.

Comprobaciones adicionales ejecutadas:
- `manage.py check`: sin errores.
- `manage.py makemigrations --check --dry-run`: No changes detected.
- `manage.py migrate --check`: salida correcta, sin migraciones pendientes.
- `manage.py collectstatic --noinput`: estáticos compilados correctamente (166 archivos).
- `manage.py revisar_alertas`, dos ejecuciones consecutivas: sin duplicados.
- `manage.py seed_demo`, repetido: catálogo ficticio idempotente.
- `scripts/configurar.ps1 -BaseExterna`: finalizó con migraciones/estáticos/catálogo correctos utilizando la conexión local existente.
- Parseo de los tres scripts PowerShell: cero errores de sintaxis.
- Ruff 0.17.4 `format --check`: 77 archivos Python con formato correcto. No equivale a una auditoría de seguridad ni se afirma una prueba de despliegue Linux.

Los mensajes 403, 404 y 409 que aparecen en el registro de pruebas son respuestas esperadas al comprobar permisos, referencias inexistentes y protección de datos. El resultado de la suite es OK.

## Navegador real
Herramienta: Playwright CLI con Microsoft Edge; servidor WSGI temporal en 127.0.0.1:8014 y PostgreSQL temporal test_buildcorp_ui. Cuentas QA con contraseña aleatoria, independientes de la base de desarrollo.

Recorrido observado: tablero → entrega de BC-001 y BC-002 con firma dibujada → devolución parcial de BC-001 con 2.50 horas y daño → préstamo aún abierto, sin cargo final → devolución de BC-002 con 3 horas y nueva firma → cierre del préstamo y cargo de $15.500. La primera herramienta queda en Mantenimiento; la segunda Disponible.

Vista móvil de inventario a 390×844: document.scrollWidth=390 e innerWidth=390, sin desbordamiento horizontal de la página. Las tablas se desplazan horizontalmente dentro de su contenedor. Tablero e inventario fueron inspeccionados visualmente.

Capturas locales, excluidas de Git por ser evidencia de QA:
- ../output/playwright/dashboard-desktop.png
- ../output/playwright/inventory-mobile.png
- ../output/playwright/webpay-approved.png

## Transbank: prueba completa en integración
Se creó una transacción de $15.500 contra webpay3gint.transbank.cl. La creación devolvió PENDING. Se abrió el formulario oficial, se usó la tarjeta VISA ficticia 4051885600446623, vencimiento futuro, CVV de prueba 123, banco simulado con RUT 11.111.111-1 y clave 123. Se eligió Aceptar en el simulador. El navegador regresó a BuildCorp; el servidor verificó el proveedor y el comprobante mostró **Pago de prueba aprobado**, estado APPROVED y autorización de prueba 1213.

No se utilizó una tarjeta personal ni se movió dinero real. Esta prueba completa acredita el camino aprobado en integración; los demás resultados bancarios se verificaron automáticamente con dobles del proveedor, sin atribuirles pruebas manuales que no se realizaron. Fuentes: [tarjetas y ambientes oficiales](https://transbankdevelopers.com/documentacion/como_empezar), [referencia REST](https://transbankdevelopers.com/referencia/webpay).

El retorno se probó con la URL del servidor QA mediante override de PUBLIC_BASE_URL exclusivo de ese proceso. La configuración normal de desarrollo conserva el puerto 8013.

## Revisión independiente y correcciones
Se utilizó un único subagente de revisión, Astra, con contexto acotado y acceso de solo lectura a código/documentación, sin ejecutar otra suite ni acceder a secretos. Terminó al entregar su informe y se detuvo; no quedan subagentes trabajando.

Hallazgo Important: consultar un intento inicializado impedía continuarlo. Se reprodujo con dos pruebas fallidas, se corrigió para conservar PENDING tras una respuesta INITIALIZED con identidad válida, y se agregó el enlace Continuar pago de prueba al mismo intento. Un resultado incierto conserva UNKNOWN y no permite crear otro pago. Las regresiones pasan en la suite final.

Hallazgo propio: dos rutas API devolvían 500 al referenciar registros inexistentes; se reprodujo en dos pruebas y se agregó traducción de ObjectDoesNotExist a 404. Regresiones incluidas en la suite final. El revisor no reportó otros hallazgos Critical/Important; no hubo una segunda revisión independiente después de aplicar los cambios.

## Límites de la evidencia
AWS, DNS, Nginx/Gunicorn bajo Linux, HTTPS y restauración de respaldos quedan documentados para ejecución posterior del estudiante. No se han ejecutado desde este trabajo. No se implementó el reemplazo temporal de herramientas durante revisión. Un pago cuyo proveedor no permite determinar resultado queda por conciliar; un fallo de creación sin token no se libera automáticamente.

La base temporal, sus cuentas y la sesión de navegador se retiran al terminar. La base de desarrollo conserva solo datos ficticios del catálogo; el administrador debe crearse con una contraseña elegida por el usuario.

Tras la prueba se suprimió el registro por petición del servidor WSGI de QA para evitar que una nueva ejecución imprima parámetros de retorno. Se comprobó sintaxis del script; el servidor de desarrollo usa filtro de redacción y el ejemplo Nginx/Gunicorn omite query strings. Dependencias Python: pip check sin incompatibilidades. La eliminación de test_buildcorp_ui y la ausencia de cuentas de desarrollo se comprobaron consultando PostgreSQL.
