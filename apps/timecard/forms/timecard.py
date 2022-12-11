from dateutil.relativedelta import relativedelta
from django.core.exceptions import ValidationError
from django.utils import timezone
from django import forms
from django.forms import BaseModelFormSet, modelformset_factory
from apps.timecard.forms import BaseForm
from apps.timecard.models import TimeCard


class TimeCardSearchForm(BaseForm):
    month = forms.CharField(
        label='表示月',
        required=False,
        max_length=7,
        widget=forms.DateInput(attrs={'type': 'month'})
    )

    def __init__(self, *args, **kwargs):
        self.base_fields['month'].initial = kwargs.pop('month').strftime('%Y-%m')
        super().__init__(*args, **kwargs)


class TimeCardForm(BaseForm, forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.today = timezone.datetime.today().astimezone(timezone.get_default_timezone()).date()
        super().__init__(*args, **kwargs)

        if not self.instance.id:
            self.initial['stamped_time'] = None

    def clean_stamped_time(self):
        if self.cleaned_data.get('stamped_time').date() > self.today:
            raise forms.ValidationError('当日以降の日付は指定できません。')
        return self.cleaned_data.get('stamped_time')

    class Meta(forms.ModelForm):
        model = TimeCard
        fields = ('kind', 'stamped_time')
        widgets = {
            'stamped_time': forms.DateInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%d %H:%M')
        }


class BaseTimeCardFormSet(BaseModelFormSet):
    def __init__(self, *args, **kwargs):
        if kwargs == {}:
            cp_args = ['']
            cp_args[0] = args[0].copy()
            for index in range(4):
                if cp_args[0]['form-{}-kind'.format(index)] and not cp_args[0]['form-{}-stamped_time'.format(index)]:
                    cp_args[0]['form-{}-kind'.format(index)] = ''

            super().__init__(*cp_args, **kwargs)
        else:
            target_date = kwargs.pop('date')
            user = kwargs.pop('user')
            super().__init__(*args, **kwargs)
            self.queryset = TimeCard.objects.filter(stamped_time__gte=target_date,
                                                    stamped_time__lt=(target_date + relativedelta(days=1)),
                                                    user=user)

    def clean(self):
        super().clean()
        start_work = end_work = enter_break = end_break = ''

        for form in self.forms:
            if form.cleaned_data == {}:
                continue

            kind = form.cleaned_data['kind']
            stamped_time = form.cleaned_data['stamped_time']
            if kind == TimeCard.Kind.IN:
                start_work = stamped_time
            elif kind == TimeCard.Kind.OUT:
                end_work = stamped_time
            elif kind == TimeCard.Kind.ENTER_BREAK:
                enter_break = stamped_time
            elif kind == TimeCard.Kind.END_BREAK:
                end_break = stamped_time

        if start_work or end_work:
            if not (start_work and end_work):
                raise ValidationError('出勤時刻と退勤時刻の両方を入力してください。')

            if end_work < start_work:
                raise ValidationError('出勤時刻＜退勤時刻となるように入力してください。')

        if enter_break or end_break:
            if not (start_work and end_work):
                raise ValidationError('休憩時間を入力する場合は、出勤時刻と退勤時刻を入力してください。')

            if not (enter_break and end_break):
                raise ValidationError('休憩開始と休憩終了の両方を入力してください。')
            elif end_break < enter_break:
                raise ValidationError('休憩開始＜休憩終了となるように入力してください。')

            if enter_break < start_work or end_work < enter_break:
                raise forms.ValidationError('休憩時刻は勤務時間内となるように入力してください。')

    def _should_delete_form(self, form):
        return forms.formsets.DELETION_FIELD_NAME in form.changed_data


TimeCardFormSet = \
    modelformset_factory(TimeCard, form=TimeCardForm, max_num=4, extra=4, formset=BaseTimeCardFormSet, can_delete=True)
