import pdfplumber
import re
from django.db import connection
import logging
import json

logger = logging.getLogger(__name__)

# List of known banks for detection (expand as needed)
KNOWN_BANKS = [
    "Chase",
    "Bank of America",
    "Wells Fargo",
    "First Republic",
    "Amazon",
    "Citi",
    "Capital One",
    "American Express",
    "US Bank",
    "PNC",
    "TD Bank",
    "HSBC",
    "Barclays",
    "Discover",
    "Synchrony",
    "Ally",
    "Charles Schwab",
    "Fidelity",
    "SoFi",
    "Robinhood",
    "PayPal",
    "Venmo",
    "Apple Card",
    "Goldman Sachs",
    "Comenity",
    "Santander",
    "Regions",
    "KeyBank",
    "SunTrust",
    "BB&T",
    "M&T",
    "Fifth Third",
    "BMO",
    "Huntington",
    "Citizens",
    "Navy Federal",
    "USAA",
    "Truist",
    "Silicon Valley Bank",
    "Signature Bank",
    "SVB",
    "Morgan Stanley",
    "JPMorgan",
    "J.P. Morgan",
    "JPMorgan Chase",
    "Chase Bank",
    "Wells Fargo Bank",
    "BofA",
    "BOA",
    "Amex",
    "American Express",
    "Discover Bank",
    "Synchrony Bank",
    "Ally Bank",
    "Charles Schwab Bank",
    "Fidelity Bank",
    "SoFi Bank",
    "Robinhood Bank",
    "PayPal Bank",
    "Venmo Bank",
    "Apple Bank",
    "Goldman Sachs Bank",
    "Comenity Bank",
    "Santander Bank",
    "Regions Bank",
    "KeyBank",
    "SunTrust Bank",
    "BB&T Bank",
    "M&T Bank",
    "Fifth Third Bank",
    "BMO Bank",
    "Huntington Bank",
    "Citizens Bank",
    "Navy Federal Credit Union",
    "USAA Bank",
    "Truist Bank",
    "Silicon Valley Bank",
    "Signature Bank",
    "SVB Bank",
    "Morgan Stanley Bank",
    "JPMorgan Bank",
    "J.P. Morgan Bank",
]

# Regex patterns for metadata
ACCOUNT_NUMBER_PATTERNS = [
    r"Account Number[:\s]*([\dXx\-\*]+)",
    r"Acct\.?\s*#?[:\s]*([\dXx\-\*]+)",
    r"Card Number[:\s]*([\dXx\-\*]+)",
]
STATEMENT_PERIOD_PATTERNS = [
    r"Statement Period[:\s]*([\w\-/]+)\s*-\s*([\w\-/]+)",
    r"Period[:\s]*([\w\-/]+)\s*-\s*([\w\-/]+)",
    r"From[:\s]*([\w\-/]+)\s*to\s*([\w\-/]+)",
]
DATE_PATTERNS = [
    r"Statement Date[:\s]*([\w\-/]+)",
    r"Date[:\s]*([\w\-/]+)",
]
TYPE_KEYWORDS = [
    "Checking",
    "Credit Card",
    "Savings",
    "Money Market",
    "Business",
    "Personal",
    "Platinum",
    "Rewards",
    "Student",
    "Premier",
    "Advantage",
    "Preferred",
    "Cash",
    "Visa",
    "Mastercard",
    "Debit",
    "Credit",
    "Account",
    "Card",
]


def extract_pdf_metadata(pdf_path):
    """
    Extracts metadata from the first page of a PDF bank/credit card statement.
    Returns a dict: {bank, account_number, statement_period, statement_date, type}
    """
    result = {
        "bank": None,
        "account_number": None,
        "statement_period": None,
        "statement_date": None,
        "type": None,
    }
    try:
        with pdfplumber.open(pdf_path) as pdf:
            if not pdf.pages:
                return result
            first_page = pdf.pages[0]
            text = first_page.extract_text() or ""
            lines = [line.strip() for line in text.split("\n") if line.strip()]
            # Bank detection
            for bank in KNOWN_BANKS:
                for line in lines[:5]:  # Only check first few lines
                    if bank.lower() in line.lower():
                        result["bank"] = bank
                        break
                if result["bank"]:
                    break
            if not result["bank"] and lines:
                result["bank"] = lines[0]  # Fallback: first line
            # Account number
            for pat in ACCOUNT_NUMBER_PATTERNS:
                m = re.search(pat, text, re.IGNORECASE)
                if m:
                    result["account_number"] = m.group(1)
                    break
            # Statement period
            for pat in STATEMENT_PERIOD_PATTERNS:
                m = re.search(pat, text, re.IGNORECASE)
                if m:
                    result["statement_period"] = (m.group(1), m.group(2))
                    break
            # Statement date
            for pat in DATE_PATTERNS:
                m = re.search(pat, text, re.IGNORECASE)
                if m:
                    result["statement_date"] = m.group(1)
                    break
            # Type detection
            for t in TYPE_KEYWORDS:
                if re.search(rf"\b{re.escape(t)}\b", text, re.IGNORECASE):
                    result["type"] = t
                    break
    except Exception as e:
        result["error"] = str(e)
    return result


# For extensibility: if all fields are None or confidence is low, fallback to vision agent


def normalize_category(category):
    if category and (category.startswith("IRS-: ") or category.startswith("BIZ-: ")):
        return category.split(": ", 1)[-1]
    return category


def get_update_fields_from_response(agent, response, agent_type, tool_usage=None):
    """
    Map LLM agent response to transaction update fields for both classification and payee lookup.
    agent_type: 'payee' or 'classification' (REQUIRED, explicit)
    """
    if agent_type not in ("payee", "classification"):
        raise ValueError(
            f"agent_type must be 'payee' or 'classification', got {agent_type}"
        )

    # Build method strings
    if tool_usage and any(tool_usage.values()):
        tool_parts = []
        for name, count in tool_usage.items():
            label = name.replace("_", " ").replace("search", "search").title()
            if count > 1:
                tool_parts.append(f"{label} ({count}x)")
            else:
                tool_parts.append(label)
        method_str = f"AI + {', '.join(tool_parts)}"
    else:
        method_str = "AI Only"

    update_fields = dict(response)

    if agent_type == "payee":
        # Map 'reasoning' to 'payee_reasoning' for model update
        if "reasoning" in update_fields:
            update_fields["payee_reasoning"] = update_fields.pop("reasoning")
        update_fields["payee_extraction_method"] = method_str
        logger.info(
            f"[Payee] Returning update_fields: {update_fields}, tool_usage: {tool_usage}"
        )
        allowed = [
            "normalized_description",
            "payee",
            "confidence",
            "payee_reasoning",
            "transaction_type",
            "questions",
            "payee_extraction_method",
        ]
        update_fields = {k: v for k, v in update_fields.items() if k in allowed}
        if "category" in update_fields:
            update_fields["category"] = normalize_category(update_fields["category"])
        return update_fields
    elif agent_type == "classification":
        update_fields["classification_method"] = method_str
        # Map category from LLM response if present
        if "category_id" in update_fields and not update_fields.get("category"):
            update_fields["category"] = update_fields["category_id"]
        elif "category_name" in update_fields and not update_fields.get("category"):
            update_fields["category"] = update_fields["category_name"]
        logger.info(
            f"[Classification] Returning update_fields: {update_fields}, tool_usage: {tool_usage}"
        )
        # Only include fields that exist on the Transaction model. LLM prompt and model fields must always be kept in sync. Only model-backed fields are allowed.
        allowed = [
            "classification_type",
            "worksheet",
            "category",
            "confidence",
            "reasoning",
            "business_percentage",
            "questions",
            "classification_method",
        ]
        update_fields = {k: v for k, v in update_fields.items() if k in allowed}
        if "category" in update_fields:
            update_fields["category"] = normalize_category(update_fields["category"])
        return update_fields


def sync_transaction_id_sequence():
    """Ensure the transaction ID sequence is in sync with the max ID in the table."""
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT setval(pg_get_serial_sequence('profiles_transaction', 'id'), (SELECT COALESCE(MAX(id), 1) FROM profiles_transaction));"
        )


def ingest_manifest_to_organizer(
    manifest, organizer_workbook, binder, business_profile, manifest_hash=None
):
    """
    Ingest a manifest dict and create/update BinderItems and BinderItemFields for the given OrganizerWorkbook and TaxYear (binder).
    This is the canonical ingestion function for use by both the management command and the admin panel.
    Args:
        manifest (dict): The loaded manifest JSON.
        organizer_workbook (OrganizerWorkbook): The organizer workbook instance.
        binder (TaxYear): The TaxYear (binder) instance.
        business_profile (BusinessProfile): The business profile instance.
        manifest_hash (str, optional): The manifest hash, if available.
    Returns:
        dict: Summary of created/updated counts.
    """
    from profiles.models import BinderItem, BinderItemField
    from django.core.exceptions import FieldDoesNotExist
    from django.db import transaction

    created_count = 0
    updated_count = 0
    field_created = 0
    field_updated = 0
    media_subdir = "organizers/outputs/4/"
    pages = manifest.get("pages", [])
    # --- BEGIN: Workflow mapping config ---
    CALCULATED_REPORTS = {
        "6A": {"action_type": "calculated", "calculated_by_report": "6A"},
        "6A Worksheet": {"action_type": "calculated", "calculated_by_report": "6A"},
    }
    UPLOAD_DOCS = {
        "W2": {"action_type": "upload", "required_document_type": "W2"},
        "1099": {"action_type": "upload", "required_document_type": "1099"},
    }
    INFO_ONLY_PAGES = {
        "Cover_Sheet": {"action_type": "info_only"},
        "Mail/Presentation Sheet": {"action_type": "info_only"},
    }
    IGNORED_PAGES = {
        "Sample_Page": {"action_type": "ignore"},
    }
    # --- END: Workflow mapping config ---
    with transaction.atomic():
        for idx, page in enumerate(pages):
            form_id = page.get("label")
            label = page.get("Title") or form_id
            if label and len(label) > 255:
                label = label[:252] + "..."
            summary = page.get("summary", "")
            page_number = page.get("page_number")
            thumbnail_file = page.get("thumbnail_file")
            if thumbnail_file and not (
                "/" in thumbnail_file or thumbnail_file.startswith(media_subdir)
            ):
                thumbnail_file = media_subdir + thumbnail_file
            pdf_page_file = page.get("pdf_page_file")
            if pdf_page_file and not (
                "/" in pdf_page_file or pdf_page_file.startswith(media_subdir)
            ):
                pdf_page_file = media_subdir + pdf_page_file
            has_user_data = page.get("has_user_data", False)
            action_type = "manual"
            calculated_by_report = None
            required_document_type = None
            source = "Organizer"
            priority = page.get("priority", "medium")
            mapping = CALCULATED_REPORTS.get(form_id) or CALCULATED_REPORTS.get(label)
            if mapping:
                action_type = mapping.get("action_type", action_type)
                calculated_by_report = mapping.get("calculated_by_report")
                source = "Report"
            mapping = UPLOAD_DOCS.get(form_id) or UPLOAD_DOCS.get(label)
            if mapping:
                action_type = mapping.get("action_type", action_type)
                required_document_type = mapping.get("required_document_type")
                source = "Upload"
            display_in_checklist = True
            if form_id in INFO_ONLY_PAGES or label in INFO_ONLY_PAGES:
                action_type = "info_only"
                display_in_checklist = False
            elif form_id in IGNORED_PAGES or label in IGNORED_PAGES:
                action_type = "ignore"
                display_in_checklist = False
            if not form_id:
                continue
            binder_item, created = BinderItem.objects.get_or_create(
                tax_year=binder,
                organizer_workbook=organizer_workbook,
                form_id=form_id,
                defaults={
                    "type": "form",
                    "label": label,
                    "status": "not_started",
                    "order": idx + 1,
                    "is_generated": True,
                    "summary": summary,
                    "notes": "",
                    "page_number": page_number,
                    "thumbnail_file": thumbnail_file,
                    "pdf_page_file": pdf_page_file,
                    "has_user_data": has_user_data,
                    "action_type": action_type,
                    "calculated_by_report": calculated_by_report,
                    "required_document_type": required_document_type,
                    "source": source,
                    "display_in_checklist": display_in_checklist,
                    "manifest_hash": manifest_hash,
                    "priority": priority,
                },
            )
            updated = False
            for field, value in [
                ("label", label),
                ("summary", summary),
                ("page_number", page_number),
                ("thumbnail_file", thumbnail_file),
                ("pdf_page_file", pdf_page_file),
                ("has_user_data", has_user_data),
                ("action_type", action_type),
                ("calculated_by_report", calculated_by_report),
                ("required_document_type", required_document_type),
                ("source", source),
                ("display_in_checklist", display_in_checklist),
                ("manifest_hash", manifest_hash),
                ("priority", priority),
            ]:
                try:
                    if (
                        hasattr(binder_item, field)
                        and getattr(binder_item, field) != value
                    ):
                        setattr(binder_item, field, value)
                        updated = True
                except FieldDoesNotExist:
                    continue
            if binder_item.tax_year != binder:
                binder_item.tax_year = binder
                updated = True
            if binder_item.organizer_workbook != organizer_workbook:
                binder_item.organizer_workbook = organizer_workbook
                updated = True
            if (
                business_profile
                and getattr(binder_item, "business_profile", None) != business_profile
            ):
                binder_item.business_profile = business_profile
                updated = True
            if updated:
                binder_item.save()
                updated_count += 1
            elif created:
                if has_user_data:
                    created_count += 1
                binder_item.save()
            data = page.get("data", {})
            if isinstance(data, dict):
                items = data.items()
            elif isinstance(data, list):
                items = enumerate(data)
            else:
                items = []
            for field_key, field_value in items:
                field_label = str(field_key)
                value_str = (
                    json.dumps(field_value)
                    if isinstance(field_value, (dict, list))
                    else str(field_value)
                )
                if len(field_label) > 255:
                    field_label = field_label[:252] + "..."
                field_obj, f_created = BinderItemField.objects.get_or_create(
                    binder_item=binder_item,
                    label=field_label,
                    defaults={
                        "value": value_str,
                        "status": "missing",
                        "order": 0,
                        "notes": "",
                    },
                )
                if f_created:
                    field_created += 1
                else:
                    if field_obj.value != value_str:
                        field_obj.value = value_str
                        field_obj.save()
                        field_updated += 1
    return {
        "created": created_count,
        "updated": updated_count,
        "field_created": field_created,
        "field_updated": field_updated,
    }
