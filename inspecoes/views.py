from django.urls import reverse
from django.shortcuts import get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import CreateView, ListView

from .models import Inspecao
from .forms import InspecaoForm
from obras.models import Obra


class InspecaoCreateView(LoginRequiredMixin, CreateView):
    model = Inspecao
    form_class = InspecaoForm
    template_name = "inspecoes/inspecao_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.obra = get_object_or_404(Obra, pk=kwargs["obra_id"])
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["obra"] = self.obra
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # aqui é o que faltava:
        context["obra"] = self.obra
        return context

    def form_valid(self, form):
        form.instance.usuario = self.request.user
        form.instance.obra = self.obra
        form.instance.latitude = self.request.POST.get("latitude") or None
        form.instance.longitude = self.request.POST.get("longitude") or None
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("obras:detalhe_obra", args=[self.obra.id])

class InspecaoObraListView(LoginRequiredMixin, ListView):
    model = Inspecao
    template_name = "inspecoes/inspecao_obra_list.html"
    context_object_name = "inspecoes"

    def dispatch(self, request, *args, **kwargs):
        self.obra = get_object_or_404(Obra, pk=kwargs["obra_id"])
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        # só inspeções daquela obra, ordenadas da mais recente pra mais antiga
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
