#!/usr/bin/env python3
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
import re

# --- CONFIG ---
BASE_DIR = Path("/Users/greg/repos/LedgerFlow_AI")
TEMPLATES_DIR = BASE_DIR / "templates"
BACKUP_TEMPLATES = BASE_DIR / "templates_backup"
ISOLATED_TEMPLATES = BASE_DIR / "templates_isolated"
SETTINGS_FILES = [
    BASE_DIR / "ledgerflow" / "settings.py",
    BASE_DIR / "core" / "settings.py",
]
SETTINGS_BACKUPS = [p.with_suffix(".py.bak") for p in SETTINGS_FILES]
LOG_FILE = BASE_DIR / "template_isolation_results.log"
ADMIN_URL = "http://localhost:8001/admin/"


# --- LOGGING ---
def log(msg):
    print(msg)
    with open(LOG_FILE, "a") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {msg}\n")


# --- BACKUP/RESTORE ---
def backup_templates():
    if BACKUP_TEMPLATES.exists():
        shutil.rmtree(BACKUP_TEMPLATES)
    if TEMPLATES_DIR.exists():
        shutil.copytree(TEMPLATES_DIR, BACKUP_TEMPLATES)
        log(f"Templates backed up to {BACKUP_TEMPLATES}")
    else:
        log("No templates directory to backup.")


def restore_templates():
    if BACKUP_TEMPLATES.exists():
        if TEMPLATES_DIR.exists():
            shutil.rmtree(TEMPLATES_DIR)
        shutil.copytree(BACKUP_TEMPLATES, TEMPLATES_DIR)
        log("Templates restored from backup.")
    else:
        log("No backup templates to restore.")


def backup_settings():
    for src, dst in zip(SETTINGS_FILES, SETTINGS_BACKUPS):
        if src.exists():
            shutil.copy2(src, dst)
            log(f"Backed up {src} to {dst}")


def restore_settings():
    for src, dst in zip(SETTINGS_BACKUPS, SETTINGS_FILES):
        if src.exists():
            shutil.copy2(src, dst)
            log(f"Restored {dst} from {src}")


# --- TEMPLATE ISOLATION ---
def isolate_templates():
    if ISOLATED_TEMPLATES.exists():
        shutil.rmtree(ISOLATED_TEMPLATES)
    if TEMPLATES_DIR.exists():
        shutil.copytree(TEMPLATES_DIR, ISOLATED_TEMPLATES)
        for item in TEMPLATES_DIR.iterdir():
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)
        log(f"Templates isolated to {ISOLATED_TEMPLATES}")
    else:
        log("No templates directory to isolate.")


def restore_template(template_path):
    src = ISOLATED_TEMPLATES / template_path
    dst = TEMPLATES_DIR / template_path
    if src.is_file():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        log(f"Restored template file: {template_path}")
    elif src.is_dir():
        shutil.copytree(src, dst)
        log(f"Restored template directory: {template_path}")


# --- SETTINGS MODIFICATION ---
def comment_out_custom_apps(settings_path):
    if not settings_path.exists():
        return
    with open(settings_path, "r") as f:
        content = f.read()
    pattern = r"INSTALLED_APPS\s*=\s*\[(.*?)\]"  # non-greedy
    match = re.search(pattern, content, re.DOTALL)
    if not match:
        log(f"Could not find INSTALLED_APPS in {settings_path}")
        return
    apps_block = match.group(1)
    lines = apps_block.split("\n")
    new_lines = []
    for line in lines:
        if "django." in line or not line.strip() or line.strip().startswith("#"):
            new_lines.append(line)
        else:
            new_lines.append("    # " + line.lstrip())
    new_block = "\n".join(new_lines)
    new_content = content.replace(apps_block, new_block)
    with open(settings_path, "w") as f:
        f.write(new_content)
    log(f"Commented out custom apps in {settings_path}")


# --- ADMIN TEST ---
def test_admin():
    log("Testing admin page...")
    server = subprocess.Popen(
        [sys.executable, "manage.py", "runserver", "localhost:8001", "--noreload"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    time.sleep(3)
    try:
        result = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", ADMIN_URL],
            capture_output=True,
            text=True,
            timeout=10,
        )
        code = result.stdout.strip()
        if code == "200":
            log("Admin page loaded successfully (HTTP 200)")
            return True
        else:
            log(f"Admin page failed to load (HTTP {code})")
            return False
    except Exception as e:
        log(f"Error testing admin page: {e}")
        return False
    finally:
        server.terminate()
        try:
            server.wait(timeout=2)
        except Exception:
            server.kill()


# --- MAIN LOGIC ---
def main():
    log("=" * 60)
    log("Starting Django Admin RecursionError diagnosis")
    log("=" * 60)
    backup_templates()
    backup_settings()
    try:
        # Step 1: Test original config
        log("\nStep 1: Testing with original configuration")
        if test_admin():
            log("No RecursionError detected. Diagnosis complete.")
            return
        # Step 2: Isolate all templates
        log("\nStep 2: Testing with all custom templates removed")
        isolate_templates()
        if test_admin():
            log(
                "RecursionError resolved after removing templates. Restoring templates one by one..."
            )
            # Step 3: Restore templates one by one
            for p in ISOLATED_TEMPLATES.rglob("*"):
                rel = p.relative_to(ISOLATED_TEMPLATES)
                restore_template(rel)
                if not test_admin():
                    log(f"Found problematic template: {rel}")
                    break
                # Remove restored template for next iteration
                if (TEMPLATES_DIR / rel).is_file():
                    (TEMPLATES_DIR / rel).unlink()
                elif (TEMPLATES_DIR / rel).is_dir():
                    shutil.rmtree(TEMPLATES_DIR / rel)
            log("Template isolation diagnosis complete.")
        else:
            # Step 4: Templates not the issue, try INSTALLED_APPS
            log(
                "\nStep 4: Templates not the issue. Testing with minimal INSTALLED_APPS"
            )
            for s in SETTINGS_FILES:
                comment_out_custom_apps(s)
            if test_admin():
                log(
                    "RecursionError resolved after modifying INSTALLED_APPS. The issue is in a custom app."
                )
            else:
                log(
                    "RecursionError persists even with minimal configuration. The issue may be more complex."
                )
    finally:
        log("\nRestoring original configuration...")
        restore_templates()
        restore_settings()
        log("Original configuration restored.")
        log("\nDiagnosis summary:")
        log(f"See detailed results in {LOG_FILE}")


if __name__ == "__main__":
    main()
