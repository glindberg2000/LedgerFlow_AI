from django.contrib import admin
from django.template.loader import render_to_string
from django.http import HttpResponseRedirect, JsonResponse, Http404

admin.site.site_header = "LedgerFlow Admin"
admin.site.site_title = "LedgerFlow Admin"
admin.site.index_title = "LedgerFlow Admin"

from .models import (
    BusinessProfile,
    Transaction,
    LLMConfig,
    Agent,
    Tool,
    NormalizedVendorData,
    IRSWorksheet,
    IRSExpenseCategory,
    BusinessExpenseCategory,
    TransactionClassification,
    ProcessingTask,
    StatementFile,
    CLASSIFICATION_METHOD_UNCLASSIFIED,
    PAYEE_EXTRACTION_METHOD_UNPROCESSED,
    ParsingRun,
    TaxChecklistItem,
    ChecklistAttachment,
)
from django.utils.translation import gettext_lazy as _
from django.http import HttpResponseRedirect
from django.urls import path, reverse
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
import json
from jsonschema import validate, ValidationError
import requests
import os
from dotenv import load_dotenv
import logging
import traceback
from openai import OpenAI
import sys
from datetime import datetime
from django.utils import timezone
from pathlib import Path
import subprocess
from django.conf import settings
from django.db import transaction as db_transaction
from django import forms
from django.utils.html import format_html
import re
from .utils import (
    extract_pdf_metadata,
    get_update_fields_from_response,
    sync_transaction_id_sequence,
)
from django.template.response import TemplateResponse
from django.contrib.admin import AdminSite
from django.utils.safestring import mark_safe
import importlib
import pkgutil
from dataextractai.utils.normalize_api import normalize_parsed_data_df
from django.core.exceptions import ValidationError
import pandas as pd
import tempfile
from django.core.files import File
from profiles.parsers_utilities.models import ImportedParser
from .bootstrap import load_canonical_tax_checklist_index
import urllib.parse

# Add the root directory to the Python path
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(
    logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
)
logger.addHandler(handler)


class BusinessProfileAdminForm(forms.ModelForm):
    class Meta:
        model = BusinessProfile
        fields = [
            "company_name",
            "contact_info",
            "business_description",
            "common_expenses",
            "custom_categories",
            "industry_keywords",
            "category_patterns",
            "business_rules",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # client_id is not editable, but we can show it as a readonly/display field in the admin if needed


class TaxChecklistItemInline(admin.TabularInline):
    model = TaxChecklistItem
    extra = 0
    can_delete = False
    show_change_link = False
    fields = (
        "form_code",
        "tax_year",
        "description",
        "entry_type",
        "enabled",
        "status",
        "notes",
    )
    readonly_fields = ("form_code", "tax_year", "description", "entry_type")
    verbose_name = "Tracked Form"
    verbose_name_plural = "Tracked Forms"

    def has_add_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        year = request.GET.get("tax_year")
        show_all = request.GET.get("show_all") == "1"
        if not year:
            year = str(datetime.now().year - 1)
        qs = qs.filter(tax_year=year)
        if not show_all:
            qs = qs.filter(enabled=True)
        return qs

    def formfield_for_dbfield(self, db_field, **kwargs):
        field = super().formfield_for_dbfield(db_field, **kwargs)
        if db_field.name == "enabled":
            field.label = "Tracked"
        return field

    def description(self, obj):
        canonical = load_canonical_tax_checklist_index()
        meta = canonical.get(obj.form_code, {})
        return meta.get("label", "")

    def entry_type(self, obj):
        canonical = load_canonical_tax_checklist_index()
        meta = canonical.get(obj.form_code, {})
        return meta.get("entry_type", "manual_entry")

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        return formset


class ChecklistAttachmentInline(admin.TabularInline):
    model = ChecklistAttachment
    extra = 0
    fields = ("file", "tag", "uploaded_at")
    readonly_fields = ("uploaded_at",)
    verbose_name = "Attachment"
    verbose_name_plural = "Attachments"
    can_delete = True
    show_change_link = False

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        form = formset.form
        form.base_fields["tag"].help_text = "Edit the tag and save to update."
        return formset


@admin.register(BusinessProfile)
class BusinessProfileAdmin(admin.ModelAdmin):
    form = BusinessProfileAdminForm
    list_display = (
        "company_name",
        "client_id",
        "business_type",
        "statement_files_count",
        "transactions_count",
        "short_business_description",
        "contact_info",
    )
    search_fields = ("company_name", "client_id", "business_description")
    fieldsets = (
        (
            "User-Defined Profile",
            {
                "fields": (
                    "company_name",
                    "contact_info",
                    "business_description",
                ),
                "description": "Client ID is a non-editable, URL-safe identifier. Company name is editable. Enter contact info and a business description. The AI will generate the rest.",
            },
        ),
        (
            "AI-Generated Profile",
            {
                "fields": (
                    "common_expenses",
                    "custom_categories",
                    "industry_keywords",
                    "category_patterns",
                    "business_rules",
                ),
                "description": "These fields are generated by AI based on your business description. You can edit them if needed.",
            },
        ),
    )
    readonly_fields = ("client_id",)
    inlines = [TaxChecklistItemInline]

    def statement_files_count(self, obj):
        return obj.statement_files.count()

    statement_files_count.short_description = "Statement Files"

    def transactions_count(self, obj):
        return obj.transactions.count()

    transactions_count.short_description = "Transactions"

    def short_business_description(self, obj):
        desc = obj.business_description or ""
        return desc[:40] + ("..." if len(desc) > 40 else "")

    short_business_description.short_description = "Business Description"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<path:object_id>/generate_ai/",
                self.admin_site.admin_view(self.generate_ai_profile_view),
                name="profiles_businessprofile_generate_ai",
            ),
        ]
        return custom_urls + urls

    def render_change_form(self, request, context, *args, **kwargs):
        obj = context.get("original")
        if obj:
            generate_url = reverse(
                "admin:profiles_businessprofile_generate_ai", args=[obj.pk]
            )
            context["adminform"].form.fields[
                "business_description"
            ].help_text += format_html(
                '<br><a class="button" href="{}" style="display:inline-block;margin-top:20px;">Generate AI Profile</a>',
                generate_url,
            )
        return super().render_change_form(request, context, *args, **kwargs)

    def generate_ai_profile_view(self, request, object_id):
        obj = self.get_object(request, object_id)
        if not obj:
            messages.error(request, "BusinessProfile not found.")
            from django.shortcuts import redirect
            return redirect("..")
        try:
            from openai import OpenAI
            agent = None
            model = None
            base_url = None
            try:
                from .models import Agent
                agent = Agent.objects.filter(
                    purpose__icontains="business profile generator"
                ).first()
                if not agent:
                    agent = Agent.objects.exclude(llm=None).first()
                if agent and agent.llm and agent.llm.model:
                    model = agent.llm.model
                    base_url = agent.llm.url
            except Exception:
                pass
            if not model:
                model = os.environ.get("OPENAI_MODEL_PRECISE", "o4-mini")
            api_key = os.environ.get("OPENAI_API_KEY")
            if base_url:
                client = OpenAI(api_key=api_key, base_url=base_url)
            else:
                client = OpenAI(api_key=api_key)
            system_prompt = (
                "You are an expert business profile generator. Given a business description, generate a JSON object with these keys: "
                "common_expenses, custom_categories, industry_keywords, category_patterns, business_rules. "
                "Each value should be a comma-separated string. Only include the required keys."
            )
            user_prompt = f"""
Business Description:
{obj.business_description}

Respond ONLY with a valid JSON object with these exact keys:
- common_expenses: comma-separated list of common business expenses
- custom_categories: comma-separated list of custom categories
- industry_keywords: comma-separated list of industry keywords
- category_patterns: comma-separated list of category patterns
- business_rules: comma-separated list of business rules or policies
Do NOT include any explanation or text outside the JSON.
"""
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content
            try:
                data = json.loads(content)
            except Exception as e:
                messages.error(
                    request, f"LLM did not return valid JSON. Raw response: {content}"
                )
                from django.shortcuts import redirect
                return redirect(
                    reverse("admin:profiles_businessprofile_change", args=[obj.pk])
                )
            if not isinstance(data, dict) or not any(data.values()):
                messages.warning(
                    request,
                    f"AI response was empty or missing fields. Raw response: {content}. If this persists, check the prompt and schema format sent to OpenAI.",
                )
            for field in [
                "common_expenses",
                "custom_categories",
                "industry_keywords",
                "category_patterns",
                "business_rules",
            ]:
                value = data.get(field, "")
                if isinstance(value, (list, dict)):
                    if isinstance(value, dict):
                        value = ", ".join(f"{k}: {v}" for k, v in value.items())
                    else:
                        value = ", ".join(str(x) for x in value)
                setattr(obj, field, value)
            obj.save()
            messages.success(
                request,
                "AI-generated profile fields have been filled in. Review and save to persist.",
            )
        except Exception as e:
            import logging
            logging.exception("Error generating AI profile")
            messages.error(request, f"Error generating AI profile: {e}")
        from django.shortcuts import redirect
        return redirect(reverse("admin:profiles_businessprofile_change", args=[obj.pk]))


@admin.register(TaxChecklistItem)
class TaxChecklistItemAdmin(admin.ModelAdmin):
    list_display = (
        "business_profile",
        "tax_year",
        "form_code",
        "enabled",
        "status",
        "date_modified",
    )
    list_filter = ("tax_year", "enabled", "status")
    search_fields = ("form_code", "notes")
    autocomplete_fields = ("business_profile",)
    ordering = ("business_profile", "tax_year", "form_code")
    inlines = [ChecklistAttachmentInline]
    readonly_fields = ("business_profile", "tax_year", "form_code")
    actions = ["enable_selected", "disable_selected"]

    def enable_selected(self, request, queryset):
        updated = queryset.update(enabled=True)
        self.message_user(request, f"Enabled {updated} checklist items.")

    enable_selected.short_description = "Enable selected checklist items"

    def disable_selected(self, request, queryset):
        updated = queryset.update(enabled=False)
        self.message_user(request, f"Disabled {updated} checklist items.")

    disable_selected.short_description = "Disable selected checklist items"

    def changelist_view(self, request, extra_context=None):
        # Default to enabled items only unless filter is set
        if "enabled__exact" not in request.GET:
            q = request.GET.copy()
            q["enabled__exact"] = "1"
            request.GET = q
            request.META["QUERY_STRING"] = request.GET.urlencode()
        return super().changelist_view(request, extra_context=extra_context)


@admin.register(ChecklistAttachment)
class ChecklistAttachmentAdmin(admin.ModelAdmin):
    list_display = ("file", "tag", "uploaded_at")
    search_fields = ("file", "tag")
    readonly_fields = ("uploaded_at",)


class ClientFilter(admin.SimpleListFilter):
    title = _("client")
    parameter_name = "client"

    def lookups(self, request, model_admin):
        clients = set(Transaction.objects.values_list("client__client_id", flat=True))
        return [(client, client) for client in clients]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(client__client_id=self.value())
        return queryset


def call_agent(
    agent_name, transaction, model=None, max_retries=2, escalate_on_fail=True
):
    """Call the specified agent with the transaction data."""
    import os
    from openai import OpenAI

    logger = logging.getLogger(__name__)

    # --- START: NEW GUARDRAIL ---
    # For classification agents, if the amount is positive, it's income. No AI needed.
    agent = Agent.objects.get(name=agent_name)
    if "classification" in agent.purpose.lower() and transaction.amount > 0:
        logger.info(
            f"Transaction {transaction.id} has positive amount. Bypassing AI and auto-classifying as Income."
        )
        return {
            "classification_type": "Income",
            "worksheet": "Income",
            "category": "Client Income",
            "confidence": "high",
            "reasoning": "Auto-classified as Income due to positive transaction amount.",
            "business_percentage": 0,
            "questions": "",
        }
    # --- END: NEW GUARDRAIL ---

    if model is None:
        model = os.environ.get("OPENAI_MODEL_PRECISE", "o4-mini")
    logger.info(f"Using OpenAI model: {model}")
    try:
        # Get the agent object from the database
        agent = Agent.objects.get(name=agent_name)
        base_url = agent.llm.url if agent.llm and agent.llm.url else None
        api_key = os.environ.get("OPENAI_API_KEY")
        if base_url:
            client = OpenAI(api_key=api_key, base_url=base_url)
        else:
            client = OpenAI(api_key=api_key)

        # --- Dynamic context construction ---
        # Fetch business profile for the transaction's client
        business_profile = None
        try:
            business_profile = transaction.client
        except Exception:
            pass
        business_context_lines = []
        if business_profile:
            if business_profile.business_type:
                business_context_lines.append(f"Business Type: {business_profile.business_type}")
            if business_profile.business_description:
                business_context_lines.append(f"Business Description: {business_profile.business_description}")
            if business_profile.contact_info:
                business_context_lines.append(f"Contact Info: {business_profile.contact_info}")
            if business_profile.common_expenses:
                business_context_lines.append(f"Common Expenses: {business_profile.common_expenses}")
            if business_profile.custom_categories:
                business_context_lines.append(f"Custom Categories: {business_profile.custom_categories}")
            if business_profile.industry_keywords:
                business_context_lines.append(f"Industry Keywords: {business_profile.industry_keywords}")
            if business_profile.category_patterns:
                business_context_lines.append(f"Category Patterns: {business_profile.category_patterns}")
            if business_profile.business_rules:
                business_context_lines.append(f"Business Rules: {business_profile.business_rules}")
        business_context = "\n".join(business_context_lines)
        if business_context:
            business_context = f"Business Profile Context:\n{business_context}\n"
        else:
            business_context = ""
        # Add payee reasoning if available
        payee_reasoning = getattr(transaction, "payee_reasoning", None)
        if payee_reasoning:
            payee_context = f"Payee Reasoning (detailed vendor info):\n{payee_reasoning}\n"
        else:
            payee_context = ""

        # --- Allowed categories ---
        from profiles.models import IRSExpenseCategory, BusinessExpenseCategory
        irs_cats = IRSExpenseCategory.objects.filter(
            is_active=True, worksheet__name__in=["6A", "Auto", "HomeOffice"]
        ).values("id", "name", "worksheet__name")
        biz_cats = BusinessExpenseCategory.objects.filter(
            is_active=True, business=transaction.client
        ).values("id", "category_name", "worksheet__name")
        allowed_categories = []
        for cat in irs_cats:
            allowed_categories.append(
                f"IRS-{cat['id']}: {cat['name']} (worksheet: {cat['worksheet__name']})"
            )
        for cat in biz_cats:
            allowed_categories.append(
                f"BIZ-{cat['id']}: {cat['category_name']} (worksheet: {cat['worksheet__name']})"
            )
        allowed_categories += ["Other", "Personal", "Review"]

        # --- Final prompt construction ---
        static_prompt = agent.prompt.strip() if agent.prompt else ""
        dynamic_context = f"\n{business_context}{payee_context}Allowed Categories (choose ONLY from this list):\n{chr(10).join(allowed_categories)}\n\nTransaction: {transaction.description}\nAmount: ${transaction.amount}\nDate: {transaction.transaction_date}"
        final_prompt = f"{static_prompt}\n\n{dynamic_context}"

        # Log the full constructed prompt
        logger.info("\n=== API Request ===")
        logger.info(f"Model: {agent.llm.model}")
        logger.info(f"Prompt: {final_prompt}")
        logger.info(f"Transaction: {transaction.description}")

        # Prepare tools for the API call with proper schema
        tool_definitions = []
        for tool in agent.tools.all():
            tool_def = {
                "name": tool.name,
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The search query to look up",
                            }
                        },
                        "required": ["query"],
                    },
                },
            }
            tool_definitions.append(tool_def)

        payload = {
            "model": agent.llm.model,
            "messages": [
                {"role": "user", "content": final_prompt},
            ],
            "response_format": {"type": "json_object"},
        }
        if tool_definitions:
            payload["tools"] = tool_definitions
            payload["tool_choice"] = "auto"

        try:
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            messages = [
                {"role": "user", "content": final_prompt},
            ]
            if tool_definitions:
                tools = tool_definitions
            else:
                tools = None
            max_tool_calls = 3
            tool_call_count = 0
            tool_usage = {}  # Track tool name -> count
            while True:
                payload = {
                    "model": agent.llm.model,
                    "messages": messages,
                    "response_format": {"type": "json_object"},
                }
                if tools:
                    payload["tools"] = tools
                    payload["tool_choice"] = "auto"
                response = client.chat.completions.create(**payload)
                logger.info(f"LLM response: {response}")
                msg = response.choices[0].message
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    if tool_call_count >= max_tool_calls:
                        messages.append(
                            {
                                "role": "user",
                                "content": "Maximum search limit reached. Now provide your final response in the exact JSON format specified.",
                            }
                        )
                        continue
                    messages.append(
                        {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [
                                (
                                    tc.to_dict()
                                    if hasattr(tc, "to_dict")
                                    else {
                                        "id": tc.id,
                                        "function": {
                                            "name": tc.function.name,
                                            "arguments": tc.function.arguments,
                                        },
                                        "type": "function",
                                    }
                                )
                                for tc in msg.tool_calls
                            ],
                        }
                    )
                    for tool_call in msg.tool_calls:
                        tool_name = tool_call.function.name
                        tool_args = json.loads(tool_call.function.arguments)
                        logger.info(
                            f"Executing tool: {tool_name} with args: {tool_args}"
                        )
                        try:
                            tool_obj = Tool.objects.get(name=tool_name)
                            module_path = tool_obj.module_path
                            module_name = module_path.split(".")[-1]
                            module = __import__(module_path, fromlist=[module_name])
                            if tool_name == "searxng_search":
                                tool_function = getattr(module, "searxng_search")
                            else:
                                tool_function = getattr(module, tool_name)
                            tool_result = tool_function(**tool_args)
                            logger.info(f"Tool result: {tool_result}")
                        except Exception as e:
                            logger.error(f"Error executing tool {tool_name}: {str(e)}")
                            raise
                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "name": tool_name,
                                "content": json.dumps(tool_result),
                            }
                        )
                        tool_usage[tool_name] = tool_usage.get(tool_name, 0) + 1
                        tool_call_count += 1
                    continue  # Loop again to get the next LLM response
                if msg.content:
                    return json.loads(msg.content), tool_usage
                logger.error(
                    "LLM returned neither tool_calls nor content. Breaking loop."
                )
                break
            raise RuntimeError("Failed to get a valid response from the LLM.")

        except Exception as e:
            logger.error(f"Error calling OpenAI API: {str(e)}")
            raise

    except Exception as e:
        logger.error(f"Error in call_agent: {str(e)}")
        raise

    return response, tool_usage


def process_transactions(modeladmin, request, queryset):
    if "agent" not in request.POST:
        # Show the agent selection form
        agents = Agent.objects.all().order_by("name")  # Order agents by name
        if not agents:
            messages.error(
                request, "No agents available. Please create an agent first."
            )
            return HttpResponseRedirect(request.get_full_path())

        return render(
            request,
            "admin/process_transactions.html",
            context={
                "transactions": queryset,
                "agents": agents,
                "title": "Select Agent to Process Transactions",
                "opts": modeladmin.model._meta,
            },
        )

    # Process the transactions with the selected agent
    agent_id = request.POST["agent"]
    try:
        agent = Agent.objects.get(id=agent_id)
        for transaction in queryset:
            response, tool_usage = call_agent(agent.name, transaction)
            update_fields = get_update_fields_from_response(
                agent,
                response,
                (
                    getattr(agent, "purpose", "").lower()
                    if hasattr(agent, "purpose")
                    else "classification"
                ),
                tool_usage=tool_usage,
            )
            logger.info(
                f"Update fields for transaction {transaction.id}: {update_fields}"
            )
            rows_updated = Transaction.objects.filter(id=transaction.id).update(
                **update_fields
            )
            logger.info(f"Updated {rows_updated} rows for transaction {transaction.id}")
            updated_tx = Transaction.objects.get(id=transaction.id)
            logger.info(
                f"Transaction {transaction.id} after update: payee={updated_tx.payee}, classification_type={updated_tx.classification_type}, worksheet={updated_tx.worksheet}, confidence={updated_tx.confidence}, category={updated_tx.category}"
            )
        messages.success(
            request,
            f"Successfully processed {queryset.count()} transactions with {agent.name}",
        )
    except Agent.DoesNotExist:
        messages.error(request, "Selected agent not found")
    except Exception as e:
        messages.error(request, f"Error processing transactions: {str(e)}")
    return HttpResponseRedirect(request.get_full_path())


process_transactions.short_description = "Process selected transactions with agent"


def reset_processing_status(modeladmin, request, queryset):
    """Reset selected transactions to 'Not Processed' status."""
    updated = queryset.update(
        payee_extraction_method="None",
        classification_method="None",
        payee=None,
        normalized_description=None,
        confidence=None,
        reasoning=None,
        payee_reasoning=None,
        business_context=None,
        questions=None,
        classification_type=None,
        worksheet=None,
        business_percentage=None,
        category=None,
    )
    messages.success(
        request, f"Successfully reset {updated} transactions to 'Not Processed' status."
    )


reset_processing_status.short_description = (
    "Reset selected transactions to 'Not Processed'"
)


class TransactionAdminForm(forms.ModelForm):
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "rows": 2,
                "cols": 60,
                "style": "min-height:40px;resize:vertical;width:100%;overflow:auto;",
            }
        ),
        label="Notes",
        help_text="Optional: Add any additional notes or context for this transaction (for bookkeeper use).",
    )
    # Explicitly define as ChoiceField to force dropdown rendering in admin
    category = forms.ChoiceField(
        choices=[],  # Will be set dynamically in __init__
        required=False,
        label="Category",
    )
    classification_type = forms.ChoiceField(
        choices=[],  # Will be set dynamically in __init__
        required=False,
        label="Classification Type",
    )
    CLASSIFICATION_TYPE_CHOICES = [
        ("business", "Business"),
        ("personal", "Personal"),
    ]

    def _get_category_choices(self, current_value=None):
        irs_cats = IRSExpenseCategory.objects.filter(
            worksheet__name="6A", is_active=True
        ).order_by("line_number")
        irs_choices = [(cat.name, f"IRS: {cat.name}") for cat in irs_cats]
        biz_cats = BusinessExpenseCategory.objects.filter(
            worksheet__name="6A", is_active=True
        ).order_by("category_name")
        biz_choices = [
            (cat.category_name, f"Business: {cat.category_name}") for cat in biz_cats
        ]
        personal_choice = [("Personal", "--- Personal ---")]
        choices = irs_choices + biz_choices + personal_choice
        if not choices:
            choices = [("", "--- No categories available ---")]
        if current_value and current_value not in [c[0] for c in choices]:
            choices = [(current_value, f"Current: {current_value}")] + choices
        return choices

    def _get_classification_type_choices(self, current_value=None):
        choices = self.CLASSIFICATION_TYPE_CHOICES.copy()
        if not choices:
            choices = [("", "--- No types available ---")]
        if current_value and current_value not in [c[0] for c in choices]:
            choices = [(current_value, f"Current: {current_value}")] + choices
        return choices

    class Meta:
        model = Transaction
        fields = "__all__"
        widgets = {
            "business_percentage": forms.NumberInput(attrs={"min": 0, "max": 100}),
            "confidence": forms.Select(
                choices=[("high", "high"), ("medium", "medium"), ("low", "low")]
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["notes"].initial = self.instance.business_context
        # Set dynamic choices for category and classification_type
        current_category = self.instance.category
        current_classification = self.instance.classification_type
        self.fields["category"].choices = self._get_category_choices(current_category)
        self.fields["classification_type"].choices = (
            self._get_classification_type_choices(current_classification)
        )
        # Make classification_method readonly (never user-editable)
        if "classification_method" in self.fields:
            self.fields["classification_method"].disabled = True

    def clean_category(self):
        # Only save the value, not the label
        return self.cleaned_data["category"]

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Save notes back to business_context
        instance.business_context = self.cleaned_data.get("notes", "")
        # Always set classification_method to 'None' if saving via admin form
        instance.classification_method = "None"
        if commit:
            instance.save()
        return instance


# Add a ProcessedFilter for sidebar
class ProcessedFilter(admin.SimpleListFilter):
    title = _("Processed")
    parameter_name = "processed"

    def lookups(self, request, model_admin):
        return (
            ("yes", _("Processed")),
            ("no", _("Unprocessed")),
        )

    def queryset(self, request, queryset):
        if self.value() == "yes":
            return queryset.exclude(classification_method__isnull=True).exclude(
                classification_method="None"
            )
        if self.value() == "no":
            return queryset.filter(
                classification_method__isnull=True
            ) | queryset.filter(classification_method="None")
        return queryset


class NeedsAccountNumberFilter(admin.SimpleListFilter):
    title = _("Needs Account Number")
    parameter_name = "needs_account_number"

    def lookups(self, request, model_admin):
        return (
            ("yes", _("Needs Account Number")),
            ("no", _("Has Account Number")),
        )

    def queryset(self, request, queryset):
        if self.value() == "yes":
            return queryset.filter(needs_account_number=True)
        if self.value() == "no":
            return queryset.filter(needs_account_number=False)
        return queryset


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    form = TransactionAdminForm
    list_display = (
        "transaction_date",
        "amount",
        "description",
        "normalized_description",
        "payee",
        "category",
        "classification_type",
        "worksheet",
        "business_percentage",
        "confidence",
        "source",
        "file_link_column",
        "account_number",
        "short_reasoning",  # Use icon if present
        "short_payee_reasoning",  # Use icon if present
        "classification_method",
        "payee_extraction_method",
    )
    list_filter = (
        ClientFilter,
        ProcessedFilter,
        NeedsAccountNumberFilter,  # Add our new filter
        "transaction_date",
        "classification_type",
        "worksheet",
        "confidence",
        "category",
        "source",
        "transaction_type",
        "classification_method",
        "payee_extraction_method",
    )
    search_fields = (
        "description",
        "normalized_description",
        "category",
        "source",
        "transaction_type",
        "account_number",
        "payee",
        "reasoning",
        "payee_reasoning",
        "business_context",
        "questions",
        "classification_type",
        "worksheet",
    )
    readonly_fields = (
        "transaction_date",
        "amount",
        "description",
        "normalized_description",
        "payee",
        "worksheet",
        "payee_extraction_method",
        "reasoning",
        "payee_reasoning",
        "classification_method",  # Always readonly
    )
    # Remove 'business_context' from readonly, add 'notes' as editable
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "transaction_date",
                    "amount",
                    "description",
                    "normalized_description",
                    "payee",
                    "category",
                    "classification_type",
                    "worksheet",
                    "business_percentage",
                    "confidence",
                    "classification_method",
                    "payee_extraction_method",
                    "reasoning",
                    "payee_reasoning",
                    "notes",
                )
            },
        ),
    )
    actions = [
        "reset_processing_status",
        "batch_payee_lookup",
        "batch_classify",
        "mark_as_personal",
        "mark_as_business",
        "mark_as_unclassified",
        "batch_set_account_number",  # New batch action
        "lookup_payee",  # Direct payee lookup action
        "classify_transactions",  # Direct classify action
    ]

    def short_reasoning(self, obj):
        if obj.reasoning:
            return format_html('<span title="{}">🛈</span>', obj.reasoning)
        return ""

    short_reasoning.short_description = "Reasoning"

    def short_payee_reasoning(self, obj):
        if obj.payee_reasoning:
            return format_html('<span title="{}">🛈</span>', obj.payee_reasoning)
        return ""

    short_payee_reasoning.short_description = "Payee Reasoning"

    def file_link_column(self, obj):
        try:
            if obj.statement_file and obj.statement_file.original_filename:
                url = reverse(
                    "reports:download_statement_file",
                    args=[obj.statement_file_id],
                )
                return format_html(
                    '<a href="{}" target="_blank">{}</a>',
                    url,
                    obj.statement_file.original_filename,
                )
            else:
                return "N/A"
        except Exception as e:
            return format_html('<span style="color:red;">Link unavailable</span>')

    file_link_column.short_description = "Original File"
    file_link_column.admin_order_field = "file_path"

    @admin.action(description="Batch set account number for selected transactions")
    def batch_set_account_number(self, request, queryset):
        from django import forms

        class AccountNumberForm(forms.Form):
            account_number = forms.CharField(label="Account Number", required=True)

        if "apply" in request.POST:
            form = AccountNumberForm(request.POST)
            if form.is_valid():
                account_number = form.cleaned_data["account_number"]
                updated = queryset.update(
                    account_number=account_number, needs_account_number=False
                )
                self.message_user(
                    request, f"Set account number for {updated} transactions."
                )
                return
        else:
            form = AccountNumberForm()
        return render(
            request,
            "admin/batch_set_account_number.html",
            {"form": form, "queryset": queryset},
        )

    def batch_payee_lookup(self, request, queryset):
        """Create a batch processing task for payee lookup."""
        if not queryset:
            messages.error(request, "No transactions selected.")
            return
        client_transactions = {}
        for transaction in queryset:
            if transaction.client_id not in client_transactions:
                client_transactions[transaction.client_id] = {
                    "client": transaction.client,
                    "transactions": [],
                    "transaction_ids": [],
                }
            client_transactions[transaction.client_id]["transactions"].append(
                transaction
            )
            client_transactions[transaction.client_id]["transaction_ids"].append(
                transaction.id
            )
        for client_id, data in client_transactions.items():
            with db_transaction.atomic():
                task = ProcessingTask.objects.create(
                    task_type="payee_lookup",
                    client=data["client"],
                    transaction_count=len(data["transactions"]),
                    status="pending",
                    task_metadata={
                        "description": f"Batch payee lookup for {len(data['transactions'])} transactions",
                        "transaction_ids": data["transaction_ids"],
                    },
                )
                messages.success(
                    request,
                    f"Created payee lookup task for client {client_id} with {len(data['transactions'])} transactions",
                )
        self.message_user(
            request, f"Created payee lookup task for selected transactions."
        )

    batch_payee_lookup.short_description = "Create batch payee lookup task"

    def batch_classify(self, request, queryset):
        """Create a batch processing task for classification."""
        if not queryset:
            messages.error(request, "No transactions selected.")
            return
        client_transactions = {}
        for transaction in queryset:
            if transaction.client_id not in client_transactions:
                client_transactions[transaction.client_id] = {
                    "client": transaction.client,
                    "transactions": [],
                    "transaction_ids": [],
                }
            client_transactions[transaction.client_id]["transactions"].append(
                transaction
            )
            client_transactions[transaction.client_id]["transaction_ids"].append(
                transaction.id
            )
        for client_id, data in client_transactions.items():
            with db_transaction.atomic():
                task = ProcessingTask.objects.create(
                    task_type="classification",
                    client=data["client"],
                    transaction_count=len(data["transactions"]),
                    status="pending",
                    task_metadata={
                        "description": f"Batch classification for {len(data['transactions'])} transactions",
                        "transaction_ids": data["transaction_ids"],
                    },
                )
                messages.success(
                    request,
                    f"Created classification task for client {client_id} with {len(data['transactions'])} transactions",
                )
        self.message_user(
            request, f"Created classification task for selected transactions."
        )

    batch_classify.short_description = "Create batch classification task"

    def mark_as_personal(self, request, queryset):
        updated = queryset.update(
            classification_type="personal",
            worksheet="Personal",
            category="Personal",
        )
        self.message_user(request, f"Marked {updated} transactions as Personal.")

    mark_as_personal.short_description = "Mark selected as Personal"

    def mark_as_business(self, request, queryset):
        from .models import IRSExpenseCategory, BusinessExpenseCategory, IRSWorksheet

        count = 0
        worksheet = IRSWorksheet.objects.filter(name="6A").first()
        for tx in queryset:
            # Set as business, worksheet 6A
            tx.classification_type = "business"
            tx.worksheet = "6A"
            tx.save(update_fields=["classification_type", "worksheet"])
            # Check if category is in IRS 6A or user-defined
            cat_name = tx.category
            if not IRSExpenseCategory.objects.filter(
                worksheet=worksheet, name=cat_name
            ).exists():
                # Not an official IRS category, check if user-defined exists
                if not BusinessExpenseCategory.objects.filter(
                    business=tx.client, worksheet=worksheet, category_name=cat_name
                ).exists():
                    # Auto-add user-defined business category
                    BusinessExpenseCategory.objects.create(
                        business=tx.client,
                        worksheet=worksheet,
                        category_name=cat_name,
                        is_active=True,
                    )
            count += 1
        self.message_user(
            request,
            f"Marked {count} transactions as Business and auto-added categories as needed.",
        )

    mark_as_business.short_description = (
        "Mark selected as Business (auto-add category if needed)"
    )

    def mark_as_unclassified(self, request, queryset):
        updated = queryset.update(
            classification_method=CLASSIFICATION_METHOD_UNCLASSIFIED,
            classification_type=None,
            worksheet=None,
            category=None,
            confidence=None,
            reasoning=None,
            business_percentage=None,
        )
        self.message_user(request, f"Marked {updated} transactions as Unclassified.")

    mark_as_unclassified.short_description = (
        "Mark selected as Unclassified (reset classification only)"
    )

    def get_actions(self, request):
        actions = super().get_actions(request)
        # Remove Business Profile Generator from actions
        actions = {
            k: v for k, v in actions.items() if "business_profile_generator" not in k
        }
        # Keep existing agent-specific actions
        for agent in Agent.objects.all():
            action_name = f'process_with_{agent.name.lower().replace(" ", "_")}'
            if "business_profile_generator" in action_name:
                continue
            action_function = self._create_agent_action(agent)
            action_function.short_description = f"Process with {agent.name}"
            actions[action_name] = (
                action_function,
                action_name,
                action_function.short_description,
            )
        return actions

    def _create_agent_action(self, agent):
        def process_with_agent(modeladmin, request, queryset):
            try:
                for transaction in queryset:
                    logger.info(
                        f"Processing transaction {transaction.id} with agent {agent.name}"
                    )
                    response, tool_usage = call_agent(agent.name, transaction)
                    logger.info(f"Agent response: {response}")
                    agent_type = _get_agent_type(agent)
                    update_fields = get_update_fields_from_response(
                        agent,
                        response,
                        agent_type=agent_type,
                        tool_usage=tool_usage,
                    )
                    logger.info(
                        f"Update fields for transaction {transaction.id}: {update_fields}"
                    )
                    rows_updated = Transaction.objects.filter(id=transaction.id).update(
                        **update_fields
                    )
                    logger.info(
                        f"Updated {rows_updated} rows for transaction {transaction.id}"
                    )
                    updated_tx = Transaction.objects.get(id=transaction.id)
                    logger.info(
                        f"Transaction {transaction.id} after update: payee={updated_tx.payee}, classification_type={updated_tx.classification_type}, worksheet={updated_tx.worksheet}, confidence={updated_tx.confidence}, category={updated_tx.category}"
                    )
                messages.success(
                    request,
                    f"Successfully processed {queryset.count()} transactions with {agent.name}",
                )
            except Exception as e:
                logger.error(
                    f"Error processing transactions with {agent.name}: {str(e)}",
                    exc_info=True,
                )
                messages.error(
                    request,
                    f"Error processing transactions with {agent.name}: {str(e)}",
                )

        return process_with_agent

    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = extra_context or {}
        task = self.get_object(request, object_id)
        # Always read-only
        extra_context["hide_save"] = True
        # Auto-refresh if running
        if task and task.status in ["pending", "processing"]:
            extra_context["auto_refresh"] = True
        # --- Real-time log display logic (single window) ---
        import os
        from django.conf import settings
        from pathlib import Path

        log_file = Path(settings.BASE_DIR) / "logs" / f"task_{task.task_id}.log"
        log_content = None
        if task:
            if task.status in ["pending", "processing"] and log_file.exists():
                # While running, read log file from disk for real-time updates
                try:
                    with open(log_file, "r") as f:
                        log_content = mark_safe(
                            '<pre style="max-height:500px;overflow:auto;background:#222;color:#eee;padding:10px;">{}</pre>'.format(f.read())
                        )
                except Exception:
                    log_content = mark_safe('<pre style="color:red;">Error reading log file.</pre>')
            else:
                # After completion, show archived DB log
                if hasattr(task, "task_log") and task.task_log:
                    log_content = mark_safe(
                        '<pre style="max-height:500px;overflow:auto;background:#222;color:#eee;padding:10px;">{}</pre>'.format(task.task_log)
                    )
                else:
                    log_content = mark_safe('<pre style="color:#888;">No log available for this task.</pre>')
        else:
            log_content = mark_safe('<pre style="color:#888;">No task found.</pre>')
        extra_context["log_content"] = log_content
        return super().change_view(
            request, object_id, form_url, extra_context=extra_context
        )

    # --- Shared agent processing logic for direct and batch flows ---
    def process_transactions_with_agent(self, agent_name, transaction_ids):
        from .models import Transaction, Agent

        agent = Agent.objects.get(name=agent_name)
        results = []
        for transaction in Transaction.objects.filter(id__in=transaction_ids):
            response, tool_usage = call_agent(agent.name, transaction)
            update_fields = get_update_fields_from_response(
                agent,
                response,
                (
                    getattr(agent, "purpose", "").lower()
                    if hasattr(agent, "purpose")
                    else "classification"
                ),
                tool_usage=tool_usage,
            )
            Transaction.objects.filter(id=transaction.id).update(**update_fields)
            results.append((transaction.id, update_fields))
        return results

    # --- Restore direct lookup/classify actions ---
    @admin.action(description="Lookup payee for selected transactions")
    def lookup_payee(self, modeladmin, request, queryset):
        agent_name = "Payee Lookup Agent"
        transaction_ids = list(queryset.values_list("id", flat=True))
        self.process_transactions_with_agent(agent_name, transaction_ids)
        messages.success(
            request, f"Processed {len(transaction_ids)} transactions with {agent_name}"
        )

    @admin.action(description="Classify selected transactions")
    def classify_transactions(self, modeladmin, request, queryset):
        agent_name = "Classification Agent"
        transaction_ids = list(queryset.values_list("id", flat=True))
        self.process_transactions_with_agent(agent_name, transaction_ids)
        messages.success(
            request, f"Processed {len(transaction_ids)} transactions with {agent_name}"
        )


@admin.register(LLMConfig)
class LLMConfigAdmin(admin.ModelAdmin):
    list_display = ("provider", "model", "url")
    search_fields = ("provider", "model")
    exclude = ("id",)  # Prevent manual id entry in admin


@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    list_display = ("name", "purpose", "llm")
    search_fields = ("name", "purpose", "llm__name")
    filter_horizontal = ("tools",)
    readonly_fields = ("name",)  # Make name read-only to prevent breaking the app
    change_form_template = "admin/agent_change_form.html"  # Use model-specific template

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<int:agent_id>/preview_prompt/",
                self.admin_site.admin_view(self.preview_prompt_view),
                name="profiles_agent_preview_prompt",
            ),
        ]
        return custom_urls + urls

    def preview_prompt_view(self, request, agent_id):
        agent = get_object_or_404(Agent, pk=agent_id)
        # Use a sample transaction and business profile for context
        transaction = Transaction.objects.first()
        business_profile = (
            transaction.client if transaction else BusinessProfile.objects.first()
        )
        # Build prompt as in call_agent
        if "payee" in agent.name.lower():
            system_prompt = """You are a diligent business researcher. Your job is to:\n1. Identify the payee/merchant from transaction descriptions\n2. Use the search tool to gather comprehensive vendor information\n3. Synthesize all information into a clear, normalized description\n4. Return a final response in the exact JSON format specified\n\nIMPORTANT RULES:\n1. Make as many search calls as needed to gather complete information\n2. Synthesize all information into a clear, normalized response\n3. NEVER use the raw transaction description in your final response\n4. Format the response exactly as specified"""
            user_prompt = f"""Analyze this transaction and return a JSON object with EXACTLY these field names:\n{{\n    \"normalized_description\": \"string - A VERY SUCCINCT 1-5 word summary of what was purchased/paid for (e.g., 'Grocery shopping', 'Fast food purchase', 'Office supplies'). DO NOT include vendor details, just the core type of purchase.\",\n    \"payee\": \"string - The normalized payee/merchant name (e.g., 'Lowe's' not 'LOWE'S #1636', 'Walmart' not 'WALMART #1234')\",\n    \"confidence\": \"string - Must be exactly 'high', 'medium', or 'low'\",\n    \"reasoning\": \"string - VERBOSE explanation of the identification, including all search results and any details about the vendor, business type, and what was purchased. If you have a long description, put it here, NOT in normalized_description.\",\n    \"transaction_type\": \"string - One of: purchase, payment, transfer, fee, subscription, service\",\n    \"questions\": \"string - Any questions about unclear elements\",\n    \"needs_search\": \"boolean - Whether additional vendor information is needed\"\n}}\n\nTransaction: {transaction.description if transaction else '[No transaction]'}\nAmount: ${transaction.amount if transaction else '[No amount]'}\nDate: {transaction.transaction_date if transaction else '[No date]'}\n\nIMPORTANT INSTRUCTIONS:\n1. The 'normalized_description' MUST be a short phrase (1-5 words) summarizing the purchase type.\n2. Place any verbose or detailed explanation in the 'reasoning' field.\n3. NEVER use the raw transaction description in your final response.\n4. Include the type of business and what was purchased in the reasoning, not in normalized_description.\n5. Reference all search results used in the reasoning field.\n6. NEVER include store numbers, locations, or other non-standard elements in the payee field.\n7. Normalize the payee name to its standard business name (e.g., 'Lowe's' not 'LOWE'S #1636').\n8. ALWAYS provide a final JSON response after gathering all necessary information."""
        else:
            from profiles.models import IRSExpenseCategory, BusinessExpenseCategory

            # IRS categories (active, for all relevant worksheets)
            irs_cats = IRSExpenseCategory.objects.filter(
                is_active=True, worksheet__name__in=["6A", "Auto", "HomeOffice"]
            ).values("id", "name", "worksheet__name")
            # Business categories for this client
            biz_cats = (
                BusinessExpenseCategory.objects.filter(
                    is_active=True, business=business_profile
                ).values("id", "category_name", "worksheet__name")
                if business_profile
                else []
            )
            allowed_categories = []
            for cat in irs_cats:
                allowed_categories.append(
                    f"IRS-{cat['id']}: {cat['name']} (worksheet: {cat['worksheet__name']})"
                )
            for cat in biz_cats:
                allowed_categories.append(
                    f"BIZ-{cat['id']}: {cat['category_name']} (worksheet: {cat['worksheet__name']})"
                )
            allowed_categories += ["Other", "Personal", "Review"]
            # Build business profile context string
            business_context_lines = []
            if business_profile:
                if business_profile.business_type:
                    business_context_lines.append(
                        f"Business Type: {business_profile.business_type}"
                    )
                if business_profile.business_description:
                    business_context_lines.append(
                        f"Business Description: {business_profile.business_description}"
                    )
                if business_profile.contact_info:
                    business_context_lines.append(
                        f"Contact Info: {business_profile.contact_info}"
                    )
                if business_profile.common_expenses:
                    business_context_lines.append(
                        f"Common Expenses: {business_profile.common_expenses}"
                    )
                if business_profile.custom_categories:
                    business_context_lines.append(
                        f"Custom Categories: {business_profile.custom_categories}"
                    )
                if business_profile.industry_keywords:
                    business_context_lines.append(
                        f"Industry Keywords: {business_profile.industry_keywords}"
                    )
                if business_profile.category_patterns:
                    business_context_lines.append(
                        f"Category Patterns: {business_profile.category_patterns}"
                    )
                if business_profile.business_rules:
                    business_context_lines.append(
                        f"Business Rules: {business_profile.business_rules}"
                    )
            business_context = "\n".join(business_context_lines)
            if business_context:
                business_context = f"Business Profile Context:\n{business_context}\n"
            else:
                business_context = ""
            # Add payee reasoning if available
            payee_reasoning = (
                getattr(transaction, "payee_reasoning", None) if transaction else None
            )
            if payee_reasoning:
                payee_context = (
                    f"Payee Reasoning (detailed vendor info):\n{payee_reasoning}\n"
                )
            else:
                payee_context = ""
            system_prompt = """You are a professional auditor and accountant. Your job is to:\n1. Analyze transactions and determine if they are business or personal expenses\n2. For business expenses, determine the appropriate worksheet (6A, Vehicle, HomeOffice, or Personal)\n3. Provide detailed reasoning for your decisions\n4. Flag any transactions that need additional review\n\nConsider these factors:\n- Business type and description\n- Industry context\n- Transaction patterns\n- Amount and frequency\n- Business rules and patterns"""
            user_prompt = f"""{business_context}{payee_context}Return your analysis in this exact JSON format:\n{{\n    \"classification_type\": \"business\" or \"personal\",\n    \"worksheet\": \"6A\" or \"Vehicle\" or \"HomeOffice\" or \"Personal\",\n    \"category_name\": \"Name of the selected category from the list below\",\n    \"confidence\": \"high\" or \"medium\" or \"low\",\n    \"reasoning\": \"Detailed explanation of your decision, referencing both the business profile and payee reasoning above.\",\n    \"business_percentage\": \"integer - 0 for personal, 100 for clear business, 50 for dual-purpose, etc.\",\n    \"questions\": \"Any questions or uncertainties about this classification\",\n    \"proposed_category_name\": \"If you chose 'Review', propose a new category name that best fits the transaction. Otherwise, leave blank.\"\n}}\n\nTransaction: {transaction.description if transaction else '[No transaction]'}\nAmount: ${transaction.amount if transaction else '[No amount]'}\nDate: {transaction.transaction_date if transaction else '[No date]'}\n\nAllowed Categories (choose ONLY from this list):\n{chr(10).join(allowed_categories)}\n\nIMPORTANT RULES:\n- You MUST use one of the allowed category_id values above.\n- If the expense is business-related but does not fit any allowed category, use 'Review' and propose a new category name.\n- Only use 'Other' if it is a genuine, catch-all business category (e.g., 'Other Expenses', 'Miscellaneous', 'Check', 'Payment').\n- If the expense is not business-related, use 'Personal'.\n- NEVER invent a new category unless you use 'Review' and fill in 'proposed_category_name'.\n- For business expenses, use the most specific category that matches.\n- ALWAYS provide a business_percentage field as described above.\n- Use the payee reasoning above as additional context for your decision.\n\nIMPORTANT: Your response must be a valid JSON object."""
        admin_context = self.admin_site.each_context(request)
        log_message = f"Prompt generated using agent: {agent.name} (ID: {agent.id})"
        context = {
            "agent": agent,
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "log_message": log_message,
        }
        context.update(admin_context)
        return render(
            request,
            "admin/agent_prompt_preview.html",
            context,
        )

    def change_view(self, request, object_id, form_url="", extra_context=None):
        # Agents are standalone; do not inject client or checklist context
        return super().change_view(request, object_id, form_url, extra_context=extra_context)


@admin.register(Tool)
class ToolAdmin(admin.ModelAdmin):
    list_display = ("name", "description", "module_path")
    search_fields = ("name", "description", "module_path")


@admin.register(IRSWorksheet)
class IRSWorksheetAdmin(admin.ModelAdmin):
    list_display = ("name", "description", "is_active")
    search_fields = ("name", "description")
    list_filter = ("is_active",)


@admin.register(IRSExpenseCategory)
class IRSExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "worksheet", "line_number", "is_active")
    search_fields = ("name", "description", "line_number")
    list_filter = ("worksheet", "is_active")
    ordering = ("worksheet", "line_number")


@admin.register(BusinessExpenseCategory)
class BusinessExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = (
        "category_name",
        "business",
        "worksheet",
        "parent_category",
        "is_active",
    )
    search_fields = ("category_name", "description")
    list_filter = ("business", "worksheet", "is_active", "tax_year")
    ordering = ("business", "category_name")


@admin.register(ProcessingTask)
class ProcessingTaskAdmin(admin.ModelAdmin):
    list_display = (
        "action_checkbox",
        "short_task_id",
        "task_type",
        "client",
        "status_with_progress",
        "transaction_count",
        "processed_count",
        "error_count",
        "created_at",
        "updated_at",
    )
    list_filter = (
        "task_type",
        "status",
        "client",
        "created_at",
        "updated_at",
    )
    search_fields = (
        "task_id",
        "client__client_id",
        "error_details",
        "task_metadata",
    )
    readonly_fields = (
        "task_id",
        "task_type",
        "client",
        "status",
        "transaction_count",
        "processed_count",
        "error_count",
        "created_at",
        "updated_at",
        "error_details",
        "task_metadata",
    )
    exclude = ("task_log",)
    actions = ["retry_failed_tasks", "cancel_tasks", "run_task"]

    @admin.display(description="Status")
    def status_with_progress(self, obj):
        status = obj.status
        badge_map = {
            "pending": ("⏳ Pending", "background:#f6c23e;color:#fff;"),
            "processing": ("🔄 Processing", "background:#36b9cc;color:#fff;"),
            "completed": ("✅ Completed", "background:#1cc88a;color:#fff;"),
            "failed": ("❌ Failed", "background:#e74a3b;color:#fff;"),
        }
        label, style = badge_map.get(status, (status.title(), ""))
        badge_html = f'<span style="font-weight:bold;padding:0.2em 0.7em;border-radius:1em;{style}font-size:0.95em;display:inline-block;margin-right:0.5em;min-width:80px;white-space:nowrap;">{label}</span>'
        progress_html = ""
        if status == "processing":
            processed = getattr(obj, "processed_count", 0) or 0
            total = getattr(obj, "transaction_count", 0) or 0
            percent = int((processed / total) * 100) if total > 0 else 0
            progress_html = f"""
                <div style="border-radius:3px;overflow:hidden;background:#f0f0f0;border:1px solid #ccc;height:20px;width:200px;margin-top:5px;">
                  <div style="background:#79aec8;height:100%;width:{percent}%;transition:width 0.3s ease;"></div>
                </div>
                <div style="font-size:12px;color:#666;margin-top:2px;">{processed} / {total}</div>
            """
        return mark_safe(badge_html + progress_html)

    @admin.display(description="Task ID", ordering="task_id")
    def short_task_id(self, obj):
        url = reverse('admin:profiles_processingtask_change', args=[obj.pk])
        short = str(obj.task_id).split('-')[0]
        return format_html('<a href="{}">{}</a>', url, short)

    def get_row_attributes(self, obj, index):
        return {'data-object-pk': str(obj.pk)}

    def run_task(self, request, queryset):
        """Execute the selected task and show progress."""
        if queryset.count() > 1:
            messages.error(request, "Please select only one task to run at a time.")
            return

        task = queryset.first()
        if task.status != "pending":
            messages.error(request, f"Task {task.task_id} is not in pending state.")
            return

        # Create log file first
        log_file = Path(settings.BASE_DIR) / "logs" / f"task_{task.task_id}.log"
        log_file.parent.mkdir(exist_ok=True)
        with open(log_file, "w") as f:
            f.write(f"[{timezone.now()}] [INFO] Starting task {task.task_id}\n")

        try:
            # Verify the task exists and is in pending state
            task.refresh_from_db()
            if task.status != "pending":
                messages.error(request, f"Task {task.task_id} is not in pending state.")
                return

            # Update task status to processing and commit it
            with db_transaction.atomic():
                task.status = "processing"
                task.started_at = timezone.now()
                task.save(force_update=True)

            # Start the task processing command
            python_executable = sys.executable
            manage_py = str(Path(settings.BASE_DIR) / "manage.py")
            cmd = [
                python_executable,
                manage_py,
                "process_task",
                str(task.task_id),
                "--log-file",
                str(log_file),
            ]

            # Set up environment variables
            env = os.environ.copy()
            project_root = str(Path(settings.BASE_DIR).parent)
            env["PYTHONPATH"] = f"{project_root}:{env.get('PYTHONPATH', '')}"
            env["DJANGO_SETTINGS_MODULE"] = "ledgerflow.settings"

            # Start the process in the background
            subprocess.Popen(
                cmd,
                env=env,
                cwd=str(settings.BASE_DIR),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                start_new_session=True,
                bufsize=1,
            )
            messages.success(request, f"Started task {task.task_id} in background.")
        except Exception as e:
            messages.error(request, f"Failed to start task: {e}")

    run_task.short_description = "Run selected task"

    def retry_failed_tasks(self, request, queryset):
        """Retry failed processing tasks."""
        for task in queryset.filter(status="failed"):
            task.status = "pending"
            task.error_count = 0
            task.error_details = {}
            task.save()
            messages.success(request, f"Retrying task {task.task_id}")
        messages.success(
            request, f"Retried {queryset.filter(status='failed').count()} failed tasks"
        )

    retry_failed_tasks.short_description = "Retry failed tasks"

    def cancel_tasks(self, request, queryset):
        """Cancel selected processing tasks."""
        for task in queryset.filter(status__in=["pending", "processing"]):
            task.status = "failed"
            task.error_details = {
                "cancelled": True,
                "cancelled_at": str(datetime.now()),
            }
            task.save()
            messages.success(request, f"Cancelled task {task.task_id}")
        messages.success(
            request,
            f"Cancelled {queryset.filter(status__in=['pending', 'processing']).count()} tasks",
        )

    cancel_tasks.short_description = "Cancel selected tasks"

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path(
                '<path:object_id>/live_status/',
                self.admin_site.admin_view(self.live_status_view),
                name='profiles_processingtask_live_status',
            ),
            path(
                'batch_status/',
                self.admin_site.admin_view(self.batch_status_view),
                name='profiles_processingtask_batch_status',
            ),
        ]
        return custom_urls + urls

    def live_status_view(self, request, object_id):
        # Only staff users can access
        if not request.user.is_staff:
            return JsonResponse({'error': 'Forbidden'}, status=403)
        try:
            task = ProcessingTask.objects.get(task_id=object_id)
        except ProcessingTask.DoesNotExist:
            raise Http404()
        # Try to read the log file if task is running, else use DB field
        import os
        from django.conf import settings
        from pathlib import Path
        log_file = Path(settings.BASE_DIR) / "logs" / f"task_{task.task_id}.log"
        if task.status in ["pending", "processing"] and log_file.exists():
            with open(log_file, "r") as f:
                log_content = f.read()
        else:
            log_content = task.task_log or ""
        return JsonResponse({
            "log": log_content,
            "processed_count": task.processed_count,
            "transaction_count": task.transaction_count,
            "status": task.status,
        })

    def batch_status_view(self, request):
        # Only staff users can access
        if not request.user.is_staff:
            return JsonResponse({'error': 'Forbidden'}, status=403)
        ids = request.GET.getlist('ids[]')
        tasks = ProcessingTask.objects.filter(task_id__in=ids)
        result = {}
        for task in tasks:
            result[str(task.task_id)] = {
                "status": task.status,
                "processed_count": task.processed_count,
                "transaction_count": task.transaction_count,
            }
        return JsonResponse(result)


def _get_agent_type(agent):
    name = getattr(agent, "name", "").lower()
    if "payee" in name:
        return "payee"
    if "classif" in name or "escalation" in name:
        return "classification"
    raise ValueError(f"Unknown agent type for agent name: {name}")
