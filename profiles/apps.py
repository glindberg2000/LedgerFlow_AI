from django.apps import AppConfig


class ProfilesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "profiles"

    def ready(self):
        # Ensure all parsers are registered at app startup
        from dataextractai.parsers_core.autodiscover import autodiscover_parsers
        from .agents import bootstrap_tools_and_agents

        autodiscover_parsers()
        bootstrap_tools_and_agents()
