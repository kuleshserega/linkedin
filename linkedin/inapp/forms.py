import collections

from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import authenticate
from django import forms


class EmailAuthenticationForm(AuthenticationForm):
    email = forms.EmailField(label="Email")

    use_required_attribute = False

    ORDER = ('email', 'password')

    def __init__(self, request=None, *args, **kwargs):
        super(EmailAuthenticationForm, self).__init__(request, *args, **kwargs)
        del self.fields['username']

        fields = collections.OrderedDict()
        for key in self.ORDER:
            fields[key] = self.fields.pop(key)
        self.fields = fields

        for field in self.fields.itervalues():
            field.widget.attrs.update({
                'class': 'form-control',
                'placeholder': field.label,
                'autocomplete': 'nope'
            })

    def clean(self):
        email = self.cleaned_data.get('email')
        password = self.cleaned_data.get('password')

        if email and password:
            self.user_cache = authenticate(email=email, password=password)
            if not self.user_cache:
                raise forms.ValidationError(
                    "Please enter a correct email and password.")
            if not self.user_cache.is_active:
                raise forms.ValidationError("This account is inactive.")
        return self.cleaned_data
