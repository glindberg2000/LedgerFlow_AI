import os
import sys
import logging
import django
import time
from django.core.management.base import BaseCommand
from django.conf import settings
from profiles.models import ProcessingTask, Transaction, Agent
from profiles.admin import call_agent
from django.db import transaction
from profiles.utils import get_update_fields_from_response

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Process a single task"

    def add_arguments(self, parser):
        parser.add_argument("task_id", type=str, help="The task ID to process")
        parser.add_argument("--log-file", type=str, help="Path to log file")
        parser.add_argument(
            "--max-retries",
            type=int,
            default=5,
            help="Maximum number of retries to find the task",
        )
        parser.add_argument(
            "--retry-delay",
            type=float,
            default=1.0,
            help="Delay in seconds between retries",
        )

    def handle(self, *args, **options):
        # Set the correct settings module
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ledgerflow.settings")

        # Initialize Django
        django.setup()

        task_id = options["task_id"]
        log_file = options.get("log_file")
        max_retries = options["max_retries"]
        retry_delay = options["retry_delay"]

        # Set up logging
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s [%(levelname)s] %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                )
            )
            logger.addHandler(file_handler)

        # Try to find the task with retries
        task = None
        for attempt in range(max_retries):
            try:
                task = ProcessingTask.objects.get(task_id=task_id)
                logger.info(f"Found task {task_id} on attempt {attempt + 1}")
                break
            except ProcessingTask.DoesNotExist:
                if attempt < max_retries - 1:
                    logger.warning(
                        f"Task {task_id} not found on attempt {attempt + 1}, retrying in {retry_delay} seconds..."
                    )
                    time.sleep(retry_delay)
                else:
                    logger.error(
                        f"Task {task_id} not found after {max_retries} attempts"
                    )
                    raise

        try:
            logger.info(f"STARTING TASK {task_id}")

            # Get the appropriate agent
            if task.task_type == "payee_lookup":
                agent = Agent.objects.get(name="Payee Lookup Agent")
            else:  # classification
                agent = Agent.objects.get(name="Classification Agent")

            if not agent:
                raise ValueError(f"No agent found for task type {task.task_type}")

            # Process each transaction
            # Use the M2M field for robust, future-proof processing
            transactions = task.transactions.all()
            total = transactions.count()
            success_count = 0
            error_count = 0
            error_details = {}

            for idx, transaction in enumerate(transactions, 1):
                try:
                    # Call the agent
                    response = call_agent(agent.name, transaction)

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
                    Transaction.objects.filter(id=transaction.id).update(
                        **update_fields
                    )
                    success_count += 1
                    logger.info(f"Processed transaction {transaction.id} successfully")

                except Exception as e:
                    error_count += 1
                    error_details[str(transaction.id)] = str(e)
                    logger.error(
                        f"Error processing transaction {transaction.id}: {str(e)}"
                    )

                # Update task progress
                task.processed_count = idx
                task.error_count = error_count
                task.error_details = error_details
                task.save()

            # Update final task status
            task.status = "completed" if error_count == 0 else "failed"
            task.save()

            logger.info(
                f"Task completed: {success_count} successful, {error_count} failed"
            )

        except ProcessingTask.DoesNotExist:
            logger.error(f"Task {task_id} not found")
            raise
        except Exception as e:
            logger.error(f"Task failed: {str(e)}")
            if "task" in locals():
                task.status = "failed"
                task.error_details = {"error": str(e)}
                task.save()
            raise
