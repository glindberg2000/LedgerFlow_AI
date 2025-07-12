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
        # Auto-fill title and summary from manifest if blank
        if (not self.title or self.title.strip() == "") or (
            not self.manifest_file_summary or self.manifest_file_summary.strip() == ""
        ):
            if self.original_file and self.original_file.name.lower().endswith(".json"):
                try:
                    self.original_file.seek(0)
                    import json

                    manifest = json.load(self.original_file)
                    # Prefer top-level Title and file_summary
                    manifest_title = manifest.get("Title")
                    manifest_summary = manifest.get("file_summary")
                    if (not self.title or self.title.strip() == "") and manifest_title:
                        self.title = manifest_title
                    if (
                        not self.manifest_file_summary
                        or self.manifest_file_summary.strip() == ""
                    ) and manifest_summary:
                        self.manifest_file_summary = manifest_summary
                    # Fallback to cover page title if needed
                    if not self.title or self.title.strip() == "":
                        pages = manifest.get("pages", [])
                        if pages and isinstance(pages, list):
                            cover = pages[0]
                            doc_title = cover.get("Title") or cover.get(
                                "document_title"
                            )
                            if doc_title:
                                self.title = doc_title
                    # Fallback to filename
                    if not self.title or self.title.strip() == "":
                        self.title = os.path.splitext(
                            os.path.basename(self.original_file.name)
                        )[0]
                except Exception:
                    if not self.title or self.title.strip() == "":
                        self.title = os.path.splitext(
                            os.path.basename(self.original_file.name)
                        )[0]
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
