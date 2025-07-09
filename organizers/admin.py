from django.contrib import admin
from .models import OrganizerWorkbook, OrganizerOutput
from profiles.models import ProcessingTask


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
    actions = ["create_extraction_task"]

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
