
import re
from django import forms
from .models import Category,Property, PropertyImage, Review, Reservation, Amenity, City, Area, Village,Category,Faqs

\

class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

    def value_from_datadict(self, data, files, name):
        upload = files.getlist(name)   # bütün faylları çəkir
        if not upload:
            return None
        return upload

    def value_omitted_from_data(self, data, files, name):
        
        return False


class MultipleImageField(forms.ImageField):
    """Fayl siyahısını (list) tək-tək təmizləyib validasiya edən ImageField."""
    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            return [single_file_clean(d, initial) for d in data]
        return single_file_clean(data, initial)

class PropertyImageForm(forms.Form):
    """Property üçün çoxlu şəkil yükləmə."""
    images = MultipleImageField(
        widget=MultipleFileInput(attrs={
            'class': 'form-control',
            'multiple': True,
            'id': 'property-images',
            'accept': 'image/png, image/jpeg',
        }),
        required=False,
        label="Əlavə Şəkillər"
    )


class PropertyForm(forms.ModelForm):
    category = forms.ModelChoiceField(
        queryset=Category.objects.all().order_by('name'),
        required=False, 
        label="Category"
    )

    city = forms.ModelChoiceField(
        queryset=City.objects.all().order_by('name'),
        required=True,
        label="City"
    )
    area = forms.ModelChoiceField(
        queryset=Area.objects.all().order_by('name'),
        required=False,
        label="Area"
    )
    village = forms.ModelChoiceField(
        queryset=Village.objects.all().order_by('name'),
        required=False,
        label="Village"
    )

    amenities = forms.ModelMultipleChoiceField(
        queryset=Amenity.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'custom-control-input'}),
        label="Təchizat / Kommunal"
    )

    class Meta:
        model = Property
        fields = [
            'category', 'city', 'area', 'village',
            'name', 'status', 'is_sale','has_mortgage',
            'price', 'square',
            'room_count',  'floor', 'floor_s',
            'is_renovated', 'has_extract',
            'description',
            'latitude', 'longitude',  
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4, 'class': 'form-control', 'placeholder': 'Ətraflı məlumat yazın...'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Qiymət'}),
            'square': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Sahə (m²)'}),
           
            'latitude': forms.HiddenInput(),  
            'longitude': forms.HiddenInput(),  
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for name, field in self.fields.items():
            if name != 'amenities' and not isinstance(field.widget, (forms.CheckboxInput, forms.HiddenInput)):
                field.widget.attrs.update({'class': 'form-control'})

        if self.instance.pk:
            self.fields['amenities'].initial = Amenity.objects.filter(
                propertyamenity__prop=self.instance
            )

    def clean(self):
        cleaned_data = super().clean()
        is_sale = cleaned_data.get('is_sale')
        price = cleaned_data.get('price')
        if is_sale and not price:
            self.add_error('price', "Satış elanı üçün qiymət mütləqdir.")
        return cleaned_data



class PropertyUpdateForm(forms.ModelForm):
    YES_NO_CHOICES = (
        (True, 'Bəli'),
        (False, 'Xeyr'),
    )


    is_renovated = forms.TypedChoiceField(
        choices=YES_NO_CHOICES,
        coerce=lambda x: x == 'True',
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Təmirli'
    )
    has_extract = forms.TypedChoiceField(
        choices=YES_NO_CHOICES,
        coerce=lambda x: x == 'True',
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Çıxarış (Kupça)'
    )
    has_mortgage = forms.TypedChoiceField(
        choices=YES_NO_CHOICES,
        coerce=lambda x: x == 'True',
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='İpotekali'
    )

    class Meta:
        model = Property
        fields = [
            'image', 'city', 'area', 'village', 'category', 'name', 
            'status', 'is_sale', 'price', 'square', 'floor_s', 'floor', 
            'room_count', 
            'is_renovated', 'has_extract', 'has_mortgage',
            'description', 'latitude', 'longitude',
        ]

        widgets = {
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'city': forms.Select(attrs={'class': 'form-control'}),
            'area': forms.Select(attrs={'class': 'form-control'}),
            'village': forms.Select(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Əmlakın adı'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'is_sale': forms.Select(
                choices=[(True, 'Satılır'), (False, 'Kirayə verilir')],
                attrs={'class': 'form-control'}
            ),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Qiymət'}),
            'square': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Sahə (m²)', 'step': '0.01'}),
            'floor_s': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Mərtəbə sayı'}),
            'floor': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Yerləşdiyi mərtəbə'}),
            'room_count': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Otaq sayı'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Əmlak haqqında məlumat'}),
            'latitude': forms.HiddenInput(attrs={'id': 'id_latitude'}),
            'longitude': forms.HiddenInput(attrs={'id': 'id_longitude'}),
            
        }

        labels = {
            'image': 'Şəkil',
            'city': 'Şəhər',
            'area': 'Rayon',
            'village': 'Qəsəbə/Kənd',
            'category': 'Kateqoriya',
            'name': 'Əmlakın adı',
            'status': 'Status',
            'is_sale': 'Elan növü',
            'price': 'Qiymət',
            'square': 'Sahə (m²)',
            'floor_s': 'Mərtəbə sayı',
            'floor': 'Yerləşdiyi mərtəbə',
            'room_count': 'Otaq sayı',
            'description': 'Təsvir',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['city'].queryset = City.objects.order_by('name')
        self.fields['area'].queryset = Area.objects.order_by('name')
        self.fields['village'].queryset = Village.objects.order_by('name')
        self.fields['category'].queryset = Category.objects.order_by('name')

        self.fields['area'].required = False
        self.fields['village'].required = False
        self.fields['category'].required = False
        self.fields['image'].required = False

        self.fields['city'].empty_label = "Şəhər seçin"
        self.fields['area'].empty_label = "Rayon seçin"
        self.fields['village'].empty_label = "Qəsəbə/Kənd seçin"
        self.fields['category'].empty_label = "Kateqoriya seçin"

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['name', 'surname', 'description', 'rating']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Adınız'}),
            'surname': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Soyadınız'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': 'Rəyinizi yazın...'}),
            'rating': forms.Select(choices=[(i, i) for i in range(1, 6)], attrs={'class': 'form-control selectpicker'}),
        }


class ReservationForm(forms.ModelForm):
    class Meta:
        model = Reservation
        fields = ["name", "surname", "phone", 'email', "message"]

        widgets = {

            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Adınız'}),
            'surname': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Soyadınız'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+994 (XX) XXX-XX-XX'}),
            'message': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': 'Mesajınız...'}),

        }

    def clean_name(self):
        name = self.cleaned_data["name"].strip()

        if len(name) < 2:
            raise forms.ValidationError("Name must be at least 2 characters.")

        if not re.fullmatch(r"[A-Za-zƏəİıÖöÜüĞğÇçŞş\s]+", name):
            raise forms.ValidationError("Name can contain only letters.")

        return name

    def clean_surname(self):
        surname = self.cleaned_data["surname"].strip()

        if surname:
            if len(surname) < 2:
                raise forms.ValidationError("Surname must be at least 2 characters.")

            if not re.fullmatch(r"[A-Za-zƏəİıÖöÜüĞğÇçŞş\s]+", surname):
                raise forms.ValidationError("Surname can contain only letters.")

        return surname

    def clean_phone(self):
        phone = self.cleaned_data["phone"].strip()

        if not re.fullmatch(r"\+?\d{10,15}", phone):
            raise forms.ValidationError("Enter a valid phone number.")

        return phone

    def clean_message(self):
        message = self.cleaned_data["message"].strip()

        if len(message) < 10:
            raise forms.ValidationError("Message must be at least 10 characters.")

        return message







class PropertyFilterForm(forms.Form):
    city = forms.ModelMultipleChoiceField(
        queryset=City.objects.all().order_by('name'),
        required=False,
        widget=forms.SelectMultiple(attrs={"class": "form-control", "id": "choices-city"})
    )

    area = forms.ModelMultipleChoiceField(
        queryset=Area.objects.all().order_by('name'),
        required=False,
        widget=forms.SelectMultiple(attrs={"class": "form-control", "id": "choices-area"})
    )

    village = forms.ModelMultipleChoiceField(
        queryset=Village.objects.all().order_by('name'),
        required=False,
        widget=forms.SelectMultiple(attrs={"class": "form-control", "id": "choices-village"})
    )