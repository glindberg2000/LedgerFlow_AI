from django import forms
from .models import OrganizerWorkbook
from profiles.models import TaxYear


class OrganizerWorkbookForm(forms.ModelForm):
    binder = forms.ModelChoiceField(
        queryset=TaxYear.objects.select_related("business_profile").order_by(
            "business_profile__company_name", "-year"
        ),
        required=True,
        label="Binder (Client – Tax Year)",
        help_text="Select the Binder (Client + Tax Year) to attach this document to. If not found, <a href='/admin/profiles/taxyear/add/' target='_blank'>create a new Binder</a>.",
        widget=forms.Select(attrs={"style": "width: 350px;"}),
    )
    title = forms.CharField(
        max_length=255,
        required=False,
        help_text="Optional. If left blank, the title will be auto-filled from the manifest or file name.",
    )

    class Meta:
        model = OrganizerWorkbook
        fields = ["binder", "title", "original_file", "notes"]

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
                title = (
                    manifest.get("document_title")
                    or (
                        manifest.get("pages")
                        and manifest["pages"][0]["data"].get("document_title")
                    )
                    or None
                )
            except Exception:
                title = None
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
        # Set binder linkage
        binder = self.cleaned_data.get("binder")
        if binder:
            instance.tax_year = binder
            instance.business_profile = binder.business_profile
        if commit:
            instance.save()
        return instance
