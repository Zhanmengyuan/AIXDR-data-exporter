"""MySQL Data Handler"""

import os
from typing import Optional, List, Dict, Any
from .base_handler import DataHandler
from ..mysql_exporter import MySQLExporter
from ..mysql_importer import MySQLImporter
from ..related_tables_exporter import RelatedTablesExporter
from ..data_validator import DataValidator


class MySQLHandler(DataHandler):
    """Handler for MySQL database operations"""

    def export(
        self,
        config: Dict[str, Any],
        asset_ids: Optional[List[int]] = None,
        table_list: Optional[List[str]] = None,
        output_path: Optional[str] = None,
    ) -> str:
        """
        Export data from MySQL

        Supports two modes:
        1. Asset mode: Export specific assets with related tables
        2. Tables mode: Export specified tables

        Args:
            config: MySQL connection config (host, user, password, database, port)
            asset_ids: Asset IDs to export (triggers asset mode)
            table_list: Table names to export (triggers tables mode)
            output_path: Output file path

        Returns:
            str: Path to exported SQL file
        """
        if not output_path:
            raise ValueError("output_path is required")

        # Ensure output directory exists
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # Asset mode: use RelatedTablesExporter
        if asset_ids:
            print(f"ℹ Exporting {len(asset_ids)} assets with related tables...")
            exporter = RelatedTablesExporter(
                host=config['host'],
                user=config['user'],
                password=config['password'],
                database=config['database'],
                port=config.get('port', 3306),
            )

            # Get export summary
            summary = exporter.get_export_summary(asset_ids)
            if 'error' in summary:
                raise RuntimeError(f"Could not get summary: {summary['error']}")

            print("ℹ Export summary:")
            total_rows = 0
            for table, count in summary['tables'].items():
                print(f"  {table}: {count} rows")
                total_rows += count
            print(f"ℹ Total rows: {total_rows}")

            # Perform export
            if not exporter.export_by_asset_ids(asset_ids, output_path):
                raise RuntimeError("Export failed")

            print(f"✓ Exported to {output_path}")
            file_size = os.path.getsize(output_path)
            print(f"ℹ File size: {file_size:,} bytes")

        # Tables mode: use MySQLExporter
        elif table_list:
            print(f"ℹ Exporting tables: {', '.join(table_list)}...")
            exporter = MySQLExporter(
                host=config['host'],
                user=config['user'],
                password=config['password'],
                database=config['database'],
                port=config.get('port', 3306),
            )

            if not exporter.export_sql(table_list, output_path):
                raise RuntimeError("Export failed")

            print(f"✓ Exported to {output_path}")
            file_size = os.path.getsize(output_path)
            print(f"ℹ File size: {file_size:,} bytes")

        else:
            raise ValueError("Either asset_ids or table_list must be provided")

        return output_path

    def import_data(
        self,
        config: Dict[str, Any],
        input_path: str,
        drop_tables: bool = False,
        asset_ids: Optional[List[int]] = None,
    ) -> bool:
        """
        Import data to MySQL

        Args:
            config: MySQL connection config
            input_path: Input SQL file path
            drop_tables: Whether to drop tables before import
            asset_ids: List of asset IDs for smart delete (only deletes these assets' data)

        Returns:
            bool: True if successful
        """
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input file not found: {input_path}")

        print(f"ℹ Importing from: {input_path}")

        importer = MySQLImporter(
            host=config['host'],
            user=config['user'],
            password=config['password'],
            database=config['database'],
            port=config.get('port', 3306),
        )

        # Create database if needed
        if importer.create_database_if_not_exists():
            print(f"ℹ Database '{config['database']}' is ready")

        # Import data with smart delete if asset_ids provided
        if asset_ids and not drop_tables:
            print(f"ℹ Smart delete mode: will delete and re-import data for assets {asset_ids}")

        if not importer.import_sql(input_path, drop_tables=drop_tables, asset_ids=asset_ids):
            raise RuntimeError("Import failed")

        print("✓ Import completed successfully")
        return True

    def verify(
        self,
        config: Dict[str, Any],
        expected_tables: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Verify data in MySQL

        Args:
            config: MySQL connection config
            expected_tables: Table names to verify

        Returns:
            dict: Verification results
        """
        if not expected_tables:
            expected_tables = [
                'XDR_ASSET',
                'XDR_ASSET_IP',
                'XDR_ASSET_VULN',
                'XDR_RISK_PORT',
            ]

        print(f"ℹ Verifying tables: {', '.join(expected_tables)}")

        validator = DataValidator(
            host=config['host'],
            user=config['user'],
            password=config['password'],
            database=config['database'],
            port=config.get('port', 3306),
        )

        results = validator.validate_tables(expected_tables)

        if results['all_valid']:
            print("✓ All tables verified successfully!")
            for table_name, info in results['tables'].items():
                print(f"  ✓ {table_name}: {info.get('row_count', 0)} rows")
        else:
            print("⚠ Some tables failed validation")
            for table_name, info in results['tables'].items():
                print(f"  {info['message']}")

        return results
