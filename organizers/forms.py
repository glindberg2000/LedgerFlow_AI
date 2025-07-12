from django import forms
from .models import OrganizerWorkbook


class OrganizerWorkbookForm(forms.ModelForm):
    class Meta:
        model = OrganizerWorkbook
        fields = ["business_profile", "tax_year", "title", "original_file", "notes"]

    def clean_original_file(self):
        file = self.cleaned_data["original_file"]
        if file:
            ext = file.name.lower().split(".")[-1]
            if ext not in ["pdf", "json"]:
                raise forms.ValidationError(
                    "Only PDF or JSON manifest files are allowed."
                )
            self.is_manifest = ext == "json"
        return file
