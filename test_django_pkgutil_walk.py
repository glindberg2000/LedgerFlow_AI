#!/usr/bin/env python
"""
Django pkgutil.walk_packages() and import diagnostic for dataextractai.parsers
"""
import os
import sys
from pathlib import Path
import pkgutil
import importlib
import pprint

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ledgerflow.settings")
import django

django.setup()

print("=== dataextractai.parsers pkgutil/import diagnostic ===\n")

import dataextractai.parsers as P

# 1. What directories constitute the namespace?
print("parsers __path__:", list(P.__path__))

# 2. Files physically present
print("\nFiles physically present:")
for root in P.__path__:
    for p in Path(root).glob("*.py"):
        print(" •", p.name)

# 3. Names pkgutil will walk
print("\nNames pkgutil will walk:")
walked = []
for _, modname, _ in pkgutil.walk_packages(P.__path__, P.__name__ + "."):
    walked.append(modname)
    try:
        importlib.import_module(modname)
        print("   ✓ imported", modname)
    except Exception as exc:
        print("   ✖", modname, "→", repr(exc))

# 4. After walk, registry
print("\nAfter walk, registry:")
from dataextractai.parsers_core.registry import ParserRegistry

print(ParserRegistry.list_parsers())

print("\n=== END DIAGNOSTIC ===")
