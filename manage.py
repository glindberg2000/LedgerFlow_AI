#!/usr/bin/env python
import os
import sys

def main():
    if os.getenv("LEDGER_ENV") == "prod" and os.getenv("ALLOW_DANGEROUS") != "1":
        sys.exit("Refusing to run mgmt commands directly in prod container.")
    
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ledgerflow.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)

if __name__ == '__main__':
    main()
