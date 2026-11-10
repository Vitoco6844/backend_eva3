# Guion de defensa BuildCorp

## Antes de presentar
Inicia PostgreSQL y Django con scripts/iniciar.ps1. Utiliza tu administrador existente (créalo solo si aún no existe), crea un bodeguero desde Admin y registra un cliente desde la tienda. El catálogo seed_demo no crea cuentas. Comprueba que PUBLIC_BASE_URL corresponde al host/puerto que usarás. Para presentar en AWS sigue DESPLIEGUE_EC2.md y prueba con su dirección pública.

## Demostración de la tienda pública

Abre `/` en una ventana sin sesión: recorre catálogo, filtro y ficha y agrega una herramienta a la selección. Muestra que no pide cuenta para explorar. Regístrate al solicitar, indica obra y fechas y presenta la estimación. En la cuenta del cliente aparece la solicitud pendiente, sin reserva ni cobro.

Entra como bodeguero o administrador, abre `/solicitudes/`, comprueba disponibilidad y aprueba la obra y tarifas. Muestra la retención y que aún no permite entregar. Vuelve como cliente, lee las condiciones y paga el período contratado con Webpay de integración. Con el pago confirmado, bodega registra la entrega con firma. Devuelve dentro de plazo y muestra que no hay segundo cargo; con retraso se genera únicamente el saldo adicional por cada herramienta. Muestra también una URL inexistente y el botón «Volver al inicio».

Las doce imágenes son referencias generadas con IA y se incluyen en el repositorio. Pueden reemplazarse por una fotografía del activo; no representan una marca o modelo certificado.

## Recorrido sugerido
1. Explica el problema: pérdida de herramientas, poca trazabilidad y fallas imprevistas.
2. Muestra Django Admin: modelos, búsquedas, filtros, usuario con rol y separación entre is_staff y rol de negocio. Los históricos son de solo lectura.
3. Crea una categoría o una obra y edítala; elimina un registro sin relaciones. Explica por qué un registro con historial no se borra.
4. En inventario abre una herramienta, su bodega, tarifa y hoja de vida. Registra un traslado disponible y muestra origen, destino, usuario y fecha.
5. Prepara y aprueba una solicitud de dos herramientas para un contratista activo; entra como titular y paga el período aprobado. Regresa a bodega, entrega con firma y muestra que ambas quedan En Uso.
6. Devuelve solo una con horas y daño. El préstamo sigue abierto y no se genera cargo final. La herramienta dañada requiere mantenimiento.
7. Devuelve la segunda, firma y muestra la liquidación: sin retraso no hay otro pago; con retraso solo se añade ese tiempo. Las horas no se vuelven a sumar si se repite la devolución.
8. Inicia y finaliza el mantenimiento con trabajo realizado y próximos límites por fecha/horas. Muestra que una revisión vencida bloquea nuevos préstamos.
9. Para demostrar morosidad sin alterar documentos firmados, crea un préstamo de prueba con un vencimiento cercano (por ejemplo, el minuto siguiente) y espera a que venza. La vista Alertas lo muestra y otra entrega al contratista se rechaza. Ejecutar revisar_alertas registra la alerta, pero el bloqueo ya funciona sin él. Devuelve el activo y comprueba regularización.
10. Entra como contratista y muestra solo sus préstamos y cargos. Realiza un pago en Webpay **de integración**, con los datos ficticios del README; muestra el comprobante confirmado en BuildCorp. Otro contratista no puede consultar esos documentos.

## Preguntas que conviene dominar
- ¿Qué protege PostgreSQL además del formulario? Restricciones relacionales e índices únicos parciales; transacciones y bloqueos evitan dos entregas simultáneas.
- ¿Por qué guardar tarifa en LoanItem? Conserva la tarifa aprobada y pagada; cambiar el catálogo no altera el contrato.
- ¿Cómo se cobra una devolución parcial? Cada línea determina su retraso respecto al vencimiento; el saldo extra se genera al cerrar todas. En préstamos anteriores a la actualización se mantiene el cálculo legacy.
- ¿Qué sucede si no corre cron? La entrega consulta morosidad y vencimiento preventivo directamente; no depende del cron.
- ¿Pagar desbloquea un contratista moroso? No: debe devolver herramientas vencidas. El bloqueo manual es independiente.
- ¿La firma es avanzada? No: trazo PNG privado, hash, responsable, usuario registrador y momento, como evidencia académica.
- ¿Cómo se confirma Webpay? El servidor consulta/confirmar con Transbank y valida monto, orden, sesión y respuesta. No acepta como prueba el mensaje del navegador.
- ¿Qué sucede con un timeout de pago? Se conserva Por conciliar, evitando nuevos intentos hasta conocer el resultado.
- ¿Se cobró dinero real? No: solo integración, endpoint fijado y tarjetas ficticias oficiales.
- ¿Qué falta para la rúbrica de despliegue? Actualizar y comprobar la nueva versión en tu EC2 siguiendo ACTUALIZAR_EC2.md y demostrarla por IP/DNS público. Esta ampliación se verificó localmente; el usuario opera su instancia.

## Mapa de evaluación
| Criterio | Dónde mostrarlo |
|---|---|
| PostgreSQL y migraciones | settings.py, migrations/, migrate --check y registros persistentes |
| Django Admin | /admin/ con todos los modelos registrados |
| CRUD y reglas | datos maestros y servicios de entrega/devolución/mantenimiento/morosidad |
| Seguridad y apoyo IA | roles, sesiones, CSRF, permisos por titular y prompts_ia.md |
| EC2 y defensa | aplicación pública después de ejecutar DESPLIEGUE_EC2.md |

Lee los servicios de dominio antes de la defensa y ejecuta los flujos tú mismo. El reemplazo temporal de herramientas durante revisiones está diferido y no se presenta como implementado.

Preguntas de la ampliación: ¿se necesita cuenta para mirar? No; solo para enviar una solicitud y consultar documentos privados. ¿La solicitud garantiza stock? Inicialmente no; al aprobar bodega se retienen unidades y al entregar se revalidan seguridad y bloqueos. ¿Puede registrarse como administrador? No; el servidor fija el rol de cliente. ¿Cuándo se paga? Tras aprobar bodega y antes de entregar. Al devolver solo se paga un posible saldo por retraso. ¿Qué pasa con una devolución anticipada? Conserva el período contratado y no hay reembolso automático.
