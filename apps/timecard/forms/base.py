from django import forms


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
