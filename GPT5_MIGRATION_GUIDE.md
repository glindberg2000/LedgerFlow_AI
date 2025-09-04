# 🚀 GPT-5 Migration Guide: Production-Ready Implementation

## ✅ Current Status: FULLY WORKING

**All GPT-5 variants tested and operational:**
- ✅ `gpt-4.1-mini` - 4.85s (baseline)
- ✅ `gpt-5-2025-08-07` - 3.79s (pinned, recommended for production)
- ✅ `gpt-5` - 3.53s (rolling alias, auto-updates)

## 🔑 Key Changes for GPT-5 Consistency

### 1. Use Pinned Model IDs for Production

```python
# ❌ Avoid - Rolling alias (gets silent upgrades)
model = "gpt-5"

# ✅ Recommended - Pinned snapshot (reproducible)
model = "gpt-5-2025-08-07"
```

**Available GPT-5 Model IDs:**
- `gpt-5-2025-08-07` - **RECOMMENDED** for production consistency
- `gpt-5` - Rolling alias (latest version)
- `gpt-5-mini` - Faster, cost-efficient variant
- `gpt-5-nano` - Fastest, most cost-efficient
- `gpt-5-chat-latest` - Latest chat variant

### 2. Parameter Requirements

#### GPT-5 Restrictions:
```python
# ❌ These parameters are NOT supported in GPT-5:
{
    "temperature": 0.7,        # GPT-5 enforces temperature=1
    "max_tokens": 1000,        # Use max_completion_tokens instead
    "top_p": 0.9,             # Not supported
    "frequency_penalty": 0.5   # Not supported
}

# ✅ GPT-5 compatible parameters:
{
    "max_completion_tokens": 1000,  # Use this instead of max_tokens
    # temperature defaults to 1 - don't specify it
    "response_format": {"type": "json_schema", "json_schema": {...}}
}
```

#### Implementation Pattern:
```python
def create_completion(model, messages, max_tokens=1000):
    """Production-ready GPT-5 compatible function"""
    
    api_params = {
        "model": model,
        "messages": messages,
        "response_format": {"type": "json_schema", "json_schema": your_schema}
    }
    
    # Handle GPT-5 parameter differences
    if model.startswith("gpt-5"):
        api_params["max_completion_tokens"] = max_tokens
        # Don't set temperature - GPT-5 enforces temperature=1
    else:
        api_params["max_tokens"] = max_tokens
        api_params["temperature"] = 0.7
    
    return client.chat.completions.create(**api_params)
```

### 3. Enforce Structured Outputs for Determinism

Since GPT-5 enforces `temperature=1`, use structured outputs for consistent results:

```python
# ✅ JSON Schema for deterministic output
business_profile_schema = {
    "type": "json_schema",
    "json_schema": {
        "name": "business_profile_response",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "common_expenses": {"type": "string"},
                "custom_categories": {"type": "string"},
                "industry_keywords": {"type": "string"}
            },
            "required": ["common_expenses", "custom_categories", "industry_keywords"],
            "additionalProperties": False
        }
    }
}

response = client.chat.completions.create(
    model="gpt-5-2025-08-07",
    messages=[...],
    response_format=business_profile_schema
)
```

## 🛠️ Implementation in LedgerFlow

### Current Django Implementation

The business profile generator (`profiles/admin.py`) has been updated with production-ready GPT-5 support:

```python
# GPT-5 specific parameter adjustments (following OpenAI migration guide)
if model.startswith("gpt-5"):
    # GPT-5 uses max_completion_tokens and enforces temperature=1
    api_params["max_completion_tokens"] = 1000
    # Remove temperature parameter - GPT-5 enforces temperature=1
    # Use response_format for deterministic JSON output instead
else:
    # Other models use max_tokens and can use custom temperature
    api_params["max_tokens"] = 1000
    api_params["temperature"] = 0.7
```

### Environment Configuration

Update `.env` to use pinned GPT-5 for consistency:

```env
# For production consistency
OPENAI_MODEL_FAST=gpt-4.1-mini
OPENAI_MODEL_PRECISE=gpt-5-2025-08-07  # Pinned version
OPENAI_MODEL_OCR=gpt-4.1
```

## 📊 Performance Benchmarks

Based on our testing with crypto trading business profile generation:

| Model | Duration | Status | Use Case |
|-------|----------|--------|----------|
| `gpt-4.1-mini` | 4.85s | ✅ | Current production baseline |
| `gpt-5-2025-08-07` | 3.79s | ✅ | **Recommended for production** |
| `gpt-5` | 3.53s | ✅ | Development/testing |

**GPT-5 shows 20-22% faster response times** while maintaining high-quality structured JSON output.

## 🚨 Critical Issues Resolved

### Issue 1: API Key Corruption
**Problem**: Embedded newlines in API keys causing `Illegal header value` errors  
**Solution**: Implemented key cleaning in both Django and test scripts:
```python
api_key = api_key.strip().replace('\n', '').replace('\r', '').replace(' ', '')
```

### Issue 2: Parameter Incompatibility  
**Problem**: GPT-5 rejected `max_tokens` and custom `temperature` values  
**Solution**: Dynamic parameter selection based on model type

### Issue 3: Inconsistent Behavior
**Problem**: Rolling model aliases causing deployment variations  
**Solution**: Pinned model versions for production consistency

## 🎯 Recommendations

### For Production Deployments:
1. **Use `gpt-5-2025-08-07`** for consistent, reproducible results
2. **Always use JSON Schema** response format for structured data
3. **Remove unsupported parameters** (temperature, max_tokens, etc.)
4. **Add CI health checks** to validate GPT-5 integration

### For Development:
1. **Test with both pinned and rolling versions** to catch breaking changes
2. **Use the test script** (`test_gpt_models.py`) to validate new API keys
3. **Monitor OpenAI documentation** for new pinned versions

## 🔧 Testing & Validation

Run the included test script to validate your setup:

```bash
python test_gpt_models.py
```

Expected output:
```
✅ gpt-4.1-mini SUCCESS | 4.85s
✅ gpt-5-2025-08-07 SUCCESS | 3.79s  
✅ gpt-5 SUCCESS | 3.53s
```

## 📋 Migration Checklist

- [ ] Update model IDs to use pinned versions
- [ ] Remove unsupported parameters (temperature, max_tokens)
- [ ] Implement dynamic parameter selection
- [ ] Add JSON Schema response format
- [ ] Update environment configuration
- [ ] Test with validation script
- [ ] Add CI health checks
- [ ] Update documentation and team notifications

---

**Status**: ✅ Production Ready  
**Last Updated**: September 4, 2025  
**Django Version**: 5.2.4  
**OpenAI Python**: Latest compatible version