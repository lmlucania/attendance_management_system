from django.utils import timezone
from django import forms
from apps.timecard.forms import BaseForm
from apps.timecard.models import TimeCard


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
            'stamped_time': forms.DateInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%d %H:%m')
        }
