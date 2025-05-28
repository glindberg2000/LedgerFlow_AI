from django.contrib import admin
from django.urls import path
from django.shortcuts import render, redirect
from django import forms
from .models import ParserTemplate, SampleStatement, ExtractionResult
from django.contrib import messages
from django.utils.safestring import mark_safe


class ParserTestForm(forms.Form):
    sample_file = forms.FileField(label="Sample Statement (PDF/CSV)")
    parser = forms.ModelChoiceField(
        queryset=ParserTemplate.objects.filter(is_active=True), label="Parser Template"
    )
    notes = forms.CharField(required=False, widget=forms.Textarea, label="Notes")


# Standalone parser test view for admin utility (importable in urls.py)
def test_parser_view(request):
    from django.contrib.admin.sites import site

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
            # Stub extraction logic (replace with real extraction)
            try:
                # For now, just show the template regex and file name
                extracted_metadata = {
                    "template": parser.template,
                    "file_name": sample.file.name,
                    "notes": notes,
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
                    error_message=str(e),
                )
                result = "fail"
                error = str(e)
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
