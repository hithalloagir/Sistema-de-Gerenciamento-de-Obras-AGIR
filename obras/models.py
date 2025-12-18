from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.db.models import Avg
from django.utils import timezone


class Obra(models.Model):
    STATUS_CHOICES = [
        ("ativa", "Ativa"),
        ("finalizada", "Finalizada"),
    ]

    nome = models.CharField(max_length=100)
    cliente = models.CharField(max_length=100, blank=True)
    endereco = models.CharField(max_length=200, blank=True)
    data_inicio = models.DateField(null=True, blank=True)
    data_fim_prevista = models.DateField(null=True, blank=True)
    capa = models.ImageField(upload_to="obras/capas/", null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="ativa")
    deletada = models.BooleanField(default=False)
    deletada_em = models.DateTimeField(null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.nome

    def soft_delete(self):
        if not self.deletada:
            self.deletada = True
            self.deletada_em = timezone.now()
            self.save(update_fields=["deletada", "deletada_em", "atualizado_em"])


def validate_image_file(image):
    if not image:
        return

    max_size = 5 * 1024 * 1024  # 5MB
    content_type = getattr(image, "content_type", "")
    allowed_types = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
    if content_type and content_type not in allowed_types:
        raise ValidationError("Envie arquivos JPG, PNG ou WEBP.")
    if image.size > max_size:
        raise ValidationError("O tamanho da imagem não pode ultrapassar 5MB.")


def validate_image_extension_optional(image):
    if not image:
        return

    name = getattr(image, "name", "") or ""
    base_name = name.rsplit("/", 1)[-1]
    if "." not in base_name:
        return

    ext = base_name.rsplit(".", 1)[-1].lower()
    if ext not in {"jpg", "jpeg", "png", "webp"}:
        raise ValidationError("A extensao do arquivo nao e permitida. Use: jpg, jpeg, png ou webp.")


class Categoria(models.Model):
    STATUS_CHOICES = [
        ("andamento", "Em andamento"),
        ("concluida", "Concluída"),
        ("atrasada", "Atrasada"),
    ]

    obra = models.ForeignKey(Obra, on_delete=models.CASCADE, related_name='categorias')
    nome = models.CharField(max_length=255)
    descricao = models.TextField(blank=True)
    prazo_final = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="andamento")
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('obra', 'nome')
        ordering = ['obra', 'nome']

    def __str__(self):
        return f"{self.obra} - {self.nome}"

    @property
    def percentual_concluido(self):
        """Calcula o percentual de conclusão da categoria com base na média de suas tarefas."""
        resultado = self.tarefas.aggregate(media=Avg('percentual_concluido'))
        media = resultado.get('media')
        return round(media, 1) if media is not None else 0


class Tarefa(models.Model):
    STATUS_CHOICES = [
        ("nao_iniciada", "Não iniciada"),
        ("andamento", "Em andamento"),
        ("concluida", "Concluída"),
        ("bloqueada", "Bloqueada"),
    ]

    categoria = models.ForeignKey(
        Categoria, on_delete=models.CASCADE, related_name="tarefas"
    )
    nome = models.CharField(max_length=255)
    descricao = models.TextField(blank=True)

    ordem = models.PositiveIntegerField(default=1)

    data_inicio_prevista = models.DateField(null=True, blank=True)
    data_fim_prevista = models.DateField(null=True, blank=True)
    data_fim_real = models.DateField(null=True, blank=True)

    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="nao_iniciada"
    )

    percentual_concluido = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["categoria", "ordem", "id"]

    def __str__(self):
        return f"{self.categoria} - {self.nome}"

    def clean(self):
        super().clean()
        # regra: não pode concluir com pendências abertas
        if self.percentual_concluido == 100:
            tem_pendencias_abertas = self.pendencias.filter(status="aberta").exists()
            if tem_pendencias_abertas:
                raise ValidationError(
                    "Não é possível concluir a tarefa com pendências em aberto."
                )

    def save(self, *args, **kwargs):
        # Atualiza o status com base no percentual
        if self.percentual_concluido == 100:
            if self.status != "concluida":
                self.status = "concluida"
                self.data_fim_real = timezone.now().date()
        elif self.percentual_concluido > 0:
            self.status = "andamento"
            self.data_fim_real = None  # Garante que a data de fim seja nula se a tarefa for reaberta
        else:
            self.status = "nao_iniciada"
            self.data_fim_real = None

        self.full_clean()
        return super().save(*args, **kwargs)


class Pendencia(models.Model):
    STATUS_CHOICES = [
        ("aberta", "Aberta"),
        ("andamento", "Em andamento"),
        ("resolvida", "Resolvida"),
    ]

    PRIORIDADE_CHOICES = [
        ("baixa", "Baixa"),
        ("media", "Média"),
        ("alta", "Alta"),
    ]

    obra = models.ForeignKey(
        Obra, on_delete=models.CASCADE, related_name="pendencias"
    )
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pendencias",
    )
    tarefa = models.ForeignKey(
        Tarefa, on_delete=models.CASCADE, related_name="pendencias"
    )

    descricao = models.TextField()
    prioridade = models.CharField(
        max_length=10, choices=PRIORIDADE_CHOICES, default="media"
    )
    imagem_problema = models.ImageField(
        upload_to="pendencias/problemas/",
        null=True,
        blank=True,
        validators=[
            validate_image_extension_optional,
            validate_image_file,
        ],
    )
    responsavel = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pendencias_responsavel",
    )
    imagem_resolucao = models.ImageField(
        upload_to="pendencias/resolucoes/",
        null=True,
        blank=True,
        validators=[
            validate_image_extension_optional,
            validate_image_file,
        ],
    )

    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default="aberta"
    )
    data_limite = models.DateField(null=True, blank=True)
    data_abertura = models.DateTimeField(auto_now_add=True)
    data_fechamento = models.DateTimeField(null=True, blank=True)

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.obra} - {self.descricao[:50]}"

    def save(self, *args, **kwargs):
        if self.status == "resolvida" and not self.data_fechamento:
            self.data_fechamento = timezone.now()
        if self.status != "resolvida":
            self.data_fechamento = None
        super().save(*args, **kwargs)


class SolucaoPendencia(models.Model):
    pendencia = models.ForeignKey(
        Pendencia, on_delete=models.CASCADE, related_name="solucoes"
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="solucoes_pendencias",
    )
    descricao = models.TextField()
    data_hora = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Solução #{self.id} - Pendência {self.pendencia_id}"


class AnexoObra(models.Model):
    obra = models.ForeignKey(Obra, on_delete=models.CASCADE, related_name="anexos")
    categoria = models.ForeignKey(Categoria, on_delete=models.SET_NULL, null=True, blank=True, related_name="anexos")
    arquivo = models.FileField(upload_to="anexos/")
    descricao = models.CharField(max_length=255, blank=True)
    enviado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    enviado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-enviado_em"]

    def __str__(self):
        return f"Anexo {self.id} - {self.obra.nome}"


class ObraSnapshot(models.Model):
    obra = models.ForeignKey(Obra, on_delete=models.CASCADE, related_name="snapshots")
    data = models.DateField()
    percentual_real = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    percentual_esperado = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )

    class Meta:
        unique_together = ("obra", "data")
        ordering = ["data"]

    def __str__(self):
        return f"{self.obra} - {self.data:%Y-%m-%d}"


@receiver(pre_save, sender=Tarefa)
def tarefa_capture_previous_state(sender, instance, **kwargs):
    if not instance.pk:
        instance._previous_percentual_concluido = None
        return
    previous = sender.objects.filter(pk=instance.pk).values("percentual_concluido").first()
    instance._previous_percentual_concluido = previous["percentual_concluido"] if previous else None


@receiver(post_save, sender=Tarefa)
def tarefa_upsert_snapshot_on_progress_change(sender, instance, created, **kwargs):
    previous = getattr(instance, "_previous_percentual_concluido", None)
    if created or previous is None or previous != instance.percentual_concluido:
        from .services import upsert_obra_snapshot
        upsert_obra_snapshot(instance.categoria.obra)


@receiver(pre_save, sender=Pendencia)
def pendencia_capture_previous_state(sender, instance, **kwargs):
    if not instance.pk:
        instance._previous_status = None
        return
    previous = sender.objects.filter(pk=instance.pk).values("status").first()
    instance._previous_status = previous["status"] if previous else None


@receiver(post_save, sender=Pendencia)
def pendencia_create_snapshot_on_resolve(sender, instance, created, **kwargs):
    previous = getattr(instance, "_previous_status", None)
    if created or (previous is not None and previous != instance.status):
        from .services import upsert_obra_snapshot
        upsert_obra_snapshot(instance.obra)
