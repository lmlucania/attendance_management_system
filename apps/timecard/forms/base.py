from datetime import datetime
import re

from django import forms
from django.utils import timezone


class BaseForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setup_bootstrap_class()

    def setup_bootstrap_class(self):
        for field_name, field in self.fields.items():
            if 'class' in field.widget.attrs:
                class_list = [field.widget.attrs['class']]
            elif (isinstance(field.widget, forms.RadioSelect) or
                  isinstance(field.widget, forms.CheckboxInput) or
                  isinstance(field.widget, forms.CheckboxSelectMultiple)):
                class_list = ['custom-control-input']
            else:
                class_list = ['form-control']

            if self.has_error(field_name):
                class_list.append('is-invalid')

            field.widget.attrs['class'] = ' '.join(class_list)


class SplitDateTimeWidget(forms.SplitDateTimeWidget):
    def value_from_datadict(self, data, files, name):
        date_str, time_str = super().value_from_datadict(data, files, name)

        if not date_str and not time_str:
            return

        value = (date_str or '') + (time_str or '')
        try:
            if self.is_HMS(time_str):
                return datetime.strptime(value, '%Y-%m-%d%H:%M:%S').astimezone(timezone.get_default_timezone())
            elif self.is_HM(time_str):
                return datetime.strptime(value, '%Y-%m-%d%H:%M').astimezone(timezone.get_default_timezone())
            return value
        except:
            return value

    def is_HMS(self, time_str):
        pattern = r'^((0?|1)[0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]$'
        return re.compile(pattern).match(time_str)

    def is_HM(self, time_str):
        pattern = r'^((0?|1)[0-9]|2[0-3]):[0-5][0-9]$'
        return re.compile(pattern).match(time_str)

    def decompress(self, value):
        try:
            return super().decompress(value)
        except:
            return value
