from django.db import models
from django.contrib.auth import get_user_model


class ParserTemplate(models.Model):
    name = models.CharField(max_length=100)
    bank = models.CharField(max_length=100, blank=True, null=True)
    type = models.CharField(max_length=10, choices=[("pdf", "PDF"), ("csv", "CSV")])
    template = models.TextField(help_text="Regex or template logic for extraction")
    is_active = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    # For extensibility: add fields for vision fallback, etc.

    def __str__(self):
        return f"{self.name} ({self.bank or 'Any'}) [{self.type}]"


class SampleStatement(models.Model):
    file = models.FileField(upload_to="sample_statements/")
    bank = models.CharField(max_length=100, blank=True, null=True)
    type = models.CharField(max_length=10, choices=[("pdf", "PDF"), ("csv", "CSV")])
    uploaded_by = models.ForeignKey(
        get_user_model(), on_delete=models.SET_NULL, null=True, blank=True
    )
    upload_timestamp = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, null=True)
    # For extensibility: add snapshot/image field for admin preview

    def __str__(self):
        return f"{self.file.name} ({self.bank or 'Unknown'}) [{self.type}]"


class ExtractionResult(models.Model):
    sample = models.ForeignKey(SampleStatement, on_delete=models.CASCADE)
    parser = models.ForeignKey(
        ParserTemplate, on_delete=models.SET_NULL, null=True, blank=True
    )
    extracted_metadata = models.JSONField(blank=True, null=True)
    status = models.CharField(
        max_length=20, choices=[("success", "Success"), ("fail", "Fail")]
    )
    error_message = models.TextField(blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True)
    # For extensibility: add field for vision fallback result, etc.

    def __str__(self):
        return f"Result for {self.sample} with {self.parser or 'N/A'}: {self.status}"
