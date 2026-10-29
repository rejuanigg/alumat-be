w# Contrato de API: Gestión de Pedidos

Sección del contrato de API de ALUMAT correspondiente al Proceso 3: Gestión de Pedidos (PEDIDO y DETALLE_PEDIDO).

Sigue las mismas convenciones que [Gestión de Productos y Diseños](CONTRATO_API_PRODUCTOS.md).

## Convenciones generales

- **URL base:** `/api/`
- **Formato:** JSON (`Content-Type: application/json`), con codificación UTF-8.
- **Fechas:** formato ISO 8601 (`AAAA-MM-DD`).
- **Medidas:** `ancho` y `alto` en **milímetros**, números enteros.
- **Nombres de campos:** iguales a los del diccionario de datos (`id_pedido`, `id_cliente`, etc.).
- **Autenticación:** todos los endpoints requieren un usuario autenticado. Se usa la sesión de Django (el mismo login del sitio). Si no hay sesión válida, se responde `403` con `{"detail": "Las credenciales de autenticación no se proveyeron."}`.
- **Sin borrado de pedidos:** un pedido no se elimina, se cancela. `DELETE` sobre un pedido responde `405 Method Not Allowed`.

## Modelo de datos

### PEDIDO

| Atributo | Tipo | Restricciones |
|---|---|---|
| `id_pedido` | entero | **PK**, autoincremental, solo lectura |
| `id_cliente` | entero | **FK → CLIENTE**, obligatorio |
| `id_usuario` | entero | **FK → USUARIO** (Django Auth), solo lectura: lo asigna la API con el usuario autenticado |
| `fecha_pedido` | fecha | opcional al registrar; por defecto, la fecha del día |
| `estado` | texto | uno de los [estados permitidos](#estados-del-pedido); por defecto `pendiente` |
| `observaciones` | texto | opcional (por defecto `""`) |

### DETALLE_PEDIDO

| Atributo | Tipo | Restricciones |
|---|---|---|
| `id_detalle_pedido` | entero | **PK**, autoincremental, solo lectura |
| `id_pedido` | entero | **FK → PEDIDO**, solo lectura: se toma de la URL |
| `id_producto` | entero | **FK → PRODUCTO**, obligatorio |
| `id_diseno` | entero | **FK → DISEÑO**, obligatorio; debe pertenecer a `id_producto` |
| `ancho` | entero (mm) | obligatorio, mayor a 0 |
| `alto` | entero (mm) | obligatorio, mayor a 0 |
| `cantidad` | entero | obligatorio, mayor a 0 |
| `tipo_vidrio` | texto (máx. 80) | obligatorio |
| `color_aluminio` | texto (máx. 80) | obligatorio |
| `tipo_revestimiento` | texto (máx. 80) | obligatorio |
| `observaciones` | texto | opcional (por defecto `""`) |

### Relaciones

```
CLIENTE  1 ──< N  PEDIDO  N >── 1  USUARIO
                    1
                    │
                    N
               DETALLE_PEDIDO  N >── 1  PRODUCTO  1 ──< N  DISEÑO
                    N                                       1
                    └──────────────────── >─────────────────┘
```

- Un CLIENTE tiene muchos PEDIDOS, y cada PEDIDO es de un único CLIENTE.
- Un USUARIO registra muchos PEDIDOS, y cada PEDIDO lo registra un único USUARIO.
- Un PEDIDO tiene muchos DETALLES, y cada DETALLE pertenece a un único PEDIDO.
- Cada DETALLE referencia un PRODUCTO y uno de **sus** DISEÑOS.

### Estados del pedido

| Valor | Significado |
|---|---|
| `pendiente` | registrado, todavía se puede modificar |
| `en_produccion` | en fabricación |
| `terminado` | fabricado, pendiente de entrega |
| `entregado` | entregado al cliente |
| `cancelado` | cancelado; se conserva como historial |

Cualquier otro valor se rechaza con `400`.

### Reglas de integridad que la API hace cumplir

| Regla | Respuesta si se incumple |
|---|---|
| El cliente debe existir | `400`, error en `id_cliente` |
| El usuario debe existir | se toma del usuario autenticado; sin sesión, `403` |
| El detalle debe pertenecer a un pedido existente | `404` (el `id_pedido` de la URL no existe) |
| El producto y el diseño deben existir | `400`, error en `id_producto` o `id_diseno` |
| **El diseño debe corresponder al producto** | `400`, error en `id_diseno` |
| Estado dentro de los valores permitidos | `400`, error en `estado` |
| Medidas y cantidad mayores a 0 | `400`, error en el campo |
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
| `POST` | `/api/pedidos/{id_pedido}/cancelar/` | Cancela un pedido y conserva sus detalles como historial |
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
- Si el pedido está en otro estado, la API responde `409 Conflict`. La excepción es el cambio de `estado` para avanzarlo (`en_produccion` → `terminado` → `entregado`).
- Un pedido `cancelado` o `entregado` no admite cambios.
- Para cancelar se usa `POST .../cancelar/`. Enviar `"estado": "cancelado"` por `PATCH` se rechaza con `400`, así la cancelación queda como una operación explícita.

### Pedidos

#### `GET /api/pedidos/`

Lista los pedidos, del más reciente al más antiguo. Filtros opcionales:

| Parámetro | Ejemplo | Descripción |
|---|---|---|
| `id_cliente` | `?id_cliente=7` | pedidos de un cliente |
| `id_usuario` | `?id_usuario=4` | pedidos registrados por un usuario |
| `estado` | `?estado=pendiente` | pedidos en un estado |
| `fecha_desde` / `fecha_hasta` | `?fecha_desde=2026-10-01&fecha_hasta=2026-10-31` | rango de `fecha_pedido`, ambos extremos incluidos |

Respuesta `200`: lista de pedidos (ver [JSON de PEDIDO](#json-de-pedido)).

#### `POST /api/pedidos/`

Cuerpo:

```json
{
  "id_cliente": 7,
  "fecha_pedido": "2026-10-29",
  "observaciones": "Entregar por la mañana."
}
```

- `id_usuario` no se envía: la API asigna el usuario autenticado.
- `estado` no se envía: el pedido nace `pendiente`.
- `fecha_pedido` es opcional; si no se envía, se usa la fecha del día.

Respuestas:
- `201`: el pedido creado.
- `400`: el `id_cliente` no existe, o la fecha es inválida.

#### `GET /api/pedidos/{id_pedido}/`

- `200`: el pedido.
- `404`: no existe.

#### `PUT` / `PATCH /api/pedidos/{id_pedido}/`

Campos editables: `id_cliente`, `fecha_pedido`, `estado` y `observaciones`. `id_pedido` e `id_usuario` son de solo lectura.

Ejemplo para avanzar el estado:

```json
{ "estado": "en_produccion" }
```

- `200`: el pedido actualizado.
- `400`: datos inválidos o estado no permitido.
- `404`: no existe.
- `409`: el pedido no está `pendiente` y se intenta cambiar algo que no es el estado.

#### `POST /api/pedidos/{id_pedido}/cancelar/`

Sin cuerpo. Pasa el pedido a `cancelado` y conserva sus detalles como historial.

- `200`: el pedido con `"estado": "cancelado"`.
- `404`: no existe.
- `409`: el pedido ya está `cancelado` o `entregado`.

### Detalles del pedido

#### `GET /api/pedidos/{id_pedido}/detalles/`

- `200`: lista de detalles del pedido. Todos tienen el mismo `id_pedido`; si no tiene detalles, devuelve `[]`.
- `404`: el pedido no existe.

#### `POST /api/pedidos/{id_pedido}/detalles/`

Cuerpo:

```json
{
  "id_producto": 1,
  "id_diseno": 3,
  "ancho": 1500,
  "alto": 1100,
  "cantidad": 2,
  "tipo_vidrio": "Float 4 mm",
  "color_aluminio": "Blanco",
  "tipo_revestimiento": "Pintura electrostática",
  "observaciones": "Con mosquitero."
}
```

- `201`: el detalle creado, con `id_detalle_pedido` e `id_pedido`.
- `400`: dato inválido (ver el ejemplo de abajo).
- `404`: el pedido no existe.
- `409`: el pedido no está `pendiente`.

Si `id_diseno` no pertenece a `id_producto`, la respuesta es `400`:

```json
{
  "id_diseno": ["El diseño elegido no corresponde al producto."]
}
```

#### `GET /api/pedidos/{id_pedido}/detalles/{id_detalle_pedido}/`

- `200`: el detalle.
- `404`: el pedido o el detalle no existen, o el detalle es de otro pedido.

#### `PUT` / `PATCH /api/pedidos/{id_pedido}/detalles/{id_detalle_pedido}/`

Campos editables: todos salvo `id_detalle_pedido` e `id_pedido`. Si se cambia `id_producto` o `id_diseno`, se vuelve a comprobar que el diseño corresponda al producto.

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
  "fecha_pedido": "2026-10-29",
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
  "id_producto": 1,
  "id_diseno": 3,
  "ancho": 1500,
  "alto": 1100,
  "cantidad": 2,
  "tipo_vidrio": "Float 4 mm",
  "color_aluminio": "Blanco",
  "tipo_revestimiento": "Pintura electrostática",
  "observaciones": "Con mosquitero."
}
```

## Errores

| Código | Cuándo |
|---|---|
| `400 Bad Request` | datos inválidos, referencia inexistente o diseño que no corresponde al producto |
| `403 Forbidden` | sin autenticación, o el usuario no tiene permiso para la operación |
| `404 Not Found` | el pedido o el detalle no existe |
| `405 Method Not Allowed` | `DELETE` sobre un pedido |
| `409 Conflict` | operación no permitida por el estado del pedido |

Formato de error de validación (`400`): un objeto con el campo y la lista de mensajes.

```json
{
  "ancho": ["Asegúrese de que este valor sea mayor o igual a 1."]
}
```

Formato de los demás errores:

```json
{
  "detail": "El pedido no está pendiente y no puede modificarse."
}
```

## Decisiones a confirmar con el equipo

- **Estados y transiciones:** la lista de estados y el orden de avance (`pendiente` → `en_produccion` → `terminado` → `entregado`) no figuran en el diccionario de datos. Falta definir, por ejemplo, desde qué estados se puede cancelar.
- **Medidas:** se asumió milímetros, enteros y mayores a 0. Falta saber si hay mínimos o máximos por tipo de producto.
- **`tipo_vidrio`, `color_aluminio` y `tipo_revestimiento`:** hoy son texto libre. Si van a tener valores fijos, hay que listarlos en el contrato.
- **Productos y diseños inactivos:** ¿se rechaza agregarlos a un pedido nuevo? Se propone que sí, con `400`.
- **Permisos:** quién puede registrar, modificar, avanzar el estado y cancelar.
- **CLIENTE:** el contrato solo usa `id_cliente`. Si las respuestas de pedido tienen que incluir datos del cliente (nombre, etc.), hay que esperar el diccionario de datos de CLIENTE.
- **Paginación:** si los listados se paginan, definir el formato (por ejemplo `count`, `next`, `previous`, `results`).
