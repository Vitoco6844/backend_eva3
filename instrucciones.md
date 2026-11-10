# Proyecto Aplicación del Paradigma 4+1

El presente documento establece las especificaciones y enunciados de proyectos prácticos orientados a los estudiantes del curso de Backend. El objetivo fundamental de esta actividad es aplicar rigurosamente un desarrollo para estructurar, diseñar y analizar sistemas de software complejos frente a necesidades reales del entorno empresarial.

## Proyecto 4: Sistema de Alquiler y Control de Herramientas para Empresas de Construcción (BuildCorp)

### Contexto y Problema

La empresa constructora BuildCorp registra pérdidas millonarias anuales por extravío de maquinaria ligera y herramientas, cobros inexactos a subcontratistas y fallas mecánicas imprevistas. La falta de visibilidad del inventario distribuido entre múltiples obras dificulta el control y el mantenimiento oportuno de los activos.

### Objetivo General

Diseñar e implementar un sistema centralizado de gestión de activos que controle préstamos, trazabilidad entre bodegas de obra, hojas de vida de equipos y mantenimiento preventivo.

### Funcionalidades Clave y Alcance

●	Catálogo de activos con trazabilidad de estado (Disponible, En Uso, Mantenimiento, Dado de Baja).
●	Módulo de entrega y devolución de herramientas con firma digital del responsable de obra.
●	Programación de mantenimientos preventivos basados en horas de uso o fechas límite.
●	Sistema de alertas por morosidad en devoluciones y bloqueo automático de contratistas morosos.

# EVA 3: Desarrollo Backend

## Aprendizaje Esperado:

Codifica Aplicaciones web para proponer soluciones tentativas a una problemática, utilizando un framework del lado del servidor y herramientas de inteligencia como apoyo al desarrollo.

## Criterios de Evaluación:

o	1: Configura la conexión a una base de datos, según requerimiento. 
o	2: Utiliza el administrador de Django, de acuerdo a los requerimientos. 
o	3: Codifica funciones que realicen operaciones CRUD, sobre una base de datos según requerimiento. 
o	4: Codifica una aplicación backend con acceso a base de datos y seguridad, según los requerimientos del problema planteado y orientaciones generadas por herramientas de inteligencia artificial. 

## Proyecto 4: Sistema de Alquiler y Control de Herramientas (BuildCorp)

### Problema:
Pérdida de maquinaria ligera y herramientas, cobros inexactos a subcontratistas y fallas imprevistas en obras de construcción.

### Requerimientos del Caso:
1.- Catálogo de activos y herramientas con trazabilidad de estado (Disponible, en Uso, Mantenimiento, Dado de baja).
2.- Modulo de entrega y devolución de herramientas con firma digital del responsable de obra.
3.- Programación de mantenimientos preventivos basados en uso o fechas límite.
4.- Sistema de Alertas por morosidad en devoluciones y bloqueo automático de contratistas morosos.

## Requerimientos Técnicos Arquitectónicos

### Framework y Backend:

-   Desarrollo sobre Django / Django REST Framework (DRF).
-   Habilitación y personalización de Django Admin para la gestión administrativa de los modelos del dominio.
-   Manejo de sesiones, autenticación y permisos de seguridad segun corresponda a los roles del caso.

### Base de datos Relacional:

-   Configuración y conexión del backend Django a una base de datos PostgreSQL
-   Aplicación correcta de migraciones de modelos del ORM de Django.

### Frontend y Enmascaramiento:

-   Interfaz web responsiva integrada (Templates HTML/CSS/JS) o enmascaramiento asincrono que consuma los servicios de la API/Backend.

### Despliegue en AWS Cloud:

-   Configuración y despliegue de la solución en una isntancia EC2 única dentro de AWS Acadaemy.
-   La aplicación debe quedar pública y funcional accesible a través de su Ip Pública/DNS en AWS.
-   Servidor de base de datos PostgreSQL y servidor de aplicación Django corriendo ene l entorono de la instancia EC2.

### Apoyo de IA:

-   Se acepta el uso de herramientas de IA para optimizar la codificación, generación de estructuras HTML/CSS o scripts de despliegue. 
-   Se debe incluir en el repositorio un archivo prompts_ia.md especificando las consultas y apoyos solicitados a la IA.



# Instrucciones Extra.
Usar como base C:\Users\vimat\Desktop\Clases\2do sm\backend\backend_eva2 el proyecto que se encuentra aqui.

Trabajar todo en C:\Users\vimat\Desktop\Clases\2do sm\backend_eva3. Ahi guardaras todo lo que hagas respecto al proyecto

No copiar todo del mismo proyecto, sino bien, usarlo de base para no tener que escribir todo un codigo y poder utilizar lo que ya este a la mano.

A todo esto, sumarle el uso de transbank es algo que no tiene ese proyecto y es necesario para esto.

Sobre la Ip Publica/DNS podemos ocupar alguno directamente sacado de DuckDNS pero eso sera cuando tengamos el proyecto subido a AWS.

No pido que subas ni hagas nada dentro de AWS ni relacionado al DNS hasta que yo te lo pida, asi tu en vez de hacerlo, tu me dejas las instrucciones claras, cosa que yo te pueda ir consultando especificamente que cosas ir haciendo.

Tambien, se pide subir a un Github, pero, no es obligatorio que me ayudes con eso, eso puedo hacerlo yo sin ningun problema.

Sobre el apartado de apoyo de IA, trata de hacer sonar mas "profesional" a los prompts, para que asi no hayan problemas respecto a que quizas se lo pedi todo a la IA

# Rubrica

1. Configuración de Base de Datos PostgreSQL 
	Configura de forma correcta e íntegra la conexión a PostgreSQL en AWS EC2. Las migraciones del ORM están totalmente aplicadas y los datos se persisten de forma relacional.

2. Uso del Administrador de Django 
	Implementa y personaliza un panel de Admin registrando todos los modelos del caso con filtros, búsquedas y campos visuales optimizados con templates.

3. Operaciones CRUD y Reglas del Caso 
	Codifica de forma completa e impecable todas las operaciones CRUD y lógica de negocio específica para las 4 funcionalidades clave del proyecto asignado.

4. Seguridad, Sesiones y Apoyo de IA 
	Implementa autenticación de usuarios, manejo de sesiones y restricciones de seguridad adecuadas. Adjunta el archivo de evidencia de uso de IA (prompts_ia.md) bien estructurado.

5. Despliegue en AWS EC2 y Defensa en Vivo
    El proyecto está 100% operativo en una instancia EC2 accesible mediante la IP Pública asignada. Durante la defensa, el estudiante demuestra dominio total del sistema y de los requerimientos.


