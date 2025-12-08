import json
from django.db.models import Count, Q
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from .models import Obra, Categoria, Tarefa, Pendencia
from .forms import ObraForm, CategoriaForm, TarefaForm, PendenciaForm, CategoriaInlineFormSet


class ObraListView(LoginRequiredMixin, ListView):
    model = Obra
    template_name = "obras/obra_list.html"
    context_object_name = "obras"

    def get_queryset(self):
        # aqui você pode filtrar por empresa/usuário depois, se precisar
        return (
            Obra.objects.all()
            .order_by("nome")
        )

class ObraCreateView(LoginRequiredMixin, CreateView):
    model = Obra
    form_class = ObraForm
    template_name = "obras/obra_form.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['categorias_formset'] = CategoriaInlineFormSet(self.request.POST, prefix='categorias')
        else:
            context['categorias_formset'] = CategoriaInlineFormSet(prefix='categorias')
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        formset = context['categorias_formset']
        if formset.is_valid():
            self.object = form.save()
            formset.instance = self.object
            formset.save()
            return super().form_valid(form)
        else:
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse_lazy("obras:detalhe_obra", kwargs={"pk": self.object.pk})

class ObraUpdateView(LoginRequiredMixin, UpdateView):
    model = Obra
    form_class = ObraForm
    template_name = "obras/obra_form.html"

    def get_success_url(self):
        return reverse_lazy("obras:detalhe_obra", kwargs={"pk": self.object.pk})


class CategoriaCreateView(LoginRequiredMixin, CreateView):
    model = Categoria
    form_class = CategoriaForm
    template_name = "obras/categoria_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.obra = get_object_or_404(Obra, pk=self.kwargs['obra_id'])
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.obra = self.obra
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['obra'] = self.obra
        return context

    def get_success_url(self):
        return reverse_lazy("obras:detalhe_obra", kwargs={"pk": self.obra.pk})


class TarefaCreateView(LoginRequiredMixin, CreateView):
    model = Tarefa
    form_class = TarefaForm
    template_name = "obras/tarefa_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.categoria = get_object_or_404(Categoria, pk=self.kwargs['categoria_id'])
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.categoria = self.categoria
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categoria'] = self.categoria
        context['obra'] = self.categoria.obra
        return context

    def get_success_url(self):
        return reverse_lazy("obras:detalhe_obra", kwargs={"pk": self.categoria.obra.pk})


class TarefaUpdateView(LoginRequiredMixin, UpdateView):
    model = Tarefa
    form_class = TarefaForm
    template_name = "obras/tarefa_form.html"

    def get_success_url(self):
        # self.object é a instância da tarefa que foi editada
        return reverse_lazy("obras:detalhe_obra", kwargs={"pk": self.object.categoria.obra.pk})


@login_required
@require_POST
def update_task_progress(request):
    try:
        data = json.loads(request.body)
        task_id = data.get("task_id")
        progress = int(data.get("progress"))

        if not (0 <= progress <= 100):
            return JsonResponse({"status": "error", "message": "Percentual inválido."}, status=400)

        task = get_object_or_404(Tarefa, pk=task_id)
        task.percentual_concluido = progress
        task.save()

        # Retorna o novo percentual da categoria para atualizar a UI
        return JsonResponse({
            "status": "success",
            "new_category_progress": task.categoria.percentual_concluido,
            "task_status": task.status,
            "task_status_display": task.get_status_display()
        })
    except (json.JSONDecodeError, TypeError, ValueError):
        return JsonResponse({"status": "error", "message": "Dados inválidos."}, status=400)

class PendenciaCreateView(LoginRequiredMixin, CreateView):
    model = Pendencia
    form_class = PendenciaForm
    template_name = "obras/pendencia_form.html"

    # Implementação similar à CategoriaCreateView (dispatch, form_valid, etc.)
    # para associar a pendência à obra correta.
    # (O código completo foi omitido por brevidade, mas segue o mesmo padrão)

    def get_success_url(self):
        return reverse_lazy("obras:detalhe_obra", kwargs={"pk": self.kwargs['obra_id']})

class ObraDetailView(LoginRequiredMixin, DetailView):
    model = Obra
    template_name = "obras/obra_detail.html"
    context_object_name = "obra"

    def get_queryset(self):
        # Otimiza a consulta, buscando previamente as categorias e suas respectivas tarefas
        return super().get_queryset().prefetch_related("categorias__tarefas")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obra = self.object

        # As categorias já vêm com as tarefas pré-carregadas devido ao get_queryset
        categorias = obra.categorias.all()

        # Otimização: Calcula o percentual de conclusão com uma única query
        stats = Tarefa.objects.filter(categoria__obra=obra).aggregate(
            total_tarefas=Count('id'),
            concluidas=Count('id', filter=Q(status='concluida'))
        )
        total_tarefas = stats.get('total_tarefas', 0)
        concluidas = stats.get('concluidas', 0)

        percentual_concluido = (
            (concluidas / total_tarefas) * 100 if total_tarefas > 0 else 0
        )

        context["categorias"] = categorias
        context["percentual_concluido"] = round(percentual_concluido, 1)
        return context
