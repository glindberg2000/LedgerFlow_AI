from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("profiles", "0001_initial"),
    ]
    operations = [
        migrations.AddField(
            model_name="binderitem",
            name="priority",
            field=models.CharField(
                max_length=10,
                choices=[("high", "High"), ("medium", "Medium"), ("low", "Low")],
                default="medium",
                help_text="Priority for this item (affects checklist order and color).",
            ),
        ),
    ]
