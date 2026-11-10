# BuildCorp EVA3: especificación de diseño

Fecha: 2026-11-09. Estado: especificación aprobada por el usuario en el chat; reemplazos durante mantenimiento reservados como mejora posterior.

## Objetivo y alcance
Aplicación académica de alquiler y control de herramientas para BuildCorp. Cumplir los cuatro requisitos funcionales de instrucciones.md, Django Admin, CRUD, seguridad y PostgreSQL. Añadir Webpay Plus exclusivamente en integración para demostrar pagos de alquiler sin dinero real. Entregar instrucciones para desplegar en una única EC2 con PostgreSQL y servidor Django; no ejecutar acciones en AWS, DNS ni publicar en GitHub.

## Base y ubicación
Todo artefacto nuevo se guarda en C:/Users/vimat/Desktop/Clases/2do sm/backend_eva3. Origen de componentes reutilizables: C:/Users/vimat/Desktop/Clases/2do sm/backend/backend_eva2. No modificar EVA2 ni copiar bases, claves, usuarios, repositorio Git, entornos virtuales o módulos de conciertos. Reutilizar selectivamente configuración por variables de entorno, utilidades de presentación, patrones transaccionales y scripts locales adaptados; documentar su procedencia. Las migraciones serán propias de BuildCorp.

## Arquitectura
Monolito Django con DRF, PostgreSQL obligatorio y templates HTML/CSS/JavaScript responsivos. Autenticación por sesiones de Django y CSRF, compartida entre interfaz y API. Separar configuración (buildcorp), cuentas y permisos (accounts), inventario (inventory), préstamos y morosidad (rentals), mantenimiento (maintenance), pagos (payments) e interfaz (web). Reglas de negocio en servicios compartidos por API, interfaz y acciones administrativas. Usar Django Admin personalizado para todos los modelos con búsquedas, filtros y campos calculados de solo lectura.

## Cuentas y autorización
Roles administrador, bodeguero y contratista. El administrador gestiona cuentas, contratistas y configuración; bodegueros operan inventario, entregas, devoluciones y mantenimiento; contratistas consultan exclusivamente sus préstamos, comprobantes y pagos. Cuentas creadas por administrador; no hay autoasignación pública de roles. Los permisos se verifican en servidor, incluyendo filtros por propietario en listados y detalles. El acceso a Admin requiere permisos de Django; ser bodeguero no otorga acceso administrativo irrestricto.

## Modelo de dominio
- Contratista: identificación única, razón social, contacto, activo y bloqueo manual separado de morosidad calculada.
- Obra y bodega: cada bodega pertenece a una obra; herramientas identificadas individualmente por código y número de serie cuando corresponda.
- Activo: categoría, descripción, bodega actual, estado (Disponible, En Uso, Mantenimiento, Dado de Baja), tarifa diaria en pesos enteros y horas acumuladas.
- Movimiento e historial: activo, origen/destino, actor, instante y motivo. El traslado requiere activo disponible; no se permite cambiar ubicación directamente omitiendo el historial.
- Préstamo: contratista, obra, responsable, entrega, vencimiento y líneas de activos con tarifa aceptada conservada. Cada línea admite devolución individual, horas de uso, estado y observaciones.
- Firma de entrega y de devolución: trazo capturado en pantalla, nombre del firmante, usuario registrador, instante y vínculo al documento. Evidencia académica de aceptación, sin presentarla como firma electrónica avanzada. Su consulta requiere autorización. Validar formato y tamaño; impedir edición posterior de documentos firmados.
- Plan y registro de mantenimiento: activo, fecha límite y/o umbral de horas; finalizar mantenimiento registra trabajo, responsable, fecha, horas y próximos límites.
- Cargo de alquiler: vinculado a préstamo, monto calculado en servidor y estado de pago. El cierre total del préstamo fija el monto final, sumando tarifa diaria por activo por días de uso, con mínimo de un día y redondeo hacia arriba por períodos de 24 horas. El alcance académico no agrega impuestos, multas ni cobros por daños.
- Intento de pago: cargo, orden única, token privado, monto, estado, código de respuesta y autorización. No almacenar datos de tarjeta.
- Alerta: préstamo vencido, fecha de detección y resolución; evitar duplicados abiertos para el mismo préstamo.

## Reglas y transiciones
Entregar solo activos disponibles, sin mantenimiento vencido, a contratistas activos sin bloqueo manual ni préstamos vencidos abiertos. Bloquear filas en transacciones y establecer restricciones de base para impedir préstamos simultáneos del mismo activo. La entrega cambia a En Uso y genera historial y firma dentro de una única operación consistente.

Devolver cada activo una sola vez, exigiendo horas no negativas y firma. Acumular horas una sola vez; enviar a Mantenimiento si tiene desperfectos o alcanzó un límite, en caso contrario a Disponible. Al devolver el último activo, cerrar el préstamo y fijar el cargo. Conservar préstamos y movimientos históricos; usar bajas/desactivaciones donde borrar rompería trazabilidad.

La morosidad corresponde a vencimiento anterior al instante actual con activos pendientes. El rechazo de un nuevo préstamo consulta esa condición directamente, aunque el proceso de alertas no haya corrido. Un comando idempotente revisa vencimientos y mantenimientos para ejecución periódica local o con cron en EC2. Resolver alerta al regularizar devolución; el pago por sí solo no regulariza activos pendientes. El bloqueo manual permanece independiente.

Un plan exige al menos un límite (fecha u horas). No permitir prestar equipo vencido aunque su estado material aún figure Disponible. Iniciar y finalizar mantenimiento mediante servicios; no permitir estados arbitrarios en Admin o API. Las horas acumuladas no disminuyen.

## Webpay exclusivamente académico
Integrar Webpay Plus con el endpoint oficial de integración y credenciales públicas de prueba documentadas por Transbank. No ofrecer selección de producción; rechazar una configuración distinta a integración. Mostrar permanentemente en el flujo: «Ambiente de integración: pago de prueba, sin cobro real». Las tarjetas de prueba se documentan desde fuentes oficiales; no solicitar tarjetas reales.

Flujo: contratista autenticado inicia pago de cargo propio pendiente; servidor calcula monto y crea intento; redirección al formulario de Transbank; retorno se confirma contra Transbank desde servidor. Validar respuesta aprobada, monto, orden y vinculación del intento antes de registrar pago. El retorno no confía en campos de monto o estado enviados por navegador. Evitar cobros duplicados con un intento activo por cargo y conciliación de intentos de resultado desconocido antes de reintentar. Retornos repetidos no duplican efectos. Tratar rechazo, cancelación, expiración, token desconocido, timeout y fallo de red con estados claros. El retorno externo tendrá la excepción CSRF estrictamente necesaria y no dependerá de que el navegador conserve la sesión para confirmar; la visualización del comprobante sí requiere autorización. No exponer tokens ni claves en páginas, logs o URLs de comprobantes.

Fuentes oficiales consultadas el 2026-11-09:
- https://transbankdevelopers.com/ayuda : ambiente de integración de acceso libre y sin costo asociado.
- https://transbankdevelopers.com/documentacion/como_empezar : ambientes, credenciales y tarjetas de prueba; producción utiliza dinero real.
- https://transbankdevelopers.com/documentacion/webpay-plus : flujo de Webpay Plus y retornos.

## Interfaz y API
Pantallas: ingreso, tablero con indicadores, activos y hoja de vida, obras/bodegas/contratistas, préstamos y firmas, devoluciones, mantenimiento, alertas y cargos/comprobantes. Formularios con mensajes en español y navegación adaptada al rol. La API expone CRUD para entidades maestras y acciones específicas para transiciones; campos derivados e históricos no son editables genéricamente. Administración personalizada conserva las mismas restricciones.

## Validación y criterios de aceptación
Pruebas sobre PostgreSQL real: CRUD y permisos por rol y propietario; entregas simultáneas; devolución parcial y repetida; vencimientos y bloqueo sin tarea periódica; mantenimiento por horas y fecha; tarifas históricas y cálculo de cargo; rechazo de transiciones inválidas; firmas inválidas y acceso no autorizado; pagos aprobados, rechazados, cancelados, retorno repetido, respuestas inconsistentes y timeout con conciliación. Las pruebas automáticas de pago usan dobles del proveedor y se distinguen de cualquier prueba real contra integración. Verificar migraciones sin cambios pendientes, Django check, collectstatic y recorridos de navegador. Registrar los comandos y resultados realmente ejecutados, sin atribuirse comprobaciones de AWS.

## Entregables y defensa
Código, migraciones, requisitos reproducibles, .env.example sin secretos, datos ficticios sin contraseña compartida, scripts de instalación/inicio, README, documentación de arquitectura 4+1 y modelo relacional, guía de pruebas y demostración, guía de EC2/PostgreSQL/Gunicorn/Nginx y configuración posterior de DNS. prompts_ia.md registra apoyos reales con redacción profesional, sin inventar consultas ni ocultar alcance de asistencia. El despliegue público permanece pendiente de ejecución del usuario.

## Secuencia propuesta
1. Base ejecutable con PostgreSQL, usuarios y Admin.
2. Inventario y trazabilidad.
3. Préstamos, firmas, devoluciones y morosidad.
4. Mantenimiento y alertas programables.
5. Cargos e integración de pagos.
6. Verificación integral, documentación y preparación de defensa.

Antes de programar se revisará esta especificación y, después, el plan de implementación conforme al flujo de diseño aplicable.

