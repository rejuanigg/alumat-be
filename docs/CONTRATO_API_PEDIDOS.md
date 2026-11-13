# Contrato de API: Gestión de Pedidos

Sección del contrato de API de ALUMAT correspondiente al Proceso 3: Gestión de Pedidos (PEDIDO y DETALLE_PEDIDO).

Sigue las mismas convenciones que [Gestión de Productos y Diseños](CONTRATO_API_PRODUCTOS.md).

## Convenciones generales

- **URL base:** `/api/`
- **Formato:** JSON (`Content-Type: application/json`), con codificación UTF-8.
- **Fechas:** `fecha_pedido` tiene fecha y hora, en formato ISO 8601 (`AAAA-MM-DDTHH:MM:SS` con zona horaria). Los filtros `fecha_desde` y `fecha_hasta` usan solo la fecha (`AAAA-MM-DD`).
- **Medidas:** `ancho` y `alto` son números decimales con 2 decimales (hasta `9999.99`), mayores a 0.
- **Nombres de campos:** iguales a los del diccionario de datos (`id_pedido`, `id_cliente`, etc.).
- **Autenticación:** todos los endpoints requieren un usuario autenticado. Se usa la sesión de Django (el mismo login del sitio). Si no hay sesión válida, se responde `403` con `{"detail": "Las credenciales de autenticación no se proveyeron."}`.
- **Roles:** el Administrador (superusuario) y el Vendedor consultan y modifican; el Dueño solo consulta (`GET`). Si el Dueño intenta modificar, se responde `403` con `{"detail": "El Dueño solo puede consultar información."}`.
- **Sin borrado de pedidos:** un pedido no se elimina; se conserva como historial. `DELETE` sobre un pedido responde `405 Method Not Allowed`.

## Modelo de datos

### PEDIDO (tabla `pedidos`)

| Atributo | Tipo | Restricciones |
|---|---|---|
| `id_pedido` | entero | **PK**, autoincremental, solo lectura |
| `id_cliente` | entero | **FK → CLIENTE**, obligatorio |
| `id_usuario` | entero | **FK → USUARIO** (Django Auth), solo lectura: lo asigna la API con el usuario autenticado |
| `fecha_pedido` | fecha y hora | opcional al registrar; por defecto, el momento actual. No puede ser posterior al momento actual |
| `estado` | texto | uno de los [estados permitidos](#estados-del-pedido); por defecto `pendiente` |
| `observaciones` | texto | opcional (por defecto `""`) |

### DETALLE_PEDIDO (tabla `detalle_pedidos`)

| Atributo | Tipo | Restricciones |
|---|---|---|
| `id_detalle_pedido` | entero | **PK**, autoincremental, solo lectura |
| `id_pedido` | entero | **FK → PEDIDO**, solo lectura: se toma de la URL |
| `id_diseno` | entero | **FK → DISEÑO**, obligatorio. El producto se obtiene a través del diseño |
| `ancho` | decimal (6,2) | obligatorio, mayor a 0 |
| `alto` | decimal (6,2) | obligatorio, mayor a 0 |
| `cantidad` | entero | mayor a 0; por defecto `1` |
| `tipo_vidrio` | texto (máx. 100) | condicional (puede ir vacío); uno de la [lista de vidrios](#listas-predefinidas) |
| `color_aluminio` | texto (máx. 50) | obligatorio; uno de la [lista de colores](#listas-predefinidas) |
| `tipo_revestimiento` | texto (máx. 100) | condicional (puede ir vacío); uno de la [lista de revestimientos](#listas-predefinidas) |
| `observaciones` | texto | opcional (por defecto `""`) |

### Listas predefinidas

Se envía y se guarda la **clave**, en minúsculas. Son valores de ejemplo y quedan a confirmar con ALUMAT.

| Campo | Clave | Etiqueta |
|---|---|---|
| `tipo_vidrio` | `simple_4` | Simple 4 mm |
| | `dvh_4_9_4` | DVH 4+9+4 |
| | `laminado_3_3` | Laminado 3+3 |
| | `templado_8` | Templado 8 mm |
| `color_aluminio` | `blanco` | Blanco |
| | `negro` | Negro |
| | `natural` | Natural |
| | `bronce` | Bronce |
| `tipo_revestimiento` | `simil_madera` | Símil madera |
| | `texturado` | Texturado |

Cualquier otro valor se rechaza con `400`.

### Relaciones

```
CLIENTE  1 ──< N  PEDIDO  N >── 1  USUARIO
                    1
                    │
                    N
               DETALLE_PEDIDO  N >── 1  DISEÑO  N >── 1  PRODUCTO
```

- Un CLIENTE tiene muchos PEDIDOS, y cada PEDIDO es de un único CLIENTE.
- Un USUARIO registra muchos PEDIDOS, y cada PEDIDO lo registra un único USUARIO.
- Un PEDIDO tiene muchos DETALLES, y cada DETALLE pertenece a un único PEDIDO.
- Cada DETALLE referencia un DISEÑO; el PRODUCTO es el de ese diseño.

### Estados del pedido

| Valor | Etiqueta | Significado |
|---|---|---|
| `pendiente` | Pendiente | registrado, todavía se puede modificar |
| `en_proceso` | En proceso | en fabricación |
| `finalizado` | Finalizado | terminado; ya no admite cambios |

El estado avanza solo hacia adelante y de a un paso: `pendiente` → `en_proceso` → `finalizado`. No hay estado cancelado. Cualquier otro valor se rechaza con `400`.

### Reglas de integridad que la API hace cumplir

| Regla | Respuesta si se incumple |
|---|---|
| El cliente debe existir | `400`, error en `id_cliente` |
| El usuario debe existir | se toma del usuario autenticado; sin sesión, `403` |
| El detalle debe pertenecer a un pedido existente | `404` (el `id_pedido` de la URL no existe) |
| El diseño debe existir | `400`, error en `id_diseno` |
| El diseño y su producto deben estar activos | `400`, error en `id_diseno` |
| Estado dentro de los valores permitidos | `400`, error en `estado` |
| El estado no retrocede ni saltea pasos | `400`, error en `estado` |
| Medidas y cantidad mayores a 0 | `400`, error en el campo |
| Vidrio, color y revestimiento dentro de sus listas | `400`, error en el campo |
| No borrar registros padre con dependencias | no hay `DELETE` de pedidos (`405`); los clientes, productos y diseños usados en pedidos no se pueden borrar |
| Pedido no modificable fuera de `pendiente` | `409`, ver [Reglas de modificación](#reglas-de-modificación) |

## Endpoints

### Resumen

| MÉTODO HTTP | ENDPOINT | DESCRIPCIÓN |
|---|---|---|
| `GET` | `/api/pedidos/` | Lista los pedidos (filtros: `id_cliente`, `id_usuario`, `estado`, `fecha_desde`, `fecha_hasta`) |
| `POST` | `/api/pedidos/` | Registra un pedido para un cliente existente, a nombre del usuario autenticado |
| `GET` | `/api/pedidos/{id_pedido}/` | Consulta un pedido |
| `PUT` | `/api/pedidos/{id_pedido}/` | Modifica todos los campos editables de un pedido pendiente |
| `PATCH` | `/api/pedidos/{id_pedido}/` | Modifica algunos campos de un pedido pendiente o avanza su estado |
| `GET` | `/api/pedidos/{id_pedido}/detalles/` | Lista los detalles de un pedido |
| `POST` | `/api/pedidos/{id_pedido}/detalles/` | Agrega un detalle a un pedido pendiente |
| `GET` | `/api/pedidos/{id_pedido}/detalles/{id_detalle_pedido}/` | Consulta un detalle del pedido |
| `PUT` | `/api/pedidos/{id_pedido}/detalles/{id_detalle_pedido}/` | Modifica todos los campos editables de un detalle |
| `PATCH` | `/api/pedidos/{id_pedido}/detalles/{id_detalle_pedido}/` | Modifica algunos campos de un detalle |
| `DELETE` | `/api/pedidos/{id_pedido}/detalles/{id_detalle_pedido}/` | Quita un detalle de un pedido pendiente |

`PUT` reemplaza todos los campos editables; `PATCH` modifica solo los que se envían.

Los detalles se gestionan siempre **dentro de su pedido** (`/api/pedidos/{id_pedido}/detalles/`). Así un detalle no puede crearse sin un pedido existente ni pasarse a otro pedido.

### Reglas de modificación

- Solo un pedido en estado `pendiente` permite modificar sus datos y agregar, modificar o quitar detalles.
- Si el pedido está en otro estado, la API responde `409 Conflict`. La excepción es el cambio de `estado` para avanzarlo un paso (`pendiente` → `en_proceso` → `finalizado`).
- Un pedido `finalizado` no admite cambios.

### Pedidos

#### `GET /api/pedidos/`

Lista los pedidos, del más reciente al más antiguo. Filtros opcionales:

| Parámetro | Ejemplo | Descripción |
|---|---|---|
| `id_cliente` | `?id_cliente=7` | pedidos de un cliente |
| `id_usuario` | `?id_usuario=4` | pedidos registrados por un usuario |
| `estado` | `?estado=pendiente` | pedidos en un estado |
| `fecha_desde` / `fecha_hasta` | `?fecha_desde=2026-10-01&fecha_hasta=2026-10-31` | rango del día de `fecha_pedido`, ambos extremos incluidos (el día completo) |

Respuesta `200`: lista de pedidos (ver [JSON de PEDIDO](#json-de-pedido)).

#### `POST /api/pedidos/`

Cuerpo:

```json
{
  "id_cliente": 7,
  "fecha_pedido": "2026-10-29T10:30:00-03:00",
  "observaciones": "Entregar por la mañana."
}
```

- `id_usuario` no se envía: la API asigna el usuario autenticado.
- `estado` no se envía: el pedido nace `pendiente`.
- `fecha_pedido` es opcional; si no se envía, se usa el momento actual. No puede ser posterior al momento actual.

Respuestas:
- `201`: el pedido creado.
- `400`: el `id_cliente` no existe o está inactivo, o la fecha es inválida o futura.

#### `GET /api/pedidos/{id_pedido}/`

- `200`: el pedido.
- `404`: no existe.

#### `PUT` / `PATCH /api/pedidos/{id_pedido}/`

Campos editables: `id_cliente`, `fecha_pedido`, `estado` y `observaciones`. `id_pedido` e `id_usuario` son de solo lectura.

Ejemplo para avanzar el estado:

```json
{ "estado": "en_proceso" }
```

- `200`: el pedido actualizado.
- `400`: datos inválidos, estado no permitido, o el estado retrocede o saltea un paso.
- `404`: no existe.
- `409`: el pedido no está `pendiente` y se intenta cambiar algo que no es el estado; el pedido está `finalizado`; o el pedido cambió mientras se editaba.

### Detalles del pedido

#### `GET /api/pedidos/{id_pedido}/detalles/`

- `200`: lista de detalles del pedido. Todos tienen el mismo `id_pedido`; si no tiene detalles, devuelve `[]`.
- `404`: el pedido no existe.

#### `POST /api/pedidos/{id_pedido}/detalles/`

Cuerpo:

```json
{
  "id_diseno": 3,
  "ancho": "1500.00",
  "alto": "1100.50",
  "cantidad": 2,
  "tipo_vidrio": "dvh_4_9_4",
  "color_aluminio": "blanco",
  "tipo_revestimiento": "",
  "observaciones": "Con mosquitero."
}
```

- `201`: el detalle creado, con `id_detalle_pedido` e `id_pedido`.
- `400`: dato inválido (ver el ejemplo de abajo).
- `404`: el pedido no existe.
- `409`: el pedido no está `pendiente`.

Si el valor no está en la lista, la respuesta es `400`:

```json
{
  "color_aluminio": ["\"rojo\" no es una elección válida."]
}
```

#### `GET /api/pedidos/{id_pedido}/detalles/{id_detalle_pedido}/`

- `200`: el detalle.
- `404`: el pedido o el detalle no existen, o el detalle es de otro pedido.

#### `PUT` / `PATCH /api/pedidos/{id_pedido}/detalles/{id_detalle_pedido}/`

Campos editables: todos salvo `id_detalle_pedido` e `id_pedido`. Si se cambia `id_diseno`, se vuelve a comprobar que el diseño y su producto estén activos.

- `200`: el detalle actualizado.
- `400`: datos inválidos.
- `404`: no existe.
- `409`: el pedido no está `pendiente`.

#### `DELETE /api/pedidos/{id_pedido}/detalles/{id_detalle_pedido}/`

Quita una línea de un pedido `pendiente`. Un detalle no tiene registros que dependan de él, así que se puede borrar.

- `204`: eliminado, sin cuerpo.
- `404`: no existe.
- `409`: el pedido no está `pendiente`.

## JSON de ejemplo

Los ejemplos son coherentes entre sí y con el contrato de productos:
- El detalle 31 pertenece al pedido 15.
- El pedido 15 es del cliente 7 y lo registró el usuario 4.
- El diseño 3 ("Dos hojas con mosquitero") pertenece al producto 1 ("Ventana corrediza"), igual que en el ejemplo de productos.

### JSON de PEDIDO

Registro devuelto por `GET /api/pedidos/15/`:

```json
{
  "id_pedido": 15,
  "id_cliente": 7,
  "id_usuario": 4,
  "fecha_pedido": "2026-10-29T10:30:00-03:00",
  "estado": "pendiente",
  "observaciones": "Entregar por la mañana."
}
```

### JSON de DETALLE_PEDIDO

Registro devuelto por `GET /api/pedidos/15/detalles/31/`:

```json
{
  "id_detalle_pedido": 31,
  "id_pedido": 15,
  "id_diseno": 3,
  "ancho": "1500.00",
  "alto": "1100.50",
  "cantidad": 2,
  "tipo_vidrio": "dvh_4_9_4",
  "color_aluminio": "blanco",
  "tipo_revestimiento": "",
  "observaciones": "Con mosquitero."
}
```

## Errores

| Código | Cuándo |
|---|---|
| `400 Bad Request` | datos inválidos, referencia inexistente, valor fuera de una lista o avance de estado no permitido |
| `403 Forbidden` | sin autenticación, o el usuario no tiene permiso para la operación (por ejemplo, el Dueño intentando modificar) |
| `404 Not Found` | el pedido o el detalle no existe |
| `405 Method Not Allowed` | `DELETE` sobre un pedido |
| `409 Conflict` | operación no permitida por el estado del pedido |

Formato de error de validación (`400`): un objeto con el campo y la lista de mensajes.

```json
{
  "ancho": ["Asegúrese de que este valor es mayor o igual a 0.01."]
}
```

Formato de los demás errores:

```json
{
  "detail": "El pedido no está pendiente y no puede modificarse."
}
```

## Decisiones a confirmar con el equipo

- **Listas de vidrio, color y revestimiento:** los valores actuales son de ejemplo; hay que confirmarlos con ALUMAT.
- **Medidas:** falta confirmar la unidad (el sistema guarda decimales con 2 decimales) y si hay mínimos o máximos por tipo de producto.
- **Campos condicionales:** `tipo_vidrio` y `tipo_revestimiento` pueden ir vacíos; falta definir en qué casos son obligatorios.
- **CLIENTE:** el contrato solo usa `id_cliente`. Si las respuestas de pedido tienen que incluir datos del cliente (nombre, etc.), hay que agregarlos.
- **Paginación:** si los listados se paginan, definir el formato (por ejemplo `count`, `next`, `previous`, `results`).
