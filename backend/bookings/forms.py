from django import forms

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