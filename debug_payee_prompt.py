#!/usr/bin/env python3
"""
Debug script to check what the Payee Lookup Agent's actual prompt is in the database
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ledgerflow.settings')
django.setup()

from profiles.models import Agent, Transaction

def debug_payee_agent():
    """Debug the Payee Lookup Agent prompt and context"""
    print("🔍 Debugging Payee Lookup Agent")
    print("=" * 60)
    
    # Get the agent
    try:
        agent = Agent.objects.get(name="Payee Lookup Agent")
        print(f"✅ Found agent: {agent.name}")
        print(f"   Purpose: {agent.purpose}")
        print(f"   Model: {agent.llm.model if agent.llm else 'No LLM'}")
        print(f"   Tools: {[tool.name for tool in agent.tools.all()]}")
        print()
        
        # Print the agent's actual prompt from the database
        print("📝 Agent Prompt from Database:")
        print("-" * 40)
        if agent.prompt:
            print(repr(agent.prompt))
        else:
            print("NO PROMPT STORED IN DATABASE")
        print("-" * 40)
        print()
        
        # Get a sample transaction
        transaction = Transaction.objects.first()
        if not transaction:
            print("❌ No transactions found")
            return
            
        print(f"📋 Sample Transaction:")
        print(f"   ID: {transaction.id}")
        print(f"   Description: {transaction.description}")
        print(f"   Amount: ${transaction.amount}")
        print(f"   Date: {transaction.transaction_date}")
        print()
        
        # Test the context building
        from profiles.admin import call_agent
        import jinja2
        
        context = {
            "transaction": transaction,
            "allowed_categories": "",
            "business_profile": getattr(transaction, "client", None),
            "payee_reasoning": getattr(transaction, "payee_reasoning", None),
        }
        
        print("🧪 Testing Template Rendering:")
        print("-" * 40)
        
        if agent.prompt:
            try:
                env = jinja2.Environment(undefined=jinja2.StrictUndefined)
                template = env.from_string(agent.prompt)
                rendered = template.render(**context)
                
                print("✅ Template rendered successfully:")
                print(repr(rendered))
                
                # Check if it splits into system/user
                if "---USER---" in rendered:
                    system_prompt, user_prompt = rendered.split("---USER---", 1)
                    print("\n🔄 Split into system/user prompts:")
                    print("SYSTEM:", repr(system_prompt))
                    print("USER:", repr(user_prompt))
                else:
                    print("\n📝 Single system prompt (no ---USER--- delimiter)")
                    
            except Exception as e:
                print(f"❌ Template rendering failed: {e}")
                print("Will fall back to fallback prompts")
                
                # Test fallback
                from profiles.prompt_utils import get_fallback_payee_prompts
                system_prompt, user_prompt = get_fallback_payee_prompts(transaction)
                print("\n🔧 Fallback prompts:")
                print("SYSTEM:", repr(system_prompt[:200] + "..."))
                print("USER:", repr(user_prompt[:200] + "..."))
        else:
            print("No stored prompt, will use fallback")
            from profiles.prompt_utils import get_fallback_payee_prompts
            system_prompt, user_prompt = get_fallback_payee_prompts(transaction)
            print("\n🔧 Fallback prompts:")
            print("SYSTEM:", repr(system_prompt[:200] + "..."))
            print("USER:", repr(user_prompt[:200] + "..."))
        
        print("-" * 40)
        
    except Agent.DoesNotExist:
        print("❌ Payee Lookup Agent not found in database")
        return
        
if __name__ == "__main__":
    debug_payee_agent()