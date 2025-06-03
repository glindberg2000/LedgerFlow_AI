#!/usr/bin/env python
"""
Django Shell Registry Test - Professor Synapse Diagnostic #1
Tests registry state and import identity in Django context
"""

import os
import sys
import django
from pathlib import Path

# Setup Django
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ledgerflow.settings")
django.setup()

print("=== DJANGO SHELL REGISTRY DIAGNOSTIC ===")

# Test 1: Registry state in Django shell
print("\n1. Registry State in Django Shell:")
try:
    from dataextractai.parsers_core.registry import ParserRegistry

    parsers = list(getattr(ParserRegistry, "_parsers", {}).keys())
    print(f"   Parsers found: {parsers}")
    print(f"   Registry has parsers: {len(parsers) > 0}")
except Exception as e:
    print(f"   ERROR: {e}")
    import traceback

    traceback.print_exc()

# Test 2: sys.modules check for dataextractai
print("\n2. sys.modules check for dataextractai:")
try:
    import pprint

    dataextractai_modules = [m for m in sys.modules if m.startswith("dataextractai")]
    print(f"   Found {len(dataextractai_modules)} dataextractai modules:")
    pprint.pprint(dataextractai_modules)
except Exception as e:
    print(f"   ERROR: {e}")

# Test 3: Import identity check
print("\n3. Import Identity Check:")
try:
    import dataextractai.parsers_core.registry as r1
    from importlib import import_module

    r2 = import_module("dataextractai.parsers_core.registry")
    print(f"   r1 is r2: {r1 is r2}")
    print(f"   r1 id: {id(r1)}")
    print(f"   r2 id: {id(r2)}")
    print(f"   r1.ParserRegistry id: {id(r1.ParserRegistry)}")
    print(f"   r2.ParserRegistry id: {id(r2.ParserRegistry)}")
    print(f"   Same ParserRegistry object: {r1.ParserRegistry is r2.ParserRegistry}")
except Exception as e:
    print(f"   ERROR: {e}")
    import traceback

    traceback.print_exc()

# Test 4: Manual autodiscover test
print("\n4. Manual Autodiscover Test:")
try:
    from dataextractai.parsers_core.autodiscover import autodiscover_parsers

    print("   Before autodiscover:")
    before_parsers = list(getattr(ParserRegistry, "_parsers", {}).keys())
    print(f"     Parsers: {before_parsers}")

    print("   Running autodiscover_parsers()...")
    autodiscover_parsers()

    print("   After autodiscover:")
    after_parsers = list(getattr(ParserRegistry, "_parsers", {}).keys())
    print(f"     Parsers: {after_parsers}")
    print(f"     Added: {set(after_parsers) - set(before_parsers)}")
except Exception as e:
    print(f"   ERROR: {e}")
    import traceback

    traceback.print_exc()

# Test 5: Registry object location
print("\n5. Registry Object Analysis:")
try:
    from dataextractai.parsers_core.registry import ParserRegistry

    print(f"   ParserRegistry class: {ParserRegistry}")
    print(f"   ParserRegistry.__module__: {ParserRegistry.__module__}")
    print(
        f"   ParserRegistry._parsers: {getattr(ParserRegistry, '_parsers', 'NOT_FOUND')}"
    )
    print(
        f"   Registry file: {sys.modules['dataextractai.parsers_core.registry'].__file__}"
    )
except Exception as e:
    print(f"   ERROR: {e}")
    import traceback

    traceback.print_exc()

print("\n=== END DIAGNOSTIC ===")
