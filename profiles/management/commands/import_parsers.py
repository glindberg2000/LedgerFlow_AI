import os
from django.core.management.base import BaseCommand
from profiles.parsers_utilities.models import ParserTemplate

PARSERS_DIR = os.path.join(
    os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "dataextractai",
        "parsers",
        "dataextractai",
        "parsers",
    )
)


class Command(BaseCommand):
    help = "Batch import parser scripts as ParserTemplate entries."

    def handle(self, *args, **options):
        count = 0
        for fname in os.listdir(PARSERS_DIR):
            if fname.endswith("_parser.py"):
                name = fname.replace("_parser.py", "").replace("_", " ").title()
                bank = fname.split("_")[0].title() if "_" in fname else "Unknown"
                module_path = (
                    f"dataextractai.parsers.dataextractai.parsers.{fname[:-3]}"
                )
                # Only create if not already present
                if not ParserTemplate.objects.filter(
                    name=name, bank=bank, type="pdf"
                ).exists():
                    ParserTemplate.objects.create(
                        name=name,
                        bank=bank,
                        type="pdf",
                        template=module_path,
                        is_active=True,
                    )
                    count += 1
        self.stdout.write(self.style.SUCCESS(f"Imported {count} parser templates."))
