# Generated by Django 5.1.6 on 2025-03-30 09:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('matches', '0008_match_allow_undo'),
    ]

    operations = [
        migrations.AddField(
            model_name='match',
            name='is_deleted',
            field=models.BooleanField(default=False),
        ),
    ]
