from django import forms
from .models import Inspecao
from obras.models import Categoria, Tarefa


class InspecaoForm(forms.ModelForm):
    class Meta:
        model = Inspecao
        fields = ["obra", "categoria", "tarefa", "observacoes_gerais"]
        widgets = {
            'obra': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        obra = kwargs.pop("obra", None)
        super().__init__(*args, **kwargs)

        if obra:
            self.fields["categoria"].queryset = Categoria.objects.filter(obra=obra)
            self.fields["tarefa"].queryset = Tarefa.objects.filter(categoria__obra=obra)

