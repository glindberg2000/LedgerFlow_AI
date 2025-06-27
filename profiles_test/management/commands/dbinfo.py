from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Prints current database connection info (database, user, server address)"

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT current_database(), current_user, inet_server_addr();"
            )
            db, user, addr = cursor.fetchone()
            self.stdout.write(self.style.SUCCESS(f"Database: {db}"))
            self.stdout.write(self.style.SUCCESS(f"User: {user}"))
            self.stdout.write(self.style.SUCCESS(f"Server Address: {addr}"))
