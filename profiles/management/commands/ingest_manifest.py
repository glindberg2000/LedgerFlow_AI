from django.core.management.base import BaseCommand
from profiles.models import BusinessProfile, TaxYear, BinderItem, BinderItemField
import json
import os
from django.db import transaction
from django.core.exceptions import FieldDoesNotExist
from organizers.models import OrganizerWorkbook


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

        if options.get("delete_existing"):
            BinderItem.objects.filter(tax_year=tax_year).delete()

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
            # Delete all BinderItems for this binder and organizer_workbook
            BinderItem.objects.filter(
                tax_year=binder, organizer_workbook=organizer_workbook
            ).delete()

        with transaction.atomic():
            # --- BEGIN: Workflow mapping config ---
            # Example: Map form_id or label to action_type and related fields
            CALCULATED_REPORTS = {
                "6A": {"action_type": "calculated", "calculated_by_report": "6A"},
                "6A Worksheet": {
                    "action_type": "calculated",
                    "calculated_by_report": "6A",
                },
            }
            UPLOAD_DOCS = {
                "W2": {"action_type": "upload", "required_document_type": "W2"},
                "1099": {"action_type": "upload", "required_document_type": "1099"},
            }
            INFO_ONLY_PAGES = {
                "Cover_Sheet": {"action_type": "info_only"},
                "Mail/Presentation Sheet": {"action_type": "info_only"},
            }
            IGNORED_PAGES = {
                "Sample_Page": {"action_type": "ignore"},
            }
            # --- END: Workflow mapping config ---
            # Always use the business_profile from OrganizerWorkbook or the client argument
            if organizer_workbook:
                business_profile = organizer_workbook.business_profile
            else:
                business_profile = client
            # (Removed fallback logic that tried to get client_id from manifest)

            for idx, page in enumerate(pages):
                form_id = page.get("label")
                label = page.get("Title") or form_id
                # Ensure label is a short string (max 255 chars)
                if label and len(label) > 255:
                    label = label[:252] + "..."
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
                # --- BEGIN: Set workflow fields ---
                # Defaults
                action_type = "manual"
                calculated_by_report = None
                required_document_type = None
                source = "Organizer"
                # Check for calculated reports
                mapping = CALCULATED_REPORTS.get(form_id) or CALCULATED_REPORTS.get(
                    label
                )
                if mapping:
                    action_type = mapping.get("action_type", action_type)
                    calculated_by_report = mapping.get("calculated_by_report")
                    source = "Report"
                # Check for upload docs
                mapping = UPLOAD_DOCS.get(form_id) or UPLOAD_DOCS.get(label)
                if mapping:
                    action_type = mapping.get("action_type", action_type)
                    required_document_type = mapping.get("required_document_type")
                    source = "Upload"
                # --- END: Set workflow fields ---
                # Determine action_type and display_in_checklist
                display_in_checklist = True
                if form_id in INFO_ONLY_PAGES or label in INFO_ONLY_PAGES:
                    action_type = "info_only"
                    display_in_checklist = False
                elif form_id in IGNORED_PAGES or label in IGNORED_PAGES:
                    action_type = "ignore"
                    display_in_checklist = False
                if not form_id:
                    self.stderr.write(
                        self.style.WARNING(f"Page {idx+1} missing 'label', skipping.")
                    )
                    continue
                # Use both tax_year and organizer_workbook for uniqueness
                binder_item, created = BinderItem.objects.get_or_create(
                    tax_year=binder,
                    organizer_workbook=organizer_workbook,
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
                        # New workflow fields
                        "action_type": action_type,
                        "calculated_by_report": calculated_by_report,
                        "required_document_type": required_document_type,
                        "source": source,
                        "display_in_checklist": display_in_checklist,
                        "manifest_hash": manifest_hash,
                    },
                )
                updated = False
                # Always update all fields from manifest for existing items
                for field, value in [
                    ("label", label),
                    ("notes", notes),
                    ("page_number", page_number),
                    ("thumbnail_file", thumbnail_file),
                    ("pdf_page_file", pdf_page_file),
                    ("has_user_data", has_user_data),
                    # New workflow fields
                    ("action_type", action_type),
                    ("calculated_by_report", calculated_by_report),
                    ("required_document_type", required_document_type),
                    ("source", source),
                    ("display_in_checklist", display_in_checklist),
                    ("manifest_hash", manifest_hash),
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
                # Always ensure correct linkage
                if binder_item.tax_year != binder:
                    binder_item.tax_year = binder
                    updated = True
                if binder_item.organizer_workbook != organizer_workbook:
                    binder_item.organizer_workbook = organizer_workbook
                    updated = True
                if (
                    business_profile
                    and getattr(binder_item, "business_profile", None)
                    != business_profile
                ):
                    binder_item.business_profile = business_profile
                    updated = True
                if updated:
                    binder_item.save()
                    updated_count += 1
                elif created:
                    if has_user_data:
                        created_count += 1
                    binder_item.save()
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
                    # Ensure field_label is not too long
                    if len(field_label) > 255:
                        field_label = field_label[:252] + "..."
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
