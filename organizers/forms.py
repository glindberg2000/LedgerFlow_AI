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
    pages_to_parse = forms.CharField(
        required=False,
        label="Pages to Parse (optional)",
        help_text="Enter a page range (e.g. 1-5,8,10-12) or leave blank to parse all pages.",
    )

    class Meta:
        model = OrganizerWorkbook
        fields = ["binder", "title", "original_file"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            # On change, remove binder, title, file, and pages_to_parse fields (all are read-only in admin)
            for field in ["binder", "title", "original_file", "pages_to_parse"]:
                if field in self.fields:
                    self.fields.pop(field)
        else:
            # On add, add a reminder to re-select the file if the form reloads
            self.fields["original_file"].help_text = (
                (self.fields["original_file"].help_text or "")
                + "<br><span style='color:red;'>If the form reloads due to an error, you must re-select the file before submitting again.</span>"
            )

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

    def clean_pages_to_parse(self):
        value = self.cleaned_data.get("pages_to_parse", "").strip()
        if not value:
            return ""  # treat blank as no restriction
        import re

        # Accept formats like 1-5,8,10-12
        pattern = r"^\s*\d+\s*(-\s*\d+\s*)?(\s*,\s*\d+\s*(-\s*\d+\s*)?)*\s*$"
        if not re.match(pattern, value):
            raise forms.ValidationError(
                "Invalid page range format. Use e.g. 1-5,8,10-12 or leave blank."
            )
        return value

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Set binder linkage on creation
        if not instance.pk:
            binder = self.cleaned_data.get("binder")
            if binder:
                instance.tax_year = binder
                instance.business_profile = binder.business_profile
        if commit:
            instance.save()
        return instance
