from django.apps import AppConfig


class ProfilesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "profiles"

    def ready(self):
        # autodiscover_parsers()  # Temporarily disabled to debug recursion error
        pass


class ProfilesTestConfig(AppConfig):
    name = "profiles_test"
