# EVA 4 · BuildCorp interno

La rama `eva4` conserva Django y los módulos de dominio en la raíz. `frontend/` tiene la aplicación React. `deploy/eva4/` tiene archivos de referencia para ambas EC2. Usa [la guía AWS](EVA4_AWS.md) después de validar localmente. Las rutas de EVA 3 quedan disponibles con su configuración histórica para mantener sus pruebas. El servidor EVA 4 se inicia explícitamente con `buildcorp.eva4_settings`, que publica solamente la API interna.

## Levantar en Windows

Desde la carpeta del repositorio, con `.venv` y `.env` configurados. Usa el PostgreSQL local de desarrollo o una copia limpia. El nombre y puerto deben coincidir con los de tu entorno.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts/local_db.py start
.\.venv\Scripts\python.exe manage.py migrate --settings=buildcorp.eva4_settings
# Si todavía no tienes una cuenta interna:
.\.venv\Scripts\python.exe manage.py createsuperuser --settings=buildcorp.eva4_settings
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000 --settings=buildcorp.eva4_settings
```

Usa `DJANGO_DEBUG=True` únicamente en desarrollo. Con `DEBUG=False` debes definir una `JWT_SIGNING_KEY` independiente en `.env`. En una **segunda terminal** con Node compatible (Node 24 LTS es una opción), ejecuta:

```powershell
cd frontend
npm.cmd ci
npm.cmd run dev
```

Abre [localhost:5173](http://localhost:5173/). Vite reenvía `/api/` al backend. Los tokens están en memoria de la pestaña y el acceso dura cinco minutos, con renovación hasta ocho horas. Recargar la página requiere iniciar sesión. El cierre local elimina los tokens de la memoria de la aplicación. El backend consulta el estado y rol de la cuenta en las peticiones autorizadas.

## API y recorrido

| Ruta bajo /api/ | Uso |
|---|---|
| `health/` | GET público de salud |
| `auth/token/`, `auth/refresh/`, `auth/me/` | POST con usuario y contraseña, POST con refresh y GET de identidad, respectivamente |
| `sites/`, `warehouses/`, `categories/`, `assets/` | GET/POST de colección y GET/PATCH/DELETE por ID. La API impide borrar registros con historial y reserva DELETE para administración. Las herramientas con historial se dan de baja. |
| `contractors/`, `users/` | Gestión interna. Solo administradores gestionan usuarios y modifican contratistas. |
| `rental-requests/` | Listado y creación interna. Por ID: GET `approval-quote/`, POST `approve/`, `reject/` o `fulfill/`. |
| `loans/` | Listado, detalle y POST `return/` por ID. |
| `maintenance-plans/`, `maintenance-jobs/` | Planes, inicio de mantenimiento y POST `finish/` por trabajo. |
| `alerts/`, `charges/` | Consulta de vencimientos, bloqueos y cargos históricos. |

El frontend envía `Authorization: Bearer <access>` en las peticiones protegidas. Los listados están paginados. Las validaciones de negocio son responsabilidad de DRF y de los servicios Django.

1. Da de alta obra, bodega, categoría, herramienta y contratista. El administrador puede gestionar cuentas de personal.
2. Crea una solicitud para un contratista con inicio futuro y vencimiento posterior. Aprueba y selecciona la obra para reservar la herramienta.
3. Dentro del período aprobado, registra la entrega con firma y luego la devolución con horas y daños. El préstamo nuevo es de tipo `INTERNAL`. No solicita ni genera un pago. Las solicitudes y préstamos anteriores conservan su modalidad comercial, reservas, importes y comprobantes. Las solicitudes de EVA 3 pendientes de pago requieren resolución como casos históricos.
4. Comprueba mantenimiento y alertas. Prueba con un bodeguero y confirma que el menú Usuarios esté reservado a administración.

### Verificación local

```powershell
.\.venv\Scripts\python.exe manage.py test tests.test_eva4 --settings=buildcorp.eva4_settings
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run --settings=buildcorp.eva4_settings
cd frontend
npm.cmd run build
```

La prueba usa una base temporal PostgreSQL y comprueba JWT, permisos, persistencia, entrega interna y devolución. Durante la comprobación local también se creó una categoría desde React en un navegador real, verificando HTTP 201 y la fila correspondiente en la base temporal. El informe técnico y las evidencias AWS se completan durante el despliegue real.
