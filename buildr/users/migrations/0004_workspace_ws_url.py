# Generated by Django 5.0.7 on 2024-08-25 11:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0003_workspace_workspacemember'),
    ]

    operations = [
        migrations.AddField(
            model_name='workspace',
            name='ws_url',
            field=models.URLField(default='url', unique=True),
        ),
    ]