from django.db import models
from django.utils import timezone

from apps.accounts.models import User


class TimeCard(models.Model):
    class Kind(models.TextChoices):
        IN = '0', '出勤'
        OUT = '1', '退勤'
        OFF = '2', '全休'
        MORNING_OFF = '3', '午前休'
        AFTERNOON_OFF = '4', '午後休'
        ENTER_BREAK = '5', '休憩開始'
        END_BREAK = '6', '休憩終了'

    class State(models.TextChoices):
        NEW = '0', '新規'
        PROCESSING = '1', '申請中'
        APPROVED = '2', '承認済み'
        REVISION_REQUEST = '3', '修正依頼'

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='timecard', verbose_name='ユーザー')
    kind = models.CharField(verbose_name='打刻区分', max_length=1, choices=Kind.choices)
    stamped_time = models.DateTimeField(verbose_name='打刻時刻', default=timezone.now)
    state = models.CharField(verbose_name='ステータス', max_length=1, choices=State.choices, default=State.NEW)

    created_at = models.DateTimeField(verbose_name='登録日時', auto_now_add=True)
    updated_at = models.DateTimeField(verbose_name='更新日時', auto_now=True)

    class Meta:
        db_table = 'timecard'
        verbose_name = 'タイムカード'


class TimeCardSummary(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='timecardsummary', verbose_name='ユーザー')
    total_work_hours = models.CharField(verbose_name='総労働時間', max_length=10)
    total_break_hours = models.CharField(verbose_name='総休暇時間', max_length=10)
    work_days_flag = models.PositiveIntegerField(verbose_name='出勤日フラグ')
    month = models.CharField(verbose_name='対象月', max_length=6)
    created_at = models.DateTimeField(verbose_name='登録日時', auto_now_add=True)
    updated_at = models.DateTimeField(verbose_name='更新日時', auto_now=True)

    class Meta:
        db_table = 'timecard_summary'
        verbose_name = 'サマリ'
