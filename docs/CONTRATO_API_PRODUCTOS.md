# Contrato de API: Gestión de Productos y Diseños

Sección del contrato de API de ALUMAT correspondiente al Proceso 2: Gestión de Productos y Diseños.

## Convenciones generales

- **URL base:** `/api/`
- **Formato:** JSON (`Content-Type: application/json`), con codificación UTF-8.
- **Nombres de campos:** iguales a los del diccionario de datos (`id_producto`, `id_diseno`, etc.).
- **Autenticación:** todos los endpoints requieren un usuario autenticado. Si no hay sesión válida, se responde `401`.
- **Sin borrado físico:** productos y diseños no se eliminan, se desactivan con `activo: false` para conservar el historial. Por eso no existe `DELETE`; si se usa, la API responde `405 Method Not Allowed`.
- **Fuera de alcance:** no hay atributos ni endpoints de stock, precio ni inventario.

## Modelo de datos

### PRODUCTO

| Atributo | Tipo | Restricciones |
|---|---|---|
| `id_producto` | entero | **PK**, autoincremental, solo lectura |
| `nombre` | texto (máx. 120) | obligatorio |
| `tipo_abertura` | texto (máx. 80) | obligatorio |
| `descripcion` | texto | opcional (por defecto `""`) |
| `activo` | booleano | por defecto `true` |

FK: ninguna.

### DISEÑO

| Atributo | Tipo | Restricciones |
|---|---|---|
| `id_diseno` | entero | **PK**, autoincremental, solo lectura |
| `id_producto` | entero | **FK → PRODUCTO**, obligatorio, no se puede modificar después de crearlo |
| `nombre_diseno` | texto (máx. 120) | obligatorio |
| `activo` | booleano | por defecto `true` |

**Relación:** un PRODUCTO tiene muchos DISEÑOS (1:N), y cada DISEÑO pertenece a un único PRODUCTO.

### Reglas de integridad que la API hace cumplir

| Regla | Respuesta si se incumple |
|---|---|
| Un diseño no puede referenciar un producto inexistente | `400`, error en `id_producto` |
| No se puede borrar un producto que tenga diseños | no hay `DELETE` (`405`) |
| No se puede borrar un diseño usado en detalles de pedido | no hay `DELETE` (`405`) |
| La asociación diseño → producto se mantiene | `id_producto` se ignora o se rechaza en `PUT`/`PATCH` (`400`) |
| Desactivar sin perder historial | `PATCH` con `{"activo": false}` |

## Endpoints

### Resumen

| MÉTODO HTTP | ENDPOINT | DESCRIPCIÓN |
|---|---|---|
| `GET` | `/api/productos/` | Lista los productos (filtros: `activo`, `tipo_abertura`, `q`) |
| `POST` | `/api/productos/` | Registra un producto |
| `GET` | `/api/productos/{id_producto}/` | Consulta un producto |
| `PUT` | `/api/productos/{id_producto}/` | Modifica todos los campos editables de un producto |
| `PATCH` | `/api/productos/{id_producto}/` | Modifica algunos campos de un producto; con `{"activo": false}` lo desactiva y con `{"activo": true}` lo reactiva |
| `GET` | `/api/productos/{id_producto}/disenos/` | Lista los diseños asociados a un producto (filtro: `activo`) |
| `GET` | `/api/disenos/` | Lista los diseños (filtros: `id_producto`, `activo`) |
| `POST` | `/api/disenos/` | Registra un diseño para un producto existente |
| `GET` | `/api/disenos/{id_diseno}/` | Consulta un diseño |
| `PUT` | `/api/disenos/{id_diseno}/` | Modifica todos los campos editables de un diseño |
| `PATCH` | `/api/disenos/{id_diseno}/` | Modifica algunos campos de un diseño; con `{"activo": false}` lo desactiva y con `{"activo": true}` lo reactiva |

`PUT` reemplaza todos los campos editables; `PATCH` modifica solo los que se envían.

### Productos

#### `GET /api/productos/`

Lista los productos. Filtros opcionales por query string:

| Parámetro | Ejemplo | Descripción |
|---|---|---|
| `activo` | `?activo=true` | solo activos (`true`) o inactivos (`false`); sin el parámetro devuelve todos |
| `tipo_abertura` | `?tipo_abertura=corrediza` | coincidencia exacta |
| `q` | `?q=ventana` | busca en `nombre` |

Respuesta `200`: lista de productos (ver [JSON de PRODUCTO](#json-de-producto)).

#### `POST /api/productos/`

Cuerpo:

```json
{
  "nombre": "Ventana corrediza",
  "tipo_abertura": "corrediza",
  "descripcion": "Ventana de aluminio de dos hojas corredizas."
}
```

- `201`: devuelve el producto creado, con `id_producto` y `activo: true`.
- `400`: falta un campo obligatorio o supera la longitud máxima.

#### `GET /api/productos/{id_producto}/`

- `200`: el producto.
- `404`: no existe.

#### `PUT` / `PATCH /api/productos/{id_producto}/`

Campos editables: `nombre`, `tipo_abertura`, `descripcion` y `activo`. `id_producto` es de solo lectura.

Desactivar:

```json
{ "activo": false }
```

- `200`: el producto actualizado.
- `400`: datos inválidos.
- `404`: no existe.

#### `GET /api/productos/{id_producto}/disenos/`

Lista los diseños asociados al producto. Acepta el filtro `?activo=true|false`.

- `200`: lista de diseños. Todos tienen el mismo `id_producto`; si no tiene diseños, devuelve `[]`.
- `404`: el producto no existe.

### Diseños

#### `GET /api/disenos/`

Filtros opcionales:

| Parámetro | Ejemplo | Descripción |
|---|---|---|
| `id_producto` | `?id_producto=1` | diseños de un producto |
| `activo` | `?activo=true` | solo activos o inactivos |

Respuesta `200`: lista de diseños (ver [JSON de DISEÑO](#json-de-diseño)).

#### `POST /api/disenos/`

Cuerpo:

```json
{
  "id_producto": 1,
  "nombre_diseno": "Dos hojas con mosquitero"
}
```

- `201`: devuelve el diseño creado, con `id_diseno` y `activo: true`.
- `400`: falta un campo obligatorio, o `id_producto` no corresponde a un producto existente.

#### `GET /api/disenos/{id_diseno}/`

- `200`: el diseño.
- `404`: no existe.

#### `PUT` / `PATCH /api/disenos/{id_diseno}/`

Campos editables: `nombre_diseno` y `activo`. `id_diseno` e `id_producto` no se pueden modificar, para mantener la asociación con el producto.

- `200`: el diseño actualizado.
- `400`: datos inválidos o intento de cambiar `id_producto`.
- `404`: no existe.

## JSON de ejemplo

### JSON de PRODUCTO

Registro devuelto por `GET /api/productos/1/`:

```json
{
  "id_producto": 1,
  "nombre": "Ventana corrediza",
  "tipo_abertura": "corrediza",
  "descripcion": "Ventana de aluminio de dos hojas corredizas.",
  "activo": true
}
```

### JSON de DISEÑO

Registro devuelto por `GET /api/disenos/3/`. Su `id_producto` apunta al producto anterior:

```json
{
  "id_diseno": 3,
  "id_producto": 1,
  "nombre_diseno": "Dos hojas con mosquitero",
  "activo": true
}
```

### Relación PRODUCTO → DISEÑO

`GET /api/productos/1/disenos/` devuelve todos los diseños del producto 1, y cada uno repite su `id_producto`:

```json
[
  {
    "id_diseno": 2,
    "id_producto": 1,
    "nombre_diseno": "Dos hojas",
    "activo": true
  },
  {
    "id_diseno": 3,
    "id_producto": 1,
    "nombre_diseno": "Dos hojas con mosquitero",
    "activo": true
  }
]
```

## Errores

| Código | Cuándo |
|---|---|
| `400 Bad Request` | datos inválidos |
| `401 Unauthorized` | sin autenticación |
| `403 Forbidden` | el usuario no tiene permiso para la operación |
| `404 Not Found` | el producto o diseño no existe |
| `405 Method Not Allowed` | se intenta `DELETE` |

Formato de error de validación (`400`): un objeto con el campo y la lista de mensajes.

```json
{
  "id_producto": ["El producto indicado no existe."]
}
```

Formato de los demás errores:

```json
{
  "detail": "No encontrado."
}
```

## Decisiones a confirmar con el equipo

- **Permisos de escritura:** quién puede registrar, modificar y desactivar (¿cualquier usuario aprobado o solo el administrador?).
- **Diseños de un producto inactivo:** ¿se permite registrar diseños nuevos en un producto desactivado? ¿Al desactivar un producto se desactivan también sus diseños, o quedan como están?
- **`tipo_abertura`:** hoy es texto libre. Si va a tener valores fijos (corrediza, batiente, etc.), hay que listarlos en el contrato.
- **Paginación:** si los listados se paginan, definir el formato (por ejemplo `count`, `next`, `previous`, `results`).
