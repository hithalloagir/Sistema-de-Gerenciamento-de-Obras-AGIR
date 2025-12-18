from django import forms
from .models import Inspecao


class InspecaoForm(forms.ModelForm):
    class Meta:
        model = Inspecao
        fields = ["obra", "observacoes_gerais"]
        widgets = {
            'obra': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        kwargs.pop("obra", None)
        super().__init__(*args, **kwargs)
