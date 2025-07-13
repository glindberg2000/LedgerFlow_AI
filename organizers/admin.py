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
from .forms import OrganizerWorkbookForm
from django import forms


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


@admin.action(description="Import Manifest to Checklist (overwrite existing items)")
def import_manifest_to_checklist(modeladmin, request, queryset):
    count = 0
    for organizer in queryset:
        if organizer.status != "manifest_ready" or not organizer.manifest_hash:
            messages.warning(
                request,
                f"Organizer '{organizer}' is not ready for manifest import or missing hash.",
            )
            continue
        # Delete previous BinderItems for this organizer
        BinderItem.objects.filter(organizer_workbook=organizer).delete()
        # Ingest manifest
        manifest_path = organizer.original_file.path
        try:
            ingest_cmd = IngestManifestCommand()
            ingest_cmd.handle(
                manifest=manifest_path,
                tax_year=organizer.title,
                client_id=organizer.business_profile.client_id,  # <-- fix: pass client_id
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
    form = OrganizerWorkbookForm
    list_display = (
        "title",
        "business_profile",
        "upload_date",
        "status",
        "manifest_hash",
        "manifest_page_count",
        "short_manifest_summary",
    )
    list_filter = ["status", "upload_date"]
    search_fields = ["title", "business_profile__name"]
    readonly_fields = [
        "upload_date",
        "status",
        "manifest_hash",
        "manifest_page_count",
        "manifest_file_summary",
    ]
    inlines = [OrganizerOutputInline]
    actions = [delete_all_checklist_items, import_manifest_to_checklist]

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # Hide business_profile and tax_year fields if present
        if "business_profile" in form.base_fields:
            form.base_fields["business_profile"].widget = forms.HiddenInput()
        if "tax_year" in form.base_fields:
            form.base_fields["tax_year"].widget = forms.HiddenInput()
        return form

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

    def short_manifest_summary(self, obj):
        if obj.manifest_file_summary:
            return obj.manifest_file_summary[:80] + (
                "..." if len(obj.manifest_file_summary) > 80 else ""
            )
        return ""

    short_manifest_summary.short_description = "Manifest Summary"

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
