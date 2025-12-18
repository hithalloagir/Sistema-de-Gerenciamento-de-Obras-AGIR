from django.urls import path
from . import views

app_name = "obras"

urlpatterns = [
    path("", views.ObraListView.as_view(), name="listar_obras"),
    path("nova/", views.ObraCreateView.as_view(), name="nova_obra"),
    path("<int:pk>/", views.ObraDetailView.as_view(), name="detalhe_obra"),
    path("visao-geral/", views.ObraOverviewView.as_view(), name="visao_geral"),
    path("<int:pk>/relatorio/", views.ObraReportView.as_view(), name="relatorio_obra"),
    path("<int:pk>/editar/", views.ObraUpdateView.as_view(), name="editar_obra"),
    path("<int:pk>/excluir/", views.ExcluirObraView.as_view(), name="excluir_obra"),
    path("<int:obra_id>/nova-categoria/", views.CategoriaCreateView.as_view(), name="nova_categoria"),
    path("categorias/<int:pk>/editar/", views.CategoriaUpdateView.as_view(), name="editar_categoria"),
    path("categorias/<int:pk>/excluir/", views.CategoriaDeleteView.as_view(), name="excluir_categoria"),
    path("<int:obra_id>/nova-pendencia/", views.PendenciaCreateView.as_view(), name="nova_pendencia"),
    path("<int:obra_id>/novo-anexo/", views.AnexoObraCreateView.as_view(), name="novo_anexo"),
    path("categoria/<int:categoria_id>/nova-tarefa/", views.TarefaCreateView.as_view(), name="nova_tarefa"),
    path("tarefas/<int:pk>/editar/", views.TarefaUpdateView.as_view(), name="editar_tarefa"),
    path("tarefas/<int:pk>/excluir/", views.TarefaDeleteView.as_view(), name="excluir_tarefa"),
    path("tarefa/<int:pk>/editar/", views.TarefaUpdateView.as_view(), name="editar_tarefa_legacy"),
    path("tarefa/update-progress/", views.update_task_progress, name="update_task_progress"),
    path("<int:pk>/concluir/", views.ConcluirObraView.as_view(), name="concluir_obra"),
    path("pendencias/", views.PendenciaListView.as_view(), name="listar_pendencias"),
    path("pendencias/<int:pk>/", views.PendenciaDetailView.as_view(), name="detalhe_pendencia"),
    path("pendencias/<int:pk>/atualizar/", views.PendenciaUpdateStatusView.as_view(), name="atualizar_pendencia"),
]
