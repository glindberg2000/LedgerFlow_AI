from django.core.management.base import BaseCommand
from profiles.models import BinderRowTemplate


class Command(BaseCommand):
    help = "Bootstrap sample BinderRowTemplate entries (e.g., Form 15: Charitable Contributions)"

    def handle(self, *args, **options):
        # Example: Form 15 - Charitable Contributions
        template, created = BinderRowTemplate.objects.get_or_create(
            section="Form 15",
            label="Charitable Contributions",
            defaults={
                "description": "Enter the total amount of charitable contributions for itemized deductions.",
                "is_generated": False,
                "order": 1,
                "notes": "Fill in the amount for the current year. Previous year will be shown for comparison.",
            },
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created template: {template}"))
        else:
            self.stdout.write(
                self.style.WARNING(f"Template already exists: {template}")
            )

        # Add more templates here as needed
