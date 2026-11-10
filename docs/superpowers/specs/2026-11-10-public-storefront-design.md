# BuildCorp: tienda pública y solicitudes de alquiler

Fecha: 2026-11-10. Estado: enfoque conversacional aprobado; especificación pendiente de revisión del usuario.

## Intención y alcance aprobado
El usuario espera una experiencia pública de BuildCorp, realizada con templates de Django en el mismo proyecto, donde cualquier visitante pueda consultar herramientas y crear una cuenta. Aceptó el flujo recomendado: el cliente solicita herramientas, el bodeguero confirma la entrega con firma y el cargo definitivo se calcula después de la devolución. La versión actual implementa el panel operativo, pero no esta experiencia pública.

Se incorporan inicio público, catálogo con imágenes, filtros y fichas, registro, selección de herramientas, solicitudes y área del cliente. Se conservan el panel operativo, los permisos, las firmas, el mantenimiento y los pagos Webpay exclusivamente de integración. No se ejecutarán cambios en AWS ni se publicará en GitHub: el usuario subirá el código y recibirá comandos para actualizar su instancia.

Esta especificación reemplaza la prohibición de registro público de la especificación inicial únicamente en lo relativo a cuentas de cliente. La asignación de privilegios de administrador/bodeguero continúa restringida a administración. Se preserva el método de ejecución elegido por el usuario: implementación en este chat; subagentes solamente si son estrictamente necesarios.

## Enfoque elegido y alternativas
Se amplía el monolito existente con una experiencia pública en templates, reutilizando sus servicios transaccionales para entrega y devolución. Un frontend separado introduciría otra aplicación y no corresponde a lo solicitado. Convertir la tienda en reserva y pago anticipado exigiría reglas nuevas de stock futuro, cancelación y facturación; el usuario eligió solicitud con confirmación operativa y cobro al devolver.

## Navegación y presentación
- `/`: portada pública de BuildCorp con presentación del alquiler, categorías, herramientas destacadas y acceso al catálogo, ingreso y registro.
- `/catalogo/`: catálogo público, paginado y con filtros por nombre, categoría y disponibilidad actual.
- `/catalogo/herramientas/<id>/`: fotografía referencial, nombre, categoría, descripción, tarifa diaria y disponibilidad actual; permite agregar una herramienta a la selección cuando se encuentra disponible.
- `/mi-solicitud/`: selección persistida en sesión y resumen con fechas y estimación; el envío requiere cuenta de cliente.
- `/cuenta/registro/`: alta pública. El ingreso conserva compatibilidad con `/accounts/login/`.
- `/mis-solicitudes/` y detalle: seguimiento privado de solicitudes, cancelación de pendientes y acceso al préstamo originado al entregarlas.
- `/panel/`: tablero operativo; `/` deja de exigir autenticación. Se mantienen los enlaces existentes a inventario, préstamos, firmas, mantenimiento y pagos.
- `/solicitudes/`: bandeja para administrador y bodeguero, con filtros por estado y acciones de entrega o rechazo.

El cliente autenticado dispone de navegación a catálogo, selección, solicitudes, préstamos y cargos propios. El personal tiene acceso claro al panel. Tras ingresar, se respeta un next local válido; en ausencia de next, el personal va al panel y el cliente a sus solicitudes. Se usa una presentación comercial pública coherente con BuildCorp y una navegación operativa diferenciada, sin reemplazar la aplicación por otro framework.

## Catálogo e imágenes
Se utilizan los activos físicos actuales: cada herramienta del catálogo representa un activo identificable del inventario, sin crear un sistema paralelo de productos o stock. Solo se publican activos no dados de baja y asociados a categoría, bodega y obra activas. Se puede mostrar una herramienta en uso o revisión como temporalmente no disponible, deshabilitando su incorporación a la selección.

La ficha pública no expone números de serie, bodegas internas, ubicación exacta, contratistas actuales, movimientos, firmas ni trabajos internos. La disponibilidad significa disponible hoy, no una garantía de reserva futura; la interfaz lo explica antes de enviar la solicitud.

Se agrega imagen opcional de activo, con edición autorizada al personal desde formularios/API/Admin. Se aceptan JPEG, PNG y WebP válidos, hasta 512 KiB y 4096 píxeles por dimensión. Se usan imágenes ilustrativas originales de herramientas como respaldo por categoría, identificadas como referenciales. Los activos existentes siguen funcionando sin imagen subida.

Las imágenes subidas se sirven mediante una ruta pública que obtiene el archivo del activo publicado, sin aceptar rutas arbitrarias. Las firmas continúan en su endpoint privado y no se exponen mediante un directorio media público. Los archivos subidos se guardan en MEDIA_ROOT, fuera de Git; los respaldos estáticos del catálogo forman parte del código.

## Registro y titularidad
Crear una cuenta e iniciar sesión es obligatorio para enviar cualquier solicitud de alquiler; no habrá alquiler ni solicitudes anónimas. Un visitante puede consultar el catálogo y preparar su selección; al intentar enviarla se le dirige a ingreso/registro, conservando la selección y un destino local válido para continuar después.

Formulario de cliente: usuario, nombre del responsable, correo, identificación/RUT, nombre o razón social, teléfono, contraseña y confirmación. La cuenta se activa al completar un registro válido; este alcance académico no incorpora envío de correo ni verificación por email.

Una transacción crea un Contractor propio y el User vinculado con rol CONTRATISTA, is_staff=False e is_superuser=False. Los campos de privilegio enviados por el navegador no se aceptan. Las contraseñas usan validadores y hash de Django; no se guardan ni registran en texto plano. Después del registro se inicia sesión y se conserva la selección de herramientas.

La identificación se normaliza y valida como RUT chileno, incluido dígito verificador. Las cuentas nuevas no se enlazan automáticamente a un Contractor existente por conocer su RUT o correo. Si esos datos ya están registrados, el formulario informa que se debe ingresar con la cuenta existente o contactar administración; no muestra documentos de esa empresa ni crea una segunda identidad para eludir un bloqueo.

Se agregan restricciones para identificación normalizada de contratista y correo de usuario no vacío sin distinguir mayúsculas. Los correos vacíos de cuentas existentes siguen permitidos. Una migración previa verifica colisiones de datos existentes y, si encuentra alguna, se detiene con una explicación; no elimina ni combina usuarios o historiales. Los identificadores ficticios DEMO actuales se conservan, aunque el formulario público solo admite RUT válido.

El cambio no convierte usuarios existentes ni modifica claves o permisos. Las cuentas administrativas y sus préstamos siguen accesibles después de migrar.

## Selección y solicitud
La selección de sesión almacena únicamente IDs de activos distintos. Los precios, nombres y disponibilidad se vuelven a obtener del servidor. Un mismo activo no admite cantidad mayor que uno porque representa una unidad física. Se permite agregar y quitar herramientas; una selección vacía no se envía.

Para enviar, el cliente proporciona obra/dirección de destino, responsable, inicio previsto, fin previsto y observaciones. No se publica un selector con todas las obras internas de BuildCorp: nombre y dirección se guardan como datos de la solicitud, y el bodeguero vincula una obra operativa al entregar.

El inicio previsto no puede estar en el pasado y el fin debe ser posterior al inicio. Se rechazan contratistas inactivos, bloqueados manualmente o morosos, y herramientas no disponibles o con revisión vencida en ese instante. La entrega posterior vuelve a comprobar estas reglas.

La estimación suma tarifa diaria actual por activo por períodos de 24 horas previstos, redondeados hacia arriba y con mínimo un día. La solicitud guarda tarifas/estimación informativas para mostrar lo que se presentó. No genera cargo ni intento Webpay y no garantiza la tarifa final: la tarifa aceptada se fija en la entrega firmada y el cargo real se calcula con las devoluciones efectivas. Esta diferencia se explica al cliente antes de enviar.

El envío emplea una clave de idempotencia asociada al usuario y al contenido: repetir la confirmación no duplica solicitudes; cambiar el contenido con la misma clave se rechaza. La selección se vacía solo tras confirmarse la operación.

## Modelo y estados nuevos
Se agregan entidades de solicitud al dominio rentals, con migraciones incrementales:
- RentalRequest: cliente solicitante, Contractor, obra/dirección solicitadas, responsable, fechas previstas, observaciones, estado, instante de creación/actualización, clave de envío, actor/motivo de resolución y préstamo generado opcional.
- RentalRequestItem: solicitud, activo, tarifa diaria estimada presentada y referencia histórica protegida. Una línea por activo y solicitud.

Estados persistidos: PENDIENTE, ENTREGADA, RECHAZADA y CANCELADA. Una solicitud pendiente cuyo fin previsto ya pasó muestra plazo vencido y no puede entregarse; puede cancelarse o volver a solicitarse con fechas válidas. El mero paso del tiempo no modifica registros desde una petición GET.

El cliente puede cancelar solo su solicitud pendiente. Administrador/bodeguero pueden rechazar una pendiente con motivo o confirmar la entrega. Todas las solicitudes y transiciones se consultan por titularidad y se conservan para seguimiento, sin borrados genéricos de históricos.

## Confirmación por bodega
La bandeja muestra fechas, contratista, datos de obra y activos solicitados. Confirmar entrega abre un formulario con obra operativa, responsable, vencimiento y firma. Se conservan las herramientas solicitadas: la entrega es completa; cambiar parcialmente la selección exige rechazar la solicitud con motivo y que el cliente cree otra. No se agrega sustitución de herramientas a este alcance.

La firma, tarifa vigente y vencimiento se revisan en ese momento. Una solicitud con tarifa cambiada muestra la diferencia antes de capturar aceptación; las líneas del Loan conservan la tarifa realmente aceptada. No se puede confirmar una entrega con vencimiento pasado.

La operación bloquea contratista, solicitud y activos en un orden compatible con los servicios actuales. Invoca issue_loan dentro de la misma transacción y vincula el préstamo antes de pasar a ENTREGADA. Si falla disponibilidad, mantenimiento, firma o validación, no crea una entrega parcial ni cambia estado. Repetir la confirmación de una ya entregada retorna su préstamo existente, sin duplicar firmas ni préstamos. Confirmación, cancelación y rechazo concurrentes no pueden producir estados contradictorios.

La solicitud no retiene stock. Dos clientes pueden pedir la misma herramienta; al confirmar las entregas, los bloqueos y restricciones PostgreSQL existentes permiten una sola entrega activa. La otra solicitud conserva una explicación accionable para el bodeguero.

## Páginas no encontradas
Actualmente el proyecto no tiene template 404 propio ni handler404 personalizado. Se incorporará una página pública de BuildCorp que indique «Página no encontrada» y tenga un botón «Volver al inicio» apuntando a `/`.

La página funciona tanto para visitantes como para usuarios autenticados y conserva el estado HTTP 404. No redirige automáticamente ni oculta el motivo de la navegación fallida. No muestra detalles técnicos ni revela si un documento privado pertenece a otra persona. Los permisos 403 mantienen su significado y el acceso a documentos ajenos continúa protegido.

La API conserva respuestas JSON con estado 404 y no se redirige a HTML. La verificación contempla URL web inexistente con DEBUG=False, visitante/usuario autenticado, enlace correcto al inicio y respuesta JSON para rutas API inexistentes.

## Seguridad e integración
Páginas públicas y registro tienen permisos anónimos explícitos y mínimos. El resto mantiene autenticación y CSRF. Los clientes solo acceden a selección/sus solicitudes/sus préstamos/sus cargos. No se publica la API completa de inventario: se usa una proyección pública limitada de los datos del catálogo. Las acciones operativas se ejecutan a través de servicios compartidos por web/API/Admin.

Admin registra los modelos nuevos con filtros y búsquedas. Los documentos de solicitud y sus líneas no admiten edición genérica que omita las transiciones; las acciones remiten al flujo operativo correspondiente. La foto de inventario sí es editable con las mismas validaciones de formato/tamaño.

Se conserva Webpay en integración, sin pago por registrar una solicitud. El cliente puede pagar el cargo que se genera al cerrar el préstamo. El reemplazo temporal por mantenimiento sigue diferido.

## Migración y actualización de EC2
Se realizan cambios locales en backend_eva3, preservando las migraciones iniciales y agregando migraciones nuevas. No se borra ni recrea PostgreSQL y no se requiere copiar el .env local al servidor.

Se documentará cómo comprobar la rama/remoto usados por el usuario, respaldar la base, detener temporalmente BuildCorp, actualizar Git, instalar requisitos, aplicar migraciones, ejecutar collectstatic y check y reiniciar/comprobar Gunicorn y Nginx. El procedimiento revisará la IP pública actual y los valores ALLOWED_HOSTS, PUBLIC_BASE_URL, CSRF_TRUSTED_ORIGINS y server_name cuando vuelva a encender la instancia. La guía distinguirá actualización normal de recuperación ante fallo; no recomendará revertir migraciones o restablecer la base a ciegas.

La instancia será encendida y actualizada por el usuario. No se harán operaciones AWS/DNS ni push desde esta tarea.

## Validación y aceptación
Pruebas sobre PostgreSQL real:
- Visitante puede abrir portada, catálogo, filtros y ficha; solo ve campos públicos y herramientas publicadas.
- Registro válido crea cuenta de cliente y contratista propios; contraseñas inválidas, RUT inválido/duplicado y privilegios manipulados se rechazan sin altas parciales. RUT o correo conocidos no permiten asumir una cuenta existente.
- Datos existentes, usuarios y préstamos sobreviven a las migraciones; las colisiones normalizadas se detectan antes de imponer restricciones.
- Un visitante no puede enviar una solicitud ni generar un préstamo: se exige registro e ingreso, se conserva su selección y se puede continuar después de autenticarse.
- Página 404 propia funciona para visitante y usuario, con botón «Volver al inicio», sin redirección automática ni detalles privados; la API responde JSON 404.
- Selección mantiene activos sin duplicarlos; servidor recalcula precios y condiciones; envío repetido es idempotente y una selección vacía/fecha inválida se rechaza.
- Cliente bloqueado o moroso no puede enviar ni recibir entrega; no se elude el bloqueo con un registro duplicado del mismo RUT.
- Cliente no ve ni modifica solicitudes ajenas; solo puede cancelar las propias pendientes. Personal puede ver y resolver con motivo.
- Entrega de solicitud crea un solo Loan con firma, a través del servicio existente; repeticiones/carreras con cancelación o con otra entrega del mismo activo conservan integridad.
- Fallo de entrega no genera préstamo, cargo, firma ni cambio de estado parcial.
- Imágenes inválidas y exceso de tamaño se rechazan; foto referencial funciona en activos existentes; endpoint público no expone firmas ni archivos arbitrarios.
- Flujos existentes de devolución, mantenimiento y pagos siguen pasando la suite de regresión.

Verificación adicional: check, makemigrations --check --dry-run, migrate --check, collectstatic y recorrido en navegador de escritorio/móvil: visita anónima → registro → catálogo → selección → solicitud → confirmación por bodeguero con firma → seguimiento por cliente → devolución → cargo de prueba. Registrar resultados reales y limitaciones, sin atribuir pruebas de AWS que no se ejecutaron.

## Documentación afectada
Actualizar README, arquitectura 4+1, modelo relacional, defensa, verificación, prompts_ia.md y guía de actualización EC2. Registrar que el usuario aprobó habilitar acceso público y autogestión de clientes, modificando el alcance inicial de alta exclusiva por administrador.

## Revisión propia de la especificación
El registro asigna siempre la identidad en servidor; no hay asociación automática por RUT. Las solicitudes no reservan stock ni cobran; la entrega reaplica los bloqueos del dominio existente. La tarifa estimada de solicitud se distingue de la pactada al entregar y del cargo efectivo al devolver. Las obras internas no se publican. La migración es incremental y preserva credenciales/historiales. La foto pública está separada de las firmas privadas. La aprobación del enfoque conversacional permite esta especificación; queda pendiente su revisión antes de escribir el plan de implementación.

