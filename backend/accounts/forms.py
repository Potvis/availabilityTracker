from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from members.models import Member
from .models import UserProfile


class UserRegistrationForm(UserCreationForm):
    """Form for new user registration"""
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'uw.email@voorbeeld.be'
        })
    )
    first_name = forms.CharField(
        required=True,
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Voornaam'
        })
    )
    last_name = forms.CharField(
        required=True,
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Achternaam'
        })
    )
    date_of_birth = forms.DateField(
        label='Geboortedatum',
        required=True,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'placeholder': 'dd-mm-jjjj'
        }),
        help_text='Vereist voor verzekering'
    )

    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'password1', 'password2')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({'class': 'form-control'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control'})
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('Dit e-mailadres is al geregistreerd.')
        return email
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data['email']  # Use email as username
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']

        if commit:
            user.save()
            # Save date_of_birth to associated member
            if hasattr(user, 'profile') and user.profile.member:
                user.profile.member.date_of_birth = self.cleaned_data['date_of_birth']
                user.profile.member.save()

        return user


class UserLoginForm(AuthenticationForm):
    """Custom login form"""
    username = forms.EmailField(
        label='E-mail',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'uw.email@voorbeeld.be',
            'autofocus': True
        })
    )
    password = forms.CharField(
        label='Wachtwoord',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Wachtwoord'
        })
    )


class ProfileCompletionForm(forms.ModelForm):
    """Form for completing user profile with required fields"""

    # Member fields
    first_name = forms.CharField(
        label='Voornaam',
        required=True,
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Voornaam'
        })
    )
    last_name = forms.CharField(
        label='Achternaam',
        required=True,
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Achternaam'
        })
    )
    date_of_birth = forms.DateField(
        label='Geboortedatum',
        required=True,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
        }),
        help_text='Vereist voor verzekering'
    )
    phone = forms.CharField(
        label='Telefoonnummer',
        required=True,
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+32 123 45 67 89'
        })
    )
    shoe_size = forms.CharField(
        label='Schoenmaat',
        required=True,
        max_length=10,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Bijv. 42'
        }),
        help_text='Uw Europese schoenmaat (nodig voor apparatuurselectie)'
    )
    
    # UserProfile fields
    weight = forms.DecimalField(
        label='Gewicht (kg)',
        required=True,
        max_digits=5,
        decimal_places=2,
        min_value=30,
        max_value=300,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Bijv. 75.5',
            'step': '0.1'
        }),
        help_text='Uw gewicht in kilogram (nodig voor juiste veersterkte)'
    )
    
    receive_notifications = forms.BooleanField(
        label='Ontvang notificaties over mijn boekingen',
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    
    newsletter_subscription = forms.BooleanField(
        label='Schrijf me in voor de nieuwsbrief',
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    
    class Meta:
        model = UserProfile
        fields = ['weight', 'receive_notifications', 'newsletter_subscription']
    
    def __init__(self, *args, **kwargs):
        self.member = kwargs.pop('member', None)
        super().__init__(*args, **kwargs)

        # Pre-populate member fields if available
        if self.member:
            self.fields['first_name'].initial = self.member.first_name
            self.fields['last_name'].initial = self.member.last_name
            self.fields['date_of_birth'].initial = self.member.date_of_birth
            self.fields['phone'].initial = self.member.phone
            self.fields['shoe_size'].initial = self.member.shoe_size
    
    def clean_shoe_size(self):
        """Validate shoe size is numeric"""
        shoe_size = self.cleaned_data.get('shoe_size')
        try:
            size_num = int(shoe_size)
            if size_num < 25 or size_num > 55:
                raise forms.ValidationError('Voer een geldige schoenmaat in (25-55).')
        except (ValueError, TypeError):
            raise forms.ValidationError('Schoenmaat moet een getal zijn.')
        return shoe_size
    
    def save(self, commit=True):
        # Save UserProfile
        profile = super().save(commit=False)

        # Update associated Member
        if self.member:
            self.member.first_name = self.cleaned_data['first_name']
            self.member.last_name = self.cleaned_data['last_name']
            self.member.date_of_birth = self.cleaned_data['date_of_birth']
            self.member.phone = self.cleaned_data['phone']
            self.member.shoe_size = self.cleaned_data['shoe_size']

            if commit:
                self.member.save()

        if commit:
            profile.save()
            profile.check_profile_complete()

        return profile


class QuickProfileUpdateForm(forms.ModelForm):
    """Simplified form for quick profile updates"""
    
    phone = forms.CharField(
        label='Telefoonnummer',
        required=False,
        max_length=20,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    shoe_size = forms.CharField(
        label='Schoenmaat',
        required=False,
        max_length=10,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = UserProfile
        fields = ['weight', 'receive_notifications']
        widgets = {
            'weight': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.1'
            }),
            'receive_notifications': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
