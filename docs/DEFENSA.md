# Guion de defensa BuildCorp

## Antes de presentar
Inicia PostgreSQL y Django con scripts/iniciar.ps1. Crea tu administrador y dos cuentas desde Admin: un bodeguero y un contratista asociado a una entidad Contractor. El catálogo seed_demo no crea cuentas. Comprueba que PUBLIC_BASE_URL corresponde al host/puerto que usarás. Para presentar en AWS sigue DESPLIEGUE_EC2.md y prueba con su dirección pública.

## Recorrido sugerido
1. Explica el problema: pérdida de herramientas, poca trazabilidad y fallas imprevistas.
2. Muestra Django Admin: modelos, búsquedas, filtros, usuario con rol y separación entre is_staff y rol de negocio. Los históricos son de solo lectura.
3. Crea una categoría o una obra y edítala; elimina un registro sin relaciones. Explica por qué un registro con historial no se borra.
4. En inventario abre una herramienta, su bodega, tarifa y hoja de vida. Registra un traslado disponible y muestra origen, destino, usuario y fecha.
5. Entrega dos herramientas a un contratista activo, captura firma del responsable y abre la constancia. Las dos quedan En Uso.
6. Devuelve solo una con horas y daño. El préstamo sigue abierto y no se genera cargo final. La herramienta dañada requiere mantenimiento.
7. Devuelve la segunda, firma y muestra el cargo calculado con tarifas históricas. Las horas no se vuelven a sumar si se repite la devolución.
8. Inicia y finaliza el mantenimiento con trabajo realizado y próximos límites por fecha/horas. Muestra que una revisión vencida bloquea nuevos préstamos.
9. Para demostrar morosidad sin alterar documentos firmados, crea un préstamo de prueba con un vencimiento cercano (por ejemplo, el minuto siguiente) y espera a que venza. La vista Alertas lo muestra y otra entrega al contratista se rechaza. Ejecutar revisar_alertas registra la alerta, pero el bloqueo ya funciona sin él. Devuelve el activo y comprueba regularización.
10. Entra como contratista y muestra solo sus préstamos y cargos. Realiza un pago en Webpay **de integración**, con los datos ficticios del README; muestra el comprobante confirmado en BuildCorp. Otro contratista no puede consultar esos documentos.

## Preguntas que conviene dominar
- ¿Qué protege PostgreSQL además del formulario? Restricciones relacionales e índices únicos parciales; transacciones y bloqueos evitan dos entregas simultáneas.
- ¿Por qué guardar tarifa en LoanItem? Es la tarifa pactada al entregar; cambiar el catálogo no altera el cobro histórico.
- ¿Cómo se cobra una devolución parcial? Cada línea calcula días hasta su devolución; el cargo final aparece al cerrar todas las líneas.
- ¿Qué sucede si no corre cron? La entrega consulta morosidad y vencimiento preventivo directamente; no depende del cron.
- ¿Pagar desbloquea un contratista moroso? No: debe devolver herramientas vencidas. El bloqueo manual es independiente.
- ¿La firma es avanzada? No: trazo PNG privado, hash, responsable, usuario registrador y momento, como evidencia académica.
- ¿Cómo se confirma Webpay? El servidor consulta/confirmar con Transbank y valida monto, orden, sesión y respuesta. No acepta como prueba el mensaje del navegador.
- ¿Qué sucede con un timeout de pago? Se conserva Por conciliar, evitando nuevos intentos hasta conocer el resultado.
- ¿Se cobró dinero real? No: solo integración, endpoint fijado y tarjetas ficticias oficiales.
- ¿Qué falta para la rúbrica de despliegue? Ejecutar la guía en tu AWS Academy y demostrar la aplicación por IP/DNS público; no se ha desplegado desde este trabajo.

## Mapa de evaluación
| Criterio | Dónde mostrarlo |
|---|---|
| PostgreSQL y migraciones | settings.py, migrations/, migrate --check y registros persistentes |
| Django Admin | /admin/ con todos los modelos registrados |
| CRUD y reglas | datos maestros y servicios de entrega/devolución/mantenimiento/morosidad |
| Seguridad y apoyo IA | roles, sesiones, CSRF, permisos por titular y prompts_ia.md |
| EC2 y defensa | aplicación pública después de ejecutar DESPLIEGUE_EC2.md |

Lee los servicios de dominio antes de la defensa y ejecuta los flujos tú mismo. El reemplazo temporal de herramientas durante revisiones está diferido y no se presenta como implementado.
