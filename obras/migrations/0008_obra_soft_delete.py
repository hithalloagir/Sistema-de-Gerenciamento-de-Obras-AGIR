from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("obras", "0007_obrasnapshot"),
    ]

    operations = [
        migrations.AddField(
            model_name="obra",
            name="deletada",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="obra",
            name="deletada_em",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]

