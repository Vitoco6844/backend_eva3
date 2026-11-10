# Pago previo a la entrega — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Exigir el pago confirmado del período contratado antes de cada nueva entrega y liquidar solo el retraso al devolver, conservando los documentos históricos de EC2.

**Architecture:** Extender el monolito Django con aprobación/retención y cargos tipados previos al préstamo. Reutilizar el proveedor y sus validaciones, sin pagos manuales. Unificar las entregas nuevas en la solicitud pagada; mantener el cierre postpago exclusivamente para préstamos existentes.

**Tech Stack:** Python 3.12, Django 5.2, DRF, PostgreSQL, templates HTML/CSS/JS, Webpay Plus integration, pruebas Django y Playwright CLI.

**Spec:** docs/superpowers/specs/2026-11-10-prepaid-rentals-design.md — aprobada por el usuario; el método elegido se conserva: implementación nativa en este chat. Plan pendiente de revisión del usuario antes de ejecutar.

## Global Constraints

- La cuenta se exige al enviar la solicitud; la portada, catálogo y selección siguen públicos.
- Bodega aprueba y retiene equipos; solo el pago verificado en servidor habilita entregar con firma.
- No se ofrece reembolso automático: devolución anticipada conserva el período contratado y cancelación posterior al pago requiere revisión.
- No se opera AWS/DNS ni se publica GitHub. Conservar .env, media, usuarios, documentos e IDs existentes.
- Los préstamos existentes mantienen LEGACY_POSTPAID; los nuevos usan PREPAID y no admiten entrega directa sin su solicitud pagada.
- No instalar frameworks ni regenerar imágenes. Webpay sigue exclusivamente en integration.
- Trabajar en backend_eva3 y rama backend/buildcorp, según elección persistente del usuario. No crear implementadores paralelos. Una revisión independiente final acotada al terminar, conforme al método nativo.

## Review Focus

1. Un cliente paga una aprobación y el equipo se intenta trasladar, retirar, editar o entregar a otra persona: retención efectiva en todas las escrituras relevantes.
2. Cancelación y creación/confirmación bancaria simultáneas: no liberar equipos ni cobrar un cargo anulado; orden de bloqueos estable, sin interbloqueos entre pago y entrega.
3. Un antiguo préstamo sin solicitud y con pago previo existente migra: no pierde acceso, no cambia importe/estado ni recibe exigencia retroactiva.
4. Doble devolución o mezcla de líneas a tiempo/tarde durante cambio horario: generar únicamente el extra correcto una vez, con UTC real y sin pago de cero pesos.
5. Un envío antiguo a /api/loans/ o /rentals/new/ intenta saltarse el flujo: no crea un préstamo sin aprobación/pago; errores claros y camino útil para el personal.

## Archivos y responsabilidades

- `rentals/request_models.py`: estados aprobada/pagada, cotización aprobada, obra operativa, actor/fecha y AssetHold activo único por herramienta.
- `rentals/models.py`: modo LEGACY_POSTPAID/PREPAID y resumen de cargos del préstamo, sin dependencia de una única relación charge.
- `payments/models.py`: Charge con origen solicitud/préstamo, tipo LEGACY/INITIAL/EXTRA, anulación pendiente sin borrar historial y restricciones.
- Nuevas migraciones `rentals/migrations/0003_prepaid_approval.py`, `payments/migrations/0002_prepaid_charges.py`, con dependencias explícitas y ninguna edición de las migraciones aplicadas.
- `rentals/approval_services.py` (nuevo): aprobación/cotización versionada, creación de solicitud por operador y retenciones; cancelación/rechazo coordinados con pagos.
- `rentals/request_services.py`: envío público sin cobro y entrega de solicitud pagada; delegar aprobación y evitar crecer un único módulo.
- `payments/billing.py` (nuevo): liquidación legacy y cálculo del saldo de retraso; `payments/services.py`: pagos/conciliación/titularidad de ambos orígenes y transición pagada.
- `inventory/catalog.py`, `inventory/services.py`, `inventory/serializers.py`, `inventory/admin.py`, `maintenance/services.py`, `web/views.py`: respeto de retenciones y eliminación de supuestos antiguos en formularios/consultas.
- `rentals/request_forms.py`, `request_serializers.py`, `request_api.py`, `request_views.py`, `rentals/views.py`, `serializers.py`, `web/urls.py`: aprobación, preparación por operador y bloqueo de entrega directa.
- `payments/serializers.py`, `views.py`, `admin.py`, `rentals/admin.py` y templates de requests/payments/rentals/public: estados, acciones, titularidad y resumen inicial/pagado/extra.
- Pruebas nuevas de prepago, liquidación, migraciones y concurrencia; adaptación de pruebas existentes solo donde cambia el contrato aprobado.
- Documentación, prompts_ia.md y guía EC2 al finalizar; scripts/ui_server.py para QA temporal aislada.

### Tarea 1: Persistencia y compatibilidad de documentos anteriores

**Interfaces:** `Loan.billing_mode`, valores LEGACY_POSTPAID/PREPAID; `RentalRequest.approved_at`, `approved_by`, `approved_site`, `approved_amount`; `RentalRequestItem.approved_daily_rate`; `AssetHold(request, asset único)`; `Charge.kind`, `rental_request`, `loan` opcional FK, `voided_at`, propiedades contractor/contractor_id según origen. Charge expone `loan.charges` en lugar de asumir one-to-one.

- [ ] Escribir `tests/test_prepaid_migrations.py`: migrar desde rentals0002/payments0001 con préstamo abierto/cerrado, cargo pagado y PaymentAttempt; verificar IDs, contraseñas, montos y estados tras migrar, modo legacy, solicitud pendiente conservada y creación posterior PREPAID. Probar unicidad de retención y origen/tipo/cargo duplicado inválidos.
- [ ] Ejecutar `manage.py test tests.test_prepaid_migrations --noinput`, observar el fallo de campos/tablas ausentes y registrar RED.
- [ ] Añadir campos/tablas/restricciones y migraciones incrementales: campo de modo primero con default legacy para filas existentes, después default prepaid para filas nuevas. El cargo existente queda LEGACY. Cambiar la relación de cargo a FK sin borrar filas. Validar exclusión de orígenes y un INITIAL por solicitud / EXTRA por préstamo / LEGACY por préstamo. Inicializar campos nuevos de forma compatible con datos viejos; ninguna autorización bancaria ficticia.
- [ ] Adaptar los consumidores de lectura que impiden ejecutar las migraciones/pruebas, manteniendo acceso a documentos antiguos. Actualizar los destinos latest de las pruebas de migración anteriores y asegurar restauración de su esquema incluso ante fallo.
- [ ] Ejecutar pruebas nuevas y `makemigrations --check --dry-run`; leer salida y guardar commit local verificado.

### Tarea 2: Aprobar, retener y cancelar sin carreras

**Interfaces:** `approval_quote(req, actor) -> str`; `approve_request(*, request_id, site_id, quote, actor) -> RentalRequest`; `create_operator_request(*, contractor_id, asset_ids, site_name, site_address, responsible, starts_at, ends_at, notes, submit_key, actor) -> RentalRequest`. Las acciones existentes cancel_request/reject_request admiten PENDIENTE y APROBADA cancelable, nunca PAGADA. Contrato de retención consultable por `AssetHold.objects.filter(asset_id=...)`.

- [ ] Escribir `tests/test_prepaid_approval.py`: aprobación fija tarifa $6.000 × dos días = $12.000, crea INITIAL y retención, no Loan/firma; reserva ajena rechazada; cotización antigua o manipulada rechazada; intentos activos/UNKNOWN o pago confirmado impiden cancelar/rechazar; cancelación válida anula INITIAL y libera stock; cliente no puede aprobar ni crear solicitud por otra identidad.
- [ ] Ejecutar las pruebas y observar RED antes de implementar servicios.
- [ ] Implementar aprobación atómica con orden Contractor → Request → Charge existente si corresponde → Assets ordenados; revalidar disponibilidad/mantenimiento/fechas y bloqueos. Guardar tarifa y fechas aprobadas inmutables y el cargo INITIAL de monto positivo. Aprobación repetida devuelve el mismo resultado sin duplicarlo; no se permite cambiar importe mientras haya aprobación vigente.
- [ ] Coordinar cancelación/rechazo con el mismo bloqueo de solicitud/cargo que start_payment. Anular cargos no pagados sin intentos activos; no borrar documentos. Impedir start_payment de un cargo anulado. Registrar eventos de retención/liberación sin introducir un quinto estado físico de activo.
- [ ] Hacer que catálogo, traslados, bajas, mantenimiento y edición de ubicación/categoría respeten retenciones; las tarifas futuras pueden cambiar sin modificar el contrato aprobado. La desactivación de maestros que afecte entrega debe mostrarse como incidencia y bloquear entrega, nunca liberar un pago.
- [ ] Ejecutar las pruebas y las de inventario/mantenimiento afectadas; guardar commit local verificado.

### Tarea 3: Pago inicial y entrega exclusivamente pagada

**Interfaces:** `start_payment(*, charge_id, actor)`, `_apply(attempt_id, data)` conservan firma; titularidad por Charge.contractor_id. `fulfill_request(*, request_id, signature, responsible, actor, ...) -> Loan` exige estado PAGADA/cargo INITIAL pagado/retenciones y datos aprobados. `issue_loan(..., request_id)` exige solicitud pagada en todo nuevo uso y no admite un parámetro público para forzar legacy o saltar pago.

- [ ] Escribir `tests/test_prepaid_payments.py`: cliente titular paga INITIAL sin Loan; retorno verificado marca pagada una vez; monto/orden/sesión incoherentes y timeout no permiten entregar; INITIALIZED se puede continuar sin otra creación; cargo anulado y cliente ajeno no pueden pagar. Escribir `tests/test_prepaid_delivery.py`: APROBADA sin pago falla sin efectos, PAGADA entrega con tarifa fija aunque cambie catálogo, consume retenciones y enlaza INITIAL, doble entrega devuelve mismo préstamo; fechas distintas o mantenimiento/bloqueo sobrevenido fallan sin consumir pago.
- [ ] Ejecutar pruebas nuevas y observar RED. Ajustar solo los contratos de pruebas previas que ahora esperan entrega sin pago.
- [ ] Implementar start_payment y _apply con orden compatible Contractor → Request → Charge → Attempt cuando haya solicitud, derivando IDs sin bloqueo antes de abrir la transacción y validando relaciones dentro. Todas las llamadas de red quedan fuera del bloqueo. Pagos legacy/EXTRA mantienen su comportamiento y titularidad. Un pago confirmado siempre conserva el comprobante aunque la entrega posterior encuentre una incidencia.
- [ ] Centralizar entrega pagada en servicios compartidos. Bloquear intento por parámetros antiguos tanto en API como en web, sin crear filas parciales. No añadir atajos por DEBUG, actor administrador ni argumentos legacy al servicio productivo. Emitir la firma solo al entregar, no al aprobar/pagar.
- [ ] Adaptar fixtures para distinguir explícitamente datos históricos de flujos nuevos; no desactivar validaciones en tests ni convertir pruebas de permisos/estado en fábricas sin reglas. Mantener pruebas independientes de pago, firma, bloqueo y disponibilidad.
- [ ] Ejecutar pruebas nuevas, solicitudes, pagos y préstamos; guardar commit local verificado.

### Tarea 4: Liquidación de retrasos y concurrencia

**Interfaces:** `payments.billing.close_charge(loan) -> Charge | None`, reexportado desde payments.services si lo requieren consumidores existentes. Para legacy conserva cargo completo por tiempo real; para PREPAID produce exclusivamente EXTRA o None si saldo cero. Resumen `billing_summary(loan) -> {initial, extra, paid, outstanding, total}`.

- [ ] Escribir `tests/test_prepaid_billing.py`: $12.000 inicial y devolución a tiempo/anticipada → ningún EXTRA; diez horas tarde a $6.000 → EXTRA $6.000; dos equipos con fechas de devolución distintas cobran solo su retraso; llamada repetida conserva un único cargo; legacy conserva cálculo anterior y cargo ya pagado. Fechas UTC reales cruzan horario de verano sin redondeos de pared.
- [ ] Escribir `tests/test_prepaid_concurrency.py` con TransactionTestCase, conexiones independientes y barreras: dos aprobaciones compiten por un activo; cancelación contra start_payment; dos entregas de solicitud pagada; conciliación contra entrega y dos cierres de devolución. Esperar una retención/préstamo/cargo y ningún deadlock. No ejecutar runners Django simultáneos contra la misma base de test.
- [ ] Ejecutar pruebas y observar RED antes del cálculo/ajustes de bloqueo.
- [ ] Implementar días contratados fijos y extra por línea `ceil(max(0, returned_at - due_at)/24h) × approved_daily_rate` en UTC. Respetar devolución parcial y crear EXTRA solamente al cierre completo, con importe positivo e idempotencia. Los importes pagados nunca se editan para simular una liquidación.
- [ ] Ejecutar estas pruebas y las existentes de cargos/concurrencia, ajustando los asserts antiguos solo donde cambia el contrato comercial. Guardar commit local verificado.

### Tarea 5: Web/API/Admin y mensajes públicos coherentes

**Interfaces:** POST `/api/rental-requests/{id}/approve/`, POST `/solicitudes/{id}/aprobar/`; preparación por operador en `/solicitudes/nueva/`; GET/POST entrega existente acepta exclusivamente los valores aprobados. `/rentals/new/` conduce al nuevo formulario; POST antiguo devuelve error de validación con ruta útil. `/api/loans/` mantiene consulta y requiere request_id pagado para crear. El cliente paga desde el cargo INITIAL vinculado a su solicitud.

- [ ] Escribir `tests/test_prepaid_web.py`: selección pública, solicitud sin reserva inicial, aprobación visible para personal, cliente ve condiciones y botón pagar; sin pago no aparece entrega ejecutable, POST forzado falla; con pago aparece entrega; estados y cargos de otro cliente permanecen 404/403. Panel muestra retenciones y medio de creación por operador. Regresión de /api/loans/ con payload antiguo sin pago.
- [ ] Ejecutar pruebas y observar RED. Implementar formularios/serializadores/acciones/URLs y actualizar templates de requests, payments y rentals. No aceptar montos, tarifas, paid_at, actor, tipo legacy ni contratista ajeno desde el cliente. Mostrar importe inicial, fechas, tarifa acordada, estado bancario, saldo extra y deuda pendiente claramente.
- [ ] Sustituir textos que prometen cobro únicamente al devolver en portada, selección, fichas y guía de uso. Mostrar antes de pagar las condiciones aprobadas de devolución anticipada y cancelación. El catálogo reconoce retención además del estado físico.
- [ ] Adaptar Admin/serializadores/listados, eliminar todos los supuestos obligatorios charge.loan y loan.charge único; mantener documentos de pago y transaccionales de solo lectura. Ni operador ni Admin pueden marcar un cargo como pagado editando campos.
- [ ] Ejecutar pruebas web/API/Admin, pagos, 404 y registro; guardar commit local verificado.

### Tarea 6: Recorrido final, revisión, documentación y entrega EC2

- [ ] Ejecutar suite completa sobre PostgreSQL separado; `check`, `makemigrations --check --dry-run`, `migrate --check`, `collectstatic`, `pip check`, `ruff format --check` y `git diff --check`. Si hay un fallo, aplicar systematic-debugging y corregir con prueba roja antes de afirmar éxito.
- [ ] En servidor QA temporal, probar visitante → selección → registro → solicitud → aprobación por operador → pago inicial → entrega firmada → devolución a tiempo sin nuevo cargo; comprobar un saldo de retraso y préstamo histórico por pruebas. Si el pago se simula en QA, identificarlo explícitamente: no atribuir un pago real al proveedor sin ejecutarlo. No usar la base de desarrollo ni EC2 para tests.
- [ ] Revisar escritorio/móvil, retenciones, errores conservando datos, condiciones antes de pagar, permisos y estados. Cerrar navegador/servidor y retirar base/credenciales/sesiones QA; no borrar datos reales.
- [ ] Ejecutar una única revisión independiente final de pagos, carreras y migraciones con contexto acotado; el trabajador no edita ni opera AWS. Detenerlo al recibir el informe. Hallazgos importantes: un pase de regresión RED→GREEN y suite completa, sin rondas redundantes.
- [ ] Actualizar README.md, docs/ARQUITECTURA.md, MODELO_RELACIONAL.md, DEFENSA.md, VERIFICACION.md y ACTUALIZAR_EC2.md: respaldo y parada de servicio/cron, migración incremental, preservación de legacy, nuevas rutas, comprobación de registros existentes y diagnóstico sin borrados. Actualizar prompts_ia.md al finalizar con las solicitudes reales y límites de la evidencia.
- [ ] Guardar commits locales revisados y entregar instrucciones para que el usuario publique GitHub y actualice EC2. No hacer push ni conexión SSH a la instancia.

## Revisión propia del plan

Persistencia histórica y restricciones: tarea1. Retenciones/cancelación y escrituras laterales: tarea2. Validación bancaria y todas las rutas de entrega: tarea3. Liquidación/idempotencia/UTC/carreras: tarea4. Acciones útiles, titularidad y textos: tarea5. QA, comprobaciones, revisión independiente, documentación y prompts: tarea6. Los cinco Review Focus tienen pruebas asignadas. Las funciones nuevas tienen productor/consumidor y los nombres de estado, modo y tipo coinciden con la especificación. No se repite un checkout ni se altera la selección de método del usuario.
