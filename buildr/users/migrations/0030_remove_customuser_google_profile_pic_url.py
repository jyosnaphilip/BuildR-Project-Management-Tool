# Generated by Django 5.0.7 on 2024-11-06 18:37

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0029_customuser_google_profile_pic_url"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="customuser",
            name="google_profile_pic_url",
        ),
    ]