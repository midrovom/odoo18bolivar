# Website Shop - Filtrar por Precio Mostrado (Odoo 18)

## Problema

El filtro de precio nativo de `website_sale` utiliza `product.template.list_price`
para el dominio y los límites del slider. Sin embargo, las tarjetas de `/shop`
utilizan `product.template._get_sales_prices(website)` y muestran el importe
`price_reduce`, que puede ser distinto debido a la lista de precios, descuentos,
impuestos y posición fiscal.

## Funcionamiento

- Mantiene el aspecto y los controles existentes del filtro nativo.
- Selecciona productos por el importe `price_reduce` que utiliza `/shop`.
- Calcula mínimo y máximo según los productos de la búsqueda/categoría/filtros
  del catálogo, sin imponer antes el rango de precio.
- Conserva búsqueda, categorías, atributos, etiquetas, orden y paginación.
- Calcula el importe en la moneda del sitio web y lo redondea con su precisión.
- Es una extensión independiente: no modifica `website_sale`.

## Instalación

1. Descomprimir y copiar la carpeta `website_shop_display_price_filter` a la
   ruta de `custom-addons` de la instancia Odoo 18.
2. Reiniciar el servicio de Odoo.
3. Activar modo desarrollador, actualizar la lista de aplicaciones y buscar
   `Website Shop - Filtrar por Precio Mostrado`.
4. Instalar el módulo. El filtro de precio nativo debe estar habilitado en
   el editor del sitio web.

## Verificaciones sugeridas

1. Producto con `list_price=100` y precio mostrado `80`: debe aparecer en el
   rango 70-90 y excluirse de 95-110.
2. Diferentes listas de precios, monedas, impuestos y posiciones fiscales:
   utilizar siempre el precio mostrado al visitante.
3. Cambiar de categoría, marca o atributos: los extremos del filtro deben
   seguir los productos de la selección.
4. Probar paginación y búsquedas con rangos de precio.
5. Comprobar `0,00`, productos sin publicar y visitantes anónimos.

## Limitaciones importantes

- Esta implementación usa el método estándar `_get_sales_prices` de Odoo 18.
  Si el tema o un módulo personalizado presenta un precio por otro campo o
  cálculo, hay que adaptar esta extensión a dicha fuente de precio.
- Para catálogos muy grandes se aconseja probar carga/rendimiento con los
  filtros y listas de precios reales, ya que se calculan importes por producto.
- No modifica el precio del producto ni los cálculos del carrito.
- El filtro nativo redondea sus extremos a dos decimales; se mantiene ese
  comportamiento visual.
- Cambios en otros controladores de terceros que también sustituyan `shop`
  podrían requerir revisión de la cadena de herencia.
