from django.db import models
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserProfile(models.Model):
    class Level(models.TextChoices):
        ADMIN = ("admin", "Administrador")
        NIVEL2 = ("nivel2", "Nível 2")
        NIVEL1 = ("nivel1", "Nível 1")

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=20, choices=Level.choices, default=Level.NIVEL1)
    empresa = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"

    @property
    def is_admin(self):
        return self.role == self.Level.ADMIN

    def can_create_level(self, target_level):
        if self.role == self.Level.ADMIN:
            return target_level in {self.Level.ADMIN, self.Level.NIVEL2, self.Level.NIVEL1}
        if self.role == self.Level.NIVEL2:
            return target_level == self.Level.NIVEL1
        return False


class ObraAlocacao(models.Model):
    obra = models.ForeignKey("obras.Obra", on_delete=models.CASCADE, related_name="alocacoes")
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="obras_alocadas",
    )
    alocado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="alocacoes_atribuidas",
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("obra", "usuario")
        verbose_name = "Alocação de obra"
        verbose_name_plural = "Alocações de obras"
        ordering = ("obra__nome", "usuario__username")

    def __str__(self):
        return f"{self.usuario} -> {self.obra}"


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def ensure_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
