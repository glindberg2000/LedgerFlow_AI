from django.contrib import admin
from django.urls import path
from django.shortcuts import render
import sys
import os
from .models import ImportedParser


# Read-only admin for ImportedParser
@admin.register(ImportedParser)
class ImportedParserAdmin(admin.ModelAdmin):
    list_display = ("name", "last_imported")
    search_fields = ("name",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


# Custom admin view for showing registered parsers (function-based, not ModelAdmin)
def registered_parsers_view(request):
    # Patch sys.path for subrepo if needed
    PDF_EXTRACTOR_PATH = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../../PDF-extractor")
    )
    if PDF_EXTRACTOR_PATH not in sys.path:
        sys.path.insert(0, PDF_EXTRACTOR_PATH)
    # Import and run autodiscover
    try:
        from dataextractai.parsers_core.autodiscover import autodiscover_parsers

        autodiscover_parsers()
        from dataextractai.parsers_core.registry import ParserRegistry

        parser_names = ParserRegistry.list_parsers()
    except Exception as e:
        parser_names = []
        error = str(e)
    else:
        error = None
    context = dict(admin.site.each_context(request))
    context.update(
        {
            "title": "Registered Modular Parsers (Read-Only)",
            "parser_names": parser_names,
            "error": error,
        }
    )
    return render(request, "admin/parsers_utilities/registered_parsers.html", context)


# Patch admin URLs to add the custom view
old_get_urls = admin.site.get_urls


def get_urls():
    urls = old_get_urls()
    custom_urls = [
        path(
            "parsers_utilities/registered-parsers/",
            admin.site.admin_view(registered_parsers_view),
            name="registered_parsers",
        ),
    ]
    return custom_urls + urls


admin.site.get_urls = get_urls
