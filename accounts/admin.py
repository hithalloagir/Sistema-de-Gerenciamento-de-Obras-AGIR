from django.contrib import admin
from .models import UserProfile, ObraAlocacao


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "empresa")
    list_filter = ("role",)
    search_fields = ("user__username", "empresa")


@admin.register(ObraAlocacao)
class ObraAlocacaoAdmin(admin.ModelAdmin):
    list_display = ("obra", "usuario", "alocado_por", "criado_em")
    list_filter = ("obra",)
    search_fields = ("obra__nome", "usuario__username")
