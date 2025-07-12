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

    def clean(self):
        cleaned_data = super().clean()
        file = cleaned_data.get("original_file")
        title = cleaned_data.get("title")
        if file and file.name.lower().endswith(".json"):
            import json

            try:
                file.seek(0)
                manifest = json.load(file)
                # Try to extract a title from the manifest
                doc_title = None
                if "pages" in manifest and manifest["pages"]:
                    cover = manifest["pages"][0]
                    doc_title = cover.get("data", {}).get("document_title")
                if not doc_title:
                    doc_title = manifest.get("file_summary")
                if not doc_title:
                    doc_title = file.name
                cleaned_data["title"] = doc_title[:255]
            except Exception:
                if not title:
                    cleaned_data["title"] = file.name[:255]
        return cleaned_data
