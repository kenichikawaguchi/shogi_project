# Generated by Django 5.1.6 on 2025-02-24 05:50

import django.db.models.deletion
import matches.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('matches', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='GameState',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('board', models.JSONField(default=matches.models.initial_board)),
                ('pieces_in_hand', models.JSONField(default=dict)),
                ('match', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='game_state', to='matches.match')),
            ],
        ),
    ]
