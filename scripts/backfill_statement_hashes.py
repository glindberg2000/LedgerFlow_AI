#!/usr/bin/env python
"""
Backfill statement_hash for all existing StatementFile rows.
Run with: python scripts/backfill_statement_hashes.py
"""
import os
import sys
from pathlib import Path
from tqdm import tqdm

# Ensure project root is on sys.path
PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ledgerflow.settings")
django.setup()

from profiles.models import StatementFile

print("Backfilling statement_hash for all StatementFile rows...")
qs = StatementFile.objects.all()
updated = 0
for sf in tqdm(qs, desc="Processing statement files"):
    if not sf.statement_hash and sf.file:
        sf.statement_hash = sf.compute_statement_hash()
        sf.save(update_fields=["statement_hash"])
        updated += 1

print(f"Done. Populated hashes for {updated} statement files.")
