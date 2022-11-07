from django.db import models
from django.utils import timezone

from apps.accounts.models import User


class TimeCard(models.Model):
    class Kind(models.TextChoices):
        IN = '0', '出勤'
        OUT = '1', '退勤'
        RESET = '9', 'リセット'

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='timecard', verbose_name='ユーザー')
    kind = models.CharField(verbose_name='打刻区分', max_length=1, choices=Kind.choices)
    stamped_time = models.DateTimeField(verbose_name='打刻時刻', default=timezone.now)

    created_at = models.DateTimeField(verbose_name='登録日時', auto_now_add=True)
    updated_at = models.DateTimeField(verbose_name='更新日時', auto_now_add=True)

    class Meta:
        db_table = 'timecard'
        verbose_name = 'タイムカード'
