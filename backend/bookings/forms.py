from django import forms
from django.contrib.auth.models import User
from .schedule_models import BusinessEventBooking


class CSVImportForm(forms.Form):
    file = forms.FileField(
        label='CSV Bestand',
        help_text='Upload een CSV bestand met sessie aanwezigheden',
        widget=forms.FileInput(attrs={'accept': '.csv'})
    )
    auto_assign_cards = forms.BooleanField(
        label='Automatisch kaarten toewijzen',
        help_text='Probeer automatisch sessies toe te wijzen aan actieve kaarten van leden',
        required=False,
        initial=True
    )


class BusinessEventBookingForm(forms.ModelForm):
    """Form for guests to book a business event session."""

    first_name = forms.CharField(
        label='Voornaam',
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Voornaam'
        })
    )
    last_name = forms.CharField(
        label='Achternaam',
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Achternaam'
        })
    )
    email = forms.EmailField(
        label='E-mailadres',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'uw.email@voorbeeld.be'
        })
    )
    shoe_size = forms.CharField(
        label='Schoenmaat',
        max_length=10,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Bijv. 42'
        }),
        help_text='Uw Europese schoenmaat (nodig voor selectie Kangoo Boots)'
    )
    weight = forms.DecimalField(
        label='Gewicht (kg)',
        max_digits=5,
        decimal_places=2,
        min_value=30,
        max_value=300,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Bijv. 75.5',
            'step': '0.1'
        }),
        help_text='Dit wordt enkel gebruikt om te bepalen welk type veer (standaard of HD) we voor u klaarzetten.'
    )

    # Optional account creation
    create_account = forms.BooleanField(
        label='Maak een account aan zodat ik in de toekomst makkelijk kan boeken',
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'id': 'id_create_account'
        })
    )
    password1 = forms.CharField(
        label='Wachtwoord',
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Kies een wachtwoord'
        })
    )
    password2 = forms.CharField(
        label='Bevestig wachtwoord',
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Herhaal uw wachtwoord'
        })
    )

    class Meta:
        model = BusinessEventBooking
        fields = ['first_name', 'last_name', 'email', 'shoe_size', 'weight']

    def clean_shoe_size(self):
        shoe_size = self.cleaned_data.get('shoe_size')
        try:
            size_num = int(shoe_size)
            if size_num < 25 or size_num > 55:
                raise forms.ValidationError('Voer een geldige schoenmaat in (25-55).')
        except (ValueError, TypeError):
            raise forms.ValidationError('Schoenmaat moet een getal zijn.')
        return shoe_size

    def clean(self):
        cleaned_data = super().clean()
        create_account = cleaned_data.get('create_account')
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')

        if create_account:
            if not password1:
                self.add_error('password1', 'Wachtwoord is verplicht als u een account wilt aanmaken.')
            if not password2:
                self.add_error('password2', 'Bevestig uw wachtwoord.')
            if password1 and password2 and password1 != password2:
                self.add_error('password2', 'De wachtwoorden komen niet overeen.')
            if password1 and len(password1) < 8:
                self.add_error('password1', 'Wachtwoord moet minimaal 8 tekens bevatten.')

            # Check if email is already registered as a user
            email = cleaned_data.get('email')
            if email and User.objects.filter(email=email).exists():
                self.add_error(
                    'email',
                    'Dit e-mailadres heeft al een account. '
                    'Log in om te boeken of gebruik een ander e-mailadres.'
                )

        return cleaned_data