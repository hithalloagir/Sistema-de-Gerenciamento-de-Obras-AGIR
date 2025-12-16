from functools import wraps

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import redirect

from .utils import get_or_create_profile, user_has_obra_access

DEFAULT_DENIED_MESSAGE = "Você não tem permissão para acessar esta área."


class RoleRequiredMixin(LoginRequiredMixin):
    allowed_roles = None
    permission_denied_redirect = "obras:listar_obras"
    permission_denied_message = DEFAULT_DENIED_MESSAGE

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)
        profile = self.get_profile(request)
        role = getattr(profile, "role", None)
        if self.allowed_roles and role not in self.allowed_roles:
            return self.handle_no_permission(request)
        return super().dispatch(request, *args, **kwargs)

    def get_profile(self, request):
        return get_or_create_profile(request.user)

    def handle_no_permission(self, request):
        messages.error(request, self.permission_denied_message)
        return redirect(self.permission_denied_redirect)

    def ensure_obra_access(self, obra):
        if obra is None:
            return None
        if not user_has_obra_access(self.request.user, obra):
            return self.handle_no_permission(self.request)
        return None


def level_required(allowed_roles=None, *, json_response=False, message=DEFAULT_DENIED_MESSAGE):
    allowed_roles = tuple(allowed_roles or [])

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            profile = get_or_create_profile(request.user)
            role = getattr(profile, "role", None)
            if allowed_roles and role not in allowed_roles:
                if json_response:
                    return JsonResponse({"status": "error", "message": message}, status=403)
                messages.error(request, message)
                return redirect("obras:listar_obras")
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator
