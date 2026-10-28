from django import forms
from .models import Categoria, Producto


class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = ("codigo", "nombre", "categoria", "descripcion", "precio", "stock")
        widgets = {"descripcion": forms.Textarea(attrs={"rows": 4})}

    def clean_codigo(self):
        codigo = self.cleaned_data["codigo"].strip().upper()
        if (
            Producto.objects.filter(codigo__iexact=codigo)
            .exclude(pk=self.instance.pk)
            .exists()
        ):
            raise forms.ValidationError("Ya existe un producto con ese código.")
        return codigo


class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ("nombre",)

    def clean_nombre(self):
        nombre = self.cleaned_data["nombre"].strip()
        if (
            Categoria.objects.filter(nombre__iexact=nombre)
            .exclude(pk=self.instance.pk)
            .exists()
        ):
            raise forms.ValidationError("Ya existe esa categoría.")
        return nombre
