import sys
import traceback

# === EDIT THIS SECTION ===
PDF_PATH = "/Users/greg/repos/LedgerFlow_AI/clients/sample2/a90155b4-a660-49fb-b947-6a8b639f3f67.pdf"  # <-- Using the problematic file
from dataextractai.parsers.chase_checking import (
    ChaseCheckingParser,
)  # <-- Using Chase Checking parser

# ========================


def main():
    parser = ChaseCheckingParser()
    try:
        print(f"Running parser on: {PDF_PATH}")
        result = parser.parse_file(PDF_PATH)
        print("\n=== PARSER RESULT ===")
        for i, txn in enumerate(result):
            print(f"--- Transaction {i+1} ---")
            for k, v in txn.items():
                print(f"{k}: {v!r} (type: {type(v)})")
        print("\n=== SUMMARY OF FIELD TYPES ===")
        if result:
            keys = result[0].keys()
            for k in keys:
                types = set(type(txn[k]) for txn in result if k in txn)
                print(f"{k}: {types}")
    except Exception as e:
        print("\n=== ERROR OCCURRED ===")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
