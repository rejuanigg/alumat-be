# Arquitectura de ALUMAT

> **Importante:** el proyecto tiene dos partes. Las pantallas web (`/cuentas/`, `/productos/`, inicio) son Django "clásico": devuelven **páginas HTML** armadas con templates. La API JSON para el frontend vive bajo `/api/` y está hecha con Django REST Framework (ver `EXPLICACION_ENDPOINTS.txt`).

## Stack

- **Django 5.2** + **PostgreSQL 17**, levantados con Docker Compose (`compose.yaml`): el servicio `db` es Postgres y `web` es Django con `runserver`.
- **Producción:** `compose.servidor.yaml` + **Gunicorn** + **Caddy** (`infra/Caddyfile`) como proxy HTTPS. **WhiteNoise** sirve los estáticos.
- **django-axes** bloquea el login después de varios intentos fallidos.
- Toda la configuración sale de variables de entorno (`.env`, que se genera con `scripts/configurar.py`).

## Estructura: 1 proyecto + varias apps

```
config/            → settings.py y urls.py raíz (el "cableado" general)
cuentas/           → usuarios, registro, login y aprobación de cuentas
productos/         → productos (aberturas) y diseños: pantallas web y API
clientes/          → clientes particulares y empresas (API)
pedidos/           → pedidos y sus detalles (API)
cajas/             → cajas y aperturas (API)
movimientos_caja/  → movimientos y cierres de caja (API)
ventas/            → ventas y cobros; services.py registra los cobros
inicio/            → dashboard (home), healthcheck y comandos (cargar_demo, crear_roles)
templates/         → HTML de las pantallas web
```

URLs raíz en `config/urls.py`:

| Prefijo | App |
|---|---|
| `/admin/` | Admin de Django (solo superusuario) |
| `/cuentas/` | `cuentas.urls` |
| `/productos/` | `productos.urls_web` (pantallas) |
| `/api/` | APIs de `clientes`, `productos`, `pedidos`, `cajas` y `movimientos_caja` |
| `/` | `inicio.urls` |

## App `cuentas`: usuarios con aprobación

**Modelo** (`cuentas/models.py`): `Usuario` extiende `AbstractUser` y suma:

- `estado`: `pendiente` / `aprobado` / `rechazado`.
- `is_active=False` por defecto. Una restricción en la base de datos impide que un usuario quede activo sin estar aprobado (`activo_solo_aprobado`).
- El usuario y el email son únicos sin importar mayúsculas, y siempre se guardan en minúsculas.

**Cómo funciona:**

1. La persona se registra en `/cuentas/registrarse/` y queda `pendiente` e inactiva (`RegistroForm.save`).
2. El superusuario ve las solicitudes en `/cuentas/solicitudes/` y aprueba o rechaza con un POST a `/cuentas/solicitudes/<id>/resolver/`.
3. Esa decisión pasa por `cuentas/services.py → resolver_solicitud()`, que:
   - corre en una transacción con `select_for_update` para evitar condiciones de carrera;
   - verifica que quien resuelve sea superusuario;
   - deja registro en `LogEntry`, la auditoría del admin.
4. Recién ahí el usuario puede entrar por `/cuentas/ingresar/`.

| URL | Vista | Acceso |
|---|---|---|
| `ingresar/` | `AccesoView` (LoginView) | público |
| `salir/` | `LogoutView` | logueado |
| `registrarse/` | `registro` | público |
| `pendiente/` | `pendiente` | público |
| `solicitudes/` | `solicitudes` | superusuario |
| `solicitudes/<pk>/resolver/` | `resolver` (solo POST) | superusuario |

## App `productos`: aberturas y diseños

**Modelos** (`productos/models.py`, tablas `productos` y `disenos`):

- `Producto`: `nombre`, `tipo_abertura`, `descripcion` y `activo`. El nombre no se repite dentro del mismo tipo de abertura (sin importar mayúsculas).
- `Diseno`: pertenece a un producto (`PROTECT`); su nombre no se repite dentro del producto.
- No se borran: se desactivan (`activo=False`) para conservar los pedidos anteriores.
- El stock y el inventario quedan fuera del alcance del documento.

## App `pedidos`: pedidos y detalles

- `Pedido` (tabla `pedidos`): `fecha_pedido` con fecha y hora; estados `pendiente` → `en_proceso` → `finalizado`, solo hacia adelante y de a un paso. No hay cancelación. Solo un pedido pendiente admite cambios en sus datos y detalles (409 si no).
- `DetallePedido` (tabla `detalle_pedidos`): referencia un `Diseno`; el producto se obtiene a través del diseño. Medidas decimales y listas predefinidas para vidrio, color de aluminio y revestimiento. Ver `docs/CONTRATO_API_PEDIDOS.md`.

## App `ventas`: ventas y cobros

- `Venta` (tabla `ventas`): una por pedido (`id_pedido` UNIQUE), con el usuario que la registró e `importe_total` > 0. Calcula `total_cobrado` y `saldo_pendiente`.
- `Cobro` (tabla `cobros`): `tipo_cobro` `parcial` o `total`; el monto no puede superar el saldo, un cobro total cubre todo el saldo y uno parcial no; `numero_boleta` es único.
- **`ventas/services.py → registrar_cobro()`** es la única vía para dar de alta un cobro: corre en una transacción, bloquea la venta con `select_for_update` para no cobrar dos veces el mismo saldo y, si el cobro es en efectivo, exige una apertura de caja abierta y registra automáticamente el movimiento de Entrada en esa caja. En el admin, los cobros son de solo lectura.

**Pantallas web** (`productos/vistas_web.py`, `productos/urls_web.py`): *class-based views* genéricas de Django. `GuardadoSeguroMixin` guarda dentro de una transacción y, si hay un `IntegrityError` (por ejemplo un duplicado), muestra un error en el formulario en vez de un 500.

| URL | Qué hace | Acceso |
|---|---|---|
| `/productos/` | lista con búsqueda `?q=` (nombre o tipo) y paginación de 12 | logueado |
| `nuevo/`, `<pk>/`, `<pk>/editar/` | crear, ver (con sus diseños) y editar producto; desactivar desde editar | logueado |
| `<pk>/disenos/nuevo/`, `disenos/<pk>/editar/` | agregar y editar diseños | logueado |

La API (`/api/productos/`, `/api/disenos/`) usa los mismos modelos: ver `docs/CONTRATO_API_PRODUCTOS.md`.

## App `inicio`

- `/`: `home` muestra contadores de productos y diseños activos y, si sos admin, las solicitudes pendientes.
- `/salud/`: healthcheck en JSON que hace un `SELECT 1`. Lo usa Docker en producción.
- `context_processors.organizacion` agrega `SITE_NAME` a todos los templates.
- `inicio/management/commands/cargar_demo.py` carga datos de ejemplo (`python manage.py cargar_demo`).
- `inicio/management/commands/crear_roles.py` crea los grupos `Vendedor` y `Dueño` (`python manage.py crear_roles`); se puede correr varias veces sin duplicar nada.

## Seguridad y permisos

- La sesión dura 8 horas y se cierra al cerrar el navegador.
- En producción usa cookies seguras y redirección a SSL.
- Las contraseñas tienen que tener mínimo 10 caracteres y pasan los validadores de Django.
- Login: 5 intentos fallidos bloquean al usuario durante 15 minutos (django-axes).
- Hay dos niveles de acceso: **logueado** (`login_required` / `LoginRequiredMixin`) y **superusuario** (`is_superuser`).
- **Roles del documento** (`cuentas/permisos.py`): el **Administrador** es el superusuario; el **Vendedor** y el **Dueño** son grupos de Django. Todos los ViewSets usan `[IsAuthenticated, PermisoPorRol]`: Administrador y Vendedor operan, y el Dueño solo consulta (los `POST`, `PUT` y `PATCH` le responden 403). En las pantallas web, el Dueño no puede entrar a crear ni editar productos o diseños (403). Un superusuario nunca se trata como Dueño.
- Tests: un `tests.py` por app (más `productos/tests_web.py` para las pantallas). Se corren con `docker compose exec web python manage.py test`.

## Cómo agregar endpoints nuevos

### Páginas HTML (mismo patrón que lo actual)

1. Creá una app nueva: `python manage.py startapp ventas` (por ejemplo) y agregala a `INSTALLED_APPS`.
2. Escribí el modelo en `models.py` (copiá el estilo de `Producto`: `activo` en lugar de borrar, restricciones en `Meta`) y corré `makemigrations` + `migrate`.
3. Armá los formularios en `forms.py` como `ModelForm` con sus `clean_*`.
4. Escribí las vistas reutilizando `GuardadoSeguroMixin` desde `productos.vistas_web`. Si lo vas a usar mucho, conviene moverlo a un módulo común.
5. Definí `urls.py` con su `app_name` y sumalo con `include()` en `config/urls.py`.
6. Creá los templates en `templates/<app>/` extendiendo `base.html`.

### API JSON (para un frontend web o mobile)

1. Sumá **Django REST Framework** (`djangorestframework`) a `requirements.in` y `requirements.txt`, y agregá `rest_framework` a `INSTALLED_APPS`.
2. Escribí *serializers* y *ViewSets* sobre los mismos modelos (como `productos/serializers.py` y `productos/views.py`).
3. Montalos bajo `/api/` en `config/urls.py`.
4. Decidí la autenticación:
   - **Sesión:** sirve si el frontend está en el mismo dominio.
   - **Token/JWT:** necesario para la app mobile o para un frontend en otro dominio (en ese caso también hace falta CORS).

## Comparación con Laravel

La idea general es la misma: los dos son frameworks MVC con ORM, migraciones, rutas con nombre, templates, formularios con validación y middleware. Lo que cambia sobre todo son los nombres.

> **Ojo con los nombres:** lo que en Django se llama **"view"** es el **Controller** de Laravel. Lo que en Laravel es la **View** (Blade), en Django es el **template**. Django lo llama "MTV" (Model-Template-View), pero es MVC.

### Equivalencias generales

| Laravel | Django | En este proyecto |
|---|---|---|
| Proyecto (`app/`, `routes/`, `config/`) | Proyecto (`config/`) + varias **apps** | `config/` + `cuentas/`, `productos/`, `inicio/`, … |
| Módulo/carpeta de dominio (o un paquete) | **App** de Django: modelos, vistas, urls y forms juntos | `productos/` |
| `routes/web.php` | `urls.py` (uno raíz + uno por app) | `config/urls.py` → `include("productos.urls_web")` |
| `Route::get(...)->name('x')` | `path(..., name="x")` | `name="lista"` |
| `route('productos.index')` | `reverse("productos:lista")` / `{% url 'productos:lista' %}` | `app_name = "productos"` hace de prefijo |
| `Route::prefix('productos')->group(...)` | `path("productos/", include(...))` | `config/urls.py` |
| Controller | **View** (función o clase) | `productos/vistas_web.py` |
| `Route::resource` + resource controller | Vistas genéricas `ListView`, `DetailView`, `CreateView`, `UpdateView`, `DeleteView` | `ProductoListView`, etc. |
| Blade (`resources/views/*.blade.php`) | Templates de Django (`templates/*.html`) | `templates/productos/lista.html` |
| `@extends('layouts.app')` / `@section` / `@yield` | `{% extends "base.html" %}` / `{% block %}` | `templates/base.html` |
| `@include('partials.x')` | `{% include "componentes/x.html" %}` | `templates/componentes/` |
| `View::share` / View Composer | **Context processor** | `inicio/context_processors.py` |
| Eloquent Model | Model del ORM de Django | `Producto`, `Diseno`, `Usuario` |
| Migrations escritas a mano | Migrations **generadas** desde el modelo (`makemigrations`) | `productos/migrations/` |
| `php artisan migrate` | `python manage.py migrate` | lo corre `compose.yaml` al arrancar |
| `php artisan make:...` | `python manage.py startapp ...` | — |
| `php artisan tinker` | `python manage.py shell` | — |
| Artisan command | Management command | `inicio/management/commands/cargar_demo.py` |
| Seeder | Management command o fixture | `cargar_demo` |
| Form Request / `$request->validate()` | **Form** / **ModelForm** con `clean_<campo>()` | `productos/forms.py`, `cuentas/forms.py` |
| `@csrf` | `{% csrf_token %}` | en cada `<form>` |
| Middleware (`app/Http/Middleware`, `Kernel`) | Middleware (`MIDDLEWARE` en settings) | `config/settings.py` |
| `.env` + `config/*.php` | `.env` → `os.environ` en `settings.py` | `config/settings.py` |
| Auth (Breeze/Fortify) | `django.contrib.auth` (LoginView, LogoutView) | `cuentas/views.py` |
| `User` model | `AbstractUser` + `AUTH_USER_MODEL` | `cuentas.Usuario` |
| Middleware `auth` | `@login_required` / `LoginRequiredMixin` | todas las vistas de productos |
| Gate / Policy | `UserPassesTestMixin` / `PermissionDenied` / permisos de DRF | `cuentas/views.py`, `cuentas/permisos.py` |
| `abort(403)` | `raise PermissionDenied` | `cuentas/views.py` |
| `findOrFail()` | `get_object_or_404()` | `cuentas/views.py` |
| `DB::transaction()` | `transaction.atomic()` | `GuardadoSeguroMixin`, `services.py` |
| `->lockForUpdate()` | `.select_for_update()` | `resolver_solicitud()` |
| Clase de servicio (`app/Services`) | Módulo `services.py` (convención, no lo impone el framework) | `cuentas/services.py`, `ventas/services.py` |
| Flash (`session()->flash`, `with('success')`) | `messages.success(request, ...)` | vistas de productos |
| `redirect()->route('x')` | `redirect("app:x")` | `cuentas/views.py` |
| `response()->json()` | `JsonResponse` | `inicio/views.py → salud` |
| Paginación `->paginate(12)` | `paginate_by = 12` | `ProductoListView` |
| Laravel Nova / Filament | **Admin de Django** (ya viene incluido) | `cuentas/admin.py` |
| PHPUnit / Pest (`php artisan test`) | `unittest` de Django (`manage.py test`) | `cuentas/tests.py`, `productos/tests_web.py` |
| API Resources + Sanctum | **Django REST Framework** (serializers + ViewSets) + auth de DRF | `*/serializers.py`, bajo `/api/` |
| `composer.json` | `requirements.in` / `requirements.txt` | — |
| PHP-FPM + Nginx | Gunicorn + Caddy | `Dockerfile`, `infra/Caddyfile` |

### Eloquent vs ORM de Django, con ejemplos de este código

| Eloquent | Django |
|---|---|
| `Producto::all()` | `Producto.objects.all()` |
| `Producto::count()` | `Producto.objects.count()` |
| `Producto::find($id)` | `Producto.objects.get(pk=id)` |
| `Producto::where('nombre', 'like', "%$q%")->orWhere(...)` | `Producto.objects.filter(Q(nombre__icontains=q) \| Q(tipo_abertura__icontains=q))` |
| `->with('producto')` (eager loading) | `.select_related("producto")` (FK) / `.prefetch_related()` (relaciones a muchos) |
| `->orderBy('nombre')->take(5)` | `.order_by("nombre")[:5]` |
| `->where('id', '!=', $id)` | `.exclude(pk=id)` |
| `->exists()` | `.exists()` |
| `belongsTo(Producto::class)` | `models.ForeignKey(Producto, ...)` |
| `hasMany` (se define del otro lado) | automático: `producto.diseno_set` o el `related_name` (`producto.disenos`) |
| `$fillable` / `$guarded` | `fields = (...)` en el `ModelForm` |
| `$timestamps` (`created_at`, `updated_at`) | `auto_now_add=True` / `auto_now=True` (por ejemplo `Cliente.fecha_registro`) |
| `->constrained()->restrictOnDelete()` | `on_delete=models.PROTECT` |

**La diferencia más grande:** en Laravel escribís la migración y el modelo por separado. En Django **el modelo es la fuente de verdad**: declarás los campos en `models.py` y `makemigrations` genera la migración sola.

### El mismo flujo en los dos frameworks

**"Crear producto"** en Laravel:

```php
// routes/web.php
Route::middleware('auth')->group(function () {
    Route::resource('productos', ProductoController::class);
});

// ProductoController@store
public function store(StoreProductoRequest $request) {
    $producto = Producto::create($request->validated());
    return redirect()->route('productos.show', $producto)->with('success', 'Cambios guardados.');
}
```

En este proyecto (Django):

```python
# productos/urls_web.py
path("nuevo/", vistas_web.ProductoCreateView.as_view(), name="crear"),

# productos/vistas_web.py
class ProductoCreateView(LoginRequiredMixin, GuardadoSeguroMixin, CreateView):
    model = Producto
    form_class = ProductoForm            # ≈ StoreProductoRequest
    template_name = "productos/formulario.html"
    # Al validar, guarda y redirige a get_absolute_url() del producto.
```

`CreateView` hace en una sola clase lo que en Laravel son `create()` (mostrar el formulario) y `store()` (guardarlo): con GET muestra el formulario y con POST lo valida y guarda. Los **mixins** (`LoginRequiredMixin`, `GuardadoSeguroMixin`) son como **traits** de PHP que además cumplen el papel del middleware de la ruta.

### Diferencias de enfoque

- **Las apps son autocontenidas.** En Laravel los modelos van en `app/Models` y los controladores en `app/Http/Controllers`, todo junto. En Django cada app tiene sus propios `models.py`, `views.py`, `urls.py` y `forms.py`.
- **El admin viene incluido.** `/admin/` es un panel CRUD automático, sin instalar nada como Nova o Filament.
- **No hay contenedor de dependencias ni facades.** Se importa directamente lo que se usa (`from .models import Producto`).
- **La validación vive en el Form, no en el request.** El mismo `ModelForm` valida los datos y además dibuja los campos en el template.
- **No hay `make:controller`.** Las vistas y las URLs se escriben a mano. Las vistas genéricas reemplazan casi todo el boilerplate.
