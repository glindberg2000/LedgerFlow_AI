#!/usr/bin/env python3
"""
Debug script for LedgerFlow batch processing system
"""

import os
import sys
import django
import json
from pathlib import Path

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ledgerflow.settings")
sys.path.append(str(Path(__file__).parent))
django.setup()

from profiles.models import ProcessingTask, Transaction, Agent
from profiles.utils.async_batch_processor import submit_processing_task_batch, AsyncBatchProcessor

def main():
    print("=== LedgerFlow Batch Processing Debug Tool ===\n")
    
    # 1. List all processing tasks
    print("1. PROCESSING TASKS:")
    tasks = ProcessingTask.objects.all().order_by('-created_at')[:10]
    
    for task in tasks:
        print(f"   Task ID: {task.task_id}")
        print(f"   Status: {task.status}")
        print(f"   Type: {task.task_type}")
        print(f"   Client: {task.client}")
        print(f"   Transactions: {task.transaction_count}")
        print(f"   Created: {task.created_at}")
        print(f"   Metadata: {json.dumps(task.task_metadata, indent=4)}")
        print("   ---")
    
    # 2. Focus on batch processing tasks
    print("\n2. BATCH PROCESSING TASKS:")
    batch_tasks = ProcessingTask.objects.filter(task_metadata__batch_processing=True).order_by('-created_at')
    
    if not batch_tasks.exists():
        print("   No batch processing tasks found.")
        return
    
    latest_task = batch_tasks.first()
    print(f"   Latest Batch Task: {latest_task.task_id}")
    print(f"   Status: {latest_task.status}")
    print(f"   Agent: {latest_task.task_metadata.get('agent_name', 'Unknown')}")
    print(f"   OpenAI Batch ID: {latest_task.task_metadata.get('openai_batch_id', 'Not submitted')}")
    
    # 3. Examine transactions for this task
    print(f"\n3. TRANSACTIONS IN TASK {latest_task.task_id}:")
    transactions = latest_task.transactions.all()[:5]  # Show first 5
    
    for tx in transactions:
        print(f"   TX {tx.id}: {tx.description[:50]}... | {tx.amount} | {getattr(tx, 'transaction_date', 'N/A')}")
    
    if latest_task.transactions.count() > 5:
        print(f"   ... and {latest_task.transactions.count() - 5} more transactions")
    
    # 4. Check agent configuration
    agent_name = latest_task.task_metadata.get('agent_name')
    if agent_name:
        try:
            agent = Agent.objects.get(name=agent_name)
            print(f"\n4. AGENT CONFIGURATION ({agent_name}):")
            print(f"   LLM Model: {agent.llm.model if agent.llm else 'Not configured'}")
            print(f"   Prompt length: {len(agent.system_prompt)} characters")
            print(f"   Prompt preview: {agent.system_prompt[:200]}...")
        except Agent.DoesNotExist:
            print(f"\n4. AGENT ERROR: Agent '{agent_name}' not found!")
    
    # 5. Test batch processor components
    print(f"\n5. TESTING BATCH PROCESSOR:")
    
    try:
        processor = AsyncBatchProcessor()
        print(f"   ✓ AsyncBatchProcessor initialized")
        
        # Test client creation (this will trigger API key cleaning)
        client = processor.client
        print(f"   ✓ OpenAI client created successfully")
        
        # Test tool definitions
        tools = processor.tool_definitions
        print(f"   ✓ Tool definitions loaded: {len(tools)} tools")
        
    except Exception as e:
        print(f"   ✗ Batch processor error: {e}")
        return
    
    # 6. Interactive debugging options
    print(f"\n6. DEBUGGING OPTIONS:")
    print(f"   a) Run specific task: python debug_batch_processing.py run {latest_task.task_id}")
    print(f"   b) Check batch status: python debug_batch_processing.py status {latest_task.task_id}")
    print(f"   c) View batch JSONL: python debug_batch_processing.py jsonl {latest_task.task_id}")

def run_task(task_id):
    """Debug: Run a specific batch task"""
    try:
        task = ProcessingTask.objects.get(task_id=task_id)
        print(f"Running batch task: {task_id}")
        print(f"Status before: {task.status}")
        
        success = submit_processing_task_batch(task)
        
        task.refresh_from_db()
        print(f"Status after: {task.status}")
        print(f"Success: {success}")
        
        if success:
            print(f"OpenAI Batch ID: {task.task_metadata.get('openai_batch_id', 'Not found')}")
        
    except ProcessingTask.DoesNotExist:
        print(f"Task {task_id} not found")
    except Exception as e:
        print(f"Error running task: {e}")

def check_status(task_id):
    """Check OpenAI batch status"""
    try:
        task = ProcessingTask.objects.get(task_id=task_id)
        batch_id = task.task_metadata.get('openai_batch_id')
        
        if not batch_id:
            print(f"Task {task_id} has no OpenAI batch ID")
            return
        
        processor = AsyncBatchProcessor()
        status = processor.get_batch_status(batch_id)
        
        print(f"OpenAI Batch Status for {batch_id}:")
        print(json.dumps(status, indent=2))
        
    except ProcessingTask.DoesNotExist:
        print(f"Task {task_id} not found")
    except Exception as e:
        print(f"Error checking status: {e}")

def view_jsonl(task_id):
    """View the JSONL that would be sent to OpenAI"""
    try:
        task = ProcessingTask.objects.get(task_id=task_id)
        agent_name = task.task_metadata.get('agent_name')
        agent = Agent.objects.get(name=agent_name)
        transactions = list(task.transactions.all())
        
        processor = AsyncBatchProcessor()
        jsonl_file = processor.build_jsonl_batch(transactions, agent)
        
        print(f"JSONL file created: {jsonl_file}")
        print(f"Contents:")
        
        with open(jsonl_file, 'r') as f:
            lines = f.readlines()
            for i, line in enumerate(lines[:3]):  # Show first 3 lines
                print(f"Line {i+1}: {line.strip()}")
            
            if len(lines) > 3:
                print(f"... and {len(lines) - 3} more lines")
        
    except Exception as e:
        print(f"Error viewing JSONL: {e}")

def download_results(task_id):
    """Download and view the actual results from OpenAI"""
    try:
        task = ProcessingTask.objects.get(task_id=task_id)
        batch_id = task.task_metadata.get('openai_batch_id')
        
        if not batch_id:
            print(f"Task {task_id} has no OpenAI batch ID")
            return
        
        processor = AsyncBatchProcessor()
        
        # Get batch status first
        status = processor.get_batch_status(batch_id)
        print(f"Batch Status: {status.get('status')}")
        
        if status.get('status') != 'completed':
            print(f"Batch is not completed yet. Current status: {status.get('status')}")
            return
        
        output_file_id = status.get('output_file_id')
        if not output_file_id:
            print("No output file ID found")
            return
        
        print(f"Downloading results from file: {output_file_id}")
        
        # Download the results
        results = processor.download_batch_results(output_file_id)
        
        print(f"\nFound {len(results)} results:")
        for i, result in enumerate(results):
            custom_id = result.get('custom_id', 'Unknown')
            
            print(f"\nResult {i+1} (Custom ID: {custom_id}):")
            print(f"Full result structure: {json.dumps(result, indent=2)[:1000]}...")
            
            # Check if this is the direct response or wrapped
            if 'response' in result:
                response = result['response']
                print(f"Has response wrapper")
                
                if 'body' in response:
                    body = response['body']
                    print(f"Has body in response")
                    
                    if 'choices' in body and body['choices']:
                        message = body['choices'][0]['message']
                        content = message.get('content')
                        tool_calls = message.get('tool_calls')
                        
                        print(f"Content: {content}")
                        print(f"Tool calls: {len(tool_calls) if tool_calls else 0}")
                        
                        if tool_calls:
                            for tc in tool_calls:
                                print(f"  Tool: {tc['function']['name']}")
                                print(f"  Args: {tc['function']['arguments']}")
        
    except ProcessingTask.DoesNotExist:
        print(f"Task {task_id} not found")
    except Exception as e:
        print(f"Error downloading results: {e}")

def process_results(task_id):
    """Process the results and update the database"""
    try:
        task = ProcessingTask.objects.get(task_id=task_id)
        batch_id = task.task_metadata.get('openai_batch_id')
        agent_name = task.task_metadata.get('agent_name')
        
        if not batch_id:
            print(f"Task {task_id} has no OpenAI batch ID")
            return
            
        agent = Agent.objects.get(name=agent_name)
        processor = AsyncBatchProcessor()
        
        # Get batch status
        status = processor.get_batch_status(batch_id)
        if status.get('status') != 'completed':
            print(f"Batch is not completed yet. Status: {status.get('status')}")
            return
        
        # Download results
        output_file_id = status.get('output_file_id')
        batch_results = processor.download_batch_results(output_file_id)
        
        # Process results
        processed_results = processor.process_batch_results(batch_results, agent)
        
        print(f"Processing results for {len(processed_results)} transactions:")
        for tx_id, result in processed_results.items():
            print(f"Transaction {tx_id}: {'✓' if result['success'] else '✗'}")
            if not result['success']:
                print(f"  Error: {result['error']}")
            else:
                print(f"  Data keys: {list(result['data'].keys())}")
        
        # Update transactions in database
        success_count, failed_count = processor.update_transactions(processed_results, agent, task)
        
        print(f"\nDatabase Updates:")
        print(f"  Successful: {success_count}")
        print(f"  Failed: {failed_count}")
        
        # Update task status
        task.refresh_from_db()
        print(f"Task status: {task.status}")
        
    except Exception as e:
        print(f"Error processing results: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "run" and len(sys.argv) > 2:
            run_task(sys.argv[2])
        elif command == "status" and len(sys.argv) > 2:
            check_status(sys.argv[2])
        elif command == "jsonl" and len(sys.argv) > 2:
            view_jsonl(sys.argv[2])
        elif command == "download" and len(sys.argv) > 2:
            download_results(sys.argv[2])
        elif command == "process" and len(sys.argv) > 2:
            process_results(sys.argv[2])
        else:
            print("Usage:")
            print("  python debug_batch_processing.py")
            print("  python debug_batch_processing.py run <task_id>")
            print("  python debug_batch_processing.py status <task_id>")
            print("  python debug_batch_processing.py jsonl <task_id>")
            print("  python debug_batch_processing.py download <task_id>")
            print("  python debug_batch_processing.py process <task_id>")
    else:
        main()