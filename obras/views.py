import json
from django.db.models import Count, Q
from django.views.generic import ListView, DetailView, CreateView, UpdateView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone

from .models import Obra, Categoria, Tarefa, Pendencia, AnexoObra
from .forms import (
    ObraForm,
    CategoriaForm,
    TarefaForm,
    PendenciaForm,
    CategoriaInlineFormSet,
    AnexoObraForm,
)
from accounts.mixins import RoleRequiredMixin


class ObraListView(LoginRequiredMixin, ListView):
    model = Obra
    template_name = "obras/obra_list.html"
    context_object_name = "obras"

    def get_queryset(self):
        qs = Obra.objects.all().order_by("nome")
        status = self.request.GET.get("status")
        q = self.request.GET.get("q")
        if status:
            qs = qs.filter(status=status)
        if q:
            qs = qs.filter(nome__icontains=q)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        status_counts = Obra.objects.values("status").annotate(total=Count("id"))
        counts = {item["status"]: item["total"] for item in status_counts}
        context["counts"] = counts
        context["status_filter"] = self.request.GET.get("status", "")
        context["search_query"] = self.request.GET.get("q", "")
        # Percentual por obra
        perc_map = {}
        for obra in context["obras"]:
            stats = Tarefa.objects.filter(categoria__obra=obra).aggregate(
                total=Count("id"),
                concluidas=Count("id", filter=Q(status="concluida")),
            )
            total = stats.get("total") or 0
            concl = stats.get("concluidas") or 0
            perc_map[obra.id] = round((concl / total) * 100, 1) if total else 0
        for obra in context["obras"]:
            obra.perc_concluido = perc_map.get(obra.id, 0)
        return context


class ObraOverviewView(LoginRequiredMixin, ListView):
    model = Obra
    template_name = "obras/visao_geral.html"
    context_object_name = "obras"

    def get_queryset(self):
        return (
            Obra.objects
            .all()
            .prefetch_related("categorias__tarefas")
            .annotate(pendencias_abertas=Count("pendencias", filter=Q(pendencias__status="aberta")))
            .order_by("nome")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        hoje = timezone.now().date()
        obras_json = []
        chart_lines = []
        for obra in context["obras"]:
            stats = Tarefa.objects.filter(categoria__obra=obra).aggregate(
                total=Count("id"),
                concluidas=Count("id", filter=Q(status="concluida")),
            )
            total = stats.get("total") or 0
            concl = stats.get("concluidas") or 0
            obra.perc_concluido = round((concl / total) * 100, 1) if total else 0
            obra.dias_restantes = (obra.data_fim_prevista - hoje).days if obra.data_fim_prevista else None
            obras_json.append({
                "id": obra.id,
                "nome": obra.nome,
                "perc_concluido": obra.perc_concluido,
                "pendencias_abertas": getattr(obra, "pendencias_abertas", 0),
                "dias_restantes": obra.dias_restantes,
            })
            if obra.data_inicio and obra.data_fim_prevista:
                dias_totais = (obra.data_fim_prevista - obra.data_inicio).days or 1
                dias_passados = (hoje - obra.data_inicio).days
                chart_lines.append({
                    "nome": obra.nome,
                    "pontos": [
                        {"x": 0, "y": 0},
                        {"x": max(dias_passados, 0), "y": obra.perc_concluido},
                        {"x": dias_totais, "y": 100},
                    ],
                })
        context["obras_json"] = obras_json
        context["chart_lines"] = chart_lines
        return context


class ObraCreateView(RoleRequiredMixin, CreateView):
    model = Obra
    form_class = ObraForm
    template_name = "obras/obra_form.html"
    allowed_roles = ["admin"]
    
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
        return self.form_invalid(form)

    def get_success_url(self):
        return reverse_lazy("obras:detalhe_obra", kwargs={"pk": self.object.pk})


class ObraUpdateView(RoleRequiredMixin, UpdateView):
    model = Obra
    form_class = ObraForm
    template_name = "obras/obra_form.html"
    allowed_roles = ["admin", "avaliador", "gerente", "engenheiro", "fiscal"]

    def get_success_url(self):
        return reverse_lazy("obras:detalhe_obra", kwargs={"pk": self.object.pk})


class CategoriaCreateView(RoleRequiredMixin, CreateView):
    model = Categoria
    form_class = CategoriaForm
    template_name = "obras/categoria_form.html"
    allowed_roles = ["admin"]

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


class TarefaCreateView(RoleRequiredMixin, CreateView):
    model = Tarefa
    form_class = TarefaForm
    template_name = "obras/tarefa_form.html"
    allowed_roles = ["admin", "avaliador", "gerente", "engenheiro", "fiscal"]

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
        context['current_categoria'] = self.categoria
        context['current_obra'] = self.categoria.obra
        return context

    def get_success_url(self):
        return reverse_lazy("obras:detalhe_obra", kwargs={"pk": self.categoria.obra.pk})


class TarefaUpdateView(RoleRequiredMixin, UpdateView):
    model = Tarefa
    form_class = TarefaForm
    template_name = "obras/tarefa_form.html"
    allowed_roles = ["admin", "avaliador", "gerente", "engenheiro", "fiscal"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["obra"] = self.object.categoria.obra
        context["categoria"] = self.object.categoria
        context["current_obra"] = self.object.categoria.obra
        context["current_categoria"] = self.object.categoria
        return context

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

        return JsonResponse({
            "status": "success",
            "new_category_progress": task.categoria.percentual_concluido,
            "task_status": task.status,
            "task_status_display": task.get_status_display(),
            "task_real_end_date": task.data_fim_real.strftime("%d/%m/%Y") if task.data_fim_real else None
        })
    except (json.JSONDecodeError, TypeError, ValueError):
        return JsonResponse({"status": "error", "message": "Dados inválidos."}, status=400)


class PendenciaCreateView(RoleRequiredMixin, CreateView):
    model = Pendencia
    form_class = PendenciaForm
    template_name = "obras/pendencia_form.html"
    allowed_roles = ["admin", "avaliador", "gerente", "engenheiro", "fiscal"]

    def dispatch(self, request, *args, **kwargs):
        self.obra = get_object_or_404(Obra, pk=kwargs["obra_id"])
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["obra"] = self.obra  # filtra tarefas da obra
        return kwargs

    def form_valid(self, form):
        tarefa = form.cleaned_data["tarefa"]
        if tarefa.categoria.obra_id != self.obra.id:
            form.add_error("tarefa", "Tarefa não pertence a esta obra.")
            return self.form_invalid(form)

        form.instance.obra = self.obra
        form.instance.categoria = tarefa.categoria
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["obra"] = self.obra
        return context

    def get_success_url(self):
        return reverse_lazy("obras:detalhe_obra", kwargs={"pk": self.kwargs['obra_id']})


class ObraDetailView(LoginRequiredMixin, DetailView):
    model = Obra
    template_name = "obras/obra_detail.html"
    context_object_name = "obra"

    def get_queryset(self):
        # Otimiza a consulta, buscando previamente as categorias e suas respectivas tarefas
        return super().get_queryset().prefetch_related("categorias__tarefas", "anexos")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obra = self.object

        # As categorias já vêm com as tarefas pré-carregadas devido ao get_queryset
        categorias = obra.categorias.all()

        stats = Tarefa.objects.filter(categoria__obra=obra).aggregate(
            total_tarefas=Count('id'),
            concluidas=Count('id', filter=Q(status='concluida')),
            atrasadas=Count('id', filter=Q(status='bloqueada')),
        )
        total_tarefas = stats.get('total_tarefas', 0)
        concluidas = stats.get('concluidas', 0)
        atrasadas = stats.get('atrasadas', 0)

        percentual_concluido = (concluidas / total_tarefas) * 100 if total_tarefas > 0 else 0

        context["categorias"] = categorias
        context["percentual_concluido"] = round(percentual_concluido, 1)
        context["stats_resumo"] = {
            "total": total_tarefas,
            "concluidas": concluidas,
            "atrasadas": atrasadas,
        }
        context["inspecoes_recentes"] = obra.inspecoes.select_related("usuario", "categoria", "tarefa").order_by("-data_inspecao", "-id")[:5]
        context["anexo_form"] = AnexoObraForm()
        context["anexos"] = obra.anexos.select_related("categoria", "enviado_por")
        return context


class AnexoObraCreateView(RoleRequiredMixin, CreateView):
    model = AnexoObra
    form_class = AnexoObraForm
    template_name = "obras/anexo_form.html"
    allowed_roles = ["admin", "avaliador", "gerente", "engenheiro", "fiscal"]

    def dispatch(self, request, *args, **kwargs):
        self.obra = get_object_or_404(Obra, pk=self.kwargs["obra_id"])
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.obra = self.obra
        form.instance.enviado_por = self.request.user
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["obra"] = self.obra
        return context

    def get_success_url(self):
        return reverse_lazy("obras:detalhe_obra", kwargs={"pk": self.obra.pk})


class ConcluirObraView(RoleRequiredMixin, View):
    allowed_roles = ["admin", "avaliador", "gerente", "engenheiro", "fiscal"]
    def post(self, request, pk):
        obra = get_object_or_404(Obra, pk=pk)
        obra.status = "finalizada"
        if not obra.data_fim_prevista:
            obra.data_fim_prevista = timezone.now().date()
        obra.save(update_fields=["status", "data_fim_prevista", "atualizado_em"])
        messages.success(request, "Obra marcada como concluída.")
        return redirect("obras:detalhe_obra", pk=obra.pk)


class PendenciaListView(LoginRequiredMixin, ListView):
    model = Pendencia
    template_name = "obras/pendencia_list.html"
    context_object_name = "pendencias"

    def get_queryset(self):
        qs = Pendencia.objects.select_related("obra", "tarefa", "categoria", "responsavel").order_by("-data_abertura")
        status = self.request.GET.get("status")
        q = self.request.GET.get("q")
        if status:
            qs = qs.filter(status=status)
        if q:
            qs = qs.filter(
                Q(descricao__icontains=q) |
                Q(obra__nome__icontains=q) |
                Q(tarefa__nome__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        status_counts = Pendencia.objects.values("status").annotate(total=Count("id"))
        counts = {item["status"]: item["total"] for item in status_counts}
        context["counts"] = counts
        context["status_filter"] = self.request.GET.get("status", "")
        context["search_query"] = self.request.GET.get("q", "")
        return context
