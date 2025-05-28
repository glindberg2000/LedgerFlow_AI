import pdfplumber
import re

# List of known banks for detection (expand as needed)
KNOWN_BANKS = [
    "Chase",
    "Bank of America",
    "Wells Fargo",
    "First Republic",
    "Amazon",
    "Citi",
    "Capital One",
    "American Express",
    "US Bank",
    "PNC",
    "TD Bank",
    "HSBC",
    "Barclays",
    "Discover",
    "Synchrony",
    "Ally",
    "Charles Schwab",
    "Fidelity",
    "SoFi",
    "Robinhood",
    "PayPal",
    "Venmo",
    "Apple Card",
    "Goldman Sachs",
    "Comenity",
    "Santander",
    "Regions",
    "KeyBank",
    "SunTrust",
    "BB&T",
    "M&T",
    "Fifth Third",
    "BMO",
    "Huntington",
    "Citizens",
    "Navy Federal",
    "USAA",
    "Truist",
    "Silicon Valley Bank",
    "Signature Bank",
    "SVB",
    "Morgan Stanley",
    "JPMorgan",
    "J.P. Morgan",
    "JPMorgan Chase",
    "Chase Bank",
    "Wells Fargo Bank",
    "BofA",
    "BOA",
    "Amex",
    "American Express",
    "Discover Bank",
    "Synchrony Bank",
    "Ally Bank",
    "Charles Schwab Bank",
    "Fidelity Bank",
    "SoFi Bank",
    "Robinhood Bank",
    "PayPal Bank",
    "Venmo Bank",
    "Apple Bank",
    "Goldman Sachs Bank",
    "Comenity Bank",
    "Santander Bank",
    "Regions Bank",
    "KeyBank",
    "SunTrust Bank",
    "BB&T Bank",
    "M&T Bank",
    "Fifth Third Bank",
    "BMO Bank",
    "Huntington Bank",
    "Citizens Bank",
    "Navy Federal Credit Union",
    "USAA Bank",
    "Truist Bank",
    "Silicon Valley Bank",
    "Signature Bank",
    "SVB Bank",
    "Morgan Stanley Bank",
    "JPMorgan Bank",
    "J.P. Morgan Bank",
]

# Regex patterns for metadata
ACCOUNT_NUMBER_PATTERNS = [
    r"Account Number[:\s]*([\dXx\-\*]+)",
    r"Acct\.?\s*#?[:\s]*([\dXx\-\*]+)",
    r"Card Number[:\s]*([\dXx\-\*]+)",
]
STATEMENT_PERIOD_PATTERNS = [
    r"Statement Period[:\s]*([\w\-/]+)\s*-\s*([\w\-/]+)",
    r"Period[:\s]*([\w\-/]+)\s*-\s*([\w\-/]+)",
    r"From[:\s]*([\w\-/]+)\s*to\s*([\w\-/]+)",
]
DATE_PATTERNS = [
    r"Statement Date[:\s]*([\w\-/]+)",
    r"Date[:\s]*([\w\-/]+)",
]
TYPE_KEYWORDS = [
    "Checking",
    "Credit Card",
    "Savings",
    "Money Market",
    "Business",
    "Personal",
    "Platinum",
    "Rewards",
    "Student",
    "Premier",
    "Advantage",
    "Preferred",
    "Cash",
    "Visa",
    "Mastercard",
    "Debit",
    "Credit",
    "Account",
    "Card",
]


def extract_pdf_metadata(pdf_path):
    """
    Extracts metadata from the first page of a PDF bank/credit card statement.
    Returns a dict: {bank, account_number, statement_period, statement_date, type}
    """
    result = {
        "bank": None,
        "account_number": None,
        "statement_period": None,
        "statement_date": None,
        "type": None,
    }
    try:
        with pdfplumber.open(pdf_path) as pdf:
            if not pdf.pages:
                return result
            first_page = pdf.pages[0]
            text = first_page.extract_text() or ""
            lines = [line.strip() for line in text.split("\n") if line.strip()]
            # Bank detection
            for bank in KNOWN_BANKS:
                for line in lines[:5]:  # Only check first few lines
                    if bank.lower() in line.lower():
                        result["bank"] = bank
                        break
                if result["bank"]:
                    break
            if not result["bank"] and lines:
                result["bank"] = lines[0]  # Fallback: first line
            # Account number
            for pat in ACCOUNT_NUMBER_PATTERNS:
                m = re.search(pat, text, re.IGNORECASE)
                if m:
                    result["account_number"] = m.group(1)
                    break
            # Statement period
            for pat in STATEMENT_PERIOD_PATTERNS:
                m = re.search(pat, text, re.IGNORECASE)
                if m:
                    result["statement_period"] = (m.group(1), m.group(2))
                    break
            # Statement date
            for pat in DATE_PATTERNS:
                m = re.search(pat, text, re.IGNORECASE)
                if m:
                    result["statement_date"] = m.group(1)
                    break
            # Type detection
            for t in TYPE_KEYWORDS:
                if re.search(rf"\b{re.escape(t)}\b", text, re.IGNORECASE):
                    result["type"] = t
                    break
    except Exception as e:
        result["error"] = str(e)
    return result


# For extensibility: if all fields are None or confidence is low, fallback to vision agent
