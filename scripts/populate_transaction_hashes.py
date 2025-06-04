#!/usr/bin/env python
"""
Standalone script to populate transaction_hash for all existing Transaction rows.
Run with: python scripts/populate_transaction_hashes.py
"""
import os
import sys
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import django
from tqdm import tqdm

print(f"[DEBUG] cwd: {os.getcwd()}")
print(f"[DEBUG] sys.path: {sys.path}")

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ledgerflow.settings")
django.setup()

from profiles.models import Transaction

print("Populating transaction_hash for all Transaction rows...")
qs = Transaction.objects.all()
updated = 0
for tx in tqdm(qs, desc="Processing transactions"):
    if not tx.transaction_hash:
        tx.transaction_hash = Transaction.compute_transaction_hash(
            tx.client_id,
            tx.transaction_date,
            tx.amount,
            tx.description,
            tx.category,
        )
        tx.save(update_fields=["transaction_hash"])
        updated += 1

print(f"Done. Populated hashes for {updated} transactions.")
