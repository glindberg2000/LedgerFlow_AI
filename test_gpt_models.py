#!/usr/bin/env python3
"""
Simple test script to compare GPT-5 and GPT-4.1 API calls
"""
import os
import time
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_model(model_name, timeout=60):
    """Test a specific OpenAI model with a simple request"""
    print(f"\n🧪 Testing {model_name}...")
    print(f"   Timeout: {timeout} seconds")
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ No API key found!")
        return None
    
    # Clean the API key (remove any whitespace/newlines like Django admin does)
    api_key = api_key.strip().replace('\n', '').replace('\r', '').replace(' ', '')
    
    print(f"   API Key: {api_key[:10]}...")
    print(f"   API Key Length: {len(api_key)}")
    print(f"   API Key ends with: ...{api_key[-10:]}")
    
    try:
        client = OpenAI(api_key=api_key, timeout=timeout)
        print(f"   OpenAI client created successfully")
        
        # Simple test prompt
        test_prompt = "Generate a JSON object with these fields: name, type, description. Make it about cryptocurrency trading."
        
        start_time = time.time()
        print(f"   Making API call to {model_name}...")
        
        # GPT-5 has different parameter requirements (including pinned versions)
        if model_name.startswith("gpt-5"):
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant. Always respond with valid JSON."},
                    {"role": "user", "content": test_prompt}
                ],
                max_completion_tokens=200
                # temperature not specified (GPT-5 enforces temperature=1)
            )
        else:
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant. Always respond with valid JSON."},
                    {"role": "user", "content": test_prompt}
                ],
                max_tokens=200,
                temperature=0.7
            )
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"✅ {model_name} SUCCESS")
        print(f"   Duration: {duration:.2f} seconds")
        print(f"   Response: {response.choices[0].message.content[:100]}...")
        
        return {
            "model": model_name,
            "success": True,
            "duration": duration,
            "response": response.choices[0].message.content
        }
        
    except Exception as e:
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"❌ {model_name} FAILED")
        print(f"   Duration: {duration:.2f} seconds")
        print(f"   Error Type: {type(e).__name__}")
        print(f"   Error Message: {str(e)}")
        
        # Additional debugging for connection errors
        if hasattr(e, '__cause__') and e.__cause__:
            print(f"   Underlying cause: {type(e.__cause__).__name__}: {str(e.__cause__)}")
        
        return {
            "model": model_name,
            "success": False,
            "duration": duration,
            "error": str(e)
        }

def main():
    print("🚀 OpenAI Model Comparison Test")
    print("=" * 50)
    
    # Test both models (using pinned GPT-5 version for consistency)
    models_to_test = [
        ("gpt-4.1-mini", 30),        # GPT-4.1-mini (current working model)
        ("gpt-5-2025-08-07", 120),   # GPT-5 pinned version for consistency
        ("gpt-5", 120)               # GPT-5 rolling alias (for comparison)
    ]
    
    results = []
    
    for model, timeout in models_to_test:
        result = test_model(model, timeout)
        if result:
            results.append(result)
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 SUMMARY")
    print("=" * 50)
    
    for result in results:
        status = "✅ SUCCESS" if result["success"] else "❌ FAILED"
        print(f"{result['model']:10} | {status} | {result['duration']:.2f}s")
        if not result["success"]:
            print(f"           | Error: {result['error'][:60]}...")
    
    print("\n🏁 Test completed!")

if __name__ == "__main__":
    main()