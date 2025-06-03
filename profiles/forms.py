from django import forms
from .models import StatementFile, BusinessProfile
from django.contrib.auth import get_user_model


class TransactionCSVForm(forms.Form):
    csv_file = forms.FileField(help_text="Upload a CSV file containing transactions.")


class StatementFileUploadForm(forms.Form):
    client = forms.ModelChoiceField(
        queryset=BusinessProfile.objects.all(), required=True
    )
    file_type = forms.ChoiceField(
        choices=StatementFile._meta.get_field("file_type").choices, required=True
    )
    files = forms.FileField(
        widget=forms.ClearableFileInput(),
        required=True,
        help_text="Upload one or more PDF/CSV files. (Hold Ctrl/Cmd to select multiple files)"
    )

    def clean_files(self):
        files = (
            self.files.getlist("files")
            if hasattr(self.files, "getlist")
            else [self.files["files"]]
        )
        allowed_types = ["application/pdf", "text/csv"]
        max_size = 10 * 1024 * 1024  # 10MB
        for f in files:
            if f.content_type not in allowed_types:
                raise forms.ValidationError(f"Unsupported file type: {f.content_type}")
            if f.size > max_size:
                raise forms.ValidationError(f"File {f.name} exceeds 10MB size limit.")
        return files
