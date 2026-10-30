# CONEDERA | Home de crédito para Odoo 18

Módulo técnico: `conedera_credit_home` — versión `18.0.1.0.0`.

## Qué hace

- Publica el home comercial en **/credito-conedera** (no reemplaza la página principal `/` automáticamente).
- Incluye logo oficial de CONEDERA (convertido a fondo transparente) y 7 ilustraciones/íconos SVG originales.
- Utiliza los colores extraídos del logo: **naranja #E38001** y **azul #29307A**.
- Presenta solicitud, seguimiento de solicitudes, ingreso de documentos cuando corresponda, pasos del proceso, preguntas frecuentes y llamada a la acción.
- Respeta la empresa del sitio web (`request.website.company_id`), compatible con instalaciones multiempresa por dominio.
- No modifica formularios, estados, PDF, historial, permisos, cron, WhatsApp ni otras funciones del módulo de crédito.

## Instalación

1. Copiar la carpeta `conedera_credit_home` del ZIP al `addons_path` de Odoo 18.
2. Verificar que están instalados **website** y **custom_web_credito_conedera** (dependencias).
3. Reiniciar el servicio Odoo y actualizar la lista de aplicaciones.
4. Instalar **CONEDERA | Home de crédito**.
5. Abrir `https://SU-DOMINIO/credito-conedera`.

## Enlaces con el portal instalado

Las rutas exactas de la versión que está en el servidor no estaban en los archivos proporcionados. Por seguridad no se inventaron rutas del módulo anterior.

Para asignarlas, ir a **Ajustes** -> sección **CONEDERA - Home de crédito**, seleccionar la empresa correcta y guardar:
- **Solicitar crédito**: ruta ya existente del formulario.
- **Historial de solicitudes**: ruta ya existente del historial.
- **Ingreso de documentos**: ruta ya existente de documentos.

Puede ingresarse una ruta relativa como `/mi/ruta` o una URL HTTP(S) completa. Si los campos están vacíos, se intenta reutilizar el enlace de un menú del sitio con un nombre equivalente; como alternativa, el botón abre `/my` (portal de Odoo). La página comercial nunca crea ni envía una solicitud directamente.

## Usar este diseño como página principal del dominio

El módulo no toma automáticamente la ruta `/`, para evitar sobrescribir un home existente. Puede enlazar `/credito-conedera` en el menú principal de Website, o definir una redirección desde `/` desde el editor/configuración del sitio previa comprobación del home actual. El home no altera otras empresas ni otros sitios.

## Archivos de marca

- `static/src/img/logo_conedera_transparente.png`: logo provisto por el usuario, sin fondo blanco.
- `static/src/img/isotipo_conedera.png`: símbolo original del logo.
- `static/src/img/hero_negocio.svg`: ilustración vectorial original.
- `static/src/img/icon_*.svg`: íconos vectoriales originales.

El ZIP independiente de recursos incluye todos ellos; se puede usar para otras páginas.
