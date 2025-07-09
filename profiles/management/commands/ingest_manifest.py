from django.core.management.base import BaseCommand
from profiles.models import BusinessProfile, TaxYear, BinderItem, BinderItemField
import json
import os
from django.db import transaction
from django.core.exceptions import FieldDoesNotExist


class Command(BaseCommand):
    help = "Ingest a manifest JSON and create BinderItems and BinderItemFields for a client and tax year."

    def add_arguments(self, parser):
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

        try:
            binder = TaxYear.objects.get(business_profile=client, year=tax_year)
        except TaxYear.DoesNotExist:
            self.stderr.write(
                self.style.ERROR(
                    f"No TaxYear found for client_id={client_id}, year={tax_year}"
                )
            )
            return

        with open(manifest_path, "r") as f:
            manifest = json.load(f)

        pages = manifest.get("pages", [])
        created_count = 0
        updated_count = 0
        field_created = 0
        field_updated = 0

        # Set the subdirectory for media files
        media_subdir = "organizers/outputs/4/"

        with transaction.atomic():
            for idx, page in enumerate(pages):
                form_id = page.get("label")
                label = page.get("Title") or form_id
                notes = page.get("summary", "")
                page_number = page.get("page_number")
                # Fix media file paths
                thumbnail_file = page.get("thumbnail_file")
                if thumbnail_file and not (
                    "/" in thumbnail_file or thumbnail_file.startswith(media_subdir)
                ):
                    thumbnail_file = media_subdir + thumbnail_file
                pdf_page_file = page.get("pdf_page_file")
                if pdf_page_file and not (
                    "/" in pdf_page_file or pdf_page_file.startswith(media_subdir)
                ):
                    pdf_page_file = media_subdir + pdf_page_file
                has_user_data = page.get("has_user_data", False)
                if not form_id:
                    self.stderr.write(
                        self.style.WARNING(f"Page {idx+1} missing 'label', skipping.")
                    )
                    continue
                binder_item, created = BinderItem.objects.get_or_create(
                    tax_year=binder,
                    form_id=form_id,
                    defaults={
                        "type": "form",
                        "label": label,
                        "status": "not_started",
                        "order": idx + 1,
                        "is_generated": True,
                        "notes": notes,
                        "page_number": page_number,
                        "thumbnail_file": thumbnail_file,
                        "pdf_page_file": pdf_page_file,
                        "has_user_data": has_user_data,
                    },
                )
                updated = False
                if not created:
                    # Update fields if changed
                    for field, value in [
                        ("label", label),
                        ("notes", notes),
                        ("page_number", page_number),
                        ("thumbnail_file", thumbnail_file),
                        ("pdf_page_file", pdf_page_file),
                        ("has_user_data", has_user_data),
                    ]:
                        try:
                            if (
                                hasattr(binder_item, field)
                                and getattr(binder_item, field) != value
                            ):
                                setattr(binder_item, field, value)
                                updated = True
                        except FieldDoesNotExist:
                            continue
                    if updated:
                        binder_item.save()
                        updated_count += 1
                else:
                    if has_user_data:
                        created_count += 1
                # Ingest fields (unchanged)
                data = page.get("data", {})
                if isinstance(data, dict):
                    items = data.items()
                elif isinstance(data, list):
                    items = enumerate(data)
                else:
                    items = []
                for field_key, field_value in items:
                    field_label = str(field_key)
                    value_str = (
                        json.dumps(field_value)
                        if isinstance(field_value, (dict, list))
                        else str(field_value)
                    )
                    field_obj, f_created = BinderItemField.objects.get_or_create(
                        binder_item=binder_item,
                        label=field_label,
                        defaults={
                            "value": value_str,
                            "status": "missing",
                            "order": 0,
                            "notes": "",
                        },
                    )
                    if f_created:
                        field_created += 1
                    else:
                        if field_obj.value != value_str:
                            field_obj.value = value_str
                            field_obj.save()
                            field_updated += 1
        self.stdout.write(
            self.style.SUCCESS(
                f"Ingest complete: {created_count} BinderItems created, {updated_count} updated, {field_created} fields created, {field_updated} fields updated."
            )
        )
