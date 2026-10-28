from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ("username", "email", "estado", "is_active", "is_superuser")
    readonly_fields = ("estado",)
    fieldsets = UserAdmin.fieldsets + (("Aprobación", {"fields": ("estado",)}),)

    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_add_permission(self, request):
        # Las altas pasan por registro; el primer administrador usa createsuperuser.
        return False

    def has_delete_permission(self, request, obj=None):
        return False
