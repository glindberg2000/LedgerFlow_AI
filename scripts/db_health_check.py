#!/usr/bin/env python3
"""
Database health check and validation script
"""

import sqlite3
import sys
from pathlib import Path

def check_database_health(db_path):
    """Comprehensive database health check"""
    print(f"🔍 Analyzing database: {db_path}")
    
    if not Path(db_path).exists():
        print(f"❌ Database file not found: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Integrity check
        cursor.execute("PRAGMA integrity_check")
        integrity = cursor.fetchone()[0]
        if integrity != "ok":
            print(f"❌ Database integrity failed: {integrity}")
            return False
        
        # Check for business profiles
        cursor.execute("""
            SELECT COUNT(*) as total, 
                   COUNT(CASE WHEN company_name != 'ACME Corp' THEN 1 END) as real_profiles
            FROM profiles_businessprofile
        """)
        total_profiles, real_profiles = cursor.fetchone()
        
        # Check transactions
        cursor.execute("SELECT COUNT(*) FROM profiles_transaction")
        transaction_count = cursor.fetchone()[0]
        
        # Check uploaded files (handle missing table gracefully)
        try:
            cursor.execute("SELECT COUNT(*) FROM profiles_uploadedfile")
            file_count = cursor.fetchone()[0]
        except sqlite3.OperationalError:
            file_count = 0
        
        print(f"✅ Database integrity: OK")
        print(f"📊 Business profiles: {total_profiles} total, {real_profiles} real")
        print(f"💰 Transactions: {transaction_count}")
        print(f"📁 Uploaded files: {file_count}")
        
        # Determine if this is production data
        is_production = real_profiles > 0 or transaction_count > 100 or file_count > 5
        
        if is_production:
            print(f"🚨 This appears to be PRODUCTION DATA - handle with extreme care!")
            
            # Show actual business names for verification
            cursor.execute("SELECT company_name FROM profiles_businessprofile WHERE company_name != 'ACME Corp' LIMIT 3")
            business_names = [row[0] for row in cursor.fetchall()]
            if business_names:
                print(f"🏢 Real businesses: {', '.join(business_names)}")
        else:
            print(f"🧪 This appears to be demo/test data")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Database check failed: {e}")
        return False

if __name__ == "__main__":
    db_file = sys.argv[1] if len(sys.argv) > 1 else "ledgerflow.sqlite3"
    success = check_database_health(db_file)
    sys.exit(0 if success else 1)