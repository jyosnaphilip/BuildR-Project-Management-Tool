# Generated by Django 5.0.7 on 2024-09-05 03:28

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0016_merge_20240905_0857"),
    ]

    operations = [
        migrations.AddField(
            model_name="priority",
            name="icon",
            field=models.CharField(max_length=20, null=True),
        ),
    ]
