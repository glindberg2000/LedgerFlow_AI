from django import template
from django.urls import reverse

register = template.Library()


@register.simple_tag(takes_context=True)
def get_admin_nav(context):
    app_list = context["available_apps"]

    # Streamlined nav structure
    nav_structure = {
        "Core": {
            "models": [
                "BusinessProfile",
                "Transaction",
                "StatementFile",
                "ProcessingTask",
                "ParsingRun",
            ],
            "icon": "💼",
        },
        "AI & Processing": {
            "models": [
                "LLMConfig",
                "Agent",
                "Tool",
            ],
            "icon": "🤖",
        },
        "Taxonomy": {
            "models": [
                "IRSWorksheet",
                "IRSExpenseCategory",
                "BusinessExpenseCategory",
            ],
            "icon": "🧾",
        },
        "Parsers Utilities": {
            "models": ["ImportedParser"],
            "icon": "🧩",
        },
        "System": {
            "models": ["User", "Group"],
            "icon": "👥",
        },
    }

    nav = []
    for section_name, section_data in nav_structure.items():
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

    # Add Reports as a standalone link at the end
    nav.append(
        {
            "name": "Reports",
            "url": reverse("admin:reports_reportsproxy_changelist"),
            "icon": "📈",
        }
    )
    return nav
