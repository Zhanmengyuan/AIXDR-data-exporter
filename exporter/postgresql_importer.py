"""PostgreSQL Data Importer"""

import csv
import json
import re
from typing import Optional, List, Set
import psycopg2
from psycopg2.extras import RealDictCursor
from .sql_converter import MySQLToPostgreSQLConverter


class PostgreSQLImporter:
    """Import data into PostgreSQL database"""

    def __init__(self, host: str, user: str, password: str, database: str, port: int = 5432):
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.port = port
        self.connection = None

    def _connect(self):
        """Establish database connection"""
        if not self.connection:
            self.connection = psycopg2.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                dbname=self.database,
                port=self.port,
            )

    def _disconnect(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            self.connection = None

    def import_sql(self, sql_file: str, drop_tables: bool = False, asset_ids: List = None, convert_from_mysql: bool = True) -> bool:
        """Import data from SQL script
        
        只导入数据（INSERT），不操作表结构（跳过 DROP/CREATE TABLE）。
        表名必须与目标数据库中的表名完全匹配（小写）。

        Args:
            sql_file: Path to SQL file to import
            drop_tables: If True, drop tables before import
            asset_ids: List of asset_ids to delete before import (for smart deletion)
            convert_from_mysql: If True, convert MySQL SQL to PostgreSQL syntax

        Returns:
            bool: True if import successful
        """
        try:
            # Connect
            self._connect()
            cursor = self.connection.cursor()
            
            # Debug connection info
            cursor.execute("SELECT current_database(), current_user, current_schema")
            db_name, db_user, current_schema = cursor.fetchone()
            print(f"ℹ Connected to database: {db_name} as {db_user}, current schema: {current_schema}")
            
            # Read and convert SQL
            print(f"ℹ Reading SQL file...")
            with open(sql_file, 'r', encoding='utf-8') as f:
                sql_content = f.read()
            
            # Split into statements
            statements = self._split_sql_statements(sql_content)
            converted_statements = []
            
            if convert_from_mysql:
                print("Converting MySQL SQL to PostgreSQL syntax...")
                for stmt in statements:
                    if stmt.strip():
                        try:
                            converted_stmt = MySQLToPostgreSQLConverter.convert(stmt)
                            converted_statements.append(converted_stmt)
                        except Exception as e:
                            converted_statements.append(stmt)
            else:
                converted_statements = statements
            
            # Delete existing data if needed (using bare lowercase table names)
            if asset_ids and not drop_tables:
                print(f"Deleting existing data for asset_ids: {asset_ids}")
                # 从 SQL 文件中提取 device_ids（兜底方案，首次导入时目标库 xdr_asset 可能还没有数据）
                parsed_device_ids = self._extract_device_ids_from_sql(sql_content, asset_ids)
                if parsed_device_ids:
                    print(f"  Extracted device_ids from SQL file: {parsed_device_ids}")
                self._delete_by_asset_ids(cursor, asset_ids, parsed_device_ids=parsed_device_ids)
                self.connection.commit()
            
            # Test table accessibility before importing
            print(f"ℹ Testing table accessibility...")
            target_tables = ['xdr_asset', 'xdr_asset_ip', 'xdr_asset_vuln', 'xdr_risk_port', 'xdr_weak_password']
            table_refs = {}  # Cache working table references
            for tbl in target_tables:
                for test_name in [tbl, f"public.{tbl}"]:
                    try:
                        cursor.execute("SAVEPOINT test_tbl")
                        cursor.execute(f"SELECT 1 FROM {test_name} LIMIT 1")
                        cursor.fetchone()
                        cursor.execute("RELEASE SAVEPOINT test_tbl")
                        table_refs[tbl] = test_name
                        print(f"  ✓ '{test_name}' accessible for '{tbl}'")
                        break
                    except Exception:
                        cursor.execute("ROLLBACK TO SAVEPOINT test_tbl")
                if tbl not in table_refs:
                    print(f"  ⚠ Table '{tbl}' not accessible")
            
            # Import data - only INSERT statements, skip DROP/CREATE TABLE
            insert_count = 0
            insert_counts_per_table = {}  # Track inserts per table
            error_count = 0
            for stmt in converted_statements:
                if not stmt.strip():
                    continue
                
                stmt_upper = stmt.upper().strip()
                
                # Skip DROP/CREATE TABLE - do not modify target table structure
                if stmt_upper.startswith('DROP TABLE') or stmt_upper.startswith('CREATE TABLE'):
                    continue
                
                # Skip comment-only lines (but not statements that start with comments followed by INSERT)
                # Check if the statement actually contains an INSERT before skipping
                if stmt.strip().startswith('--') and 'INSERT' not in stmt_upper:
                    continue
                
                # Replace table name with working reference if available
                current_stmt = stmt
                table_name_for_count = None
                if table_refs and ('INSERT INTO' in stmt_upper or stmt_upper.startswith('INSERT INTO')):
                    import re
                    # Match table name with or without quotes, ignoring leading comments/whitespace
                    mt = re.search(r'INSERT\s+INTO\s+(?:"([^"]+)"|([a-zA-Z0-9_.]+))\s*\(', stmt, re.IGNORECASE)
                    if mt:
                        raw_tbl = (mt.group(1) or mt.group(2)).lower().strip()
                        raw_tbl_clean = raw_tbl.split('.')[-1]
                        if raw_tbl_clean in table_refs:
                            correct_ref = table_refs[raw_tbl_clean]
                            if correct_ref != raw_tbl:
                                pattern = r'INSERT\s+INTO\s+(?:"' + re.escape(raw_tbl) + r'"|' + re.escape(raw_tbl) + r')\s*\('
                                replacement = f'INSERT INTO {correct_ref} ('
                                current_stmt = re.sub(pattern, replacement, current_stmt, flags=re.IGNORECASE)
                            table_name_for_count = correct_ref.strip('"')
                        else:
                            if error_count < 3:
                                print(f"  ⚠ Skipping '{raw_tbl_clean}' - table not accessible")
                            error_count += 1
                            continue
                
                # Skip empty statements
                if not current_stmt.strip():
                    continue
                
                try:
                    # 使用 SAVEPOINT 确保单条语句失败不会回滚整个事务
                    sp_id = f"sp_insert_{insert_count}"
                    cursor.execute(f"SAVEPOINT {sp_id}")
                    
                    # Execute the statement
                    cursor.execute(current_stmt)
                    
                    # Release savepoint on success
                    cursor.execute(f"RELEASE SAVEPOINT {sp_id}")
                    
                    # Check if it's an INSERT (even with leading comments)
                    if 'INSERT' in stmt_upper:
                        insert_count += 1
                        if table_name_for_count:
                            insert_counts_per_table[table_name_for_count] = insert_counts_per_table.get(table_name_for_count, 0) + 1
                        if insert_count % 100 == 0:
                            print(f"  Inserted {insert_count} records...")
                    
                    if insert_count % 500 == 0 and insert_count > 0:
                        self.connection.commit()
                        
                except Exception as e:
                    print(f"  Warning: Error inserting (skipping): {str(e)[:100]}")
                    try:
                        cursor.execute(f"ROLLBACK TO SAVEPOINT {sp_id}")
                    except Exception:
                        # 如果 SAVEPOINT 回滚也失败，尝试全局 rollback
                        self.connection.rollback()
                    continue
            
            self.connection.commit()
            print(f"✓ Import completed. Total inserted: {insert_count} records")
            if insert_count > 0:
                # Print per-table summary
                print("\n  Insert summary per table:")
                for tbl, cnt in sorted(insert_counts_per_table.items()):
                    print(f"    - {tbl}: {cnt} rows")
            else:
                print("  No records were inserted (check warnings above for details)")
            self._disconnect()
            return True
            
        except Exception as e:
            print(f"Error importing SQL: {e}")
            import traceback
            traceback.print_exc()
            if self.connection:
                self.connection.rollback()
            self._disconnect()
            return False

    def _split_sql_statements(self, sql_content: str) -> List[str]:
        """Intelligently split SQL statements, handling semicolons in string literals"""
        statements = []
        current = []
        in_single_quote = False
        in_double_quote = False
        in_backtick = False
        i = 0

        while i < len(sql_content):
            char = sql_content[i]

            # Handle escape sequences
            if char == '\\' and i + 1 < len(sql_content):
                current.append(char)
                current.append(sql_content[i + 1])
                i += 2
                continue

            # Handle quotes
            if char == "'" and not in_double_quote and not in_backtick:
                in_single_quote = not in_single_quote
            elif char == '"' and not in_single_quote and not in_backtick:
                in_double_quote = not in_double_quote
            elif char == '`' and not in_single_quote and not in_double_quote:
                in_backtick = not in_backtick
            elif char == ';' and not in_single_quote and not in_double_quote and not in_backtick:
                # Found a statement terminator
                stmt = ''.join(current).strip()
                if stmt:
                    statements.append(stmt)
                current = []
                i += 1
                continue

            current.append(char)
            i += 1

        # Add the last statement if any
        stmt = ''.join(current).strip()
        if stmt:
            statements.append(stmt)

        return statements

    def _table_exists(self, cursor, table_name: str) -> bool:
        """Check if a table exists in the database (using lowercase)"""
        try:
            cursor.execute(
                "SELECT 1 FROM information_schema.tables WHERE table_name = %s",
                (table_name.lower(),)
            )
            return cursor.fetchone() is not None
        except Exception:
            return False

    def _delete_by_asset_ids(self, cursor, asset_ids: List, parsed_device_ids: List = None) -> bool:
        """Delete data related to specific asset_ids from PostgreSQL tables (using bare lowercase names)
        
        对于 xdr_weak_password 表，逻辑是：
        1. 合并从目标库 xdr_asset 查询到的 device_ids 和从 SQL 文件中解析的 device_ids
        2. 先检查这些 device_id 是否在目标库的 xdr_weak_password 中存在
        3. 存在才删除，不存在则跳过（避免无效 DELETE）
        4. 其他表直接按 asset_id 删除
        """
        try:
            asset_id_placeholders = ','.join(['%s'] * len(asset_ids))

            # 从目标库 xdr_asset 中查询 device_ids
            db_device_ids = []
            if self._table_exists(cursor, "xdr_asset"):
                qry_device = f"SELECT DISTINCT device_id FROM xdr_asset WHERE asset_id IN ({asset_id_placeholders}) AND device_id IS NOT NULL"
                cursor.execute(qry_device, asset_ids)
                device_rows = cursor.fetchall()
                db_device_ids = [row[0] for row in device_rows] if device_rows else []

            # 合并两种来源的 device_ids（DB 查询 + SQL 文件解析）
            all_device_ids = list(set(db_device_ids + (parsed_device_ids or [])))

            # 对于 xdr_weak_password：先检查 device_id 是否存在，存在才删除
            if all_device_ids and self._table_exists(cursor, "xdr_weak_password"):
                # 先检查哪些 device_id 在目标库中存在
                valid_device_ids = self._filter_existing_device_ids(cursor, all_device_ids)
                if valid_device_ids:
                    placeholders = ','.join(['%s'] * len(valid_device_ids))
                    cursor.execute(
                        f'DELETE FROM xdr_weak_password WHERE device_id IN ({placeholders})',
                        valid_device_ids
                    )
                    deleted = cursor.rowcount
                    print(f"  ✓ Deleted {deleted} rows from xdr_weak_password (device_ids: {valid_device_ids})")
                else:
                    print(f"  ℹ No existing device_ids found in xdr_weak_password, skipping deletion")

            # 其他表直接按 asset_id 删除
            other_tables = ['xdr_risk_port', 'xdr_asset_vuln', 'xdr_asset_ip', 'xdr_asset']
            for table in other_tables:
                if not self._table_exists(cursor, table):
                    continue
                try:
                    placeholders = ','.join(['%s'] * len(asset_ids))
                    query = f'DELETE FROM {table} WHERE asset_id IN ({placeholders})'
                    cursor.execute(query, asset_ids)
                    deleted = cursor.rowcount
                    if deleted > 0:
                        print(f"  Deleted {deleted} rows from {table}")
                except Exception as e:
                    print(f"  Warning: Could not delete from {table}: {e}")

            return True
        except Exception as e:
            print(f"Error deleting by asset_ids: {e}")
            return False

    def _filter_existing_device_ids(self, cursor, device_ids: List) -> List:
        """检查 device_ids 中哪些在目标库 xdr_weak_password 中真实存在"""
        if not device_ids:
            return []
        placeholders = ','.join(['%s'] * len(device_ids))
        cursor.execute(
            f'SELECT DISTINCT device_id FROM xdr_weak_password WHERE device_id IN ({placeholders})',
            device_ids
        )
        rows = cursor.fetchall()
        return [row[0] for row in rows] if rows else []

    def _extract_device_ids_from_sql(self, sql_content: str, target_asset_ids: List) -> List[str]:
        """从 SQL 文件内容中解析 xdr_asset 的 INSERT 语句，提取 asset_id→device_id 映射
        
        这是兜底方案——当目标库 xdr_asset 还没有数据时（首次导入），
        直接从即将导入的 SQL 中提取 device_ids，用于清理 xdr_weak_password。
        """
        device_ids = set()
        target_ids = set(str(aid) for aid in target_asset_ids)

        # 按语句拆分
        statements = self._split_sql_statements(sql_content)

        for stmt in statements:
            stmt_upper = stmt.upper().strip()
            if not stmt_upper.startswith('INSERT INTO'):
                continue

            # 匹配表名
            mt = re.match(
                r'INSERT\s+INTO\s+(?:"([^"]+)"|([a-zA-Z0-9_.]+))\s*\(',
                stmt, re.IGNORECASE
            )
            if not mt:
                continue
            tbl_name = (mt.group(1) or mt.group(2)).lower()
            tbl_clean = tbl_name.split('.')[-1]
            if tbl_clean != 'xdr_asset':
                continue

            # 提取列名
            paren_start = stmt.index('(')
            paren_end = stmt.index(')')
            cols_str = stmt[paren_start + 1:paren_end]
            columns = [c.strip().strip('"').lower() for c in cols_str.split(',')]

            # 定位 asset_id 和 device_id 的列索引
            try:
                asset_idx = columns.index('asset_id')
            except ValueError:
                continue
            try:
                device_idx = columns.index('device_id')
            except ValueError:
                continue

            # 匹配 VALUES 子句
            values_match = re.search(
                r'VALUES\s*\((.*)\)\s*;?\s*$', stmt, re.IGNORECASE | re.DOTALL
            )
            if not values_match:
                continue

            values_str = values_match.group(1)
            values = self._parse_sql_row_values(values_str)

            if asset_idx < len(values) and device_idx < len(values):
                asset_val = values[asset_idx].strip("'")
                device_val = values[device_idx].strip("'")
                if device_val and asset_val in target_ids:
                    device_ids.add(device_val)

        return list(device_ids)

    def _parse_sql_row_values(self, values_str: str) -> List[str]:
        """解析 SQL VALUES 子句中的值列表，正确处理引号内的逗号"""
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

    def import_csv(self, csv_file: str, table: str, truncate: bool = False) -> bool:
        """Import data from CSV file"""
        try:
            self._connect()
            cursor = self.connection.cursor()

            # Truncate table if requested
            if truncate:
                cursor.execute(f'TRUNCATE TABLE "{table}" RESTART IDENTITY CASCADE')

            # Read CSV and insert data
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)

                for row in reader:
                    columns = list(row.keys())
                    values = []
                    placeholders = []

                    for col in columns:
                        val = row[col]
                        if val is None or val == '':
                            values.append(None)
                        else:
                            values.append(val)
                        placeholders.append('%s')

                    col_names = ', '.join([f'"{c}"' for c in columns])
                    placeholders_str = ', '.join(placeholders)
                    stmt = f'INSERT INTO "{table}" ({col_names}) VALUES ({placeholders_str})'

                    try:
                        cursor.execute(stmt, values)
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
                cursor.execute(f'TRUNCATE TABLE "{table}" RESTART IDENTITY CASCADE')

            # Read JSON Lines and insert data
            with open(json_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    row = json.loads(line)
                    columns = list(row.keys())
                    values = []
                    placeholders = []

                    for col in columns:
                        val = row[col]
                        if val is None:
                            values.append(None)
                        elif isinstance(val, bool):
                            values.append(val)
                        elif isinstance(val, (int, float)):
                            values.append(val)
                        else:
                            values.append(str(val))
                        placeholders.append('%s')

                    col_names = ', '.join([f'"{c}"' for c in columns])
                    placeholders_str = ', '.join(placeholders)
                    stmt = f'INSERT INTO "{table}" ({col_names}) VALUES ({placeholders_str})'

                    try:
                        cursor.execute(stmt, values)
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
            # Connect to default 'postgres' database first
            conn = psycopg2.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                dbname='postgres',
                port=self.port,
            )
            conn.autocommit = True  # Required for CREATE DATABASE
            cursor = conn.cursor()

            # Check if database exists
            cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (self.database,))
            exists = cursor.fetchone()

            if not exists:
                print(f"Creating database {self.database}...")
                cursor.execute(f'CREATE DATABASE "{self.database}"')

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

            cursor.execute(
                "SELECT 1 FROM information_schema.tables WHERE table_name = %s",
                (table.lower(),)
            )
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

            cursor.execute(f'SELECT COUNT(*) FROM "{table}"')
            result = cursor.fetchone()

            self._disconnect()
            return result[0] if result else 0
        except Exception as e:
            print(f"Error getting row count: {e}")
            return -1
