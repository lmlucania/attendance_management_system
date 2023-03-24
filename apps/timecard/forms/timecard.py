from dateutil.relativedelta import relativedelta
from django.core.validators import FileExtensionValidator
from django import forms
from django.db import transaction
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


class TimeCardForm(BaseForm, forms.ModelForm):
    DISPLAY_KIND_CHOICES = [TimeCard.Kind.IN, TimeCard.Kind.OUT, TimeCard.Kind.ENTER_BREAK, TimeCard.Kind.END_BREAK]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['stamped_time'].required = False
        self.fields['kind'].widget.choices[1:] = [choice for choice in self.fields['kind'].widget.choices
                                                  if choice[0] in self.DISPLAY_KIND_CHOICES]

        if not self.instance.id:
            self.initial['stamped_time'] = None

    class Meta(forms.ModelForm):
        model = TimeCard
        fields = ('kind', 'stamped_time')
        widgets = {
            'stamped_time': forms.DateInput(attrs={'type': 'time'}, format='%H:%M')
        }
        labels = {
            'kind': '',
            'stamped_time': ''
        }


class BaseTimeCardFormSet(BaseModelFormSet):
    ERR_MSG_NEED_WORK_TIME = '出勤時刻と退勤時刻の両方を入力してください。'
    ERR_MSG_NEED_WORK_TIME_BY_BREAK_TIME = '休憩時間が入力されています。出勤時刻と退勤時刻を入力してください。'
    ERR_MSG_WORK_TIME = '出勤時刻＜退勤時刻で入力してください。'
    ERR_MSG_NEED_BREAK_TIME = '休憩開始と休憩終了の両方を入力してください。'
    ERR_MSG_BREAK_TIME = '休憩開始＜休憩終了で入力してください。'
    ERR_MSG_BREAK_TIME_OUT_OF_RANGE = '休憩時刻は勤務時間内で入力してください。'
    ERR_MSG_DUPLICATE_KIND = '打刻区分が重複しています。'


    def __init__(self, *args, **kwargs):
        if kwargs == {}:
            super().__init__(*args, **kwargs)
        else:
            date = kwargs.pop('date')
            user = kwargs.pop('user')
            super().__init__(*args, **kwargs)
            self.queryset = TimeCard.objects.filter(stamped_time__gte=date,stamped_time__lt=(
                    date + relativedelta(days=1)),user=user).order_by('kind')

    @transaction.non_atomic_requests
    def save(self):
        try:
            return super().save(commit=True)
        except:
            return False

    def clean(self):
        super().clean()
        if any('DELETE' in query_dict_key for query_dict_key in self.data.keys()):
            return

        start_work = end_work = enter_break = end_break = ''
        kind_list = []

        for form in self.forms:
            if form.cleaned_data == {}:
                continue

            cleaned_kind = form.cleaned_data.get('kind')
            cleaned_stamped_time = form.cleaned_data.get('stamped_time')

            if cleaned_kind == TimeCard.Kind.IN:
                start_work = cleaned_stamped_time
            elif cleaned_kind == TimeCard.Kind.OUT:
                end_work = cleaned_stamped_time
            elif cleaned_kind == TimeCard.Kind.ENTER_BREAK:
                enter_break = cleaned_stamped_time
            elif cleaned_kind == TimeCard.Kind.END_BREAK:
                end_break = cleaned_stamped_time

            kind_list.append(cleaned_kind)

        if self._has_duplicates(kind_list):
            raise forms.ValidationError(self.ERR_MSG_DUPLICATE_KIND)

        if start_work or end_work:
            if not (start_work and end_work):
                raise forms.ValidationError(self.ERR_MSG_NEED_WORK_TIME)

            elif not(start_work < end_work):
                raise forms.ValidationError(self.ERR_MSG_WORK_TIME)

        if enter_break or end_break:
            if not (start_work and end_work):
                raise forms.ValidationError(self.ERR_MSG_NEED_WORK_TIME_BY_BREAK_TIME)

            if not (enter_break and end_break):
                raise forms.ValidationError(self.ERR_MSG_NEED_BREAK_TIME)
            elif not(enter_break < end_break):
                raise forms.ValidationError(self.ERR_MSG_BREAK_TIME)

            if not(start_work <= enter_break) or not(end_break <= end_work):
                raise forms.ValidationError(self.ERR_MSG_BREAK_TIME_OUT_OF_RANGE)

    def _should_delete_form(self, form):
        return forms.formsets.DELETION_FIELD_NAME in form.changed_data

    def _has_duplicates(self, kind_list):
        return len(kind_list) != len(set(kind_list))

TimeCardFormSet = \
    modelformset_factory(TimeCard, form=TimeCardForm, max_num=4, extra=4, formset=BaseTimeCardFormSet, can_delete=True)

class UploadFileForm(BaseForm):
    LIMIT_SIZE = 2 * 10 * 10 ** 3
    file = forms.FileField(
        label='アップロードファイル',
        allow_empty_file=False,
        validators = [
            FileExtensionValidator(['xlsx'], message='許可されていないファイルが指定されました。Excelファイルを選択してください。')
        ])

    def clean_file(self):
        file = self.cleaned_data['file']

        if file.size > self.LIMIT_SIZE:
            raise forms.ValidationError('ファイルサイズが大きすぎます。 20KB以下のファイルを指定してください。')

        return file
