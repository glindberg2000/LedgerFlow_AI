# Generated by Django 5.2.1 on 2025-06-09 16:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("profiles", "0007_statementfile_account_holder_name_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="transaction",
            name="transaction_id",
            field=models.CharField(
                blank=True, db_index=True, max_length=128, null=True
            ),
        ),
    ]
