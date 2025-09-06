#!/usr/bin/env python3
"""
Test all agents to verify they work correctly with the new prompt templates
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ledgerflow.settings')
django.setup()

from profiles.models import Transaction, Agent
from profiles.admin import call_agent
import json

def test_all_agents():
    """Test all agents with sample transactions"""
    print("🧪 Testing All Agent Functionality")
    print("=" * 60)
    
    # Get a sample transaction
    try:
        transaction = Transaction.objects.first()
        if not transaction:
            print("❌ No transactions found in database")
            return False
    except Exception as e:
        print(f"❌ Error getting transaction: {e}")
        return False
    
    print(f"📋 Using sample transaction:")
    print(f"   ID: {transaction.id}")
    print(f"   Description: {transaction.description}")
    print(f"   Amount: ${transaction.amount}")
    print(f"   Date: {transaction.transaction_date}")
    print()
    
    # Test each agent
    agents_to_test = [
        "Payee Lookup Agent",
        "Classification Agent",
        "Business Profile Generation Agent",
        "Classification Escalation Agent"
    ]
    
    results = {}
    
    for agent_name in agents_to_test:
        print(f"🤖 Testing {agent_name}...")
        print("-" * 40)
        
        try:
            # Check if agent exists
            agent = Agent.objects.get(name=agent_name)
            print(f"   ✅ Agent found: {agent.name}")
            print(f"      Model: {agent.llm.model if agent.llm else 'No LLM'}")
            print(f"      Tools: {[tool.name for tool in agent.tools.all()]}")
            
            # Test the agent (with timeout and limited retries for testing)
            print(f"   🔄 Calling agent...")
            
            result = call_agent(
                agent_name=agent_name,
                transaction=transaction,
                max_retries=1,  # Reduced for testing
                escalate_on_fail=False
            )
            
            if result:
                print(f"   ✅ Agent responded successfully!")
                
                # Show key fields from response
                key_fields = ['payee', 'normalized_description', 'confidence', 'classification_type', 'business_name']
                shown_fields = []
                for field in key_fields:
                    if field in result:
                        shown_fields.append(f"{field}: {result[field]}")
                
                if shown_fields:
                    print(f"   📄 Key response fields:")
                    for field in shown_fields[:3]:  # Show up to 3 key fields
                        print(f"      - {field}")
                
                # Check if response looks valid (has expected structure)
                if agent_name == "Payee Lookup Agent":
                    expected_fields = ['payee', 'normalized_description', 'confidence']
                elif agent_name in ["Classification Agent", "Classification Escalation Agent"]:
                    expected_fields = ['classification_type', 'confidence']
                elif agent_name == "Business Profile Generation Agent":
                    expected_fields = ['business_name', 'business_type', 'industry']
                else:
                    expected_fields = []
                
                missing_fields = [f for f in expected_fields if f not in result]
                if missing_fields:
                    print(f"   ⚠️  Missing expected fields: {missing_fields}")
                else:
                    print(f"   ✅ Response structure looks correct")
                
                results[agent_name] = {"success": True, "result": result}
            else:
                print(f"   ❌ Agent returned empty result")
                results[agent_name] = {"success": False, "error": "Empty result"}
                
        except Agent.DoesNotExist:
            print(f"   ❌ Agent '{agent_name}' not found in database")
            results[agent_name] = {"success": False, "error": "Agent not found"}
        except Exception as e:
            print(f"   ❌ Error testing agent: {str(e)}")
            results[agent_name] = {"success": False, "error": str(e)}
        
        print()
    
    # Summary
    print("=" * 60)
    print("📊 TESTING SUMMARY")
    print("=" * 60)
    
    successful = 0
    failed = 0
    
    for agent_name, result in results.items():
        status = "✅ PASS" if result["success"] else "❌ FAIL"
        print(f"{agent_name:35} | {status}")
        if not result["success"]:
            print(f"{'':35} | Error: {result['error']}")
        
        if result["success"]:
            successful += 1
        else:
            failed += 1
    
    print("-" * 60)
    print(f"Total Agents Tested: {len(results)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    
    if failed == 0:
        print("\n🎉 ALL AGENTS ARE WORKING CORRECTLY!")
        return True
    else:
        print(f"\n⚠️  {failed} agents need attention")
        return False

if __name__ == "__main__":
    success = test_all_agents()
    if success:
        print("\n✅ All agent tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some agent tests failed!")
        sys.exit(1)