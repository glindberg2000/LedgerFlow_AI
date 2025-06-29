from django.apps import AppConfig
import os
import sys


class ProfilesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "profiles"

    def ready(self):
        # Only run in main process, not migrations or shell_plus
        if os.environ.get("RUN_MAIN") == "true" or (
            len(sys.argv) > 1
            and sys.argv[1] in ["runserver", "runserver_plus", "uwsgi", "gunicorn"]
        ):
            try:
                from dataextractai.parsers_core.autodiscover import autodiscover_parsers
                from .agents import bootstrap_tools_and_agents

                autodiscover_parsers()
                bootstrap_tools_and_agents()
            except Exception as e:
                import logging

                logging.getLogger("django").error(
                    f"[profiles.apps] Bootstrapping tools/agents failed: {e}"
                )
                # Do not crash startup; log and continue
