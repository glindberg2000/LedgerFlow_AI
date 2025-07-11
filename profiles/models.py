from django.db import models
from django.db.models import JSONField
import uuid
import importlib.util
import os
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
import hashlib
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.utils import timezone
from django.conf import settings
import re

# Canonical value for unclassified transactions. Use this everywhere a transaction is unclassified or not processed.
CLASSIFICATION_METHOD_UNCLASSIFIED = "None"
# Canonical value for unprocessed payee extraction. Use this everywhere payee_extraction_method is not processed.
PAYEE_EXTRACTION_METHOD_UNPROCESSED = "None"

# Create your models here.


class BusinessProfile(models.Model):
    # Default 'id' integer PK is used
    client_id = models.CharField(
        max_length=64,
        unique=True,
        editable=False,
        blank=False,
        null=False,
        help_text="Unique, URL-safe identifier for this client. Used for lookups and URLs, but not the primary key.",
    )
    company_name = models.CharField(
        max_length=255,
        blank=False,
        null=False,
        default="ACME Corp",
        help_text="Human-friendly business name. Editable.",
    )
    business_type = models.TextField(blank=True, null=True)
    business_description = models.TextField(blank=True, null=True)
    contact_info = models.TextField(blank=True, null=True)
    location = models.CharField(max_length=200, blank=True, null=True)

    # User-friendly text fields for AI-generated data
    common_expenses = models.TextField(blank=True, null=True)
    custom_categories = models.TextField(blank=True, null=True)
    industry_keywords = models.TextField(blank=True, null=True)
    category_patterns = models.TextField(blank=True, null=True)
    business_rules = models.TextField(blank=True, null=True)
    ai_generated_profile = models.JSONField(default=dict)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.company_name

    def clean(self):
        # Ensure client_id is URL-safe
        if not re.match(r"^[a-zA-Z0-9_-]+$", self.client_id):
            raise ValidationError(
                {
                    "client_id": "Client ID must be URL-safe (letters, numbers, underscores, hyphens only)."
                }
            )


class ClientExpenseCategory(models.Model):
    client = models.ForeignKey(
        BusinessProfile,
        on_delete=models.CASCADE,
        related_name="client_expense_categories",
    )
    category_name = models.CharField(max_length=255)
    category_type = models.CharField(
        max_length=50,
        choices=[
            ("other_expense", "Other Expense"),
            ("custom_category", "Custom Category"),
        ],
    )
    description = models.TextField(blank=True, null=True)
    tax_year = models.IntegerField()
    worksheet = models.CharField(
        max_length=50,
        choices=[
            ("6A", "6A"),
            ("Auto", "Auto"),
            ("HomeOffice", "HomeOffice"),
            ("Personal", "Personal"),
            ("None", "None"),
        ],
    )
    parent_category = models.CharField(max_length=255, blank=True, null=True)
    line_number = models.CharField(max_length=50, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["client", "category_name", "tax_year"],
                name="unique_client_category_year",
            )
        ]


class TransactionClassification(models.Model):
    """
    Tracks classifications for transactions, allowing history and multiple classifications over time.
    Links to Transaction model without modifying its structure.
    """

    transaction = models.ForeignKey(
        "Transaction", on_delete=models.CASCADE, related_name="classifications"
    )
    classification_type = models.CharField(
        max_length=50, help_text="Type of classification (e.g., 'business', 'personal')"
    )
    worksheet = models.CharField(
        max_length=50,
        help_text="Tax worksheet category (e.g., '6A', 'Auto', 'HomeOffice')",
    )
    category = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Specific expense category within the worksheet",
    )
    business_percentage = models.IntegerField(
        default=100, help_text="Percentage of the transaction that is business-related"
    )
    confidence = models.CharField(
        max_length=20, help_text="Confidence level of the classification"
    )
    reasoning = models.TextField(
        help_text="Explanation for the classification decision"
    )

    # Audit fields
    created_by = models.CharField(
        max_length=100, help_text="Agent or user who created this classification"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(
        default=True, help_text="Whether this is the current active classification"
    )

    class Meta:
        indexes = [
            models.Index(fields=["transaction", "created_at"]),
            models.Index(fields=["transaction", "is_active"]),
            models.Index(fields=["classification_type"]),
            models.Index(fields=["worksheet"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.transaction} - {self.classification_type} ({self.worksheet})"

    def save(self, *args, **kwargs):
        # If this is a new active classification, deactivate other classifications
        if self.is_active and not self.pk:
            TransactionClassification.objects.filter(
                transaction=self.transaction, is_active=True
            ).update(is_active=False)
        super().save(*args, **kwargs)


class Transaction(models.Model):
    client = models.ForeignKey(
        BusinessProfile, on_delete=models.CASCADE, related_name="transactions"
    )
    transaction_date = models.DateField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField()
    category = models.CharField(max_length=255, blank=True, null=True)
    parsed_data = models.JSONField(default=dict, blank=True)
    file_path = models.CharField(max_length=255, blank=True, null=True)
    source = models.CharField(max_length=255, blank=True, null=True)
    transaction_type = models.CharField(max_length=50, blank=True, null=True)
    normalized_amount = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    statement_start_date = models.DateField(blank=True, null=True)
    statement_end_date = models.DateField(blank=True, null=True)
    account_number = models.CharField(max_length=50, blank=True, null=True)
    transaction_hash = models.CharField(
        max_length=64, unique=True, db_index=True, blank=True, null=True
    )
    transaction_id = models.CharField(
        max_length=128, db_index=True, null=True, blank=True
    )

    # Fields for LLM processing
    normalized_description = models.TextField(blank=True, null=True)
    payee = models.CharField(max_length=255, blank=True, null=True)
    confidence = models.CharField(
        max_length=50, blank=True, null=True
    )  # high, medium, low
    reasoning = models.TextField(blank=True, null=True)  # Classification reasoning
    payee_reasoning = models.TextField(blank=True, null=True)  # Payee lookup reasoning
    business_context = models.TextField(blank=True, null=True)
    questions = models.TextField(blank=True, null=True)

    # Classification fields
    classification_type = models.CharField(
        max_length=50,
        help_text="Type of classification (e.g., 'business', 'personal')",
        null=True,
        blank=True,
    )
    worksheet = models.CharField(
        max_length=50,
        help_text="Tax worksheet category (e.g., '6A', 'Auto', 'HomeOffice')",
        null=True,
        blank=True,
    )
    business_percentage = models.IntegerField(
        default=100, help_text="Percentage of the transaction that is business-related"
    )

    # Processing method tracking
    payee_extraction_method = models.CharField(
        max_length=128,
        default=None,  # Changed from "AI" to None
        help_text="Method used to extract the payee information",
    )
    classification_method = models.CharField(
        max_length=128,
        default=None,
        help_text="Method used to classify the transaction",
    )

    # New fields for full auditability
    statement_file = models.ForeignKey(
        "StatementFile", on_delete=models.CASCADE, null=True, blank=True
    )  # One-way FK only (RecursionError fix, see o3_dev review)
    parser_name = models.CharField(max_length=64, null=True, blank=True)

    # New field for needs_account_number
    needs_account_number = models.BooleanField(
        default=False,
        help_text="True if this transaction needs an account number to be entered manually.",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["client", "transaction_hash"], name="unique_transaction"
            )
        ]

    def __str__(self):
        return f"{self.client.client_id} - {self.transaction_date} - {self.amount}"

    @property
    def current_classification(self):
        """Get the current active classification for this transaction."""
        return self.classifications.filter(is_active=True).first()

    @property
    def classification_history(self):
        """Get all classifications for this transaction in chronological order."""
        return self.classifications.all()

    def add_classification(
        self, classification_type, worksheet, confidence, reasoning, created_by
    ):
        """
        Add a new classification for this transaction.
        Automatically deactivates previous classifications.
        """
        return TransactionClassification.objects.create(
            transaction=self,
            classification_type=classification_type,
            worksheet=worksheet,
            confidence=confidence,
            reasoning=reasoning,
            created_by=created_by,
            is_active=True,
        )

    @staticmethod
    def compute_transaction_hash(
        client_id, transaction_date, amount, description, category
    ):
        """Deterministically hash the canonical fields for deduplication."""
        key = f"{client_id}|{transaction_date}|{amount}|{description}|{category}"
        return hashlib.sha256(key.encode("utf-8")).hexdigest()

    def save(self, *args, **kwargs):
        if not self.transaction_hash:
            self.transaction_hash = Transaction.compute_transaction_hash(
                self.client_id,
                self.transaction_date,
                self.amount,
                self.description,
                self.category,
            )
        super().save(*args, **kwargs)


class LLMConfig(models.Model):
    provider = models.CharField(max_length=255)
    model = models.CharField(max_length=255, unique=True)
    url = models.URLField(blank=True, null=True)

    def __str__(self):
        return self.model


class Tool(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, null=True)
    module_path = models.CharField(max_length=255)  # Path to the tool module
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Agent(models.Model):
    name = models.CharField(max_length=255)
    purpose = models.TextField()
    prompt = models.TextField()
    llm = models.ForeignKey(
        LLMConfig,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="agents",
    )
    tools = models.ManyToManyField(
        Tool, related_name="agents", blank=True
    )  # Add tools relationship

    def __str__(self):
        return self.name


class NormalizedVendorData(models.Model):
    transaction = models.OneToOneField(
        Transaction, on_delete=models.CASCADE, related_name="normalized_data"
    )
    normalized_name = models.CharField(max_length=255)
    normalized_description = models.TextField(blank=True, null=True)
    justification = models.TextField(blank=True, null=True)
    confidence = models.DecimalField(max_digits=5, decimal_places=2)

    def __str__(self):
        return self.normalized_name


class IRSWorksheet(models.Model):
    """Global IRS worksheet definitions"""

    name = models.CharField(
        max_length=50, unique=True
    )  # e.g., "6A", "Auto", "HomeOffice"
    description = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class IRSExpenseCategory(models.Model):
    """Standard IRS expense categories that appear on worksheets"""

    worksheet = models.ForeignKey(
        IRSWorksheet, on_delete=models.CASCADE, related_name="categories"
    )
    name = models.CharField(max_length=255)
    description = models.TextField()
    line_number = models.CharField(
        max_length=50, help_text="Line number on the IRS form"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["worksheet", "name"]
        ordering = ["worksheet", "line_number"]

    def __str__(self):
        return f"{self.worksheet.name} - {self.name} (Line {self.line_number})"


class BusinessExpenseCategory(models.Model):
    """Custom expense categories specific to a business"""

    business = models.ForeignKey(
        BusinessProfile,
        on_delete=models.CASCADE,
        related_name="business_expense_categories",
    )
    category_name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    worksheet = models.ForeignKey(
        IRSWorksheet, on_delete=models.CASCADE, related_name="business_categories"
    )
    parent_category = models.ForeignKey(
        IRSExpenseCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="The IRS category this maps to (e.g., 'Other Expenses' on 6A)",
    )
    is_active = models.BooleanField(default=True)
    tax_year = models.IntegerField(help_text="Tax year this category applies to")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Business Expense Categories"
        unique_together = ["business", "category_name"]

    def __str__(self):
        return f"{self.business.client_id} - {self.category_name}"


class ClassificationOverride(models.Model):
    """Model for manual classification overrides by bookkeepers."""

    transaction = models.ForeignKey(
        Transaction,
        on_delete=models.CASCADE,
        related_name="classification_overrides",
        null=True,
        blank=True,
    )
    new_classification_type = models.CharField(max_length=50, null=True, blank=True)
    new_worksheet = models.CharField(max_length=50, null=True, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Classification Override"
        verbose_name_plural = "Classification Overrides"

    def __str__(self):
        return f"Override for {self.transaction} by {self.created_by}"


class ProcessingTask(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]

    TASK_TYPES = [
        ("payee_lookup", "Payee Lookup"),
        ("classification", "Classification"),
    ]

    task_id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    task_type = models.CharField(max_length=20, choices=TASK_TYPES)
    client = models.ForeignKey(BusinessProfile, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    transaction_count = models.IntegerField()
    processed_count = models.IntegerField(default=0)
    error_count = models.IntegerField(default=0)
    error_details = models.JSONField(default=dict)
    task_metadata = models.JSONField(default=dict)  # For storing dynamic configuration
    transactions = models.ManyToManyField(
        "Transaction", related_name="processing_tasks", blank=True
    )

    def __str__(self):
        return f"{self.task_type} task for {self.client.client_id} ({self.status})"


class SearchResult(models.Model):
    """Model to store search results from SearXNG."""

    query = models.CharField(max_length=255)
    title = models.CharField(max_length=255)
    url = models.URLField()
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    source = models.CharField(max_length=50, default="searxng")

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["query"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.title} ({self.query})"


def statement_upload_to_uuid(instance, filename):
    ext = filename.split(".")[-1]
    uuid_str = str(uuid.uuid4())
    return f"clients/{instance.client.client_id}/{uuid_str}.{ext}"


class StatementFile(models.Model):
    """
    Stores uploaded statement files (PDF, CSV, etc.) for a client.
    Now includes a statement_hash (SHA256 of file contents) for deduplication per client.
    """

    STATUS_CHOICES = [
        ("uploaded", "Uploaded"),
        ("identified", "Identified"),
        ("parsed", "Parsed"),
        ("normalized", "Normalized"),
        ("error", "Error"),
    ]
    client = models.ForeignKey(
        BusinessProfile, on_delete=models.CASCADE, related_name="statement_files"
    )
    file = models.FileField(upload_to=statement_upload_to_uuid)
    file_type = models.CharField(
        max_length=10, choices=[("pdf", "PDF"), ("csv", "CSV"), ("other", "Other")]
    )
    original_filename = models.CharField(max_length=255)
    upload_timestamp = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(
        get_user_model(), on_delete=models.SET_NULL, null=True, blank=True
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="uploaded")
    status_detail = models.TextField(blank=True, null=True)
    bank = models.CharField(max_length=100, blank=True, null=True)
    account_number = models.CharField(max_length=100, blank=True, null=True)
    year = models.IntegerField(blank=True, null=True)
    month = models.IntegerField(blank=True, null=True)
    parsed_metadata = models.JSONField(blank=True, null=True, default=dict)
    parser_module = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Registered parser module name (from ParserRegistry)",
    )
    statement_type = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Flexible statement type (e.g., VISA, checking, etc.)",
    )
    statement_hash = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        help_text="SHA256 of file contents for deduplication",
    )
    needs_account_number = models.BooleanField(
        default=False,
        help_text="True if this file needs an account number to be entered manually.",
    )
    account_holder_name = models.CharField(max_length=255, blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    statement_period_start = models.CharField(max_length=32, blank=True, null=True)
    statement_period_end = models.CharField(max_length=32, blank=True, null=True)
    statement_date = models.CharField(max_length=32, blank=True, null=True)
    account_type = models.CharField(max_length=64, blank=True, null=True)

    class Meta:
        ordering = ["-upload_timestamp"]
        verbose_name = "Statement File"
        verbose_name_plural = "Statement Files"
        constraints = [
            models.UniqueConstraint(
                fields=["client", "statement_hash"], name="unique_client_statement_hash"
            )
        ]

    def get_source_display(self):
        """Returns a user-friendly display name for the transaction source."""
        parts = []
        if self.bank:
            parts.append(self.bank)
        if self.account_number:
            # Display last 4 digits for privacy
            parts.append(f"....{self.account_number[-4:]}")
        if self.statement_type:
            parts.append(self.statement_type)

        return " - ".join(parts) if parts else "Unknown Source"

    def __str__(self):
        return f"{self.client.client_id} - {self.original_filename}"

    def compute_statement_hash(self):
        """Compute SHA256 hash of the file contents."""
        if not self.file:
            return None
        self.file.seek(0)
        file_bytes = self.file.read()
        self.file.seek(0)
        return hashlib.sha256(file_bytes).hexdigest()

    def save(self, *args, **kwargs):
        if not self.statement_hash and self.file:
            self.statement_hash = self.compute_statement_hash()
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        # Compute hash if not set and file is present
        if not self.statement_hash and self.file:
            self.statement_hash = self.compute_statement_hash()
        if self.statement_hash:
            qs = type(self).objects.filter(
                client=self.client, statement_hash=self.statement_hash
            )
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                raise ValidationError(
                    "This statement file has already been uploaded for this client."
                )

    # For extensibility: add batch_id, progress, etc. as needed for batch uploads


class ParsingRun(models.Model):
    statement_file = models.ForeignKey(
        "StatementFile", on_delete=models.CASCADE, related_name="parsing_runs"
    )
    parser_module = models.CharField(max_length=100)
    status = models.CharField(
        max_length=20, choices=[("success", "Success"), ("fail", "Fail")]
    )
    error_message = models.TextField(blank=True, null=True)
    rows_imported = models.IntegerField(default=0)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.statement_file} | {self.parser_module} | {self.status} | {self.created}"


@receiver(post_delete, sender=StatementFile)
def delete_statementfile_file(sender, instance, **kwargs):
    if instance.file:
        instance.file.delete(save=False)


class TaxChecklistItem(models.Model):
    STATUS_CHOICES = [
        ("not_started", "Not Started"),
        ("in_progress", "In Progress"),
        ("complete", "Complete"),
        ("needs_review", "Needs Review"),
    ]

    business_profile = models.ForeignKey(
        BusinessProfile, on_delete=models.CASCADE, related_name="tax_checklist_items"
    )
    tax_year = models.CharField(
        max_length=8
    )  # e.g., "2023"; change to FK if you have a TaxYear model
    form_code = models.CharField(max_length=10)
    enabled = models.BooleanField(default=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="not_started"
    )
    notes = models.TextField(blank=True, null=True)
    current_year_value = models.TextField(blank=True, null=True)
    date_modified = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("business_profile", "tax_year", "form_code")
        verbose_name = "Tax Checklist Item"
        verbose_name_plural = "Tax Checklist Items"
        ordering = ["business_profile", "tax_year", "form_code"]

    def __str__(self):
        return f"{self.business_profile} - {self.tax_year} - {self.form_code} ({self.get_status_display()})"

    @classmethod
    def enabled_for_client_year(cls, business_profile, tax_year):
        return cls.objects.filter(
            business_profile=business_profile, tax_year=tax_year, enabled=True
        )


class ChecklistAttachment(models.Model):
    checklist_item = models.ForeignKey(
        "TaxChecklistItem",
        on_delete=models.CASCADE,
        related_name="checklist_attachments",
    )
    file = models.FileField(upload_to="tax_checklist_attachments/")
    tag = models.CharField(
        max_length=100,
        help_text="Type or description of the document (e.g., W-2, 1099, Receipt)",
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.tag} ({self.file.name})"
