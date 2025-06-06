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
