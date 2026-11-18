# Analytics Sales — Odoo 18 Community

**Versión: 18.0.1.1.84** · Migración de `analytics_sales` 16.0.1.1.84.

## Instalación y actualización en Odoo 18

1. Haga una copia de seguridad de la base y del directorio de addons. Extraiga este ZIP en el directorio de addons personalizados, conservando el nombre `analytics_sales`.
2. Reinicie la instancia de Odoo 18 y actualice la lista de aplicaciones. Instale Analytics Sales si no existe en la base de destino; si ya existe, actualice el módulo (`-u analytics_sales`). No desinstale el módulo existente para actualizarlo.
3. Asigne explícitamente el grupo Analytics Sales / Administrador a un usuario interno. Abra Administración → Configuración API y seleccione o verifique las tres APIs de la compañía. API Administrator debe estar disponible y ser compatible con Odoo 18 para sincronizar; sigue siendo una integración opcional, no una dependencia obligatoria.
4. Verifique los perfiles Tienda, Supervisor y Administrador, establecimientos, metas, bodegas y el dashboard. Recargue los assets del navegador (Ctrl+F5).

Ejemplo desde el entorno virtual y directorio de su instancia Odoo 18, con el servicio detenido:

```bash
./odoo-bin -c /ruta/odoo18.conf -d BASE_PRUEBAS -i analytics_sales --stop-after-init
# Si ya está instalado, sustituir -i por -u.
# Pruebas en una base aislada:
./odoo-bin -c /ruta/odoo18.conf -d BASE_PRUEBAS -u analytics_sales --test-enable --test-tags /analytics_sales --stop-after-init
```

## Cambios de compatibilidad

- Vistas `list`, acciones `list,form`, modificadores directos y columnas ocultas con `column_invisible`.
- `ir.cron`: retirados `numbercall` y `doall` tanto del XML como de los métodos de configuración. Se mantienen XML IDs, creación `noupdate`, frecuencia anual (00:00 Ecuador), mensual (cada dos horas) y bodegas (cada día), así como selección persistente por compañía y actualización manual de las tres APIs.
- Dashboard OWL: importación de `rpc` y `user` desde los módulos nativos de Odoo 18. Se mantiene la URL única de consulta y el contexto del usuario/compañía, sin temporizadores de navegador.
- ORM: nombre visible de bodegas con `_compute_display_name`, seguridad de bodegas con `_check_access` y verificación de establecimiento con `check_access`. ACL y reglas originales conservadas. Dependencia nativa `html_editor` para los reportes HTML de metas/establecimientos.
- Se conservan nombres técnicos, modelos, campos, contratos API, fórmulas, datos de instalación y lógica funcional de 16.0.1.1.84. Los assets históricos no activos y los scripts de migraciones 16.0 originales se mantienen como referencia; no se ejecuta una migración de registros entre bases distintas con este ZIP.

## Validación y alcance

Se comprobaron estáticamente Python, XML, JavaScript y estructura del ZIP. Se mantienen las pruebas de Odoo y se añaden pruebas de nombre visible y acceso ORM de bodegas. No se dispone de servidor Odoo 18/PostgreSQL ni del módulo API Administrator de destino en este entorno: las pruebas ORM, la instalación, la compilación OWL real y las conexiones API requieren validación en una base Odoo 18. La migración de toda una base Odoo 16 a 18 o la transferencia de registros entre bases es un proceso separado; los IDs de API deben verificarse en la base de destino.

---

# Historial y documentación de la versión Odoo 16 (referencia)

Los apartados siguientes se conservan literalmente como historial; para instalar o configurar Odoo 18 prevalecen las instrucciones anteriores y el código actual.

# Analytics Sales — Inteligencia Comercial para Odoo 16 Community

Módulo independiente: **`analytics_sales`**. Dashboard OWL responsive con el estilo oscuro del prototipo HTML Analytics Sales, base histórica opcional de `analisis Analytics Sales(1).xlsx` y sincronización con el módulo existente **API Administrator**.

## Qué incluye

- Tres roles: **Tienda**, **Supervisor**, **Administrador**.
- Asignación **usuario × compañía × rol × locales `nlocal` autorizados**.
- Tienda y supervisor: únicamente sus locales, sin costos, margen o utilidad.
- Administrador: todos los locales de su compañía, costos y rentabilidad.
- Filtros por `nlocal`, línea, marca, vendedor, fecha y ámbito todas las líneas/Moda (filtro opcional heredado). La vista inicial muestra todas las líneas.
- Contadores de **facturas FA distintas** y notas DE distintas; FA suma, DE resta.
- Análisis de unidades FA, unidades DE, unidades netas, ventas, ticket, unidades/factura, vendedores, locales, marcas, productos, devoluciones, ABC y velocidad comercial.
- Sincronización manual / cron cada 2 horas opcional, por compañía.
- Diario de sincronizaciones y actualización por corte completo sin duplicados.
- Carga manual de cualquier Excel de ventas con columnas compatibles, seleccionado por el usuario en Odoo. No se incluye ningún histórico en el ZIP ni se requiere conectar la API para importar.

## Instalación

1. Extraiga el ZIP en el directorio de *addons personalizados* de su **Odoo 16** (debe quedar una carpeta `analytics_sales` con `__manifest__.py`).
2. Configure ese directorio en `addons_path` del servicio Odoo y reinicie el servicio.
3. Odoo → Aplicaciones → **Actualizar lista de aplicaciones** → instalar **Analytics Sales | Inteligencia Comercial**.
4. Entre con el administrador técnico de Odoo, vaya a **Analytics Sales → Administración → Configuración API**.
5. Para ensayar con datos de demostración, vaya a **Importar Excel**, seleccione el archivo Excel que quiera analizar y pulse **Importar archivo**. Puede usar el IDR adjunto u otro archivo compatible. No hay datos integrados ni carga automática; compruebe la compañía activa.
6. Abra **Locales** para verificar los locales recibidos; vaya a **Usuarios y permisos**, seleccione usuario, rol y locales autorizados.
7. En API Administrator existente, configure el endpoint del ERP de facturación de su empresa. Registre el **nombre del endpoint existente** en Configuración API y pulse **Guardar configuración**.
8. Pulse **Sincronizar ahora**. Si el endpoint devuelve un corte completo válido, desde ese momento el dashboard utiliza la API en lugar de los datos importados desde Excel.
9. Active **Sincronización automática cada 2 horas**, si lo desea.

### Instalación por consola (opcional)

```bash
# Sustituya rutas de ejemplo y nombre de base por los reales:
unzip Analytics_Sales_Odoo16_v1_1.zip -d /ruta/addons_custom/
# Reiniciar servicio Odoo 16 conforme a su instalación.
# En modo de mantenimiento:
./odoo-bin -c /ruta/odoo.conf -d BASE_ODOO -i analytics_sales --stop-after-init
```

**Nota:** este ZIP no sustituye ni instala API Administrator, ni almacena nuevas credenciales. El módulo puede instalarse sin API Administrator para visualizar el histórico. La sincronización requerirá que el modelo `api.administrator` exista.

## Contrato de API ERP (GET, corte completo)

En el módulo existente API Administrator debe registrarse una entrada que identifica el endpoint, la URL, el path y las credenciales. En esta aplicación solo se configura el **nombre de esa entrada**.

Formato de respuesta esperado: arreglo de objetos o estructura `{ "data": [ ... ] }`, `{ "result": { "rows": [ ... ] } }` o `{ "items": [ ... ] }`.

```json
{
  "data": [
    {
      "Tipo": "FA",
      "numero": "2601",
      "FechaFactura": "2026-02-26",
      "nlocal": "Tienda Centro 001-001",
      "Codvendedor": "V01",
      "Vendedor": "Ejemplo Vendedor",
      "Codproducto": "SKU001",
      "Producto": "Ejemplo de calzado",
      "Marca": "Ejemplo Marca",
      "Linea": "CALZADO",
      "Cantidad": 2,
      "Total_neto": 40.00,
      "Total_Costo": 26.00,
      "id_linea": "2601-1"
    }
  ]
}
```

**Campos mínimos:** `Tipo` (`FA`/`DE`), `numero`, `FechaFactura`, `nlocal`, `Codproducto`, `Cantidad`, `Total_neto`. `Total_Costo` es recomendado y obligatorio si se requiere rentabilidad válida; si falta, el dashboard administrativo mostrará **N/D** en los totales con costos incompletos. `id_linea` es recomendado para identificar líneas de forma estable. Se admiten variantes frecuentes de escritura de campos (véase `models/sync.py`).

El importe `Total_neto` y `Total_Costo` se interpreta como **valor de la línea completa**, no unitario. En caso de varias líneas con mismo SKU dentro de una factura, envíe un `id_linea` distinto. `DE` se envía positivo o negativo: se guarda valor absoluto y se resta en la analítica.

**Corte completo requerido:** el endpoint debe devolver todas las líneas que deben existir en la base analítica de la compañía. Los registros que ya no aparezcan en un corte válido se eliminan de la vista API; no use este procedimiento para un endpoint incremental. Ante HTTP/JSON inválido o cero filas, se conserva el último corte. Cada corte se actualiza dentro de una misma transacción de Odoo.

### Cómo se conecta con el API Administrator existente

En otras instalaciones del grupo se han observado **dos contratos**:

1. Modelo con método `call_api(endpoint, method='get', company_id=...)`. Si existe, se utiliza ese contrato directamente.
2. Modelo que **solo almacena la configuración**, con campos `url`, `end_point`, `user_id`, `password`. Se busca la definición activa por nombre y compañía, se unen URL y path y se envía un GET con las cabeceras `user_id`/`password`, siguiendo el patrón documentado del módulo previo de comisiones.

Ambas variantes están concentradas en **`models/sync.py`, método `_fetch_api()`**. **No fue posible verificar aquí la versión exacta del módulo API Administrator instalado en el Odoo 16 de destino**; si usa otros nombres de campos/cabeceras, adapte solo este método al código real de referencia antes de probar en producción. No se inventa una API nueva ni se replican tokens en configuraciones Analytics Sales.

### Recomendaciones operativas

- **FA únicas:** clave lógica de conteo `nlocal + Tipo + numero`. Se cuentan una sola vez por factura, sin importar sus líneas. En los desgloses por marca/vendedor una misma factura multicomponente puede aparecer en varios grupos; **no se deben sumar los conteos de grupos para obtener el total**.
- **Margen bruto:** (venta neta − costo neto) / venta neta, y solo cuando se conocen todos los costos del filtro.
- **ABC:** clase A hasta 80% de aporte a ventas, B hasta 95%, C resto (SKU con venta neta positiva); velocidad de venta = unidades netas/días calendario. No equivale a rotación de existencias.
- **Productividad:** `FA/día con FA` no significa productividad por turno: no hay horas laboradas ni turnos en el origen.
- **Devoluciones:** las DE pueden corresponder a ventas de períodos anteriores; no convertir la tasa del período en tasa de devolución por cohorte sin vínculos al documento de origen.
- **Rendimiento:** 7.632 líneas se procesan del lado servidor en cada consulta, sin exponer líneas ni costos al cliente comercial. Para cientos de miles o millones de líneas, será necesario añadir agregación SQL/materializada y carga por páginas.
- **Respaldo:** haga respaldo PostgreSQL y pruebas de permisos, empresa y endpoint en una copia de la base antes de instalar en producción.

## Seguridad

Se utiliza un servicio RPC (`analytics.sales.dashboard.get_dashboard`) que **verifica la compañía activa, el rol y los locales autorizados en el servidor**, construye los agregados y no envía campos de costo a tienda/supervisor. Los modelos de movimientos no conceden acceso ORM directo a tienda ni supervisor. La configuración y los logs solo son accesibles a administrador; los cambios de usuarios validan compañía activa. Los permisos y filtros no están definidos por el navegador.

**Actualización desde la versión antigua:** al cambiar el identificador técnico de `idr_moda_analytics` a `analytics_sales`, Odoo lo considera un módulo distinto. Si ya instaló la versión anterior, no instale ambos en producción sin migración de modelos, datos, parámetros y permisos. Respaldar primero.

**Limitación de pruebas:** se verificaron sintaxis de Python, XML y JavaScript, estructura del ZIP y un test de cálculo con datos del Excel. **No se ha instalado ni validado funcionalmente en un servidor Odoo 16 ni se ha probado contra API Administrator real** desde este entorno.

## Corrección 16.0.1.1.1 — OWL + Excel IDR de demostración

- Corregido el error `TypeError: ctx.String is not a function` en el selector de local, pasando la comparación a `isLocalSelected()` del componente JavaScript.
- La versión anterior utilizó `data/initial_snapshot.json.gz` (ya **eliminado del módulo** desde 16.0.1.1.2) para datos IDR de prueba; ahora se selecciona cualquier Excel compatible directamente desde Odoo.
- El botón de demostración anterior se reemplazó por la carga manual de un Excel seleccionado. La opción Reemplazar solo modifica `historico` de la compañía activa y **no elimina movimientos `api`**. Cuando exista un corte API con datos, este tiene prioridad automáticamente.
- Para actualizar un módulo ya instalado: copie el nuevo ZIP sobre el código del módulo, reinicie Odoo, actualice la aplicación y recargue el navegador con Ctrl+F5; luego use el botón de carga de Excel en Configuración API. Respaldar la base antes de actualizar.
- Verificación fuera de servidor: JSON y estructura Excel, validación de campos obligatorios, XML, JS y sintaxis Python. Sin prueba en la instancia real de Odoo del usuario.

## Versión 16.0.1.1.2 — Selección libre de archivos Excel

**Esta versión reemplaza el histórico de demostración integrado**. Ya **NO contiene** `data/initial_snapshot.json.gz` ni incorpora el archivo Excel original o sus datos. Ahora el administrador puede cargar archivos propios desde:

- **Analytics Sales → Administración → Importar Excel**, o
- **Analytics Sales → Administración → Configuración API → Importar Excel**.

Seleccione el archivo `.xlsx` (admitido de forma nativa) o `.xls` (necesita instalar la librería Python `xlrd` en el servidor Odoo), y opcionalmente el nombre de la hoja. Si se deja vacío, se detecta automáticamente una hoja con encabezados compatibles. Se aceptan encabezados con distintas mayúsculas, acentos y algunos sinónimos, aunque la estructura de los datos debe conservar los campos mínimos descritos abajo.

**Campos mínimos:** `Tipo`, `numero`, `FechaFactura`, `nlocal`, `Codproducto`, `Cantidad`, `Total_neto`. El módulo reconoce fechas Excel serializadas, fechas ISO o las formas `dd/mm/aaaa` y `dd-mm-aaaa`. Campos adicionales recomendados: `Total_Costo`, `costo`, `Vendedor`, `CodVendedor`, `Linea`, `Marca`, `Producto`, `Factura`, `id_linea`. El costo unitario se multiplica por la cantidad solo si falta `Total_Costo`. Si falta `Codproducto` o una fórmula de Excel devuelve un error en esa columna, pero existe `Producto`, se usa un código temporal estable `SIN-CODIGO-...` basado en la descripción y se avisa al importar. Si también falta la descripción, se rechaza el archivo indicando la fila problemática.

**Elegir modalidad al importar:**

- **Agregar/actualizar (predeterminada):** retiene las líneas históricas anteriores; identifica coincidencias de contenido, IDs de línea y líneas únicas por factura/local/SKU para actualizar sin duplicados reconocibles. Si un documento tiene múltiples líneas de igual SKU y hay cambios, incluya `id_linea` para poder distinguirlas inequívocamente.
- **Reemplazar:** convierte el Excel seleccionado en el nuevo corte completo del histórico Excel de la compañía activa y descarta líneas históricas que no estén en el archivo. **No elimina movimientos originados por la API**, que continúan siendo fuente prioritaria del dashboard cuando existan.

Las cargas son transaccionales: si una línea es inválida no se aplica un corte parcial. Archivos: máximo 30 MB comprimidos, 350.000 filas. Se guardan nombre de archivo, hoja, modo y totales en **Historial de sincronización**. No se necesita API Administrator para importar.

**Actualización desde 16.0.1.1.1:** no se borran automáticamente los registros de demostración que ya se hubieran cargado a la base de datos. Si desea quitar esos registros y poner otro archivo, seleccione la modalidad **Reemplazar** en la primera importación. La importación **Agregar/actualizar** trata de reutilizar líneas idénticas del viejo histórico sin duplicarlas.

La sincronización API sigue funcionando independientemente y mantiene su comportamiento de corte completo. Esta versión conserva la corrección de OWL `ctx.String` de la versión anterior.


## Versión 16.0.1.1.3 — Registro del modelo de importación y actualización segura

Esta versión mantiene el selector de archivos Excel de la 16.0.1.1.2 (no incluye ningún Excel ni datos de prueba). Refuerza el orden de importación Python del asistente `analytics.sales.excel.import` y utiliza la referencia explícita del modelo en las dos reglas `ir.model.access.csv`.

**Error de actualización: `No se han encontrado registros coincidentes para id. externo model_analytics_sales_excel_import`.** La clase Python existe en `models/import_wizard.py`; si la versión anterior se estaba ejecutando al copiar el código, el proceso Odoo antiguo aún no la había importado y la actualización desde la interfaz fallaba al llegar a los accesos.

**Pasos obligatorios en el servidor Odoo 16 (respaldar la base primero):**

1. Descomprimir este ZIP y reemplazar la carpeta `analytics_sales` completa en la ruta de addons personalizada efectiva. Mantener los permisos de lectura para el usuario del servicio.
2. Reiniciar **todos los procesos que atienden esa instancia Odoo**, incluidos workers si los hay. Por ejemplo, si se llama `odoo16`: `sudo systemctl restart odoo16` (verificar antes el nombre real con `systemctl list-units --type=service | grep -i odoo`). Si se usa Docker u otra instancia, reiniciar allí.
3. **Solo después del reinicio**, actualizar `Analytics Sales` desde Aplicaciones (activar modo desarrollador si es necesario). No desinstalar el módulo.
4. Actualizar el navegador con `Ctrl+F5` y entrar en Analytics Sales → Administración → Importar Excel.

**Verificación opcional en Odoo shell:** dentro de la instancia y base correctas, con el entorno de Odoo cargado, `env.registry.get('analytics.sales.excel.import')` debe devolver una clase, no `None`. Si es `None`, verificar que se copió en la ruta addons activa el nuevo `models/import_wizard.py` y que el servicio realmente se reinició. Revise el log de arranque para detectar fallos de importación de Python.

No se modificó el modelo de movimientos, no se borran datos antiguos y se mantienen ambos modos de importación (agregar/actualizar y reemplazar solo histórico Excel), además de la sincronización API independiente.

## Versión 16.0.1.1.4 — Scroll invisible en el panel

Se habilitó el desplazamiento vertical del panel de Analytics Sales dentro de la vista de Odoo 16: con la rueda del mouse/trackpad en escritorio y deslizando el dedo en móviles. Las barras de desplazamiento del panel, los rankings, las tablas y la evolución mensual se mantienen invisibles, pero las zonas siguen siendo desplazables.

El ajuste está limitado al archivo `static/src/css/dashboard.css` y al número de versión. No cambia los modelos, las métricas, la carga manual de Excel, la API, los permisos ni los datos almacenados. Tras copiar la nueva carpeta en addons, reiniciar el servicio Odoo 16 y actualizar el módulo, recargar el navegador con Ctrl+F5 para renovar los assets.


## 16.0.1.1.5 — diseño IDR Moda HTML integrado
- Dashboard OWL rediseñado a partir del prototipo visual IDR Moda (tarjetas, filtros, tendencias SVG, ranking, facturación, alertas, ABC, devoluciones y rentabilidad).
- Conexión con los agregados seguros existentes de Odoo; sin datos de prueba incrustados ni dependencia de CDN.
- Botón Abrir Excel que ejecuta el asistente de importación ya existente (solo Administrador).
- Perfil real Odoo, en lugar de simulación de perfiles del HTML. Costos no se entregan a roles de venta.
- Se conservan exportación CSV, sincronización API y scroll vertical invisible.

## 16.0.1.1.6 — perfiles + selectores oscuros

- Se respeta el perfil de Analytics Sales de la compañía, incluso cuando el usuario también es administrador técnico de Odoo. Administradores técnicos sin perfil explícito conservan acceso de configuración inicial.
- Perfil Tienda: solo un nlocal autorizado por consulta; cuando tiene varios asignados los puede seleccionar individualmente. Perfil Supervisor: comparación exclusiva de los locales autorizados, sin costos. Perfil Administrador: todas las tiendas y rentabilidad, con costos solo cuando se dispone de ellos.
- Tablas con contenido diferenciado como el prototipo HTML: vendedores para Tienda, comparativo nlocal para Supervisor, rentabilidad para Administración; aporte por marca para perfiles sin costos.
- Los cuatro filtros desplegables usan un menú oscuro nativo del dashboard (incluidas opciones, resaltados y desplazamiento móvil), sin popup blanco del navegador.
- No modifica modelos de movimientos, importación Excel ni sincronización. No incluye datos de demostración.


## 16.0.1.1.7 — Cron de ventas anuales y mensuales

- **Cron 1**: `Analytics Sales | Ventas anuales |` invoca el endpoint de API Administrator `ventas_anuales` todos los días a medianoche de Ecuador (`America/Guayaquil`, 05:00 UTC).
- **Cron 2**: `Analytics Sales | Ventas mensuales |` invoca `ventas_mensuales` en las horas locales 00, 02, 04, 06, 08, 10, 12, 14, 16, 18, 20 y 22. Odoo puede iniciar las tareas con un pequeño retraso según sus workers y carga.
- Se desactiva el cron anterior `Analytics Sales | Sincronización ERP cada 2 horas` durante la actualización. El método antiguo permanece sin operación para evitar ejecuciones duplicadas.
- La configuración es independiente por compañía desde **Analytics Sales → Administración → Configuración de API** (nombres de endpoints y dos casillas de activación). Para base de una sola compañía, ambos quedan habilitados en la primera instalación/actualización; para multiempresa se hereda activación previa o se habilitan las empresas con endpoints específicos, y las demás necesitan activación manual.
- **Conservación de datos**: los dos cortes API comparten la misma base de movimientos `api`, usan modalidad **agregar/actualizar** en lugar de borrado de corte completo. Un endpoint no elimina registros que solo aparezcan en el otro. Se mantiene la carga Excel separada y el dashboard prioriza API.
- **Historial de sincronización** registra nombre de endpoint, éxito o error, filas leídas, insertadas y actualizadas, por empresa. Excepciones y JSON vacío no alteran los movimientos existentes.
- **Contrato requerido**: ambos endpoints deben responder un arreglo JSON de líneas de ventas con `Tipo` (FA/DE), `numero`, `FechaFactura`, `nlocal`, `Codproducto` (o `Producto`), `Cantidad` y `Total_neto`. Los campos adicionales `id_linea` y `Total_Costo` son recomendables. Un `id_linea` único y estable por línea dentro de cada comprobante permite deduplicar de manera más confiable cambios de importe y cantidad. Para otros esquemas JSON, se debe adaptar normalización después de revisar una respuesta real.
- Ejecutar `Sincronizar ventas anuales ahora` y `Sincronizar ventas mensuales ahora` para validar conexión antes del primer ciclo programado; no hemos podido consultar su API Administrator real en este entorno.
- **Instalación segura**: respaldo, reemplazar código de `analytics_sales`, reiniciar Odoo, actualizar aplicación y verificar en Ajustes → Técnico → Automatización → Acciones planificadas que estén los 2 cron activos; revisar que el anterior esté inactivo.

## Versión 16.0.1.1.8 — Asociación robusta de dos cron con API Administrator

- `Analytics Sales > Administración > Configuración API`: seleccionar desde la lista **API de ventas anuales** y **API de ventas mensuales**. Cada opción es un registro existente de `api.administrator`, mostrado con su **ID**. No crear APIs ni endpoints desde Analytics Sales.
- Pulsar **Guardar vínculos de API**. Se guarda `analytics_sales.api_annual_id.<company_id>` y `analytics_sales.api_monthly_id.<company_id>` en `ir.config_parameter`, además del estado de cada cron. Cada ejecución recupera la API por el mismo **ID** y utiliza el nombre que tenga *en ese momento*. Renombrar `ventas_anuales` a `ventas`, por ejemplo, no cambia el ID ni la relación. Sí debe volver a seleccionar si el registro es eliminado y recreado (ID diferente).
- El botón **Verificar APIs seleccionadas** informa las relaciones **guardadas** (sin hacer llamadas). Los botones de **Sincronizar ahora** invocan la API y producen un historial con nombre, ID, fecha, cantidad y errores. El ID aparece además en el listado de historial.
- Migración desde 16.0.1.1.7: durante la actualización se buscan los nombres antiguos una sola vez; si coinciden **exactamente** con un registro activo para la compañía, se almacena su ID. Si existen homónimos, o el registro ya cambió de nombre, por seguridad no se adivina: hay que seleccionarlo manualmente en Configuración API.
- Si está deshabilitada una API, la consulta falla con un mensaje explícito. La UI sigue accesible para corregir la selección.
- Se respetan los horarios programados del paquete anterior (anual: medianoche en Ecuador, mensual: cada 2 horas), otras compañías, controles de acceso al dashboard, Excel y lógica de mezcla de ventas.


## Actualización 16.0.1.1.9 — facturado, devuelto y neto en las vistas

- En los rankings de **líneas, marcas, vendedores y velocidad de venta**, cada fila identifica el importe **Facturado FA**, **Devuelto DE**, **Neto vendido** y **Vendido FA** en unidades, además de conservar su barra y valor principal.
- Se añadió la facturación FA y el importe devuelto DE al resumen principal.
- Las tablas de vendedores, productos, locales y marcas presentan columnas adicionales para facturación FA, devoluciones DE y unidades vendidas antes de devoluciones, sin alterar su cálculo de venta neta.
- Definiciones: **Facturado FA** = suma de importes FA; **Devuelto DE** = suma de magnitudes DE; **Venta neta** = FA − DE; **Vendido FA** = unidades facturadas antes de devoluciones; **Unidades netas** = unidades FA − unidades DE.
- Cambio exclusivamente de frontend: no modifica los métodos RPC, seguridad de los perfiles, crons, configuración API, importación Excel ni registros existentes.
- Los rankings conservan desplazamiento sin barra visible; los datos adicionales se adaptan al ancho del navegador.


## Versión 16.0.1.1.10 — Valores visibles EN las tres tarjetas del ranking

- **Marcas más vendidas, Vendedores destacados y Mayor velocidad de venta:** cada renglón del ranking ahora exhibe sin hacer clic ni abrir otra tabla cuatro importes/cantidades, con etiquetas claras: **Vendido FA (unidades)**, **Facturado FA (USD)**, **Neto vendido (USD)** y **Devuelto DE (USD)**. En productos se conserva además velocidad comercial (uds./día).
- Las barras siguen ordenadas como antes (neto para marcas y vendedores, unidades netas/día para productos). Los valores son agregados reales recibidos del backend para el perfil y filtros activos.
- Los listados ya no se recortan en una zona de scroll interior; crecen con el dashboard para verse con el desplazamiento general invisible con mouse o dedo.
- Se renombraron los 3 archivos de assets en el manifest (`dashboard_v110.css`, `dashboard_v110.js`, `dashboard_v110.xml`) para forzar una nueva compilación y evitar presentar el diseño anterior en caché. El nombre lógico de plantilla OWL y la acción de cliente permanecen iguales.
- No se modifican métodos Python, conexión API Administrator, cron, importador Excel, filtros, perfiles, reglas de acceso ni datos almacenados.
- Después de actualizar el módulo: reiniciar Odoo, pulsar **Actualizar** en Aplicaciones y hacer **Ctrl+Shift+R**. Revisar que la versión instalada sea `16.0.1.1.10`.


## Versión 16.0.1.1.11 — unidades devueltas en rankings

- **Ventas por línea de producto**, **Marcas más vendidas**, **Vendedores destacados** y **Mayor velocidad de venta**: ahora muestran seis datos por registro: Facturado FA (USD), Devuelto DE (USD), Neto vendido (USD), Vendido FA (unidades), Unidades devueltas DE y Unidades netas.
- **Líneas con más devoluciones**: agrega las unidades devueltas DE junto al importe.
- Tablas comerciales: incorporan columna de Unidades devueltas DE donde se presentan las unidades de venta, sin modificar el origen de datos.
- Diseño responsive: detalle completo sin desplazamiento interior oculto; el dashboard mantiene su scroll general invisible.
- Sin cambios en modelos, cálculos, cron de ventas anuales/mensuales, API Administrator o importación manual de Excel.
- Assets versionados `dashboard_v111` para evitar caché de Odoo tras la actualización.


## v16.0.1.1.12 - JSON nativo de API Administrator (IDR)

- Ambas acciones programadas (ventas_anuales 00:00 Ecuador y ventas_mensuales cada 2 horas) pueden recibir el JSON `{"success":true,"data":[...]}` con `clave`, `Tipo`, `numero`, `Factura`, `FechaFactura` (YYYY.MM.DD), `nlocal`, `Codvendedor`, `Vendedor`, `Codproducto`, `Producto`, `Linea`, `Marca`, `Cantidad`, `Total_neto` y `Total_costo`.
- `clave` se usa como identificador estable del movimiento en ambas APIs; ante una clave repetida dentro de la misma respuesta se preservan las dos ocurrencias (sin error ni duplicar en la siguiente carga idéntica). Las repeticiones se advierten en el historial de sincronización. Para actualizar individualmente dos líneas que comparten la misma `clave`, el proveedor debe agregar un verdadero `id_linea` único por detalle.
- Número de documento de API 5377 se almacena como FA-5377, o DE-128 si es devolución; la importación de Excel no cambia.
- `Cantidad`, `Total_neto` y `Total_costo` aceptan cadenas decimales con signo; las DE negativas se normalizan a magnitudes absolutas y se restan una sola vez en el dashboard.
- Fecha con puntos, espacios sobrantes, líneas vacías y vendedor vacío se normalizan. Costo cero proporcionado explícitamente se conserva como cero; revisar su fiabilidad con el origen antes de interpretar márgenes.
- No se incluyen los 1.180 movimientos del JSON dentro del módulo ni se cambian las credenciales, selección de APIs, cron, perfiles o importación Excel.


### v16.0.1.1.13 — clave IDR única
- La clave de cada línea API es su identidad estable, independientemente de local, fecha o endpoint.
- Filas idénticas repetidas por la API se procesan una sola vez; duplicados con valores conflictivos detienen el lote y generan error explicativo.
- Al actualizar, se consolidan líneas históricas idénticas repetidas por versiones antiguas, manteniendo Excel separado.
- Los cron anual y mensual continúan haciendo upsert sin borrar históricos.


## 16.0.1.1.14 — Actualización periódica de datos API

- Cada cron vuelve a consultar su registro seleccionado en API Administrator. La tabla de movimientos es un *snapshot de lectura* que se actualiza por `clave`, no un histórico inmutable. Cantidades, precios, costos, vendedor, local, marca, línea y demás campos se sobrescriben cuando el ERP devuelve valores nuevos.
- Todas las claves devueltas quedan marcadas con `api_last_checked_at` y `api_last_checked_kind`, incluso cuando sus valores comerciales no cambian. Historial indica cuántas claves se consultaron y cuándo finalizó cada sincronización.
- Las APIs de ventas anuales y ventas mensuales siguen a las 00:00 (Ecuador) y cada dos horas, respectivamente. **No son conexión instantánea continua**: los datos cambian al ejecutar los cron o la sincronización manual.
- El dashboard vuelve a leer los datos almacenados por Odoo cada 120 segundos mientras está abierto y al volver a la pestaña. **No consulta las APIs externas cada 120 segundos**.
- Los filtros de 30 días, 90 días y Año siguen la última fecha disponible para mostrar también registros de nuevas fechas sin tener que reiniciar el navegador. Los rangos personalizados permanecen fijos.
- Compatible con una indicación de anulación explícita del origen (`anulado=true`, `activo=false` o `estado=anulado`), que excluye la línea del panel sin borrar su identificador. Una activación posterior vuelve a incluirla.
- **Importante**: no se infieren anulaciones a partir de claves ausentes en una respuesta: una API mensual puede devolver un período parcial y borrar indiscriminadamente lo ausente corrompería el histórico anual. Para reconciliar borrados por ausencia, la API debe declarar que envía un corte completo y el período exacto.
- Mantiene aislados los datos importados desde Excel y los permisos de los tres perfiles.


## 16.0.1.1.15 — Acceso exclusivo por grupos Analytics Sales

- El módulo solamente es visible para usuarios con grupos Analytics Sales: Administrador, Supervisor o Tienda. Los permisos técnicos de Ajustes (`base.group_system`) ya no abren el dashboard ni la configuración.
- El acceso RPC valida siempre el grupo real; los perfiles por compañía conservan el control de nlocal y prevalecen cuando un usuario tiene roles distintos entre compañías.
- Se eliminan los ACL técnicos de versiones previas tanto en instalaciones nuevas como durante la actualización de instalaciones existentes. Los menús se reescriben para quitar los permisos heredados.
- Para empezar, desde Ajustes > Usuarios otorgue explícitamente el grupo Analytics Sales / Administrador a quien administrará el módulo. Para Tienda o Supervisor, asigne además sus locales en Analytics Sales > Administración > Usuarios y permisos.
- Los cron siguen ejecutándose como usuario técnico de Odoo (sin mostrar el módulo a los usuarios de Ajustes). No se modifica la configuración ni los datos de las APIs.

## 16.0.1.1.16 — Establecimientos, metas anuales y proyección diaria

- En **Administración → Establecimiento** se puede registrar un nombre, p. ej. «Durán», y asociar locales `nlocal` existentes de la misma compañía. Un `nlocal` pertenece como máximo a un establecimiento; el maestro no sustituye el identificador `nlocal` recibido por la API.
- En **Administración → Metas** se pueden registrar objetivos monetarios de ventas netas para un año, tanto generales de compañía (sin establecimiento) como específicos de un establecimiento. No se permiten metas duplicadas para el mismo año y ámbito. Solo Analytics Sales Administrador puede modificar los establecimientos y las metas.
- Nuevo filtro **Establecimiento** en el dashboard. A continuación el usuario puede elegir un `nlocal` dentro de ese establecimiento. Ambos filtros respetan los nlocal autorizados por compañía y perfil. Si hay locales sin establecimiento asociado, siguen disponibles en «Todos los establecimientos».
- Nuevo gráfico **Ventas netas por día · proyección**: 15 días por defecto para proyectar, configurable de 1 a 90. Muestra los últimos 15 días reales y las futuras estimaciones. Modelo explicable: promedio diario neto (FA − DE) de hasta 30 días calendario disponibles en el período/filtro, incluidos días sin ventas; no presenta la predicción como facturación real ni añade movimientos.
- El comparativo de localidades se mueve al final del dashboard, ocupa todo el ancho, contiene barras por todos los locales autorizados (sin truncamiento Top 9), y cuenta con desplazamiento vertical y horizontal en gráfico y tabla, con scrollbar visible.
- No modifica las llamadas existentes de `ventas_anuales` / `ventas_mensuales`, su `clave` única ni su frecuencia programada; los perfiles y la protección de costos permanecen.

## 16.0.1.1.17 — Establecimiento y meta anual calculada por nlocal

- El menú y la acción **Administración → Establecimiento** se renombran a **Administración → Establecimiento** (también el encabezado de lista), sin cambiar el modelo ni las asociaciones ya registradas.
- En **Administración → Metas**, el campo visible **Meta anual de ventas netas** es ahora un total **calculado, solo lectura**, según el año y el establecimiento seleccionados: `Σ Total_neto FA − Σ Total_neto DE` de **todos** los locales `nlocal` vinculados, con independencia de la línea de producto. Los movimientos anulados no se cuentan.
- Si no hay establecimiento seleccionado, el cálculo corresponde a todos los locales de la compañía; si el establecimiento no tiene locales, el resultado es cero. Los movimientos de años distintos tampoco se cuentan.
- La misma regla de origen del dashboard evita sumar Excel y API juntos: cuando existe información API para la compañía, se consultan sus movimientos; si no, se utiliza el histórico de Excel. Se restringe por compañía y año.
- Se muestran también **Facturado FA del año**, **Devuelto DE del año** y **Locales incluidos**. Estos campos no se almacenan: cada nueva lectura toma las cifras vigentes de la base tras los cron `ventas_anuales` y `ventas_mensuales` (o sincronización manual). Para ver datos recién sincronizados, refresque la vista.
- La antigua meta manual (`target_amount`) **no se elimina ni modifica**: se conserva con el nuevo nombre **Objetivo anual (opcional)**. Su valor predeterminado es 0 para poder crear metas sin ingresar objetivos. El **Cumplimiento del objetivo (%)** es `Meta anual calculada / Objetivo manual × 100` cuando se haya ingresado un objetivo positivo.
- Se mantienen permisos exclusivamente para **Analytics Sales / Administrador** en el modelo Metas, y no se modifican API Administrator, cron, dashboard, proyección, importador ni claves únicas de origen.


## 16.0.1.1.18 — Metas por mes, localidad y vendedor

- Administración → Metas → abrir una meta: pestaña **Locales agrupados por mes** (enero a diciembre). Cada mes muestra todos los `nlocal` asociados al establecimiento, con facturado FA, devuelto DE, neto vendido, cuota meta mensual y porcentaje de cumplimiento. Si la meta es general, agrupa todos los locales de la compañía.
- Pestaña **Distribución por vendedor**: para cada mes/local, agrupa vendedores por `Codvendedor` (o nombre cuando falta código); muestra FA, DE, neto, meta automática de ese vendedor y cumplimiento. Incluye vendedores con cero movimientos en el mes cuando figuran en otro mes del año. Los movimientos sin vendedor se presentan aparte sin asignación personal.
- Regla explícita: primero `Objetivo anual (opcional)` cuando es mayor que cero. Si está vacío, usa las **ventas netas anuales efectivas como base referencial** (NO una meta planificada). Se reparte en 12 partes y, dentro de cada mes, por igual entre nlocal y entre los vendedores identificados de cada local; los centavos restantes se asignan en orden estable. Si un local no tiene vendedores identificados en el año, su cuota queda en **Meta pendiente de asignar**.
- Se obtiene el dato en lectura a través de un `read_group` por mes/local/vendedor/tipo de documento, con la misma prioridad de API sobre Excel, compañía, año y exclusión de anulados que la meta anual. El detalle se recalcula en cada lectura de la meta y no almacena acumulados ni altera movimientos o cron. Acceso solamente Analytics Sales Administrador.
- Para ver la información después de un cron, vuelva a abrir/refrescar la ficha de Metas. Las previsiones no son movimientos contables y no alteran el dashboard ni la importación.

## 16.0.1.1.19 — Histórico diario real y metas sin objetivo manual

- **Ventas netas por día** muestra solo el historial real FA − DE, sin estimación de ventas futuras.
  Permite seleccionar de 1 a 90 días históricos (15 por defecto) dentro del período filtrado,
  incluyendo días sin movimientos con cero; barras desplazables horizontalmente.
  Se muestran total neto histórico, promedio neto diario histórico y último día con movimientos.
- **Administración → Metas** elimina de lista/formulario «Objetivo de ventas (opcional)»,
  «Objetivo anual (opcional)» y «Cumplimiento del objetivo (%)».
- La distribución anual, mensual, por establecimiento, nlocal y vendedor usa solo ventas
  netas reales FA − DE como base referencial y se actualiza al consultar tras cada cron.
  El antiguo campo objetivo (`target_amount`) permanece almacenado exclusivamente por
  compatibilidad, pero queda oculto y nunca interviene en los cálculos.
- Sin cambios en la configuración API, cron, importación Excel, locales, roles, ni otros gráficos.


## 16.0.1.1.20 — Comparativo de todos los nlocal del establecimiento

- Corrige **Ventas netas por localidades (nlocal)**: muestra todos los locales
  autorizados del establecimiento seleccionado, aunque en el filtro **Local (nlocal)**
  se haya elegido uno para consultar los demás indicadores. Locales sin movimientos
  en las fechas y líneas filtradas aparecen con valores cero.
- El comparativo respeta compañía, permisos de Administrador/Supervisor,
  establecimiento, período, línea, marca, vendedor y prioridad API/Excel.
  El filtro de local individual sigue afectando al resto del dashboard.
- El perfil Tienda conserva su vista por vendedor del local autorizado; no
  obtiene datos de otros nlocal ni costos. Sin cambios en cron, JSON, metas
  ni cálculos de facturación o devoluciones.


## 16.0.1.1.23 — Vínculos cron / API seleccionables

- Configuración API reemplaza «Activar cron anual» y «Activar cron mensual» por
  «Cron de ventas anuales» y «Cron de ventas mensuales». Se seleccionan registros
  `ir.cron` existentes de **Analytics Sales**; no se exponen acciones ajenas.
- El vínculo de cada API y cron se guarda por ID y por compañía. Cuando un
  trabajo programado se ejecuta, llama a la API que tenga asignada por ID,
  independientemente de los nombres visibles. No permite asignar el mismo
  cron a ambas APIs para una misma compañía.
- Migración compatible: mientras no se hayan guardado los nuevos vínculos,
  las selecciones se derivan de las casillas de activación anteriores.
- El cron anual mantiene el horario diario a medianoche de Ecuador; el mensual
  continúa cada 2 horas. Se conservan los otros datos y pantallas sin cambios.

## 16.0.1.1.24 — Metas agrupadas por establecimiento y porcentaje igual por vendedor

- **Administración → Metas:** vista lista agrupada por año y establecimiento. En el formulario,
  **Resumen anual por establecimiento** separa las ventas FA/DE, la venta neta anual y la base
  distribuida; **Locales agrupados por mes** presenta establecimiento → mes → nlocal.
  Una meta general de compañía desglosa los establecimientos de la compañía y los locales
  no asociados. Una meta de establecimiento se limita a ese establecimiento.
- **Distribución por vendedor:** cada establecimiento reparte la base referencial anual de ventas
  netas reales en doce meses y **a partes iguales entre sus vendedores únicos**. Cada vendedor
  recibe el mismo porcentaje dentro de su establecimiento, independientemente de cuántos
  vendedores tenga un local. Un vendedor que figura en varios nlocal cuenta una sola vez;
  su cuota mensual se divide entre sus locales. Diferencias de centavos se compensan sin
  cambiar el total. El informe muestra cuotas **anuales y mensuales**, porcentajes y ventas reales.
- **Administración → Establecimiento:** se muestra automáticamente el listado de vendedores
  identificados en los movimientos FA/DE de los locales asignados, con código y nombres de
  sus nlocal. No crea maestros de vendedores ni altera documentos. Se recalcula al consultar.
- Si faltan vendedores, sus movimientos aparecen sin vendedor y no reciben cuota personal.
  Si todo el establecimiento carece de vendedores, la base queda pendiente de asignar.
- Se mantiene la prioridad de datos API sobre Excel, filtrado por compañía, fechas y
  exclusión de anulaciones. No se cambian API Administrator, cron, configuración de API,
  dashboard, permisos, importador ni los movimientos sincronizados.


## 16.0.1.1.25 — Simplificación visual de Metas y columnas legibles

- En **Administración → Metas** se ocultan de la ficha los dos paneles
  «Ventas netas anuales calculadas (FA - DE)» y «Distribución automática de meta anual»,
  incluidos sus campos Facturado/Devuelto anual, Meta anual, Base anual y Meta pendiente.
- La vista lista tampoco muestra los tres importes anuales de dichos paneles.
  Sus modelos y cálculos permanecen intactos para alimentar los informes y mantener los datos.
- En la pestaña «Distribución por vendedor» se oculta la columna **Código**. No cambia la
  identificación interna de vendedores ni sus cuotas y porcentajes.
- Las tablas de resumen anual, locales mensuales y distribución por vendedor usan
  columnas de ancho estable, texto ajustable y desplazamiento horizontal/vertical
  para evitar nombres, importes y celdas superpuestos.
- No cambia el funcionamiento de API Administrator, cron, permisos, establecimientos,
  sincronización ni dashboard.


## 16.0.1.1.26 — Establecimiento: tabla legible; Metas: únicamente distribución por vendedor

- El listado de vendedores de **Establecimiento** ocupa el ancho completo de la ficha,
  con columnas de ancho definido para nombre, código y localidades; scroll horizontal
  en pantallas estrechas. Corrige la visualización de texto vertical por columnas comprimidas.
- En **Administración → Metas**, solo queda la pestaña **Distribución por vendedor**.
  Se ocultan **Resumen anual por establecimiento** y **Locales agrupados por mes**.
- La distribución presenta los doce meses de cada establecimiento, los vendedores,
  sus localidades, el porcentaje igual de meta, **Facturado FA**, **Devuelto DE**,
  **Ventas netas**, **Meta mensual asignada** y **Cumplimiento**.
- Cálculos, importación, API/cron, permisos y dashboard no se modifican.


### 16.0.1.1.27 — Distribución equitativa por vendedor y mes

- En Metas, informe por establecimiento, mes, Local (nlocal) y Vendedor con columnas Facturado FA, Devuelto DE, Ventas netas, Meta mensual asignada y Cumplimiento.
- Reparto equitativo para cada vendedor **dentro de cada mes**, con diferencia máxima de un centavo en ajustes de redondeo. Vendedores en varios locales se muestran una sola vez por mes y su meta no se duplica.
- Sin cambios en APIs, cron, permisos, establecimientos ni dashboard.


### 16.0.1.1.28 — Agrupación de vendedores por local y mes

- Establecimiento: listado de vendedores agrupado por cada nlocal, sin repetir el nombre del local por persona; conserva Código y conteo único de vendedores.
- Metas: 12 encabezados mensuales, agrupación de locales antes de vendedores, sin repetir el mes ni la combinación de locales en cada fila.
- Vendedores asociados a más de un local se muestran una vez por mes bajo el encabezado conjunto de sus locales, para conservar íntegra su cuota equitativa y evitar duplicar resultados.
- Sin cambios en cálculos, API, cron, permisos ni dashboard.


### 16.0.1.1.29 — Etiquetas limpias de locales

- En Establecimiento y en Distribución por vendedor, los encabezados muestran **Local** en lugar de **Local (nlocal)**.
- Se oculta únicamente en la presentación el prefijo **C/** al principio del nombre de un local, por ejemplo **Local: Rotonda 001-050**. Se conservan sin modificar el nombre y código originales del local en Odoo.
- Sin cambios en cálculos, metas, cron, APIs, dashboard ni permisos.


### 16.0.1.1.30 — Etiquetas de Locales en Administración

- En Administración, el menú, la acción y la lista se llaman simplemente **Locales**.
- La selección de locales de Establecimiento se etiqueta **Locales**.
- En Metas, el nombre de columna es **Local**, sin el sufijo «(nlocal)».
- Cambios solo de texto visible: sin cambios en datos, reglas, cálculos, APIs, cron ni dashboard.


### 16.0.1.1.31 — Metas: pestañas mensuales separadas y vendedores sin duplicados

- Administración → Metas: **Distribución por mes** muestra los doce meses y los locales con FA, DE, neto, meta mensual y cumplimiento; **Distribución por vendedor** mantiene una cuota única por vendedor y mes.
- Administración → Establecimiento: listado único por vendedor; cada persona muestra en una sola celda todos los locales donde trabaja, en vez de aparecer repetida bajo cada local.
- En la distribución por vendedor, cada local de referencia tiene un único encabezado mensual. Si el vendedor tiene varios locales, aparece una sola vez al mes y sus cifras incluyen todos sus locales; la lista completa está disponible al pasar el cursor por su nombre.
- No se cambian los importes, la distribución, las APIs, cron, permisos ni el dashboard.


### 16.0.1.1.32 — Metas mensuales por establecimiento y vendedores sin locales repetidos

- Distribución por mes: exactamente 12 filas de totales por establecimiento y año; sin detalle ni repetición de locales.
- Distribución por vendedor: un encabezado por mes, una sola fila por vendedor y mes, y porcentaje de meta equitativo visible; sin encabezados «Local:».
- Se conserva el cálculo de ventas FA/DE, netos, meta y cumplimiento y el reparto equitativo de las versiones anteriores.
- Sin cambios en establecimiento, API, cron, dashboard, importación ni permisos.


### 16.0.1.1.33 — Cabecera de establecimiento sobre columnas en Metas

- En **Distribución por mes** y **Distribución por vendedor**, el encabezado
  «Establecimiento: ... — Año ...» se muestra en la primera fila de la tabla,
  por encima de los títulos de las columnas.
- Para metas que contienen varios establecimientos se genera una tabla por
  establecimiento, manteniendo sus datos separados y el encabezado primero.
- Sin cambios en datos, cálculos, metas asignadas, API, cron o demás pantallas.


## 16.0.1.1.34 — Lista compacta de Metas

- Únicamente en Administración → Metas, se limita el ancho de la tabla y se asignan anchuras proporcionadas a Año, Descripción, Establecimiento y Activo, evitando grandes espacios horizontales.
- Sin cambios de cálculos, datos, filtros, cron, permisos ni otras vistas.


## 16.0.1.1.35 — Año centrado en lista de Metas

- Solo cambio visual en Administración → Metas: centrar cabecera y valores de la columna Año.
- Se mantiene el ancho compacto de las columnas; sin cambios de datos, cálculos, permisos, cron, APIs o dashboard.


## v16.0.1.1.36 — Metas mensuales por establecimiento

- Permite ingresar importes independientes de enero a diciembre en Metas -> Distribución por mes, conservando las metas y datos ya existentes.
- Si se define alguna meta mensual, los meses no definidos quedan en cero y se utiliza el importe del mes para calcular el cumplimiento y repartir una cuota igual por vendedor. Si todas están en cero se mantiene el cálculo anterior derivado de ventas netas anuales.
- Desplaza «Meta mensual asignada» junto a Mes en el reporte mensual, y junto a «% de meta» en la distribución por vendedor.
- El cambio se limita a Metas; no modifica las ventas reales, los cron ni las APIs.


## Versión 16.0.1.1.37 — Meta mensual editable en su fila
- En Administración → Metas → Distribución por mes, el campo **Meta mensual asignada** es editable en cada fila inmediatamente después de Mes. Se retiró el panel superior con 12 campos separados.
- Una meta mensual sin registrar queda en **0**. Ya no se deriva automáticamente de las ventas netas del año. Los importes FA/DE/neto se recalculan desde las ventas de la API; no alteran los objetivos ingresados.
- La pestaña Distribución por vendedor ya no muestra **% de meta**. La cuota de cada mes se distribuye por partes iguales entre sus vendedores únicos (con ajuste máximo de un centavo).
- Los importes manuales mensuales anteriores se transfieren una sola vez a las filas de cada mes al actualizar el módulo. No se modificaron sincronizaciones ni cron.


## Versión 16.0.1.1.38 — Cumplimiento alineado a la derecha
- En Administración → Metas → Distribución por mes, los valores de la columna **Cumplimiento** se alinean a la derecha.
- No cambian cálculos, metas mensuales, ventas ni demás vistas.


### 16.0.1.1.39 — Metas masivas y Mes actual
- En Administración > Metas > Distribución por mes, nuevo importe mensual único con botón Aplicar: copia el valor a los doce meses, vacía el campo de entrada y mantiene las doce celdas editables.
- El dashboard ya no muestra el bloque de importación Excel; se conserva el asistente existente fuera del dashboard.
- Nuevo período Mes actual: mes calendario hasta el día de hoy según zona horaria del usuario, sin cambiar 30 días, 90 días, Año ni los rangos manuales.


### 16.0.1.1.40 — Cumplimiento de metas por establecimiento y vendedor
- Nuevo dashboard después de los filtros: compara la meta del período vs la venta real del establecimiento seleccionado, sumando todos sus locales sin desglosarlos por nlocal.
- Tabla de vendedores: meta asignada, vendido real, diferencia y cumplimiento; la meta del período se divide equitativamente entre los vendedores identificados del establecimiento.
- La comparación exige seleccionar un establecimiento para evitar mezclar metas de distintos establecimientos.


### 16.0.1.1.41 — Filtro Mes anterior
- Se incorpora **Mes anterior** al grupo de períodos del dashboard, entre Mes actual y 30 días.
- Usa desde el primer hasta el último día del mes calendario anterior en la zona horaria del usuario, incluso en enero (diciembre del año anterior).
- Se mantienen los otros filtros, el comparativo por establecimiento, metas, APIs y cron sin cambios.

### 16.0.1.1.42 — Filtro de período compacto
- Se reemplazan los cinco botones altos por un único selector oscuro con Mes actual, Mes anterior, 30 días, 90 días y Año.
- El período manual aparece como Personalizado al editar el rango de fechas.
- En escritorio, los cinco filtros comerciales, Período y Rango de fechas caben en una sola fila; el diseño se adapta a pantallas estrechas.
- Sin cambios en consultas, metas, permisos, API, cron o dashboard fuera de esta área.


### 16.0.1.1.43 — Ventas netas por establecimiento, antes de metas
- El comparativo deja de mostrar cada nlocal: suma los movimientos FA−DE de los locales autorizados asociados a cada establecimiento y muestra una fila por establecimiento.
- Si se filtra por Durán, aparece solo Durán; sin un establecimiento concreto se comparan establecimientos y, cuando corresponda, un único grupo Sin establecimiento para los locales sin asignación.
- El comparativo se mueve después de los filtros y antes de Cumplimiento de metas por establecimiento y vendedor.
- El resto de los KPI mantiene sus filtros; Supervisor/Tienda solo agregan sus locales permitidos.


### 16.0.1.1.44 — Meta del período sin prorrateo en Mes actual, Mes anterior y Año
- Mes actual y Mes anterior muestran el importe completo configurado para ese mes, aunque el mes actual no haya terminado.
- Año suma las doce metas mensuales del año seleccionado aunque las ventas reales terminen antes de diciembre.
- Los períodos 30/90 días y personalizados mantienen la proporcionalidad por días sobre el calendario; el objetivo del establecimiento y las cuotas por vendedor usan siempre la misma base.
- Sin cambios en los datos FA/DE, las APIs, cron, permisos, filtros comerciales ni demás bloques del dashboard.


### 16.0.1.1.45 — Meta asignada a vendedores sin diferencias frente a Metas
- Cumplimiento de metas del dashboard: **Meta asignada** usa exactamente el reparto mensual de Administración → Metas → Distribución por vendedor, incluida la distribución equitativa de centavos; no se prorratea por días en Mes actual, Mes anterior ni Año.
- **Vendido real** y su cumplimiento permanecen calculados a partir de los movimientos FA y DE actuales de la API.
- Los rangos parciales personalizados, 30 y 90 días mantienen la prorrata ya existente. No se cambian otros apartados del módulo.


### 16.0.1.1.46 — Establecimiento y local combinados en el comparativo
- Si se seleccionan **Establecimiento** y **Local**, el bloque de ventas netas cercano a los filtros presenta únicamente el local elegido (barra y tabla, FA, DE, unidades, utilidad donde esté autorizada).
- Al dejar **Local = Todos los autorizados**, se conserva el total agregado del establecimiento; con Todos los establecimientos se mantiene el comparativo anterior.
- El período del bloque local respeta el mismo rango seleccionado por los indicadores; sin ampliación de permisos ni cambios en las metas, cron o API.


### 16.0.1.1.47 — Porcentaje de cumplimiento en dashboard y comparativo
- Se incorpora una tarjeta de cumplimiento de meta dentro de los indicadores principales.
- Ventas netas por establecimientos incorpora porcentaje junto a cada barra y una columna Cumplimiento.
- Usa las metas mensuales guardadas por establecimiento y respeta Mes actual, Mes anterior, Año y rangos parciales.
- Si se selecciona establecimiento + local, etiqueta el resultado Aporte a meta: venta neta del local frente a la meta total del establecimiento, sin inventar una meta propia del local.
- Sin objetivo mensual positivo se muestra Sin meta, no 0% de cumplimiento.


### 16.0.1.1.49 — Cumplimiento para todos los establecimientos con acordeones
- La sección de cumplimiento presenta una tarjeta por establecimiento autorizado al escoger «Todos los establecimientos», con metas y ventas reales separadas.
- Cada tarjeta se puede expandir para ver los vendedores y su cumplimiento. Al filtrar por un establecimiento concreto, el detalle aparece expandido.
- Se conserva el reparto original de metas por vendedor, la integración API, los cron y los controles de acceso.
- Se retira el comportamiento «Sin selección» de la edición 16.0.1.1.48; regresan los valores explícitos «Todos ...» de la 16.0.1.1.47.


### 16.0.1.1.50 — Sin establecimiento en el acordeón general de metas
- Con **Todos los establecimientos**, añade **Sin establecimiento** para sumar exclusivamente los locales autorizados de la compañía que no pertenecen a ningún establecimiento.
- Su acordeón muestra sus vendedores y ventas netas reales FA − DE, sin atribuirles metas de otros establecimientos. Cuando no exista meta propia, indica **Sin meta**.
- Los locales asociados permanecen agrupados solo en sus establecimientos y no se duplican en la vista general.
- No altera la selección de establecimiento individual, los cron ni los cálculos de metas ya existentes.


### 16.0.1.1.51 — Detalle directo con un establecimiento
- En el dashboard Cumplimiento de metas por establecimiento y vendedor, el acordeón se utiliza únicamente cuando está seleccionado Todos los establecimientos.
- Cuando se selecciona un establecimiento concreto, se muestra directamente su comparación de meta/venta real y su tabla de vendedores, sin encabezado plegable ni acordeón. Sin modificaciones en los cálculos ni permisos.


### 16.0.1.1.52 — Venta real de metas consistente con Venta neta
- El importe **Venta real** del dashboard de cumplimiento y las ventas reales de cada vendedor reutilizan exactamente las líneas ya filtradas que alimentan **Venta neta** (misma fuente API/Excel, compañía, permisos, fechas, establecimiento, local, Moda/todas las líneas, línea de productos, marca y vendedor).
- En **Todos los establecimientos** se conserva la agrupación por establecimiento y **Sin establecimiento**, sin duplicar movimientos. Con un local seleccionado se muestra solo el grupo correspondiente.
- Las metas asignadas y su reparto igualitario **no se modifican** por los filtros comerciales. Se conserva la configuración API, cron y todas las demás vistas.


### 16.0.1.1.53 — Orden del histórico diario
- Se reubica únicamente el bloque «Ventas netas por día · histórico real» para que aparezca inmediatamente antes de «Gestión de facturación — Facturas, productividad y decisión comercial».
- No se alteran filtros, cálculos, datos, APIs, permisos, cron ni estilos.

### 16.0.1.1.54 — Histórico diario más compacto
- Se revierte exclusivamente la reubicación de la versión anterior: el gráfico **Ventas netas por día · histórico real** vuelve a su posición original.
- Su panel tendrá un ancho máximo de 900 px en escritorio y será responsive.
- No se modifican los cálculos, filtros, permisos, APIs, cron ni los demás gráficos.

### 16.0.1.1.55 — Histórico diario del mismo ancho que Evolución de ventas netas
- El bloque «Ventas netas por día · histórico real» coincide con el ancho de «Evolución de ventas netas» en la misma pantalla, calculado como 1,5 / 2,5 del espacio de la cuadrícula con separación de 14 píxeles.
- En pantallas pequeñas conserva el ancho del contenedor; no modifica posición, cálculos, filtros ni datos.


### 16.0.1.1.56 — Scroll en Rentabilidad por marca y Productividad por vendedor
- Ambas tablas disponen de desplazamiento vertical y horizontal en su propio panel,
  con encabezados fijos y sin alargar el dashboard.
- Se muestran todos los vendedores y marcas disponibles en esas tablas, en el
  mismo orden y con los mismos cálculos previos, en vez de truncar a 8 filas.
- No cambia el backend, permisos, fuentes API, cron, metas ni otros gráficos.


### 16.0.1.1.57 — Nombres largos en Mayor velocidad de venta (móvil)
- Se ajusta exclusivamente el apartado «Mayor velocidad de venta» en pantallas de hasta 810 px.
- Los nombres/SKU largos se muestran en varias líneas dentro del ancho del panel, sin recortar información ni desplazar las tarjetas.
- El dato «Uds./día» queda alineado a la derecha en una segunda línea del encabezado de producto.
- No se modifican ventas, devoluciones, cálculos, filtros, permisos, APIs, cron ni otros rankings.

### 16.0.1.1.58 — Modelos y avance de meta por establecimiento
- Campo opcional `modelo` en movimientos API (y columna opcional Modelo en Excel). Actualiza por clave existente sin duplicar; un envío sin modelo no borra un dato previamente recibido. Ejecutar la sincronización anual para completar el modelo de movimientos previos incluidos en su respuesta. Los movimientos aún sin modelo se reúnen como «Sin modelo»; no se infieren valores desde SKU.
- ABC y Productos más vendidos usan agrupación independiente por modelo con los mismos filtros y cálculo FA − DE. Los demás rankings por SKU (incluida velocidad), exportación, totales, permisos y metas se mantienen.
- Ventas netas por establecimientos: importe a la derecha = meta del período, venta neta bajo la barra; llenado = venta neta / meta, limitado visualmente a 100%, porcentaje real visible incluso al superar la meta. Sin meta: carril vacío y etiqueta Sin meta. El cálculo de metas y el comparativo de locales no cambian.


### 16.0.1.1.59 — Histórico diario a ancho completo
- El panel «Ventas netas por día · histórico real» vuelve a ocupar todo el ancho disponible del dashboard, también en móvil.
- Conserva su posición, sus cálculos, el selector de días y el scroll horizontal interno.


### 16.0.1.1.60 — Cumplimiento de metas por vendedor
- Listado único sin acordeones. Con Todos los establecimientos, incluye vendedores autorizados y sin establecimiento; con uno seleccionado conserva sus vendedores. Identidad por código o nombre normalizado sin código. Si el vendedor aparece en varios grupos, se suman las cuotas ya asignadas y las ventas filtradas, sin volver a repartir las metas. Se conservan los grupos en la respuesta RPC por compatibilidad.
- La columna Avance hacia la meta muestra la barra (venta neta / meta individual, limitada visualmente al 100 %) y el importe de la meta, no la venta real. Se conservan Diferencia y Cumplimiento; sin meta se muestra un carril vacío y Sin meta. Los indicadores generales conservan sus importes y filtros.
- Se conserva el scroll de la tabla. No se modifican metas mensuales ni su reparto, fuente de ventas FA − DE, permisos, APIs, cron ni otros gráficos.


### 16.0.1.1.61 — Eliminar recargas automáticas del dashboard
- Se retiran la consulta de indicadores cada 120 segundos y la consulta al volver a una pestaña visible. Ambas llamaban a `analytics.sales.dashboard.get_dashboard`, sin ejecutar APIs externas.
- Nuevo botón «Actualizar datos» para todos los perfiles: consulta los datos ya guardados en Odoo, conserva los filtros y no sincroniza las APIs. La vista sigue consultando al abrir, al cambiar filtros o tras la sincronización/importación manual existente. Si un cron termina mientras el dashboard está abierto, se verán los nuevos datos en la próxima consulta explícita.
- Sin cambios en los cron (anual 00:00 Ecuador; mensual cada 2 horas), sus vínculos, el botón de administrador «Sincronizar API», cálculos, fuentes de datos ni permisos.

### 16.0.1.1.62 — Únicamente sincronización manual existente
- Se elimina el botón adicional «Actualizar datos» y su manejador. Se conserva «Sincronizar API» con sus permisos y la recarga del dashboard tras una sincronización exitosa.
- No se reactivan las consultas periódicas ni al regresar a la pestaña. Se mantienen las consultas al abrir y cambiar filtros y los cron existentes.

### 16.0.1.1.63 — Barras amplias de cumplimiento por vendedor
- Se reemplaza la tabla de avance individual por el diseño de barras de establecimientos: vendedor y código a la izquierda, barra amplia al centro, meta a la derecha, venta neta, diferencia y cumplimiento debajo. Se conserva el scroll vertical. En móvil, nombre y meta sobre la barra de ancho disponible.
- Se reutilizan los mismos datos, colores por cumplimiento y cálculo visual del avance (limitado a 100%, porcentaje real visible). Sin meta: carril vacío. No cambian filtros, metas, agrupación de vendedores, APIs, cron, permisos ni recargas.

### 16.0.1.1.64 — Meta como primer indicador principal
- Se retiran las cuatro tarjetas del resumen del panel Cumplimiento de metas por vendedor. Se conserva la meta calculada como tarjeta «Meta», inmediatamente antes de «Facturas FA únicas», con el mismo importe y filtros del resumen anterior.
- Se conservan las barras individuales, la venta neta, la diferencia y el cumplimiento por vendedor y los indicadores principales existentes. Sin cambios en el servidor, permisos, APIs ni cron.


### 16.0.1.1.65 — Consulta actualizada al refrescar el navegador
- Al abrir o refrescar el dashboard (F5), se realiza una solicitud JSON-RPC nueva con una URL única por consulta para evitar respuestas HTTP reutilizadas. Se conserva el contexto nativo de usuario y compañía de Odoo 16, los filtros y los permisos del servicio.
- Se muestra la hora de la consulta a Odoo, separada de la última sincronización exitosa de la API. No se invoca la API externa al refrescar; solo se muestran datos ya guardados por una sincronización completada. Los filtros iniciales al recargar el navegador conservan el comportamiento anterior.
- No se agregan botones ni se reactivan temporizadores o eventos de visibilidad. Se conserva Sincronizar API, los cron, cálculos, metas y gráficos existentes.

### 16.0.1.1.66 — Solo última sincronización visible
- Se retira únicamente la etiqueta «Consulta Odoo» del dashboard; se conserva «Última sincronización».
- La recarga mediante F5 y la consulta sin caché permanecen intactas, sin llamadas a la API externa ni recargas automáticas.

### 16.0.1.1.67 — Vista web móvil tipo aplicación
- Cabecera IDR Moda fija durante el desplazamiento y controles táctiles (44 px) en pantallas de hasta 810 px.
- La barra de navegación de Odoo se oculta sólo durante el dashboard móvil; el botón Menú Odoo permite recuperarla, y se restaura al cambiar de acción. En escritorio no cambia el diseño.
- Experiencia visual tipo PWA, sin manifest de instalación, service worker ni almacenamiento adicional de datos. No es posible retirar la barra de direcciones del navegador automáticamente en una pestaña web normal.
- Se conservan la carga al abrir/F5, filtros, sincronización manual y cron originales. No se agregan consultas automáticas, ni se cambia el backend o permisos.

### 16.0.1.1.68 — Actualizar información
- Se cambia exclusivamente la etiqueta visible del botón «Sincronizar API» por «Actualizar información». Se conserva la acción original, sus permisos y el estado durante la sincronización.


### 16.0.1.1.69 — Etiqueta de información
- Se reemplaza el texto visible «API sincronizada» por «Actualizar información», conservando la última sincronización y la lógica existente.

### 16.0.1.1.70 — Etiquetas de actualización
- El estado visible indica «Información actualizada» y la fecha indica «Última actualización». El botón conserva «Actualizar información». No cambia la lógica de sincronización.

### 16.0.1.1.71 — Confirmación de agrupación por modelo
- Clasificación ABC por ventas netas y Productos más vendidos agrupan por el campo JSON `Modelo`/`modelo`.
- Los registros sin ese dato se muestran como `Sin modelo`.
- Requiere sincronizar nuevamente la información para que los movimientos anteriores reciban el modelo si aún no lo tenían.

### 16.0.1.1.72 — Etiqueta Modelo
- En clasificación ABC se sustituye «grupos por modelo» por «Modelo», sin modificar cálculos.

### 16.0.1.1.73 - Total meta anual
- Campo monetario calculado y de solo lectura en el formulario y la lista de Metas. Suma exclusivamente las metas mensuales de cada ficha, sin utilizar ventas reales ni la meta anual legada.
- Se recalcula al editar las metas mensuales o aplicar un importe a los doce meses. No cambia la distribucion existente ni el dashboard.

### 16.0.1.1.74 — Maestro de bodegas y valorización
- Administración → Bodega: código, nombre, item, valor USD y última actualización desde la API; relaciones manuales a un local (establecimiento derivado de su configuración) o directamente a un establecimiento si no tiene local. No se crean ni cambian establecimientos automáticamente.
- Configuración API: seleccionar el registro existente `actualizar_bodega`, guardar vínculos. Cron exclusivo cada 5 horas, independiente de los cron de ventas. Botón de actualización manual desde Configuración API. La actualización de ventas existente no cambia.
- Contrato provisional, pendiente de confirmar con el JSON real: arreglo de objetos (también acepta envoltorios del adaptador existente), una fila resumen por código, ej. `{"Codigo":"B01","Nombre":"Bodega Centro","Item":120,"Valor":15000.25}`. Se admiten mayúsculas/minúsculas y alias explícitos; `Item` se guarda como texto sin inferir cantidad ni SKU. El valor recibido representa el total de esa bodega en USD. Duplicados idénticos se ignoran; datos contradictorios de un mismo código se rechazan para evitar sumar dos veces. Ausencias no eliminan bodegas ni cambian relaciones. Si el endpoint es de detalle por artículo, adaptar el contrato antes de usarlo.
- Dashboard de valores de bodegas antes de Ventas netas por establecimientos: subtotales por establecimiento/local y detalle de cada bodega, incluyendo no asignadas en la vista general. Valores del último corte recibido; no dependen de fechas ni filtros comerciales de ventas. Solo Administrador Analytics Sales de la compañía activa hasta confirmar permisos de valorización. No se reintroducen recargas automáticas.
- Historial de sincronización identifica la API de bodegas; su fecha no altera la última actualización de ventas.

### 16.0.1.1.75 — Bodegas por establecimiento
- Bodega tiene una sola relación directa y editable con Establecimiento de la misma compañía. Se elimina la relación a Local de las vistas y del modelo.
- Migración: conserva las asignaciones directas y convierte los vínculos anteriores por local si existe un establecimiento activo único de la misma compañía. Los demás quedan sin establecimiento; la sincronización no modifica la nueva relación.
- El panel agrupa directamente las bodegas por establecimiento, sin subtotales por local. Solo responde al filtro Establecimiento; las bodegas sin asignar aparecen en la vista general. Se conserva el acceso exclusivo de Administrador. El selector compartido de establecimientos mantiene su comportamiento anterior (establecimientos asociados a locales).
- Sin cambios en API, cron, importes ni cálculos de ventas.

### 16.0.1.1.76 — Contrato real de bodegas y selección por establecimiento
- API: Bodega = código, nBodega = nombre sin espacios exteriores, Stock = cantidad decimal, Valor = monto total con seis decimales. Se conserva la envoltura success/data del adaptador.
- Maestro y dashboard muestran Stock en lugar de Item. El valor monetario se muestra a dos decimales y se suma antes de redondear. Las relaciones se mantienen al sincronizar por código y compañía.
- Selección múltiple de bodegas en Administración → Establecimiento, sobre la misma relación directa existente. Una bodega solo pertenece a un establecimiento.
- La valorización conserva acceso exclusivo de Administrador y cron de cinco horas. Un establecimiento con bodegas y sin locales puede seleccionarse por Administrador.
- Si existían bodegas de versiones provisionales, se conserva su antiguo campo Item sin asumir que es Stock. Actualice bodegas para completar los nuevos datos.

### 16.0.1.1.77 — Configuración API persistente
- Un registro permanente por compañía, compartido entre administradores autorizados.
- El guardado normal y Guardar vínculos persisten los IDs en los parámetros existentes; abrir el menú no borra enlaces.
- La migración consolida formularios temporales duplicados sin tocar parámetros, cron ni registros comerciales.
- Si un vínculo nunca fue guardado o su API ya no existe, debe seleccionarse una sola vez.
- Una desvinculación explícita se guarda como 0 para no reactivar valores antiguos al actualizar.


### 16.0.1.1.78 — Bodegas en vista compacta
- El dashboard de bodegas usa una tabla única: establecimiento, bodega, stock y valor.
- Se oculta el código únicamente en el dashboard. Cada bodega ocupa una fila; los establecimientos con varias bodegas conservan una fila de subtotal.
- Sin cambios en datos, API, configuración persistente, permisos ni cálculos.

### 16.0.1.1.79
- Se oculta solo la fila de subtotal de bodegas Sin establecimiento. Se conservan sus filas, los subtotales de establecimientos asignados y el total general.

### 16.0.1.1.80 — Etiquetas de valorización de inventario
- Se cambia «Valor (USD)» por «Valor (uds.)» y «Valor total» por «Valor total de unidades» en el panel de bodegas; se armonizan las etiquetas del maestro.
- Se conserva el formato monetario, el stock y el cálculo original de valorización recibido de la API.

### 16.0.1.1.81 — Valor total uds
- Se abrevia la etiqueta «Valor total de unidades» a «Valor total uds» en el dashboard y el maestro de bodegas. Sin cambios de cálculos.


### 16.0.1.1.82 — Totales de inventario por establecimiento
- Una fila por establecimiento con stock y valor acumulados de sus bodegas; sin columna Bodega ni filas de detalle o subtotal duplicadas.
- En la vista general, las bodegas no asignadas se muestran agrupadas en una sola fila Sin establecimiento, sin subtotal adicional.
- Se mantienen stock decimal, valoración en dólares, totales generales, filtros, permisos y sincronización. Solo cambia la presentación del panel.


### 16.0.1.1.83 — Vínculos API recuperables, bodegas diarias y actualización manual completa
- Los vínculos por compañía se leen de los parámetros persistentes, con respaldo en el registro permanente de configuración. Si falta una copia de parámetro se recupera al actualizar el módulo, sin reemplazar IDs existentes ni una desvinculación explícita (`0`). El formulario mantiene visible el ID guardado de una API temporalmente no disponible.
- El cron de bodegas existente pasa a 1 día (se mantiene su próxima ejecución y estado activo); no se recrea. Los otros cron conservan su frecuencia.
- Actualizar información ejecuta las tres APIs; las cantidades de bodegas se muestran por separado de los movimientos de ventas. Se recarga el dashboard tras los resultados, incluso si una API falla y otras terminan correctamente. No se reactivan las recargas periódicas.
- Si se perdieron ambas copias de una selección, es necesario seleccionarla una vez; no se infieren vínculos de bodegas por nombres similares.

### 16.0.1.1.84 — Cron automáticos fijos
- Los tres cron aparecen en Configuración API como vínculos de solo lectura. Cada uno ejecuta exclusivamente la API guardada para su tipo y compañía. No se requieren selecciones manuales de cron.
- Ventas anuales: 00:00 Ecuador; mensuales: cada dos horas pares; bodegas: cada día, conservando su próxima ejecución. Se reactivan los tres cron existentes y se corrigen sus intervalos al actualizar, sin crear nuevos cron.
- Se conservan los botones de actualización manual opcional, las APIs seleccionadas y los dashboards. Los vínculos antiguos invertidos o vacíos no afectan al cron automático.
