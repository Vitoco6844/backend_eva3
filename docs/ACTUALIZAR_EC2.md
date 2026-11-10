# Actualizar la instancia EC2 existente

Esta guía corresponde a una instancia ya configurada, con el servicio `buildcorp`, PostgreSQL y Nginx. El usuario ejecuta los comandos; esta ampliación no ha sido desplegada desde el asistente. Publica primero tus cambios locales en GitHub. No recrees la base ni el administrador y no reemplaces `.env` por `.env.example`.

## Cambio incluido: pago antes de nuevas entregas

Esta actualización añade `payments.0002_prepaid_approval` y `rentals.0003_prepaid_approval`. Los préstamos que ya existen quedan como LEGACY_POSTPAID y conservan sus cobros originales; los nuevos usan PREPAID. Las solicitudes pendientes existentes deben aprobarse y pagarse antes de una nueva entrega. No se modifican los pagos ya aprobados ni se pide un pago retroactivo por herramientas entregadas anteriormente.

**Ejecuta las etapas en orden y con el servicio detenido durante pull/migrate.** Cambia el contrato de cargos y de entrega: no es una actualización para mezclar procesos antiguos y nuevos mientras migran. Mantén pausada la entrada cron de BuildCorp desde el respaldo hasta reiniciar y comprobar la versión. Los respaldos permiten recuperar una versión coherente; no se deben revertir migraciones a ciegas.

## 1. Encender y revisar la dirección

Enciende tu instancia y consulta su IPv4 pública actual: puede cambiar después de detenerla. Desde PowerShell, reemplaza `IP_ACTUAL`:

```powershell
ssh -i "C:\Users\vimat\Downloads\buildcorp.pem" ubuntu@IP_ACTUAL
```

Dentro de Ubuntu:

```bash
cd /home/ubuntu/buildcorp
git status --short
git branch --show-current
git remote -v
git log -1 --oneline
```

La rama de trabajo local de esta entrega es `backend/buildcorp`; comprueba que la instancia siga la rama donde publicaste los cambios. Si hay cambios locales, resuélvelos antes de continuar. No uses reset forzado ni borres archivos para hacer pasar un pull. Anota el commit actual para diagnóstico.

Si cambió la IP, edita `.env` con `nano .env`. Conserva la clave secreta y las credenciales existentes. Para la instalación por HTTP configura estos valores con la IP nueva:

```dotenv
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=IP_ACTUAL,127.0.0.1,localhost
PUBLIC_BASE_URL=http://IP_ACTUAL
CSRF_TRUSTED_ORIGINS=http://IP_ACTUAL
```

Si ya utilizas dominio y HTTPS, conserva el protocolo, dominio y cookies seguras correspondientes. Actualiza también `server_name` en `/etc/nginx/sites-available/buildcorp` si estaba fijado a la IP anterior. Esta actualización no requiere crear recursos AWS ni cambiar Webpay a producción.

## 2. Respaldo antes de modificar código o esquema

Detén temporalmente la aplicación para obtener un respaldo coherente con sus archivos. PostgreSQL permanece activo. Si existe un cron de BuildCorp, pausa solo su entrada durante la actualización y restáurala al terminar.

```bash
sudo systemctl stop buildcorp
mkdir -p /home/ubuntu/buildcorp-backups
chmod 700 /home/ubuntu/buildcorp-backups
umask 077
buildcorp_stamp=$(date +%Y%m%d-%H%M%S)
pg_dump -h 127.0.0.1 -U buildcorp_app -W -Fc buildcorp -f "/home/ubuntu/buildcorp-backups/buildcorp-$buildcorp_stamp.dump"
pg_restore --list "/home/ubuntu/buildcorp-backups/buildcorp-$buildcorp_stamp.dump" > "/home/ubuntu/buildcorp-backups/buildcorp-$buildcorp_stamp.list"
cp .env "/home/ubuntu/buildcorp-backups/env-$buildcorp_stamp"
git rev-parse HEAD > "/home/ubuntu/buildcorp-backups/commit-$buildcorp_stamp.txt"
if [ -d media ]; then tar -czf "/home/ubuntu/buildcorp-backups/media-$buildcorp_stamp.tar.gz" media; fi
```

`pg_dump -W` pide la contraseña PostgreSQL que configuraste. Adapta usuario/nombre si tus valores DB_USER/DB_NAME son distintos. Ejecuta cada comando y revisa su resultado; **si falla el respaldo, no continúes con la actualización**. Listar el volcado comprueba su legibilidad, pero no equivale a una restauración probada. Los respaldos contienen información privada y no se suben a GitHub. La guía DESPLIEGUE_EC2.md describe restauración en una base distinta.

## 3. Actualizar, migrar y reunir estáticos

Ejecuta cada comando dentro de `/home/ubuntu/buildcorp`. Detente si alguno falla:

```bash
git pull --ff-only
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python manage.py check
.venv/bin/python manage.py migrate --noinput
.venv/bin/python manage.py migrate --check
.venv/bin/python manage.py collectstatic --noinput
```

Las migraciones conservan el catálogo y añaden aprobación, retenciones y cargos INITIAL/EXTRA, con identificación de los préstamos antiguos. Las anteriores de identidad por RUT/correo y de imágenes permanecen en el historial. No eliminan préstamos ni usuarios. Si detectan correos o RUT duplicados, se detendrán mostrando los identificadores afectados: revisa esos registros con sus responsables, corrige la identidad y repite migrate. No borres la base, no uses `--fake` y no fusiones clientes automáticamente.

No ejecutes `seed_demo`, `createsuperuser` ni pruebas sobre la base de la instancia para esta actualización. El catálogo existente y el administrador se conservan. Las doce imágenes de referencia vienen con el código; si algún activo tiene una fotografía propia, se mantiene en `media/`.

## 4. Iniciar y comprobar

```bash
sudo nginx -t
sudo systemctl start buildcorp
sudo systemctl status buildcorp --no-pager
sudo systemctl reload nginx
curl -I http://127.0.0.1:8000/
curl -I http://127.0.0.1:8000/accounts/login/
```

Abre `http://IP_ACTUAL/` sin sesión: debe aparecer la tienda, no un ingreso obligatorio. Revisa catálogo, ficha e imágenes; agrega un equipo y comprueba que recién al enviar pide cuenta. Registra un cliente de demostración y envía una solicitud. Desde bodega aprueba la cotización: las unidades deben quedar retenidas y aún no debe permitir entregar. Como cliente paga el período contratado con Webpay de integración; con el pago confirmado, vuelve a bodega y entrega con firma. Devuelve a tiempo y comprueba que no aparece otro cargo; el retraso genera únicamente su saldo. Comprueba también que un préstamo antiguo sigue accesible, con sus importes y pagos conservados. Una ruta inexistente debe mostrar «Volver al inicio» y conservar HTTP 404.

Restablece la entrada cron que pausaste. El personal accede al panel en `/panel/`; Admin permanece en `/admin/`. Webpay continúa exclusivamente en integración.

Si hay un fallo:

```bash
sudo journalctl -u buildcorp -n 80 --no-pager
sudo systemctl status postgresql nginx buildcorp --no-pager
.venv/bin/python manage.py showmigrations
```

Si el pull falló antes de modificar código/esquema, puedes arrancar el servicio anterior con `sudo systemctl start buildcorp`. Si ya cambió el esquema, identifica el error y completa la migración antes de abrir el servicio. No restaures encima de la base activa ni reviertas migraciones ciegamente: conserva respaldo, commit y logs y prepara una recuperación coherente en una base distinta si fuera necesaria.

## Comprobación específica después de esta actualización

```bash
.venv/bin/python manage.py showmigrations rentals payments
.venv/bin/python manage.py shell -c 'from rentals.models import Loan; from payments.models import Charge; print("Historicos:", Loan.objects.filter(billing_mode="LEGACY_POSTPAID").count()); print("Prepago:", Loan.objects.filter(billing_mode="PREPAID").count()); print("Cargos:", Charge.objects.count())'
```

Las migraciones indicadas deben tener `[X]`. Compara los documentos anteriores con lo anotado antes de actualizar: las cantidades de préstamos, usuarios y cargos no deben desaparecer. La nueva colección de cargos distingue período contratado y saldo extra; no requiere recrear la base ni el administrador. Si una herramienta retenida necesita mantenimiento o el cliente queda bloqueado, la entrega seguirá impedida aunque haya pago: revisa el caso con BuildCorp. La interfaz no ofrece reembolso ni cancelación automática de un arriendo pagado.
