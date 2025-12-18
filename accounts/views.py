from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import TemplateView

from .forms import UserCreationWithRoleForm, UserUpdateForm
from .mixins import RoleRequiredMixin
from .models import UserProfile
from .utils import manageable_users_queryset

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


class UserManagementView(RoleRequiredMixin, TemplateView):
    template_name = "accounts/user_management.html"
    allowed_roles = [UserProfile.Level.ADMIN, UserProfile.Level.NIVEL2]

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            new_user, password = form.save(created_by=request.user)
            role_display = dict(UserProfile.Level.choices).get(form.cleaned_data["role"], "Usuário")
            message = f"Usuário {new_user.username} ({role_display}) criado com sucesso."
            if form.cleaned_data.get("auto_password"):
                message += f" Senha inicial: {password}"
            messages.success(request, message)
            return redirect("accounts:manage_users")
        messages.error(request, "Revise os campos destacados e tente novamente.")
        return self.render_to_response(self.get_context_data(form=form))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = kwargs.get("form") or self.get_form()
        context["users"] = self.get_user_queryset()
        context["manageable_user_ids"] = set(
            manageable_users_queryset(self.request.user).values_list("id", flat=True)
        )
        return context

    def get_form_kwargs(self):
        kwargs = {"creator": self.request.user}
        if self.request.method in ("POST",):
            kwargs["data"] = self.request.POST
        return kwargs

    def get_form(self):
        return UserCreationWithRoleForm(**self.get_form_kwargs())

    def get_user_queryset(self):
        User = get_user_model()
        return (
            User.objects.filter(profile__isnull=False)
            .select_related("profile")
            .prefetch_related("obras_alocadas__obra")
            .order_by("username")
        )


class UserEditView(RoleRequiredMixin, TemplateView):
    template_name = "accounts/user_edit.html"
    allowed_roles = [UserProfile.Level.ADMIN, UserProfile.Level.NIVEL2]

    def dispatch(self, request, *args, **kwargs):
        self.target_user = get_object_or_404(
            manageable_users_queryset(request.user).prefetch_related("obras_alocadas__obra"),
            pk=kwargs.get("pk"),
        )
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            form.save()
            messages.success(request, f"UsuÇ­rio {self.target_user.username} atualizado com sucesso.")
            return redirect("accounts:manage_users")
        messages.error(request, "Revise os campos destacados e tente novamente.")
        return self.render_to_response(self.get_context_data(form=form))

    def get_form_kwargs(self):
        kwargs = {"editor": self.request.user, "user_obj": self.target_user}
        if self.request.method == "POST":
            kwargs["data"] = self.request.POST
        return kwargs

    def get_form(self):
        return UserUpdateForm(**self.get_form_kwargs())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["target_user"] = self.target_user
        context["form"] = kwargs.get("form") or self.get_form()
        return context


class UserDeleteView(RoleRequiredMixin, TemplateView):
    template_name = "accounts/user_confirm_delete.html"
    allowed_roles = [UserProfile.Level.ADMIN, UserProfile.Level.NIVEL2]

    def dispatch(self, request, *args, **kwargs):
        self.target_user = get_object_or_404(
            manageable_users_queryset(request.user).prefetch_related("obras_alocadas__obra"),
            pk=kwargs.get("pk"),
        )
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        username = self.target_user.username
        self.target_user.delete()
        messages.success(request, f"UsuÇ­rio {username} excluÇðdo com sucesso.")
        return redirect("accounts:manage_users")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["target_user"] = self.target_user
        return context
