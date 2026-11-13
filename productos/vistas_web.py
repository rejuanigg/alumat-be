"""Pantallas web de productos y diseños (la API está en views.py)."""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from cuentas.permisos import es_dueno

from .forms import DisenoForm, ProductoForm
from .models import Diseno, Producto


class SinDuenoMixin:
    """El Dueño solo consulta: no entra a las pantallas de alta ni de edición (403)."""

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and es_dueno(request.user):
            raise PermissionDenied("El Dueño solo puede consultar información.")
        return super().dispatch(request, *args, **kwargs)


class GuardadoSeguroMixin:
    def form_valid(self, form):
        try:
            with transaction.atomic():
                response = super().form_valid(form)
        except IntegrityError:
            form.add_error(
                None,
                "No se pudo guardar: otro registro usa esos datos. Revisá e intentá de nuevo.",
            )
            return self.form_invalid(form)
        messages.success(self.request, "Cambios guardados.")
        return response


class ProductoListView(LoginRequiredMixin, ListView):
    model = Producto
    template_name = "productos/lista.html"
    paginate_by = 12

    def get_queryset(self):
        # Con Count, Django no aplica el orden del modelo: se indica acá.
        qs = Producto.objects.annotate(
            cantidad_disenos=Count("disenos", filter=Q(disenos__activo=True))
        ).order_by("nombre", "id_producto")
        q = self.request.GET.get("q", "").strip()[:100]
        if q:
            qs = qs.filter(Q(nombre__icontains=q) | Q(tipo_abertura__icontains=q))
        return qs


class ProductoDetailView(LoginRequiredMixin, DetailView):
    model = Producto
    template_name = "productos/detalle.html"


class ProductoCreateView(LoginRequiredMixin, SinDuenoMixin, GuardadoSeguroMixin, CreateView):
    model = Producto
    form_class = ProductoForm
    template_name = "productos/formulario.html"


class ProductoUpdateView(LoginRequiredMixin, SinDuenoMixin, GuardadoSeguroMixin, UpdateView):
    model = Producto
    form_class = ProductoForm
    template_name = "productos/formulario.html"


class DisenoCreateView(LoginRequiredMixin, SinDuenoMixin, GuardadoSeguroMixin, CreateView):
    model = Diseno
    form_class = DisenoForm
    template_name = "productos/diseno_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.producto = get_object_or_404(Producto, pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "producto": self.producto}

    def form_valid(self, form):
        if not self.producto.activo:
            form.add_error(None, "No se puede agregar un diseño a un producto inactivo.")
            return self.form_invalid(form)
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), "producto": self.producto}

    def get_success_url(self):
        return self.producto.get_absolute_url()


class DisenoUpdateView(LoginRequiredMixin, SinDuenoMixin, GuardadoSeguroMixin, UpdateView):
    model = Diseno
    form_class = DisenoForm
    template_name = "productos/diseno_form.html"

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), "producto": self.object.producto}

    def get_success_url(self):
        return self.object.producto.get_absolute_url()
