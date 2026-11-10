# BuildCorp · Control y alquiler de herramientas

Proyecto académico EVA 3: Django, DRF, PostgreSQL, Django Admin y templates responsivos. Inventario por obra/bodega, entregas y devoluciones firmadas, mantenimiento preventivo por fecha u horas, morosidad y pagos con Webpay Plus **exclusivamente en integración, sin dinero real**.

## Abrir en este computador

Abre PowerShell:

```powershell
cd "C:\Users\vimat\Desktop\Clases\2do sm\backend_eva3"
.\.venv\Scripts\python.exe scripts/local_db.py start
.\.venv\Scripts\python.exe manage.py createsuperuser
.\scripts\iniciar.ps1
```

La creación del administrador es necesaria solo la primera vez. Elige tu propia contraseña. Abre [BuildCorp local](http://127.0.0.1:8013/) y entra con esa cuenta. [Django Admin](http://127.0.0.1:8013/admin/) permite crear usuarios y asignarles roles. No hay usuarios o contraseñas compartidas. Los usuarios QAManager y QAContractor son exclusivos de una base temporal de verificación y no existen en tu base.

La base local usa el puerto **55433**, el nombre `buildcorp` y credenciales propias en `.env`; EVA2 conserva su base independiente. Este computador reutiliza los ejecutables PostgreSQL de EVA2 mediante `POSTGRES_BIN` en `.env`. No se comparten datos ni contraseñas. Si se mueve o elimina EVA2, actualiza esa ruta o ejecuta el configurador para instalar PostgreSQL portable propio.

Para detener, Ctrl+C en el servidor, y luego `scripts/detener.ps1`. Este último detiene únicamente el clúster local de BuildCorp.

## Instalación en otro computador Windows

Requisitos: Python 3.12 o superior, internet y espacio para PostgreSQL portable. Con PostgreSQL ya instalado puedes usar una base externa.

```powershell
.\scripts\configurar.ps1 -Python python
.\.venv\Scripts\python.exe manage.py createsuperuser
.\scripts\iniciar.ps1
```

Si tienes binarios portables disponibles: `scripts/configurar.ps1 -PostgresBin 'C:\ruta\pgsql\bin'`. No copies `.venv`, `.env` ni la carpeta de datos de otro computador. Si PowerShell bloquea scripts, permite la ejecución solo en la terminal actual: `Set-ExecutionPolicy -Scope Process Bypass`.

Con base externa: copia `.env.example` a `.env`, elige claves propias, configura DB_NAME/DB_USER/DB_PASSWORD/DB_HOST/DB_PORT y ejecuta `configurar.ps1 -BaseExterna`; inicia con `iniciar.ps1 -BaseExterna`. `DJANGO_SECRET_KEY` requiere al menos 40 caracteres aleatorios. Generador: `python -c "import secrets; print(secrets.token_urlsafe(56))"`. No publiques el resultado.

## Uso y roles

- Administrador: cuentas, contratistas, datos maestros y operaciones. El superusuario inicial accede a todos los modelos de Admin.
- Bodeguero: inventario, préstamos, devoluciones y mantenimiento. No asigna roles ni administra contratistas.
- Contratista: consulta y paga únicamente sus propios cargos; su cuenta debe tener asignado el contratista correspondiente en Admin.

En Django Admin, asignar el rol no concede automáticamente permisos de administración: el acceso requiere `is_staff` y permisos Django. La interfaz de operaciones utiliza el rol de negocio. Para un bodeguero normal basta una cuenta activa con rol BODEGUERO, sin permisos de Admin.

1. Revisa o crea obras, bodegas, categorías, contratistas y herramientas. Los datos iniciales son ficticios.
2. En **Préstamos → Entregar herramientas**, selecciona herramientas disponibles, responsable, vencimiento y firma.
3. En el detalle registra devolución parcial o total, horas utilizadas, daños y firma. Las horas son las de ese préstamo, no el total del contador.
4. Si corresponde revisión o daño, el activo pasa a Mantenimiento. Inicia el trabajo y finalízalo indicando trabajo realizado y próxima revisión por fecha y/o horas acumuladas.
5. La devolución completa genera un cargo con las tarifas aceptadas al entregar. Cada herramienta se cobra por períodos de 24 horas redondeados hacia arriba, mínimo un día, hasta su propia devolución. No se agregan multas ni impuestos en este alcance académico.
6. Entra como contratista y paga el cargo con Webpay de prueba. Un pago no reemplaza una devolución de herramientas.

Las revisiones se programan con una fecha límite o umbral de horas. Los límites se renuevan al cerrar cada mantenimiento. El intercambio temporal de herramientas queda como mejora posterior.

## Webpay de prueba

El sistema rechaza `WEBPAY_ENV` distinto de `integration`; el destino bancario está fijado a `webpay3gint.transbank.cl`. No hay opción de producción. No necesitas contrato ni claves bancarias reales para este ambiente gratuito. [Fuente oficial](https://transbankdevelopers.com/ayuda).

Datos ficticios oficiales para aprobar una transacción: tarjeta VISA `4051885600446623`, CVV `123`, fecha futura; banco simulado: RUT `11.111.111-1`, clave `123`, luego Aceptar. Para rechazar, el simulador permite elegir Rechazar. Usa estos datos **solo en el formulario de integración de Transbank**. [Tarjetas oficiales](https://transbankdevelopers.com/documentacion/como_empezar).

Configura `PUBLIC_BASE_URL` con la dirección donde abres la aplicación. Por defecto es `http://127.0.0.1:8013`; si cambias puerto, actualízala y reinicia. El navegador vuelve a esa dirección al terminar. El retorno puede confirmar el pago sin sesión, pero el comprobante exige autenticación del titular.

**Por conciliar** significa que el resultado no pudo verificarse, no que el pago fue rechazado. Consulta el estado antes de reintentar. Si falla la creación y no se recibe token, el sistema conserva el bloqueo del intento; no lo borres para forzar otro pago. Revisa con el proveedor la orden y documenta la resolución. Este comportamiento conservador evita duplicados.

## Pruebas

Con PostgreSQL iniciado:

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py migrate --check
.\.venv\Scripts\python.exe manage.py test tests --noinput
.\.venv\Scripts\python.exe manage.py collectstatic --noinput
.\.venv\Scripts\python.exe manage.py revisar_alertas
```

Las pruebas usan una base temporal `test_buildcorp`; el rol PostgreSQL local tiene CREATEDB, sin ser superusuario. Nunca uses datos de producción para pruebas. El servidor opcional `scripts/ui_server.py` usa `test_buildcorp_ui` en el puerto 8014, con cuentas y claves aleatorias temporales; se cierra mediante `python scripts/ui_server.py --stop`.

## Documentación

- [Arquitectura 4+1 y API](docs/ARQUITECTURA.md).
- [Modelo relacional](docs/MODELO_RELACIONAL.md).
- [Preparación para AWS EC2](docs/DESPLIEGUE_EC2.md).
- [Guion para la defensa](docs/DEFENSA.md).
- [Verificación ejecutada](docs/VERIFICACION.md).
- [Procedencia de componentes](docs/REUTILIZACION.md).
- [Registro de apoyo de IA](prompts_ia.md).

Versiona código, migraciones, requisitos y documentación. No incluyas `.env`, `.local`, `.runtime`, `.venv`, datos de PostgreSQL, sesiones, tokens ni firmas privadas. Los estilos e identidad visual son locales, sin CDN ni fuentes remotas. El proyecto está preparado para despliegue, pero este trabajo no crea recursos en AWS, configura DNS ni publica repositorios.

Si abandonas un formulario de pago aún abierto, usa **Continuar pago de prueba** para retomar el mismo intento. Consultar un estado inicializado válido conserva esa opción; no crea otro pago.
