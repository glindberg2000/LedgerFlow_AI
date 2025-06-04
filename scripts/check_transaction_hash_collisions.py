#!/usr/bin/env python
"""
Check for transaction_hash collisions in the Transaction table.
Outputs a CSV of all collisions (hashes with >1 row) for review.
"""
import os
import sys
from pathlib import Path
import csv

# Ensure project root is on sys.path
PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ledgerflow.settings")
django.setup()

from profiles.models import Transaction
from collections import defaultdict

hash_map = defaultdict(list)

for tx in Transaction.objects.all():
    h = Transaction.compute_transaction_hash(
        tx.client_id,
        tx.transaction_date,
        tx.amount,
        tx.description,
        tx.category,
    )
    hash_map[h].append(tx)

collisions = {h: txs for h, txs in hash_map.items() if len(txs) > 1}

print(f"Found {len(collisions)} hash collisions.")

with open("transaction_hash_collisions.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(
        [
            "hash",
            "client_id",
            "transaction_date",
            "amount",
            "description",
            "category",
            "transaction_id",
        ]
    )
    for h, txs in collisions.items():
        for tx in txs:
            writer.writerow(
                [
                    h,
                    tx.client_id,
                    tx.transaction_date,
                    tx.amount,
                    tx.description,
                    tx.category,
                    tx.id,
                ]
            )

print("Collision details written to transaction_hash_collisions.csv")
