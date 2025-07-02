from django.core.management.base import BaseCommand
from profiles.models import BusinessProfile, TaxChecklistItem
import json
import os
from django.conf import settings

CHECKLIST_PATH = os.path.join(
    settings.BASE_DIR, "profiles", "bootstrap", "tax_checklist_index.json"
)


class Command(BaseCommand):
    help = "Initialize TaxChecklistItem entries for a client and tax year from the canonical checklist index. Only 6A is enabled by default."

    def add_arguments(self, parser):
        parser.add_argument(
            "--client_id",
            type=str,
            required=True,
            help="Client ID (BusinessProfile.client_id)",
        )
        parser.add_argument(
            "--tax_year", type=str, required=True, help="Tax year (e.g., 2023)"
        )

    def handle(self, *args, **options):
        client_id = options["client_id"]
        tax_year = options["tax_year"]
        try:
            client = BusinessProfile.objects.get(client_id=client_id)
        except BusinessProfile.DoesNotExist:
            self.stderr.write(
                self.style.ERROR(f"No BusinessProfile found for client_id={client_id}")
            )
            return

        with open(CHECKLIST_PATH, "r") as f:
            checklist = json.load(f)

        created = 0
        skipped = 0
        for form_code, meta in checklist.items():
            enabled = True if form_code == "6A" else False
            obj, was_created = TaxChecklistItem.objects.get_or_create(
                business_profile=client,
                tax_year=tax_year,
                form_code=form_code,
                defaults={
                    "enabled": enabled,
                    "status": "not_started",
                    "notes": f"{meta.get('label', '')} | Topic: {meta.get('topic', '')} | Entry type: {meta.get('entry_type', '')}",
                },
            )
            if was_created:
                created += 1
            else:
                skipped += 1
        self.stdout.write(
            self.style.SUCCESS(
                f"Checklist initialized for {client} ({tax_year}): {created} created, {skipped} skipped. Only 6A enabled by default."
            )
        )
