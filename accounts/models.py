from django.db import models
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserProfile(models.Model):
    ROLE_CHOICES = [
        ("admin", "Administrador"),
        ("avaliador", "Avaliador"),
        ("gerente", "Gerente"),
        ("engenheiro", "Engenheiro"),
        ("fiscal", "Fiscal/QA"),
        ("visualizador", "Visualizador"),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="visualizador")
    empresa = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def ensure_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
