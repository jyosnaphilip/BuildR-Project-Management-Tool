# Generated by Django 5.0.7 on 2024-09-09 15:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0019_alter_issue_assignee_bridge_unique_together_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='comments',
            name='sentiment_score',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
