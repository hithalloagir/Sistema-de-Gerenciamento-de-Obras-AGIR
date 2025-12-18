from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import CreateView, DetailView, ListView

from accounts.mixins import RoleRequiredMixin
from accounts.models import UserProfile
from accounts.utils import (
    filter_queryset_by_user_obras,
    get_user_level,
    user_has_obra_access,
)
from obras.constants import NO_OBRA_PERMISSION_MESSAGE, READ_ONLY_MESSAGE
from obras.models import Obra, Tarefa

from .forms import InspecaoForm
from .models import Inspecao, InspecaoFoto, InspecaoAlteracaoTarefa


class InspecaoCreateView(RoleRequiredMixin, CreateView):
    model = Inspecao
    form_class = InspecaoForm
    template_name = "inspecoes/inspecao_form.html"
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
            messages.error(request, READ_ONLY_MESSAGE)
            return redirect("obras:detalhe_obra", pk=self.obra.pk)
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["obra"] = self.obra
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        initial["obra"] = self.obra
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["obra"] = self.obra
        context["user_level"] = get_user_level(self.request.user)
        context["categorias"] = self.obra.categorias.prefetch_related("tarefas").all()
        return context

    def form_valid(self, form):
        form.instance.usuario = self.request.user
        form.instance.obra = self.obra
        form.instance.categoria = None
        form.instance.tarefa = None

        latitude = (self.request.POST.get("latitude") or "").strip()
        longitude = (self.request.POST.get("longitude") or "").strip()

        location_error_reason = (self.request.POST.get("location_error_reason") or "").strip()
        location_error_code = (self.request.POST.get("location_error_code") or "").strip()
        location_error_message = (self.request.POST.get("location_error_message") or "").strip()

        if latitude and longitude:
            try:
                form.instance.latitude = Decimal(latitude)
                form.instance.longitude = Decimal(longitude)
            except (InvalidOperation, TypeError, ValueError):
                form.instance.latitude = None
                form.instance.longitude = None
                messages.warning(
                    self.request,
                    "Não foi possível ler a localização informada. A inspeção foi salva sem coordenadas.",
                )
        else:
            form.instance.latitude = None
            form.instance.longitude = None

        user_level = get_user_level(self.request.user)

        try:
            with transaction.atomic():
                response = super().form_valid(form)

                if not self.object.latitude or not self.object.longitude:
                    if location_error_reason:
                        details = []
                        if location_error_code:
                            details.append(f"code={location_error_code}")
                        if location_error_message:
                            details.append(location_error_message)
                        suffix = f" ({' | '.join(details)})" if details else ""
                        messages.warning(
                            self.request,
                            f"{location_error_reason}{suffix}. A inspeção foi salva sem coordenadas.",
                        )
                    else:
                        messages.warning(
                            self.request,
                            "Localização não autorizada ou indisponível. A inspeção foi salva sem coordenadas.",
                        )

                tarefas = (
                    Tarefa.objects.filter(categoria__obra=self.obra)
                    .select_related("categoria")
                    .order_by("categoria_id", "ordem", "id")
                )

                alteracoes = []
                for tarefa in tarefas:
                    field_name = f"task_percent_{tarefa.id}"
                    raw_value = self.request.POST.get(field_name)
                    if raw_value is None:
                        continue

                    try:
                        progress = int(raw_value)
                    except (TypeError, ValueError):
                        raise ValidationError(
                            f"Percentual inválido para a tarefa '{tarefa.nome}'."
                        )

                    if not (0 <= progress <= 100):
                        raise ValidationError(
                            f"Percentual inválido para a tarefa '{tarefa.nome}'. Use 0..100."
                        )

                    if (
                        user_level == UserProfile.Level.NIVEL1
                        and tarefa.status == "concluida"
                        and progress != tarefa.percentual_concluido
                    ):
                        raise ValidationError(
                            f"Tarefa '{tarefa.nome}' concluída: somente Nível 2/ADM pode alterar."
                        )

                    percentual_antes = tarefa.percentual_concluido
                    if progress != percentual_antes:
                        tarefa.percentual_concluido = progress
                        try:
                            tarefa.save()
                        except ValidationError as exc:
                            message = (
                                exc.messages[0]
                                if getattr(exc, "messages", None)
                                else str(exc)
                            )
                            raise ValidationError(
                                f"Erro ao atualizar a tarefa '{tarefa.nome}': {message}"
                            )
                        alteracoes.append(
                            InspecaoAlteracaoTarefa(
                                inspecao=self.object,
                                tarefa=tarefa,
                                percentual_antes=percentual_antes,
                                percentual_depois=progress,
                            )
                        )

                if alteracoes:
                    InspecaoAlteracaoTarefa.objects.bulk_create(alteracoes)

                fotos = self.request.FILES.getlist("fotos")
                for foto in fotos:
                    InspecaoFoto.objects.create(inspecao=self.object, imagem=foto)

                return response
        except ValidationError as exc:
            message = exc.messages[0] if getattr(exc, "messages", None) else str(exc)
            form.add_error(None, message)
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse("obras:detalhe_obra", args=[self.obra.id])


class InspecaoObraListView(LoginRequiredMixin, ListView):
    model = Inspecao
    template_name = "inspecoes/inspecao_obra_list.html"
    context_object_name = "inspecoes"

    def dispatch(self, request, *args, **kwargs):
        self.obra = get_object_or_404(Obra, pk=kwargs["obra_id"])
        if not user_has_obra_access(request.user, self.obra):
            messages.error(request, NO_OBRA_PERMISSION_MESSAGE)
            return redirect("obras:listar_obras")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return (
            Inspecao.objects.filter(obra=self.obra)
            .select_related("usuario", "categoria", "tarefa")
            .order_by("-data_inspecao", "-id")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["obra"] = self.obra

        markers_data = []
        for inspecao in context["inspecoes"]:
            if inspecao.latitude and inspecao.longitude:
                markers_data.append(
                    {
                        "lat": float(inspecao.latitude),
                        "lng": float(inspecao.longitude),
                        "popup": f"{inspecao.data_inspecao:%d/%m/%Y} - {inspecao.usuario.username}",
                    }
                )
        context["markers_data_json"] = markers_data
        return context


class InspecaoDetailView(LoginRequiredMixin, DetailView):
    model = Inspecao
    template_name = "inspecoes/inspecao_detail.html"
    context_object_name = "inspecao"

    def get_queryset(self):
        qs = (
            super()
            .get_queryset()
            .select_related("obra", "categoria", "tarefa", "usuario")
            .prefetch_related(
                "itens__ponto", "fotos", "alteracoes_tarefas__tarefa__categoria"
            )
        )
        return filter_queryset_by_user_obras(qs, self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        alteracoes = list(
            self.object.alteracoes_tarefas.select_related("tarefa__categoria").order_by(
                "tarefa__categoria__nome", "tarefa__ordem", "tarefa__id"
            )
        )
        context["alteracoes_tarefas"] = alteracoes
        context["alteracoes_tarefas_count"] = len(alteracoes)
        return context
