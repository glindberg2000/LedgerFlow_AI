from django.apps import AppConfig


class ProfilesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "profiles"

    def ready(self):
        # Ensure all parsers are registered at app startup
        from dataextractai.parsers_core.autodiscover import autodiscover_parsers

        autodiscover_parsers()
