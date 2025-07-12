from django.contrib import admin
from .models import OrganizerWorkbook, OrganizerOutput
from profiles.models import ProcessingTask
from django.urls import path
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.contrib import messages
from profiles.management.commands.ingest_manifest import (
    Command as IngestManifestCommand,
)
from profiles.models import BinderItem
import os
import json
from django.core.files.base import ContentFile
from django.utils.html import format_html


class OrganizerOutputInline(admin.TabularInline):
    model = OrganizerOutput
    extra = 0
    readonly_fields = ["output_type", "file", "page_number", "created_at"]
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


class OrganizerAdminSite(admin.AdminSite):
    site_header = "LedgerFlow Organizer Admin"
    site_title = "LedgerFlow Organizer Admin"
    index_title = "Organizer Administration"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "organizer-upload/",
                self.admin_view(self.organizer_upload_redirect),
                name="organizer_upload_link",
            ),
        ]
        return custom_urls + urls

    def organizer_upload_redirect(self, request):
        return HttpResponseRedirect(reverse("organizer_workbook_upload"))


@admin.action(description="Delete all checklist items for selected organizers")
def delete_all_checklist_items(modeladmin, request, queryset):
    count = 0
    for organizer in queryset:
        deleted, _ = BinderItem.objects.filter(organizer_workbook=organizer).delete()
        count += deleted
    messages.success(
        request, f"Deleted {count} checklist items for selected organizers."
    )


@admin.action(
    description="Import Manifest to Checklist (auto-create/update Binder and BinderItems)"
)
def import_manifest_to_checklist(modeladmin, request, queryset):
    import json
    from profiles.models import TaxYear, BinderItem
    from django.db import transaction

    count = 0
    for organizer in queryset:
        if organizer.status != "manifest_ready" or not organizer.manifest_hash:
            messages.warning(
                request,
                f"Organizer '{organizer}' is not ready for manifest import or missing hash.",
            )
            continue
        # Read manifest and extract tax year
        manifest_path = organizer.original_file.path
        try:
            with open(manifest_path, "r") as f:
                manifest_data = json.load(f)
            # Try to extract tax year from cover sheet
            tax_year = None
            for page in manifest_data.get("pages", []):
                data = page.get("data", {})
                if isinstance(data, dict) and "tax_year" in data:
                    tax_year = str(data["tax_year"]).strip()
                    break
            if not tax_year:
                messages.error(
                    request,
                    f"No tax year found in manifest for '{organizer}'. Aborting.",
                )
                continue
            # Look up or create Binder (TaxYear)
            client = organizer.business_profile
            binder, created = TaxYear.objects.get_or_create(
                business_profile=client,
                year=tax_year,
                defaults={"status": "not_started"},
            )
            if created:
                messages.info(
                    request, f"Created new Binder (TaxYear) {tax_year} for {client}."
                )
            # Link organizer to binder if not already (and save immediately)
            if organizer.tax_year != binder:
                organizer.tax_year = binder
                organizer.save()
            # Warn if overwriting existing BinderItems
            existing_items = BinderItem.objects.filter(
                tax_year=binder, organizer_workbook=organizer
            )
            if existing_items.exists():
                messages.warning(
                    request,
                    f"Overwriting {existing_items.count()} existing BinderItems for '{organizer}'.",
                )
                existing_items.delete()
            # Ingest manifest and create BinderItems
            ingest_cmd = IngestManifestCommand()
            ingest_cmd.handle(
                manifest=manifest_path,
                tax_year=tax_year,
                client_id=client.client_id,
                organizer_workbook_id=organizer.id,
                manifest_hash=organizer.manifest_hash,
                overwrite=True,
            )
            organizer.status = "checklist_created"
            organizer.save()
            count += 1
        except Exception as e:
            messages.error(request, f"Failed to import manifest for '{organizer}': {e}")
    if count:
        messages.success(
            request,
            f"Imported manifest and created checklist for {count} organizer(s).",
        )


@admin.register(OrganizerWorkbook)
class OrganizerWorkbookAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "business_profile",
        "tax_year",
        "upload_date",
        "status",
        "manifest_page_count",
        "short_manifest_summary",
        "short_manifest_hash",
    )
    list_filter = ["status", "upload_date"]
    search_fields = ["title", "business_profile__name"]
    readonly_fields = (
        "manifest_hash",
        "manifest_page_count",
        "manifest_file_summary",
    )
    inlines = [OrganizerOutputInline]
    actions = [delete_all_checklist_items, import_manifest_to_checklist]

    def create_extraction_task(self, request, queryset):
        created = 0
        for workbook in queryset:
            # Avoid duplicate tasks for the same workbook
            if not ProcessingTask.objects.filter(
                task_type="organizer_extraction",
                client=workbook.business_profile,
                task_metadata__workbook_id=workbook.id,
            ).exists():
                ProcessingTask.objects.create(
                    task_type="organizer_extraction",
                    client=workbook.business_profile,
                    transaction_count=1,
                    status="pending",
                    task_metadata={
                        "workbook_id": workbook.id,
                        "file": workbook.original_file.name,
                    },
                )
                created += 1
        self.message_user(
            request, f"Created {created} extraction task(s) for selected workbook(s)."
        )

    create_extraction_task.short_description = (
        "Create Extraction Task for selected workbooks"
    )

    def short_manifest_hash(self, obj):
        if obj.manifest_hash:
            return format_html(
                '<span title="{}">{}...</span>',
                obj.manifest_hash,
                obj.manifest_hash[:8],
            )
        return ""

    short_manifest_hash.short_description = "Manifest Hash"
    short_manifest_hash.admin_order_field = "manifest_hash"

    def short_manifest_summary(self, obj):
        if obj.manifest_file_summary:
            short = obj.manifest_file_summary[:60].replace("\n", " ")
            return format_html(
                '<span title="{}">{}</span>',
                obj.manifest_file_summary,
                short + ("..." if len(obj.manifest_file_summary) > 60 else ""),
            )
        return ""

    short_manifest_summary.short_description = "Manifest Summary"
    short_manifest_summary.admin_order_field = "manifest_file_summary"

    def save_model(self, request, obj, form, change):
        file = form.cleaned_data.get("original_file")
        if file and file.name.lower().endswith(".json"):
            # Read the uploaded file into memory
            file.seek(0)
            manifest_bytes = file.read()
            try:
                manifest_data = json.loads(manifest_bytes.decode("utf-8"))
            except Exception:
                manifest_data = None
            if manifest_data:
                obj.manifest_hash = manifest_data.get("file_hash")
                obj.manifest_file_summary = manifest_data.get("file_summary")
                # Try to get page count from manifest structure
                if "pages" in manifest_data:
                    obj.manifest_page_count = len(manifest_data["pages"])
                elif "items" in manifest_data:
                    obj.manifest_page_count = len(manifest_data["items"])
                else:
                    obj.manifest_page_count = None
                obj.status = "manifest_ready"
            else:
                obj.manifest_hash = None
                obj.manifest_file_summary = None
                obj.manifest_page_count = None
                obj.status = "pending"
            # Rewind file pointer for model save
            file.seek(0)
        super().save_model(request, obj, form, change)
