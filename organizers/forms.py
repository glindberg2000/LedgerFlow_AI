from django import forms
from .models import OrganizerWorkbook


class OrganizerWorkbookForm(forms.ModelForm):
    class Meta:
        model = OrganizerWorkbook
        fields = ["business_profile", "tax_year", "original_file", "notes"]

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

    def clean(self):
        cleaned_data = super().clean()
        file = cleaned_data.get("original_file")
        title = None
        if file and file.name.lower().endswith(".json"):
            import json
            try:
                file.seek(0)
                manifest = json.load(file)
                # Try to extract a title from the manifest
                title = (
                    manifest.get("document_title")
                    or (manifest.get("pages") and manifest["pages"][0]["data"].get("document_title"))
                    or None
                )
            except Exception:
                title = None
        # Fallbacks
        if not title and file:
            title = file.name
        if not title:
            title = "TAX ORGANIZER"
        cleaned_data["title"] = title
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Set the title from cleaned_data
        instance.title = self.cleaned_data.get("title")
        if commit:
            instance.save()
        return instance
