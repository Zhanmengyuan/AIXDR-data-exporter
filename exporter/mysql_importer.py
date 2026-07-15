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

            # Cache for target table columns (for INSERT column filtering)
            target_columns_cache = {}
            rebuild_count = 0
            skip_count = 0

            insert_count = 0
            for stmt in statements:
                if not stmt:
                    continue

                stmt_upper = stmt.upper().strip()

                # When using smart deletion (asset_ids), skip DROP and CREATE table statements
                # as tables already exist and we only want to insert data
                if asset_ids and not drop_tables:
                    # Skip DROP TABLE statements
                    if stmt_upper.startswith('DROP TABLE'):
                        continue
                    # Convert CREATE TABLE to CREATE TABLE IF NOT EXISTS to avoid errors
                    if stmt_upper.startswith('CREATE TABLE'):
                        stmt = stmt.replace('CREATE TABLE', 'CREATE TABLE IF NOT EXISTS', 1)
                        stmt_upper = stmt.upper().strip()

                # Filter INSERT columns to match target table schema
                if stmt_upper.startswith('INSERT INTO'):
                    original_stmt = stmt
                    stmt = self._rebuild_insert_for_target(stmt, cursor, target_columns_cache)
                    if stmt is None:
                        skip_count += 1
                        continue
                    if stmt != original_stmt:
                        rebuild_count += 1

                try:
                    cursor.execute(stmt)
                    if stmt_upper.startswith('INSERT INTO'):
                        insert_count += 1
                        if insert_count % 100 == 0:
                            print(f"  Inserted {insert_count} records...")
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
            if rebuild_count > 0:
                print(f"ℹ Rebuilt {rebuild_count} INSERT statements to match target schema")
            if skip_count > 0:
                print(f"ℹ Skipped {skip_count} INSERT statements (no matching columns)")
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

    def _get_target_columns(self, cursor, table_name: str, cache: dict) -> set:
        """Get column names for a table in the target database (cached)"""
        clean_name = table_name.strip('`"')
        if clean_name in cache:
            return cache[clean_name]

        try:
            cursor.execute(f"DESCRIBE `{clean_name}`")
            cols = {row['Field'].lower() for row in cursor.fetchall()}
            cache[clean_name] = cols
            return cols
        except Exception:
            cache[clean_name] = None
            return None

    def _rebuild_insert_for_target(self, stmt: str, cursor, cache: dict) -> str:
        """Filter INSERT to only include columns that exist in the target table.

        Returns:
            str: Rebuilt INSERT statement, or original if no mismatch.
            None: If no columns match the target (skip this INSERT).
        """
        import re

        match = re.match(
            r'INSERT\s+INTO\s+(?:`([^`]+)`|"([^"]+)"|(\w+))\s*\(\s*(.*?)\s*\)\s*VALUES\s*\(',
            stmt, re.IGNORECASE | re.DOTALL
        )
        if not match:
            return stmt

        table_name = match.group(1) or match.group(2) or match.group(3)
        columns_str = match.group(4)
        raw_columns = [c.strip().strip('`"') for c in columns_str.split(',')]
        columns_lower = [c.lower() for c in raw_columns]

        target_cols = self._get_target_columns(cursor, table_name, cache)
        if target_cols is None:
            return stmt

        missing = {c for c in columns_lower if c not in target_cols}
        if not missing:
            return stmt

        values_start = match.end()
        values_str = self._extract_parenthesized_content(stmt, values_start)
        if values_str is None:
            return stmt

        values = self._parse_sql_row_values(values_str)

        keep_indices = [i for i, c in enumerate(columns_lower) if c not in missing]
        if not keep_indices:
            return None

        if match.group(1):
            table_ref = f'`{table_name}`'
            quote = '`'
        elif match.group(2):
            table_ref = f'"{table_name}"'
            quote = '"'
        else:
            table_ref = table_name
            quote = ''

        new_columns = [f'{quote}{raw_columns[i]}{quote}' for i in keep_indices]
        new_values = [values[i] if i < len(values) else 'NULL' for i in keep_indices]

        return f'INSERT INTO {table_ref} ({", ".join(new_columns)}) VALUES ({", ".join(new_values)});'

    def _extract_parenthesized_content(self, s: str, start: int) -> str:
        """Extract content between matching parentheses, starting right after the opening paren"""
        depth = 1
        result = []
        in_single_quote = False
        in_double_quote = False
        in_backtick = False
        i = start

        while i < len(s):
            char = s[i]

            if char == '\\' and i + 1 < len(s):
                result.append(char)
                result.append(s[i + 1])
                i += 2
                continue

            if char == "'" and not in_double_quote and not in_backtick:
                in_single_quote = not in_single_quote
            elif char == '"' and not in_single_quote and not in_backtick:
                in_double_quote = not in_double_quote
            elif char == '`' and not in_single_quote and not in_double_quote:
                in_backtick = not in_backtick
            elif not in_single_quote and not in_double_quote and not in_backtick:
                if char == '(':
                    depth += 1
                elif char == ')':
                    depth -= 1
                    if depth == 0:
                        return ''.join(result)

            result.append(char)
            i += 1

        return None

    def _parse_sql_row_values(self, values_str: str) -> list:
        """Parse SQL VALUES clause content into individual value strings"""
        values = []
        current = []
        in_single_quote = False
        paren_depth = 0

        for char in values_str:
            if char == "'" and not in_single_quote:
                in_single_quote = True
                current.append(char)
            elif char == "'" and in_single_quote:
                in_single_quote = False
                current.append(char)
            elif char == '(' and not in_single_quote:
                paren_depth += 1
                current.append(char)
            elif char == ')' and not in_single_quote:
                paren_depth -= 1
                if paren_depth >= 0:
                    current.append(char)
            elif char == ',' and not in_single_quote and paren_depth == 0:
                values.append(''.join(current).strip())
                current = []
            else:
                current.append(char)

        if current:
            values.append(''.join(current).strip())

        return values

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
