from django import template
from django.urls import reverse

register = template.Library()


@register.simple_tag(takes_context=True)
def get_admin_nav(context):
    app_list = context["available_apps"]

    nav_structure = {
        "Clients": {
            "models": ["BusinessProfile", "BusinessExpenseCategory"],
            "icon": "👤",
        },
        "Workflow": {
            "models": [
                "TaxYear",  # Binders
                "BinderItem",  # Binder Items
                "StatementFile",  # Statement Files
                "Transaction",  # Transactions
            ],
            "icon": "📂",
        },
        "Reports": {
            "models": [],  # No dropdowns, just a link
            "icon": "📈",
        },
        "Setup & Ingest": {
            "models": [
                "OrganizerWorkbook",  # Organizer Workbooks (upload/ingest)
                "ImportedParser",
                "ParsingRun",
            ],
            "icon": "🛠️",
        },
        "Worksheets": {
            "models": [
                "IRSWorksheet",
                "IRSExpenseCategory",
            ],
            "icon": "🧾",
        },
        "AI & Utilities": {
            "models": [
                "Agent",
                "LLMConfig",
                "Tool",
            ],
            "icon": "🤖",
        },
        "System": {
            "models": ["User", "Group"],
            "icon": "👥",
        },
    }

    nav = []
    for section_name, section_data in nav_structure.items():
        # Special case for Reports: add as a single link, not a dropdown
        if section_name == "Reports":
            nav.append(
                {
                    "name": "Reports",
                    "url": reverse("admin:reports_reportsproxy_changelist"),
                    "icon": section_data.get("icon", ""),
                }
            )
            continue
        section = {
            "name": section_name,
            "icon": section_data.get("icon", ""),
            "models": [],
        }
        for app in app_list:
            for model in app["models"]:
                if model["object_name"] in section_data["models"]:
                    section["models"].append(
                        {"name": model["name"], "url": model["admin_url"]}
                    )
        if section["models"]:
            nav.append(section)
    return nav
