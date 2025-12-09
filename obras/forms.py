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
            "custo_previsto",
            "custo_real",
        ]
        widgets = {
            "data_inicio": forms.DateInput(attrs={"type": "date"}),
            "data_fim_prevista": forms.DateInput(attrs={"type": "date"}),
        }


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
        fields = ["tarefa", "descricao", "prioridade", "responsavel", "data_limite"]
        widgets = {
            "data_limite": forms.DateInput(attrs={"type": "date"}),
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
