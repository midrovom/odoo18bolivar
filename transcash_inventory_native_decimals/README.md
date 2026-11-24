# TRANSCASH | Decimales nativos de Odoo 18

**Dependencia obligatoria:** `transcash_inventory`, probado contra el paquete suministrado `18.0.1.51.0`.

Este addon NO modifica los archivos ni modelos del módulo original. Hereda sus rutas HTML (dashboard, datos importados, importación de Excel y sincronización de fotografías), conserva sus controles de acceso y les añade un puente de formato para obtener `decimal_point`, `thousands_sep` y `grouping` desde `res.lang` según `res.users.lang` del usuario conectado.

## Instalación

1. Descomprime este ZIP dentro de la carpeta de addons personalizados de Odoo, junto a `transcash_inventory` (carpetas separadas).
2. Reinicia el servicio de Odoo y actualiza la lista de aplicaciones (modo desarrollador).
3. Busca e instala **TRANSCASH | Decimales nativos de Odoo 18**.
4. En **Ajustes > Traducciones > Idiomas** configura *Separador decimal*, *Separador de miles* y *Formato de agrupación* en el idioma que utiliza el usuario.
5. Recarga el navegador (Ctrl+F5) y vuelve a abrir Inventario Inteligente.

No hay parámetros adicionales ni trabajos programados. Para cambiar el resultado se modifica el idioma del usuario o los separadores de ese idioma en Odoo.

## Ejemplos

| Configuración Odoo | Cantidad formateada (2 decimales) |
|---|---|
| decimal `.` / miles `,` / agrupación `[3,0]` | `1,234,567.89` |
| decimal `,` / miles `.` / agrupación `[3,0]` | `1.234.567,89` |
| decimal `,` / miles ` ` / agrupación `[3,2,0]` | `12 34 567,89` |
| decimal `.` / miles vacío / agrupación `[]` | `1234567.89` |

## Alcance

- Dashboard: cantidades, KPIs, porcentajes, valores monetarios y tablas que usan el formateador existente.
- Datos importados: columnas numéricas y contador de registros.
- Fotografías: contadores de productos y progreso.
- Carga de Excel: contadores de importación y tamaño del archivo.
- Exportación CSV del dashboard: usa el separador decimal elegido, sin separador de miles para preservar importación numérica. Se mantiene el delimitador de columnas `;` original.

**No modifica** valores JSON, cálculos, registros de base de datos, importación numérica de origen, archivos XLSX ni precisión decimal (número de dígitos), que siguen sus propias reglas en el módulo nativo y, para importes monetarios Odoo, en `res.currency`.

### Nota técnica

El módulo nativo carga JS sin `web.assets_backend` dentro de sus propios iframes y tiene `new Intl.NumberFormat('es-EC')` fijo. Por compatibilidad, este addon inyecta la configuración al HTML y adapta *únicamente* ese locale `es-EC` dentro del iframe; no se altera `window` del cliente web principal ni el código original. Si se reemplaza el JS del módulo principal con otra arquitectura o cambia a otro locale literal, se deberá revisar la adaptación.

## Reversión

Desinstala este addon y recarga la página para volver a los formatos originales de `transcash_inventory`; no hay cambios de datos que revertir.
