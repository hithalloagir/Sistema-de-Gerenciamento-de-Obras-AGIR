from django import forms
from django.contrib.auth import get_user_model
from .models import Obra, Categoria, Pendencia, Tarefa, AnexoObra
from accounts.models import UserProfile
from accounts.utils import get_user_level


class ObraForm(forms.ModelForm):
    class Meta:
        model = Obra
        fields = [
            "nome",
            "cliente",
            "endereco",
            "data_inicio",
            "data_fim_prevista",
            "capa",
            "status",
        ]
        widgets = {
            "data_inicio": forms.DateInput(attrs={"type": "date"}),
            "data_fim_prevista": forms.DateInput(attrs={"type": "date"}),
        }


class ObraCreateForm(ObraForm):
    duplicate_last = forms.BooleanField(
        required=False,
        label="Duplicar ultima obra (categorias e tarefas)",
    )

    def __init__(self, *args, **kwargs):
        self.last_obra = kwargs.pop("last_obra", None)
        allow_duplicate = kwargs.pop("allow_duplicate", True)
        super().__init__(*args, **kwargs)
        if not allow_duplicate or self.last_obra is None:
            self.fields.pop("duplicate_last", None)
        else:
            nome_modelo = getattr(self.last_obra, "nome", "")
            self.fields["duplicate_last"].help_text = (
                f"Modelo atual: {nome_modelo}. Apenas categorias e tarefas serao copiadas."
            )


class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ["nome", "descricao", "prazo_final"]
        widgets = {
            "prazo_final": forms.DateInput(attrs={"type": "date"}),
        }


class TarefaForm(forms.ModelForm):
    class Meta:
        model = Tarefa
        fields = [
            "nome",
            "descricao",
            "ordem",
            "data_inicio_prevista",
            "data_fim_prevista",
            "percentual_concluido",
        ]
        widgets = {
            "data_inicio_prevista": forms.DateInput(attrs={"type": "date"}),
            "data_fim_prevista": forms.DateInput(attrs={"type": "date"}),
            "percentual_concluido": forms.NumberInput(attrs={
                "type": "number",
                "value": 0
            }),
        }


class PendenciaForm(forms.ModelForm):
    class Meta:
        model = Pendencia
        fields = [
            "tarefa",
            "descricao",
            "prioridade",
            "responsavel",
            "data_limite",
            "imagem_problema",
        ]
        widgets = {
            "data_limite": forms.DateInput(attrs={"type": "date"}),
            "imagem_problema": forms.ClearableFileInput(
                attrs={"accept": "image/jpeg,image/png,image/webp"}
            ),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        obra = kwargs.pop("obra", None)
        super().__init__(*args, **kwargs)
        if obra:
            self.fields["tarefa"].queryset = Tarefa.objects.filter(categoria__obra=obra)

        if "responsavel" not in self.fields:
            return

        User = get_user_model()
        if not getattr(user, "is_authenticated", False):
            self.fields["responsavel"].queryset = User.objects.none()
            return

        user_level = get_user_level(user)

        if user_level == UserProfile.Level.NIVEL1:
            self.initial["responsavel"] = user
            self.fields.pop("responsavel", None)
            return

        if user_level == UserProfile.Level.NIVEL2:
            if obra is None:
                self.fields["responsavel"].queryset = User.objects.filter(pk=user.pk)
                return

            allowed_qs = User.objects.filter(pk=user.pk)
            allowed_qs = allowed_qs | User.objects.filter(
                obras_alocadas__obra=obra,
                profile__role=UserProfile.Level.NIVEL1,
            )
            self.fields["responsavel"].queryset = allowed_qs.distinct().order_by("username")
            return

        if user_level == UserProfile.Level.ADMIN:
            self.fields["responsavel"].queryset = User.objects.all().order_by("username")
            return


# Formset para adicionar categorias ao criar uma obra
CategoriaInlineFormSet = forms.inlineformset_factory(Obra, Categoria, form=CategoriaForm, extra=2, can_delete=False)


class AnexoObraForm(forms.ModelForm):
    class Meta:
        model = AnexoObra
        fields = ["arquivo", "descricao", "categoria"]
