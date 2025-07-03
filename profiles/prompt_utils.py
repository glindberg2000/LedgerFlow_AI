def get_fallback_payee_prompt():
    """Return the fallback system prompt for payee agent as a plain string."""
    return """You are a transaction analysis assistant. Your task is to identify the payee/merchant from transaction descriptions, use search tools as needed, and synthesize a clear, normalized description. Return a final response in the exact JSON format specified.\n\nIMPORTANT RULES:\n1. Make as many search calls as needed to gather complete information\n2. Synthesize all information into a clear, normalized response\n3. NEVER use the raw transaction description in your final response\n4. Format the response exactly as specified.\n"""


def get_fallback_payee_prompts(transaction):
    """Return (system_prompt, user_prompt) for payee agent fallback."""
    system_prompt = """You are a transaction analysis assistant. Your task is to identify the payee/merchant from transaction descriptions, use search tools as needed, and synthesize a clear, normalized description. Return a final response in the exact JSON format specified.

IMPORTANT RULES:
1. Make as many search calls as needed to gather complete information
2. Synthesize all information into a clear, normalized response
3. NEVER use the raw transaction description in your final response
4. Format the response exactly as specified.
"""
    user_prompt = f"""Analyze this transaction and return a JSON object with EXACTLY these field names:
{{
    "normalized_description": "string - A VERY SUCCINCT 1-5 word summary of what was purchased/paid for (e.g., 'Grocery shopping', 'Fast food purchase', 'Office supplies'). DO NOT include vendor details, just the core type of purchase.",
    "payee": "string - The normalized payee/merchant name (e.g., 'Lowe's' not 'LOWE'S #1636', 'Walmart' not 'WALMART #1234')",
    "confidence": "string - Must be exactly 'high', 'medium', or 'low'",
    "reasoning": "string - VERBOSE explanation of the identification, including all search results and any details about the vendor, business type, and what was purchased. If you have a long description, put it here, NOT in normalized_description.",
    "transaction_type": "string - One of: purchase, payment, transfer, fee, subscription, service",
    "questions": "string - Any questions about unclear elements",
    "needs_search": "boolean - Whether additional vendor information is needed"
}}

Transaction: {transaction.description}
Amount: ${transaction.amount}
Date: {transaction.transaction_date}"""
    return system_prompt, user_prompt
