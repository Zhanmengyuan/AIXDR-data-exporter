"""PostgreSQL Data Handler"""

import os
from typing import Optional, List, Dict, Any
from .base_handler import DataHandler
from ..postgresql_importer import PostgreSQLImporter
from ..postgresql_exporter import PostgreSQLExporter
from ..data_validator import DataValidator


class PostgreSQLHandler(DataHandler):
    """Handler for PostgreSQL database operations"""

    def export(
        self,
        config: Dict[str, Any],
        asset_ids: Optional[List[int]] = None,
        table_list: Optional[List[str]] = None,
        output_path: Optional[str] = None,
    ) -> str:
        """
        Export data from PostgreSQL
        
        Args:
            config: PostgreSQL connection config
            asset_ids: Asset IDs to export
            table_list: Table names to export (not used, exports all related tables)
            output_path: Output file path

        Returns:
            str: Path to exported file
        """
        if not output_path:
            raise ValueError("Output path is required for export")

        print(f"ℹ Exporting from PostgreSQL to: {output_path}")

        exporter = PostgreSQLExporter(
            host=config['host'],
            user=config['user'],
            password=config['password'],
            database=config['database'],
            port=config.get('port', 5432),
        )

        # Get summary before export
        if asset_ids:
            summary = exporter.get_export_summary(asset_ids)
            if 'error' not in summary:
                print("ℹ Export summary:")
                for table, count in summary.get('tables', {}).items():
                    print(f"  {table}: {count} rows")

        # Export data
        if not exporter.export_by_asset_ids(asset_ids, output_path):
            raise RuntimeError("Export failed")

        print("✓ Export completed successfully")
        return output_path

    def import_data(
        self,
        config: Dict[str, Any],
        input_path: str,
        drop_tables: bool = False,
        asset_ids: Optional[List[int]] = None,
        convert_from_mysql: bool = True,
    ) -> bool:
        """
        Import data to PostgreSQL

        Args:
            config: PostgreSQL connection config
            input_path: Input SQL file path
            drop_tables: Whether to drop tables before import
            asset_ids: List of asset IDs for smart delete
            convert_from_mysql: Whether to convert from MySQL syntax

        Returns:
            bool: True if successful
        """
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input file not found: {input_path}")

        print(f"ℹ Importing from: {input_path}")

        importer = PostgreSQLImporter(
            host=config['host'],
            user=config['user'],
            password=config['password'],
            database=config['database'],
            port=config.get('port', 5432),
        )

        # Create database if needed
        if importer.create_database_if_not_exists():
            print(f"ℹ Database '{config['database']}' is ready")

        # Import data
        if not importer.import_sql(
            input_path,
            drop_tables=drop_tables,
            asset_ids=asset_ids,
            convert_from_mysql=convert_from_mysql
        ):
            raise RuntimeError("Import failed")

        print("✓ Import completed successfully")
        return True

    def verify(
        self,
        config: Dict[str, Any],
        expected_tables: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Verify data in PostgreSQL

        Args:
            config: PostgreSQL connection config
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

        # For now, we'll use a simple verification
        # TODO: Implement proper PostgreSQL data validator
        results = {
            'all_valid': True,
            'tables': {}
        }

        try:
            importer = PostgreSQLImporter(
                host=config['host'],
                user=config['user'],
                password=config['password'],
                database=config['database'],
                port=config.get('port', 5432),
            )

            for table_name in expected_tables:
                exists = importer.table_exists(table_name)
                if exists:
                    count = importer.get_row_count(table_name)
                    results['tables'][table_name] = {
                        'exists': True,
                        'row_count': count,
                        'message': f"✓ {table_name}: {count} rows"
                    }
                else:
                    results['tables'][table_name] = {
                        'exists': False,
                        'row_count': 0,
                        'message': f"✗ {table_name}: does not exist"
                    }
                    results['all_valid'] = False

            if results['all_valid']:
                print("✓ All tables verified successfully!")
                for table_name, info in results['tables'].items():
                    print(f"  {info['message']}")
            else:
                print("⚠ Some tables failed validation")
                for table_name, info in results['tables'].items():
                    print(f"  {info['message']}")

        except Exception as e:
            print(f"Error during verification: {e}")
            results['all_valid'] = False
            results['error'] = str(e)

        return results
