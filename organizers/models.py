from django.db import models
from profiles.models import BusinessProfile, TaxYear


class OrganizerWorkbook(models.Model):
    business_profile = models.ForeignKey(
        BusinessProfile, on_delete=models.CASCADE, related_name="organizer_workbooks"
    )
    tax_year = models.ForeignKey(
        TaxYear, on_delete=models.CASCADE, related_name="organizer_workbooks"
    )
    title = models.CharField(max_length=255)
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
