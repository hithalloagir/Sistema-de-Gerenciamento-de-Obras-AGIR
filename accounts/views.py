from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin


class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/profile.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        alocacoes = (
            self.request.user.obras_alocadas.select_related("obra").order_by("obra__nome")
            if hasattr(self.request.user, "obras_alocadas")
            else []
        )
        context["alocacoes"] = alocacoes
        return context
