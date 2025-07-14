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
from django.utils.safestring import mark_safe
from django.shortcuts import render, redirect
from django.urls import path
from django.template.response import TemplateResponse
import logging
from profiles.utils.utils import ingest_manifest_to_organizer


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
            # Load manifest JSON
            with open(organizer.original_file.path, "r") as f:
                manifest = json.load(f)
            result = ingest_manifest_to_organizer(
                manifest=manifest,
                organizer_workbook=organizer,
                binder=organizer.tax_year,
                business_profile=organizer.business_profile,
                manifest_hash=organizer.manifest_hash,
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
                    with open(organizer.original_file.path, "r") as f:
                        manifest = json.load(f)
                    result = ingest_manifest_to_organizer(
                        manifest=manifest,
                        organizer_workbook=organizer,
                        binder=organizer.tax_year,
                        business_profile=organizer.business_profile,
                        manifest_hash=organizer.manifest_hash,
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


class ManifestUploadForm(forms.Form):
    manifest_file = forms.FileField(label="Manifest JSON file", required=True)


@admin.register(OrganizerWorkbook)
class OrganizerWorkbookAdmin(admin.ModelAdmin):
    def get_binder_name(self, obj):
        if obj.tax_year:
            return str(obj.tax_year)
        return f"Binder for Organizer {obj.id}"

    get_binder_name.short_description = "Binder (Client – Year)"
    get_binder_name.admin_order_field = "tax_year__year"

    list_display = (
        "get_binder_name",  # Binder (Client – Year), clickable
        "tax_year_display",  # Just the year
        "id",
        "title_with_width",
        "upload_date",
        "status",
        "manifest_page_count",
        "manifest_summary_icon",
        "manifest_hash_icon",
    )
    list_display_links = ("get_binder_name",)
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
    ]

    change_form_template = "admin/organizerworkbook/change_form_with_manifest.html"

    def extract_manifest_fields(self, file_obj):
        """Parse manifest JSON and extract hash, page count, summary, and title."""
        logger = logging.getLogger(__name__)
        file_obj.seek(0)
        try:
            manifest = json.load(file_obj)
        except Exception as e:
            logger.error(f"Failed to parse manifest JSON: {e}")
            return None, None, None, None
        manifest_hash = manifest.get("file_hash")
        manifest_summary = manifest.get("file_summary")
        manifest_title = manifest.get("Title")
        if "pages" in manifest:
            manifest_page_count = len(manifest["pages"])
        elif "items" in manifest:
            manifest_page_count = len(manifest["items"])
        else:
            manifest_page_count = None
        if not manifest_hash:
            logger.warning(f"Manifest missing file_hash: {manifest}")
        if manifest_page_count is None:
            logger.warning(f"Manifest missing page count: {manifest}")
        return manifest_hash, manifest_page_count, manifest_summary, manifest_title

    def render_change_form(
        self, request, context, add=False, change=False, form_url="", obj=None
    ):
        # Add manifest upload form to context if editing an existing organizer
        if obj and obj.pk:
            if request.method == "POST" and "manifest_upload" in request.POST:
                manifest_form = ManifestUploadForm(request.POST, request.FILES)
                if manifest_form.is_valid():
                    manifest_file = manifest_form.cleaned_data["manifest_file"]
                    filename = f"organizer_{obj.id}_manifest.json"
                    obj.original_file.save(
                        filename, ContentFile(manifest_file.read()), save=False
                    )
                    # Re-open the file for parsing
                    with open(obj.original_file.path, "r") as f:
                        (
                            manifest_hash,
                            manifest_page_count,
                            manifest_summary,
                            manifest_title,
                        ) = self.extract_manifest_fields(f)
                    obj.manifest_hash = manifest_hash
                    obj.manifest_page_count = manifest_page_count
                    obj.manifest_file_summary = manifest_summary
                    if manifest_title:
                        obj.title = manifest_title
                    obj.status = "manifest_ready"
                    obj.save()
                    # Immediately import manifest to checklist (same as PDF flow)
                    try:
                        with open(obj.original_file.path, "r") as f:
                            manifest = json.load(f)
                        result = ingest_manifest_to_organizer(
                            manifest=manifest,
                            organizer_workbook=obj,
                            binder=obj.tax_year,
                            business_profile=obj.business_profile,
                            manifest_hash=obj.manifest_hash,
                        )
                        obj.status = "checklist_created"
                        obj.save()
                        messages.success(
                            request,
                            f"Manifest uploaded and checklist imported for organizer '{obj}'.",
                        )
                    except Exception as e:
                        messages.error(
                            request,
                            f"Manifest uploaded but failed to import checklist: {e}",
                        )
                else:
                    context["manifest_upload_error"] = "Invalid manifest upload form."
            else:
                manifest_form = ManifestUploadForm()
            context["manifest_upload_form"] = manifest_form
        return super().render_change_form(request, context, add, change, form_url, obj)

    def change_view(self, request, object_id, form_url="", extra_context=None):
        obj = self.get_object(request, object_id)
        manifest_upload_form = ManifestUploadForm()
        if request.method == "POST" and "manifest_upload" in request.POST:
            form = ManifestUploadForm(request.POST, request.FILES)
            if form.is_valid():
                manifest_file = form.cleaned_data["manifest_file"]
                filename = f"organizer_{obj.id}_manifest.json"
                obj.original_file.save(
                    filename, ContentFile(manifest_file.read()), save=False
                )
                # Re-open the file for parsing
                with open(obj.original_file.path, "r") as f:
                    (
                        manifest_hash,
                        manifest_page_count,
                        manifest_summary,
                        manifest_title,
                    ) = self.extract_manifest_fields(f)
                obj.manifest_hash = manifest_hash
                obj.manifest_page_count = manifest_page_count
                obj.manifest_file_summary = manifest_summary
                if manifest_title:
                    obj.title = manifest_title
                obj.status = "manifest_ready"
                obj.save()
                # Immediately import manifest to checklist (same as PDF flow)
                try:
                    with open(obj.original_file.path, "r") as f:
                        manifest = json.load(f)
                    result = ingest_manifest_to_organizer(
                        manifest=manifest,
                        organizer_workbook=obj,
                        binder=obj.tax_year,
                        business_profile=obj.business_profile,
                        manifest_hash=obj.manifest_hash,
                    )
                    obj.status = "checklist_created"
                    obj.save()
                    self.message_user(
                        request,
                        f"Manifest attached, fields updated, and checklist imported for organizer '{obj}'.",
                        level=messages.SUCCESS,
                    )
                except Exception as e:
                    self.message_user(
                        request,
                        f"Manifest attached but failed to import checklist: {e}",
                        level=messages.ERROR,
                    )
                return HttpResponseRedirect(request.path)
            else:
                self.message_user(
                    request,
                    "No manifest file selected or file is empty.",
                    level=messages.ERROR,
                )
                return HttpResponseRedirect(request.path)
        if extra_context is None:
            extra_context = {}
        extra_context["manifest_upload_form"] = manifest_upload_form
        return super().change_view(
            request, object_id, form_url, extra_context=extra_context
        )

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

    def tax_year_display(self, obj):
        # Show just the year (assumes TaxYear has a 'year' field)
        return getattr(obj.tax_year, "year", str(obj.tax_year) or "-")

    tax_year_display.short_description = "Tax year"
    tax_year_display.admin_order_field = "tax_year__year"

    def title_with_width(self, obj):
        return format_html(
            '<div style="min-width: 300px; max-width: 600px; white-space: normal;">{}</div>',
            obj.title or "-",
        )

    title_with_width.short_description = "Title"
    title_with_width.admin_order_field = "title"

    def manifest_summary_icon(self, obj):
        summary = obj.manifest_file_summary or ""
        if summary.strip():
            return format_html('<span title="{}">📄</span>', summary)
        return "-"

    manifest_summary_icon.short_description = "Manifest summary"

    def manifest_hash_icon(self, obj):
        hashval = obj.manifest_hash or ""
        if hashval.strip():
            return format_html('<span title="{}">🔑</span>', hashval)
        return "-"

    manifest_hash_icon.short_description = "Manifest hash"

    def save_model(self, request, obj, form, change):
        # Auto-set business_profile from tax_year on add, robust to missing relation
        if (
            not change
            and hasattr(obj, "tax_year")
            and obj.tax_year
            and not getattr(obj, "business_profile", None)
        ):
            obj.business_profile = obj.tax_year.business_profile
        # If a manifest file is uploaded, extract fields
        file = form.cleaned_data.get("original_file")
        if file and file.name.lower().endswith(".json"):
            file.seek(0)
            manifest_hash, manifest_page_count, manifest_summary, manifest_title = (
                self.extract_manifest_fields(file)
            )
            obj.manifest_hash = manifest_hash
            obj.manifest_page_count = manifest_page_count
            obj.manifest_file_summary = manifest_summary
            if manifest_title:
                obj.title = manifest_title
            obj.status = "manifest_ready" if manifest_hash else "pending"
        super().save_model(request, obj, form, change)
        # --- Wire up pages_to_parse for batch parser job ---
        if not change:
            pages = form.cleaned_data.get("pages_to_parse", "").strip()
            if pages:
                # Add to ProcessingTask metadata for batch parser
                ProcessingTask.objects.create(
                    task_type="organizer_extraction",
                    client=obj.business_profile,
                    transaction_count=1,
                    status="pending",
                    task_metadata={
                        "workbook_id": obj.id,
                        "file": obj.original_file.name,
                        "pages_to_parse": pages,
                    },
                )
            else:
                # Default: all pages
                ProcessingTask.objects.create(
                    task_type="organizer_extraction",
                    client=obj.business_profile,
                    transaction_count=1,
                    status="pending",
                    task_metadata={
                        "workbook_id": obj.id,
                        "file": obj.original_file.name,
                    },
                )
