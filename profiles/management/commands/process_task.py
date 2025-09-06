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
from profiles.utils.utils import get_update_fields_from_response

# Add these imports for organizer extraction
from organizers.models import OrganizerWorkbook, OrganizerOutput
from dataextractai.parsers.organizer_extractor import OrganizerExtractor
import json

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

            if task.task_type == "organizer_extraction":
                # --- ORGANIZER EXTRACTION LOGIC ---
                try:
                    workbook_id = task.task_metadata.get("workbook_id")
                    workbook = OrganizerWorkbook.objects.get(id=workbook_id)
                    workbook.status = "processing"
                    workbook.save()
                    task.status = "processing"
                    task.save()

                    # Set up output directory
                    output_dir = os.path.join(
                        settings.MEDIA_ROOT, "organizers", "outputs", str(workbook.id)
                    )
                    os.makedirs(output_dir, exist_ok=True)

                    # Run the extractor
                    extractor = OrganizerExtractor(
                        workbook.original_file.path, output_dir
                    )
                    # Get page range from task_metadata if present
                    pages_to_parse = task.task_metadata.get(
                        "pages_to_parse", ""
                    ).strip()
                    page_numbers = None
                    if pages_to_parse:
                        # Parse string like "1-5,8,10-12" into a list of ints
                        import re

                        page_numbers = set()
                        for part in pages_to_parse.split(","):
                            part = part.strip()
                            if "-" in part:
                                start, end = part.split("-")
                                page_numbers.update(range(int(start), int(end) + 1))
                            elif part:
                                page_numbers.add(int(part))
                        page_numbers = sorted(page_numbers)
                    # Run extraction with or without page_numbers
                    result = extractor.extract_all_fields_manifest(
                        page_numbers=page_numbers
                    )

                    # Look for cleaned manifest
                    cleaned_manifest_path = os.path.join(
                        output_dir, "all_fields_manifest_cleaned.json"
                    )
                    if os.path.exists(cleaned_manifest_path):
                        # Save as OrganizerOutput
                        OrganizerOutput.objects.create(
                            workbook=workbook,
                            output_type="manifest",
                            file=os.path.relpath(
                                cleaned_manifest_path, settings.MEDIA_ROOT
                            ),
                        )
                        # --- PATCH: Parse manifest and update OrganizerWorkbook fields ---
                        try:
                            with open(cleaned_manifest_path, "r") as f:
                                manifest = json.load(f)
                            workbook.manifest_hash = manifest.get("file_hash")
                            workbook.manifest_file_summary = manifest.get(
                                "file_summary"
                            )
                            if "pages" in manifest:
                                workbook.manifest_page_count = len(manifest["pages"])
                            elif "items" in manifest:
                                workbook.manifest_page_count = len(manifest["items"])
                            else:
                                workbook.manifest_page_count = None
                            # --- INGEST MANIFEST TO CREATE BINDER ITEMS ---
                            from profiles.utils.utils import (
                                ingest_manifest_to_organizer,
                            )

                            ingest_manifest_to_organizer(
                                manifest=manifest,
                                organizer_workbook=workbook,
                                binder=workbook.tax_year,
                                business_profile=workbook.business_profile,
                                manifest_hash=workbook.manifest_hash,
                            )
                            workbook.status = "manifest_ready"
                            logger.info(
                                f"Updated OrganizerWorkbook {workbook.id} with manifest metadata and ingested BinderItems."
                            )
                        except Exception as e:
                            logger.error(
                                f"Failed to update OrganizerWorkbook with manifest or ingest BinderItems: {e}"
                            )
                        # --- END PATCH ---
                        workbook.status = "completed"
                        task.status = "completed"
                        task.error_details = {}
                        logger.info(
                            f"Organizer extraction completed for workbook {workbook.id}"
                        )
                    else:
                        workbook.status = "failed"
                        task.status = "failed"
                        task.error_details = {
                            "error": "Manifest not found after extraction."
                        }
                        logger.error(f"Manifest not found for workbook {workbook.id}")
                    workbook.save()
                    task.save()
                except Exception as e:
                    logger.error(f"Organizer extraction failed: {e}")
                    if "workbook" in locals():
                        workbook.status = "failed"
                        workbook.save()
                    task.status = "failed"
                    task.error_details = {"error": str(e)}
                    task.save()
                return

            # --- BATCH PROCESSING LOGIC ---
            if task.task_metadata.get("batch_processing"):
                # Handle OpenAI Batch API tasks
                from profiles.utils.async_batch_processor import submit_processing_task_batch
                
                logger.info(f"Starting batch processing for task {task_id}")
                success = submit_processing_task_batch(task)
                
                if success:
                    logger.info(f"Successfully submitted batch processing task {task_id} to OpenAI")
                else:
                    logger.error(f"Failed to submit batch processing task {task_id} to OpenAI")
                    
                return

            # --- EXISTING TRANSACTION-BASED LOGIC ---
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
