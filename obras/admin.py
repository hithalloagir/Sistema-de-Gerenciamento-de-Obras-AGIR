from django.contrib import admin
from .models import Obra, Categoria, Tarefa, Pendencia, SolucaoPendencia


class CategoriaInline(admin.TabularInline):
    model = Categoria
    extra = 0


class TarefaInline(admin.TabularInline):
    model = Tarefa
    extra = 0


@admin.register(Obra)
class ObraAdmin(admin.ModelAdmin):
    list_display = ("nome", "cliente", "data_inicio", "data_fim_prevista", "criado_em")
    search_fields = ("nome", "cliente")
    list_filter = ("data_inicio", "data_fim_prevista")
    inlines = [CategoriaInline]


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ("nome", "obra", "prazo_final", "status")
    list_filter = ("obra", "status", "prazo_final")
    search_fields = ("nome", "obra__nome")
    ordering = ("obra", "nome")


@admin.register(Tarefa)
class TarefaAdmin(admin.ModelAdmin):
    list_display = ("nome", "categoria", "status", "ordem", "data_fim_prevista")
    list_filter = ("status", "categoria__obra", "categoria")
    search_fields = ("nome", "categoria__nome", "categoria__obra__nome")
    ordering = ("categoria", "ordem")


class SolucaoPendenciaInline(admin.TabularInline):
    model = SolucaoPendencia
    extra = 0


@admin.register(Pendencia)
class PendenciaAdmin(admin.ModelAdmin):
    list_display = (
        "descricao_curta",
        "obra",
        "categoria",
        "tarefa",
        "status",
        "prioridade",
        "responsavel",
        "data_abertura",
        "data_fechamento",
    )
    list_filter = (
        "status",
        "prioridade",
        "obra",
        "categoria",
        "tarefa",
        "responsavel",
    )
    search_fields = (
        "descricao",
        "obra__nome",
        "categoria__nome",
        "tarefa__nome",
        "responsavel__username",
    )
    inlines = [SolucaoPendenciaInline]

    def descricao_curta(self, obj):
        return (obj.descricao[:60] + "...") if len(obj.descricao) > 60 else obj.descricao

    descricao_curta.short_description = "Descrição"
