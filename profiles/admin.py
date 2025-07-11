from django.contrib import admin
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
from profiles.prompt_utils import get_fallback_payee_prompts
import jinja2

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
    business_description = forms.CharField(
        required=True,
        widget=forms.Textarea(attrs={"rows": 3, "cols": 60}),
        help_text="Describe your business in your own words. The AI will generate the rest of your business profile.",
    )
    contact_info = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 2, "cols": 60}),
        help_text="Contact information for the business (optional).",
    )
    common_expenses = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "rows": 2,
                "cols": 60,
                "style": "min-height:60px;resize:vertical;width:100%;overflow:auto;",
            }
        ),
        help_text="",
    )
    custom_categories = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "rows": 2,
                "cols": 60,
                "style": "min-height:60px;resize:vertical;width:100%;overflow:auto;",
            }
        ),
        help_text="",
    )
    industry_keywords = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "rows": 2,
                "cols": 60,
                "style": "min-height:60px;resize:vertical;width:100%;overflow:auto;",
            }
        ),
        help_text="",
    )
    category_patterns = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "rows": 2,
                "cols": 60,
                "style": "min-height:60px;resize:vertical;width:100%;overflow:auto;",
            }
        ),
        help_text="",
    )
    business_rules = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "rows": 2,
                "cols": 60,
                "style": "min-height:60px;resize:vertical;width:100%;overflow:auto;",
            }
        ),
        help_text="",
    )

    class Meta:
        model = BusinessProfile
        fields = [
            "company_name",
            "business_type",
            "business_description",
            "contact_info",
            "location",
            "common_expenses",
            "custom_categories",
            "industry_keywords",
            "category_patterns",
            "business_rules",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in [
            "common_expenses",
            "custom_categories",
            "industry_keywords",
            "category_patterns",
            "business_rules",
        ]:
            val = getattr(self.instance, field, None)
            if val:
                if isinstance(val, dict):
                    val = ", ".join(f"{k}: {v}" for k, v in val.items())
                elif isinstance(val, list):
                    val = ", ".join(str(x) for x in val)
                elif isinstance(val, str):
                    val = val.replace("{", "").replace("}", "")
                    val = ", ".join([v.strip() for v in val.split(",") if v.strip()])
                # Ensure only one space after each comma (UI formatting)
                val = re.sub(r",\s*", ", ", val)
            else:
                val = ""
            self.fields[field].initial = val


@admin.register(BusinessProfile)
class BusinessProfileAdmin(admin.ModelAdmin):
    form = BusinessProfileAdminForm
    list_display = ("company_name", "business_type")
    search_fields = ("company_name", "business_description")
    fieldsets = (
        (
            "User-Defined Profile",
            {
                "fields": ("company_name", "contact_info", "business_description"),
                "description": "Enter the company name, contact info, and a business description. The AI will generate the rest.",
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
            from django.urls import reverse
            from django.utils.html import format_html

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
            from django.contrib import messages

            messages.error(request, "BusinessProfile not found.")
            return redirect("..")
        try:
            from openai import OpenAI
            import os
            import json
            from django.urls import reverse
            from .models import Agent
            import jinja2

            # Robust: search for agent by name containing either 'business profile generator' or 'business profile generation'
            agent = Agent.objects.filter(
                name__icontains="business profile generator"
            ).first()
            if not agent:
                agent = Agent.objects.filter(
                    name__icontains="business profile generation"
                ).first()
            if not agent or not agent.llm or not agent.llm.model:
                from django.contrib import messages

                messages.error(
                    request,
                    "No Business Profile Generator agent with LLM configured in UI. Please create or update an agent with name containing 'Business Profile Generator' or 'Business Profile Generation' and assign an LLM config.",
                )
                return redirect("..")
            model = agent.llm.model
            base_url = agent.llm.url
            api_key = os.environ.get("OPENAI_API_KEY")
            # Render prompt from UI (Jinja2)
            try:
                env = jinja2.Environment(undefined=jinja2.StrictUndefined)
                template = env.from_string(agent.prompt)
                rendered = template.render(business_profile=obj)
                if "---USER---" in rendered:
                    system_prompt, user_prompt = rendered.split("---USER---", 1)
                else:
                    system_prompt = rendered
                    user_prompt = ""
            except Exception as e:
                from django.contrib import messages

                messages.error(request, f"Failed to render agent prompt: {e}")
                return redirect(
                    reverse("admin:profiles_businessprofile_change", args=[obj.pk])
                )
            # Log the actual prompts being sent
            logger.info(f"System Prompt Sent: {system_prompt!r}")
            logger.info(f"User Prompt Sent: {user_prompt!r}")
            # Use LLMConfig.url as base_url if set
            if base_url:
                client = OpenAI(api_key=api_key, base_url=base_url)
            else:
                client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content
            print(f"Raw LLM response: {content}")
            try:
                data = json.loads(content)
            except Exception as e:
                from django.contrib import messages

                messages.error(
                    request, f"LLM did not return valid JSON. Raw response: {content}"
                )
                return redirect(
                    reverse("admin:profiles_businessprofile_change", args=[obj.pk])
                )
            if not isinstance(data, dict) or not any(data.values()):
                from django.contrib import messages

                messages.warning(
                    request,
                    f"AI response was empty or missing fields. Raw response: {content}. If this persists, check the prompt and schema format sent to the LLM.",
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
            from django.contrib import messages

            messages.success(
                request,
                "AI-generated profile fields have been filled in. Review and save to persist.",
            )
        except Exception as e:
            import logging

            logging.exception("Error generating AI profile")
            from django.contrib import messages

            messages.error(request, f"Error generating AI profile: {e}")
            return redirect(
                reverse("admin:profiles_businessprofile_change", args=[obj.pk])
            )
        from django.urls import reverse

        return redirect(reverse("admin:profiles_businessprofile_change", args=[obj.pk]))


class ClientFilter(admin.SimpleListFilter):
    title = _("client")
    parameter_name = "client"

    def lookups(self, request, model_admin):
        clients = set(
            Transaction.objects.values_list("client__company_name", flat=True)
        )
        return [(client, client) for client in clients]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(client__company_name=self.value())
        return queryset


def build_allowed_categories(transaction):
    from .models import IRSExpenseCategory, BusinessExpenseCategory

    irs_cats = IRSExpenseCategory.objects.filter(
        worksheet__name="6A", is_active=True
    ).order_by("line_number")
    biz_cats = BusinessExpenseCategory.objects.filter(
        business=transaction.client, worksheet__name="6A", is_active=True
    ).order_by("category_name")
    lines = []
    for cat in irs_cats:
        lines.append(f"IRS-{cat.line_number}: {cat.name}")
    for cat in biz_cats:
        lines.append(f"BIZ-{cat.id}: {cat.category_name}")
    lines.append("Other: Other Expenses")
    lines.append("Personal: Personal")
    lines.append("Review: Review (propose a new category)")
    return "\n".join(lines)


def call_agent(
    agent_name, transaction, model=None, max_retries=2, escalate_on_fail=True
):
    """Call the specified agent with the transaction data."""
    import os
    from openai import OpenAI

    logger = logging.getLogger(__name__)
    try:
        agent = Agent.objects.get(name=agent_name)
        # Ensure tool_definitions is always defined
        tool_definitions = []
        if hasattr(agent, "tools"):
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
        # Patch: always build allowed_categories for classification agents
        is_classification = (
            "classification" in (agent.purpose or "").lower()
            or "classification" in (agent.name or "").lower()
        )
        allowed_categories = ""
        if is_classification:
            allowed_categories = build_allowed_categories(transaction)
            logger.info(f"Allowed categories sent to LLM:\n{allowed_categories}")
        context = {
            "transaction": transaction,
            "allowed_categories": allowed_categories,
            "business_profile": getattr(transaction, "client", None),
            "payee_reasoning": getattr(transaction, "payee_reasoning", None),
        }
        # Always use Agent.prompt (UI template) as primary for ALL agents
        template_rendered = False
        system_prompt = None
        user_prompt = None
        if agent.prompt:
            try:
                env = jinja2.Environment(undefined=jinja2.StrictUndefined)
                template = env.from_string(agent.prompt)
                rendered = template.render(**context)
                # Split into system/user if delimiter present, else use as system
                if "---USER---" in rendered:
                    system_prompt, user_prompt = rendered.split("---USER---", 1)
                else:
                    system_prompt = rendered
                    user_prompt = ""
                template_rendered = True
                logger.info(
                    "[PROMPT] Used Agent.prompt from UI for agent '%s'", agent_name
                )
            except Exception as e:
                logger.warning(
                    f"[PROMPT] Failed to render Agent.prompt for agent '%s': %s. Falling back.",
                    agent_name,
                    e,
                )
        if not template_rendered:
            # Use fallback for any agent type if template missing or fails
            if "payee" in agent_name.lower():
                system_prompt, user_prompt = get_fallback_payee_prompts(transaction)
                logger.info(
                    "[PROMPT] Used fallback payee prompt for agent '%s'", agent_name
                )
            else:
                # Generic fallback for other agents (can be improved with more helpers)
                system_prompt = "Classification fallback prompt not implemented."
                user_prompt = ""
                logger.info(
                    "[PROMPT] Used fallback generic prompt for agent '%s'", agent_name
                )
        # Log the actual prompts being sent
        logger.info(f"System Prompt Sent: {system_prompt!r}")
        logger.info(f"User Prompt Sent: {user_prompt!r}")
        # Model selection logic: ONLY use agent.llm.model from UI
        if not (agent.llm and agent.llm.model):
            logger.error(
                f"Agent '{agent_name}' does not have an LLM model configured in the UI. Aborting."
            )
            raise ValueError(
                f"Agent '{agent_name}' does not have an LLM model configured in the UI."
            )
        model = agent.llm.model
        # Log the actual model and tools used right before the API call
        logger.info(f"Using OpenAI model: {model}")
        if tool_definitions:
            logger.info(f"Tools passed to LLM: {[t['name'] for t in tool_definitions]}")
        else:
            logger.info("No tools passed to LLM for this agent.")
        # ... existing code to call LLM ...
        try:
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
            if tool_definitions:
                tools = tool_definitions
            else:
                tools = None
            max_tool_calls = 3
            tool_call_count = 0
            tool_usage_counter = {}
            while True:
                payload = {
                    "model": model,
                    "messages": messages,
                    "response_format": {"type": "json_object"},
                }
                if tools:
                    payload["tools"] = tools
                    payload["tool_choice"] = "auto"
                response = client.chat.completions.create(**payload)
                logger.info(f"Raw LLM Response: {response}")
                msg = response.choices[0].message
                # If the LLM returns a tool call, append the assistant message and then the tool message(s)
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    if tool_call_count >= max_tool_calls:
                        messages.append(
                            {
                                "role": "user",
                                "content": "Maximum search limit reached. Now provide your final response in the exact JSON format specified.",
                            }
                        )
                        continue
                    # 1. Append the assistant message with tool_calls
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
                    # 2. For each tool_call, execute and append a tool message
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
                            # Track tool usage
                            tool_usage_counter[tool_name] = (
                                tool_usage_counter.get(tool_name, 0) + 1
                            )
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
                        tool_call_count += 1
                    continue
                # If the LLM returns a final content message, parse and return it
                if msg.content:
                    try:
                        result = json.loads(msg.content)
                        if tool_usage_counter:
                            result["_tool_usage"] = tool_usage_counter
                        return result
                    except Exception as e:
                        logger.warning(
                            f"[PROMPT] LLM returned non-JSON content: {msg.content!r} (error: {e})"
                        )
                        return {}
                logger.error(
                    "LLM returned neither tool_calls nor content. Breaking loop."
                )
                break
            logger.warning(
                "[PROMPT] LLM returned None or invalid response. Returning empty dict."
            )
            return {}
        except Exception as e:
            logger.error(f"Error calling OpenAI API: {str(e)}")
            return {}

    except Exception as e:
        logger.error(f"Error in call_agent: {str(e)}")
        raise


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
            response = call_agent(agent.name, transaction)
            logger.info(f"Agent response: {response}")
            # Robust agent_type mapping
            purpose = (
                getattr(agent, "purpose", "").lower()
                if hasattr(agent, "purpose")
                else ""
            )
            name = getattr(agent, "name", "").lower() if hasattr(agent, "name") else ""
            if "payee" in purpose or "payee" in name:
                agent_type = "payee"
            else:
                agent_type = "classification"
            # Detect tool usage from response if present
            tool_usage = None
            if isinstance(response, dict) and "_tool_usage" in response:
                tool_usage = response.pop("_tool_usage")
            update_fields = get_update_fields_from_response(
                agent,
                response,
                agent_type,
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
        # Always set classification_method to 'Human' (the correct CHOICE value) if saving via admin form
        instance.classification_method = "Human"
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
        "file_path",
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

        # Group transactions by client
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

        # Create a task for each client's transactions
        for client_id, data in client_transactions.items():
            with db_transaction.atomic():
                task = ProcessingTask.objects.create(
                    task_type="payee_lookup",
                    client=data["client"],
                    transaction_count=len(data["transactions"]),
                    status="pending",
                    task_metadata={
                        "description": f"Batch payee lookup for {len(data['transactions'])} transactions"
                    },
                )
                task.transactions.add(*data["transaction_ids"])
                messages.success(
                    request,
                    f"Created payee lookup task for client {client_id} with {len(data['transactions'])} transactions",
                )

    batch_payee_lookup.short_description = "Create batch payee lookup task"

    def batch_classify(self, request, queryset):
        """Create a batch processing task for classification."""
        if not queryset:
            messages.error(request, "No transactions selected.")
            return

        # Group transactions by client
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

        # Create a task for each client's transactions
        for client_id, data in client_transactions.items():
            with db_transaction.atomic():
                task = ProcessingTask.objects.create(
                    task_type="classification",
                    client=data["client"],
                    transaction_count=len(data["transactions"]),
                    status="pending",
                    task_metadata={
                        "description": f"Batch classification for {len(data['transactions'])} transactions"
                    },
                )
                task.transactions.add(*data["transaction_ids"])
                messages.success(
                    request,
                    f"Created classification task for client {client_id} with {len(data['transactions'])} transactions",
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
                    response = call_agent(agent.name, transaction)
                    logger.info(f"Agent response: {response}")
                    # Robust agent_type mapping
                    purpose = (
                        getattr(agent, "purpose", "").lower()
                        if hasattr(agent, "purpose")
                        else ""
                    )
                    name = (
                        getattr(agent, "name", "").lower()
                        if hasattr(agent, "name")
                        else ""
                    )
                    if "payee" in purpose or "payee" in name:
                        agent_type = "payee"
                    else:
                        agent_type = "classification"
                    # Detect tool usage from response if present
                    tool_usage = None
                    if isinstance(response, dict) and "_tool_usage" in response:
                        tool_usage = response.pop("_tool_usage")
                    update_fields = get_update_fields_from_response(
                        agent,
                        response,
                        agent_type,
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

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        # Remove 'Save and add another' and relabel 'Save and continue editing' to 'Save'
        extra_context = extra_context or {}
        extra_context["show_save_and_add_another"] = False
        extra_context["show_save_and_continue"] = True
        extra_context["save_as_continue"] = False
        extra_context["save_as"] = False
        extra_context["save_continue_label"] = "Save"
        return super().changeform_view(
            request, object_id, form_url, extra_context=extra_context
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
        "task_id",
        "task_type",
        "client",
        "status",
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
        "client__company_name",
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
    actions = ["retry_failed_tasks", "cancel_tasks", "run_task"]

    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = extra_context or {}
        task = self.get_object(request, object_id)
        # Always read-only
        extra_context["hide_save"] = True
        # Auto-refresh if running
        if task and task.status in ["pending", "processing"]:
            extra_context["auto_refresh"] = True
        # Add log viewer if log file exists
        import os
        from django.conf import settings
        from pathlib import Path

        log_file = Path(settings.BASE_DIR) / "logs" / f"task_{task.task_id}.log"
        if log_file.exists():
            try:
                with open(log_file, "r") as f:
                    lines = f.readlines()[-100:]
                log_content = mark_safe(
                    '<pre style="max-height:300px;overflow:auto;background:#222;color:#eee;padding:10px;">{}</pre>'.format(
                        "".join(lines)
                    )
                )
                extra_context["log_content"] = log_content
            except Exception:
                extra_context["log_content"] = mark_safe(
                    '<pre style="color:red;">Error reading log file.</pre>'
                )
        else:
            extra_context["log_content"] = mark_safe(
                '<pre style="color:#888;">No log file found for this task.</pre>'
            )
        return super().change_view(
            request, object_id, form_url, extra_context=extra_context
        )

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
            # Always use the manage.py in the LedgerFlow project root
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
            process = subprocess.Popen(
                cmd,
                env=env,
                cwd=str(settings.BASE_DIR),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                start_new_session=True,
                bufsize=1,
            )

            # Log the process start
            logger.info(f"Started task {task.task_id} with PID {process.pid}")
            self.message_user(request, f"Started task {task.task_id}")

            # Start a thread to read the output
            def read_output():
                while True:
                    output = process.stdout.readline()
                    if output == "" and process.poll() is not None:
                        break
                    if output:
                        logger.info(output.strip())
                        with open(log_file, "a") as f:
                            f.write(output)

            import threading

            output_thread = threading.Thread(target=read_output)
            output_thread.daemon = True
            output_thread.start()

            # Start a thread to read errors
            def read_errors():
                while True:
                    error = process.stderr.readline()
                    if error == "" and process.poll() is not None:
                        break
                    if error:
                        logger.error(error.strip())
                        with open(log_file, "a") as f:
                            f.write(f"[ERROR] {error}")

            error_thread = threading.Thread(target=read_errors)
            error_thread.daemon = True
            error_thread.start()

            # Wait for the process to complete
            def wait_for_process():
                process.wait()
                if process.returncode != 0:
                    logger.error(
                        f"Task {task.task_id} failed with return code {process.returncode}"
                    )
                    # Update task status to failed if the process failed
                    task.refresh_from_db()
                    if task.status == "processing":
                        task.status = "failed"
                        task.error_details = {
                            "error": f"Process failed with return code {process.returncode}"
                        }
                        task.save(force_update=True)

            # Start the wait thread
            wait_thread = threading.Thread(target=wait_for_process)
            wait_thread.daemon = True
            wait_thread.start()

        except Exception as e:
            logger.error(f"Failed to start task {task.task_id}: {str(e)}")
            task.status = "failed"
            task.error_details = {"error": str(e)}
            task.save(force_update=True)
            self.message_user(
                request, f"Failed to start task: {str(e)}", level=messages.ERROR
            )

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

    def view_task_transactions(self, request, task_id):
        """View transactions associated with a processing task."""
        task = get_object_or_404(ProcessingTask, task_id=task_id)
        transactions = task.transactions.all()
        return render(
            request,
            "admin/processing_task_transactions.html",
            context={
                "task": task,
                "transactions": transactions,
                "title": f"Transactions for Task {task_id}",
                "opts": self.model._meta,
            },
        )


# Restore the original StatementFileAdminForm for single-file upload
class StatementFileAdminForm(forms.ModelForm):
    file = forms.FileField(
        widget=forms.ClearableFileInput(), required=True, label="Upload File"
    )

    class Meta:
        model = StatementFile
        fields = [
            "client",
            "file",
            "file_type",
            "bank",
            "account_number",
            "year",
            "month",
            "status",
            "status_detail",
        ]


def get_parser_module_choices():
    try:
        sys.path.append("/Users/greg/repos/LedgerFlow_AI/PDF-extractor")
        from dataextractai.parsers_core.autodiscover import autodiscover_parsers

        autodiscover_parsers()
        registry_mod = importlib.import_module("dataextractai.parsers_core.registry")
        registry = getattr(registry_mod, "ParserRegistry")
        parser_names = list(getattr(registry, "_parsers", {}).keys())
        # Add 'autodetect' as the default option
        return [("autodetect", "Autodetect (Recommended)")] + [
            (name, name) for name in parser_names
        ]
    except Exception as e:
        print(f"[DEBUG] Exception in get_parser_module_choices: {e}")
        import traceback

        traceback.print_exc()
        return [("autodetect", "Autodetect (Recommended)")]


# Restore the batch uploader form (no multiple=True in widget)
class BatchStatementFileUploadForm(forms.Form):
    client = forms.ModelChoiceField(
        queryset=BusinessProfile.objects.all(), required=True
    )
    file_type = forms.ChoiceField(
        choices=StatementFile._meta.get_field("file_type").choices, required=True
    )
    parser_module = forms.ChoiceField(
        choices=[], required=False, label="Parser Module (optional)"
    )
    account_number = forms.CharField(label="Account Number (optional)", required=False)
    auto_parse = forms.BooleanField(
        label="Auto-parse and create transactions on upload",
        required=False,
        initial=True,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["parser_module"].choices = get_parser_module_choices()


@admin.register(StatementFile)
class StatementFileAdmin(admin.ModelAdmin):
    form = StatementFileAdminForm
    list_display = (
        "client",
        "original_filename",
        "file_type",
        "parser_module",
        "status",
        "upload_timestamp",
        "uploaded_by",
        "bank",
        "account_number",
        "account_holder_name",
        "address",
        "account_type",
        "statement_period_start",
        "statement_period_end",
        "statement_date",
        "year",
        "month",
        "status_detail",
    )
    list_filter = (
        "client",
        "file_type",
        "status",
        "year",
        "month",
        "bank",
        NeedsAccountNumberFilter,
    )
    search_fields = (
        "original_filename",
        "bank",
        "account_number",
        "account_holder_name",
        "address",
        "status_detail",
    )
    readonly_fields = (
        "upload_timestamp",
        "uploaded_by",
        "parsed_metadata",
        "parser_module",
        "file_link",
        "bank",
        "account_number",
        "account_holder_name",
        "address",
        "account_type",
        "statement_period_start",
        "statement_period_end",
        "statement_date",
        "year",
        "month",
        "status_detail",
    )
    fieldsets = (
        (
            None,
            {
                "fields": [
                    "client",
                    "file",
                    "file_type",
                    "parser_module",
                    "status",
                    "status_detail",
                    "bank",
                    "account_number",
                    "account_holder_name",
                    "address",
                    "account_type",
                    "statement_period_start",
                    "statement_period_end",
                    "statement_date",
                    "year",
                    "month",
                    "upload_timestamp",
                    "uploaded_by",
                    "parsed_metadata",
                    "file_link",
                ]
            },
        ),
    )
    actions = [
        "batch_set_account_number",
    ]

    def file_link(self, obj):
        if obj.file and hasattr(obj.file, "url"):
            return format_html(
                '<a href="{}" target="_blank">{}</a>', obj.file.url, obj.file.name
            )
        return "No file uploaded"

    file_link.short_description = "File Download Link"

    @admin.action(description="Batch set account number for selected statement files")
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
                    request, f"Set account number for {updated} statement files."
                )
                return
        else:
            form = AccountNumberForm()
        return render(
            request,
            "admin/batch_set_account_number.html",
            {"form": form, "queryset": queryset},
        )

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        from django.urls import reverse

        extra_context["batch_upload_url"] = reverse(
            "admin:profiles_statementfile_batch_upload"
        )
        return super().changelist_view(request, extra_context=extra_context)

    def batch_upload_view(self, request):
        if request.method == "POST":
            form = BatchStatementFileUploadForm(request.POST, request.FILES)
            if form.is_valid():
                client = form.cleaned_data["client"]
                file_type = form.cleaned_data["file_type"]
                parser_module = form.cleaned_data["parser_module"]
                account_number = form.cleaned_data["account_number"]
                auto_parse = form.cleaned_data["auto_parse"]
                files = request.FILES.getlist("files")
                uploaded_by = request.user if request.user.is_authenticated else None
                results = []
                import sys

                sys.path.append("/Users/greg/repos/LedgerFlow_AI/PDF-extractor")
                from dataextractai.parsers_core.autodiscover import autodiscover_parsers

                autodiscover_parsers()
                import importlib

                registry_mod = importlib.import_module(
                    "dataextractai.parsers_core.registry"
                )
                registry = getattr(registry_mod, "ParserRegistry")
                for f in files:
                    result = {"file": f.name}
                    temp_file_path = None
                    try:
                        import tempfile, os

                        with tempfile.NamedTemporaryFile(
                            delete=False, suffix=os.path.splitext(f.name)[1]
                        ) as temp_file:
                            for chunk in f.chunks():
                                temp_file.write(chunk)
                            temp_file_path = temp_file.name
                        # Detect parser if needed
                        used_parser = parser_module
                        if parser_module == "autodetect" or not parser_module:
                            from dataextractai.parsers.detect import (
                                detect_parser_for_file,
                            )

                            detected = detect_parser_for_file(temp_file_path)
                            if detected:
                                used_parser = detected
                                result["parser"] = detected
                            else:
                                result["error"] = "No compatible parser found."
                                results.append(result)
                                os.unlink(temp_file_path)
                                continue
                        # Get parser class from registry
                        parser_cls = registry.get_parser(used_parser)
                        if not parser_cls:
                            result["error"] = (
                                f"Parser '{used_parser}' not found in registry."
                            )
                            results.append(result)
                            os.unlink(temp_file_path)
                            continue
                        # Call main() and expect ParserOutput
                        parser_mod = importlib.import_module(parser_cls.__module__)
                        parser_main = getattr(parser_mod, "main")
                        try:
                            parser_output = parser_main(input_path=temp_file_path)
                        except Exception as e:
                            result["error"] = f"Parser error: {e}"
                            results.append(result)
                            os.unlink(temp_file_path)
                            continue
                        # Validate ParserOutput
                        try:
                            from dataextractai.parsers_core.models import ParserOutput

                            if not isinstance(parser_output, ParserOutput):
                                result["error"] = (
                                    f"Parser did not return ParserOutput. Got: {type(parser_output)}"
                                )
                                results.append(result)
                                os.unlink(temp_file_path)
                                continue
                        except Exception as e:
                            result["error"] = f"ParserOutput validation error: {e}"
                            results.append(result)
                            os.unlink(temp_file_path)
                            continue
                        # Extract metadata and transactions
                        metadata = (
                            parser_output.metadata.dict()
                            if parser_output.metadata
                            else {}
                        )
                        transactions = (
                            [t.dict() for t in parser_output.transactions]
                            if parser_output.transactions
                            else []
                        )
                        result["normalized"] = True
                        result["metadata"] = metadata
                        result["transaction_count"] = len(transactions)
                        if parser_output.errors:
                            result["errors"] = parser_output.errors
                        if parser_output.warnings:
                            result["warnings"] = parser_output.warnings
                        # Create StatementFile
                        try:
                            statement_file = StatementFile.objects.create(
                                client=client,
                                file=f,
                                file_type=file_type,
                                account_number=metadata.get(
                                    "account_number", account_number
                                ),
                                original_filename=f.name,
                                uploaded_by=uploaded_by,
                                status="uploaded",
                                bank=metadata.get("bank_name"),
                                year=metadata.get("year"),
                                month=metadata.get("month"),
                                parser_module=used_parser,
                                account_holder_name=metadata.get("account_holder_name"),
                                address=metadata.get("address"),
                                account_type=metadata.get("account_type"),
                                statement_period_start=metadata.get(
                                    "statement_period_start"
                                ),
                                statement_period_end=metadata.get(
                                    "statement_period_end"
                                ),
                                statement_date=metadata.get("statement_date"),
                                parsed_metadata=metadata,
                            )
                            result["statement_file"] = statement_file.id
                        except Exception as e:
                            result["error"] = f"StatementFile creation failed: {e}"
                            results.append(result)
                            os.unlink(temp_file_path)
                            continue
                        # Create transactions immediately after parsing
                        transactions_created = 0
                        transaction_errors = []
                        from profiles.models import Transaction

                        for idx, tx in enumerate(transactions):
                            try:
                                Transaction.objects.create(
                                    client=client,
                                    statement_file=statement_file,
                                    transaction_date=tx.get("transaction_date"),
                                    amount=tx.get("amount"),
                                    description=tx.get("description"),
                                    category=tx.get("category", ""),
                                    file_path=statement_file.file.name,
                                    source=tx.get("source", "batch_upload"),
                                    transaction_type=tx.get("transaction_type", ""),
                                    normalized_amount=tx.get("normalized_amount"),
                                    parser_name=used_parser,
                                    classification_method=tx.get(
                                        "classification_method", "None"
                                    ),
                                    payee_extraction_method=tx.get(
                                        "payee_extraction_method", "None"
                                    ),
                                )
                                transactions_created += 1
                            except Exception as e:
                                transaction_errors.append(
                                    {"index": idx, "error": str(e)}
                                )
                        result["transactions_created"] = transactions_created
                        result["transaction_errors"] = transaction_errors
                        # Optionally create ParsingRun (for audit, not for deferred processing)
                        if auto_parse and used_parser:
                            try:
                                ParsingRun.objects.create(
                                    statement_file=statement_file,
                                    parser_module=used_parser,
                                    status="completed",
                                )
                                result["parsing_run"] = "created"
                            except Exception as e:
                                result["parsing_run_error"] = str(e)
                        result["success"] = True
                        os.unlink(temp_file_path)
                    except Exception as e:
                        result["error"] = str(e)
                        if temp_file_path and os.path.exists(temp_file_path):
                            os.unlink(temp_file_path)
                    results.append(result)
                from django.urls import reverse
                from django.contrib import messages

                messages.success(
                    request, f"Processed {len(files)} files. See results below."
                )
                context = {
                    "form": form,
                    "results": results,
                    "title": "Batch Upload Statement Files",
                }
                context.update(self.admin_site.each_context(request))
                return render(
                    request, "admin/batch_upload_statement_files.html", context
                )
            else:
                context = {
                    "form": form,
                    "title": "Batch Upload Statement Files",
                }
                context.update(self.admin_site.each_context(request))
                return render(
                    request, "admin/batch_upload_statement_files.html", context
                )
        else:
            form = BatchStatementFileUploadForm()
            context = {
                "form": form,
                "title": "Batch Upload Statement Files",
            }
            context.update(self.admin_site.each_context(request))
            return render(request, "admin/batch_upload_statement_files.html", context)

    def get_urls(self):
        from django.urls import path

        urls = super().get_urls()
        custom_urls = [
            path(
                "batch-upload/",
                self.admin_site.admin_view(self.batch_upload_view),
                name="profiles_statementfile_batch_upload",
            ),
        ]
        return custom_urls + urls  # CUSTOM URLS FIRST


@admin.register(ParsingRun)
class ParsingRunAdmin(admin.ModelAdmin):
    list_display = (
        "statement_file",
        "parser_module",
        "status",
        "rows_imported",
        "short_error",
        "created",
    )
    search_fields = (
        "statement_file__original_filename",
        "parser_module",
        "error_message",
    )
    list_filter = ("status", "parser_module", "created")

    def short_error(self, obj):
        return (
            (obj.error_message[:60] + "...")
            if obj.error_message and len(obj.error_message) > 60
            else obj.error_message
        )

    short_error.short_description = "Error Message"


@admin.register(TaxChecklistItem)
class TaxChecklistItemAdmin(admin.ModelAdmin):
    list_display = (
        "business_profile",
        "tax_year",
        "form_code",
        "status",
        "enabled",
        "date_modified",
    )
    search_fields = (
        "business_profile__company_name",
        "tax_year",
        "form_code",
        "status",
    )
    list_filter = ("business_profile", "tax_year", "status", "enabled")
