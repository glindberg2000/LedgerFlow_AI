from django.apps import AppConfig


class OrganizersConfig(AppConfig):
    name = "organizers"
    verbose_name = "Organizers"

    def ready(self):
        import organizers.signals
