"""
Async OpenAI Batch API Processor for LedgerFlow

This command implements a multi-stage async batch processing system for 
transaction categorization using OpenAI's Batch API (50% cost savings).

Workflow:
1. Stage 1: Payee Lookup Batch (with function calls)
2. Stage 2: Tool Execution & Re-submission  
3. Stage 3: Classification Batch
4. Update all transactions

Usage:
python manage.py async_batch_processor --agent "Payee Lookup Agent" --batch-size 100
python manage.py async_batch_processor --workflow full --batch-size 50
"""

import json
import time
import tempfile
import os
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.db import transaction
from django.conf import settings

from openai import OpenAI
from profiles.models import Transaction, Agent
from profiles.utils.utils import get_update_fields_from_response

logger = logging.getLogger(__name__)


class BatchStatus:
    """Track batch job status and metrics"""
    
    def __init__(self, batch_type: str, transaction_ids: List[int]):
        self.batch_type = batch_type
        self.transaction_ids = transaction_ids
        self.batch_id = None
        self.openai_batch_id = None
        self.status = "preparing"
        self.created_at = datetime.now(timezone.utc)
        self.completed_at = None
        self.total_requests = len(transaction_ids)
        self.successful_requests = 0
        self.failed_requests = 0
        self.cost_estimate = 0.0
        self.actual_cost = 0.0
        self.errors = []
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "batch_type": self.batch_type,
            "batch_id": self.batch_id,
            "openai_batch_id": self.openai_batch_id,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "cost_estimate": self.cost_estimate,
            "actual_cost": self.actual_cost,
            "transaction_ids": self.transaction_ids,
            "errors": self.errors
        }


class AsyncBatchProcessor:
    """OpenAI Batch API processor with multi-stage workflow support"""
    
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.status_dir = Path(settings.BASE_DIR) / "batch_status"
        self.status_dir.mkdir(exist_ok=True)
        
        # Tool definitions for function calling
        self.tool_definitions = self._load_tool_definitions()
        
    def _load_tool_definitions(self) -> List[Dict]:
        """Load available tool definitions for function calling"""
        # Import search tools dynamically
        try:
            from tools.search_tool.searxng_search import searxng_search
            from tools.vendor_lookup.brave_search import brave_search
            
            return [
                {
                    "type": "function",
                    "function": {
                        "name": "searxng_search",
                        "description": "Search for merchant/payee information using SearXNG",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "query": {
                                    "type": "string",
                                    "description": "The search query to look up merchant/payee information"
                                }
                            },
                            "required": ["query"]
                        }
                    }
                },
                {
                    "type": "function", 
                    "function": {
                        "name": "brave_search",
                        "description": "Search for merchant/payee information using Brave Search",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "query": {
                                    "type": "string",
                                    "description": "The search query to look up merchant/payee information"
                                }
                            },
                            "required": ["query"]
                        }
                    }
                }
            ]
        except ImportError:
            logger.warning("Search tools not available")
            return []
            
    def build_jsonl_batch(self, transactions: List[Transaction], agent: Agent, 
                         additional_context: Dict = None) -> Tuple[str, BatchStatus]:
        """Build JSONL batch file for OpenAI Batch API"""
        
        batch_status = BatchStatus(
            batch_type=f"{agent.name}_batch",
            transaction_ids=[tx.id for tx in transactions]
        )
        
        # Create temporary JSONL file
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False)
        
        try:
            for tx in transactions:
                # Build context for agent prompt
                context = {
                    "transaction": tx,
                    "business_profile": getattr(tx, "client", None),
                    "payee_reasoning": getattr(tx, "payee_reasoning", None),
                    **(additional_context or {})
                }
                
                # Render agent prompt template
                from jinja2 import Template
                template = Template(agent.prompt)
                rendered_prompt = template.render(**context)
                
                # Build request body
                request_body = {
                    "model": agent.llm_model,
                    "messages": [
                        {"role": "system", "content": rendered_prompt}
                    ],
                    "response_format": {"type": "json_object"}
                }
                
                # Add tools if agent supports them (payee lookup)
                if "payee" in agent.name.lower() and self.tool_definitions:
                    request_body["tools"] = self.tool_definitions
                    request_body["tool_choice"] = "auto"
                    
                # Create JSONL request
                jsonl_request = {
                    "custom_id": f"tx_{tx.id}",
                    "method": "POST",
                    "url": "/v1/chat/completions",
                    "body": request_body
                }
                
                # Write to JSONL file
                temp_file.write(json.dumps(jsonl_request) + '\n')
                
            temp_file.flush()
            return temp_file.name, batch_status
            
        except Exception as e:
            temp_file.close()
            os.unlink(temp_file.name)
            raise e
        finally:
            temp_file.close()
            
    def submit_batch(self, jsonl_file_path: str, batch_status: BatchStatus) -> str:
        """Submit batch to OpenAI and return batch ID"""
        
        try:
            # Upload JSONL file
            with open(jsonl_file_path, 'rb') as f:
                file_response = self.client.files.create(
                    file=f,
                    purpose="batch"
                )
                
            # Create batch job
            batch_response = self.client.batches.create(
                input_file_id=file_response.id,
                endpoint="/v1/chat/completions",
                completion_window="24h",
                metadata={
                    "description": f"LedgerFlow {batch_status.batch_type}",
                    "transaction_count": str(batch_status.total_requests)
                }
            )
            
            batch_status.openai_batch_id = batch_response.id
            batch_status.status = "submitted"
            
            # Save status
            self._save_batch_status(batch_status)
            
            logger.info(f"Submitted batch {batch_response.id} with {batch_status.total_requests} requests")
            
            return batch_response.id
            
        finally:
            # Clean up temp file
            if os.path.exists(jsonl_file_path):
                os.unlink(jsonl_file_path)
                
    def poll_batch_status(self, batch_id: str, max_wait_seconds: int = 3600) -> Dict:
        """Poll batch status until completion"""
        
        start_time = time.time()
        
        while time.time() - start_time < max_wait_seconds:
            batch = self.client.batches.retrieve(batch_id)
            
            logger.info(f"Batch {batch_id} status: {batch.status}")
            
            if batch.status == "completed":
                return {
                    "status": "completed",
                    "output_file_id": batch.output_file_id,
                    "request_counts": batch.request_counts._asdict() if batch.request_counts else {}
                }
            elif batch.status == "failed":
                return {
                    "status": "failed",
                    "errors": getattr(batch, 'errors', [])
                }
            elif batch.status in ["expired", "cancelled"]:
                return {
                    "status": batch.status
                }
                
            # Wait before next poll
            time.sleep(30)  # Poll every 30 seconds
            
        return {"status": "timeout"}
        
    def download_batch_results(self, output_file_id: str) -> List[Dict]:
        """Download and parse batch results"""
        
        file_response = self.client.files.content(output_file_id)
        content = file_response.content.decode('utf-8')
        
        results = []
        for line in content.strip().split('\n'):
            if line.strip():
                results.append(json.loads(line))
                
        return results
        
    def execute_function_calls(self, batch_results: List[Dict]) -> Dict[str, str]:
        """Execute function calls from batch results and return search results"""
        
        search_results = {}
        
        for result in batch_results:
            custom_id = result["custom_id"]
            response = result.get("response", {})
            
            if "choices" in response and response["choices"]:
                message = response["choices"][0].get("message", {})
                
                if "tool_calls" in message:
                    for tool_call in message["tool_calls"]:
                        function_name = tool_call["function"]["name"]
                        arguments = json.loads(tool_call["function"]["arguments"])
                        
                        # Execute the function call
                        try:
                            if function_name == "searxng_search":
                                from tools.search_tool.searxng_search import searxng_search
                                result = searxng_search(arguments["query"])
                            elif function_name == "brave_search":
                                from tools.vendor_lookup.brave_search import brave_search
                                result = brave_search(arguments["query"])
                            else:
                                result = f"Unknown function: {function_name}"
                                
                            search_results[custom_id] = result
                            
                        except Exception as e:
                            logger.error(f"Error executing {function_name}: {e}")
                            search_results[custom_id] = f"Error: {str(e)}"
                            
        return search_results
        
    def process_batch_results(self, batch_results: List[Dict], agent: Agent) -> Dict[str, Any]:
        """Process batch results and extract structured data"""
        
        processed_results = {}
        
        for result in batch_results:
            custom_id = result["custom_id"]
            transaction_id = int(custom_id.replace("tx_", ""))
            
            try:
                response = result.get("response", {})
                if "choices" in response and response["choices"]:
                    content = response["choices"][0]["message"]["content"]
                    
                    # Parse JSON response
                    data = json.loads(content)
                    
                    processed_results[transaction_id] = {
                        "success": True,
                        "data": data,
                        "raw_response": content
                    }
                    
                else:
                    processed_results[transaction_id] = {
                        "success": False,
                        "error": "No response choices",
                        "raw_response": str(result)
                    }
                    
            except Exception as e:
                processed_results[transaction_id] = {
                    "success": False,
                    "error": str(e),
                    "raw_response": str(result)
                }
                
        return processed_results
        
    def update_transactions(self, processed_results: Dict[str, Any], agent: Agent):
        """Update transactions with processed results"""
        
        successful_updates = 0
        failed_updates = 0
        
        for transaction_id, result in processed_results.items():
            try:
                if result["success"]:
                    with transaction.atomic():
                        tx = Transaction.objects.get(id=transaction_id)
                        
                        # Determine agent type for field mapping
                        agent_type = (
                            "payee" if "payee" in agent.name.lower()
                            else "classification"
                        )
                        
                        # Get update fields
                        update_fields = get_update_fields_from_response(
                            agent, result["data"], agent_type
                        )
                        
                        # Update transaction
                        Transaction.objects.filter(id=transaction_id).update(**update_fields)
                        successful_updates += 1
                        
                else:
                    logger.error(f"Failed to process transaction {transaction_id}: {result['error']}")
                    failed_updates += 1
                    
            except Exception as e:
                logger.error(f"Error updating transaction {transaction_id}: {e}")
                failed_updates += 1
                
        logger.info(f"Updated {successful_updates} transactions, {failed_updates} failed")
        
        return successful_updates, failed_updates
        
    def _save_batch_status(self, batch_status: BatchStatus):
        """Save batch status to file"""
        status_file = self.status_dir / f"batch_{batch_status.batch_type}_{batch_status.created_at.strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(status_file, 'w') as f:
            json.dump(batch_status.to_dict(), f, indent=2)
            
    def run_payee_lookup_workflow(self, transactions: List[Transaction]) -> Dict[str, Any]:
        """Run complete payee lookup workflow with function calls"""
        
        try:
            payee_agent = Agent.objects.get(name="Payee Lookup Agent")
        except Agent.DoesNotExist:
            raise ValueError("Payee Lookup Agent not found")
            
        logger.info(f"Starting payee lookup workflow for {len(transactions)} transactions")
        
        # Stage 1: Initial batch submission
        jsonl_file, batch_status = self.build_jsonl_batch(transactions, payee_agent)
        batch_id = self.submit_batch(jsonl_file, batch_status)
        
        # Stage 2: Poll until completion
        result = self.poll_batch_status(batch_id)
        
        if result["status"] != "completed":
            raise RuntimeError(f"Batch failed with status: {result['status']}")
            
        # Stage 3: Download results
        batch_results = self.download_batch_results(result["output_file_id"])
        
        # Stage 4: Execute function calls if present
        search_results = self.execute_function_calls(batch_results)
        
        # Stage 5: Re-submit with search results if needed
        if search_results:
            logger.info(f"Re-submitting batch with search results for {len(search_results)} transactions")
            
            # Filter transactions that need re-submission
            resubmit_transactions = [tx for tx in transactions if f"tx_{tx.id}" in search_results]
            
            # Build context with search results
            additional_context = {}
            for tx in resubmit_transactions:
                custom_id = f"tx_{tx.id}"
                if custom_id in search_results:
                    additional_context[f"search_results_{tx.id}"] = search_results[custom_id]
                    
            # Re-submit batch
            jsonl_file, batch_status_2 = self.build_jsonl_batch(
                resubmit_transactions, payee_agent, additional_context
            )
            batch_id_2 = self.submit_batch(jsonl_file, batch_status_2)
            
            # Poll second batch
            result_2 = self.poll_batch_status(batch_id_2)
            if result_2["status"] == "completed":
                batch_results = self.download_batch_results(result_2["output_file_id"])
            else:
                logger.error(f"Second batch failed: {result_2}")
                
        # Stage 6: Process results and update transactions
        processed_results = self.process_batch_results(batch_results, payee_agent)
        successful_updates, failed_updates = self.update_transactions(processed_results, payee_agent)
        
        return {
            "status": "completed",
            "total_transactions": len(transactions),
            "successful_updates": successful_updates,
            "failed_updates": failed_updates,
            "batch_ids": [batch_id] + ([batch_id_2] if search_results else [])
        }
        
    def run_classification_workflow(self, transactions: List[Transaction]) -> Dict[str, Any]:
        """Run classification workflow (requires payee data)"""
        
        try:
            classification_agent = Agent.objects.get(name="Classification Agent")
        except Agent.DoesNotExist:
            raise ValueError("Classification Agent not found")
            
        logger.info(f"Starting classification workflow for {len(transactions)} transactions")
        
        # Build batch with classification context
        jsonl_file, batch_status = self.build_jsonl_batch(transactions, classification_agent)
        batch_id = self.submit_batch(jsonl_file, batch_status)
        
        # Poll until completion
        result = self.poll_batch_status(batch_id)
        
        if result["status"] != "completed":
            raise RuntimeError(f"Classification batch failed: {result['status']}")
            
        # Download and process results
        batch_results = self.download_batch_results(result["output_file_id"])
        processed_results = self.process_batch_results(batch_results, classification_agent)
        successful_updates, failed_updates = self.update_transactions(processed_results, classification_agent)
        
        return {
            "status": "completed", 
            "total_transactions": len(transactions),
            "successful_updates": successful_updates,
            "failed_updates": failed_updates,
            "batch_id": batch_id
        }


class Command(BaseCommand):
    help = "Process transactions using OpenAI Batch API (50% cost savings)"
    
    def add_arguments(self, parser):
        parser.add_argument(
            "--workflow", 
            type=str,
            choices=["full", "payee", "classification"],
            default="full",
            help="Workflow to run"
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=100,
            help="Number of transactions per batch"
        )
        parser.add_argument(
            "--filter",
            type=str,
            help='Filter transactions (e.g., "client_id=123")'
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be processed without making API calls"
        )
        
    def handle(self, *args, **options):
        workflow = options["workflow"]
        batch_size = options["batch_size"] 
        filter_str = options["filter"]
        dry_run = options["dry_run"]
        
        processor = AsyncBatchProcessor()
        
        # Build query
        query = Q()
        if filter_str:
            field, value = filter_str.split("=")
            query = Q(**{field: value})
            
        # Get transactions
        if workflow == "payee":
            # Unprocessed payee lookups
            query &= Q(payee_extraction_method="unprocessed")
        elif workflow == "classification":  
            # Unclassified with payee data
            query &= Q(classification_method="unclassified") & ~Q(payee__isnull=True)
        elif workflow == "full":
            # Unprocessed transactions
            query &= Q(payee_extraction_method="unprocessed")
            
        transactions = list(Transaction.objects.filter(query)[:batch_size])
        
        if not transactions:
            self.stdout.write("No transactions to process")
            return
            
        if dry_run:
            self.stdout.write(f"Would process {len(transactions)} transactions")
            return
            
        try:
            if workflow == "payee":
                result = processor.run_payee_lookup_workflow(transactions)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Payee lookup completed: {result['successful_updates']}/{result['total_transactions']} successful"
                    )
                )
                
            elif workflow == "classification":
                result = processor.run_classification_workflow(transactions)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Classification completed: {result['successful_updates']}/{result['total_transactions']} successful"
                    )
                )
                
            elif workflow == "full":
                # Run payee lookup first
                payee_result = processor.run_payee_lookup_workflow(transactions)
                self.stdout.write(f"Payee lookup: {payee_result['successful_updates']} successful")
                
                # Then run classification on successful transactions
                successful_transactions = Transaction.objects.filter(
                    id__in=[tx.id for tx in transactions],
                    payee_extraction_method__in=["ai_processed", "manual"]
                )
                
                if successful_transactions.exists():
                    classification_result = processor.run_classification_workflow(list(successful_transactions))
                    self.stdout.write(f"Classification: {classification_result['successful_updates']} successful")
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Full workflow completed: {len(transactions)} transactions processed"
                        )
                    )
                else:
                    self.stdout.write("No transactions available for classification")
                    
        except Exception as e:
            self.stderr.write(
                self.style.ERROR(f"Workflow failed: {str(e)}")
            )
            raise