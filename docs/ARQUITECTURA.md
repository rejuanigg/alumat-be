# Arquitectura de ALUMAT

> **Importante:** no es un backend de API. Es un Django "clásico": cada URL devuelve una **página HTML** armada con templates, no JSON. El único endpoint JSON es `/salud/`. Si los endpoints nuevos se van a consumir desde un frontend separado (web o mobile), hay que agregar una capa de API (ver el final).

## Stack

- **Django 5.2** + **PostgreSQL 17**, levantados con Docker Compose (`compose.yaml`): el servicio `db` es Postgres y `web` es Django con `runserver`.
- **Producción:** `compose.servidor.yaml` + **Gunicorn** + **Caddy** (`infra/Caddyfile`) como proxy HTTPS. **WhiteNoise** sirve los estáticos.
- **django-axes** bloquea el login después de varios intentos fallidos.
- Toda la configuración sale de variables de entorno (`.env`, que se genera con `scripts/configurar.py`).

## Estructura: 1 proyecto + 3 apps

```
config/      → settings.py y urls.py raíz (el "cableado" general)
cuentas/     → usuarios, registro, login y aprobación de cuentas
catalogo/    → productos y categorías (el CRUD de negocio)
inicio/      → dashboard (home) y healthcheck
templates/   → HTML de todas las apps
```

URLs raíz en `config/urls.py`:

| Prefijo | App |
|---|---|
| `/admin/` | Admin de Django (solo superusuario) |
| `/cuentas/` | `cuentas.urls` |
| `/catalogo/` | `catalogo.urls` |
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

## App `catalogo`: CRUD de productos

**Modelos** (`catalogo/models.py`):

- `Categoria`: `nombre`, único sin importar mayúsculas.
- `Producto`:
  - `codigo` (único), `nombre`, `categoria` (FK), `descripcion`, `precio` (≥0), `stock`.
  - Auditoría: `creado_por`, `actualizado_por`, `creado` y `actualizado`.
- Las FK usan `PROTECT`: no se puede borrar una categoría que tenga productos ni un usuario que haya creado productos.

**Vistas** (`catalogo/views.py`): todas son *class-based views* genéricas de Django (`ListView`, `CreateView`, etc.) y reutilizan dos mixins:

- `SoloAdministradorMixin`: exige estar logueado y ser superusuario.
- `GuardadoSeguroMixin`: guarda dentro de una transacción. Si hay un `IntegrityError` (por ejemplo un duplicado), muestra un error en el formulario en vez de un 500.

| URL | Qué hace | Acceso |
|---|---|---|
| `/catalogo/` | lista con búsqueda `?q=` y paginación de 12 | logueado |
| `nuevo/`, `<pk>/`, `<pk>/editar/` | crear, ver y editar producto | logueado |
| `<pk>/eliminar/` | borrar producto | superusuario |
| `categorias/` | listar categorías | logueado |
| `categorias/nueva/`, `<pk>/editar/`, `<pk>/eliminar/` | ABM de categorías | superusuario |

Las validaciones de "ya existe" están en `catalogo/forms.py`. La base de datos además lo garantiza con constraints.

## App `inicio`

- `/`: `home` muestra contadores, los últimos 5 productos y, si sos admin, las solicitudes pendientes.
- `/salud/`: healthcheck en JSON que hace un `SELECT 1`. Lo usa Docker en producción.
- `context_processors.organizacion` agrega `SITE_NAME` a todos los templates.
- `inicio/management/commands/cargar_demo.py` carga datos de ejemplo (`python manage.py cargar_demo`).

## Seguridad y permisos

- La sesión dura 8 horas y se cierra al cerrar el navegador.
- En producción usa cookies seguras y redirección a SSL.
- Las contraseñas tienen que tener mínimo 10 caracteres y pasan los validadores de Django.
- Login: 5 intentos fallidos bloquean al usuario durante 15 minutos (django-axes).
- Hay dos niveles de permiso: **logueado** (`login_required` / `LoginRequiredMixin`) y **superusuario** (`is_superuser`). No usa grupos ni permisos de Django más finos.
- Tests: `cuentas/tests.py` y `catalogo/tests.py`. Se corren con `docker compose exec web python manage.py test`.

## Cómo agregar endpoints nuevos

### Páginas HTML (mismo patrón que lo actual)

1. Creá una app nueva: `python manage.py startapp ventas` (por ejemplo) y agregala a `INSTALLED_APPS`.
2. Escribí el modelo en `models.py` (copiá el estilo de `Producto` con `creado_por`/`actualizado_por`) y corré `makemigrations` + `migrate`.
3. Armá los formularios en `forms.py` como `ModelForm` con sus `clean_*`.
4. Escribí las vistas reutilizando `SoloAdministradorMixin` y `GuardadoSeguroMixin` desde `catalogo.views`. Si los vas a usar mucho, conviene moverlos a un módulo común.
5. Definí `urls.py` con su `app_name` y sumalo con `include()` en `config/urls.py`.
6. Creá los templates en `templates/<app>/` extendiendo `base.html`.

### API JSON (para un frontend web o mobile)

1. Sumá **Django REST Framework** (`djangorestframework`) a `requirements.in` y `requirements.txt`, y agregá `rest_framework` a `INSTALLED_APPS`.
2. Escribí *serializers* y *ViewSets* sobre los mismos modelos (`Producto`, `Categoria`, `Usuario`).
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
| Proyecto (`app/`, `routes/`, `config/`) | Proyecto (`config/`) + varias **apps** | `config/` + `cuentas/`, `catalogo/`, `inicio/` |
| Módulo/carpeta de dominio (o un paquete) | **App** de Django: modelos, vistas, urls y forms juntos | `catalogo/` |
| `routes/web.php` | `urls.py` (uno raíz + uno por app) | `config/urls.py` → `include("catalogo.urls")` |
| `Route::get(...)->name('x')` | `path(..., name="x")` | `name="lista"` |
| `route('productos.index')` | `reverse("catalogo:lista")` / `{% url 'catalogo:lista' %}` | `app_name = "catalogo"` hace de prefijo |
| `Route::prefix('catalogo')->group(...)` | `path("catalogo/", include(...))` | `config/urls.py` |
| Controller | **View** (función o clase) | `catalogo/views.py` |
| `Route::resource` + resource controller | Vistas genéricas `ListView`, `DetailView`, `CreateView`, `UpdateView`, `DeleteView` | `ProductoListView`, etc. |
| Blade (`resources/views/*.blade.php`) | Templates de Django (`templates/*.html`) | `templates/catalogo/lista.html` |
| `@extends('layouts.app')` / `@section` / `@yield` | `{% extends "base.html" %}` / `{% block %}` | `templates/base.html` |
| `@include('partials.x')` | `{% include "componentes/x.html" %}` | `templates/componentes/` |
| `View::share` / View Composer | **Context processor** | `inicio/context_processors.py` |
| Eloquent Model | Model del ORM de Django | `Producto`, `Categoria`, `Usuario` |
| Migrations escritas a mano | Migrations **generadas** desde el modelo (`makemigrations`) | `catalogo/migrations/` |
| `php artisan migrate` | `python manage.py migrate` | lo corre `compose.yaml` al arrancar |
| `php artisan make:...` | `python manage.py startapp ...` | — |
| `php artisan tinker` | `python manage.py shell` | — |
| Artisan command | Management command | `inicio/management/commands/cargar_demo.py` |
| Seeder | Management command o fixture | `cargar_demo` |
| Form Request / `$request->validate()` | **Form** / **ModelForm** con `clean_<campo>()` | `catalogo/forms.py`, `cuentas/forms.py` |
| `@csrf` | `{% csrf_token %}` | en cada `<form>` |
| Middleware (`app/Http/Middleware`, `Kernel`) | Middleware (`MIDDLEWARE` en settings) | `config/settings.py` |
| `.env` + `config/*.php` | `.env` → `os.environ` en `settings.py` | `config/settings.py` |
| Auth (Breeze/Fortify) | `django.contrib.auth` (LoginView, LogoutView) | `cuentas/views.py` |
| `User` model | `AbstractUser` + `AUTH_USER_MODEL` | `cuentas.Usuario` |
| Middleware `auth` | `@login_required` / `LoginRequiredMixin` | todas las vistas de catálogo |
| Gate / Policy | `UserPassesTestMixin` / `PermissionDenied` | `SoloAdministradorMixin` |
| `abort(403)` | `raise PermissionDenied` | `cuentas/views.py` |
| `findOrFail()` | `get_object_or_404()` | `cuentas/views.py` |
| `DB::transaction()` | `transaction.atomic()` | `GuardadoSeguroMixin`, `services.py` |
| `->lockForUpdate()` | `.select_for_update()` | `resolver_solicitud()` |
| Clase de servicio (`app/Services`) | Módulo `services.py` (convención, no lo impone el framework) | `cuentas/services.py` |
| Flash (`session()->flash`, `with('success')`) | `messages.success(request, ...)` | vistas de catálogo |
| `redirect()->route('x')` | `redirect("app:x")` | `cuentas/views.py` |
| `response()->json()` | `JsonResponse` | `inicio/views.py → salud` |
| Paginación `->paginate(12)` | `paginate_by = 12` | `ProductoListView` |
| Laravel Nova / Filament | **Admin de Django** (ya viene incluido) | `cuentas/admin.py` |
| PHPUnit / Pest (`php artisan test`) | `unittest` de Django (`manage.py test`) | `cuentas/tests.py`, `catalogo/tests.py` |
| API Resources + Sanctum | **Django REST Framework** (serializers + ViewSets) + auth de DRF | no está; habría que agregarlo |
| `composer.json` | `requirements.in` / `requirements.txt` | — |
| PHP-FPM + Nginx | Gunicorn + Caddy | `Dockerfile`, `infra/Caddyfile` |

### Eloquent vs ORM de Django, con ejemplos de este código

| Eloquent | Django |
|---|---|
| `Producto::all()` | `Producto.objects.all()` |
| `Producto::count()` | `Producto.objects.count()` |
| `Producto::find($id)` | `Producto.objects.get(pk=id)` |
| `Producto::where('nombre', 'like', "%$q%")->orWhere(...)` | `Producto.objects.filter(Q(nombre__icontains=q) \| Q(codigo__icontains=q))` |
| `->with('categoria')` (eager loading) | `.select_related("categoria")` (FK) / `.prefetch_related()` (relaciones a muchos) |
| `->orderByDesc('actualizado')->take(5)` | `.order_by("-actualizado")[:5]` |
| `->where('id', '!=', $id)` | `.exclude(pk=id)` |
| `->exists()` | `.exists()` |
| `belongsTo(Categoria::class)` | `models.ForeignKey(Categoria, ...)` |
| `hasMany` (se define del otro lado) | automático: `categoria.producto_set` o el `related_name` |
| `$fillable` / `$guarded` | `fields = (...)` en el `ModelForm` |
| `$timestamps` (`created_at`, `updated_at`) | `auto_now_add=True` / `auto_now=True` (`creado`, `actualizado`) |
| `->constrained()->restrictOnDelete()` | `on_delete=models.PROTECT` |

**La diferencia más grande:** en Laravel escribís la migración y el modelo por separado. En Django **el modelo es la fuente de verdad**: declarás los campos en `models.py` y `makemigrations` genera la migración sola.

### El mismo flujo en los dos frameworks

**"Crear producto"** en Laravel:

```php
// routes/web.php
Route::middleware('auth')->group(function () {
    Route::resource('catalogo', ProductoController::class);
});

// ProductoController@store
public function store(StoreProductoRequest $request) {
    $producto = Producto::create($request->validated() + [
        'creado_por' => auth()->id(),
        'actualizado_por' => auth()->id(),
    ]);
    return redirect()->route('catalogo.show', $producto)->with('success', 'Cambios guardados.');
}
```

En este proyecto (Django):

```python
# catalogo/urls.py
path("nuevo/", views.ProductoCreateView.as_view(), name="crear"),

# catalogo/views.py
class ProductoCreateView(LoginRequiredMixin, GuardadoSeguroMixin, CreateView):
    model = Producto
    form_class = ProductoForm            # ≈ StoreProductoRequest
    template_name = "catalogo/formulario.html"

    def form_valid(self, form):          # se ejecuta cuando la validación pasó
        form.instance.creado_por = self.request.user
        form.instance.actualizado_por = self.request.user
        return super().form_valid(form)  # guarda y redirige a get_absolute_url()
```

`CreateView` hace en una sola clase lo que en Laravel son `create()` (mostrar el formulario) y `store()` (guardarlo): con GET muestra el formulario y con POST lo valida y guarda. Los **mixins** (`LoginRequiredMixin`, `GuardadoSeguroMixin`) son como **traits** de PHP que además cumplen el papel del middleware de la ruta.

### Diferencias de enfoque

- **Las apps son autocontenidas.** En Laravel los modelos van en `app/Models` y los controladores en `app/Http/Controllers`, todo junto. En Django cada app tiene sus propios `models.py`, `views.py`, `urls.py` y `forms.py`.
- **El admin viene incluido.** `/admin/` es un panel CRUD automático, sin instalar nada como Nova o Filament.
- **No hay contenedor de dependencias ni facades.** Se importa directamente lo que se usa (`from .models import Producto`).
- **La validación vive en el Form, no en el request.** El mismo `ModelForm` valida los datos y además dibuja los campos en el template.
- **No hay `make:controller`.** Las vistas y las URLs se escriben a mano. Las vistas genéricas reemplazan casi todo el boilerplate.
