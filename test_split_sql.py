#!/usr/bin/env python3
# Test the SQL splitting function

import sys
import os

# Add the project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from exporter.postgresql_importer import PostgreSQLImporter

# Test file
test_file = '/Users/mengyuan/Documents/trae_projects/AIXDR_data_exporter_custom_副本/exports/assets_export.sql'

# Read the file
with open(test_file, 'r', encoding='utf-8') as f:
    sql_content = f.read()

# Create importer instance
importer = PostgreSQLImporter('localhost', 'root', '', 'test', 5432)

# Split statements
statements = importer._split_sql_statements(sql_content)

print(f"Total statements: {len(statements)}")
print("\n=== First 5 statements ===")
for i, stmt in enumerate(statements[:5]):
    print(f"\n--- Statement {i+1} ---")
    print(stmt[:200])

print("\n=== Statements containing xdr_asset ===")
for i, stmt in enumerate(statements):
    if 'xdr_asset' in stmt.lower() and 'insert' in stmt.lower():
        print(f"\n--- Statement {i+1} ---")
        print(stmt[:300])
