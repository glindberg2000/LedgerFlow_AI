from django import forms
from profiles.models import BusinessProfile


class ClientSelectForm(forms.Form):
    client = forms.ModelChoiceField(
        queryset=BusinessProfile.objects.all(), required=True, label="Client"
    )
