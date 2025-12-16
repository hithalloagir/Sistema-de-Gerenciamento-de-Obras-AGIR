from decimal import Decimal, InvalidOperation

from django.urls import reverse
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import CreateView, ListView, DetailView
from django.contrib import messages

from .models import Inspecao, InspecaoFoto
from .forms import InspecaoForm
from obras.models import Obra
from accounts.mixins import RoleRequiredMixin
from accounts.models import UserProfile
from accounts.utils import filter_queryset_by_user_obras, user_has_obra_access
from obras.constants import NO_OBRA_PERMISSION_MESSAGE, READ_ONLY_MESSAGE


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
        return context

    def form_valid(self, form):
        form.instance.usuario = self.request.user
        form.instance.obra = self.obra
        latitude = self.request.POST.get("latitude")
        longitude = self.request.POST.get("longitude")

        if not latitude or not longitude:
            form.add_error(
                None, "Capture a localizaÇõÇœo antes de salvar a inspeÇõÇœo."
            )
            return self.form_invalid(form)

        try:
            form.instance.latitude = Decimal(latitude)
            form.instance.longitude = Decimal(longitude)
        except (InvalidOperation, TypeError, ValueError):
            form.add_error(
                None, "NÇœo foi possÇðvel ler a localizaÇõÇœo informada. Tente novamente."
            )
            return self.form_invalid(form)

        response = super().form_valid(form)
        fotos = self.request.FILES.getlist("fotos")
        for foto in fotos:
            InspecaoFoto.objects.create(inspecao=self.object, imagem=foto)
        return response

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
        # só inspeções daquela obra, ordenadas da mais recente para a mais antiga
        return (
            Inspecao.objects
            .filter(obra=self.obra)
            .select_related("usuario", "categoria", "tarefa")
            .order_by("-data_inspecao", "-id")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["obra"] = self.obra

        # Prepara dados para o mapa Leaflet de forma segura
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
            .prefetch_related("itens__ponto", "fotos")
        )
        return filter_queryset_by_user_obras(qs, self.request.user)
