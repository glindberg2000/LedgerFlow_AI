#!/usr/bin/env python3
"""
Fix the Payee Lookup Agent's prompt to properly include transaction data
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ledgerflow.settings')
django.setup()

from profiles.models import Agent

def fix_payee_agent_prompt():
    """Fix the Payee Lookup Agent's prompt to include transaction data"""
    print("🔧 Fixing Payee Lookup Agent Prompt")
    print("=" * 50)
    
    try:
        agent = Agent.objects.get(name="Payee Lookup Agent")
        print(f"✅ Found agent: {agent.name}")
        
        # Current broken prompt
        print("❌ Current broken prompt:")
        print(repr(agent.prompt))
        print()
        
        # New correct prompt with transaction data
        new_prompt = """You are a transaction analysis assistant. Your task is to identify the payee/merchant from transaction descriptions, use search tools as needed, and synthesize a clear, normalized description.

IMPORTANT RULES:
1. Make as many search calls as needed to gather complete information
2. Synthesize all information into a clear, normalized response  
3. NEVER use the raw transaction description in your final response
4. Format the response exactly as specified below

---USER---

Analyze this transaction and return a JSON object with EXACTLY these field names:
{
    "normalized_description": "string - A VERY SUCCINCT 1-5 word summary of what was purchased/paid for (e.g., 'Grocery shopping', 'Fast food purchase', 'Office supplies'). DO NOT include vendor details, just the core type of purchase.",
    "payee": "string - The normalized payee/merchant name (e.g., 'Lowe's' not 'LOWE'S #1636', 'Walmart' not 'WALMART #1234')",
    "confidence": "string - Must be exactly 'high', 'medium', or 'low'",
    "reasoning": "string - VERBOSE explanation of the identification, including all search results and any details about the vendor, business type, and what was purchased. If you have a long description, put it here, NOT in normalized_description.",
    "transaction_type": "string - One of: purchase, payment, transfer, fee, subscription, service",
    "questions": "string - Any questions about unclear elements",
    "needs_search": "boolean - Whether additional vendor information is needed"
}

Transaction: {{transaction.description}}
Amount: ${{transaction.amount}}
Date: {{transaction.transaction_date}}

{% if business_profile %}
Business Context: This transaction is for {{business_profile.business_name}}, a {{business_profile.business_type}} business.
{% endif %}"""

        # Update the prompt
        agent.prompt = new_prompt
        agent.save()
        
        print("✅ Updated prompt successfully!")
        print("🔍 New prompt preview:")
        print(new_prompt[:200] + "...")
        print()
        print("📋 Key features added:")
        print("   - Includes {{transaction.description}} variable")
        print("   - Includes {{transaction.amount}} and {{transaction.transaction_date}} variables")
        print("   - Has ---USER--- delimiter for proper system/user split")
        print("   - Includes business_profile context if available")
        print("   - Provides clear JSON response format")
        print("   - Instructs agent to use search tools")
        print()
        print("🎉 Payee Lookup Agent should now work correctly!")
        
    except Agent.DoesNotExist:
        print("❌ Payee Lookup Agent not found in database")
        return False
    except Exception as e:
        print(f"❌ Error updating agent: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = fix_payee_agent_prompt()
    if success:
        print("\n✅ Fix completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Fix failed!")
        sys.exit(1)