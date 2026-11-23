# Icono personalizado para Control de Caja Chica (Odoo 18)

Este módulo **no modifica** los archivos del módulo original `petty_cash_control`. Solo actualiza el campo `web_icon` del menú raíz `petty_cash_control.menu_petty_cash_root`.

## Instalación

1. Mantener instalado el módulo original **Control de Caja Chica** (`petty_cash_control`).
2. Descomprimir el ZIP y copiar la carpeta `petty_cash_icon_custom` dentro de alguno de los directorios configurados en `addons_path` (puede ser el mismo directorio de addons personalizados del módulo original).
3. Reiniciar el servicio Odoo 18 correspondiente.
4. Activar el modo desarrollador. Ir a **Aplicaciones > Actualizar lista de aplicaciones**.
5. Quitar el filtro «Aplicaciones» si no aparece y buscar **Caja Chica - Icono Personalizado**; instalar.
6. Recargar el navegador con `Ctrl + F5` o abrir una ventana de incógnito para evitar mostrar el ícono anterior en caché.

## Alcance

- Cambia únicamente el ícono del menú principal de Caja chica.
- Conserva todas las operaciones, vistas, permisos y modelos originales.
- No crea un segundo menú ni duplica la aplicación.
- La dependencia `petty_cash_control` asegura que el módulo principal exista antes de aplicar el cambio.

## Nota

Si se desinstala la extensión, Odoo puede conservar el último valor del ícono del menú. En caso de querer restaurar el ícono predeterminado, se puede editar el campo `web_icon` desde el menú técnico o instalar un módulo que lo restablezca; la extensión no desinstala ni deshabilita el módulo original.
