from django import forms
from .models import OrganizerWorkbook


class OrganizerWorkbookForm(forms.ModelForm):
    class Meta:
        model = OrganizerWorkbook
        fields = ["business_profile", "title", "original_file", "notes"]
