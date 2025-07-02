from django import forms

# from .models import UploadedFile, BusinessProfile
from django.contrib.auth import get_user_model


class TransactionCSVForm(forms.Form):
    csv_file = forms.FileField(help_text="Upload a CSV file containing transactions.")


class StatementFileUploadForm(forms.Form):
    client = forms.ModelChoiceField(
        queryset=BusinessProfile.objects.all(), required=True
    )
    # file_type = forms.ChoiceField(
    #     choices=UploadedFile._meta.get_field("file_type").choices, required=True
    # )
    files = forms.FileField(
        widget=forms.ClearableFileInput(),
        required=True,
        help_text="Upload one or more PDF/CSV files. (Hold Ctrl/Cmd to select multiple files)",
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


class BatchStatementFileUploadForm(forms.Form):
    client = forms.ModelChoiceField(
        queryset=BusinessProfile.objects.all(), required=True
    )
    # file_type = forms.ChoiceField(
    #     choices=UploadedFile._meta.get_field("file_type").choices, required=True
    # )
    parser_module = forms.ChoiceField(
        choices=[], required=False, label="Parser Module (optional)"
    )
    account_number = forms.CharField(label="Account Number (optional)", required=False)
    auto_parse = forms.BooleanField(
        label="Auto-parse and create transactions on upload",
        required=False,
        initial=True,
        help_text="If checked, transactions will be created immediately after upload. Uncheck to only extract metadata.",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["parser_module"].choices = get_parser_module_choices()
