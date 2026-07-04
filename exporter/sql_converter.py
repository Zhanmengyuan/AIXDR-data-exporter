"""MySQL to PostgreSQL SQL Converter"""

import re
from typing import List


class MySQLToPostgreSQLConverter:
    """Convert MySQL SQL statements to PostgreSQL-compatible syntax"""

    # PostgreSQL reserved keywords (simplified list)
    RESERVED_KEYWORDS = {
        'ALL', 'ANALYSE', 'ANALYZE', 'AND', 'ANY', 'ARRAY', 'AS', 'ASC', 'ASYMMETRIC',
        'AUTHORIZATION', 'BINARY', 'BOTH', 'CASE', 'CAST', 'CHECK', 'COLLATE', 'COLUMN',
        'CONCURRENTLY', 'CONSTRAINT', 'CREATE', 'CROSS', 'CURRENT_CATALOG', 'CURRENT_DATE',
        'CURRENT_ROLE', 'CURRENT_TIME', 'CURRENT_TIMESTAMP', 'CURRENT_USER', 'DEFAULT',
        'DEFERRABLE', 'DESC', 'DISTINCT', 'DO', 'ELSE', 'END', 'EXCEPT', 'FALSE', 'FETCH',
        'FOR', 'FOREIGN', 'FROM', 'GRANT', 'GROUP', 'HAVING', 'IN', 'INITIALLY', 'INTERSECT',
        'INTO', 'LATERAL', 'LEADING', 'LIMIT', 'LOCALTIME', 'LOCALTIMESTAMP', 'NOT', 'NULL',
        'OF', 'OFFSET', 'ON', 'ONLY', 'OR', 'ORDER', 'PLACING', 'PRIMARY', 'REFERENCES',
        'RETURNING', 'SELECT', 'SESSION_USER', 'SOME', 'SYMMETRIC', 'TABLE', 'THEN', 'TO',
        'TRAILING', 'TRUE', 'UNION', 'UNIQUE', 'USER', 'USING', 'VARIADIC', 'WHEN', 'WHERE',
        'WINDOW', 'WITH',
    }

    # MySQL to PostgreSQL type mapping
    TYPE_MAPPING = {
        # Text types
        'TINYTEXT': 'TEXT',
        'TEXT': 'TEXT',
        'MEDIUMTEXT': 'TEXT',
        'LONGTEXT': 'TEXT',
        'VARCHAR': 'VARCHAR',
        'CHAR': 'CHAR',
        # Numeric types
        'TINYINT': 'SMALLINT',
        'SMALLINT': 'SMALLINT',
        'MEDIUMINT': 'INTEGER',
        'INT': 'INTEGER',
        'INTEGER': 'INTEGER',
        'BIGINT': 'BIGINT',
        'FLOAT': 'REAL',
        'DOUBLE': 'DOUBLE PRECISION',
        'DECIMAL': 'DECIMAL',
        'NUMERIC': 'NUMERIC',
        # Date/Time types
        'DATE': 'DATE',
        'TIME': 'TIME',
        'DATETIME': 'TIMESTAMP',
        'TIMESTAMP': 'TIMESTAMP',
        'YEAR': 'SMALLINT',
        # Binary types
        'BLOB': 'BYTEA',
        'TINYBLOB': 'BYTEA',
        'MEDIUMBLOB': 'BYTEA',
        'LONGBLOB': 'BYTEA',
        'BINARY': 'BYTEA',
        'VARBINARY': 'BYTEA',
        # Boolean types
        'BOOLEAN': 'BOOLEAN',
        'BOOL': 'BOOLEAN',
    }

    @classmethod
    def convert(cls, mysql_sql: str) -> str:
        """Convert MySQL SQL to PostgreSQL SQL"""
        # Normalize line endings
        sql = mysql_sql.replace('\r\n', '\n').replace('\r', '\n')

        # Split into statements (simplified, handles most cases)
        statements = cls._split_statements(sql)
        converted_statements = []

        for stmt in statements:
            if not stmt.strip():
                continue
            try:
                converted = cls._convert_statement(stmt)
                if converted:
                    converted_statements.append(converted)
            except Exception as e:
                # If conversion fails, keep original and warn
                print(f"Warning: Could not convert statement, keeping original: {e}")
                converted_statements.append(stmt)

        return '\n\n'.join(converted_statements) + '\n'

    @classmethod
    def _split_statements(cls, sql: str) -> List[str]:
        """Split SQL into individual statements, handling semicolons in strings"""
        statements = []
        current = []
        in_single_quote = False
        in_double_quote = False
        in_backtick = False
        i = 0

        while i < len(sql):
            char = sql[i]

            # Handle escape sequences
            if char == '\\' and i + 1 < len(sql):
                current.append(char)
                current.append(sql[i + 1])
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
                # End of statement
                stmt = ''.join(current).strip()
                if stmt:
                    statements.append(stmt)
                current = []
                i += 1
                continue

            current.append(char)
            i += 1

        # Add the last statement
        stmt = ''.join(current).strip()
        if stmt:
            statements.append(stmt)

        return statements

    @classmethod
    def _convert_statement(cls, stmt: str) -> str:
        """Convert a single SQL statement"""
        stmt_upper = stmt.upper().strip()

        # Always first convert backticks to double quotes for any statement
        stmt = cls._replace_backticks(stmt)

        if stmt_upper.startswith('CREATE TABLE'):
            return cls._convert_create_table(stmt)
        elif stmt_upper.startswith('DROP TABLE'):
            return cls._convert_drop_table(stmt)
        elif stmt_upper.startswith('INSERT INTO'):
            return cls._convert_insert(stmt)
        elif stmt_upper.startswith('CREATE INDEX') or stmt_upper.startswith('CREATE UNIQUE INDEX'):
            return cls._convert_create_index(stmt)
        elif stmt_upper.startswith('ALTER TABLE'):
            return cls._convert_alter_table(stmt)
        else:
            # For other statements, apply basic conversions
            return cls._apply_basic_conversions(stmt)

    @classmethod
    def _convert_create_table(cls, stmt: str) -> str:
        """Convert CREATE TABLE statement"""
        # Backticks are already replaced in _convert_statement
        sql = stmt

        # Step 1: Handle IF NOT EXISTS
        if 'IF NOT EXISTS' in sql.upper():
            # PostgreSQL supports IF NOT EXISTS for CREATE TABLE
            pass

        # Step 2: Extract and convert column definitions
        # Find the part between parentheses
        open_paren = sql.find('(')
        close_paren = sql.rfind(')')
        if open_paren == -1 or close_paren == -1:
            return sql

        before = sql[:open_paren + 1]
        definitions = sql[open_paren + 1:close_paren]
        after = sql[close_paren:]

        # Convert column definitions
        converted_defs = cls._convert_column_definitions(definitions)

        sql = before + converted_defs + after

        # Step 3: Remove MySQL-specific table options
        # These usually appear at the end of the CREATE TABLE statement
        mysql_options = [
            r'ENGINE\s*=\s*\w+',
            r'DEFAULT\s+CHARSET\s*=\s*[\w]+',
            r'CHARSET\s*=\s*[\w]+',
            r'COLLATE\s*=\s*[\w_]+',
            r'ROW_FORMAT\s*=\s*\w+',
            r'AUTO_INCREMENT\s*=\s*\d+',
            r'COMMENT\s*=\s*\'[^\']*\'',
        ]

        for pattern in mysql_options:
            sql = re.sub(pattern, '', sql, flags=re.IGNORECASE)

        # Clean up extra spaces and semicolons
        sql = re.sub(r'\s*\(\s*\)', '()', sql)
        sql = re.sub(r',\s*,', ',', sql)
        sql = re.sub(r'\s+,', ',', sql)
        sql = re.sub(r',\s+\)', ')', sql)

        # Step 4: Convert AUTO_INCREMENT to SERIAL or BIGSERIAL
        sql = cls._convert_auto_increment(sql)

        # Step 5: Apply other basic conversions
        sql = cls._apply_basic_conversions(sql)

        return sql.strip()

    @classmethod
    def _convert_column_definitions(cls, definitions: str) -> str:
        """Convert column definitions inside CREATE TABLE"""
        # Split into individual columns/constraints
        # This is simplified - for production, use proper SQL parser
        parts = []
        current = []
        depth = 0
        in_single_quote = False
        in_double_quote = False

        for char in definitions:
            if char == '(':
                depth += 1
            elif char == ')':
                depth -= 1
            elif char == "'" and not in_double_quote:
                in_single_quote = not in_single_quote
            elif char == '"' and not in_single_quote:
                in_double_quote = not in_double_quote
            elif char == ',' and depth == 0 and not in_single_quote and not in_double_quote:
                parts.append(''.join(current).strip())
                current = []
                continue

            current.append(char)

        if current:
            parts.append(''.join(current).strip())

        # Process each part
        converted_parts = []
        for part in parts:
            if not part:
                continue
            converted = cls._convert_column_or_constraint(part)
            if converted:
                converted_parts.append(converted)

        return ',\n  '.join(converted_parts)

    @classmethod
    def _convert_column_or_constraint(cls, part: str) -> str:
        """Convert a single column definition or constraint"""
        part_upper = part.upper()

        # Handle PRIMARY KEY
        if 'PRIMARY KEY' in part_upper:
            return cls._convert_primary_key(part)

        # Handle KEY/INDEX
        if part_upper.startswith('KEY ') or part_upper.startswith('INDEX '):
            # Convert to CONSTRAINT or skip (PostgreSQL prefers separate CREATE INDEX)
            return ''  # We'll handle indexes separately

        # Handle UNIQUE KEY
        if 'UNIQUE KEY' in part_upper or 'UNIQUE INDEX' in part_upper:
            return cls._convert_unique_constraint(part)

        # Handle FOREIGN KEY
        if 'FOREIGN KEY' in part_upper:
            return cls._convert_foreign_key(part)

        # It's a column definition
        return cls._convert_column(part)

    @classmethod
    def _convert_column(cls, col_def: str) -> str:
        """Convert a single column definition"""
        # First, check for AUTO_INCREMENT - we'll handle this separately
        has_auto_inc = 'AUTO_INCREMENT' in col_def.upper()

        # Convert data types
        for mysql_type, pg_type in cls.TYPE_MAPPING.items():
            # Match whole word
            pattern = r'\b' + re.escape(mysql_type) + r'\b'
            col_def = re.sub(pattern, pg_type, col_def, flags=re.IGNORECASE)

        # Handle VARCHAR(n) - PostgreSQL supports this
        # Handle INT(11) - PostgreSQL ignores length modifier for integer types
        col_def = re.sub(r'\b(INT|INTEGER|SMALLINT|BIGINT|NUMERIC|DECIMAL)\s*\(\s*\d+\s*\)', r'\1', col_def, flags=re.IGNORECASE)

        # Remove UNSIGNED (PostgreSQL doesn't support)
        col_def = re.sub(r'\bUNSIGNED\b', '', col_def, flags=re.IGNORECASE)

        # Remove ZEROFILL
        col_def = re.sub(r'\bZEROFILL\b', '', col_def, flags=re.IGNORECASE)

        # Convert CHARSET/COLLATE on columns
        col_def = re.sub(r'\bCHARSET\s*=\s*\w+', '', col_def, flags=re.IGNORECASE)
        col_def = re.sub(r'\bCOLLATE\s*=\s*[\w_]+', '', col_def, flags=re.IGNORECASE)

        # Convert COMMENT on columns
        col_def = re.sub(r'\bCOMMENT\s*=\s*\'[^\']*\'', '', col_def, flags=re.IGNORECASE)

        # Convert backticks to quotes
        col_def = cls._replace_backticks(col_def)

        # Remove AUTO_INCREMENT (we handle at table level)
        col_def = re.sub(r'\bAUTO_INCREMENT\b', '', col_def, flags=re.IGNORECASE)

        # Clean up extra spaces
        col_def = re.sub(r'\s+', ' ', col_def).strip()

        return col_def

    @classmethod
    def _convert_auto_increment(cls, sql: str) -> str:
        """Convert AUTO_INCREMENT to SERIAL/BIGSERIAL"""
        # Look for PRIMARY KEY columns with integer types
        # This is simplified - for complex cases, use a proper parser
        if 'SERIAL' in sql.upper() or 'BIGSERIAL' in sql.upper():
            return sql

        # In PostgreSQL, we use SERIAL instead of AUTO_INCREMENT
        # For existing tables, this is more complex. For simplicity,
        # we'll just remove AUTO_INCREMENT and rely on sequences if needed.
        sql = re.sub(r'\bAUTO_INCREMENT\b', '', sql, flags=re.IGNORECASE)

        return sql

    @classmethod
    def _convert_primary_key(cls, part: str) -> str:
        """Convert PRIMARY KEY constraint"""
        part = cls._replace_backticks(part)
        return part

    @classmethod
    def _convert_unique_constraint(cls, part: str) -> str:
        """Convert UNIQUE KEY/INDEX constraint"""
        # Convert "UNIQUE KEY name (col)" to "UNIQUE (col)" or "CONSTRAINT name UNIQUE (col)"
        part_upper = part.upper()

        if 'UNIQUE KEY' in part_upper:
            part = re.sub(r'\bUNIQUE KEY\b', 'UNIQUE', part, flags=re.IGNORECASE)
        elif 'UNIQUE INDEX' in part_upper:
            part = re.sub(r'\bUNIQUE INDEX\b', 'UNIQUE', part, flags=re.IGNORECASE)

        part = cls._replace_backticks(part)
        return part

    @classmethod
    def _convert_foreign_key(cls, part: str) -> str:
        """Convert FOREIGN KEY constraint"""
        part = cls._replace_backticks(part)
        return part

    @classmethod
    def _convert_drop_table(cls, stmt: str) -> str:
        """Convert DROP TABLE statement"""
        # Backticks are already replaced in _convert_statement
        sql = stmt

        # Add IF EXISTS if not present
        if 'IF EXISTS' not in sql.upper():
            sql = re.sub(r'\bDROP TABLE\b', 'DROP TABLE IF EXISTS', sql, flags=re.IGNORECASE)

        return sql

    @classmethod
    def _convert_insert(cls, stmt: str) -> str:
        """Convert INSERT INTO statement"""
        # Backticks are already replaced in _convert_statement
        sql = stmt

        # Fix MySQL-style escaping inside single-quoted string values
        # MySQL:  \" inside '...' means literal "  (MySQL treats \ as escape char)
        # PG:     \" inside '...' means literal \ + " (PG standard_conforming_strings=on)
        # Fix: unescape \" → " inside single-quoted strings for PG compatibility
        #
        # Additional fix for double-escaped quotes:
        # If MySQL data contains \" (escaped quote), mysql_exporter.py will export it as \\"
        # (because backslash is escaped). We need to handle \\\" → \" → " (double unescape)
        result = []
        in_single_quote = False
        i = 0
        while i < len(sql):
            char = sql[i]
            if char == "'" and (i == 0 or sql[i-1] != '\\'):
                in_single_quote = not in_single_quote
                result.append(char)
            elif char == '\\' and in_single_quote and i + 1 < len(sql):
                # Check for double-escaped quote: \\"
                if i + 2 < len(sql) and sql[i+1] == '\\' and sql[i+2] == '"':
                    # Skip both backslashes, output only double quote
                    result.append('"')
                    i += 2  # Skip \\"
                elif sql[i+1] == '"':
                    # Single escaped quote: \"
                    # Skip backslash, output only double quote
                    result.append('"')
                    i += 1
                else:
                    # Other escape sequences, keep as is
                    result.append(char)
            else:
                result.append(char)
            i += 1

        return ''.join(result)

    @classmethod
    def _convert_create_index(cls, stmt: str) -> str:
        """Convert CREATE INDEX statement"""
        # Backticks are already replaced in _convert_statement
        sql = stmt

        # Remove index length specifiers like (191)
        # PostgreSQL doesn't support prefix indexes the same way
        sql = re.sub(r'\((\d+)\)', '', sql)

        # Add IF NOT EXISTS if not present
        if 'IF NOT EXISTS' not in sql.upper():
            sql = re.sub(r'\bCREATE INDEX\b', 'CREATE INDEX IF NOT EXISTS', sql, flags=re.IGNORECASE)
            sql = re.sub(r'\bCREATE UNIQUE INDEX\b', 'CREATE UNIQUE INDEX IF NOT EXISTS', sql, flags=re.IGNORECASE)

        return sql

    @classmethod
    def _convert_alter_table(cls, stmt: str) -> str:
        """Convert ALTER TABLE statement"""
        # Backticks are already replaced in _convert_statement
        sql = stmt
        return sql

    @classmethod
    def _replace_backticks(cls, sql: str) -> str:
        """Replace MySQL backticks with PostgreSQL double quotes, and convert identifiers to lowercase"""
        result = []
        in_single_quote = False
        in_double_quote = False
        in_backtick = False
        current_identifier = []
        i = 0

        while i < len(sql):
            char = sql[i]

            if char == '\\' and i + 1 < len(sql):
                if in_backtick:
                    current_identifier.append(char)
                    current_identifier.append(sql[i + 1])
                else:
                    result.append(char)
                    result.append(sql[i + 1])
                i += 2
                continue

            if char == "'" and not in_double_quote and not in_backtick:
                in_single_quote = not in_single_quote
                result.append(char)
            elif char == '"' and not in_single_quote and not in_backtick:
                in_double_quote = not in_double_quote
                result.append(char)
            elif char == '`' and not in_single_quote and not in_double_quote:
                if in_backtick:
                    # Closing backtick - convert identifier to lowercase and wrap with double quotes
                    identifier = ''.join(current_identifier).lower()
                    result.append(f'"{identifier}"')
                    current_identifier = []
                    in_backtick = False
                else:
                    # Opening backtick - start collecting identifier
                    in_backtick = True
            elif in_backtick:
                current_identifier.append(char)
            else:
                result.append(char)

            i += 1
        
        # If we were still inside a backtick (invalid SQL), append remaining
        if current_identifier:
            result.append(''.join(current_identifier))

        return ''.join(result)

    @classmethod
    def _apply_basic_conversions(cls, sql: str) -> str:
        """Apply basic SQL conversions that apply to all statements"""
        # Convert boolean literals
        sql = sql.replace("'true'", "TRUE")
        sql = sql.replace("'false'", "FALSE")

        # Convert escape sequences
        # MySQL uses \\, PostgreSQL uses \\ when standard_conforming_strings is off
        # For safety, we keep them as is

        return sql
