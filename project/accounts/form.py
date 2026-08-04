from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser


class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ('email', 'username', 'phone_number',
                  'bio', 'profile_picture')

class EmailVerifyForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            "class": "form-control form-control-lg border-0",
            "placeholder": "Enter your email address",
            "id": "email",
        })
    )



class VerifyCodeForm(forms.Form):
    email = forms.EmailField(
        disabled=True,
        widget=forms.EmailInput(attrs={
            "class": "form-control form-control-lg border-0",
            "id": "email",
        })
    )

    code_1 = forms.CharField(
        max_length=1,
        widget=forms.TextInput(attrs={
            "class": "form-control form-control-lg border-0 text-center mx-1 mb-2 forgot-code-input",
            "maxlength": "1",
            "inputmode": "numeric",
        })
    )

    code_2 = forms.CharField(
        max_length=1,
        widget=forms.TextInput(attrs={
            "class": "form-control form-control-lg border-0 text-center mx-1 mb-2 forgot-code-input",
            "maxlength": "1",
            "inputmode": "numeric",
        })
    )

    code_3 = forms.CharField(
        max_length=1,
        widget=forms.TextInput(attrs={
            "class": "form-control form-control-lg border-0 text-center mx-1 mb-2 forgot-code-input",
            "maxlength": "1",
            "inputmode": "numeric",
        })
    )

    code_4 = forms.CharField(
        max_length=1,
        widget=forms.TextInput(attrs={
            "class": "form-control form-control-lg border-0 text-center mx-1 mb-2 forgot-code-input",
            "maxlength": "1",
            "inputmode": "numeric",
        })
    )

    code_5 = forms.CharField(
        max_length=1,
        widget=forms.TextInput(attrs={
            "class": "form-control form-control-lg border-0 text-center mx-1 mb-2 forgot-code-input",
            "maxlength": "1",
            "inputmode": "numeric",
        })
    )

    code_6 = forms.CharField(
        max_length=1,
        widget=forms.TextInput(attrs={
            "class": "form-control form-control-lg border-0 text-center mx-1 mb-2 forgot-code-input",
            "maxlength": "1",
            "inputmode": "numeric",
        })
    )
