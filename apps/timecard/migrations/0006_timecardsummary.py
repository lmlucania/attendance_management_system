# Generated by Django 3.2 on 2023-04-28 13:26

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('timecard', '0005_alter_timecard_updated_at'),
    ]

    operations = [
        migrations.CreateModel(
            name='TimeCardSummary',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('total_work_hours', models.CharField(max_length=10, verbose_name='総労働時間')),
                ('total_break_hours', models.CharField(max_length=10, verbose_name='総休暇時間')),
                ('work_days_flag', models.PositiveIntegerField(verbose_name='出勤日フラグ')),
                ('month', models.CharField(max_length=6, verbose_name='対象月')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='登録日時')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新日時')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='timecardsummary', to=settings.AUTH_USER_MODEL, verbose_name='ユーザー')),
            ],
            options={
                'verbose_name': 'サマリ',
                'db_table': 'timecard_summary',
            },
        ),
    ]