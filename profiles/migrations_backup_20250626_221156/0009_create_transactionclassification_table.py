from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("profiles", "0008_transaction_transaction_id"),
    ]

    operations = [
        migrations.CreateModel(
            name="TransactionClassification",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "classification_type",
                    models.CharField(
                        max_length=50,
                        help_text="Type of classification (e.g., 'business', 'personal')",
                    ),
                ),
                (
                    "worksheet",
                    models.CharField(
                        max_length=50,
                        help_text="Tax worksheet category (e.g., '6A', 'Auto', 'HomeOffice')",
                    ),
                ),
                (
                    "category",
                    models.CharField(
                        max_length=255,
                        blank=True,
                        null=True,
                        help_text="Specific expense category within the worksheet",
                    ),
                ),
                (
                    "business_percentage",
                    models.IntegerField(
                        default=100,
                        help_text="Percentage of the transaction that is business-related",
                    ),
                ),
                (
                    "confidence",
                    models.CharField(
                        max_length=20,
                        help_text="Confidence level of the classification",
                    ),
                ),
                (
                    "reasoning",
                    models.TextField(
                        help_text="Explanation for the classification decision"
                    ),
                ),
                (
                    "created_by",
                    models.CharField(
                        max_length=100,
                        help_text="Agent or user who created this classification",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "is_active",
                    models.BooleanField(
                        default=True,
                        help_text="Whether this is the current active classification",
                    ),
                ),
                (
                    "transaction",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="classifications",
                        to="profiles.transaction",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(
                        fields=["transaction", "created_at"],
                        name="transactionclassification_transaction_createdat_idx",
                    ),
                    models.Index(
                        fields=["transaction", "is_active"],
                        name="transactionclassification_transaction_isactive_idx",
                    ),
                    models.Index(
                        fields=["classification_type"],
                        name="transactionclassification_type_idx",
                    ),
                    models.Index(
                        fields=["worksheet"],
                        name="transactionclassification_worksheet_idx",
                    ),
                ],
            },
        ),
    ]
