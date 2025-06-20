from django.core.management.base import BaseCommand
from django.db.models import Q
from profiles.models import Transaction


class Command(BaseCommand):
    help = "Normalizes transaction amounts to ensure debits are negative and credits are positive."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simulates the command without making changes to the database.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        self.stdout.write(
            self.style.NOTICE("Starting transaction amount normalization...")
        )

        if dry_run:
            self.stdout.write(
                self.style.WARNING("Dry run mode enabled. No changes will be saved.")
            )

        # Find transactions that need their sign flipped
        # 1. Debits that are currently positive
        debits_to_fix = Transaction.objects.filter(
            transaction_type="debit", amount__gt=0
        )

        # 2. Credits that are currently negative
        credits_to_fix = Transaction.objects.filter(
            transaction_type="credit", amount__lt=0
        )

        transactions_to_update = list(debits_to_fix) + list(credits_to_fix)
        update_count = 0

        if not transactions_to_update:
            self.stdout.write(
                self.style.SUCCESS(
                    "All transaction amounts are already normalized. No action needed."
                )
            )
            return

        self.stdout.write(
            f"Found {len(transactions_to_update)} transactions to normalize."
        )

        for tx in transactions_to_update:
            original_amount = tx.amount
            new_amount = -tx.amount
            self.stdout.write(
                f"  - ID: {tx.id}, Date: {tx.transaction_date}, Type: {tx.transaction_type}, "
                f"Original: {original_amount}, New: {new_amount}"
            )
            if not dry_run:
                tx.amount = new_amount
                tx.save(update_fields=["amount"])
            update_count += 1

        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Dry run complete. Would have updated {update_count} transactions."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"Successfully updated {update_count} transactions.")
            )
