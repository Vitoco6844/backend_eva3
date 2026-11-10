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
7. **Método de trabajo:** el usuario eligió implementación en este chat para reducir consumo y autorizó subagentes solo cuando fueran estrictamente necesarios. Cualquier revisión independiente que finalmente se ejecute se registrará en VERIFICACION.md.

## Responsabilidad y límites
La IA participó de forma sustancial en la implementación; esta evidencia no busca ocultarlo. No se inventan validaciones en AWS ni actividades realizadas por el estudiante. Las decisiones del diseño fueron revisadas y aprobadas por el usuario antes de implementar. Las fuentes técnicas se enlazan en los documentos correspondientes y los resultados de pruebas constan en docs/VERIFICACION.md.
