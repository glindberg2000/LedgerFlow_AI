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
from django.utils.html import format_html
from django.shortcuts import render, redirect
from django.urls import path


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
        if not organizer.manifest_hash:
            messages.warning(
                request,
                f"Organizer '{organizer}' is missing manifest hash and cannot be imported.",
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


class AttachManifestForm(forms.Form):
    manifest_file = forms.FileField(label="Manifest JSON file")


@admin.action(description="Attach Manifest JSON to selected organizer (full import)")
def attach_manifest(modeladmin, request, queryset):
    if queryset.count() != 1:
        modeladmin.message_user(
            request,
            "Please select exactly one organizer to attach a manifest.",
            level=messages.WARNING,
        )
        return
    organizer = queryset.first()
    if request.method == "POST":
        form = AttachManifestForm(request.POST, request.FILES)
        if form.is_valid():
            manifest_file = form.cleaned_data["manifest_file"]
            # Save manifest file to original_file (overwrite)
            filename = f"organizer_{organizer.id}_manifest.json"
            organizer.original_file.save(
                filename, ContentFile(manifest_file.read()), save=False
            )
            manifest_file.seek(0)
            try:
                manifest = json.load(manifest_file)
                organizer.manifest_hash = manifest.get("file_hash")
                organizer.manifest_file_summary = manifest.get("file_summary")
                if "pages" in manifest:
                    organizer.manifest_page_count = len(manifest["pages"])
                elif "items" in manifest:
                    organizer.manifest_page_count = len(manifest["items"])
                else:
                    organizer.manifest_page_count = None
                organizer.status = "manifest_ready"
                organizer.save()
                # Immediately import manifest to checklist (same as PDF flow)
                try:
                    ingest_cmd = IngestManifestCommand()
                    ingest_cmd.handle(
                        manifest=organizer.original_file.path,
                        tax_year=organizer.tax_year.year,
                        client_id=organizer.business_profile.client_id,
                        organizer_workbook_id=organizer.id,
                        manifest_hash=organizer.manifest_hash,
                        overwrite=True,
                    )
                    organizer.status = "checklist_created"
                    organizer.save()
                    modeladmin.message_user(
                        request,
                        f"Manifest attached, fields updated, and checklist imported for organizer '{organizer}'.",
                    )
                except Exception as e:
                    modeladmin.message_user(
                        request,
                        f"Manifest attached but failed to import checklist: {e}",
                        level=messages.ERROR,
                    )
                return
            except Exception as e:
                modeladmin.message_user(
                    request, f"Failed to attach manifest: {e}", level=messages.ERROR
                )
    else:
        form = AttachManifestForm()
    context = {
        "form": form,
        "organizer": organizer,
        "title": "Attach Manifest to Organizer",
    }
    return render(request, "admin/attach_manifest.html", context)


@admin.register(OrganizerWorkbook)
class OrganizerWorkbookAdmin(admin.ModelAdmin):
    def get_binder_name(self, obj):
        if obj.tax_year:
            return str(obj.tax_year)
        return f"Binder for Organizer {obj.id}"

    get_binder_name.short_description = "Binder (Client – Year)"
    get_binder_name.admin_order_field = "tax_year__year"

    list_display = (
        "get_binder_name",  # Show binder name (company + year)
        "id",
        "title",
        "upload_date",
        "status",
        "manifest_hash",
        "manifest_page_count",
        "manifest_file_summary",
    )
    list_display_links = ("get_binder_name",)  # Make binder name clickable
    list_filter = ["status", "upload_date"]
    search_fields = ["title", "business_profile__name"]
    readonly_fields = [
        "business_profile",
        "tax_year",
        "title",
        "original_file",
        "upload_date",
        "status",
        "manifest_hash",
        "manifest_page_count",
        "manifest_file_summary",
        "binder_items_status",
        "binder_items_link",
    ]
    actions = [
        delete_all_checklist_items,
        import_manifest_to_checklist,
        "create_extraction_task",
        attach_manifest,
    ]

    def get_fieldsets(self, request, obj=None):
        if obj is None:
            # On creation: show tax_year, title, original_file
            return ((None, {"fields": ("tax_year", "title", "original_file")}),)
        # On change: show all as read-only
        return (
            (
                None,
                {"fields": ("business_profile", "tax_year", "title", "original_file")},
            ),
            (
                "Status & Metadata",
                {
                    "fields": (
                        "upload_date",
                        "status",
                        "manifest_hash",
                        "manifest_page_count",
                        "manifest_file_summary",
                        "binder_items_status",
                        "binder_items_link",
                    )
                },
            ),
        )

    def get_readonly_fields(self, request, obj=None):
        if obj is None:
            # On creation, nothing is read-only
            return []
        return self.readonly_fields

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # Only hide on change, not add
        if obj is not None:
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

    def binder_items_status(self, obj):
        if obj.status == "checklist_created":
            return format_html(
                '<span style="color:green;font-weight:bold;">Binder Items imported</span>'
            )
        elif obj.status == "manifest_ready":
            return format_html(
                '<span style="color:orange;">Manifest uploaded, not yet imported to Binder Items</span>'
            )
        else:
            return format_html('<span style="color:gray;">Not processed</span>')

    binder_items_status.short_description = "Binder Items Import Status"

    def binder_items_link(self, obj):
        if not obj.pk or obj.status != "checklist_created":
            return ""
        url = f"/admin/profiles/binderitem/?organizer_workbook__id__exact={obj.pk}"
        return format_html(
            '<a href="{}" target="_blank" class="button" style="font-size:1.1em;padding:8px 18px;background:#2d6cdf;color:white;border-radius:5px;text-decoration:none;">View Binder Items for This Workbook</a>',
            url,
        )

    binder_items_link.short_description = "Binder Items for This Workbook"

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
