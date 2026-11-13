# API de ALUMAT para el frontend

Guía para conectar el frontend al backend. Resume todos los endpoints disponibles, los campos que se envían y se reciben, y cómo autenticarse. Para el detalle completo de productos y pedidos, ver `CONTRATO_API_PRODUCTOS.md` y `CONTRATO_API_PEDIDOS.md`.

## 1. Conexión

| Dato | Valor |
|---|---|
| URL base en desarrollo | `http://localhost:8001` (puerto `APP_PORT` del `.env`) |
| Prefijo de la API | `/api/` |
| Formato | JSON, UTF-8 (`Content-Type: application/json`) |
| Autenticación | sesión de Django (cookie `sessionid`) + token CSRF |
| Paginación | no hay: los listados devuelven un arreglo con todos los registros |
| Idioma de los mensajes | español (`es-ar`) |

### Mismo origen (importante)

El backend **no tiene CORS configurado** y usa cookies de sesión. El frontend tiene que llegar al backend **desde el mismo origen**. En desarrollo, lo más simple es un proxy en el servidor del frontend. Por ejemplo, con Vite:

```js
// vite.config.js
export default {
  server: {
    proxy: {
      "/api": "http://localhost:8001",
      "/cuentas": "http://localhost:8001",
    },
  },
};
```

Así el navegador ve todo como `http://localhost:5173/...` y las cookies funcionan sin CORS.

### Sesión e inicio de sesión

No hay un endpoint JSON de login: el login es el formulario de Django en `/cuentas/ingresar/`. Desde el frontend se usa así:

1. `GET /cuentas/ingresar/` → el backend deja la cookie `csrftoken`.
2. `POST /cuentas/ingresar/` como formulario (`application/x-www-form-urlencoded`) con `username`, `password` y `csrfmiddlewaretoken` (el valor de la cookie `csrftoken`).
   - Login correcto: responde `302` con redirección a `/` y deja la cookie `sessionid`.
   - Login incorrecto: responde `200` con la página del formulario y el error.
   - 5 intentos fallidos bloquean el usuario durante 15 minutos.
3. Cerrar sesión: `POST /cuentas/salir/` con el token CSRF (con `GET` no funciona).

La sesión dura 8 horas y se cierra al cerrar el navegador. Solo pueden entrar usuarios **aprobados** por el administrador (el registro está en `/cuentas/registrarse/`).

### Token CSRF en cada escritura

Todo `POST`, `PUT`, `PATCH` y `DELETE` a la API tiene que llevar el encabezado `X-CSRFToken` con el valor de la cookie `csrftoken`, y enviar las cookies:

```js
function leerCookie(nombre) {
  return document.cookie.split("; ").find((c) => c.startsWith(nombre + "="))?.split("=")[1];
}

async function api(metodo, url, datos) {
  const r = await fetch(url, {
    method: metodo,
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": leerCookie("csrftoken"),
    },
    body: datos ? JSON.stringify(datos) : undefined,
  });
  const cuerpo = r.status === 204 ? null : await r.json();
  if (!r.ok) throw { status: r.status, errores: cuerpo };
  return cuerpo;
}

// Ejemplos
await api("GET", "/api/clientes/?activo=true");
await api("POST", "/api/pedidos/", { id_cliente: 7 });
await api("PATCH", "/api/pedidos/15/", { estado: "en_proceso" });
```

## 2. Roles

| Rol | Cómo se reconoce | Puede |
|---|---|---|
| Administrador | superusuario | todo |
| Vendedor | grupo `Vendedor` | consultar y modificar |
| Dueño | grupo `Dueño` | solo consultar (`GET`) |

Si el Dueño intenta `POST`, `PUT`, `PATCH` o `DELETE`, la API responde:

```json
403 { "detail": "El Dueño solo puede consultar información." }
```

Los grupos se crean con `docker compose exec web python manage.py crear_roles` y se asignan desde `/admin/`.

## 3. Errores

| Código | Cuándo | Cuerpo |
|---|---|---|
| `400` | datos inválidos | `{ "campo": ["mensaje", ...] }`; los errores generales van en `non_field_errors` |
| `403` | sin sesión, o el Dueño intentando modificar | `{ "detail": "..." }` |
| `404` | el registro no existe | `{ "detail": "No encontrado." }` |
| `405` | método no ofrecido (por ejemplo `DELETE` de un cliente) | `{ "detail": "..." }` |
| `409` | el estado actual no permite la operación | `{ "detail": "..." }` |

Sugerencia para el frontend: en un `400`, mostrar cada mensaje junto al campo con el mismo nombre del formulario.

## 4. Resumen de endpoints

| Método | Endpoint | Descripción |
|---|---|---|
| **Clientes** | | |
| `GET` | `/api/clientes/` | Lista (filtros: `activo`, `tipo_cliente`) |
| `POST` | `/api/clientes/` | Registra |
| `GET` | `/api/clientes/{id_cliente}/` | Consulta |
| `PUT` / `PATCH` | `/api/clientes/{id_cliente}/` | Modifica / desactiva con `{"activo": false}` |
| **Productos y diseños** | | |
| `GET` | `/api/productos/` | Lista (filtros: `activo`, `tipo_abertura`, `q`) |
| `POST` | `/api/productos/` | Registra |
| `GET` | `/api/productos/{id_producto}/` | Consulta |
| `PUT` / `PATCH` | `/api/productos/{id_producto}/` | Modifica / desactiva |
| `GET` | `/api/productos/{id_producto}/disenos/` | Diseños del producto (filtro: `activo`) |
| `GET` | `/api/disenos/` | Lista (filtros: `id_producto`, `activo`) |
| `POST` | `/api/disenos/` | Registra |
| `GET` | `/api/disenos/{id_diseno}/` | Consulta |
| `PUT` / `PATCH` | `/api/disenos/{id_diseno}/` | Modifica / desactiva |
| **Pedidos y detalles** | | |
| `GET` | `/api/pedidos/` | Lista (filtros: `id_cliente`, `id_usuario`, `estado`, `fecha_desde`, `fecha_hasta`) |
| `POST` | `/api/pedidos/` | Registra |
| `GET` | `/api/pedidos/{id_pedido}/` | Consulta |
| `PUT` / `PATCH` | `/api/pedidos/{id_pedido}/` | Modifica (si está pendiente) o avanza el estado |
| `GET` | `/api/pedidos/{id_pedido}/detalles/` | Lista los detalles |
| `POST` | `/api/pedidos/{id_pedido}/detalles/` | Agrega un detalle |
| `GET` | `/api/pedidos/{id_pedido}/detalles/{id_detalle_pedido}/` | Consulta un detalle |
| `PUT` / `PATCH` | `/api/pedidos/{id_pedido}/detalles/{id_detalle_pedido}/` | Modifica un detalle |
| `DELETE` | `/api/pedidos/{id_pedido}/detalles/{id_detalle_pedido}/` | Quita un detalle (`204`) |
| **Cajas y aperturas** | | |
| `GET` | `/api/cajas/` | Lista (filtro: `activa`) |
| `POST` | `/api/cajas/` | Registra |
| `GET` | `/api/cajas/{id_caja}/` | Consulta |
| `PUT` / `PATCH` | `/api/cajas/{id_caja}/` | Modifica / desactiva con `{"activa": false}` |
| `GET` | `/api/cajas/{id_caja}/aperturas/` | Aperturas de la caja |
| `GET` | `/api/aperturas/` | Lista (filtros: `id_caja`, `id_usuario`, `estado`) |
| `POST` | `/api/aperturas/` | Abre una caja |
| `GET` | `/api/aperturas/{id_apertura}/` | Consulta |
| **Movimientos y cierres** | | |
| `GET` | `/api/movimiento-caja/` | Lista |
| `POST` | `/api/movimiento-caja/` | Registra un movimiento |
| `GET` | `/api/movimiento-caja/{id_movimiento}/` | Consulta |
| `GET` | `/api/cierre-caja/` | Lista |
| `POST` | `/api/cierre-caja/` | Cierra una apertura |
| `GET` | `/api/cierre-caja/{id_cierre}/` | Consulta |

Ningún recurso tiene `DELETE`, salvo los detalles de un pedido pendiente: los registros se desactivan, se conservan como historial o se cierran.

## 5. Recursos

En las tablas, **RO** significa solo lectura: sale en la respuesta, pero si el frontend lo envía se ignora.

### Clientes — `/api/clientes/`

| Campo | Tipo | Notas |
|---|---|---|
| `id_cliente` | entero | RO |
| `tipo_cliente` | `"particular"` \| `"empresa"` | obligatorio |
| `nombre`, `apellido` | texto (máx. 100) | obligatorios si es particular; vacíos si es empresa |
| `dni` | texto | obligatorio si es particular; 7 u 8 dígitos (acepta puntos); único |
| `razon_social` | texto (máx. 150) | obligatoria si es empresa; vacía si es particular |
| `cuit` | texto | obligatorio si es empresa; 11 dígitos con dígito verificador válido; se devuelve como `XX-XXXXXXXX-X`; único |
| `direccion` | texto (máx. 200) | opcional |
| `telefono` | texto (máx. 30) | opcional; números, espacios, guiones, paréntesis o `+` |
| `correo_electronico` | email (máx. 150) | opcional; se guarda en minúsculas |
| `activo` | booleano | por defecto `true` |
| `fecha_registro` | fecha y hora | RO |

Filtros: `?activo=true|false`, `?tipo_cliente=particular|empresa`.

```json
POST /api/clientes/
{ "tipo_cliente": "empresa", "razon_social": "Aluminios SA", "cuit": "20-12345678-6" }

201
{
  "id_cliente": 3, "tipo_cliente": "empresa", "nombre": "", "apellido": "", "dni": "",
  "razon_social": "Aluminios SA", "cuit": "20-12345678-6", "direccion": "",
  "telefono": "", "correo_electronico": "", "activo": true,
  "fecha_registro": "2026-11-13T19:30:00.123456-03:00"
}
```

### Productos — `/api/productos/`

| Campo | Tipo | Notas |
|---|---|---|
| `id_producto` | entero | RO |
| `nombre` | texto (máx. 100) | obligatorio; no se repite con el mismo `tipo_abertura` (sin importar mayúsculas) |
| `tipo_abertura` | texto (máx. 100) | obligatorio |
| `descripcion` | texto | opcional |
| `activo` | booleano | por defecto `true` |

Filtros: `?activo=`, `?tipo_abertura=` (coincidencia exacta), `?q=` (busca en el nombre).

### Diseños — `/api/disenos/`

| Campo | Tipo | Notas |
|---|---|---|
| `id_diseno` | entero | RO |
| `id_producto` | entero | obligatorio al crear; no se puede cambiar después; el producto tiene que estar activo |
| `nombre_diseno` | texto (máx. 100) | obligatorio; no se repite dentro del producto |
| `activo` | booleano | por defecto `true` |

Filtros: `?id_producto=`, `?activo=`.

### Pedidos — `/api/pedidos/`

| Campo | Tipo | Notas |
|---|---|---|
| `id_pedido` | entero | RO |
| `id_cliente` | entero | obligatorio; el cliente tiene que estar activo |
| `id_usuario` | entero | RO: lo pone el servidor con el usuario de la sesión |
| `fecha_pedido` | fecha y hora ISO 8601 | opcional (por defecto, ahora); no puede ser futura |
| `estado` | `"pendiente"` \| `"en_proceso"` \| `"finalizado"` | nace `pendiente`; al crear se ignora |
| `observaciones` | texto | opcional |

Reglas:
- El estado avanza de a un paso: `pendiente` → `en_proceso` → `finalizado`. Retroceder o saltear un paso da `400`.
- Solo un pedido `pendiente` permite cambiar sus datos y sus detalles. Si no, `409`.
- Un pedido `finalizado` no admite cambios (`409`).

Filtros: `?id_cliente=`, `?id_usuario=`, `?estado=`, `?fecha_desde=AAAA-MM-DD`, `?fecha_hasta=AAAA-MM-DD` (incluyen el día completo).

```json
PATCH /api/pedidos/15/
{ "estado": "en_proceso" }

200
{
  "id_pedido": 15, "id_cliente": 7, "id_usuario": 4,
  "fecha_pedido": "2026-10-29T10:30:00-03:00",
  "estado": "en_proceso", "observaciones": ""
}
```

### Detalles del pedido — `/api/pedidos/{id_pedido}/detalles/`

| Campo | Tipo | Notas |
|---|---|---|
| `id_detalle_pedido` | entero | RO |
| `id_pedido` | entero | RO: se toma de la URL |
| `id_diseno` | entero | obligatorio; el diseño y su producto tienen que estar activos. El producto se obtiene del diseño |
| `ancho`, `alto` | decimal, 2 decimales (texto `"1200.50"` o número) | obligatorios, mayores a 0, hasta `9999.99` |
| `cantidad` | entero | mayor a 0; por defecto `1` |
| `tipo_vidrio` | clave de la lista | opcional |
| `color_aluminio` | clave de la lista | **obligatorio** |
| `tipo_revestimiento` | clave de la lista | opcional |
| `observaciones` | texto | opcional |

Listas (se envía la clave, se muestra la etiqueta):

| Campo | Clave → Etiqueta |
|---|---|
| `tipo_vidrio` | `simple_4` → Simple 4 mm · `dvh_4_9_4` → DVH 4+9+4 · `laminado_3_3` → Laminado 3+3 · `templado_8` → Templado 8 mm |
| `color_aluminio` | `blanco` → Blanco · `negro` → Negro · `natural` → Natural · `bronce` → Bronce |
| `tipo_revestimiento` | `simil_madera` → Símil madera · `texturado` → Texturado |

La API no expone las listas: por ahora el frontend las tiene que tener copiadas (son valores de ejemplo a confirmar con ALUMAT).

Si se repite un detalle idéntico (mismo diseño, medidas, vidrio, color y revestimiento) en el mismo pedido, la respuesta es `400`: hay que modificar la cantidad del que ya existe.

```json
POST /api/pedidos/15/detalles/
{ "id_diseno": 3, "ancho": "1500.00", "alto": "1100.50", "cantidad": 2,
  "tipo_vidrio": "dvh_4_9_4", "color_aluminio": "blanco" }

201
{
  "id_detalle_pedido": 31, "id_pedido": 15, "id_diseno": 3,
  "ancho": "1500.00", "alto": "1100.50", "cantidad": 2,
  "tipo_vidrio": "dvh_4_9_4", "color_aluminio": "blanco",
  "tipo_revestimiento": "", "observaciones": ""
}
```

### Cajas — `/api/cajas/`

| Campo | Tipo | Notas |
|---|---|---|
| `id_caja` | entero | RO |
| `nombre_caja` | texto (máx. 100) | obligatorio; único sin importar mayúsculas |
| `activa` | booleano | por defecto `true` |

Filtro: `?activa=true|false`.

### Aperturas de caja — `/api/aperturas/`

| Campo | Tipo | Notas |
|---|---|---|
| `id_apertura` | entero | RO |
| `id_caja` | entero | obligatorio; la caja tiene que estar activa y sin otra apertura abierta |
| `id_usuario` | entero | RO: el usuario de la sesión |
| `fecha_hora_apertura` | fecha y hora | RO: la pone el servidor |
| `monto_inicial` | decimal | obligatorio, mayor o igual a 0 |
| `estado` | `"abierta"` \| `"cerrada"` | RO: nace `abierta` y se cierra con `POST /api/cierre-caja/` |

Una apertura no se modifica ni se borra. Filtros: `?id_caja=`, `?id_usuario=`, `?estado=`.

### Movimientos de caja — `/api/movimiento-caja/`

| Campo | Tipo | Notas |
|---|---|---|
| `id_movimiento` | entero | RO |
| `id_apertura` | entero | obligatorio; la apertura tiene que estar abierta (si no, `409`) |
| `id_cobro` | entero o `null` | opcional; solo un cobro en efectivo, y una sola vez |
| `id_usuario` | entero | RO |
| `fecha_movimiento` | fecha y hora | RO |
| `tipo_movimiento` | `"entrada"` \| `"salida"` | obligatorio; un cobro solo puede ser `entrada` |
| `concepto` | texto (máx. 200) | obligatorio |
| `monto` | decimal | obligatorio, mayor a 0 |

Los movimientos no se modifican ni se borran.

### Cierres de caja — `/api/cierre-caja/`

Solo se envían `id_apertura` y `efectivo_contado`; el resto lo calcula el servidor.

| Campo | Tipo | Notas |
|---|---|---|
| `id_cierre` | entero | RO |
| `id_apertura` | entero | obligatorio; tiene que estar abierta (si no, `409`) |
| `id_usuario` | entero | RO |
| `fecha_hora_cierre` | fecha y hora | RO |
| `total_ingresos`, `total_egresos` | decimal | RO: suma de entradas y salidas de la apertura |
| `saldo_esperado` | decimal | RO: `monto_inicial + total_ingresos − total_egresos` |
| `efectivo_contado` | decimal | obligatorio, mayor o igual a 0 |
| `diferencia` | decimal | RO: `efectivo_contado − saldo_esperado` |

Al cerrar, la apertura pasa a `cerrada`. El cierre es definitivo: `PUT`, `PATCH` y `DELETE` responden `405`.

```json
POST /api/cierre-caja/
{ "id_apertura": 2, "efectivo_contado": "1150.00" }

201
{
  "id_cierre": 1, "id_apertura": 2, "id_usuario": 4,
  "fecha_hora_cierre": "2026-11-13T20:00:00-03:00",
  "total_ingresos": "300.00", "total_egresos": "100.00",
  "saldo_esperado": "1200.00", "efectivo_contado": "1150.00", "diferencia": "-50.00"
}
```

Los importes y las medidas se devuelven como **texto** (`"1200.00"`), no como número, para no perder precisión. Conviértanlos al mostrarlos.

## 6. Lo que falta para conectar el frontend completo

Hoy el backend no tiene estas piezas; conviene agregarlas antes de armar esas pantallas:

| Falta | Para qué | Propuesta |
|---|---|---|
| Endpoint del usuario actual | saber quién está logueado y su rol, para mostrar u ocultar botones | `GET /api/yo/` → `{ id, username, es_admin, rol }` |
| Login y logout JSON | no depender del formulario HTML de Django | `POST /api/sesion/` y `DELETE /api/sesion/` |
| Endpoint para el token CSRF | obtener la cookie `csrftoken` sin pedir una página HTML | `GET /api/csrf/` con `ensure_csrf_cookie` |
| API de ventas y cobros | registrar ventas y cobros desde el frontend; hoy solo existe `ventas/services.py → registrar_cobro()` | `/api/ventas/` y `/api/ventas/{id}/cobros/` |
| Listas de opciones | no copiar en el frontend las listas de vidrio, color, revestimiento y estados | `GET /api/opciones/` |
| CORS | solo si el frontend se sirve desde otro dominio en producción | `django-cors-headers` |
| Paginación | listados grandes | `PageNumberPagination` de DRF |
