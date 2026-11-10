# BuildCorp EVA3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Entregar BuildCorp ejecutable en local con PostgreSQL, gestión completa del caso y Webpay de prueba.

**Architecture:** Monolito Django/DRF con sesiones y templates. Servicios transaccionales compartidos por API, web y Admin; PostgreSQL aplica restricciones de integridad. Sin reemplazos de herramientas en esta versión.

**Tech Stack:** Python, Django, DRF, PostgreSQL/psycopg, django-environ, WhiteNoise, SDK oficial de Transbank o cliente REST basado exclusivamente en documentación oficial. Seleccionar versiones compatibles, verificarlas y fijarlas durante preparación; no copiar versiones del proyecto anterior sin comprobar disponibilidad.

**Spec:** ../specs/2026-11-09-buildcorp-design.md (aprobada por el usuario en el chat).

## Global Constraints
- Todo artefacto nuevo se guarda en C:/Users/vimat/Desktop/Clases/2do sm/backend_eva3.
- No modificar EVA2 ni copiar bases, claves, usuarios, repositorio Git, entornos virtuales o módulos de conciertos.
- Monolito Django con DRF, PostgreSQL obligatorio y templates HTML/CSS/JavaScript responsivos.
- No ofrecer selección de producción; rechazar una configuración distinta a integración.
- prompts_ia.md registra apoyos reales con redacción profesional, sin inventar consultas ni ocultar alcance de asistencia.
- No ejecutar acciones en AWS, DNS ni publicar en GitHub.
- Reemplazos temporales durante mantenimiento: fuera del alcance inicial, conforme al último mensaje del usuario.

## Review Focus
- Dos entregas concurrentes del mismo activo: solo una puede confirmarse (tarea 3).
- Morosidad y mantenimiento vencidos sin ejecutar el proceso periódico: bloquear igualmente la entrega (tareas 3 y 4).
- Retorno Webpay sin cookie de sesión, repetido o con timeout: confirmar mediante proveedor sin duplicar pago ni permitir reintento incierto (tarea 6).
- Contratista modifica identificadores de otro contratista: denegar acceso a préstamos, firmas y comprobantes (tareas 1, 3 y 6).
- Devolución parcial, horas decimales y cambio de tarifa posterior: mantener horas y cobro histórico exactos (tareas 3 y 5).

## Estructura de archivos
Todas las rutas siguientes son relativas a backend_eva3.
- buildcorp/settings.py, urls.py, wsgi.py: configuración, rutas y servidor.
- accounts/models.py, permissions.py, admin.py: usuario, roles y autorización.
- inventory/models.py, services.py, serializers.py, views.py, admin.py: contratistas, obras, bodegas, categorías, activos y movimientos.
- rentals/models.py, services.py, signatures.py, serializers.py, views.py, admin.py: entrega, devolución, firmas y alertas.
- maintenance/models.py, services.py, serializers.py, views.py, admin.py: planes y trabajos de mantenimiento.
- payments/models.py, services.py, gateway.py, serializers.py, views.py, admin.py: cargos, intentos y proveedor Webpay.
- web/views.py, forms.py, urls.py; templates/; static/css/app.css; static/js/signature.js: interfaz.
- tests/test_accounts.py, test_inventory.py, test_rentals.py, test_concurrency.py, test_maintenance.py, test_charges.py, test_payments.py, test_web.py: verificación por dominio.
- Cada app incluye apps.py, __init__.py y migrations/ propias.
- scripts/configurar.ps1, iniciar.ps1, detener.ps1, local_db.py: ejecución local aislada.
- docs/ARQUITECTURA.md, MODELO_RELACIONAL.md, DESPLIEGUE_EC2.md, DEFENSA.md, VERIFICACION.md, REUTILIZACION.md; README.md; prompts_ia.md.

## Convenciones de ejecución y pruebas
Ejecutar desde backend_eva3 con su propio .venv. Los comandos de abajo usan `.venv/Scripts/python.exe`; en Linux usar `.venv/bin/python`. PostgreSQL de BuildCorp tendrá base y credenciales propias, sin utilizar ni detener el servidor/base de EVA2. Si se reutilizan binarios del PostgreSQL portable, crear clúster y puerto separados y documentarlo. No ejecutar borrados de datos para solucionar fallos de configuración.

Cada tarea de código sigue rojo → implementación → verde. Los nombres de pruebas y sus resultados esperados se fijan a continuación; los datos se crean en factories/fixtures propias sin claves reales. Crear commits pequeños solo si existe un repositorio propio de backend_eva3; nunca incluir el repositorio padre o EVA2.

### Tarea 1: Base, sesiones y administración
**Archivos:** buildcorp/*, accounts/*, manage.py, requirements.txt, .gitignore, .env.example, scripts/*, templates/registration/login.html, tests/test_accounts.py.
**Interfaces:** User.role con ADMIN/BODEGUERO/CONTRATISTA; User.contractor opcional a inventory.Contractor; can_operate(user) -> bool; contractor_scope(user, queryset, field) -> QuerySet. Login y logout mediante sesiones de Django.
- [x] Escribir test_staff_does_not_grant_business_role, test_contractor_cannot_manage_users, test_session_requires_csrf, test_login_logout. Verificar acceso denegado sin sesión, CSRF 403 al escribir sin token y cierre efectivo de sesión.
- [x] Ejecutar `.venv/Scripts/python.exe manage.py test tests.test_accounts --noinput`; registrar fallo inicial por componentes ausentes, sin confundir un error de conexión con una prueba funcional roja.
- [x] Crear entorno independiente y configuración PostgreSQL propia, ajustar selectivamente scripts de EVA2, implementar roles y permisos y habilitar Admin. Usar FK diferida a inventory.Contractor y generar migraciones al disponer del modelo de la tarea 2.
- [x] Ejecutar migrate, check y las pruebas anteriores; exigir cero errores. Documentar componentes reutilizados en docs/REUTILIZACION.md.

### Tarea 2: CRUD de inventario y trazabilidad
**Archivos:** inventory/*, accounts/migrations/*, tests/test_inventory.py, web/forms.py, web/views.py, templates/inventory/*.
**Interfaces:** Contractor, Site, Warehouse, Category, Asset, AssetEvent; transfer_asset(*, asset_id, warehouse_id, actor, reason) -> Asset; retire_asset(*, asset_id, actor, reason) -> Asset. API CRUD /api/contractors/, sites/, warehouses/, categories/, assets/; acciones /assets/{id}/transfer/ y retire/.
- [x] Escribir test_crud_by_role, test_transfer_creates_event, test_retire_protects_history, test_duplicate_asset_code, test_direct_state_edit_rejected. Assert un evento por traslado, origen correcto, rechazo de duplicados y de cambio directo de estado/bodega.
- [x] Ejecutar `manage.py test tests.test_inventory --noinput` con el Python del entorno; observar fallos correspondientes a las reglas aún ausentes.
- [x] Implementar modelos, restricciones y migraciones, servicios atómicos, API con permisos y formularios. Proteger referencias históricas con PROTECT y desactivar registros usados. En Admin, estado y bodega se modifican mediante servicios, nunca edición genérica.
- [x] Ejecutar migrate y `manage.py test tests.test_accounts tests.test_inventory --noinput`; exigir aprobación de ambos módulos.

### Tarea 3: Préstamos, firmas, devoluciones y bloqueo
**Archivos:** rentals/*, tests/test_rentals.py, tests/test_concurrency.py, static/js/signature.js, templates/rentals/*.
**Interfaces:** Loan, LoanItem, Signature, OverdueAlert; issue_loan(*, contractor_id, site_id, asset_ids, due_at, responsible, signature, actor) -> Loan; return_items(*, loan_id, items, signature, actor) -> Loan; is_delinquent(contractor_id, at=None) -> bool; refresh_overdue_alerts(at=None) -> int. items contiene item_id, usage_hours decimal, damaged boolean y notes. Firma recibe PNG en data URL con tamaño máximo 256 KiB y validación real del PNG; guardar bytes privados y hash, no SVG/HTML arbitrario. Rechazar firma vacía.
- [x] Escribir test_double_issue, test_partial_return, test_repeated_return, test_overdue_blocks_without_job, test_invalid_signature, test_foreign_signature_denied, test_decimal_hours. Assert un solo préstamo activo por activo, devolución repetida rechazada sin sumar horas, y contratista ajeno con 404/403.
- [x] Ejecutar pruebas de rentals y concurrency para observar fallos iniciales; usar TransactionTestCase y conexiones independientes para concurrencia real de PostgreSQL.
- [x] Implementar restricciones de préstamo activo, bloqueos ordenados y transacciones. Serializar también por contratista para evitar carreras en la evaluación del bloqueo. Guardar firma/documento inmutable con responsable y momento; formularios usan canvas accesible y alternativa de reintento.
- [x] Entrega consulta maintenance.is_due; devolución usa maintenance.requires_maintenance. Durante esta tarea agregar pruebas con contrato de esas funciones y completar su integración en tarea 4. Cierre total crea cargo usando payments.close_charge de tarea 5; hasta entonces no declarar completo el recorrido de cierre.
- [x] Ejecutar pruebas de préstamos/concurrencia y de autorización de firmas. Resolver alertas de préstamos regularizados sin alterar bloqueo manual.

### Tarea 4: Mantenimiento periódico
**Archivos:** maintenance/*, rentals/management/commands/revisar_alertas.py, tests/test_maintenance.py, templates/maintenance/*.
**Interfaces:** MaintenancePlan, MaintenanceJob; is_due(asset, at=None) -> bool; requires_maintenance(asset, damaged=False, at=None) -> bool; start_maintenance(*, asset_id, actor, notes) -> MaintenanceJob; finish_maintenance(*, job_id, actor, notes, next_due_at, next_due_hours) -> MaintenanceJob. Comando revisar_alertas integra refresh_overdue_alerts y revisa planes.
- [x] Escribir test_due_date_blocks_issue, test_due_hours_blocks_issue, test_plan_requires_limit, test_finish_sets_next_limits, test_job_is_idempotent, test_in_use_due_is_flagged. Assert rechazo al alcanzar fecha/horas, plan sin límites inválido, nuevos límites futuros y activos en uso alertados sin retirarles el préstamo.
- [x] Ejecutar `manage.py test tests.test_maintenance --noinput`; registrar fallos iniciales.
- [x] Implementar modelos y servicios; horas Decimal no decrecientes. Un trabajo activo por herramienta. No cambiar un activo En Uso a Mantenimiento hasta su devolución. Impedir préstamo por plan vencido aunque el estado aún sea Disponible. Personalizar Admin y pantallas del calendario/listado.
- [x] Ejecutar pruebas maintenance/rentals/concurrency, y revisar_alertas dos veces verificando ausencia de duplicados. Documentar periodicidad configurable del comando.

### Tarea 5: Cargos históricos exactos
**Archivos:** payments/models.py, payments/services.py, payments/admin.py, tests/test_charges.py, templates/payments/charge.html.
**Interfaces:** Charge (uno por préstamo cerrado); close_charge(loan) -> Charge; visible_charges(user) -> QuerySet. Cada LoanItem conserva tarifa y fecha efectiva de devolución. No hay cierre económico antes de devolución completa.
- [x] Escribir test_partial_return_has_no_final_charge, test_historical_rate, test_day_rounding, test_charge_created_once. Para tarifa 1000: 1 hora cuesta 1000; 24 horas cuesta 1000; 24 horas y 1 segundo cuesta 2000. Cada línea usa su propia devolución; cambiar tarifa de catálogo no cambia su cargo.
- [x] Ejecutar `manage.py test tests.test_charges --noinput`; comprobar fallos iniciales.
- [x] Implementar cálculo con duración y redondeo exactos, sin float ni monto enviado por cliente. Guardar cargo una sola vez bajo transacción; no permitir editar montos finales en API/Admin.
- [x] Ejecutar pruebas charges/rentals; verificar un cierre completo crea exactamente un cargo y conserva tarifas históricas.

### Tarea 6: Webpay Plus en integración
**Archivos:** payments/gateway.py, services.py, views.py, serializers.py, urls.py, migrations/*, tests/test_payments.py, templates/payments/*, .env.example.
**Interfaces:** WebpayGateway.create(*, buy_order, session_id, amount, return_url) -> dict; commit(token) -> dict; status(token) -> dict. start_payment(*, charge_id, actor) -> PaymentAttempt; confirm_payment(token) -> PaymentAttempt; reconcile_payment(attempt_id) -> PaymentAttempt. Gateway inyectable para pruebas. Estados: CREATING, PENDING, UNKNOWN, APPROVED, REJECTED, CANCELLED, EXPIRED; timeout conserva UNKNOWN y bloquea reintento hasta conciliación.
- [x] Consultar documentación y repositorio oficiales para fijar SDK/endpoints, credenciales de integración, tarjetas de prueba, retornos y estados; registrar fuentes. No inventar firma de SDK ni códigos de respuesta.
- [x] Escribir test_approved, test_rejected, test_cancelled, test_expired, test_amount_mismatch, test_unknown_token, test_duplicate_return, test_sessionless_return, test_timeout_requires_reconciliation, test_foreign_charge, test_production_config_rejected. Assert pago aprobado solo tras validación de monto/orden/estado/respuesta, un efecto por retorno y acceso restringido al comprobante.
- [x] Ejecutar `manage.py test tests.test_payments --noinput`; comprobar fallos funcionales iniciales.
- [x] Implementar gateway fijo de integración con timeout; confirmar desde servidor y conciliar estado desconocido. No mantener transacciones abiertas durante llamadas HTTP: reservar intento bajo bloqueo, llamar proveedor y persistir resultado con verificación de estado. Índice único de intento activo por cargo; orden única; token privado. Retorno de cancelación por identificadores de Transbank exige consultar proveedor antes de liberar un intento pendiente. Rechazar configuraciones/URLs de producción.
- [x] Ejecutar las pruebas anteriores sin conexión bancaria mediante dobles. Si se hace prueba manual contra integración, usar solo tarjetas oficiales ficticias y registrar su resultado separado de las pruebas unitarias. Aviso visible: «Ambiente de integración: pago de prueba, sin cobro real».

### Tarea 7: Interfaz integrada y Admin completo
**Archivos:** web/*, templates/base.html, dashboard.html, templates/admin/base_site.html, templates de cada dominio, static/css/app.css, tests/test_web.py; admin.py de las apps.
**Interfaces:** rutas /, /accounts/login/, /inventory/, /rentals/, /maintenance/, /alerts/, /payments/, /admin/, /api/; todas privadas salvo ingreso y retorno externo controlado. Usar servicios de tareas anteriores desde web y API, sin lógica paralela.
- [x] Escribir test_dashboard_by_role, test_crud_forms, test_return_validation_preserves_form, test_private_signature, test_admin_cannot_bypass_transitions. Assert navegación por rol, mensajes en español, formularios inválidos conservan datos y Admin no salta reglas.
- [x] Ejecutar `manage.py test tests.test_web --noinput`; observar fallos iniciales.
- [x] Implementar tablero, navegación responsiva, filtros, listas vacías, historial, firmas y comprobantes privados. Admin registra todos los modelos con búsqueda/filtros y campos históricos de solo lectura; restringir altas genéricas de documentos transaccionales y ofrecer acciones/formularios de servicios.
- [x] Ejecutar suite y recorrido de navegador en escritorio y móvil: alta de herramienta → préstamo firmado → devolución parcial/total → mantenimiento → cargo → intento Webpay. Verificar 403/404 con otro contratista y ausencia de errores de consola/red en recorridos locales.

### Tarea 8: Reproducibilidad, documentación y defensa
**Archivos:** README.md, prompts_ia.md, docs/*, scripts/*, inventory/management/commands/seed_demo.py, deploy/gunicorn.conf.py, deploy/buildcorp.service.example, deploy/nginx.conf.example.
**Interfaces:** configurar.ps1 prepara entorno/base propia, migrate y collectstatic; iniciar.ps1 ejecuta local; seed_demo es idempotente y no crea contraseñas compartidas; revisar_alertas ejecutable por cron sin navegador.
- [x] Verificar instalación desde requisitos fijados, migraciones y seed_demo repetido sin duplicados. Crear administrador mediante createsuperuser, con contraseña elegida por usuario.
- [x] Ejecutar `manage.py check`, `manage.py makemigrations --check --dry-run`, `manage.py migrate --check`, `manage.py test tests --noinput`, `manage.py collectstatic --noinput`. Registrar salidas reales en docs/VERIFICACION.md. No afirmar prueba de integración Webpay ni despliegue si no se ejecutaron.
- [x] Documentar vistas lógica, desarrollo, procesos y física más escenarios (+1), diagrama relacional y tabla requisito→pantalla→prueba. Preparar defensa con roles, flujo firmado, vencimiento, mantenimiento y pagos ficticios.
- [x] Escribir guía EC2 con PostgreSQL local a la instancia, Gunicorn, Nginx, variables/secretos, migraciones, estáticos, cron, copias/restauración, HTTPS y pasos posteriores de DuckDNS. Incluir ejemplos revisables sin ejecutar servicios cloud, DNS o publicación.
- [x] Actualizar prompts_ia.md con apoyo realmente solicitado y procedencia de reutilización; comprobar que .env, datos locales, firmas, tokens y credenciales no formen parte de archivos de entrega.

## Revisión propia del plan
Cobertura: tareas 1–2 cubren seguridad/CRUD/Admin/PostgreSQL; 3 cubre firmas, devolución y morosidad; 4 mantenimiento por fecha/horas; 5–6 cargos/Webpay; 7 integra interfaz y administración; 8 ejecución y documentación 4+1/EC2/IA. Dependencias diferidas de tareas 3–5 están nombradas y se verifican en conjunto antes de declarar completo el flujo. Los cinco riesgos de Review Focus tienen pruebas asignadas. No se agrega reemplazo de herramientas.

## Revisión y ejecución
Estado: plan aprobado por el usuario; ejecución nativa completada y verificada, con límites registrados en docs/VERIFICACION.md. Recomendación: ejecución nativa en este chat, por la dependencia entre préstamos, mantenimiento y pagos; no lanzar subagentes salvo elección explícita del usuario. Alternativa: implementación por subagentes con revisiones separadas y mayor coordinación. Tras aprobación del plan y método, ejecutar tarea por tarea y comunicar resultados y limitaciones concretas.
