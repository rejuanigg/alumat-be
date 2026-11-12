"""URLs de las pantallas web. Las de la API están en urls.py, bajo /api/."""

from django.urls import path

from . import vistas_web

app_name = "productos"
urlpatterns = [
    path("", vistas_web.ProductoListView.as_view(), name="lista"),
    path("nuevo/", vistas_web.ProductoCreateView.as_view(), name="crear"),
    path("<int:pk>/", vistas_web.ProductoDetailView.as_view(), name="detalle"),
    path("<int:pk>/editar/", vistas_web.ProductoUpdateView.as_view(), name="editar"),
    path(
        "<int:pk>/disenos/nuevo/",
        vistas_web.DisenoCreateView.as_view(),
        name="diseno_crear",
    ),
    path(
        "disenos/<int:pk>/editar/",
        vistas_web.DisenoUpdateView.as_view(),
        name="diseno_editar",
    ),
]
