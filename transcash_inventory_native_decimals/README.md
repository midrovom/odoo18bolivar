# TRANSCASH | Decimales nativos de Odoo 18

**Versión 18.0.1.1.0** · Complemento instalable para **transcash_inventory 18.0.1.51.0**.

Usa `res.users.lang` / `res.lang` (`decimal_point`, `thousands_sep`, `grouping`) en las páginas HTML del módulo base, en el CSV del dashboard y, ahora, también en las descargas de archivos **Excel XLSX**.

## Qué corrige esta actualización

La versión anterior solo cambiaba los separadores del dashboard y de un CSV. Las exportaciones **.xlsx** se generaban directamente en Python, usando números OpenXML independientes del idioma de Odoo. Los separadores de Excel dependen del Excel instalado en el equipo, no de Odoo: no es posible forzarlos con el formato numérico sin perder independencia del lector.

Para asegurar que el usuario *vea* el idioma de Odoo en los XLSX, el complemento añade **dos hojas** a las exportaciones de:

- **Exportar a Excel** en las tablas del dashboard;
- **Exportar a Excel** en datos importados (productos, ventas, compras, proveedores y stock);
- **Exportar a Excel** en respuestas del asistente ChatGPT.

**Primera hoja: `Formato Odoo`**. Todos los valores numéricos se presentan como *texto localizado* siguiendo la configuración nativa del idioma del usuario, por ejemplo `1.234,56` o `$1.234,56`. Se mantienen encabezados, tablas y texto sin alteraciones. Esta hoja es una presentación/consulta visual: el texto no debe utilizarse directamente para fórmulas numéricas.

**Segunda hoja: `Datos numéricos`**. Es la hoja original del módulo base, *sin modificar celdas ni sus valores*: números auténticos para sumar, filtrar, ordenar, graficar, crear tablas dinámicas o procesar con otros sistemas. La representación de esta hoja sigue dependiendo de la configuración regional del Excel del equipo.

El complemento **no modifica la base de datos, los cálculos, el contenido JSON de las API, las importaciones ni los archivos XLSX de entrada**. No se crea ningún parámetro nuevo. Las mismas reglas de permisos y CSRF del módulo base siguen vigentes.

## Cómo actualizar si ya tienes la versión anterior

1. **Conserva** instalado `transcash_inventory` (el módulo principal no cambia).
2. Reemplaza la carpeta `transcash_inventory_native_decimals` por la carpeta de este ZIP (sin duplicarla con otro nombre).
3. Reinicia Odoo 18.
4. En **Aplicaciones**, busca **TRANSCASH | Decimales nativos de Odoo 18** y presiona **Actualizar**. Si es una primera instalación, actualiza la lista de aplicaciones e instálalo.
5. Configura el idioma del usuario en Odoo y sus separadores desde **Ajustes > Traducciones > Idiomas**.
6. Recarga el dashboard con `Ctrl + F5` y genera una **nueva** exportación Excel; los archivos exportados previamente no se modifican.

Ejemplo: con decimal `,`, miles `.` y agrupación `[3,0]`:

| Valor original | Hoja Formato Odoo | Hoja Datos numéricos |
|---|---|---|
| 1234567.89 | 1.234.567,89 | número 1234567.89 |
| -1200.6 | -1.200,60 | número -1200.6 |

**Limitación deliberada:** en la hoja `Formato Odoo`, los números son texto para garantizar el formato visual incluso si Windows/Excel tiene separadores distintos. Si necesitas operaciones con números reales, utiliza `Datos numéricos`. No conviene modificar el punto decimal dentro del XML numérico de XLSX porque el archivo dejaría de ser portable o válido.

## Verificación técnica

- Reutiliza los controladores originales (los endpoints XLSX llaman primero a `super()`).
- Utiliza una transformación incremental de XML para convertir solo la primera hoja, sin volver a leer tablas SQL ni cambiar los datos originales.
- Admite agrupación Odoo y las monedas/porcentajes en los formatos de la versión del módulo suministrada.
- `node tests/test_native_decimals.js` valida la pantalla y el CSV.
- `TRANSCASH_MODULE_DIR=/ruta/al/transcash_inventory python tests/test_xlsx_export.py` valida las dos hojas usando los exportadores originales, con puntos, comas, signos, símbolos monetarios y precisión.

## Reversión

Desinstala el complemento para regresar a los formatos del módulo principal. No se modifica ningún registro persistente.
