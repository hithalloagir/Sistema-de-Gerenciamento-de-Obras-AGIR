from django.contrib import admin
from .models import PontoInspecaoTemplate, Inspecao, ItemInspecao


@admin.register(PontoInspecaoTemplate)
class PontoInspecaoTemplateAdmin(admin.ModelAdmin):
    list_display = ("nome", "obra", "ativo", "atualizado_em")
    list_filter = ("obra", "ativo")
    search_fields = ("nome", "obra__nome")
    ordering = ("obra", "nome")


class ItemInspecaoInline(admin.TabularInline):
    model = ItemInspecao
    extra = 0


@admin.register(Inspecao)
class InspecaoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "obra",
        "categoria",
        "tarefa",
        "usuario",
        "data_inspecao",
        "latitude",
        "longitude",
    )
    list_filter = (
        "obra",
        "categoria",
        "tarefa",
        "usuario",
        "data_inspecao",
    )
    search_fields = (
        "obra__nome",
        "categoria__nome",
        "tarefa__nome",
        "usuario__username",
    )
    date_hierarchy = "data_inspecao"
    inlines = [ItemInspecaoInline]
    ordering = ("-data_inspecao", "-id")


@admin.register(ItemInspecao)
class ItemInspecaoAdmin(admin.ModelAdmin):
    list_display = ("inspecao", "ponto", "status", "atualizado_em")
    list_filter = ("status", "ponto__obra")
    search_fields = ("ponto__nome", "inspecao__obra__nome")
