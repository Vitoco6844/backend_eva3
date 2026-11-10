# Pago previo a la entrega de herramientas

## Estado y propósito
Diseño preparado para revisión del usuario. El usuario aprobó el flujo conceptual: solicitud → confirmación de bodega → pago Webpay confirmado → entrega firmada → saldo por tiempo adicional. Esta especificación concreta las decisiones necesarias para cambiar la aplicación existente, que ya está desplegada por el usuario en EC2. No se ha modificado código productivo ni se ha operado AWS.

Es un cambio arquitectónico dentro del monolito existente: Charge actualmente exige un Loan ya entregado y solo se crea al cerrar. Hay que admitir cargos antes del préstamo, retener equipos y proteger todos los caminos de entrega. No es un cambio de ubicación de un botón.

## Alcance y reglas

1. El visitante sigue viendo portada, catálogo y selección sin sesión. La cuenta se exige al enviar la solicitud.
2. La solicitud inicial no reserva ni cobra. El personal revisa herramientas, mantenimiento, bloqueo del contratista, fechas y tarifas y aprueba una cotización definitiva.
3. Al aprobar se retienen exclusivamente los equipos de esa solicitud. Se muestra el importe y las condiciones al cliente antes de ir a Webpay. No se crea un préstamo, firma de entrega ni horas de uso.
4. El cliente paga el importe del período aprobado. Solo una respuesta bancaria verificada en servidor habilita la entrega: autorización, orden, sesión y monto deben coincidir. Redirección o mensaje de éxito del navegador no bastan.
5. Bodega entrega con firma únicamente después del pago confirmado, dentro de las fechas aprobadas y con los equipos retenidos. Vuelve a comprobar mantenimiento, morosidad y estado; el pago no permite entregar una herramienta insegura o a un contratista bloqueado.
6. La entrega conserva tarifas, fechas e importe aprobados. Si un cambio operativo hace imposible entregar, se muestra una incidencia y se conserva el pago y la retención para resolución del personal. Nunca se cobra otra vez ni se simula una devolución de dinero.
7. En la devolución completa se calcula únicamente el saldo adicional. Un préstamo pagado no vuelve a generar el cargo completo. Las devoluciones parciales, firmas, horas y mantenimiento conservan su comportamiento.
8. Todos los nuevos préstamos deben pasar por este flujo, también los iniciados por personal desde el panel. Los endpoints y formularios antiguos de entrega directa no pueden saltarse el pago. Se actualizarán para dirigir a la solicitud/aprobación correspondiente y rechazar una entrega sin su solicitud pagada.

## Política propuesta sobre fechas y cancelación

Estas son decisiones de diseño para este alcance académico y no afirmaciones sobre obligaciones legales o prácticas comerciales universales. Deben mostrarse antes del pago.

- El período aprobado es el de la solicitud; se cobra por tramos de 24 horas, redondeados hacia arriba y con mínimo un día. El cálculo utiliza instantes UTC para evitar errores por cambio horario.
- La aprobación fija inicio, devolución prevista y tarifas por equipo. Después de pagar no pueden editarse esos valores. La firma de entrega acredita lo ya aceptado, sin cambiar el precio.
- El importe inicial cubre todo el período contratado. Una devolución anticipada no produce un reembolso automático ni un cargo negativo.
- Por cada herramienta devuelta después del vencimiento aprobado se añade su tarifa diaria por cada tramo de 24 horas de retraso, redondeado hacia arriba. Fórmula: extra de línea = tarifa aceptada × ceil(max(0, devolución real − vencimiento aprobado) / 24 h). Una línea devuelta a tiempo no genera extras, aunque otra siga pendiente.
- Ejemplo: dos días de una herramienta de $6.000 cuestan $12.000 antes de entregar. Si vuelve dentro del plazo, saldo $0; si vuelve diez horas tarde, saldo $6.000. El saldo se calcula una sola vez al cerrar todas las líneas y se paga mediante un cargo separado.
- Antes de iniciar un pago se puede cancelar y liberar la retención. Si hay un intento bancario activo o incierto, se debe conciliar primero; no se libera stock ni se permite otro pago a ciegas.
- Después de pagar no habrá cancelación unilateral ni reembolso automático en esta ampliación. El cliente ve que debe contactar a BuildCorp; el personal ve la incidencia y el registro del pago. No se ofrece un botón que aparente reintegrar dinero. Una devolución bancaria automatizada queda fuera de este alcance.
- Para evitar liberar un equipo mientras Webpay puede confirmar un pago, la retención no expira automáticamente. El personal podrá cerrar una aprobación sin pago solo si no tiene un intento activo/incierto ni pago confirmado. Se mostrará claramente la retención en el panel. No se promete planificación de stock futuro: se retienen unidades físicas desde la aprobación.

## Estados y persistencia

RentalRequest mantiene PENDIENTE, ENTREGADA, RECHAZADA y CANCELADA, y añade APROBADA (espera de pago) y PAGADA (lista para entrega), con fecha/actor de aprobación, obra operativa y cotización inmutable. Una incidencia de entrega se muestra sin convertir el pago en un estado bancario inventado. Un pago repetido conserva idempotencia y no duplica la transición.

Las líneas de solicitud guardan separadamente la tarifa inicialmente estimada y la aprobada. El importe aprobado queda registrado; no se recalcula desde el catálogo al pagar. El personal puede crear una solicitud para un contratista existente, sin suplantar su sesión: el actor queda registrado y el pago sigue siendo exclusivo del titular autenticado.

Se añade una retención activa con relación única por Asset y relación a RentalRequest. Al aprobar se bloquean contratista → solicitud → activos en orden estable y se crean las retenciones dentro de una transacción. Una competencia por el mismo activo produce una sola aprobación válida. Al entregar se consumen las retenciones en la misma transacción que crea Loan/LoanItem y las firmas; cancelación/rechazo válido las libera con historial. Se respeta la trazabilidad de los cuatro estados del enunciado: la retención es separada del estado físico y el catálogo la presenta como no disponible.

Charge pasa de un único cargo obligatorio por Loan a varios cargos por préstamo, con tipo LEGACY (histórico), INITIAL (período contratado) y EXTRA (saldo al devolver). El cargo inicial puede existir ligado a una solicitud antes del Loan; se asocia al Loan al entregar. Las restricciones exigen origen válido, importes positivos y un solo cargo inicial por solicitud y un solo saldo por préstamo. Un saldo cero se representa en el resumen de liquidación, no mediante una orden Webpay de monto cero. Se conserva PaymentAttempt y su historial.

Se actualizan todas las consultas y representaciones que hoy asumen charge.loan obligatorio o loan.charge único: web, API, permisos, conciliación, continuaciones, retorno bancario, Admin, serializadores y plantillas. La titularidad debe obtenerse del origen correcto y no de parámetros del cliente. El resumen del préstamo mostrará importe inicial, pagado y saldo pendiente sin confundir deuda con costo total.

## Seguridad, concurrencia y pagos

Se reutiliza Webpay de integración exclusivamente. No se agregan credenciales reales, captura de tarjetas ni un segundo proveedor. La creación/consulta bancaria sigue fuera de transacciones largas. El estado aplicado se verifica y guarda transaccionalmente; repetición de retorno o conciliación no genera otro préstamo/cargo ni autoriza dos entregas.

La aprobación firma o versiona los datos relevantes para detectar formularios desactualizados. El cliente no puede enviar tarifas, monto, actor, contratista, estado pagado o vencimiento diferente. No se puede editar una cotización con un intento activo o un pago confirmado. Las retenciones se consultan también en catálogo y en traslado, baja, mantenimiento y entrega para que ninguna ruta operativa pueda asignar el mismo equipo a otro préstamo.

Para no introducir interbloqueos, la implementación documentará y conservará un orden estable de bloqueo. La confirmación bancaria no debe bloquear Charge y después esperar un Contractor ya retenido por una entrega que esté esperando ese mismo Charge. Se probará concurrencia con conexiones PostgreSQL independientes.

## Compatibilidad con la EC2 existente

Se conserva el historial y se añade un modo de cobro explícito a Loan. La migración marca los préstamos existentes como LEGACY_POSTPAID; los nuevos serán PREPAID. Los préstamos antiguos abiertos finalizan con el cálculo y cargo completos anteriores, sin exigir un pago retroactivo. Los cargos e intentos existentes mantienen IDs, montos, estados y referencias; los pagados no se reabren.

Las solicitudes existentes pendientes siguen siendo solicitudes pendientes, pero para una nueva entrega se aprueban y pagan bajo la nueva regla. Las ya entregadas conservan su préstamo histórico. No se crean pagos ficticios para adaptar datos.

Las migraciones son incrementales y conservan las anteriores. Primero se añaden campos/tablas y relaciones compatibles, luego se identifican datos anteriores y se activan las reglas nuevas. No se eliminan tablas, usuarios, préstamos o fotografías. Las operaciones se realizan con respaldo y aplicación detenida en EC2; el usuario ejecutará la actualización y no el asistente. No se promete actualización sin interrupción ni compatibilidad de todas las rutas antiguas después de activar la nueva regla comercial.

Antes de actualizar se detiene BuildCorp y su tarea periódica, se respalda PostgreSQL/.env/media y se anotan versiones. Se descarga el código publicado, instalan dependencias, aplican migraciones, ejecutan check/migrate --check/collectstatic y se reinicia/verifica. No se recrea la base, no se vuelve a crear el administrador y no se ejecutan pruebas contra datos activos. Se añadirá una comprobación de préstamos/cargos existentes a la guía de actualización.

## Verificación requerida

- Regresión de los datos históricos: préstamo abierto/cerrado, cargos pagados/pendientes, intentos y contraseñas conservados tras migrar; un préstamo antiguo no queda bloqueado por la nueva regla.
- Solicitud → aprobación/retención → cargo inicial → pago confirmado → entrega firmada. Intentar entregar antes del pago falla en web, API y servicio, sin cambios parciales.
- Rechazo de montos o identidades falsificados; cliente ajeno sin acceso; personal sin capacidad de marcar pagos manualmente.
- Stock competido: solo una aprobación por activo, sin doble entrega ni retiro/traslado incompatible. Cancelación sin pago libera; intento incierto y pago confirmado no se liberan.
- Pago repetido, timeout, rechazo, expiración bancaria, retorno sin sesión y consulta de un pago inicializado conservan la idempotencia y la posibilidad de continuar el intento válido.
- Cambio de tarifa del catálogo posterior a aprobación no modifica el importe contratado ni provoca un segundo cobro.
- Devolución a tiempo: saldo cero y ningún nuevo pago. Retraso: únicamente extra. Devolución anticipada: conserva el período contratado. Devoluciones parciales: cada equipo determina su propio retraso; liquidación repetida no duplica cargos.
- Fechas con cambio horario, aprobaciones/pagos concurrentes y doble confirmación de entrega.
- Recorrido de navegador con PostgreSQL temporal y comprobación responsive de los nuevos estados, condiciones y acciones; regresión completa de mantenimiento, firmas, morosidad y pagos.
- Actualizar README, arquitectura, modelo relacional, defensa, VERIFICACION, prompts_ia y guía de EC2 con resultados reales.

## Revisión propia

El diseño conserva acceso público y añade pago previo real validado en servidor, sin pagos simulados manualmente. Se distingue solicitud sin reserva de aprobación con retención y pago inicial de saldo extra. Se explicita el tratamiento de cancelaciones y devoluciones anticipadas, y se protege el stock entre aprobación y entrega. El historial existente usa reglas anteriores para no cobrar retroactivamente. AWS/GitHub siguen bajo operación del usuario. No se requiere generar nuevas imágenes ni añadir un framework de frontend.

Tras la aprobación de esta especificación se preparará el plan de implementación para ejecución en este mismo chat, sin abrir trabajadores adicionales para implementar.
