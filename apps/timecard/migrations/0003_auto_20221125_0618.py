# Generated by Django 3.2 on 2022-11-24 21:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('timecard', '0002_timecard_stamped_time'),
    ]

    operations = [
        migrations.AddField(
            model_name='timecard',
            name='state',
            field=models.CharField(choices=[('0', '新規'), ('1', '申請中'), ('2', '承認済み'), ('3', '修正依頼')], default='0', max_length=1, null=True, verbose_name='ステータス'),
        ),
        migrations.AlterField(
            model_name='timecard',
            name='kind',
            field=models.CharField(choices=[('0', '出勤'), ('1', '退勤'), ('2', '全休'), ('3', '午前休'), ('4', '午後休'), ('5', '休憩開始'), ('6', '休憩終了')], max_length=1, verbose_name='打刻区分'),
        ),
    ]