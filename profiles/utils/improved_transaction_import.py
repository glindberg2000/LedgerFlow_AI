#!/usr/bin/env python3
"""Improved transaction import with better duplicate handling."""


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
