# Generated by Django 5.0.7 on 2024-09-14 16:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0020_comments_sentiment_score'),
    ]

    operations = [
        migrations.AddField(
            model_name='issue',
            name='overall_sentiment_score',
            field=models.FloatField(blank=True, null=True),
        ),
    ]
