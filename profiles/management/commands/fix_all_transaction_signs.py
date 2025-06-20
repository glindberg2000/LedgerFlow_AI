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
            "service",
            "merchandise",
            "goods",
            "order",
        ]

        # Define keywords for transaction types that should always be positive
        INCOME_TYPES = ["credit", "refund", "deposit", "return", "payment received"]
        INCOME_KEYWORDS_DESC = [
            "ach credit",
            "deposit",
            "refund",
            "reversal",
            "return",
        ]  # Keywords to find in description

        # Build Q objects for querying
        expense_q = Q()
        for etype in EXPENSE_TYPES:
            expense_q |= Q(transaction_type__iexact=etype)

        income_q = Q()
        for itype in INCOME_TYPES:
            income_q |= Q(transaction_type__iexact=itype)

        # Add description keywords to the income query
        for keyword in INCOME_KEYWORDS_DESC:
            income_q |= Q(description__icontains=keyword)

        # Find positive expenses to fix
        positive_expenses = Transaction.objects.filter(expense_q & Q(amount__gt=0))

        # Find negative income/credits to fix
        negative_income = Transaction.objects.filter(income_q & Q(amount__lt=0))

        updated_transactions = []

        # --- Report and Fix Positive Expenses ---
        updated_count = 0
        if positive_expenses.exists():
            self.stdout.write(self.style.WARNING("\\nFound positive expenses to fix:"))
            for tx in positive_expenses:
                new_amount = -tx.amount
                self.stdout.write(
                    f"  - [WOULD CHANGE] ID: {tx.id}, Type: {tx.transaction_type}, "
                    f"Source: {tx.source}, Original: {tx.amount}, New: {new_amount}"
                )
                if not dry_run:
                    tx.amount = new_amount
                    tx.save()
                    updated_count += 1
                    updated_transactions.append(tx)

        # --- Report and Fix Negative Income ---
        if negative_income.exists():
            self.stdout.write(self.style.WARNING("\\nFound negative income to fix:"))
            for tx in negative_income:
                new_amount = -tx.amount
                self.stdout.write(
                    f"  - [WOULD CHANGE] ID: {tx.id}, Type: {tx.transaction_type}, "
                    f"Source: {tx.source}, Original: {tx.amount}, New: {new_amount}"
                )
                if not dry_run:
                    tx.amount = new_amount
                    tx.save()
                    updated_count += 1
                    updated_transactions.append(tx)

        if dry_run:
            total_to_fix = positive_expenses.count() + negative_income.count()
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
