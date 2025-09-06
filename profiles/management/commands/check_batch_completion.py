"""
Check and Process Completed OpenAI Batch Jobs

This command checks for completed OpenAI batch jobs in ProcessingTasks
and processes their results. Should be run periodically via cron job.

Usage:
python manage.py check_batch_completion
python manage.py check_batch_completion --dry-run
"""

from django.core.management.base import BaseCommand
from profiles.utils.async_batch_processor import check_and_process_completed_batches


class Command(BaseCommand):
    help = "Check for completed OpenAI batch jobs and process results"
    
    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be processed without making changes"
        )
        
    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        
        if dry_run:
            from profiles.models import ProcessingTask
            
            pending_tasks = ProcessingTask.objects.filter(
                status="processing",
                task_metadata__openai_batch_id__isnull=False
            )
            
            self.stdout.write(f"Found {pending_tasks.count()} pending batch tasks:")
            
            for task in pending_tasks:
                batch_id = task.task_metadata.get("openai_batch_id", "Unknown")
                agent_name = task.task_metadata.get("agent_name", "Unknown")
                
                self.stdout.write(
                    f"  Task {task.task_id}: {agent_name}, "
                    f"{task.transaction_count} transactions, "
                    f"Batch ID: {batch_id}"
                )
                
        else:
            self.stdout.write("Checking for completed batch jobs...")
            
            completed_count = check_and_process_completed_batches()
            
            if completed_count > 0:
                self.stdout.write(
                    self.style.SUCCESS(f"Processed {completed_count} completed batch jobs")
                )
            else:
                self.stdout.write("No completed batch jobs found")