# BuildCorp Public Storefront Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking. Ejecución nativa elegida por el usuario; no repartir implementación entre subagentes.

**Goal:** Completar la experiencia pública de BuildCorp en templates: catálogo ilustrado, registro obligatorio para solicitar alquiler, seguimiento de solicitudes y confirmación firmada por bodega.

**Architecture:** Ampliar el monolito Django/DRF existente con vistas públicas y privadas diferenciadas, sin otro frontend. Los servicios de solicitudes usan las reglas transaccionales actuales de inventario, mantenimiento, entrega y cargos. Migraciones incrementales preservan la base y las cuentas que el usuario ya creó en EC2.

**Tech Stack:** Python 3.12, Django 5.2, DRF, PostgreSQL/psycopg, Pillow, HTML/CSS/JavaScript y generación de imágenes originales. Reutilizar las versiones fijadas del proyecto; no agregar servicios de frontend ni de correo.

**Spec:** ../specs/2026-11-10-public-storefront-design.md, aprobada por el usuario con registro obligatorio y 404 propio.

## Global Constraints
- Los cambios serán locales en C:/Users/vimat/Desktop/Clases/2do sm/backend_eva3.
- Crear una cuenta e iniciar sesión es obligatorio para enviar cualquier solicitud de alquiler; no habrá alquiler ni solicitudes anónimas.
- La solicitud no retiene stock.
- Se conserva Webpay en integración, sin pago por registrar una solicitud.
- La firma, tarifa vigente y vencimiento se revisan en ese momento [la entrega].
- No se harán operaciones AWS/DNS ni push desde esta tarea.
- Se preserva el método de ejecución elegido por el usuario: implementación en este chat; subagentes solamente si son estrictamente necesarios.
- El usuario encargó también las imágenes al asistente y la actualización final de prompts_ia.md; no debe buscar imágenes por su cuenta.

## Review Focus
1. Identificaciones equivalentes con puntos, espacios o guion no pueden producir dos contratistas ni permitir apropiarse de datos existentes; migración no destructiva ante colisiones (tarea 1).
2. Una petición anónima o con destino next externo no puede crear solicitudes ni producir redirección abierta; el registro/ingreso conserva la selección (tareas 1 y 3).
3. Cliente altera campos de precios/roles/contratista, repite envío o intenta cancelar una solicitud ajena: el servidor conserva identidad, estimación e idempotencia (tareas 1 y 3).
4. Cancelación y entrega simultáneas, o dos solicitudes del mismo activo: una sola transición coherente y un solo préstamo activo (tarea 4).
5. Imágenes excesivas/inválidas, activos privados/baja y firmas ajenas nunca se convierten en recursos públicos; 404 web y API siguen sus formatos respectivos (tareas 2 y 5).

## Organización de archivos
Rutas relativas a backend_eva3; conservar web/views.py para operaciones actuales y añadir módulos públicos específicos.
- accounts/identity.py, forms.py, services.py, views.py, urls.py: validación de identidad, registro y acceso por rol.
- accounts/models.py, inventory/models.py y migraciones nuevas: restricciones normalizadas e imagen opcional de activo.
- inventory/catalog.py, images.py, validators.py: consulta pública limitada, entrega de imagen y validación compartida.
- rentals/request_models.py importado por rentals/models.py, request_services.py, request_forms.py, request_views.py, request_serializers.py, request_api.py: solicitudes, transiciones, formularios y API privada.
- web/storefront.py, selection.py, urls.py y buildcorp/urls.py: portada, catálogo, selección y rutas.
- templates/public/base.html, home.html, catalog.html, tool.html, selection.html, register.html; templates/requests/list.html, detail.html, fulfill.html; templates/404.html: presentación.
- static/css/storefront.css, static/images/tools/*, static/images/README.md: estilos, imágenes originales y procedencia.
- tests/test_registration.py, test_identity_migrations.py, test_catalog_public.py, test_requests.py, test_request_concurrency.py y test_error_pages.py: verificación del cambio.
- docs/ACTUALIZAR_EC2.md y documentación existente: actualización del servidor, modelo, arquitectura, defensa y evidencias.

## Ejecución y comprobaciones
Trabajar en la rama local actual backend/buildcorp, que el usuario usa en GitHub; no crear otro checkout que contradiga la carpeta elegida. Crear ledger propio .superpowers/public-storefront-progress.md y registrar decisiones y resultados; conservar el ledger anterior. PostgreSQL local de BuildCorp: puerto 55433, base y credenciales existentes; las pruebas usan bases temporales, nunca la base EC2.

Leer habilidades de ejecución, pruebas, diseño visual y generación de imágenes cuando corresponda. Antes de modificar código, iniciar PostgreSQL y correr la suite actual de 52 pruebas como baseline. Cada tarea de código sigue prueba roja de comportamiento → implementación → prueba verde; pruebas más amplias solo al integrar cambios o resolver hallazgos. Guardar commits locales acotados y no incluir .env, .local, media, sesiones o tokens.

Los comandos de test siguientes usan `.venv/Scripts/python.exe manage.py` en Windows. En Linux corresponde `.venv/bin/python manage.py`. Al escribir `manage.py test ...`, ejecutar con el Python del entorno.

### Tarea 1: Registro público y migraciones de identidad
**Archivos:** accounts/identity.py, forms.py, services.py, views.py, urls.py, models.py; inventory/models.py; migraciones nuevas de ambas apps; tests/test_registration.py y test_identity_migrations.py.
**Interfaces:** normalize_tax_id(value: str) -> str; validate_rut(value: str) -> str; register_customer(*, username, first_name, last_name, email, tax_id, company_name, phone, password) -> User. LoginView con destino local seguro y destino por rol: personal /panel/, cliente /mis-solicitudes/. Registro disponible en /cuenta/registro/.
- [x] Escribir test_valid_registration_creates_own_contractor: RUT 12.345.678-5 produce usuario CONTRATISTA, is_staff=False, is_superuser=False, contraseña cifrada y Contractor propio; dos POST iguales no duplican entidades.
- [x] Escribir test_invalid_rut_and_password_are_atomic, test_duplicate_normalized_identity_cannot_claim_company y test_privilege_fields_are_rejected: sin usuario/contratista parcial ni vínculo a un contratista ajeno; correo no vacío sin distinguir mayúsculas y usuario duplicado se rechazan.
- [x] Escribir pruebas MigrationExecutor de preservación de cuenta/contratista/préstamo y detección de colisión preexistente. Correos vacíos múltiples siguen permitidos. Restaurar migraciones finales al terminar el test para no contaminar otros módulos.
- [x] Ejecutar `manage.py test tests.test_registration tests.test_identity_migrations --noinput` y registrar fallos por funcionalidades ausentes.
- [x] Implementar normalización única en base de datos (quitar puntos/espacios/guion y normalizar mayúsculas), validación de RUT en registro y constraints de correo no vacío. Ante colisiones de datos antiguos, RunPython explica los IDs afectados y aborta sin modificar/borrar registros.
- [x] Implementar formulario con UserCreationForm/validadores Django y alta atómica. No aceptar role, is_staff, is_superuser o contractor desde el cliente. No asociar cuentas públicas a una entidad existente por RUT/correo. Capturar IntegrityError de carreras como error de formulario sin mostrar SQL.
- [x] Ejecutar pruebas anteriores y suite de cuentas existente; comprobar `makemigrations --check --dry-run` y migración real local. Commit local de tarea verificada.

### Tarea 2: Catálogo público, imágenes y portada
**Archivos:** inventory/catalog.py, images.py, validators.py, models.py, forms/serializers/Admin afectados; web/storefront.py; templates/public/*; static/css/storefront.css; static/images/tools/*; static/images/README.md; nueva migración Asset.image; tests/test_catalog_public.py.
**Interfaces:** public_assets() -> QuerySet[Asset], disponible de forma anónima y limitada a activos no BAJA con categoría/bodega/obra activas; available_for_request(asset, at=None) -> bool combina estado y mantenimiento; tool_image(request, pk) -> FileResponse con obtención de archivo por activo publicado. validate_tool_image(file) -> None; image opcional de activo con MEDIA_ROOT privado del repositorio y ruta pública controlada.
- [x] Escribir test_public_catalog_and_filters, test_public_projection_hides_operational_data y test_due_or_unavailable_asset_cannot_be_selected: mostrar nombre/categoría/imagen/tarifa, sin serie, bodega, contratista, movimientos ni firmas.
- [x] Escribir test_image_limits_and_formats: JPEG/PNG/WebP de hasta 512 KiB y 4096 píxeles por dimensión; rechazar contenido falso, otros formatos y excesos. test_unpublished_image_is_404_and_fallback_works cubre assets sin foto, baja y archivo inexistente.
- [x] Ejecutar `manage.py test tests.test_catalog_public --noinput`; observar resultados rojos relevantes.
- [x] Implementar consulta, filtros y paginación; portada / y catálogo/ficha. Trasladar tablero a /panel/ y actualizar sus enlaces y pruebas existentes: el anónimo ya no debe ser redirigido al visitar /.
- [x] Aplicar diseño visual de tienda pública coherente con BuildCorp: encabezado público, buscador, fichas, categorías y acciones claras; mantener operaciones separadas por navegación. Añadir imagen opcional a edición de herramientas web/API/Admin, pasando request.FILES y usando el mismo validador.
- [x] Usar la habilidad imagegen y su herramienta para preparar imágenes originales referenciales de las familias existentes: perforación, corte/desbaste, compactación, hormigonado, medición, energía y soldadura. Integrar recursos locales por categoría y una imagen principal si aporta a la portada. No pedir al usuario buscar imágenes ni usar enlaces remotos como dependencia de ejecución. Registrar qué se generó y no presentarlo como fotografía exacta de un equipo real.
- [x] Ejecutar pruebas de catálogo e inventario, collectstatic e inspección visual inicial. Confirmar que el endpoint público no acepta rutas arbitrarias y no expone firmas. Commit local de tarea verificada.

### Tarea 3: Selección y envío privado de solicitudes
**Archivos:** rentals/request_models.py, models.py, request_services.py, request_forms.py, request_views.py, request_serializers.py, request_api.py; web/selection.py y rutas; templates/public/selection.html, templates/requests/*; nueva migración; tests/test_requests.py.
**Interfaces:** RentalRequest, RentalRequestItem; request_selection(session) -> list[int]; submit_request(*, actor, asset_ids, site_name, site_address, responsible, starts_at, ends_at, notes, submit_key) -> RentalRequest; visible_requests(user) -> QuerySet; cancel_request(*, request_id, actor) -> RentalRequest. Estados PENDIENTE, ENTREGADA, RECHAZADA, CANCELADA; FK al préstamo opcional y único.
- [x] Escribir test_guest_can_browse_but_cannot_submit_and_keeps_selection: tras GET/POST permitido de selección, el envío anónimo dirige a ingreso con next local, no crea solicitudes, y conserva los IDs al autenticarse. test_external_next_is_rejected cubre registro y acceso.
- [x] Escribir test_server_recomputes_estimate y test_duplicate_submission_is_idempotent: dos herramientas a 1000 y 2000 CLP por día, 24 h previstas → 3000; 24 h y un segundo → 6000; el cliente no controla importes/contratista. Misma clave y mismo contenido retorna la misma solicitud; clave con contenido diferente se rechaza.
- [x] Escribir test_empty_or_invalid_dates_rejected, test_blocked_customer_cannot_submit y test_only_own_pending_request_can_be_cancelled. Validar mantenimiento vencido sin cron e identificación de contratista desde sesión, no desde POST.
- [x] Ejecutar `manage.py test tests.test_requests --noinput` y registrar fallos relevantes.
- [x] Implementar selección de IDs únicos, formularios de fechas/obra/responsable y cálculo de estimación en servidor. Solo clientes activos con Contractor pueden enviar. La selección se vacía después de confirmar la transacción; fallo conserva datos para corregirlos.
- [x] Implementar alta idempotente, detalle/listado por contractor_scope y cancelación atómica de pendientes. Los IDs y claves de envío tienen restricciones relacionales; aplicar CSRF y permisos tanto en web como en API. No modificar stock, no crear Loan, Charge ni PaymentAttempt al solicitar.
- [x] Ejecutar pruebas de solicitudes/cuentas/catálogo y migraciones. Comprobar que observaciones y nombre de obra se escapan en templates y no se expone el listado de obras internas al público. Commit local de tarea verificada.

### Tarea 4: Resolución por bodeguero y entrega firmada
**Archivos:** rentals/request_services.py, request_forms.py, request_views.py, request_api.py, admin.py; templates/requests/fulfill.html y bandeja; tests/test_requests.py y test_request_concurrency.py; ajustes mínimos en el servicio de entrega si fueran imprescindibles.
**Interfaces:** fulfill_request(*, request_id, site_id, responsible, due_at, signature, actor) -> Loan; reject_request(*, request_id, reason, actor) -> RentalRequest. Consume issue_loan actual y conserva tarifa de LoanItem de la entrega. Bandeja privada /solicitudes/.
- [x] Escribir test_fulfill_creates_one_signed_loan, test_fulfill_is_idempotent y test_fulfill_failure_rolls_back: una entrega repetida retorna el Loan existente; firma o disponibilidad inválida no deja documentos/estados parciales.
- [x] Escribir test_customer_cannot_resolve, test_rejection_requires_reason y test_expired_request_cannot_be_fulfilled: personal resuelve, cliente solo consulta/cancela lo suyo, y vencimiento pasado impide entrega.
- [x] Escribir TransactionTestCase con dos conexiones para test_cancel_vs_fulfill_one_transition y test_two_requests_one_asset_one_active_loan. Usar barrera y cierre de conexiones; no simular concurrencia con dos llamadas secuenciales.
- [x] Ejecutar pruebas anteriores y observar resultados rojos.
- [x] Implementar bloqueo en orden Contractor → RentalRequest → activos ordenados, reutilizando issue_loan dentro de atomic. No extender el bloqueo de datos a llamadas bancarias. No emitir cargos ni solicitudes de pago al entregar.
- [x] Implementar revisión de tarifas vigentes respecto a estimación, obra operativa, responsable y firma con canvas existente. La entrega contiene todas las herramientas solicitadas. Rechazo/cancelación no borran historial. Registrar modelos nuevos en Admin con búsquedas/filtros y sin edición genérica de históricos.
- [x] Ejecutar pruebas de solicitudes/concurrencia y regresión rentals/maintenance/charges/payments. Commit local de tarea verificada.

### Tarea 5: Errores 404 y navegación completa por rol
**Archivos:** web/errors.py, buildcorp/urls.py, web/urls.py, templates/404.html, templates/base.html, templates/public/base.html, templates/registration/login.html; tests/test_error_pages.py y ajustes en test_web.py/test_accounts.py.
**Interfaces:** page_not_found(request, exception) -> HttpResponse(status=404), asignado a handler404. Web muestra «Página no encontrada» y enlace «Volver al inicio» a /; rutas /api/ responden JSON 404. Errores 403 conservan su significado.
- [x] Escribir pruebas con DEBUG=False de URL desconocida para anónimo/autenticado, botón correcto, ausencia de detalles técnicos y JSON para URL API desconocida. Registro y solicitud no convierten 403 ni objetos ajenos en redirección de éxito.
- [x] Ejecutar `manage.py test tests.test_error_pages --noinput` y registrar fallos.
- [x] Implementar handler/template, enlaces cruzados de portada/ingreso/registro/selección, navegación del cliente y personal. No redirigir automáticamente un 404. Verificar que una URL de préstamo/firma ajena siga protegida y que /panel/ conserve autenticación.
- [x] Ejecutar pruebas de errores/cuentas/web y actualizar los asserts antiguos que exigían login en / únicamente cuando contradigan la nueva portada pública. Commit local de tarea verificada.

### Tarea 6: Recorrido completo y documentación de actualización
**Archivos:** scripts/ui_server.py, docs/ACTUALIZAR_EC2.md, README.md, docs/ARQUITECTURA.md, MODELO_RELACIONAL.md, DEFENSA.md, VERIFICACION.md, static/images/README.md y prompts_ia.md.
**Interfaces:** instrucciones de actualización manual desde la rama/remoto usados en EC2, conservando .env, PostgreSQL y media. No ejecutar acciones en AWS, DNS ni GitHub.
- [x] Iniciar servidor QA con PostgreSQL temporal separado. Recorrido de navegador: visitante abre portada/catálogo/ficha → prepara selección → se registra → envía solicitud → personal confirma con firma → cliente consulta préstamo → devolución genera cargo; continuar con la regresión de Webpay de integración existente, sin pretender validar producción.
- [x] Revisar escritorio/móvil, imágenes realmente cargadas, navegación por rol, errores de formularios que conservan datos, 404 con botón y ausencia de desbordamiento de página. Guardar evidencias locales sin sesiones/tokens en Git. Cerrar navegador/servidor y retirar cuentas/base QA al terminar.
- [x] Ejecutar `manage.py check`, `manage.py makemigrations --check --dry-run`, `manage.py migrate --check`, `manage.py collectstatic --noinput`, `manage.py test tests --noinput` y comprobación de formato. Leer resultados y registrar los realmente observados; no declarar completa una prueba fallida o pendiente.
- [x] Documentar catálogo, registro obligatorio, solicitud sin reserva y diferencias entre estimación, tarifa de entrega y cargo final. Incorporar modelos/rutas nuevas al modelo relacional y vistas 4+1.
- [x] Escribir ACTUALIZAR_EC2.md con comprobación de cambios locales/remoto, respaldo privado, parada temporal de BuildCorp, git pull --ff-only, pip install, migrate, collectstatic, check, arranque y comprobación con curl/systemctl. Conservar .env y media, actualizar IP/orígenes/Nginx si corresponde y explicar diagnóstico/recuperación sin borrar bases ni revertir migraciones ciegamente.
- [x] Actualizar prompts_ia.md después de completar el trabajo, incluyendo solicitudes reales de tienda pública, cuenta obligatoria, 404, imágenes originales, pruebas y guía de actualización. Redacción profesional y transparente; no inventar consultas o actividades realizadas por el usuario.
- [x] Una revisión independiente final acotada solo si la exige el flujo de revisión aplicable; no abrir trabajadores para implementación. Cerrar/interrumpir al revisor al recibir el informe y ejecutar regresiones para hallazgos importantes. Guardar commits locales y entregar instrucciones; el usuario publicará GitHub y operará EC2.

## Revisión propia
Cobertura completa: identidad/migraciones (1), catálogo/imágenes (2), selección/solicitud/registro obligatorio (3), entrega y seguimiento (4), 404 y navegación (5), verificación/documentación/actualización EC2/prompts IA (6). Los cinco puntos de Review Focus tienen pruebas asignadas. Los servicios nuevos reaplican reglas existentes y no anticipan cobros ni reservas. No se introduce un segundo sistema de permisos, de stock o de firma.

## Estado de aprobación
Especificación y plan aprobados por el usuario antes de implementar. Ejecución nativa completada en este chat. Pruebas automatizadas, revisión acotada, recorrido de navegador y comprobaciones finales registrados en docs/VERIFICACION.md. Los cambios de código de las tareas 1–5 se agruparon en un commit de funcionalidad después de verificar su integración; la documentación se entrega en un commit separado. La publicación GitHub y actualización de EC2 corresponden al usuario.
