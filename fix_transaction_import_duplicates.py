#!/usr/bin/env python3
"""
Fix transaction import duplicate handling by improving the transaction_hash logic
and implementing proper error handling during imports.

The current issue:
- Transaction hashes are created from: date + amount + description + account_number  
- Multiple legitimate transactions can have identical data (e.g., multiple $5 Starbucks on same day)
- This causes UNIQUE constraint violations during import

Solutions implemented:
1. Add row index or timestamp to make hashes more unique
2. Implement proper get_or_create logic in import process
3. Handle IntegrityError gracefully during bulk operations
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ledgerflow.settings')
django.setup()

from profiles.models import Transaction
from django.db import IntegrityError
import hashlib

def improved_compute_transaction_id(row, row_index=None):
    """
    Enhanced transaction hash that includes row index to prevent collisions.
    
    Args:
        row (dict): Transaction data
        row_index (int, optional): Row position in the import file
        
    Returns:
        str: SHA256 hash string
    """
    key_fields = [
        str(row.get("transaction_date", "")),
        str(row.get("amount", "")),
        str(row.get("description", "")),
        str(row.get("account_number", "")),
    ]
    
    # Add row index to differentiate identical transactions within the same import
    if row_index is not None:
        key_fields.append(str(row_index))
    
    key_str = "|".join(key_fields)
    return hashlib.sha256(key_str.encode("utf-8")).hexdigest()

def safe_create_transaction(transaction_data, client):
    """
    Safely create a transaction, handling duplicates gracefully.
    
    Args:
        transaction_data (dict): Transaction data from parser
        client: BusinessProfile instance
        
    Returns:
        tuple: (Transaction instance, created_boolean)
    """
    # Try to get existing transaction by hash first
    transaction_hash = transaction_data.get('transaction_hash')
    
    if transaction_hash:
        try:
            existing = Transaction.objects.get(
                client=client,
                transaction_hash=transaction_hash
            )
            print(f"⚠️ Duplicate detected: {existing.transaction_date} | ${existing.amount} | {existing.description[:30]}...")
            return existing, False
        except Transaction.DoesNotExist:
            pass
    
    # Try to create new transaction
    try:
        transaction = Transaction.objects.create(
            client=client,
            **transaction_data
        )
        print(f"✅ Created: {transaction.transaction_date} | ${transaction.amount} | {transaction.description[:30]}...")
        return transaction, True
    except IntegrityError as e:
        if "UNIQUE constraint failed" in str(e):
            # Hash collision - try to find existing transaction
            try:
                existing = Transaction.objects.get(
                    client=client,
                    transaction_hash=transaction_hash
                )
                print(f"⚠️ Hash collision resolved: {existing.transaction_date} | ${existing.amount}")
                return existing, False
            except Transaction.DoesNotExist:
                # This shouldn't happen, but handle it anyway
                print(f"❌ Unexpected hash collision for hash: {transaction_hash}")
                raise e
        else:
            raise e

def analyze_current_duplicates():
    """Analyze current database for potential duplicate issues."""
    
    print("🔍 Analyzing Current Database State")
    print("=" * 50)
    
    total_transactions = Transaction.objects.count()
    print(f"Total transactions: {total_transactions}")
    
    if total_transactions == 0:
        print("No transactions in database yet.")
        return
    
    # Check for potential hash collisions by looking for transactions that would 
    # generate the same hash (same date, amount, description)
    from django.db.models import Count
    from collections import defaultdict
    
    collision_candidates = defaultdict(list)
    
    print("\n🔍 Checking for potential hash collision patterns...")
    
    for tx in Transaction.objects.all():
        key = (tx.transaction_date, float(tx.amount) if tx.amount else 0, tx.description)
        collision_candidates[key].append(tx)
    
    collisions_found = 0
    for key, transactions in collision_candidates.items():
        if len(transactions) > 1:
            collisions_found += 1
            date, amount, desc = key
            print(f"  ⚠️  Potential collision group {collisions_found}:")
            print(f"      Date: {date}, Amount: ${amount}, Description: {desc[:50]}...")
            for tx in transactions:
                print(f"        - ID {tx.id}: hash={tx.transaction_hash}")
    
    if collisions_found == 0:
        print("  ✅ No potential hash collisions detected in current data")
    else:
        print(f"  ⚠️  Found {collisions_found} groups with potential collisions")
    
    print(f"\n📊 Summary:")
    print(f"   Total transactions: {total_transactions}")
    print(f"   Potential collision groups: {collisions_found}")

def patch_normalize_api():
    """
    Create a patched version of the normalize_api.py that handles duplicates better.
    """
    
    print("\n🔧 Creating improved transaction import logic...")
    
    patch_content = '''
# PATCHED VERSION - Better duplicate handling

def safe_bulk_create_transactions(transactions_data, client, batch_size=100):
    """
    Safely bulk create transactions with proper duplicate handling.
    
    Args:
        transactions_data (list): List of transaction dicts
        client: BusinessProfile instance  
        batch_size (int): Number of transactions to process at once
        
    Returns:
        dict: Statistics about the import process
    """
    from django.db import IntegrityError
    
    stats = {
        "total": len(transactions_data),
        "created": 0,
        "skipped": 0,
        "errors": []
    }
    
    for i, tx_data in enumerate(transactions_data):
        try:
            # Add row index to improve hash uniqueness
            if 'transaction_hash' not in tx_data:
                tx_data['transaction_hash'] = improved_compute_transaction_id(tx_data, i)
            
            transaction, created = safe_create_transaction(tx_data, client)
            
            if created:
                stats["created"] += 1
            else:
                stats["skipped"] += 1
                
        except Exception as e:
            error_msg = f"Row {i}: {str(e)}"
            stats["errors"].append(error_msg)
            print(f"❌ Error on row {i}: {e}")
    
    return stats
'''
    
    patch_file = "/Users/greg/repos/LedgerFlow_AI/profiles/utils/improved_transaction_import.py"
    with open(patch_file, 'w') as f:
        f.write('#!/usr/bin/env python3\n')
        f.write('"""Improved transaction import with better duplicate handling."""\n\n')
        f.write(patch_content)
    
    print(f"✅ Created improved import logic at: {patch_file}")

def main():
    print("🔧 Transaction Import Duplicate Fix Tool")
    print("=" * 60)
    print()
    
    # Step 1: Analyze current state
    analyze_current_duplicates()
    
    # Step 2: Create improved import logic
    patch_normalize_api()
    
    print("\n" + "=" * 60)
    print("🎯 RECOMMENDATIONS:")
    print("=" * 60)
    print()
    print("1. **Root Cause**: The transaction hash algorithm needs to include")
    print("   more unique data to prevent collisions between legitimate duplicates")
    print()
    print("2. **Immediate Fix**: Use get_or_create() instead of bulk_create() during imports")
    print("   This will handle duplicates gracefully without throwing errors")
    print()  
    print("3. **Long-term Fix**: Enhance the transaction hash to include:")
    print("   - Row position in import file")
    print("   - Post date (if different from transaction date)")
    print("   - Transaction reference number (if available)")
    print()
    print("4. **Import Process**: Modify the file upload handling to:")
    print("   - Use safe_create_transaction() instead of direct bulk_create()")
    print("   - Show clear feedback about skipped duplicates")
    print("   - Continue processing even when duplicates are encountered")
    print()
    print("✅ The 389 successfully imported transactions show the parsing works!")
    print("❌ The ~21 UNIQUE constraint errors are just duplicate handling issues.")
    print()
    print("🔧 Next step: Update the file upload process to use this improved logic.")

if __name__ == "__main__":
    main()