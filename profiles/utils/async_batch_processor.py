"""
Async OpenAI Batch API utilities for LedgerFlow

This module provides async batch processing capabilities that integrate with
the existing ProcessingTask monitoring system in Django admin.
"""

import json
import time
import tempfile
import os
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

from django.db import transaction as db_transaction
from django.conf import settings
from django.contrib import messages

from openai import OpenAI
from profiles.models import Transaction, Agent, ProcessingTask, BusinessProfile
from profiles.utils.utils import get_update_fields_from_response

logger = logging.getLogger(__name__)


class AsyncBatchProcessor:
    """OpenAI Batch API processor integrated with ProcessingTask monitoring"""
    
    def __init__(self):
        # Lazy initialization - client will be created when first needed
        self._client = None
        self._tool_definitions = None
        
    @property
    def client(self):
        """Lazy initialization of OpenAI client"""
        if self._client is None:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY environment variable not set")
            
            # Clean the API key - remove any whitespace/newlines that might have been introduced
            api_key = api_key.strip().replace('\n', '').replace('\r', '').replace(' ', '')
            
            self._client = OpenAI(api_key=api_key)
        return self._client
        
    @property
    def tool_definitions(self):
        """Lazy initialization of tool definitions"""
        if self._tool_definitions is None:
            self._tool_definitions = self._load_tool_definitions()
        return self._tool_definitions
        
    def _load_tool_definitions(self) -> List[Dict]:
        """Load available tool definitions for function calling"""
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
            
    def build_full_workflow_batch(self, transactions: List[Transaction]) -> str:
        """Build JSONL batch for full workflow (payee + classification) using configured agents"""
        
        from profiles.models import Agent
        
        # Get the configured agents from database
        payee_agent = Agent.objects.get(name="Payee Lookup Agent")
        classification_agent = Agent.objects.get(name="Classification Agent")
        
        # Create temporary JSONL file
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False)
        
        try:
            for tx in transactions:
                # Step 1: Payee extraction with tools
                from profiles.admin import build_allowed_categories
                
                payee_context = {
                    "transaction": tx,
                    "business_profile": getattr(tx, "client", None),
                }
                
                # Render payee agent prompt
                from jinja2 import Template
                payee_template = Template(payee_agent.prompt)
                payee_prompt = payee_template.render(**payee_context)
                
                # Build payee request
                payee_request = {
                    "model": payee_agent.llm.model,
                    "messages": [
                        {"role": "system", "content": payee_prompt}
                    ],
                    "response_format": {"type": "json_object"}
                }
                
                # Add tools for payee lookup
                if self.tool_definitions:
                    payee_request["tools"] = self.tool_definitions
                    payee_request["tool_choice"] = "auto"
                
                # Create first JSONL request for payee lookup
                payee_jsonl = {
                    "custom_id": f"payee_tx_{tx.id}",
                    "method": "POST", 
                    "url": "/v1/chat/completions",
                    "body": payee_request
                }
                
                temp_file.write(json.dumps(payee_jsonl) + '\n')
                
                # Step 2: Classification request (will be processed after payee)
                classification_context = {
                    "transaction": tx,
                    "business_profile": getattr(tx, "client", None),
                    "payee_reasoning": "{{PAYEE_RESULT}}", # Will be replaced after payee processing
                    "allowed_categories": build_allowed_categories(tx),
                }
                
                classification_template = Template(classification_agent.prompt) 
                classification_prompt = classification_template.render(**classification_context)
                
                classification_request = {
                    "model": classification_agent.llm.model,
                    "messages": [
                        {"role": "system", "content": classification_prompt}
                    ],
                    "response_format": {"type": "json_object"}
                }
                
                # Create second JSONL request for classification
                classification_jsonl = {
                    "custom_id": f"classification_tx_{tx.id}",
                    "method": "POST",
                    "url": "/v1/chat/completions", 
                    "body": classification_request
                }
                
                temp_file.write(json.dumps(classification_jsonl) + '\n')
                
            temp_file.flush()
            return temp_file.name
            
        except Exception as e:
            temp_file.close()
            os.unlink(temp_file.name)
            raise e
        finally:
            temp_file.close()
    
    def build_jsonl_batch(self, transactions: List[Transaction], agent: Agent, 
                         additional_context: Dict = None) -> str:
        """Build JSONL batch file for OpenAI Batch API"""
        
        # Create temporary JSONL file
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False)
        
        try:
            for tx in transactions:
                # Build context for agent prompt
                from profiles.admin import build_allowed_categories
                
                is_classification = (
                    "classification" in (agent.purpose or "").lower()
                    or "classification" in (agent.name or "").lower()
                )
                
                allowed_categories = ""
                if is_classification:
                    allowed_categories = build_allowed_categories(tx)
                
                context = {
                    "transaction": tx,
                    "business_profile": getattr(tx, "client", None),
                    "payee_reasoning": getattr(tx, "payee_reasoning", None),
                    "allowed_categories": allowed_categories,
                    **(additional_context or {})
                }
                
                # Render agent prompt template
                from jinja2 import Template
                template = Template(agent.prompt)
                rendered_prompt = template.render(**context)
                
                # Use the same model resolution as the existing call_agent function
                if not agent.llm or not agent.llm.model:
                    raise ValueError(f"Agent '{agent.name}' does not have an LLM model configured. Please configure it in Django admin.")
                
                # Build request body using existing agent configuration
                request_body = {
                    "model": agent.llm.model,
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
            return temp_file.name
            
        except Exception as e:
            temp_file.close()
            os.unlink(temp_file.name)
            raise e
        finally:
            temp_file.close()
            
    def submit_batch(self, jsonl_file_path: str, description: str = None) -> str:
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
                    "description": description or "LedgerFlow Batch Processing",
                }
            )
            
            logger.info(f"Submitted batch {batch_response.id}")
            
            return batch_response.id
            
        finally:
            # Clean up temp file
            if os.path.exists(jsonl_file_path):
                os.unlink(jsonl_file_path)
                
    def get_batch_status(self, batch_id: str) -> Dict:
        """Get current batch status from OpenAI"""
        
        try:
            batch = self.client.batches.retrieve(batch_id)
            
            # Handle request_counts safely
            request_counts = {}
            if batch.request_counts:
                try:
                    request_counts = {
                        "total": getattr(batch.request_counts, 'total', 0),
                        "completed": getattr(batch.request_counts, 'completed', 0),
                        "failed": getattr(batch.request_counts, 'failed', 0)
                    }
                except Exception as e:
                    request_counts = {"error": f"Could not parse request_counts: {e}"}
            
            return {
                "id": batch.id,
                "status": batch.status,
                "created_at": batch.created_at,
                "completed_at": batch.completed_at,
                "request_counts": request_counts,
                "metadata": batch.metadata or {},
                "output_file_id": batch.output_file_id,
                "error_file_id": batch.error_file_id
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "status": "error"
            }
            
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
        
    def process_batch_results_with_tools(self, batch_results: List[Dict], agent: Agent) -> Dict[str, Any]:
        """Process batch results that may contain tool calls, execute them, and get final responses"""
        
        processed_results = {}
        
        for result in batch_results:
            custom_id = result["custom_id"]
            transaction_id = int(custom_id.replace("tx_", ""))
            
            try:
                # Handle the nested response structure from OpenAI batch API
                response_wrapper = result.get("response", {})
                if "body" in response_wrapper:
                    response = response_wrapper["body"]
                else:
                    response = response_wrapper
                
                if not ("choices" in response and response["choices"]):
                    processed_results[transaction_id] = {
                        "success": False,
                        "error": "No response choices",
                        "raw_response": str(result)
                    }
                    continue
                
                message = response["choices"][0]["message"]
                content = message.get("content")
                
                # Case 1: Direct content response (no tool calls)
                if content:
                    try:
                        data = json.loads(content)
                        processed_results[transaction_id] = {
                            "success": True,
                            "data": data,
                            "raw_response": content
                        }
                        continue
                    except json.JSONDecodeError:
                        # Content exists but isn't JSON
                        processed_results[transaction_id] = {
                            "success": False,
                            "error": "Response content is not valid JSON",
                            "raw_response": content
                        }
                        continue
                
                # Case 2: Tool calls response - need to execute tools and continue conversation
                tool_calls = message.get("tool_calls")
                if tool_calls:
                    try:
                        # Execute tool calls
                        tool_results = []
                        for tool_call in tool_calls:
                            function_name = tool_call["function"]["name"]
                            arguments = json.loads(tool_call["function"]["arguments"])
                            
                            # Execute the function
                            if function_name == "searxng_search":
                                from tools.search_tool.searxng_search import searxng_search
                                search_result = searxng_search(**arguments)
                            elif function_name == "brave_search":
                                from tools.vendor_lookup.brave_search import brave_search
                                search_result = brave_search(**arguments)
                            else:
                                search_result = f"Unknown function: {function_name}"
                            
                            tool_results.append({
                                "tool_call_id": tool_call["id"],
                                "role": "tool",
                                "content": str(search_result)
                            })
                        
                        # Build the follow-up request with tool results
                        # Reconstruct the original conversation
                        original_messages = self._reconstruct_original_messages(result, agent, transaction_id)
                        
                        # Add the assistant's tool call message
                        original_messages.append({
                            "role": "assistant",
                            "content": None,
                            "tool_calls": tool_calls
                        })
                        
                        # Add tool results
                        original_messages.extend(tool_results)
                        
                        # Make follow-up API call to get final response
                        follow_up_response = self.client.chat.completions.create(
                            model=agent.llm.model,
                            messages=original_messages,
                            response_format={"type": "json_object"},
                            tools=self.tool_definitions,
                            tool_choice="auto"
                        )
                        
                        # Process the final response
                        final_content = follow_up_response.choices[0].message.content
                        if final_content:
                            data = json.loads(final_content)
                            processed_results[transaction_id] = {
                                "success": True,
                                "data": data,
                                "raw_response": final_content,
                                "used_tools": True,
                                "tool_calls_count": len(tool_calls)
                            }
                        else:
                            processed_results[transaction_id] = {
                                "success": False,
                                "error": "Follow-up response has no content",
                                "raw_response": str(follow_up_response)
                            }
                            
                    except Exception as e:
                        processed_results[transaction_id] = {
                            "success": False,
                            "error": f"Error processing tool calls: {e}",
                            "raw_response": str(result)
                        }
                else:
                    # No content and no tool calls
                    processed_results[transaction_id] = {
                        "success": False,
                        "error": "No content or tool calls in response",
                        "raw_response": str(result)
                    }
                    
            except Exception as e:
                processed_results[transaction_id] = {
                    "success": False,
                    "error": str(e),
                    "raw_response": str(result)
                }
                
        return processed_results
    
    def process_full_workflow_batch_results(self, batch_results: List[Dict], first_agent: Agent, task: ProcessingTask) -> Dict[str, Dict]:
        """
        Process batch results for full workflow tasks
        
        This processes first agent results, then calls second agent sequentially
        using the existing call_agent function to maintain consistency with sequential processing
        """
        
        from profiles.models import Agent, Transaction
        from profiles.admin import call_agent
        from profiles.utils.utils import get_update_fields_from_response
        
        # Get second agent from task metadata
        second_agent_name = task.task_metadata.get("second_agent")
        if not second_agent_name:
            raise ValueError(f"Full workflow task {task.task_id} missing second_agent in metadata")
        
        second_agent = Agent.objects.get(name=second_agent_name)
        
        # First, process payee results using existing logic
        if any(result.get("response", {}).get("body", {}).get("choices", [{}])[0].get("message", {}).get("tool_calls") for result in batch_results):
            payee_results = self.process_batch_results_with_tools(batch_results, first_agent)
        else:
            payee_results = self.process_batch_results(batch_results, first_agent)
        
        processed_results = {}
        
        for transaction_id, payee_result in payee_results.items():
            try:
                # Get the transaction
                transaction = Transaction.objects.get(id=int(transaction_id))
                
                # Apply payee updates to the transaction
                if payee_result.get("success"):
                    payee_update_fields = get_update_fields_from_response(
                        first_agent, payee_result.get("data", {}), "payee"
                    )
                    
                    # Update transaction with payee info (but don't save yet)
                    for field, value in payee_update_fields.items():
                        setattr(transaction, field, value)
                
                # Now call classification agent with updated transaction
                classification_response = call_agent(second_agent.name, transaction)
                classification_update_fields = get_update_fields_from_response(
                    second_agent, classification_response, "classification"
                )
                
                # Merge both sets of updates
                combined_updates = {}
                if payee_result.get("success"):
                    combined_updates.update(payee_update_fields)
                combined_updates.update(classification_update_fields)
                
                processed_results[transaction_id] = {
                    "success": True,
                    "data": combined_updates,
                    "payee_success": payee_result.get("success", False),
                    "classification_success": True,
                    "raw_response": f"Payee: {payee_result.get('raw_response', '')} | Classification: {str(classification_response)}"
                }
                
            except Exception as e:
                processed_results[transaction_id] = {
                    "success": False,
                    "error": f"Full workflow error: {str(e)}",
                    "payee_success": payee_result.get("success", False),
                    "classification_success": False,
                    "raw_response": str(payee_result)
                }
        
        return processed_results
    
    def _reconstruct_original_messages(self, batch_result: Dict, agent: Agent, transaction_id: int) -> List[Dict]:
        """Reconstruct the original messages that were sent in the batch"""
        try:
            # Get the transaction to rebuild the original prompt
            from profiles.models import Transaction
            transaction = Transaction.objects.get(id=transaction_id)
            
            # Use the same prompt building logic as build_jsonl_batch
            template = agent.prompt
            
            # Get business context
            business_profile = transaction.business_profile if hasattr(transaction, 'business_profile') else None
            business_name = business_profile.company_name if business_profile else ""
            business_type = business_profile.business_type if business_profile else "None"
            
            # Build context variables
            context = {
                'transaction_description': transaction.description or '',
                'amount': transaction.amount or 0,
                'date': getattr(transaction, 'transaction_date', 'N/A'),
                'business_name': business_name,
                'business_type': business_type,
            }
            
            # Render the template (simple string replacement)
            rendered_prompt = template
            for key, value in context.items():
                rendered_prompt = rendered_prompt.replace(f'{{{key}}}', str(value))
            
            return [{"role": "system", "content": rendered_prompt}]
            
        except Exception as e:
            logger.error(f"Error reconstructing messages for transaction {transaction_id}: {e}")
            return [{"role": "system", "content": agent.prompt}]
    
    def process_batch_results(self, batch_results: List[Dict], agent: Agent) -> Dict[str, Any]:
        """Process batch results and extract structured data (legacy method for compatibility)"""
        return self.process_batch_results_with_tools(batch_results, agent)
        
    def update_transactions(self, processed_results: Dict[str, Any], agent: Agent, processing_task: ProcessingTask):
        """Update transactions with processed results"""
        
        successful_updates = 0
        failed_updates = 0
        errors = []
        
        for transaction_id, result in processed_results.items():
            try:
                if result["success"]:
                    with db_transaction.atomic():
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
                    error_msg = f"Transaction {transaction_id}: {result['error']}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    failed_updates += 1
                    
            except Exception as e:
                error_msg = f"Error updating transaction {transaction_id}: {e}"
                logger.error(error_msg)
                errors.append(error_msg)
                failed_updates += 1
                
        # Update processing task
        processing_task.processed_count = successful_updates
        processing_task.error_count = failed_updates
        if errors:
            processing_task.error_details = {"errors": errors}
        
        # CRITICAL FIX: Mark task as completed when batch finishes
        if failed_updates == 0:
            processing_task.status = "completed"
            logger.info(f"✅ Task {processing_task.task_id} marked as COMPLETED - all {successful_updates} transactions processed successfully")
        else:
            # Mark as failed if there were errors, but still save the successful updates
            processing_task.status = "failed" if successful_updates == 0 else "completed"
            logger.warning(f"⚠️ Task {processing_task.task_id} completed with {failed_updates} failures out of {successful_updates + failed_updates} total")
            
        processing_task.save()
        
        logger.info(f"Updated {successful_updates} transactions, {failed_updates} failed")
        
        return successful_updates, failed_updates
    
    def update_full_workflow_transactions(self, processed_results: Dict[str, Any], first_agent: Agent, processing_task: ProcessingTask):
        """Update transactions with full workflow processed results (payee + classification combined)"""
        
        successful_updates = 0
        failed_updates = 0
        errors = []
        payee_success_count = 0
        classification_success_count = 0
        
        logger.info(f"🔄 Processing full workflow results for task {processing_task.task_id}")
        
        for transaction_id, result in processed_results.items():
            try:
                if result["success"]:
                    with db_transaction.atomic():
                        # The full workflow result has combined payee + classification data
                        combined_data = result["data"]
                        
                        # Update transaction with combined data
                        updated_count = Transaction.objects.filter(id=transaction_id).update(**combined_data)
                        
                        if updated_count > 0:
                            successful_updates += 1
                            # Track individual step success
                            if result.get("payee_success", False):
                                payee_success_count += 1
                            if result.get("classification_success", False):
                                classification_success_count += 1
                                
                            logger.info(f"✅ Transaction {transaction_id}: Payee={'✅' if result.get('payee_success') else '❌'} Classification={'✅' if result.get('classification_success') else '❌'}")
                        else:
                            logger.error(f"❌ Transaction {transaction_id}: No rows updated (transaction may not exist)")
                            failed_updates += 1
                        
                else:
                    error_msg = f"Transaction {transaction_id}: {result['error']}"
                    logger.error(f"❌ {error_msg}")
                    errors.append(error_msg)
                    failed_updates += 1
                    
            except Exception as e:
                error_msg = f"Error updating transaction {transaction_id}: {e}"
                logger.error(f"❌ {error_msg}")
                errors.append(error_msg)
                failed_updates += 1
                
        # Update processing task with detailed statistics
        processing_task.processed_count = successful_updates
        processing_task.error_count = failed_updates
        if errors:
            processing_task.error_details = {"errors": errors}
        
        # Add full workflow specific metadata
        processing_task.task_metadata.update({
            "payee_success_count": payee_success_count,
            "classification_success_count": classification_success_count,
            "total_transactions": len(processed_results),
            "full_workflow_completed": True
        })
        
        # Mark as completed/failed
        if failed_updates == 0:
            processing_task.status = "completed"
            logger.info(f"✅ Full workflow task {processing_task.task_id} COMPLETED: {successful_updates} transactions processed successfully")
            logger.info(f"📊 Payee extraction: {payee_success_count}/{successful_updates} | Classification: {classification_success_count}/{successful_updates}")
        else:
            processing_task.status = "failed" if successful_updates == 0 else "completed"
            logger.warning(f"⚠️ Full workflow task {processing_task.task_id} completed with {failed_updates} failures out of {successful_updates + failed_updates} total")
            
        processing_task.save()
        
        logger.info(f"🏁 Full workflow complete: {successful_updates} successful, {failed_updates} failed")
        
        return successful_updates, failed_updates


def start_batch_processing(transactions: List[Transaction], agent_name: str, request, 
                         task_type: str = None) -> Optional[ProcessingTask]:
    """
    Start async batch processing and create ProcessingTask for monitoring
    
    Args:
        transactions: List of Transaction objects to process
        agent_name: Name of the agent to use
        request: Django request object for messages
        task_type: Override task type (default inferred from agent)
    
    Returns:
        ProcessingTask object for monitoring, or None if failed
    """
    
    if not transactions:
        messages.error(request, "No transactions selected")
        return None
        
    try:
        agent = Agent.objects.get(name=agent_name)
    except Agent.DoesNotExist:
        messages.error(request, f"Agent '{agent_name}' not found")
        return None
        
    # Group transactions by client (required for ProcessingTask model)
    client_groups = {}
    for tx in transactions:
        if tx.client_id not in client_groups:
            client_groups[tx.client_id] = []
        client_groups[tx.client_id].append(tx)
        
    processing_tasks = []
    
    # Create ProcessingTask for each client
    for client_id, client_transactions in client_groups.items():
        try:
            client = BusinessProfile.objects.get(client_id=client_id)
            
            # Determine task type
            if not task_type:
                if "payee" in agent.name.lower():
                    task_type_final = "batch_payee_lookup"
                elif "classification" in agent.name.lower():
                    task_type_final = "batch_classification" 
                else:
                    task_type_final = "batch_full_workflow"
            else:
                task_type_final = task_type
                
            # Create ProcessingTask
            task_metadata = {
                "agent_name": agent_name,
                "task_type": task_type_final,  # Store in metadata for UI
                "batch_processing": True,
                "openai_batch_api": True,
                "cost_savings": "50% vs real-time API"
            }
            
            # For full workflow tasks, populate first_agent and second_agent from configured agents
            if task_type_final == "batch_full_workflow":
                # Get agents from database configuration, not hard-coded names
                try:
                    payee_agent = Agent.objects.filter(
                        name__icontains="payee"
                    ).first()
                    classification_agent = Agent.objects.filter(
                        name__icontains="classification"
                    ).exclude(name__icontains="escalation").first()
                    
                    if payee_agent and classification_agent:
                        task_metadata.update({
                            "first_agent": payee_agent.name,
                            "second_agent": classification_agent.name
                        })
                    else:
                        raise ValueError("Could not find configured payee and classification agents")
                except Exception as e:
                    logger.error(f"Error finding configured agents: {e}")
                    # Fallback - but this should not happen if agents are properly configured
                    raise ValueError("Full workflow requires both payee and classification agents to be configured in the database")
            
            processing_task = ProcessingTask.objects.create(
                task_type=task_type_final,
                client=client,
                transaction_count=len(client_transactions),
                processed_count=0,
                error_count=0,
                status="processing",
                task_metadata=task_metadata
            )
            
            # Associate transactions with task
            processing_task.transactions.set(client_transactions)
            
            # Set initial status to 'pending' - batch will be submitted later when user runs the task
            processing_task.status = "pending"
            processing_task.save()
            
            processing_tasks.append(processing_task)
            
            messages.success(
                request, 
                f"Created batch processing task for {len(client_transactions)} transactions "
                f"(Client: {client.company_name}). "
                f"Go to ProcessingTask admin to run the batch job when ready."
            )
                
        except BusinessProfile.DoesNotExist:
            messages.error(request, f"Client {client_id} not found")
            continue
            
    return processing_tasks[0] if processing_tasks else None


def submit_processing_task_batch(processing_task: ProcessingTask) -> bool:
    """
    Submit a ProcessingTask to OpenAI Batch API
    
    This function should be called when user manually runs a batch job
    from the admin interface
    
    Args:
        processing_task: ProcessingTask object (accepts 'pending' or 'processing' status)
        
    Returns:
        bool: True if successful, False if failed
    """
    
    # Accept both 'pending' and 'processing' status (admin sets to processing before calling this)
    if processing_task.status not in ["pending", "processing"]:
        logger.error(f"Task {processing_task.task_id} has status '{processing_task.status}' but expected 'pending' or 'processing'")
        return False
        
    try:
        # Get agent
        agent_name = processing_task.task_metadata.get("agent_name")
        if not agent_name:
            logger.error(f"Task {processing_task.task_id} has no agent_name in metadata")
            return False
            
        agent = Agent.objects.get(name=agent_name)
        
        # Get transactions
        transactions = list(processing_task.transactions.all())
        if not transactions:
            logger.error(f"Task {processing_task.task_id} has no transactions")
            return False
            
        # Initialize batch processor
        processor = AsyncBatchProcessor()
        
        # Build batch - for full workflow, get agent info from metadata
        if processing_task.task_type == "batch_full_workflow":
            # For full workflow, use first agent from task metadata 
            first_agent_name = processing_task.task_metadata.get("first_agent", agent_name)
            first_agent = Agent.objects.get(name=first_agent_name)
            jsonl_file = processor.build_jsonl_batch(transactions, first_agent)
            agent_name = f"{first_agent_name} (Full Workflow)"
        else:
            jsonl_file = processor.build_jsonl_batch(transactions, agent)
        
        # Submit to OpenAI
        batch_id = processor.submit_batch(
            jsonl_file, 
            f"LedgerFlow {agent_name} - {len(transactions)} transactions"
        )
        
        # Update task metadata with batch ID
        processing_task.task_metadata.update({
            "openai_batch_id": batch_id,
            "batch_submitted_at": datetime.now(timezone.utc).isoformat()
        })
        processing_task.status = "processing"
        processing_task.save()
        
        logger.info(f"Successfully submitted task {processing_task.task_id} as batch {batch_id}")
        return True
        
    except Exception as e:
        # Mark task as failed
        processing_task.status = "failed"
        processing_task.error_details = {"error": str(e)}
        processing_task.save()
        
        logger.error(f"Failed to submit task {processing_task.task_id}: {e}")
        return False


def check_and_process_completed_batches():
    """
    Check for completed batch jobs and process results
    This should be called periodically (e.g., via cron job or admin action)
    """
    
    # Find processing tasks with batch IDs that are still processing
    pending_tasks = ProcessingTask.objects.filter(
        status="processing",
        task_metadata__openai_batch_id__isnull=False
    )
    
    processor = AsyncBatchProcessor()
    completed_count = 0
    
    for task in pending_tasks:
        batch_id = task.task_metadata.get("openai_batch_id")
        if not batch_id:
            continue
            
        # Check batch status
        batch_status = processor.get_batch_status(batch_id)
        
        # DEBUG: Log the actual batch status
        logger.info(f"Task {task.task_id}: Batch {batch_id} status = {batch_status.get('status')}")
        
        if batch_status.get("status") == "completed":
            try:
                # Get agent
                agent_name = task.task_metadata.get("agent_name")
                agent = Agent.objects.get(name=agent_name)
                
                # Download results
                output_file_id = batch_status.get("output_file_id") 
                if not output_file_id:
                    # Try to get it from the batch object
                    batch = processor.client.batches.retrieve(batch_id)
                    output_file_id = batch.output_file_id
                    
                if output_file_id:
                    batch_results = processor.download_batch_results(output_file_id)
                    
                    # Process results based on task type
                    if task.task_type == "batch_full_workflow":
                        logger.info(f"Task {task.task_id}: Processing full workflow batch results (payee + classification)")
                        # Get first agent from task metadata
                        first_agent_name = task.task_metadata.get("first_agent")
                        if not first_agent_name:
                            raise ValueError(f"Full workflow task {task.task_id} missing first_agent in metadata")
                        first_agent = Agent.objects.get(name=first_agent_name)
                        processed_results = processor.process_full_workflow_batch_results(batch_results, first_agent, task)
                    else:
                        # Check if batch results contain tool calls
                        has_tool_calls = any(
                            result.get("response", {}).get("body", {}).get("choices", [{}])[0].get("message", {}).get("tool_calls")
                            for result in batch_results
                        )
                        
                        # Process results - use appropriate method based on whether tool calls are present
                        if has_tool_calls:
                            logger.info(f"Task {task.task_id}: Processing batch with tool calls using process_batch_results_with_tools")
                            processed_results = processor.process_batch_results_with_tools(batch_results, agent)
                        else:
                            logger.info(f"Task {task.task_id}: Processing batch without tool calls using process_batch_results")
                            processed_results = processor.process_batch_results(batch_results, agent)
                    
                    # Update transactions based on task type
                    if task.task_type == "batch_full_workflow":
                        # For full workflow, use custom update method that handles combined results
                        processor.update_full_workflow_transactions(processed_results, first_agent, task)
                    else:
                        # For regular tasks, use existing update method
                        processor.update_transactions(processed_results, agent, task)
                    
                    # Mark task as completed
                    task.status = "completed"
                    task.task_metadata.update({
                        "completed_at": datetime.now(timezone.utc).isoformat(),
                        "batch_status": batch_status
                    })
                    task.save()
                    
                    completed_count += 1
                    logger.info(f"Completed batch processing task {task.task_id}")
                    
                    # Full workflow tasks handle both payee and classification in one batch job
                    # No separate classification job creation needed
            except Exception as e:
                # Mark task as failed
                task.status = "failed"
                task.error_details = {"error": str(e)}
                task.save()
                
                logger.error(f"Error processing completed batch {batch_id}: {e}")
                
        elif batch_status.get("status") in ["failed", "expired", "cancelled"]:
            # Mark task as failed
            task.status = "failed"
            task.error_details = {
                "error": f"OpenAI batch {batch_status.get('status')}: {batch_status.get('error', 'No details')}"
            }
            task.save()
            
            logger.error(f"Batch {batch_id} failed with status: {batch_status.get('status')}")
            
    logger.info(f"Processed {completed_count} completed batch jobs")
    return completed_count