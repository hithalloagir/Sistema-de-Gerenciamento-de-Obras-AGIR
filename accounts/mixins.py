from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.contrib import messages


class RoleRequiredMixin(LoginRequiredMixin):
    allowed_roles = None  # list or tuple

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if not user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)

        profile = getattr(user, "profile", None)
        if profile is None:
            from accounts.models import UserProfile
            profile = UserProfile.objects.create(user=user)
        role = getattr(profile, "role", None)
        if self.allowed_roles and role not in self.allowed_roles:
            messages.error(request, "Você não tem permissão para acessar esta área.")
            return redirect("obras:listar_obras")
        return super().dispatch(request, *args, **kwargs)
