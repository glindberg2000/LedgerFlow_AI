import os
import json
from django.conf import settings
import re

CHECKLIST_INDEX_PATH = os.path.join(
    settings.BASE_DIR, "profiles", "bootstrap", "tax_checklist_index.json"
)


def load_canonical_tax_checklist_index():
    if not os.path.exists(CHECKLIST_INDEX_PATH):
        raise FileNotFoundError(
            f"Required checklist index file not found: {CHECKLIST_INDEX_PATH}"
        )
    with open(CHECKLIST_INDEX_PATH, "r") as f:
        return json.load(f)


def make_url_safe_client_id(name):
    # Lowercase, replace spaces and special chars with underscores, remove non-url-safe chars
    safe = re.sub(r"[^a-zA-Z0-9_-]", "_", name.lower())
    safe = re.sub(r"_+", "_", safe)
    return safe.strip("_")


# Example usage in bootstrap logic:
def create_demo_business_profile():
    company_name = "Acme, Inc."
    client_id = make_url_safe_client_id(company_name)
    from profiles.models import BusinessProfile

    BusinessProfile.objects.create(
        client_id=client_id,
        company_name=company_name,
        # ... other fields ...
    )
