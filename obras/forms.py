from django import forms
from .models import Obra, Categoria, Pendencia, Tarefa, AnexoObra


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
        obra = kwargs.pop("obra", None)
        super().__init__(*args, **kwargs)
        if obra:
            self.fields["tarefa"].queryset = Tarefa.objects.filter(categoria__obra=obra)


# Formset para adicionar categorias ao criar uma obra
CategoriaInlineFormSet = forms.inlineformset_factory(Obra, Categoria, form=CategoriaForm, extra=2, can_delete=False)


class AnexoObraForm(forms.ModelForm):
    class Meta:
        model = AnexoObra
        fields = ["arquivo", "descricao", "categoria"]
