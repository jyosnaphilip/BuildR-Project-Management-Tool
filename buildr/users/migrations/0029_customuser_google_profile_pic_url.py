# Generated by Django 5.0.7 on 2024-10-21 14:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0028_alter_issue_priority_alter_issue_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='google_profile_pic_url',
            field=models.CharField(blank=True, max_length=500, null=True),
        ),
    ]
