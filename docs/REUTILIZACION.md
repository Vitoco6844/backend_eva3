# Procedencia y adaptación

Base solicitada: ../backend/backend_eva2 (Pulso Tickets). Se leyó su configuración, permisos, modelos, servicios transaccionales, plantillas y scripts. No se copiaron módulos de conciertos, usuarios, secretos, datos, entorno virtual ni repositorio Git.

Reutilización directa adaptada: scripts/local_db.py conserva el arranque y preparación de PostgreSQL portable de EVA2; usa BuildCorp como usuario bootstrap, clúster propio, puerto 55433 y credenciales generadas independientemente. Se agregó POSTGRES_BIN para utilizar ejecutables existentes sin compartir datos. scripts/ui_server.py sigue el patrón de servidor WSGI temporal y base de QA separada de EVA2, adaptado a BuildCorp.

Patrones adaptados: configuración con django-environ, PostgreSQL obligatorio, WhiteNoise, tarifas históricas y servicios atomic/select_for_update. El código de dominio, modelos y migraciones de BuildCorp es específico para herramientas, no un renombrado de conciertos. La autenticación cambia a sesiones de Django y la administración incorpora Django Admin real.

La identidad visual, templates, CSS y canvas de firma son propios de esta entrega. No se incorporan imágenes remotas ni librerías de iconos de EVA2.
