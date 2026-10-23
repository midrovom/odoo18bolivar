# Portal de Solicitudes de Crédito CONEDERA - Odoo 18

Módulo nuevo e independiente de los módulos de Recursos Humanos utilizados como referencia.

## Funcionalidades incluidas

- La entrada **Solicitar crédito** abre el login nativo de Odoo con retorno al formulario de crédito. Los usuarios de portal ya autenticados van directamente al formulario.
- El registro utiliza la pantalla nativa `/web/signup` de Odoo. Tras enviar el formulario, el usuario verifica el código OTP y solo entonces se activa la cuenta mediante `res.users.signup()` de `auth_signup` y un token firmado nativo generado por el contacto; no se usa `res.users.create()` ni un modelo paralelo de cuentas.
- El acceso público de **Solicitar crédito** conduce primero a `/web/login` nativo de Odoo. Desde el propio login, el visitante puede abrir el registro nativo `/web/signup`.
- Código de verificación OTP de seis dígitos enviado por correo; vence en 3 minutos y limita los intentos de validación.
- La cuenta nativa de Odoo se crea únicamente después de validar el código. Luego se solicita iniciar sesión en `/web/login` y el acceso por defecto redirige a `/my/credito/nueva`.
- Formulario web con los campos de la página 1 del PDF: propietario/representante, tipo de solicitante configurable, negocio, datos económicos, relación de dependencia y referencias comerciales, personales y bancarias ampliables desde tres líneas iniciales.
- En Datos del negocio o empresa, las dos cédulas de Personas autorizadas (comprar y retirar mercadería) se validan primero con el algoritmo ecuatoriano; si falla, se acepta un documento extranjero de exactamente 10 dígitos numéricos. Se comprueba en el portal, el controlador y el modelo Odoo.
- Historial personal de solicitudes y detalle con etapas visibles para el cliente.
- Kanban interno por etapas para arrastrar solicitudes y avanzar el proceso. Los cambios se registran en la línea de tiempo y generan intento de notificación por correo al solicitante.
- La etapa **Aprobada** habilita la carga documental. El tipo de solicitante configurado en Odoo determina los documentos y sus requisitos obligatorios.
- Gestión de la documentación recibida y controles para aceptar el expediente o pedir correcciones.
- Campos de la página 2 del PDF destinados a la verificación interna de la ubicación del negocio.
- Se notifica a `cobranzas@viteltek.com` la latitud y longitud ingresadas del negocio, sin generar ni almacenar enlaces de Google Maps.

## Documentos posteriores a la aprobación

### Persona natural

1. Solicitud de crédito preparada y firmada.
2. RUC actualizado.
3. Cédula a color del cliente; cédula del cónyuge cuando se haya indicado cónyuge en la solicitud.
4. Certificado de votación vigente del cliente.
5. Planilla de servicio básico del local y del lugar de residencia.
6. Fotografías interna y externa del local.
7. Fotografía del solicitante firmando, con el rostro claramente visible.

### Persona jurídica

1. Solicitud de crédito preparada y firmada por el representante legal.
2. RUC actualizado.
3. Cédula a color del representante legal.
4. Certificado de votación vigente del representante legal.
5. Planilla de servicio básico del local y del lugar de residencia.
6. Nombramiento del representante legal.
7. Fotografías interna y externa del local.
8. Fotografía del solicitante firmando, con el rostro claramente visible.

Documentos administrativos aceptan PDF/JPG/PNG; los tres campos de fotografía aceptan JPG/PNG. El límite aplicado por archivo en el portal es 12 MB.

## Etapas iniciales

1. Recibida
2. En revisión
3. Aprobada
4. Documentación recibida
5. Verificación
6. Finalizada
7. Denegada

Las etapas se pueden administrar desde **Crédito CONEDERA → Etapas del flujo**. La etapa aprobada activa la carga documental y la etapa denegada la oculta/bloquea.

## Instalación

1. Copiar `custom_web_credito_conedera` en el directorio de addons personalizados de Odoo 18.
2. Reiniciar el servicio de Odoo.
3. Actualizar la lista de aplicaciones.
4. Si el módulo ya estaba instalado, usar **Actualizar / Upgrade** para aplicar los campos y las vistas nuevas; si es una instalación nueva, instalar **Portal de Solicitudes de Crédito CONEDERA**.
5. Asignar a los usuarios internos que administrarán el flujo el grupo **Gestión de solicitudes de crédito CONEDERA**.
6. Configurar un servidor SMTP saliente en Odoo y un correo de compañía o remitente predeterminado; es necesario para enviar códigos OTP y avisos de etapa.

## Seguridad y notas

- El usuario del portal solo puede consultar los registros enlazados a su propio usuario; las rutas verifican propiedad antes de leer una solicitud o cargar archivos.
- Los accesos de backend y las etapas están restringidos al grupo interno del módulo.
- Los datos de verificación de ubicación son campos internos. El portal solicita dirección del negocio, latitud y longitud, con opción de geolocalización autorizada por el navegador.
- La declaración/autorización del formulario web sigue el texto de la solicitud PDF entregada. Por tratarse de una autorización legal de crédito, el área legal de CONEDERA debe validar la versión web antes de producción.
- Este paquete se validó estáticamente (estructura, XML y sintaxis Python). No se ejecutó contra una instancia real de Odoo ni se verificó el SMTP, por lo que se recomienda instalar primero en una base de pruebas.


### Ajustes de registro y aceptación documental
- El registro reutiliza el formulario nativo de Odoo y la casilla única **Acepto términos y condiciones** que aporta `custom_web_hr_datos_candidatos`; no agrega una segunda aceptación de tratamiento de datos.
- Al pulsar **Registrarse**, se envía automáticamente el primer código y se abre un modal para ingresarlo. El contador tiene una vigencia de 3 minutos; al llegar a cero aparece **Reenviar código** y solo ese clic envía un código nuevo e invalida el anterior.
- La cuenta de `res.users` se crea después de validar un código vigente. El servidor también valida que se haya aceptado la casilla de términos y condiciones.
- Antes de enviar la solicitud, el cliente debe aceptar por separado las cláusulas sugeridas sobre relación comercial previa, citación telemática, consulta de score crediticio por cualquier plataforma o buró de crédito autorizado, firma/sello de CONEDERA y documentos financieros adicionales.
- La aceptación de documentos financieros adicionales sigue siendo una casilla de la solicitud; los comprobantes de IVA, renta y certificado bancario ahora solo se solicitan si el administrador los agrega como requisitos en el catálogo de documentos del tipo de solicitante. Los archivos de versiones antiguas no se eliminan.
- La autorización para consulta de score/historial se muestra como bloque independiente y no identifica a un proveedor específico.


### Integración con el usuario nativo de Odoo
- La cuenta se crea con el mecanismo `res.users.signup()` de `auth_signup`, usando un token firmado nativo generado para el contacto que se vinculará a la cuenta. La creación del contacto y del usuario ocurre en un `savepoint`; si falla el registro nativo, se revierte la operación para no dejar contactos huérfanos.
- No se crea un modelo personalizado de usuarios ni un segundo usuario de portal. La solicitud de crédito se vincula al `res.users` autenticado. Como en Odoo estándar, cada usuario tiene su contacto `res.partner` asociado.
- El menú público **Solicitar crédito** abre `/web/login?redirect=/my/credito/nueva`. Las rutas antiguas de registro y las pantallas de verificación sin una sesión pendiente también devuelven al login, no al registro.


## Corrección 18.0.1.0.3

La versión 18.0.1.0.6 envía al usuario al login de forma predeterminada, valida la casilla de términos antes de comprobar si el correo ya existe y verifica en el servidor que la aceptación esté registrada en la sesión antes de completar el alta.



## Configuración del correo SMTP de crédito

En Ajustes > Técnico > Correo > Servidores de correo saliente, marque el servidor SMTP correspondiente con la casilla **Correo de crédito**. Configure su usuario SMTP (`smtp_user`) y deje marcada esa opción en un único servidor. Los códigos OTP de registro, las notificaciones de etapas y el aviso de ubicación de negocio enviados por este módulo usan ese servidor explícitamente y establecen `email_from` con su `smtp_user`. El servidor marcado **Correo de Reclutamiento** por el módulo `custom_web_hr_datos_candidatos` permanece separado y sin cambios.


### Corrección del modal de verificación (18.0.1.0.8)

- El modal incluye una X que cancela el registro pendiente y vuelve al registro nativo de Odoo.
- El temporizador se calcula cada 250 ms desde la hora de vencimiento del servidor para actualizar el contador cada segundo y habilitar el reenvío al vencer.
- La inicialización JavaScript funciona incluso cuando los assets se cargan después de `DOMContentLoaded`.


### Corrección 18.0.1.0.9: creación de cuentas luego del OTP (Odoo 18)

- Se corrigió la incompatibilidad que impedía crear la cuenta tras verificar el código: en Odoo 18, `res.partner.signup_prepare()` no rellena `signup_token` como en versiones antiguas. Ahora se invoca `partner._generate_signup_token()` y se pasa ese valor a `res.users.signup()` para enlazar el usuario con el contacto recién creado.
- Se conserva la transacción con `savepoint`, la validación del código, el inicio de sesión manual, el uso de la plantilla de usuario portal nativa y la prevención de correos ya registrados.
- Si ocurre otro error durante la creación, el registro de Odoo conserva la excepción real bajo `No se pudo crear la cuenta nativa del portal de crédito CONEDERA` para facilitar la revisión por el administrador.
- Actualizar este módulo en Odoo (Upgrade) y reiniciar el servicio; no es necesario modificar el módulo de recursos humanos.

## Versión 18.0.1.1.0 — tipos de solicitante y documentación configurable

- **Configuración**: Crédito CONEDERA > Tipos de solicitante. Cree cualquier cantidad de tipos y establezca sus documentos desde la pestaña **Documentos exigidos**. Por requisito puede configurar orden, nombre, carácter obligatorio, visibilidad condicionada a que la solicitud informe un cónyuge, formato fotográfico y descripción.
- **Portal de solicitudes**: el campo Tipo de solicitante lee los registros activos del catálogo. Se conservan los campos de ambas páginas de la solicitud PDF; se separaron los campos Lugar y Fecha, y Ciudad/Cantón/Parroquia de la verificación interna de ubicación.
- **Portal documental**: después de que la solicitud sea aprobada, la lista de archivos a cargar corresponde al catálogo del tipo seleccionado, no a una lista codificada en el controlador. Permite guardado parcial. Las planillas de servicios y las fotografías interiores/exteriores se solicitan como archivos separados. La cédula del cónyuge solo se muestra cuando en la solicitud consta el nombre del cónyuge.
- **Tipos iniciales**: Persona natural y Persona jurídica; requisitos iniciales según las siete u ocho categorías indicadas, divididas en archivos independientes donde aplica.
- **Validaciones**: se aceptan PDF/JPG/PNG para documentos, JPG/PNG para fotos, máximo 12 MB, verificación del encabezado del archivo y verificación del documento seleccionado (su tipo debe corresponder al de la solicitud). La aceptación de la documentación se bloquea si faltan requisitos obligatorios.
- **Actualización**: se mantiene temporalmente el campo antiguo `person_type` para conservar datos históricos, pero **no** es el selector activo. Al actualizar se asigna el nuevo `applicant_type_id` a solicitudes anteriores y se copian los archivos legados para los requisitos iniciales sin duplicarlos. Los binarios antiguos siguen almacenados y se consultan en **Documentación recibida > Archivos de versiones anteriores**. La copia omite archivos antiguos sin un nombre/extensión recuperables o que no superen la validación; esos archivos permanecen disponibles en su campo histórico.

### Actualizar desde 18.0.1.0.9

1. Realice respaldo de base de datos **y filestore**.
2. Instale los archivos nuevos en la carpeta del módulo `custom_web_credito_conedera`.
3. Reinicie Odoo y actualice la lista de aplicaciones; actualice el módulo.
4. Confirme los tipos y requisitos en el menú de configuración.
5. Pruebe en el portal una solicitud de cada tipo, apruebe la solicitud, adjunte documentos de prueba y valide los contadores en la sección interna.
6. Revise la migración de expedientes previos antes de eliminar datos o archivos históricos. **No elimine** los campos legados durante esta actualización.

## Versión 18.0.1.2.0 — identificadores, estados y formulario paso a paso

- Los **nombres y apellidos** del propietario/representante inician vacíos en la solicitud, aunque el usuario haya iniciado sesión. El correo del usuario puede continuar precargado.
- Los **tipos de solicitante** poseen un **ID único permanente** (`code`): se conservan `natural` y `juridical` de los tipos precargados; los nuevos tipos reciben códigos de secuencia `TC-000001`, `TC-000002`, etc. El código aparece en su formulario/listado administrativo, no se puede modificar y las solicitudes/documentos siguen relacionados mediante Many2one, no nombres. Los tipos antiguos que carecían de código reciben uno al actualizar, sin cambiar los que ya existían.
- **Estados civiles**: catálogo nuevo `conedera.credit.marital.status`. Se precargan Soltero/a, Casado/a, Divorciado/a, Viudo/a, Unión de hecho y Otro. Puede añadir/renombrar, desactivar o eliminar estados no utilizados desde **Crédito CONEDERA > Estados civiles**. El antiguo `marital_status` se conserva para compatibilidad y se migra a `marital_status_id` sin alterar las solicitudes ya existentes. Los nuevos estados civiles también tienen código estable.
- **Etapas de solicitud**: continúan administrándose en **Crédito CONEDERA > Etapas del flujo** y ya no se limitan por una lista fija de nombres en la barra de estado. Se añade el atributo **Documentación recibida (acción automática)**, usado para localizar el destino de la acción sin depender de que el estado se llame literalmente “Documentación recibida”. La migración asigna el indicador a la etapa original. Si una etapa está vinculada con solicitudes, debe archivarse en vez de borrarla (integridad histórica).
- **Portal de cinco pasos**: (1) propietario/representante; (2) negocio/empresa; (3) actividad económica en relación de dependencia y referencias comerciales; (4) referencias personales y bancarias; (5) términos y condiciones. Navegación con **Siguiente/Anterior**, validación por paso y conservación de lo escrito mientras no se recargue la página. Las dos secciones legales se leen juntas bajo **Términos y condiciones**, pero cada una conserva sus casillas individuales de aceptación.
- **Envío bloqueado sin aceptaciones**: validación en navegador, controlador HTTP y `create()` del modelo. No se crea ningún registro hasta enviar la última pantalla con todas las aceptaciones afirmativas. Si hay validaciones de servidor, se devuelven los valores para que el usuario corrija la solicitud.
- El módulo no ofrece guardado de borrador entre sesiones o recargas de página: avanzar/retroceder se realiza dentro de un formulario sin crear todavía la solicitud. Se conservan los requisitos documentales configurables de la versión 18.0.1.1.0 y el registro por OTP de versiones anteriores.

### Instalación sobre versiones anteriores

1. Respalde base de datos y filestore.
2. Reemplace la carpeta del addon y reinicie Odoo.
3. Actualice el módulo **Portal de Solicitudes de Crédito CONEDERA** desde Aplicaciones.
4. Valide el catálogo de **Tipos de solicitante**, los **Estados civiles** y las **Etapas del flujo**.
5. Pruebe las cinco pantallas, el botón Anterior, una aceptación faltante, una solicitud correcta, su etapa y los archivos documentales.

Las verificaciones incluidas en el paquete son estáticas (compilación Python, parseo XML y sintaxis JavaScript, más inspección estructural del formulario). No se ha ejecutado una instancia de Odoo 18 ni probado la migración contra una base real.


### Versión 18.0.1.3.0
- Catálogo editable de tipos de vivienda, con identificadores estables (`VI-000001`), menú propio y migración de registros históricos.
- Cédula/RUC del solicitante: estructura y dígito verificador cuando corresponde; cédula opcional del cónyuge y celular de exactamente 10 dígitos. Validación en portal y ORM. No consulta en tiempo real al SRI/Registro Civil.
- Vehículos: dos filas predeterminadas en el formulario, botón «Agregar otro vehículo» (hasta 30 por solicitud para evitar envíos abusivos), almacenamiento One2many y migración idempotente de vehículos 1 y 2 de solicitudes anteriores.

## Novedades 18.0.1.4.0

- **Vehículos:** se muestra solo Vehículo 1. El botón «Agregar otro vehículo» crea Vehículo 2, 3, etc. (hasta 30 por formulario). Los datos se guardan en `vehicle_ids`.
- **Referencias:** se muestran tres líneas iniciales independientes para comerciales, personales y bancarias. Cada sección permite añadir filas (hasta 30) y eliminarlas; se guardan en `reference_ids`.
- **Documento del propietario:** `identification_type` es cédula ecuatoriana (10 dígitos con verificador), RUC (exactamente 13 numéricos) o cédula extranjera (exactamente 10 numéricos). El RUC del negocio exige 13 numéricos. Esta regla estructural no consulta ni garantiza existencia en el SRI.
- **Cónyuge:** los campos de nombre, identificación y profesión son obligatorios para los estados civiles marcados como **Requiere datos del cónyuge** (por defecto Casado/a y Unión de hecho); los demás tipos los ocultan y no los guardan. El documento admite cédula ecuatoriana válida o identificación extranjera numérica de 10 dígitos.
- **Ubicación:** `business_latitude` y `business_longitude` permiten escribir coordenadas o usar geolocalización del navegador mediante autorización. No se solicita ni genera enlace de Google Maps.
- **Permiso especial (actual):** el responsable autorizado habilita desde cada solicitud la actualización de datos, documentos o ambas opciones. El servidor valida la propiedad de la solicitud y los permisos individuales.
- **Verificación paralela:** `verification_status` es independiente de `stage_id`: Pendiente, En verificación, Verificado y No conforme. Para aprobar, se requiere Verificado, inspección realizada, dirección encontrada, dirección verificada y verificador identificado. Para rechazar, la verificación debe estar finalizada. La antigua etapa «Verificación» se archiva sin borrar su historial.
- **Una solicitud en trámite por usuario:** no se permite crear otra hasta que la anterior se apruebe o rechace; una solicitud ya aprobada que avanza al expediente documental sigue considerándose decidida. La comprobación se aplica también desde el ORM con bloqueo transaccional por usuario.

Instalación: respaldar base de datos y filestore, sustituir directorio, reiniciar Odoo y actualizar el módulo. Probar con una base de ensayo, especialmente si hay expedientes históricos, antes de llevarlo a producción.


## Versión 18.0.1.5.0 — corrección del historial, permisos y documentación

- El historial muestra **Actualizar** al propietario con el permiso especial y solicitud pendiente de decisión; abre los cinco pasos precargados con vehículos, referencias, datos de negocio y aceptaciones. Los demás usuarios solo pueden consultar **Ver detalle**.
- La versión 18.0.1.5.0 utilizó autorización global; el mecanismo vigente habilita cada solicitud individualmente. No se necesita ningún permiso global en el usuario de portal.
- En el backend, el botón inteligente **Acceso especial** requiere tanto el grupo de gestor de crédito como el permiso especial. Permite abrir datos (para corregir antes de la decisión), historial interno o expediente documental (solo tras aprobación).
- La carga documental depende ahora del estado real (Aprobada o Documentación recibida después de aprobar), no solo de un indicador booleano que pudo quedar activo. Se oculta en revisión, se bloquea la URL de carga incluso por acceso directo y se limpia el indicador obsoleto al actualizar el módulo. Se conservan los archivos históricos.
- Ningún usuario puede modificar una solicitud ajena desde el portal; una solicitud aprobada, denegada o con documentos ya recibidos no permite cambiar los datos iniciales desde el portal.


## 18.0.1.6.0 — Permisos por solicitud como Historial de Postulaciones

- A diferencia del permiso global anterior, cada solicitud almacena `portal_update_scope`: `none`, `history`, `documentation`, `both`. Por seguridad, los expedientes antiguos se mantienen sin permiso hasta que el responsable los habilite.
- En **Crédito CONEDERA → Solicitudes**, el usuario interno que pertenezca al grupo **Gestionar permisos de actualización del portal de crédito** ve el botón de cabecera **Habilitar permiso del portal** y el botón inteligente **Permiso portal**. Ambos abren el mismo asistente de autorización con botones **Habilitar/Cancelar**, como en `custom_web_hr_historial_postulaciones`.
- El responsable se puede autorizar desde **Ajustes → Usuarios → Puede habilitar permisos del portal de crédito**, o asignándole el grupo de administración correspondiente. Este grupo implica gestionar crédito y **no se otorga a usuarios portal**.
- **Historial:** aparecerá el botón **Actualizar** para la solicitud autorizada, mientras esté en trámite y no aprobada/rechazada. Se cargan los datos existentes del formulario de cinco pasos.
- **Documentación:** el primer ingreso de archivos se permite tras la aprobación; modificaciones posteriores de un expediente ya creado requieren el permiso `documentation` o `both` de esa solicitud (igual que el módulo de referencia). Sin aprobación no se permite cargar archivos ni mediante URL.
- Puede revocarse el permiso seleccionando **Ninguna sección**. Se guardan la fecha y el usuario responsable de la autorización.
- El permiso obsoleto de corrección global y su campo auxiliar quedan retirados a partir de 18.0.1.7.0.


## 18.0.1.7.0 — Retiro definitivo del grupo global obsoleto

- Se elimina del código el grupo de corrección global del portal y el campo auxiliar antiguo de `res.users`.
- Al **actualizar** una base que tenga versiones anteriores, `migrations/18.0.1.7.0/post-remove-old-portal-group.py` quita el grupo legado de `res.groups` y sus asignaciones a usuarios.
- Se mantiene sin cambios el grupo **Gestionar permisos de actualización del portal de crédito**, el botón inteligente **Permiso portal** y los permisos individuales de las solicitudes.
- La migración se ejecuta al actualizar el módulo por cambio de versión; no es suficiente reemplazar archivos sin actualizar el módulo en Odoo.


## Versión 18.0.1.8.0: permisos, colores y corrección de un solo uso
- El permiso de Historial permite actualizar una vez; al guardar se consume y la vista vuelve a `Ver detalle`. Si se concedieron ambas opciones, queda solo el permiso de documentación.
- Grupo **Usuario de crédito (revisión y verificación)**: lectura de datos del solicitante, movimiento de etapa y edición exclusiva de verificación de ubicación/negocio. El resto de modelos (catálogos, referencias, vehículos y documentos) queda en solo lectura. Las restricciones se comprueban en el ORM, además de las vistas.
- Grupo **Administrador de crédito (edición completa)**: gestión completa de solicitudes y catálogos, con pantalla **Crédito CONEDERA → Colores del portal** (colores HEX).
- Grupo **Gestionar permisos de actualización del portal de crédito**: para personal autorizado que concede permisos por solicitud; implica el rol administrador de crédito.
- Atención al actualizar: los usuarios que solo tenían el grupo anterior «Gestión de solicitudes» pasan a tener el rol de usuario limitado; para conservar la edición completa se debe asignar explícitamente **Administrador de crédito**.


## Corrección 18.0.1.8.1 (vistas Odoo 18)

- Corrige la definición de la vista de historial de etapas: los campos del modelo `conedera.credit.stage.history` no consultan el campo `credit_is_admin` de la solicitud principal.
- El historial permanece de solo lectura para todos los roles; el administrador gestiona la solicitud en su formulario y los empleados autorizados actualizan la etapa desde el encabezado.
- Mantiene la separación Administrador/Usuario de crédito, los colores configurables y la actualización del portal de un solo uso.


## Versión 18.0.1.8.2 — Solo coordenadas

- Eliminado `maps_url` del modelo, formulario del portal y vista administrativa. La base de datos mantiene sus registros históricos, sin mostrar ese campo.
- El detalle de la solicitud presenta latitud y longitud; se mantiene el botón «Usar mi ubicación actual».
- El envío a cobranzas, cuando se registran coordenadas nuevas, incluye únicamente latitud y longitud.
- Conservadas las validaciones y restricciones de acceso del módulo anterior.

## Corrección 18.0.1.8.3: ubicación automática

El botón «Usar mi ubicación actual» distingue entre sitio sin HTTPS, permiso denegado, ubicación no disponible y tiempo agotado. La captura automática requiere HTTPS válido (o localhost para pruebas), permiso de ubicación del navegador y servicios de ubicación activos en el dispositivo. No depende de Google Maps y continúa permitiendo ingresar latitud y longitud manualmente.
