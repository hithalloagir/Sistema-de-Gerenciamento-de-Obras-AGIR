from django.db import migrations, models
import django.db.models.deletion
from django.core.validators import MaxValueValidator, MinValueValidator


class Migration(migrations.Migration):

    dependencies = [
        ("obras", "0006_pendencia_imagem_problema_pendencia_imagem_resolucao"),
    ]

    operations = [
        migrations.CreateModel(
            name="ObraSnapshot",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("data", models.DateField()),
                ("percentual_real", models.DecimalField(decimal_places=1, max_digits=5, validators=[MinValueValidator(0), MaxValueValidator(100)])),
                ("percentual_esperado", models.DecimalField(blank=True, decimal_places=1, max_digits=5, null=True, validators=[MinValueValidator(0), MaxValueValidator(100)])),
                ("obra", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="snapshots", to="obras.obra")),
            ],
            options={
                "ordering": ["data"],
                "unique_together": {("obra", "data")},
            },
        ),
    ]

