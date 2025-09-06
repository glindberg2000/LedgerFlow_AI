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
    TaxYear,
    BinderItem,
    BinderItemField,
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
from profiles.utils.utils import get_update_fields_from_response
from profiles.utils.utils import sync_transaction_id_sequence
from profiles.utils.utils import extract_pdf_metadata
from profiles.utils.async_batch_processor import start_batch_processing
from profiles.utils.binder_item_options import get_all_binder_item_options
from django.template.response import TemplateResponse
from django.contrib.admin import AdminSite
from django.utils.safestring import mark_safe
import importlib
import pkgutil
from dataextractai.utils.normalize_api import normalize_parsed_data_df
from django.core.exceptions import ValidationError
import pandas as pd
import tempfile
# Removed fallback imports - NO FALLBACKS ALLOWED FOR FINANCIAL DATA
import jinja2
from django.forms import TextInput
from django.db import models
from organizers.models import OrganizerWorkbook

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
                name__icontains="business profile generation"
            ).first()
            if not agent:
                agent = Agent.objects.filter(
                    name__icontains="business profile generator"
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
            
            # Force reload environment and clean the API key (critical for GPT-5)
            load_dotenv(override=True)
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                # Clean API key to prevent "Illegal header value" errors - essential for GPT-5
                api_key = api_key.strip().replace('\n', '').replace('\r', '').replace(' ', '')
            if not api_key:
                messages.error(
                    request,
                    "OPENAI_API_KEY is not set in the environment. Set it in your .env or process env and retry.",
                )
                return redirect(
                    reverse("admin:profiles_businessprofile_change", args=[obj.pk])
                )
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
            # Increase timeout for GPT-5 which takes longer to process
            timeout_seconds = 120.0 if model == 'gpt-5' else 30.0
            if base_url:
                client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout_seconds)
            else:
                client = OpenAI(api_key=api_key, timeout=timeout_seconds)
            # Use OpenAI's structured outputs with JSON schema (standard API)
            business_profile_schema = {
                "type": "json_schema",
                "json_schema": {
                    "name": "business_profile_response",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "properties": {
                            "common_expenses": {
                                "type": "string",
                                "description": "Common business expenses for this industry/business type"
                            },
                            "custom_categories": {
                                "type": "string", 
                                "description": "Custom expense categories specific to this business"
                            },
                            "industry_keywords": {
                                "type": "string",
                                "description": "Keywords that identify transactions for this industry"
                            },
                            "category_patterns": {
                                "type": "string",
                                "description": "Patterns for categorizing transactions automatically"
                            },
                            "business_rules": {
                                "type": "string",
                                "description": "Business-specific rules for transaction processing"
                            }
                        },
                        "required": ["common_expenses", "custom_categories", "industry_keywords", "category_patterns", "business_rules"],
                        "additionalProperties": False
                    }
                }
            }
            
            # GPT-5 has different parameter requirements
            api_params = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt or "Generate business profile fields based on the business information provided."},
                ],
                "response_format": business_profile_schema,
            }
            
            # GPT-5 specific parameter handling (based on OpenAI GPT-5 migration guide)
            if model.startswith("gpt-5"):
                # GPT-5 is a reasoning model that REJECTS legacy parameters
                # GPT-5 uses tokens for internal reasoning FIRST, then for response
                # Remove token cap - let GPT-5 use whatever tokens needed for reasoning + response
                # Don't specify max_completion_tokens - use model default
                # GPT-5 enforces temperature=1 internally - DO NOT specify temperature
                # GPT-5 rejects: temperature, top_p, presence_penalty, frequency_penalty, 
                # logprobs, top_logprobs, logit_bias, stop, n
                # Use structured outputs (response_format) for deterministic results
                pass  # No additional parameters for GPT-5
            else:
                # Legacy models (GPT-4.1, etc.) support classic parameters
                api_params["max_tokens"] = 1000
                api_params["temperature"] = 0.7
            
            response = client.chat.completions.create(**api_params)
            # Extract structured data from JSON response
            content = response.choices[0].message.content
            print(f"Structured LLM response: {content}")
            
            try:
                data = json.loads(content)
            except Exception as e:
                from django.contrib import messages
                messages.error(
                    request, f"LLM did not return valid JSON. Raw response: {content}. Error: {e}"
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

            err_type = type(e).__name__
            # Provide more context to help debugging without exposing secrets
            debug_ctx = f"model={model!r}, base_url={(base_url or 'https://api.openai.com/v1')!r}, api_key_present={bool(api_key)}"
            cause = getattr(e, "__cause__", None)
            context_exc = getattr(e, "__context__", None)
            cause_str = f"; cause={cause!r}" if cause else ""
            context_str = f"; context={context_exc!r}" if context_exc else ""
            messages.error(
                request,
                f"Error generating AI profile ({err_type}). Details: {e}{cause_str}{context_str}. Context: {debug_ctx}",
            )
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
                logger.error(
                    f"[PROMPT] CRITICAL ERROR: Failed to render Agent.prompt for agent '{agent_name}': {e}",
                )
                # NEVER USE FALLBACKS FOR FINANCIAL DATA - ERROR OUT IMMEDIATELY
                raise ValueError(
                    f"Agent '{agent_name}' prompt template failed to render. "
                    f"This is financial data - no fallbacks allowed. "
                    f"Fix the template immediately. Error: {e}"
                )
        
        if not template_rendered:
            # NEVER USE FALLBACKS FOR FINANCIAL DATA - ERROR OUT IMMEDIATELY
            logger.error(f"[PROMPT] CRITICAL ERROR: No template rendered for agent '{agent_name}'")
            raise ValueError(
                f"Agent '{agent_name}' has no valid prompt template. "
                f"This is financial data - no fallbacks or guesswork allowed. "
                f"Configure a proper template immediately."
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
            # Force reload environment and clean the API key
            load_dotenv(override=True)
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                api_key = api_key.strip()  # Remove any whitespace/newlines
            logger.info(f"Using API key (first 10 chars): {api_key[:10] if api_key else 'None'}")
            client = OpenAI(api_key=api_key)
            # Ensure user_prompt contains "json" for json_object response format
            if user_prompt and "json" not in user_prompt.lower():
                user_prompt += "\n\nPlease respond with a valid JSON object."
            elif not user_prompt:
                user_prompt = "Please respond with a valid JSON object containing the requested information."
            
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
        help_text="Bookkeeper context or explanation for this transaction. Not used by AI unless explicitly included in the prompt.",
    )
    # Explicitly define as ChoiceField to force dropdown rendering in admin
    category = forms.ChoiceField(
        choices=[],  # Will be set dynamically in __init__
        required=False,
        label="Category",
        help_text="Select the most specific category. Use 'Review' if no category fits and propose a new one in notes.",
    )
    classification_type = forms.ChoiceField(
        choices=[],  # Will be set dynamically in __init__
        required=False,
        label="Classification Type",
    )
    worksheet = forms.ChoiceField(choices=[], required=False, label="Worksheet")
    transaction_type = forms.ChoiceField(
        choices=[], required=False, label="Transaction Type"
    )
    payee_extraction_method = forms.ChoiceField(
        choices=[
            ("AI", "AI Only"),
            ("AI+Search", "AI with Search"),
            ("Human", "Human Override"),
            ("None", "Not Processed"),
        ],
        required=False,
        label="Payee Extraction Method",
    )
    classification_method = forms.ChoiceField(
        choices=[
            ("AI", "AI Only"),
            ("Human", "Human Override"),
            ("Manual", "Manual"),
            ("None", "Not Processed"),
        ],
        required=False,
        label="Classification Method",
        disabled=True,
    )
    CLASSIFICATION_TYPE_CHOICES = [
        ("business", "Business"),
        ("personal", "Personal"),
    ]
    CANONICAL_TRANSACTION_TYPE_CHOICES = [
        ("debit", "Debit (Money Out)"),
        ("credit", "Credit (Money In)"),
        ("purchase", "Purchase"),
        ("refund", "Refund"),
        ("other", "Other/Custom"),
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
        review_choice = [("Review", "Review (propose a new category)")]
        choices = irs_choices + biz_choices + personal_choice + review_choice
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
        fields = "__all__"  # Ensure all model fields, including classification_method, are present
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
        # Worksheet dropdown: all active IRSWorksheet names + static options
        worksheet_choices = [
            (w.name, w.name) for w in IRSWorksheet.objects.filter(is_active=True)
        ]
        # Always add Personal and Review as static options
        worksheet_choices += [
            ("Personal", "Personal"),
            ("Review", "Review (propose a new worksheet)"),
        ]
        if self.instance.worksheet and self.instance.worksheet not in [
            c[0] for c in worksheet_choices
        ]:
            worksheet_choices = [
                (self.instance.worksheet, f"Current: {self.instance.worksheet}")
            ] + worksheet_choices
        self.fields["worksheet"].choices = worksheet_choices
        # Transaction type dropdown: canonical choices + legacy/custom values
        tx_types = list(
            Transaction.objects.exclude(transaction_type__isnull=True)
            .exclude(transaction_type="")
            .values_list("transaction_type", flat=True)
            .distinct()
        )
        tx_type_choices = self.CANONICAL_TRANSACTION_TYPE_CHOICES.copy()
        # Add legacy/custom values if not already present
        for t in tx_types:
            if t and t not in [c[0] for c in tx_type_choices]:
                tx_type_choices.append((t, f"Legacy/Custom: {t}"))
        if self.instance.transaction_type and self.instance.transaction_type not in [
            c[0] for c in tx_type_choices
        ]:
            tx_type_choices = [
                (
                    self.instance.transaction_type,
                    f"Current: {self.instance.transaction_type}",
                )
            ] + tx_type_choices
        tx_type_choices = [("", "--- Select ---")] + tx_type_choices
        self.fields["transaction_type"].choices = tx_type_choices
        # Make classification_method readonly (never user-editable)
        if "classification_method" in self.fields:
            self.fields["classification_method"].disabled = True
        # Questions field help text
        if "questions" in self.fields:
            self.fields["questions"].help_text = (
                "For AI or bookkeeper to record uncertainties or follow-up questions about this classification."
            )

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
        "transaction_type",  # Show type
        "bank_name",  # Custom method for bank
        "download_file_link",  # Download link now provides original filename
        "account_number",
        "short_reasoning",
        "short_payee_reasoning",
        "classification_method",
        "payee_extraction_method",
        "source",  # Move to end
        "parser_name",  # Move to end
    )
    list_filter = (
        ClientFilter,
        ProcessedFilter,
        NeedsAccountNumberFilter,
        "transaction_date",
        "classification_type",
        "worksheet",
        "confidence",
        "category",
        "source",
        "parser_name",
        "transaction_type",
        "classification_method",
        "payee_extraction_method",
        # Optionally add a custom filter for bank if needed
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
    readonly_fields = ("classification_method",)  # Only this should be readonly
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "client",
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
                    "account_number",
                    "transaction_type",
                    "file_path",
                    "source",
                    "statement_start_date",
                    "statement_end_date",
                    "parser_name",
                    "statement_file",
                    "questions",
                    "payee_extraction_method",
                    "classification_method",
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
        "batch_escalate_classification",
        "async_batch_payee_lookup",  # New async batch action
        "async_batch_classify",  # New async batch action
        "async_batch_full_workflow",  # New async batch action
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
        import logging
        from django import forms
        from django.shortcuts import render, redirect
        from django.urls import reverse
        from django.http import HttpResponseRedirect

        logger = logging.getLogger("django.request")

        class AccountNumberForm(forms.Form):
            account_number = forms.CharField(label="Account Number", required=True)

        if "apply" in request.POST:
            form = AccountNumberForm(request.POST)
            if form.is_valid():
                account_number = form.cleaned_data["account_number"]
                pks = list(queryset.values_list("pk", flat=True))
                logger.info(
                    f"Batch set account number action triggered. Setting account_number='{account_number}' for {len(pks)} transactions: {pks}"
                )
                updated = queryset.update(
                    account_number=account_number, needs_account_number=False
                )
                logger.info(
                    f"Batch set account number: Updated {updated} transactions."
                )
                self.message_user(
                    request, f"Set account number for {updated} transactions."
                )
                changelist_url = reverse("admin:profiles_transaction_changelist")
                return HttpResponseRedirect(changelist_url)
            else:
                logger.info(
                    f"Batch set account number: Form invalid. Errors: {form.errors}"
                )
        else:
            form = AccountNumberForm()
            if queryset.count() == 0:
                logger.info("Batch set account number: No transactions selected.")
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

    def batch_escalate_classification(self, request, queryset):
        """Create a batch processing task for classification escalation."""
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
                    task_type="classification_escalation",
                    client=data["client"],
                    transaction_count=len(data["transactions"]),
                    status="pending",
                    task_metadata={
                        "description": f"Batch escalation classification for {len(data['transactions'])} transactions"
                    },
                )
                task.transactions.add(*data["transaction_ids"])
                messages.success(
                    request,
                    f"Created escalation classification task for client {client_id} with {len(data['transactions'])} transactions",
                )

    batch_escalate_classification.short_description = "Create batch escalation task"

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

    def original_file_name(self, obj):
        if obj.statement_file and obj.statement_file.original_filename:
            return obj.statement_file.original_filename
        return "-"

    original_file_name.short_description = "Original File Name"

    def bank_name(self, obj):
        if obj.statement_file and obj.statement_file.bank:
            return obj.statement_file.bank
        return "-"

    bank_name.short_description = "Bank"

    def download_file_link(self, obj):
        if obj.statement_file and obj.statement_file.id:
            from django.urls import reverse

            return format_html(
                '<a href="{}" target="_blank">{}</a>',
                reverse(
                    "reports:download_statement_file", args=[obj.statement_file.id]
                ),
                obj.statement_file.original_filename or "Download",
            )
        return "-"

    download_file_link.short_description = "Download File"
    download_file_link.allow_tags = True

    @admin.action(description="Start Async Batch Payee Lookup (50 percent cost savings)")
    def async_batch_payee_lookup(self, request, queryset):
        """Start async batch processing for payee lookup using OpenAI Batch API."""
        transactions = list(queryset)
        start_batch_processing(transactions, "Payee Lookup Agent", request)

    async_batch_payee_lookup.short_description = "Async Batch Payee Lookup (50 percent cost savings)"

    @admin.action(description="Start Async Batch Classification (50 percent cost savings)")
    def async_batch_classify(self, request, queryset):
        """Start async batch processing for classification using OpenAI Batch API."""
        transactions = list(queryset)
        start_batch_processing(transactions, "Classification Agent", request)

    async_batch_classify.short_description = "Async Batch Classification (50 percent cost savings)"

    @admin.action(description="Start Async Batch Full Workflow (50 percent cost savings)")
    def async_batch_full_workflow(self, request, queryset):
        """Start async batch processing for full workflow using OpenAI Batch API."""
        transactions = list(queryset)
        # Start with payee lookup first
        start_batch_processing(transactions, "Payee Lookup Agent", request, task_type="batch_full_workflow")

    async_batch_full_workflow.short_description = "Async Batch Full Workflow (50 percent cost savings)"


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
        "task_id_link",
        "task_type",
        "client", 
        "status",
        "batch_status_display",
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
        "batch_status_display",
        "error_details",
    )
    actions = ["retry_failed_tasks", "cancel_tasks", "run_task", "check_batch_completion"]
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'batch-status/<str:task_id>/',
                self.admin_site.admin_view(self.batch_status_detail_view),
                name='processingtask_batch_status',
            ),
        ]
        return custom_urls + urls
    
    def batch_status_detail_view(self, request, task_id):
        """Enhanced OpenAI batch status view with debugging info"""
        # Handle both UUID and integer task IDs
        try:
            task = get_object_or_404(ProcessingTask, task_id=task_id)
        except:
            task = get_object_or_404(ProcessingTask, pk=task_id)
        
        context = {
            'title': f'OpenAI Batch Status - Task {task.task_id}',
            'task': task,
            'batch_details': None,
            'error': None,
            'database_info': None,
            'response_sample': None,
            'agent_details': None,
            'prompt_details': None,
        }
        
        # Get database info for task
        try:
            from profiles.models import Transaction
            
            # Get transaction count info based on task selection criteria  
            if hasattr(task, 'transaction_filter_criteria') and task.transaction_filter_criteria:
                # Use stored filter criteria if available
                filter_criteria = task.transaction_filter_criteria
            else:
                # Fallback to basic criteria based on task type
                if task.task_type == "batch_full_workflow":
                    filter_criteria = {
                        'client': task.client,
                        'payee__isnull': True  # Transactions needing payee extraction
                    }
                else:
                    filter_criteria = {
                        'client': task.client,
                        'normalized_description__isnull': True  # Transactions needing classification
                    }
            
            # Get counts for database info
            total_transactions = Transaction.objects.filter(client=task.client).count()
            null_payee_count = Transaction.objects.filter(client=task.client, payee__isnull=True).count()
            null_normalized_count = Transaction.objects.filter(client=task.client, normalized_description__isnull=True).count()
            both_null_count = Transaction.objects.filter(
                client=task.client, 
                payee__isnull=True, 
                normalized_description__isnull=True
            ).count()
            
            context['database_info'] = {
                'total_transactions': total_transactions,
                'null_payee_count': null_payee_count,
                'null_normalized_count': null_normalized_count,
                'both_null_count': both_null_count,
                'task_processed_count': task.processed_count or 0,
                'task_error_count': task.error_count or 0,
            }
            
        except Exception as e:
            context['database_info'] = {'error': f"Could not load database info: {e}"}
        
        # Get agent and prompt details for verification
        try:
            from profiles.models import Agent
            agent_details = {}
            prompt_details = {}
            
            # Get agent info based on task type  
            if task.task_type == "batch_full_workflow":
                # Full workflow - get both agents
                first_agent_name = task.task_metadata.get('first_agent')
                second_agent_name = task.task_metadata.get('second_agent')
                
                if first_agent_name:
                    first_agent = Agent.objects.get(name=first_agent_name)
                    agent_details['first_agent'] = {
                        'name': first_agent.name,
                        'model': first_agent.llm.model if first_agent.llm else 'No LLM configured',
                        'purpose': first_agent.purpose or 'No purpose specified',
                        'prompt_length': len(first_agent.prompt) if first_agent.prompt else 0,
                        'prompt_preview': (first_agent.prompt[:200] + '...' if len(first_agent.prompt) > 200 else first_agent.prompt) if first_agent.prompt else 'No prompt configured',
                    }
                    
                if second_agent_name:
                    second_agent = Agent.objects.get(name=second_agent_name)
                    agent_details['second_agent'] = {
                        'name': second_agent.name,
                        'model': second_agent.llm.model if second_agent.llm else 'No LLM configured',
                        'purpose': second_agent.purpose or 'No purpose specified',
                        'prompt_length': len(second_agent.prompt) if second_agent.prompt else 0,
                        'prompt_preview': (second_agent.prompt[:200] + '...' if len(second_agent.prompt) > 200 else second_agent.prompt) if second_agent.prompt else 'No prompt configured',
                    }
            else:
                # Single agent task
                agent_name = task.task_metadata.get('agent_name')
                if agent_name:
                    agent = Agent.objects.get(name=agent_name)
                    agent_details['single_agent'] = {
                        'name': agent.name,
                        'model': agent.llm.model if agent.llm else 'No LLM configured', 
                        'purpose': agent.purpose or 'No purpose specified',
                        'prompt_length': len(agent.prompt) if agent.prompt else 0,
                        'prompt_preview': (agent.prompt[:200] + '...' if len(agent.prompt) > 200 else agent.prompt) if agent.prompt else 'No prompt configured',
                    }
                    
            context['agent_details'] = agent_details
            
            # Get sample rendered prompts for verification
            if task.transactions.exists():
                sample_tx = task.transactions.first()
                
                try:
                    # Try to render prompt template with sample transaction
                    if task.task_type == "batch_full_workflow" and first_agent_name:
                        agent = Agent.objects.get(name=first_agent_name)
                    elif agent_name:
                        agent = Agent.objects.get(name=agent_name)
                    else:
                        agent = None
                        
                    if agent and agent.prompt:
                        from jinja2 import Template
                        
                        # Build context like async_batch_processor does
                        context_vars = {
                            "transaction": sample_tx,
                            "business_profile": getattr(sample_tx, "client", None),
                        }
                        
                        # For classification agents, add allowed categories
                        if "classification" in agent.name.lower():
                            context_vars["allowed_categories"] = build_allowed_categories(sample_tx)
                        
                        template = Template(agent.prompt)
                        rendered_prompt = template.render(**context_vars)
                        
                        prompt_details['sample_rendered'] = {
                            'agent_name': agent.name,
                            'transaction_id': sample_tx.id,
                            'transaction_desc': sample_tx.description,
                            'rendered_length': len(rendered_prompt),
                            'rendered_preview': rendered_prompt,
                        }
                        
                except Exception as prompt_error:
                    prompt_details['sample_rendered'] = {
                        'error': f"Could not render sample prompt: {prompt_error}"
                    }
                    
            context['prompt_details'] = prompt_details
            
        except Exception as e:
            context['agent_details'] = {'error': f"Could not load agent details: {e}"}
            context['prompt_details'] = {'error': f"Could not load prompt details: {e}"}
        
        if task.task_metadata and task.task_metadata.get('openai_batch_id'):
            try:
                from profiles.utils.async_batch_processor import AsyncBatchProcessor
                processor = AsyncBatchProcessor()
                batch_id = task.task_metadata.get('openai_batch_id')
                
                # Get detailed batch status from OpenAI
                batch_details = processor.get_batch_status(batch_id)
                
                # Calculate remaining count
                if 'request_counts' in batch_details:
                    total = batch_details['request_counts'].get('total', 0)
                    completed = batch_details['request_counts'].get('completed', 0) 
                    failed = batch_details['request_counts'].get('failed', 0)
                    batch_details['remaining_count'] = max(0, total - completed - failed)
                
                # Add timing information
                if batch_details.get('created_at'):
                    import datetime
                    created_timestamp = batch_details['created_at']
                    created_dt = datetime.datetime.fromtimestamp(created_timestamp)
                    batch_details['created_at_formatted'] = created_dt.strftime('%Y-%m-%d %H:%M:%S UTC')
                    
                    # Calculate elapsed time
                    now = datetime.datetime.now()
                    elapsed = now - created_dt
                    batch_details['elapsed_time'] = str(elapsed).split('.')[0]  # Remove microseconds
                
                if batch_details.get('completed_at'):
                    completed_timestamp = batch_details['completed_at']
                    completed_dt = datetime.datetime.fromtimestamp(completed_timestamp)
                    batch_details['completed_at_formatted'] = completed_dt.strftime('%Y-%m-%d %H:%M:%S UTC')
                
                # Check if we can get file contents for debugging
                if batch_details.get('error_file_id'):
                    try:
                        error_content = processor.client.files.content(batch_details['error_file_id'])
                        batch_details['error_content'] = error_content.content.decode('utf-8')
                    except Exception as e:
                        batch_details['error_content'] = f"Could not read error file: {e}"
                
                # Try to get sample response data if batch is completed
                if batch_details.get('output_file_id') and batch_details.get('status') == 'completed':
                    try:
                        import json
                        output_content = processor.client.files.content(batch_details['output_file_id'])
                        response_text = output_content.content.decode('utf-8')
                        
                        # Parse first few lines for sample
                        lines = response_text.strip().split('\n')[:3]  # First 3 responses
                        sample_responses = []
                        
                        for line in lines:
                            if line.strip():
                                try:
                                    response_data = json.loads(line)
                                    # Extract key info from response
                                    response_content = "No content"
                                    if response_data.get('response') and response_data['response'].get('body'):
                                        choices = response_data['response']['body'].get('choices', [])
                                        if choices and len(choices) > 0:
                                            message = choices[0].get('message', {})
                                            content = message.get('content', 'No message content')
                                            response_content = content if content else 'Empty content'
                                    
                                    sample = {
                                        'custom_id': response_data.get('custom_id', 'N/A'),
                                        'response_status': response_content
                                    }
                                    sample_responses.append(sample)
                                except (json.JSONDecodeError, KeyError, IndexError, TypeError) as parse_error:
                                    sample_responses.append({
                                        'custom_id': 'Parse Error',
                                        'error': f"Could not parse response line: {str(parse_error)}"
                                    })
                        
                        context['response_sample'] = sample_responses
                        
                        # Also store full output for debugging  
                        batch_details['output_sample'] = response_text
                        
                    except Exception as e:
                        context['response_sample'] = [{'error': f"Could not parse response file: {e}"}]
                
                context['batch_details'] = batch_details
                
            except Exception as e:
                context['error'] = str(e)
        
        return TemplateResponse(request, 'admin/profiles/processingtask/batch_status_detail.html', context)

    def batch_status_display(self, obj):
        """Clean, useful batch status display"""
        if not obj.task_metadata or not obj.task_metadata.get("openai_batch_id"):
            if obj.status == "pending":
                return format_html('<span style="color:#666;">⏳ Ready to submit</span>')
            elif obj.status == "processing":
                return format_html('<span style="color:#ff9800;">🔄 Submitting to OpenAI...</span>')
            else:
                return format_html('<span style="color:#666;">No batch processing</span>')
        
        # Has batch ID - get live status
        try:
            from profiles.utils.async_batch_processor import AsyncBatchProcessor
            processor = AsyncBatchProcessor()
            batch_id = obj.task_metadata.get("openai_batch_id")
            batch_status = processor.get_batch_status(batch_id)
            
            status = batch_status.get('status', 'unknown')
            total = batch_status.get('request_counts', {}).get('total', 0)
            completed = batch_status.get('request_counts', {}).get('completed', 0)
            failed = batch_status.get('request_counts', {}).get('failed', 0)
            
            if status == 'completed':
                return format_html(
                    '<div><strong style="color:#4CAF50;">✅ Completed</strong><br>'
                    '<small><a href="{}batch-status/{}/" target="_blank" style="color:#2E7D32;">📋 Batch ID: {}</a></small><br>'
                    '<small>Processed: {}/{} | Failed: {}</small></div>',
                    '/admin/profiles/processingtask/',
                    obj.task_id,
                    batch_id[:20] + '...' if len(batch_id) > 20 else batch_id,
                    completed, total, failed
                )
            elif status == 'in_progress':
                return format_html(
                    '<div><strong style="color:#ff9800;">🔄 Processing at OpenAI</strong><br>'
                    '<small><a href="{}batch-status/{}/" target="_blank" style="color:#F57C00;">📋 Batch ID: {}</a></small><br>'
                    '<small>Progress: {}/{} | Failed: {}</small></div>',
                    '/admin/profiles/processingtask/',
                    obj.task_id,
                    batch_id[:20] + '...' if len(batch_id) > 20 else batch_id,
                    completed, total, failed
                )
            elif status == 'validating':
                return format_html(
                    '<div><strong style="color:#2196F3;">🔍 Validating at OpenAI</strong><br>'
                    '<small><a href="{}batch-status/{}/" target="_blank" style="color:#1976D2;">📋 Batch ID: {}</a></small><br>'
                    '<small>Total requests: {}</small></div>',
                    '/admin/profiles/processingtask/',
                    obj.task_id,
                    batch_id[:20] + '...' if len(batch_id) > 20 else batch_id,
                    total
                )
            elif status in ['failed', 'expired', 'cancelled']:
                return format_html(
                    '<div><strong style="color:#f44336;">❌ {}</strong><br>'
                    '<small>Batch ID: {}</small></div>',
                    status.title(),
                    batch_id[:20] + '...' if len(batch_id) > 20 else batch_id
                )
            else:
                return format_html(
                    '<div><strong style="color:#666;">📋 {}</strong><br>'
                    '<small>Batch ID: {}</small></div>',
                    status.title(),
                    batch_id[:20] + '...' if len(batch_id) > 20 else batch_id
                )
        except Exception as e:
            return format_html('<span style="color:#f44336;">❌ Error: {}</span>', str(e))
    
    batch_status_display.short_description = "Live Batch Status"

    def has_change_permission(self, request, obj=None):
        # This is a read-only status view, not editable
        return False
    
    def has_add_permission(self, request):
        # Don't allow manual creation - tasks are created programmatically
        return False
    
    def has_delete_permission(self, request, obj=None):
        # Allow deletion for cleanup
        return True
        
    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = extra_context or {}
        task = self.get_object(request, object_id)
        
        # This is a status/detail view, not a change form
        extra_context["title"] = f"Task Status: {task.task_id}"
        extra_context["subtitle"] = f"{task.task_type} - {task.status.title()}"
        
        # Auto-refresh every 10 seconds if task is running
        if task and task.status in ["pending", "processing"]:
            extra_context["auto_refresh"] = True
            extra_context["refresh_message"] = f"⟳ Auto-refreshing every 10 seconds while {task.status}..."
        
        # Auto-process completed batches silently
        if task and task.status == "processing" and task.task_metadata and task.task_metadata.get("openai_batch_id"):
            try:
                from profiles.utils.async_batch_processor import check_and_process_completed_batches
                check_and_process_completed_batches()  # Silent auto-processing
            except Exception:
                pass  # Silent failure - don't clutter UI
                
        return super().change_view(request, object_id, form_url, extra_context=extra_context)

    def run_task(self, request, queryset):
        """Execute the selected task with immediate feedback."""
        if queryset.count() > 1:
            messages.error(request, "Please select only one task to run at a time.")
            return

        task = queryset.first()
        if task.status != "pending":
            messages.error(request, f"Task {task.task_id} is not in pending state.")
            return

        try:
            # Update status to processing immediately for user feedback
            task.status = "processing" 
            task.started_at = timezone.now()
            task.save()
            
            # Submit batch processing directly (no subprocess)
            if task.task_type.startswith("batch_"):
                from profiles.utils.async_batch_processor import submit_processing_task_batch
                
                success = submit_processing_task_batch(task)
                if success:
                    # Refresh to get updated metadata with batch ID
                    task.refresh_from_db()
                    batch_id = task.task_metadata.get('openai_batch_id')
                    
                    messages.success(
                        request, 
                        f"✅ Batch submitted successfully! "
                        f"OpenAI Batch ID: {batch_id[:20] if batch_id else 'N/A'}... "
                        f"Processing {task.transaction_count} transactions."
                    )
                    messages.info(
                        request,
                        "The batch is now processing at OpenAI. This page will auto-refresh to show progress. "
                        "Typical processing time: 5-60 minutes depending on queue load."
                    )
                else:
                    task.refresh_from_db()  # Get error details
                    error_msg = task.error_details.get('error', 'Unknown error') if task.error_details else 'Submission failed'
                    messages.error(request, f"❌ Failed to submit batch: {error_msg}")
            else:
                messages.error(request, f"Task type '{task.task_type}' not supported for direct execution.")
                task.status = "failed"
                task.error_details = {"error": f"Unsupported task type: {task.task_type}"}
                task.save()

        except Exception as e:
            logger.error(f"Failed to run task {task.task_id}: {str(e)}")
            task.status = "failed"
            task.error_details = {"error": str(e)}
            task.save()
            messages.error(request, f"❌ Error starting task: {str(e)}")

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

    def check_batch_completion(self, request, queryset):
        """Manually check for completed OpenAI batches and process results."""
        from profiles.utils.async_batch_processor import check_and_process_completed_batches
        
        try:
            completed_count = check_and_process_completed_batches()
            if completed_count > 0:
                messages.success(request, f"✅ Processed {completed_count} completed batch jobs")
            else:
                messages.info(request, "ℹ️ No completed batch jobs found")
        except Exception as e:
            messages.error(request, f"❌ Error checking batch completion: {str(e)}")
    
    check_batch_completion.short_description = "Check for completed batches"

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

    def check_batch_completion(self, request, queryset):
        """Check for completed batch jobs and process results."""
        from profiles.utils.async_batch_processor import AsyncBatchProcessor, Agent
        
        # Filter to only batch processing tasks that are still processing
        batch_tasks = queryset.filter(
            status="processing",
            task_metadata__batch_processing=True,
            task_metadata__openai_batch_id__isnull=False
        )
        
        if not batch_tasks.exists():
            messages.warning(request, "No batch processing tasks selected or all are already completed.")
            return
        
        processor = AsyncBatchProcessor()
        completed_count = 0
        
        for task in batch_tasks:
            batch_id = task.task_metadata.get("openai_batch_id")
            agent_name = task.task_metadata.get("agent_name", "Unknown")
            
            if not batch_id:
                continue
            
            try:
                # Check batch status
                status = processor.get_batch_status(batch_id)
                batch_status = status.get("status", "unknown")
                
                messages.info(request, f"Task {task.task_id}: OpenAI batch status is '{batch_status}'")
                
                if batch_status == "completed":
                    # Get agent and process results
                    agent = Agent.objects.get(name=agent_name)
                    output_file_id = status.get("output_file_id")
                    
                    if output_file_id:
                        # Download and process results
                        batch_results = processor.download_batch_results(output_file_id)
                        processed_results = processor.process_batch_results(batch_results, agent)
                        
                        # Update transactions
                        success_count, failed_count = processor.update_transactions(
                            processed_results, agent, task
                        )
                        
                        # Update task status
                        if failed_count == 0:
                            task.status = "completed"
                            task.save()
                            messages.success(
                                request, 
                                f"✅ Task {task.task_id} completed! Processed {success_count} transactions successfully."
                            )
                        else:
                            messages.warning(
                                request, 
                                f"⚠️ Task {task.task_id}: {success_count} succeeded, {failed_count} failed"
                            )
                        
                        completed_count += 1
                    else:
                        messages.error(request, f"❌ Task {task.task_id}: No output file found")
                        
                elif batch_status == "failed":
                    task.status = "failed"
                    task.save()
                    messages.error(
                        request, 
                        f"❌ Task {task.task_id}: OpenAI batch failed - {status.get('errors', 'Unknown error')}"
                    )
                    
                elif batch_status in ["validating", "in_progress", "finalizing"]:
                    messages.info(request, f"⏳ Task {task.task_id}: Batch still {batch_status}...")
                
            except Exception as e:
                messages.error(request, f"❌ Task {task.task_id}: Error checking batch - {str(e)}")
        
        if completed_count > 0:
            messages.success(request, f"🎉 Successfully processed {completed_count} completed batch jobs!")
        else:
            messages.info(request, "No completed batches found to process.")
    
    check_batch_completion.short_description = "Check & Process Completed Batch Jobs"

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

    def pages_to_parse(self, obj):
        return obj.pages_to_parse or "-"

    pages_to_parse.short_description = "Pages to Parse"

    def tax_year_column(self, obj):
        # For organizer_extraction, show the tax year (binder) if possible
        if obj.task_type == "organizer_extraction":
            workbook_id = obj.task_metadata.get("workbook_id")
            if workbook_id:
                try:
                    workbook = OrganizerWorkbook.objects.get(id=workbook_id)
                    return getattr(workbook.tax_year, "year", "-")
                except Exception:
                    return "-"
        return "-"

    tax_year_column.short_description = "Tax Year"

    def get_fields(self, request, obj=None):
        fields = super().get_fields(request, obj)
        # Remove transactions field from the detail view
        if "transactions" in fields:
            fields = tuple(f for f in fields if f != "transactions")
        return fields
    
    def task_id_link(self, obj):
        """Generate task ID link that redirects batch tasks to enhanced dashboard"""
        from django.utils.html import format_html
        from django.urls import reverse
        
        # Check if this is a batch processing task
        has_openai_batch = obj.task_metadata and obj.task_metadata.get('openai_batch_id')
        is_batch_type = obj.task_type == 'batch_full_workflow' or 'batch' in obj.task_type
        
        if has_openai_batch or is_batch_type:
            # Link to enhanced batch status page
            url = reverse('admin:processingtask_batch_status', args=[obj.task_id])
            return format_html('<a href="{}">{}</a>', url, obj.task_id)
        else:
            # Link to regular change form for non-batch tasks
            url = reverse('admin:profiles_processingtask_change', args=[obj.pk])
            return format_html('<a href="{}">{}</a>', url, obj.task_id)
    
    task_id_link.short_description = 'Task ID'
    task_id_link.admin_order_field = 'task_id'
    
    def response_change(self, request, obj):
        """Override to redirect batch processing tasks to enhanced batch status page"""
        from django.http import HttpResponseRedirect
        from django.urls import reverse
        
        # Check if this is a batch processing task
        has_openai_batch = obj.task_metadata and obj.task_metadata.get('openai_batch_id')
        is_batch_type = obj.task_type == 'batch_full_workflow' or 'batch' in obj.task_type
        
        if has_openai_batch or is_batch_type:
            # Redirect to enhanced batch status page instead of regular change form
            batch_status_url = reverse(
                'admin:processingtask_batch_status',
                args=[obj.task_id]
            )
            return HttpResponseRedirect(batch_status_url)
        
        # For non-batch tasks, use default behavior
        return super().response_change(request, obj)


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
                        # Create StatementFile with duplicate handling
                        try:
                            # Use get_or_create to handle duplicate files gracefully
                            statement_file, file_created = StatementFile.objects.get_or_create(
                                client=client,
                                statement_hash=getattr(f, 'statement_hash', None) or f.name,
                                defaults={
                                    "file": f,
                                    "file_type": file_type,
                                    "account_number": metadata.get(
                                        "account_number", account_number
                                    ),
                                    "original_filename": f.name,
                                    "uploaded_by": uploaded_by,
                                    "status": "uploaded",
                                    "bank": metadata.get("bank_name"),
                                    "year": metadata.get("year"),
                                    "month": metadata.get("month"),
                                    "parser_module": used_parser,
                                    "account_holder_name": metadata.get("account_holder_name"),
                                    "address": metadata.get("address"),
                                    "account_type": metadata.get("account_type"),
                                    "statement_period_start": metadata.get(
                                        "statement_period_start"
                                    ),
                                    "statement_period_end": metadata.get(
                                        "statement_period_end"
                                    ),
                                    "statement_date": metadata.get("statement_date"),
                                    "parsed_metadata": metadata,
                                }
                            )
                            result["statement_file"] = statement_file.id
                            if not file_created:
                                # Log duplicate file detection for clear user feedback
                                result["warning"] = f"💡 DUPLICATE FILE DETECTED: This exact file was already imported (StatementFile #{statement_file.id}). Processing transactions anyway to check for new data."
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
                                # Generate transaction hash if not present
                                if "transaction_hash" not in tx or not tx["transaction_hash"]:
                                    tx_hash = Transaction.compute_transaction_hash(
                                        client.client_id,
                                        tx.get("transaction_date"),
                                        tx.get("amount"),
                                        tx.get("description"),
                                        tx.get("category", "")
                                    )
                                else:
                                    tx_hash = tx["transaction_hash"]
                                
                                # Use get_or_create to handle duplicates gracefully
                                transaction, created = Transaction.objects.get_or_create(
                                    client=client,
                                    transaction_hash=tx_hash,
                                    defaults={
                                        "statement_file": statement_file,
                                        "transaction_hash": tx_hash,
                                        "transaction_date": tx.get("transaction_date"),
                                        "amount": tx.get("amount"),
                                        "description": tx.get("description"),
                                        "category": tx.get("category", ""),
                                        "file_path": statement_file.file.name,
                                        "source": tx.get("source", "batch_upload"),
                                        "transaction_type": tx.get("transaction_type", ""),
                                        "normalized_amount": tx.get("normalized_amount"),
                                        "parser_name": used_parser,
                                        "classification_method": tx.get(
                                            "classification_method", "None"
                                        ),
                                        "payee_extraction_method": tx.get(
                                            "payee_extraction_method", "None"
                                        ),
                                    }
                                )
                                if created:
                                    transactions_created += 1
                                else:
                                    # Log duplicate transaction (for debugging)
                                    duplicate_info = f"Duplicate transaction skipped: {tx.get('transaction_date')} | ${tx.get('amount')} | {tx.get('description', '')[:30]}..."
                                    print(f"⚠️  Idx {idx}: {duplicate_info}")
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

                # Calculate totals for obvious feedback
                total_files = len(files)
                total_created = sum(result.get("transactions_created", 0) for result in results)
                total_skipped = sum(result.get("transactions_skipped", 0) for result in results)
                duplicate_files = sum(1 for result in results if result.get("warning"))
                
                # Build detailed success message with obvious feedback
                feedback_parts = [
                    f"✅ BATCH UPLOAD COMPLETE: {total_files} files processed",
                    f"📊 TRANSACTION STATS: {total_created} created, {total_skipped} skipped duplicates"
                ]
                
                if duplicate_files > 0:
                    feedback_parts.append(f"💡 DUPLICATE FILES: {duplicate_files} files were already imported")
                
                messages.success(
                    request, " | ".join(feedback_parts)
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


class BinderItemFieldInline(admin.TabularInline):
    model = BinderItemField
    extra = 1
    fields = ("label", "value", "status", "category_code", "order", "notes")
    ordering = ("order",)


class BinderItemAdminForm(forms.ModelForm):
    class Meta:
        model = BinderItem
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        options = get_all_binder_item_options(grouped=True)
        choices = [("", "---------")]
        if options["workbook"]:
            choices.append(
                (
                    "Organizer Forms",
                    [(o["form_id"], o["label"]) for o in options["workbook"]],
                )
            )
        if options["ad_hoc"]:
            choices.append(
                (
                    "Ad Hoc Items",
                    [(o["form_id"], o["label"]) for o in options["ad_hoc"]],
                )
            )
        self.fields["form_id"].choices = choices
        self.fields["form_id"].required = False
        self.fields["form_id"].widget.attrs["style"] = "width: 350px;"
        # Allow freeform entry
        self.fields["form_id"].widget.can_add_related = True


@admin.register(BinderItem)
class BinderItemAdmin(admin.ModelAdmin):
    form = BinderItemAdminForm
    list_display = (
        "label",
        "priority_badge",
        "status_badge",
        "summary_tooltip",  # Only one summary/info icon column
        "tax_year",
        "type",
        "form_id",
        "status",
        "order",
        "is_generated",
        "page_number",
        "has_user_data",
        "thumbnail_preview",
        # "fields_preview",  # removed
        "summary_preview",
        "updated_at",
    )
    list_filter = (
        "tax_year",
        "type",
        "status",
        "has_user_data",
        "priority",
    )  # Only field names here
    list_filter_classes = [
        "ActionableListFilter",
    ]
    search_fields = ("label", "form_id", "notes")
    inlines = [BinderItemFieldInline]
    ordering = ("-priority", "status", "tax_year", "order")

    actions = [
        "set_status_not_started",
        "set_status_incomplete",
        "set_status_complete",
        "set_status_missing",
    ]

    def set_status_not_started(self, request, queryset):
        updated = queryset.update(status="not_started")
        self.message_user(
            request, f"Set status to 'Not Started' for {updated} Binder Items."
        )

    set_status_not_started.short_description = "Set status to Not Started"

    def set_status_incomplete(self, request, queryset):
        updated = queryset.update(status="incomplete")
        self.message_user(
            request, f"Set status to 'Incomplete' for {updated} Binder Items."
        )

    set_status_incomplete.short_description = "Set status to Incomplete"

    def set_status_complete(self, request, queryset):
        updated = queryset.update(status="complete")
        self.message_user(
            request, f"Set status to 'Complete' for {updated} Binder Items."
        )

    set_status_complete.short_description = "Set status to Complete"

    def set_status_missing(self, request, queryset):
        updated = queryset.update(status="missing")
        self.message_user(
            request, f"Set status to 'Missing' for {updated} Binder Items."
        )

    set_status_missing.short_description = "Set status to Missing"

    class Media:
        css = {"all": ("admin/binderitem_custom.css",)}

    def thumbnail_preview(self, obj):
        # Show a small thumbnail (80x100px) with magnifier on hover
        if obj.thumbnail_file:
            thumb_url = obj.thumbnail_file
            if not thumb_url.startswith("/media/") and not thumb_url.startswith("http"):
                thumb_url = (
                    f"/media/{thumb_url}"
                    if not thumb_url.startswith("media/")
                    else f"/{thumb_url}"
                )
            link_url = obj.pdf_page_file or obj.thumbnail_file
            if (
                link_url
                and not link_url.startswith("/media/")
                and not link_url.startswith("http")
            ):
                link_url = (
                    f"/media/{link_url}"
                    if not link_url.startswith("media/")
                    else f"/{link_url}"
                )
            return format_html(
                '<div class="binder-thumb-wrap" style="display:inline-block;max-width:90px;">'
                '<a href="{}" target="_blank">'
                '<img class="binder-thumb" src="{}" style="width:80px;height:100px;object-fit:contain;border:1px solid #ccc;box-shadow:1px 1px 4px #eee;" />'
                '<span class="binder-thumb-magnify"><img src="{}" /></span>'
                "</a>"
                "</div>",
                link_url,
                thumb_url,
                thumb_url,
            )
        return ""

    thumbnail_preview.short_description = "Thumbnail"
    thumbnail_preview.allow_tags = True

    def summary_preview(self, obj):
        summary = obj.summary or ""
        if summary:
            return format_html(
                '<span style="cursor:pointer;" title="{}">&#9432;</span>', summary
            )
        return ""

    summary_preview.short_description = "Summary"

    def priority_badge(self, obj):
        color = {
            "high": "red",
            "medium": "orange",
            "low": "green",
        }.get(obj.priority, "gray")
        return format_html(
            '<span style="color:white;background:{};padding:2px 6px;border-radius:4px;font-weight:bold">{}</span>',
            color,
            obj.get_priority_display(),
        )

    priority_badge.short_description = "Priority"

    def status_badge(self, obj):
        color = {
            "not_started": "gray",
            "incomplete": "orange",
            "complete": "green",
            "missing": "red",
        }.get(obj.status, "gray")
        return format_html(
            '<span style="color:white;background:{};padding:2px 6px;border-radius:4px;font-weight:bold">{}</span>',
            color,
            obj.get_status_display(),
        )

    status_badge.short_description = "Status"

    def summary_tooltip(self, obj):
        if obj.summary:
            return format_html(
                '<span title="{}" style="cursor:help;">&#9432;</span>', obj.summary
            )
        return ""

    summary_tooltip.short_description = "Summary"

    class ActionableListFilter(admin.SimpleListFilter):
        title = "Actionable"
        parameter_name = "actionable"

        def lookups(self, request, model_admin):
            return (
                ("yes", "Actionable"),
                ("no", "Not Actionable"),
            )

        def queryset(self, request, queryset):
            if self.value() == "yes":
                return queryset.exclude(type="cover_page")
            if self.value() == "no":
                return queryset.filter(type="cover_page")
            return queryset

    actionable = ActionableListFilter


class BinderItemInline(admin.TabularInline):
    model = BinderItem
    extra = 1
    fields = (
        "type",
        "label",
        "form_id",
        "status",
        "order",
        "is_generated",
        "reference_file",
        "previous_year_value",
        "notes",
    )
    ordering = ("order",)


@admin.register(TaxYear)
class TaxYearAdmin(admin.ModelAdmin):
    list_display = ("business_profile", "year", "status", "created_at", "updated_at")
    list_filter = ("business_profile", "year", "status")
    search_fields = ("business_profile__company_name", "year", "notes")
    # inlines = [BinderItemInline]  # Removed to avoid showing inline BinderItems table
    ordering = ("-year",)
    verbose_name = "Binder"
    verbose_name_plural = "Binders"

    def view_binder_items_link(self, obj):
        from django.urls import reverse
        from django.utils.html import format_html

        url = (
            reverse("admin:profiles_binderitem_changelist")
            + f"?tax_year__id__exact={obj.id}"
        )
        return format_html(
            '<a class="button" href="{}">View/Edit Items for this Binder</a>', url
        )

    view_binder_items_link.short_description = "Binder Items"
    view_binder_items_link.allow_tags = True

    readonly_fields = ("view_binder_items_link",)
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "business_profile",
                    "year",
                    "status",
                    "notes",
                    "view_binder_items_link",
                )
            },
        ),
    )
