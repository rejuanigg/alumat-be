from django.urls import path
from . import views

app_name = "catalogo"
urlpatterns = [
    path("", views.ProductoListView.as_view(), name="lista"),
    path("nuevo/", views.ProductoCreateView.as_view(), name="crear"),
    path("<int:pk>/", views.ProductoDetailView.as_view(), name="detalle"),
    path("<int:pk>/editar/", views.ProductoUpdateView.as_view(), name="editar"),
    path("<int:pk>/eliminar/", views.ProductoDeleteView.as_view(), name="eliminar"),
    path("categorias/", views.CategoriaListView.as_view(), name="categorias"),
    path(
        "categorias/nueva/", views.CategoriaCreateView.as_view(), name="categoria_crear"
    ),
    path(
        "categorias/<int:pk>/editar/",
        views.CategoriaUpdateView.as_view(),
        name="categoria_editar",
    ),
    path(
        "categorias/<int:pk>/eliminar/",
        views.CategoriaDeleteView.as_view(),
        name="categoria_eliminar",
    ),
]
