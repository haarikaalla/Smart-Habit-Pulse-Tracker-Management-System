from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("tracker", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="habit",
            name="owner",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="habits",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="habit",
            name="target_per_week",
            field=models.PositiveSmallIntegerField(default=7),
        ),
        migrations.AddField(
            model_name="habit",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddIndex(
            model_name="habit",
            index=models.Index(fields=["owner", "completed"], name="tracker_hab_owner_i_2f4915_idx"),
        ),
        migrations.AlterModelOptions(
            name="habit",
            options={"ordering": ["-created_at"]},
        ),
    ]
