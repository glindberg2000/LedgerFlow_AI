from django.core.management.base import BaseCommand
from profiles.models import TaxYear, BinderRow, BinderRowTemplate


class Command(BaseCommand):
    help = "Populate BinderRows for a given TaxYear from all BinderRowTemplates."

    def add_arguments(self, parser):
        parser.add_argument(
            "--taxyear_id", type=int, help="ID of the TaxYear (binder) to populate"
        )

    def handle(self, *args, **options):
        taxyear_id = options.get("taxyear_id")
        if not taxyear_id:
            self.stderr.write(self.style.ERROR("You must provide --taxyear_id"))
            return
        try:
            taxyear = TaxYear.objects.get(id=taxyear_id)
        except TaxYear.DoesNotExist:
            self.stderr.write(
                self.style.ERROR(f"TaxYear with id {taxyear_id} does not exist")
            )
            return
        templates = BinderRowTemplate.objects.all().order_by("order")
        created_count = 0
        for template in templates:
            row, created = BinderRow.objects.get_or_create(
                tax_year=taxyear,
                template=template,
                defaults={
                    "is_generated": template.is_generated,
                    "section": template.section,
                    "label": template.label,
                    "description": template.description,
                    "calculation_query": template.calculation_query,
                    "order": template.order,
                    "notes": template.notes,
                },
            )
            if created:
                created_count += 1
        self.stdout.write(
            self.style.SUCCESS(
                f"Populated {created_count} BinderRows for TaxYear {taxyear}"
            )
        )
