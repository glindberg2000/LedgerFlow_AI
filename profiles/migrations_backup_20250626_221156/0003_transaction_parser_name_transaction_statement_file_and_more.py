# Generated by Django 5.2.1 on 2025-06-05 02:13

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("profiles", "0002_statementfile_statement_hash_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="transaction",
            name="parser_name",
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
        migrations.AddField(
            model_name="transaction",
            name="statement_file",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="profiles.statementfile",
            ),
        ),
    ]
