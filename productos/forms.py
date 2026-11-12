from django import forms

from .models import Diseno, Producto


class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = ("nombre", "tipo_abertura", "descripcion", "stock", "activo")
        labels = {"activo": "Activo (disponible para nuevos pedidos)"}
        help_texts = {"stock": "Cantidad de aberturas disponibles, sin importar sus medidas."}
        widgets = {"descripcion": forms.Textarea(attrs={"rows": 4})}


class DisenoForm(forms.ModelForm):
    class Meta:
        model = Diseno
        fields = ("nombre_diseno", "activo")
        labels = {"activo": "Activo (disponible para nuevos pedidos)"}

    def __init__(self, *args, producto=None, **kwargs):
        super().__init__(*args, **kwargs)
        if producto is not None:
            # El producto lo define la URL, no el formulario.
            self.instance.producto = producto

    def clean_nombre_diseno(self):
        # Django no valida la restricción única porque "producto" no es un
        # campo del formulario: se controla acá con un mensaje claro.
        nombre = self.cleaned_data["nombre_diseno"].strip()
        if (
            Diseno.objects.filter(
                producto_id=self.instance.producto_id, nombre_diseno__iexact=nombre
            )
            .exclude(pk=self.instance.pk)
            .exists()
        ):
            raise forms.ValidationError("El producto ya tiene un diseño con ese nombre.")
        return nombre
