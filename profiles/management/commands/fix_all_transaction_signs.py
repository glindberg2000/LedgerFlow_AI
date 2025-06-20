from django.core.management.base import BaseCommand
from profiles.models import Transaction
from django.db.models import Q


class Command(BaseCommand):
    help = "Comprehensive script to normalize all historical transaction signs."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simulates the command without making changes to the database.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        self.stdout.write(
            self.style.NOTICE(
                "Starting comprehensive transaction sign normalization..."
            )
        )

        if dry_run:
            self.stdout.write(
                self.style.WARNING("Dry run mode enabled. No changes will be saved.")
            )

        # Define keywords for transaction types that should always be negative
        EXPENSE_TYPES = [
            "purchase",
            "fee",
            "debit",
            "withdrawal",
            "charge",
            "payment",
            "service charge",
        ]

        # Define keywords for transaction types that should always be positive
        INCOME_TYPES = [
            "credit",
            "refund",
            "return",
            "deposit",
            "interest credit",
            "interest payment",
        ]

        # --- Query for positive expenses ---
        positive_expense_query = Q()
        for t_type in EXPENSE_TYPES:
            positive_expense_query |= Q(transaction_type__iexact=t_type)

        transactions_to_fix_positive = Transaction.objects.filter(
            positive_expense_query, amount__gt=0
        )

        # --- Query for negative income ---
        negative_income_query = Q()
        for t_type in INCOME_TYPES:
            negative_income_query |= Q(transaction_type__iexact=t_type)

        transactions_to_fix_negative = Transaction.objects.filter(
            negative_income_query, amount__lt=0
        )

        # --- Report and Fix Positive Expenses ---
        updated_count = 0
        if transactions_to_fix_positive.exists():
            self.stdout.write(self.style.WARNING("\\nFound positive expenses to fix:"))
            for tx in transactions_to_fix_positive:
                new_amount = -tx.amount
                self.stdout.write(
                    f"  - [WOULD CHANGE] ID: {tx.id}, Type: {tx.transaction_type}, "
                    f"Source: {tx.source}, Original: {tx.amount}, New: {new_amount}"
                )
                if not dry_run:
                    tx.amount = new_amount
                    tx.save()
                    updated_count += 1

        # --- Report and Fix Negative Income ---
        if transactions_to_fix_negative.exists():
            self.stdout.write(self.style.WARNING("\\nFound negative income to fix:"))
            for tx in transactions_to_fix_negative:
                new_amount = -tx.amount
                self.stdout.write(
                    f"  - [WOULD CHANGE] ID: {tx.id}, Type: {tx.transaction_type}, "
                    f"Source: {tx.source}, Original: {tx.amount}, New: {new_amount}"
                )
                if not dry_run:
                    tx.amount = new_amount
                    tx.save()
                    updated_count += 1

        if dry_run:
            total_to_fix = (
                transactions_to_fix_positive.count()
                + transactions_to_fix_negative.count()
            )
            if total_to_fix > 0:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"\\nDry run complete. Found {total_to_fix} transactions to fix."
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS("\\nDry run complete. No inconsistencies found.")
                )
        else:
            if updated_count > 0:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"\\nSuccessfully updated {updated_count} transactions."
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS("\\nNo transactions needed fixing.")
                )
