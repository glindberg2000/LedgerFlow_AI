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
)
from django.utils.translation import gettext_lazy as _
from django.http import HttpResponseRedirect
from django.urls import path
from django.shortcuts import render, get_object_or_404
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
from django.urls import reverse
from django.utils import timezone
from pathlib import Path
import subprocess
from django.conf import settings
from django.db import transaction as db_transaction
from django import forms
from django.utils.html import format_html
import re
from .utils import extract_pdf_metadata, get_update_fields_from_response
from django.template.response import TemplateResponse
from django.contrib.admin import AdminSite
from django.utils.safestring import mark_safe
import importlib
import pkgutil
from dataextractai.utils.normalize_api import normalize_parsed_data

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
            "client_id",
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
    list_display = ("client_id", "business_type")
    search_fields = ("client_id", "business_description")
    fieldsets = (
        (
            "User-Defined Profile",
            {
                "fields": ("client_id", "contact_info", "business_description"),
                "description": "Enter the client ID, contact info, and a business description. The AI will generate the rest.",
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
            from django.shortcuts import redirect

            messages.error(request, "BusinessProfile not found.")
            return redirect("..")
        try:
            from openai import OpenAI
            import os
            import json
            from django.urls import reverse

            # Always use the Agent with purpose containing 'Business Profile Generator'
            agent = None
            model = None
            base_url = None
            try:
                from .models import Agent

                # Prefer a dedicated Business Profile Generator agent
                agent = Agent.objects.filter(
                    purpose__icontains="business profile generator"
                ).first()
                # Fallback: any agent with an LLMConfig
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
            # Use the LLMConfig.url as base_url if set, for multi-provider support
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
            print(f"Raw LLM response: {content}")
            try:
                data = json.loads(content)
            except Exception as e:
                from django.contrib import messages
                from django.shortcuts import redirect

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
        from django.shortcuts import redirect
        from django.urls import reverse

        return redirect(reverse("admin:profiles_businessprofile_change", args=[obj.pk]))


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
    if model is None:
        model = os.environ.get("OPENAI_MODEL_PRECISE", "o4-mini")
    logger.info(f"Using OpenAI model: {model}")
    try:
        # Get the agent object from the database
        agent = Agent.objects.get(name=agent_name)
        base_url = agent.llm.url if agent.llm and agent.llm.url else None
        api_key = os.environ.get("OPENAI_API_KEY")
        # Use the LLMConfig.url as base_url if set, for multi-provider support
        if base_url:
            client = OpenAI(api_key=api_key, base_url=base_url)
        else:
            client = OpenAI(api_key=api_key)

        # Get the appropriate prompt based on agent type
        if "payee" in agent_name.lower():
            system_prompt = """You are a transaction analysis assistant. Your task is to:\n1. Identify the payee/merchant from transaction descriptions\n2. Use the search tool to gather comprehensive vendor information\n3. Synthesize all information into a clear, normalized description\n4. Return a final response in the exact JSON format specified\n\nIMPORTANT RULES:\n1. Make as many search calls as needed to gather complete information\n2. Synthesize all information into a clear, normalized response\n3. NEVER use the raw transaction description in your final response\n4. Format the response exactly as specified"""

            user_prompt = f"""Analyze this transaction and return a JSON object with EXACTLY these field names:\n{{\n    \"normalized_description\": \"string - A VERY SUCCINCT 2-5 word summary of what was purchased/paid for (e.g., 'Grocery shopping', 'Fast food purchase', 'Office supplies'). DO NOT include vendor details, just the core type of purchase.\",\n    \"payee\": \"string - The normalized payee/merchant name (e.g., 'Lowe's' not 'LOWE'S #1636', 'Walmart' not 'WALMART #1234')\",\n    \"confidence\": \"string - Must be exactly 'high', 'medium', or 'low'\",\n    \"reasoning\": \"string - VERBOSE explanation of the identification, including all search results and any details about the vendor, business type, and what was purchased. If you have a long description, put it here, NOT in normalized_description.\",\n    \"transaction_type\": \"string - One of: purchase, payment, transfer, fee, subscription, service\",\n    \"questions\": \"string - Any questions about unclear elements\",\n    \"needs_search\": \"boolean - Whether additional vendor information is needed\"\n}}\n\nTransaction: {transaction.description}\nAmount: ${transaction.amount}\nDate: {transaction.transaction_date}\n\nIMPORTANT INSTRUCTIONS:\n1. The 'normalized_description' MUST be a short phrase (2-5 words) summarizing the purchase type.\n2. Place any verbose or detailed explanation in the 'reasoning' field.\n3. NEVER use the raw transaction description in your final response.\n4. Include the type of business and what was purchased in the reasoning, not in normalized_description.\n5. Reference all search results used in the reasoning field.\n6. NEVER include store numbers, locations, or other non-standard elements in the payee field.\n7. Normalize the payee name to its standard business name (e.g., 'Lowe's' not 'LOWE'S #1636').\n8. ALWAYS provide a final JSON response after gathering all necessary information."""

        else:
            # Dynamically build allowed categories
            from profiles.models import (
                IRSExpenseCategory,
                IRSWorksheet,
                BusinessExpenseCategory,
            )

            # IRS categories (active, for all relevant worksheets)
            irs_cats = IRSExpenseCategory.objects.filter(
                is_active=True, worksheet__name__in=["6A", "Auto", "HomeOffice"]
            ).values("id", "name", "worksheet__name")
            # Business categories for this client
            biz_cats = BusinessExpenseCategory.objects.filter(
                is_active=True, business=transaction.client
            ).values("id", "category_name", "worksheet__name")
            # Build display list for prompt
            allowed_categories = []
            for cat in irs_cats:
                allowed_categories.append(
                    f"IRS-{cat['id']}: {cat['name']} (worksheet: {cat['worksheet__name']})"
                )
            for cat in biz_cats:
                allowed_categories.append(
                    f"BIZ-{cat['id']}: {cat['category_name']} (worksheet: {cat['worksheet__name']})"
                )
            allowed_categories.append("Other")  # Genuine catch-all
            allowed_categories.append("Personal")
            allowed_categories.append("Review")  # For LLM to flag for admin review
            # Build mapping for validation (not in prompt, but for post-processing)
            allowed_category_ids = set(
                [f"IRS-{cat['id']}" for cat in irs_cats]
                + [f"BIZ-{cat['id']}" for cat in biz_cats]
                + ["Other", "Personal", "Review"]
            )
            # Fetch business profile for the transaction's client
            business_profile = None
            try:
                business_profile = transaction.client
            except Exception:
                pass
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
            payee_reasoning = getattr(transaction, "payee_reasoning", None)
            if payee_reasoning:
                payee_context = (
                    f"Payee Reasoning (detailed vendor info):\n{payee_reasoning}\n"
                )
            else:
                payee_context = ""
            system_prompt = """You are an expert in business expense classification and tax preparation. Your role is to:\n1. Analyze transactions and determine if they are business or personal expenses\n2. For business expenses, determine the appropriate worksheet (6A, Vehicle, HomeOffice, or Personal)\n3. Provide detailed reasoning for your decisions\n4. Flag any transactions that need additional review\n\nConsider these factors:\n- Business type and description\n- Industry context\n- Transaction patterns\n- Amount and frequency\n- Business rules and patterns"""

            user_prompt = f"""{business_context}{payee_context}Return your analysis in this exact JSON format:\n{{\n    \"classification_type\": \"business\" or \"personal\",\n    \"worksheet\": \"6A\" or \"Vehicle\" or \"HomeOffice\" or \"Personal\",\n    \"category_id\": \"IRS-<id>\" or \"BIZ-<id>\" or \"Other\" or \"Personal\" or \"Review\",\n    \"category_name\": \"Name of the selected category from the list below\",\n    \"confidence\": \"high\" or \"medium\" or \"low\",\n    \"reasoning\": \"Detailed explanation of your decision, referencing both the business profile and payee reasoning above.\",\n    \"business_percentage\": \"integer - 0 for personal, 100 for clear business, 50 for dual-purpose, etc.\",\n    \"questions\": \"Any questions or uncertainties about this classification\",\n    \"proposed_category_name\": \"If you chose 'Review', propose a new category name that best fits the transaction. Otherwise, leave blank.\"\n}}\n\nTransaction: {transaction.description}\nAmount: ${transaction.amount}\nDate: {transaction.transaction_date}\n\nAllowed Categories (choose ONLY from this list):\n{chr(10).join(allowed_categories)}\n\nIMPORTANT RULES:\n- You MUST use one of the allowed category_id values above.\n- If the expense is business-related but does not fit any allowed category, use 'Review' and propose a new category name.\n- Only use 'Other' if it is a genuine, catch-all business category (e.g., 'Other Expenses', 'Miscellaneous', 'Check', 'Payment').\n- If the expense is not business-related, use 'Personal'.\n- NEVER invent a new category unless you use 'Review' and fill in 'proposed_category_name'.\n- For business expenses, use the most specific category that matches.\n- ALWAYS provide a business_percentage field as described above.\n- Use the payee reasoning above as additional context for your decision.\n\nIMPORTANT: Your response must be a valid JSON object."""

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

        # Prepare the API request payload
        payload = {
            "model": agent.llm.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
        }

        # Only add tools and tool_choice if tools are available
        if tool_definitions:
            payload["tools"] = tool_definitions
            payload["tool_choice"] = "auto"

        # Log the complete API request
        logger.info("\n=== API Request ===")
        logger.info(f"Model: {agent.llm.model}")
        logger.info(f"System Prompt: {system_prompt}")
        logger.info(f"User Prompt: {user_prompt}")
        logger.info(f"Transaction: {transaction.description}")
        if tool_definitions:
            logger.info(f"Tools: {json.dumps(tool_definitions, indent=2)}")

        try:
            # Retry logic
            for attempt in range(max_retries + 1):
                response = client.chat.completions.create(**payload)
                logger.info(f"LLM response (attempt {attempt+1}): {response}")
                # Parse and validate response
                try:
                    result = response.choices[0].message.content
                    result_json = json.loads(result)
                    # Validate category_id
                    cat_id = result_json.get("category_id")
                    if cat_id not in allowed_category_ids:
                        raise ValidationError(f"Invalid category_id: {cat_id}")
                    # Optionally: validate worksheet, classification_type, etc.
                    return result_json
                except Exception as e:
                    logger.warning(f"Validation failed (attempt {attempt+1}): {e}")
                    if attempt == max_retries and escalate_on_fail:
                        # Escalate to Classification Escalation Agent
                        try:
                            escalation_agent = Agent.objects.get(
                                name="Classification Escalation Agent"
                            )
                            logger.info(
                                "Escalating to Classification Escalation Agent..."
                            )
                            return call_agent(
                                escalation_agent.name,
                                transaction,
                                model=escalation_agent.llm.model,
                                max_retries=1,
                                escalate_on_fail=False,
                            )
                        except Exception as esc_e:
                            logger.error(f"Escalation failed: {esc_e}")
                            return {
                                "classification_type": "review",
                                "reasoning": f"Escalation failed: {esc_e}",
                                "category": "Review",
                            }
                    elif attempt == max_retries:
                        logger.error("Max retries reached. Marking for manual review.")
                        return {
                            "classification_type": "review",
                            "reasoning": "Max retries reached. Marking for manual review.",
                            "category": "Review",
                        }
            # Fallback (should not reach here)
            return {
                "classification_type": "review",
                "reasoning": "Unknown error.",
                "category": "Review",
            }

        except Exception as e:
            logger.error(f"Error calling OpenAI API: {str(e)}")
            raise

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
            update_fields = get_update_fields_from_response(
                agent,
                response,
                (
                    getattr(agent, "purpose", "").lower()
                    if hasattr(agent, "purpose")
                    else "classification"
                ),
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
        ProcessedFilter,  # Add processed filter
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
        "mark_as_unclassified",  # New action
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
            classification_method="None",
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
                    update_fields = get_update_fields_from_response(
                        agent,
                        response,
                        (
                            getattr(agent, "purpose", "").lower()
                            if hasattr(agent, "purpose")
                            else "classification"
                        ),
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

    def get_urls(self):
        urls = super().get_urls()
        return urls

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

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<uuid:task_id>/transactions/",
                self.admin_site.admin_view(self.view_task_transactions),
                name="profiles_processingtask_transactions",
            ),
        ]
        return custom_urls + urls

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


class StatementFileAdminForm(forms.ModelForm):
    # Use standard single file upload for ModelForm; batch upload requires custom view
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
        print(f"[DEBUG] Parser registry contents: {parser_names}")
        return [("", "--- No Change ---")] + [(name, name) for name in parser_names]
    except Exception as e:
        print(f"[DEBUG] Exception in get_parser_module_choices: {e}")
        import traceback

        traceback.print_exc()
        return [("", "--- No Change ---")]


class BulkTagForm(forms.Form):
    parser_module = forms.ChoiceField(required=False, label="Parser Module")
    statement_type = forms.CharField(
        required=False,
        label="Statement Type",
        help_text="Flexible statement type (e.g., VISA, checking, etc.)",
    )
    bank = forms.ChoiceField(required=False, label="Bank")
    year = forms.ChoiceField(required=False, label="Year")

    def __init__(self, *args, **kwargs):
        banks = kwargs.pop("banks", [])
        years = kwargs.pop("years", [])
        super().__init__(*args, **kwargs)
        self.fields["parser_module"].choices = get_parser_module_choices()
        # Remove duplicates and sort
        unique_banks = sorted(set(b for b in banks if b))
        unique_years = sorted(set(y for y in years if y))
        self.fields["bank"].choices = [("", "--- No Change ---")] + [
            (b, b) for b in unique_banks
        ]
        self.fields["year"].choices = [("", "--- No Change ---")] + [
            (y, y) for y in unique_years
        ]


@admin.action(description="Bulk tag: Parser/Statement Type/Bank/Year")
def bulk_tag_action(modeladmin, request, queryset):
    banks = StatementFile.objects.values_list("bank", flat=True).distinct()
    years = StatementFile.objects.values_list("year", flat=True).distinct()
    if "apply" in request.POST:
        form = BulkTagForm(request.POST, banks=banks, years=years)
        if form.is_valid():
            data = form.cleaned_data
            update_fields = {}
            if data["parser_module"]:
                update_fields["parser_module"] = data["parser_module"]
            if data["statement_type"]:
                update_fields["statement_type"] = data["statement_type"]
            if data["bank"]:
                update_fields["bank"] = data["bank"]
            if data["year"]:
                update_fields["year"] = data["year"]
            queryset.update(**update_fields)
            modeladmin.message_user(request, f"Updated {queryset.count()} files.")
            return None
    else:
        form = BulkTagForm(banks=banks, years=years)
    return TemplateResponse(
        request,
        "admin/bulk_tag_action.html",
        {
            "form": form,
            "queryset": queryset,
            "action_checkbox_name": admin.helpers.ACTION_CHECKBOX_NAME,
        },
    )


@admin.action(description="Batch Parse and Normalize")
def batch_parse_and_normalize(modeladmin, request, queryset):
    from django.db import transaction as db_transaction
    from django.contrib import messages
    import logging

    logger = logging.getLogger(__name__)
    logger.error(f"[DEBUG] sys.path: {sys.path}")
    from dataextractai.parsers_core.registry import ParserRegistry

    logger.error(
        f"[DEBUG] Registered parsers after forced import: {list(getattr(ParserRegistry, '_parsers', {}).keys())}"
    )
    created, updated, skipped, errors = 0, 0, 0, 0
    for sf in queryset:
        parser_name = sf.parser_module
        logger.error(f"[DEBUG] parser_name for file {sf.file}: {parser_name}")
        client = sf.client
        client_name = client.client_id if client else None
        file_path = sf.file.path if hasattr(sf.file, "path") else sf.file.name
        try:
            tx_dicts = normalize_parsed_data(file_path, parser_name, client_name)
            for tx in tx_dicts:
                try:
                    with db_transaction.atomic():
                        obj, is_created = Transaction.objects.update_or_create(
                            client=client,
                            transaction_id=tx["transaction_id"],
                            defaults={
                                k: v
                                for k, v in tx.items()
                                if k
                                in [
                                    "transaction_date",
                                    "amount",
                                    "description",
                                    "category",
                                    "parsed_data",
                                    "file_path",
                                    "source",
                                    "transaction_type",
                                    "normalized_amount",
                                    "statement_start_date",
                                    "statement_end_date",
                                    "account_number",
                                    "normalized_description",
                                    "payee",
                                    "confidence",
                                    "reasoning",
                                    "payee_reasoning",
                                    "business_context",
                                    "questions",
                                    "classification_type",
                                    "worksheet",
                                    "business_percentage",
                                ]
                            },
                        )
                        if is_created:
                            created += 1
                        else:
                            updated += 1
                except Exception as e:
                    logger.error(f"Error upserting transaction: {e}")
                    errors += 1
        except Exception as e:
            logger.error(f"Error parsing file {file_path}: {e}")
            errors += 1
    logger.error(
        f"[DEBUG] Batch parse complete: {created} created, {updated} updated, {errors} errors."
    )
    messages.success(
        request,
        f"Batch parse complete: {created} created, {updated} updated, {errors} errors.",
    )


@admin.register(StatementFile)
class StatementFileAdmin(admin.ModelAdmin):
    form = StatementFileAdminForm
    list_display = (
        "client",
        "original_filename",
        "file_type",
        "status",
        "upload_timestamp",
        "uploaded_by",
        "bank",
        "account_number",
        "year",
        "month",
        "status_detail",
    )
    list_filter = ("client", "file_type", "status", "year", "month", "bank")
    search_fields = ("original_filename", "bank", "account_number", "status_detail")
    readonly_fields = ("upload_timestamp", "uploaded_by", "parsed_metadata")
    actions = [bulk_tag_action, batch_parse_and_normalize]

    def save_model(self, request, obj, form, change):
        # First, save the object so the file is written to disk
        super().save_model(request, obj, form, change)
        # Now, if it's a PDF and file exists, extract metadata
        if obj.file and obj.file_type == "pdf":
            file_path = obj.file.path
            if os.path.exists(file_path):
                try:
                    meta = extract_pdf_metadata(file_path)
                    updated = False
                    if meta.get("bank") and obj.bank != meta["bank"]:
                        obj.bank = meta["bank"]
                        updated = True
                    if (
                        meta.get("account_number")
                        and obj.account_number != meta["account_number"]
                    ):
                        obj.account_number = meta["account_number"]
                        updated = True
                    # Try to extract year/month from statement_period or statement_date
                    from datetime import datetime

                    date_str = None
                    if meta.get("statement_period") and isinstance(
                        meta["statement_period"], tuple
                    ):
                        date_str = meta["statement_period"][1]  # Use end date
                    elif meta.get("statement_date"):
                        date_str = meta["statement_date"]
                    if date_str:
                        try:
                            dt = datetime.strptime(date_str, "%m/%d/%Y")
                            if obj.year != dt.year:
                                obj.year = dt.year
                                updated = True
                            if obj.month != dt.month:
                                obj.month = dt.month
                                updated = True
                        except Exception:
                            pass
                    # Add status_detail for debugging
                    obj.status_detail = f"Auto-extracted: {meta}"
                    updated = True
                except Exception as e:
                    obj.status_detail = f"Auto-extract error: {e}"
                    updated = True
                if updated:
                    obj.save()

    def add_view(self, request, form_url="", extra_context=None):
        # Custom add_view to support batch upload
        if (
            request.method == "POST"
            and request.FILES.getlist("file")
            and len(request.FILES.getlist("file")) > 1
        ):
            form = self.get_form(request)(request.POST, request.FILES)
            if form.is_valid():
                for f in request.FILES.getlist("file"):
                    instance = StatementFile(
                        client=form.cleaned_data["client"],
                        file=f,
                        file_type=form.cleaned_data["file_type"],
                        original_filename=f.name,
                        uploaded_by=request.user,
                        status=form.cleaned_data.get("status", "uploaded"),
                        status_detail=form.cleaned_data.get("status_detail", ""),
                        bank=form.cleaned_data.get("bank", ""),
                        account_number=form.cleaned_data.get("account_number", ""),
                        year=form.cleaned_data.get("year", None),
                        month=form.cleaned_data.get("month", None),
                    )
                    instance.save()
                self.message_user(
                    request,
                    f"Uploaded {len(request.FILES.getlist('file'))} files successfully.",
                )
                from django.shortcuts import redirect

                return redirect("admin:profiles_statementfile_changelist")
        return super().add_view(request, form_url, extra_context)

    # For extensibility: add progress bars, batch status, and custom UI as needed
