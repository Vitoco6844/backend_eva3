# EVA 4 · Despliegue de BuildCorp en AWS

Procedimiento para ejecutar después de autorizar el despliegue. Esta guía usa dos EC2 Ubuntu, RDS PostgreSQL, S3, CloudFront para el recurso de interfaz, API Gateway HTTP API, un ALB interno y CloudWatch. Usa un dominio nuevo para EVA 4 o cambia el de EVA 3 solo después de validar la nueva instalación.

```text
Navegador HTTPS → EC2 frontend / Nginx → HTTPS API Gateway
    → VPC Link → ALB interno → EC2 backend / DRF → RDS por TLS
Navegador HTTPS → CloudFront → bucket privado S3 (imagen de inicio)
CloudWatch → alarma de CPU de EC2 → SNS si disponible
RDS → respaldos automáticos y snapshot manual si está disponible
```

## 0. Preparar el commit y el laboratorio

1. Publica la rama `eva4` cuando estés listo con `git push -u origin eva4`. Anota el SHA con `git rev-parse HEAD`. Las dos EC2 deben usar ese mismo SHA.
2. Selecciona una sola región habilitada en el laboratorio. Confirma permisos para EC2, RDS, API Gateway HTTP API/VPC Link, ALB, S3, CloudFront, CloudWatch y SNS, más acceso administrativo a las EC2. Revisa el presupuesto del laboratorio antes de aprovisionar. ALB y el mecanismo de salida de subredes privadas pueden generar consumo mientras existen.
3. Si Academy bloquea un servicio, guarda el error y acuerda con el docente una alternativa. Para CloudFront una opción es servir un recurso S3 privado a través de una URL prefirmada de corta duración emitida por el backend. Para la integración privada de HTTP API también existe AWS Cloud Map con VPC Link. No sustituyas API Gateway por la URL directa de EC2 para acreditar throttling.
4. `BACKEND_SHA` representa el SHA publicado. `FRONTEND_DOMAIN` es el dominio elegido. `GATEWAY_HOST` es el host real del gateway, sin protocolo ni ruta. Los comandos se ejecutan en cada Ubuntu salvo cuando se indica consola AWS.

## 1. Red, Security Groups y RDS

1. Usa una VPC con DNS habilitado. Ubica el frontend en una subred pública con ruta al Internet Gateway. Usa dos subredes privadas en AZ distintas para el grupo de subredes de RDS, el ALB interno y VPC Link. Ubica el backend en una subred privada. Define antes de lanzarlo cómo le darás administración y salida para instalar dependencias y descargar el commit (por ejemplo SSM y salida por NAT si están disponibles, o paquetes preparados y acceso administrativo por la EC2 de frontend). Una subred privada sin salida no puede hacer `apt`, `git clone` ni `pip install` contra Internet.
2. Crea estos grupos de seguridad. Las fuentes que empiezan por `SG-` son grupos de la misma VPC.

| Grupo | Entrada |
|---|---|
| SG-frontend | TCP 80 y 443 desde los usuarios de la web. SSH 22 desde la IP de administración si usas SSH. |
| SG-vpclink | Sin reglas de entrada necesarias. Salida TCP 80 al ALB. |
| SG-alb | TCP 80 desde SG-vpclink. Salida TCP 8000 al backend. |
| SG-backend | TCP 8000 desde SG-alb. SSH 22 desde el grupo de administración solo si aplica. Salida TCP 5432 hacia RDS. |
| SG-rds | TCP 5432 solo desde SG-backend. |

3. En **RDS → Subnet groups**, crea el grupo con subredes privadas de al menos dos AZ. En **Databases → Create database**, elige PostgreSQL, accesibilidad pública **No**, el grupo anterior, SG-rds, almacenamiento cifrado desde la creación y retención de respaldos de, por ejemplo, 7 días. Elige una versión y tamaño permitidos por Academy. Guarda endpoint, puerto y nombre de base. Conserva la credencial maestra fuera de Git.
4. Una vez instalada la EC2 backend y descargado el certificado de RDS según el paso 2, vuelve aquí. Conecta con la cuenta maestra usando TLS y crea un usuario de aplicación y una base dedicada. Usa el endpoint real de RDS. Introduce las contraseñas solo en los prompts.

```bash
psql "host=ENDPOINT_RDS dbname=postgres user=USUARIO_MAESTRO sslmode=verify-full sslrootcert=/etc/ssl/certs/rds-global-bundle.pem"
```

```sql
CREATE ROLE buildcorp_app LOGIN;
\password buildcorp_app
CREATE DATABASE buildcorp OWNER buildcorp_app;
```

Opcional si vas a conservar datos de EVA 3: primero genera un `pg_dump -Fc` en origen, transfiérelo por un canal privado y ejecuta `pg_restore --no-owner --no-acl --exit-on-error` con el usuario de aplicación contra una base vacía en RDS. Hazlo **antes** de `migrate` y valida catálogo, usuarios, recuentos y préstamos históricos. Listar el contenido de un respaldo no prueba que la restauración funcione. Mantén la instancia anterior intacta durante la validación.

[Conexiones TLS de RDS PostgreSQL](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/PostgreSQL.Concepts.General.SSL.html) · [Respaldos y restauración](https://docs.aws.amazon.com/AmazonRDS/latest/gettingstartedguide/managing-backup-restore.html)

## 2. EC2 backend

En Ubuntu del backend, como usuario `ubuntu`:

```bash
sudo apt update
sudo apt install -y git python3-venv postgresql-client ca-certificates curl
git clone --branch eva4 https://github.com/Vitoco6844/backend_eva3.git /home/ubuntu/buildcorp-eva4
cd /home/ubuntu/buildcorp-eva4
git checkout --detach BACKEND_SHA
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
curl --fail --silent --show-error https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem | sudo tee /etc/ssl/certs/rds-global-bundle.pem >/dev/null
umask 077
cp .env.example .env
nano .env
```

Antes de seguir, vuelve al paso 1.4 y crea la base y el usuario de aplicación si aún no existen. Luego configura el archivo privado. Genera dos secretos aleatorios independientes para Django y JWT, de al menos 40 caracteres cada uno. Puedes usar `openssl rand -hex 32` en una terminal privada. No incluyas secretos en capturas ni registros.

```dotenv
DJANGO_SECRET_KEY=SECRETO_DJANGO
JWT_SIGNING_KEY=SECRETO_JWT
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost,IP_PRIVADA_BACKEND,DNS_ALB,GATEWAY_HOST
DB_NAME=buildcorp
DB_USER=buildcorp_app
DB_PASSWORD=CONTRASENA_DE_APLICACION
DB_HOST=ENDPOINT_RDS
DB_PORT=5432
DB_TLS=True
DB_SSL_ROOT_CERT=/etc/ssl/certs/rds-global-bundle.pem
WEBPAY_ENV=integration
SECURE_SSL_REDIRECT=False
```

Agrega los hosts del ALB y gateway cuando estén creados. El salto HTTP interno usa grupos de seguridad. El navegador y Nginx se conectan por HTTPS y Django conecta a RDS con verificación del certificado. Si se exige TLS también entre servicios dentro de la VPC, configura listeners y certificados internos compatibles antes de habilitarlo. El proxy confiable debe sobrescribir los encabezados de esquema antes de habilitar redirecciones HTTPS en Django.

```bash
export DJANGO_SETTINGS_MODULE=buildcorp.eva4_settings
.venv/bin/python manage.py check
.venv/bin/python manage.py migrate --noinput
.venv/bin/python manage.py migrate --check
# Solo si la base está nueva y aún no existe un administrador.
.venv/bin/python manage.py createsuperuser
sudo cp deploy/eva4/buildcorp-api.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now buildcorp-api
curl --fail http://127.0.0.1:8000/api/health/
```

Comprueba TLS de PostgreSQL desde la conexión de la app:

```sql
SELECT ssl, version FROM pg_stat_ssl WHERE pid = pg_backend_pid();
```

Ejecuta la consulta en `manage.py dbshell` con las opciones TLS activas. Para diagnóstico usa `sudo journalctl -u buildcorp-api -n 50 --no-pager`.

## 3. ALB interno, API Gateway y rate limit

1. En **EC2 → Target groups**, crea un grupo de instancias HTTP en puerto **8000**. Registra la EC2 backend. Usa `/api/health/` como health check y espera estado **Healthy**. El health check usa como host la IP privada del backend. Verifica que esté incluida en `DJANGO_ALLOWED_HOSTS`.
2. Crea un **Application Load Balancer interno**, listener HTTP 80, SG-alb y subredes privadas de dos AZ. Reenvía al target group.
3. En **API Gateway → VPC links**, crea un VPC Link compatible con HTTP API en la VPC con SG-vpclink. Espera **Available**. Crea una **HTTP API** con integración **private resource / ALB listener**. Crea la ruta `ANY /api/{proxy+}` y el stage `$default` con auto deploy. Configura el mapeo para sobrescribir la ruta de integración con `$request.path` si se añade el stage al prefijo. Conserva `Authorization` para que DRF valide JWT y el rol. Nginx llama al gateway desde el servidor, por lo que el browser trabaja con el mismo origen.
4. Crea la ruta específica `GET /api/health/` con la misma integración. En **Stages → $default → Route throttling**, configura en esa ruta **2 solicitudes por segundo** y **ráfaga 5** para la evidencia. Mantén un límite razonable para la app y limita la ruta de login por separado si la creas explícitamente. Las cifras son objetivos de throttling. Prueba solo en tu entorno y conserva la evidencia de al menos una respuesta 429.

```bash
curl -i https://GATEWAY_HOST/api/health/
curl -i https://GATEWAY_HOST/api/assets/
seq 1 18 | xargs -P 9 -I '{}' curl -sS -o /dev/null -w '%{http_code}\n' https://GATEWAY_HOST/api/health/
```

Se espera 200 en salud, 401 en inventario sin JWT y una mezcla de 200 y 429 bajo la prueba de ráfaga. Si no aparecen 429, comprueba el stage, ruta e integración antes de repetir. No expongas el puerto 8000 públicamente. Una respuesta 502 desde el gateway suele requerir revisar el target group, SG, ruta de integración o hosts permitidos.

[Integraciones privadas de HTTP API](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-develop-integrations-private.html) · [Límites por ruta](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-throttling.html)

## 4. S3, HTTPS y EC2 frontend

1. Crea un bucket privado con **Block Public Access** completo, **Bucket owner enforced** y cifrado **SSE-S3**. Sube `frontend/public/buildcorp.png` desde el commit publicado. En CloudFront, crea una distribución con origen **S3 REST** y **Origin Access Control** para firmar las solicitudes. Aplica la política sugerida restringida al ARN de tu distribución y al objeto o prefijo publicado. Conserva privadas las firmas y los datos de contratistas.
2. Cuando la distribución esté desplegada, comprueba la URL `https://DISTRIBUCION.cloudfront.net/buildcorp.png`. El recurso debe responder por CloudFront y dar acceso denegado a una solicitud anónima directamente a S3.
3. En la EC2 frontend instala Git, Nginx, Certbot y Node.js compatible con la versión fijada de Vite (usa Node 24 LTS de la [descarga oficial de Node.js](https://nodejs.org/en/download), elige Linux x64 para instancias x86_64 o arm64 para Graviton). Antes de dar acceso al sitio, configura un dominio para esa EC2, habilita entrada 80 y 443 y valida que el dominio resuelva a la interfaz. Si usas DuckDNS, asigna un nombre a la EC2 frontend y ejecuta el actualizador desde ella. No reutilices el nombre de EVA 3 durante la validación.

```bash
sudo apt update
sudo apt install -y git nginx certbot python3-certbot-nginx ca-certificates
node --version
npm --version
git clone --branch eva4 https://github.com/Vitoco6844/backend_eva3.git /home/ubuntu/buildcorp-eva4
cd /home/ubuntu/buildcorp-eva4
git checkout --detach BACKEND_SHA
cd frontend
npm ci
VITE_BRAND_URL=https://DISTRIBUCION.cloudfront.net/buildcorp.png npm run build
sudo install -d -m 755 /var/www/buildcorp-eva4
sudo cp -a dist/. /var/www/buildcorp-eva4/
cd ..
sudo cp deploy/eva4/frontend.nginx.conf /etc/nginx/sites-available/buildcorp-eva4
sudo nano /etc/nginx/sites-available/buildcorp-eva4
```

Reemplaza **todas** las apariciones de `GATEWAY_HOST` y `FRONTEND_DOMAIN`. La configuración asume stage `$default`. Habilita el sitio y solicita el certificado:

```bash
sudo ln -s /etc/nginx/sites-available/buildcorp-eva4 /etc/nginx/sites-enabled/buildcorp-eva4
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx --redirect -d FRONTEND_DOMAIN
sudo certbot renew --dry-run
curl --fail https://FRONTEND_DOMAIN/api/health/
```

Abre el navegador por HTTPS. Inicia sesión con un usuario administrador de prueba, crea una categoría o una obra y verifica su fila en RDS. Confirma en CloudWatch/API Gateway que las peticiones pasan por el gateway. Comprueba que la imagen de inicio se descargue desde CloudFront. La pantalla de inicio requiere HTTPS público porque el formulario de solicitudes usa la API de UUID del navegador. En desarrollo funciona en localhost.

[SSE-S3](https://docs.aws.amazon.com/AmazonS3/latest/userguide/default-bucket-encryption.html) · [CloudFront con OAC](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-restricting-access-to-s3.html)

## 5. CloudWatch, respaldos y pruebas

1. En **CloudWatch → Metrics → EC2 → Per-Instance Metrics**, selecciona el backend y `CPUUtilization`. Crea una alarma, por ejemplo promedio ≥80 % durante dos períodos de cinco minutos. Si SNS está disponible, crea un tema, agrega una suscripción y confírmala desde el correo. Captura métrica, umbral, instancia y estado de la alarma. Habilita access logs de API Gateway si el laboratorio lo permite, sin tokens, contraseñas ni cuerpo de solicitudes.
2. En RDS confirma la retención de respaldos. Si el laboratorio lo permite, crea un snapshot manual y espera estado **Available**. La recuperación puntual o desde snapshot crea otra instancia. Prueba la recuperación en una base aislada si el presupuesto lo permite y vuelve a ejecutar las comprobaciones de lectura. Diferencia capturas de configuración de una restauración efectivamente validada.
3. **Propuesta opcional cada siete horas.** EventBridge Scheduler `rate(7 hours)` invoca una Lambda con permiso limitado a solicitar y consultar snapshots del RDS de BuildCorp. Usa un identificador determinista por ejecución para reintentos, una política de retención y una notificación cuando el snapshot esté disponible o falle. La solicitud de creación no implica que el respaldo ya se pueda restaurar.
4. Deja para el cierre los análisis SAST y DAST solicitados. Guarda el alcance y la fecha de SonarQube y de la revisión pasiva autorizada con OWASP ZAP, y documenta los resultados reales y su tratamiento.
5. Registra dos decisiones de seguridad para el entregable de uso de IA. La primera es RDS privado con verificación del certificado desde Django, contrastada con la guía de TLS de RDS. La segunda es S3 con acceso público bloqueado y distribución OAC, contrastada con la guía de CloudFront. Acompaña cada decisión con su configuración y una comprobación real.
6. Guarda evidencias de JWT con 401 y 403, CRUD HTTP y datos en RDS, throttle 429, TLS, cifrado y permisos S3/RDS, alarma, respaldos y recomendaciones de IA contrastadas. Usa datos de prueba y oculta credenciales, tokens, hashes completos y datos personales.

[Alarma EC2 en CloudWatch](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using-cloudwatch-createalarm.html) · [Expresiones de EventBridge Scheduler](https://docs.aws.amazon.com/scheduler/latest/UserGuide/schedule-types.html)
