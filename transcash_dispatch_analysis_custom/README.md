# Transcash · Análisis de despachos personalizado

Versión 18.0.1.0.0 para Odoo 18. Dependencia: `transcash_dispatch_analysis` original 18.0.1.8.7. El ZIP base original se entrega separado y sin cambios.

## Funcionalidad
- Conserva los últimos filtros aplicados y el favorito activo por usuario y conjunto de compañías activas. Los favoritos nativos (`ir.filters`) permanecen intactos. Se usa una tabla pequeña propia de preferencias; no hay migración automática de preferencias guardadas por versiones intermedias.
- Despachos completados por mes de finalización y porcentaje de retraso sobre despachos evaluables según el SLA original.
- Pendientes acumulados por mes de facturación del mismo año, al corte seleccionado; no son saldos históricos al cierre mensual. El rango de fechas normal sigue gobernando las tarjetas. Los gráficos usan el año de Hasta, Desde, corte o año actual y los demás filtros del tablero. Se conservan los límites de 200.000 facturas del análisis anual y se leen detalles por lotes de 2.000 al filtrar bodegas.
- En Mayores retrasos (ambas pestañas), solo la etiqueta usa `FA/` + `external_number` (campo API `Factura`), manteniendo ID, clic, destino, título interno, Factura (archivo), importación, agrupación y plazos originales. Sin valor externo, muestra `FA/SIN NÚMERO EXTERNO`.

## Instalación
1. Respaldar base de datos y filestore; probar en una copia si se aplicaron versiones intermedias del módulo base.
2. Detener Odoo. Retirar la carpeta completa del base antiguo fuera de addons; extraer el ZIP original en una carpeta limpia. NO mezclar archivos de versiones 1.8.11–1.8.20 ni desinstalar el base.
3. Extraer este ZIP como carpeta hermana `transcash_dispatch_analysis_custom`. Reiniciar Odoo y actualizar la lista de aplicaciones.
4. Si el base instalado es el original 18.0.1.8.7, instalar únicamente el personalizado (quitar filtro Aplicaciones para localizar el técnico). No requiere actualizar el módulo base. Si la base de datos tiene registrada una versión posterior, restaurar una copia compatible o validar la reversión en una copia antes de hacerla en producción; no cambiar el número de versión manualmente ni forzar una degradación. Si se completó una migración 1.8.11/12 que fusionó facturas, recuperar/validar los datos previamente.
5. Recargar navegador. Para actualizaciones futuras, actualizar solo el personalizado.

El complemento no tiene scripts de migración, hooks de instalación, cron ni cambios en `dispatch.invoice` / `dispatch.invoice.line`. No vuelve a consultar la API al instalarse. La primera consulta del tablero sí realiza las lecturas anuales necesarias para los gráficos. No se ha ejecutado Odoo/PostgreSQL real en este entorno.

Pruebas locales: `python -m unittest discover -s tests -p 'test_extension_standalone.py'` con el módulo original al lado. Usa ORM simulado y verifica datos, alcance, retrasos, numeración y objetivos XML. También se verificó el JavaScript con Node.


Actualización 18.0.1.0.1: en "Mayores retrasos" la columna "Factura / destino" muestra el valor anterior y el externo juntos, por ejemplo: FA/23245 / FA/4791.


18.0.1.0.2: compatibilidad RPC con get_active_filter_state y save_active_filter_state de assets anteriores. Ambos delegan en los métodos personalizados existentes, con las mismas validaciones y preferencias por usuario y compañía. No hay migración ni cambio de esquema. Se recomienda renovar los assets del módulo original y conservar su carpeta limpia.


### 18.0.1.0.3 — Ícono del menú principal

El personalizado asigna su imagen PNG de 256 × 256 al menú existente `transcash_dispatch_analysis.menu_dispatch_root` mediante `web_icon`. No crea otro menú ni modifica archivos del módulo base. Actualizar únicamente el personalizado y recargar la sesión web.
