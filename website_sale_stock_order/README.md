# Website - Ordenar productos por stock (Odoo 18)

## Qué hace

- Ordena **todo el catálogo** por stock antes de la paginación; no solamente los productos de la página visible.
- Por defecto, después de instalar, se usa **Stock: mayor a menor** en los sitios existentes.
- Incorpora al menú de ordenación **Stock: mayor a menor** y **Stock: menor a mayor**, conservando **Destacados**, precio, nombre y fecha.
- Mantiene visibles los productos con stock 0; aparecen detrás de los productos con stock positivo cuando se usa el orden de stock descendente.
- Se actualiza en cada solicitud a la tienda: no hace falta cron ni actualizar secuencias.
- Utiliza **cantidad libre** (`free_qty`: cantidad física menos reservada), en el almacén configurado en el sitio web. Si el sitio no tiene uno, utiliza los almacenes de su compañía según las reglas nativas de Odoo.
- Para plantillas con variantes, **suma el stock de las variantes almacenables**.
- No cambia stock, movimientos, reservas, fichas de productos, ventas ni la política de productos agotados.

## Instalación

1. Extrae el archivo ZIP (una sola vez); copia la carpeta `website_sale_stock_order` a la ruta de `custom-addons` que ya figura en tu `addons_path`.
2. Reinicia el servicio Odoo 18.
3. En Aplicaciones, habilita el modo desarrollador y pulsa **Actualizar lista de aplicaciones**.
4. Busca **Website - Ordenar productos por stock** e instala el módulo.
5. Entra a `/shop` en una ventana privada: debería aparecer **Stock: mayor a menor** como predeterminado.

## Cambiar el orden predeterminado por sitio

Ve a **Sitio web > Configuración > Ajustes > Tienda - Productos > Orden de productos en la tienda**. También se podrá elegir un orden específico mediante el menú «Ordenar por» del catálogo.

**Importante**: elegir **Destacados** mantiene el comportamiento nativo de Odoo (secuencia manual) y **no** coloca automáticamente los agotados al final. Para priorizar inventario, selecciona **Stock: mayor a menor**.

## Notas técnicas

- Compatibilidad objetivo: **Odoo 18.0** (Community/Enterprise), requiere `website_sale_stock` (que instala las dependencias oficiales de inventario y comercio electrónico).
- Usa `website_sale.controllers.main.WebsiteSale._shop_lookup_products()` y `_get_search_order()` de Odoo 18.0 y las selecciones nativas de `website.shop_default_sort`.
- El cálculo del inventario se realiza con **una agregación** ORM sobre `stock.quant` por solicitud del catálogo que utiliza la ordenación por stock. En catálogos muy grandes o con muchísimos visitantes simultáneos, probar el rendimiento en una copia de la base antes de activarlo en producción.
- El inventario resultante puede ser negativo para algunos artículos; el orden descendente sitúa los positivos, luego los ceros y después los negativos.
- Solo modifica el orden de `/shop`, sus categorías, búsquedas y filtros. No reordena bloques especiales del inicio creados con snippets.
- Si un visitante selecciona «Precio», «Destacados» u otra opción, se respeta su elección.
- En la desinstalación, cualquier sitio que continúe en orden por stock vuelve a **Destacados** para evitar una selección inválida.

## Comprobación rápida

1. Crea o identifica productos publicados de stock 30, 10 y 0.
2. Abre `/shop` sin parámetros de orden y revisa 30, 10, 0.
3. Verifica una categoría y una página posterior del catálogo.
4. Cambia a **Destacados** y comprueba que mantiene la secuencia manual original.
5. Realiza una reserva/entrada de stock y vuelve a abrir la tienda para comprobar el nuevo orden.
