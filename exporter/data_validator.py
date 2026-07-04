"""Data Validation Module"""

from typing import List, Dict, Tuple
import pymysql
from pymysql.cursors import DictCursor


class DataValidator:
    """Validate and compare database data"""

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

    def validate_table_exists(self, table: str) -> Tuple[bool, str]:
        """Validate that a table exists"""
        try:
            self._connect()
            cursor = self.connection.cursor()

            cursor.execute(f"SHOW TABLES LIKE '{table}'")
            result = cursor.fetchone()

            self._disconnect()

            if result:
                return True, f"✓ Table {table} exists"
            else:
                return False, f"✗ Table {table} does not exist"
        except Exception as e:
            return False, f"✗ Error checking table {table}: {e}"

    def validate_table_has_data(self, table: str) -> Tuple[bool, str, int]:
        """Validate that a table has data"""
        try:
            self._connect()
            cursor = self.connection.cursor()

            cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
            result = cursor.fetchone()
            row_count = result['count'] if result else 0

            self._disconnect()

            if row_count > 0:
                return True, f"✓ Table {table} has {row_count} rows", row_count
            else:
                return False, f"✗ Table {table} is empty", 0
        except Exception as e:
            return False, f"✗ Error checking table data {table}: {e}", 0

    def validate_tables(self, tables: List[str]) -> Dict[str, any]:
        """Validate multiple tables"""
        results = {
            'all_valid': True,
            'tables': {}
        }

        for table in tables:
            exists, msg = self.validate_table_exists(table)
            if not exists:
                results['all_valid'] = False
                results['tables'][table] = {'exists': False, 'message': msg}
                continue

            has_data, data_msg, row_count = self.validate_table_has_data(table)
            results['tables'][table] = {
                'exists': True,
                'has_data': has_data,
                'row_count': row_count,
                'message': data_msg
            }

            if not has_data:
                results['all_valid'] = False

        return results

    def compare_row_counts(self, source_host: str, source_user: str, source_password: str,
                          source_db: str, target_host: str, target_user: str,
                          target_password: str, target_db: str, tables: List[str],
                          source_port: int = 3306, target_port: int = 3306) -> Dict[str, any]:
        """Compare row counts between source and target databases"""
        results = {
            'match': True,
            'tables': {}
        }

        # Connect to source
        try:
            source_conn = pymysql.connect(
                host=source_host,
                user=source_user,
                password=source_password,
                database=source_db,
                port=source_port,
                charset='utf8mb4',
                cursorclass=DictCursor
            )
            source_cursor = source_conn.cursor()
        except Exception as e:
            return {'error': f"Failed to connect to source: {e}"}

        # Connect to target
        try:
            target_conn = pymysql.connect(
                host=target_host,
                user=target_user,
                password=target_password,
                database=target_db,
                port=target_port,
                charset='utf8mb4',
                cursorclass=DictCursor
            )
            target_cursor = target_conn.cursor()
        except Exception as e:
            source_conn.close()
            return {'error': f"Failed to connect to target: {e}"}

        # Compare each table
        for table in tables:
            try:
                source_cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
                source_count = source_cursor.fetchone()['count']

                target_cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
                target_count = target_cursor.fetchone()['count']

                match = source_count == target_count
                if not match:
                    results['match'] = False

                results['tables'][table] = {
                    'source_count': source_count,
                    'target_count': target_count,
                    'match': match,
                    'difference': abs(source_count - target_count)
                }
            except Exception as e:
                results['tables'][table] = {'error': str(e)}
                results['match'] = False

        source_conn.close()
        target_conn.close()

        return results

    def validate_schema(self, table: str) -> Tuple[bool, str, List[Dict]]:
        """Validate table schema (columns and types)"""
        try:
            self._connect()
            cursor = self.connection.cursor()

            cursor.execute(f"DESCRIBE {table}")
            columns = cursor.fetchall()

            self._disconnect()

            return True, f"✓ Table {table} schema is valid", columns
        except Exception as e:
            return False, f"✗ Error validating schema for {table}: {e}", []

    def compare_schemas(self, source_host: str, source_user: str, source_password: str,
                       source_db: str, target_host: str, target_user: str,
                       target_password: str, target_db: str, table: str,
                       source_port: int = 3306, target_port: int = 3306) -> Dict[str, any]:
        """Compare schemas between source and target"""
        results = {
            'match': True,
            'differences': []
        }

        # Get source schema
        try:
            source_conn = pymysql.connect(
                host=source_host,
                user=source_user,
                password=source_password,
                database=source_db,
                port=source_port,
                charset='utf8mb4',
                cursorclass=DictCursor
            )
            source_cursor = source_conn.cursor()
            source_cursor.execute(f"DESCRIBE {table}")
            source_columns = source_cursor.fetchall()
            source_conn.close()
        except Exception as e:
            return {'error': f"Failed to get source schema: {e}"}

        # Get target schema
        try:
            target_conn = pymysql.connect(
                host=target_host,
                user=target_user,
                password=target_password,
                database=target_db,
                port=target_port,
                charset='utf8mb4',
                cursorclass=DictCursor
            )
            target_cursor = target_conn.cursor()
            target_cursor.execute(f"DESCRIBE {table}")
            target_columns = target_cursor.fetchall()
            target_conn.close()
        except Exception as e:
            return {'error': f"Failed to get target schema: {e}"}

        # Compare columns
        source_cols = {c['Field']: c for c in source_columns}
        target_cols = {c['Field']: c for c in target_columns}

        # Check for missing columns
        for col_name in source_cols:
            if col_name not in target_cols:
                results['match'] = False
                results['differences'].append(f"Column '{col_name}' missing in target")

        # Check for extra columns
        for col_name in target_cols:
            if col_name not in source_cols:
                results['match'] = False
                results['differences'].append(f"Column '{col_name}' not in source")

        # Check column types
        for col_name in source_cols:
            if col_name in target_cols:
                if source_cols[col_name]['Type'] != target_cols[col_name]['Type']:
                    results['match'] = False
                    results['differences'].append(
                        f"Column '{col_name}' type mismatch: "
                        f"{source_cols[col_name]['Type']} vs {target_cols[col_name]['Type']}"
                    )

        return results
