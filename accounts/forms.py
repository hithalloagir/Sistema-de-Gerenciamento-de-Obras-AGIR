from typing import Iterable, Optional, Tuple

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction

from obras.models import Obra

from .models import ObraAlocacao, UserProfile
from .utils import filter_obras_for_user, get_or_create_profile


class UserCreationWithRoleForm(forms.Form):
    username = forms.CharField(
        label="Nome de usuário",
        max_length=150,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "ex: joao.silva"}),
    )
    role = forms.ChoiceField(
        label="Nível de acesso",
        choices=UserProfile.Level.choices,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    auto_password = forms.BooleanField(
        label="Gerar senha automaticamente",
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )
    password1 = forms.CharField(
        label="Senha",
        required=False,
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "********"}),
    )
    password2 = forms.CharField(
        label="Confirme a senha",
        required=False,
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "********"}),
    )
    obras = forms.ModelMultipleChoiceField(
        label="Obras alocadas",
        queryset=Obra.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={"class": "form-check-input"}),
        help_text="Selecione uma ou mais obras para liberar o acesso.",
    )

    def __init__(self, *args, creator=None, **kwargs):
        self.creator = creator
        super().__init__(*args, **kwargs)
        self._final_password: Optional[str] = None
        self._setup_role_choices()
        self._setup_obras_field()

    def _setup_role_choices(self):
        profile = get_or_create_profile(self.creator)
        creator_role = getattr(profile, "role", None)
        allowed_roles: Iterable[str] = []
        if creator_role == UserProfile.Level.ADMIN:
            allowed_roles = (UserProfile.Level.NIVEL2, UserProfile.Level.NIVEL1)
        elif creator_role == UserProfile.Level.NIVEL2:
            allowed_roles = (UserProfile.Level.NIVEL1,)
        else:
            allowed_roles = ()
        filtered_choices = [
            (value, label) for value, label in UserProfile.Level.choices if value in allowed_roles
        ]
        self.fields["role"].choices = filtered_choices

    def _setup_obras_field(self):
        queryset = filter_obras_for_user(
            Obra.objects.filter(deletada=False).order_by("nome"),
            self.creator,
        )
        self.fields["obras"].queryset = queryset

    def clean_username(self):
        username = self.cleaned_data["username"]
        user_model = get_user_model()
        if user_model.objects.filter(username=username).exists():
            raise ValidationError("Já existe um usuário com esse nome.")
        return username

    def clean_role(self):
        role = self.cleaned_data["role"]
        profile = get_or_create_profile(self.creator)
        if not profile or not profile.can_create_level(role):
            raise ValidationError("Você não tem permissão para criar usuários nesse nível.")
        return role

    def clean_obras(self):
        obras = self.cleaned_data.get("obras")
        if not obras:
            return obras
        allowed_ids = set(self.fields["obras"].queryset.values_list("id", flat=True))
        invalid = [obra for obra in obras if obra.id not in allowed_ids]
        if invalid:
            raise ValidationError("Você tentou alocar obras fora do seu escopo permitido.")
        return obras

    def clean(self):
        cleaned = super().clean()
        auto_password = cleaned.get("auto_password")
        password1 = cleaned.get("password1")
        password2 = cleaned.get("password2")

        if auto_password:
            self._final_password = get_user_model().objects.make_random_password(length=10)
            return cleaned

        if not password1 or not password2:
            raise ValidationError("Informe a senha ou marque a opção de gerar automaticamente.")

        if password1 != password2:
            raise ValidationError("As senhas não conferem.")

        validate_password(password1)
        self._final_password = password1
        return cleaned

    def save(self, *, created_by) -> Tuple:
        if self._final_password is None:
            raise ValidationError("A senha não foi definida corretamente.")
        user_model = get_user_model()
        role = self.cleaned_data["role"]
        obras = self.cleaned_data["obras"]

        with transaction.atomic():
            user = user_model.objects.create_user(
                username=self.cleaned_data["username"],
                password=self._final_password,
            )
            profile = get_or_create_profile(user)
            profile.role = role
            profile.save(update_fields=["role"])
            for obra in obras:
                ObraAlocacao.objects.get_or_create(
                    obra=obra,
                    usuario=user,
                    defaults={"alocado_por": created_by},
                )
        return user, self._final_password


class UserUpdateForm(forms.Form):
    username = forms.CharField(
        label="Nome de usuÇ­rio",
        max_length=150,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    role = forms.ChoiceField(
        label="NÇðvel de acesso",
        choices=UserProfile.Level.choices,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    password1 = forms.CharField(
        label="Nova senha",
        required=False,
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": "Deixe em branco para manter"}
        ),
    )
    password2 = forms.CharField(
        label="Confirme a nova senha",
        required=False,
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": "Deixe em branco para manter"}
        ),
    )
    obras = forms.ModelMultipleChoiceField(
        label="Obras alocadas",
        queryset=Obra.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={"class": "form-check-input"}),
        help_text="Selecione uma ou mais obras para liberar o acesso.",
    )

    def __init__(self, *args, editor=None, user_obj=None, **kwargs):
        self.editor = editor
        self.user_obj = user_obj
        super().__init__(*args, **kwargs)
        self._setup_role_choices()
        self._setup_obras_field()
        self._set_initial_values()

    def _setup_role_choices(self):
        profile = get_or_create_profile(self.editor)
        editor_role = getattr(profile, "role", None)
        allowed_roles: Iterable[str] = []
        if editor_role == UserProfile.Level.ADMIN:
            allowed_roles = (UserProfile.Level.NIVEL2, UserProfile.Level.NIVEL1)
        elif editor_role == UserProfile.Level.NIVEL2:
            allowed_roles = (UserProfile.Level.NIVEL1,)
        else:
            allowed_roles = ()
        filtered_choices = [
            (value, label) for value, label in UserProfile.Level.choices if value in allowed_roles
        ]
        self.fields["role"].choices = filtered_choices

    def _setup_obras_field(self):
        queryset = filter_obras_for_user(
            Obra.objects.filter(deletada=False).order_by("nome"),
            self.editor,
        )
        self.fields["obras"].queryset = queryset

    def _set_initial_values(self):
        if not self.user_obj:
            return
        self.initial.setdefault("username", self.user_obj.username)
        profile = get_or_create_profile(self.user_obj)
        self.initial.setdefault("role", getattr(profile, "role", None))

        allowed_ids = set(self.fields["obras"].queryset.values_list("id", flat=True))
        current_ids = set(
            ObraAlocacao.objects.filter(usuario=self.user_obj, obra_id__in=allowed_ids).values_list(
                "obra_id", flat=True
            )
        )
        self.initial.setdefault("obras", list(current_ids))

    def clean_username(self):
        username = self.cleaned_data["username"]
        user_model = get_user_model()
        qs = user_model.objects.filter(username=username)
        if self.user_obj:
            qs = qs.exclude(pk=self.user_obj.pk)
        if qs.exists():
            raise ValidationError("Já­ existe um usuário com esse nome.")
        return username

    def clean_role(self):
        role = self.cleaned_data["role"]
        profile = get_or_create_profile(self.editor)
        if not profile or not profile.can_create_level(role):
            raise ValidationError("Você não tem permissão para definir esse nível.")
        return role

    def clean_obras(self):
        obras = self.cleaned_data.get("obras")
        if not obras:
            return obras
        allowed_ids = set(self.fields["obras"].queryset.values_list("id", flat=True))
        invalid = [obra for obra in obras if obra.id not in allowed_ids]
        if invalid:
            raise ValidationError("Você tentou alocar obras fora do seu escopo permitido.")
        return obras

    def clean(self):
        cleaned = super().clean()
        password1 = cleaned.get("password1")
        password2 = cleaned.get("password2")

        if password1 or password2:
            if not password1 or not password2:
                raise ValidationError("Preencha e confirme a nova senha.")
            if password1 != password2:
                raise ValidationError("As senhas nÇœo conferem.")
            validate_password(password1, user=self.user_obj)

        return cleaned

    def save(self):
        if not self.user_obj:
            raise ValidationError("Usuá­rio invá­lido.")

        role = self.cleaned_data["role"]
        obras = self.cleaned_data.get("obras") or Obra.objects.none()
        password1 = self.cleaned_data.get("password1")

        with transaction.atomic():
            if self.user_obj.username != self.cleaned_data["username"]:
                self.user_obj.username = self.cleaned_data["username"]
                self.user_obj.save(update_fields=["username"])

            profile = get_or_create_profile(self.user_obj)
            if profile.role != role:
                profile.role = role
                profile.save(update_fields=["role"])

            if password1:
                self.user_obj.set_password(password1)
                self.user_obj.save(update_fields=["password"])

            allowed_ids = set(self.fields["obras"].queryset.values_list("id", flat=True))
            desired_ids = set(obras.values_list("id", flat=True))
            current_ids = set(
                ObraAlocacao.objects.filter(usuario=self.user_obj, obra_id__in=allowed_ids).values_list(
                    "obra_id", flat=True
                )
            )

            to_remove = current_ids - desired_ids
            if to_remove:
                ObraAlocacao.objects.filter(usuario=self.user_obj, obra_id__in=to_remove).delete()

            to_add = desired_ids - current_ids
            for obra_id in to_add:
                ObraAlocacao.objects.get_or_create(
                    obra_id=obra_id,
                    usuario=self.user_obj,
                    defaults={"alocado_por": self.editor},
                )

        return self.user_obj
