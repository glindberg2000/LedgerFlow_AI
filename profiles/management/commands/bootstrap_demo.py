from django.core.management.base import BaseCommand
from django.conf import settings
import os
import json
from pathlib import Path
from django.db import transaction
from profiles.models import (
    BusinessProfile,
    IRSWorksheet,
    IRSExpenseCategory,
    BusinessExpenseCategory,
    Agent,
    LLMConfig,
    Tool,
)
from django.core.files import File
from profiles.models import StatementFile, Transaction
import shutil
import csv
import datetime
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = "Bootstrap the ACME Corp demo environment. Use --force to wipe all data and reload demo config."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Wipe all data and reload demo config (DANGEROUS)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be done, but make no changes",
        )
        parser.add_argument(
            "--quickstart",
            "--yes",
            action="store_true",
            help="Zero-friction: skip all prompts, use defaults, and auto-create SQLite DB if needed.",
        )
        parser.add_argument(
            "--sqlite",
            action="store_true",
            help="Force use of a new SQLite DB for demo onboarding, regardless of current settings.",
        )
        parser.add_argument(
            "--i-understand-danger",
            action="store_true",
            help="(DANGEROUS) Allow destructive actions on non-SQLite DBs. Use only if you are 100% sure.",
        )

    def handle(self, *args, **options):
        # Ensure all model imports are available in this scope
        from profiles.models import (
            BusinessProfile,
            IRSWorksheet,
            IRSExpenseCategory,
            BusinessExpenseCategory,
        )

        force = options["force"]
        dry_run = options["dry_run"]
        quickstart = options["quickstart"]
        use_sqlite = options["sqlite"]
        override_danger = options["i_understand_danger"]

        # Print which .env file is loaded (if using python-dotenv or os.environ)
        env_file = (
            os.environ.get("DOTENV_FILE")
            or os.environ.get("ENV_FILE")
            or ".env (default or not shown)"
        )
        self.stdout.write(self.style.NOTICE(f"Loaded environment file: {env_file}"))

        db_settings = settings.DATABASES.get("default", {})
        db_engine = db_settings.get("ENGINE", "")
        db_name = db_settings.get("NAME", "")
        is_sqlite = db_engine == "django.db.backends.sqlite3"
        db_url = (
            db_name
            if is_sqlite
            else f"{db_engine}://{db_settings.get('USER','')}@{db_settings.get('HOST','')}:{db_settings.get('PORT','')}/{db_name}"
        )

        # Failsafe: If --quickstart or --sqlite, always use a new SQLite DB in project root
        if quickstart or use_sqlite:
            import pathlib

            sqlite_path = Path(settings.BASE_DIR) / "demo_bootstrap.sqlite3"
            self.stdout.write(
                self.style.WARNING(
                    f"[FAILSAFE] For quickstart/onboarding, using new SQLite DB: {sqlite_path}"
                )
            )
            # Patch settings at runtime
            settings.DATABASES["default"]["ENGINE"] = "django.db.backends.sqlite3"
            settings.DATABASES["default"]["NAME"] = str(sqlite_path)
            db_engine = "django.db.backends.sqlite3"
            db_name = str(sqlite_path)
            is_sqlite = True
            db_url = db_name
            # Remove any existing file for a clean start
            if sqlite_path.exists():
                self.stdout.write(
                    self.style.WARNING(
                        f"[FAILSAFE] SQLite DB already exists at {sqlite_path}. If you want a clean start, please delete this file manually and rerun 'python manage.py migrate' before bootstrapping."
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(f"Created new SQLite DB for demo: {sqlite_path}")
                )
            # Run migrate to initialize schema
            from django.core.management import call_command

            call_command("migrate", interactive=False, verbosity=0)
        else:
            self.stdout.write(self.style.WARNING(f"Target database: {db_url}"))
            if (force or quickstart) and not is_sqlite:
                if not override_danger:
                    self.stdout.write(
                        self.style.ERROR(
                            "[FAILSAFE] Refusing to wipe or modify a non-SQLite database in quickstart/force mode. Use --i-understand-danger ONLY if you are 100% sure. Aborting."
                        )
                    )
                    return
                else:
                    self.stdout.write(
                        self.style.ERROR(
                            "[DANGER] You have overridden the failsafe. Proceeding with destructive action on a non-SQLite DB!"
                        )
                    )

        if dry_run:
            self.stdout.write(
                self.style.WARNING("*** DRY RUN: No changes will be made. ***")
            )
            if force:
                self.stdout.write(
                    self.style.WARNING("Would wipe all data and reload demo config.")
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        "Would bootstrap demo ONLY IF database is empty."
                    )
                )
            return

        if force:
            if not quickstart:
                self.stdout.write(
                    self.style.WARNING(
                        "*** DANGER: This will WIPE ALL DATA and reload the ACME Corp demo! ***"
                    )
                )
                self.stdout.write(
                    self.style.WARNING(
                        f"You are about to wipe the following database: {db_url}"
                    )
                )
                confirm = input(f"Type the database name ({db_name}) to confirm: ")
                if confirm != db_name:
                    self.stdout.write(
                        self.style.ERROR("Aborted: Database name did not match.")
                    )
                    return
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        "Quickstart: Skipping DB confirmation and proceeding to flush DB."
                    )
                )
            self.stdout.write(self.style.WARNING("Wiping all data..."))
            from django.core.management import call_command

            call_command("flush", interactive=False)
            self.stdout.write(self.style.SUCCESS("Data wiped."))
        else:
            self.stdout.write(
                self.style.WARNING("Bootstrapping demo ONLY IF database is empty...")
            )
            # Check if DB is empty (no StatementFile, Transaction, or BusinessProfile)
            from profiles.models import StatementFile, Transaction, BusinessProfile

            if (
                StatementFile.objects.exists()
                or Transaction.objects.exists()
                or BusinessProfile.objects.exists()
            ):
                self.stdout.write(
                    self.style.ERROR("Database is not empty. Aborting demo bootstrap.")
                )
                return
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        "Database is empty. Proceeding with demo bootstrap."
                    )
                )
        # TODO: Load config files, create demo data, run batch upload
        bootstrap_dir = Path(os.path.dirname(__file__)) / "../../bootstrap"
        bootstrap_dir = bootstrap_dir.resolve()
        created = {}

        def filter_fields(data, model):
            valid_fields = {
                f.name
                for f in model._meta.get_fields()
                if f.concrete and not f.auto_created
            }
            filtered = {k: v for k, v in data.items() if k in valid_fields}
            ignored = {k: v for k, v in data.items() if k not in valid_fields}
            return filtered, ignored

        with transaction.atomic():
            # Strict validation for all demo data files
            def strict_load_json(path, expect_type=dict, label=None):
                with open(path) as f:
                    data = json.load(f)
                if isinstance(data, list):
                    for i, entry in enumerate(data):
                        if not isinstance(entry, expect_type):
                            raise ValueError(
                                f"{label or path}: Entry {i} is not a {expect_type.__name__}: {entry}"
                            )
                elif not isinstance(data, expect_type):
                    raise ValueError(
                        f"{label or path}: Top-level object is not a {expect_type.__name__}: {data}"
                    )
                return data

            # Use strict loader for all demo files
            bp_data = strict_load_json(
                bootstrap_dir / "business_profile.json", dict, "business_profile.json"
            )
            worksheets = strict_load_json(
                bootstrap_dir / "worksheets.json", dict, "worksheets.json"
            )
            categories_6a = strict_load_json(
                bootstrap_dir / "categories_6A.json", dict, "categories_6A.json"
            )
            bec_data = strict_load_json(
                bootstrap_dir / "business_expense_categories.json",
                dict,
                "business_expense_categories.json",
            )

            # Map 'address' to 'location' if present
            if "address" in bp_data:
                bp_data["location"] = bp_data.pop("address")
            # Ensure company_name is always set
            if "company_name" not in bp_data or not bp_data["company_name"]:
                bp_data["company_name"] = "ACME Corp"
            bp_data_filtered, bp_ignored = filter_fields(bp_data, BusinessProfile)
            if bp_ignored:
                self.stdout.write(
                    self.style.WARNING(
                        f"Ignored fields in business_profile.json: {list(bp_ignored.keys())}"
                    )
                )
            bp_obj, _ = BusinessProfile.objects.get_or_create(**bp_data_filtered)
            bp_obj.refresh_from_db()
            if not hasattr(bp_obj, "client_id") or not bp_obj.client_id:
                raise ValueError(
                    f"BusinessProfile object has no client_id after save: {bp_obj}"
                )
            created["BusinessProfile"] = getattr(bp_obj, "client_id", str(bp_obj))

            # Load worksheets.json (create IRSWorksheet)
            ws_objs = []
            for ws in worksheets if isinstance(worksheets, list) else [worksheets]:
                ws_filtered, ws_ignored = filter_fields(ws, IRSWorksheet)
                if ws_ignored:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Ignored fields in worksheets.json: {list(ws_ignored.keys())}"
                        )
                    )
                ws_obj, _ = IRSWorksheet.objects.get_or_create(**ws_filtered)
                ws_objs.append(ws_obj.name)
            created["IRSWorksheets"] = ws_objs

            # Load categories_6A.json (create IRSExpenseCategory linked to worksheet)
            cat6a_objs = []
            for cat in categories_6a:
                if not isinstance(cat, dict):
                    self.stdout.write(
                        self.style.ERROR(f"Invalid category entry (not a dict): {cat}")
                    )
                    continue
                worksheet_name = cat.pop("worksheet", "6A")
                worksheet = IRSWorksheet.objects.get(name=worksheet_name)
                cat_filtered, cat_ignored = filter_fields(cat, IRSExpenseCategory)
                if cat_ignored:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Ignored fields in categories_6A.json: {list(cat_ignored.keys())}"
                        )
                    )
                obj, _ = IRSExpenseCategory.objects.get_or_create(
                    worksheet=worksheet, **cat_filtered
                )
                cat6a_objs.append(obj.name)
            created["IRS 6A Categories"] = cat6a_objs

            # Load business_expense_categories.json (create BusinessExpenseCategory linked to business and worksheet/category)
            bec_objs = []
            current_year = datetime.datetime.now().year
            seen_bec = set()
            for cat in bec_data if isinstance(bec_data, list) else [bec_data]:
                # Map 'name' to 'category_name' for model
                if "name" in cat:
                    cat["category_name"] = cat.pop("name")
                if "category_name" not in cat or not cat["category_name"]:
                    raise ValueError(
                        f"Missing 'category_name' in business_expense_categories.json entry: {cat}"
                    )
                if "tax_year" not in cat:
                    cat["tax_year"] = current_year
                bec_name = cat.get("category_name")
                key = (bp_obj.client_id, bec_name)
                if key in seen_bec:
                    raise ValueError(
                        f"Duplicate BusinessExpenseCategory for business_id={bp_obj.client_id}, name={bec_name} in JSON. Aborting."
                    )
                seen_bec.add(key)
                worksheet_name = cat.pop("worksheet", "6A")
                worksheet = IRSWorksheet.objects.get(name=worksheet_name)
                parent_category_name = cat.pop("parent_category", None)
                parent_category = None
                if parent_category_name:
                    try:
                        parent_category = IRSExpenseCategory.objects.get(
                            worksheet=worksheet, name=parent_category_name
                        )
                    except IRSExpenseCategory.DoesNotExist:
                        parent_category = None
                bec_filtered, bec_ignored = filter_fields(cat, BusinessExpenseCategory)
                if bec_ignored:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Ignored fields in business_expense_categories.json: {list(bec_ignored.keys())}"
                        )
                    )
                # DEBUG: Print all keys/values before creation
                self.stdout.write(
                    self.style.NOTICE(
                        f"Creating BusinessExpenseCategory: business={bp_obj.client_id}, worksheet={worksheet}, parent_category={parent_category}, data={bec_filtered}"
                    )
                )
                try:
                    obj, _ = BusinessExpenseCategory.objects.get_or_create(
                        business=bp_obj,
                        worksheet=worksheet,
                        parent_category=parent_category,
                        **bec_filtered,
                    )
                    bec_objs.append(obj.category_name)
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f"Error creating BusinessExpenseCategory: {e}\n  business={bp_obj.client_id}, worksheet={worksheet}, parent_category={parent_category}, data={bec_filtered}"
                        )
                    )
                    raise
            created["Business Expense Categories"] = bec_objs

            # Load agents.json
            agents_path = bootstrap_dir / "agents.json"
            with open(agents_path) as f:
                agents_data = json.load(f)
            agent_objs = []
            # Ensure searxng_search tool exists
            searxng_tool, _ = Tool.objects.get_or_create(
                name="searxng_search",
                defaults={
                    "description": "Search the web using SearXNG",
                    "module_path": "tools.search_tool.searxng_search",
                },
            )
            for agent in agents_data:
                name = agent.get("name")
                purpose = agent.get("description")
                system_prompt = agent.get("system_prompt", "")
                user_prompt = agent.get("user_prompt", "")
                prompt = system_prompt.strip() + "\n\n" + user_prompt.strip()
                llm_model = agent.get("llm_model")
                if not (name and purpose and prompt and llm_model):
                    raise ValueError(f"Agent missing required fields: {agent}")
                llm, _ = LLMConfig.objects.get_or_create(
                    model=llm_model, defaults={"provider": "openai"}
                )
                agent_obj, _ = Agent.objects.get_or_create(
                    name=name,
                    defaults={
                        "purpose": purpose,
                        "prompt": prompt,
                        "llm": llm,
                    },
                )
                # Update fields if agent existed but was missing info
                updated = False
                if agent_obj.purpose != purpose:
                    agent_obj.purpose = purpose
                    updated = True
                if agent_obj.prompt != prompt:
                    agent_obj.prompt = prompt
                    updated = True
                if agent_obj.llm != llm:
                    agent_obj.llm = llm
                    updated = True
                if updated:
                    agent_obj.save()
                # Attach searxng_search tool if not already
                if not agent_obj.tools.filter(pk=searxng_tool.pk).exists():
                    agent_obj.tools.add(searxng_tool)
                agent_objs.append(agent_obj.name)
            created["Agents"] = agent_objs

            # Load field_mapping.json (for future use)
            fm_path = bootstrap_dir / "field_mapping.json"
            with open(fm_path) as f:
                field_mapping = json.load(f)
            created["Field Mapping"] = "Loaded"

        self.stdout.write(self.style.SUCCESS("Demo config loaded and objects created:"))
        for k, v in created.items():
            self.stdout.write(f"  {k}: {v}")
        self.stdout.write(self.style.SUCCESS("Demo bootstrapping complete!"))

        # Ensure sample_transactions.csv exists by copying from .example if needed
        bootstrap_dir = Path(os.path.dirname(__file__)) / "../../bootstrap"
        bootstrap_dir = bootstrap_dir.resolve()
        csv_path = os.path.join(bootstrap_dir, "sample_transactions.csv")
        csv_example_path = os.path.join(
            bootstrap_dir, "sample_transactions.csv.example"
        )
        if not os.path.exists(csv_path) and os.path.exists(csv_example_path):
            shutil.copy(csv_example_path, csv_path)
            self.stdout.write(
                self.style.WARNING(
                    f"Copied sample_transactions.csv.example to sample_transactions.csv for demo import."
                )
            )

        # After config loading, import sample_transactions.csv as a StatementFile and process it
        sample_csv_path = bootstrap_dir / "sample_transactions.csv"
        if not sample_csv_path.exists():
            self.stdout.write(
                self.style.ERROR(
                    "sample_transactions.csv not found in bootstrap directory. Skipping import."
                )
            )
        else:
            # Copy to media directory and create StatementFile
            media_dir = Path(settings.MEDIA_ROOT) / "bootstrap_demo"
            media_dir.mkdir(parents=True, exist_ok=True)
            dest_path = media_dir / sample_csv_path.name
            shutil.copy(sample_csv_path, dest_path)
            with open(dest_path, "rb") as f:
                django_file = File(f, name=sample_csv_path.name)
                statement_file = StatementFile.objects.create(
                    client=bp_obj,
                    file=django_file,
                    file_type="csv",
                    original_filename=sample_csv_path.name,
                    uploaded_by=None,
                    status="uploaded",
                )
            self.stdout.write(
                self.style.SUCCESS(
                    f"StatementFile created for demo CSV: {statement_file}"
                )
            )
            # Minimal CSV import logic: create Transaction objects for each row
            tx_count = 0
            error_count = 0
            with open(dest_path, "r", newline="") as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    try:
                        # Map CSV columns to model fields
                        transaction_date = row.get("Transaction Date")
                        if transaction_date:
                            # Parse to YYYY-MM-DD
                            try:
                                transaction_date = str(
                                    datetime.datetime.strptime(
                                        transaction_date.strip(), "%Y-%m-%d"
                                    ).date()
                                )
                            except Exception:
                                try:
                                    transaction_date = str(
                                        datetime.datetime.strptime(
                                            transaction_date.strip(), "%m/%d/%Y"
                                        ).date()
                                    )
                                except Exception:
                                    pass
                        description = row.get("Description")
                        category = row.get("Category")
                        debit = row.get("Debit")
                        credit = row.get("Credit")
                        amount = None
                        if debit and debit.strip():
                            amount = float(debit.replace(",", ""))
                        elif credit and credit.strip():
                            amount = -float(credit.replace(",", ""))
                        if not transaction_date or amount is None:
                            raise ValueError(
                                f"Missing required field: transaction_date={transaction_date}, amount={amount}"
                            )
                        tx = Transaction.objects.create(
                            client=bp_obj,
                            transaction_date=transaction_date,
                            amount=amount,
                            description=description,
                            category=category or "",
                            file_path=dest_path.as_posix(),
                            source="bootstrap_demo",
                            transaction_type=row.get("transaction_type", ""),
                            normalized_amount=None,
                            statement_file=statement_file,
                            parser_name="bootstrap_demo",
                            classification_method="None",
                            payee_extraction_method="None",
                        )
                        tx_count += 1
                    except Exception as e:
                        error_count += 1
                        self.stdout.write(
                            self.style.ERROR(f"Error importing transaction: {e}")
                        )
            self.stdout.write(
                self.style.SUCCESS(f"Imported {tx_count} transactions from demo CSV.")
            )
            if error_count:
                self.stdout.write(
                    self.style.ERROR(f"Encountered {error_count} errors during import.")
                )

        # Create a default superuser for demo onboarding
        User = get_user_model()
        demo_username = "demo"
        demo_password = "demo1234"
        demo_email = "demo@example.com"
        if not User.objects.filter(username=demo_username).exists():
            User.objects.create_superuser(demo_username, demo_email, demo_password)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Demo superuser created: username='{demo_username}', password='{demo_password}'"
                )
            )
            self.stdout.write(
                self.style.WARNING(
                    "[SECURITY] Change this password immediately in any real deployment!"
                )
            )
        else:
            self.stdout.write(
                self.style.NOTICE(
                    f"Demo superuser already exists: username='{demo_username}'"
                )
            )
