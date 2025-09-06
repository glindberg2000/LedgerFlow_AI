#!/usr/bin/env python3
"""
Debug script to capture raw GPT-5 responses and see what's happening
"""
import os
import json
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_gpt5_raw_response():
    """Test GPT-5 and capture the raw response content"""
    print("🔍 Debug: Testing GPT-5 Raw Response")
    print("=" * 50)
    
    # Clean the API key (same as Django does)
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        api_key = api_key.strip().replace('\n', '').replace('\r', '').replace(' ', '')
    
    print(f"API Key Length: {len(api_key) if api_key else 'None'}")
    print(f"API Key First 10: {api_key[:10] if api_key else 'None'}...")
    print(f"API Key Last 10: ...{api_key[-10:] if api_key else 'None'}")
    print()
    
    try:
        client = OpenAI(api_key=api_key, timeout=120)
        
        # Use same prompt structure as Django admin
        system_prompt = """You are an AI assistant for generating business profiles from user descriptions.

Based on the following business information, generate a comprehensive business profile with the specific JSON structure required:

Business Information:
- Company Name: Test Company
- Business Type: Technology Consulting
- Description: Software development and consulting services
- Contact Info: 123 Test St, Test City, CA 12345
- Location: California

"""

        user_prompt = """
Generate specific business profile fields based on the above business information. Provide detailed, industry-specific, and actionable information that is directly relevant to this particular business (not generic advice).

Return ONLY a JSON object with these exact fields:
{
  "common_expenses": "Specific expenses relevant to Test Company and Technology Consulting industry",
  "custom_categories": "Expense categories specific to Technology Consulting businesses like Test Company", 
  "industry_keywords": "Keywords and terms specifically related to Technology Consulting and businesses like Test Company",
  "category_patterns": "Common transaction descriptions and patterns for Technology Consulting businesses",
  "business_rules": "Specific business rules and considerations for Test Company type business"
}"""

        # Same JSON schema as Django
        json_schema = {
            "type": "json_schema",
            "json_schema": {
                "name": "business_profile_response",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "common_expenses": {
                            "type": "string",
                            "description": "Common business expenses for this industry/business type"
                        },
                        "custom_categories": {
                            "type": "string",
                            "description": "Custom expense categories specific to this business"
                        },
                        "industry_keywords": {
                            "type": "string",
                            "description": "Keywords that identify transactions for this industry"
                        },
                        "category_patterns": {
                            "type": "string",
                            "description": "Patterns for categorizing transactions automatically"
                        },
                        "business_rules": {
                            "type": "string",
                            "description": "Business-specific rules for transaction processing"
                        }
                    },
                    "required": [
                        "common_expenses",
                        "custom_categories", 
                        "industry_keywords",
                        "category_patterns",
                        "business_rules"
                    ],
                    "additionalProperties": False
                }
            }
        }

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        # Test multiple GPT-5 variants
        models_to_test = [
            "gpt-5",
            "gpt-5-2025-08-07", 
            "gpt-4.1-mini",  # For comparison
        ]

        for model in models_to_test:
            print(f"\n🧪 Testing {model}")
            print("-" * 30)
            
            try:
                # Build API parameters same as Django (based on GPT-5 migration guide)
                api_params = {
                    "model": model,
                    "messages": messages,
                    "response_format": json_schema
                }
                
                # Handle GPT-5 parameter requirements (REASONING MODEL - rejects legacy params)
                if model.startswith("gpt-5"):
                    # GPT-5 is a reasoning model that REJECTS legacy parameters
                    # GPT-5 uses tokens for internal reasoning FIRST, then for response
                    # Remove token cap - let GPT-5 use whatever tokens needed
                    # Don't specify max_completion_tokens - use model default
                    # GPT-5 enforces temperature=1 internally - DO NOT specify temperature
                    # GPT-5 REJECTS: temperature, top_p, presence_penalty, frequency_penalty, 
                    # logprobs, top_logprobs, logit_bias, stop, n, max_tokens
                    pass  # No additional parameters for GPT-5
                else:
                    # Legacy models (GPT-4.1, etc.) support classic parameters
                    api_params["max_tokens"] = 1000
                    api_params["temperature"] = 0.7
                
                print(f"API Parameters: {list(api_params.keys())}")
                print(f"Making API call...")
                
                response = client.chat.completions.create(**api_params)
                
                # Extract response content
                raw_content = response.choices[0].message.content
                
                print(f"✅ {model} - SUCCESS")
                print(f"Raw Content Length: {len(raw_content) if raw_content else 0}")
                print(f"Raw Content Type: {type(raw_content)}")
                print(f"Raw Content (first 200 chars): {repr(raw_content[:200]) if raw_content else 'None'}")
                
                if raw_content:
                    # Try to parse JSON
                    try:
                        parsed = json.loads(raw_content)
                        print(f"✅ JSON Parse - SUCCESS")
                        print(f"JSON Keys: {list(parsed.keys()) if isinstance(parsed, dict) else 'Not a dict'}")
                    except json.JSONDecodeError as e:
                        print(f"❌ JSON Parse - FAILED: {e}")
                        print(f"Raw content for manual inspection:")
                        print(f"'{raw_content}'")
                else:
                    print(f"❌ EMPTY RESPONSE - This is the problem!")
                
                # Check response metadata
                print(f"Response ID: {response.id}")
                print(f"Model Used: {response.model}")
                print(f"Usage: {response.usage}")
                print(f"Finish Reason: {response.choices[0].finish_reason}")
                
            except Exception as e:
                print(f"❌ {model} - FAILED: {type(e).__name__}: {e}")
                
        print(f"\n🏁 Debug complete!")

    except Exception as e:
        print(f"❌ SETUP FAILED: {type(e).__name__}: {e}")

if __name__ == "__main__":
    test_gpt5_raw_response()