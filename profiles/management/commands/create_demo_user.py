from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import IntegrityError


class Command(BaseCommand):
    help = "Create demo user (demo/demo1234) for the current database"

    def handle(self, *args, **options):
        User = get_user_model()
        demo_username = "demo"
        demo_password = "demo1234"
        demo_email = "demo@example.com"

        try:
            if User.objects.filter(username=demo_username).exists():
                self.stdout.write(
                    self.style.NOTICE(
                        f"Demo user '{demo_username}' already exists - skipping creation"
                    )
                )
            else:
                User.objects.create_superuser(demo_username, demo_email, demo_password)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✅ Demo superuser created: username='{demo_username}', password='{demo_password}'"
                    )
                )
                self.stdout.write(
                    self.style.WARNING(
                        "🔐 [SECURITY] Change this password immediately in any real deployment!"
                    )
                )
        except IntegrityError as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Failed to create demo user: {e}")
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Unexpected error: {e}")
            )