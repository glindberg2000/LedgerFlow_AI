from django.contrib import admin
from .models import ParserTemplate, SampleStatement, ExtractionResult


@admin.register(ParserTemplate)
class ParserTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "bank", "type", "is_active", "updated")
    search_fields = ("name", "bank", "template")
    list_filter = ("bank", "type", "is_active")
    # For extensibility: add inline preview of template logic, test extraction, etc.


@admin.register(SampleStatement)
class SampleStatementAdmin(admin.ModelAdmin):
    list_display = ("file", "bank", "type", "uploaded_by", "upload_timestamp", "notes")
    search_fields = ("file", "bank", "notes")
    list_filter = ("bank", "type", "uploaded_by")
    # For extensibility: add preview snapshot, test extraction action, etc.


@admin.register(ExtractionResult)
class ExtractionResultAdmin(admin.ModelAdmin):
    list_display = ("sample", "parser", "status", "created", "short_error")
    search_fields = ("sample__file", "parser__name", "error_message")
    list_filter = ("status", "parser", "created")

    def short_error(self, obj):
        return (
            (obj.error_message[:60] + "...")
            if obj.error_message and len(obj.error_message) > 60
            else obj.error_message
        )

    short_error.short_description = "Error Message"
    # For extensibility: add link to extracted metadata, rerun extraction, etc.
