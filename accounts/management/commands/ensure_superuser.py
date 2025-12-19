import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Ensures a superuser exists (idempotent) based on DJANGO_SUPERUSER_* env vars."

    def handle(self, *args, **options):
        username = (os.getenv("DJANGO_SUPERUSER_USERNAME") or "").strip()
        email = (os.getenv("DJANGO_SUPERUSER_EMAIL") or "").strip()
        password = os.getenv("DJANGO_SUPERUSER_PASSWORD") or ""

        User = get_user_model()
        username_field = getattr(User, "USERNAME_FIELD", "username")

        identifier = email if username_field == "email" else username
        if not identifier or not password:
            self.stdout.write("DJANGO_SUPERUSER_* não configuradas; pulando.")
            return

        if User.objects.filter(**{username_field: identifier}).exists():
            self.stdout.write("Superuser já existe; ok.")
            return

        create_kwargs = {username_field: identifier, "password": password}
        if username_field != "email" and email:
            create_kwargs["email"] = email

        User.objects.create_superuser(**create_kwargs)
        self.stdout.write("Superuser criado.")
