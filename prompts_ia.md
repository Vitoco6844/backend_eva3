# Registro de apoyo de inteligencia artificial

## Contexto y criterio de registro
Este proyecto utilizó asistencia de IA para analizar requisitos, proponer arquitectura, generar e implementar código, preparar pruebas y documentación. Las entradas siguientes son resúmenes profesionales del trabajo solicitado en esta conversación; no se presentan como transcripciones literales ni como evidencia de consultas realizadas por separado. El estudiante debe revisar y comprender la solución para defenderla.

## Solicitudes y aportes
1. **Análisis de requisitos y reutilización:** revisar instrucciones.md y el proyecto EVA2 para identificar componentes aprovechables y adaptar una solución Django/DRF al control de activos BuildCorp. Resultado: especificación y plan, aislamiento de datos y módulos nuevos.
2. **Diseño del dominio y seguridad:** definir roles, modelo relacional, transiciones de herramientas, préstamos firmados, morosidad y mantenimiento. Resultado: servicios compartidos, permisos por propietario y restricciones PostgreSQL.
3. **Integración académica de pagos:** verificar en documentación oficial si Transbank de pruebas tiene costo o mueve dinero real. Resultado: integración limitada a Webpay de pruebas, con credenciales públicas de ese ambiente y aviso explícito en interfaz.
4. **Construcción y verificación:** implementar el alcance aprobado en este chat, con pruebas de concurrencia, permisos, firmas, mantenimiento y pagos; revisar los recorridos en navegador. Resultado: código, pruebas, scripts y evidencias documentadas.
5. **Preparación de despliegue y defensa:** documentar la instalación en una única EC2 con PostgreSQL, sin operar AWS o DNS; explicar decisiones técnicas y recorridos de demostración.
6. **Mejora propuesta y diferida:** analizar el intercambio temporal por revisión preventiva; el usuario decidió dejarlo fuera del alcance inicial.
7. **Método de trabajo:** el usuario eligió implementación en este chat para reducir consumo y autorizó subagentes solo cuando fueran estrictamente necesarios. Se ejecutó una revisión independiente acotada de la ampliación; el revisor terminó y fue detenido. El alcance y los hallazgos están registrados en VERIFICACION.md.

8. **Tienda mediante templates:** incorporar portada, catálogo, fichas, selección persistente y registro de clientes al monolito Django existente; mantener el panel privado para las operaciones. El usuario precisó que explorar la página no requiere cuenta y que el registro obligatorio comienza al solicitar el arriendo.
9. **Flujo comercial:** permitir al cliente indicar obra y fechas, ver una estimación y enviar una solicitud sin reservar stock ni pagar. Bodega revisa y confirma una entrega completa con firma y tarifa aceptada; la devolución conserva el cálculo de cargo existente. Se añadieron seguimiento, cancelación y rechazo según rol.
10. **Navegación y errores:** incorporar una página 404 que conserve su código HTTP y ofrezca volver al inicio; mantener los errores de API en JSON y el acceso privado a documentos ajenos.
11. **Imágenes originales:** generar e integrar doce referencias de herramientas sin exigir al usuario buscar fotografías. Se utilizó ImageGen con un estilo coherente y sin marcas; siete referencias de categoría y cinco individuales. Los archivos y los resúmenes de prompts constan en static/images/README.md. No se presentan como fotografías de equipos reales.
12. **Pruebas y correcciones:** ampliar las pruebas a registro, identidad, migraciones, titularidad, solicitudes, concurrencia y recuperación de selección; comprobar el flujo con navegador y una base temporal. Se corrigieron hallazgos de selección despublicada, parámetros Unicode y duración durante cambios horarios, con regresiones. La evidencia documenta únicamente comprobaciones realizadas.
13. **Entrega y actualización:** preparar instrucciones para actualizar la EC2 existente desde GitHub, conservando base, administrador, .env y archivos; actualizar arquitectura, modelo, defensa y este registro después de completar la tienda. El usuario publicará el repositorio y ejecutará los pasos de AWS.

## Responsabilidad y límites
La IA participó de forma sustancial en la implementación; esta evidencia no busca ocultarlo. No se inventan validaciones en AWS ni actividades realizadas por el estudiante. Las decisiones del diseño fueron revisadas y aprobadas por el usuario antes de implementar. Las fuentes técnicas se enlazan en los documentos correspondientes y los resultados de pruebas constan en docs/VERIFICACION.md.
