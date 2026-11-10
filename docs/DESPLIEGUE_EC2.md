# Guía para desplegar BuildCorp en una única EC2

**Estado: instrucciones preparadas; no ejecutadas en AWS.** Sigue estas etapas cuando decidas desplegar. No hace falta cambiar Webpay a producción. Esta guía usa Ubuntu Server 24.04 LTS, usuario `ubuntu` y directorio `/home/ubuntu/buildcorp`; adapta usuario/ruta si eliges otra imagen.

## 1. Crear la instancia en AWS Academy

Inicia el laboratorio y espera sus credenciales temporales. En EC2 elige una instancia Ubuntu admitida por el laboratorio, con IPv4 pública y espacio para sistema, dependencias y PostgreSQL (por ejemplo 16 GB). Usa el tamaño permitido por tu curso; no presupongas que un recurso está cubierto por los créditos. Conserva la clave privada del par de claves.

Grupo de seguridad: TCP 22 desde **tu IP**, TCP 80 para acceso web y TCP 443 cuando habilites HTTPS. No abras 5432 ni 8000 al público: base y Gunicorn escuchan en loopback. [Reglas oficiales EC2](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/security-group-rules-reference.html).

Desde PowerShell, reemplazando ruta de clave e IP:

```powershell
ssh -i 'C:\ruta\clave.pem' ubuntu@PUBLIC_IP
```

## 2. Preparar servidor y copiar solo la entrega

Dentro de EC2:

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip postgresql postgresql-client nginx
mkdir -p /home/ubuntu/buildcorp
```

Copia código desde tu repositorio o una carpeta de entrega limpia. No copies `.env`, `.venv`, `.local`, `.runtime`, archivos QA, sesiones o datos locales. Desde tu computador puedes usar `scp` para una carpeta preparada, o clonar tu repositorio en la ruta indicada. Publicar GitHub es una actividad separada y no se realizó aquí.

## 3. Crear PostgreSQL en la misma instancia

```bash
sudo systemctl enable --now postgresql
sudo -u postgres psql
```

Dentro de psql:

```sql
CREATE ROLE buildcorp_app LOGIN;
\password buildcorp_app
CREATE DATABASE buildcorp OWNER buildcorp_app;
\q
```

`\password` pide una clave que eliges tú; no copies una contraseña del ejemplo. El rol de aplicación no necesita ser superusuario. No ejecutes las pruebas contra la base de la defensa: las pruebas locales crean otra base y usan un rol con CREATEDB.

## 4. Entorno Python y variables

```bash
cd /home/ubuntu/buildcorp
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
chmod 600 .env
.venv/bin/python -c 'import secrets; print(secrets.token_urlsafe(56))'
nano .env
```

Completa `.env` con una clave secreta propia y la contraseña PostgreSQL elegida:

```dotenv
DJANGO_SECRET_KEY=TU_CLAVE_ALEATORIA_DE_AL_MENOS_40_CARACTERES
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=PUBLIC_IP,127.0.0.1,localhost
DB_NAME=buildcorp
DB_USER=buildcorp_app
DB_PASSWORD=TU_CLAVE_POSTGRESQL
DB_HOST=127.0.0.1
DB_PORT=5432
WEBPAY_ENV=integration
PUBLIC_BASE_URL=http://PUBLIC_IP
COOKIE_SECURE=False
```

Reemplaza los marcadores, no los dejes literales. La primera comprobación por IP/HTTP requiere cookies no seguras; usa cuentas ficticias durante esa etapa. Cuando esté disponible HTTPS, cambia las variables de la etapa 8. `POSTGRES_BIN` es exclusivo del script portable Windows y no se usa en EC2.

```bash
.venv/bin/python manage.py migrate --noinput
.venv/bin/python manage.py collectstatic --noinput
.venv/bin/python manage.py seed_demo
.venv/bin/python manage.py createsuperuser
.venv/bin/python manage.py check
.venv/bin/python manage.py migrate --check
```

No copies el administrador de tu computador. Crea aquí el propio y luego las cuentas de demostración. WhiteNoise sirve los archivos estáticos generados; no se necesita hacer pública la carpeta con firmas, ya que estas están protegidas en PostgreSQL.

## 5. Gunicorn y Nginx

Los archivos de `deploy/` son ejemplos revisables, no acciones ya realizadas. Verifica rutas y usuario antes de copiarlos.

```bash
sudo cp deploy/buildcorp.service.example /etc/systemd/system/buildcorp.service
sudo systemctl daemon-reload
sudo systemctl enable --now buildcorp
sudo systemctl status buildcorp --no-pager
curl -I http://127.0.0.1:8000/accounts/login/
```

Prepara la configuración Nginx reemplazando `PUBLIC_IP`:

```bash
sudo cp deploy/nginx.conf.example /etc/nginx/sites-available/buildcorp
sudo nano /etc/nginx/sites-available/buildcorp
sudo ln -s /etc/nginx/sites-available/buildcorp /etc/nginx/sites-enabled/buildcorp
sudo nginx -t
sudo systemctl reload nginx
```

Si la página por defecto captura tu solicitud, revisa los bloques activos y deshabilita únicamente el sitio por defecto identificado en esa instancia. Comprueba `http://PUBLIC_IP/accounts/login/`. No uses runserver como servidor público. El log de acceso de ejemplo guarda la ruta sin parámetros para no registrar tokens de retorno Webpay.

## 6. Alertas periódicas

Como usuario ubuntu, `crontab -e` y agrega:

```cron
*/5 * * * * cd /home/ubuntu/buildcorp && .venv/bin/python manage.py revisar_alertas >> /home/ubuntu/buildcorp/alerts.log 2>&1
```

El bloqueo de morosos y activos con revisión vencida funciona aunque cron aún no haya corrido. El proceso crea alertas de morosidad y reporta revisiones pendientes; es idempotente. No es un sistema de envío de correos.

## 7. Verificación pública y fallos frecuentes

Prueba con administrador, bodeguero y contratista: CRUD, entrega firmada, devolución parcial/total, mantenimiento por fecha y horas, bloqueo por morosidad y pago de integración. PUBLIC_BASE_URL debe coincidir con la dirección pública y puerto: al terminar, el navegador retorna a esa dirección. Las tarjetas son ficticias; la aplicación seguirá sin cobrar dinero real aunque esté en una EC2 pública.

Comandos de diagnóstico:

```bash
sudo journalctl -u buildcorp -n 80 --no-pager
sudo nginx -t
sudo systemctl status postgresql nginx buildcorp --no-pager
.venv/bin/python manage.py check --deploy
```

Error 502: revisar Gunicorn, usuario, rutas y conexión DB. Error 400/DisallowedHost: revisar ALLOWED_HOSTS. Error CSRF: revisar host, protocolo, orígenes confiables y cookies. CSS ausente: ejecutar collectstatic y reiniciar Gunicorn. Después de cambios en `.env`: `sudo systemctl restart buildcorp`.

`check --deploy` identifica ajustes de seguridad dependientes del despliegue; no significa que el sitio ya esté protegido por HTTPS ni que AWS haya sido probado desde este computador.

## 8. DNS y HTTPS, cuando decidas hacerlo

Una vez que EC2 funcione, puedes configurar un nombre DuckDNS hacia su IP pública. Esta entrega no registra nombres ni configura actualizaciones DNS. Cuando el nombre resuelva a la instancia, inclúyelo en server_name y ALLOWED_HOSTS, instala/configura un certificado HTTPS según el proveedor elegido y verifica su renovación.

Después, configura:

```dotenv
PUBLIC_BASE_URL=https://TU_NOMBRE.duckdns.org
DJANGO_ALLOWED_HOSTS=TU_NOMBRE.duckdns.org,127.0.0.1,localhost
CSRF_TRUSTED_ORIGINS=https://TU_NOMBRE.duckdns.org
COOKIE_SECURE=True
SECURE_SSL_REDIRECT=True
```

Nginx debe terminar TLS y sobrescribir X-Forwarded-Proto; Gunicorn continúa solo en loopback. Django confía en ese encabezado únicamente dentro de este esquema de proxy controlado. Revisa `check --deploy` y habilita HSTS después de comprobar HTTPS y sus subdominios. [Lista oficial Django](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/).

En AWS Academy la IP puede cambiar al recrear o detener/iniciar recursos: comprueba IP, reglas, DNS y PUBLIC_BASE_URL antes de la defensa. No automatices DNS hasta decidir la configuración definitiva.

## 9. Respaldo y restauración

Como ubuntu, crea una carpeta privada y un respaldo PostgreSQL de formato custom; usa un nombre con fecha para no sobrescribir el último:

```bash
mkdir -p ~/buildcorp-backups
chmod 700 ~/buildcorp-backups
pg_dump -h 127.0.0.1 -U buildcorp_app -W -Fc buildcorp -f ~/buildcorp-backups/buildcorp-FECHA.dump
pg_restore --list ~/buildcorp-backups/buildcorp-FECHA.dump
```

Conserva por separado `.env` y el código/migraciones de la misma versión. El volcado contiene firmas y datos de usuarios: trátalo como privado. Para demostrar restauración, crea **una base distinta**, asígnala al mismo rol y restaura allí con `pg_restore --no-owner --no-privileges -h 127.0.0.1 -U buildcorp_app -W -d buildcorp_restore_test ARCHIVO.dump`. Nunca apuntes esa prueba a la base activa. Configura temporalmente otra instancia de aplicación para consultar la copia y compara conteos y un préstamo completo. La restauración en AWS queda pendiente de tu ejecución.
