# Inventario Web API — Productos, precios y bodegas (Odoo 16)

## Versión 16.0.1.17.0 — precios por bodega y un endpoint

La sincronización procesa **un endpoint activo y marcado por empresa externa**. Cada registro JSON tiene los campos:

| Campo | Acción |
|---|---|
| `codigo` | Buscar/crear el producto por SKU dentro de la empresa Odoo relacionada |
| `Nombre`, `Linea`, `Marca`, `formato`, `Peso`, `mxpallets`, `mxplaca`, `mxcaja` | Actualizar los datos del producto |
| `Precio` | **Precio público**, `product.template.list_price` |
| `Precio_2` | **Precio mayorista**, regla fija `product.pricelist.item.fixed_price` de la **lista configurada en API Administrator** |
| `StockTotal` | Referencia total y, si es cero, poner en cero las existencias del producto en las bodegas de la empresa |
| `Bodegas[].Bodega` | Resolver `stock.warehouse.code` de la empresa Odoo relacionada |
| `Bodegas[].StockBodega` | Ajustar la bodega explícita; **cero también se procesa** |

**El sufijo `/lista` ya no determina qué campo JSON se usa para cada precio.** Ambos precios se obtienen de una sola descarga, sin volver a consultar otra lista. La empresa externa continúa identificándose por `/show_inventory_web/<empresa_externa>/<lista>`, mientras que el destino Odoo se identifica por `api_administrator.company_id` (estos IDs no tienen por qué coincidir).

### Ejemplo

Un registro con `Precio: 27.7846` y `Precio_2: 22.8429` genera `list_price = 27.7846` y precio fijo **mayorista = 22.8429** para ese SKU. Si su bodega `ABS` tiene `1.92` y `NAJ` `0.96`, solo se ajustan esas bodegas. Un producto ausente de la respuesta no se pone en cero. Si `StockTotal = 0`, se conservan las reglas del módulo para llevar a cero todas las bodegas de la empresa.

### Configuración

1. Dentro de **API Administrator**, mantén solo **un** endpoint GET activo y marcado con **Inventario Web: Productos y Bodegas** para cada empresa externa. Desmarca la opción antigua **¿Es para actualización de stock?** en esa API.
2. Configura **Empresa** de Odoo y selecciona tu **lista pública ya existente** en el campo `price_list_id`. No es necesario un segundo endpoint para Precio 2.
3. **No se crean listas de precios.** Si falta una lista, o aún está seleccionada alguna `Inventario Web Mayorista - ...` creada por una versión anterior, el módulo muestra un error claro para que selecciones la lista existente. Las listas antiguas no se eliminan automáticamente porque podrían estar vinculadas a clientes o pedidos.
4. Usa el botón superior **Sincronizar** de esa API o el cron de modelo `stock.inventory.web.sync`, código `model.sync_inventory_web_products()`.
5. El cron procesa una sola API marcada por empresa; si quedaron dos antiguas marcadas, selecciona la de menor número de lista del endpoint y deja una advertencia `[INV_WEB_SYNC] ENDPOINTS_EXTRA_OMITIDOS`. Al usar el botón manual se prioriza la API cuyo formulario tiene abierto.

**No se modifica `stock_api_assing` ni `sync_all_inventory`**, que pueden permanecer para otras integraciones.

### Rendimiento, seguridad y auditoría

Búsqueda y precarga de productos, quants y tarifas por lotes de hasta 250 SKUs. Ajustes mediante procedimientos oficiales de Odoo, sin escribir directamente `stock.quant.quantity`. Cuando existen reservas, lotes o ubicaciones ambiguas, genera advertencia y evita ajustes potencialmente incorrectos. Logs en ficha de producto, lista general de sincronizaciones y `odoo.log` (`[INV_WEB_SYNC]`, `PRECIO_CAMPO`, `BODEGA`, `PROGRESO`). La duración en producción depende del volumen de productos, las ubicaciones y el coste de aplicar los ajustes.

### Actualización

Sustituir la carpeta `stock_inventory_web_sync`, reiniciar el servicio Odoo y actualizar el módulo **en la base correcta**. Revisar la empresa, lista pública existente y check de la única API elegida antes de ejecutar el cron. Probar primero en un entorno de pruebas con copia de los datos, ya que la sincronización modifica existencias y reglas de precio.

### Nueva regla de precio por bodega

`api_administrator.warehouse_id` se mantiene como `Many2one` para el resto de integraciones.
Al marcar **Inventario Web: Productos y Bodegas**, el formulario sustituye visualmente
ese campo por **Bodega Relacionada (selección múltiple)**, guardada en
`inventory_web_price_warehouse_ids`. La migración incorpora la bodega anterior
sin perderla. Selecciona una lista de precios Odoo en `price_list_id`.

- En una venta que use esa lista y una **bodega seleccionada donde la API
  relacionó el producto**, se utiliza `Precio` del JSON.
- En una venta con esa lista y cualquier otra bodega, se utiliza `Precio_2`,
  incluso cuando el producto existe también en una bodega seleccionada.
- Precio 0 **se respeta**. La ficha del producto sigue guardando `Precio` como
  precio público y `Precio_2` como precio mayorista. La lista configurada
  conserva `Precio_2` como precio base para otros flujos sin bodega de venta.
- Odoo no ofrece precios por bodega en las listas estándar: la selección se
  aplica al calcular el precio de **líneas de pedidos de venta**, usando la
  bodega de la línea de `stock_api_assing` cuando está disponible, o en su defecto
  la del pedido. No modifica precios de otras listas ni los precios de compras.
- El inventario **se sigue actualizando en todas las bodegas enviadas por la API**.
  Este selector solamente determina el precio de venta.

Requiere `sale_stock` para el almacén del pedido (se incluye como dependencia).
En variantes, al procesar un SKU solo se toma `Precio` en almacenes realmente
asociados al producto (incluidas bodegas explícitas de stock cero). Si un SKU no
aparece en el almacén elegido, utiliza `Precio_2`.

**Advertencia:** Los canales externos que consulten directamente precios de la
lista sin contexto de almacén (por ejemplo, algunas tiendas o integraciones
externas) verán el precio base `Precio_2`. Para esos canales es necesario enviar
la bodega y resolver el precio con la lógica de la venta.

## Ajuste 16.0.1.16.0

Se eliminó por completo el campo informativo `inventory_web_external_price` de API Administrator y de su vista. Se conservan el selector múltiple de bodegas, la lista de precios, el check de Inventario Web, el botón Sincronizar, el cron y la lógica de precios y existencias.

## Ajuste 16.0.1.17.0 — utilizar lista existente, sin creación automática

- Se eliminó la creación y la asignación automáticas de `Inventario Web Mayorista - ...` y de cualquier lista alternativa.
- `Precio` actualiza `product.template.list_price`; `Precio_2` crea/actualiza **reglas de precio de producto en la lista existente seleccionada**. Nunca crea una nueva lista `product.pricelist`. Una lista existente llamada `Public Pricelist` también es válida.
- Al vender con esa lista, el almacén seleccionado y vinculado al SKU aplica `Precio`; otras bodegas aplican `Precio_2` mediante la extensión de `sale.order.line`. En canales sin contexto de bodega, la lista devuelve su precio base (`Precio_2`).
- Si existe una lista autogenerada por versiones anteriores, se debe seleccionar manualmente la lista real antes de sincronizar. La lista autogenerada **no se elimina ni archiva automáticamente** por seguridad. Revisar sus clientes, reglas y pedidos antes de archivarla.
