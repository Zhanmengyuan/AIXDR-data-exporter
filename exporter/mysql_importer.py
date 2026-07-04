"""MySQL Data Importer"""

import csv
import json
from typing import Optional
import pymysql
from pymysql.cursors import DictCursor


class MySQLImporter:
    """Import data into MySQL database"""

    def __init__(self, host: str, user: str, password: str, database: str, port: int = 3306):
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.port = port
        self.connection = None

    def _connect(self):
        """Establish database connection"""
        if not self.connection:
            self.connection = pymysql.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database,
                port=self.port,
                charset='utf8mb4',
                cursorclass=DictCursor
            )

    def _disconnect(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            self.connection = None

    def import_sql(self, sql_file: str, drop_tables: bool = False, asset_ids: list = None) -> bool:
        """Import data from SQL script

        Args:
            sql_file: Path to SQL file to import
            drop_tables: If True, drop tables before import
            asset_ids: List of asset_ids to delete before import (for smart deletion)
                      If provided, only delete data related to these asset_ids

        Returns:
            bool: True if import successful
        """
        try:
            self._connect()
            cursor = self.connection.cursor()

            # Smart deletion: delete only data related to specific asset_ids
            if asset_ids and not drop_tables:
                print(f"Deleting existing data for asset_ids: {asset_ids}")
                self._delete_by_asset_ids(cursor, asset_ids)

            with open(sql_file, 'r', encoding='utf-8') as f:
                sql_content = f.read()

            # Split SQL statements more intelligently
            statements = self._split_sql_statements(sql_content)

            insert_count = 0
            for stmt in statements:
                if not stmt:
                    continue

                # When using smart deletion (asset_ids), skip DROP and CREATE table statements
                # as tables already exist and we only want to insert data
                if asset_ids and not drop_tables:
                    # Skip DROP TABLE statements
                    if stmt.upper().strip().startswith('DROP TABLE'):
                        continue
                    # Convert CREATE TABLE to CREATE TABLE IF NOT EXISTS to avoid errors
                    if stmt.upper().strip().startswith('CREATE TABLE'):
                        stmt = stmt.replace('CREATE TABLE', 'CREATE TABLE IF NOT EXISTS', 1)

                try:
                    # For INSERT statements with smart deletion, use special handling
                    if stmt.upper().strip().startswith('INSERT INTO') and asset_ids and not drop_tables:
                        cursor.execute(stmt)
                        insert_count += 1
                        if insert_count % 100 == 0:
                            print(f"  Inserted {insert_count} records...")
                    else:
                        cursor.execute(stmt)
                except Exception as e:
                    error_str = str(e).lower()
                    # Skip errors for CREATE TABLE IF NOT EXISTS
                    if 'already exists' in error_str and 'CREATE TABLE' in stmt.upper():
                        continue
                    # For INSERT errors, try to continue with a warning
                    elif 'INSERT' in stmt.upper():
                        print(f"  Warning: INSERT error (skipping this record): {str(e)[:80]}")
                        # Try to commit what we have so far and continue
                        self.connection.commit()
                        continue
                    else:
                        print(f"Error executing statement: {e}")
                        print(f"Statement: {stmt[:100]}...")
                        self.connection.rollback()
                        self._disconnect()
                        return False

            self.connection.commit()
            if insert_count > 0:
                print(f"✓ Successfully inserted {insert_count} records")
            self._disconnect()
            return True
        except Exception as e:
            print(f"Error importing SQL: {e}")
            if self.connection:
                self.connection.rollback()
            self._disconnect()
            return False

    def _split_sql_statements(self, sql_content: str) -> list:
        """Intelligently split SQL statements, handling semicolons in string literals"""
        statements = []
        current_stmt = []
        in_single_quote = False
        in_double_quote = False
        i = 0

        while i < len(sql_content):
            char = sql_content[i]

            # Handle escape sequences
            if char == '\\' and i + 1 < len(sql_content):
                current_stmt.append(char)
                current_stmt.append(sql_content[i + 1])
                i += 2
                continue

            # Handle quotes
            if char == "'" and not in_double_quote:
                in_single_quote = not in_single_quote
            elif char == '"' and not in_single_quote:
                in_double_quote = not in_double_quote
            elif char == ';' and not in_single_quote and not in_double_quote:
                # Found a statement terminator
                stmt = ''.join(current_stmt).strip()
                if stmt:
                    statements.append(stmt)
                current_stmt = []
                i += 1
                continue

            current_stmt.append(char)
            i += 1

        # Add the last statement if any
        stmt = ''.join(current_stmt).strip()
        if stmt:
            statements.append(stmt)

        return statements

    def _delete_by_asset_ids(self, cursor, asset_ids: list) -> bool:
        """Delete data related to specific asset_ids"""
        try:
            # Build quoted asset_id list (asset_id is stored as string in DB)
            asset_id_quoted = ','.join(f"'{aid}'" for aid in asset_ids)

            # Debug: show which asset_ids we will target
            print(f"DEBUG: Deleting by asset_ids: {asset_ids}")
            print(f"DEBUG: Quoted asset_id list: {asset_id_quoted}")

            # Get device_ids associated with these assets (for XDR_WEAK_PASSWORD deletion)
            qry_device = f"SELECT DISTINCT device_id FROM XDR_ASSET WHERE asset_id IN ({asset_id_quoted}) AND device_id IS NOT NULL"
            print(f"DEBUG: Device ID query: {qry_device}")
            cursor.execute(qry_device)
            device_rows = cursor.fetchall()
            device_ids = [row['device_id'] for row in device_rows]
            print(f"DEBUG: Collected device_ids: {device_ids}")

            # Delete from related tables
            tables_delete_order = [
                ('XDR_WEAK_PASSWORD', 'device_id', device_ids if device_ids else [], True),  # True = string type
                ('XDR_RISK_PORT', 'asset_id', asset_ids, True),
                ('XDR_ASSET_VULN', 'asset_id', asset_ids, True),
                ('XDR_ASSET_IP', 'asset_id', asset_ids, True),
                ('XDR_ASSET', 'asset_id', asset_ids, True),
            ]

            for table, key, ids, is_string in tables_delete_order:
                if not ids:
                    continue

                try:
                    # Properly quote string IDs
                    if is_string:
                        id_str = ','.join(f"'{id_val}'" for id_val in ids)
                    else:
                        id_str = ','.join(str(id_val) for id_val in ids)
                    # Debug: show delete query before executing
                    query = f"DELETE FROM `{table}` WHERE `{key}` IN ({id_str})"
                    print(f"DEBUG: Delete query: {query}")
                    cursor.execute(query)
                    deleted = cursor.rowcount
                    if deleted > 0:
                        print(f"  Deleted {deleted} rows from {table}")
                except Exception as e:
                    print(f"  Warning: Could not delete from {table}: {e}")

            self.connection.commit()
            return True

        except Exception as e:
            print(f"Error deleting by asset_ids: {e}")
            return False

    def import_csv(self, csv_file: str, table: str, truncate: bool = False) -> bool:
        """Import data from CSV file"""
        try:
            self._connect()
            cursor = self.connection.cursor()

            # Truncate table if requested
            if truncate:
                cursor.execute(f"TRUNCATE TABLE {table}")

            # Read CSV and insert data
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)

                for row in reader:
                    columns = list(row.keys())
                    values = []

                    for col in columns:
                        val = row[col]
                        if val is None or val == '':
                            values.append("NULL")
                        elif val.isdigit():
                            values.append(val)
                        else:
                            escaped = val.replace("'", "''")
                            values.append(f"'{escaped}'")

                    col_names = ", ".join([f"`{c}`" for c in columns])
                    values_str = ", ".join(values)
                    stmt = f"INSERT INTO `{table}` ({col_names}) VALUES ({values_str})"

                    try:
                        cursor.execute(stmt)
                    except Exception as e:
                        print(f"Error inserting row: {e}")
                        self.connection.rollback()
                        self._disconnect()
                        return False

            self.connection.commit()
            self._disconnect()
            return True
        except Exception as e:
            print(f"Error importing CSV: {e}")
            if self.connection:
                self.connection.rollback()
            self._disconnect()
            return False

    def import_json(self, json_file: str, table: str, truncate: bool = False) -> bool:
        """Import data from JSON Lines file"""
        try:
            self._connect()
            cursor = self.connection.cursor()

            # Truncate table if requested
            if truncate:
                cursor.execute(f"TRUNCATE TABLE {table}")

            # Read JSON Lines and insert data
            with open(json_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    row = json.loads(line)
                    columns = list(row.keys())
                    values = []

                    for col in columns:
                        val = row[col]
                        if val is None:
                            values.append("NULL")
                        elif isinstance(val, bool):
                            values.append("1" if val else "0")
                        elif isinstance(val, (int, float)):
                            values.append(str(val))
                        else:
                            escaped = str(val).replace("'", "''")
                            values.append(f"'{escaped}'")

                    col_names = ", ".join([f"`{c}`" for c in columns])
                    values_str = ", ".join(values)
                    stmt = f"INSERT INTO `{table}` ({col_names}) VALUES ({values_str})"

                    try:
                        cursor.execute(stmt)
                    except Exception as e:
                        print(f"Error inserting row: {e}")
                        self.connection.rollback()
                        self._disconnect()
                        return False

            self.connection.commit()
            self._disconnect()
            return True
        except Exception as e:
            print(f"Error importing JSON: {e}")
            if self.connection:
                self.connection.rollback()
            self._disconnect()
            return False

    def create_database_if_not_exists(self) -> bool:
        """Create database if it doesn't exist"""
        try:
            # Connect without specifying database
            conn = pymysql.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                port=self.port,
                charset='utf8mb4'
            )
            cursor = conn.cursor()

            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{self.database}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            conn.commit()
            conn.close()

            return True
        except Exception as e:
            print(f"Error creating database: {e}")
            return False

    def table_exists(self, table: str) -> bool:
        """Check if table exists"""
        try:
            self._connect()
            cursor = self.connection.cursor()

            cursor.execute(f"SHOW TABLES LIKE '{table}'")
            result = cursor.fetchone()

            self._disconnect()
            return result is not None
        except Exception as e:
            print(f"Error checking table: {e}")
            return False

    def get_row_count(self, table: str) -> int:
        """Get row count of a table"""
        try:
            self._connect()
            cursor = self.connection.cursor()

            cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
            result = cursor.fetchone()

            self._disconnect()
            return result['count'] if result else 0
        except Exception as e:
            print(f"Error getting row count: {e}")
            return -1
