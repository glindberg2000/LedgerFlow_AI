# Generated by Django 5.2 on 2025-04-24 23:24

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0005_create_processingtask_transactions'),
    ]

    operations = [
        migrations.DeleteModel(
            name='ProcessingTaskTransaction',
        ),
    ]
