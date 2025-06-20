from django.core.management.base import BaseCommand
from django.db.models import Q
from profiles.models import Transaction


class Command(BaseCommand):
    help = "Corrects the sign for historical Apple Card transactions where purchases were stored as positive amounts."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simulates the command without making changes to the database.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        self.stdout.write(
            self.style.NOTICE("Starting Apple Card transaction sign correction...")
        )

        if dry_run:
            self.stdout.write(
                self.style.WARNING("Dry run mode enabled. No changes will be saved.")
            )

        # We are looking for Apple Card purchases that are incorrectly stored as positive values.
        # We also want to avoid accidentally flipping any payments or refunds.
        # We will assume that any "purchase" type with a positive amount is incorrect.
        transactions_to_fix = Transaction.objects.filter(
            source="apple_card_csv",
            amount__gt=0,  # Amount is positive
            transaction_type__iexact="purchase",  # Type is 'purchase'
        )

        update_count = transactions_to_fix.count()
        self.stdout.write(f"Found {update_count} Apple Card transactions to normalize.")

        if dry_run:
            for tx in transactions_to_fix:
                self.stdout.write(
                    f"  - [WOULD CHANGE] ID: {tx.id}, Date: {tx.transaction_date}, Type: {tx.transaction_type}, Original: {tx.amount}, New: {-tx.amount}"
                )
        else:
            updated_transactions = []
            for tx in transactions_to_fix:
                tx.amount = -tx.amount
                updated_transactions.append(tx)
                self.stdout.write(
                    f"  - [CHANGED] ID: {tx.id}, Date: {tx.transaction_date}, Type: {tx.transaction_type}, Original: {-tx.amount}, New: {tx.amount}"
                )

            if updated_transactions:
                Transaction.objects.bulk_update(updated_transactions, ["amount"])
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Successfully updated {len(updated_transactions)} transactions."
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS("No transactions needed updating.")
                )

        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Dry run complete. Would have updated {update_count} transactions."
                )
            )
        else:
            self.stdout.write(self.style.SUCCESS("Normalization complete."))
