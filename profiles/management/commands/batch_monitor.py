"""
Batch Monitor - Track and manage OpenAI batch jobs

This command provides monitoring, cost tracking, and management utilities 
for async batch processing jobs.

Usage:
python manage.py batch_monitor --list                # List all batch jobs
python manage.py batch_monitor --status batch_id     # Check specific batch status 
python manage.py batch_monitor --costs               # Show cost analysis
python manage.py batch_monitor --cleanup             # Clean up old status files
"""

import json
import glob
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from django.core.management.base import BaseCommand
from django.conf import settings
from openai import OpenAI


class BatchMonitor:
    """Monitor and manage OpenAI batch jobs"""
    
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.status_dir = Path(settings.BASE_DIR) / "batch_status"
        self.status_dir.mkdir(exist_ok=True)
        
        # Pricing (as of 2024, varies by model)
        self.model_pricing = {
            "gpt-4.1-mini": {
                "input_batch": 0.000075,   # 50% discount from $0.00015
                "output_batch": 0.0003,    # 50% discount from $0.0006
                "input_realtime": 0.00015,
                "output_realtime": 0.0006
            },
            "o4-mini": {
                "input_batch": 0.000075,   # 50% discount  
                "output_batch": 0.0003,    # 50% discount
                "input_realtime": 0.00015,
                "output_realtime": 0.0006
            }
        }
        
    def list_local_batches(self) -> List[Dict]:
        """List all local batch status files"""
        
        status_files = glob.glob(str(self.status_dir / "batch_*.json"))
        batches = []
        
        for file_path in status_files:
            try:
                with open(file_path, 'r') as f:
                    batch_data = json.load(f)
                    batch_data['status_file'] = file_path
                    batches.append(batch_data)
            except Exception as e:
                print(f"Error reading {file_path}: {e}")
                
        # Sort by creation date
        batches.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return batches
        
    def get_openai_batch_status(self, batch_id: str) -> Dict:
        """Get current status from OpenAI"""
        
        try:
            batch = self.client.batches.retrieve(batch_id)
            
            return {
                "id": batch.id,
                "status": batch.status,
                "created_at": batch.created_at,
                "completed_at": batch.completed_at,
                "request_counts": batch.request_counts._asdict() if batch.request_counts else {},
                "metadata": batch.metadata or {}
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "status": "error"
            }
            
    def estimate_batch_cost(self, transactions_count: int, model: str, 
                           avg_input_tokens: int = 500, avg_output_tokens: int = 100) -> Dict:
        """Estimate batch processing cost"""
        
        if model not in self.model_pricing:
            return {"error": f"Unknown model: {model}"}
            
        pricing = self.model_pricing[model]
        
        # Calculate costs
        input_cost_batch = (avg_input_tokens / 1000) * pricing["input_batch"] * transactions_count
        output_cost_batch = (avg_output_tokens / 1000) * pricing["output_batch"] * transactions_count
        total_batch_cost = input_cost_batch + output_cost_batch
        
        # Compare with real-time costs
        input_cost_realtime = (avg_input_tokens / 1000) * pricing["input_realtime"] * transactions_count
        output_cost_realtime = (avg_output_tokens / 1000) * pricing["output_realtime"] * transactions_count
        total_realtime_cost = input_cost_realtime + output_cost_realtime
        
        savings = total_realtime_cost - total_batch_cost
        savings_percent = (savings / total_realtime_cost) * 100 if total_realtime_cost > 0 else 0
        
        return {
            "model": model,
            "transactions": transactions_count,
            "estimated_tokens": {
                "input": avg_input_tokens,
                "output": avg_output_tokens
            },
            "batch_cost": {
                "input": input_cost_batch,
                "output": output_cost_batch,
                "total": total_batch_cost
            },
            "realtime_cost": {
                "input": input_cost_realtime,
                "output": output_cost_realtime,
                "total": total_realtime_cost
            },
            "savings": {
                "amount": savings,
                "percent": savings_percent
            }
        }
        
    def get_cost_analysis(self) -> Dict:
        """Analyze costs across all batches"""
        
        batches = self.list_local_batches()
        
        total_transactions = 0
        total_estimated_cost = 0.0
        total_estimated_savings = 0.0
        model_breakdown = {}
        
        for batch in batches:
            if batch.get('total_requests', 0) > 0:
                # Extract model from batch type or assume gpt-4.1-mini
                model = "gpt-4.1-mini"  # Default
                if "classification" in batch.get('batch_type', '').lower():
                    model = "o4-mini"
                    
                cost_est = self.estimate_batch_cost(
                    batch['total_requests'], 
                    model
                )
                
                total_transactions += batch['total_requests']
                total_estimated_cost += cost_est['batch_cost']['total']
                total_estimated_savings += cost_est['savings']['amount']
                
                if model not in model_breakdown:
                    model_breakdown[model] = {
                        "transactions": 0,
                        "batches": 0,
                        "cost": 0.0,
                        "savings": 0.0
                    }
                    
                model_breakdown[model]["transactions"] += batch['total_requests']
                model_breakdown[model]["batches"] += 1
                model_breakdown[model]["cost"] += cost_est['batch_cost']['total']
                model_breakdown[model]["savings"] += cost_est['savings']['amount']
                
        return {
            "total_batches": len(batches),
            "total_transactions": total_transactions,
            "total_estimated_cost": total_estimated_cost,
            "total_estimated_savings": total_estimated_savings,
            "model_breakdown": model_breakdown
        }
        
    def cleanup_old_status_files(self, days_old: int = 30) -> int:
        """Remove old status files"""
        
        cutoff_date = datetime.now() - timedelta(days=days_old)
        removed_count = 0
        
        for status_file in glob.glob(str(self.status_dir / "batch_*.json")):
            file_path = Path(status_file)
            
            # Check file modification time
            mod_time = datetime.fromtimestamp(file_path.stat().st_mtime)
            
            if mod_time < cutoff_date:
                try:
                    file_path.unlink()
                    removed_count += 1
                    print(f"Removed old status file: {file_path.name}")
                except Exception as e:
                    print(f"Error removing {file_path}: {e}")
                    
        return removed_count
        
    def get_active_batches(self) -> List[Dict]:
        """Get currently running batches"""
        
        local_batches = self.list_local_batches()
        active_batches = []
        
        for batch in local_batches:
            if batch.get('openai_batch_id'):
                openai_status = self.get_openai_batch_status(batch['openai_batch_id'])
                
                if openai_status.get('status') in ['validating', 'in_progress', 'finalizing']:
                    batch['current_openai_status'] = openai_status
                    active_batches.append(batch)
                    
        return active_batches
        
    def sync_batch_statuses(self) -> Dict:
        """Sync local batch statuses with OpenAI"""
        
        local_batches = self.list_local_batches()
        updated_count = 0
        error_count = 0
        
        for batch in local_batches:
            if batch.get('openai_batch_id') and batch.get('status') not in ['completed', 'failed', 'expired']:
                openai_status = self.get_openai_batch_status(batch['openai_batch_id'])
                
                if 'error' not in openai_status:
                    # Update local status
                    batch['status'] = openai_status['status']
                    if openai_status.get('completed_at'):
                        batch['completed_at'] = openai_status['completed_at']
                        
                    # Save updated status
                    try:
                        with open(batch['status_file'], 'w') as f:
                            json.dump({k: v for k, v in batch.items() if k != 'status_file'}, f, indent=2)
                        updated_count += 1
                    except Exception as e:
                        print(f"Error updating status file: {e}")
                        error_count += 1
                else:
                    error_count += 1
                    
        return {
            "updated": updated_count,
            "errors": error_count,
            "total_checked": len([b for b in local_batches if b.get('openai_batch_id')])
        }


class Command(BaseCommand):
    help = "Monitor and manage OpenAI batch jobs"
    
    def add_arguments(self, parser):
        parser.add_argument(
            "--list",
            action="store_true",
            help="List all batch jobs"
        )
        parser.add_argument(
            "--status",
            type=str,
            help="Check status of specific batch ID"
        )
        parser.add_argument(
            "--costs",
            action="store_true",
            help="Show cost analysis"
        )
        parser.add_argument(
            "--active",
            action="store_true", 
            help="Show only active batches"
        )
        parser.add_argument(
            "--sync",
            action="store_true",
            help="Sync local status with OpenAI"
        )
        parser.add_argument(
            "--cleanup",
            type=int,
            default=30,
            help="Clean up status files older than N days"
        )
        parser.add_argument(
            "--estimate-cost",
            nargs=3,
            metavar=('TRANSACTIONS', 'MODEL', 'INPUT_TOKENS'),
            help="Estimate cost for batch (transactions model input_tokens)"
        )
        
    def handle(self, *args, **options):
        monitor = BatchMonitor()
        
        if options.get("list"):
            self.list_batches(monitor)
            
        elif options.get("status"):
            self.show_batch_status(monitor, options["status"])
            
        elif options.get("costs"):
            self.show_cost_analysis(monitor)
            
        elif options.get("active"):
            self.show_active_batches(monitor)
            
        elif options.get("sync"):
            self.sync_statuses(monitor)
            
        elif options.get("cleanup"):
            self.cleanup_files(monitor, options["cleanup"])
            
        elif options.get("estimate_cost"):
            self.estimate_cost(monitor, options["estimate_cost"])
            
        else:
            self.stdout.write("Use --help to see available commands")
            
    def list_batches(self, monitor: BatchMonitor):
        """List all batch jobs"""
        batches = monitor.list_local_batches()
        
        if not batches:
            self.stdout.write("No batch jobs found")
            return
            
        self.stdout.write(f"\n{'Batch Type':<25} {'Status':<12} {'Transactions':<12} {'Created':<20} {'OpenAI ID':<20}")
        self.stdout.write("-" * 95)
        
        for batch in batches:
            created_at = batch.get('created_at', 'Unknown')
            if created_at != 'Unknown':
                try:
                    dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    created_at = dt.strftime('%Y-%m-%d %H:%M')
                except:
                    pass
                    
            self.stdout.write(
                f"{batch.get('batch_type', 'Unknown'):<25} "
                f"{batch.get('status', 'Unknown'):<12} "
                f"{batch.get('total_requests', 0):<12} "
                f"{created_at:<20} "
                f"{batch.get('openai_batch_id', 'None'):<20}"
            )
            
    def show_batch_status(self, monitor: BatchMonitor, batch_id: str):
        """Show detailed status for specific batch"""
        
        # First check local status
        local_batches = monitor.list_local_batches()
        local_batch = next((b for b in local_batches if b.get('openai_batch_id') == batch_id), None)
        
        if local_batch:
            self.stdout.write(f"\nLocal Batch Status:")
            self.stdout.write(f"Type: {local_batch.get('batch_type')}")
            self.stdout.write(f"Status: {local_batch.get('status')}")
            self.stdout.write(f"Transactions: {local_batch.get('total_requests')}")
            self.stdout.write(f"Successful: {local_batch.get('successful_requests', 0)}")
            self.stdout.write(f"Failed: {local_batch.get('failed_requests', 0)}")
            
        # Get OpenAI status
        openai_status = monitor.get_openai_batch_status(batch_id)
        
        self.stdout.write(f"\nOpenAI Status:")
        if 'error' in openai_status:
            self.stdout.write(f"Error: {openai_status['error']}")
        else:
            self.stdout.write(f"Status: {openai_status['status']}")
            self.stdout.write(f"Created: {openai_status.get('created_at')}")
            self.stdout.write(f"Completed: {openai_status.get('completed_at', 'Not completed')}")
            
            if openai_status.get('request_counts'):
                counts = openai_status['request_counts']
                self.stdout.write(f"Request Counts: {counts}")
                
    def show_cost_analysis(self, monitor: BatchMonitor):
        """Show cost analysis across all batches"""
        
        analysis = monitor.get_cost_analysis()
        
        self.stdout.write(f"\n=== Cost Analysis ===")
        self.stdout.write(f"Total Batches: {analysis['total_batches']}")
        self.stdout.write(f"Total Transactions: {analysis['total_transactions']:,}")
        self.stdout.write(f"Estimated Total Cost: ${analysis['total_estimated_cost']:.4f}")
        self.stdout.write(f"Estimated Total Savings: ${analysis['total_estimated_savings']:.4f}")
        
        if analysis['total_estimated_cost'] > 0:
            realtime_cost = analysis['total_estimated_cost'] + analysis['total_estimated_savings']
            savings_percent = (analysis['total_estimated_savings'] / realtime_cost) * 100
            self.stdout.write(f"Savings Percentage: {savings_percent:.1f}%")
            
        self.stdout.write(f"\n=== By Model ===")
        for model, data in analysis['model_breakdown'].items():
            self.stdout.write(f"\n{model}:")
            self.stdout.write(f"  Batches: {data['batches']}")
            self.stdout.write(f"  Transactions: {data['transactions']:,}")
            self.stdout.write(f"  Cost: ${data['cost']:.4f}")
            self.stdout.write(f"  Savings: ${data['savings']:.4f}")
            
    def show_active_batches(self, monitor: BatchMonitor):
        """Show currently active batches"""
        
        active_batches = monitor.get_active_batches()
        
        if not active_batches:
            self.stdout.write("No active batches found")
            return
            
        self.stdout.write(f"\n=== Active Batches ({len(active_batches)}) ===")
        
        for batch in active_batches:
            openai_status = batch.get('current_openai_status', {})
            
            self.stdout.write(f"\nBatch: {batch.get('batch_type')}")
            self.stdout.write(f"OpenAI ID: {batch.get('openai_batch_id')}")
            self.stdout.write(f"Status: {openai_status.get('status')}")
            self.stdout.write(f"Transactions: {batch.get('total_requests')}")
            
            if openai_status.get('request_counts'):
                counts = openai_status['request_counts']
                completed = counts.get('completed', 0)
                total = counts.get('total', batch.get('total_requests', 0))
                if total > 0:
                    progress = (completed / total) * 100
                    self.stdout.write(f"Progress: {completed}/{total} ({progress:.1f}%)")
                    
    def sync_statuses(self, monitor: BatchMonitor):
        """Sync local statuses with OpenAI"""
        
        self.stdout.write("Syncing batch statuses with OpenAI...")
        
        result = monitor.sync_batch_statuses()
        
        self.stdout.write(f"Updated: {result['updated']}")
        self.stdout.write(f"Errors: {result['errors']}")
        self.stdout.write(f"Total Checked: {result['total_checked']}")
        
    def cleanup_files(self, monitor: BatchMonitor, days_old: int):
        """Clean up old status files"""
        
        self.stdout.write(f"Cleaning up status files older than {days_old} days...")
        
        removed_count = monitor.cleanup_old_status_files(days_old)
        
        self.stdout.write(f"Removed {removed_count} old status files")
        
    def estimate_cost(self, monitor: BatchMonitor, params: List[str]):
        """Estimate batch cost"""
        
        try:
            transactions = int(params[0])
            model = params[1]
            input_tokens = int(params[2])
            
            estimate = monitor.estimate_batch_cost(transactions, model, input_tokens)
            
            if 'error' in estimate:
                self.stderr.write(f"Error: {estimate['error']}")
                return
                
            self.stdout.write(f"\n=== Cost Estimate ===")
            self.stdout.write(f"Transactions: {transactions:,}")
            self.stdout.write(f"Model: {model}")
            self.stdout.write(f"Estimated Input Tokens: {input_tokens}")
            self.stdout.write(f"Estimated Output Tokens: {estimate['estimated_tokens']['output']}")
            
            self.stdout.write(f"\nBatch Cost: ${estimate['batch_cost']['total']:.4f}")
            self.stdout.write(f"Real-time Cost: ${estimate['realtime_cost']['total']:.4f}")
            self.stdout.write(f"Savings: ${estimate['savings']['amount']:.4f} ({estimate['savings']['percent']:.1f}%)")
            
        except (ValueError, IndexError) as e:
            self.stderr.write(f"Invalid parameters: {e}")
            self.stderr.write("Usage: --estimate-cost TRANSACTIONS MODEL INPUT_TOKENS")