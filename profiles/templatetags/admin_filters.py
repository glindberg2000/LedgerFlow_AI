from django import template
from django.urls import reverse

register = template.Library()


@register.simple_tag(takes_context=True)
def get_admin_nav(context):
    app_list = context["available_apps"]

    # Define the structure of the navigation
    nav_structure = {
        "Core": {
            "models": ["BusinessProfile", "Transaction", "StatementFile"],
            "icon": "💼",
        },
        "AI & Processing": {
            "models": ["Agent", "LLMConfig", "ProcessingTask", "Tool"],
            "icon": "🤖",
        },
        "Configuration": {
            "models": ["IRSWorksheet", "IRSExpenseCategory", "BusinessExpenseCategory"],
            "icon": "⚙️",
        },
        "System": {"models": ["User", "Group"], "icon": "👥"},
    }

    # Build the navigation list
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

    # Add reports as a standalone link
    nav.append(
        {
            "name": "Reports",
            "url": reverse("admin:reports_reportsproxy_changelist"),
            "icon": "📈",
        }
    )

    return nav
