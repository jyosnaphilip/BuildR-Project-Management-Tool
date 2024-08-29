# Generated by Django 5.0.7 on 2024-08-28 10:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0008_alter_priority_name'),
    ]

    operations = [
        migrations.AlterField(
            model_name='priority',
            name='name',
            field=models.CharField(choices=[('Urgent', 'Urgent'), ('High Priority', 'High Priority'), ('Medium Priority', 'Medium Priority'), ('Low Priority', 'Low Prioirty'), ('No Priority', 'No Priority')], max_length=100),
        ),
    ]
