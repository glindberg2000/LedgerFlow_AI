from django.contrib import admin
from django.urls import path
from django.shortcuts import render, redirect
from django import forms
from .models import ParserTemplate, SampleStatement, ExtractionResult
from django.contrib import messages
from django.utils.safestring import mark_safe
import importlib
import traceback
import pandas as pd
import sys
import os


class ParserTestForm(forms.Form):
    sample_file = forms.FileField(label="Sample Statement (PDF/CSV)")
    parser = forms.ModelChoiceField(
        queryset=ParserTemplate.objects.filter(is_active=True), label="Parser Template"
    )
    notes = forms.CharField(required=False, widget=forms.Textarea, label="Notes")


# Standalone parser test view for admin utility (importable in urls.py)
def test_parser_view(request):
    from django.contrib.admin.sites import site

    # --- Patch sys.path for legacy parser imports ---
    PARSERS_ROOT = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../../dataextractai/parsers")
    )
    if PARSERS_ROOT not in sys.path:
        sys.path.insert(0, PARSERS_ROOT)
    # This allows imports like 'from dataextractai.utils.logging_config import configure_logging' to work
    context = dict(site.each_context(request))
    result = None
    error = None
    extracted_metadata = None
    if request.method == "POST":
        form = ParserTestForm(request.POST, request.FILES)
        if form.is_valid():
            sample_file = form.cleaned_data["sample_file"]
            parser = form.cleaned_data["parser"]
            notes = form.cleaned_data["notes"]
            # Save sample
            sample = SampleStatement.objects.create(
                file=sample_file,
                bank=parser.bank,
                type=parser.type,
                uploaded_by=request.user if request.user.is_authenticated else None,
                notes=notes,
            )
            try:
                # --- Dynamic parser execution ---
                import_path = parser.template
                if import_path.startswith("dataextractai.parsers.dataextractai."):
                    import_path = import_path.replace(
                        "dataextractai.parsers.dataextractai.",
                        "dataextractai.parsers.",
                        1,
                    )
                if import_path.startswith("dataextractai.parsers.parsers."):
                    import_path = import_path.replace(
                        "dataextractai.parsers.parsers.", "dataextractai.parsers.", 1
                    )
                module = importlib.import_module(import_path)
                entrypoint = None
                for fn_name in ["parse_pdf", "parse_file", "main", "run"]:
                    if hasattr(module, fn_name):
                        entrypoint = getattr(module, fn_name)
                        break
                if not entrypoint:
                    raise Exception(
                        f"Parser module {import_path} does not have a standard entrypoint (parse_pdf, parse_file, main, or run)"
                    )
                file_path = sample.file.path
                output = entrypoint(file_path)
                if isinstance(output, pd.DataFrame):
                    output = output.to_dict(orient="records")
                extracted_metadata = {
                    "parser": parser.template,
                    "file_name": sample.file.name,
                    "notes": notes,
                    "result": output,
                }
                ExtractionResult.objects.create(
                    sample=sample,
                    parser=parser,
                    extracted_metadata=extracted_metadata,
                    status="success",
                )
                result = "success"
            except Exception as e:
                ExtractionResult.objects.create(
                    sample=sample,
                    parser=parser,
                    extracted_metadata=None,
                    status="fail",
                    error_message=traceback.format_exc(),
                )
                result = "fail"
                error = f"{e}\nSee traceback in ExtractionResult."
    else:
        form = ParserTestForm()
    context.update(
        {
            "form": form,
            "result": result,
            "error": error,
            "extracted_metadata": extracted_metadata,
            "title": "Parser Test Utility",
        }
    )
    return render(request, "admin/parsers_utilities/test_parser.html", context)


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
