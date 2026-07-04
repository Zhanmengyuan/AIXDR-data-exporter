"""Operation Classes for Export, Import, and ExportImport"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from datetime import datetime


class Operation(ABC):
    """Base operation class"""

    @abstractmethod
    def execute(self) -> bool:
        """Execute the operation"""
        pass

    def format_timestamp(self) -> str:
        """Get formatted timestamp"""
        return datetime.now().strftime('%Y%m%d_%H%M%S')


class ExportOperation(Operation):
    """Export-only operation"""

    def __init__(
        self,
        handler,
        config: Dict[str, Any],
        mode: str = 'tables',
        asset_ids: Optional[List[int]] = None,
        table_list: Optional[List[str]] = None,
        output_path: Optional[str] = None,
    ):
        """
        Initialize export operation

        Args:
            handler: Data handler (MySQLHandler or ElasticsearchHandler)
            config: Source configuration
            mode: 'asset' or 'tables'
            asset_ids: List of asset IDs (for asset mode)
            table_list: List of table names (for tables mode)
            output_path: Output file path
        """
        self.handler = handler
        self.config = config
        self.mode = mode
        self.asset_ids = asset_ids
        self.table_list = table_list
        self.output_path = output_path

    def execute(self) -> bool:
        """Execute export operation"""
        try:
            self.handler.export(
                self.config,
                asset_ids=self.asset_ids,
                table_list=self.table_list,
                output_path=self.output_path,
            )
            return True
        except Exception as e:
            print(f"Export operation failed: {e}")
            return False


class ImportOperation(Operation):
    """Import-only operation"""

    def __init__(
        self,
        handler,
        config: Dict[str, Any],
        input_path: str,
        drop_tables: bool = False,
        asset_ids: Optional[List[int]] = None,
    ):
        """
        Initialize import operation

        Args:
            handler: Data handler (MySQLHandler or ElasticsearchHandler)
            config: Target configuration
            input_path: Input file path
            drop_tables: Whether to drop tables before import
            asset_ids: List of asset IDs for smart delete (MySQL only)
        """
        self.handler = handler
        self.config = config
        self.input_path = input_path
        self.drop_tables = drop_tables
        self.asset_ids = asset_ids

    def execute(self) -> bool:
        """Execute import operation"""
        try:
            self.handler.import_data(
                self.config,
                self.input_path,
                drop_tables=self.drop_tables,
                asset_ids=self.asset_ids,
            )
            return True
        except Exception as e:
            print(f"Import operation failed: {e}")
            return False


class ExportImportOperation(Operation):
    """Combined export + import operation"""

    def __init__(
        self,
        export_handler,
        import_handler,
        source_config: Dict[str, Any],
        target_config: Dict[str, Any],
        mode: str = 'tables',
        asset_ids: Optional[List[int]] = None,
        table_list: Optional[List[str]] = None,
        temp_file: Optional[str] = None,
        verify_enabled: bool = True,
    ):
        """
        Initialize export+import operation

        Args:
            export_handler: Handler for export (MySQLHandler or ElasticsearchHandler)
            import_handler: Handler for import (MySQLHandler or ElasticsearchHandler)
            source_config: Source configuration
            target_config: Target configuration
            mode: 'asset' or 'tables'
            asset_ids: List of asset IDs (for asset mode)
            table_list: List of table names (for tables mode)
            temp_file: Temporary file for export before import
            verify_enabled: Whether to verify after import
        """
        self.export_handler = export_handler
        self.import_handler = import_handler
        self.source_config = source_config
        self.target_config = target_config
        self.mode = mode
        self.asset_ids = asset_ids
        self.table_list = table_list
        self.temp_file = temp_file or f'./temp_export_{self.format_timestamp()}.sql'
        self.verify_enabled = verify_enabled

    def execute(self) -> bool:
        """Execute export + import operation"""
        try:
            # Step 1: Export
            print("\n" + "=" * 60)
            print("Step 1: Exporting data...")
            print("=" * 60)

            self.export_handler.export(
                self.source_config,
                asset_ids=self.asset_ids,
                table_list=self.table_list,
                output_path=self.temp_file,
            )

            # Step 2: Import
            print("\n" + "=" * 60)
            print("Step 2: Importing data...")
            print("=" * 60)

            self.import_handler.import_data(
                self.target_config,
                self.temp_file,
            )

            # Step 3: Verify (optional)
            if self.verify_enabled:
                print("\n" + "=" * 60)
                print("Step 3: Verifying data...")
                print("=" * 60)

                result = self.import_handler.verify(
                    self.target_config,
                    expected_tables=self.table_list,
                )

                if not result.get('all_valid', False):
                    print("⚠ Some tables failed verification")

            print("\n" + "=" * 60)
            print("✓ Export+Import operation completed!")
            print("=" * 60)

            return True

        except Exception as e:
            print(f"Export+Import operation failed: {e}")
            return False
