from django import forms
from accounts.models import CustomUser

class ProfileForm(forms.ModelForm):
    MAX_FILE_SIZE = 5 * 1024 * 1024
    old_password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={
            "class": "form-control form-control-lg border-0",
            "id": "oldPassword",
        }),
        label="Köhnə şifrə"
    )

    new_password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={
            "class": "form-control form-control-lg border-0",
            "id": "newPassword",
        }),
        label="Yeni şifrə"
    )

    confirm_new_password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={
            "class": "form-control form-control-lg border-0",
            "id": "confirmNewPassword",
        }),
        label="Yeni şifrəni təsdiqləyin"
    )

    class Meta:
        model = CustomUser
        fields = [
            'profile_picture',
            'first_name',
            'last_name',
            'phone_number',
            'email',
            'bio',
        ]

        widgets = {
            'profile_picture': forms.FileInput(attrs={
                'class': 'custom-file-input',
                'id': 'customFile',
                'hidden': True,
                'accept': 'image/*',
            }),

            'first_name': forms.TextInput(attrs={
                'class': 'form-control form-control-lg border-0',
                'id': 'firstName',
            }),

            'last_name': forms.TextInput(attrs={
                'class': 'form-control form-control-lg border-0',
                'id': 'lastName',
            }),

            'phone_number': forms.TextInput(attrs={
                'class': 'form-control form-control-lg border-0',
                'id': 'phone',
            }),

            'email': forms.EmailInput(attrs={
                'class': 'form-control form-control-lg border-0',
                'id': 'email',
            }),

            'bio': forms.TextInput(attrs={
                'class': 'form-control form-control-lg border-0',
                'id': 'title',
            }),
        }

        labels = {
            'first_name': 'Ad',
            'last_name': 'Soyad',
            'phone_number': 'Telefon',
            'email': 'Email',
            'bio': 'Vəzifə',
        }


    def clean_profile_picture(self):
        picture = self.cleaned_data.get("profile_picture")

        if picture:
            if picture.size > self.MAX_FILE_SIZE:
                raise forms.ValidationError(
                    "Şəklin ölçüsü 5 MB-dan böyük ola bilməz."
                )

        return picture