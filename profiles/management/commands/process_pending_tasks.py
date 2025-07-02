import logging
import django
import os
from django.core.management.base import BaseCommand
from profiles.models import ProcessingTask, Transaction, Agent
from profiles.admin import call_agent
from django.db import transaction as db_transaction
from django.utils import timezone
from django.conf import settings
from profiles.utils import get_update_fields_from_response

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Process all pending tasks"

    def handle(self, *args, **options):
        # Set the correct settings module
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ledgerflow.settings")

        # Initialize Django
        django.setup()

        # Debug output for database settings
        self.stdout.write(
            f"Using database: {settings.DATABASES['default']['HOST']}:{settings.DATABASES['default']['PORT']}"
        )
        self.stdout.write(f"Database name: {settings.DATABASES['default']['NAME']}")
        self.stdout.write(f"Database user: {settings.DATABASES['default']['USER']}")

        # Get all pending tasks
        pending_tasks = ProcessingTask.objects.filter(status="pending")

        if not pending_tasks.exists():
            self.stdout.write(self.style.SUCCESS("No pending tasks found"))
            return

        self.stdout.write(f"Found {pending_tasks.count()} pending tasks")

        for task in pending_tasks:
            try:
                self.stdout.write(f"Processing task {task.task_id}")

                # Update task status to processing
                with db_transaction.atomic():
                    task.status = "processing"
                    task.started_at = timezone.now()
                    task.save(force_update=True)

                # Get the appropriate agent
                if task.task_type == "payee_lookup":
                    agent = Agent.objects.get(name="Payee Lookup Agent")
                else:  # classification
                    agent = Agent.objects.get(name="Classification Agent")

                if not agent:
                    raise ValueError(f"No agent found for task type {task.task_type}")

                # Process each transaction
                total = task.transactions.count()
                success_count = 0
                error_count = 0
                error_details = {}

                for idx, tx in enumerate(task.transactions.all(), 1):
                    try:
                        # Call the agent
                        response = call_agent(agent.name, tx)

                        # Use shared field mapping logic
                        agent_type = (
                            "payee"
                            if task.task_type == "payee_lookup"
                            else "classification"
                        )
                        update_fields = get_update_fields_from_response(
                            agent, response, agent_type
                        )

                        # Update the transaction
                        Transaction.objects.filter(id=tx.id).update(**update_fields)
                        success_count += 1
                        self.stdout.write(f"Processed transaction {tx.id} successfully")

                    except Exception as e:
                        error_count += 1
                        error_details[str(tx.id)] = str(e)
                        self.stdout.write(
                            self.style.ERROR(
                                f"Error processing transaction {tx.id}: {str(e)}"
                            )
                        )

                    # Update task progress
                    with db_transaction.atomic():
                        task.processed_count = idx
                        task.error_count = error_count
                        task.error_details = error_details
                        task.save(force_update=True)

                # Update final task status
                with db_transaction.atomic():
                    task.status = "completed" if error_count == 0 else "failed"
                    task.save(force_update=True)

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Task {task.task_id} completed: {success_count} successful, {error_count} failed"
                    )
                )

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Failed to process task {task.task_id}: {str(e)}")
                )
                with db_transaction.atomic():
                    task.status = "failed"
                    task.error_details = {"error": str(e)}
                    task.save(force_update=True)
