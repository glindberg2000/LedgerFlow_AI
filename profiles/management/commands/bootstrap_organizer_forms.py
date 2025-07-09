from django.core.management.base import BaseCommand
from profiles.models import OrganizerFormTemplate, OrganizerFormField


class Command(BaseCommand):
    help = "Bootstrap organizer form templates and fields (e.g., Form 15)"

    def handle(self, *args, **options):
        # --- Form 15: Itemized Deductions – Contributions ---
        template, created = OrganizerFormTemplate.objects.get_or_create(
            name="Itemized Deductions – Contributions (Form 15)",
            defaults={
                "description": "Enter details for charitable contributions for itemized deductions.",
                "notes": "Prefilled value is for common miscellaneous organized charities.",
            },
        )
        fields = [
            {
                "label": "Organization or Description of Contribution",
                "field_type": "text",
                "help_text": "Enter the name or description of the organization.",
                "required": True,
                "order": 1,
            },
            {
                "label": "Prefilled: MISCELLANEOUS ORGANIZED CHARITIES",
                "field_type": "text",
                "help_text": "Prefilled value for common charities. Edit if needed.",
                "required": False,
                "order": 2,
            },
            {
                "label": "Amount",
                "field_type": "number",
                "help_text": "Enter the amount contributed.",
                "required": True,
                "order": 3,
            },
        ]
        for field in fields:
            OrganizerFormField.objects.get_or_create(
                template=template, label=field["label"], defaults=field
            )
        self.stdout.write(
            self.style.SUCCESS("Form 15 template and fields bootstrapped!")
        )
