from django.db import migrations, models
import django.db.models.deletion
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ("inspecoes", "0002_inspecaofoto"),
        ("obras", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="InspecaoAlteracaoTarefa",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "percentual_antes",
                    models.PositiveSmallIntegerField(
                        validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)]
                    ),
                ),
                (
                    "percentual_depois",
                    models.PositiveSmallIntegerField(
                        validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)]
                    ),
                ),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                (
                    "inspecao",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="alteracoes_tarefas",
                        to="inspecoes.inspecao",
                    ),
                ),
                (
                    "tarefa",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="alteracoes_inspecao",
                        to="obras.tarefa",
                    ),
                ),
            ],
            options={
                "ordering": ["-criado_em", "-id"],
                "unique_together": {("inspecao", "tarefa")},
            },
        ),
    ]

