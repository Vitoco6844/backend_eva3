# Verificación ejecutada

Fechas: 9 y 10 de noviembre de 2026, America/Santiago. Proyecto: backend_eva3. Esta evidencia corresponde a ejecución local; no acredita despliegue público en AWS.

## Ajuste a pago previo, verificación final

Suite `.venv/Scripts/python.exe manage.py test tests --noinput`: **114 pruebas en 76.412 segundos, OK**, PostgreSQL real, base separada creada y retirada. La ejecución previa a la corrección horaria también pasó con 113 pruebas en 74.454 segundos. Los resultados siguientes de 90/52 pruebas se conservan como evidencia de versiones anteriores y no describen el flujo vigente de nuevas entregas.

Se observaron ciclos RED→GREEN de migración histórica, aprobación/retención/cancelación, pago previo/entrega, liquidación y web/API. Incluye competencia por un activo, cancelación simultánea con creación de pago, doble entrega idempotente, cargos iniciales sin préstamo, monto bancario incoherente, cargos anulados, titularidad y bloqueo de entrega directa. Las regresiones anteriores conservan firmas, horas, mantenimiento y morosidad. Pruebas específicas verifican retorno anticipado/a tiempo sin extra, diez horas tarde por $6.000, devolución parcial con una sola línea tardía y duración UTC en cambio horario.

La prueba de migración retrocede en una base temporal a rentals0002/payments0001 y comprueba que el préstamo y cargo anteriores, pago aprobado, identificadores y contraseña se conservan; asigna LEGACY_POSTPAID a filas existentes y PREPAID como default nuevo. En la base local de desarrollo se creó un pg_dump privado, se comprobó su legibilidad con pg_restore --list y luego ambas migraciones se aplicaron correctamente. No se presenta el listado del respaldo como prueba de restauración ni como migración probada en EC2.

Revisión independiente final: un revisor Astra, solo lectura, sin DB/red/secretos. Encontró un Important: se formateaba UTC sin zona en el datetime-local del operador, desplazando el inicio tres horas. Se reprodujo con 15:02 frente a 12:02, se corrigió mediante localtime y la nueva prueba pasó en 0.664 segundos, seguida de la suite completa de 114. El revisor terminó y fue detenido; no hubo una segunda revisión. Su alcance excluyó ejecución EC2, concurrencia empírica, navegador y proveedor; estos últimos tres se verificaron por el principal localmente.

Recorrido real de Edge/Playwright CLI con base temporal test_buildcorp_ui y DEBUG=False: visita anónima → ficha → selección → registro conservando herramienta → solicitud de dos días de Taladro percutor a $6.000/día → aprobación de bodega por $12.000. La interfaz mostró retención y cero acciones de entregar antes del pago. El titular leyó condiciones e inició el cargo INITIAL, completó el formulario oficial de `webpay3gint.transbank.cl` con tarjeta y credenciales bancarias ficticias, regresó a BuildCorp y vio pago aprobado y autorización de integración. Se confirmó la solicitud pagada y se realizó entrega con firma; devolución anticipada con nueva firma y 2.50 horas produjo total $12.000, pagado $12.000 y pendiente $0, sin EXTRA ni segundo cobro. Esta prueba usó el proveedor real de integración, no un mock, y no movió dinero real. Los datos de prueba se contrastaron con la [documentación oficial de Transbank](https://transbankdevelopers.com/documentacion/como_empezar).

En móvil 390×844, solicitud/cargo/préstamo respondieron 200 con document.scrollWidth=390 e innerWidth=390. Se inspeccionaron capturas y se mantienen tablas con desplazamiento interno. El formulario del operador mostró la hora chilena correcta. Capturas locales excluidas de Git: prepaid-payment-approved.png, prepaid-return-no-extra.png, prepaid-request-mobile.png, prepaid-payment-mobile.png y prepaid-loan-mobile.png en output/playwright/.

Decisiones de implementación: las fixtures de regresión representan expresamente documentos legacy en la DB de test; no existe bandera productiva para saltar pago. La propiedad loan.charge se conserva solo para lectura histórica y el producto nuevo usa loan.charges. Los tests de carrera usan un reloj común estable, evitando mocks temporales independientes entre threads. El código y las migraciones tienen commits locales; la publicación GitHub y ejecución EC2 corresponden al usuario.

Comprobaciones finales de prepago: Django check sin errores; makemigrations --check --dry-run sin cambios; migrate --check sin pendientes; collectstatic con 181 archivos fuente y 443 procesados; pip check sin incompatibilidades; Ruff format --check con 134 archivos correctos; git diff --check limpio. Se cerró el navegador y servidor QA, y se comprobó que su base PostgreSQL temporal, contraseña y sesiones de esta ejecución fueron retiradas. El respaldo local privado se conserva fuera de Git.

## Ampliación de tienda pública, 10 de noviembre

Suite final posterior a las correcciones: `.venv/Scripts/python.exe manage.py test tests --noinput` → **90 pruebas en 54.861 segundos, OK** (repetición final de entrega; la ejecución anterior también aprobó en 56.866 segundos), con PostgreSQL real y base de pruebas separada. Incluye registro con RUT válido y correo único, rechazo de rol/identidad inyectados, preservación de datos anteriores en migraciones, acceso público al catálogo, imágenes validadas, selección anónima, solicitud sin reserva/cargo, titularidad, envío repetido, confirmación concurrente, tarifas, cancelación/rechazo y 404 web/API. Se conservan las regresiones previas de devolución, mantenimiento, morosidad y Webpay con proveedor simulado.

Se hizo una revisión independiente acotada de lectura de código. El revisor no ejecutó pruebas, navegador ni AWS y no inspeccionó secretos. Terminó y fue detenido. Se reprodujeron y corrigieron la selección bloqueada al desaparecer veinte activos publicados y el parámetro de categoría Unicode que provocaba error 500. La revisión propia añadió una regresión de duración UTC al cambiar horario de verano. Los tres casos quedaron verdes antes de ejecutar la suite completa.

Navegador real (Edge, Playwright CLI), con `DEBUG=False`, servidor temporal y base `test_buildcorp_ui`: visitante abre portada/ficha y agrega Taladro percutor sin sesión → se registra y conserva la selección → solicita dos días a $6.000/día → estimación $12.000. Consulta directa de QA confirmó estado PENDIENTE, cero Loan, cero Charge y activo DISPONIBLE. Operador confirma con obra y firma dibujada → devolución con 2.50 horas y nueva firma → cliente consulta solicitud entregada, préstamo cerrado, constancias y cargo de $6.000 por el mínimo de un día real. No se inició otro pago bancario en este recorrido; se mantiene separada la evidencia anterior de integración real y las regresiones automatizadas.

Portada de escritorio a 1440×1000: ancho de página 1440. Portada, catálogo, registro, selección vacía y 404 a 390×844: ancho de página 390 en todas, sin desbordamiento horizontal. Se recorrieron y decodificaron todas las imágenes antes de capturar: 7/7 en portada y 12/12 en catálogo. La ruta ficticia respondió 404, el enlace «Volver al inicio» apunta a `/` y devolvió efectivamente a la portada. Se inspeccionaron capturas de escritorio, catálogo móvil y 404 móvil. La consola registró un 400 esperado al editar transitoriamente fechas inválidas y un 404 solicitado expresamente; no se observó una excepción JavaScript.

Capturas locales de esta ampliación: `output/playwright/storefront-home-desktop.png`, `storefront-home-mobile.png`, `storefront-catalog-mobile.png`, `storefront-register-mobile.png`, `storefront-selection-mobile.png`, `storefront-404-mobile.png` y `storefront-selection.png`. Están excluidas de Git, igual que sesiones y credenciales temporales.

Comprobaciones finales de la ampliación: `check` sin errores; `makemigrations --check --dry-run` sin cambios; `migrate --check` sin pendientes; `collectstatic` correcto (181 archivos fuente, 444 procesados); `pip check` sin incompatibilidades; `ruff format --check .` con 122 archivos formateados; `git diff --check` limpio. Se cerró el navegador QA y se verificó que su base temporal, contraseña y sesiones de esta ejecución fueron retiradas.

Las imágenes generadas y las fotografías subidas se distinguen de las firmas privadas. La ampliación no fue desplegada en EC2 desde este trabajo; ACTUALIZAR_EC2.md describe los pasos que realizará el usuario.

## Evidencia de la versión inicial

Los resultados siguientes corresponden a la versión previa de 52 pruebas y se conservan como antecedentes, incluidos sus recorridos de integración. No se atribuyen como nuevos ensayos de la ampliación.

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
