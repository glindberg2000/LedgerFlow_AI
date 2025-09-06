#!/usr/bin/env python
import os
import django
from django.conf import settings

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ledgerflow.settings')
django.setup()

# Now import and test
from profiles.models import BusinessProfile
from profiles.admin import generate_ai_profile

def test_ai_profile_generator():
    """Test the AI profile generator with structured output"""
    print("Testing AI Profile Generator with GPT-5 and structured output...")
    
    # Get the first business profile
    bp = BusinessProfile.objects.first()
    if not bp:
        print("No BusinessProfile found in database")
        return
    
    print(f"Testing with BusinessProfile: {bp.company_name}")
    print(f"Business Type: {bp.business_type}")
    print(f"Description: {bp.business_description[:100]}...")
    
    try:
        result = generate_ai_profile(bp)
        print("\n✅ SUCCESS: AI profile generator working!")
        print("Generated AI Profile Fields:")
        for key, value in result.items():
            print(f"  {key}: {value[:150] + '...' if len(value) > 150 else value}")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_ai_profile_generator()