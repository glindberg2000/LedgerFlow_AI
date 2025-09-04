from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction, IntegrityError
from profiles.models import BusinessProfile, TaxYear
import json
from pathlib import Path
from django.conf import settings


class Command(BaseCommand):
    help = "Simple bootstrap: creates demo user and basic data in current active database"

    def add_arguments(self, parser):
        parser.add_argument(
            "--fresh",
            action="store_true", 
            help="Create fresh demo data (skips if data exists)"
        )
        parser.add_argument(
            "--wipe",
            action="store_true",
            help="⚠️ DANGER: Wipe existing database and create fresh (requires confirmation)"
        )
        parser.add_argument(
            "--new-db",
            type=str,
            help="Create new database file with this name (e.g., --new-db=myproject.sqlite3)"
        )

    def handle(self, *args, **options):
        fresh = options["fresh"]
        wipe = options["wipe"]
        new_db = options["new_db"]
        
        self.stdout.write(self.style.NOTICE("🚀 Simple Bootstrap Starting..."))
        
        # Handle new database creation
        if new_db:
            return self.create_new_database(new_db)
        
        # Show current database
        db_settings = settings.DATABASES.get("default", {})
        db_name = db_settings.get("NAME", "")
        is_sqlite = db_settings.get("ENGINE") == "django.db.backends.sqlite3"
        
        if not is_sqlite:
            self.stdout.write(self.style.ERROR("❌ This bootstrap only works with SQLite databases"))
            return
        
        self.stdout.write(self.style.SUCCESS(f"📊 Using database: {db_name}"))
        
        # Handle database wiping with confirmation
        if wipe:
            return self.wipe_and_create(db_name)
        
        # Run the bootstrap process  
        self.run_bootstrap_process(fresh=fresh)

    def create_demo_user(self):
        User = get_user_model()
        demo_username = "demo"
        demo_password = "demo1234"
        demo_email = "demo@example.com"

        if User.objects.filter(username=demo_username).exists():
            self.stdout.write(
                self.style.NOTICE(f"👤 Demo user '{demo_username}' already exists")
            )
        else:
            User.objects.create_superuser(demo_username, demo_email, demo_password)
            self.stdout.write(
                self.style.SUCCESS(f"✅ Created demo user: {demo_username}/demo1234")
            )

    def create_demo_business(self):
        # Create ACME Corp demo business
        business, created = BusinessProfile.objects.get_or_create(
            client_id="acme_corp_demo",
            defaults={
                "company_name": "ACME Corp",
                "business_type": "Corporation", 
                "business_description": "Demo company for testing and development",
                "location": "San Francisco, CA",
                "ai_generated_profile": "{}",
            }
        )
        
        if created:
            self.stdout.write(
                self.style.SUCCESS("✅ Created ACME Corp demo business profile")
            )
        else:
            self.stdout.write(
                self.style.NOTICE("👔 ACME Corp business profile already exists")
            )

    def create_tax_years(self):
        # Get the demo business profile
        try:
            business = BusinessProfile.objects.get(client_id="acme_corp_demo")
        except BusinessProfile.DoesNotExist:
            self.stdout.write(
                self.style.WARNING("⚠️  No business profile found, skipping tax years")
            )
            return

        # Create basic tax years for the business
        for year in ["2024", "2025"]:
            tax_year, created = TaxYear.objects.get_or_create(
                business_profile=business,
                year=year,
                defaults={
                    "status": "not_started",
                }
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f"📅 Created tax year {year} for {business.company_name}")
                )
            else:
                self.stdout.write(
                    self.style.NOTICE(f"📅 Tax year {year} already exists for {business.company_name}")
                )

    def create_new_database(self, db_filename):
        """Create a completely new database file"""
        import os
        from pathlib import Path
        from django.db import connections
        from django.core.management import call_command
        
        new_db_path = Path(db_filename)
        
        if new_db_path.exists():
            self.stdout.write(self.style.ERROR(f"❌ Database file already exists: {db_filename}"))
            self.stdout.write(self.style.NOTICE("Use --wipe to overwrite or choose a different name"))
            return
        
        # Temporarily modify Django settings to use new database
        original_db_name = settings.DATABASES["default"]["NAME"]
        settings.DATABASES["default"]["NAME"] = str(new_db_path.absolute())
        
        self.stdout.write(self.style.SUCCESS(f"🆕 Creating new database: {db_filename}"))
        
        # Close any existing connections to force reconnection with new database
        connections.close_all()
        
        # Run the bootstrap process (which includes migrations)
        self.run_bootstrap_process(fresh=True)
        
        # Ensure file exists and is readable
        if new_db_path.exists():
            self.stdout.write(self.style.SUCCESS(f"📁 Database file size: {new_db_path.stat().st_size} bytes"))
        else:
            self.stdout.write(self.style.ERROR(f"❌ Database file was not created: {new_db_path.absolute()}"))
        
        # Restore original database setting
        settings.DATABASES["default"]["NAME"] = original_db_name
        connections.close_all()  # Close connections to new database
        
        self.stdout.write(self.style.SUCCESS(f"✅ New database created: {db_filename}"))
        self.stdout.write(self.style.WARNING(f"💡 Update your .env.dev to use: DATABASE_URL=sqlite:///{new_db_path.absolute()}"))

    def wipe_and_create(self, db_name):
        """Wipe existing database and create fresh"""
        import os
        from pathlib import Path
        
        db_path = Path(db_name)
        
        # Show warning and require confirmation
        self.stdout.write(self.style.ERROR("⚠️  DANGER: About to DELETE ALL DATA"))
        self.stdout.write(self.style.ERROR(f"⚠️  Database file: {db_path.absolute()}"))
        
        if db_path.exists():
            # Check if database has real data
            try:
                User = get_user_model()
                from profiles.models import BusinessProfile
                user_count = User.objects.count()
                business_count = BusinessProfile.objects.count()
                
                self.stdout.write(self.style.WARNING(f"📊 Current data: {user_count} users, {business_count} businesses"))
            except Exception:
                self.stdout.write(self.style.WARNING("📊 Cannot read existing data (migration needed?)"))
        
        confirmation = input(f"Type 'DELETE {db_name}' to confirm: ")
        if confirmation != f"DELETE {db_name}":
            self.stdout.write(self.style.NOTICE("❌ Cancelled - no changes made"))
            return
        
        # Create backup before deletion
        self.create_backup_if_exists(db_path)
        
        # Delete and recreate
        if db_path.exists():
            db_path.unlink()
        
        self.stdout.write(self.style.SUCCESS(f"🗑️  Deleted: {db_name}"))
        self.run_bootstrap_process(fresh=True)

    def create_backup_if_exists(self, db_path):
        """Create backup of existing database"""
        if db_path.exists():
            import shutil
            from datetime import datetime
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{db_path.stem}_backup_{timestamp}.sqlite3"
            backup_path = db_path.parent / backup_name
            
            shutil.copy2(db_path, backup_path)
            self.stdout.write(self.style.SUCCESS(f"💾 Backup created: {backup_name}"))

    def run_bootstrap_process(self, fresh=False):
        """Run the actual bootstrap process"""
        # Ensure migrations are run
        from django.core.management import call_command
        self.stdout.write(self.style.NOTICE("🔄 Running migrations..."))
        call_command("migrate", verbosity=0)
        
        with transaction.atomic():
            # 1. Create demo superuser
            self.create_demo_user()
            
            # 2. Create demo business profile
            if fresh or not BusinessProfile.objects.exists():
                self.create_demo_business()
                
            # 3. Create basic tax years
            self.create_tax_years()
        
        self.stdout.write(self.style.SUCCESS("✅ Bootstrap Complete!"))
        self.stdout.write(self.style.SUCCESS("🌐 Access: http://localhost:9002/admin/"))
        self.stdout.write(self.style.SUCCESS("👤 Login: demo/demo1234 or admin/admin123"))