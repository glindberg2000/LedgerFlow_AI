from django.apps import AppConfig


class ParsersUtilitiesConfig(AppConfig):
    name = "profiles.parsers_utilities"

    def ready(self):
        # Import here to avoid import cycles
        from .models import ImportedParser
        import sys
        import os

        PDF_EXTRACTOR_PATH = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../../PDF-extractor")
        )
        if PDF_EXTRACTOR_PATH not in sys.path:
            sys.path.insert(0, PDF_EXTRACTOR_PATH)
        try:
            from dataextractai.parsers_core.autodiscover import autodiscover_parsers

            autodiscover_parsers()
            from dataextractai.parsers_core.registry import ParserRegistry

            parser_names = ParserRegistry.list_parsers()
            for name in parser_names:
                ImportedParser.objects.update_or_create(name=name)
        except Exception as e:
            # Log or ignore errors, do not crash app
            pass


default_app_config = "profiles.parsers_utilities.apps.ParsersUtilitiesConfig"
