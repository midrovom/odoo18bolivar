# Solicitud de crédito — WhatsApp Odoo 18

Complemento **independiente** para `custom_web_credito_conedera` (Odoo 18).
No reemplaza ni modifica los archivos del módulo principal y **no depende** de `conedera_credit_authorization` (Odoo 16).

## Eventos

- **Recibida**: etapa con `is_initial=True` al crear la solicitud.
- **Aprobada**: etapa con `is_approved=True`.
- **Rechazada/Denegada**: etapa con `is_rejected=True`.

No envía WhatsApp por otras etapas, incluida Documentación recibida. Se crea una entrada en cola por cada cambio de etapa pertinente; el cron procesa los mensajes, los reintentos y el resultado del API.

## Configuración multiempresa

1. Instalar el complemento y comprobar el menú **Solicitud de crédito → WhatsApp**.
2. En **Conexión por empresa**, elegir la empresa y configurar **API Key**, **Channel ID**, URL y prefijo internacional. Las configuraciones se crean desactivadas por seguridad.
3. Revisar **Plantillas de mensajes** para Recibida, Aprobada y Rechazada, separadas por empresa.
4. Activar **Notificaciones automáticas** solo después de efectuar una prueba.
5. Ver los resultados en **Historial de mensajes**. El cron corre una vez por minuto.

El payload usa el proveedor del módulo Odoo 16: `channelId`, `to`, y `message` (o `caption`, según la configuración). `mediaUrl`, `mediaType` y `filename` se incluyen cuando está activada la imagen adjunta (por defecto usa la imagen del complemento, como en Odoo 16). Puede desactivarse para enviar solo texto si el proveedor lo permite. La autorización usa `Authorization: Bearer ...`.

No se incluyen credenciales en el ZIP. El servicio debe admitir mensajes salientes usando la modalidad contratada. Si el canal oficial de WhatsApp requiere plantillas aprobadas fuera de la ventana de servicio, configúrelas en el proveedor antes de activar el envío.

Las campañas masivas son **manuales**, opcionales, limitadas por destinatarios y restringidas a administradores.

## Seguridad

- La empresa procede de `application.company_id` (no de la empresa activa del empleado).
- Se utiliza `application.mobile` y se añade por defecto el prefijo 593.
- Los mensajes generados incluyen enlace al historial de la empresa de la solicitud, sin tokens ni datos sensibles.
- Los logs de una empresa solo son visibles a quienes tienen acceso a ella.
- Los envíos quedan en cola cuando se guardan las solicitudes; no se envía nada dentro de la transacción de registro.
- Puede haber reenvíos en fallos extremos entre el éxito remoto y la confirmación en Odoo si el proveedor ignora el identificador de idempotencia.

## Pruebas sugeridas

Registrar solicitud nueva → 1 mensaje Recibida; mover a revisión → ninguno; aprobar → 1 Aprobada; rechazar una solicitud de prueba → 1 Rechazada; cambiar campos sin etapa → ninguno; validar números locales 099… → 59399…; probar empresas con distintas API Keys y canales.
