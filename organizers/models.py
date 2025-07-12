from django.db import models
from profiles.models import BusinessProfile, TaxYear
import os
import json


class OrganizerWorkbook(models.Model):
    business_profile = models.ForeignKey(
        BusinessProfile, on_delete=models.CASCADE, related_name="organizer_workbooks"
    )
    tax_year = models.ForeignKey(
        TaxYear, on_delete=models.CASCADE, related_name="organizer_workbooks"
    )
    title = models.CharField(max_length=255, blank=True)
    original_file = models.FileField(upload_to="organizers/originals/")
    upload_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=50,
        choices=[
            ("pending", "Pending Processing"),
            ("processing", "Processing"),
            ("completed", "Completed"),
            ("failed", "Failed"),
            ("manifest_ready", "Manifest Ready"),
            ("checklist_created", "Checklist Created"),
        ],
        default="pending",
    )
    notes = models.TextField(blank=True, null=True)

    # --- ADDED FIELDS FOR ADMIN ---
    manifest_hash = models.CharField(max_length=128, blank=True, null=True)
    manifest_page_count = models.IntegerField(blank=True, null=True)
    manifest_file_summary = models.TextField(blank=True, null=True)
    # -----------------------------

    def save(self, *args, **kwargs):
        if not self.title or self.title.strip() == "":
            if self.original_file and self.original_file.name.lower().endswith(".json"):
                try:
                    self.original_file.seek(0)
                    manifest = json.load(self.original_file)
                    pages = manifest.get("pages", [])
                    if pages and isinstance(pages, list):
                        cover = pages[0]
                        doc_title = (
                            cover.get("document_title")
                            or cover.get("Title")
                            or cover.get("label")
                        )
                        if doc_title:
                            self.title = str(doc_title)
                        else:
                            self.title = os.path.basename(self.original_file.name)
                    else:
                        self.title = os.path.basename(self.original_file.name)
                except Exception:
                    self.title = os.path.basename(self.original_file.name)
            else:
                self.title = (
                    os.path.basename(self.original_file.name) or "TAX ORGANIZER"
                )
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.business_profile} - {self.tax_year} - {self.title}"


class OrganizerOutput(models.Model):
    workbook = models.ForeignKey(
        OrganizerWorkbook, on_delete=models.CASCADE, related_name="outputs"
    )
    output_type = models.CharField(
        max_length=50,
        choices=[
            ("thumbnail", "Thumbnail"),
            ("page_pdf", "Page PDF"),
            ("manifest", "Manifest"),
        ],
    )
    file = models.FileField(upload_to="organizers/outputs/")
    page_number = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return (
            f"{self.workbook.title} - {self.output_type} - {self.page_number or 'N/A'}"
        )
