#!/usr/bin/env python3
"""
Test script to verify payee lookup functionality with clean API key
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ledgerflow.settings')
django.setup()

from profiles.models import Transaction, Agent
from profiles.admin import call_agent

def test_payee_lookup():
    """Test the payee lookup functionality"""
    print("🔍 Testing Payee Lookup Functionality")
    print("=" * 50)
    
    # Check if Payee Lookup Agent exists
    try:
        agent = Agent.objects.get(name="Payee Lookup Agent")
        print(f"✅ Payee Lookup Agent found: {agent.name}")
        print(f"   Model: {agent.llm.model if agent.llm else 'No LLM configured'}")
        print(f"   Tools: {[tool.name for tool in agent.tools.all()]}")
    except Agent.DoesNotExist:
        print("❌ Payee Lookup Agent not found")
        return False
    
    # Get a sample transaction to test with
    try:
        transaction = Transaction.objects.first()
        if not transaction:
            print("❌ No transactions found in database")
            return False
            
        print(f"\n📝 Testing with transaction:")
        print(f"   Description: {transaction.description}")
        print(f"   Amount: ${transaction.amount}")
        print(f"   Current Payee: {transaction.payee or 'None'}")
        
    except Exception as e:
        print(f"❌ Error getting transaction: {e}")
        return False
    
    # Test the payee lookup call
    print(f"\n🤖 Calling Payee Lookup Agent...")
    try:
        result = call_agent(
            agent_name="Payee Lookup Agent",
            transaction=transaction,
            max_retries=1,
            escalate_on_fail=False
        )
        
        if result and result.get('success'):
            print(f"✅ Payee lookup successful!")
            if 'payee' in result:
                print(f"   Identified Payee: {result['payee']}")
            if 'payee_reasoning' in result:
                print(f"   Reasoning: {result['payee_reasoning']}")
            print(f"   Full result: {result}")
            return True
        else:
            print(f"❌ Payee lookup failed")
            print(f"   Result: {result}")
            return False
            
    except Exception as e:
        print(f"❌ Error calling payee lookup agent: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_payee_lookup()
    if success:
        print(f"\n🎉 Test PASSED - Payee lookup is working!")
        sys.exit(0)
    else:
        print(f"\n💥 Test FAILED - Payee lookup is not working")
        sys.exit(1)