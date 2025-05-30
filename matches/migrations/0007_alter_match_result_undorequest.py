# Generated by Django 5.1.6 on 2025-03-28 23:51

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('matches', '0006_move'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name='match',
            name='result',
            field=models.CharField(choices=[('ongoing', '進行中'), ('sente_win', '先手勝利'), ('gote_win', '後手勝利'), ('draw', '引き分け'), ('waiting', '開始待ち')], default='waiting', max_length=20, verbose_name='対局結果'),
        ),
        migrations.CreateModel(
            name='UndoRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('accepted', 'Accepted'), ('denied', 'Denied')], default='pending', max_length=10)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('match', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='undo_request', to='matches.match')),
                ('requested_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
