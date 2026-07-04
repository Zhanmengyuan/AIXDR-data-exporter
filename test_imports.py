#!/usr/bin/env python3
"""
Test that all new PostgreSQL modules import correctly
"""

print("Testing imports...")

# Test 1: Import from sql_converter
print("\n1. Testing sql_converter...")
try:
    from exporter.sql_converter import MySQLToPostgreSQLConverter
    print("   ✓ MySQLToPostgreSQLConverter imported successfully")
except Exception as e:
    print(f"   ✗ Error: {e}")

# Test 2: Import from postgresql_importer
print("\n2. Testing postgresql_importer...")
try:
    from exporter.postgresql_importer import PostgreSQLImporter
    print("   ✓ PostgreSQLImporter imported successfully")
except Exception as e:
    print(f"   ✗ Error: {e}")

# Test 3: Import from postgresql_handler
print("\n3. Testing postgresql_handler...")
try:
    from exporter.handlers.postgresql_handler import PostgreSQLHandler
    print("   ✓ PostgreSQLHandler imported successfully")
except Exception as e:
    print(f"   ✗ Error: {e}")

# Test 4: Import from main exporter package
print("\n4. Testing main exporter package imports...")
try:
    from exporter import (
        PostgreSQLHandler,
        PostgreSQLImporter,
        MySQLToPostgreSQLConverter,
    )
    print("   ✓ All main package imports successful")
except Exception as e:
    print(f"   ✗ Error: {e}")

# Test 5: Test ConfigManager with pg_target
print("\n5. Testing ConfigManager pg_target support...")
try:
    from exporter import ConfigManager
    
    # Test with a sample config
    test_config = {
        "pg_target": {
            "host": "localhost",
            "port": 5432,
            "user": "postgres",
            "password": "test",
            "database": "testdb"
        }
    }
    
    # Test extracting config
    pg_config = ConfigManager.extract_pg_target_config(test_config)
    print(f"   ✓ pg_target extraction works: {pg_config}")
    
    # Test getting target type
    target_type = ConfigManager.get_target_type(test_config)
    print(f"   ✓ Target type detection works: {target_type}")
    
except Exception as e:
    print(f"   ✗ Error: {e}")

print("\n✅ All import tests completed!")
