#!/usr/bin/env python
import os
import django
from django.conf import settings

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ledgerflow.settings')
django.setup()

# Now import and test
from profiles.models import BusinessProfile, Agent, LLMConfig
from django.contrib.admin.sites import site

def test_ai_generator():
    """Test if BusinessProfile and Agent exist, and if we can simulate the AI generator"""
    print("=== AI Profile Generator Test ===")
    
    # Check if BusinessProfile exists
    bp_count = BusinessProfile.objects.count()
    print(f"BusinessProfile count: {bp_count}")
    
    if bp_count > 0:
        bp = BusinessProfile.objects.first()
        print(f"Sample BusinessProfile: {bp.company_name}")
        print(f"Business type: {bp.business_type}")
        print(f"Current common_expenses: {bp.common_expenses[:100] if bp.common_expenses else 'None'}...")
    
    # Check if Agent exists with Business Profile generation
    agent = Agent.objects.filter(name__icontains="business profile generation").first()
    if not agent:
        agent = Agent.objects.filter(name__icontains="business profile generator").first()
    
    if agent:
        print(f"Found agent: {agent.name}")
        print(f"Agent model: {agent.llm.model if agent.llm else 'No LLM configured'}")
        print(f"Agent prompt: {agent.prompt[:100] if agent.prompt else 'None'}...")
    else:
        print("No Business Profile Generator agent found")
        # List all agents
        agents = Agent.objects.all()
        print(f"Available agents ({agents.count()}):")
        for a in agents[:5]:  # Show first 5
            print(f"  - {a.name}")
    
    # Check LLM configs
    llm_count = LLMConfig.objects.count()
    print(f"LLM Config count: {llm_count}")
    if llm_count > 0:
        llm = LLMConfig.objects.first()
        print(f"Sample LLM: {llm.model}")

if __name__ == "__main__":
    test_ai_generator()