from django.db import models
from django.conf import settings
from django.utils import timezone

from obras.models import Obra, Categoria, Tarefa, Pendencia


class PontoInspecaoTemplate(models.Model):
    obra = models.ForeignKey(
        Obra, on_delete=models.CASCADE, related_name="pontos_inspecao"
    )
    nome = models.CharField(max_length=255)
    descricao = models.TextField(blank=True)
    ativo = models.BooleanField(default=True)

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("obra", "nome")
        ordering = ["obra", "nome"]

    def __str__(self):
        return f"{self.obra} - {self.nome}"


class Inspecao(models.Model):
    obra = models.ForeignKey(Obra, on_delete=models.CASCADE, related_name="inspecoes")
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="inspecoes",
    )
    tarefa = models.ForeignKey(
        Tarefa,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="inspecoes",
    )

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inspecoes",
    )

    data_hora = models.DateTimeField(auto_now_add=True)
    data_inspecao = models.DateField(editable=False)

    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )

    observacoes_gerais = models.TextField(blank=True)

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        # garante no máximo 1 inspeção por dia por usuario/obra/tarefa (ajuste se quiser outro critério)
        unique_together = ("obra", "tarefa", "usuario", "data_inspecao")
        ordering = ["-data_hora"]

    def save(self, *args, **kwargs):
        if not self.data_inspecao:
            self.data_inspecao = (self.data_hora or timezone.now()).date()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Inspeção {self.id} - {self.obra} ({self.data_inspecao})"


class InspecaoFoto(models.Model):
    inspecao = models.ForeignKey(Inspecao, on_delete=models.CASCADE, related_name="fotos")
    imagem = models.ImageField(upload_to="inspecoes/fotos/")
    legenda = models.CharField(max_length=255, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em"]

    def __str__(self):
        return f"Foto {self.id} - Inspeção {self.inspecao_id}"


class ItemInspecao(models.Model):
    STATUS_CHOICES = [
        ("aprovado", "Aprovado"),
        ("reprovado", "Reprovado"),
        ("nao_aplicavel", "Não aplicável"),
    ]

    inspecao = models.ForeignKey(
        Inspecao, on_delete=models.CASCADE, related_name="itens"
    )
    ponto = models.ForeignKey(
        PontoInspecaoTemplate,
        on_delete=models.PROTECT,
        related_name="itens_inspecao",
    )

    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="aprovado"
    )
    observacao = models.TextField(blank=True)

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.inspecao} - {self.ponto}"
