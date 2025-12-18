from django.contrib import admin
from .models import PontoInspecaoTemplate, Inspecao, ItemInspecao, InspecaoAlteracaoTarefa


@admin.register(PontoInspecaoTemplate)
class PontoInspecaoTemplateAdmin(admin.ModelAdmin):
    list_display = ("nome", "obra", "ativo", "atualizado_em")
    list_filter = ("obra", "ativo")
    search_fields = ("nome", "obra__nome")
    ordering = ("obra", "nome")


class ItemInspecaoInline(admin.TabularInline):
    model = ItemInspecao
    extra = 0


class InspecaoAlteracaoTarefaInline(admin.TabularInline):
    model = InspecaoAlteracaoTarefa
    extra = 0
    readonly_fields = ("criado_em",)


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
    inlines = [ItemInspecaoInline, InspecaoAlteracaoTarefaInline]
    ordering = ("-data_inspecao", "-id")


@admin.register(ItemInspecao)
class ItemInspecaoAdmin(admin.ModelAdmin):
    list_display = ("inspecao", "ponto", "status", "atualizado_em")
    list_filter = ("status", "ponto__obra")
    search_fields = ("ponto__nome", "inspecao__obra__nome")


@admin.register(InspecaoAlteracaoTarefa)
class InspecaoAlteracaoTarefaAdmin(admin.ModelAdmin):
    list_display = ("inspecao", "tarefa", "percentual_antes", "percentual_depois", "criado_em")
    list_filter = ("inspecao__obra", "tarefa__categoria")
    search_fields = ("inspecao__obra__nome", "tarefa__nome", "tarefa__categoria__nome")
    ordering = ("-criado_em", "-id")
