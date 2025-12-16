import json
from django.db import transaction
from django.db.models import Count, Q
from django.core.paginator import Paginator
from django.views.generic import ListView, DetailView, CreateView, UpdateView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme

from .models import Obra, Categoria, Tarefa, Pendencia, AnexoObra, SolucaoPendencia
from .forms import (
    ObraForm,
    ObraCreateForm,
    CategoriaForm,
    TarefaForm,
    PendenciaForm,
    CategoriaInlineFormSet,
    AnexoObraForm,
)
from .services import (
    clone_obra_structure,
    generate_duplicate_name,
    get_last_accessible_obra,
)
from accounts.mixins import RoleRequiredMixin, level_required
from accounts.models import UserProfile
from accounts.utils import (
    filter_obras_for_user,
    filter_queryset_by_user_obras,
    get_user_level,
    user_has_obra_access,
)
from .constants import NO_OBRA_PERMISSION_MESSAGE, READ_ONLY_MESSAGE, STATUS_FILTERS


def obra_read_only_redirect(request, obra):
    messages.error(request, READ_ONLY_MESSAGE)
    return redirect("obras:detalhe_obra", pk=obra.pk)


class ObraListView(LoginRequiredMixin, ListView):
    model = Obra
    template_name = "obras/obra_list.html"
    context_object_name = "obras"

    def get_queryset(self):
        qs = filter_obras_for_user(Obra.objects.all().order_by("nome"), self.request.user)
        status = self.request.GET.get("status") or "ativa"
        if status not in STATUS_FILTERS:
            status = "ativa"
        q = (self.request.GET.get("q") or "").strip()

        if q:
            qs = qs.filter(nome__icontains=q)
        qs = qs.filter(status=status)

        self.status_filter = status
        self.search_query = q
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        base_qs = filter_obras_for_user(Obra.objects.all(), self.request.user)
        if self.search_query:
            base_qs = base_qs.filter(nome__icontains=self.search_query)
        status_counts = base_qs.values("status").annotate(total=Count("id"))
        counts = {"ativa": 0, "finalizada": 0}
        counts.update({item["status"]: item["total"] for item in status_counts})

        context["counts"] = counts
        context["status_filter"] = getattr(self, "status_filter", "ativa")
        context["search_query"] = getattr(self, "search_query", "")
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
        qs = (
            Obra.objects
            .all()
            .prefetch_related("categorias__tarefas")
            .annotate(pendencias_abertas=Count("pendencias", filter=Q(pendencias__status="aberta")))
        )
        qs = filter_obras_for_user(qs, self.request.user)
        return qs.order_by("nome")

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
    form_class = ObraCreateForm
    template_name = "obras/obra_form.html"
    allowed_roles = [UserProfile.Level.ADMIN, UserProfile.Level.NIVEL2]

    def dispatch(self, request, *args, **kwargs):
        self.user_level = get_user_level(request.user)
        self._last_model_obra = get_last_accessible_obra(request.user)
        if self.user_level == UserProfile.Level.NIVEL2 and self._last_model_obra is None:
            messages.error(request, "Nao ha obras disponiveis para duplicar.")
            return redirect("obras:listar_obras")
        return super().dispatch(request, *args, **kwargs)

    def get_last_model_obra(self):
        if not hasattr(self, "_last_model_obra") or self._last_model_obra is None:
            self._last_model_obra = get_last_accessible_obra(self.request.user)
        return self._last_model_obra

    def user_can_duplicate(self):
        user_level = getattr(self, "user_level", get_user_level(self.request.user))
        return (
            user_level in (UserProfile.Level.ADMIN, UserProfile.Level.NIVEL2)
            and self.get_last_model_obra() is not None
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["last_obra"] = self.get_last_model_obra()
        kwargs["allow_duplicate"] = self.user_can_duplicate()
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context["categorias_formset"] = CategoriaInlineFormSet(self.request.POST, prefix="categorias")
        else:
            context["categorias_formset"] = CategoriaInlineFormSet(prefix="categorias")
        context["can_duplicate_last_obra"] = self.user_can_duplicate()
        context["last_obra_for_duplicate"] = self.get_last_model_obra()
        context["creator_user_level"] = getattr(self, "user_level", get_user_level(self.request.user))
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        formset = context["categorias_formset"]
        duplicate_last = bool(form.cleaned_data.get("duplicate_last"))

        if getattr(self, "user_level", None) == UserProfile.Level.NIVEL2 and not duplicate_last:
            form.add_error(None, "Usuarios nivel 2 so podem criar obras duplicando o ultimo modelo.")
            messages.error(self.request, "Selecione a opcao de duplicar ultima obra para continuar.")
            return self.form_invalid(form)

        if duplicate_last and not self.user_can_duplicate():
            form.add_error("duplicate_last", "Nao foi possivel localizar uma obra para duplicar.")
            messages.error(self.request, "Nao ha obras disponiveis para duplicacao.")
            return self.form_invalid(form)

        if not duplicate_last and not formset.is_valid():
            return self.form_invalid(form)

        source_obra = self.get_last_model_obra() if duplicate_last else None

        with transaction.atomic():
            self.object = form.save(commit=False)
            if duplicate_last and source_obra:
                self.object.nome = generate_duplicate_name(source_obra.nome)
                self.object.status = "ativa"
            self.object.save()
            form.save_m2m()

            if duplicate_last and source_obra:
                clone_obra_structure(source_obra, self.object)
            else:
                formset.instance = self.object
                formset.save()

        if duplicate_last:
            messages.success(
                self.request,
                f"Obra criada a partir de '{source_obra.nome}' (categorias e tarefas copiadas).",
            )
        else:
            messages.success(self.request, "Obra criada com sucesso.")

        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse_lazy("obras:detalhe_obra", kwargs={"pk": self.object.pk})


class ObraUpdateView(RoleRequiredMixin, UpdateView):
    model = Obra
    form_class = ObraForm
    template_name = "obras/obra_form.html"
    allowed_roles = [UserProfile.Level.ADMIN]

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.status == "finalizada":
            return obra_read_only_redirect(request, self.object)
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return filter_obras_for_user(super().get_queryset(), self.request.user)

    def get_success_url(self):
        return reverse_lazy("obras:detalhe_obra", kwargs={"pk": self.object.pk})


class CategoriaCreateView(RoleRequiredMixin, CreateView):
    model = Categoria
    form_class = CategoriaForm
    template_name = "obras/categoria_form.html"
    allowed_roles = [UserProfile.Level.ADMIN, UserProfile.Level.NIVEL2]

    def dispatch(self, request, *args, **kwargs):
        self.obra = get_object_or_404(Obra, pk=self.kwargs['obra_id'])
        denied = self.ensure_obra_access(self.obra)
        if denied:
            return denied
        if self.obra.status == "finalizada":
            return obra_read_only_redirect(request, self.obra)
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
    allowed_roles = [UserProfile.Level.ADMIN, UserProfile.Level.NIVEL2]

    def dispatch(self, request, *args, **kwargs):
        self.categoria = get_object_or_404(Categoria, pk=self.kwargs['categoria_id'])
        denied = self.ensure_obra_access(self.categoria.obra)
        if denied:
            return denied
        if self.categoria.obra.status == "finalizada":
            return obra_read_only_redirect(request, self.categoria.obra)
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
    allowed_roles = [UserProfile.Level.ADMIN, UserProfile.Level.NIVEL2]

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        denied = self.ensure_obra_access(self.object.categoria.obra)
        if denied:
            return denied
        if self.object.categoria.obra.status == "finalizada":
            return obra_read_only_redirect(request, self.object.categoria.obra)
        return super().dispatch(request, *args, **kwargs)

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
@login_required
@require_POST
@level_required(
    [
        UserProfile.Level.ADMIN,
        UserProfile.Level.NIVEL2,
        UserProfile.Level.NIVEL1,
    ],
    json_response=True,
    message="Você não tem permissão para atualizar esta tarefa.",
)
def update_task_progress(request):
    try:
        data = json.loads(request.body)
        task_id = data.get("task_id")
        progress = int(data.get("progress"))

        if not (0 <= progress <= 100):
            return JsonResponse({"status": "error", "message": "Percentual inválido."}, status=400)

        task = get_object_or_404(Tarefa, pk=task_id)
        obra = task.categoria.obra
        if not user_has_obra_access(request.user, obra):
            return JsonResponse(
                {"status": "error", "message": NO_OBRA_PERMISSION_MESSAGE},
                status=403,
            )

        user_level = get_user_level(request.user)
        if user_level == UserProfile.Level.NIVEL1 and task.status == "concluida":
            return JsonResponse(
                {
                    "status": "locked",
                    "message": "Tarefa concluída. Solicite apoio de um usuário Nível 2 para ajustes.",
                },
                status=403,
            )

        if obra.status == "finalizada":
            return JsonResponse(
                {"status": "error", "message": READ_ONLY_MESSAGE},
                status=403,
            )

        task.percentual_concluido = progress
        task.save()

        return JsonResponse({
            "status": "success",
            "new_category_progress": task.categoria.percentual_concluido,
            "task_status": task.status,
            "task_status_display": task.get_status_display(),
            "task_real_end_date": task.data_fim_real.strftime("%d/%m/%Y") if task.data_fim_real else None,
            "task_completed": progress == 100,
        })
    except (json.JSONDecodeError, TypeError, ValueError):
        return JsonResponse({"status": "error", "message": "Dados inválidos."}, status=400)


class PendenciaCreateView(RoleRequiredMixin, CreateView):
    model = Pendencia
    form_class = PendenciaForm
    template_name = "obras/pendencia_form.html"
    allowed_roles = [
        UserProfile.Level.ADMIN,
        UserProfile.Level.NIVEL2,
        UserProfile.Level.NIVEL1,
    ]

    def dispatch(self, request, *args, **kwargs):
        self.obra = get_object_or_404(Obra, pk=kwargs["obra_id"])
        denied = self.ensure_obra_access(self.obra)
        if denied:
            return denied
        if self.obra.status == "finalizada":
            return obra_read_only_redirect(request, self.obra)
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
        qs = super().get_queryset().prefetch_related("categorias__tarefas", "anexos")
        return filter_obras_for_user(qs, self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obra = self.object

        # As categorias ja vem com as tarefas pre-carregadas devido ao get_queryset
        categorias = obra.categorias.all()

        pend_status = self.request.GET.get("pend_status") or "aberta"
        pendencias_qs = (
            obra.pendencias.select_related("tarefa", "categoria", "responsavel")
            .prefetch_related("solucoes__usuario")
            .order_by("-data_abertura")
        )
        pend_counts_qs = pendencias_qs.values("status").annotate(total=Count("id"))
        pend_counts = {"aberta": 0, "andamento": 0, "resolvida": 0}
        pend_counts.update({item["status"]: item["total"] for item in pend_counts_qs})
        if pend_status not in pend_counts:
            pend_status = "aberta"
        pendencias = pendencias_qs.filter(status=pend_status)

        stats = Tarefa.objects.filter(categoria__obra=obra).aggregate(
            total_tarefas=Count("id"),
            concluidas=Count("id", filter=Q(status="concluida")),
            atrasadas=Count("id", filter=Q(status="bloqueada")),
        )
        total_tarefas = stats.get("total_tarefas", 0)
        concluidas = stats.get("concluidas", 0)
        atrasadas = stats.get("atrasadas", 0)

        percentual_concluido = (concluidas / total_tarefas) * 100 if total_tarefas > 0 else 0

        inspecoes_qs = obra.inspecoes.select_related("usuario", "categoria", "tarefa").order_by(
            "-data_inspecao", "-id"
        )
        insp_paginator = Paginator(inspecoes_qs, 10)
        insp_page_number = self.request.GET.get("insp_page")
        inspecoes_page = insp_paginator.get_page(insp_page_number)

        context["categorias"] = categorias
        context["percentual_concluido"] = round(percentual_concluido, 1)
        context["stats_resumo"] = {
            "total": total_tarefas,
            "concluidas": concluidas,
            "atrasadas": atrasadas,
        }
        context["pendencias"] = pendencias
        context["pendencias_counts"] = pend_counts
        context["pendencias_status"] = pend_status
        context["inspecoes_page"] = inspecoes_page
        context["inspecoes_total"] = inspecoes_page.paginator.count
        context["pendencias_redirect"] = self.request.get_full_path()
        context["anexo_form"] = AnexoObraForm()
        context["anexos"] = obra.anexos.select_related("categoria", "enviado_por")
        user_level = get_user_level(self.request.user)
        context["user_level"] = user_level
        context["can_manage_obra"] = user_level == UserProfile.Level.ADMIN
        context["can_manage_structure"] = user_level in (
            UserProfile.Level.ADMIN,
            UserProfile.Level.NIVEL2,
        )
        context["can_manage_pendencias"] = user_level in (
            UserProfile.Level.ADMIN,
            UserProfile.Level.NIVEL2,
            UserProfile.Level.NIVEL1,
        )
        context["can_add_inspecao"] = context["can_manage_pendencias"]
        context["can_add_anexo"] = context["can_manage_pendencias"]
        context["can_update_task_progress"] = context["can_manage_pendencias"]
        context["nivel1_lock_message"] = (
            "Tarefa concluída. Solicite apoio de um usuário Nível 2 para ajustes."
        )
        return context



class ObraReportView(LoginRequiredMixin, DetailView):
    model = Obra
    template_name = "obras/relatorio_obra.html"
    context_object_name = "obra"

    def get_queryset(self):
        qs = (
            super()
            .get_queryset()
            .prefetch_related(
                "categorias__tarefas",
                "pendencias__tarefa",
                "pendencias__categoria",
                "pendencias__responsavel",
            )
        )
        return filter_obras_for_user(qs, self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obra = self.object
        tarefas_stats = Tarefa.objects.filter(categoria__obra=obra).aggregate(
            total=Count("id"),
            concluidas=Count("id", filter=Q(status="concluida")),
        )
        total_tarefas = tarefas_stats.get("total") or 0
        concluidas = tarefas_stats.get("concluidas") or 0
        progresso_real = (
            round((concluidas / total_tarefas) * 100, 1) if total_tarefas else 0
        )
        progresso_esperado = self._calc_progresso_esperado(obra)

        pendencias = (
            obra.pendencias.select_related("tarefa", "categoria", "responsavel")
            .order_by("status", "-data_abertura")
        )
        pendencias_grupos = {
            "aberta": [],
            "andamento": [],
            "resolvida": [],
        }
        for pendencia in pendencias:
            pendencias_grupos.setdefault(pendencia.status, []).append(pendencia)
        pendencias_counts = {
            status: len(items) for status, items in pendencias_grupos.items()
        }

        inspecoes_qs = obra.inspecoes.select_related("usuario", "categoria", "tarefa").order_by("-data_inspecao", "-id")
        inspecoes_total = inspecoes_qs.count()
        inspecoes_recentes = list(inspecoes_qs[:5])
        ultima_inspecao = inspecoes_recentes[0] if inspecoes_recentes else None

        context.update(
            {
                "categorias": obra.categorias.all(),
                "total_tarefas": total_tarefas,
                "tarefas_concluidas": concluidas,
                "progresso_real": progresso_real,
                "progresso_esperado": progresso_esperado,
                "pendencias_por_status": pendencias_grupos,
                "pendencias_counts": pendencias_counts,
                "pendencias_total": sum(pendencias_counts.values()),
                "inspecoes_total": inspecoes_total,
                "ultima_inspecao": ultima_inspecao,
                "inspecoes_recentes": inspecoes_recentes,
                "generated_at": timezone.now(),
            }
        )
        return context

    def _calc_progresso_esperado(self, obra):
        if obra.data_inicio and obra.data_fim_prevista:
            total_dias = (obra.data_fim_prevista - obra.data_inicio).days
            if total_dias <= 0:
                return 100.0 if timezone.now().date() >= obra.data_fim_prevista else 0.0
            dias_passados = (timezone.now().date() - obra.data_inicio).days
            percentual = (dias_passados / total_dias) * 100
            percentual = max(0, min(percentual, 100))
            return round(percentual, 1)
        return None


class AnexoObraCreateView(RoleRequiredMixin, CreateView):
    model = AnexoObra
    form_class = AnexoObraForm
    template_name = "obras/anexo_form.html"
    allowed_roles = [
        UserProfile.Level.ADMIN,
        UserProfile.Level.NIVEL2,
        UserProfile.Level.NIVEL1,
    ]

    def dispatch(self, request, *args, **kwargs):
        self.obra = get_object_or_404(Obra, pk=self.kwargs["obra_id"])
        denied = self.ensure_obra_access(self.obra)
        if denied:
            return denied
        if self.obra.status == "finalizada":
            return obra_read_only_redirect(request, self.obra)
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
    allowed_roles = [UserProfile.Level.ADMIN]
    def post(self, request, pk):
        obra = get_object_or_404(Obra, pk=pk)
        denied = self.ensure_obra_access(obra)
        if denied:
            return denied
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
        qs = filter_queryset_by_user_obras(qs, self.request.user)
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
        base_qs = filter_queryset_by_user_obras(Pendencia.objects.all(), self.request.user)
        search_query = self.request.GET.get("q")
        if search_query:
            base_qs = base_qs.filter(
                Q(descricao__icontains=search_query)
                | Q(obra__nome__icontains=search_query)
                | Q(tarefa__nome__icontains=search_query)
            )
        status_counts = base_qs.values("status").annotate(total=Count("id"))
        counts = {"aberta": 0, "andamento": 0, "resolvida": 0}
        counts.update({item["status"]: item["total"] for item in status_counts})
        context["counts"] = counts
        context["status_filter"] = self.request.GET.get("status", "")
        context["search_query"] = self.request.GET.get("q", "")
        return context


class PendenciaDetailView(LoginRequiredMixin, DetailView):
    model = Pendencia
    template_name = "obras/pendencia_detail.html"
    context_object_name = "pendencia"

    def get_queryset(self):
        qs = (
            super()
            .get_queryset()
            .select_related("obra", "tarefa", "responsavel", "categoria")
            .prefetch_related("solucoes__usuario")
        )
        return filter_queryset_by_user_obras(qs, self.request.user)



class PendenciaUpdateStatusView(RoleRequiredMixin, View):
    allowed_roles = [
        UserProfile.Level.ADMIN,
        UserProfile.Level.NIVEL2,
        UserProfile.Level.NIVEL1,
    ]

    def post(self, request, pk):
        pendencia = get_object_or_404(Pendencia, pk=pk)
        novo_status = request.POST.get("novo_status")
        solucao_texto = request.POST.get("solucao", "").strip()
        next_url = request.POST.get("next")
        redirect_url = reverse("obras:detalhe_pendencia", kwargs={"pk": pendencia.pk})

        if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
            redirect_url = next_url

        if not user_has_obra_access(request.user, pendencia.obra):
            messages.error(request, NO_OBRA_PERMISSION_MESSAGE)
            return redirect(redirect_url)

        if pendencia.obra.status == "finalizada":
            messages.error(request, READ_ONLY_MESSAGE)
            return redirect(redirect_url)

        if novo_status not in ["andamento", "resolvida"]:
            messages.error(request, "Status invalido para atualizacao.")
            return redirect(redirect_url)

        if novo_status == "resolvida":
            if not solucao_texto:
                messages.error(request, "Informe a solucao para marcar como resolvida.")
                return redirect(redirect_url)
            pendencia.status = "resolvida"
            pendencia.save(update_fields=["status", "data_fechamento", "atualizado_em"])
            SolucaoPendencia.objects.create(
                pendencia=pendencia,
                usuario=request.user,
                descricao=solucao_texto,
            )
            messages.success(request, "Pendencia marcada como resolvida.")
        else:
            if pendencia.status != "andamento":
                pendencia.status = "andamento"
                pendencia.save(update_fields=["status", "data_fechamento", "atualizado_em"])
                messages.success(request, "Pendencia marcada como em andamento.")
            else:
                messages.info(request, "Pendencia ja esta em andamento.")

        return redirect(redirect_url)
