from django.db import models
from django.db.models import JSONField
import uuid
import importlib.util
import os
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
import hashlib

# Create your models here.


class BusinessProfile(models.Model):
    client_id = models.CharField(max_length=255, primary_key=True)
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
        return f"Business Profile for client {self.client_id}"


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
        max_length=20,
        choices=[
            ("AI", "AI Only"),
            ("AI+Search", "AI with Search"),
            ("Human", "Human Override"),
            ("None", "Not Processed"),  # Added this choice
        ],
        default=None,  # Changed from "AI" to None
        help_text="Method used to extract the payee information",
    )
    classification_method = models.CharField(
        max_length=20,
        choices=[
            ("AI", "AI Only"),
            ("Human", "Human Override"),
            ("None", "Not Processed"),
        ],
        default=None,
        help_text="Method used to classify the transaction",
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
        "Transaction", related_name="processing_tasks"
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
    file = models.FileField(upload_to="clients/%Y/%m/%d/")
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
    transactions = models.ManyToManyField(
        "Transaction", related_name="source_files", blank=True
    )
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

    class Meta:
        ordering = ["-upload_timestamp"]
        verbose_name = "Statement File"
        verbose_name_plural = "Statement Files"
        constraints = [
            models.UniqueConstraint(
                fields=["client", "statement_hash"], name="unique_client_statement_hash"
            )
        ]

    def __str__(self):
        return f"{self.client} - {self.original_filename} ({self.status})"

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

    # For extensibility: add batch_id, progress, etc. as needed for batch uploads
