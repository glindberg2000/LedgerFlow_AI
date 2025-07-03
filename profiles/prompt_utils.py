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


def get_fallback_classification_prompts(
    transaction, allowed_categories=None, business_profile=None, payee_reasoning=None
):
    """Return (system_prompt, user_prompt) for classification agent fallback."""

    system_prompt = """You are an expert in business expense classification and tax preparation. Your role is to:
1. Analyze transactions and determine if they are business or personal expenses.
2. For business expenses, determine the appropriate worksheet (6A, Vehicle, HomeOffice, or Personal).
3. Provide detailed reasoning for your decisions.
4. Flag any transactions that need additional review.

Consider these factors:
- Business type and description
- Industry context
- Transaction patterns
- Amount and frequency
- Business rules and patterns
"""

    user_prompt = (
        f"Return your analysis in this exact JSON format:\n"
        "{\n"
        '    "classification_type": "business" or "personal",\n'
        '    "worksheet": "6A" or "Vehicle" or "HomeOffice" or "Personal",\n'
        '    "category_id": "IRS-<id>" or "BIZ-<id>" or "Other" or "Personal" or "Review",\n'
        '    "category_name": "Name of the selected category from the list below",\n'
        '    "confidence": "high" or "medium" or "low",\n'
        '    "reasoning": "Detailed explanation of your decision, referencing both the business profile and payee reasoning above.",\n'
        '    "business_percentage": "integer - 0 for personal, 100 for clear business, 50 for dual-purpose, etc.",\n'
        '    "questions": "Any questions or uncertainties about this classification",\n'
        '    "proposed_category_name": "If you chose \'Review\', propose a new category name that best fits the transaction. Otherwise, leave blank."\n'
        "}\n\n"
        f"Transaction: {transaction.description}\n"
        f"Amount: ${transaction.amount}\n"
        f"Date: {transaction.transaction_date}\n"
    )

    if allowed_categories:
        user_prompt += f"\nAllowed Categories (choose ONLY from this list):\n{allowed_categories}\n"

    user_prompt += (
        "\nIMPORTANT RULES:"
        "\n- You MUST use one of the allowed category_id values above."
        "\n- If the expense is business-related but does not fit any allowed category, use 'Review' and propose a new category name."
        "\n- Only use 'Other' if it is a genuine, catch-all business category (e.g., 'Other Expenses', 'Miscellaneous', 'Check', 'Payment')."
        "\n- If the expense is not business-related, use 'Personal'."
        "\n- NEVER invent a new category unless you use 'Review' and fill in 'proposed_category_name'."
        "\n- For business expenses, use the most specific category that matches."
        "\n- ALWAYS provide a business_percentage field as described above."
        "\n- Use the payee reasoning above as additional context for your decision."
        "\n\nIMPORTANT: Your response must be a valid JSON object.\n"
    )

    return system_prompt, user_prompt
