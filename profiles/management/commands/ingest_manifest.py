from django.core.management.base import BaseCommand
from profiles.models import BusinessProfile, TaxYear, BinderItem, BinderItemField
import json
import os
from django.db import transaction
from django.core.exceptions import FieldDoesNotExist
from organizers.models import OrganizerWorkbook
from profiles.utils.utils import ingest_manifest_to_organizer


class Command(BaseCommand):
    help = "Ingest a manifest JSON and create BinderItems and BinderItemFields for a client and tax year."

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "--delete-existing",
            action="store_true",
            help="Delete all BinderItems for this binder before ingesting",
        )
        parser.add_argument(
            "--manifest", type=str, required=True, help="Path to manifest JSON file"
        )
        parser.add_argument(
            "--client_id",
            type=str,
            required=True,
            help="Client ID (BusinessProfile.client_id)",
        )
        parser.add_argument(
            "--tax_year", type=str, required=True, help="Tax year (e.g., 2023)"
        )
        parser.add_argument(
            "--organizer-workbook-id",
            type=int,
            help="ID of OrganizerWorkbook to link items to",
        )
        parser.add_argument("--manifest-hash", type=str, help="Hash of the manifest")
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="Delete all BinderItems for this organizer before ingesting",
        )

    def handle(self, *args, **options):
        manifest_path = options["manifest"]
        client_id = options["client_id"]
        tax_year = options["tax_year"]

        if not os.path.exists(manifest_path):
            self.stderr.write(
                self.style.ERROR(f"Manifest file not found: {manifest_path}")
            )
            return

        try:
            client = BusinessProfile.objects.get(client_id=client_id)
        except BusinessProfile.DoesNotExist:
            self.stderr.write(
                self.style.ERROR(f"No BusinessProfile found for client_id={client_id}")
            )
            return

        with open(manifest_path, "r") as f:
            manifest = json.load(f)
        manifest_title = manifest.get("Title")
        manifest_summary = manifest.get("file_summary")
        manifest_tax_year = manifest.get("Tax_Year")

        tax_year = (
            str(manifest_tax_year)
            if manifest_tax_year
            else str(options.get("tax_year"))
        )

        try:
            binder = TaxYear.objects.get(business_profile=client, year=tax_year)
        except TaxYear.DoesNotExist:
            self.stderr.write(
                self.style.ERROR(
                    f"No TaxYear found for client_id={client_id}, year={tax_year}"
                )
            )
            return

        organizer_workbook = None
        if options.get("organizer_workbook_id"):
            from organizers.models import OrganizerWorkbook

            try:
                organizer_workbook = OrganizerWorkbook.objects.get(
                    id=options["organizer_workbook_id"]
                )
            except OrganizerWorkbook.DoesNotExist:
                self.stderr.write(
                    self.style.ERROR(
                        f"OrganizerWorkbook with id={options['organizer_workbook_id']} does not exist. Aborting."
                    )
                )
                return
        else:
            self.stderr.write(
                self.style.ERROR("No organizer_workbook_id provided. Aborting.")
            )
            return
        manifest_hash = options.get("manifest_hash")
        if options.get("overwrite") and organizer_workbook:
            BinderItem.objects.filter(
                tax_year=binder, organizer_workbook=organizer_workbook
            ).delete()

        try:
            result = ingest_manifest_to_organizer(
                manifest=manifest,
                organizer_workbook=organizer_workbook,
                binder=binder,
                business_profile=client,
                manifest_hash=manifest_hash,
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"Ingest complete: {result['created']} BinderItems created, {result['updated']} updated, {result['field_created']} fields created, {result['field_updated']} fields updated."
                )
            )
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Failed to ingest manifest: {e}"))
