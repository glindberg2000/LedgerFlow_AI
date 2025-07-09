from django.contrib import admin
from .models import OrganizerWorkbook, OrganizerOutput


class OrganizerOutputInline(admin.TabularInline):
    model = OrganizerOutput
    extra = 0
    readonly_fields = ["output_type", "file", "page_number", "created_at"]
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(OrganizerWorkbook)
class OrganizerWorkbookAdmin(admin.ModelAdmin):
    list_display = ["title", "business_profile", "upload_date", "status"]
    list_filter = ["status", "upload_date"]
    search_fields = ["title", "business_profile__name"]
    readonly_fields = ["upload_date", "status"]
    inlines = [OrganizerOutputInline]
